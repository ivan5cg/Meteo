from meteodash.ciudad import Ciudad, render_pagina

render_pagina(Ciudad(
    nombre="Ávila",
    lat=40.659,
    lon=-4.680,
    estacion_aemet="2444",
    historico="datos/avila_1990.csv",
    semana=True,
    ens_ecmwf=True,
    nieve=True,
    zonas_aviso=("ES137",),  # Meseta de Ávila
))
