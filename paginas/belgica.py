from meteodash.ciudad import Ciudad, render_grupo

render_grupo("Bélgica 🇧🇪", [
    Ciudad(nombre, lat, lon, tz="Europe/Brussels", presion_y_cape=False)
    for nombre, lat, lon in [
        ("Bruselas", 50.8503, 4.3517),
        ("Gante", 51.0543, 3.7174),
        ("Brujas", 51.2093, 3.2247),
    ]
])
