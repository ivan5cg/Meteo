"""Configuración de los lugares de cada página (ver ciudad.Ciudad), compartida por sus páginas y por la portada.

Auroras (`kp_auroras`): el Kp con el que el borde del óvalo auroral llega a la latitud geomagnética del lugar, redondeado
hacia arriba. Según la NOAA, el borde está hacia los 66º geomagnéticos con Kp 0 y baja unos 2º por cada punto de Kp;
latitud geomagnética con el dipolo del IGRF de 2025 (polo norte en 80,8º N 72,7º O).
"""

from .alertas import Alerta
from .avisos import NWS
from .ciudad import Camara, Ciudad
from .observaciones import Estacion


# Cámaras: mejor de sitios céntricos o emblemáticos con imagen fija (JPG con URL estable) o vídeo HLS que se pueda
# reproducir fuera de su web; si no hay, las de carreteras a unos pocos km. Sin ninguna así: Kilmahog, Bélgica (la de
# la Grand-Place no deja reproducirse fuera de la web del ayuntamiento y las de verkeerscentrum.be devuelven 403),
# Riga (las de carretera están a 10-20 km y la imagen va dentro de las teselas de su mapa), Nueva York (nyctmc.org
# bloquea peticiones desde fuera de EE. UU.) y Asia salvo Hong Kong (sin feeds JPG/HLS abiertos y estables)

def _dgt(*camaras):
    return tuple(Camara(f"https://etraffic.dgt.es/camarasEtraffic/{codigo}.jpg", "DGT", nombre)
                 for codigo, nombre in camaras)


def _fintraffic(*camaras):  # cámaras de las estaciones meteorológicas de carretera, cada 10 min
    return tuple(Camara(f"https://weathercam.digitraffic.fi/{codigo}.jpg", "Fintraffic", nombre)
                 for codigo, nombre in camaras)


def _tfl(*camaras):  # JamCams de Transport for London, cada pocos minutos
    return tuple(Camara(f"https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/00001.{codigo}.jpg", "TfL", nombre)
                 for codigo, nombre in camaras)


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
        Camara(f"https://informo.madrid.es/cameras/Camara{codigo}.jpg", "Ayuntamiento de Madrid")
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
    camaras=_dgt(("168018", "AP-51 km 104, llegando a Ávila"), ("168017", "AP-51 km 99")),
    mapas_arome="Ávila",
)

ALICANTE = Ciudad(
    nombre="Alicante",
    lat=38.346,
    lon=-0.48,
    estacion_aemet="8025",
    bandas="datos/bandas/alicante.csv",
    zonas_aviso=("ES241",),  # Litoral sur de Alicante
    mar=True,
    camaras=(Camara("https://streaming.comunitatvalenciana.com/webcam/AlicanteCentro/manifest.m3u8",
                    "Turisme Comunitat Valenciana", "Centro, hacia la plaza del Ayuntamiento"),
             *_dgt(("176529", "A-31 km 234, entrada a Alicante"), ("1701", "A-70 km 21,6"))),
    mapas_arome="Alicante",
)

SANTANDER = Ciudad(
    nombre="Santander",
    lat=43.4661,
    lon=-3.798,
    estacion_aemet="1111X",
    bandas="datos/bandas/santander.csv",
    zonas_aviso=("ES133",),  # Litoral cántabro
    mar=True,
    camaras=_dgt(("505", "S-10 km 4, Maliaño"), ("187681", "S-30 km 6,5"), ("503", "A-67 km 197, Mortera")),
    mapas_arome="Santander",
)

TORRELAVEGA = Ciudad(
    nombre="Torrelavega",
    lat=43.35,
    lon=-4.047,
    estacion_aemet="1154H",  # Sierrapando
    bandas="datos/bandas/torrelavega.csv",
    zonas_aviso=("ES133",),  # Litoral cántabro
    mapas_arome="Torrelavega",
    camaras=_dgt(("1527", "A-8 km 232, Torrelavega"), ("1526", "A-8 km 228"), ("1516", "A-67 km 177, Cartes"),
                 ("1515", "A-67 km 170, Corrales de Buelna")),
)

# Observación solo donde hay una estación representativa: la de Búbal está a 1,7 km de Tramacastilla. Para Sallent
# no lo es (a 8 km y 175 m más abajo; Formigal, 500 m más arriba) ni hay ninguna a la altura del punto de Torla-Ordesa.
# Los tres están en la zona de montaña del Pirineo aragonés de AEMET y en la del boletín de aludes del Pirineo navarro
# y aragonés
PIRINEOS = [
    Ciudad(nombre, lat, lon, presion_y_cape=False, nieve=True, nieve_fuera_de_temporada=True, calidad_aire=False,
           zonas_aviso=("ES099",), estaciones=estaciones,  # Pirineo oscense
           montaña_aemet=("arn1", "Pirineo aragonés"), aludes_aemet="1", camaras=camaras)
    for nombre, lat, lon, estaciones, camaras in [
        ("Sallent de Gállego", 42.77147619941324, -0.3307980233574127, (),
         _dgt(("164373", "A-136 km 17,8, Sallent"), ("166454", "A-136 km 21, Formigal"))),
        ("Tramacastilla de Tena", 42.71396690891642, -0.3163249093993428,
         (Estacion("aemet", "9453X", "Embalse de Búbal"),),
         _dgt(("180323", "A-136 km 8,8, Saqués"), ("183192", "N-260a km 505, Biescas"))),
        ("Torla-Ordesa", 42.640, 0.000, (),
         (Camara("https://images-webcams.windy.com/03/1456992103/current/full/1456992103.jpg",
                 "Windy Webcams", "Refugio de Góriz, Ordesa"),)),
    ]
]

# ---------------------------------------------------------------- Europa

# Observación de Met Éireann en Phoenix Park, a 5 km: temperatura en grados enteros y sin viento
DUBLIN = Ciudad(nombre="Dublín", lat=53.338, lon=-6.28, tz="Europe/Dublin", pais="ireland",
                zonas_aviso=("EI07",),  # condado de Dublín (código FIPS)
                estaciones=(Estacion("met_eireann", "phoenix-park", "Phoenix Park"),), bandas="datos/bandas/dublin.csv",
                camaras=tuple(Camara(f"https://irecam.carsprogram.org/Kapsch/time_logo_cctv-{codigo}.jpg", "TII", nombre)
                              for codigo, nombre in [("700", "N7 en el enlace con la M50"),
                                                     ("554", "M50 en Ballymount")]))

# Observación: METAR de Linate, a 7 km (los datos de ARPA Lombardia ya no se pueden consultar sin registro)
MILAN = Ciudad(nombre="Milán", lat=45.464, lon=9.190, tz="Europe/Rome", pais="italy", zonas_aviso=("lombardia",),
               estaciones=(Estacion("metar", "LIML", "aeropuerto de Linate"),), bandas="datos/bandas/milan.csv",
               camaras=(Camara("https://www.meteogiuliacci.it/webcam/milano.jpg", "MeteoGiuliacci"),))

# Fuera del dominio del PE-AROME: el ensemble a 48 h es el ICON-EU EPS.
# Zonas de aviso: regiones de ARSO, por el nombre en esloveno o en inglés (Liubliana en la central, Bled en la noroeste).
# Observaciones de ARSO: Bežigrad, en Liubliana, y el aeródromo de Lesce, a 4,5 km de Bled.
# Cámaras: las de la estación de Bežigrad (ARSO), una por rumbo, y las de la autopista en Vrba, a 4 km de Bled (DARS)
_ARSO_WEBCAM = "https://meteo.arso.gov.si/uploads/probase/www/observ/webcam/LJUBL-ANA_BEZIGRAD_dir/siwc_LJUBL-ANA_BEZIGRAD"
ESLOVENIA = [
    Ciudad(nombre, lat, lon, tz="Europe/Ljubljana", ensemble="icon_eu", nieve=True, pais="slovenia",
           zonas_aviso=zonas, estaciones=(Estacion("arso", codigo, estacion),), bandas=f"datos/bandas/{bandas}.csv",
           camaras=camaras)
    for nombre, lat, lon, zonas, codigo, estacion, bandas, camaras in [
        ("Liubliana", 46.051, 14.506, ("osrednj", "central"), "LJUBL-ANA_BEZIGRAD", "Bežigrad", "liubliana",
         tuple(Camara(f"{_ARSO_WEBCAM}_{rumbo}.jpg", "ARSO", f"Bežigrad, hacia el {texto}")
               for rumbo, texto in [("n", "norte"), ("ne", "nordeste"), ("e", "este"), ("se", "sudeste"),
                                    ("s", "sur"), ("nw", "noroeste")])),
        ("Bled", 46.368, 14.114, ("severozahod", "north-west", "northwest"), "LESCE", "aeródromo de Lesce", "bled",
         tuple(Camara(f"https://kamere.dars.si/kamere/Hrusica/Vrba_smer_{sentido}.jpg", "DARS", f"A2 en Vrba, {texto}")
               for sentido, texto in [("Jesenice", "hacia Jesenice"), ("Ljubljana", "hacia Liubliana")])),
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
# Lugares: Edimburgo y las paradas de la excursión del domingo 22/11/2026, en el orden de la ruta: Kilmahog (junto a
# Callander), Glen Coe (mirador de las Tres Hermanas, en la A82), Fort Augustus (Lago Ness), Inverness y Pitlochry.
# Zonas de aviso: regiones de la Met Office en Meteoalarm («Lothian & Borders», «Highlands & Eilean Siar» y
# «Central, Tayside & Fife», que incluye Stirling y Perth and Kinross). Observación: METAR de los aeropuertos de
# Edimburgo e Inverness (la Met Office solo da las de sus estaciones con clave); rangos habituales, solo los de
# Edimburgo. Auroras: latitud geomagnética de 58,1º en Edimburgo y de 58,6-59,8º en el resto (Kp 4 en todos)
# Avisos propios (ver alertas.py): lo que importa en cada parada, en las horas en que la excursión suele pasar por allí
# (salida de Edimburgo a las 7:00 y vuelta hacia las 20:30). Los umbrales son orientativos: se pueden ajustar aquí
ALERTAS_ESCOCIA = {
    "Edimburgo": (
        Alerta("rachas", 60, "Viento fuerte: cuidado en Calton Hill, la explanada del castillo y los puentes; el "
                             "paraguas no sirve de mucho", horas=(8, 23)),
        Alerta("helada", 0, "Posible hielo en los adoquines de la Royal Mile, Cockburn St y Victoria St: calzado con "
                            "buena suela", horas=(6, 23)),
        Alerta("lluvia", 5, "Tarde y noche de lluvia: cuenta con ella para el paseo hasta la cena y la vuelta",
               horas=(17, 23)),
    ),
    "Kilmahog": (
        Alerta("helada", 0, "Hielo en la carretera de subida (A84) y en el camino al cercado de las vacas peludas",
               horas=(7, 11)),
        Alerta("lluvia", 2, "Lluvia en la parada de las vacas peludas: barro en el cercado, impermeable a mano",
               horas=(8, 11)),
    ),
    "Glen Coe": (
        Alerta("rachas", 60, "Viento fuerte en los miradores de las Tres Hermanas: cuidado al borde y con el móvil, y "
                             "mucho más frío del que marca el termómetro", horas=(10, 14)),
        Alerta("nieve", 1, "Nieve en Glen Coe y Rannoch Moor (A82): puede retrasar la ruta o cambiar las paradas",
               horas=(8, 15)),
        Alerta("lluvia", 4, "Lluvia y nubes bajas: las Tres Hermanas pueden quedar tapadas", horas=(10, 14)),
    ),
    "Fort Augustus": (
        Alerta("rachas", 50, "Viento en el Lago Ness: el barco puede moverse mucho o no salir", horas=(12, 16)),
        Alerta("lluvia", 3, "Lluvia a la hora de comer: mejor un sitio a cubierto que comida para llevar",
               horas=(12, 16)),
    ),
    "Inverness": (
        Alerta("rachas", 60, "Viento fuerte en el paseo junto al río Ness", horas=(15, 18)),
        Alerta("lluvia", 3, "Lluvia en el paseo por Inverness", horas=(15, 18)),
    ),
    "Pitlochry": (
        Alerta("cota_nieve", 500, "Nieve en la A9 por el puerto de Drumochter (unos 460 m), el camino de vuelta: "
                                  "puede retrasar la llegada a Edimburgo", horas=(16, 21)),
        Alerta("helada", 0, "Hielo en la carretera de vuelta y en las aceras de Pitlochry", horas=(17, 21)),
    ),
}

ESCOCIA = [
    Ciudad(nombre, lat, lon, tz="Europe/London", ensemble="ukmo", presion_y_cape=False,
           nieve=nieve, pais="united-kingdom", zonas_aviso=zonas,
           estaciones=(Estacion("metar", metar, "aeropuerto"),) if metar else (), bandas=bandas, kp_auroras=kp,
           camaras=camaras, alertas=ALERTAS_ESCOCIA.get(nombre, ()))
    for nombre, lat, lon, nieve, zonas, metar, bandas, kp, camaras in [
        ("Edimburgo", 55.953, -3.189, False, ("lothian",), "EGPH", "datos/bandas/edimburgo.csv", 4,
         (Camara("https://images-webcams.windy.com/75/1653631975/current/full/1653631975.jpg", "Windy Webcams"),)),
        ("Kilmahog", 56.248, -4.245, True, ("tayside",), None, None, 4, ()),
        ("Glen Coe", 56.668, -4.986, True, ("highland",), None, None, 4,
         (Camara("https://www.winterhighland.info/cams/glencoe/base.jpeg", "Glencoe Mountain Resort", "Base"),
          Camara("https://www.winterhighland.info/cams/glencoe/base1200.jpeg", "Glencoe Mountain Resort",
                 "Cota 365 m (1200 ft)"))),
        ("Fort Augustus", 57.143, -4.681, True, ("highland",), None, None, 4,
         (Camara("https://abbeycottagelochness.co.uk/cams/cam-11.jpg", "Abbey Cottage",
                 "Esclusas del canal de Caledonia"),)),
        ("Inverness", 57.478, -4.224, True, ("highland",), "EGPE", None, 4,
         (Camara("https://images-webcams.windy.com/56/1660716056/current/full/1660716056.jpg", "Windy Webcams"),)),
        ("Pitlochry", 56.704, -3.730, True, ("tayside",), None, None, 4,
         (Camara("https://s153.ipcamlive.com/streams/992tvpk1jicko47ag/snapshot.jpg", "Pitlochry Webcam",
                 "Atholl Road"),)),
    ]
]

# Dentro del dominio del PE-AROME. Zona de aviso: la región de la Met Office «London & South East England».
# Observación: METAR del aeropuerto de London City, a 13 km, en los Docklands. Sin rangos habituales: los datos
# diarios de St James's Park, la estación del centro, solo se descargan con cuenta de CEDA, y en GHCN-Daily solo están
# Heathrow, a 23 km, en el borde oeste de la ciudad y con noches más frías que el centro, y Hampstead, en un alto a
# 137 m y solo hasta 2016. Auroras, no: con una latitud geomagnética de 53,4º harían falta Kp 7 y un cielo sin la luz
# del centro
LONDRES = Ciudad(nombre="Londres", lat=51.508, lon=-0.128,  # Trafalgar Square
                 tz="Europe/London", pais="united-kingdom", zonas_aviso=("london",),
                 estaciones=(Estacion("metar", "EGLC", "aeropuerto de London City"),),
                 camaras=_tfl(("04502", "Puente de Westminster"), ("06502", "Trafalgar Square"),
                              ("06501", "Parliament Square"), ("04223", "Puente de Waterloo"),
                              ("08850", "Marble Arch")))

# ---------------------------------------------------------------- Báltico y Laponia

# Fuera del dominio del PE-AROME: el ensemble a 48 h es el ICON-EU EPS. Auroras: latitud geomagnética de 57,8º
HELSINKI = Ciudad(nombre="Helsinki", lat=60.170, lon=24.941, tz="Europe/Helsinki", ensemble="icon_eu", nieve=True,
                  pais="finland", zonas_aviso=("FI034",),  # Uusimaa
                  estaciones=(Estacion("fmi", "100971", "Kaisaniemi"),), bandas="datos/bandas/helsinki.csv",
                  kp_auroras=5,
                  camaras=_fintraffic(("C0167400", "Ruoholahti"), ("C0167500", "Lauttasaari"), ("C0159000", "Ilmala"),
                                      ("C0158700", "Kivihaka"), ("C0170602", "Munkkiniemi")))

# Bajo el óvalo auroral (latitud geomagnética de 63,6º): con Kp 2 y el cielo despejado suelen verse auroras.
# La estación del centro solo mide temperatura y humedad: el viento y la lluvia son los del aeropuerto, a 10 km
ROVANIEMI = Ciudad(nombre="Rovaniemi", lat=66.503, lon=25.729, tz="Europe/Helsinki", ensemble="icon_eu", nieve=True,
                   nieve_fuera_de_temporada=True, pais="finland", zonas_aviso=("FI014",), kp_auroras=2,
                   estaciones=(Estacion("fmi", "101928", "estación de tren"), Estacion("fmi", "137190", "aeropuerto")),
                   bandas="datos/bandas/rovaniemi.csv",
                   camaras=_fintraffic(("C1455101", "Revontuli, en el centro"), ("C1456801", "Santa Claus Village"),
                                       ("C1452601", "Círculo Polar Ártico"), ("C1455401", "Pöykkölä")))

# Estonia no pone código a las zonas de aviso: se buscan por el nombre del condado de Harju.
# Observación: METAR del aeropuerto, a 5 km (los datos abiertos del servicio estonio llegan con un día de retraso).
# Auroras: latitud geomagnética de 57,1º
TALLIN = Ciudad(nombre="Tallin", lat=59.437, lon=24.754, tz="Europe/Tallinn", ensemble="icon_eu", nieve=True,
                pais="estonia", zonas_aviso=("EE004", "harju"),
                estaciones=(Estacion("metar", "EETN", "aeropuerto"),), bandas="datos/bandas/tallin.csv", kp_auroras=5,
                camaras=tuple(
                    Camara(f"https://ristmikud.tallinn.ee/last/cam{codigo}.jpg", "Tallinna Transpordiamet", nombre)
                    for codigo, nombre in [("103", "Viru väljak (hacia Mere pst)"),
                                           ("104", "Viru väljak (hacia Pärnu mnt)"),
                                           ("001", "Estonia pst · Teatri väljak"),
                                           ("056", "Pärnu mnt · Draamateater")]
                ))

# Letonia delimita los avisos en tierra con polígonos y no con códigos; por el nombre se colarían los del golfo de Riga.
# Observación de LVĢMC en la Universidad, en el centro (no hay un registro diario largo y público para los rangos).
# Auroras: latitud geomagnética de 54,8º, solo con tormentas fuertes
RIGA = Ciudad(nombre="Riga", lat=56.949, lon=24.105, tz="Europe/Riga", ensemble="icon_eu", nieve=True, pais="latvia",
              avisos_por_poligono=True, estaciones=(Estacion("lvgmc", "RIGASLU", "Universidad"),), kp_auroras=6)

# ---------------------------------------------------------------- América

# Fuera de Europa: el ensemble a 48 h es el GEFS de la NOAA y el del medio plazo, el ECMWF, con el GFS determinista
# (ver fuentes.MEDIO_PLAZO). Avisos del Servicio Meteorológico Nacional (NWS) para el punto, en lugar de Meteoalarm.
# Observación: METAR de Central Park, a 2,7 km (en EE. UU. el parte da la temperatura en décimas); rangos habituales de
# la misma estación. Auroras, no: con una latitud geomagnética de unos 50º, solo con Kp 9. Altitud del suelo del USGS
# (3DEP, 1 m): el modelo del terreno de Open-Meteo da 105 m, la de los tejados de Midtown
NUEVA_YORK = Ciudad(nombre="Nueva York", lat=40.758, lon=-73.985,  # Times Square, en Midtown (Manhattan)
                    tz="America/New_York", elevacion=15, ensemble="gefs", medio="ecmwf", nieve=True, pais=NWS,
                    estaciones=(Estacion("metar", "KNYC", "Central Park"),), bandas="datos/bandas/nueva_york.csv")

# ---------------------------------------------------------------- Asia

# Como en Nueva York: el ensemble a 48 h es el GEFS de la NOAA y el del medio plazo, el ECMWF, con el GFS determinista.
# Sin avisos oficiales: Meteoalarm y el NWS no llegan a Asia. Altitud del suelo: la del modelo del terreno de Open-Meteo
# vale en todos los puntos (no da la de los tejados, como en Times Square).
# Observación: METAR del aeropuerto solo si está a 20 km o menos, en llano y dentro de la ciudad (Haneda, Hongqiao,
# Subang y Don Mueang). No lo son Beijing Capital (26 km, en el campo, con noches más frías que el centro), Noi Bai
# (22 km, al otro lado del río Rojo y en el campo), Chek Lap Kok (26 km, junto a la isla de Lantau) ni Chongqing
# Jiangbei (19 km y 150 m más arriba).
# Rangos habituales, solo en Beijing y Chongqing: en el resto, GHCN-Daily solo tiene los resúmenes diarios GSOD, con
# huecos (de 1991 a 2020 falta la mínima del 22 % de los días en Bangkok, del 39 % en Subang y del 45 % en Tokio; Noi
# Bai, casi siempre), o el registro del centro se corta (el Observatorio de Hong Kong, en 1992; Xujiahui, en Shanghái,
# tiene 10 años completos, y Baoshan está a 19 km, junto al estuario del Yangtsé)
def _asia(nombre, lat, lon, tz, metar=None, aeropuerto=None, **opciones):
    estaciones = (Estacion("metar", metar, f"aeropuerto de {aeropuerto}"),) if metar else ()
    return Ciudad(nombre, lat, lon, tz=tz, ensemble="gefs", medio="ecmwf", estaciones=estaciones, **opciones)


TOKIO = _asia("Tokio", 35.681, 139.767, "Asia/Tokyo", "RJTT", "Haneda", nieve=True)  # estación de Tokio, a 14 km
BEIJING = _asia("Beijing", 39.904, 116.397, "Asia/Shanghai", nieve=True,  # plaza de Tiananmén
                bandas="datos/bandas/beijing.csv")
SHANGHAI = _asia("Shanghái", 31.230, 121.474, "Asia/Shanghai", "ZSSS", "Hongqiao")  # plaza del Pueblo, a 13 km
CHONGQING = _asia("Chongqing", 29.557, 106.577, "Asia/Shanghai",  # Jiefangbei, en la península de Yuzhong
                  bandas="datos/bandas/chongqing.csv")
HONG_KONG = _asia("Hong Kong", 22.302, 114.174, "Asia/Hong_Kong",  # Tsim Sha Tsui, junto al Observatorio
                  camaras=tuple(
                      Camara(f"https://tdcctv.data.one.gov.hk/{codigo}.JPG", "Transport Department", nombre)
                      for codigo, nombre in [("K101F", "Nathan Rd · Salisbury Rd (Tsim Sha Tsui)"),
                                             ("K102F", "Nathan Rd · Peking Rd (Tsim Sha Tsui)"),
                                             ("K802F", "Chatham Rd South · Austin Ave"),
                                             ("H201F", "Gloucester Rd (Wan Chai)")]
                  ))
HANOI = _asia("Hanói", 21.028, 105.852, "Asia/Ho_Chi_Minh")  # lago Hoan Kiem
BANGKOK = _asia("Bangkok", 13.746, 100.535, "Asia/Bangkok", "VTBD", "Don Mueang")  # Siam, a 20 km
KUALA_LUMPUR = _asia("Kuala Lumpur", 3.148, 101.694, "Asia/Kuala_Lumpur", "WMSA", "Subang")  # plaza Merdeka, a 16 km

# Yakutsk, la gran ciudad más fría del mundo: medias de -40º en enero y de +20º en julio, sobre el permafrost. Nieve de
# octubre a mayo (también fuera de MESES_NIEVE). Observación: METAR del aeropuerto, a 7 km, en llano y en el borde de
# la ciudad. Rangos habituales: GHCN-Daily tiene la estación de Yakutsk (OMM 24959) completa; falta generar su CSV
# (python generar_bandas.py yakutsk). Auroras, no: con una latitud geomagnética de 53,4º (la del dipolo; los 62º de
# latitud no cuentan) harían falta Kp 7, como en Londres
YAKUTSK = _asia("Yakutsk", 62.028, 129.732, "Asia/Yakutsk", "UEEE", "Yakutsk",  # plaza de Lenin
                nieve=True, nieve_fuera_de_temporada=True)

# ---------------------------------------------------------------- Portada

# Secciones de la navegación: (página, lugares que muestra)
SECCIONES = {
    "España": [("paginas/madrid.py", [MADRID]), ("paginas/avila.py", [AVILA]), ("paginas/alicante.py", [ALICANTE]),
               ("paginas/santander.py", [SANTANDER]), ("paginas/torrelavega.py", [TORRELAVEGA]),
               ("paginas/pirineos.py", PIRINEOS)],
    "Europa": [("paginas/dublin.py", [DUBLIN]), ("paginas/milan.py", [MILAN]), ("paginas/eslovenia.py", ESLOVENIA),
               ("paginas/belgica.py", BELGICA), ("paginas/escocia.py", ESCOCIA), ("paginas/londres.py", [LONDRES])],
    "Báltico y Laponia": [("paginas/helsinki.py", [HELSINKI]), ("paginas/rovaniemi.py", [ROVANIEMI]),
                          ("paginas/tallin.py", [TALLIN]), ("paginas/riga.py", [RIGA])],
    "América": [("paginas/nueva_york.py", [NUEVA_YORK])],
    "Asia": [("paginas/tokio.py", [TOKIO]), ("paginas/beijing.py", [BEIJING]), ("paginas/shanghai.py", [SHANGHAI]),
             ("paginas/chongqing.py", [CHONGQING]), ("paginas/hong_kong.py", [HONG_KONG]),
             ("paginas/hanoi.py", [HANOI]), ("paginas/bangkok.py", [BANGKOK]),
             ("paginas/kuala_lumpur.py", [KUALA_LUMPUR]), ("paginas/yakutsk.py", [YAKUTSK])],
}
