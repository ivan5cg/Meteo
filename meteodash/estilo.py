"""Estilo visual común: CSS de la app (tonos arena cálidos) y tema de los gráficos Plotly."""

import streamlit as st

FUENTE = "Plus Jakarta Sans, Inter"
TEXTO = "#2a241f"
ROJO = "#d93856"
AZUL = "#0277bd"
AMBAR = "#d97706"

# Pestaña de auroras: cielo nocturno
AURORA = "#34d399"
NOCHE_TEXTO = "#e2e8f0"
NOCHE_SUAVE = "#94a3b8"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

/* Colores: tema de .streamlit/config.toml. Aquí solo la tipografía y los detalles que el tema no cubre */
html, body, [data-testid="stAppViewContainer"], .stApp {
    font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Sin la franja de color superior de Streamlit */
[data-testid="stDecoration"] {
    display: none !important;
}

/* Separadores (dividers) visibles y elegantes */
hr, [data-testid="stDivider"], .stDivider {
    border: none !important;
    height: 1.5px !important;
    background: linear-gradient(90deg, transparent 0%, #b8b0a2 15%, #948b7d 50%, #b8b0a2 85%, transparent 100%) !important;
    margin: 2rem 0 !important;
    opacity: 1 !important;
}

section[data-testid="stSidebar"] {
    border-right: 1px solid #c8c0b2;
}

/* Tabla de récords del sidebar */
.records-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
    margin-bottom: 15px;
    font-size: 0.85rem;
}
.records-table th {
    text-align: left;
    padding: 8px;
    color: #635b53;
    font-weight: 600;
    border-bottom: 1px solid #c8c0b2;
}
.records-table td {
    padding: 8px;
    border-bottom: 1px solid #dcd5c9;
    color: #2a241f;
}
.records-table tr:hover {
    background-color: rgba(217, 119, 6, 0.06);
}
.records-table td.temp-max { color: #d93856 !important; font-weight: 600; }
.records-table td.temp-min { color: #0277bd !important; font-weight: 600; }
.records-nota {
    font-size: 0.82rem;
    color: #635b53;
    line-height: 1.6;
}

/* Temperaturas de la predicción de montaña: la tabla de récords, con la altitud junto al lugar */
.tabla-lugares { margin-top: 4px; font-size: 0.88rem; }
.tabla-lugares .altitud { font-size: 0.85em; color: #635b53; white-space: nowrap; }
.tabla-lugares td:not(:first-child), .tabla-lugares th:not(:first-child) { text-align: center; white-space: nowrap; }
@media (max-width: 460px) {
    .tabla-lugares { font-size: 0.78rem; }
    .tabla-lugares th, .tabla-lugares td { padding: 6px 4px; }
}
.nivel-aludes {
    border-left: 5px solid var(--nivel);
    background: color-mix(in srgb, var(--nivel) 12%, #fffdf8);
    padding: 8px 12px;
    border-radius: 8px;
}

/* Rejilla responsiva para cámaras */
.camera-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin-top: 15px;
}
.camera-card {
    border-radius: 14px;
    overflow: hidden;
    background: #f7f4ee;
    border: 1px solid #d6cfc4;
    box-shadow: 0 4px 14px -2px rgba(60, 50, 40, 0.08);
}
.camera-card img {
    width: 100%;
    height: auto;
    display: block;
}
.camara-pie {
    display: block;
    padding: 6px 10px;
    color: #6b6158;
    font: 500 0.8rem 'Plus Jakarta Sans', 'Inter', sans-serif;
}
a.camera-card { cursor: zoom-in; text-decoration: none; transition: transform 0.2s ease, box-shadow 0.2s ease; }
a.camera-card:hover { transform: translateY(-2px); box-shadow: 0 10px 24px -8px rgba(60, 50, 40, 0.3); }

/* Cámara en grande (tarjetas.camaras): oculta salvo cuando la URL acaba en su #id */
.camara-grande {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 999999;
    align-items: center;
    justify-content: center;
    padding: 16px;
}
.camara-grande:target { display: flex; }
.camara-fondo { position: absolute; inset: 0; background: rgba(12, 10, 8, 0.88); cursor: zoom-out; }
.camara-grande img {
    position: relative;
    max-width: min(100%, 1100px);
    max-height: calc(100vh - 96px);
    width: auto;
    height: auto;
    border-radius: 10px;
    box-shadow: 0 20px 60px -10px rgba(0, 0, 0, 0.7);
}
.camara-cerrar, .camara-flecha {
    position: absolute;
    display: grid;
    place-items: center;
    border-radius: 50%;
    background: rgba(247, 244, 238, 0.14);
    color: #f7f4ee !important;
    text-decoration: none !important;
    line-height: 1;
}
.camara-cerrar:hover, .camara-flecha:hover { background: rgba(247, 244, 238, 0.28); }
.camara-cerrar { top: 14px; right: 14px; width: 42px; height: 42px; font-size: 1.2rem; }
.camara-flecha { top: 50%; width: 48px; height: 48px; margin-top: -24px; font-size: 2rem; padding-bottom: 4px; }
.camara-flecha.anterior { left: 12px; }
.camara-flecha.siguiente { right: 12px; }
.camara-cuenta {
    position: absolute;
    bottom: 16px;
    left: 50%;
    transform: translateX(-50%);
    max-width: calc(100% - 140px);
    text-align: center;
    color: #e5ded2;
    font: 600 0.85rem 'Plus Jakarta Sans', 'Inter', sans-serif;
}
@media (max-width: 640px) {
    .camara-grande { padding: 8px; }
    .camara-flecha { top: auto; bottom: 8px; margin-top: 0; width: 44px; height: 44px; }
    .camara-cuenta { bottom: 20px; }
}

/* Tarjetas de métricas */
/* Filas equilibradas: tarjetas.py fija en --n las columnas; la última fila, si queda incompleta, va centrada.
   En pantallas estrechas se reducen las columnas según el ancho disponible (consultas de contenedor) */
.rejilla { container-type: inline-size; }
.weather-grid {
    --columnas: var(--n, 3);
    --hueco: 16px;
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--hueco);
    margin-bottom: 25px;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}
.weather-grid > .metric-card {
    box-sizing: border-box;
    min-width: 0;
    flex: 0 0 calc((100% - (var(--columnas) - 1) * var(--hueco)) / var(--columnas));
}
@container (max-width: 560px) { .weather-grid > .metric-card { --columnas: min(var(--n, 3), 2); } }
@container (max-width: 250px) { .weather-grid > .metric-card { --columnas: 1; } }
.metric-card {
    background: #f7f4ee;
    border: 1px solid #d6cfc4;
    padding: 20px;
    border-radius: 14px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    box-shadow: 0 4px 16px -2px rgba(60, 50, 40, 0.08);
    --card-hue: 30;
}
.metric-card[title] { cursor: help; }
/* Efecto hover dinámico según la temperatura de la tarjeta */
.metric-card.temp-card:hover {
    border-color: hsla(var(--card-hue), 85%, 45%, 0.5);
    box-shadow: 0 8px 24px -4px hsla(var(--card-hue), 85%, 40%, 0.18);
    transform: translateY(-3px);
    background: #ffffff;
}
.metric-card.static-card:hover {
    border-color: rgba(217, 119, 6, 0.4);
    box-shadow: 0 8px 24px -4px rgba(217, 119, 6, 0.15);
    transform: translateY(-3px);
    background: #ffffff;
}
.metric-label {
    font-size: 0.75rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #635b53;
    margin-bottom: 8px;
    font-weight: 600;
}
.metric-value {
    font-size: 2.25rem;
    font-weight: 700;
    color: #2a241f;
    margin: 0;
    line-height: 1;
    letter-spacing: -0.025em;
}
.metric-value .unidad {
    font-size: 1.1rem;
    opacity: 0.4;
    font-weight: 400;
}
.metric-delta {
    font-size: 0.85rem;
    margin-top: 10px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 4px;
}
.metric-delta .nota {
    font-weight: 400;
    opacity: 0.6;
    font-size: 0.9em;
    margin-left: 2px;
}

/* Tarjetas compactas (condiciones actuales, calidad del aire...) */
.weather-grid.compacta { --hueco: 12px; }
@container (max-width: 600px) { .weather-grid.compacta > .metric-card { --columnas: min(var(--n, 4), 3); } }
@container (max-width: 460px) { .weather-grid.compacta > .metric-card { --columnas: min(var(--n, 4), 2); } }
.weather-grid.compacta .metric-card {
    padding: 14px 16px;
}
.weather-grid.compacta .metric-value {
    font-size: 1.6rem;
}
.metric-nota {
    font-size: 0.78rem;
    margin-top: 8px;
    color: #635b53;
}

/* Móvil: dos tarjetas por fila, más compactas */
@container (max-width: 460px) {
    .weather-grid { --hueco: 10px; margin-bottom: 16px; }
    .weather-grid .metric-card, .weather-grid.compacta .metric-card { padding: 12px 14px; border-radius: 12px; }
    .metric-label { font-size: 0.66rem; margin-bottom: 6px; letter-spacing: 0.04em; }
    .metric-value, .weather-grid.compacta .metric-value { font-size: 1.6rem; }
    .metric-value .unidad { font-size: 0.85rem; }
    .metric-delta { font-size: 0.75rem; margin-top: 6px; flex-wrap: wrap; }
    .metric-nota { font-size: 0.72rem; margin-top: 6px; }
    .progress-bg { margin-top: 12px; }
    .perc-row { gap: 6px; margin-top: 8px; }
    .perc-text { width: auto; font-size: 0.75rem; }
}
@media (max-width: 640px) {
    hr, [data-testid="stDivider"], .stDivider { margin: 1.2rem 0 !important; }
}

/* Resumen en texto y hora de los datos, bajo el título */
.resumen {
    font-size: 1.05rem;
    line-height: 1.5;
    color: #2a241f;
    margin: 0 0 18px;
}
.datos-de {
    font-size: 0.8rem;
    color: #635b53;
    margin: 0;
}
/* La línea de los datos y su botón de actualizar (actualizar.linea_datos) */
[class*="st-key-datos_"] { margin: -10px 0 6px; row-gap: 0; }
/* Streamlit resta 1rem bajo cada texto: en la fila, el botón se montaría sobre la última línea */
[class*="st-key-datos_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0; }
[class*="st-key-datos_"] button { min-height: 0; padding: 0 4px; font-size: 0.8rem; color: #b45309; }

/* Índice de secciones del corto plazo (tarjetas.indice) y los puntos a los que salta */
.indice {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin: -8px 0 6px;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
    font-size: 0.8rem;
}
.indice span { color: #635b53; margin-right: 2px; }
.indice a {
    padding: 3px 10px;
    border-radius: 999px;
    border: 1px solid #d6cfc4;
    background: #f7f4ee;
    color: #2a241f !important;
    text-decoration: none !important;
    white-space: nowrap;
}
.indice a:hover { border-color: rgba(217, 119, 6, 0.5); background: #ffffff; }
.ancla { scroll-margin-top: 70px; }

/* Tira de 7 días */
.tira-semana {
    display: grid;
    grid-template-columns: repeat(var(--dias, 7), minmax(0, 1fr));
    gap: 6px;
    margin-bottom: 6px;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}
.tira-semana .dia {
    background: #f7f4ee;
    border: 1px solid #d6cfc4;
    border-radius: 12px;
    padding: 10px 2px;
    text-align: center;
}
.dia-nombre { font-size: 0.75rem; font-weight: 600; color: #635b53; white-space: nowrap; }
.dia-icono { font-size: 1.6rem; line-height: 1.2; margin: 4px 0; }
.dia-max { font-size: 1.05rem; font-weight: 700; color: #2a241f; }
.dia-min { font-size: 0.9rem; color: #635b53; }
.dia-lluvia { font-size: 0.75rem; font-weight: 600; color: #0277bd; margin-top: 4px; }
.dia-lluvia.vacia { color: #b8b0a2; }
@media (max-width: 460px) {
    .tira-semana { gap: 3px; }
    .tira-semana .dia { padding: 8px 0; border-radius: 9px; }
    .dia-nombre { font-size: 0.62rem; }
    .dia-icono { font-size: 1.2rem; }
    .dia-max { font-size: 0.9rem; }
    .dia-min, .dia-lluvia { font-size: 0.7rem; }
}

/* Portada: una fila por lugar (enlace a su página) con la temperatura actual, hoy y mañana */
.portada {
    display: grid;
    gap: 8px;
    margin-bottom: 10px;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}
.pl-fila {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(0, 0.75fr) minmax(0, 1.4fr) minmax(0, 1.4fr);
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    background: #f7f4ee;
    border: 1px solid #d6cfc4;
    border-radius: 12px;
    color: #2a241f !important;
    text-decoration: none !important;
    transition: all 0.2s ease;
}
a.pl-fila:hover {
    background: #ffffff;
    border-color: rgba(217, 119, 6, 0.45);
    box-shadow: 0 6px 18px -6px rgba(217, 119, 6, 0.25);
    transform: translateY(-1px);
}
.pl-fila.pl-cabecera {
    background: none;
    border: none;
    padding: 0 16px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #635b53 !important;
}
.pl-nombre { font-weight: 700; font-size: 0.98rem; min-width: 0; overflow-wrap: anywhere; }
.pl-nombre small { display: block; font-weight: 400; font-size: 0.72rem; color: #635b53; }
.pl-aviso {
    display: inline-block;
    margin-left: 6px;
    padding: 0 5px;
    border-radius: 6px;
    font-size: 0.85rem;
    background: color-mix(in srgb, var(--aviso) 18%, #fffdf8);
    border: 1px solid var(--aviso);
    cursor: help;
}
.pl-ahora { font-size: 1.35rem; font-weight: 700; color: hsl(var(--hue, 30), 65%, 36%); line-height: 1.1; }
.pl-ahora small { display: block; font-size: 0.68rem; font-weight: 500; color: #635b53; }
.pl-ahora.vacio, .pl-dia.vacio { color: #b8b0a2; font-weight: 400; }
.pl-dia { display: flex; align-items: center; gap: 8px; }
.pl-icono { font-size: 1.45rem; line-height: 1; }
.pl-temps b { font-size: 1.02rem; }
.pl-temps span { color: #635b53; font-size: 0.9rem; }
.pl-lluvia { font-size: 0.78rem; font-weight: 600; color: #0277bd; margin-left: 2px; }
.pl-lluvia.vacia { color: #b8b0a2; }
/* Móvil: el día en dos líneas (icono y temperaturas, y la lluvia debajo) */
@container (max-width: 520px) {
    .pl-fila { gap: 6px; padding: 9px 10px; grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.7fr) minmax(0, 1fr) minmax(0, 1fr); }
    .pl-fila.pl-cabecera { padding: 0 10px; font-size: 0.62rem; }
    .pl-nombre { font-size: 0.84rem; }
    .pl-ahora { font-size: 1.1rem; }
    .pl-dia { flex-wrap: wrap; gap: 2px 5px; }
    .pl-icono { font-size: 1.15rem; }
    .pl-temps b { font-size: 0.88rem; }
    .pl-temps span { font-size: 0.78rem; }
    .pl-lluvia { flex-basis: 100%; margin-left: 0; font-size: 0.7rem; }
}

/* Luna: el disco con su fase, salida y puesta y las próximas fases principales. Siempre en oscuro, como un cielo
   de noche, con el tema claro de la app o sin él */
.rejilla .luna {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 18px 28px;
    background: radial-gradient(120% 90% at 15% 0%, #1b2c55 0%, #0f1a36 50%, #080d1c 100%);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 20px;
    box-shadow: 0 14px 34px -18px rgba(7, 11, 24, 0.85);
    color-scheme: dark;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}
.luna-hoy { display: flex; align-items: center; gap: 16px; flex: 1 1 260px; }
.luna-disco { width: 84px; height: 84px; flex-shrink: 0; filter: drop-shadow(0 0 14px rgba(243, 234, 210, 0.35)); }
.luna-sombra { fill: #1f2940; }
.luna-luz { fill: #f3ead2; }
.luna-borde { fill: none; stroke: rgba(226, 232, 240, 0.28); stroke-width: 1; }
.rejilla .luna .metric-label { color: #94a3b8; }
.luna-nombre { font-size: 1.35rem; font-weight: 700; color: #f1f5f9; line-height: 1.2; }
.luna-dato { font-size: 0.84rem; color: #cbd5e1; margin-top: 3px; }
.luna-proximas {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    flex: 1 1 340px;
}
.luna-fase { text-align: center; font-size: 0.74rem; color: #94a3b8; line-height: 1.35; }
.luna-fase b { display: block; color: #e2e8f0; font-size: 0.78rem; }
.luna-emoji { display: block; font-size: 1.5rem; line-height: 1.2; }
.luna-donde { color: #f3ead2; font-weight: 600; }
/* Mapa del cielo: el horizonte en el borde, el cénit en el centro */
.luna-cielo { display: flex; flex-direction: column; align-items: center; gap: 2px; flex: 0 0 auto; }
.luna-cielo span { font-size: 0.7rem; color: #94a3b8; }
.cielo { width: 136px; height: 136px; }
.cielo-horizonte { fill: rgba(148, 163, 184, 0.06); stroke: rgba(226, 232, 240, 0.4); stroke-width: 1; }
.cielo-altura { fill: none; stroke: rgba(226, 232, 240, 0.14); stroke-width: 0.6; stroke-dasharray: 2 2; }
.cielo-rotulo { fill: #94a3b8; font-size: 7.5px; font-weight: 700; text-anchor: middle; dominant-baseline: central;
                font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; }
.cielo-recorrido { fill: none; stroke: rgba(243, 234, 210, 0.55); stroke-width: 1.4; stroke-dasharray: 3 2.5;
                   stroke-linecap: round; }
.cielo-luna { fill: #f3ead2; filter: drop-shadow(0 0 4px rgba(243, 234, 210, 0.9)); }
@container (max-width: 460px) {
    .rejilla .luna { padding: 14px; gap: 14px; }
    .luna-disco { width: 64px; height: 64px; }
    .luna-nombre { font-size: 1.1rem; }
    .luna-proximas { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

/* Barra de fiabilidad */
.progress-bg {
    background: #ded8cd;
    height: 6px;
    border-radius: 3px;
    width: 100%;
    margin-top: 18px;
    overflow: hidden;
}
.progress-fill {
    background: linear-gradient(90deg, #d97706 0%, #d93856 100%);
    height: 100%;
    transition: width 1s ease-out;
}

/* Barra de percentil histórico */
.perc-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 12px;
}
.perc-text {
    font-size: 0.85rem;
    font-weight: 700;
    color: #403831;
    white-space: nowrap;
    width: 45px;
}
.perc-text span {
    font-size: 0.75em;
    font-weight: 400;
    opacity: 0.6;
    margin-left: 2px;
}
.perc-track {
    flex-grow: 1;
    height: 8px;
    background: #ded8cd;
    border-radius: 4px;
    overflow: hidden;
}
.perc-fill {
    height: 100%;
    /* Degradado cálido Turquesa - Ámbar - Coral */
    background-image: linear-gradient(90deg, #0277bd 0%, #d97706 50%, #d93856 100%);
    background-repeat: no-repeat;
    background-position: left center;
    border-radius: 4px;
    transition: width 0.5s ease-out;
}

/* Avisos */
.alerts-container {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 25px;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}
.alert-item {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    border-radius: 12px;
    border: 1px solid;
    transition: transform 0.2s ease;
    flex: 1 1 auto;
    min-width: 200px;
    max-width: fit-content;
}
.alert-item:hover { transform: translateY(-2px); }
.alert-warm { background: #fdf6e7; border-color: #fce7c6; color: #b45309; }
.alert-cold { background: #eefbfe; border-color: #c5f3fa; color: #0369a1; }
/* Avisos oficiales (Meteoalarm): color del nivel en --aviso */
/* Rejilla de columnas iguales: los avisos quedan alineados y se leen en orden, fila a fila */
.alerts-container.oficiales {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    /* Al desplegar los detalles de un aviso, los de su fila no se estiran */
    align-items: start;
}
.alerts-container.oficiales .alert-item {
    max-width: none;
    min-width: 0;
    align-items: flex-start;
}
/* Sin min-width: 0 el texto no se encoge y las URL largas del detalle se salen de la tarjeta */
.alerts-container.oficiales .alert-text {
    min-width: 0;
    overflow-wrap: anywhere;
}
.alert-oficial {
    background: color-mix(in srgb, var(--aviso) 10%, #fffdf8);
    border-color: color-mix(in srgb, var(--aviso) 45%, transparent);
    border-left: 5px solid var(--aviso);
    color: #2a241f;
}
.alert-emoji {
    font-size: 1.5rem;
    line-height: 1;
    margin-right: 12px;
}
.alert-detalle {
    display: block;
    font-size: 0.82rem;
    font-weight: 400;
    margin-top: 6px;
    line-height: 1.45;
}
.alert-detalle summary {
    cursor: pointer;
    font-size: 0.78rem;
    opacity: 0.7;
}
.alert-periodo {
    display: block;
    font-size: 0.8rem;
    opacity: 0.7;
    margin-top: 2px;
}
.alert-icon-container {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
    color: currentColor;
    flex-shrink: 0;
}
.alert-text {
    font-size: 0.9rem;
    font-weight: 500;
    letter-spacing: 0.01em;
}

/* ---------------------------------------------------------------- Auroras: cielo nocturno */
/* El contenedor de la pestaña (st.container(key="auroras")) y lo que Streamlit dibuja dentro */
.st-key-auroras {
    background: radial-gradient(120% 50% at 50% 0%, #13254d 0%, #0b1530 45%, #070b18 100%);
    border: 1px solid rgba(110, 231, 183, 0.14);
    border-radius: 22px;
    padding: 14px 18px 22px;
    box-shadow: 0 24px 60px -28px rgba(7, 11, 24, 0.9);
}
.st-key-auroras h1, .st-key-auroras h2, .st-key-auroras h3, .st-key-auroras strong { color: #f1f5f9 !important; }
.st-key-auroras p, .st-key-auroras li { color: #cbd5e1; }
.st-key-auroras [data-testid="stCaptionContainer"], .st-key-auroras [data-testid="stCaptionContainer"] p {
    color: #8193ad !important;
}
.st-key-auroras hr, .st-key-auroras [data-testid="stDivider"] {
    background: linear-gradient(90deg, transparent, rgba(52, 211, 153, 0.35) 30%, rgba(167, 139, 250, 0.35) 70%,
                transparent) !important;
}
.st-key-auroras [data-testid="stExpander"] details {
    background: rgba(15, 23, 42, 0.55);
    border-color: rgba(148, 163, 184, 0.2);
}
.st-key-auroras [data-testid="stExpander"] summary, .st-key-auroras [data-testid="stExpander"] summary * {
    color: #e2e8f0 !important;
}
.st-key-auroras .metric-card {
    background: rgba(15, 23, 42, 0.65);
    border-color: rgba(148, 163, 184, 0.18);
    box-shadow: none;
}
.st-key-auroras .metric-card.static-card:hover {
    background: rgba(30, 41, 59, 0.85);
    border-color: rgba(52, 211, 153, 0.45);
    box-shadow: 0 0 24px -8px rgba(52, 211, 153, 0.5);
}
.st-key-auroras .metric-label, .st-key-auroras .metric-nota { color: #94a3b8; }
.st-key-auroras .metric-value { color: #f1f5f9; }

/* Cabecera: cielo estrellado, cortinas de aurora animadas y un bosque de abetos */
.aurora-hero {
    position: relative;
    overflow: hidden;
    min-height: 240px;
    border-radius: 16px;
    margin-bottom: 18px;
    background: linear-gradient(180deg, #050a1a 0%, #0b1736 55%, #12305a 100%);
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
    isolation: isolate;
}
.aurora-estrellas {
    position: absolute;
    inset: 0;
    background-image:
        radial-gradient(1.5px 1.5px at 12% 18%, #fff, transparent),
        radial-gradient(1px 1px at 27% 42%, #fff, transparent),
        radial-gradient(1.2px 1.2px at 41% 12%, #fff, transparent),
        radial-gradient(1px 1px at 58% 30%, #fff, transparent),
        radial-gradient(1.6px 1.6px at 73% 9%, #fff, transparent),
        radial-gradient(1px 1px at 86% 36%, #fff, transparent),
        radial-gradient(1.2px 1.2px at 93% 16%, #fff, transparent),
        radial-gradient(1px 1px at 6% 52%, #fff, transparent),
        radial-gradient(1px 1px at 64% 55%, #fff, transparent),
        radial-gradient(1.3px 1.3px at 34% 66%, #fff, transparent);
    background-size: 260px 170px;
    opacity: 0.85;
    animation: aurora-titila 5s ease-in-out infinite;
}
.aurora-cortina {
    position: absolute;
    left: -25%;
    width: 150%;
    height: 70%;
    top: -8%;
    border-radius: 50%;
    filter: blur(26px);
    mix-blend-mode: screen;
    /* Rayos verticales suaves, como los de una cortina de aurora */
    -webkit-mask-image: repeating-linear-gradient(90deg, #000 0, rgba(0, 0, 0, 0.7) 7px, #000 13px, rgba(0, 0, 0, 0.82) 21px, #000 27px);
    mask-image: repeating-linear-gradient(90deg, #000 0, rgba(0, 0, 0, 0.7) 7px, #000 13px, rgba(0, 0, 0, 0.82) 21px, #000 27px);
    animation: aurora-ondea 16s ease-in-out infinite alternate;
}
.aurora-cortina.uno {
    background: linear-gradient(90deg, transparent 5%, rgba(52, 211, 153, 0.75) 30%, rgba(45, 212, 191, 0.6) 55%,
                rgba(52, 211, 153, 0.2) 80%, transparent);
}
.aurora-cortina.dos {
    top: 4%;
    height: 55%;
    background: linear-gradient(90deg, transparent 20%, rgba(167, 139, 250, 0.5) 45%, rgba(232, 121, 249, 0.45) 65%,
                transparent 90%);
    animation-duration: 21s;
    animation-delay: -6s;
}
.aurora-cortina.tres {
    top: 18%;
    height: 40%;
    background: linear-gradient(90deg, transparent, rgba(110, 231, 183, 0.45) 20%, transparent 45%,
                rgba(52, 211, 153, 0.5) 75%, transparent);
    animation-duration: 12s;
    animation-delay: -3s;
}
@keyframes aurora-ondea {
    0% { transform: translateX(-6%) skewY(-5deg) scaleY(1); opacity: 0.65; }
    50% { transform: translateX(3%) skewY(-1deg) scaleY(1.18); opacity: 1; }
    100% { transform: translateX(8%) skewY(-7deg) scaleY(0.9); opacity: 0.7; }
}
@keyframes aurora-titila {
    0%, 100% { opacity: 0.85; }
    50% { opacity: 0.45; }
}
@media (prefers-reduced-motion: reduce) {
    .aurora-cortina, .aurora-estrellas { animation: none; }
}
.aurora-bosque {
    position: absolute;
    left: 0;
    right: 0;
    bottom: -1px;
    width: 100%;
    height: 70px;
    fill: #040812;
}
.aurora-hero-texto {
    position: relative;
    z-index: 1;
    padding: 22px 24px 84px;
    color: #f1f5f9;
    text-shadow: 0 2px 12px rgba(4, 8, 18, 0.8);
}
.aurora-hero-lugar {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #a7f3d0;
}
.aurora-hero-nota { font-size: 0.95rem; color: #cbd5e1; margin-top: 14px; }
.aurora-hero-puntos {
    font-size: 3.6rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.03em;
    color: var(--nivel);
    text-shadow: 0 0 28px var(--nivel), 0 2px 12px rgba(4, 8, 18, 0.8);
}
.aurora-hero-puntos span { font-size: 1.3rem; font-weight: 500; color: #cbd5e1; text-shadow: none; margin-left: 4px; }
.aurora-hero-veredicto { font-size: 1.05rem; font-weight: 600; margin-top: 6px; }

/* Tarjetas de cada noche: puntuación en un anillo, valoración, mejor ventana y factores */
.noches {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
    margin: 4px 0 14px;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}
.noches.compactas { grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }
.noche {
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.78), rgba(15, 23, 42, 0.78));
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-top: 3px solid var(--nivel);
    border-radius: 16px;
    padding: 14px 16px;
    color: #e2e8f0;
    box-shadow: 0 0 26px -14px var(--nivel);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.noche:hover { transform: translateY(-3px); box-shadow: 0 0 30px -8px var(--nivel); }
.noche[title] { cursor: help; }
.noche-cabecera {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #94a3b8;
}
.noche-confianza {
    text-transform: none;
    letter-spacing: 0;
    font-weight: 500;
    padding: 1px 8px;
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.12);
    white-space: nowrap;
}
.noche-confianza.alta { color: #6ee7b7; }
.noche-confianza.media { color: #fcd34d; }
.noche-confianza.baja { color: #94a3b8; }
.noche-centro { display: flex; align-items: center; gap: 14px; margin: 12px 0; }
.noche-anillo {
    --tam: 76px;
    width: var(--tam);
    height: var(--tam);
    flex-shrink: 0;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: conic-gradient(var(--nivel) calc(var(--p) * 1%), rgba(148, 163, 184, 0.15) 0);
    box-shadow: 0 0 18px -4px var(--nivel);
}
.noche-puntos {
    width: calc(var(--tam) - 12px);
    height: calc(var(--tam) - 12px);
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: #0d1426;
    font-size: 1.5rem;
    font-weight: 800;
    color: #f8fafc;
}
.noche-veredicto { font-size: 1.15rem; font-weight: 700; color: var(--nivel); }
.noche-ventana { font-size: 0.8rem; color: #cbd5e1; margin-top: 2px; }
.noche-factores { display: grid; gap: 6px; }
.factor {
    display: grid;
    grid-template-columns: 76px 1fr 20px;
    align-items: center;
    gap: 8px;
    font-size: 0.74rem;
    color: #94a3b8;
}
.factor[title] { cursor: help; }
.factor i { display: block; height: 6px; border-radius: 3px; background: rgba(148, 163, 184, 0.15); overflow: hidden; }
.factor i b { display: block; height: 100%; border-radius: 3px; background: var(--color); }
.factor em { font-style: normal; text-align: right; font-weight: 700; color: #e2e8f0; }
.noche-detalle {
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid rgba(148, 163, 184, 0.12);
    font-size: 0.74rem;
    color: #94a3b8;
    line-height: 1.5;
}
.noches.compactas .noche { padding: 10px 8px; text-align: center; }
.noches.compactas .noche-cabecera { justify-content: center; font-size: 0.66rem; }
.noches.compactas .noche-centro { flex-direction: column; gap: 6px; margin: 8px 0 0; }
.noches.compactas .noche-anillo { --tam: 54px; }
.noches.compactas .noche-puntos { font-size: 1.1rem; }
.noches.compactas .noche-veredicto { font-size: 0.85rem; }
.noches.compactas .noche-ventana { font-size: 0.7rem; color: #94a3b8; }
@media (max-width: 460px) {
    .st-key-auroras { padding: 10px 10px 16px; border-radius: 16px; }
    .aurora-hero { min-height: 210px; }
    .aurora-hero-texto { padding: 16px 16px 70px; }
    .aurora-hero-puntos { font-size: 2.9rem; }
    .noches.compactas { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

/* Pantallas táctiles: lo que se explica al pasar el ratón (atributo title) se muestra al tocar, en una burbuja
   (ver TOQUES); una "i" discreta indica qué tarjetas la tienen */
.burbuja-info {
    position: fixed;
    z-index: 1000000;
    max-width: min(300px, calc(100vw - 16px));
    padding: 8px 11px;
    border-radius: 9px;
    background: #2a241f;
    color: #f7f4ee;
    font: 500 0.8rem/1.45 'Plus Jakarta Sans', 'Inter', sans-serif;
    box-shadow: 0 10px 28px -10px rgba(20, 15, 10, 0.6);
    pointer-events: none;
}
.burbuja-info[hidden] { display: none; }
@media (hover: none) {
    .metric-card[title]::after, .noche[title]::after {
        content: "i";
        position: absolute;
        top: 8px;
        right: 9px;
        width: 15px;
        height: 15px;
        border-radius: 50%;
        border: 1px solid currentColor;
        font: italic 700 10px/13px Georgia, serif;
        text-align: center;
        opacity: 0.35;
    }
    .noche { position: relative; }
}
</style>
"""

# Al tocar un elemento con explicación (title) en una pantalla táctil, la muestra en una burbuja; al tocar otra vez,
# fuera o al desplazarse, la oculta. Dentro de un enlace (las filas de la portada) solo lo hace la insignia de avisos,
# para que tocar la fila siga abriendo su página
TOQUES = """
<script>
(() => {
  if (window.meteoToques) return;
  window.meteoToques = true;
  const burbuja = document.createElement("div");
  burbuja.className = "burbuja-info";
  burbuja.hidden = true;
  document.body.appendChild(burbuja);
  let actual = null;
  const ocultar = () => { burbuja.hidden = true; actual = null; };

  document.addEventListener("click", (e) => {
    if (!matchMedia("(hover: none)").matches) return;
    const el = e.target.closest('[data-testid="stMarkdownContainer"] [title], .portada [title]');
    if (!el || (el.closest("a") && !el.classList.contains("pl-aviso"))) { ocultar(); return; }
    e.preventDefault();
    e.stopPropagation();
    if (actual === el) { ocultar(); return; }
    actual = el;
    burbuja.textContent = el.getAttribute("title");
    burbuja.hidden = false;
    const r = el.getBoundingClientRect(), b = burbuja.getBoundingClientRect();
    const izquierda = Math.min(Math.max(8, r.left + r.width / 2 - b.width / 2), innerWidth - b.width - 8);
    const arriba = r.bottom + 8 + b.height > innerHeight ? r.top - b.height - 8 : r.bottom + 8;
    burbuja.style.left = `${izquierda}px`;
    burbuja.style.top = `${Math.max(8, arriba)}px`;
  }, true);
  addEventListener("scroll", ocultar, true);
  // Escape cierra la cámara en grande (tarjetas.camaras)
  addEventListener("keydown", (e) => {
    if (e.key === "Escape" && location.hash.startsWith("#camara-")) location.hash = "ir-camaras";
  });
})();
</script>
"""


def coma(valor, formato=""):
    """Número con coma decimal, como se escribe en español: coma(4.5) -> "4,5"; coma(3.14159, ".1f") -> "3,1".

    Sin `formato`, el número tal cual (14.0 -> "14,0").
    """

    return format(valor, formato).replace(".", ",")


def aplicar_estilos():
    st.markdown(CSS, unsafe_allow_html=True)
    st.html(TOQUES, unsafe_allow_javascript=True)


def tema_plotly(fig, titulo, titulo_y="", leyenda=True, hovermode="x unified"):
    """Aplica el tema cálido común a una figura Plotly."""

    ejes = dict(
        showgrid=True,
        gridcolor="rgba(60, 50, 40, 0.12)",
        linecolor="rgba(60, 50, 40, 0.25)",
        color=TEXTO,
        tickfont=dict(color=TEXTO, family=FUENTE, size=11),
    )
    fig.update_layout(
        title=dict(text=titulo, font=dict(color=TEXTO, size=16, family=FUENTE), x=0, y=0.98),
        xaxis=dict(title="", tickcolor="rgba(60, 50, 40, 0.25)", tickformat="%a %d\n%H:%M", **ejes),
        yaxis=dict(title=dict(text=titulo_y, font=dict(family=FUENTE, size=12, color=TEXTO)), **ejes),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(
            bgcolor="rgba(247, 244, 238, 0.96)",
            bordercolor="#d6cfc4",
            font=dict(color=TEXTO, family=FUENTE, size=12),
            align="left",
        ),
        hovermode=hovermode,
        margin=dict(l=10, r=10, t=50, b=60 if leyenda else 10),
        legend=dict(
            orientation="h", yref="container", yanchor="bottom", y=0, xanchor="left", x=0,
            font=dict(color=TEXTO, family=FUENTE, size=11),
            bgcolor="rgba(0,0,0,0)",
        ) if leyenda else None,
        showlegend=leyenda,
        dragmode=False,
        separators=", ",  # coma decimal y, para los miles, un espacio
    )
    # Ejes fijos: sin zoom ni desplazamiento al arrastrar (ver graficos.CONFIG)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def tema_noche(fig, titulo, titulo_y="", leyenda=True, hovermode="x unified"):
    """El tema común con los colores del cielo nocturno de la pestaña de auroras (en todos los ejes)."""

    tema_plotly(fig, titulo, titulo_y, leyenda, hovermode)
    fuente = dict(color=NOCHE_SUAVE, family=FUENTE, size=11)
    # automargin: sin el tema de Streamlit (theme=None, que aclararía los gráficos), las etiquetas se saldrían
    ejes = dict(gridcolor="rgba(148, 163, 184, 0.12)", linecolor="rgba(148, 163, 184, 0.25)", color=NOCHE_SUAVE,
                tickfont=fuente, title_font=fuente, zerolinecolor="rgba(148, 163, 184, 0.2)", automargin=True)
    fig.update_xaxes(**ejes)
    fig.update_yaxes(**ejes)
    fig.update_layout(
        title_font_color=NOCHE_TEXTO,
        hoverlabel=dict(bgcolor="rgba(15, 23, 42, 0.95)", bordercolor="rgba(52, 211, 153, 0.45)",
                        font=dict(color=NOCHE_TEXTO, family=FUENTE, size=12)),
        modebar=dict(bgcolor="rgba(0, 0, 0, 0)", color="#64748b", activecolor=NOCHE_TEXTO),
    )
    if leyenda:
        fig.update_layout(legend_font_color=NOCHE_SUAVE)
    return fig
