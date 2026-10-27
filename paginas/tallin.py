from meteodash.ciudad import Ciudad, render_pagina

# Estonia no pone código a las zonas de aviso: se buscan por el nombre del condado de Harju
render_pagina(Ciudad(nombre="Tallin", lat=59.437, lon=24.754, tz="Europe/Tallinn", ensemble="icon_eu", nieve=True,
                     pais="estonia", zonas_aviso=("EE004", "harju")),
              titulo="Tallin 🇪🇪")
