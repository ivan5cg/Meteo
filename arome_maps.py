"""Mapas AROME interactivos para visualización de campos meteorológicos en Meteo Dash."""

from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
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


GRID_STEP = 0.05
MAX_WORKERS = 3
REQUEST_PAUSE = 0.15
USER_AGENT = {"User-Agent": "MeteoDash map viewer (personal use)"}

VARIABLES = {
    "Temperatura": {"mode": 8, "cache": "temperatura", "cmap": "RdYlBu_r", "step": 1, "unit": "°C"},
    "Rachas": {"mode": 13, "cache": "rachas", "cmap": "YlOrRd", "step": 5, "unit": "km/h"},
    "Precipitación": {"mode": 10, "cache": "precipitacion", "cmap": "PuBuGn", "step": 0.5, "unit": "mm"},
}

LOCATIONS = {
    "Madrid": {
        "name": "Madrid",
        "center_lat": 40.4623,
        "center_lon": -3.7004,
        "half_side_km": 50,  # 100x100 km = 10.000 km²
        "marker_label": "Chamartín",
        "zoom": 8.95,
        "key_prefix": "madrid",
    },
    "Torrelavega": {
        "name": "Torrelavega",
        "center_lat": 43.35,
        "center_lon": -4.047,
        "half_side_km": 25,  # 50x50 km = 2.500 km²
        "marker_label": "Torrelavega",
        "zoom": 9.95,
        "key_prefix": "torrelavega",
    },
}


def _compute_bounds(center_lat, center_lon, half_side_km):
    """Calcula los límites geográficos (sur, norte, oeste, este) para el semi-lado en km dado."""
    lat_half_span = half_side_km / 111.32
    lon_half_span = half_side_km / (111.32 * np.cos(np.deg2rad(center_lat)))
    south, north = center_lat - lat_half_span, center_lat + lat_half_span
    west, east = center_lon - lon_half_span, center_lon + lon_half_span
    return south, north, west, east


def _points(bounds, grid_step=GRID_STEP):
    """Genera la lista de coordenadas (lat, lon) que cubren los límites dados."""
    south, north, west, east = bounds
    latitudes = np.arange(np.floor(south / grid_step) * grid_step, north + grid_step / 2, grid_step)
    longitudes = np.arange(np.floor(west / grid_step) * grid_step, east + grid_step / 2, grid_step)
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
def _latest_run(center_lat, center_lon):
    """Pasada más reciente: (hora UTC, último instante previsto). El instante identifica la pasada de ese día."""
    reference = (center_lat, center_lon)
    available = {}
    for run in (3, 9, 15, 21):
        try:
            available[run] = _parse(_url(*reference, mode=8, run=run)).index.max()
        except Exception:
            continue
    if not available:
        raise RuntimeError("No se pudo obtener una pasada AROME disponible")
    run = max(available, key=available.get)
    return run, available[run]


@st.cache_resource(show_spinner=False)
def _grids():
    """Rejillas descargadas, en memoria y compartidas por todas las sesiones mientras la app sigue en marcha.

    Clave: (ubicación, variable, pasada). Solo se guarda la pasada más reciente de cada variable.
    """
    return {}


def _fetch_point(lat, lon, mode, run):
    last_error = None
    for attempt in range(3):
        try:
            series = _parse(_url(lat, lon, mode, run))
            time.sleep(REQUEST_PAUSE)
            return pd.DataFrame({"time": series.index, "lat": lat, "lon": lon, "value": series.values})
        except Exception as error:  # reintento ante respuestas temporales de Meteociel
            last_error = error
            time.sleep(0.5 * (attempt + 1))
    raise last_error


def _download_field(spec, run, run_id, bounds, location_key, progress):
    points = _points(bounds)
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

    grids = _grids()
    for key in [k for k in grids if k[:2] == (location_key, spec["cache"])]:
        del grids[key]
    grids[(location_key, spec["cache"], run_id)] = field
    return field


def _regular_grid(data, timestamp):
    field = data.loc[data.time == timestamp, ["lat", "lon", "value"]]
    latitudes = np.sort(field.lat.unique())
    longitudes = np.sort(field.lon.unique())
    values = field.pivot(index="lat", columns="lon", values="value").reindex(index=latitudes, columns=longitudes).to_numpy()
    return longitudes, latitudes, values


def _weather_image(data, timestamp, cmap, levels, bounds):
    south, north, west, east = bounds
    longitudes, latitudes, values = _regular_grid(data, timestamp)
    figure, axis = plt.subplots(figsize=(8, 6), dpi=125)
    figure.patch.set_alpha(0)
    axis.set_facecolor((0, 0, 0, 0))
    axis.contourf(longitudes, latitudes, values, levels=levels, cmap=cmap, alpha=0.60, extend="both", antialiased=True)
    lines = axis.contour(longitudes, latitudes, values, levels=levels, colors="#202020", linewidths=0.65, alpha=0.82)
    axis.clabel(lines, inline=True, fontsize=7, fmt=lambda value: f"{value:g}")
    axis.set(xlim=(west, east), ylim=(south, north))
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


def _weather_layer(image, bounds):
    south, north, west, east = bounds
    return {
        "sourcetype": "image",
        "source": image,
        "coordinates": [[west, north], [east, north], [east, south], [west, south]],
        "below": "traces",
        "opacity": 1,
    }


def _map_title(title, timestamp):
    """Devuelve un encabezado compacto con la fecha/hora local de la previsión."""
    moment = pd.Timestamp(timestamp)
    weekdays = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
    months = (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    )
    label = f"{weekdays[moment.weekday()]}, {moment.day} de {months[moment.month - 1]} · {moment:%H:%M} h"
    return f"<b>{title}</b><br><span style='font-size:12px'>{label}</span>"


@st.cache_data(ttl="30m", max_entries=24, show_spinner=False)
def _build_map(data, title, cmap, interval, bounds, center_lat, center_lon, marker_label, zoom, minimum=None):
    timestamps = sorted(data.time.unique())
    values = data.value.dropna()
    lower = np.floor(values.quantile(0.02) / interval) * interval if minimum is None else minimum
    upper = np.ceil(values.quantile(0.98) / interval) * interval
    if upper <= lower:
        upper = lower + interval
    levels = np.arange(lower, upper + interval * 1.01, interval)
    images = {timestamp: _weather_image(data, timestamp, cmap, levels, bounds) for timestamp in timestamps}
    steps = [
        {
            "label": pd.Timestamp(timestamp).strftime("%d %b %H:%M"),
            "method": "relayout",
            "args": [{
                "mapbox.layers": [TOPO_BASE, _weather_layer(images[timestamp], bounds)],
                "title.text": _map_title(title, timestamp),
            }],
        }
        for timestamp in timestamps
    ]
    figure = go.Figure(go.Scattermapbox(
        lat=[center_lat], lon=[center_lon], mode="markers+text", text=[marker_label],
        textposition="top right", hoverinfo="skip", marker={"size": 8, "color": "#111111"},
        textfont={"color": "#111111", "size": 12}, showlegend=False,
    ))
    figure.update_layout(
        title={"text": _map_title(title, timestamps[0]), "x": 0.5, "xanchor": "center", "y": 0.975},
        height=735,
        mapbox={
            "style": "white-bg", "center": {"lat": center_lat, "lon": center_lon}, "zoom": zoom,
            "layers": [TOPO_BASE, _weather_layer(images[timestamps[0]], bounds)],
        },
        sliders=[{"active": 0, "currentvalue": {"prefix": "Hora local: "}, "pad": {"t": 45}, "steps": steps}],
        margin={"l": 0, "r": 0, "t": 58, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def render_arome_maps(location="Madrid"):
    """Renderiza la pestaña de mapas para la ubicación indicada."""
    if isinstance(location, str):
        if location not in LOCATIONS:
            raise ValueError(f"Ubicación '{location}' no configurada en LOCATIONS ({list(LOCATIONS.keys())})")
        cfg = LOCATIONS[location]
    elif isinstance(location, dict):
        cfg = location
    else:
        raise TypeError("El parámetro 'location' debe ser un string o un dict de configuración.")

    st.header("Mapas AROME")

    name = cfg["name"]
    center_lat = cfg["center_lat"]
    center_lon = cfg["center_lon"]
    half_side_km = cfg["half_side_km"]
    marker_label = cfg.get("marker_label", name)
    zoom = cfg.get("zoom", 8.95)
    key_prefix = cfg.get("key_prefix", name.lower())

    bounds = _compute_bounds(center_lat, center_lon, half_side_km)

    try:
        run, run_id = _latest_run(center_lat, center_lon)
    except RuntimeError as error:
        st.error(str(error))
        return

    selected = st.segmented_control("Variable", list(VARIABLES), default="Temperatura", key=f"{key_prefix}_arome_map_variable")
    if not selected:
        selected = "Temperatura"
    spec = VARIABLES[selected]
    grid_key = (key_prefix, spec["cache"], run_id)
    data = _grids().get(grid_key)
    if data is None:
        st.info(f"Aún no hay una rejilla de {selected.lower()} para la pasada {run:02d}Z.")
        if st.button("Descargar mapa AROME", icon=":material/download:", type="primary", key=f"{key_prefix}_download_btn"):
            progress = st.progress(0, text="Preparando descarga…")
            try:
                _download_field(spec, run, run_id, bounds, key_prefix, progress)
            except RuntimeError as error:
                st.error(str(error))
                return
            finally:
                progress.empty()
            st.rerun()
        return

    if st.button("Actualizar esta variable", icon=":material/refresh:", key=f"{key_prefix}_refresh_btn"):
        _grids().pop(grid_key, None)
        _build_map.clear()
        st.rerun()

    with st.spinner("Preparando isolíneas…"):
        figure = _build_map(
            data,
            f"AROME · {selected} · entorno de {name}",
            spec["cmap"],
            spec["step"],
            bounds,
            center_lat,
            center_lon,
            marker_label,
            zoom,
            0 if selected == "Precipitación" else None,
        )
    st.plotly_chart(figure, width="stretch", config={"scrollZoom": True, "displaylogo": False})
