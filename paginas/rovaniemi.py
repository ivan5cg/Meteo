from meteodash.ciudad import Ciudad, render_pagina
from meteodash.observaciones import Estacion

# Bajo el óvalo auroral: con Kp 2 y el cielo despejado suelen verse auroras.
# La estación del centro solo mide temperatura y humedad: el viento y la lluvia son los del aeropuerto, a 10 km
render_pagina(Ciudad(nombre="Rovaniemi", lat=66.503, lon=25.729, tz="Europe/Helsinki", ensemble="icon_eu", nieve=True,
                     nieve_fuera_de_temporada=True, pais="finland", zonas_aviso=("FI014",), kp_auroras=2,
                     estaciones=(Estacion("fmi", "101928", "estación de tren"), Estacion("fmi", "137190", "aeropuerto")),
                     bandas="datos/bandas/rovaniemi.csv"),
              titulo="Rovaniemi 🇫🇮")
