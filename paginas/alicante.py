import streamlit as st

from meteodash.ciudad import Ciudad, render_pagina

st.set_page_config(layout="wide")

render_pagina(Ciudad(
    nombre="Alicante",
    lat=38.346,
    lon=-0.48,
    estacion_aemet="8025",
    semana=True,
))
