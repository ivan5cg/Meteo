"""Descarga y preparación de datos: Meteociel (AROME y GEFS), Open-Meteo e históricos locales."""

from concurrent.futures import ThreadPoolExecutor
import threading

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

USER_AGENT = {"User-Agent": "Mozilla/5.0 (Meteo Dash; Streamlit)"}

# Modos de las tablas de ensemble AROME de Meteociel
MODOS_AROME = {"temperatura": 8, "rachas": 13, "presion": 1, "mucape": 0, "precipitacion": 10}
RUNS_AROME = [3, 9, 15, 21]  # UTC
RUNS_GEFS = [0, 6, 12, 18]  # UTC

# Columnas de Open-Meteo -> nombre corto en los gráficos
MODELOS_OPEN_METEO = {
    "ecmwf_ifs025": "ECMWF",
    "gfs_global": "GFS",
    "meteofrance_arome_france_hd": "AROME",
    "meteofrance_arpege_europe": "ARPEGE",
    "icon_eu": "ICON",
}

# Polen de CAMS (Open-Meteo) -> nombre en español
POLENES = {"alder": "Aliso", "birch": "Abedul", "grass": "Gramíneas", "mugwort": "Artemisa", "olive": "Olivo",
           "ragweed": "Ambrosía"}


# Descargas en paralelo. La caché de Streamlit tiene un cerrojo por clave: si el hilo principal pide un valor
# que un hilo del pool ya está descargando, espera a que termine en lugar de repetir la petición.
_POOL = ThreadPoolExecutor(max_workers=16, thread_name_prefix="meteodash")  # una página pide hasta ~20 recursos


def en_paralelo(funcion, *args):
    """Lanza `funcion(*args)` en el pool con el contexto de la sesión actual; devuelve el Future."""

    ctx = get_script_run_ctx()

    def tarea():
        add_script_run_ctx(threading.current_thread(), ctx)
        return funcion(*args)

    return _POOL.submit(tarea)


def descargar(url, timeout=30, params=None):
    response = requests.get(url, params=params, timeout=timeout, headers=USER_AGENT)
    response.raise_for_status()
    return response


# ---------------------------------------------------------------- Meteociel

def leer_tabla_meteociel(url, tz="Europe/Madrid"):
    """Descarga una tabla de ensemble de Meteociel (AROME o GEFS) como DataFrame, sin caché.

    Las celdas no numéricas (vacías, "-") quedan como NaN en lugar de invalidar toda la tabla.
    """

    soup = BeautifulSoup(descargar(url).text, "html.parser")

    table = soup.find("table", {"class": "gefs"})
    if table is None:
        raise ValueError(f"Meteociel no ha devuelto la tabla esperada: {url}")

    rows = table.find_all("tr")
    headers = [header.get_text(strip=True) for header in rows[0].find_all("td")]
    data = [[column.get_text(strip=True) for column in row.find_all("td")] for row in rows[1:]]

    df = pd.DataFrame(data, columns=headers)
    df.index = pd.DatetimeIndex(pd.to_datetime(df["Date"], utc=True)).tz_convert(tz)
    df = df.drop(["Date", "Ech."], axis=1)
    return df.apply(pd.to_numeric, errors="coerce")


@st.cache_data(ttl="30m", show_spinner=False)
def get_meteociel_table(url, tz="Europe/Madrid"):
    return leer_tabla_meteociel(url, tz)


def get_last_run(url, runs, tz="Europe/Madrid"):
    """Pase más reciente (el que empieza más tarde) de los disponibles en Meteociel: (hora UTC, instante inicial)."""

    first_index = pd.Timestamp(year=2017, month=1, day=1, tz="UTC")
    valid_run = None

    tablas = {run: en_paralelo(get_meteociel_table, f"{url}&run={run}", tz) for run in runs}
    for run, tabla in tablas.items():
        try:
            first_index_run = tabla.result().index[0]
        except Exception:
            continue

        if first_index_run > first_index:
            first_index = first_index_run
            valid_run = run

    if valid_run is None:
        raise ConnectionError(f"Ningún pase disponible en Meteociel: {url}")

    return valid_run, first_index


def url_arome(lat, lon, modo):
    return f"https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat={lat}&lon={lon}&mode={modo}&sort=0"


def url_gefs(lat, lon):
    return f"https://www.meteociel.fr/modeles/gefs_table.php?x=0&y=0&lat={lat}&lon={lon}&ext=1&mode=7&sort=0"


def get_ensemble_arome(lat, lon, tz, variables):
    """Pase más reciente del ensemble PE-AROME y sus tablas para las variables pedidas."""

    run, _ = get_last_run(url_arome(lat, lon, MODOS_AROME["temperatura"]), RUNS_AROME, tz)
    tablas = {var: en_paralelo(get_meteociel_table, f"{url_arome(lat, lon, MODOS_AROME[var])}&run={run}", tz)
              for var in variables}
    return run, {var: tabla.result() for var, tabla in tablas.items()}


def get_ensemble_gefs(lat, lon, tz):
    run, _ = get_last_run(url_gefs(lat, lon), RUNS_GEFS, tz)
    return get_meteociel_table(f"{url_gefs(lat, lon)}&run={run}", tz)


def hora_local_run(run_utc, tz):
    """Hora local a la que corresponde un pase dado en horas UTC (p. ej. 9 UTC -> 11 h en verano en Madrid)."""

    hoy_utc = pd.Timestamp.now(tz="UTC").normalize()
    return (hoy_utc + pd.Timedelta(hours=run_utc)).tz_convert(tz).hour


# ---------------------------------------------------------------- Open-Meteo

@st.cache_data(ttl="1h", show_spinner=False)
def get_open_meteo(lat, lon, tz):
    """Previsión horaria multimodelo de Open-Meteo: un DataFrame por variable, una columna por modelo."""

    variables = {"temperatura": "temperature_2m", "precipitacion": "precipitation", "rachas": "windgusts_10m"}
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(variables.values()),
        "timezone": tz,
        "models": ",".join(MODELOS_OPEN_METEO),
    }
    horario = descargar("https://api.open-meteo.com/v1/forecast", params=params).json()["hourly"]
    indice = pd.to_datetime(horario["time"])

    datos = {}
    for nombre, variable in variables.items():
        df = pd.DataFrame(index=indice)
        for modelo, corto in MODELOS_OPEN_METEO.items():
            valores = horario.get(f"{variable}_{modelo}")
            if valores is not None:
                df[corto] = pd.to_numeric(pd.Series(valores, index=indice), errors="coerce")
        datos[nombre] = df.dropna(axis=1, how="all")

    return datos


@st.cache_data(ttl="1h", show_spinner=False)
def get_open_meteo_detalle(lat, lon, tz):
    """Variables complementarias del mejor modelo de Open-Meteo para el punto.

    Devuelve {"horario", "diario", "elevacion"}.
    """

    horarias = {
        "sensacion": "apparent_temperature", "humedad": "relative_humidity_2m", "nubes": "cloud_cover",
        "nieve": "snowfall", "espesor_nieve": "snow_depth", "isocero": "freezing_level_height",
    }
    diarias = {"nieve": "snowfall_sum", "uv_max": "uv_index_max", "nubes": "cloud_cover_mean"}
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "hourly": ",".join(horarias.values()),
        "daily": ",".join(diarias.values()),
        "forecast_days": 8,
    }
    datos = descargar("https://api.open-meteo.com/v1/forecast", params=params).json()

    def tabla(bloque, variables):
        df = pd.DataFrame({nombre: datos[bloque].get(variable) for nombre, variable in variables.items()},
                          index=pd.to_datetime(datos[bloque]["time"]))
        return df.apply(pd.to_numeric, errors="coerce")

    return {"horario": tabla("hourly", horarias), "diario": tabla("daily", diarias), "elevacion": datos.get("elevation")}


@st.cache_data(ttl="1h", show_spinner=False)
def get_calidad_aire(lat, lon, tz):
    """Índice europeo de calidad del aire, contaminantes y polen (CAMS vía Open-Meteo), 4 días."""

    variables = ["european_aqi", "pm2_5", "pm10", "nitrogen_dioxide", "ozone"] + [f"{p}_pollen" for p in POLENES]
    params = {"latitude": lat, "longitude": lon, "timezone": tz, "forecast_days": 4, "hourly": ",".join(variables)}
    horario = descargar("https://air-quality-api.open-meteo.com/v1/air-quality", params=params).json()["hourly"]
    df = pd.DataFrame({v: horario.get(v) for v in variables}, index=pd.to_datetime(horario["time"]))
    return df.apply(pd.to_numeric, errors="coerce")


@st.cache_data(ttl="1h", show_spinner=False)
def get_ensemble_ecmwf(lat, lon, tz):
    """Ensemble ECMWF IFS (control y 50 miembros) a 15 días: {"temperatura", "precipitacion"}, un miembro por columna."""

    variables = {"temperatura": "temperature_2m", "precipitacion": "precipitation"}
    params = {"latitude": lat, "longitude": lon, "timezone": tz, "forecast_days": 15,
              "hourly": ",".join(variables.values()), "models": "ecmwf_ifs025"}
    horario = descargar("https://ensemble-api.open-meteo.com/v1/ensemble", params=params, timeout=60).json()["hourly"]
    indice = pd.to_datetime(horario["time"])

    datos = {}
    for nombre, variable in variables.items():
        columnas = {("Ctrl" if clave == variable else clave.removeprefix(f"{variable}_member")): valores
                    for clave, valores in horario.items() if clave == variable or clave.startswith(f"{variable}_member")}
        datos[nombre] = pd.DataFrame(columnas, index=indice).apply(pd.to_numeric, errors="coerce").dropna(how="all")
    return datos


# ---------------------------------------------------------------- Históricos locales

def dia_historico(fecha):
    """Día del año sin 29 de febrero (1-365), el mismo índice que usan los históricos."""

    fecha = pd.Timestamp(fecha)
    return fecha.dayofyear - (1 if fecha.is_leap_year and fecha.month >= 3 else 0)


def _dias_historicos(indice):
    dias = pd.Series(indice.day_of_year, index=indice)
    return dias - (indice.is_leap_year & (indice.month >= 3)).astype(int)


@st.cache_data(show_spinner=False)
def get_historico(ruta_csv):
    """Serie diaria (tmax, tmin, tmed, prec) y bandas habituales (percentiles 15-85 de la media móvil de 15 días)."""

    datos = pd.read_csv(ruta_csv, usecols=["fecha", "tmed", "tmax", "tmin", "prec"], index_col="fecha", parse_dates=True)
    datos = datos[~((datos.index.month == 2) & (datos.index.day == 29))]
    datos["día_del_año"] = _dias_historicos(datos.index)

    medias = datos[["tmed", "tmax", "tmin"]].dropna(how="any")
    rolling = medias.rolling(15, center=True).mean().dropna()
    rolling["día_del_año"] = _dias_historicos(rolling.index)
    bandas = rolling.groupby("día_del_año").quantile([0.15, 0.85]).unstack()

    return datos, bandas


def probabilidad_lluvia(datos, fecha, margen=7, umbral=1):
    """Porcentaje de días con al menos `umbral` L/m² en el histórico, a ±`margen` días de la fecha."""

    distancia = (datos["día_del_año"] - dia_historico(fecha)).abs()
    cerca = datos.loc[(distancia <= margen) | (distancia >= 365 - margen), "prec"].dropna()
    return None if cerca.empty else 100 * (cerca >= umbral).mean()
