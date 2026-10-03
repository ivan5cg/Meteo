from meteodash.ciudad import Ciudad, render_pagina

render_pagina(Ciudad(nombre="Milán", lat=45.464, lon=9.190, tz="Europe/Rome", semana=True, ens_ecmwf=True,
                     pais="italy", zonas_aviso=("lombardia",)),
              titulo="Milán 🇮🇹")
