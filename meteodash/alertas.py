"""Avisos propios de cada lugar (Ciudad.alertas): lo que allí importa de verdad (viento en un mirador, nieve en un
puerto de montaña, hielo en los adoquines...), con umbrales y textos elegidos para ese sitio. No son avisos oficiales.

Se comprueban día a día, en un tramo de horas de cada día, hasta donde llega el ensemble del medio plazo (el ICON-EU,
unos 5 días): las rachas, la lluvia y las heladas, con sus miembros; la nieve y la cota de nieve, con el modelo
determinista del detalle de Open-Meteo (como el visor del medio plazo).
"""

from dataclasses import dataclass

import pandas as pd

from .fuentes import UMBRAL_LLUVIA_HORA

# Tipo -> (emoji, unidad del umbral)
TIPOS = {
    "rachas": ("💨", "km/h"),  # racha máxima en el tramo, de al menos `umbral`
    "lluvia": ("🌧️", "L/m²"),  # lluvia acumulada en el tramo, de al menos `umbral`
    "helada": ("🧊", "º"),  # temperatura mínima en el tramo, de `umbral` o menos
    "nieve": ("❄️", "cm"),  # nieve acumulada en el tramo en el punto, de al menos `umbral`
    "cota_nieve": ("🏔️", "m"),  # cota de nieve de `umbral` o menos mientras hay precipitación (para un puerto cercano)
}
DIFERENCIA_COTA = 300  # m: la cota de nieve, unos 300 m por debajo de la isoterma de 0º (como en visor.py)


@dataclass(frozen=True)
class Alerta:
    tipo: str  # clave de TIPOS
    umbral: float
    texto: str  # qué supone en ese sitio, en una frase
    horas: tuple[int, int] = (8, 20)  # tramo del día que se mira, en hora local: de la primera a la segunda (sin ella)
    prob: int = 30  # % de los miembros del ensemble que tienen que llegar al umbral (rachas, lluvia, helada y cota)


def _tramo(indice, fecha, horas, desde):
    """Filas de `indice` (hora local, con o sin zona) del día `fecha`, dentro de `horas` y a partir de `desde`."""

    return (indice.date == fecha) & (indice.hour >= horas[0]) & (indice.hour < horas[1]) & (indice >= desde)


def _miembros(df):
    return df.drop(columns="Observado", errors="ignore").dropna(axis=1, how="all")


def _comprobar(alerta, fecha, ens, detalle, desde):
    """Texto con el dato que dispara la alerta ese día, o None si no se dispara (o no hay datos del tramo)."""

    unidad = TIPOS[alerta.tipo][1]
    umbral = f"{alerta.umbral:g}"

    if alerta.tipo in ("rachas", "lluvia", "helada"):
        if ens is None:
            return None
        variable = {"rachas": "rachas", "lluvia": "precipitacion", "helada": "temperatura"}[alerta.tipo]
        df = _miembros(ens[variable])
        tramo = df[_tramo(df.index, fecha, alerta.horas, desde)]
        if tramo.empty or tramo.shape[1] == 0:
            return None
        if alerta.tipo == "rachas":
            valores = tramo.max().dropna()
            prob = 100 * (valores >= alerta.umbral).mean()
            dato = (f"Racha máxima de {valores.median():.0f} km/h según la mediana (hasta {valores.quantile(0.9):.0f} "
                    f"en el 10 % más ventoso); el {prob:.0f} % de los miembros llega a {umbral} {unidad}")
        elif alerta.tipo == "lluvia":
            valores = tramo.sum(min_count=1).dropna()
            prob = 100 * (valores >= alerta.umbral).mean()
            dato = (f"{valores.median():.0f} L/m² según la mediana (hasta {valores.quantile(0.9):.0f} en el 10 % más "
                    f"lluvioso); el {prob:.0f} % de los miembros llega a {umbral} {unidad}")
        else:
            valores = tramo.min().dropna()
            prob = 100 * (valores <= alerta.umbral).mean()
            dato = (f"Mínima de {valores.median():.0f}º según la mediana ({valores.quantile(0.1):.0f}º en el 10 % más "
                    f"frío); el {prob:.0f} % de los miembros baja a {umbral}º o menos")
        return dato if not valores.empty and prob >= alerta.prob else None

    if detalle is None:
        return None
    horario = detalle["horario"]
    tramo = horario[_tramo(horario.index, fecha, alerta.horas, desde.tz_localize(None))]
    if tramo.empty:
        return None

    if alerta.tipo == "nieve":
        total = tramo["nieve"].sum()
        return f"{total:.0f} cm de nieve en el tramo según el modelo determinista" if total >= alerta.umbral else None

    # Cota de nieve: horas con la cota a `umbral` o menos y, en ellas, % de miembros con precipitación
    cota = (tramo["isocero"] - DIFERENCIA_COTA).clip(lower=0)
    bajas = cota[cota <= alerta.umbral].index
    if bajas.empty or ens is None:
        return None
    prec = _miembros(ens["precipitacion"])
    prec = prec[prec.index.tz_localize(None).isin(bajas)]
    if prec.empty or prec.shape[1] == 0:
        return None
    prob = 100 * (prec >= UMBRAL_LLUVIA_HORA).any().mean()
    if prob < alerta.prob:
        return None
    return f"Cota de nieve de hasta {cota.min():.0f} m, con precipitación en el {prob:.0f} % de los miembros"


def alertas_del_lugar(ciudad, ens, detalle, ahora):
    """Alertas propias que se disparan de hoy al último día del ensemble: [{"fecha", "alerta", "dato"}], por fecha.

    `ens`: ensemble del medio plazo ({"temperatura", "precipitacion", "rachas"}, índice en hora local con zona) o None;
    `detalle`: el de fuentes.get_open_meteo_detalle o None. De hoy solo cuenta lo que queda.
    """

    if not ciudad.alertas or (ens is None and detalle is None):
        return []
    desde = ahora.floor("h")
    if ens is not None:
        fechas = sorted({f for f in ens["temperatura"].index.date if f >= ahora.date()})
    else:
        fechas = sorted({f for f in detalle["horario"].index.date if f >= ahora.date()})[:5]
    disparadas = []
    for fecha in fechas:
        for alerta in ciudad.alertas:
            dato = _comprobar(alerta, fecha, ens, detalle, desde)
            if dato is not None:
                disparadas.append({"fecha": fecha, "alerta": alerta, "dato": dato})
    return disparadas
