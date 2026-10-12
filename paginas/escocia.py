from meteodash.ciudad import Ciudad, render_grupo

# Fuera del dominio del PE-AROME: el ensemble a 48 h es el de la Met Office (MOGREPS-UK 2 km + MOGREPS-G).
# Zonas de aviso: regiones de la Met Office en Meteoalarm
render_grupo("Edimburgo y Highlands 🏴󠁧󠁢󠁳󠁣󠁴󠁿", [
    Ciudad(nombre, lat, lon, tz="Europe/London", ensemble="ukmo", presion_y_cape=False, semana=True, ens_ecmwf=True,
           nieve=nieve, pais="united-kingdom", zonas_aviso=zonas)
    for nombre, lat, lon, nieve, zonas in [
        ("Edimburgo", 55.953, -3.189, False, ("lothian",)),
        ("Inverness", 57.478, -4.224, True, ("highland",)),
        ("Fort William", 56.819, -5.105, True, ("highland",)),
        ("Aviemore", 57.195, -3.826, True, ("highland", "grampian")),
        ("Portree (Skye)", 57.413, -6.196, True, ("highland",)),
    ]
])
