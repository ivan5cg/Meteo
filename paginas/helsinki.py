from meteodash.ciudad import Ciudad, render_pagina
from meteodash.observaciones import Estacion

# Fuera del dominio del PE-AROME: el ensemble a 48 h es el ICON-EU EPS
render_pagina(Ciudad(nombre="Helsinki", lat=60.170, lon=24.941, tz="Europe/Helsinki", ensemble="icon_eu", nieve=True,
                     pais="finland", zonas_aviso=("FI034",),  # Uusimaa
                     estaciones=(Estacion("fmi", "100971", "Kaisaniemi"),), bandas="datos/bandas/helsinki.csv"),
              titulo="Helsinki 🇫🇮")
