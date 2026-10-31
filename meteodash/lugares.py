"""Configuración de los lugares de cada página (ver ciudad.Ciudad), compartida por sus páginas y por la portada.

Auroras (`kp_auroras`): el Kp con el que el borde del óvalo auroral llega a la latitud geomagnética del lugar, redondeado
hacia arriba. Según la NOAA, el borde está hacia los 66º geomagnéticos con Kp 0 y baja unos 2º por cada punto de Kp;
latitud geomagnética con el dipolo del IGRF de 2025 (polo norte en 80,8º N 72,7º O).
"""

from .ciudad import Ciudad
from .observaciones import Estacion

# ---------------------------------------------------------------- España

MADRID = Ciudad(
    nombre="Madrid",
    lat=40.41,
    lon=-3.659,
    estacion_aemet="3195",  # Retiro
    historico="datos/retiro_1950.csv",
    ccaa_aemet=("mad", "Comunidad de Madrid"),
    resumen_mensual=True,
    zonas_aviso=("ES219",),  # Metropolitana y Henares
    camaras=tuple(
        f"https://informo.madrid.es/cameras/Camara{codigo}.jpg"
        for codigo in ["03310", "14303", "01304", "07306", "04301", "12305"]
    ),
    mapas_arome="Madrid",
)

AVILA = Ciudad(
    nombre="Ávila",
    lat=40.659,
    lon=-4.680,
    estacion_aemet="2444",
    historico="datos/avila_1990.csv",
    ccaa_aemet=("cle", "Castilla y León"),
    resumen_mensual=True,
    nieve=True,
    zonas_aviso=("ES137",),  # Meseta de Ávila
)

ALICANTE = Ciudad(
    nombre="Alicante",
    lat=38.346,
    lon=-0.48,
    estacion_aemet="8025",
    bandas="datos/bandas/alicante.csv",
    zonas_aviso=("ES241",),  # Litoral sur de Alicante
    mar=True,
)

SANTANDER = Ciudad(
    nombre="Santander",
    lat=43.4661,
    lon=-3.798,
    estacion_aemet="1111X",
    bandas="datos/bandas/santander.csv",
    zonas_aviso=("ES133",),  # Litoral cántabro
    mar=True,
)

TORRELAVEGA = Ciudad(
    nombre="Torrelavega",
    lat=43.35,
    lon=-4.047,
    estacion_aemet="1154H",  # Sierrapando
    bandas="datos/bandas/torrelavega.csv",
    zonas_aviso=("ES133",),  # Litoral cántabro
    mapas_arome="Torrelavega",
)

# Observación solo donde hay una estación representativa: la de Búbal está a 1,7 km de Tramacastilla. Para Sallent
# no lo es (a 8 km y 175 m más abajo; Formigal, 500 m más arriba) ni hay ninguna a la altura del punto de Torla-Ordesa.
# Los tres están en la zona de montaña del Pirineo aragonés de AEMET y en la del boletín de aludes del Pirineo navarro
# y aragonés
PIRINEOS = [
    Ciudad(nombre, lat, lon, presion_y_cape=False, nieve=True, nieve_fuera_de_temporada=True, calidad_aire=False,
           zonas_aviso=("ES099",), estaciones=estaciones,  # Pirineo oscense
           montaña_aemet=("arn1", "Pirineo aragonés"), aludes_aemet="1")
    for nombre, lat, lon, estaciones in [
        ("Sallent de Gállego", 42.77147619941324, -0.3307980233574127, ()),
        ("Tramacastilla de Tena", 42.71396690891642, -0.3163249093993428,
         (Estacion("aemet", "9453X", "Embalse de Búbal"),)),
        ("Torla-Ordesa", 42.640, 0.000, ()),
    ]
]

# ---------------------------------------------------------------- Europa

# Observación de Met Éireann en Phoenix Park, a 5 km: temperatura en grados enteros y sin viento
DUBLIN = Ciudad(nombre="Dublín", lat=53.338, lon=-6.28, tz="Europe/Dublin", pais="ireland",
                zonas_aviso=("EI07",),  # condado de Dublín (código FIPS)
                estaciones=(Estacion("met_eireann", "phoenix-park", "Phoenix Park"),), bandas="datos/bandas/dublin.csv")

# Observación: METAR de Linate, a 7 km (los datos de ARPA Lombardia ya no se pueden consultar sin registro)
MILAN = Ciudad(nombre="Milán", lat=45.464, lon=9.190, tz="Europe/Rome", pais="italy", zonas_aviso=("lombardia",),
               estaciones=(Estacion("metar", "LIML", "aeropuerto de Linate"),), bandas="datos/bandas/milan.csv")

# Fuera del dominio del PE-AROME: el ensemble a 48 h es el ICON-EU EPS.
# Zonas de aviso: regiones de ARSO, por el nombre en esloveno o en inglés (Liubliana en la central, Bled en la noroeste).
# Observaciones de ARSO: Bežigrad, en Liubliana, y el aeródromo de Lesce, a 4,5 km de Bled
ESLOVENIA = [
    Ciudad(nombre, lat, lon, tz="Europe/Ljubljana", ensemble="icon_eu", nieve=True, pais="slovenia",
           zonas_aviso=zonas, estaciones=(Estacion("arso", codigo, estacion),), bandas=f"datos/bandas/{bandas}.csv")
    for nombre, lat, lon, zonas, codigo, estacion, bandas in [
        ("Liubliana", 46.051, 14.506, ("osrednj", "central"), "LJUBL-ANA_BEZIGRAD", "Bežigrad", "liubliana"),
        ("Bled", 46.368, 14.114, ("severozahod", "north-west", "northwest"), "LESCE", "aeródromo de Lesce", "bled"),
    ]
]

# Zonas de aviso: provincias, con el nombre en neerlandés, francés o inglés según el idioma del aviso.
# Observaciones y rangos habituales de las estaciones del KMI; Brujas no tiene ninguna representativa (Zeebrugge, la más
# cercana, está en la costa)
BELGICA = [
    Ciudad(nombre, lat, lon, tz="Europe/Brussels", presion_y_cape=False, pais="belgium", zonas_aviso=zonas,
           estaciones=(Estacion("kmi", codigo, estacion),) if codigo else (),
           bandas=f"datos/bandas/{bandas}.csv" if bandas else None)
    for nombre, lat, lon, zonas, codigo, estacion, bandas in [
        ("Bruselas", 50.8503, 4.3517, ("brussel", "bruxelles"), "6447", "Uccle", "bruselas"),
        ("Gante", 51.0543, 3.7174, ("oost-vlaanderen", "flandre orientale", "east flanders"), "6434", "Melle", "gante"),
        ("Brujas", 51.2093, 3.2247, ("west-vlaanderen", "flandre occidentale", "west flanders"), None, None, None),
    ]
]

# Fuera del dominio del PE-AROME: el ensemble a 48 h es el de la Met Office (MOGREPS-UK 2 km + MOGREPS-G).
# Zonas de aviso: regiones de la Met Office en Meteoalarm. Observación: METAR de los aeropuertos de Edimburgo e
# Inverness (la Met Office solo da las de sus estaciones con clave); rangos habituales, solo los de Edimburgo.
# Auroras: latitud geomagnética de 58,1º en Edimburgo y de 59,3-60,0º en las Highlands (Portree, la más alta)
ESCOCIA = [
    Ciudad(nombre, lat, lon, tz="Europe/London", ensemble="ukmo", presion_y_cape=False,
           nieve=nieve, pais="united-kingdom", zonas_aviso=zonas,
           estaciones=(Estacion("metar", metar, "aeropuerto"),) if metar else (), bandas=bandas, kp_auroras=kp)
    for nombre, lat, lon, nieve, zonas, metar, bandas, kp in [
        ("Edimburgo", 55.953, -3.189, False, ("lothian",), "EGPH", "datos/bandas/edimburgo.csv", 4),
        ("Inverness", 57.478, -4.224, True, ("highland",), "EGPE", None, 4),
        ("Fort William", 56.819, -5.105, True, ("highland",), None, None, 4),
        ("Aviemore", 57.195, -3.826, True, ("highland", "grampian"), None, None, 4),
        ("Portree (Skye)", 57.413, -6.196, True, ("highland",), None, None, 3),
    ]
]

# ---------------------------------------------------------------- Báltico y Laponia

# Fuera del dominio del PE-AROME: el ensemble a 48 h es el ICON-EU EPS. Auroras: latitud geomagnética de 57,8º
HELSINKI = Ciudad(nombre="Helsinki", lat=60.170, lon=24.941, tz="Europe/Helsinki", ensemble="icon_eu", nieve=True,
                  pais="finland", zonas_aviso=("FI034",),  # Uusimaa
                  estaciones=(Estacion("fmi", "100971", "Kaisaniemi"),), bandas="datos/bandas/helsinki.csv",
                  kp_auroras=5)

# Bajo el óvalo auroral (latitud geomagnética de 63,6º): con Kp 2 y el cielo despejado suelen verse auroras.
# La estación del centro solo mide temperatura y humedad: el viento y la lluvia son los del aeropuerto, a 10 km
ROVANIEMI = Ciudad(nombre="Rovaniemi", lat=66.503, lon=25.729, tz="Europe/Helsinki", ensemble="icon_eu", nieve=True,
                   nieve_fuera_de_temporada=True, pais="finland", zonas_aviso=("FI014",), kp_auroras=2,
                   estaciones=(Estacion("fmi", "101928", "estación de tren"), Estacion("fmi", "137190", "aeropuerto")),
                   bandas="datos/bandas/rovaniemi.csv")

# Estonia no pone código a las zonas de aviso: se buscan por el nombre del condado de Harju.
# Observación: METAR del aeropuerto, a 5 km (los datos abiertos del servicio estonio llegan con un día de retraso).
# Auroras: latitud geomagnética de 57,1º
TALLIN = Ciudad(nombre="Tallin", lat=59.437, lon=24.754, tz="Europe/Tallinn", ensemble="icon_eu", nieve=True,
                pais="estonia", zonas_aviso=("EE004", "harju"),
                estaciones=(Estacion("metar", "EETN", "aeropuerto"),), bandas="datos/bandas/tallin.csv", kp_auroras=5)

# Letonia delimita los avisos en tierra con polígonos y no con códigos; por el nombre se colarían los del golfo de Riga.
# Observación de LVĢMC en la Universidad, en el centro (no hay un registro diario largo y público para los rangos).
# Auroras: latitud geomagnética de 54,8º, solo con tormentas fuertes
RIGA = Ciudad(nombre="Riga", lat=56.949, lon=24.105, tz="Europe/Riga", ensemble="icon_eu", nieve=True, pais="latvia",
              avisos_por_poligono=True, estaciones=(Estacion("lvgmc", "RIGASLU", "Universidad"),), kp_auroras=6)

# ---------------------------------------------------------------- Portada

# Secciones de la navegación: (página, lugares que muestra)
SECCIONES = {
    "España": [("paginas/madrid.py", [MADRID]), ("paginas/avila.py", [AVILA]), ("paginas/alicante.py", [ALICANTE]),
               ("paginas/santander.py", [SANTANDER]), ("paginas/torrelavega.py", [TORRELAVEGA]),
               ("paginas/pirineos.py", PIRINEOS)],
    "Europa": [("paginas/dublin.py", [DUBLIN]), ("paginas/milan.py", [MILAN]), ("paginas/eslovenia.py", ESLOVENIA),
               ("paginas/belgica.py", BELGICA), ("paginas/escocia.py", ESCOCIA)],
    "Báltico y Laponia": [("paginas/helsinki.py", [HELSINKI]), ("paginas/rovaniemi.py", [ROVANIEMI]),
                          ("paginas/tallin.py", [TALLIN]), ("paginas/riga.py", [RIGA])],
}
