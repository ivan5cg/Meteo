"""Avisos oficiales de los servicios meteorológicos europeos (AEMET, Met Éireann, IRM...) a través de Meteoalarm y, en
EE. UU., del Servicio Meteorológico Nacional (NWS)."""

import re

import pandas as pd
import streamlit as st

from .fuentes import descargar

# Ciudad.pais de los lugares de EE. UU.: avisos del NWS para el punto, en lugar de un feed de Meteoalarm
NWS = "usa"

# Nivel de Meteoalarm -> (nombre, color). El 1 (verde) es "sin aviso" y no se muestra
NIVELES = {2: ("amarillo", "#ca8a04"), 3: ("naranja", "#ea580c"), 4: ("rojo", "#dc2626")}

# Tipo de Meteoalarm -> (fenómeno, emoji); del 101 en adelante, los del NWS que no tienen equivalente en Meteoalarm
TIPOS = {
    1: ("viento", "💨"), 2: ("nieve y hielo", "❄️"), 3: ("tormentas", "⛈️"), 4: ("niebla", "🌫️"),
    5: ("temperaturas altas", "🥵"), 6: ("temperaturas bajas", "🥶"), 7: ("fenómenos costeros", "🌊"),
    8: ("incendios forestales", "🔥"), 9: ("aludes", "🏔️"), 10: ("lluvia", "🌧️"), 12: ("inundaciones", "🌊"),
    13: ("lluvia e inundaciones", "🌧️"),
    101: ("tornados", "🌪️"), 102: ("ciclón tropical", "🌀"), 103: ("mala calidad del aire", "😷"),
}
# Orden entre avisos que empiezan y acaban a la vez y tienen el mismo nivel: primero los fenómenos más peligrosos
PRIORIDAD = [101, 102, 3, 13, 12, 10, 1, 2, 9, 8, 5, 6, 7, 103, 4]


def _parametro(info, nombre):
    """Número inicial de un parámetro de la alerta ("3; orange; Severe" -> 3), o None."""

    for parametro in info.get("parameter", []):
        if parametro.get("valueName") == nombre:
            try:
                return int(parametro.get("value", "").split(";")[0])
            except ValueError:
                return None
    return None


def _poligono(texto):
    """Polígono CAP ("lat,lon lat,lon ...") como tupla de (lat, lon)."""

    return tuple(tuple(float(v) for v in punto.split(",")) for punto in texto.split())


def _dentro(punto, poligono):
    """Si el punto (lat, lon) está dentro del polígono (algoritmo del rayo)."""

    lat, lon = punto
    dentro = False
    for (lat1, lon1), (lat2, lon2) in zip(poligono, poligono[-1:] + poligono[:-1]):
        if (lat1 > lat) != (lat2 > lat) and lon < (lon2 - lon1) * (lat - lat1) / (lat2 - lat1) + lon1:
            dentro = not dentro
    return dentro


@st.cache_data(ttl="15m", show_spinner=False)
def get_avisos(pais):
    """Avisos amarillos o superiores publicados para un país (`pais`: nombre del feed de Meteoalarm, p. ej. "spain").

    Se descartan los cancelados y los que una actualización posterior sustituye. El texto, en español o, si no lo
    hay, en inglés; los nombres de las zonas, en todos los idiomas del aviso.
    """

    alertas = [a["alert"] for a in descargar(f"https://feeds.meteoalarm.org/api/v1/warnings/feeds-{pais}",
                                              timeout=60).json()["warnings"]]

    # "references": "emisor,identificador,fecha emisor,identificador,fecha ..."
    sustituidas = {ref.split(",")[1] for a in alertas for ref in (a.get("references") or "").split() if "," in ref}

    avisos = []
    for alerta in alertas:
        if alerta.get("msgType") == "Cancel" or alerta.get("identifier") in sustituidas or not alerta.get("info"):
            continue
        infos = alerta["info"]
        info = next((i for idioma in ("es", "en") for i in infos if i.get("language", "").startswith(idioma)), infos[0])
        nivel, tipo = _parametro(info, "awareness_level"), _parametro(info, "awareness_type")
        if nivel not in NIVELES or tipo is None:
            continue
        areas = info.get("area", [])
        avisos.append({
            "nivel": nivel,
            "tipo": tipo,
            "inicio": pd.Timestamp(info.get("onset") or info.get("effective")),
            "fin": pd.Timestamp(info["expires"]),
            "nombres": tuple({a.get("areaDesc", "").lower() for i in infos for a in i.get("area", [])}),
            "codigos": tuple(g.get("value") for a in areas for g in a.get("geocode", [])),
            # Solo de las zonas sin código: las que lo tienen se identifican por él
            "poligonos": tuple(_poligono(p) for a in areas if not a.get("geocode") for p in a.get("polygon", [])),
            "descripcion": info.get("description") or "",
        })
    return avisos


# ---------------------------------------------------------------- EE. UU.: NWS

# Fenómeno de un aviso del NWS según las palabras de su nombre (en minúsculas): el primero que aparezca, así que los
# nombres más concretos van antes ("wind chill" antes que "wind", "coastal flood" antes que "flood"). "freezing" (lluvia
# o niebla engelante) es otra palabra que "freeze" (helada)
TIPOS_NWS = [
    ("tornado", 101), ("hurricane", 102), ("tropical", 102), ("storm surge", 7), ("thunderstorm", 3), ("fog", 4),
    ("smoke", 103), ("air quality", 103), ("air stagnation", 103), ("coastal flood", 7), ("lakeshore flood", 7),
    ("flood", 12), ("hydrologic", 12), ("wind chill", 6), ("cold", 6), ("freeze", 6), ("frost", 6), ("blizzard", 2),
    ("winter", 2), ("snow", 2), ("ice", 2), ("freezing", 2), ("sleet", 2), ("heat", 5), ("red flag", 8), ("fire", 8),
    ("avalanche", 9), ("wind", 1), ("gale", 1), ("dust", 1), ("rip current", 7), ("surf", 7), ("beach", 7),
    ("tsunami", 7), ("rain", 10),
]
# Productos solo informativos ("Special Weather Statement", "Hazardous Weather Outlook"...): no son avisos
NO_SON_AVISOS = ("statement", "outlook", "message", "test")


def _nivel_nws(nombre, gravedad):
    """Nivel equivalente al de Meteoalarm: rojo las emergencias y los warning de gravedad extrema (tornados,
    huracanes...), naranja el resto de warning y amarillo los advisory, watch y alert."""

    if nombre.endswith("Emergency") or (nombre.endswith("Warning") and gravedad == "Extreme"):
        return 4
    return 3 if nombre.endswith("Warning") else 2


def _sin_cortes(texto):
    """El texto del NWS sin los saltos de línea de su ancho fijo: un párrafo por línea."""

    parrafos = re.split(r"\n\s*\n", texto.strip())
    return "\n".join(" ".join(linea.strip() for linea in p.splitlines()) for p in parrafos)


@st.cache_data(ttl="15m", show_spinner=False)
def get_avisos_nws(lat, lon):
    """Avisos en vigor del NWS para un punto, con el formato de get_avisos (el NWS ya los da filtrados por el punto:
    los de su zona de predicción, su condado y los de polígono que lo contienen).

    El nivel sale del tipo de producto (ver _nivel_nws) y el fenómeno, del nombre (TIPOS_NWS); se descartan los
    productos informativos, los de fenómenos sin equivalente y los que una actualización posterior sustituye. El texto
    va en inglés, precedido del nombre oficial del aviso.
    """

    # El NWS no acepta más de 4 decimales
    datos = descargar("https://api.weather.gov/alerts/active", params={"point": f"{lat:.4f},{lon:.4f}"}).json()
    alertas = [f["properties"] for f in datos.get("features", [])]
    sustituidas = {ref.get("identifier") for a in alertas for ref in a.get("references") or []}

    avisos = []
    for alerta in alertas:
        evento = (alerta.get("event") or "").strip()
        if (alerta.get("status") != "Actual" or alerta.get("messageType") == "Cancel"
                or alerta.get("id") in sustituidas or evento.lower().endswith(NO_SON_AVISOS)):
            continue
        tipo = next((t for clave, t in TIPOS_NWS if re.search(rf"\b{clave}\b", evento.lower())), None)
        inicio, fin = alerta.get("onset") or alerta.get("effective"), alerta.get("ends") or alerta.get("expires")
        if tipo is None or not inicio or not fin:
            continue
        descripcion = "\n".join(t for t in (evento, _sin_cortes(alerta.get("description") or ""),
                                            _sin_cortes(alerta.get("instruction") or "")) if t)
        avisos.append({"nivel": _nivel_nws(evento, alerta.get("severity")), "tipo": tipo,
                       "inicio": pd.Timestamp(inicio), "fin": pd.Timestamp(fin), "nombres": (), "codigos": (),
                       "poligonos": (), "descripcion": descripcion})
    return avisos


# ---------------------------------------------------------------- Avisos de un lugar

def descarga_avisos(pais, punto=None):
    """(función, argumentos) para lanzar en paralelo la descarga de los avisos de un lugar (ver avisos_vigentes)."""

    return (get_avisos_nws, *punto) if pais == NWS else (get_avisos, pais)


def avisos_vigentes(pais, zonas, ahora, punto=None):
    """Avisos de las zonas indicadas que aún no han terminado.

    Orden: cronológico (los ya activos primero, del que antes termina al que más dura); a igual periodo, el de más
    nivel y, a igual nivel, según PRIORIDAD.

    Cada zona es un código (EMMA_ID, FIPS...: "ES219") o parte del nombre de la zona ("lombardia"). Con `punto`
    (lat, lon), también los avisos cuyo polígono lo contiene (Letonia delimita así los avisos en tierra). Con el NWS
    (`pais` NWS), los del punto, que es obligatorio.
    """

    if pais == NWS:  # ya vienen filtrados por el punto
        avisos = get_avisos_nws(*punto)

        def es_de_la_zona(aviso):
            return True
    else:
        avisos = get_avisos(pais)

        def es_de_la_zona(aviso):
            return (any(zona in aviso["codigos"] or any(zona.lower() in nombre for nombre in aviso["nombres"])
                        for zona in zonas)
                    or (punto is not None and any(_dentro(punto, poligono) for poligono in aviso["poligonos"])))

    # Del mismo fenómeno y periodo (p. ej. el interior y la costa de una zona) solo se muestra el nivel más alto
    vistos, vigentes = set(), []
    for aviso in sorted(avisos, key=lambda a: (a["inicio"], -a["nivel"])):
        clave = (aviso["tipo"], aviso["inicio"], aviso["fin"])
        if aviso["fin"] > ahora and clave not in vistos and es_de_la_zona(aviso):
            vistos.add(clave)
            vigentes.append(aviso)

    def orden(aviso):
        prioridad = PRIORIDAD.index(aviso["tipo"]) if aviso["tipo"] in PRIORIDAD else len(PRIORIDAD)
        return max(aviso["inicio"], ahora), aviso["fin"], -aviso["nivel"], prioridad

    return sorted(vigentes, key=orden)
