"""Descarga y preparación de datos: Meteociel (PE-AROME), Open-Meteo (ensembles y deterministas) e históricos."""

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

# Deterministas de Open-Meteo para el medio plazo -> nombre corto en los gráficos
MODELOS_DETERMINISTAS = {"icon_eu": "ICON-EU"}

# Ensembles de Open-Meteo: modelo -> (nombre corto, días que se piden, si el primer miembro es un control)
ENSEMBLES = {
    "icon_eu": ("ICON-EU", 6, False),  # 40 miembros, unas 120 h: medio plazo
    "ecmwf_ifs025": ("ECMWF", 15, True),  # control y 50 miembros: largo plazo (15 días)
    "gfs_seamless": ("GEFS", 16, True),  # control y 30 miembros: largo plazo (15 días)
}
VARIABLES_ENSEMBLE = {"temperatura": "temperature_2m", "precipitacion": "precipitation", "rachas": "wind_gusts_10m"}

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


def o_none(funcion, *args):
    """Resultado de una fuente secundaria, o None si falla (su sección simplemente no se muestra)."""

    try:
        return funcion(*args)
    except Exception:
        return None


def descargar(url, timeout=30, params=None):
    response = requests.get(url, params=params, timeout=timeout, headers=USER_AGENT)
    response.raise_for_status()
    return response


# ---------------------------------------------------------------- Meteociel

def leer_tabla_meteociel(url, tz="Europe/Madrid"):
    """Descarga una tabla de ensemble de Meteociel como DataFrame, sin caché.

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


def get_ensemble_arome(lat, lon, tz, variables):
    """Pase más reciente del ensemble PE-AROME y sus tablas para las variables pedidas."""

    run, _ = get_last_run(url_arome(lat, lon, MODOS_AROME["temperatura"]), RUNS_AROME, tz)
    tablas = {var: en_paralelo(get_meteociel_table, f"{url_arome(lat, lon, MODOS_AROME[var])}&run={run}", tz)
              for var in variables}
    return run, {var: tabla.result() for var, tabla in tablas.items()}


def hora_local_run(run_utc, tz):
    """Hora local a la que corresponde un pase dado en horas UTC (p. ej. 9 UTC -> 11 h en verano en Madrid)."""

    hoy_utc = pd.Timestamp.now(tz="UTC").normalize()
    return (hoy_utc + pd.Timedelta(hours=run_utc)).tz_convert(tz).hour


# ---------------------------------------------------------------- Open-Meteo

@st.cache_data(ttl="1h", show_spinner=False)
def get_deterministas(lat, lon, tz):
    """Previsión horaria de MODELOS_DETERMINISTAS: {variable: DataFrame}, una columna por modelo."""

    params = {"latitude": lat, "longitude": lon, "timeformat": "unixtime", "forecast_days": 6,
              "hourly": ",".join(VARIABLES_ENSEMBLE.values()), "models": ",".join(MODELOS_DETERMINISTAS)}
    horario = descargar("https://api.open-meteo.com/v1/forecast", params=params).json()["hourly"]
    indice = pd.to_datetime(horario["time"], unit="s", utc=True).tz_convert(tz)

    datos = {}
    for nombre, variable in VARIABLES_ENSEMBLE.items():
        columnas = {corto: horario.get(f"{variable}_{modelo}") for modelo, corto in MODELOS_DETERMINISTAS.items()}
        df = pd.DataFrame({c: v for c, v in columnas.items() if v is not None}, index=indice)
        datos[nombre] = df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
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
    diarias = {"nieve": "snowfall_sum", "uv_max": "uv_index_max", "nubes": "cloud_cover_mean",
               "tmax": "temperature_2m_max", "tmin": "temperature_2m_min", "lluvia": "precipitation_sum",
               "prob_lluvia": "precipitation_probability_max", "codigo": "weather_code"}
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


@st.cache_data(ttl="7d", show_spinner=False)
def buscar_lugares(texto):
    """Localidades que coinciden con `texto` según el geocodificador de Open-Meteo (nombre, región, lat, lon, tz)."""

    params = {"name": texto, "count": 10, "language": "es", "format": "json"}
    resultados = descargar("https://geocoding-api.open-meteo.com/v1/search", params=params).json().get("results", [])
    return [{"nombre": r["name"], "region": ", ".join(x for x in (r.get("admin1"), r.get("country")) if x),
             "lat": r["latitude"], "lon": r["longitude"], "tz": r.get("timezone")} for r in resultados]


@st.cache_data(ttl="7d", show_spinner=False)
def get_zona_horaria(lat, lon):
    """Zona horaria del punto según Open-Meteo (p. ej. "Europe/Paris")."""

    params = {"latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 1}
    return descargar("https://api.open-meteo.com/v1/forecast", params=params).json()["timezone"]


@st.cache_data(ttl="7d", show_spinner=False)
def get_nombre_lugar(lat, lon):
    """Localidad más cercana al punto según OpenStreetMap (Nominatim), o None si no la hay."""

    params = {"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 10, "accept-language": "es"}
    datos = descargar("https://nominatim.openstreetmap.org/reverse", params=params, timeout=10).json()
    direccion = datos.get("address", {})
    for clave in ("city", "town", "village", "municipality", "county", "state"):
        if clave in direccion:
            return direccion[clave]
    return None


@st.cache_data(ttl="1h", show_spinner=False)
def get_mar(lat, lon, tz):
    """Oleaje (MFWAM de Météo-France) y temperatura del agua (SMOC de Météo-France) en el punto de la rejilla de mar más
    cercano, según la API marina de Open-Meteo, 7 días: {"horario", "lat", "lon"} con la posición de ese punto.

    Columnas: olas y mar de fondo (altura significativa, m), periodo (s), direccion (de donde vienen, grados) y agua (ºC).
    """

    variables = {"olas": "wave_height", "mar_fondo": "swell_wave_height", "periodo": "wave_period",
                 "direccion": "wave_direction", "agua": "sea_surface_temperature"}
    params = {"latitude": lat, "longitude": lon, "timezone": tz, "forecast_days": 7,
              "hourly": ",".join(variables.values())}
    datos = descargar("https://marine-api.open-meteo.com/v1/marine", params=params).json()
    horario = datos["hourly"]
    df = pd.DataFrame({nombre: horario.get(v) for nombre, v in variables.items()}, index=pd.to_datetime(horario["time"]))
    return {"horario": df.apply(pd.to_numeric, errors="coerce"), "lat": datos["latitude"], "lon": datos["longitude"]}


@st.cache_data(ttl="1h", show_spinner=False)
def get_calidad_aire(lat, lon, tz):
    """Índice europeo de calidad del aire, contaminantes y polen (CAMS vía Open-Meteo), 4 días."""

    variables = ["european_aqi", "pm2_5", "pm10", "nitrogen_dioxide", "ozone"] + [f"{p}_pollen" for p in POLENES]
    params = {"latitude": lat, "longitude": lon, "timezone": tz, "forecast_days": 4, "hourly": ",".join(variables)}
    horario = descargar("https://air-quality-api.open-meteo.com/v1/air-quality", params=params).json()["hourly"]
    df = pd.DataFrame({v: horario.get(v) for v in variables}, index=pd.to_datetime(horario["time"]))
    return df.apply(pd.to_numeric, errors="coerce")


# Ensembles de Open-Meteo que sustituyen al PE-AROME fuera de su dominio (Ciudad.ensemble). Cada modelo: prefijo de
# sus columnas y si su primer miembro es el control que se destaca. El pase sale de los metadatos de Open-Meteo
# (`meta`) o, si no se actualizan, del final de la previsión menos su duración (`horizonte`, en horas)
ENSEMBLES_48H = {
    # Escocia: MOGREPS-UK, 2 km y 3 miembros, más MOGREPS-G, 20 km y 18 miembros, para tener dispersión
    "ukmo": {"nombre": "Met Office", "modelos": {"ukmo_uk_ensemble_2km": ("UK", True),
                                                 "ukmo_global_ensemble_20km": ("G", False)},
             "meta": "ukmo_uk_ensemble_2km"},
    # Finlandia, el Báltico y Eslovenia: ICON-EU EPS, 40 miembros (sus metadatos en Open-Meteo están parados)
    "icon_eu": {"nombre": "ICON-EU", "modelos": {"icon_eu": ("", False)}, "horizonte": 120},
}
VARIABLES_48H = {"temperatura": "temperature_2m", "precipitacion": "precipitation", "rachas": "wind_gusts_10m",
                 "presion": "pressure_msl", "mucape": "cape"}


@st.cache_data(ttl="30m", show_spinner=False)
def get_ensemble_48h(lat, lon, tz, variables, origen):
    """Ensemble de Open-Meteo a 48 h (ENSEMBLES_48H[origen]) con el formato de las tablas de Meteociel:
    (inicio del pase UTC o None, {variable: DataFrame}).

    Empieza a las 00 h locales de hoy, así que los extremos de hoy salen del día completo. El control que se destaca
    es la columna "Ctrl"; el resto de miembros, prefijo y número: "UK1", "UK2", "G0"... "G17" o, sin prefijo, "0", "1"...
    """

    config = ENSEMBLES_48H[origen]
    modelos = config["modelos"]
    params = {"latitude": lat, "longitude": lon, "timezone": tz, "timeformat": "unixtime",
              "forecast_days": 6 if "horizonte" in config else 3,  # con horizonte hace falta el final de la previsión
              "hourly": ",".join(VARIABLES_48H[v] for v in variables), "models": ",".join(modelos)}
    horario = descargar("https://ensemble-api.open-meteo.com/v1/ensemble", params=params, timeout=60).json()["hourly"]
    indice = pd.to_datetime(horario["time"], unit="s", utc=True).tz_convert(tz)
    fin = pd.Timestamp.now(tz=tz).floor("h") + pd.Timedelta(hours=48)

    completos = {}
    for nombre in variables:
        variable, columnas = VARIABLES_48H[nombre], {}
        for modelo, (prefijo, con_control) in modelos.items():
            sufijo = f"_{modelo}" if len(modelos) > 1 else ""  # con un solo modelo, Open-Meteo no lo añade
            for clave, valores in horario.items():
                if clave == f"{variable}{sufijo}":
                    columnas["Ctrl" if con_control else f"{prefijo}0"] = valores
                elif clave.startswith(f"{variable}_member") and clave.endswith(sufijo):
                    miembro = clave.removeprefix(f"{variable}_member").removesuffix(sufijo)
                    columnas[f"{prefijo}{int(miembro)}"] = valores
        completos[nombre] = pd.DataFrame(columnas, index=indice).apply(pd.to_numeric, errors="coerce").dropna(how="all")
    datos = {nombre: df[df.index <= fin] for nombre, df in completos.items()}

    run = None
    if "meta" in config:
        try:
            run = pd.Timestamp(descargar(f"https://ensemble-api.open-meteo.com/data/{config['meta']}/static/meta.json")
                               .json()["last_run_initialisation_time"], unit="s", tz="UTC")
        except Exception:
            pass
    elif not completos["temperatura"].empty:
        run = completos["temperatura"].index[-1].tz_convert("UTC") - pd.Timedelta(hours=config["horizonte"])
    return run, datos


@st.cache_data(ttl="1h", show_spinner=False)
def get_ensemble(lat, lon, tz, modelo):
    """Ensemble de Open-Meteo (ver ENSEMBLES): {"temperatura", "precipitacion", "rachas"}, un miembro por columna.

    El índice es la hora local con zona. El control, si el modelo lo tiene, es la columna "Ctrl"; el resto, "1", "2"...
    """

    _, dias, con_control = ENSEMBLES[modelo]
    params = {"latitude": lat, "longitude": lon, "timeformat": "unixtime", "forecast_days": dias,
              "hourly": ",".join(VARIABLES_ENSEMBLE.values()), "models": modelo}
    horario = descargar("https://ensemble-api.open-meteo.com/v1/ensemble", params=params, timeout=60).json()["hourly"]
    indice = pd.to_datetime(horario["time"], unit="s", utc=True).tz_convert(tz)

    datos = {}
    for nombre, variable in VARIABLES_ENSEMBLE.items():
        columnas = {}
        for clave, valores in horario.items():
            if clave == variable:
                columnas["Ctrl" if con_control else "0"] = valores
            elif clave.startswith(f"{variable}_member"):
                columnas[str(int(clave.removeprefix(f"{variable}_member")))] = valores
        datos[nombre] = pd.DataFrame(columnas, index=indice).apply(pd.to_numeric, errors="coerce").dropna(how="all")
    return datos


def extremos_diarios(temperatura, fechas, minimo_horas=23):
    """Máximas y mínimas diarias de cada miembro en `fechas` con al menos `minimo_horas` horas: (DataFrame, DataFrame).

    Por defecto, solo días completos (23-25 h con el cambio de hora).
    """

    por_dia = temperatura.groupby(temperatura.index.date)
    completos = [f for f, horas in por_dia.size().items() if horas >= minimo_horas and f in set(fechas)]
    return por_dia.max().loc[completos], por_dia.min().loc[completos]


# ---------------------------------------------------------------- Probabilidad de lluvia

UMBRAL_LLUVIA = 1  # L/m² acumulados en un día o tramo: la misma referencia que el histórico ("día de lluvia")
UMBRAL_LLUVIA_HORA = 0.2  # L/m² en una hora: por debajo son trazas que apenas mojan


def prob_miembros(precipitacion, umbral=UMBRAL_LLUVIA):
    """% de miembros del ensemble con al menos `umbral` L/m² acumulados en las filas de `precipitacion` (o None).

    Es la probabilidad de que llueva en algún momento de la ventana. El máximo de las probabilidades horarias la
    subestima: si cada miembro moja a una hora distinta, ninguna hora suma muchos miembros.
    """

    total = precipitacion.drop(columns="Observado", errors="ignore").sum(min_count=1).dropna()
    return None if total.empty else 100 * (total >= umbral).mean()


def prob_por_hora(precipitacion):
    """% de miembros con al menos UMBRAL_LLUVIA_HORA en cada hora."""

    ens = precipitacion.drop(columns="Observado", errors="ignore")
    return 100 * (ens >= UMBRAL_LLUVIA_HORA).sum(axis=1) / ens.notna().sum(axis=1).clip(lower=1)


def prob_diaria(precipitacion, desde=None):
    """prob_miembros de cada día ({fecha: %}); con `desde`, las horas anteriores no cuentan (lo que queda de hoy)."""

    if desde is not None:
        precipitacion = precipitacion[precipitacion.index >= desde]
    return {fecha: prob_miembros(dia) for fecha, dia in precipitacion.groupby(precipitacion.index.date)}


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


@st.cache_data(show_spinner=False)
def get_lluvia_diaria(ruta_csv):
    """Lluvia diaria (L/m²) del histórico, con los 29 de febrero (get_historico los quita): Series por fecha."""

    return pd.read_csv(ruta_csv, usecols=["fecha", "prec"], index_col="fecha", parse_dates=True)["prec"]


@st.cache_data(show_spinner=False)
def get_bandas(ruta_csv):
    """Rangos habituales precalculados por generar_bandas.py, con el formato de las bandas de get_historico, y su
    origen (estación, periodo y fuente), que va en la primera línea del CSV."""

    with open(ruta_csv, encoding="utf-8") as f:
        origen = f.readline().removeprefix("#").strip()
    bandas = pd.read_csv(ruta_csv, comment="#", index_col="día_del_año")
    bandas.columns = pd.MultiIndex.from_tuples([(c.split("_p")[0], int(c.split("_p")[1]) / 100) for c in bandas.columns])
    return bandas, origen


def probabilidad_lluvia(datos, fecha, margen=7, umbral=UMBRAL_LLUVIA):
    """Porcentaje de días con al menos `umbral` L/m² en el histórico, a ±`margen` días de la fecha."""

    distancia = (datos["día_del_año"] - dia_historico(fecha)).abs()
    cerca = datos.loc[(distancia <= margen) | (distancia >= 365 - margen), "prec"].dropna()
    return None if cerca.empty else 100 * (cerca >= umbral).mean()
