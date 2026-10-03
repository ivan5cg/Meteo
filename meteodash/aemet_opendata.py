"""API OpenData de AEMET (necesita clave): comentario de los predictores por comunidad autónoma y resúmenes mensuales de estación.

La clave se lee de `st.secrets["AEMET_API_KEY"]` o de la variable de entorno AEMET_API_KEY. Sin clave, las
funciones lanzan `SinClave` y la página simplemente no muestra estas secciones.
"""

import json
import os
import re
import time

import pandas as pd
import requests
import streamlit as st

from .fuentes import USER_AGENT

API = "https://opendata.aemet.es/opendata/api"
NORMAL_DESDE, NORMAL_HASTA = 1991, 2020  # periodo de referencia de las normales climatológicas


class SinClave(Exception):
    pass


def _clave():
    try:
        clave = st.secrets.get("AEMET_API_KEY")
    except Exception:  # sin .streamlit/secrets.toml
        clave = None
    clave = clave or os.environ.get("AEMET_API_KEY")
    if not clave:
        raise SinClave("Falta AEMET_API_KEY")
    return clave


def hay_clave():
    try:
        _clave()
    except SinClave:
        return False
    return True


def _pedir_bruto(ruta, reintentos=3):
    """Consulta en dos pasos (AEMET devuelve primero la URL de los datos). Reintenta ante 429, 5xx o cuerpo vacío."""

    cabeceras = USER_AGENT | {"api_key": _clave()}
    for intento in range(reintentos):
        respuesta = requests.get(f"{API}{ruta}", headers=cabeceras, timeout=20)
        if respuesta.status_code == 429 or respuesta.status_code >= 500:
            time.sleep(2 * (intento + 1))
            continue
        respuesta.raise_for_status()
        meta = respuesta.json()
        if meta.get("estado") != 200:
            raise ValueError(f"AEMET {meta.get('estado')}: {meta.get('descripcion')}")
        datos = requests.get(meta["datos"], headers=USER_AGENT, timeout=20)
        if datos.status_code == 200 and datos.content.strip():
            return datos.content
        time.sleep(2 * (intento + 1))
    raise RuntimeError(f"AEMET no ha respondido a {ruta}")


def _decodificar(contenido):
    """La codificación varía según la respuesta (UTF-8 o ISO-8859-15) y no siempre se declara."""

    try:
        return contenido.decode("utf-8")
    except UnicodeDecodeError:
        return contenido.decode("iso-8859-15")


def _pedir(ruta):
    return json.loads(_decodificar(_pedir_bruto(ruta)))


# ---------------------------------------------------------------- Comentario de los predictores (por comunidad)

DIAS_PREDICCION = {"hoy": 0, "manana": 1, "pasadomanana": 2}
MESES = {mes: i for i, mes in enumerate(["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO",
                                          "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"], start=1)}


def parsear_prediccion(texto, desplazamiento):
    """Texto de AEMET -> {"fecha": día al que se refiere, "elaborado": Timestamp, "secciones": [(título, texto)]}.

    `desplazamiento` son los días entre la elaboración y el día de validez (0 hoy, 1 mañana, 2 pasado mañana).
    """

    elaboracion = re.search(r"DÍA\s+(\d+)\s+DE\s+(\w+)\s+DE\s+(\d{4})\s+A\s+LAS\s+(\d+):(\d+)", texto)
    if not elaboracion:
        raise ValueError("No se reconoce la fecha de elaboración del texto de AEMET")
    dia, mes, año, hora, minuto = elaboracion.groups()
    elaborado = pd.Timestamp(int(año), MESES[mes.upper()], int(dia), int(hora), int(minuto), tz="Europe/Madrid")

    secciones = []
    for linea in texto.splitlines()[4:]:
        titulo = re.match(r"^[A-Z]\.-\s*(.+?)\s*$", linea)
        if titulo:
            secciones.append((titulo[1].capitalize(), []))
        elif secciones and linea.strip():
            secciones[-1][1].append(linea.strip())
    secciones = [(titulo, " ".join(lineas)) for titulo, lineas in secciones if lineas]
    if not secciones:
        raise ValueError("No se reconocen las secciones del texto de AEMET")

    return {"fecha": elaborado.tz_localize(None).normalize() + pd.Timedelta(days=desplazamiento),
            "elaborado": elaborado, "secciones": secciones}


@st.cache_data(ttl="30m", show_spinner=False)
def get_comentario_aemet(ccaa, dia):
    """Predicción general que redactan los predictores de AEMET para una comunidad (`mad`, `cle`...).

    `dia` es "hoy", "manana" o "pasadomanana". El texto de "hoy" a veces no se renueva y llega con la fecha de
    otro día: quien lo use debe comprobar `fecha`.
    """

    return parsear_prediccion(_decodificar(_pedir_bruto(f"/prediccion/ccaa/{dia}/{ccaa}")), DIAS_PREDICCION[dia])


# ---------------------------------------------------------------- Resumen mensual de una estación

@st.cache_data(ttl="12h", show_spinner=False)
def get_resumen_mensual(estacion, año):
    """Último mes publicado por AEMET (de `año - 1` o `año`): (año, mes, valores de AEMET), o None si no hay ninguno."""

    filas = _pedir(f"/valores/climatologicos/mensualesanuales/datos/anioini/{año - 1}/aniofin/{año}/estacion/{estacion}")
    publicados = []
    for fila in filas:
        año_fila, mes = map(int, fila["fecha"].split("-"))
        if mes <= 12 and "tm_mes" in fila:  # el mes 13 es el resumen anual; los meses sin publicar vienen vacíos
            publicados.append((año_fila, mes, fila))
    return max(publicados, key=lambda p: p[:2]) if publicados else None


def valor_y_dia(texto):
    """'39.5(23)' -> (39.5, 23); un valor sin día ('39.5') -> (39.5, None)."""

    coincidencia = re.fullmatch(r"\s*(-?[\d.]+)\s*(?:\((\d+)\))?\s*", texto or "")
    if not coincidencia:
        return None, None
    return float(coincidencia[1]), int(coincidencia[2]) if coincidencia[2] else None


def racha_maxima(texto):
    """'08/14.2(14)' (dirección/m/s(día)) -> (51.1 km/h, 14); (None, None) si no se entiende."""

    _, _, resto = (texto or "").partition("/")
    velocidad, dia = valor_y_dia(resto)
    return (None, None) if velocidad is None else (round(velocidad * 3.6, 1), dia)


def normales_mensuales(datos_hist, mes):
    """Promedio de `mes` en 1991-2020 a partir del histórico diario: tmed, tmax, tmin, lluvia (L/m²) y días con ≥ 1 L/m².

    Solo cuentan los años con el mes casi completo. Devuelve None si el histórico no cubre el periodo.
    """

    periodo = datos_hist[(datos_hist.index.month == mes) & datos_hist.index.year.isin(range(NORMAL_DESDE, NORMAL_HASTA + 1))]
    por_año = periodo.groupby(periodo.index.year)
    completos = por_año.filter(lambda g: g["tmed"].count() >= 25).groupby(lambda f: f.year)
    if completos.ngroups < 20:
        return None

    return {
        "tmed": completos["tmed"].mean().mean(),
        "tmax": completos["tmax"].mean().mean(),
        "tmin": completos["tmin"].mean().mean(),
        "lluvia": completos["prec"].sum().mean(),
        "dias_lluvia": completos["prec"].apply(lambda s: (s >= 1).sum()).mean(),
    }
