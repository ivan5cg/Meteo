"""Datos de ahora, hoy y mañana, avisos y tabla de récords (HTML con las clases de estilo.CSS)."""

from html import escape

import numpy as np
import pandas as pd
import streamlit as st

from .aemet_opendata import MESES, NIVELES_ALUDES
from .avisos import NIVELES, TIPOS
from .estilo import AMBAR, AZUL, ROJO, coma
from .graficos import dia_semana
from .luna import rumbo

TEXTO_PERCENTIL = "Percentil frente a los registros de este día: 0, la más baja; 100, la más alta."

# (desde, nivel, color) de la fiabilidad del ensemble
NIVELES_FIABILIDAD = [(7, "alta", "#059669"), (4, "media", AMBAR), (0, "baja", ROJO)]

# Códigos WMO del tiempo de Open-Meteo: (hasta, emoji, texto)
TIEMPO_WMO = [
    (0, "☀️", "Despejado"), (1, "🌤️", "Poco nuboso"), (2, "⛅", "Nubes y claros"), (3, "☁️", "Cubierto"),
    (48, "🌫️", "Niebla"), (57, "🌦️", "Llovizna"), (65, "🌧️", "Lluvia"), (67, "🌧️", "Lluvia helada"),
    (77, "🌨️", "Nieve"), (82, "🌦️", "Chubascos"), (86, "🌨️", "Chubascos de nieve"), (99, "⛈️", "Tormenta"),
]

SVG = {
    "calor": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
    "frio": '<line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/><path d="M20 12h-8M4 12h8M12 4v8M12 20v-8M16.39 8.39l-6.39 6.39M7.61 15.61l6.39-6.39M16.39 15.61L10 10M7.61 8.39L14 14"/>',
    "sube": '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    "baja": '<polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/>',
    # Iconos de las etiquetas de los datos (ver dato), del mismo trazo
    "termometro": '<path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>',
    "gota": '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
    "nube": '<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>',
    "capas": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/>'
             '<polyline points="2 12 12 17 22 12"/>',
    "olas": "".join(f'<path d="M2 {y}c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>'
                    for y in (6, 12, 18)),
    "hoja": '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/>'
            '<path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
}


def tono_temperatura(t):
    """Tono HSL según la temperatura: -10 ºC azul (240) ... 45 ºC rojo (0)."""

    if pd.isna(t):
        return 220
    return int(240 * (1 - max(0, min(1, (t + 10) / 55))))


def _html(contenido, destino=st):
    # Sin sangría: Markdown trataría las líneas sangradas como bloque de código
    destino.markdown("\n".join(linea.strip() for linea in contenido.splitlines()), unsafe_allow_html=True)


def _icono(nombre, tamaño=14):
    return (f'<svg class="icono" viewBox="0 0 24 24" width="{tamaño}" height="{tamaño}" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{SVG[nombre]}</svg>')


def _columnas(n, maximo):
    """Columnas para repartir `n` datos en filas equilibradas de como mucho `maximo`: 5 de 3 en 3 -> 3 + 2; 4 -> 2 + 2."""

    return -(-n // -(-n // maximo))


def _datos(celdas):
    """Rejilla de datos en filas equilibradas: como mucho 3 por fila en el móvil, 4 en pantallas medianas y 6 en las
    anchas (consultas de contenedor de estilo.CSS)."""

    columnas = "; ".join(f"--c{i}: {_columnas(len(celdas), maximo)}" for i, maximo in enumerate((3, 4, 6), 1))
    return f'<div class="datos" style="{columnas}">{"".join(celdas)}</div>'


def _grados(t):
    return "–" if t is None or pd.isna(t) else f"{coma(t)}º"


def _delta(valor):
    """Diferencia de temperatura con flecha: roja si sube, azul si baja."""

    valor = round(float(valor), 1)
    if valor == 0:
        return '<span class="delta">= 0º</span>'
    clase, flecha = ("sube", "▲") if valor > 0 else ("baja", "▼")
    return f'<span class="delta {clase}">{flecha} {coma(abs(valor))}º</span>'


def dato(t):
    """Un dato: dict(label, valor, unidad="", nota="", title="", color=None, icono=None).

    `color` pone un punto de ese color junto al valor (la categoría de la calidad del aire, el signo de una
    desviación...); `icono`, una clave de SVG ante la etiqueta.
    """

    titulo = f' title="{escape(t["title"])}"' if t.get("title") else ""
    icono = _icono(t["icono"]) if t.get("icono") else ""
    unidad = f'<span class="unidad"> {t["unidad"]}</span>' if t.get("unidad") else ""
    punto = f'<i class="punto" style="--color: {t["color"]}"></i>' if t.get("color") else ""
    nota = f'<div class="dato-nota">{t["nota"]}</div>' if t.get("nota") else ""
    return (f'<div class="dato"{titulo}><div class="dato-etiqueta">{icono}<span>{t["label"]}</span></div>'
            f'<div class="dato-valor">{t["valor"]}{unidad}{punto}</div>{nota}</div>')


def condiciones(tarjetas):
    """Datos en una rejilla compacta (ver dato)."""

    _html(f'<div class="rejilla" lang="es">{_datos([dato(t) for t in tarjetas])}</div>')


def _percentil(valor, minima):
    """Escala del percentil frente al histórico: de azul (de las más bajas) a rojo (de las más altas), con un punto."""

    valor = int(round(valor))
    explicacion = (f"más alta que el {valor} %" if valor >= 50 else f"más baja que el {100 - valor} %")
    titulo = f"Percentil {valor}: {explicacion} de las {'mínimas' if minima else 'máximas'} registradas este día"
    color = ROJO if valor > 60 else AZUL if valor < 40 else "#8a8178"
    return (f'<div class="percentil" title="{titulo}"><i><b style="left: {valor}%; --color: {color}"></b></i>'
            f'<span>{valor}</span></div>')


def _extremo(e):
    """Máxima o mínima prevista: dict(label, temp, perc=None, horas=None); `horas`, si el día no está completo."""

    minima = e["label"].startswith("Mín")
    titulo, debajo = "", ""
    if e.get("horas"):
        titulo = ' title="El pase del modelo no cubre el día entero: el valor solo tiene en cuenta estas horas"'
        debajo = f'<div class="dato-nota">solo {e["horas"]}</div>'
    elif e.get("perc") is not None and not pd.isna(e["perc"]):
        debajo = _percentil(e["perc"], minima)
    return (f'<div class="dato"{titulo}><div class="dato-etiqueta"><i class="marca {"min" if minima else "max"}"></i>'
            f'<span>{e["label"]}</span></div><div class="dato-valor">{_grados(e["temp"])}</div>{debajo}</div>')


def avisos_temperatura(perc_max_hoy, perc_max_mañana):
    """Calor o frío anómalos según los percentiles históricos de las máximas (None: sin dato): [(tipo, icono, texto)].

    Una subida o bajada brusca sustituye al aviso de mañana, y el mismo aviso hoy y mañana se dice una vez.
    """

    cambio = None
    if perc_max_hoy is not None and perc_max_mañana is not None:
        if perc_max_mañana - perc_max_hoy > 50:
            cambio = ("calor", "sube", "Mañana, subida brusca")
        elif perc_max_hoy - perc_max_mañana > 50:
            cambio = ("frio", "baja", "Mañana, bajada brusca")

    dias = {}
    for percentil, dia in [(perc_max_hoy, "Hoy"), (perc_max_mañana, "Mañana")]:
        if percentil is None or (dia == "Mañana" and cambio):
            continue
        if percentil > 80:
            dias.setdefault("calor", []).append(dia)
        elif percentil < 20:
            dias.setdefault("frio", []).append(dia)

    lista = [(tipo, tipo, f"{' y '.join(d).capitalize()}, muy {'cálido' if tipo == 'calor' else 'fresco'} para la fecha")
             for tipo, d in dias.items()]
    return lista + ([cambio] if cambio else [])


def panel_ahora(ahora, mañana, extremos, avisos, datos):
    """Ahora, hoy y mañana en un solo bloque, plano como el meteograma, en tres franjas: la temperatura de ahora (en
    grande) con la de mañana a esta hora y la fiabilidad; las máximas y mínimas con su percentil y los avisos de calor
    o frío (ver avisos_temperatura); y los demás datos de ahora (ver dato).

    `ahora`: dict(temp, observada, ayer=None, sensacion=None), o None; `mañana`: dict(temp, fiabilidad); `extremos`:
    ver _extremo.
    """

    cabecera = ""
    if ahora is not None:
        lineas = []
        if ahora.get("ayer") is not None and not pd.isna(ahora["ayer"]):
            lineas.append(f'{_delta(ahora["temp"] - ahora["ayer"])} vs ayer')
        if ahora.get("sensacion") is not None and not pd.isna(ahora["sensacion"]):
            lineas.append(f'Sensación <b>{ahora["sensacion"]:.0f}º</b>')
        origen = "observada" if ahora["observada"] else "prevista"
        cabecera += (f'<div class="pa-ahora"><div class="pa-etiqueta">Ahora <span>· {origen}</span></div>'
                     f'<div class="pa-temp">{_grados(ahora["temp"])}</div>'
                     + "".join(f'<div class="pa-linea">{linea}</div>' for linea in lineas) + '</div>')

    delta = f" {_delta(mañana['temp'] - ahora['temp'])}" if ahora is not None else ""
    fiabilidad = mañana["fiabilidad"]
    nivel, color = next((n, c) for limite, n, c in NIVELES_FIABILIDAD if fiabilidad >= limite)
    cabecera += (f'<div class="pa-manana"><div class="pa-etiqueta">Mañana a esta hora</div>'
                 f'<div class="pa-valor">{_grados(mañana["temp"])}{delta}</div></div>'
                 f'<div class="pa-fiabilidad" title="Acuerdo de los miembros del ensemble en la temperatura de mañana a '
                 f'esta hora: cuanto menos se separan, más fiable"><div class="pa-etiqueta">Fiabilidad</div>'
                 f'<div class="pa-valor">{coma(fiabilidad)}<small> / 10 · {nivel}</small></div>'
                 f'<div class="medidor"><b style="width: {fiabilidad * 10:.0f}%; background: {color}"></b></div></div>')
    secciones = [f'<div class="pa-cabecera{"" if ahora is not None else " sin-ahora"}">{cabecera}</div>']

    if extremos or avisos:
        seccion = _datos([_extremo(e) for e in extremos]) if extremos else ""
        if avisos:
            seccion += '<div class="pa-avisos">' + "".join(
                f'<span class="pa-aviso {tipo}">{_icono(icono)}{texto}</span>' for tipo, icono, texto in avisos) + "</div>"
        if any(e.get("perc") is not None for e in extremos):
            seccion += f'<div class="pa-nota">{TEXTO_PERCENTIL}</div>'
        secciones.append(seccion)
    if datos:
        secciones.append(_datos([dato(t) for t in datos]))

    _html('<div class="rejilla" lang="es"><section class="panel-ahora">'
          + "".join(f'<div class="pa-seccion">{s}</div>' for s in secciones) + "</section></div>")


def comentario_predictores(textos, lugar, ahora):
    """Comentario de los predictores de AEMET (ver aemet_opendata.get_comentario_aemet), con una pestaña por día.

    Solo se muestran los textos de hoy en adelante: el de "hoy" de AEMET a veces no se renueva y llega caducado.
    """

    hoy = ahora.normalize().tz_localize(None)
    vigentes = sorted((t for t in textos if t["fecha"] >= hoy), key=lambda t: t["fecha"])
    if not vigentes:
        return False

    st.markdown(f"**Comentario de los predictores de AEMET · {lugar}**")
    with st.container(border=True):
        for pestaña, texto in zip(st.tabs([_nombre_dia(t["fecha"], hoy) for t in vigentes]), vigentes):
            with pestaña:
                st.caption(f"Elaborado {_momento(texto['elaborado'], ahora)} h")
                for titulo, cuerpo in texto["secciones"]:
                    st.markdown(f"**{titulo}**")
                    st.markdown(cuerpo)
    return True


def _nombre_dia(fecha, hoy):
    """"Hoy · Sáb 31", "Mañana · Dom 1", "Pasado mañana · Lun 2" o, más adelante, "Martes 3"."""

    dia = {0: "Hoy", 1: "Mañana", 2: "Pasado mañana"}.get((fecha - hoy).days)
    return f"{dia} · {dia_semana(fecha)}" if dia else dia_semana(fecha, largo=True)


def _valor_y_unidad(texto):
    """"3300 m" -> ("3300", "m"); "NE 30 km/h" -> ("NE 30", "km/h"); "VRB 10 km/h" -> ("Var. 10", "km/h")."""

    valor, _, unidad = texto.replace("VRB", "Var.").rpartition(" ")
    return (valor, unidad) if unidad in ("m", "km/h") else (texto, "")


def prediccion_montaña(dias, lugar, ahora):
    """Predicción de montaña de AEMET (ver aemet_opendata.get_prediccion_montaña), con una pestaña por día.

    `dias`: [(días desde hoy, predicción)]. Cada día: el texto por apartados y, para hoy y mañana, la atmósfera libre
    y las temperaturas y la sensación térmica de varios puntos de la zona, de los valles a las cumbres.
    """

    hoy = ahora.normalize().tz_localize(None)
    st.markdown(f"**Predicción de montaña de AEMET · {lugar}**")
    with st.container(border=True):
        nombres = [_nombre_dia(hoy + pd.Timedelta(days=d), hoy) for d, _ in dias]
        for pestaña, (_, dia) in zip(st.tabs(nombres), dias):
            with pestaña:
                for titulo, texto in dia["apartados"]:
                    st.markdown(f"**{titulo}.** {texto}")
                if dia["atmosfera"]:
                    condiciones([{"label": titulo, "valor": valor, "unidad": unidad, "nota": "atmósfera libre"}
                                 for titulo, (valor, unidad) in ((t, _valor_y_unidad(v)) for t, v in dia["atmosfera"])])
                if dia["lugares"]:
                    filas = "".join(
                        f'<tr><td>{escape(l["nombre"])} <span class="altitud">{escape(l["altitud"])}</span></td>'
                        f'<td class="temp-min">{_grados(l["minima"])}</td><td class="temp-max">{_grados(l["maxima"])}</td>'
                        f'<td>{_grados(l["st_minima"])} / {_grados(l["st_maxima"])}</td></tr>'
                        for l in dia["lugares"])
                    _html(f'<table class="records-table tabla-lugares"><thead><tr><th>Lugar</th><th>Mín.</th>'
                          f'<th>Máx.</th><th>Sensación térmica</th></tr></thead><tbody>{filas}</tbody></table>')
        st.caption("AEMET la actualiza a diario. Atmósfera libre: lejos del relieve, sin el efecto del terreno.")


def boletin_aludes(boletin, ahora):
    """Boletín de peligro de aludes de AEMET (ver aemet_opendata.get_boletin_aludes): plegado, con el nivel más alto
    que cita en el título, si es reciente; si no, una nota (fuera de campaña AEMET no lo publica)."""

    if boletin is None:
        st.caption("No se ha podido consultar el boletín de peligro de aludes de AEMET.")
        return
    elaborado = boletin["elaborado"]
    fecha = f"{elaborado.day} de {list(MESES)[elaborado.month - 1].lower()}"
    if (ahora.tz_localize(None).normalize() - elaborado).days > 2:
        st.caption(f"AEMET no publica el boletín de peligro de aludes fuera de temporada: el último es del {fecha} de "
                   f"{elaborado.year}.")
        return

    nivel = boletin["nivel"]
    etiqueta = "Boletín de peligro de aludes de AEMET"
    if nivel is not None:
        etiqueta += f" · peligro {NIVELES_ALUDES[nivel][0]} ({nivel})"
    with st.expander(etiqueta, icon=":material/landslide:", expanded=nivel is not None and nivel >= 3):
        if nivel is not None:
            nombre, color = NIVELES_ALUDES[nivel]
            _html(f'<p class="nivel-aludes" style="--nivel: {color}">Nivel más alto que cita: <b>{nivel} · {nombre}</b> '
                  f'(escala europea de 1 a 5)</p>')
        st.caption(f"{boletin['titulo']}. Elaborado el {fecha}.")
        for parrafo in boletin["parrafos"]:
            st.markdown(escape(parrafo))


def _momento(t, ahora):
    hoy = ahora.normalize().tz_localize(None)
    dia = t.tz_localize(None).normalize()
    nombre = {0: "hoy", 1: "mañana"}.get((dia - hoy).days, dia_semana(t).lower())
    return f"{nombre} {t:%H:%M}"


def avisos_oficiales(lista, ahora):
    """Avisos de Meteoalarm o del NWS (ver avisos.avisos_vigentes), con el intervalo en hora local."""

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
        detalle = (f'<details class="alert-detalle"><summary>Detalles</summary>{detalle}</details>'
                   if detalle else "")
        html += (f'<div class="alert-item alert-oficial" style="--aviso: {color};">'
                 f'<span class="alert-emoji">{emoji}</span>'
                 f'<span class="alert-text"><b>Aviso {nombre}</b> por {fenomeno}'
                 f'<span class="alert-periodo">{periodo}</span>{detalle}</span></div>')

    _html(f'<div class="alerts-container oficiales">{html}</div>')
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
        return f'<td class="{clase}">{coma(serie[fecha])}º <span style="font-size: 0.85em; opacity: 0.5;">({fecha.year})</span></td>'

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
        lineas.append(f"Día más lluvioso: <b>{coma(lluvia.max(), '.1f')} L/m²</b> ({lluvia.idxmax().year})")
    if prob_lluvia is not None:
        lineas.append(f"Llueve (≥ 1 L/m²) el <b>{prob_lluvia:.0f} %</b> de los días en estas fechas")
    if lineas:
        _html(f'<p class="records-nota">{"<br>".join(lineas)}</p>', destino=st.sidebar)


def camaras(imagenes):
    """Rejilla de cámaras [(url, pie)]; al pulsar una se ve en grande, a pantalla completa, con flechas a la anterior
    y la siguiente. Sin JavaScript: cada vista grande es un elemento que se muestra cuando la URL acaba en su #id
    (:target); cerrar vuelve a #ir-camaras, la sección. Escape también cierra (ver estilo.TOQUES)."""

    n = len(imagenes)
    celdas, grandes = "", ""
    for i, (url, pie) in enumerate(imagenes):
        pie = escape(pie)
        celdas += (f'<a class="camera-card" href="#camara-{i}" title="Ver en grande">'
                   f'<img src="{url}" alt="Cámara: {pie}" loading="lazy"><span class="camara-pie">{pie}</span></a>')
        anterior, siguiente = (i - 1) % n, (i + 1) % n
        flechas = (f'<a class="camara-flecha anterior" href="#camara-{anterior}" aria-label="Cámara anterior">‹</a>'
                   f'<a class="camara-flecha siguiente" href="#camara-{siguiente}" aria-label="Cámara siguiente">›</a>'
                   if n > 1 else "")
        grandes += (f'<div class="camara-grande" id="camara-{i}">'
                    f'<a class="camara-fondo" href="#ir-camaras" aria-label="Cerrar"></a>'
                    f'<img src="{url}" alt="Cámara: {pie}, en grande" loading="lazy">'
                    f'<a class="camara-cerrar" href="#ir-camaras" aria-label="Cerrar">✕</a>{flechas}'
                    f'<span class="camara-cuenta">{pie} · {i + 1} / {n}</span></div>')
    _html(f'<div class="camera-grid">{celdas}</div>{grandes}')


VIDEO_CSS = """
.video-directo { position: relative; aspect-ratio: 16 / 9; border-radius: 14px; overflow: hidden; background: #1c1814; }
.video-directo video { width: 100%; height: 100%; display: block; object-fit: contain; }
.video-directo button {
    position: absolute; inset: 0; margin: auto; width: max-content; height: max-content; padding: 12px 20px;
    border: none; border-radius: 999px; background: #d97706; color: white; cursor: pointer;
    font: 600 15px 'Plus Jakarta Sans', 'Inter', sans-serif;
}
.video-directo .error {
    position: absolute; inset: 0; display: none; place-items: center; color: #e5ded2;
    font: 14px 'Plus Jakarta Sans', 'Inter', sans-serif;
}
"""

VIDEO_JS = """
const hlsjs = import("https://unpkg.com/hls.js@1.5.17/dist/hls.mjs");

export default function(component) {
  const { data, parentElement } = component;
  const marco = parentElement.querySelector(".video-directo");
  if (marco._listo) return;  // las recargas de la página no deben cortar el vídeo
  marco._listo = true;
  const video = marco.querySelector("video");
  const fallo = () => { marco.querySelector(".error").style.display = "grid"; };
  // La emisión solo se descarga al pulsar: el desplegable cerrado no gasta datos
  marco.querySelector("button").onclick = async (e) => {
    e.target.remove();
    const Hls = (await hlsjs).default;
    if (Hls.isSupported()) {
      const hls = new Hls({liveSyncDurationCount: 3});
      hls.on(Hls.Events.ERROR, (_, datos) => { if (datos.fatal) fallo(); });
      hls.loadSource(`${data.url}?t=${Date.now()}`);  // una copia en caché de la web de origen puede venir sin CORS
      hls.attachMedia(video);
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = data.url;  // Safari (iPhone) reproduce HLS sin hls.js
    } else {
      return fallo();
    }
    video.play().catch(() => {});
  };
}
"""

_video = st.components.v2.component(
    "video_en_directo", css=VIDEO_CSS, js=VIDEO_JS, isolate_styles=False,
    html='<div class="video-directo"><video muted playsinline controls></video><button>▶ Ver en directo</button>'
         '<div class="error">La emisión no está disponible ahora mismo</div></div>')


def video_en_directo(url, pie):
    """Emisión HLS (.m3u8) con hls.js; requiere que el servidor de origen permita CORS."""

    _video(data={"url": url}, key=f"video_{url}")
    st.caption(pie)


def ancla(nombre):
    """Punto de la página al que salta un enlace del índice (ver indice)."""

    _html(f'<div id="ir-{nombre}" class="ancla"></div>')


def indice(secciones):
    """Enlaces a las secciones de más abajo (`secciones`: [(ancla, texto)]): en el móvil, la página es larga."""

    enlaces = "".join(f'<a href="#ir-{nombre}">{texto}</a>' for nombre, texto in secciones)
    _html(f'<nav class="indice"><span>Ir a</span>{enlaces}</nav>')


def resumen(frases):
    """Resumen en texto de hoy y mañana, arriba de la página."""

    if frases:
        _html(f'<p class="resumen">{" ".join(escape(f) for f in frases)}</p>')


def tiempo_wmo(codigo):
    """(emoji, texto) del código WMO del tiempo."""

    if codigo is None or pd.isna(codigo):
        return "", ""
    return next(((e, t) for limite, e, t in TIEMPO_WMO if codigo <= limite), ("", ""))


def tira_dias(dias, nota):
    """Un día por columna: tiempo, máxima, mínima y probabilidad de lluvia, con `nota` debajo.

    Cada día: dict(fecha, codigo (WMO, o None), tmax, tmin, prob (%, o None), nombre (opcional, p. ej. "Hoy")).
    """

    html = ""
    for d in dias:
        if pd.isna(d["tmax"]) or pd.isna(d["tmin"]):
            continue
        emoji, texto = tiempo_wmo(d.get("codigo"))
        p = d.get("prob")
        lluvia = (f'<div class="dia-lluvia">{p:.0f} %</div>' if p is not None and not pd.isna(p) and p >= 10
                  else '<div class="dia-lluvia vacia">–</div>')
        html += (f'<div class="dia" title="{texto}"><div class="dia-nombre">{d.get("nombre") or dia_semana(d["fecha"])}</div>'
                 f'<div class="dia-icono">{emoji}</div>'
                 f'<div class="dia-max">{d["tmax"]:.0f}º</div>'
                 f'<div class="dia-min">{d["tmin"]:.0f}º</div>{lluvia}</div>')
    if html:
        _html(f'<div class="tira-semana" style="--dias: {len(dias)}">{html}</div>')
        st.caption(nota)


# ---------------------------------------------------------------- Luna

def svg_luna(iluminada, crece, clase="luna-disco"):
    """La Luna como se ve desde el hemisferio norte: iluminada por la derecha cuando crece y por la izquierda cuando
    mengua. La parte iluminada es medio disco más (o menos) media elipse, la del terminador."""

    limbo = 1 if crece else 0  # el arco del borde iluminado, por la derecha o por la izquierda
    rx = 40 * abs(1 - 2 * iluminada)
    terminador = 1 if (iluminada >= 0.5) == crece else 0
    return (f'<svg class="{clase}" viewBox="0 0 100 100" aria-hidden="true">'
            '<circle cx="50" cy="50" r="40" class="luna-sombra"/>'
            f'<path d="M50,10 A40,40 0 0 {limbo} 50,90 A{rx:.2f},40 0 0 {terminador} 50,10 Z" class="luna-luz"/>'
            '<circle cx="50" cy="50" r="40" class="luna-borde"/></svg>')


def svg_cielo(recorrido, azimut, altura):
    """Mapa del cielo visto desde arriba, como una brújula (norte arriba, este a la derecha): el borde es el horizonte
    y el centro, el cénit. El recorrido de la Luna en el día (ver luna.recorrido) y, si está sobre el horizonte, dónde
    está ahora."""

    radio, centro = 42, 55

    def xy(az, alt):
        r = radio * (90 - alt) / 90
        return centro + r * np.sin(np.radians(az)), centro - r * np.cos(np.radians(az))

    # El recorrido, en tramos sobre el horizonte (puede salir y ponerse en el mismo día)
    tramos, tramo = [], []
    for az, alt in recorrido[["azimut", "altura"]].itertuples(index=False):
        if alt > 0:
            tramo.append("{:.1f},{:.1f}".format(*xy(az, alt)))
        elif tramo:
            tramos.append(tramo)
            tramo = []
    tramos += [tramo] if tramo else []
    lineas = "".join(f'<polyline points="{" ".join(t)}" class="cielo-recorrido"/>' for t in tramos if len(t) > 1)

    rotulos = "".join(f'<text x="{x:.1f}" y="{y:.1f}" class="cielo-rotulo">{texto}</text>'
                      for texto, (x, y) in [(t, (centro + 50 * np.sin(np.radians(a)), centro - 50 * np.cos(np.radians(a))))
                                            for t, a in [("N", 0), ("E", 90), ("S", 180), ("O", 270)]])
    luna = ""
    if altura > 0:
        x, y = xy(azimut, altura)
        luna = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" class="cielo-luna"/>'
    return (f'<svg class="cielo" viewBox="0 0 110 110" role="img" aria-label="Posición de la Luna en el cielo">'
            f'<circle cx="{centro}" cy="{centro}" r="{radio}" class="cielo-horizonte"/>'
            f'<circle cx="{centro}" cy="{centro}" r="{radio * 2 / 3:.0f}" class="cielo-altura"/>'
            f'<circle cx="{centro}" cy="{centro}" r="{radio / 3:.0f}" class="cielo-altura"/>'
            f'<path d="M{centro},{centro - radio} V{centro + radio} M{centro - radio},{centro} H{centro + radio}" '
            f'class="cielo-altura"/>{rotulos}{lineas}{luna}</svg>')


def luna(fase, proximas, salida_puesta, cielo, ahora):
    """Fase de la Luna ahora (ver luna.fase), su salida y puesta hoy, dónde está en el cielo y las próximas fases
    principales.

    `cielo`: dict(azimut, altura) de ahora, `recorrido` del día (ver luna.recorrido) y azimut de la salida y de la puesta
    (`az_salida`, `az_puesta`, o None).
    """

    salida, puesta, arriba = salida_puesta
    if salida is None and puesta is None:
        horario = "Todo el día sobre el horizonte" if arriba else "Hoy no sale"
    else:
        partes = [f"sale a las {salida:%H:%M} por el {rumbo(cielo['az_salida'])}" if salida else "no sale",
                  f"se pone a las {puesta:%H:%M} por el {rumbo(cielo['az_puesta'])}" if puesta else "no se pone"]
        horario = " · ".join(partes)
        horario = horario[0].upper() + horario[1:]
    if cielo["altura"] > 0:
        donde = f"Ahora al {rumbo(cielo['azimut'])}, a {cielo['altura']:.0f}º sobre el horizonte"
    else:
        donde = "Ahora bajo el horizonte"
    edad = f" · {fase['edad']:.0f} días desde la nueva".replace(" 1 días", " 1 día") if fase["edad"] is not None else ""

    def cuando(momento):
        dia = (momento.normalize() - ahora.normalize()).days
        nombre = {0: "hoy", 1: "mañana"}.get(dia, dia_semana(momento).lower())
        return f"{nombre}, {momento:%H:%M}"

    fases = "".join(f'<div class="luna-fase"><span class="luna-emoji">{emoji}</span><b>{nombre}</b>'
                    f'<span>{cuando(momento)}</span></div>' for nombre, emoji, momento in proximas)
    _html(f'<div class="rejilla"><div class="luna"><div class="luna-hoy">{svg_luna(fase["iluminada"], fase["crece"])}'
          f'<div><div class="luna-etiqueta">Luna hoy</div><div class="luna-nombre">{fase["nombre"]}</div>'
          f'<div class="luna-dato">{100 * fase["iluminada"]:.0f} % iluminada{edad}</div>'
          f'<div class="luna-dato">{horario}</div><div class="luna-dato luna-donde">{donde}</div></div></div>'
          f'<div class="luna-cielo">{svg_cielo(cielo["recorrido"], cielo["azimut"], cielo["altura"])}'
          f'<span>Recorrido de hoy</span></div>'
          f'<div class="luna-proximas">{fases}</div></div></div>')


# ---------------------------------------------------------------- Auroras

def _bosque():
    """Silueta de un bosque de abetos (path SVG de 800 x 70) para el pie de la cabecera de auroras."""

    trazos = ["M0,70 L0,62 L800,62 L800,70 Z"]
    for i in range(46):
        x, alto = i * 17.7 + (i * 37 % 11), 22 + (i * 53 % 40)  # posiciones y alturas variadas pero fijas
        ancho, base = 0.3 * alto, 64
        puntos = [(-1, 0), (-0.35, 0.35), (-0.7, 0.35), (-0.25, 0.68), (-0.5, 0.68), (0, 1),
                  (0.5, 0.68), (0.25, 0.68), (0.7, 0.35), (0.35, 0.35), (1, 0)]
        trazos.append("M" + " L".join(f"{x + dx * ancho:.1f},{base - dy * alto:.1f}" for dx, dy in puntos) + " Z")
    return "".join(trazos)


BOSQUE = _bosque()


def nombre_noche(fecha, ahora):
    """"Esta noche", "Lo que queda de noche" (la que empezó ayer) o "Noche del mié 28"."""

    hoy = ahora.date()
    if fecha == hoy:
        return "Esta noche"
    if fecha < hoy:
        return "Lo que queda de noche"
    return f"Noche del {dia_semana(fecha).lower()}"


def _ventana(noche, factores):
    """Mejor ventana de la noche y, si la noche no es buena, el factor que más resta; si está perdida, solo este."""

    ventana = f"mejor de {noche['inicio']:%H} a {noche['fin']:%H} h"
    motivo = f"sobre todo por {factores[noche['limita']][2]}"
    if noche["puntuacion"] < 2:
        return motivo
    return f"{ventana}, {motivo}" if noche["puntuacion"] < 6 else ventana


def cabecera_auroras(lugar, noche, ahora, factores):
    """Cielo estrellado con auroras animadas, el lugar y la puntuación de la primera noche (ver auroras.puntuar_noches;
    `factores`: ver auroras.FACTORES)."""

    if noche is None:
        resumen = '<div class="aurora-hero-veredicto">Sin puntuación por ahora</div>'
    else:
        resumen = (f'<div class="aurora-hero-nota">{nombre_noche(noche["fecha"], ahora)}</div>'
                   f'<div class="aurora-hero-puntos" style="--nivel: {noche["color"]}">'
                   f'{coma(noche["puntuacion"], ".1f")}<span>/ 10</span></div>'
                   f'<div class="aurora-hero-veredicto">{noche["valoracion"]}: {_ventana(noche, factores)}</div>')
    _html(f'<div class="aurora-hero"><div class="aurora-estrellas"></div>'
          f'<div class="aurora-cortina uno"></div><div class="aurora-cortina dos"></div>'
          f'<div class="aurora-cortina tres"></div>'
          f'<svg class="aurora-bosque" viewBox="0 0 800 70" preserveAspectRatio="none" aria-hidden="true">'
          f'<path d="{BOSQUE}"/></svg>'
          f'<div class="aurora-hero-texto"><div class="aurora-hero-lugar">Auroras boreales · {escape(lugar)}</div>'
          f'{resumen}</div></div>')


def _color_factor(valor):
    return "#34d399" if valor >= 0.7 else "#fbbf24" if valor >= 0.4 else "#f87171"


def noches_aurora(noches, ahora, factores, compacta=False):
    """Una tarjeta por noche (ver auroras.puntuar_noches): puntuación en un anillo, valoración y mejor ventana y, salvo
    `compacta`, la confianza, cada factor (`factores`: ver auroras.FACTORES) y los datos de la noche."""

    html = ""
    for n in noches:
        kp = f"Kp ~{n['kp']:.0f} (27 días)" if n["kp_27"] else f"Kp {coma(n['kp'], '.1f')}"
        datos = [kp]
        if n["tormenta"] >= 10:
            datos.append(f"tormenta {n['tormenta']:.0f} %")
        if not pd.isna(n["nubes"]):
            datos.append(f"nubes {n['nubes']:.0f} %")
        datos.append(f"luna {100 * n['luna']:.0f} %")
        if not pd.isna(n["sensacion"]):
            datos.append(f"sensación {n['sensacion']:.0f}º")
        datos.append(f"{n['horas_oscuras']} h de noche oscura")
        ventana = _ventana(n, factores)
        ventana = ventana[0].upper() + ventana[1:]
        cabecera = f'<span class="noche-nombre">{nombre_noche(n["fecha"], ahora)}</span>'
        centro = (f'<div class="noche-centro"><div class="noche-anillo"><span class="noche-puntos">'
                  f'{coma(n["puntuacion"], ".1f")}</span></div><div><div class="noche-veredicto">{n["valoracion"]}</div>'
                  f'<div class="noche-ventana">{ventana}</div></div></div>')
        estilo = f'style="--nivel: {n["color"]}; --p: {10 * n["puntuacion"]:.0f}"'

        if compacta:
            titulo = escape(f"{ventana}. Confianza {n['confianza']}. " + " · ".join(datos))
            html += f'<div class="noche" {estilo} title="{titulo}"><div class="noche-cabecera">{cabecera}</div>{centro}</div>'
            continue

        filas = ""
        for clave, (nombre, explicacion, _) in factores.items():
            valor = n["factores"][clave]
            filas += (f'<div class="factor" title="{escape(explicacion)}"><span>{nombre}</span>'
                      f'<i><b style="width: {100 * valor:.0f}%; --color: {_color_factor(valor)}"></b></i>'
                      f'<em>{10 * valor:.0f}</em></div>')
        html += (f'<div class="noche" {estilo}><div class="noche-cabecera">{cabecera}'
                 f'<span class="noche-confianza {n["confianza"]}">confianza {n["confianza"]}</span></div>'
                 f'{centro}<div class="noche-factores">{filas}</div>'
                 f'<div class="noche-detalle">{" · ".join(datos)}</div></div>')

    _html(f'<div class="noches{" compactas" if compacta else ""}">{html}</div>')
