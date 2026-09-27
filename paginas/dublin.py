import streamlit as st

from meteodash.ciudad import Ciudad, render_pagina

st.set_page_config(layout="wide")

render_pagina(Ciudad(nombre="Dublín", lat=53.338, lon=-6.28, tz="Europe/Dublin"), titulo="Dublín 🇮🇪")
