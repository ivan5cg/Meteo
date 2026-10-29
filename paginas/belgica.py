from meteodash.ciudad import Ciudad, render_grupo
from meteodash.observaciones import Estacion

# Zonas de aviso: provincias, con el nombre en neerlandés, francés o inglés según el idioma del aviso.
# Observaciones y rangos habituales de las estaciones del KMI; Brujas no tiene ninguna representativa (Zeebrugge, la más
# cercana, está en la costa)
render_grupo("Bélgica 🇧🇪", [
    Ciudad(nombre, lat, lon, tz="Europe/Brussels", presion_y_cape=False, pais="belgium", zonas_aviso=zonas,
           estaciones=(Estacion("kmi", codigo, estacion),) if codigo else (),
           bandas=f"datos/bandas/{bandas}.csv" if bandas else None)
    for nombre, lat, lon, zonas, codigo, estacion, bandas in [
        ("Bruselas", 50.8503, 4.3517, ("brussel", "bruxelles"), "6447", "Uccle", "bruselas"),
        ("Gante", 51.0543, 3.7174, ("oost-vlaanderen", "flandre orientale", "east flanders"), "6434", "Melle", "gante"),
        ("Brujas", 51.2093, 3.2247, ("west-vlaanderen", "flandre occidentale", "west flanders"), None, None, None),
    ]
])
