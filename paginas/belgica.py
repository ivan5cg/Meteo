from meteodash.ciudad import Ciudad, render_grupo

# Zonas de aviso: provincias, con el nombre en neerlandés, francés o inglés según el idioma del aviso
render_grupo("Bélgica 🇧🇪", [
    Ciudad(nombre, lat, lon, tz="Europe/Brussels", presion_y_cape=False, semana=True, ens_ecmwf=True,
           pais="belgium", zonas_aviso=zonas)
    for nombre, lat, lon, zonas in [
        ("Bruselas", 50.8503, 4.3517, ("brussel", "bruxelles")),
        ("Gante", 51.0543, 3.7174, ("oost-vlaanderen", "flandre orientale", "east flanders")),
        ("Brujas", 51.2093, 3.2247, ("west-vlaanderen", "flandre occidentale", "west flanders")),
    ]
])
