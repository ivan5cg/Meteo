"""Año hidrológico (del 1 de octubre al 30 de septiembre): lluvia acumulada frente a lo normal y a años anteriores.

Sale del histórico diario de AEMET de la ciudad y, para los días que aún no tiene el CSV, de AEMET OpenData (con clave).
"""

import calendar

import pandas as pd
import streamlit as st

from . import graficos, tarjetas
from .aemet_opendata import NORMAL_DESDE, NORMAL_HASTA, get_lluvia_reciente, hay_clave
from .estilo import AZUL, ROJO
from .fuentes import get_lluvia_diaria

MESES_HIDROLOGICOS = [10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9]
FALTAN_MAX = 10  # días sin dato con los que un año aún cuenta para el rango habitual


def inicio_año(fecha):
    """1 de octubre del año hidrológico al que pertenece la fecha."""

    fecha = pd.Timestamp(fecha)
    return pd.Timestamp(fecha.year if fecha.month >= 10 else fecha.year - 1, 10, 1)


def nombre_año(inicio):
    return f"{inicio.year}-{str(inicio.year + 1)[-2:]}"


def normales_lluvia(lluvia):
    """Lluvia normal de cada mes (L/m²): media de 1991-2020 con los meses completos, o None si hay menos de 20 años."""

    periodo = lluvia[(lluvia.index.year >= NORMAL_DESDE) & (lluvia.index.year <= NORMAL_HASTA)]
    por_mes = periodo.groupby([periodo.index.year, periodo.index.month])
    con_dato = por_mes.count()
    dias = pd.Series([calendar.monthrange(año, mes)[1] for año, mes in con_dato.index], index=con_dato.index)
    totales = por_mes.sum()[con_dato == dias]
    normales = {}
    for mes in range(1, 13):
        del_mes = totales[totales.index.get_level_values(1) == mes]
        if len(del_mes) < 20:
            return None
        normales[mes] = del_mes.mean()
    return normales


def _dias_del_año(inicio):
    """Fechas del año hidrológico que empieza en `inicio`, sin el 29 de febrero (365, para alinear los años)."""

    fechas = pd.date_range(inicio, inicio + pd.DateOffset(years=1) - pd.Timedelta(days=1))
    return fechas[~((fechas.month == 2) & (fechas.day == 29))]


def acumulada(lluvia, inicio):
    """Lluvia acumulada día a día en el año que empieza en `inicio`, hasta el último día con datos (el 29 de febrero
    suma pero no tiene punto propio). Los días sin dato suman 0. Devuelve (Series por posición 0-364, días sin dato)."""

    fin = inicio + pd.DateOffset(years=1) - pd.Timedelta(days=1)
    del_año = lluvia[(lluvia.index >= inicio) & (lluvia.index <= fin)]
    if del_año.empty:
        return pd.Series(dtype=float), 0
    dias = pd.date_range(inicio, del_año.index[-1])
    serie = del_año.reindex(dias)
    faltan = int(serie.isna().sum())
    total = serie.fillna(0).cumsum()
    total = total[~((total.index.month == 2) & (total.index.day == 29))]
    return total.reset_index(drop=True), faltan


def normal_acumulada(normales, inicio):
    """Lluvia normal acumulada en cada día del año hidrológico: los meses completos y la parte del mes en curso."""

    valores, previo = [], 0.0
    for fecha in _dias_del_año(inicio):
        dias_mes = calendar.monthrange(fecha.year, fecha.month)[1]
        valores.append(previo + normales[fecha.month] * fecha.day / dias_mes)
        if fecha.day == dias_mes or (fecha.month == 2 and fecha.day == 28):
            previo += normales[fecha.month]
    return pd.Series(valores)


def lluvia_diaria(ciudad, ahora):
    """Lluvia diaria del histórico más, si hay clave, los días que le faltan hasta lo último publicado por AEMET (como
    mucho desde el inicio del año hidrológico anterior). Devuelve (Series, si se ha completado con OpenData)."""

    lluvia = get_lluvia_diaria(ciudad.historico)
    if not ciudad.estacion_aemet or not hay_clave():
        return lluvia, False
    desde = max(lluvia.index[-1] + pd.Timedelta(days=1), inicio_año(ahora) - pd.DateOffset(years=1))
    try:
        reciente = get_lluvia_reciente(ciudad.estacion_aemet, f"{desde:%Y-%m-%d}")
    except Exception:
        return lluvia, False
    reciente = reciente[reciente.index > lluvia.index[-1]]
    return pd.concat([lluvia, reciente]), not reciente.empty


def render_año_hidrologico(ciudad, ahora):
    """Tarjetas del año en curso y del anterior frente a lo normal, y gráfico de la lluvia acumulada."""

    lluvia, completada = lluvia_diaria(ciudad, ahora)
    hoy = ahora.tz_localize(None).normalize()
    inicio = inicio_año(hoy)
    anterior = inicio - pd.DateOffset(years=1)
    normales = normales_lluvia(lluvia)
    if normales is None:
        return False
    normal = normal_acumulada(normales, inicio)

    actual, _ = acumulada(lluvia, inicio)
    previo, faltan_previo = acumulada(lluvia, anterior)
    ultimo = lluvia.dropna().index[-1]

    # Rango habitual: todos los años completos del histórico, con pocos días sin dato
    años = {}
    for año in range(lluvia.index[0].year + (lluvia.index[0].month > 10), inicio.year):
        serie, faltan = acumulada(lluvia, pd.Timestamp(año, 10, 1))
        if len(serie) == 365 and faltan <= FALTAN_MAX:
            años[año] = serie
    rango = pd.DataFrame(años)

    lista = []
    if not actual.empty:
        normal_hoy = normal.iloc[len(actual) - 1]
        tarjeta = {"label": "Desde el 1 de octubre", "valor": f"{actual.iloc[-1]:.0f}", "unidad": "L/m²",
                   "title": f"Normal hasta el {ultimo.day}/{ultimo.month} (1991-2020): {normal_hoy:.0f} L/m²"}
        if normal_hoy >= 5:  # al principio del año, unos pocos litros darían porcentajes enormes
            porcentaje = 100 * actual.iloc[-1] / normal_hoy
            tarjeta["nota"] = f"{porcentaje:.0f} % de lo normal a esta fecha"
            if abs(porcentaje - 100) >= 25:
                tarjeta["color"] = AZUL if porcentaje > 100 else ROJO
        else:
            tarjeta["nota"] = f"normal a esta fecha: {normal_hoy:.0f} L/m²"
        lista.append(tarjeta)
    if len(previo) == 365:
        total_normal = sum(normales.values())
        porcentaje = 100 * previo.iloc[-1] / total_normal
        tarjeta = {"label": f"Año {nombre_año(anterior)}", "valor": f"{previo.iloc[-1]:.0f}", "unidad": "L/m²",
                   "nota": f"{porcentaje:.0f} % de lo normal ({total_normal:.0f} L/m²)"}
        if faltan_previo:
            tarjeta["nota"] += f" · {faltan_previo} días sin dato"
        if abs(porcentaje - 100) >= 25:
            tarjeta["color"] = AZUL if porcentaje > 100 else ROJO
        otros = rango.drop(columns=anterior.year, errors="ignore")
        if not otros.empty and not faltan_previo:
            puesto = int((otros.iloc[-1] > previo.iloc[-1]).sum()) + 1
            tarjeta["title"] = (f"El {puesto}.º más lluvioso de los {len(otros.columns) + 1} años con menos de "
                                f"{FALTAN_MAX + 1} días sin dato")
        lista.append(tarjeta)
    if not lista:
        return False

    st.subheader(f"Año hidrológico {nombre_año(inicio)}")
    tarjetas.condiciones(lista)
    st.plotly_chart(graficos.año_hidrologico(_dias_del_año(inicio), actual, previo, normal, rango,
                                             nombre_año(inicio), nombre_año(anterior)))
    desde = min(años) if años else inicio.year
    st.caption(f"Lluvia acumulada desde el 1 de octubre en la estación de AEMET de {ciudad.nombre}, con datos hasta el "
               f"{ultimo.day}/{ultimo.month}/{ultimo.year}"
               + (" (los últimos días, de AEMET OpenData, que los publica con algo de retraso)" if completada else "")
               + f". Normal: promedio de 1991-2020. Rango: 10-90 % de los años desde {desde}-{str(desde + 1)[-2:]} "
                 f"con menos de {FALTAN_MAX + 1} días sin dato.")
    return True
