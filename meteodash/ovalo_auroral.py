"""Óvalo auroral: la probabilidad de aurora de OVATION (NOAA) para la próxima hora sobre un globo de MapLibre.

El visor (ovalo_auroral.js) recibe la rejilla de 1º y hace en el navegador la imagen suavizada, el día y la noche de ese
momento y el valor bajo el ratón.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

LAT_MIN = 30  # get_ovation solo deja las latitudes desde aquí

VISOR = st.components.v2.component(
    "ovalo_auroral", isolate_styles=False,
    html='<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.css">'
         '<div class="ovalo-auroral"><div class="oa-mapa"></div>'
         '<div class="oa-tarjeta"><div class="oa-titulo"><b>Óvalo auroral</b><span>%</span></div>'
         '<div class="oa-barra"></div><div class="oa-marcas"></div><div class="oa-fuente"></div></div>'
         '<div class="oa-globo"></div><div class="oa-aviso">Cargando el globo…</div></div>',
    css=Path(__file__).with_name("ovalo_auroral.css").read_text(encoding="utf-8"),
    js=Path(__file__).with_name("ovalo_auroral.js").read_text(encoding="utf-8"),
)


def ovalo_auroral(momento, rejilla, ciudad):
    """Globo con la rejilla de OVATION (`rejilla`: lon 0-359, lat, prob) de `momento` y la ciudad marcada con la
    probabilidad de su celda, la misma que la tarjeta de «Ahora»."""

    tabla = rejilla.pivot(index="lat", columns="lon", values="prob").reindex(index=range(LAT_MIN, 91),
                                                                            columns=range(360))
    valor = tabla.loc[round(ciudad.lat), round(ciudad.lon) % 360]
    VISOR(key=f"ovalo_{ciudad.nombre}", data={
        "momento": int(momento.value // 10**6), "tz": ciudad.tz, "lat0": LAT_MIN,
        # Filas de sur a norte y, en cada una, longitudes de 0 a 359; None si falta la celda
        "valores": [None if pd.isna(v) else int(round(v)) for v in tabla.to_numpy().ravel()],
        "lugar": {"nombre": ciudad.nombre, "lat": ciudad.lat, "lon": ciudad.lon,
                  "valor": None if pd.isna(valor) else int(round(valor))},
    })
