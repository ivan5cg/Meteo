from meteodash.ciudad import Ciudad, render_pagina

# Letonia delimita los avisos en tierra con polígonos y no con códigos; por el nombre se colarían los del golfo de Riga
render_pagina(Ciudad(nombre="Riga", lat=56.949, lon=24.105, tz="Europe/Riga", ensemble="icon_eu", nieve=True,
                     pais="latvia", avisos_por_poligono=True),
              titulo="Riga 🇱🇻")
