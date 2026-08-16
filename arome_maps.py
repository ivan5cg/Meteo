"""Mapas AROME interactivos para la pestaña de Madrid."""

from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
import streamlit as st


CENTER_LAT, CENTER_LON = 40.4623, -3.7004  # Chamartín
HALF_SIDE_KM = 50
LAT_HALF_SPAN = HALF_SIDE_KM / 111.32
LON_HALF_SPAN = HALF_SIDE_KM / (111.32 * np.cos(np.deg2rad(CENTER_LAT)))
SOUTH, NORTH = CENTER_LAT - LAT_HALF_SPAN, CENTER_LAT + LAT_HALF_SPAN
WEST, EAST = CENTER_LON - LON_HALF_SPAN, CENTER_LON + LON_HALF_SPAN
GRID_STEP = 0.05
MAX_WORKERS = 3
REQUEST_PAUSE = 0.15
CACHE_DIR = Path("datos_arome_madrid")
USER_AGENT = {"User-Agent": "MeteoDash Madrid map (personal use)"}

VARIABLES = {
    "Temperatura": {"mode": 8, "cache": "temperatura", "cmap": "RdYlBu_r", "step": 1, "unit": "°C"},
    "Rachas": {"mode": 13, "cache": "rachas", "cmap": "YlOrRd", "step": 5, "unit": "km/h"},
    "Precipitación": {"mode": 10, "cache": "precipitacion", "cmap": "PuBuGn", "step": 0.5, "unit": "mm"},
}


def _points():
    latitudes = np.arange(np.floor(SOUTH / GRID_STEP) * GRID_STEP, NORTH + GRID_STEP / 2, GRID_STEP)
    longitudes = np.arange(np.floor(WEST / GRID_STEP) * GRID_STEP, EAST + GRID_STEP / 2, GRID_STEP)
    return [(round(lat, 4), round(lon, 4)) for lat in latitudes for lon in longitudes]


def _url(lat, lon, mode, run=None):
    url = (
        "https://www.meteociel.fr/modeles/pe-arome_table.php?"
        f"x=0&y=0&lat={lat:.4f}&lon={lon:.4f}&mode={mode}&sort=0"
    )
    return f"{url}&run={run}" if run is not None else url


def _parse(url):
    response = requests.get(url, timeout=45, headers=USER_AGENT)
    response.raise_for_status()
    table = BeautifulSoup(response.text, "html.parser").find("table", {"class": "gefs"})
    if table is None:
        raise ValueError("Meteociel no devolvió la tabla AROME esperada")
    rows = table.find_all("tr")
    headers = [cell.get_text(strip=True) for cell in rows[0].find_all("td")]
    records = [[cell.get_text(strip=True) for cell in row.find_all("td")] for row in rows[1:]]
    data = pd.DataFrame(records, columns=headers)
    data["Date"] = pd.to_datetime(data["Date"], utc=True).dt.tz_convert("Europe/Madrid")
    data = data.set_index("Date").drop(columns="Ech.").apply(pd.to_numeric, errors="coerce")
    return data.mean(axis=1).rename("value")


@st.cache_data(ttl="30m", show_spinner=False)
def _latest_run():
    reference = (CENTER_LAT, CENTER_LON)
    available = {}
    for run in (3, 9, 15, 21):
        try:
            available[run] = _parse(_url(*reference, mode=8, run=run)).index.max()
        except Exception:
            continue
    if not available:
        raise RuntimeError("No se pudo obtener una pasada AROME disponible")
    return max(available, key=available.get)


def _cache_file(name, run):
    return CACHE_DIR / f"arome_{name}_run_{run:02d}_square_100km_step_{GRID_STEP:.3f}.pkl"


def _fetch_point(lat, lon, mode, run):
    last_error = None
    for attempt in range(3):
        try:
            series = _parse(_url(lat, lon, mode, run))
            time.sleep(REQUEST_PAUSE)
            return pd.DataFrame({"time": series.index, "lat": lat, "lon": lon, "value": series.values})
        except Exception as error:  # reintento ante respuestas temporales de Meteociel
            last_error = error
            time.sleep(1.5 * (attempt + 1))
    raise last_error


def _download_field(spec, run, progress):
    CACHE_DIR.mkdir(exist_ok=True)
    path = _cache_file(spec["cache"], run)
    if path.exists():
        return pd.read_pickle(path)

    points = _points()
    frames = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_fetch_point, lat, lon, spec["mode"], run) for lat, lon in points]
        for number, future in enumerate(as_completed(futures), start=1):
            try:
                frames.append(future.result())
            except Exception:
                pass
            progress.progress(number / len(points), text=f"Descargando {spec['cache']}: {number}/{len(points)} puntos")
    if not frames:
        raise RuntimeError(f"No se obtuvieron datos de {spec['cache']} desde Meteociel")
    field = pd.concat(frames, ignore_index=True)
    field.to_pickle(path)
    return field


def _load_field(spec, run):
    path = _cache_file(spec["cache"], run)
    return pd.read_pickle(path) if path.exists() else None


def _regular_grid(data, timestamp):
    field = data.loc[data.time == timestamp, ["lat", "lon", "value"]]
    latitudes = np.sort(field.lat.unique())
    longitudes = np.sort(field.lon.unique())
    values = field.pivot(index="lat", columns="lon", values="value").reindex(index=latitudes, columns=longitudes).to_numpy()
    return longitudes, latitudes, values


def _weather_image(data, timestamp, cmap, levels):
    longitudes, latitudes, values = _regular_grid(data, timestamp)
    figure, axis = plt.subplots(figsize=(8, 6), dpi=125)
    figure.patch.set_alpha(0)
    axis.set_facecolor((0, 0, 0, 0))
    axis.contourf(longitudes, latitudes, values, levels=levels, cmap=cmap, alpha=0.60, extend="both", antialiased=True)
    lines = axis.contour(longitudes, latitudes, values, levels=levels, colors="#202020", linewidths=0.65, alpha=0.82)
    axis.clabel(lines, inline=True, fontsize=7, fmt=lambda value: f"{value:g}")
    axis.set(xlim=(WEST, EAST), ylim=(SOUTH, NORTH))
    axis.axis("off")
    figure.subplots_adjust(left=0, right=1, bottom=0, top=1)
    buffer = BytesIO()
    figure.savefig(buffer, format="png", transparent=True, dpi=125, pad_inches=0)
    plt.close(figure)
    return "data:image/png;base64," + b64encode(buffer.getvalue()).decode("ascii")


TOPO_BASE = {
    "sourcetype": "raster",
    "source": ["https://a.tile.opentopomap.org/{z}/{x}/{y}.png"],
    "sourceattribution": "© OpenStreetMap contributors, SRTM | OpenTopoMap (CC-BY-SA)",
    "opacity": 0.48,
    "below": "traces",
}


def _weather_layer(image):
    return {
        "sourcetype": "image",
        "source": image,
        "coordinates": [[WEST, NORTH], [EAST, NORTH], [EAST, SOUTH], [WEST, SOUTH]],
        "below": "traces",
        "opacity": 1,
    }


@st.cache_data(ttl="30m", max_entries=12, show_spinner=False)
def _build_map(data, title, cmap, interval, minimum=None):
    timestamps = sorted(data.time.unique())
    values = data.value.dropna()
    lower = np.floor(values.quantile(0.02) / interval) * interval if minimum is None else minimum
    upper = np.ceil(values.quantile(0.98) / interval) * interval
    if upper <= lower:
        upper = lower + interval
    levels = np.arange(lower, upper + interval * 1.01, interval)
    images = {timestamp: _weather_image(data, timestamp, cmap, levels) for timestamp in timestamps}
    steps = [
        {
            "label": pd.Timestamp(timestamp).strftime("%d %b %H:%M"),
            "method": "relayout",
            "args": [{"mapbox.layers": [TOPO_BASE, _weather_layer(images[timestamp])]}],
        }
        for timestamp in timestamps
    ]
    figure = go.Figure(go.Scattermapbox(
        lat=[CENTER_LAT], lon=[CENTER_LON], mode="markers+text", text=["Chamartín"],
        textposition="top right", hoverinfo="skip", marker={"size": 8, "color": "#111111"},
        textfont={"color": "#111111", "size": 12}, showlegend=False,
    ))
    figure.update_layout(
        title={"text": title, "x": 0.5}, height=760,
        mapbox={
            "style": "white-bg", "center": {"lat": CENTER_LAT, "lon": CENTER_LON}, "zoom": 8.95,
            "layers": [TOPO_BASE, _weather_layer(images[timestamps[0]])],
        },
        sliders=[{"active": 0, "currentvalue": {"prefix": "Hora local: "}, "pad": {"t": 45}, "steps": steps}],
        margin={"l": 0, "r": 0, "t": 75, "b": 20}, paper_bgcolor="white",
    )
    return figure


def render_arome_maps():
    """Renderiza la pestaña de mapas sin tocar ni recalcular la previsión habitual."""
    st.header("Mapas AROME")
    st.caption("Entorno de 10.000 km² centrado en Chamartín. Fondo topográfico tenue e isolíneas AROME.")
    try:
        run = _latest_run()
    except RuntimeError as error:
        st.error(str(error))
        return

    selected = st.segmented_control("Variable", list(VARIABLES), default="Temperatura", key="arome_map_variable")
    spec = VARIABLES[selected]
    data = _load_field(spec, run)
    if data is None:
        st.info(f"Aún no hay una rejilla de {selected.lower()} para la pasada {run:02d}Z.")
        if st.button("Descargar mapa AROME", icon=":material/download:", type="primary"):
            progress = st.progress(0, text="Preparando descarga…")
            try:
                data = _download_field(spec, run, progress)
            except RuntimeError as error:
                st.error(str(error))
                return
            finally:
                progress.empty()
            st.rerun()
        return

    if st.button("Actualizar esta variable", icon=":material/refresh:"):
        _cache_file(spec["cache"], run).unlink(missing_ok=True)
        _build_map.clear()
        st.rerun()

    with st.spinner("Preparando isolíneas…"):
        figure = _build_map(data, f"AROME · {selected} · entorno de Madrid", spec["cmap"], spec["step"], 0 if selected == "Precipitación" else None)
    st.plotly_chart(figure, width="stretch", config={"scrollZoom": True, "displaylogo": False})
