"""Probabilidad de ver auroras hora a hora, en un visor como el del meteograma (horas_auroras.js) y con el tema nocturno
de la pestaña: la probabilidad, el Kp y la nubosidad apilados, las noches sombreadas y un cursor que da, para cada hora,
esos datos y los seis factores de la puntuación (los mismos que las tarjetas de las noches).
"""

from hashlib import md5
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from .graficos import valoracion_kp

VISOR = st.components.v2.component(
    "horas_auroras", isolate_styles=False, html='<div class="horas-auroras" tabindex="0"></div>',
    css=Path(__file__).with_name("horas_auroras.css").read_text(encoding="utf-8"),
    js=Path(__file__).with_name("horas_auroras.js").read_text(encoding="utf-8"),
)


def _ms(momento):
    return int(pd.Timestamp(momento).value // 10**6)


def _lista(serie, decimales):
    """Serie -> lista para JSON, con None donde falta."""
    return [None if pd.isna(v) else round(float(v), decimales) for v in serie]


def horas_auroras(ciudad, horario, kp, kp_27, factores):
    """Visor de `horario` (ver auroras.horario_noches) con el Kp cada 3 h (`kp`) y, después, el máximo de cada día de
    la previsión a 27 días (`kp_27`). `factores`: auroras.FACTORES."""

    umbral = ciudad.kp_auroras
    inicio, fin = horario.index[0], horario.index[-1] + pd.Timedelta(hours=1)
    datos = {
        "tz": ciudad.tz, "umbral": umbral,
        "horas": [_ms(h) for h in horario.index],
        # Solo de noche: de día no hay probabilidad que valga
        "prob": _lista((100 * horario["prob"]).where(horario["f_oscuridad"] > 0), 0),
        "oscuro": [bool(v > 0) for v in horario["f_oscuridad"]],
        "factores": [[nombre, limita, _lista(horario[f"f_{clave}"], 2)]
                     for clave, (nombre, _, limita) in factores.items()],
    }

    # Kp: bloques de 3 h [inicio, kp, tipo, color, valoración] y días de la previsión a 27 días [inicio, fin, kp, ...]
    bloques, dias = [], []
    if kp is not None:
        for momento, fila in kp[(kp.index > inicio - pd.Timedelta(hours=3)) & (kp.index < fin)].iterrows():
            texto, color = valoracion_kp(fila["kp"], umbral)
            bloques.append([_ms(momento), round(float(fila["kp"]), 2), fila["tipo"], color, texto])
    if kp_27 is not None:
        for dia in sorted(set(horario.index[horario["tipo_kp"] == "27 días"].tz_convert("UTC").date)):
            valor = kp_27.get(dia)
            if valor is not None and not pd.isna(valor):
                comienzo = pd.Timestamp(dia, tz="UTC")
                texto, color = valoracion_kp(valor, umbral)
                dias.append([_ms(comienzo), _ms(comienzo + pd.Timedelta(days=1)), float(valor), color, texto])
    maximo = max([umbral + 3] + [b[1] + 1 for b in bloques] + [d[2] + 1 for d in dias])
    datos |= {"kp": bloques, "kp27": dias, "kp_max": min(9, maximo)}

    # Nubes: mediana y rango 10-90 % de los miembros del ensemble o, sin ensemble, la del determinista
    if horario["nubes_p50"].notna().any():
        datos["nubes"] = {c: _lista(horario[f"nubes_{c}"], 0) for c in ("p50", "p10", "p90")}
    else:
        datos["nubes"] = {"p50": _lista(horario["nubes"], 0)}

    datos["clave"] = md5(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:12]
    VISOR(key=f"horas_auroras_{ciudad.nombre}", data=datos)
