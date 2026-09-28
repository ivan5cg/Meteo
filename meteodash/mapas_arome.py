"""Mapas AROME interactivos: rejillas de puntos del ensemble PE-AROME de Meteociel dibujadas como isolíneas.

Cada rejilla son cientos de tablas de Meteociel, así que se descarga en un hilo en segundo plano (sigue aunque el
visitante cambie de página) y se guarda en memoria, compartida entre visitantes. Las imágenes se generan hora a
hora, solo la que se está viendo, y quedan en caché.
"""

from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from io import BytesIO
import threading
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .fuentes import MODOS_AROME, RUNS_AROME, get_last_run, leer_tabla_meteociel, url_arome
from .graficos import dia_semana

MAX_WORKERS = 3
REQUEST_PAUSE = 0.15
TZ = "Europe/Madrid"

VARIABLES = {
    "Temperatura": {"cache": "temperatura", "cmap": "RdYlBu_r", "step": 1, "unit": "°C"},
    "Rachas": {"cache": "rachas", "cmap": "YlOrRd", "step": 5, "unit": "km/h"},
    "Precipitación": {"cache": "precipitacion", "cmap": "PuBuGn", "step": 0.5, "unit": "mm"},
}

LOCATIONS = {
    "Madrid": {
        "name": "Madrid",
        "center_lat": 40.4623,
        "center_lon": -3.7004,
        "half_side_km": 50,  # 100x100 km = 10.000 km²
        "grid_step": 0.08,  # ~200 puntos (con 0.05 serían ~475)
        "marker_label": "Chamartín",
        "zoom": 8.95,
        "key_prefix": "madrid",
    },
    "Torrelavega": {
        "name": "Torrelavega",
        "center_lat": 43.35,
        "center_lon": -4.047,
        "half_side_km": 25,  # 50x50 km = 2.500 km²
        "grid_step": 0.05,  # ~140 puntos
        "marker_label": "Torrelavega",
        "zoom": 9.95,
        "key_prefix": "torrelavega",
    },
}

TOPO_BASE = {
    "sourcetype": "raster",
    "source": ["https://a.tile.opentopomap.org/{z}/{x}/{y}.png"],
    "sourceattribution": "© OpenStreetMap contributors, SRTM | OpenTopoMap (CC-BY-SA)",
    "opacity": 0.48,
    "below": "traces",
}


def _compute_bounds(center_lat, center_lon, half_side_km):
    """Calcula los límites geográficos (sur, norte, oeste, este) para el semi-lado en km dado."""
    lat_half_span = half_side_km / 111.32
    lon_half_span = half_side_km / (111.32 * np.cos(np.deg2rad(center_lat)))
    south, north = center_lat - lat_half_span, center_lat + lat_half_span
    west, east = center_lon - lon_half_span, center_lon + lon_half_span
    return south, north, west, east


def _points(bounds, grid_step):
    """Genera la lista de coordenadas (lat, lon) que cubren los límites dados."""
    south, north, west, east = bounds
    latitudes = np.arange(np.floor(south / grid_step) * grid_step, north + grid_step / 2, grid_step)
    longitudes = np.arange(np.floor(west / grid_step) * grid_step, east + grid_step / 2, grid_step)
    return [(round(lat, 4), round(lon, 4)) for lat in latitudes for lon in longitudes]


# ---------------------------------------------------------------- Descarga en segundo plano

@dataclass
class _Download:
    total: int
    done: int = 0
    error: str | None = None


@st.cache_resource(show_spinner=False)
def _state():
    """Rejillas descargadas y descargas en curso, en memoria y compartidas por todas las sesiones.

    Clave: (ubicación, variable, inicio de la pasada). Solo se guarda la pasada más reciente de cada variable.
    """
    return {"grids": {}, "downloads": {}, "lock": threading.Lock()}


def _fetch_point(lat, lon, mode, run):
    last_error = None
    for attempt in range(3):
        try:
            series = leer_tabla_meteociel(f"{url_arome(lat, lon, mode)}&run={run}", TZ).mean(axis=1)
            time.sleep(REQUEST_PAUSE)
            return pd.DataFrame({"time": series.index, "lat": lat, "lon": lon, "value": series.values})
        except Exception as error:  # reintento ante respuestas temporales de Meteociel
            last_error = error
            time.sleep(0.5 * (attempt + 1))
    raise last_error


def _download_field(state, key, download, mode, run, points):
    """Descarga la rejilla (en un hilo propio: no usa Streamlit) y la guarda en el estado compartido."""
    frames = []
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(_fetch_point, lat, lon, mode, run) for lat, lon in points]
            for future in as_completed(futures):
                try:
                    frames.append(future.result())
                except Exception:
                    pass
                download.done += 1
        if not frames:
            raise RuntimeError("Meteociel no ha devuelto datos para ningún punto de la rejilla")
        field = pd.concat(frames, ignore_index=True)
        with state["lock"]:
            for old in [k for k in state["grids"] if k[:2] == key[:2]]:
                del state["grids"][old]
            state["grids"][key] = field
            del state["downloads"][key]
    except Exception as error:
        download.error = str(error)


def _start_download(key, mode, run, points):
    state = _state()
    with state["lock"]:
        if key in state["grids"] or key in state["downloads"]:
            return  # otro visitante ya la tiene o la está descargando
        download = state["downloads"][key] = _Download(total=len(points))
    threading.Thread(target=_download_field, args=(state, key, download, mode, run, points), daemon=True).start()


@st.fragment(run_every="1s")
def _download_progress(key, label):
    state = _state()
    download = state["downloads"].get(key)
    if download is None:  # terminada: se recarga la página para mostrar el mapa
        st.rerun()
    if download.error:
        st.error(f"No se ha podido descargar la rejilla de {label}: {download.error}")
        if st.button("Reintentar", icon=":material/refresh:", key=f"{key[0]}_retry_btn"):
            with state["lock"]:
                state["downloads"].pop(key, None)
            st.rerun()
        return
    st.progress(download.done / download.total,
                text=f"Descargando {label}: {download.done}/{download.total} puntos. Puedes seguir navegando mientras tanto.")


# ---------------------------------------------------------------- Imágenes

@st.cache_data(ttl="1h", max_entries=24, show_spinner=False)
def _levels(key, _data, interval, minimum=None):
    """Niveles de las isolíneas, comunes a todas las horas de la rejilla `key`."""
    values = _data.value.dropna()
    lower = np.floor(values.quantile(0.02) / interval) * interval if minimum is None else minimum
    upper = np.ceil(values.quantile(0.98) / interval) * interval
    if upper <= lower:
        upper = lower + interval
    return tuple(np.arange(lower, upper + interval * 1.01, interval))


def _regular_grid(data, timestamp):
    field = data.loc[data.time == timestamp, ["lat", "lon", "value"]]
    latitudes = np.sort(field.lat.unique())
    longitudes = np.sort(field.lon.unique())
    values = field.pivot(index="lat", columns="lon", values="value").reindex(index=latitudes, columns=longitudes).to_numpy()
    return longitudes, latitudes, values


@st.cache_data(ttl="1h", max_entries=150, show_spinner=False)
def _weather_image(key, _data, timestamp, cmap, levels, bounds):
    """PNG (data URI) de una hora de la rejilla `key`. `_data` no se hashea: la clave ya identifica la rejilla."""
    south, north, west, east = bounds
    longitudes, latitudes, values = _regular_grid(_data, timestamp)
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


# ---------------------------------------------------------------- Página

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
    marker_label = cfg.get("marker_label", name)
    zoom = cfg.get("zoom", 8.95)
    key_prefix = cfg.get("key_prefix", name.lower())

    bounds = _compute_bounds(center_lat, center_lon, cfg["half_side_km"])

    try:
        run, run_start = get_last_run(url_arome(center_lat, center_lon, MODOS_AROME["temperatura"]), RUNS_AROME, TZ)
    except Exception:
        st.error("No se ha podido obtener una pasada AROME disponible en Meteociel. Prueba a recargar en unos minutos.")
        return

    selected = st.segmented_control("Variable", list(VARIABLES), default="Temperatura", key=f"{key_prefix}_arome_map_variable")
    if not selected:
        selected = "Temperatura"
    spec = VARIABLES[selected]
    grid_key = (key_prefix, spec["cache"], run_start)
    state = _state()
    data = state["grids"].get(grid_key)

    if data is None:
        if grid_key in state["downloads"]:
            _download_progress(grid_key, selected.lower())
            return
        st.info(f"Aún no hay una rejilla de {selected.lower()} para la pasada {run:02d}Z.")
        if st.button("Descargar mapa AROME", icon=":material/download:", type="primary", key=f"{key_prefix}_download_btn"):
            _start_download(grid_key, MODOS_AROME[spec["cache"]], run, _points(bounds, cfg.get("grid_step", 0.05)))
            st.rerun()
        return

    if st.button("Actualizar esta variable", icon=":material/refresh:", key=f"{key_prefix}_refresh_btn"):
        with state["lock"]:
            state["grids"].pop(grid_key, None)
        _levels.clear()
        _weather_image.clear()
        st.rerun()

    timestamps = sorted(data.time.unique())
    now = pd.Timestamp.now(tz=TZ).floor("h")
    moment = st.select_slider(
        "Hora local",
        options=timestamps,
        value=next((t for t in timestamps if t >= now), timestamps[0]),
        format_func=lambda t: f"{dia_semana(t)} · {t:%H:%M}",
        key=f"{key_prefix}_{spec['cache']}_{run_start:%Y%m%d%H}_arome_map_time",
    )

    levels = _levels(grid_key, data, spec["step"], 0 if selected == "Precipitación" else None)
    with st.spinner("Preparando isolíneas…"):
        image = _weather_image(grid_key, data, moment, spec["cmap"], levels, bounds)

    figure = go.Figure(go.Scattermapbox(
        lat=[center_lat], lon=[center_lon], mode="markers+text", text=[marker_label],
        textposition="top right", hoverinfo="skip", marker={"size": 8, "color": "#111111"},
        textfont={"color": "#111111", "size": 12}, showlegend=False,
    ))
    figure.update_layout(
        title={"text": _map_title(f"AROME · {selected} · entorno de {name}", moment), "x": 0.5, "xanchor": "center", "y": 0.975},
        height=700,
        mapbox={
            "style": "white-bg", "center": {"lat": center_lat, "lon": center_lon}, "zoom": zoom,
            "layers": [TOPO_BASE, _weather_layer(image, bounds)],
        },
        margin={"l": 0, "r": 0, "t": 58, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        uirevision=key_prefix,  # conserva el zoom y el encuadre al cambiar de hora o de variable
    )
    st.plotly_chart(figure, config={"scrollZoom": True, "displaylogo": False}, key=f"{key_prefix}_arome_map")
