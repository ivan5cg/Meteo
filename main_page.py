"""Punto de entrada de Meteo Dash: navegación, estilo común y controles del sidebar."""

import pandas as pd
import streamlit as st

from meteodash.aemet import get_aemet_horario
from meteodash.estilo import aplicar_estilos
from meteodash.fuentes import get_meteociel_table, get_open_meteo

# La caché es común a todos los visitantes: como mucho una actualización forzada cada tanto
INTERVALO_ACTUALIZAR = pd.Timedelta(minutes=5)

st.set_page_config(page_title="Meteo Dash", page_icon=":material/partly_cloudy_day:", layout="wide")

paginas = st.navigation({
    "España": [
        st.Page("paginas/madrid.py", title="Madrid", icon=":material/location_city:", default=True),
        st.Page("paginas/avila.py", title="Ávila", icon=":material/fort:"),
        st.Page("paginas/alicante.py", title="Alicante", icon=":material/beach_access:"),
        st.Page("paginas/santander.py", title="Santander", icon=":material/sailing:"),
        st.Page("paginas/torrelavega.py", title="Torrelavega", icon=":material/landscape:"),
        st.Page("paginas/pirineos.py", title="Pirineos", icon=":material/terrain:"),
    ],
    "Europa": [
        st.Page("paginas/dublin.py", title="Dublín", icon=":material/public:"),
        st.Page("paginas/milan.py", title="Milán", icon=":material/public:"),
        st.Page("paginas/belgica.py", title="Bélgica", icon=":material/public:"),
    ],
})



@st.cache_resource
def _ultima_actualizacion():
    return {"momento": None}


def actualizar_datos():
    """Vacía la caché de previsiones y observaciones (no la de históricos ni mapas), como mucho una vez cada 5 min."""

    ultima = _ultima_actualizacion()
    ahora = pd.Timestamp.now(tz="UTC")
    if ultima["momento"] is not None and ahora - ultima["momento"] < INTERVALO_ACTUALIZAR:
        espera = int((ultima["momento"] + INTERVALO_ACTUALIZAR - ahora).total_seconds() // 60) + 1
        st.toast(f"Los datos se acaban de actualizar. Podrás volver a hacerlo en {espera} min.", icon=":material/schedule:")
        return
    ultima["momento"] = ahora
    for funcion in (get_meteociel_table, get_open_meteo, get_aemet_horario):
        funcion.clear()
    st.rerun()


aplicar_estilos()

with st.sidebar:
    if st.button("Actualizar datos", icon=":material/refresh:", width="stretch",
                 help="Vuelve a descargar las previsiones y observaciones"):
        actualizar_datos()

paginas.run()
