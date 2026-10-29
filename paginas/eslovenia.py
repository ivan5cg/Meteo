from meteodash.ciudad import Ciudad, render_grupo
from meteodash.observaciones import Estacion

# Fuera del dominio del PE-AROME: el ensemble a 48 h es el ICON-EU EPS.
# Zonas de aviso: regiones de ARSO, por el nombre en esloveno o en inglés (Liubliana en la central, Bled en la noroeste).
# Observaciones de ARSO: Bežigrad, en Liubliana, y el aeródromo de Lesce, a 4,5 km de Bled
render_grupo("Liubliana y Bled 🇸🇮", [
    Ciudad(nombre, lat, lon, tz="Europe/Ljubljana", ensemble="icon_eu", nieve=True, pais="slovenia",
           zonas_aviso=zonas, estaciones=(Estacion("arso", codigo, estacion),), bandas=f"datos/bandas/{bandas}.csv")
    for nombre, lat, lon, zonas, codigo, estacion, bandas in [
        ("Liubliana", 46.051, 14.506, ("osrednj", "central"), "LJUBL-ANA_BEZIGRAD", "Bežigrad", "liubliana"),
        ("Bled", 46.368, 14.114, ("severozahod", "north-west", "northwest"), "LESCE", "aeródromo de Lesce", "bled"),
    ]
])
