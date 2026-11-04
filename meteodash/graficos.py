"""Gráficos Plotly: el histórico frente a la previsión (corto plazo) y el Kp a 27 días (auroras). Los del medio y el
largo plazo van en visor.py, y las 48 h, en el meteograma."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .estilo import AMBAR, FUENTE, NOCHE_TEXTO, ROJO, TEXTO, coma, tema_noche, tema_plotly

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIAS_LARGOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Gráficos fijos y sin barra de herramientas: en el móvil, arrastrar el dedo sobre ellos desplaza la página en lugar de
# hacer zoom (los ejes fijos y sin arrastre, en estilo.tema_plotly). Tocar un punto sigue mostrando sus valores
CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showAxisDragHandles": False}


def mostrar(fig, **kwargs):
    """st.plotly_chart con CONFIG."""

    st.plotly_chart(fig, config=CONFIG, **kwargs)


def dia_semana(fecha, largo=False):
    fecha = pd.Timestamp(fecha)
    nombres = DIAS_LARGOS if largo else DIAS
    return f"{nombres[fecha.weekday()]} {fecha.day}"


# ---------------------------------------------------------------- Calidad del aire

# Índice europeo de calidad del aire: (límite superior, categoría, color)
CATEGORIAS_ICA = [
    (20, "Buena", "#50f0e6"), (40, "Razonablemente buena", "#50ccaa"), (60, "Regular", "#f0e641"),
    (80, "Desfavorable", "#ff5050"), (100, "Muy desfavorable", "#960032"),
    (float("inf"), "Extremadamente desfavorable", "#7d2181"),
]


def categoria_ica(valor):
    """(categoría, color) del índice europeo de calidad del aire."""

    return next((nombre, color) for limite, nombre, color in CATEGORIAS_ICA if valor <= limite)


# ---------------------------------------------------------------- Histórico

def historico_vs_prevision(datos, dia, hoy, mañana):
    """Temperaturas registradas un día como hoy frente a la previsión de hoy y mañana.

    `hoy` y `mañana` son tuplas (mínima, máxima); los valores NaN no se dibujan.
    """

    del_dia = datos[datos["día_del_año"] == dia]
    tablas = []
    for tipo, columna in [("Mínima", "tmin"), ("Máxima", "tmax")]:
        serie = del_dia[columna].dropna()
        tablas.append(pd.DataFrame({"Tipo": tipo, "Temperatura": serie, "Año": serie.index.year.astype(str)}))

    fig = px.strip(pd.concat(tablas), x="Tipo", y="Temperatura", color="Tipo", hover_data=["Año"],
                   stripmode="overlay", color_discrete_sequence=["#0284c7", ROJO])
    fig.update_traces(
        jitter=0.8, opacity=0.35,
        marker=dict(size=8, line=dict(width=0.5, color="rgba(99, 91, 83, 0.2)")),
        hovertemplate="<b>Año %{customdata[0]}</b><br>Temp %{x}: <b>%{y:.1f}°C</b><extra></extra>",
    )

    for (minima, maxima), nombre, color, simbolo, posicion in [
        (hoy, "Hoy", "#059669", "circle", "middle left"),
        (mañana, "Mañana", AMBAR, "diamond", "middle right"),
    ]:
        puntos = [(tipo, valor) for tipo, valor in [("Mínima", minima), ("Máxima", maxima)] if not pd.isna(valor)]
        if not puntos:
            continue
        fig.add_trace(go.Scatter(
            x=[tipo for tipo, _ in puntos], y=[valor for _, valor in puntos], mode="markers+text",
            name=f"Prev. {nombre}",
            marker=dict(size=16, color=color, line=dict(width=2, color="white"), symbol=simbolo),
            text=[f"<b>{nombre}: {coma(valor)}º</b>" for _, valor in puntos], textposition=posicion,
            textfont=dict(color=TEXTO, size=11, family=FUENTE),
            hovertemplate=f"<b>Previsión {nombre} (%{{x}}): %{{y:.1f}}°C</b><extra></extra>",
        ))

    tema_plotly(fig, "", "Temperatura (°C)", hovermode="closest")
    fig.update_layout(xaxis=dict(showgrid=False, title_text=""), legend_title_text="")
    return fig


# ---------------------------------------------------------------- Auroras (tema nocturno)

# (Kp sobre el umbral del lugar, valoración, color) de la actividad geomagnética
NIVELES_AURORA = [(2, "Muy buenas", "#e879f9"), (0, "Buenas", "#34d399"), (-1, "Posibles", "#fbbf24")]
SIN_AURORAS = ("Poco probables", "#64748b")


def valoracion_kp(kp, umbral):
    """(valoración, color) de la actividad geomagnética en un lugar que suele ver auroras desde Kp `umbral`."""

    return next(((texto, color) for margen, texto, color in NIVELES_AURORA if kp >= umbral + margen), SIN_AURORAS)


def kp_27_dias(serie, umbral, hoy):
    """Kp máximo previsto de cada día (Series indexada por fecha), coloreado según lo que se ve con él."""

    serie = serie[serie.index >= hoy]
    fechas = pd.DatetimeIndex(serie.index)
    fig = go.Figure(go.Bar(
        x=fechas, y=serie, marker=dict(color=[valoracion_kp(v, umbral)[1] for v in serie], line=dict(width=0)),
        text=[f"<b>{v:.0f}</b>" for v in serie], textposition="outside",
        textfont=dict(color=NOCHE_TEXTO, size=10, family=FUENTE),
        customdata=[dia_semana(f, largo=True) for f in fechas],
        hovertemplate="%{customdata}: Kp máximo <b>%{y:.0f}</b><extra></extra>",
    ))
    tema_noche(fig, "Kp máximo previsto · 27 días", "Kp", leyenda=False, hovermode="closest")
    marcas = [fechas[0]] + [f for f in fechas[1:] if f.weekday() == 0]
    fig.update_xaxes(tickvals=marcas, ticktext=["Hoy" if f.date() == hoy else dia_semana(f) for f in marcas])
    fig.update_yaxes(range=[0, min(9, max(umbral + 3, serie.max() + 1.5))])
    return fig
