import streamlit as st

from meteodash.ciudad import Ciudad, render_pagina

st.set_page_config(layout="wide")

render_pagina(Ciudad(nombre="Milán", lat=45.464, lon=9.190, tz="Europe/Rome"), titulo="Milán 🇮🇹")
