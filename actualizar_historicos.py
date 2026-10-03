"""Añade a los CSV históricos los días que faltan hasta lo más reciente que publica AEMET.

Uso (PowerShell):
    $env:AEMET_API_KEY = "<tu clave de https://opendata.aemet.es/centrodedescargas/altaUsuario>"
    python actualizar_historicos.py            # Madrid (Retiro) y Ávila
    python actualizar_historicos.py --dry-run  # solo muestra lo que añadiría
"""

import argparse
import csv
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

API = "https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos"
RAIZ = Path(__file__).parent
ESTACIONES = {"3195": RAIZ / "datos/retiro_1950.csv", "2444": RAIZ / "datos/avila_1990.csv"}
NUMERICAS = ("tmed", "prec", "tmin", "tmax")  # las que lee get_historico: punto decimal y sin "Ip"
TROZO_DIAS = 180  # AEMET admite como máximo 6 meses por consulta


def pedir(url, clave, reintentos=6):
    """GET con la clave de AEMET; espera y reintenta si salta el límite de peticiones."""

    for intento in range(reintentos):
        respuesta = requests.get(url, headers={"api_key": clave}, timeout=60)
        if respuesta.status_code == 429 or respuesta.status_code >= 500:
            time.sleep(10 * (intento + 1))
            continue
        respuesta.raise_for_status()
        return respuesta.json()
    raise RuntimeError("AEMET sigue limitando las peticiones o está caído (429/5xx)")


def descargar(estacion, desde, hasta, clave):
    """Registros diarios de una estación entre dos fechas (ambas incluidas); [] si AEMET no tiene datos."""

    url = (f"{API}/fechaini/{desde}T00:00:00UTC/fechafin/{hasta}T23:59:59UTC/estacion/{estacion}")
    meta = pedir(url, clave)
    if meta.get("estado") == 404:  # "No hay datos que satisfagan esos criterios"
        return []
    if meta.get("estado") != 200:
        raise RuntimeError(f"AEMET: {meta.get('estado')} {meta.get('descripcion')}")
    for intento in range(6):  # a veces devuelve cuerpo vacío o 429 si se le pide muy seguido
        respuesta = requests.get(meta["datos"], timeout=60)
        if respuesta.status_code == 200 and respuesta.text.strip():
            return respuesta.json()
        time.sleep(10 * (intento + 1))
    raise RuntimeError(f"AEMET no ha entregado los datos de {estacion} ({desde} -> {hasta})")


def limpiar(registro, columnas):
    fila = {c: registro.get(c, "") for c in columnas if c != "Día año"}
    for c in NUMERICAS:
        valor = str(fila[c]).replace(",", ".")
        fila[c] = "0.0" if valor == "Ip" else valor
    if "Día año" in columnas:
        fila["Día año"] = date.fromisoformat(fila["fecha"]).timetuple().tm_yday
    return fila


def actualizar(estacion, ruta, clave, dry_run):
    with open(ruta, newline="", encoding="utf-8") as f:
        lector = csv.DictReader(f)
        columnas = lector.fieldnames
        ultima = max(fila["fecha"] for fila in lector)
    inicio = date.fromisoformat(ultima) + timedelta(days=1)
    fin = date.today() - timedelta(days=1)
    print(f"{ruta.name}: último dato {ultima}; pidiendo {inicio} -> {fin}")

    nuevas = {}
    while inicio <= fin:
        tope = min(inicio + timedelta(days=TROZO_DIAS - 1), fin)
        for registro in descargar(estacion, inicio, tope, clave):
            nuevas[registro["fecha"]] = limpiar(registro, columnas)
        inicio = tope + timedelta(days=1)
        time.sleep(1)

    if not nuevas:
        print("  sin datos nuevos")
        return
    fechas = sorted(nuevas)
    print(f"  {len(fechas)} días nuevos ({fechas[0]} -> {fechas[-1]})")
    if dry_run:
        return
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, columnas, lineterminator="\r\n")
        escritor.writerows(nuevas[fecha] for fecha in fechas)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    clave = os.environ.get("AEMET_API_KEY")
    if not clave:
        sys.exit("Falta la variable de entorno AEMET_API_KEY (clave gratuita de AEMET OpenData).")
    for estacion, ruta in ESTACIONES.items():
        actualizar(estacion, ruta, clave, args.dry_run)


if __name__ == "__main__":
    main()
