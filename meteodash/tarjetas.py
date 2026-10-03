"""Tarjetas de métricas, avisos y tabla de récords (HTML con las clases de estilo.CSS)."""

from html import escape

import pandas as pd
import streamlit as st

from .avisos import NIVELES, TIPOS
from .estilo import AZUL, ROJO
from .graficos import dia_semana

TEXTO_PERCENTIL = (
    "El percentil indica cómo es la temperatura frente a los registros históricos: un valor cercano a 100 "
    "indica un registro extremadamente alto y uno cercano a 0, extremadamente bajo."
)

SVG = {
    "calor": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
    "frio": '<line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/><path d="M20 12h-8M4 12h8M12 4v8M12 20v-8M16.39 8.39l-6.39 6.39M7.61 15.61l6.39-6.39M16.39 15.61L10 10M7.61 8.39L14 14"/>',
    "sube": '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    "baja": '<polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/>',
}


def tono_temperatura(t):
    """Tono HSL según la temperatura: -10 ºC azul (240) ... 45 ºC rojo (0)."""

    if pd.isna(t):
        return 220
    return int(240 * (1 - max(0, min(1, (t + 10) / 55))))


def _html(contenido, destino=st):
    # Sin sangría: Markdown trataría las líneas sangradas como bloque de código
    destino.markdown("\n".join(linea.strip() for linea in contenido.splitlines()), unsafe_allow_html=True)


def _grados(t):
    return "–" if t is None or pd.isna(t) else f"{t}º"


def _delta(valor, nota):
    if pd.isna(valor):
        return ""
    if valor == 0:
        return f'<div class="metric-delta" style="color: #635b53">= 0º <span class="nota">{nota}</span></div>'
    color = ROJO if valor > 0 else AZUL
    flecha = "▲" if valor > 0 else "▼"
    return f'<div class="metric-delta" style="color: {color}">{flecha} {abs(valor)}º <span class="nota">{nota}</span></div>'


def principales(temp_mañana, fiabilidad, temp_actual=None, temp_ayer=None):
    """Temperatura actual (si hay observación), la de mañana a esta hora y la fiabilidad del ensemble."""

    tarjetas = ""
    if temp_actual is not None:
        tarjetas += f"""
        <div class="metric-card temp-card" style="--card-hue: {tono_temperatura(temp_actual)};">
        <div class="metric-label">Actual</div>
        <div class="metric-value">{_grados(temp_actual)}</div>
        {_delta(round(float(temp_actual - temp_ayer), 1), "vs ayer")}
        </div>"""

    delta_mañana = _delta(round(float(temp_mañana - temp_actual), 1), "previsto") if temp_actual is not None else ""
    tarjetas += f"""
    <div class="metric-card temp-card" style="--card-hue: {tono_temperatura(temp_mañana)};">
    <div class="metric-label">Mañana a esta hora</div>
    <div class="metric-value">{_grados(temp_mañana)}</div>
    {delta_mañana}
    </div>
    <div class="metric-card static-card" title="Coincidencia entre los miembros del ensemble para la temperatura de mañana a esta hora">
    <div class="metric-label">Fiabilidad</div>
    <div class="metric-value">{fiabilidad}<span class="unidad"> / 10</span></div>
    <div class="progress-bg"><div class="progress-fill" style="width: {fiabilidad * 10}%;"></div></div>
    </div>"""

    _html(f'<div class="weather-grid">{tarjetas}</div>')


def extremos(tarjetas):
    """Máximas y mínimas previstas. Cada tarjeta: dict(label, temp, perc=None, horas=None).

    `horas` indica que el día no está completo en los datos ("17-23 h"): se muestra junto a la etiqueta.
    """

    html = ""
    for tarjeta in tarjetas:
        percentil = tarjeta.get("perc")
        barra, titulo = "", ""
        etiqueta = tarjeta["label"]
        if tarjeta.get("horas"):
            etiqueta += f' <span style="text-transform: none; opacity: 0.7">({tarjeta["horas"]})</span>'
            titulo = ' title="El pase del modelo no cubre el día entero: el valor solo tiene en cuenta estas horas"'
        if percentil is not None and not pd.isna(percentil):
            valor = int(round(percentil))
            # El degradado se escala a la inversa para que no se comprima con barras cortas
            tamaño_fondo = 100 / max(1, valor) * 100
            barra = f"""
            <div class="perc-row">
            <div class="perc-text">{valor}<span>perc</span></div>
            <div class="perc-track"><div class="perc-fill" style="width: {valor}%; background-size: {tamaño_fondo:.0f}% 100%;"></div></div>
            </div>"""
            titulo = f' title="{TEXTO_PERCENTIL}"'

        html += f"""
        <div class="metric-card temp-card" style="--card-hue: {tono_temperatura(tarjeta['temp'])};"{titulo}>
        <div class="metric-label">{etiqueta}</div>
        <div class="metric-value">{_grados(tarjeta['temp'])}</div>
        {barra}
        </div>"""

    _html(f'<div class="weather-grid">{html}</div>')


def condiciones(tarjetas):
    """Tarjetas compactas. Cada una: dict(label, valor, unidad="", nota="", title="", color=None).

    `color` pinta un borde superior (p. ej. el de la categoría de calidad del aire).
    """

    html = ""
    for t in tarjetas:
        estilo = f' style="border-top: 4px solid {t["color"]};"' if t.get("color") else ""
        titulo = f' title="{t["title"]}"' if t.get("title") else ""
        unidad = f'<span class="unidad"> {t["unidad"]}</span>' if t.get("unidad") else ""
        nota = f'<div class="metric-nota">{t["nota"]}</div>' if t.get("nota") else ""
        html += f"""
        <div class="metric-card static-card"{estilo}{titulo}>
        <div class="metric-label">{t["label"]}</div>
        <div class="metric-value">{t["valor"]}{unidad}</div>
        {nota}
        </div>"""

    _html(f'<div class="weather-grid compacta">{html}</div>')


def comentario_predictores(textos, lugar, ahora):
    """Comentario de los predictores de AEMET (ver aemet_opendata.get_comentario_aemet), con una pestaña por día.

    Solo se muestran los textos de hoy en adelante: el de "hoy" de AEMET a veces no se renueva y llega caducado.
    """

    hoy = ahora.normalize().tz_localize(None)
    vigentes = sorted((t for t in textos if t["fecha"] >= hoy), key=lambda t: t["fecha"])
    if not vigentes:
        return False

    def nombre(fecha):
        dia = {0: "Hoy", 1: "Mañana", 2: "Pasado mañana"}.get((fecha - hoy).days)
        return f"{dia} · {dia_semana(fecha)}" if dia else dia_semana(fecha, largo=True)

    st.markdown(f"**Comentario de los predictores de AEMET · {lugar}**")
    with st.container(border=True):
        for pestaña, texto in zip(st.tabs([nombre(t["fecha"]) for t in vigentes]), vigentes):
            with pestaña:
                st.caption(f"Elaborado {_momento(texto['elaborado'], ahora)} h")
                for titulo, cuerpo in texto["secciones"]:
                    st.markdown(f"**{titulo}**")
                    st.markdown(cuerpo)
    return True


def _momento(t, ahora):
    hoy = ahora.normalize().tz_localize(None)
    dia = t.tz_localize(None).normalize()
    nombre = {0: "hoy", 1: "mañana"}.get((dia - hoy).days, dia_semana(t).lower())
    return f"{nombre} {t:%H:%M}"


def avisos_oficiales(lista, ahora):
    """Avisos de Meteoalarm (ver avisos.avisos_vigentes), con el intervalo en hora local."""

    if not lista:
        return False

    html = ""
    for aviso in lista:
        nombre, color = NIVELES[aviso["nivel"]]
        inicio, fin = aviso["inicio"].tz_convert(ahora.tz), aviso["fin"].tz_convert(ahora.tz)
        if inicio <= ahora:
            periodo = f"hasta {_momento(fin, ahora)}"
        elif inicio.date() == fin.date():
            periodo = f"{_momento(inicio, ahora)}–{fin:%H:%M}"
        else:
            periodo = f"{_momento(inicio, ahora)} – {_momento(fin, ahora)}"
        fenomeno, emoji = TIPOS.get(aviso["tipo"], ("fenómenos adversos", "⚠️"))
        # Todo en una línea: _html recorta cada línea y Markdown rompería el bloque con los saltos del texto
        detalle = "<br>".join(escape(linea.strip()) for linea in aviso["descripcion"].splitlines() if linea.strip())
        detalle = f'<span class="alert-detalle">{detalle}</span>' if detalle else ""
        html += (f'<div class="alert-item alert-oficial" style="--aviso: {color};">'
                 f'<span class="alert-emoji">{emoji}</span>'
                 f'<span class="alert-text"><b>Aviso {nombre}</b> por {fenomeno}'
                 f'<span class="alert-periodo">{periodo}</span>{detalle}</span></div>')

    _html(f'<div class="alerts-container oficiales">{html}</div>')
    return True


def avisos(perc_max_hoy, perc_max_mañana):
    """Avisos de calor o frío anómalos según los percentiles históricos de las máximas (None: sin dato)."""

    lista = []
    for percentil, dia in [(perc_max_hoy, "Hoy"), (perc_max_mañana, "Mañana")]:
        if percentil is None:
            continue
        if percentil > 80:
            lista.append(("calor", "calor", f"{dia} hará mucho calor"))
        elif percentil < 20:
            lista.append(("frio", "frio", f"{dia} hará mucho frío"))

    if perc_max_hoy is not None and perc_max_mañana is not None:
        if perc_max_mañana - perc_max_hoy > 50:
            lista.append(("calor", "sube", "Mañana subirán mucho las temperaturas"))
        elif perc_max_hoy - perc_max_mañana > 50:
            lista.append(("frio", "baja", "Mañana bajarán mucho las temperaturas"))

    if not lista:
        return False

    html = ""
    for tipo, icono, texto in lista:
        clase = "alert-warm" if tipo == "calor" else "alert-cold"
        svg = (f'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" '
               f'stroke-linecap="round" stroke-linejoin="round">{SVG[icono]}</svg>')
        html += f'<div class="alert-item {clase}"><span class="alert-icon-container">{svg}</span><span class="alert-text">{texto}</span></div>'

    _html(f'<div class="alerts-container">{html}</div>')
    return True


def records(del_dia, prob_lluvia=None):
    """Tabla de récords del día en el sidebar a partir de las filas históricas de ese día del año.

    Debajo, el día más lluvioso y `prob_lluvia`: % de días con lluvia en estas fechas.
    """

    def celda(columna, funcion, clase):
        serie = del_dia[columna].dropna()
        if serie.empty:
            return f'<td class="{clase}">–</td>'
        fecha = serie.idxmax() if funcion == "max" else serie.idxmin()
        return f'<td class="{clase}">{serie[fecha]}º <span style="font-size: 0.85em; opacity: 0.5;">({fecha.year})</span></td>'

    st.sidebar.markdown("### Récords para hoy")
    _html(f"""
    <table class="records-table">
    <thead><tr><th>Récord</th><th>T. Máx</th><th>T. Mín</th></tr></thead>
    <tbody>
    <tr><td>Calor</td>{celda("tmax", "max", "temp-max")}{celda("tmin", "max", "temp-min")}</tr>
    <tr><td>Frío</td>{celda("tmax", "min", "temp-max")}{celda("tmin", "min", "temp-min")}</tr>
    </tbody>
    </table>
    """, destino=st.sidebar)

    lineas = []
    lluvia = del_dia["prec"].dropna() if "prec" in del_dia else pd.Series(dtype=float)
    if not lluvia.empty and lluvia.max() > 0:
        lineas.append(f"Día más lluvioso: <b>{lluvia.max():.1f} L/m²</b> ({lluvia.idxmax().year})")
    if prob_lluvia is not None:
        lineas.append(f"Llueve (≥ 1 L/m²) el <b>{prob_lluvia:.0f} %</b> de los días en estas fechas")
    if lineas:
        _html(f'<p class="records-nota">{"<br>".join(lineas)}</p>', destino=st.sidebar)
