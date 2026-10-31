"""Observaciones horarias de las últimas 24 h: AEMET, otros servicios meteorológicos nacionales y METAR.

Cada red devuelve, como aemet.get_aemet_horario, una fila por hora (la hora en que acaba el intervalo) con temperatura
(ºC), racha (máxima de la hora, km/h), dir_racha (punto cardinal), precipitacion (de la hora, L/m²) y humedad (%). Lo
que la estación no mide queda en NaN.
"""

import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from .aemet import get_aemet_horario
from .fuentes import descargar

HORAS = 30  # algo más de 24 h, para tener la temperatura de ayer a esta hora
ANTIGUEDAD_MAXIMA = pd.Timedelta(hours=3)  # una observación más antigua ya no es la actual
COLUMNAS = ["temperatura", "racha", "dir_racha", "precipitacion", "humedad"]
RUMBOS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]  # los mismos que usa AEMET


@dataclass(frozen=True)
class Estacion:
    red: str  # clave de REDES
    codigo: str
    nombre: str | None = None  # cómo se cita en la página ("Uccle", "aeropuerto de Linate")


def cardinal(grados):
    return None if pd.isna(grados) else RUMBOS[int((grados % 360 + 22.5) // 45) % 8]


def _desde():
    return pd.Timestamp.now(tz="UTC").floor("h") - pd.Timedelta(hours=HORAS)


def _tabla(temperatura=None, racha=None, dir_racha=None, precipitacion=None, humedad=None):
    """Series horarias (índice UTC) -> DataFrame con todas las COLUMNAS, ordenado de la hora más antigua a la última."""

    series = {"temperatura": temperatura, "racha": racha, "dir_racha": dir_racha, "precipitacion": precipitacion,
              "humedad": humedad}
    tabla = pd.DataFrame({c: s for c, s in series.items() if s is not None}).reindex(columns=COLUMNAS).sort_index()
    return tabla.round({"temperatura": 1, "racha": 1, "precipitacion": 1, "humedad": 0})


def _en_punto(serie):
    """Valores de las horas en punto de una serie cada pocos minutos."""

    return serie[serie.index.minute == 0]


def _por_horas(serie, funcion):
    """Agrega una serie cada pocos minutos (índice al final de cada intervalo) por horas: de h-1 (excluida) a h.

    La última hora solo cuenta si está completa.
    """

    serie = serie.dropna()
    horas = serie.groupby(serie.index.ceil("h")).agg(funcion)
    return horas[horas.index <= serie.index.max()] if not serie.empty else horas


def _racha_horaria(racha, direccion):
    """Racha máxima de cada hora y la dirección del intervalo en que se dio."""

    racha = racha.dropna()
    maxima = _por_horas(racha, "max")
    momento = pd.DatetimeIndex(_por_horas(racha, "idxmax"))
    rumbo = pd.Series(direccion.reindex(momento).map(cardinal).to_numpy(), index=maxima.index)
    return maxima, rumbo


# ---------------------------------------------------------------- Finlandia: FMI

BSWFS = "{http://xml.fmi.fi/schema/wfs/2.0}"


@st.cache_data(ttl="10m", show_spinner=False)
def get_fmi(fmisid):
    """Instituto Meteorológico de Finlandia (WFS de datos abiertos), cada 10 min."""

    params = {"service": "WFS", "version": "2.0.0", "request": "getFeature", "fmisid": fmisid,
              "storedquery_id": "fmi::observations::weather::simple", "parameters": "t2m,rh,wg_10min,wd_10min,r_1h",
              "starttime": f"{_desde():%Y-%m-%dT%H:%M:%SZ}"}
    raiz = ET.fromstring(descargar("https://opendata.fmi.fi/wfs", params=params).content)
    filas = [(e.findtext(f"{BSWFS}Time"), e.findtext(f"{BSWFS}ParameterName"), e.findtext(f"{BSWFS}ParameterValue"))
             for e in raiz.iter(f"{BSWFS}BsWfsElement")]
    if not filas:
        raise ValueError(f"FMI no ha devuelto observaciones de la estación {fmisid}")

    datos = pd.DataFrame(filas, columns=["hora", "variable", "valor"]).pivot(index="hora", columns="variable",
                                                                          values="valor")
    datos.index = pd.to_datetime(datos.index, utc=True)
    datos = datos.apply(pd.to_numeric, errors="coerce")
    racha, rumbo = _racha_horaria(3.6 * datos["wg_10min"], datos["wd_10min"])
    # r_1h, en las horas en punto, es lo acumulado en la hora
    return _tabla(_en_punto(datos["t2m"]), racha, rumbo, _en_punto(datos["r_1h"]), _en_punto(datos["rh"]))


# ---------------------------------------------------------------- Eslovenia: ARSO

VARIABLES_ARSO = ["t", "rh", "ffmax_val_kmh", "ddmax_val", "rr_val"]


@st.cache_data(ttl="10m", show_spinner=False)
def get_arso(estacion):
    """Agencia de Medio Ambiente de Eslovenia: archivo de 48 h de una estación automática (cada 10 o 30 min).

    `estacion` es su identificador sin el guion bajo final ("LJUBL-ANA_BEZIGRAD"); ver observationAms_si_latest.xml.
    """

    url = ("https://meteo.arso.gov.si/uploads/probase/www/observ/surface/text/sl/recent/"
           f"observationAms_{estacion}_history.xml")
    filas = [{"hora": m.findtext("valid_UTC"), **{v: m.findtext(v) for v in VARIABLES_ARSO}}
             for m in ET.fromstring(descargar(url).content).iter("metData")]
    if not filas:
        raise ValueError(f"ARSO no ha devuelto observaciones de la estación {estacion}")

    datos = pd.DataFrame(filas)
    datos.index = pd.to_datetime(datos.pop("hora"), format="%d.%m.%Y %H:%M UTC", utc=True)
    datos = datos.apply(pd.to_numeric, errors="coerce").sort_index()
    racha, rumbo = _racha_horaria(datos["ffmax_val_kmh"], datos["ddmax_val"])
    return _tabla(_en_punto(datos["t"]), racha, rumbo, _por_horas(datos["rr_val"], "sum"), _en_punto(datos["rh"]))


# ---------------------------------------------------------------- Bélgica: KMI/IRM

@st.cache_data(ttl="10m", show_spinner=False)
def get_kmi(codigo):
    """Real Instituto Meteorológico de Bélgica: estación automática, cada 10 min (WFS de datos abiertos).

    Las rachas solo cuentan si el anemómetro está a 10 m: en Uccle está a 30 m y no son comparables con las de los
    modelos.
    """

    filtro = f"code={codigo} AND timestamp >= '{_desde():%Y-%m-%dT%H:%M:%SZ}'"
    params = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typenames": "aws:aws_10min",
              "outputFormat": "application/json", "CQL_FILTER": filtro}
    filas = [f["properties"] for f in descargar("https://opendata.meteo.be/service/ows", params=params).json()["features"]]
    if not filas:
        raise ValueError(f"El KMI no ha devuelto observaciones de la estación {codigo}")

    datos = pd.DataFrame(filas)
    datos.index = pd.to_datetime(datos.pop("timestamp"), utc=True)  # final de cada intervalo de 10 min
    datos = datos.apply(pd.to_numeric, errors="coerce").sort_index()
    racha = rumbo = None
    if datos["wind_speed_10m"].notna().any():
        racha, rumbo = _racha_horaria(3.6 * datos["wind_gusts_speed"], datos["wind_direction"])
    return _tabla(_en_punto(datos["temp_dry_shelter_avg"]), racha, rumbo, _por_horas(datos["precip_quantity"], "sum"),
                  _en_punto(datos["humidity_rel_shelter_avg"]))


# ---------------------------------------------------------------- Letonia: LVĢMC

URL_LVGMC = ("https://data.gov.lv/dati/dataset/40d80be5-0c09-47c4-80f3-fad4bec19f33/resource/"
             "17460efb-ae99-4d1d-8144-1068f184b05f/download/meteo_operativie_dati.csv")
VARIABLES_LVGMC = {"TDRY": "temperatura", "HWSMX": "racha", "HWDMX": "dir_racha", "HPRAB": "precipitacion",
                   "RLH": "humedad"}


@st.cache_data(ttl="20m", show_spinner=False)
def get_lvgmc(estacion):
    """Centro de Medio Ambiente, Geología y Meteorología de Letonia: datos horarios operativos de las últimas 48 h
    (un CSV con todas las estaciones en data.gov.lv, que se renueva a los ~20 min de cada hora; horas en UTC)."""

    datos = pd.read_csv(io.BytesIO(descargar(URL_LVGMC, timeout=60).content), encoding="utf-8-sig")
    datos = datos[(datos["STATION_ID"] == estacion) & datos["ABBREVIATION"].isin(VARIABLES_LVGMC)]
    if datos.empty:
        raise ValueError(f"LVĢMC no tiene observaciones de la estación {estacion}")

    tabla = datos.pivot_table(index="DATETIME", columns="ABBREVIATION", values="VALUE", aggfunc="last")
    tabla.index = pd.to_datetime(tabla.index, format="%Y.%m.%d %H:%M:%S").tz_localize("UTC")
    tabla = tabla.rename(columns=VARIABLES_LVGMC)
    return _tabla(tabla.get("temperatura"), 3.6 * tabla["racha"] if "racha" in tabla else None,
                  tabla["dir_racha"].map(cardinal) if "dir_racha" in tabla else None, tabla.get("precipitacion"),
                  tabla.get("humedad"))


# ---------------------------------------------------------------- Irlanda: Met Éireann

@st.cache_data(ttl="10m", show_spinner=False)
def get_met_eireann(estacion):
    """Met Éireann: observaciones horarias de ayer y de hoy (API de datos abiertos, hora local de Irlanda).

    La temperatura viene en grados enteros y la racha solo cuando es destacable.
    """

    filas = []
    for dia in ("yesterday", "today"):
        filas += descargar(f"https://prodapi.met.ie/observations/{estacion}/{dia}").json()
    if not filas:
        raise ValueError(f"Met Éireann no ha devuelto observaciones de la estación {estacion}")

    datos = pd.DataFrame(filas)
    hora = pd.to_datetime(datos["date"] + " " + datos["reportTime"], format="%d-%m-%Y %H:%M")
    datos.index = pd.DatetimeIndex(hora).tz_localize("Europe/Dublin", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    datos = datos[datos.index.notna()]

    def numero(columna):  # "NA", "-" o "-99" cuando no hay dato
        return pd.to_numeric(datos[columna].astype(str).str.strip(), errors="coerce")

    racha = numero("windGust")
    rumbo = numero("windDirection").map(cardinal).where(racha.notna())
    return _tabla(numero("temperature"), racha, rumbo, numero("rainfall"), numero("humidity"))


# ---------------------------------------------------------------- METAR (aeropuertos)

@st.cache_data(ttl="10m", show_spinner=False)
def get_metar(icao):
    """Partes METAR de un aeropuerto (API de aviationweather.gov): temperatura en grados enteros, sin lluvia ni humedad
    (la que sale de temperatura y punto de rocío enteros es poco precisa) y racha solo cuando es destacable."""

    params = {"ids": icao, "format": "json", "hours": HORAS}
    datos = pd.DataFrame(descargar("https://aviationweather.gov/api/data/metar", params=params).json())
    if datos.empty:
        raise ValueError(f"No hay partes METAR recientes de {icao}")

    datos.index = pd.to_datetime(datos["reportTime"], utc=True)
    datos = datos[datos.index.minute == 0].sort_index()  # el parte de cada hora (el de y 50 se fecha a en punto)
    datos = datos[~datos.index.duplicated(keep="last")]  # correcciones del mismo parte
    # Sin ninguna racha en las últimas horas no viene ni la columna; "VRB" (dirección variable) queda sin dirección
    datos = datos.reindex(columns=["temp", "wdir", "wgst"]).apply(pd.to_numeric, errors="coerce")
    racha = 1.852 * datos["wgst"]  # nudos -> km/h
    return _tabla(datos["temp"], racha, datos["wdir"].map(cardinal).where(racha.notna()))


# ---------------------------------------------------------------- Carga común

# Red -> (nombre que se cita, descarga de una estación)
REDES = {
    "aemet": ("AEMET", get_aemet_horario),
    "fmi": ("FMI", get_fmi),
    "arso": ("ARSO", get_arso),
    "kmi": ("KMI", get_kmi),
    "lvgmc": ("LVĢMC", get_lvgmc),
    "met_eireann": ("Met Éireann", get_met_eireann),
    "metar": ("METAR", get_metar),
}
DESCARGAS = tuple(descarga for _, descarga in REDES.values())


def descargar_en(estacion):
    """(función, código) para lanzar la descarga de una estación en paralelo."""

    return REDES[estacion.red][1], estacion.codigo


def _combinar(estaciones, tz):
    """Observaciones de las estaciones en hora local, cada variable de la primera que la mida, o None si no hay
    ninguna reciente (la temperatura más reciente con más de ANTIGUEDAD_MAXIMA no sería la actual); y si han fallado
    todas las descargas."""

    tablas = []
    for estacion in estaciones:
        try:
            tablas.append(REDES[estacion.red][1](estacion.codigo).tz_convert(tz))
        except Exception:
            pass
    if not tablas:
        return None, True

    primeras = {c: next((t[c] for t in tablas if t[c].notna().any()), None) for c in COLUMNAS}
    obs = pd.DataFrame({c: s for c, s in primeras.items() if s is not None}).reindex(columns=COLUMNAS)
    temperatura = obs["temperatura"].dropna()
    if temperatura.empty or pd.Timestamp.now(tz=tz) - temperatura.index[-1] > ANTIGUEDAD_MAXIMA:
        return None, False
    return obs, False


def temperatura_reciente(estaciones, tz):
    """Última temperatura observada y su hora, o None si no hay ninguna reciente; sin avisos en la página (portada)."""

    obs, _ = _combinar(estaciones, tz) if estaciones else (None, False)
    if obs is None:
        return None
    temperatura = obs["temperatura"].dropna()
    return temperatura.iloc[-1], temperatura.index[-1]


def cargar_observaciones(estaciones, tz, lugar):
    """Observaciones de las estaciones en hora local, o None si no hay ninguna reciente; y el texto que cita su origen.

    Con varias estaciones, cada variable sale de la primera que la mida (ver _combinar). Si falla la descarga, avisa en
    la página.
    """

    redes = " y ".join(dict.fromkeys(REDES[e.red][0] for e in estaciones))
    obs, fallan = _combinar(estaciones, tz)
    if fallan:
        st.warning(f"No se han podido descargar las observaciones de {redes} ({lugar}). Se muestra solo la previsión.")
    if obs is None:
        return None, f"observación {redes} no disponible"
    temperatura = obs["temperatura"].dropna()

    nombres = [e.nombre for e in estaciones if e.nombre]
    cita = f"{redes} ({' y '.join(nombres)})" if nombres else redes
    return obs, f"observación {cita} de las {temperatura.index[-1].hour} h"


def temperatura_actual_y_ayer(obs):
    """Temperatura observada más reciente y la de 24 h antes (o la más antigua disponible).

    Devuelve (None, None) si no hay observaciones de temperatura (la red caída o la estación sin ese sensor).
    """

    temp = obs["temperatura"].dropna() if obs is not None else pd.Series(dtype=float)
    if temp.empty:
        return None, None

    temp_ayer = temp.asof(temp.index[-1] - pd.Timedelta(hours=24))
    return temp.iloc[-1], temp_ayer if not pd.isna(temp_ayer) else temp.iloc[0]
