import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st

MADRID_TZ = "Europe/Madrid"
USER_AGENT = {"User-Agent": "Mozilla/5.0 (Meteo Dash; Streamlit)"}

# Nombres de columna del antiguo CSV de "últimos datos", que usan las páginas
COLUMNAS = {
    "temperatura": "Temperatura (ºC)",
    "vel_viento": "Velocidad del viento (km/h)",
    "dir_viento": "Dirección del viento",
    "vel_racha": "Racha (km/h)",
    "dir_racha": "Dirección de racha",
    "precipitacion": "Precipitación (mm)",
    "presion": "Presión (hPa)",
    "tendencia": "Tendencia (hPa)",
    "humedad": "Humedad (%)",
}


@st.cache_data(ttl="10m", show_spinner=False)
def get_aemet_horario(estacion):
    """Últimas ~24 h de observaciones horarias de una estación de AEMET, de la más reciente a la más antigua.

    AEMET retiró en 2026 el CSV de "últimos datos"; su web ahora consume este XML.
    """

    response = requests.get(
        f"https://www.aemet.es/es/api-eltiempo/udat/tablas-graficas/horario/9/{estacion}",
        timeout=30,
        headers=USER_AGENT,
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)

    registros = []
    for periodo in root.iter("periodo"):
        registro = {"Fecha y hora oficial": periodo.get("utc")}
        for etiqueta, nombre in COLUMNAS.items():
            nodo = periodo.find(etiqueta)
            registro[nombre] = nodo.text if nodo is not None else None
        registros.append(registro)

    if not registros:
        raise ValueError(f"AEMET no ha devuelto observaciones para la estación {estacion}")

    df = pd.DataFrame(registros).set_index("Fecha y hora oficial")
    df.index = pd.to_datetime(df.index).tz_localize("UTC").tz_convert(MADRID_TZ)

    numericas = [c for c in COLUMNAS.values() if not c.startswith("Dirección")]
    df[numericas] = df[numericas].apply(pd.to_numeric, errors="coerce")

    return df.sort_index(ascending=False)


def cargar_aemet_horario(estacion, nombre):
    """Como get_aemet_horario, pero avisa en la página y devuelve None si AEMET falla."""

    try:
        return get_aemet_horario(estacion)
    except Exception:
        st.warning(f"No se han podido descargar las observaciones de AEMET ({nombre}). Se muestra solo la previsión.")
        return None


def temperatura_actual_y_ayer(aemet_horario, temp_data):
    """Temperatura observada más reciente y la de 24 h antes.

    Sin observaciones (AEMET caído o la estación sin sensor de temperatura), usa la
    media del ensemble a la hora actual (y delta 0).
    """

    temp_obs = pd.Series(dtype=float)
    if aemet_horario is not None:
        temp_obs = aemet_horario["Temperatura (ºC)"].sort_index().dropna()

    if temp_obs.empty:
        ahora = pd.Timestamp.now(tz=MADRID_TZ)
        prevista = temp_data.drop(columns="Actual data", errors="ignore").mean(axis=1).asof(ahora)
        temp_actual = pd.Series([prevista]).round(1).iloc[0]
        return temp_actual, temp_actual

    temp_actual = temp_obs.iloc[-1]
    temp_ayer = temp_obs.asof(temp_obs.index[-1] - pd.Timedelta(hours=24))
    if pd.isna(temp_ayer):
        temp_ayer = temp_obs.iloc[0]

    return temp_actual, temp_ayer
