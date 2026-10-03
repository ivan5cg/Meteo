from meteodash.ciudad import Ciudad, render_pagina

render_pagina(Ciudad(
    nombre="Torrelavega",
    lat=43.35,
    lon=-4.047,
    estacion_aemet="1154H",  # Sierrapando
    semana=True,
    ens_ecmwf=True,
    zonas_aviso=("ES133",),  # Litoral cántabro
    mapas_arome="Torrelavega",
))
