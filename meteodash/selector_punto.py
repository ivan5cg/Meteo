"""Mapa en el que se elige un punto con un clic, dentro del dominio del ensemble PE-AROME de Meteociel.

Es un componente bidireccional de Streamlit (`st.components.v2`) con Leaflet: al pulsar en el mapa devuelve a Python
las coordenadas del punto, sin dependencias nuevas.
"""

import streamlit as st

# Contorno del dominio con datos del PE-AROME en Meteociel, (lat, lon). Medido punto a punto contra sus tablas: fuera
# de él devuelven valores de relleno. Es una proyección cónica, así que se estrecha hacia el sur y su borde es curvo.
DOMINIO_AROME = [
    # Borde sur, de oeste a este
    (37.50, -8.15), (37.55, -8.0), (37.69, -6.0), (37.83, -4.0), (37.97, -2.0), (38.04, 0.0), (38.04, 2.0),
    (38.04, 4.0), (37.97, 6.0), (37.83, 8.0), (37.69, 10.0), (37.55, 12.0), (37.50, 12.15),
    # Borde este, de sur a norte
    (38.0, 12.2), (40.0, 12.55), (42.0, 12.9), (44.0, 13.37), (46.0, 13.72), (48.0, 14.19), (50.0, 14.66),
    (52.0, 15.24), (53.0, 15.48), (54.0, 15.83), (54.45, 15.82),
    # Borde norte, de este a oeste
    (54.94, 12.0), (55.12, 10.0), (55.22, 8.0), (55.31, 6.0), (55.31, 2.0), (55.31, -2.0), (55.22, -4.0),
    (55.12, -6.0), (54.94, -8.0), (54.45, -11.82),
    # Borde oeste, de norte a sur
    (54.0, -11.71), (53.0, -11.48), (52.0, -11.24), (50.0, -10.66), (48.0, -10.19), (46.0, -9.72), (44.0, -9.37),
    (42.0, -8.9), (40.0, -8.55), (38.0, -8.2),
]


def dentro_de_arome(lat, lon):
    """Si el punto cae dentro de DOMINIO_AROME (algoritmo del rayo)."""

    dentro = False
    for (lat1, lon1), (lat2, lon2) in zip(DOMINIO_AROME, DOMINIO_AROME[1:] + DOMINIO_AROME[:1]):
        if (lat1 > lat) != (lat2 > lat) and lon < lon1 + (lat - lat1) * (lon2 - lon1) / (lat2 - lat1):
            dentro = not dentro
    return dentro


HTML = '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"><div class="mapa-punto"></div>'

CSS = """
.mapa-punto { height: 460px; border-radius: 14px; border: 1px solid #d6cfc4; cursor: crosshair; }
.mapa-punto .leaflet-container { font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; }
"""

JS = """
const leaflet = import("https://unpkg.com/leaflet@1.9.4/dist/leaflet-src.esm.js");

export default async function(component) {
  const { data, parentElement, setTriggerValue } = component;
  const L = await leaflet;
  const div = parentElement.querySelector(".mapa-punto");

  // El mapa se crea una vez; en cada recarga de la página solo se mueve el marcador si el punto ha cambiado
  if (!div._mapa) {
    const mapa = L.map(div, {zoomControl: true, minZoom: 4});
    const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas";
    L.tileLayer(`${ESRI}/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`, {
      attribution: "Mapa &copy; Esri", maxZoom: 16,
    }).addTo(mapa);
    L.tileLayer(`${ESRI}/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}`, {maxZoom: 16}).addTo(mapa);
    const dominio = L.polygon(data.dominio, {color: "#d97706", weight: 2, fillOpacity: 0.04, interactive: false})
      .addTo(mapa);
    mapa.setMaxBounds(dominio.getBounds().pad(0.3));

    div._marcador = L.circleMarker([0, 0], {radius: 7, color: "#111", weight: 2, fillColor: "#d97706",
                                            fillOpacity: 1});
    mapa.on("click", (e) => {
      const lat = Math.round(e.latlng.lat * 1000) / 1000, lon = Math.round(e.latlng.lng * 1000) / 1000;
      div._marcador.setLatLng([lat, lon]).addTo(mapa);
      setTriggerValue("punto", {lat, lon});
    });
    div._mapa = mapa;
    if (data.lat === null) mapa.fitBounds(dominio.getBounds());
  }

  const clave = `${data.lat},${data.lon}`;
  if (data.lat !== null && div._clave !== clave) {
    div._marcador.setLatLng([data.lat, data.lon]).addTo(div._mapa);
    div._mapa.setView([data.lat, data.lon], div._clave === undefined ? 7 : Math.max(div._mapa.getZoom(), 7));
  }
  div._clave = clave;
  // El contenedor puede haber cambiado de tamaño (p. ej. al plegar el sidebar)
  setTimeout(() => div._mapa.invalidateSize(), 0);
}
"""

_mapa = st.components.v2.component("selector_punto", html=HTML, css=CSS, js=JS, isolate_styles=False)


def selector_punto(lat=None, lon=None, key="selector_punto"):
    """Muestra el mapa con el punto (lat, lon) marcado; devuelve {"lat", "lon"} si se acaba de pulsar en él."""

    datos = {"lat": lat, "lon": lon, "dominio": DOMINIO_AROME}
    return _mapa(data=datos, key=key, on_punto_change=lambda: None).punto
