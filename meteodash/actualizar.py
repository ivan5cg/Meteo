"""Actualización forzada de los datos: botón del sidebar y, para el móvil (donde el sidebar está cerrado), de la
cabecera del corto plazo y de la portada."""

import pandas as pd
import streamlit as st

from .aemet_opendata import get_boletin_aludes, get_comentario_aemet, get_lluvia_reciente, get_prediccion_montaña
from .auroras import (get_cielo, get_kp, get_kp_27_dias, get_nubes_ensemble, get_ovation, get_prob_tormenta,
                      get_viento_solar)
from .avisos import get_avisos
from .fuentes import (get_calidad_aire, get_deterministas, get_ensemble, get_ensemble_48h, get_mar,
                      get_meteociel_table, get_open_meteo_detalle)
from .observaciones import DESCARGAS as OBSERVACIONES

# La caché es común a todos los visitantes: como mucho una actualización forzada cada tanto
INTERVALO_ACTUALIZAR = pd.Timedelta(minutes=5)


@st.cache_resource
def _ultima_actualizacion():
    return {"momento": None}


def actualizar_datos():
    """Vacía la caché de previsiones, observaciones y avisos (no la de históricos ni mapas), como mucho cada 5 min.

    Es el callback de los botones: después, Streamlit vuelve a ejecutar la página con los datos nuevos.
    """

    ultima = _ultima_actualizacion()
    ahora = pd.Timestamp.now(tz="UTC")
    if ultima["momento"] is not None and ahora - ultima["momento"] < INTERVALO_ACTUALIZAR:
        espera = int((ultima["momento"] + INTERVALO_ACTUALIZAR - ahora).total_seconds() // 60) + 1
        st.toast(f"Los datos se acaban de actualizar. Podrás volver a hacerlo en {espera} min.", icon=":material/schedule:")
        return
    ultima["momento"] = ahora
    for funcion in (get_meteociel_table, get_ensemble_48h, get_deterministas, get_open_meteo_detalle, get_ensemble,
                    get_calidad_aire, get_mar, *OBSERVACIONES, get_avisos, get_comentario_aemet, get_prediccion_montaña,
                    get_boletin_aludes, get_lluvia_reciente, get_kp, get_prob_tormenta, get_viento_solar, get_ovation,
                    get_kp_27_dias, get_cielo, get_nubes_ensemble):
        funcion.clear()


def antiguedad(descargado):
    """"hace 12 min" desde un instante (con zona), o "" si no se sabe."""

    if descargado is None or pd.isna(descargado):
        return ""
    minutos = int((pd.Timestamp.now(tz="UTC") - descargado).total_seconds() // 60)
    return "ahora mismo" if minutos < 1 else f"hace {minutos} min" if minutos < 60 else f"hace {minutos // 60} h"


def linea_datos(texto, clave):
    """La línea de origen de los datos (`texto`, HTML) con un botón de actualizar al lado."""

    with st.container(horizontal=True, vertical_alignment="center", gap="small", key=f"datos_{clave}"):
        st.markdown(f'<p class="datos-de">{texto}</p>', unsafe_allow_html=True, width="content")
        st.button("Actualizar", icon=":material/refresh:", type="tertiary", key=f"actualizar_{clave}",
                  on_click=actualizar_datos, help="Vuelve a descargar las previsiones y observaciones")
