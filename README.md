# Meteo Dash

Panel meteorológico en Streamlit con previsiones de ensemble para varias ciudades: en tres plazos: corto, 48 h (PE-AROME: temperatura, lluvia, viento, presión y potencial de tormentas), medio, de hoy hasta donde llega el ICON-EU, unos 5 días (ensemble y determinista ICON-EU), y largo, de hoy a 15 días (ensembles ECMWF y GEFS, con probabilidad y cantidad de lluvia); además, avisos oficiales, condiciones actuales (sensación térmica, humedad, UV...), el mejor rato sin lluvia de hoy y mañana, nieve, calidad del aire y polen, comparación con el histórico, fase de la Luna, radar y mapas AROME. Según el lugar, también mar (olas y temperatura del agua), predicción de montaña y boletín de aludes de AEMET, lluvia del año hidrológico y una pestaña de auroras. La portada resume hoy y mañana en todos los lugares, y la página «Cualquier punto» da la previsión de cualquier punto de Europa.

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run main_page.py
```

En Streamlit Cloud el fichero principal es `main_page.py`.

## Estructura

| Ruta | Qué hay |
| --- | --- |
| `main_page.py` | Punto de entrada: navegación entre páginas (la portada, por defecto), estilo y botón de actualizar previsiones, observaciones y avisos (como mucho una vez cada 5 min, porque la caché es común a todos) |
| `paginas/` | Una página por ciudad o grupo, que solo muestra su configuración de `meteodash/lugares.py`; además, `inicio.py` (la portada) y `punto.py` (cualquier punto de Europa) |
| `meteodash/lugares.py` | Configuración (`Ciudad`) de todos los lugares, compartida por sus páginas y la portada, y las secciones de la portada |
| `meteodash/portada.py` | Portada: temperatura observada, hoy y mañana (ensemble ICON-EU) y avisos de todos los lugares, con enlace a su página |
| `meteodash/ciudad.py` | `Ciudad` (configuración) y las pestañas de cada página: `render_48h` (corto plazo: resumen, tarjetas y ensemble a 48 h), `render_medio` (medio plazo: ICON-EU) y `render_largo` (largo plazo, 15 días: ECMWF y GEFS) |
| `meteodash/fuentes.py` | Descarga y caché de Meteociel (PE-AROME), Open-Meteo (ensembles ICON-EU, ECMWF, GEFS y Met Office, determinista ICON-EU, variables complementarias, mar, calidad del aire), probabilidad de lluvia por miembros e históricos |
| `meteodash/hidrologico.py` | Año hidrológico (desde el 1 de octubre): lluvia acumulada frente a la normal 1991-2020, al año anterior y al rango habitual del histórico |
| `meteodash/luna.py` | Fase de la Luna (algoritmo de Meeus: las fases principales, con unos 2 min de diferencia con las del USNO), salida y puesta |
| `meteodash/avisos.py` | Avisos oficiales de Meteoalarm (AEMET y los servicios meteorológicos europeos) |
| `meteodash/radar.py` | Radar de precipitación de RainViewer (pestaña Radar de cada página) |
| `meteodash/auroras.py` | Pestaña de auroras, con tema de cielo nocturno: puntuación de 0 a 10 de las próximas 7 noches (actividad geomagnética, cielo despejado según 91 miembros de ensemble y las capas de nubes, oscuridad, luna, visibilidad y hora), viento solar, óvalo OVATION y Kp a 27 días |
| `meteodash/aemet.py` | Observaciones horarias de AEMET (temperatura, rachas y su dirección, lluvia y humedad) |
| `meteodash/observaciones.py` | Observaciones horarias de las últimas 24 h de AEMET y del resto de redes (FMI, ARSO, KMI, LVĢMC, Met Éireann y METAR), todas con el mismo formato, y su carga común |
| `meteodash/aemet_opendata.py` | API OpenData de AEMET (con clave): comentario de los predictores por comunidad, predicción de montaña, boletín de peligro de aludes, lluvia diaria reciente y resumen mensual de estación |
| `actualizar_historicos.py` | Script que añade a los CSV de `datos/` los días que faltan (requiere `AEMET_API_KEY`) |
| `generar_bandas.py` | Script que calcula los rangos habituales de máxima y mínima de `datos/bandas/` (las estaciones de AEMET requieren `AEMET_API_KEY`) |
| `meteodash/graficos.py` | Gráficos Plotly |
| `meteodash/tarjetas.py` | Tarjetas, avisos y tabla de récords |
| `meteodash/estilo.py` | CSS de la app y tema de los gráficos |
| `meteodash/mapas_arome.py` | Mapas AROME interactivos (Madrid y Torrelavega); las rejillas se descargan en segundo plano y se guardan en memoria, compartidas entre visitantes |
| `meteodash/selector_punto.py` | Mapa de la página «Cualquier punto»: se elige un punto de Europa y el ensemble a 48 h que le toca (PE-AROME en su dominio, Met Office en Gran Bretaña e Irlanda e ICON-EU en el resto) |
| `datos/` | Históricos diarios de AEMET, solo lectura (Retiro desde 1950, Ávila desde 1990; se actualizan con `actualizar_historicos.py`) |
| `datos/bandas/` | Rangos habituales de máxima y mínima por día del año de las páginas sin histórico; la primera línea de cada CSV dice de qué estación, periodo y fuente salen |

## Añadir una ciudad

Añade su configuración a `meteodash/lugares.py` (`NUEVA = Ciudad(nombre="Nueva", lat=40.0, lon=-3.0)`) y su página a `SECCIONES`, para que salga en la portada. Crea `paginas/nueva.py`:

```python
from meteodash.ciudad import render_pagina
from meteodash.lugares import NUEVA

render_pagina(NUEVA)
```

y añádela a la lista de `st.navigation` en `main_page.py`. Opciones de `Ciudad`:

- `estacion_aemet`: código de estación para la temperatura y las rachas observadas.
- `estaciones`: observaciones de otras redes, o de AEMET citando la estación, como tupla de `Estacion(red, código, nombre)` (`from meteodash.observaciones import Estacion`). Redes: `aemet`, `fmi` (fmisid), `arso` (identificador sin el guion bajo final, `LJUBL-ANA_BEZIGRAD`), `kmi`, `lvgmc`, `met_eireann` (`phoenix-park`) y `metar` (código OACI). Con varias, cada variable sale de la primera que la mida (Rovaniemi: temperatura del centro, viento y lluvia del aeropuerto). Si la última observación tiene más de 3 h, no se muestra.
- `historico`: CSV diario de AEMET; activa récords (también de lluvia), percentiles, avisos, rangos habituales y el año hidrológico (con `AEMET_API_KEY`, completado con los días que aún no tiene el CSV).
- `bandas`: sin histórico, CSV de `datos/bandas/` con los rangos habituales de máxima y mínima del gráfico de temperatura. Se añaden en `ESTACIONES` de `generar_bandas.py` y se generan con `python generar_bandas.py <página>`.
- `ccaa_aemet`: `(código, nombre)` de la comunidad (`("mad", "Comunidad de Madrid")`); añade antes del primer gráfico el comentario de los predictores de AEMET (hoy, mañana y pasado mañana). Requiere `AEMET_API_KEY`.
- `montaña_aemet`: `(zona, nombre)` de la predicción de montaña de AEMET (`("arn1", "Pirineo aragonés")`): texto, atmósfera libre y temperaturas de valles a cumbres, de hoy a 3 días. `aludes_aemet`: zona del boletín de peligro de aludes (`"1"`: Pirineo navarro y aragonés), que solo se muestra en temporada. Requieren `AEMET_API_KEY`.
- `resumen_mensual`: último mes publicado por AEMET para `estacion_aemet` frente al promedio 1991-2020 del histórico. Requiere `AEMET_API_KEY` e `historico` para la comparación.
- `nieve`: nieve prevista, espesor y cota de nieve, solo de noviembre a abril. Con `nieve_fuera_de_temporada`, también el resto del año cuando se prevé nieve en la semana (Pirineos).
- `calidad_aire`: índice europeo de calidad del aire y polen (activado por defecto).
- `mar`: temperatura del agua y olas en el punto de mar más cercano de los modelos de Météo-France (tarjetas en el corto plazo y gráfico de 7 días en el medio).
- `pais` y `zonas_aviso`: feed de Meteoalarm (`spain`, `ireland`...) y zonas de aviso, por código (`ES219`, `EI07`) o por parte del nombre (`lombardia`). Con `avisos_por_poligono`, también los avisos cuyo polígono contiene el punto (Letonia no pone código a las zonas en tierra).
- `presion_y_cape`: gráficos de presión y MUCAPE (activado por defecto).
- `camaras`: URLs de cámaras.
- `mapas_arome`: clave de `meteodash.mapas_arome.LOCATIONS` para añadir la pestaña de mapas.
- `ensemble`: fuente de los gráficos a 48 h: `"arome"` (PE-AROME de Meteociel, por defecto) o, fuera del dominio de AROME, `"ukmo"` (MOGREPS-UK 2 km + MOGREPS-G de la Met Office, para Escocia) o `"icon_eu"` (ICON-EU EPS, para Finlandia, el Báltico y Eslovenia), ambos vía Open-Meteo.
- `kp_auroras`: Kp a partir del cual suelen verse auroras en el lugar; añade la pestaña de auroras. Es el Kp con el que el borde del óvalo auroral llega a la latitud geomagnética del lugar, redondeado hacia arriba (NOAA: unos 66º con Kp 0 y 2º menos por cada punto): Rovaniemi 2, Portree 3, Edimburgo y el resto de las Highlands 4, Helsinki y Tallin 5 y Riga 6.
- `tz`: zona horaria (por defecto `Europe/Madrid`).

## Fuentes de datos

- [Meteociel](https://www.meteociel.fr): ensemble PE-AROME (tablas HTML, sin API oficial).
- [AEMET](https://www.aemet.es): observaciones de las últimas 24 h (XML interno de su web, sin API oficial).
- Observaciones fuera de España, todas de servicios oficiales y sin clave: [FMI](https://en.ilmatieteenlaitos.fi/open-data) (Helsinki y Rovaniemi), [ARSO](https://meteo.arso.gov.si/met/sl/service/) (Liubliana y Bled), [KMI/IRM](https://opendata.meteo.be) (Bruselas y Gante), [LVĢMC](https://data.gov.lv/dati/lv/dataset/hidrometeorologiskie-noverojumi) (Riga), [Met Éireann](https://data.gov.ie/organization/meteireann) (Dublín, temperatura en grados enteros) y partes METAR de [aviationweather.gov](https://aviationweather.gov/data/api/) (Milán, Edimburgo, Inverness y Tallin: temperatura en grados enteros, sin lluvia y con racha solo cuando es destacable). Solo se usan estaciones cercanas y representativas del punto; Sallent, Torla-Ordesa, Brujas, Fort William, Aviemore y Portree no tienen ninguna.
- Rangos habituales (`datos/bandas/`): [GHCN-Daily](https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily) de NOAA, datos diarios de las estaciones automáticas del KMI y AEMET OpenData; periodo 1991-2020 (o los años disponibles, con un mínimo de 15).
- [AEMET OpenData](https://opendata.aemet.es): comentario de los predictores por comunidad, predicción de montaña, boletín de peligro de aludes, resúmenes mensuales e históricos diarios. Clave gratuita en `AEMET_API_KEY`: en local, `.streamlit/secrets.toml` (`AEMET_API_KEY = "..."`, ya ignorado por git) o variable de entorno; en Streamlit Cloud, en *Secrets*. Sin clave, esas secciones no se muestran.
- [Open-Meteo](https://open-meteo.com): ICON-EU determinista; ensembles ICON-EU EPS, ECMWF, GEFS y Met Office (MOGREPS-UK y MOGREPS-G); calidad del aire y polen (CAMS); oleaje (MFWAM) y temperatura del agua (SMOC) de Météo-France.
- [Meteoalarm](https://meteoalarm.org): avisos oficiales de AEMET y del resto de servicios europeos.
- [NOAA SWPC](https://www.swpc.noaa.gov): índice Kp observado y previsto (3 y 27 días), probabilidad de tormenta geomagnética, viento solar y modelo de auroras OVATION.
- [RainViewer](https://www.rainviewer.com): radar de precipitación animado (plan gratuito: últimas 2 h, zoom máximo 7).

La app no escribe nada en disco (en Streamlit Cloud no persiste): todo se cachea en memoria.

Meteociel y AEMET no son APIs estables: si cambian el formato, la página afectada muestra un aviso en lugar de romperse. Igual con las observaciones de las demás redes: si fallan, la página avisa y muestra solo la previsión.
