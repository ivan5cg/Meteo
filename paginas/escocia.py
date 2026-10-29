from meteodash.ciudad import Ciudad, render_grupo
from meteodash.observaciones import Estacion

# Fuera del dominio del PE-AROME: el ensemble a 48 h es el de la Met Office (MOGREPS-UK 2 km + MOGREPS-G).
# Zonas de aviso: regiones de la Met Office en Meteoalarm. Observación: METAR de los aeropuertos de Edimburgo e
# Inverness (la Met Office solo da las de sus estaciones con clave); rangos habituales, solo los de Edimburgo
render_grupo("Edimburgo y Highlands 🏴󠁧󠁢󠁳󠁣󠁴󠁿", [
    Ciudad(nombre, lat, lon, tz="Europe/London", ensemble="ukmo", presion_y_cape=False,
           nieve=nieve, pais="united-kingdom", zonas_aviso=zonas,
           estaciones=(Estacion("metar", metar, "aeropuerto"),) if metar else (), bandas=bandas)
    for nombre, lat, lon, nieve, zonas, metar, bandas in [
        ("Edimburgo", 55.953, -3.189, False, ("lothian",), "EGPH", "datos/bandas/edimburgo.csv"),
        ("Inverness", 57.478, -4.224, True, ("highland",), "EGPE", None),
        ("Fort William", 56.819, -5.105, True, ("highland",), None, None),
        ("Aviemore", 57.195, -3.826, True, ("highland", "grampian"), None, None),
        ("Portree (Skye)", 57.413, -6.196, True, ("highland",), None, None),
    ]
])
