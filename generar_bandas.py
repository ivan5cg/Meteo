"""Genera los rangos habituales de máxima y mínima (datos/bandas/*.csv) de las páginas sin histórico propio.

Para cada día del año, los percentiles 15 y 85 de la media de 15 días centrada en él, igual que get_historico con los
históricos de Madrid y Ávila. Periodo de referencia 1991-2020 (los años con al menos 330 días medidos) o, si la
estación no llega ahí a 15 años, todos sus años completos desde 1991. La primera línea de cada CSV dice de dónde sale.

Uso (PowerShell):
    python generar_bandas.py                    # todas
    python generar_bandas.py bruselas gante     # solo esas
Las estaciones de AEMET necesitan $env:AEMET_API_KEY (ver actualizar_historicos.py).
"""

import argparse
import io
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from actualizar_historicos import TROZO_DIAS
from actualizar_historicos import descargar as descargar_aemet

CARPETA = Path(__file__).parent / "datos" / "bandas"
DESDE, HASTA = 1991, 2020
MINIMO_AÑOS = 15
DIAS_AÑO_COMPLETO = 330
UA = {"User-Agent": "Mozilla/5.0 (Meteo Dash; Streamlit)"}

# Página -> (fuente, código de la estación, cómo se cita). Solo estaciones cercanas y representativas del punto con un
# registro largo; sin ninguna así (Brujas, Riga, el Pirineo y las Highlands salvo Edimburgo), la página va sin bandas
ESTACIONES = {
    "alicante": ("aemet", "8025", "Alicante"),
    "santander": ("ghcn", "SPE00119981", "Santander"),
    "torrelavega": ("aemet", "1154H", "Torrelavega (Sierrapando)"),
    "dublin": ("ghcn", "EI000003969", "Phoenix Park"),
    "milan": ("ghcn", "ITE00100554", "Milano Brera"),
    "liubliana": ("ghcn", "SIM00014015", "Ljubljana Bežigrad"),
    "bled": ("ghcn", "SIE00114966", "Lesce"),
    "bruselas": ("kmi", "6447", "Uccle"),  # en GHCN-Daily le faltan muchos años desde 1991
    "gante": ("kmi", "6434", "Melle"),
    "edimburgo": ("ghcn", "UKE00105888", "Real Jardín Botánico de Edimburgo"),
    "helsinki": ("ghcn", "FI000000304", "Helsinki Kaisaniemi"),
    "rovaniemi": ("ghcn", "FIE00146241", "Rovaniemi (estación de tren)"),
    "tallin": ("ghcn", "ENE00175051", "Tallinn-Harku"),
}
NOMBRES_FUENTE = {"aemet": "AEMET", "ghcn": "GHCN-Daily, NOAA", "kmi": "KMI"}


def serie_ghcn(codigo):
    """Máximas y mínimas diarias de GHCN-Daily, sin los valores que no pasan su control de calidad."""

    url = f"https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{codigo}.csv"
    texto = requests.get(url, headers=UA, timeout=300).text
    datos = pd.read_csv(io.StringIO(texto), index_col="DATE", parse_dates=True, low_memory=False,
                        usecols=["DATE", "TMAX", "TMAX_ATTRIBUTES", "TMIN", "TMIN_ATTRIBUTES"])
    serie = pd.DataFrame(index=datos.index)
    for variable in ("TMAX", "TMIN"):
        calidad = datos[f"{variable}_ATTRIBUTES"].fillna(",,").str.split(",").str[1]  # MFLAG,QFLAG,SFLAG,hora
        serie[variable.lower()] = (datos[variable] / 10).where(calidad == "")  # décimas de grado
    return serie


def serie_kmi(codigo):
    """Máximas y mínimas diarias de una estación automática del KMI (WFS de datos abiertos, desde 2002-2003)."""

    params = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typenames": "aws:aws_1day",
              "outputFormat": "application/json", "CQL_FILTER": f"code={codigo}"}
    filas = [f["properties"] for f in requests.get("https://opendata.meteo.be/service/ows", params=params, headers=UA,
                                                     timeout=300).json()["features"]]
    datos = pd.DataFrame(filas)
    datos.index = pd.to_datetime(datos["timestamp"]).dt.tz_localize(None).dt.normalize()
    return datos[["temp_max", "temp_min"]].rename(columns={"temp_max": "tmax", "temp_min": "tmin"}).sort_index()


def serie_aemet(codigo):
    """Máximas y mínimas diarias de AEMET OpenData desde 1991 hasta el último año completo."""

    clave = os.environ.get("AEMET_API_KEY")
    if not clave:
        sys.exit("Falta la variable de entorno AEMET_API_KEY (clave gratuita de AEMET OpenData).")
    filas, inicio, fin = [], date(DESDE, 1, 1), date(date.today().year - 1, 12, 31)
    while inicio <= fin:
        tope = min(inicio + timedelta(days=TROZO_DIAS - 1), fin)
        filas += descargar_aemet(codigo, inicio, tope, clave)
        inicio = tope + timedelta(days=1)
        time.sleep(1)
    datos = pd.DataFrame(filas).set_index("fecha")
    datos.index = pd.to_datetime(datos.index)
    return datos[["tmax", "tmin"]].apply(lambda s: pd.to_numeric(s.str.replace(",", "."), errors="coerce"))


DESCARGAS = {"aemet": serie_aemet, "ghcn": serie_ghcn, "kmi": serie_kmi}


def años_de_referencia(diario):
    """Años de 1991-2020 con al menos DIAS_AÑO_COMPLETO días medidos o, si no llegan a MINIMO_AÑOS, todos desde 1991."""

    medidos = diario.dropna()
    por_año = medidos.groupby(medidos.index.year).size()
    completos = [a for a, dias in por_año.items() if dias >= DIAS_AÑO_COMPLETO and a >= DESDE]
    años = [a for a in completos if a <= HASTA]
    return años if len(años) >= MINIMO_AÑOS else completos


def bandas(diario, años):
    """Percentiles 15 y 85 de la media de 15 días centrada en cada día del año (sin 29 de febrero), en `años`."""

    diario = diario[~diario.index.duplicated()].asfreq("D")
    medias = diario.rolling(15, center=True, min_periods=12).mean()
    medias = medias[medias.index.year.isin(años) & ~((medias.index.month == 2) & (medias.index.day == 29))]
    indice = medias.index
    medias["día_del_año"] = indice.day_of_year - (indice.is_leap_year & (indice.month >= 3))  # fuentes.dia_historico
    tabla = medias.groupby("día_del_año").quantile([0.15, 0.85]).unstack()
    tabla.columns = [f"{variable}_p{round(100 * q)}" for variable, q in tabla.columns]
    return tabla.round(1)


def origen(nombre, fuente, años):
    periodo = (f"{años[0]}-{años[-1]}" if len(años) == años[-1] - años[0] + 1
               else f"{len(años)} años entre {años[0]} y {años[-1]}")
    return f"{nombre}, {periodo} ({NOMBRES_FUENTE[fuente]})"


def generar(pagina):
    fuente, codigo, nombre = ESTACIONES[pagina]
    diario = DESCARGAS[fuente](codigo)
    años = años_de_referencia(diario)
    if len(años) < MINIMO_AÑOS:
        print(f"{pagina}: solo {len(años)} años completos desde {DESDE}; no se genera")
        return
    texto = origen(nombre, fuente, años)
    CARPETA.mkdir(parents=True, exist_ok=True)
    with open(CARPETA / f"{pagina}.csv", "w", encoding="utf-8", newline="") as f:
        f.write(f"# {texto}\n")
        bandas(diario, años).to_csv(f, lineterminator="\n")
    print(f"{pagina}: {texto}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paginas", nargs="*", help=f"por defecto, todas: {', '.join(ESTACIONES)}")
    paginas = parser.parse_args().paginas or list(ESTACIONES)
    if desconocidas := set(paginas) - set(ESTACIONES):
        parser.error(f"páginas desconocidas: {', '.join(sorted(desconocidas))}")
    for pagina in paginas:
        generar(pagina)


if __name__ == "__main__":
    main()
