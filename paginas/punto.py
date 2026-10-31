"""Previsión para cualquier punto de Europa (el dominio del ICON-EU), elegido en el mapa, buscando una localidad o por
coordenadas. El corto plazo sale del PE-AROME dentro de su dominio y, fuera, del ensemble de la Met Office (Gran Bretaña
e Irlanda) o del ICON-EU (ver selector_punto.ensemble_del_punto).

El punto elegido se guarda en la URL (?lat=..&lon=..), así que se puede guardar en favoritos o compartir.
"""

import streamlit as st

from meteodash.ciudad import Ciudad, render_pagina
from meteodash.fuentes import ENSEMBLES_48H, buscar_lugares, get_nombre_lugar, get_zona_horaria
from meteodash.selector_punto import DOMINIO_EUROPA, dentro_de_europa, ensemble_del_punto, selector_punto


def elegir(lat, lon, nombre=None, tz=None):
    lat, lon = round(float(lat), 3), round(float(lon), 3)
    st.session_state.punto = {"lat": lat, "lon": lon, "nombre": nombre, "tz": tz}
    st.query_params.update(lat=lat, lon=lon)


def _punto_de_la_url():
    try:
        return float(st.query_params["lat"]), float(st.query_params["lon"])
    except (KeyError, ValueError):
        return None


if "punto" not in st.session_state:
    st.session_state.punto = None
    if (desde_url := _punto_de_la_url()) is not None:
        elegir(*desde_url)

st.header("Cualquier punto 📍")
st.caption("Pulsa en el mapa, busca una localidad o escribe las coordenadas: cualquier punto de Europa dentro del "
           "rectángulo gris. Dentro del contorno naranja, el corto plazo sale del ensemble AROME; fuera, del de la Met "
           "Office en Gran Bretaña e Irlanda y del ICON-EU en el resto.")

busqueda = st.text_input("Buscar localidad", placeholder="Ej.: Gredos, Biarritz, Annecy, Tromsø…",
                         label_visibility="collapsed", icon=":material/search:")
if busqueda:
    try:
        lugares = [l for l in buscar_lugares(busqueda.strip()) if dentro_de_europa(l["lat"], l["lon"])]
    except Exception:
        st.warning("No se ha podido consultar el buscador de localidades.")
    else:
        if not lugares:
            st.caption("No se ha encontrado ninguna localidad de Europa con ese nombre.")
        else:
            def elegir_lugar(clave):
                if (lugar := st.session_state[clave]) is not None:
                    elegir(lugar["lat"], lugar["lon"], lugar["nombre"], lugar["tz"])

            clave = f"lugares_{busqueda}"
            st.selectbox("Resultados", lugares, index=None, label_visibility="collapsed",
                         placeholder=f"{len(lugares)} resultado(s): elige uno",
                         format_func=lambda l: f"{l['nombre']} ({l['region']})" if l["region"] else l["nombre"],
                         key=clave, on_change=elegir_lugar, args=(clave,))

punto = st.session_state.punto
pulsado = selector_punto(punto and punto["lat"], punto and punto["lon"])
if pulsado is not None and (punto is None or (pulsado["lat"], pulsado["lon"]) != (punto["lat"], punto["lon"])):
    elegir(pulsado["lat"], pulsado["lon"])
    st.rerun()

sur, oeste, norte, este = DOMINIO_EUROPA
with st.expander("Coordenadas", icon=":material/my_location:"):
    with st.form("coordenadas", border=False):
        col_lat, col_lon = st.columns(2)
        lat = col_lat.number_input("Latitud", sur, norte, punto["lat"] if punto else 40.4, step=0.01, format="%.3f")
        lon = col_lon.number_input("Longitud", oeste, este, punto["lon"] if punto else -3.7, step=0.01, format="%.3f")
        if st.form_submit_button("Ver previsión", icon=":material/arrow_forward:"):
            elegir(lat, lon)
            st.rerun()

punto = st.session_state.punto
if punto is None:
    st.stop()

if not dentro_de_europa(punto["lat"], punto["lon"]):
    st.error(f"El punto {punto['lat']:.3f}, {punto['lon']:.3f} está fuera de Europa (el dominio del ICON-EU). "
             "Elige otro dentro del rectángulo gris.")
    st.stop()

# Nombre y zona horaria del punto: los de la localidad buscada o, si se ha pulsado en el mapa, consultados aparte
if punto["nombre"] is None:
    try:
        punto["nombre"] = get_nombre_lugar(punto["lat"], punto["lon"]) or ""
    except Exception:
        punto["nombre"] = ""
if punto["tz"] is None:
    try:
        punto["tz"] = get_zona_horaria(punto["lat"], punto["lon"])
    except Exception:
        punto["tz"] = "Europe/Madrid"

coordenadas = f"{punto['lat']:.3f}, {punto['lon']:.3f}"
ensemble = ensemble_del_punto(punto["lat"], punto["lon"])
st.divider()
if ensemble != "arome":
    st.caption(f"Fuera del dominio del AROME: el corto plazo sale del ensemble {ENSEMBLES_48H[ensemble]['nombre']}.")
render_pagina(
    Ciudad(nombre=punto["nombre"] or coordenadas, lat=punto["lat"], lon=punto["lon"], tz=punto["tz"],
           ensemble=ensemble, nieve=True),
    titulo=f"{punto['nombre']} ({coordenadas})" if punto["nombre"] else coordenadas,
)
