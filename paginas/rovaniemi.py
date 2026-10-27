from meteodash.ciudad import Ciudad, render_pagina

# Bajo el óvalo auroral: con Kp 2 y el cielo despejado suelen verse auroras
render_pagina(Ciudad(nombre="Rovaniemi", lat=66.503, lon=25.729, tz="Europe/Helsinki", ensemble="icon_eu", nieve=True,
                     nieve_fuera_de_temporada=True, pais="finland", zonas_aviso=("FI014",), kp_auroras=2),
              titulo="Rovaniemi 🇫🇮")
