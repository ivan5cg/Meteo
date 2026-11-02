"""El Sol hoy, en un visor como el del meteograma (sol.js): la elevación a lo largo del día sobre las bandas de los
crepúsculos, con el amanecer, el cénit, el atardecer y ahora, y un cursor que da la altura, el azimut y la fase de luz de
cada momento. El cursor se mueve en el navegador, sin recargar Streamlit.
"""

from datetime import datetime, timedelta
from hashlib import md5
import json
from pathlib import Path

import pytz
import streamlit as st
from astral import LocationInfo
from astral.sun import azimuth, elevation, noon, sunrise, sunset

from .observaciones import RUMBOS

PASO = timedelta(minutes=5)

VISOR = st.components.v2.component(
    "sol", isolate_styles=False, html='<div class="sol" tabindex="0"></div>',
    css=Path(__file__).with_name("sol.css").read_text(encoding="utf-8"),
    js=Path(__file__).with_name("sol.js").read_text(encoding="utf-8"),
)


def _ms(momento):
    return int(momento.timestamp() * 1000)


def _horas_de_luz(observador, dia, zona):
    """(amanecer, atardecer) del día, o None si el Sol no sale o no se pone (noche polar o sol de medianoche).

    Por separado: astral.sun.sun() también calcula el crepúsculo civil, y falla en cuanto el Sol no baja 6º bajo el
    horizonte (las noches blancas de Helsinki en junio), aunque salga y se ponga.
    """
    try:
        return sunrise(observador, dia, zona), sunset(observador, dia, zona)
    except ValueError:
        return None


def sol_hoy(lat, lon, zona):
    """Visor del Sol de hoy en (lat, lon), en la hora local de `zona`."""

    tz = pytz.timezone(zona)
    ahora = datetime.now(tz)
    hoy = ahora.date()
    observador = LocationInfo("", "", zona, lat, lon).observer

    # De medianoche a medianoche locales, cada 5 min (los días del cambio de hora tienen 23 o 25 h)
    inicio = tz.localize(datetime(hoy.year, hoy.month, hoy.day)).astimezone(pytz.utc)
    siguiente = hoy + timedelta(days=1)
    fin = tz.localize(datetime(siguiente.year, siguiente.month, siguiente.day)).astimezone(pytz.utc)
    # y ahora, para que el cursor empiece justo en el minuto de la marca de ahora
    momentos, momento = [ahora], inicio
    while momento <= fin:
        momentos.append(momento)
        momento += PASO
    puntos = sorted([_ms(m), round(elevation(observador, m), 2), round(azimuth(observador, m), 1)] for m in momentos)

    cenit = noon(observador, hoy, zona)
    datos = {
        "tz": zona, "puntos": puntos, "rumbos": RUMBOS,
        "cenit": [_ms(cenit), round(elevation(observador, cenit), 1)],
        "ahora": [_ms(ahora), round(elevation(observador, ahora), 1)],
    }
    luz = _horas_de_luz(observador, hoy, zona)
    if luz:
        amanecer, atardecer = luz
        datos["amanecer"], datos["atardecer"] = _ms(amanecer), _ms(atardecer)
        duracion = (atardecer - amanecer).total_seconds()
        titulo = f"Sol hoy · {int(duracion // 3600)} h {int(duracion % 3600 // 60)} min de luz"
        if luz_ayer := _horas_de_luz(observador, hoy - timedelta(days=1), zona):
            diferencia = duracion - (luz_ayer[1] - luz_ayer[0]).total_seconds()
            minutos, segundos = divmod(abs(int(diferencia)), 60)
            titulo += f" ({'+' if diferencia > 0 else '−'}{minutos} min {segundos} s)"
    else:
        sale = max(elevacion for _, elevacion, _ in puntos) > -0.833  # el borde superior del Sol, con la refracción
        titulo = "Sol hoy · " + ("no se pone (sol de medianoche)" if sale else "no sale (noche polar)")
    datos["titulo"] = titulo

    # Cambia cada minuto (ahora): el visor vuelve a dibujar, pero conserva la hora fijada si no es la de ahora
    datos["clave"] = md5(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:12]
    VISOR(key=f"sol_{lat}_{lon}", data=datos)
