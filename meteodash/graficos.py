"""Gráficos Plotly comunes a todas las páginas."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytz
from astral import LocationInfo
from astral.sun import elevation, sun
from plotly.subplots import make_subplots

from .estilo import AMBAR, AZUL, FUENTE, ROJO, TEXTO, tema_plotly

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIAS_LARGOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

OBSERVADO = "Observado"  # columna que añade ciudad.py con los datos de AEMET


def dia_semana(fecha, largo=False):
    fecha = pd.Timestamp(fecha)
    nombres = DIAS_LARGOS if largo else DIAS
    return f"{nombres[fecha.weekday()]} {fecha.day}"


def _eje_fechas_es(fig, indice, cada_horas=6):
    """Marcas del eje temporal en español (Plotly solo trae los nombres de los días en inglés)."""

    marcas = [t for t in indice if t.hour % cada_horas == 0 and t.minute == 0]
    fig.update_xaxes(
        tickvals=marcas,
        ticktext=[f"{dia_semana(t)}<br>{t:%H:%M}" for t in marcas],
        hoverformat="%d/%m %H:%M",
    )


def _ensemble(data):
    """Todos los miembros del ensemble, incluido el control."""
    return data.drop(columns=OBSERVADO, errors="ignore")


def _miembros(fig, data, color):
    # El control se dibuja aparte, destacado
    for columna in _ensemble(data).columns.drop("Ctrl", errors="ignore"):
        fig.add_trace(go.Scatter(
            x=data.index, y=data[columna], mode="lines",
            line=dict(color=color, width=1),
            name=f"Miembro {columna}", showlegend=False, hoverinfo="skip",
        ))


def _control(fig, data, color, formato, unidad):
    if "Ctrl" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Ctrl"], mode="lines",
            line=dict(color=color, width=2.5, dash="dash"),
            name="Control",
            hovertemplate=f"Control: <b>%{{y:{formato}}} {unidad}</b><extra></extra>",
        ))


def _observado(fig, data, formato, unidad, etiqueta="Observado"):
    if OBSERVADO in data.columns and data[OBSERVADO].notna().any():
        fig.add_trace(go.Scatter(
            x=data.index, y=data[OBSERVADO], mode="lines",
            line=dict(color=TEXTO, width=3),
            name="Observado",
            hovertemplate=f"{etiqueta}: <b>%{{y:{formato}}} {unidad}</b><extra></extra>",
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
        name="Media Ens",
        customdata=np.stack([ens.quantile(0.1, axis=1), ens.quantile(0.9, axis=1)], axis=-1),
        hovertemplate="Media Ens: <b>%{y:.1f}°C</b><br>Rango 10-90%: <b>%{customdata[0]:.1f}° - %{customdata[1]:.1f}°C</b><extra></extra>",
    ))
    _control(fig, data, AMBAR, ".1f", "°C")
    _observado(fig, data, ".1f", "°C")

    if bandas is not None and dia_bandas in bandas.index:
        x = data.index.tolist()
        for variable, nombre, relleno in [
            ("tmax", "Rango Máx Habitual", "rgba(217, 56, 86, 0.1)"),
            ("tmin", "Rango Mín Habitual", "rgba(2, 119, 189, 0.1)"),
        ]:
            bajo = bandas.loc[dia_bandas, (variable, 0.15)]
            alto = bandas.loc[dia_bandas, (variable, 0.85)]
            fig.add_trace(go.Scatter(
                x=x + x[::-1], y=[alto] * len(x) + [bajo] * len(x),
                fill="toself", fillcolor=relleno, line=dict(color="rgba(0,0,0,0)"),
                name=nombre, hoverinfo="skip",
            ))

    _extremos_diarios(fig, ens.mean(axis=1), ".1f", "º")
    tema_plotly(fig, "Previsión de Temperaturas (48h)", "Temperatura (°C)")
    _eje_fechas_es(fig, data.index)
    return fig


def lluvia(prec_data):
    """Probabilidad de lluvia (miembros con precipitación) y cantidad media cuando llueve."""

    llueve = prec_data != 0
    probabilidad = 100 * llueve.sum(axis=1) / len(prec_data.columns)
    media = prec_data.where(llueve).mean(axis=1).fillna(0).round(1)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5], vertical_spacing=0.1)
    fig.add_trace(go.Scatter(
        x=media.index, y=media, mode="lines+markers", fill="tozeroy",
        fillcolor="rgba(2, 119, 189, 0.12)", name="Media (L/m²)",
        line=dict(color=AZUL, width=2), marker=dict(size=4),
        hovertemplate="Lluvia media: <b>%{y} L/m²</b><extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=probabilidad.index, y=probabilidad, name="Probabilidad (%)",
        marker=dict(color=AMBAR, line=dict(color="rgba(0,0,0,0.05)", width=1)),
        hovertemplate="Probabilidad: <b>%{y:.0f}%</b><extra></extra>",
    ), row=2, col=1)

    tema_plotly(fig, "Previsión de Lluvia (48h)", leyenda=False)
    ejes = dict(showgrid=True, gridcolor="rgba(60, 50, 40, 0.12)", linecolor="rgba(60, 50, 40, 0.25)", color=TEXTO,
                tickfont=dict(color=TEXTO, family=FUENTE, size=11))
    fig.update_xaxes(range=[media.index.min(), media.index.max()], **ejes)
    fig.update_yaxes(title_text="L/m²", title_font=dict(color=TEXTO, size=11, family=FUENTE), rangemode="tozero", row=1, col=1, **ejes)
    fig.update_yaxes(title_text="Probabilidad %", title_font=dict(color=TEXTO, size=11, family=FUENTE), range=[0, 105], row=2, col=1, **ejes)
    _eje_fechas_es(fig, media.index)
    return fig


def viento(data):
    fig = go.Figure()
    _miembros(fig, data, "rgba(217, 119, 6, 0.22)")
    fig.add_trace(go.Scatter(
        x=data.index, y=_ensemble(data).mean(axis=1), mode="lines",
        line=dict(color="#b45309", width=1.5, dash="dot"),
        name="Media Ens", hovertemplate="Media Ens: <b>%{y:.0f} km/h</b><extra></extra>",
    ))
    _control(fig, data, AMBAR, ".0f", "km/h")
    _observado(fig, data, ".0f", "km/h", etiqueta="Racha observada")
    _extremos_diarios(fig, _ensemble(data).mean(axis=1), ".0f")
    tema_plotly(fig, "Previsión de Viento (Rachas) (48h)", "Velocidad (km/h)")
    _eje_fechas_es(fig, data.index)
    return fig


def presion(data):
    fig = go.Figure()
    _miembros(fig, data, "rgba(99, 91, 83, 0.22)")
    fig.add_trace(go.Scatter(
        x=data.index, y=_ensemble(data).mean(axis=1), mode="lines",
        line=dict(color="#635b53", width=1.5, dash="dot"),
        name="Media Ens", hovertemplate="Media Ens: <b>%{y:.1f} hPa</b><extra></extra>",
    ))
    _control(fig, data, AMBAR, ".1f", "hPa")
    tema_plotly(fig, "Previsión de Presión Atmosférica (48h)", "Presión (hPa)")
    fig.update_layout(yaxis=dict(range=[980, 1040]))
    _eje_fechas_es(fig, data.index)
    return fig


def mucape(data):
    fig = go.Figure()
    ens = _ensemble(data)
    _miembros(fig, data, "rgba(225, 29, 72, 0.2)")
    fig.add_trace(go.Scatter(
        x=data.index, y=ens.mean(axis=1), mode="lines",
        line=dict(color=AMBAR, width=1.5, dash="dot"),
        name="Media Ens", customdata=ens.max(axis=1),
        hovertemplate="Media CAPE: <b>%{y:.0f} J/kg</b><br>Máx Ens: <b>%{customdata:.0f} J/kg</b><extra></extra>",
    ))
    _control(fig, data, ROJO, ".0f", "J/kg")

    # Zonas de riesgo (muy sutiles)
    fig.add_hrect(y0=0, y1=300, fillcolor="#10b981", opacity=0.04, line_width=0, layer="below")
    fig.add_hrect(y0=300, y1=1000, fillcolor="#fbbf24", opacity=0.04, line_width=0, layer="below")
    fig.add_hrect(y0=1000, y1=3000, fillcolor="#ef4444", opacity=0.04, line_width=0, layer="below")

    tema_plotly(fig, "Potencial de Tormentas (MUCAPE) (48h)", "J/kg")
    _eje_fechas_es(fig, data.index)
    return fig


# ---------------------------------------------------------------- Multimodelo Open-Meteo (semana)

def _valor_referencia(valores):
    """ECMWF si está disponible; si no, la media de los modelos."""

    if "ECMWF" in valores.index and not pd.isna(valores["ECMWF"]):
        return valores["ECMWF"]
    return valores.mean()


def _resumen_hover(fig, x, columnas, plantilla):
    if x:
        fig.add_trace(go.Scatter(
            x=x, y=columnas[0], mode="markers",
            marker=dict(size=0.1, color="rgba(0,0,0,0)"),
            showlegend=False, customdata=np.stack(columnas, axis=-1), hovertemplate=plantilla,
        ))


def _dias_completos(df):
    """Agrupa por día descartando los días a los que les falta alguna hora."""

    por_dia = df.groupby(df.index.date)
    completos = por_dia.apply(lambda g: g.notnull().all())
    return por_dia, completos


def semana_temperatura(temp_df):
    por_dia, completos = _dias_completos(temp_df)
    maximas = (por_dia.max() * completos[completos]).dropna(how="all")
    minimas = (por_dia.min() * completos[completos]).dropna(how="all")

    fig = go.Figure()
    resumen = {k: [] for k in ["x", "max", "max20", "max80", "min", "min20", "min80"]}

    for i, fecha in enumerate(minimas.index[:8]):
        dia_min = minimas.loc[fecha].dropna()
        dia_max = maximas.loc[fecha].dropna() if fecha in maximas.index else pd.Series(dtype=float)
        if dia_min.empty or dia_max.empty:
            continue
        etiqueta = dia_semana(fecha, largo=True)

        for valores, nombre, color, relleno, grupo in [
            (dia_min, "Mínima", "#0284c7", "rgba(2, 132, 199, 0.15)", "A"),
            (dia_max, "Máxima", ROJO, "rgba(217, 56, 86, 0.15)", "B"),
        ]:
            fig.add_trace(go.Box(
                y=valores, x=[etiqueta] * len(valores), name=nombre,
                marker_color=color, line_color=color, fillcolor=relleno,
                boxpoints="outliers", offsetgroup=grupo, showlegend=(i == 0),
                width=0.35, line_width=2, hoverinfo="skip",
            ))

        ref_max, ref_min = _valor_referencia(dia_max), _valor_referencia(dia_min)
        resumen["x"].append(etiqueta)
        resumen["max"].append(ref_max)
        resumen["max20"].append(dia_max.quantile(0.2))
        resumen["max80"].append(dia_max.quantile(0.8))
        resumen["min"].append(ref_min)
        resumen["min20"].append(dia_min.quantile(0.2))
        resumen["min80"].append(dia_min.quantile(0.8))

        fig.add_annotation(x=etiqueta, y=ref_min, text=f"<b>{ref_min:.1f}º</b>", showarrow=False, yshift=-15,
                           font=dict(color="#0284c7", size=10.5, family=FUENTE))
        fig.add_annotation(x=etiqueta, y=ref_max, text=f"<b>{ref_max:.1f}º</b>", showarrow=False, yshift=15,
                           font=dict(color=ROJO, size=10.5, family=FUENTE))

    _resumen_hover(
        fig, resumen["x"],
        [resumen[k] for k in ["max", "max20", "max80", "min", "min20", "min80"]],
        "<b>Máxima:</b> <b>%{customdata[0]:.1f}°C</b> (20-80%: %{customdata[1]:.1f}° - %{customdata[2]:.1f}°C)<br>"
        "<b>Mínima:</b> <b>%{customdata[3]:.1f}°C</b> (20-80%: %{customdata[4]:.1f}° - %{customdata[5]:.1f}°C)<extra></extra>",
    )
    tema_plotly(fig, "Evolución Temperaturas (Próxima Semana)", "Temperatura (°C)")
    fig.update_layout(boxmode="group")
    return fig


def _semana_acumulada(diario, titulo, titulo_y, nombre, color, relleno, formato, unidad, umbral_etiqueta=None):
    fig = go.Figure()
    x, ref, p20, p80 = [], [], [], []

    for fecha, valores in diario.iterrows():
        valores = valores.dropna()
        if valores.empty:
            continue
        etiqueta = dia_semana(fecha, largo=True)
        fig.add_trace(go.Box(
            y=valores, x=[etiqueta] * len(valores), name=nombre,
            marker_color=color, line_color=color, fillcolor=relleno,
            boxpoints="all", showlegend=False, width=0.45, line_width=2, hoverinfo="skip",
        ))
        valor = _valor_referencia(valores)
        x.append(etiqueta)
        ref.append(valor)
        p20.append(valores.quantile(0.2))
        p80.append(valores.quantile(0.8))

        if umbral_etiqueta is None or valor > umbral_etiqueta:
            fig.add_annotation(x=etiqueta, y=valor, text=f"<b>{valor:{formato}} {unidad}</b>", showarrow=False,
                               yshift=14, font=dict(color=color, size=10.5, family=FUENTE))

    _resumen_hover(
        fig, x, [ref, p20, p80],
        f"ECMWF/Media: <b>%{{customdata[0]:{formato}}} {unidad}</b> "
        f"(20-80%: %{{customdata[1]:{formato}}} - %{{customdata[2]:{formato}}} {unidad})<extra></extra>",
    )
    tema_plotly(fig, titulo, titulo_y)
    fig.update_layout(boxmode="group")
    return fig


def semana_lluvia(prec_df):
    diario = prec_df.groupby(prec_df.index.date).sum(min_count=1).dropna(how="all")
    return _semana_acumulada(diario, "Evolución Precipitación Diaria (Próxima Semana)", "Lluvia Acumulada (L/m²)",
                             "Acumulado Lluvia", "#0284c7", "rgba(2, 132, 199, 0.15)", ".1f", "L/m²", umbral_etiqueta=0.1)


def semana_viento(rachas_df):
    diario = rachas_df.groupby(rachas_df.index.date).max().dropna(how="all")
    return _semana_acumulada(diario, "Evolución Viento Rachas (Próxima Semana)", "Racha Máxima (km/h)",
                             "Racha Máxima", "#ea580c", "rgba(234, 88, 12, 0.15)", ".0f", "km/h")


# ---------------------------------------------------------------- GEFS (15 días)

def gefs(temp_gefs):
    """Máximas y mínimas diarias del GFS determinista con la envolvente del ensemble GEFS."""

    maximas = temp_gefs.resample("D").max()
    minimas = temp_gefs.resample("D").min()

    # Se excluye el día de hoy, que está incompleto
    hoy = pd.Timestamp.now(tz=maximas.index.tz).normalize()
    maximas, minimas = maximas[maximas.index > hoy], minimas[minimas.index > hoy]

    miembros = [c for c in temp_gefs.columns if c != "GFS"]
    x = [dia_semana(f) for f in maximas.index]

    fig = go.Figure()
    for diario, nombre, relleno in [
        (maximas, "Rango Ens. Máxima", "rgba(217, 56, 86, 0.15)"),
        (minimas, "Rango Ens. Mínima", "rgba(2, 132, 199, 0.15)"),
    ]:
        fig.add_trace(go.Scatter(x=x, y=diario[miembros].max(axis=1), mode="lines", line=dict(width=0),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=x, y=diario[miembros].min(axis=1), mode="lines", fill="tonexty",
                                 fillcolor=relleno, line=dict(width=0), name=nombre, hoverinfo="skip"))

    for diario, nombre, color, posicion in [
        (maximas, "GFS Máxima", ROJO, "top center"),
        (minimas, "GFS Mínima", "#0284c7", "bottom center"),
    ]:
        fig.add_trace(go.Scatter(
            x=x, y=diario["GFS"], mode="lines+markers+text",
            line=dict(color=color, width=2.5), marker=dict(size=6),
            text=[f"<b>{t:.1f}º</b>" for t in diario["GFS"]], textposition=posicion,
            textfont=dict(color=color, size=11, family=FUENTE),
            name=nombre, hovertemplate=f"{nombre}: <b>%{{y:.1f}}°C</b><extra></extra>",
        ))

    tema_plotly(fig, "Previsión GEFS Temperaturas Diarias (15 días)", "Temperatura (°C)")
    return fig


# ---------------------------------------------------------------- Histórico y sol

def historico_vs_prevision(datos, dia, hoy, mañana):
    """Temperaturas registradas un día como hoy frente a la previsión de hoy y mañana.

    `hoy` y `mañana` son tuplas (mínima, máxima).
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
        fig.add_trace(go.Scatter(
            x=["Mínima", "Máxima"], y=[minima, maxima], mode="markers+text",
            name=f"Prev. {nombre}",
            marker=dict(size=16, color=color, line=dict(width=2, color="white"), symbol=simbolo),
            text=[f"<b>{nombre}: {minima}º</b>", f"<b>{nombre}: {maxima}º</b>"], textposition=posicion,
            textfont=dict(color=TEXTO, size=11, family=FUENTE),
            hovertemplate=f"<b>Previsión {nombre} (%{{x}}): %{{y:.1f}}°C</b><extra></extra>",
        ))

    tema_plotly(fig, "", "Temperatura (°C)", hovermode="closest")
    fig.update_layout(xaxis=dict(showgrid=False))
    return fig


def elevacion_solar(latitud, longitud, zona="UTC"):
    location = LocationInfo("Ubicación", "Región", zona, latitud, longitud)
    timezone = pytz.timezone(zona)
    hoy = datetime.now(tz=timezone)

    sol_hoy = sun(location.observer, date=hoy, tzinfo=timezone)
    sol_ayer = sun(location.observer, date=hoy - timedelta(days=1), tzinfo=timezone)
    amanecer, atardecer = sol_hoy["sunrise"], sol_hoy["sunset"]

    diferencia = (atardecer - amanecer).total_seconds() - (sol_ayer["sunset"] - sol_ayer["sunrise"]).total_seconds()
    dif_min, dif_seg = divmod(abs(int(diferencia)), 60)
    cambio = f"{dif_min} m {dif_seg} s {'ganados' if diferencia > 0 else 'perdidos'}"

    duracion = (atardecer - amanecer).total_seconds()
    horas_dia, minutos_dia = int(duracion // 3600), int((duracion % 3600) / 60)

    minutos = [timezone.localize(datetime(hoy.year, hoy.month, hoy.day, h, m)) for h in range(24) for m in range(60)]
    elevaciones = np.array([elevation(location.observer, dt) for dt in minutos])
    etiquetas = [dt.strftime("%H:%M") for dt in minutos]

    i_amanecer = amanecer.hour * 60 + amanecer.minute
    i_atardecer = atardecer.hour * 60 + atardecer.minute
    i_cenit = int(np.argmax(elevaciones))
    i_ahora = hoy.hour * 60 + hoy.minute

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=etiquetas, y=np.where(elevaciones >= 0, elevaciones, 0), mode="lines", fill="tozeroy",
        fillcolor="rgba(217, 119, 6, 0.18)", line=dict(color=AMBAR, width=2.5), name="Día", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=etiquetas, y=np.where(elevaciones <= 0, elevaciones, 0), mode="lines", fill="tozeroy",
        fillcolor="rgba(2, 119, 189, 0.12)", line=dict(color=AZUL, width=1.5), name="Noche", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=etiquetas, y=elevaciones, mode="lines", line=dict(color="rgba(0,0,0,0)", width=0),
        name="Elevación Solar",
        hovertemplate="Hora: <b>%{x}</b><br>Elevación Solar: <b>%{y:.1f}°</b><extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#a89f91", line_width=1)

    fig.add_trace(go.Scatter(
        x=[etiquetas[i_ahora]], y=[elevaciones[i_ahora]], mode="markers+text",
        marker=dict(size=12, color=AZUL, symbol="circle", line=dict(width=2, color="white")),
        text=[f"<b>Posición Actual ({elevaciones[i_ahora]:.1f}°)</b>"], textposition="top center",
        textfont=dict(color=AZUL, size=11, family=FUENTE), name="Posición Actual",
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
        hovertemplate="Hito Solar: <b>%{x}</b> (%{y:.1f}°)<extra></extra>",
    ))

    tema_plotly(fig, f"Perfil de Elevación Solar | Duración del día: {horas_dia}h {minutos_dia}m ({cambio})",
                "Elevación (°)", leyenda=False)
    fig.update_xaxes(tickvals=[etiquetas[i] for i in range(0, 1440, 120)], tickfont=dict(size=11, color=TEXTO))
    return fig
