"""Página de previsión de una ciudad, montada según las fuentes de datos que tenga configuradas."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

from . import graficos, tarjetas
from .estilo import AZUL, ROJO
from .aemet import cargar_aemet_horario, get_aemet_horario, temperatura_actual_y_ayer
from .aemet_opendata import (DIAS_PREDICCION, get_comentario_aemet, get_resumen_mensual, hay_clave, normales_mensuales,
                             racha_maxima, valor_y_dia)
from .avisos import avisos_vigentes, get_avisos
from .fuentes import (ENSEMBLES, POLENES, UMBRAL_LLUVIA, dia_historico, en_paralelo, extremos_diarios,
                      get_calidad_aire, get_deterministas, get_ensemble, get_ensemble_arome, get_ensemble_ukmo,
                      get_historico, get_open_meteo_detalle, hora_local_run, prob_diaria, prob_miembros,
                      probabilidad_lluvia)
from .radar import render_radar

MESES_NIEVE = {11, 12, 1, 2, 3, 4}


@dataclass(frozen=True)
class Ciudad:
    nombre: str
    lat: float
    lon: float
    tz: str = "Europe/Madrid"
    estacion_aemet: str | None = None  # observaciones de las últimas 24 h
    historico: str | None = None  # CSV diario de AEMET: récords, percentiles, avisos y rangos habituales
    ccaa_aemet: tuple[str, str] | None = None  # (código, nombre) de la comunidad: comentario de los predictores de AEMET
    resumen_mensual: bool = False  # último mes publicado por AEMET frente a lo normal (requiere estacion_aemet y clave)
    presion_y_cape: bool = True
    nieve: bool = False  # nieve prevista, espesor y cota de nieve (solo en MESES_NIEVE)
    nieve_fuera_de_temporada: bool = False  # también fuera de MESES_NIEVE si se prevé nieve en la semana
    calidad_aire: bool = True  # índice europeo de calidad del aire y polen
    pais: str = "spain"  # feed de avisos de Meteoalarm
    zonas_aviso: tuple[str, ...] = ()  # códigos o nombres de las zonas de aviso de Meteoalarm
    camaras: tuple[str, ...] = ()
    mapas_arome: str | None = None  # clave de mapas_arome.LOCATIONS
    ensemble: str = "arome"  # 48 h: "arome" (PE-AROME de Meteociel) o "ukmo" (Met Office, fuera del dominio de AROME)


def extremos_del_dia(serie, fecha):
    """Máxima y mínima horarias de un día y, si la serie no lo cubre entero, las horas cubiertas ("17-23 h")."""

    del_dia = serie[serie.index.date == fecha.date()].dropna()
    if del_dia.empty:
        return np.nan, np.nan, None
    desde, hasta = del_dia.index[0].hour, del_dia.index[-1].hour
    horas = None if (desde, hasta) == (0, 23) else f"{desde}-{hasta} h"
    return round(del_dia.max(), 1), round(del_dia.min(), 1), horas


def _o_none(funcion, *args):
    """Resultado de una fuente secundaria, o None si falla (su sección simplemente no se muestra)."""

    try:
        return funcion(*args)
    except Exception:
        return None


def _hora_actual(df, ahora):
    """Fila de un DataFrame horario de Open-Meteo (índice en hora local sin zona) más cercana a `ahora`."""

    return df.iloc[df.index.get_indexer([ahora.tz_localize(None).floor("h")], method="nearest")[0]]


def mostrar_nieve(ciudad, ahora, detalle):
    """Nieve de noviembre a abril; fuera de esos meses, solo si la ciudad lo pide y se prevé nieve en la semana."""

    if not ciudad.nieve or detalle is None:
        return False
    if ahora.month in MESES_NIEVE:
        return True
    proximas = detalle["horario"].loc[ahora.tz_localize(None).floor("h"):, "nieve"]
    return ciudad.nieve_fuera_de_temporada and proximas.sum() >= 1


def _texto_nubes(nubes):
    for limite, texto in [(20, "Despejado"), (50, "Poco nuboso"), (85, "Nuboso")]:
        if nubes < limite:
            return texto
    return "Cubierto"


def _texto_uv(uv):
    for limite, texto in [(3, "Bajo"), (6, "Moderado"), (8, "Alto"), (11, "Muy alto")]:
        if uv < limite:
            return texto
    return "Extremo"


def tarjetas_condiciones(ciudad, ahora, detalle, obs, aire):
    """Sensación térmica, humedad, nubes, UV, nieve (en temporada) y calidad del aire."""

    lista = []
    if detalle is not None:
        fila, diario = _hora_actual(detalle["horario"], ahora), detalle["diario"]
        hoy = ahora.tz_localize(None).normalize()

        lista.append({"label": "Sensación", "valor": f"{fila['sensacion']:.0f}º", "nota": "térmica ahora"})
        humedad = obs["humedad"].dropna() if obs is not None and "humedad" in obs else pd.Series(dtype=float)
        if not humedad.empty:
            lista.append({"label": "Humedad", "valor": f"{humedad.iloc[-1]:.0f}", "unidad": "%", "nota": "observada"})
        else:
            lista.append({"label": "Humedad", "valor": f"{fila['humedad']:.0f}", "unidad": "%", "nota": "prevista"})
        lista.append({"label": "Nubosidad", "valor": f"{fila['nubes']:.0f}", "unidad": "%",
                      "nota": _texto_nubes(fila["nubes"])})
        if hoy in diario.index and not pd.isna(diario.loc[hoy, "uv_max"]):
            uv = diario.loc[hoy, "uv_max"]
            lista.append({"label": "UV máx. hoy", "valor": f"{uv:.0f}", "nota": _texto_uv(uv)})

        if mostrar_nieve(ciudad, ahora, detalle):
            proximas = detalle["horario"].loc[hoy:hoy + pd.Timedelta(hours=48), "nieve"].sum()
            lista.append({"label": "Nieve 48 h", "valor": f"{proximas:.0f}", "unidad": "cm", "nota": "prevista"})
            espesor = fila["espesor_nieve"]
            if not pd.isna(espesor):
                lista.append({"label": "Espesor nieve", "valor": f"{100 * espesor:.0f}", "unidad": "cm",
                              "nota": "según el modelo"})

    if aire is not None and aire["european_aqi"].notna().any():
        ica = _hora_actual(aire.dropna(subset=["european_aqi"]), ahora)["european_aqi"]
        categoria, color = graficos.categoria_ica(ica)
        lista.append({"label": "Calidad del aire", "valor": f"{ica:.0f}", "nota": categoria, "color": color,
                      "title": "Índice europeo de calidad del aire (0-20 buena ... >100 extremadamente desfavorable)"})

    if lista:
        tarjetas.condiciones(lista)
        st.divider()


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def mostrar_resumen_mensual(ciudad, ahora, datos_hist):
    """Último mes publicado por AEMET para la estación, con la desviación respecto a 1991-2020 si hay histórico."""

    try:
        publicado = get_resumen_mensual(ciudad.estacion_aemet, ahora.year)
    except Exception:
        st.caption("No se ha podido consultar el resumen mensual de AEMET.")
        return False
    if publicado is None:
        return False

    año, mes, v = publicado
    normal = normales_mensuales(datos_hist, mes) if datos_hist is not None else None

    def numero(clave):
        try:
            return float(v[clave])
        except (KeyError, ValueError):  # ausente o "Ip" (inapreciable)
            return None

    lista = []
    for etiqueta, clave, clave_normal in [("Temp. media", "tm_mes", "tmed"), ("Máx. media", "tm_max", "tmax"),
                                          ("Mín. media", "tm_min", "tmin")]:
        valor = numero(clave)
        if valor is None:
            continue
        tarjeta = {"label": etiqueta, "valor": f"{valor:.1f}º"}
        if normal:
            desvio = valor - normal[clave_normal]
            tarjeta["nota"] = f"{desvio:+.1f}º sobre lo normal" if desvio >= 0 else f"{desvio:+.1f}º bajo lo normal"
            tarjeta["title"] = f"Normal de {MESES[mes - 1]} (1991-2020): {normal[clave_normal]:.1f}º"
            if abs(desvio) >= 1:
                tarjeta["color"] = ROJO if desvio > 0 else AZUL
        lista.append(tarjeta)

    lluvia = numero("p_mes")
    if lluvia is not None:
        tarjeta = {"label": "Lluvia", "valor": f"{lluvia:.1f}", "unidad": "L/m²"}
        if normal and normal["lluvia"] > 0:
            tarjeta["nota"] = f"{100 * lluvia / normal['lluvia']:.0f} % de lo normal"
            tarjeta["title"] = f"Normal de {MESES[mes - 1]} (1991-2020): {normal['lluvia']:.1f} L/m²"
        lista.append(tarjeta)
    dias_lluvia = numero("np_010")
    if dias_lluvia is not None:
        tarjeta = {"label": "Días de lluvia", "valor": f"{dias_lluvia:.0f}", "nota": "con ≥ 1 L/m²"}
        if normal:
            tarjeta["nota"] += f" (normal: {normal['dias_lluvia']:.0f})"
        lista.append(tarjeta)

    for etiqueta, clave in [("Máxima absoluta", "ta_max"), ("Mínima absoluta", "ta_min")]:
        valor, dia = valor_y_dia(v.get(clave))
        if valor is not None:
            lista.append({"label": etiqueta, "valor": f"{valor:.1f}º", "nota": f"el día {dia}" if dia else ""})
    racha, dia = racha_maxima(v.get("w_racha"))
    if racha is not None:
        lista.append({"label": "Racha máxima", "valor": f"{racha:.0f}", "unidad": "km/h", "nota": f"el día {dia}" if dia else ""})
    sol = numero("inso")
    if sol is not None:
        lista.append({"label": "Sol", "valor": f"{sol:.1f}", "unidad": "h/día", "nota": "insolación media"})
    for etiqueta, clave, nota in [("Días ≥ 30º", "nt_30", "de máxima"), ("Días de helada", "nt_00", "de mínima ≤ 0º")]:
        dias = numero(clave)
        if dias:
            lista.append({"label": etiqueta, "valor": f"{dias:.0f}", "nota": nota})

    if not lista:
        return False
    st.subheader(f"Resumen de {MESES[mes - 1]} de {año}")
    st.caption(f"Estación de {ciudad.nombre} según AEMET, frente al promedio de 1991-2020. "
               "AEMET publica el resumen mensual con unos días de retraso.")
    tarjetas.condiciones(lista)
    return True


PERIODOS = [(0, 6, "de madrugada"), (6, 12, "por la mañana"), (12, 18, "por la tarde"), (18, 24, "por la noche")]


def _lluvia_por_periodos(prec, fecha, desde=None):
    """(tramos con lluvia probable, probabilidad del día) según los miembros del ensemble; desde: primera hora a mirar.

    Un tramo es probable si al menos el 30 % de los miembros acumula UMBRAL_LLUVIA en él.
    """

    del_dia = prec[prec.index.date == fecha.date()]
    if desde is not None:
        del_dia = del_dia[del_dia.index >= desde]
    if del_dia.empty:
        return None, None
    horas = del_dia.index.hour
    periodos = [texto for inicio, fin, texto in PERIODOS
                if (p := prob_miembros(del_dia[(horas >= inicio) & (horas < fin)])) is not None and p >= 30]
    return periodos, prob_miembros(del_dia)


def _frase_lluvia(periodos, prob):
    if prob is None:
        return ""
    if len(periodos) == len(PERIODOS):
        return f", con lluvia probable todo el día ({prob:.0f} %)"
    if periodos:
        cuando = " y ".join([", ".join(periodos[:-1]), periodos[-1]]) if len(periodos) > 1 else periodos[0]
        return f", con lluvia probable {cuando} ({prob:.0f} %)"
    return ", sin lluvia" if prob < 10 else ""


def frases_resumen(ahora, max_hoy, horas_hoy, max_mañana, min_mañana, prec, rachas):
    """Resumen en texto de hoy y mañana a partir del ensemble a 48 h."""

    mañana = ahora + pd.Timedelta(days=1)
    frases = []

    lluvia_hoy = _lluvia_por_periodos(prec, ahora, desde=ahora.floor("h"))
    if ahora.hour < 15 and not pd.isna(max_hoy) and not horas_hoy:
        frases.append(f"Hoy, máxima de {max_hoy:.0f}º{_frase_lluvia(*lluvia_hoy)}.")
    elif (resto := _frase_lluvia(*lluvia_hoy).removeprefix(", ")):
        frases.append(f"Resto del día: {resto.removeprefix('con ')}.")

    if not pd.isna(max_mañana):
        diferencia = max_mañana - max_hoy if not pd.isna(max_hoy) else 0
        if diferencia >= 3:
            como = "más cálido"
        elif diferencia <= -3:
            como = "más fresco"
        elif abs(diferencia) >= 1.5:
            como = "algo más cálido" if diferencia > 0 else "algo más fresco"
        else:
            como = "temperaturas parecidas"
        minima = f" y {min_mañana:.0f}º de mínima" if not pd.isna(min_mañana) else ""
        frases.append(f"Mañana, {como}: {max_mañana:.0f}º de máxima{minima}"
                      f"{_frase_lluvia(*_lluvia_por_periodos(prec, mañana))}.")

    media_rachas = rachas.drop(columns="Observado", errors="ignore").mean(axis=1)
    media_rachas = media_rachas[media_rachas.index >= ahora.floor("h")]
    if not media_rachas.empty and media_rachas.max() >= 50:
        cuando = "hoy" if media_rachas.idxmax().date() == ahora.date() else "mañana"
        frases.append(f"Rachas fuertes {cuando}, de hasta {media_rachas.max():.0f} km/h.")
    return frases


def _cabecera(ciudad, titulo):
    """Título y hueco para los avisos oficiales (se rellenan al final: el feed de Meteoalarm es grande)."""

    if titulo:
        st.header(titulo)
    if ciudad.zonas_aviso:
        en_paralelo(get_avisos, ciudad.pais)
    return st.empty()


def _historico_sidebar(ciudad, ahora):
    """Histórico de la ciudad (o None) y, en el sidebar, los récords de hoy."""

    if not ciudad.historico:
        return None, None
    datos_hist, bandas = get_historico(ciudad.historico)
    tarjetas.records(datos_hist[datos_hist["día_del_año"] == dia_historico(ahora)],
                     probabilidad_lluvia(datos_hist, ahora))
    return datos_hist, bandas


def render_48h(ciudad, titulo=None):
    """Bloque de hoy y mañana: resumen, tarjetas, avisos, comentario de AEMET y el ensemble a 48 h."""

    ahora = pd.Timestamp.now(tz=ciudad.tz)
    mañana = ahora + pd.Timedelta(days=1)

    # Las demás fuentes se descargan mientras llega el ensemble; luego se leen de la caché
    hueco_avisos = _cabecera(ciudad, titulo)
    if ciudad.estacion_aemet:
        en_paralelo(get_aemet_horario, ciudad.estacion_aemet)
    en_paralelo(get_open_meteo_detalle, ciudad.lat, ciudad.lon, ciudad.tz)
    usa_opendata = hay_clave()
    if ciudad.ccaa_aemet and usa_opendata:
        for dia in DIAS_PREDICCION:
            en_paralelo(get_comentario_aemet, ciudad.ccaa_aemet[0], dia)
    if ciudad.calidad_aire:
        en_paralelo(get_calidad_aire, ciudad.lat, ciudad.lon, ciudad.tz)
    hueco_datos = st.empty()

    variables = ["temperatura", "precipitacion", "rachas"] + (["presion", "mucape"] if ciudad.presion_y_cape else [])
    if ciudad.ensemble == "ukmo":
        try:
            run, arome = get_ensemble_ukmo(ciudad.lat, ciudad.lon, ciudad.tz, tuple(variables))
        except Exception:
            st.error("No se ha podido descargar el ensemble de la Met Office (Open-Meteo). Prueba a recargar en unos minutos.")
            _avisos(ciudad, ahora, hueco_avisos)
            return
        fuentes = [f"Met Office de las {run.tz_convert(ciudad.tz):%H} h"] if run is not None else []
    else:
        try:
            run, arome = get_ensemble_arome(ciudad.lat, ciudad.lon, ciudad.tz, variables)
        except Exception:
            st.error("No se ha podido descargar el ensemble AROME de Meteociel. Prueba a recargar en unos minutos.")
            _avisos(ciudad, ahora, hueco_avisos)
            return
        fuentes = [f"AROME de las {hora_local_run(run, ciudad.tz)} h"]

    # --- Observaciones ---
    temp = arome["temperatura"]
    rachas = arome["rachas"]
    temp_actual = temp_ayer = None
    obs = None

    if ciudad.estacion_aemet:
        obs = cargar_aemet_horario(ciudad.estacion_aemet, ciudad.nombre)
        if obs is not None:
            fuentes.append(f"observación AEMET de las {obs.index[-1].hour} h")
            temp["Observado"] = obs["temperatura"]
            rachas["Observado"] = obs["racha"]
            arome["precipitacion"]["Observado"] = obs["precipitacion"]
        else:
            fuentes.append("observación AEMET no disponible")
        temp_actual, temp_ayer = temperatura_actual_y_ayer(obs)
    if fuentes:
        hueco_datos.markdown(f'<p class="datos-de">Pase {" · ".join(fuentes)}</p>', unsafe_allow_html=True)

    # --- Previsión a partir del ensemble ---
    ensemble = temp.drop(columns="Observado", errors="ignore")
    media = ensemble.mean(axis=1)

    fila_mañana = ensemble.iloc[ensemble.index.get_indexer([mañana.floor("h")], method="nearest")[0]]
    temp_mañana = round(fila_mañana.mean(), 1)
    fiabilidad = round(10 * np.exp(-0.05 * round(fila_mañana.std(), 1) ** 2.5), 1)

    # El pase empieza a su hora UTC: las horas de hoy anteriores se completan con lo observado
    serie = media
    if obs is not None and obs["temperatura"].notna().any():
        observado = obs["temperatura"].dropna().tz_convert(ciudad.tz)
        serie = pd.concat([observado, media[media.index > observado.index[-1]]])

    max_hoy, min_hoy, horas_hoy = extremos_del_dia(serie, ahora)
    max_mañana, min_mañana, horas_mañana = extremos_del_dia(serie, mañana)

    # --- Histórico ---
    datos_hist, bandas = _historico_sidebar(ciudad, ahora)
    percentiles = {}
    if datos_hist is not None:
        def percentil(fecha, columna, valor, horas):
            """Porcentaje de años del histórico con un valor inferior (los empates cuentan la mitad).

            Solo con el día completo: un extremo de unas pocas horas no es comparable con el histórico.
            """
            registros = datos_hist.loc[datos_hist["día_del_año"] == dia_historico(fecha), columna].dropna()
            if registros.empty or pd.isna(valor) or horas:
                return None
            return 100 * ((registros < valor).mean() + (registros <= valor).mean()) / 2

        percentiles = {
            "max_hoy": percentil(ahora, "tmax", max_hoy, horas_hoy),
            "min_hoy": percentil(ahora, "tmin", min_hoy, horas_hoy),
            "max_mañana": percentil(mañana, "tmax", max_mañana, horas_mañana),
            "min_mañana": percentil(mañana, "tmin", min_mañana, horas_mañana),
        }

    # --- Resumen, tarjetas y avisos ---
    tarjetas.resumen(frases_resumen(ahora, max_hoy, horas_hoy, max_mañana, min_mañana, arome["precipitacion"], rachas))
    tarjetas.principales(temp_mañana, fiabilidad, temp_actual, temp_ayer)
    st.divider()

    extremos = [
        {"label": "Máxima hoy", "temp": max_hoy, "perc": percentiles.get("max_hoy"), "horas": horas_hoy},
        {"label": "Mínima mañana", "temp": min_mañana, "perc": percentiles.get("min_mañana"), "horas": horas_mañana},
        {"label": "Máxima mañana", "temp": max_mañana, "perc": percentiles.get("max_mañana"), "horas": horas_mañana},
    ]
    if ahora.hour < 9:
        extremos.insert(0, {"label": "Mínima hoy", "temp": min_hoy, "perc": percentiles.get("min_hoy"), "horas": horas_hoy})
    tarjetas.extremos([e for e in extremos if not pd.isna(e["temp"])])
    st.divider()

    if tarjetas.avisos(percentiles.get("max_hoy"), percentiles.get("max_mañana")):
        st.divider()

    detalle = _o_none(get_open_meteo_detalle, ciudad.lat, ciudad.lon, ciudad.tz)
    aire = _o_none(get_calidad_aire, ciudad.lat, ciudad.lon, ciudad.tz) if ciudad.calidad_aire else None
    tarjetas_condiciones(ciudad, ahora, detalle, obs, aire)

    # --- Comentario de los predictores de AEMET ---
    if ciudad.ccaa_aemet and usa_opendata:
        codigo, lugar = ciudad.ccaa_aemet
        textos = [t for t in (_o_none(get_comentario_aemet, codigo, dia) for dia in DIAS_PREDICCION) if t is not None]
        if not textos:
            st.caption("No se ha podido consultar el comentario de los predictores de AEMET.")
        elif tarjetas.comentario_predictores(textos, lugar, ahora):
            st.divider()

    # --- Ensemble a 48 h ---
    st.plotly_chart(graficos.temperatura(temp, bandas, dia_historico(ahora)))
    st.plotly_chart(graficos.lluvia(arome["precipitacion"]))
    st.plotly_chart(graficos.viento(rachas, obs["dir_racha"] if obs is not None else None))
    if ciudad.presion_y_cape:
        # Plegado salvo que el ensemble vea potencial de tormenta
        cape = arome["mucape"].drop(columns="Observado", errors="ignore").mean(axis=1).max()
        tormenta = not pd.isna(cape) and cape >= 500
        etiqueta = "Presión y tormentas" + (" · potencial de tormenta" if tormenta else "")
        with st.expander(etiqueta, icon=":material/thunderstorm:", expanded=tormenta):
            st.plotly_chart(graficos.presion(arome["presion"]))
            st.plotly_chart(graficos.mucape(arome["mucape"]))
    st.divider()

    # --- Histórico frente a la previsión ---
    if datos_hist is not None:
        desde = datos_hist.index.min().year
        st.subheader("Hoy y mañana frente al histórico")
        st.caption(f"Temperaturas registradas un día como hoy desde {desde}; los puntos grandes son la previsión.")
        prev_hoy = (np.nan, np.nan) if horas_hoy else (min_hoy, max_hoy)
        prev_mañana = (np.nan, np.nan) if horas_mañana else (min_mañana, max_mañana)
        st.plotly_chart(graficos.historico_vs_prevision(datos_hist, dia_historico(ahora), prev_hoy, prev_mañana))
        st.divider()

    st.plotly_chart(graficos.elevacion_solar(ciudad.lat, ciudad.lon, ciudad.tz))

    # --- Cámaras ---
    if ciudad.camaras:
        st.divider()
        st.subheader("Cámaras de tráfico")
        marca = int(ahora.timestamp())  # evita que el navegador muestre imágenes antiguas en caché
        celdas = "".join(
            f'<div class="camera-card"><img src="{url}?rand={marca}" alt="Cámara de tráfico" loading="lazy"></div>'
            for url in ciudad.camaras
        )
        st.markdown(f'<div class="camera-grid">{celdas}</div>', unsafe_allow_html=True)

    _avisos(ciudad, ahora, hueco_avisos)


MODELOS_LARGO = ["ecmwf_ifs025", "gfs_seamless"]


def render_medio(ciudad, titulo=None):
    """Medio plazo, de ahora hasta donde llegue el ensemble ICON-EU (40 miembros, unas 120 h), con el ICON-EU
    determinista; nubes, nieve y calidad del aire."""

    ahora = pd.Timestamp.now(tz=ciudad.tz)
    desde = ahora.floor("h")
    fechas = list(pd.date_range(ahora.tz_localize(None).normalize(), periods=6).date)

    hueco_avisos = _cabecera(ciudad, titulo)
    en_paralelo(get_deterministas, ciudad.lat, ciudad.lon, ciudad.tz)
    en_paralelo(get_open_meteo_detalle, ciudad.lat, ciudad.lon, ciudad.tz)
    if ciudad.calidad_aire:
        en_paralelo(get_calidad_aire, ciudad.lat, ciudad.lon, ciudad.tz)
    _historico_sidebar(ciudad, ahora)

    try:
        icon_completo = get_ensemble(ciudad.lat, ciudad.lon, ciudad.tz, "icon_eu")
    except Exception:
        icon_completo = None
        st.warning("No se ha podido descargar el ensemble ICON-EU de Open-Meteo.")
    icon = {var: df[df.index >= desde] for var, df in icon_completo.items()} if icon_completo else None
    detalle = _o_none(get_open_meteo_detalle, ciudad.lat, ciudad.lon, ciudad.tz)
    hasta = icon["temperatura"].index[-1] if icon is not None and not icon["temperatura"].empty else None

    if hasta is not None:
        # --- Tira de días: mediana de los miembros, probabilidad por miembros y tiempo de Open-Meteo ---
        # Hoy cuenta aunque el pase empiece a medianoche UTC (20 h bastan); el último día, solo si llega completo
        maximas, minimas = extremos_diarios(icon_completo["temperatura"], fechas, minimo_horas=20)
        prob = prob_diaria(icon_completo["precipitacion"], desde)  # de hoy, solo lo que queda
        codigos = detalle["diario"]["codigo"] if detalle is not None else pd.Series(dtype=float)
        dias = [{"fecha": f, "tmax": maximas.loc[f].median(), "tmin": minimas.loc[f].median(), "prob": prob.get(f),
                 "codigo": codigos.get(pd.Timestamp(f)), "nombre": "Hoy" if f == ahora.date() else None}
                for f in maximas.index]
        tarjetas.tira_dias(dias, f"Mediana de máxima y mínima y probabilidad de al menos {UMBRAL_LLUVIA} L/m² según "
                                 f"los {icon['temperatura'].shape[1]} miembros del ensemble ICON-EU.")
        st.divider()

        deterministas = _o_none(get_deterministas, ciudad.lat, ciudad.lon, ciudad.tz)
        det_temp = deterministas["temperatura"] if deterministas is not None else pd.DataFrame()
        st.plotly_chart(graficos.medio_temperatura(icon["temperatura"], det_temp))
        st.plotly_chart(graficos.lluvia(icon["precipitacion"], titulo="Lluvia · medio plazo"))
        st.plotly_chart(graficos.viento(icon["rachas"], titulo="Rachas de viento · medio plazo"))
        st.divider()

    # --- Nubes, UV y nieve hasta donde llega el ICON-EU (o 5 días si no hay ensemble) ---
    if detalle is not None:
        hoy = ahora.tz_localize(None).normalize()
        fin = hasta.tz_localize(None) if hasta is not None else hoy + pd.Timedelta(days=5)
        dias_detalle = detalle["diario"][(detalle["diario"].index >= hoy) & (detalle["diario"].index <= fin)]
        st.plotly_chart(graficos.nubes_uv(dias_detalle, "Nubosidad y UV · medio plazo"))
        if mostrar_nieve(ciudad, ahora, detalle):
            horas = detalle["horario"]
            horas = horas[(horas.index >= desde.tz_localize(None)) & (horas.index <= fin)]
            st.plotly_chart(graficos.nieve(horas, dias_detalle, "Nieve y cota de nieve · medio plazo",
                                           detalle["elevacion"]))
        st.divider()

    # --- Calidad del aire y polen (los 4 días que da CAMS) ---
    aire = _o_none(get_calidad_aire, ciudad.lat, ciudad.lon, ciudad.tz) if ciudad.calidad_aire else None
    if aire is not None and aire["european_aqi"].notna().any():
        st.plotly_chart(graficos.calidad_aire(aire))
        con_polen = {f"{clave}_pollen": nombre for clave, nombre in POLENES.items() if aire[f"{clave}_pollen"].max() >= 1}
        if con_polen:
            st.plotly_chart(graficos.polen(aire, con_polen))

    _avisos(ciudad, ahora, hueco_avisos)


def render_largo(ciudad, titulo=None):
    """Largo plazo, de hoy a 15 días: ensembles ECMWF y GEFS juntos y, al final, el último resumen mensual de AEMET."""

    ahora = pd.Timestamp.now(tz=ciudad.tz)
    fechas = list(pd.date_range(ahora.tz_localize(None).normalize(), periods=15).date)

    hueco_avisos = _cabecera(ciudad, titulo)
    for modelo in MODELOS_LARGO:
        en_paralelo(get_ensemble, ciudad.lat, ciudad.lon, ciudad.tz, modelo)
    usa_opendata = hay_clave()
    if ciudad.resumen_mensual and ciudad.estacion_aemet and usa_opendata:
        en_paralelo(get_resumen_mensual, ciudad.estacion_aemet, ahora.year)
    datos_hist, _ = _historico_sidebar(ciudad, ahora)

    ensembles = {}
    for modelo in MODELOS_LARGO:
        nombre = ENSEMBLES[modelo][0]
        if (datos := _o_none(get_ensemble, ciudad.lat, ciudad.lon, ciudad.tz, modelo)) is not None:
            # La lluvia de hoy, solo la que queda; la temperatura, del día entero para sus extremos
            ensembles[nombre] = {**datos, "precipitacion": datos["precipitacion"][datos["precipitacion"].index >= ahora.floor("h")]}
        else:
            st.warning(f"No se ha podido descargar el ensemble {nombre} de Open-Meteo.")
    if ensembles:
        st.plotly_chart(graficos.largo(ensembles, fechas, hoy=ahora.date()))
        st.caption("Bandas: rango 10-90 % de todos los miembros; líneas finas: mediana de cada modelo. Barras, por "
                   f"modelo: probabilidad de al menos {UMBRAL_LLUVIA} L/m² en el día y lluvia media de sus miembros.")

    if ciudad.resumen_mensual and ciudad.estacion_aemet and usa_opendata:
        st.divider()
        mostrar_resumen_mensual(ciudad, ahora, datos_hist)

    _avisos(ciudad, ahora, hueco_avisos)


def _avisos(ciudad, ahora, hueco):
    """Avisos oficiales de Meteoalarm en el hueco reservado al principio de la página."""

    if not ciudad.zonas_aviso:
        return
    with hueco.container():
        try:
            vigentes = avisos_vigentes(ciudad.pais, ciudad.zonas_aviso, ahora)
        except Exception:
            st.caption("No se han podido consultar los avisos oficiales (Meteoalarm).")
        else:
            tarjetas.avisos_oficiales(vigentes, ahora)


BLOQUES = [":material/schedule: Corto plazo", ":material/view_week: Medio plazo", ":material/date_range: Largo plazo"]
RENDER_BLOQUES = [render_48h, render_medio, render_largo]


def render_pagina(ciudad, titulo=None):
    """Una ciudad en pestañas: corto, medio y largo plazo, radar y, si tiene, mapas AROME. Solo se descarga la abierta."""

    titulo = titulo or ciudad.nombre
    nombres = BLOQUES + [":material/radar: Radar"]
    if ciudad.mapas_arome:
        nombres.append(":material/map: Mapas AROME")
    pestañas = st.tabs(nombres, key=f"vista_{ciudad.nombre}", on_change="rerun")

    for pestaña, render in zip(pestañas, RENDER_BLOQUES):
        if pestaña.open:
            with pestaña:
                render(ciudad, titulo)
    radar = len(BLOQUES)
    if pestañas[radar].open:
        with pestañas[radar]:
            render_radar([(ciudad.nombre, ciudad.lat, ciudad.lon)], ciudad.tz)
    if ciudad.mapas_arome and pestañas[radar + 1].open:
        from .mapas_arome import render_arome_maps

        with pestañas[radar + 1]:
            render_arome_maps(location=ciudad.mapas_arome)


def render_grupo(titulo, ciudades):
    """Varias localidades en pestañas (cada una con sus tres plazos), más una con el radar de la zona."""

    st.header(titulo)
    pestañas = st.tabs([c.nombre for c in ciudades] + [":material/radar: Radar"], key=f"grupo_{titulo}",
                       on_change="rerun")
    for pestaña, ciudad in zip(pestañas, ciudades):
        if pestaña.open:
            with pestaña:
                bloques = st.tabs(BLOQUES, key=f"bloque_{titulo}_{ciudad.nombre}", on_change="rerun")
                for bloque, render in zip(bloques, RENDER_BLOQUES):
                    if bloque.open:
                        with bloque:
                            render(ciudad)
    if pestañas[-1].open:
        with pestañas[-1]:
            render_radar([(c.nombre, c.lat, c.lon) for c in ciudades], ciudades[0].tz)
