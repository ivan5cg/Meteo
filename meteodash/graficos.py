"""Gráficos Plotly comunes a todas las páginas."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytz
import streamlit as st
from astral import LocationInfo
from astral.sun import elevation, sun
from plotly.subplots import make_subplots

from .estilo import AMBAR, AZUL, FUENTE, ROJO, TEXTO, tema_plotly
from .fuentes import UMBRAL_LLUVIA, UMBRAL_LLUVIA_HORA, extremos_diarios, prob_diaria, prob_por_hora

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIAS_LARGOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

OBSERVADO = "Observado"  # columna que añade ciudad.py con los datos de AEMET


def dia_semana(fecha, largo=False):
    fecha = pd.Timestamp(fecha)
    nombres = DIAS_LARGOS if largo else DIAS
    return f"{nombres[fecha.weekday()]} {fecha.day}"


def _eje_fechas_es(fig, indice, cada_horas=6):
    """Marcas del eje temporal en español (Plotly solo trae los nombres de los días en inglés)."""

    # Etiquetas cortas para que quepan sin girarse en el móvil: el día a medianoche, "12 h" a mediodía y el resto,
    # solo la línea de la rejilla
    marcas = [t for t in indice if t.hour % cada_horas == 0 and t.minute == 0]
    fig.update_xaxes(
        tickvals=marcas,
        tickangle=0,
        ticktext=[f"<b>{dia_semana(t)}</b>" if t.hour == 0 else "12 h" if t.hour == 12 else "" for t in marcas],
        hoverformat="%d/%m %H:%M",
    )


def _ensemble(data):
    """Todos los miembros del ensemble, incluido el control."""
    return data.drop(columns=OBSERVADO, errors="ignore")


def _miembros(fig, data, color):
    """Los miembros (el control se dibuja aparte, destacado) en una sola traza, separados por huecos.

    Con una traza por miembro el gráfico tarda bastante más en construirse, en enviarse y en dibujarse.
    """

    miembros = _ensemble(data).drop(columns="Ctrl", errors="ignore")
    if miembros.empty:
        return
    # Cada miembro seguido de un hueco (NaT / NaN) para que no se una con el siguiente
    utc = np.append(data.index.tz_convert("UTC").tz_localize(None).to_numpy(), np.datetime64("NaT"))
    x = pd.DatetimeIndex(np.tile(utc, len(miembros.columns))).tz_localize("UTC").tz_convert(data.index.tz)
    y = np.concatenate([np.append(miembros[c].to_numpy(dtype=float), np.nan) for c in miembros.columns])
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines", line=dict(color=color, width=1), connectgaps=False,
        name="Miembros", showlegend=False, hoverinfo="skip",
    ))


def _control(fig, data, color, formato, unidad):
    if "Ctrl" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Ctrl"], mode="lines",
            line=dict(color=color, width=2.5, dash="dash"),
            name="Control",
            hovertemplate=f"Control: <b>%{{y:{formato}}} {unidad}</b><extra></extra>",
        ))


def _observado(fig, data, formato, unidad, etiqueta="Observado", detalle=None):
    """Serie observada; `detalle` (texto por hora, p. ej. la dirección del viento) se añade al hover."""

    if OBSERVADO in data.columns and data[OBSERVADO].notna().any():
        extra = ""
        if detalle is not None:
            detalle = detalle.reindex(data.index).fillna("")
            extra = " %{customdata}"
        fig.add_trace(go.Scatter(
            x=data.index, y=data[OBSERVADO], mode="lines",
            line=dict(color=TEXTO, width=3),
            name="Observado", customdata=detalle,
            hovertemplate=f"{etiqueta}: <b>%{{y:{formato}}} {unidad}</b>{extra}<extra></extra>",
        ))


def _extremos_diarios(fig, media, formato, sufijo=""):
    """Anota el máximo y el mínimo diarios de la media del ensemble (los mismos valores que las tarjetas)."""

    for fecha in sorted(set(media.index.date)):
        dia = media[media.index.date == fecha].dropna()
        if dia.empty:
            continue
        for momento, color, desplazamiento in [(dia.idxmin(), AZUL, -15), (dia.idxmax(), ROJO, 15)]:
            fig.add_annotation(
                x=momento, y=dia[momento], text=f"<b>{dia[momento]:{formato}}{sufijo}</b>",
                showarrow=False, yshift=desplazamiento, font=dict(color=color, size=11, family=FUENTE),
            )


# ---------------------------------------------------------------- Ensemble AROME (48 h)

def temperatura(data, bandas=None, dia_bandas=None):
    """Ensemble de temperatura; con histórico, añade los rangos habituales de máxima y mínima."""

    fig = go.Figure()
    ens = _ensemble(data)

    _miembros(fig, data, "rgba(99, 91, 83, 0.22)")
    fig.add_trace(go.Scatter(
        x=data.index, y=ens.mean(axis=1), mode="lines",
        line=dict(color="#635b53", width=1.5, dash="dot"),
        name="Media",
        customdata=np.stack([ens.quantile(0.1, axis=1), ens.quantile(0.9, axis=1)], axis=-1),
        hovertemplate="Media: <b>%{y:.1f}°C</b><br>Rango 10-90%: <b>%{customdata[0]:.1f}° - %{customdata[1]:.1f}°C</b><extra></extra>",
    ))
    _control(fig, data, AMBAR, ".1f", "°C")
    _observado(fig, data, ".1f", "°C")

    if bandas is not None and dia_bandas in bandas.index:
        x = data.index.tolist()
        for variable, nombre, relleno in [
            ("tmax", "Máx. habitual", "rgba(217, 56, 86, 0.1)"),
            ("tmin", "Mín. habitual", "rgba(2, 119, 189, 0.1)"),
        ]:
            bajo = bandas.loc[dia_bandas, (variable, 0.15)]
            alto = bandas.loc[dia_bandas, (variable, 0.85)]
            fig.add_trace(go.Scatter(
                x=x + x[::-1], y=[alto] * len(x) + [bajo] * len(x),
                fill="toself", fillcolor=relleno, line=dict(color="rgba(0,0,0,0)"),
                name=nombre, hoverinfo="skip",
            ))

    _extremos_diarios(fig, ens.mean(axis=1), ".1f", "º")
    tema_plotly(fig, "Temperatura · 48 h", "Temperatura (°C)")
    _eje_fechas_es(fig, data.index)
    return fig


def lluvia(prec_data, titulo="Lluvia · 48 h"):
    """Probabilidad de lluvia de cada hora (miembros con al menos UMBRAL_LLUVIA_HORA), cantidad media cuando llueve y,
    si hay, la observada."""

    ens = _ensemble(prec_data)
    llueve = ens >= UMBRAL_LLUVIA_HORA  # los miembros sin dato (NaN) no cuentan como lluvia
    probabilidad = prob_por_hora(prec_data)
    media = ens.where(llueve).mean(axis=1).fillna(0).round(1)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5], vertical_spacing=0.1)
    fig.add_trace(go.Scatter(
        x=media.index, y=media, mode="lines+markers", fill="tozeroy",
        fillcolor="rgba(2, 119, 189, 0.12)", name="Media (L/m²)",
        line=dict(color=AZUL, width=2), marker=dict(size=4),
        hovertemplate="Lluvia media: <b>%{y} L/m²</b><extra></extra>",
    ), row=1, col=1)
    if OBSERVADO in prec_data.columns and prec_data[OBSERVADO].notna().any():
        observada = prec_data[OBSERVADO]
        fig.add_trace(go.Bar(
            x=observada.index, y=observada, name="Observada", marker=dict(color="rgba(42, 36, 31, 0.6)"),
            hovertemplate="Observada: <b>%{y:.1f} L/m²</b><extra></extra>",
        ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=probabilidad.index, y=probabilidad, name="Probabilidad (%)",
        marker=dict(color=AMBAR, line=dict(color="rgba(0,0,0,0.05)", width=1)),
        hovertemplate=f"Prob. ≥ {str(UMBRAL_LLUVIA_HORA).replace('.', ',')} L/m² en la hora: <b>%{{y:.0f}}%</b><extra></extra>",
    ), row=2, col=1)

    tema_plotly(fig, titulo, leyenda=False)
    ejes = dict(showgrid=True, gridcolor="rgba(60, 50, 40, 0.12)", linecolor="rgba(60, 50, 40, 0.25)", color=TEXTO,
                tickfont=dict(color=TEXTO, family=FUENTE, size=11))
    fig.update_xaxes(range=[media.index.min(), media.index.max()], **ejes)
    fig.update_yaxes(title_text="L/m²", title_font=dict(color=TEXTO, size=11, family=FUENTE), rangemode="tozero", row=1, col=1, **ejes)
    fig.update_yaxes(title_text="Probabilidad %", title_font=dict(color=TEXTO, size=11, family=FUENTE), range=[0, 105], row=2, col=1, **ejes)
    _eje_fechas_es(fig, media.index)
    return fig


def viento(data, direccion=None, titulo="Rachas de viento · 48 h"):
    """Rachas del ensemble; `direccion` (puntos cardinales observados) se muestra junto a la racha observada."""

    fig = go.Figure()
    _miembros(fig, data, "rgba(217, 119, 6, 0.22)")
    fig.add_trace(go.Scatter(
        x=data.index, y=_ensemble(data).mean(axis=1), mode="lines",
        line=dict(color="#b45309", width=1.5, dash="dot"),
        name="Media", hovertemplate="Media: <b>%{y:.0f} km/h</b><extra></extra>",
    ))
    _control(fig, data, AMBAR, ".0f", "km/h")
    _observado(fig, data, ".0f", "km/h", etiqueta="Racha observada", detalle=direccion)
    _extremos_diarios(fig, _ensemble(data).mean(axis=1), ".0f")
    tema_plotly(fig, titulo, "Velocidad (km/h)")
    _eje_fechas_es(fig, data.index)
    return fig


def presion(data):
    fig = go.Figure()
    _miembros(fig, data, "rgba(99, 91, 83, 0.22)")
    fig.add_trace(go.Scatter(
        x=data.index, y=_ensemble(data).mean(axis=1), mode="lines",
        line=dict(color="#635b53", width=1.5, dash="dot"),
        name="Media", hovertemplate="Media: <b>%{y:.1f} hPa</b><extra></extra>",
    ))
    _control(fig, data, AMBAR, ".1f", "hPa")
    tema_plotly(fig, "Presión · 48 h", "Presión (hPa)")
    # Al menos 30 hPa de rango, centrado en los valores previstos: una borrasca profunda no se sale del gráfico
    valores = _ensemble(data).stack()
    if not valores.empty:
        centro = (valores.min() + valores.max()) / 2
        mitad = max((valores.max() - valores.min()) / 2 + 3, 15)
        fig.update_yaxes(range=[centro - mitad, centro + mitad])
    _eje_fechas_es(fig, data.index)
    return fig


def mucape(data):
    fig = go.Figure()
    ens = _ensemble(data)
    _miembros(fig, data, "rgba(225, 29, 72, 0.2)")
    fig.add_trace(go.Scatter(
        x=data.index, y=ens.mean(axis=1), mode="lines",
        line=dict(color=AMBAR, width=1.5, dash="dot"),
        name="Media", customdata=ens.max(axis=1),
        hovertemplate="Media CAPE: <b>%{y:.0f} J/kg</b><br>Máx Ens: <b>%{customdata:.0f} J/kg</b><extra></extra>",
    ))
    _control(fig, data, ROJO, ".0f", "J/kg")

    # Zonas de riesgo (muy sutiles)
    fig.add_hrect(y0=0, y1=300, fillcolor="#10b981", opacity=0.04, line_width=0, layer="below")
    fig.add_hrect(y0=300, y1=1000, fillcolor="#fbbf24", opacity=0.04, line_width=0, layer="below")
    fig.add_hrect(y0=1000, y1=3000, fillcolor="#ef4444", opacity=0.04, line_width=0, layer="below")

    tema_plotly(fig, "Potencial de tormentas (MUCAPE) · 48 h", "J/kg")
    _eje_fechas_es(fig, data.index)
    return fig


# ---------------------------------------------------------------- Medio plazo: ensemble ICON-EU

def medio_temperatura(ens, deterministas):
    """Miembros y mediana del ensemble ICON-EU, con el ICON-EU determinista superpuesto."""

    fig = go.Figure()
    _miembros(fig, ens, "rgba(99, 91, 83, 0.18)")
    mediana = ens.median(axis=1)
    fig.add_trace(go.Scatter(
        x=ens.index, y=mediana, mode="lines", line=dict(color="#635b53", width=2.5), name="Mediana ensemble",
        customdata=np.stack([ens.quantile(0.1, axis=1), ens.quantile(0.9, axis=1)], axis=-1),
        hovertemplate=("Mediana: <b>%{y:.1f}°C</b><br>Rango 10-90%: <b>%{customdata[0]:.1f}° - "
                       "%{customdata[1]:.1f}°C</b><extra></extra>"),
    ))
    for modelo, color, trazo in [("ICON-EU", AZUL, "dash")]:
        if modelo in deterministas.columns:
            serie = deterministas[modelo].reindex(ens.index)
            fig.add_trace(go.Scatter(
                x=serie.index, y=serie, mode="lines", line=dict(color=color, width=2, dash=trazo), name=modelo,
                hovertemplate=f"{modelo}: <b>%{{y:.1f}}°C</b><extra></extra>",
            ))
    _extremos_diarios(fig, mediana, ".1f", "º")
    tema_plotly(fig, "Temperatura · medio plazo", "Temperatura (°C)")
    _eje_fechas_es(fig, ens.index)
    return fig


def _eje_dias(fig, indice):
    """Una marca por día (a medianoche) con el nombre del día en español."""

    dias = pd.DatetimeIndex(sorted(set(pd.DatetimeIndex(indice).normalize())))
    fig.update_xaxes(tickvals=dias, ticktext=[dia_semana(d) for d in dias], hoverformat="%d/%m %H:%M")


def nubes_uv(diario, titulo):
    """Nubosidad media y UV máximo de cada día."""

    x = [dia_semana(f) for f in diario.index]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=x, y=diario["nubes"], name="Nubosidad media", marker=dict(color="rgba(99, 91, 83, 0.3)"),
        hovertemplate="Nubosidad media: <b>%{y:.0f}%</b><extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=x, y=diario["uv_max"], mode="lines+markers+text", name="UV máximo",
        line=dict(color=AMBAR, width=2.5), marker=dict(size=7),
        text=[f"<b>{v:.0f}</b>" if not pd.isna(v) else "" for v in diario["uv_max"]], textposition="top center",
        textfont=dict(color=AMBAR, size=11, family=FUENTE),
        hovertemplate="UV máximo: <b>%{y:.1f}</b><extra></extra>",
    ), secondary_y=True)
    tema_plotly(fig, titulo, "Nubosidad (%)")
    fig.update_yaxes(range=[0, 105], secondary_y=False)
    fig.update_yaxes(title_text="Índice UV", range=[0, max(11, diario["uv_max"].max() + 1.5)], showgrid=False,
                     tickfont=dict(color=TEXTO, family=FUENTE, size=11), secondary_y=True)
    return fig


def nieve(horario, diario, titulo, elevacion=None):
    """Nieve diaria prevista y cota de nieve aproximada (300 m por debajo de la isoterma de 0 ºC)."""

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    mediodia = pd.DatetimeIndex(diario.index) + pd.Timedelta(hours=12)
    fig.add_trace(go.Bar(
        x=mediodia, y=diario["nieve"], name="Nieve diaria", width=20 * 3600 * 1000,
        marker=dict(color="rgba(2, 132, 199, 0.35)", line=dict(color="#0284c7", width=1)),
        text=[f"<b>{v:.0f} cm</b>" if v >= 1 else "" for v in diario["nieve"].fillna(0)], textposition="outside",
        textfont=dict(color="#0284c7", size=11, family=FUENTE),
        hovertemplate="Nieve del día: <b>%{y:.1f} cm</b><extra></extra>",
    ), secondary_y=False)
    cota = (horario["isocero"] - 300).clip(lower=0)
    fig.add_trace(go.Scatter(
        x=cota.index, y=cota, mode="lines", name="Cota de nieve aprox.", line=dict(color=TEXTO, width=2),
        hovertemplate="Cota de nieve: <b>%{y:.0f} m</b><extra></extra>",
    ), secondary_y=True)
    if elevacion is not None:  # una traza y no add_hline: su anotación acabaría en el eje de la nieve
        fig.add_trace(go.Scatter(
            x=[cota.index.min(), cota.index.max()], y=[elevacion, elevacion], mode="lines",
            name=f"Altitud ({elevacion:.0f} m)", line=dict(color=ROJO, width=1.5, dash="dot"), hoverinfo="skip",
        ), secondary_y=True)

    tema_plotly(fig, titulo, "Nieve (cm)")
    fig.update_yaxes(range=[0, max(5, 1.3 * diario["nieve"].max())], secondary_y=False)
    fig.update_yaxes(title_text="Cota (m)", rangemode="tozero", showgrid=False,
                     tickfont=dict(color=TEXTO, family=FUENTE, size=11), secondary_y=True)
    _eje_dias(fig, cota.index)
    return fig


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


def calidad_aire(df):
    """Índice europeo de calidad del aire con las bandas de cada categoría y los contaminantes en el hover."""

    fig = go.Figure()
    tope = max(60, df["european_aqi"].max() + 10)
    abajo = 0
    for limite, _, color in CATEGORIAS_ICA:
        if abajo < tope:
            fig.add_hrect(y0=abajo, y1=min(limite, tope), fillcolor=color, opacity=0.12, line_width=0, layer="below")
        abajo = limite

    fig.add_trace(go.Scatter(
        x=df.index, y=df["european_aqi"], mode="lines", line=dict(color=TEXTO, width=2.5), name="ICA europeo",
        customdata=df[["pm2_5", "pm10", "nitrogen_dioxide", "ozone"]].to_numpy(),
        hovertemplate=("ICA: <b>%{y:.0f}</b><br>PM2,5: %{customdata[0]:.0f} · PM10: %{customdata[1]:.0f} · "
                       "NO₂: %{customdata[2]:.0f} · O₃: %{customdata[3]:.0f} µg/m³<extra></extra>"),
    ))
    tema_plotly(fig, "Calidad del aire · 4 días", "Índice europeo (ICA)", leyenda=False)
    fig.update_yaxes(range=[0, tope])
    _eje_fechas_es(fig, df.index, cada_horas=12)
    return fig


def polen(df, nombres):
    """Concentración de cada tipo de polen (`nombres`: columna -> nombre en español)."""

    fig = go.Figure()
    colores = [AMBAR, "#059669", ROJO, "#7c3aed", AZUL, "#635b53"]
    for (columna, nombre), color in zip(nombres.items(), colores):
        fig.add_trace(go.Scatter(
            x=df.index, y=df[columna], mode="lines", name=nombre, line=dict(color=color, width=2),
            hovertemplate=f"{nombre}: <b>%{{y:.0f}} granos/m³</b><extra></extra>",
        ))
    tema_plotly(fig, "Polen · 4 días", "Granos/m³")
    fig.update_yaxes(rangemode="tozero")
    _eje_fechas_es(fig, df.index, cada_horas=12)
    return fig


# ---------------------------------------------------------------- Largo plazo: ensembles ECMWF y GEFS

COLORES_MODELO = {"ECMWF": AZUL, "GEFS": AMBAR}
TRAZOS_MODELO = {"ECMWF": "dot", "GEFS": "dash"}


def largo(ensembles, fechas, hoy=None):
    """Máximas y mínimas diarias de todos los miembros juntos (mediana y rango 10-90 %), la mediana de cada modelo y,
    por modelo, la probabilidad de lluvia y la lluvia media de cada día.

    `ensembles`: {nombre: {"temperatura", "precipitacion"}} (ver fuentes.get_ensemble); `fechas`: días a mostrar.
    `hoy` se rotula "Hoy" y cuenta aunque el pase empiece a medianoche UTC (20 h bastan).
    """

    maximas, minimas, por_modelo, probabilidades, totales = [], [], {}, {}, {}
    for nombre, datos in ensembles.items():
        maxima, minima = extremos_diarios(datos["temperatura"], fechas, minimo_horas=20)
        maximas.append(maxima)
        minimas.append(minima)
        por_modelo[nombre] = (maxima.median(axis=1), minima.median(axis=1))
        probabilidades[nombre] = prob_diaria(datos["precipitacion"])
        prec = datos["precipitacion"]
        totales[nombre] = prec.groupby(prec.index.date).sum(min_count=1)  # lluvia de cada miembro en cada día
    maximas, minimas = pd.concat(maximas, axis=1), pd.concat(minimas, axis=1)
    dias = [f for f in fechas if f in maximas.index]
    x = ["Hoy" if f == hoy else dia_semana(f) for f in dias]
    total = sum(d["temperatura"].shape[1] for d in ensembles.values())

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.58, 0.21, 0.21], vertical_spacing=0.05)
    for diario, nombre, color, relleno, posicion in [
        (maximas.loc[dias], "Máxima", ROJO, "rgba(217, 56, 86, 0.15)", "top center"),
        (minimas.loc[dias], "Mínima", "#0284c7", "rgba(2, 132, 199, 0.15)", "bottom center"),
    ]:
        p10, p90, mediana = diario.quantile(0.1, axis=1), diario.quantile(0.9, axis=1), diario.median(axis=1)
        fig.add_trace(go.Scatter(x=x, y=p90, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=x, y=p10, mode="lines", fill="tonexty", fillcolor=relleno, line=dict(width=0),
                                 showlegend=False, hoverinfo="skip"), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=x, y=mediana, mode="lines+markers+text", line=dict(color=color, width=2.5), marker=dict(size=6),
            text=[f"<b>{t:.0f}º</b>" for t in mediana], textposition=posicion,
            textfont=dict(color=color, size=10.5, family=FUENTE), name=nombre,
            customdata=np.stack([p10, p90], axis=-1),
            hovertemplate=(f"{nombre}: <b>%{{y:.1f}}°C</b> "
                           "(10-90%: %{customdata[0]:.1f}° - %{customdata[1]:.1f}°C)<extra></extra>"),
        ), row=1, col=1)

    # Mediana de cada modelo, fina: se ve si discrepan sin cargar el gráfico
    for modelo, (maxima, minima) in por_modelo.items():
        for serie, mostrar in [(maxima, True), (minima, False)]:
            serie = serie.reindex(dias)
            fig.add_trace(go.Scatter(
                x=x, y=serie, mode="lines", name=modelo, legendgroup=modelo, showlegend=mostrar,
                line=dict(color=COLORES_MODELO.get(modelo, TEXTO), width=1.5, dash=TRAZOS_MODELO.get(modelo)),
                hovertemplate=f"{modelo}: <b>%{{y:.1f}}°C</b><extra></extra>",
            ), row=1, col=1)

    for modelo, probabilidad in probabilidades.items():
        fig.add_trace(go.Bar(
            x=x, y=[probabilidad.get(f) for f in dias], name=modelo, legendgroup=modelo, showlegend=False,
            marker=dict(color=COLORES_MODELO.get(modelo, TEXTO), opacity=0.6),
            hovertemplate=f"{modelo}, lluvia ≥ {UMBRAL_LLUVIA} L/m²: <b>%{{y:.0f}}%</b><extra></extra>",
        ), row=2, col=1)

    # Lluvia media de los miembros (lo esperable) y, en el hover, la del 10 % de miembros más lluviosos
    for modelo, lluvia in totales.items():
        lluvia = lluvia.reindex(dias)
        fig.add_trace(go.Bar(
            x=x, y=lluvia.mean(axis=1).round(1), name=modelo, legendgroup=modelo, showlegend=False,
            marker=dict(color=COLORES_MODELO.get(modelo, TEXTO), opacity=0.6),
            customdata=lluvia.quantile(0.9, axis=1).round(1),
            hovertemplate=(f"{modelo}: media <b>%{{y:.1f}} L/m²</b><br>"
                           "10 % más lluvioso: ≥ %{customdata:.1f} L/m²<extra></extra>"),
        ), row=3, col=1)

    tema_plotly(fig, f"Largo plazo · ECMWF + GEFS ({total} miembros)", "Temperatura (°C)")
    ejes = dict(showgrid=True, gridcolor="rgba(60, 50, 40, 0.12)", linecolor="rgba(60, 50, 40, 0.25)", color=TEXTO,
                tickfont=dict(color=TEXTO, family=FUENTE, size=11))
    fig.update_xaxes(**ejes)
    fig.update_yaxes(title_text="Prob. %", title_font=dict(color=TEXTO, size=11, family=FUENTE), range=[0, 105],
                     row=2, col=1, **ejes)
    fig.update_yaxes(title_text="L/m²", title_font=dict(color=TEXTO, size=11, family=FUENTE), rangemode="tozero",
                     row=3, col=1, **ejes)
    fig.update_layout(height=640, barmode="group")
    return fig


# ---------------------------------------------------------------- Histórico y sol

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
            text=[f"<b>{nombre}: {valor}º</b>" for _, valor in puntos], textposition=posicion,
            textfont=dict(color=TEXTO, size=11, family=FUENTE),
            hovertemplate=f"<b>Previsión {nombre} (%{{x}}): %{{y:.1f}}°C</b><extra></extra>",
        ))

    tema_plotly(fig, "", "Temperatura (°C)", hovermode="closest")
    fig.update_layout(xaxis=dict(showgrid=False, title_text=""), legend_title_text="")
    return fig


@st.cache_data(max_entries=50, show_spinner=False)
def _curva_solar(latitud, longitud, zona, fecha):
    """Elevación solar minuto a minuto de un día, con amanecer, atardecer y el cambio de duración frente a ayer."""

    location = LocationInfo("Ubicación", "Región", zona, latitud, longitud)
    timezone = pytz.timezone(zona)

    sol_hoy = sun(location.observer, date=fecha, tzinfo=timezone)
    sol_ayer = sun(location.observer, date=fecha - timedelta(days=1), tzinfo=timezone)
    amanecer, atardecer = sol_hoy["sunrise"], sol_hoy["sunset"]

    diferencia = (atardecer - amanecer).total_seconds() - (sol_ayer["sunset"] - sol_ayer["sunrise"]).total_seconds()
    dif_min, dif_seg = divmod(abs(int(diferencia)), 60)
    cambio = f"{'+' if diferencia > 0 else '−'}{dif_min} min {dif_seg} s"

    duracion = (atardecer - amanecer).total_seconds()
    horas_dia, minutos_dia = int(duracion // 3600), int((duracion % 3600) / 60)

    minutos = [timezone.localize(datetime(fecha.year, fecha.month, fecha.day, h, m)) for h in range(24) for m in range(60)]
    elevaciones = np.array([elevation(location.observer, dt) for dt in minutos])
    etiquetas = [dt.strftime("%H:%M") for dt in minutos]

    i_amanecer = amanecer.hour * 60 + amanecer.minute
    i_atardecer = atardecer.hour * 60 + atardecer.minute
    titulo = f"Sol hoy · {horas_dia} h {minutos_dia} min de luz ({cambio})"
    return etiquetas, elevaciones, i_amanecer, i_atardecer, titulo


def elevacion_solar(latitud, longitud, zona="UTC"):
    hoy = datetime.now(tz=pytz.timezone(zona))
    etiquetas, elevaciones, i_amanecer, i_atardecer, titulo = _curva_solar(latitud, longitud, zona, hoy.date())
    i_cenit = int(np.argmax(elevaciones))
    i_ahora = hoy.hour * 60 + hoy.minute

    # La curva, cada 5 min (con minuto a minuto el gráfico pesa 5 veces más). El eje es de categorías ("HH:MM"):
    # se incluyen los minutos de los marcadores para que no aparezcan como categorías nuevas al final del eje
    indices = sorted(set(range(0, 1440, 5)) | {i_amanecer, i_atardecer, i_cenit, i_ahora})
    x, curva = [etiquetas[i] for i in indices], elevaciones[indices]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=np.where(curva >= 0, curva, 0), mode="lines", fill="tozeroy",
        fillcolor="rgba(217, 119, 6, 0.18)", line=dict(color=AMBAR, width=2.5), name="Día", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=np.where(curva <= 0, curva, 0), mode="lines", fill="tozeroy",
        fillcolor="rgba(2, 119, 189, 0.12)", line=dict(color=AZUL, width=1.5), name="Noche", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=curva, mode="lines", line=dict(color="rgba(0,0,0,0)", width=0),
        name="Elevación solar",
        hovertemplate="Hora: <b>%{x}</b><br>Elevación solar: <b>%{y:.1f}°</b><extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#a89f91", line_width=1)

    fig.add_trace(go.Scatter(
        x=[etiquetas[i_ahora]], y=[elevaciones[i_ahora]], mode="markers+text",
        marker=dict(size=12, color=AZUL, symbol="circle", line=dict(width=2, color="white")),
        text=[f"<b>Ahora ({elevaciones[i_ahora]:.1f}°)</b>"], textposition="top center",
        textfont=dict(color=AZUL, size=11, family=FUENTE), name="Ahora",
        hovertemplate="Actual (%{x}): <b>%{y:.1f}°</b><extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[etiquetas[i_amanecer], etiquetas[i_cenit], etiquetas[i_atardecer]],
        y=[0, elevaciones[i_cenit], 0], mode="markers+text",
        marker=dict(size=9, color=[AMBAR, ROJO, "#ea580c"]),
        text=[f"<b>Amanecer {etiquetas[i_amanecer]}</b>",
              f"<b>Cénit {etiquetas[i_cenit]} ({elevaciones[i_cenit]:.1f}°)</b>",
              f"<b>Atardecer {etiquetas[i_atardecer]}</b>"],
        textposition=["bottom center", "top center", "bottom center"],
        textfont=dict(color=TEXTO, size=10.5, family=FUENTE), showlegend=False,
        hovertemplate="<b>%{x}</b> (%{y:.1f}°)<extra></extra>",
    ))

    tema_plotly(fig, titulo, "Elevación (°)", leyenda=False)
    fig.update_xaxes(tickvals=[etiquetas[i] for i in range(0, 1440, 120)], tickfont=dict(size=11, color=TEXTO))
    return fig
