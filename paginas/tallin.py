from meteodash.ciudad import Ciudad, render_pagina
from meteodash.observaciones import Estacion

# Estonia no pone código a las zonas de aviso: se buscan por el nombre del condado de Harju.
# Observación: METAR del aeropuerto, a 5 km (los datos abiertos del servicio estonio llegan con un día de retraso)
render_pagina(Ciudad(nombre="Tallin", lat=59.437, lon=24.754, tz="Europe/Tallinn", ensemble="icon_eu", nieve=True,
                     pais="estonia", zonas_aviso=("EE004", "harju"),
                     estaciones=(Estacion("metar", "EETN", "aeropuerto"),), bandas="datos/bandas/tallin.csv"),
              titulo="Tallin 🇪🇪")
