from meteodash.ciudad import Ciudad, render_pagina

render_pagina(Ciudad(
    nombre="Madrid",
    lat=40.41,
    lon=-3.659,
    estacion_aemet="3195",  # Retiro
    historico="datos/retiro_1950.csv",
    semana=True,
    gefs=True,
    camaras=tuple(
        f"https://informo.madrid.es/cameras/Camara{codigo}.jpg"
        for codigo in ["03310", "14303", "01304", "07306", "04301", "12305"]
    ),
    mapas_arome="Madrid",
))
