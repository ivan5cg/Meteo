"""Observaciones horarias de las estaciones de AEMET (últimas 24 h)."""

import xml.etree.ElementTree as ET

import pandas as pd
import streamlit as st

from .fuentes import descargar

# Etiqueta del XML -> columna
VARIABLES = {"temperatura": "temperatura", "vel_racha": "racha", "precipitacion": "precipitacion", "humedad": "humedad"}
TEXTOS = {"dir_racha": "dir_racha"}  # se quedan como texto (puntos cardinales)


@st.cache_data(ttl="10m", show_spinner=False)
def get_aemet_horario(estacion):
    """Observaciones horarias de una estación, ordenadas de la más antigua a la más reciente (hora de Madrid).

    AEMET retiró en 2026 el CSV de "últimos datos"; su web ahora consume este XML (no es una API documentada).
    """

    response = descargar(f"https://www.aemet.es/es/api-eltiempo/udat/tablas-graficas/horario/9/{estacion}")
    root = ET.fromstring(response.content)

    registros = []
    for periodo in root.iter("periodo"):
        registro = {"utc": periodo.get("utc")}
        for etiqueta, columna in (VARIABLES | TEXTOS).items():
            nodo = periodo.find(etiqueta)
            registro[columna] = nodo.text if nodo is not None else None
        registros.append(registro)

    if not registros:
        raise ValueError(f"AEMET no ha devuelto observaciones para la estación {estacion}")

    df = pd.DataFrame(registros).set_index("utc")
    df.index = pd.to_datetime(df.index).tz_localize("UTC").tz_convert("Europe/Madrid")
    numericas = list(VARIABLES.values())
    df[numericas] = df[numericas].apply(pd.to_numeric, errors="coerce")
    return df.sort_index()


def cargar_aemet_horario(estacion, nombre):
    """Como get_aemet_horario, pero avisa en la página y devuelve None si AEMET falla."""

    try:
        return get_aemet_horario(estacion)
    except Exception:
        st.warning(f"No se han podido descargar las observaciones de AEMET ({nombre}). Se muestra solo la previsión.")
        return None


def temperatura_actual_y_ayer(obs):
    """Temperatura observada más reciente y la de 24 h antes (o la más antigua disponible).

    Devuelve (None, None) si no hay observaciones de temperatura (AEMET caído o la estación sin ese sensor).
    """

    temp = obs["temperatura"].dropna() if obs is not None else pd.Series(dtype=float)
    if temp.empty:
        return None, None

    temp_ayer = temp.asof(temp.index[-1] - pd.Timedelta(hours=24))
    return temp.iloc[-1], temp_ayer if not pd.isna(temp_ayer) else temp.iloc[0]
