"""Gráficos del medio y el largo plazo en un visor como el meteograma de las 48 h (visor.js): paneles apilados con un
solo cursor que se mueve en el navegador, sin recargar Streamlit (ratón, dedo arrastrando en horizontal o flechas), y
los valores de ese momento encima de cada panel.

- `medio`: el ensemble del medio plazo hora a hora (temperatura con el determinista, lluvia y rachas), nubes, UV y,
  plegadas salvo que se prevea, la nieve y su cota.
- `mar`: olas y temperatura del agua, 7 días.
- `calidad_aire`: índice europeo de calidad del aire con sus categorías y el polen, 4 días.
- `largo`: máximas, mínimas y lluvia día a día de los ensembles ECMWF y GEFS, 15 días.
- `año_hidrologico`: lluvia acumulada desde el 1 de octubre frente a la normal y al año anterior.

Aquí solo se preparan las series, con nombre, y para cada panel sus capas (miembros, líneas, bandas, barras...) y lo que
se lee con el cursor; las cuentas son las mismas que las de los gráficos Plotly a los que sustituyen.
"""

from hashlib import md5
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from .estilo import AMBAR, AZUL, ROJO, TEXTO
from .fuentes import UMBRAL_LLUVIA, UMBRAL_LLUVIA_HORA, extremos_diarios, prob_diaria, prob_por_hora
from .graficos import CATEGORIAS_ICA, categoria_ica
from .observaciones import cardinal

VISOR = st.components.v2.component(
    "visor", isolate_styles=False, html='<div class="visor" tabindex="0"></div>',
    css=Path(__file__).with_name("visor.css").read_text(encoding="utf-8"),
    js=Path(__file__).with_name("visor.js").read_text(encoding="utf-8"),
)

# Los colores del meteograma
GRIS = "#635b53"
MIEMBROS = "rgba(99, 91, 83, 0.22)"
MIEMBROS_RACHAS = "rgba(217, 119, 6, 0.22)"
RACHAS = "#b45309"
AZUL_CLARO = "#0284c7"  # mínimas del largo plazo, mar de fondo y nieve
RANGO = "rgba(99, 91, 83, 0.13)"

COLORES_MODELO = {"ECMWF": AZUL, "GEFS": AMBAR}
TRAZOS_MODELO = {"ECMWF": "punteada", "GEFS": "discontinua"}
COLORES_POLEN = [AMBAR, "#059669", ROJO, "#7c3aed", AZUL, GRIS]


def _ms(momento):
    """Instante con zona -> milisegundos desde 1970 (UTC), como los usa el navegador."""
    return int(pd.Timestamp(momento).value // 10**6)


def _dia_ms(fecha, tz):
    """Medianoche local de una fecha, en milisegundos."""
    return _ms(pd.Timestamp(fecha).tz_localize(tz))


def _lista(serie, decimales):
    """Serie -> lista para JSON, con None donde falta."""
    return [None if pd.isna(v) else round(float(v), decimales) for v in serie]


def _chip(color):
    """Cuadradito del color de una serie, para las lecturas (hace de leyenda)."""
    return f'<i class="vs-chip" style="background:{color}"></i>'


def _con_zona(df, desfase, tz):
    """Tabla de Open-Meteo en hora local sin zona -> con la zona del lugar.

    Open-Meteo aplica el mismo desfase con UTC a toda la previsión (`utc_offset_seconds`), aunque en medio cambie la hora,
    así que se deshace con él; sin él, se localiza tal cual (las horas repetidas o inexistentes se pierden).
    """

    if desfase is None:
        df = df.tz_localize(tz, ambiguous="NaT", nonexistent="NaT")
        return df[df.index.notna()]
    return df.set_axis((df.index - pd.Timedelta(seconds=desfase)).tz_localize("UTC").tz_convert(tz))


def _extremos(serie, decimales, sufijo="", minimos=True, color_max=ROJO):
    """Etiquetas del máximo (y del mínimo) de cada día de `serie`, con el índice del eje del visor:
    [[posición, valor, texto, "arriba" | "abajo", color]]. Los mismos valores que las tarjetas."""

    etiquetas, valores, fechas = [], serie.to_numpy(dtype=float), np.array(serie.index.date)
    for fecha in sorted(set(fechas)):
        posiciones = np.flatnonzero((fechas == fecha) & ~np.isnan(valores))
        if not len(posiciones):
            continue
        dia = valores[posiciones]
        pares = [(posiciones[dia.argmax()], "arriba", color_max)]
        if minimos:
            pares.append((posiciones[dia.argmin()], "abajo", AZUL))
        for i, lado, color in pares:
            etiquetas.append([int(i), round(float(valores[i]), decimales),
                              f"{valores[i]:.{decimales}f}".replace(".", ",") + sufijo, lado, color])
    return etiquetas


def _mostrar(clave, datos):
    # El visor solo vuelve a dibujar si cambian los datos (Streamlit recarga la página por cualquier otra cosa)
    datos["clave"] = md5(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:12]
    VISOR(key=clave, data=datos)


# ---------------------------------------------------------------- Medio plazo

def _ensemble_medio(horas, ens, deterministas, series, leyenda):
    """Paneles de temperatura, lluvia y rachas del ensemble del medio plazo (con el determinista, si lo hay)."""

    temp = ens["temperatura"].reindex(horas)
    mediana = temp.median(axis=1)
    series |= {"t_miembros": [_lista(temp[c], 1) for c in temp.columns], "t_mediana": _lista(mediana, 1),
               "t_p10": _lista(temp.quantile(0.1, axis=1), 1), "t_p90": _lista(temp.quantile(0.9, axis=1), 1)}
    capas_t = [{"tipo": "miembros", "series": "t_miembros", "color": MIEMBROS},
               {"tipo": "linea", "serie": "t_mediana", "color": GRIS, "ancho": 2.2, "cursor": True}]
    lectura_t = [["<b>{} °C</b>", "t_mediana", 1], ["10-90 %: {} a {}", ["t_p10", "t_p90"], 1]]

    rachas = ens["rachas"].reindex(horas)
    mediana_r = rachas.median(axis=1)
    series |= {"r_miembros": [_lista(rachas[c], 0) for c in rachas.columns], "r_mediana": _lista(mediana_r, 0)}
    capas_r = [{"tipo": "miembros", "series": "r_miembros", "color": MIEMBROS_RACHAS},
               {"tipo": "linea", "serie": "r_mediana", "color": RACHAS, "ancho": 2, "cursor": True}]
    lectura_r = [["<b>{} km/h</b>", "r_mediana", 0]]

    leyenda.append({"texto": "mediana", "color": GRIS})
    # El determinista (una columna con el nombre del modelo), discontinuo y en azul
    for variable, capas, lectura, decimales in [("temperatura", capas_t, lectura_t, 1), ("rachas", capas_r, lectura_r, 0)]:
        det = deterministas.get(variable) if deterministas else None
        if det is None or det.empty:
            continue
        modelo = det.columns[0]
        series[f"det_{variable}"] = _lista(det[modelo].reindex(horas), decimales)
        capas.append({"tipo": "linea", "serie": f"det_{variable}", "color": AZUL, "ancho": 2, "trazo": "discontinua",
                      "cursor": True})
        lectura.append([f"{modelo} {{}}", f"det_{variable}", decimales])
        if variable == "temperatura":
            leyenda.append({"texto": modelo, "color": AZUL, "trazo": "discontinua"})
    leyenda.append({"texto": "miembros", "color": "rgba(99, 91, 83, 0.3)"})
    capas_t.append({"tipo": "etiquetas", "puntos": _extremos(mediana, 1, "°")})
    capas_r.append({"tipo": "etiquetas", "puntos": _extremos(mediana_r, 0)})

    # Lluvia: arriba, la cantidad media de los miembros que llueven (los que no, no la rebajan); abajo, el % de miembros
    # con al menos UMBRAL_LLUVIA_HORA en la hora. Como en el meteograma
    prec = ens["precipitacion"]
    llueve = prec.where(prec >= UMBRAL_LLUVIA_HORA)
    media = llueve.mean(axis=1).fillna(0).reindex(horas)
    prob = prob_por_hora(prec).reindex(horas)
    series |= {"ll_media": _lista(media, 1), "ll_prob": _lista(prob, 0), "ll_si": _lista(media.where(prob > 0), 1)}
    lluvia = {"id": "lluvia", "titulo": "Lluvia", "zonas": [
        {"alto": 110, "escala": {"cero": True, "max_minimo": 1, "margen": 0.15, "arriba": 10, "abajo": 0,
                                 "sin_cero": True},
         "capas": [{"tipo": "linea", "serie": "ll_media", "color": AZUL, "area": "rgba(2, 119, 189, 0.12)",
                    "puntos": True, "cursor": True}]},
        {"alto": 70, "escala": {"fijo": [0, 100], "guias": [50, 100], "sufijo": " %", "arriba": 4, "abajo": 0},
         "capas": [{"tipo": "barras", "serie": "ll_prob", "color": AMBAR, "opacidad": 0.85}]},
    ], "lectura": [["<b>{} %</b> de prob.", "ll_prob", 0], ["{} L/m² de media si llueve", "ll_si", 1]]}

    return [
        {"id": "temperatura", "titulo": "Temperatura", "lectura": lectura_t,
         "zonas": [{"alto": 240, "escala": {"paso": 1}, "capas": capas_t}]},
        lluvia,
        {"id": "rachas", "titulo": "Rachas", "lectura": lectura_r,
         "zonas": [{"alto": 160, "escala": {"paso": 5, "piso": 0}, "capas": capas_r}]},
    ]


def _nubes_uv(horario, series):
    """Paneles de nubosidad y UV, hora a hora (del mejor modelo de Open-Meteo)."""

    paneles = []
    if horario["nubes"].notna().any():
        series["nubes"] = _lista(horario["nubes"], 0)
        paneles.append({"id": "nubes", "titulo": "Nubosidad", "lectura": [["<b>{} %</b>", "nubes", 0]], "zonas": [
            {"alto": 80, "escala": {"fijo": [0, 100], "guias": [50, 100], "sufijo": " %", "arriba": 6},
             "capas": [{"tipo": "linea", "serie": "nubes", "color": GRIS, "ancho": 1.5, "area": "rgba(99, 91, 83, 0.18)",
                        "cursor": True}]}]})
    if "uv" in horario and horario["uv"].notna().any():
        series["uv"] = _lista(horario["uv"], 1)
        maximos = [e for e in _extremos(horario["uv"], 0, minimos=False, color_max=AMBAR) if e[1] >= 0.5]
        paneles.append({"id": "uv", "titulo": "Índice UV", "lectura": [["<b>{}</b>", "uv", 0]], "zonas": [
            {"alto": 80, "escala": {"cero": True, "max_minimo": 3, "margen": 0.25},
             "capas": [{"tipo": "linea", "serie": "uv", "color": AMBAR, "area": "rgba(217, 119, 6, 0.15)",
                        "cursor": True},
                       {"tipo": "etiquetas", "puntos": maximos}]}]})
    return paneles


def _nieve(horas, horario, elevacion, series):
    """Grupo plegable de la nieve (cm en cada hora, con el total de cada día) y su cota (300 m por debajo de la isoterma
    de 0 ºC), desplegado si se prevé al menos 1 cm."""

    nieve = horario["nieve"]
    cota = (horario["isocero"] - 300).clip(lower=0)
    por_dia = nieve.groupby(nieve.index.date)
    series |= {"nieve": _lista(nieve, 1), "nieve_dia": _lista(por_dia.transform("sum"), 1),
               "cota": _lista(cota.round(-1), 0)}
    totales = []
    for _, dia in por_dia:
        if dia.sum() >= 1:
            totales.append([int(horas.get_loc(dia.idxmax())), round(float(dia.max()), 1), f"{dia.sum():.0f} cm",
                            "arriba", AZUL_CLARO])
    capas_cota = [{"tipo": "linea", "serie": "cota", "color": TEXTO, "ancho": 2, "cursor": True}]
    if elevacion is not None:
        capas_cota.append({"tipo": "referencia", "valor": elevacion, "color": ROJO,
                           "texto": f"altitud {elevacion:.0f} m"})
    hay_nieve = bool(nieve.sum() >= 1)
    return {"titulo": "Nieve y cota de nieve", "aviso": "nieve prevista" if hay_nieve else None,
            "desplegado": hay_nieve, "paneles": [
                {"id": "nieve", "titulo": "Nieve", "zonas": [
                    {"alto": 100, "escala": {"cero": True, "max_minimo": 0.5, "margen": 0.3},
                     "capas": [{"tipo": "barras", "serie": "nieve", "color": "rgba(2, 132, 199, 0.55)"},
                               {"tipo": "etiquetas", "puntos": totales}]}],
                 "lectura": [["<b>{} cm</b> en la hora", "nieve", 1], ["{} cm en el día", "nieve_dia", 1]]},
                {"id": "cota", "titulo": "Cota de nieve", "lectura": [["<b>{} m</b>", "cota", 0]],
                 "zonas": [{"alto": 110, "escala": {"paso": 100, "piso": 0}, "capas": capas_cota}]},
            ]}


def medio(ciudad, ens, deterministas, detalle, desde, con_nieve=False):
    """Medio plazo hora a hora, de `desde` hasta donde llegue `ens` (el ensemble, {variable: DataFrame}; sin él, 5
    días): temperatura, lluvia y rachas del ensemble con el determinista (`deterministas`, ver
    fuentes.get_determinista); nubes y UV de `detalle` (fuentes.get_open_meteo_detalle) y, con `con_nieve`, la nieve."""

    horario = None
    if detalle is not None:
        horario = _con_zona(detalle["horario"], detalle.get("desfase"), ciudad.tz)
    if ens is not None:
        horas = ens["temperatura"].index
        for df in ens.values():
            horas = horas.union(df.index)
    elif horario is not None:
        horas = horario.index[(horario.index >= desde) & (horario.index < desde.normalize() + pd.Timedelta(days=6))]
    else:
        return False

    series, leyenda, paneles, grupos = {}, [], [], []
    if ens is not None:
        paneles += _ensemble_medio(horas, ens, deterministas, series, leyenda)
    if horario is not None:
        horario = horario.reindex(horas)
        paneles += _nubes_uv(horario, series)
        if con_nieve:
            grupos.append(_nieve(horas, horario, detalle.get("elevacion"), series))
    if not paneles:
        paneles, grupos = [p for g in grupos for p in g["paneles"]], []
    if not paneles:
        return False

    _mostrar(f"medio_{ciudad.nombre}", {
        "modo": "hora", "tz": ciudad.tz, "lat": ciudad.lat, "lon": ciudad.lon, "horas": [_ms(h) for h in horas],
        "series": series, "leyenda": leyenda, "paneles": paneles, "grupos": grupos,
    })
    return True


# ---------------------------------------------------------------- Mar

def mar(ciudad, datos, desde):
    """Altura de las olas y del mar de fondo y temperatura del agua (ver fuentes.get_mar), desde `desde`."""

    horario = _con_zona(datos["horario"], datos.get("desfase"), ciudad.tz)
    horario = horario[horario.index >= desde]
    if not horario["olas"].notna().any():
        return False

    series = {"olas": _lista(horario["olas"], 2), "fondo": _lista(horario["mar_fondo"], 2),
              "periodo": _lista(horario["periodo"], 0), "rumbo": [cardinal(g) for g in horario["direccion"]]}
    paneles = [{"id": "olas", "titulo": "Olas", "zonas": [
        {"alto": 150, "escala": {"cero": True, "max_minimo": 1, "margen": 0.2},
         "capas": [{"tipo": "linea", "serie": "olas", "color": AZUL, "ancho": 2.5, "area": "rgba(2, 119, 189, 0.15)",
                    "cursor": True},
                   {"tipo": "linea", "serie": "fondo", "color": AZUL_CLARO, "ancho": 1.5, "trazo": "punteada",
                    "cursor": True}]}],
        "lectura": [["<b>{} m</b>", "olas", 1], ["periodo {} s", "periodo", 0], ["del {}", "rumbo"],
                    ["mar de fondo {} m", "fondo", 1]]}]

    agua = horario["agua"].dropna()
    if not agua.empty:  # al menos 4º de rango: si no, unas décimas parecen grandes cambios
        centro, mitad = (agua.min() + agua.max()) / 2, max((agua.max() - agua.min()) / 2 + 0.5, 2)
        series["agua"] = _lista(horario["agua"], 2)
        paneles.append({"id": "agua", "titulo": "Agua", "lectura": [["<b>{} °C</b>", "agua", 1]], "zonas": [
            {"alto": 90, "escala": {"fijo": [round(centro - mitad, 2), round(centro + mitad, 2)]},
             "capas": [{"tipo": "linea", "serie": "agua", "color": ROJO, "ancho": 2, "cursor": True}]}]})

    _mostrar(f"mar_{ciudad.nombre}", {
        "modo": "hora", "tz": ciudad.tz, "lat": ciudad.lat, "lon": ciudad.lon, "titulo": "Mar · 7 días",
        "horas": [_ms(h) for h in horario.index], "series": series, "paneles": paneles,
        "leyenda": [{"texto": "olas", "color": AZUL, "grosor": 2.5},
                    {"texto": "mar de fondo", "color": AZUL_CLARO, "trazo": "punteada"}],
    })
    return True


# ---------------------------------------------------------------- Calidad del aire y polen

def calidad_aire(ciudad, aire, polenes):
    """Índice europeo de calidad del aire sobre las franjas de sus categorías, con los contaminantes en la lectura, y
    la concentración de cada polen de `polenes` (columna -> nombre), si hay alguno (ver fuentes.get_calidad_aire)."""

    df = _con_zona(aire, aire.attrs.get("desfase"), ciudad.tz)
    ica = df["european_aqi"]
    tope = max(60, ica.max() + 10)
    franjas, abajo = [], 0
    for limite, _, color in CATEGORIAS_ICA:
        if abajo < tope:
            franjas.append([abajo, None if limite == float("inf") else limite, color, 0.14])
        abajo = limite

    series = {"ica": _lista(ica, 0), "ica_cat": [None if pd.isna(v) else categoria_ica(v)[0].lower() for v in ica],
              "pm25": _lista(df["pm2_5"], 0), "pm10": _lista(df["pm10"], 0), "no2": _lista(df["nitrogen_dioxide"], 0),
              "o3": _lista(df["ozone"], 0)}
    paneles = [{"id": "ica", "titulo": "Índice europeo (ICA)", "zonas": [
        {"alto": 150, "escala": {"fijo": [0, round(float(tope))], "arriba": 4},
         "capas": [{"tipo": "franjas", "franjas": franjas},
                   {"tipo": "linea", "serie": "ica", "color": TEXTO, "ancho": 2.5, "cursor": True}]}],
        "lectura": [["<b>{}</b> {}", ["ica", "ica_cat"], 0],
                    ["PM2,5 {} · PM10 {} · NO₂ {} · O₃ {} µg/m³", ["pm25", "pm10", "no2", "o3"], 0]]}]

    if polenes:
        capas, lectura = [], []
        for (columna, nombre), color in zip(polenes.items(), COLORES_POLEN):
            series[columna] = _lista(df[columna], 0)
            capas.append({"tipo": "linea", "serie": columna, "color": color, "ancho": 2, "cursor": True})
            lectura.append([f"{_chip(color)}{nombre} <b>{{}}</b>", columna, 0])
        paneles.append({"id": "polen", "titulo": "Polen (granos/m³)", "lectura": lectura,
                        "zonas": [{"alto": 120, "escala": {"cero": True, "max_minimo": 10}, "capas": capas}]})

    _mostrar(f"aire_{ciudad.nombre}", {
        "modo": "hora", "tz": ciudad.tz, "lat": ciudad.lat, "lon": ciudad.lon,
        "titulo": "Calidad del aire y polen · 4 días" if polenes else "Calidad del aire · 4 días",
        "horas": [_ms(h) for h in df.index], "series": series, "paneles": paneles,
    })
    return True


# ---------------------------------------------------------------- Largo plazo: ensembles ECMWF y GEFS

def largo(ciudad, ensembles, fechas, hoy):
    """Máximas y mínimas diarias de todos los miembros juntos (mediana y rango 10-90 %), la mediana de cada modelo y,
    por modelo, la probabilidad de lluvia y la lluvia media de cada día.

    `ensembles`: {nombre: {"temperatura", "precipitacion"}} (ver fuentes.get_ensemble); `fechas`: días a mostrar.
    El día de hoy (`hoy`) cuenta aunque el pase empiece a medianoche UTC (20 h bastan).
    """

    maximas, minimas, por_modelo, probabilidades, totales = [], [], {}, {}, {}
    for nombre, datos in ensembles.items():
        maxima, minima = extremos_diarios(datos["temperatura"], fechas, minimo_horas=20)
        maximas.append(maxima)
        minimas.append(minima)
        por_modelo[nombre] = (maxima.median(axis=1), minima.median(axis=1))
        probabilidades[nombre] = prob_diaria(datos["precipitacion"])
        prec = datos["precipitacion"]
        totales[nombre] = prec.groupby(prec.index.date).sum(min_count=1)  # lluvia de cada miembro en cada día
    maximas, minimas = pd.concat(maximas, axis=1), pd.concat(minimas, axis=1)
    dias = [f for f in fechas if f in maximas.index]
    if not dias:
        return False
    total = sum(d["temperatura"].shape[1] for d in ensembles.values())

    series, capas_t, etiquetas = {}, [], []
    lectura_t = []
    for clave, diario, color, relleno, lado, nombre in [
        ("tmax", maximas.loc[dias], ROJO, "rgba(217, 56, 86, 0.15)", "arriba", "máx."),
        ("tmin", minimas.loc[dias], AZUL_CLARO, "rgba(2, 132, 199, 0.15)", "abajo", "mín."),
    ]:
        mediana = diario.median(axis=1)
        series |= {clave: _lista(mediana, 1), f"{clave}_p10": _lista(diario.quantile(0.1, axis=1), 1),
                   f"{clave}_p90": _lista(diario.quantile(0.9, axis=1), 1)}
        capas_t.append({"tipo": "banda", "bajo": f"{clave}_p10", "alto": f"{clave}_p90", "color": relleno})
        etiquetas += [[i, round(float(v), 1), f"{v:.0f}°", lado, color] for i, v in enumerate(mediana) if not pd.isna(v)]
        lectura_t.append([f"{nombre} <b>{{}}°</b> ({{}} a {{}})", [clave, f"{clave}_p10", f"{clave}_p90"], [1, 0, 0]])

    # Mediana de cada modelo, fina: se ve si discrepan sin cargar el gráfico
    leyenda = [{"texto": "máxima", "color": ROJO, "grosor": 2.5}, {"texto": "mínima", "color": AZUL_CLARO, "grosor": 2.5},
               {"texto": "rango 10-90 %", "color": "rgba(99, 91, 83, 0.2)", "tipo": "area"}]
    for modelo, (maxima, minima) in por_modelo.items():
        color, trazo = COLORES_MODELO.get(modelo, TEXTO), TRAZOS_MODELO.get(modelo)
        for clave, serie in [("tmax", maxima), ("tmin", minima)]:
            series[f"{modelo}_{clave}"] = _lista(serie.reindex(dias), 1)
            capas_t.append({"tipo": "linea", "serie": f"{modelo}_{clave}", "color": color, "ancho": 1.5, "trazo": trazo})
        lectura_t.append([f"{_chip(color)}{modelo} {{}} / {{}}°", [f"{modelo}_tmax", f"{modelo}_tmin"], 1])
        leyenda.append({"texto": modelo, "color": color, "trazo": trazo})
    capas_t += [{"tipo": "linea", "serie": "tmax", "color": ROJO, "ancho": 2.5, "marcas": True, "cursor": True},
                {"tipo": "linea", "serie": "tmin", "color": AZUL_CLARO, "ancho": 2.5, "marcas": True, "cursor": True},
                {"tipo": "etiquetas", "puntos": etiquetas}]

    # Por modelo, barras juntas: probabilidad de lluvia y lluvia media de los miembros (lo esperable) y, en la lectura,
    # la del 10 % de miembros más lluviosos
    capas_p, lectura_p, capas_l, lectura_l = [], [], [], []
    for k, modelo in enumerate(probabilidades):
        color, grupo = COLORES_MODELO.get(modelo, TEXTO), [k, len(probabilidades)]
        series[f"{modelo}_prob"] = _lista(pd.Series([probabilidades[modelo].get(f) for f in dias], dtype=float), 0)
        lluvia = totales[modelo].reindex(dias)
        series[f"{modelo}_lluvia"] = _lista(lluvia.mean(axis=1), 1)
        series[f"{modelo}_p90"] = _lista(lluvia.quantile(0.9, axis=1), 1)
        capas_p.append({"tipo": "barras", "serie": f"{modelo}_prob", "color": color, "opacidad": 0.65, "grupo": grupo})
        capas_l.append({"tipo": "barras", "serie": f"{modelo}_lluvia", "color": color, "opacidad": 0.65, "grupo": grupo})
        lectura_p.append([f"{_chip(color)}{modelo} <b>{{}} %</b>", f"{modelo}_prob", 0])
        lectura_l.append([f"{_chip(color)}{modelo} <b>{{}}</b> (≥ {{}})", [f"{modelo}_lluvia", f"{modelo}_p90"], 1])

    _mostrar(f"largo_{ciudad.nombre}", {
        "modo": "dia", "eje": "dias", "tz": ciudad.tz, "titulo": f"{' + '.join(ensembles)} · {total} miembros",
        "horas": [_dia_ms(f, ciudad.tz) for f in dias], "series": series, "leyenda": leyenda,
        "inicio": dias.index(hoy) if hoy in dias else None,
        "paneles": [
            {"id": "temperatura", "titulo": "Temperatura", "lectura": lectura_t,
             "zonas": [{"alto": 250, "escala": {"paso": 1}, "capas": capas_t}]},
            {"id": "probabilidad", "titulo": f"Prob. de ≥ {UMBRAL_LLUVIA} L/m²", "lectura": lectura_p, "zonas": [
                {"alto": 90, "escala": {"fijo": [0, 100], "guias": [50, 100], "sufijo": " %", "arriba": 6},
                 "capas": capas_p}]},
            {"id": "lluvia", "titulo": "Lluvia media (L/m²)", "lectura": lectura_l, "zonas": [
                {"alto": 100, "escala": {"cero": True, "max_minimo": 2, "margen": 0.15, "arriba": 6},
                 "capas": capas_l}]},
        ],
    })
    return True


# ---------------------------------------------------------------- Año hidrológico

def año_hidrologico(ciudad, fechas, actual, anterior, normal, rango, nombre_actual, nombre_anterior):
    """Lluvia acumulada del año hidrológico en curso y del anterior, la normal y el rango 10-90 % de los años del
    histórico (ver hidrologico.py). Las series van por posición (0-364) sobre `fechas`, las del año en curso."""

    def completa(serie):
        return _lista(pd.Series(serie.to_numpy(dtype=float)).reindex(range(len(fechas))), 0)

    series, capas, lectura, leyenda = {"normal": completa(normal)}, [], [], []
    if not rango.empty:
        series |= {"p10": completa(rango.quantile(0.1, axis=1)), "p90": completa(rango.quantile(0.9, axis=1))}
        capas.append({"tipo": "banda", "bajo": "p10", "alto": "p90", "color": RANGO})
    capas.append({"tipo": "linea", "serie": "normal", "color": GRIS, "ancho": 1.8, "trazo": "discontinua",
                  "cursor": True})
    for clave, serie, nombre, color, ancho in [("anterior", anterior, nombre_anterior, AMBAR, 1.8),
                                               ("actual", actual, nombre_actual, AZUL, 3)]:
        if serie.empty:
            continue
        series[clave] = completa(serie)
        capas.append({"tipo": "linea", "serie": clave, "color": color, "ancho": ancho, "cursor": True})
        lectura.insert(0, [f"{_chip(color)}{nombre} <b>{{}} L/m²</b>", clave, 0])
        leyenda.insert(0, {"texto": nombre, "color": color, "grosor": ancho})
    if not actual.empty:
        capas.append({"tipo": "etiquetas", "puntos": [[len(actual) - 1, round(float(actual.iloc[-1]), 0),
                                                       f"{actual.iloc[-1]:.0f}", "arriba", AZUL]]})
    lectura += [[f"{_chip(GRIS)}normal {{}}", "normal", 0], ["rango 10-90 %: {} a {}", ["p10", "p90"], 0]]
    leyenda += [{"texto": "normal", "color": GRIS, "trazo": "discontinua"}]
    if not rango.empty:
        leyenda.append({"texto": "rango 10-90 %", "color": "rgba(99, 91, 83, 0.2)", "tipo": "area"})

    _mostrar(f"hidrologico_{ciudad.nombre}", {
        "modo": "dia", "eje": "meses", "relativa": False, "tz": ciudad.tz,
        "titulo": "Lluvia acumulada desde el 1 de octubre",
        "horas": [_dia_ms(f, ciudad.tz) for f in fechas], "series": series, "leyenda": leyenda,
        # El cursor empieza en el último día con datos
        "inicio": len(actual) - 1 if not actual.empty else None, "boton": "Último dato" if not actual.empty else "Hoy",
        "paneles": [{"id": "acumulada", "titulo": "Lluvia", "lectura": lectura,
                     "zonas": [{"alto": 280, "escala": {"cero": True, "margen": 0.08}, "capas": capas}]}],
    })
    return True
