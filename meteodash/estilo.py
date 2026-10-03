"""Estilo visual común: CSS de la app (tonos arena cálidos) y tema de los gráficos Plotly."""

import streamlit as st

FUENTE = "Plus Jakarta Sans, Inter"
TEXTO = "#2a241f"
ROJO = "#d93856"
AZUL = "#0277bd"
AMBAR = "#d97706"

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

/* Tarjetas de métricas */
.weather-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 25px;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}
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
.weather-grid.compacta {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
}
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
}
.alerts-container.oficiales .alert-item {
    max-width: none;
    min-width: 0;
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
</style>
"""


def aplicar_estilos():
    st.markdown(CSS, unsafe_allow_html=True)


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
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(color=TEXTO, family=FUENTE, size=11),
            bgcolor="rgba(0,0,0,0)",
        ) if leyenda else None,
        showlegend=leyenda,
    )
    return fig
