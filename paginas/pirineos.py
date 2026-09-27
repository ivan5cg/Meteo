import streamlit as st

from meteodash.ciudad import Ciudad, render_grupo

st.set_page_config(layout="wide")

render_grupo("Pirineos 🏔️", [
    Ciudad(nombre, lat, lon, presion_y_cape=False)
    for nombre, lat, lon in [
        ("Sallent de Gállego", 42.77147619941324, -0.3307980233574127),
        ("Tramacastilla de Tena", 42.71396690891642, -0.3163249093993428),
        ("Torla-Ordesa", 42.640, 0.000),
    ]
])
