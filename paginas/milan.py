from meteodash.ciudad import Ciudad, render_pagina
from meteodash.observaciones import Estacion

# Observación: METAR de Linate, a 7 km (los datos de ARPA Lombardia ya no se pueden consultar sin registro)
render_pagina(Ciudad(nombre="Milán", lat=45.464, lon=9.190, tz="Europe/Rome", pais="italy", zonas_aviso=("lombardia",),
                     estaciones=(Estacion("metar", "LIML", "aeropuerto de Linate"),),
                     bandas="datos/bandas/milan.csv"),
              titulo="Milán 🇮🇹")
