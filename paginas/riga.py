from meteodash.ciudad import Ciudad, render_pagina
from meteodash.observaciones import Estacion

# Letonia delimita los avisos en tierra con polígonos y no con códigos; por el nombre se colarían los del golfo de Riga.
# Observación de LVĢMC en la Universidad, en el centro (no hay un registro diario largo y público para los rangos)
render_pagina(Ciudad(nombre="Riga", lat=56.949, lon=24.105, tz="Europe/Riga", ensemble="icon_eu", nieve=True,
                     pais="latvia", avisos_por_poligono=True, estaciones=(Estacion("lvgmc", "RIGASLU", "Universidad"),)),
              titulo="Riga 🇱🇻")
