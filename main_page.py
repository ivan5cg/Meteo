"""Punto de entrada de Meteo Dash: navegación, estilo común y controles del sidebar."""

import streamlit as st

from meteodash.estilo import aplicar_estilos

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

aplicar_estilos()

with st.sidebar:
    if st.button("Actualizar datos", icon=":material/refresh:", use_container_width=True,
                 help="Vuelve a descargar todas las previsiones y observaciones"):
        st.cache_data.clear()
        st.rerun()

paginas.run()
