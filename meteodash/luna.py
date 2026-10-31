"""Fase de la Luna: parte iluminada, nombre de la fase, próximas fases principales, salida y puesta.

Las fases principales salen del algoritmo de Meeus (Astronomical Algorithms, cap. 49), con un error de pocos minutos;
la parte iluminada, del ángulo de fase con los términos principales de la elongación (cap. 48). Salida y puesta, de
astral.
"""

from math import cos, radians, sin

import pandas as pd
import pytz
from astral import Observer, moon

MES_SINODICO = 29.530588861  # días
DELTA_T = 69 / 86400  # TT - UT hacia 2026, en días

# (nombre, emoji) de las ocho fases, cada 45º de elongación; las principales son las pares
FASES = [("Luna nueva", "🌑"), ("Creciente", "🌒"), ("Cuarto creciente", "🌓"), ("Gibosa creciente", "🌔"),
         ("Luna llena", "🌕"), ("Gibosa menguante", "🌖"), ("Cuarto menguante", "🌗"), ("Menguante", "🌘")]


def _dia_juliano(momento):
    return momento.tz_convert("UTC").to_julian_date()


def _desde_dia_juliano(jd):
    return pd.Timestamp(jd - 2440587.5, unit="D", tz="UTC").round("min")


def _elementos(jd):
    """Elongación media D, anomalías medias del Sol M y de la Luna M' (grados) y siglos desde J2000."""

    t = (jd - 2451545.0) / 36525
    d = 297.8501921 + 445267.1114034 * t - 0.0018819 * t ** 2
    m = 357.5291092 + 35999.0502909 * t - 0.0001536 * t ** 2
    m_luna = 134.9633964 + 477198.8675055 * t + 0.0087414 * t ** 2
    return d, m, m_luna


def iluminacion(momento):
    """(fracción del disco iluminada, si crece) en un instante (Timestamp con zona)."""

    d, m, m_luna = _elementos(_dia_juliano(momento))
    angulo = (180 - d - 6.289 * sin(radians(m_luna)) + 2.100 * sin(radians(m)) - 1.274 * sin(radians(2 * d - m_luna))
              - 0.658 * sin(radians(2 * d)) - 0.214 * sin(radians(2 * m_luna)) - 0.110 * sin(radians(d)))
    return (1 + cos(radians(angulo))) / 2, d % 360 < 180


def _fase_principal(k):
    """Instante (UTC) de la fase principal k: entero la nueva, +0,25 cuarto creciente, +0,5 llena, +0,75 menguante."""

    t = k / 1236.85
    jde = (2451550.09766 + MES_SINODICO * k + 0.00015437 * t ** 2 - 0.000000150 * t ** 3
           + 0.00000000073 * t ** 4)
    e = 1 - 0.002516 * t - 0.0000074 * t ** 2
    m = radians(2.5534 + 29.10535670 * k - 0.0000014 * t ** 2 - 0.00000011 * t ** 3)
    ml = radians(201.5643 + 385.81693528 * k + 0.0107582 * t ** 2 + 0.00001238 * t ** 3 - 0.000000058 * t ** 4)
    f = radians(160.7108 + 390.67050284 * k - 0.0016118 * t ** 2 - 0.00000227 * t ** 3 + 0.000000011 * t ** 4)
    om = radians(124.7746 - 1.56375588 * k + 0.0020672 * t ** 2 + 0.00000215 * t ** 3)

    tipo = round((k % 1) * 4) % 4
    if tipo in (0, 2):  # nueva y llena
        a = (-0.40720, 0.17241, 0.01608, 0.01039, 0.00739, -0.00514, 0.00208) if tipo == 0 else \
            (-0.40614, 0.17302, 0.01614, 0.01043, 0.00734, -0.00515, 0.00209)
        correccion = (a[0] * sin(ml) + a[1] * e * sin(m) + a[2] * sin(2 * ml) + a[3] * sin(2 * f)
                      + a[4] * e * sin(ml - m) + a[5] * e * sin(ml + m) + a[6] * e ** 2 * sin(2 * m)
                      - 0.00111 * sin(ml - 2 * f) - 0.00057 * sin(ml + 2 * f) + 0.00056 * e * sin(2 * ml + m)
                      - 0.00042 * sin(3 * ml) + 0.00042 * e * sin(m + 2 * f) + 0.00038 * e * sin(m - 2 * f)
                      - 0.00024 * e * sin(2 * ml - m) - 0.00017 * sin(om))
    else:  # cuartos
        correccion = (-0.62801 * sin(ml) + 0.17172 * e * sin(m) - 0.01183 * e * sin(ml + m) + 0.00862 * sin(2 * ml)
                      + 0.00804 * sin(2 * f) + 0.00454 * e * sin(ml - m) + 0.00204 * e ** 2 * sin(2 * m)
                      - 0.00180 * sin(ml - 2 * f) - 0.00070 * sin(ml + 2 * f) - 0.00040 * sin(3 * ml)
                      - 0.00034 * e * sin(2 * ml - m) + 0.00032 * e * sin(m + 2 * f) + 0.00032 * e * sin(m - 2 * f)
                      - 0.00028 * e ** 2 * sin(ml + 2 * m) + 0.00027 * e * sin(2 * ml + m) - 0.00017 * sin(om))
        w = (0.00306 - 0.00038 * e * cos(m) + 0.00026 * cos(ml) - 0.00002 * cos(ml - m) + 0.00002 * cos(ml + m)
             + 0.00002 * cos(2 * f))
        correccion += w if tipo == 1 else -w
    return _desde_dia_juliano(jde + correccion - DELTA_T)


def fases_principales(desde, n=4):
    """Las n fases principales a partir de `desde`: [(nombre, emoji, instante en la zona de `desde`)]."""

    k = (_dia_juliano(desde) - 2451550.09766) / MES_SINODICO
    k = (k // 0.25) * 0.25 - 0.25  # un cuarto antes, por si la corrección adelanta la fase
    fases = []
    while len(fases) < n:
        momento = _fase_principal(k)
        if momento >= desde:
            nombre, emoji = FASES[2 * (round((k % 1) * 4) % 4)]
            fases.append((nombre, emoji, momento.tz_convert(desde.tz)))
        k += 0.25
    return fases


def fase(momento):
    """Fase en un instante: dict(nombre, emoji, iluminada, crece, edad (días desde la última luna nueva)).

    Las principales (nueva, cuartos y llena) solo se nombran el día local en que ocurren; el resto del tiempo, la
    intermedia que toque.
    """

    iluminada, crece = iluminacion(momento)
    hoy = momento.normalize()
    principal = next((f for f in fases_principales(hoy, 1) if f[2] < hoy + pd.Timedelta(days=1)), None)
    if principal is not None:
        nombre, emoji = principal[:2]
    else:
        d, _, _ = _elementos(_dia_juliano(momento))
        nombre, emoji = FASES[int(d % 360 // 90) * 2 + 1]
    anterior = [f for f in fases_principales(momento - pd.Timedelta(days=30), 8) if f[0] == "Luna nueva"
                and f[2] <= momento]
    edad = (momento - anterior[-1][2]).total_seconds() / 86400 if anterior else None
    return {"nombre": nombre, "emoji": emoji, "iluminada": iluminada, "crece": crece, "edad": edad}


def salida_y_puesta(lat, lon, tz, fecha):
    """(salida, puesta, arriba) de la Luna el día local `fecha`: None en lugar de la salida o la puesta si ese día no
    hay (cerca del círculo polar); `arriba`, si está sobre el horizonte al mediodía."""

    observador, zona = Observer(lat, lon), pytz.timezone(tz)
    resultado = []
    for funcion in (moon.moonrise, moon.moonset):
        try:
            resultado.append(funcion(observador, fecha, tzinfo=zona))
        except ValueError:  # ese día no sale o no se pone
            resultado.append(None)
    mediodia = zona.localize(pd.Timestamp(fecha).to_pydatetime().replace(hour=12))
    return resultado[0], resultado[1], moon.elevation(observador, mediodia) > 0
