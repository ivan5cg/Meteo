"""Mapas AROME interactivos: rejillas de puntos del ensemble PE-AROME de Meteociel, en un visor propio con MapLibre.

Cada rejilla son cientos de tablas de Meteociel, así que se descarga en un hilo en segundo plano (sigue aunque el
visitante cambie de página) y se guarda en memoria, compartida entre visitantes. El visor (visor_arome.js) recibe
todas las horas de una vez y hace en el navegador el campo de colores, las isolíneas y la línea de tiempo, así que
cambiar de hora o de punto no recarga la página.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import threading
import time

import numpy as np
import pandas as pd
import streamlit as st

from .fuentes import MODOS_AROME, RUNS_AROME, get_last_run, leer_tabla_meteociel, url_arome

MAX_WORKERS = 3
REQUEST_PAUSE = 0.15
TZ = "Europe/Madrid"

# "cache" es también la escala de colores del visor; "step", la equidistancia de las isolíneas (la lluvia tiene las suyas)
VARIABLES = {
    "Temperatura": {"cache": "temperatura", "step": 1, "unit": "°C", "decimals": 1},
    "Rachas": {"cache": "rachas", "step": 5, "unit": "km/h", "decimals": 0},
    "Precipitación": {"cache": "precipitacion", "step": 0.5, "unit": "L/m²", "decimals": 1},
}

# Cada rejilla tiene que caer entera dentro del dominio del PE-AROME (selector_punto.DOMINIO_AROME): fuera, Meteociel
# devuelve valores de relleno. El marcador es el punto de la previsión de la página, salvo en Madrid
LOCATIONS = {
    "Madrid": {
        "name": "Madrid",
        "center_lat": 40.4623,
        "center_lon": -3.7004,
        "half_side_km": 50,  # 100x100 km = 10.000 km²
        "grid_step": 0.08,  # ~200 puntos (con 0.05 serían ~475)
        # Punto por defecto del visor: la estación de AEMET del Retiro (3195), la de las observaciones de la página
        "marker_label": "Retiro",
        "marker_lat": 40.4111,
        "marker_lon": -3.6781,
        "key_prefix": "madrid",
    },
    "Torrelavega": {
        "name": "Torrelavega",
        "center_lat": 43.35,
        "center_lon": -4.047,
        "half_side_km": 25,  # 50x50 km = 2.500 km²
        "grid_step": 0.05,  # ~140 puntos
        "marker_label": "Torrelavega",
        "marker_lat": 43.35,
        "marker_lon": -4.047,
        "key_prefix": "torrelavega",
    },
    "Ávila": {
        "name": "Ávila",
        "center_lat": 40.659,
        "center_lon": -4.680,
        "half_side_km": 35,  # 70x70 km: Gredos al sur y el oeste de Guadarrama
        "grid_step": 0.06,  # ~180 puntos
        "marker_label": "Ávila",
        "marker_lat": 40.659,
        "marker_lon": -4.680,
        "key_prefix": "avila",
    },
    "Santander": {
        "name": "Santander",
        "center_lat": 43.4661,
        "center_lon": -3.798,
        "half_side_km": 25,  # 50x50 km
        "grid_step": 0.05,  # ~150 puntos
        "marker_label": "Santander",
        "marker_lat": 43.4661,
        "marker_lon": -3.798,
        "key_prefix": "santander",
    },
    "Alicante": {
        "name": "Alicante",
        "center_lat": 38.346,
        "center_lon": -0.48,
        "half_side_km": 25,  # 50x50 km; con más, el borde sur se acercaría al límite del dominio
        "grid_step": 0.05,  # ~140 puntos
        "marker_label": "Alicante",
        "marker_lat": 38.346,
        "marker_lon": -0.48,
        "key_prefix": "alicante",
    },
}

VIEWER = st.components.v2.component(
    "visor_arome", isolate_styles=False,
    html='<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.css">'
         '<div class="visor-arome" tabindex="0"><div class="va-marco"><div class="va-mapa"></div>'
         '<div class="va-tarjeta"><div class="va-titulo"><b></b><span></span></div><div class="va-barra"></div>'
         '<div class="va-marcas"></div><div class="va-fuente"></div></div>'
         '<div class="va-globo"></div><div class="va-aviso">Cargando el mapa…</div></div>'
         '<div class="va-tiempo"><button class="va-play" title="Reproducir o pausar (barra espaciadora)"></button>'
         '<div class="va-pista"><div class="va-cabecera"><span class="va-hora"></span><span class="va-lectura"></span>'
         '</div><svg class="va-serie"></svg></div></div></div>',
    css=Path(__file__).with_name("visor_arome.css").read_text(encoding="utf-8"),
    js=Path(__file__).with_name("visor_arome.js").read_text(encoding="utf-8"),
)


def _compute_bounds(center_lat, center_lon, half_side_km):
    """Calcula los límites geográficos (sur, norte, oeste, este) para el semi-lado en km dado."""
    lat_half_span = half_side_km / 111.32
    lon_half_span = half_side_km / (111.32 * np.cos(np.deg2rad(center_lat)))
    south, north = center_lat - lat_half_span, center_lat + lat_half_span
    west, east = center_lon - lon_half_span, center_lon + lon_half_span
    return south, north, west, east


def _axes(bounds, grid_step):
    """Latitudes y longitudes (crecientes) de la rejilla que cubre los límites dados."""
    south, north, west, east = bounds
    latitudes = np.arange(np.floor(south / grid_step) * grid_step, north + grid_step / 2, grid_step)
    longitudes = np.arange(np.floor(west / grid_step) * grid_step, east + grid_step / 2, grid_step)
    return [round(float(lat), 4) for lat in latitudes], [round(float(lon), 4) for lon in longitudes]


def _points(bounds, grid_step):
    """Genera la lista de coordenadas (lat, lon) que cubren los límites dados."""
    latitudes, longitudes = _axes(bounds, grid_step)
    return [(lat, lon) for lat in latitudes for lon in longitudes]


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


# ---------------------------------------------------------------- Visor

@st.cache_data(ttl="1h", max_entries=12, show_spinner=False)
def _viewer_grid(key, _data, latitudes, longitudes):
    """Rejilla `key` para el visor: horas (ms desde 1970) y, por hora, los valores de sur a norte y de oeste a este,
    con None donde falta el punto. `_data` no se hashea: la clave ya identifica la rejilla."""
    cube = (_data.pivot(index="time", columns=["lat", "lon"], values="value").sort_index()
            .reindex(columns=pd.MultiIndex.from_product([latitudes, longitudes])))
    values = cube.to_numpy(dtype=float).round(1)
    return {
        # Cambia con cada descarga (también al actualizar la misma pasada): el visor solo recalcula si cambia
        "clave": f"{key[1]}_{key[2]:%Y%m%d%H}_{time.time_ns()}",
        "horas": (cube.index.asi8 // 10**6).tolist(),
        "valores": [[None if np.isnan(value) else float(value) for value in row] for row in values],
        "faltan": int(cube.isna().all().sum()),
    }


# ---------------------------------------------------------------- Página

def render_arome_maps(location):
    """Renderiza la pestaña de mapas para una ubicación de LOCATIONS."""
    cfg = LOCATIONS[location]

    st.header("Mapas AROME")

    center_lat = cfg["center_lat"]
    center_lon = cfg["center_lon"]
    key_prefix = cfg["key_prefix"]

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
            _start_download(grid_key, MODOS_AROME[spec["cache"]], run, _points(bounds, cfg["grid_step"]))
            st.rerun()
        return

    if st.button("Actualizar esta variable", icon=":material/refresh:", key=f"{key_prefix}_refresh_btn"):
        with state["lock"]:
            state["grids"].pop(grid_key, None)
        _viewer_grid.clear()
        st.rerun()

    latitudes, longitudes = _axes(bounds, cfg["grid_step"])
    grid = _viewer_grid(grid_key, data, latitudes, longitudes)
    # Misma clave para las tres variables: al cambiar de una a otra, el mapa conserva el encuadre, la hora y el punto
    VIEWER(key=f"{key_prefix}_arome_viewer", data={
        "variable": selected, "paleta": spec["cache"], "unidad": spec["unit"], "paso": spec["step"],
        "decimales": spec["decimals"], "pasada": f"{run:02d}Z", "tz": TZ, "lats": latitudes, "lons": longitudes,
        "lugar": {"nombre": cfg["marker_label"], "lat": cfg["marker_lat"], "lon": cfg["marker_lon"]},
        **grid,
    })

    total = len(latitudes) * len(longitudes)
    missing = (f" Meteociel no ha devuelto {grid['faltan']} de los puntos: se rellenan con la media de sus vecinos."
               if grid["faltan"] else "")
    st.caption(f"Media del ensemble PE-AROME de Météo-France (vía Meteociel) en {total} puntos, uno cada "
               f"{str(cfg['grid_step']).replace('.', ',')}°, interpolada entre ellos.{missing} Pulsa en el mapa o "
               "arrastra el marcador para ver abajo la evolución de ese punto; las flechas ← → cambian de hora y la "
               "barra espaciadora reproduce. Las noches van sombreadas.")
