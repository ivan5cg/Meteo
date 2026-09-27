import streamlit as st

from meteodash.ciudad import Ciudad, render_pagina

st.set_page_config(layout="wide")

render_pagina(Ciudad(
    nombre="Torrelavega",
    lat=43.35,
    lon=-4.047,
    estacion_aemet="1154H",  # Sierrapando
    semana=True,
    mapas_arome="Torrelavega",
))
