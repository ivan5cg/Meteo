"""Radar de precipitación de RainViewer: las últimas 2 h, cada 10 min, animadas en bucle sobre un mapa base.

La animación corre en el navegador (Leaflet dentro de un iframe), así que no provoca recargas de Streamlit. El plan
gratuito de RainViewer solo sirve teselas hasta el zoom 7: Leaflet las amplía al acercar (`maxNativeZoom`).
"""

import json

import streamlit as st
import streamlit.components.v1 as components

ALTURA = 600

PLANTILLA = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body { margin: 0; height: 100%; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; }
  #mapa { height: 100%; border-radius: 14px; }
  .panel {
    position: absolute; z-index: 1000; left: 12px; bottom: 22px; display: flex; align-items: center; gap: 10px;
    background: rgba(247, 244, 238, 0.95); border: 1px solid #d6cfc4; border-radius: 12px; padding: 8px 12px;
    color: #2a241f; box-shadow: 0 4px 14px -2px rgba(60, 50, 40, 0.15); font-size: 14px;
  }
  .panel button {
    border: none; background: #d97706; color: white; border-radius: 8px; width: 34px; height: 30px;
    font-size: 15px; cursor: pointer;
  }
  #hora { font-weight: 700; min-width: 48px; font-variant-numeric: tabular-nums; }
  #barra { display: flex; gap: 3px; }
  #barra span { width: 8px; height: 8px; border-radius: 50%; background: #d6cfc4; cursor: pointer; }
  #barra span.activo { background: #d97706; }
  #error { position: absolute; z-index: 1000; top: 12px; left: 50%; transform: translateX(-50%); display: none;
           background: #fdf6e7; border: 1px solid #fce7c6; color: #b45309; padding: 8px 12px; border-radius: 10px; }
</style>
</head>
<body>
<div id="mapa"></div>
<div class="panel">
  <button id="play" title="Pausar / reproducir">⏸</button>
  <span id="hora">--:--</span>
  <div id="barra"></div>
</div>
<div id="error">No se ha podido descargar el radar de RainViewer</div>
<script>
const PUNTOS = __PUNTOS__;
const TZ = __TZ__;
const PASO_MS = 600, PAUSA_FINAL_MS = 1800;

const centro = [PUNTOS.reduce((s, p) => s + p[1], 0) / PUNTOS.length,
                PUNTOS.reduce((s, p) => s + p[2], 0) / PUNTOS.length];
const mapa = L.map("mapa", {zoomControl: true}).setView(centro, 7);
// Mapa base gris claro de Esri (sin clave) y sus etiquetas por encima del radar
const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas";
L.tileLayer(`${ESRI}/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`, {
  attribution: 'Mapa &copy; Esri | Radar: <a href="https://www.rainviewer.com" target="_blank">RainViewer</a>',
  maxZoom: 12,
}).addTo(mapa);
mapa.createPane("etiquetas").style.zIndex = 450;
mapa.getPane("etiquetas").style.pointerEvents = "none";
L.tileLayer(`${ESRI}/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}`, {pane: "etiquetas", maxZoom: 12}).addTo(mapa);
for (const [nombre, lat, lon] of PUNTOS) {
  L.circleMarker([lat, lon], {radius: 5, color: "#111", weight: 2, fillColor: "#fff", fillOpacity: 1})
    // Con varios puntos cercanos las etiquetas fijas se solapan: entonces solo al pasar el ratón
    .bindTooltip(nombre, {permanent: PUNTOS.length === 1, direction: "right", offset: [6, 0]}).addTo(mapa);
}

let fotogramas = [], capas = [], actual = -1, reproduciendo = true, temporizador = null;
const formato = new Intl.DateTimeFormat("es-ES", {hour: "2-digit", minute: "2-digit", timeZone: TZ});

function mostrar(i) {
  if (actual >= 0 && capas[actual]) capas[actual].setOpacity(0);
  actual = i;
  capas[i].setOpacity(0.8);
  document.getElementById("hora").textContent = formato.format(new Date(fotogramas[i].time * 1000));
  document.querySelectorAll("#barra span").forEach((s, j) => s.classList.toggle("activo", j === i));
}

function avanzar() {
  mostrar((actual + 1) % capas.length);
  temporizador = setTimeout(avanzar, actual === capas.length - 1 ? PAUSA_FINAL_MS : PASO_MS);  // pausa en el último
}

function pausar(pausa) {
  reproduciendo = !pausa;
  clearTimeout(temporizador);
  document.getElementById("play").textContent = reproduciendo ? "⏸" : "▶";
  if (reproduciendo) temporizador = setTimeout(avanzar, PASO_MS);
}

async function cargar() {
  try {
    const datos = await (await fetch("https://api.rainviewer.com/public/weather-maps.json")).json();
    capas.forEach(c => mapa.removeLayer(c));
    fotogramas = datos.radar.past;
    capas = fotogramas.map(f => L.tileLayer(`${datos.host}${f.path}/256/{z}/{x}/{y}/2/1_1.png`, {
      opacity: 0, maxNativeZoom: 7, maxZoom: 12, zIndex: 10,
    }));
    capas.forEach(c => c.addTo(mapa));  // se cargan todas desde el principio: el bucle va fluido desde la 1.ª vuelta
    const barra = document.getElementById("barra");
    barra.innerHTML = "";
    capas.forEach((_, j) => {
      const punto = document.createElement("span");
      punto.onclick = () => { pausar(true); mostrar(j); };
      barra.appendChild(punto);
    });
    actual = -1;
    mostrar(capas.length - 1);
    document.getElementById("error").style.display = "none";
    if (reproduciendo) { clearTimeout(temporizador); temporizador = setTimeout(avanzar, PAUSA_FINAL_MS); }
  } catch (e) {
    document.getElementById("error").style.display = "block";
  }
}

document.getElementById("play").onclick = () => pausar(reproduciendo);
cargar();
setInterval(cargar, 10 * 60 * 1000);  // RainViewer publica un fotograma nuevo cada 10 min
</script>
</body>
</html>
"""


def render_radar(puntos, tz="Europe/Madrid"):
    """Radar animado centrado en los puntos [(nombre, lat, lon)], que se marcan en el mapa."""

    st.header("Radar de precipitación")
    html = PLANTILLA.replace("__PUNTOS__", json.dumps(puntos, ensure_ascii=False)).replace("__TZ__", json.dumps(tz))
    components.html(html, height=ALTURA)
    st.caption("Últimas 2 h, una imagen cada 10 min, en bucle. Pulsa un punto de la barra para ver ese momento. "
               "Al acercar mucho se ve pixelado: el servicio gratuito no da más resolución.")
