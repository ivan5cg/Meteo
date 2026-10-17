from meteodash.ciudad import Ciudad, render_pagina

render_pagina(Ciudad(nombre="Dublín", lat=53.338, lon=-6.28, tz="Europe/Dublin", pais="ireland", zonas_aviso=("EI07",)),  # condado de Dublín (código FIPS)
              titulo="Dublín 🇮🇪")
