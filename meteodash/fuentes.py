"""Descarga y preparación de datos: Meteociel (AROME y GEFS), Open-Meteo e históricos locales."""

import logging
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

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


def descargar(url, timeout=30):
    response = requests.get(url, timeout=timeout, headers=USER_AGENT)
    response.raise_for_status()
    return response


def en_paralelo(funcion, argumentos, hilos=4):
    """Aplica `funcion` a cada tupla de `argumentos` en varios hilos.

    Devuelve los resultados en el mismo orden; si una llamada falla, en su lugar va la excepción.
    """

    def protegida(args):
        try:
            return funcion(*args)
        except Exception as error:
            logger.debug("Fallo en %s%s: %s", funcion.__name__, args, error)
            return error

    with ThreadPoolExecutor(max_workers=hilos) as executor:
        return list(executor.map(protegida, argumentos))


# ---------------------------------------------------------------- Meteociel

def leer_tabla_meteociel(url, tz="Europe/Madrid", timeout=30):
    """Descarga una tabla de ensemble de Meteociel (AROME o GEFS) como DataFrame, una columna por miembro.

    Sin caché: se llama desde hilos, donde st.cache_data no está disponible.
    Las celdas que no son números (vacías, "-") quedan como NaN en lugar de romper la tabla entera.
    """

    soup = BeautifulSoup(descargar(url, timeout).text, "html.parser")

    table = soup.find("table", {"class": "gefs"})
    if table is None:
        raise ValueError(f"Meteociel no ha devuelto la tabla esperada: {url}")

    rows = table.find_all("tr")
    headers = [header.get_text(strip=True) for header in rows[0].find_all("td")]
    data = [[column.get_text(strip=True) for column in row.find_all("td")] for row in rows[1:]]

    df = pd.DataFrame(data, columns=headers)
    df.index = pd.DatetimeIndex(pd.to_datetime(df["Date"], utc=True)).tz_convert(tz)
    df.index.name = None
    return df.drop(columns=["Date", "Ech."]).apply(pd.to_numeric, errors="coerce")


def ultimo_pase(url, runs, tz="Europe/Madrid"):
    """Descarga en paralelo todos los pases de una tabla y devuelve (pase, tabla) del más reciente.

    El más reciente es el que empieza más tarde: a primera hora el pase de las 21 UTC es el de ayer.
    """

    tablas = en_paralelo(leer_tabla_meteociel, [(f"{url}&run={run}", tz) for run in runs])
    disponibles = {
        run: tabla for run, tabla in zip(runs, tablas)
        if isinstance(tabla, pd.DataFrame) and not tabla.empty
    }
    if not disponibles:
        raise ConnectionError(f"Ningún pase disponible en Meteociel: {url}")

    run = max(disponibles, key=lambda r: disponibles[r].index[0])
    return run, disponibles[run]


def url_arome(lat, lon, modo, run=None):
    url = f"https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat={lat}&lon={lon}&mode={modo}&sort=0"
    return f"{url}&run={run}" if run is not None else url


def url_gefs(lat, lon):
    return f"https://www.meteociel.fr/modeles/gefs_table.php?x=0&y=0&lat={lat}&lon={lon}&ext=1&mode=7&sort=0"


@st.cache_data(ttl="30m", show_spinner=False)
def get_ensemble_arome(lat, lon, tz, variables):
    """Pase más reciente del ensemble PE-AROME y sus tablas para las variables pedidas.

    El pase se elige con la temperatura; el resto de variables se descargan a la vez.
    """

    run, temperatura = ultimo_pase(url_arome(lat, lon, MODOS_AROME["temperatura"]), RUNS_AROME, tz)
    resto = [var for var in variables if var != "temperatura"]
    tablas = en_paralelo(leer_tabla_meteociel, [(url_arome(lat, lon, MODOS_AROME[var], run), tz) for var in resto])

    datos = {"temperatura": temperatura}
    for var, tabla in zip(resto, tablas):
        if isinstance(tabla, Exception):
            raise tabla
        datos[var] = tabla
    return run, datos


@st.cache_data(ttl="30m", show_spinner=False)
def get_ensemble_gefs(lat, lon, tz):
    return ultimo_pase(url_gefs(lat, lon), RUNS_GEFS, tz)[1]


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
    response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=30, headers=USER_AGENT)
    response.raise_for_status()
    horario = response.json()["hourly"]
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
    """Serie diaria (tmax, tmin, tmed) y bandas habituales (percentiles 15-85 de la media móvil de 15 días)."""

    datos = pd.read_csv(ruta_csv, usecols=["fecha", "tmed", "tmax", "tmin"], index_col="fecha", parse_dates=True)
    datos = datos[~((datos.index.month == 2) & (datos.index.day == 29))]
    datos["día_del_año"] = _dias_historicos(datos.index)

    medias = datos[["tmed", "tmax", "tmin"]].dropna(how="any")
    rolling = medias.rolling(15, center=True).mean().dropna()
    rolling["día_del_año"] = _dias_historicos(rolling.index)
    bandas = rolling.groupby("día_del_año").quantile([0.15, 0.85]).unstack()

    return datos, bandas
