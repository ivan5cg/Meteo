from meteodash.ciudad import Ciudad, render_pagina
from meteodash.observaciones import Estacion

# Observación de Met Éireann en Phoenix Park, a 5 km: temperatura en grados enteros y sin viento
render_pagina(Ciudad(nombre="Dublín", lat=53.338, lon=-6.28, tz="Europe/Dublin", pais="ireland", zonas_aviso=("EI07",),  # condado de Dublín (código FIPS)
                     estaciones=(Estacion("met_eireann", "phoenix-park", "Phoenix Park"),),
                     bandas="datos/bandas/dublin.csv"),
              titulo="Dublín 🇮🇪")
