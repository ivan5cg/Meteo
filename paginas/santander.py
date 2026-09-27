from meteodash.ciudad import Ciudad, render_pagina

render_pagina(Ciudad(
    nombre="Santander",
    lat=43.4661,
    lon=-3.798,
    estacion_aemet="1111X",
    semana=True,
    gefs=True,
))
