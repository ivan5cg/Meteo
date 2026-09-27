import streamlit as st

from meteodash.aemet import acumular_en_excel
from meteodash.ciudad import Ciudad, render_pagina

st.set_page_config(layout="wide")

acumular_en_excel("2444", "Histórico/Acumulado Ávila.xlsx")

render_pagina(Ciudad(
    nombre="Ávila",
    lat=40.659,
    lon=-4.680,
    estacion_aemet="2444",
    historico="datos/avila_1990.csv",
    semana=True,
))
