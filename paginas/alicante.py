from meteodash.ciudad import Ciudad, render_pagina

render_pagina(Ciudad(
    nombre="Alicante",
    lat=38.346,
    lon=-0.48,
    estacion_aemet="8025",
    bandas="datos/bandas/alicante.csv",
    zonas_aviso=("ES241",),  # Litoral sur de Alicante
))
