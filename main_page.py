"""Punto de entrada de Meteo Dash: navegación, estilo común y controles del sidebar."""

import streamlit as st

from meteodash.actualizar import actualizar_datos
from meteodash.estilo import aplicar_estilos

st.set_page_config(page_title="Meteo Dash", page_icon=":material/partly_cloudy_day:", layout="centered")

paginas = st.navigation({
    "": [
        st.Page("paginas/inicio.py", title="Todos los lugares", icon=":material/dashboard:", default=True),
    ],
    "España": [
        st.Page("paginas/madrid.py", title="Madrid", icon=":material/location_city:"),
        st.Page("paginas/avila.py", title="Ávila", icon=":material/fort:"),
        st.Page("paginas/alicante.py", title="Alicante", icon=":material/beach_access:"),
        st.Page("paginas/santander.py", title="Santander", icon=":material/sailing:"),
        st.Page("paginas/torrelavega.py", title="Torrelavega", icon=":material/landscape:"),
        st.Page("paginas/pirineos.py", title="Pirineos", icon=":material/terrain:"),
    ],
    "Europa": [
        st.Page("paginas/dublin.py", title="Dublín", icon=":material/sports_bar:"),
        st.Page("paginas/milan.py", title="Milán", icon=":material/church:"),
        st.Page("paginas/eslovenia.py", title="Liubliana y Bled", icon=":material/forest:"),
        st.Page("paginas/belgica.py", title="Bélgica", icon=":material/cookie:"),
        st.Page("paginas/escocia.py", title="Edimburgo y Highlands", icon=":material/golf_course:"),
        st.Page("paginas/londres.py", title="Londres", icon=":material/directions_bus:"),
    ],
    "Báltico y Laponia": [
        st.Page("paginas/helsinki.py", title="Helsinki", icon=":material/directions_boat:"),
        st.Page("paginas/rovaniemi.py", title="Rovaniemi", icon=":material/auto_awesome:"),
        st.Page("paginas/tallin.py", title="Tallin", icon=":material/castle:"),
        st.Page("paginas/riga.py", title="Riga", icon=":material/account_balance:"),
    ],
    "América": [
        st.Page("paginas/nueva_york.py", title="Nueva York", icon=":material/apartment:"),
    ],
    "Asia": [
        st.Page("paginas/tokio.py", title="Tokio", icon=":material/local_florist:"),
        st.Page("paginas/beijing.py", title="Beijing", icon=":material/stadium:"),
        st.Page("paginas/shanghai.py", title="Shanghái", icon=":material/domain:"),
        st.Page("paginas/chongqing.py", title="Chongqing", icon=":material/soup_kitchen:"),
        st.Page("paginas/hong_kong.py", title="Hong Kong", icon=":material/tram:"),
        st.Page("paginas/hanoi.py", title="Hanói", icon=":material/two_wheeler:"),
        st.Page("paginas/bangkok.py", title="Bangkok", icon=":material/temple_buddhist:"),
        st.Page("paginas/kuala_lumpur.py", title="Kuala Lumpur", icon=":material/mosque:"),
        st.Page("paginas/yakutsk.py", title="Yakutsk", icon=":material/ac_unit:"),
    ],
    "Explorar": [
        st.Page("paginas/punto.py", title="Cualquier punto", icon=":material/add_location_alt:"),
    ],
})


aplicar_estilos()

with st.sidebar:
    st.button("Actualizar datos", icon=":material/refresh:", width="stretch", on_click=actualizar_datos,
              help="Vuelve a descargar las previsiones y observaciones")

paginas.run()
