"""Meteograma de las 48 h: temperatura, lluvia, rachas y, si la ciudad los tiene, presión y MUCAPE, en paneles apilados
con un solo cursor (meteograma.js).

El cursor se mueve en el navegador, sin recargar Streamlit: pasar el ratón, arrastrar el dedo en horizontal (en vertical
sigue desplazando la página) o las flechas. Aquí solo se preparan las series, con las mismas cuentas que las tarjetas y
que los gráficos a los que sustituye (media del ensemble con el control, probabilidad de lluvia por hora...).
"""

from hashlib import md5
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from .fuentes import UMBRAL_LLUVIA_HORA, prob_por_hora

OBSERVADO = "Observado"  # columna que añade ciudad.py con las observaciones
UMBRAL_TORMENTA = 500  # J/kg de MUCAPE medio: a partir de aquí, presión y tormentas salen desplegadas

VISOR = st.components.v2.component(
    "meteograma", isolate_styles=False, html='<div class="meteograma" tabindex="0"></div>',
    css=Path(__file__).with_name("meteograma.css").read_text(encoding="utf-8"),
    js=Path(__file__).with_name("meteograma.js").read_text(encoding="utf-8"),
)


def _lista(serie, decimales):
    """Serie -> lista para JSON, con None donde falta."""
    return [None if pd.isna(v) else round(float(v), decimales) for v in serie]


def _ensemble(df, horas, decimales):
    """Miembros, control, media (con el control, como en las tarjetas) y observado, si lo hay, en las `horas`."""

    ens = df.drop(columns=OBSERVADO, errors="ignore").reindex(horas)
    miembros = ens.drop(columns="Ctrl", errors="ignore")
    observado = df[OBSERVADO] if OBSERVADO in df.columns and df[OBSERVADO].notna().any() else None
    return {
        "miembros": [_lista(miembros[columna], decimales) for columna in miembros.columns],
        "control": _lista(ens["Ctrl"], decimales) if "Ctrl" in ens.columns else None,
        "media": _lista(ens.mean(axis=1), decimales),
        "observado": None if observado is None else _lista(observado.reindex(horas), decimales),
    }


def _extremos(media, decimales):
    """Máximo y mínimo de cada día de la media del ensemble: [[ms, valor, "max" | "min"]]."""

    extremos = []
    for fecha in sorted(set(media.index.date)):
        dia = media[media.index.date == fecha].dropna()
        if not dia.empty:
            for momento, tipo in [(dia.idxmax(), "max"), (dia.idxmin(), "min")]:
                extremos.append([int(momento.value // 10**6), round(float(dia[momento]), decimales), tipo])
    return extremos


def meteograma(ciudad, arome, direccion=None, bandas=None, dia_bandas=None):
    """Meteograma de `arome` ({variable: DataFrame con un miembro por columna y, si hay, "Observado"}). `direccion`:
    punto cardinal de la racha observada; `bandas`: rangos habituales de máxima y mínima (los del día `dia_bandas`)."""

    horas = arome["temperatura"].index
    for df in arome.values():
        horas = horas.union(df.index)

    temp = arome["temperatura"]
    ens = temp.drop(columns=OBSERVADO, errors="ignore")
    temperatura = _ensemble(temp, horas, 1) | {
        "p10": _lista(ens.quantile(0.1, axis=1).reindex(horas), 1),
        "p90": _lista(ens.quantile(0.9, axis=1).reindex(horas), 1),
        "extremos": _extremos(ens.mean(axis=1), 1),
    }
    if bandas is not None and dia_bandas in bandas.index:
        temperatura["bandas"] = {variable: [round(float(bandas.loc[dia_bandas, (variable, q)]), 1) for q in (0.15, 0.85)]
                                 for variable in ("tmax", "tmin")}

    prec = arome["precipitacion"]
    ens = prec.drop(columns=OBSERVADO, errors="ignore")
    lluvia = {
        # Cantidad media de los miembros que llueven (los que no, no la rebajan) y % de miembros que llueven
        "media": _lista(ens.where(ens >= UMBRAL_LLUVIA_HORA).mean(axis=1).fillna(0).reindex(horas), 1),
        "probabilidad": _lista(prob_por_hora(prec).reindex(horas), 0),
        "observado": _ensemble(prec, horas, 1)["observado"],
        "umbral": UMBRAL_LLUVIA_HORA,
    }

    rachas = arome["rachas"]
    datos = {
        "horas": [int(h.value // 10**6) for h in horas],
        "tz": ciudad.tz, "lat": ciudad.lat, "lon": ciudad.lon,
        "temperatura": temperatura,
        "lluvia": lluvia,
        "rachas": _ensemble(rachas, horas, 0) | {
            "extremos": _extremos(rachas.drop(columns=OBSERVADO, errors="ignore").mean(axis=1), 0),
            "direccion": None if direccion is None else [None if pd.isna(d) or d == "" else str(d)
                                                         for d in direccion.reindex(horas)],
        },
    }
    if "presion" in arome and "mucape" in arome:
        presion = arome["presion"].drop(columns=OBSERVADO, errors="ignore")
        valores = presion.stack()
        datos["presion"] = _ensemble(arome["presion"], horas, 1)
        if not valores.empty:
            # Al menos 30 hPa de rango, centrado en lo previsto: una borrasca profunda no se sale del panel
            centro, mitad = (valores.min() + valores.max()) / 2, max((valores.max() - valores.min()) / 2 + 3, 15)
            datos["presion"]["rango"] = [round(float(centro - mitad), 1), round(float(centro + mitad), 1)]
        cape = arome["mucape"].drop(columns=OBSERVADO, errors="ignore")
        datos["mucape"] = _ensemble(arome["mucape"], horas, 0) | {"maximo": _lista(cape.max(axis=1).reindex(horas), 0)}
        # Plegados salvo que el ensemble vea potencial de tormenta
        maximo = cape.mean(axis=1).max()
        datos["tormenta"] = bool(not pd.isna(maximo) and maximo >= UMBRAL_TORMENTA)

    # El visor solo vuelve a dibujar si cambian los datos (Streamlit recarga la página por cualquier otra cosa)
    datos["clave"] = md5(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:12]
    VISOR(key=f"meteograma_{ciudad.nombre}", data=datos)
