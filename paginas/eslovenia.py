from meteodash.ciudad import Ciudad, render_grupo

# Fuera del dominio del PE-AROME: el ensemble a 48 h es el ICON-EU EPS.
# Zonas de aviso: regiones de ARSO, por el nombre en esloveno o en inglés (Liubliana en la central, Bled en la noroeste)
render_grupo("Liubliana y Bled 🇸🇮", [
    Ciudad(nombre, lat, lon, tz="Europe/Ljubljana", ensemble="icon_eu", nieve=True, pais="slovenia",
           zonas_aviso=zonas)
    for nombre, lat, lon, zonas in [
        ("Liubliana", 46.051, 14.506, ("osrednj", "central")),
        ("Bled", 46.368, 14.114, ("severozahod", "north-west", "northwest")),
    ]
])
