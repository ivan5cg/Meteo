from meteodash.ciudad import Ciudad, render_grupo
from meteodash.observaciones import Estacion

# Observación solo donde hay una estación representativa: la de Búbal está a 1,7 km de Tramacastilla. Para Sallent
# no lo es (a 8 km y 175 m más abajo; Formigal, 500 m más arriba) ni hay ninguna a la altura del punto de Torla-Ordesa
render_grupo("Pirineos 🏔️", [
    Ciudad(nombre, lat, lon, presion_y_cape=False, nieve=True, nieve_fuera_de_temporada=True, calidad_aire=False,
           zonas_aviso=("ES099",), estaciones=estaciones)  # Pirineo oscense
    for nombre, lat, lon, estaciones in [
        ("Sallent de Gállego", 42.77147619941324, -0.3307980233574127, ()),
        ("Tramacastilla de Tena", 42.71396690891642, -0.3163249093993428,
         (Estacion("aemet", "9453X", "Embalse de Búbal"),)),
        ("Torla-Ordesa", 42.640, 0.000, ()),
    ]
])
