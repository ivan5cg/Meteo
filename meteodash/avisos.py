"""Avisos oficiales de los servicios meteorológicos europeos (AEMET, Met Éireann, IRM...) a través de Meteoalarm."""

import pandas as pd
import streamlit as st

from .fuentes import descargar

# Nivel de Meteoalarm -> (nombre, color). El 1 (verde) es "sin aviso" y no se muestra
NIVELES = {2: ("amarillo", "#ca8a04"), 3: ("naranja", "#ea580c"), 4: ("rojo", "#dc2626")}

# Tipo de Meteoalarm -> (fenómeno, emoji)
TIPOS = {
    1: ("viento", "💨"), 2: ("nieve y hielo", "❄️"), 3: ("tormentas", "⛈️"), 4: ("niebla", "🌫️"),
    5: ("temperaturas altas", "🥵"), 6: ("temperaturas bajas", "🥶"), 7: ("fenómenos costeros", "🌊"),
    8: ("incendios forestales", "🔥"), 9: ("aludes", "🏔️"), 10: ("lluvia", "🌧️"), 12: ("inundaciones", "🌊"),
    13: ("lluvia e inundaciones", "🌧️"),
}
# Orden entre avisos que empiezan y acaban a la vez y tienen el mismo nivel: primero los fenómenos más peligrosos
PRIORIDAD = [3, 13, 12, 10, 1, 2, 9, 8, 5, 6, 7, 4]


def _parametro(info, nombre):
    """Número inicial de un parámetro de la alerta ("3; orange; Severe" -> 3), o None."""

    for parametro in info.get("parameter", []):
        if parametro.get("valueName") == nombre:
            try:
                return int(parametro.get("value", "").split(";")[0])
            except ValueError:
                return None
    return None


@st.cache_data(ttl="15m", show_spinner=False)
def get_avisos(pais):
    """Avisos amarillos o superiores publicados para un país (`pais`: nombre del feed de Meteoalarm, p. ej. "spain").

    Se descartan los cancelados y los que una actualización posterior sustituye.
    """

    alertas = [a["alert"] for a in descargar(f"https://feeds.meteoalarm.org/api/v1/warnings/feeds-{pais}",
                                              timeout=60).json()["warnings"]]

    # "references": "emisor,identificador,fecha emisor,identificador,fecha ..."
    sustituidas = {ref.split(",")[1] for a in alertas for ref in (a.get("references") or "").split() if "," in ref}

    avisos = []
    for alerta in alertas:
        if alerta.get("msgType") == "Cancel" or alerta.get("identifier") in sustituidas or not alerta.get("info"):
            continue
        info = next((i for i in alerta["info"] if i.get("language", "").startswith("es")), alerta["info"][0])
        nivel, tipo = _parametro(info, "awareness_level"), _parametro(info, "awareness_type")
        if nivel not in NIVELES or tipo is None:
            continue
        areas = info.get("area", [])
        avisos.append({
            "nivel": nivel,
            "tipo": tipo,
            "inicio": pd.Timestamp(info.get("onset") or info.get("effective")),
            "fin": pd.Timestamp(info["expires"]),
            "nombres": tuple(a.get("areaDesc", "").lower() for a in areas),
            "codigos": tuple(g.get("value") for a in areas for g in a.get("geocode", [])),
            "descripcion": info.get("description") or "",
        })
    return avisos


def avisos_vigentes(pais, zonas, ahora):
    """Avisos de las zonas indicadas que aún no han terminado.

    Orden: cronológico (los ya activos primero, del que antes termina al que más dura); a igual periodo, el de más
    nivel y, a igual nivel, según PRIORIDAD.

    Cada zona es un código (EMMA_ID, FIPS...: "ES219") o parte del nombre de la zona ("lombardia").
    """

    def es_de_la_zona(aviso):
        return any(zona in aviso["codigos"] or any(zona.lower() in nombre for nombre in aviso["nombres"])
                   for zona in zonas)

    # Del mismo fenómeno y periodo (p. ej. el interior y la costa de una zona) solo se muestra el nivel más alto
    vistos, vigentes = set(), []
    for aviso in sorted(get_avisos(pais), key=lambda a: (a["inicio"], -a["nivel"])):
        clave = (aviso["tipo"], aviso["inicio"], aviso["fin"])
        if aviso["fin"] > ahora and clave not in vistos and es_de_la_zona(aviso):
            vistos.add(clave)
            vigentes.append(aviso)

    def orden(aviso):
        prioridad = PRIORIDAD.index(aviso["tipo"]) if aviso["tipo"] in PRIORIDAD else len(PRIORIDAD)
        return max(aviso["inicio"], ahora), aviso["fin"], -aviso["nivel"], prioridad

    return sorted(vigentes, key=orden)
