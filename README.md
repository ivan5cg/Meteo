# Meteo Dash

Panel meteorológico en Streamlit con previsiones de ensemble para varias ciudades: temperatura, lluvia, viento, presión y potencial de tormentas a 48 h, previsión semanal multimodelo, tendencia a 15 días, comparación con el histórico y mapas AROME.

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run main_page.py
```

En Streamlit Cloud el fichero principal es `main_page.py`.

## Estructura

| Ruta | Qué hay |
| --- | --- |
| `main_page.py` | Punto de entrada: navegación entre páginas, estilo y botón de actualizar |
| `paginas/` | Una página por ciudad o grupo; cada una es solo su configuración |
| `meteodash/ciudad.py` | `Ciudad` (configuración) y `render_ciudad`, que monta la página completa |
| `meteodash/fuentes.py` | Descarga y caché de Meteociel (AROME, GEFS), Open-Meteo e históricos |
| `meteodash/aemet.py` | Observaciones horarias de AEMET |
| `meteodash/graficos.py` | Gráficos Plotly |
| `meteodash/tarjetas.py` | Tarjetas, avisos y tabla de récords |
| `meteodash/estilo.py` | CSS de la app y tema de los gráficos |
| `arome_maps.py` | Mapas AROME interactivos (Madrid y Torrelavega); las rejillas se guardan en memoria, compartidas entre visitantes |
| `datos/` | Históricos diarios de AEMET, solo lectura (Retiro 1950-2022, Ávila 1990-2022) |

## Añadir una ciudad

Crea `paginas/nueva.py`:

```python
from meteodash.ciudad import Ciudad, render_pagina

render_pagina(Ciudad(nombre="Nueva", lat=40.0, lon=-3.0, semana=True))
```

y añádela a la lista de `st.navigation` en `main_page.py`. Opciones de `Ciudad`:

- `estacion_aemet`: código de estación para la temperatura y las rachas observadas.
- `historico`: CSV diario de AEMET; activa récords, percentiles, avisos y rangos habituales.
- `semana`: previsión multimodelo de Open-Meteo a 7 días.
- `gefs`: tendencia a 15 días del ensemble GFS.
- `presion_y_cape`: gráficos de presión y MUCAPE (activado por defecto).
- `camaras`: URLs de cámaras.
- `mapas_arome`: clave de `arome_maps.LOCATIONS` para añadir la pestaña de mapas.
- `tz`: zona horaria (por defecto `Europe/Madrid`).

## Fuentes de datos

- [Meteociel](https://www.meteociel.fr): ensembles PE-AROME y GEFS (tablas HTML, sin API oficial).
- [AEMET](https://www.aemet.es): observaciones de las últimas 24 h (XML interno de su web, sin API oficial).
- [Open-Meteo](https://open-meteo.com): ECMWF, GFS, AROME, ARPEGE e ICON.

La app no escribe nada en disco (en Streamlit Cloud no persiste): todo se cachea en memoria.

Meteociel y AEMET no son APIs estables: si cambian el formato, la página afectada muestra un aviso en lugar de romperse.
