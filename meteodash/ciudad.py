"""Página de previsión de una ciudad, montada según las fuentes de datos que tenga configuradas."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

from . import graficos, tarjetas
from .aemet import cargar_aemet_horario, get_aemet_horario, temperatura_actual_y_ayer
from .avisos import avisos_vigentes, get_avisos
from .fuentes import (POLENES, RUNS_GEFS, dia_historico, en_paralelo, get_calidad_aire, get_ensemble_arome,
                      get_ensemble_ecmwf, get_ensemble_gefs, get_historico, get_meteociel_table, get_open_meteo,
                      get_open_meteo_detalle, hora_local_run, probabilidad_lluvia, url_gefs)
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
    presion_y_cape: bool = True
    semana: bool = False  # previsión multimodelo de Open-Meteo para 7 días
    gefs: bool = False  # ensemble GFS a 15 días
    ens_ecmwf: bool = False  # ensemble ECMWF a 15 días (Open-Meteo)
    nieve: bool = False  # nieve prevista, espesor y cota de nieve (solo en MESES_NIEVE)
    nieve_fuera_de_temporada: bool = False  # también fuera de MESES_NIEVE si se prevé nieve en la semana
    calidad_aire: bool = True  # índice europeo de calidad del aire y polen
    pais: str = "spain"  # feed de avisos de Meteoalarm
    zonas_aviso: tuple[str, ...] = ()  # códigos o nombres de las zonas de aviso de Meteoalarm
    camaras: tuple[str, ...] = ()
    mapas_arome: str | None = None  # clave de mapas_arome.LOCATIONS


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


def render_ciudad(ciudad, titulo=None):
    if titulo:
        st.header(titulo)

    ahora = pd.Timestamp.now(tz=ciudad.tz)
    mañana = ahora + pd.Timedelta(days=1)

    # Las demás fuentes se descargan mientras llega AROME; luego se leen de la caché (los errores se ven al leerlas)
    if ciudad.estacion_aemet:
        en_paralelo(get_aemet_horario, ciudad.estacion_aemet)
    if ciudad.zonas_aviso:
        en_paralelo(get_avisos, ciudad.pais)
    en_paralelo(get_open_meteo_detalle, ciudad.lat, ciudad.lon, ciudad.tz)
    if ciudad.calidad_aire:
        en_paralelo(get_calidad_aire, ciudad.lat, ciudad.lon, ciudad.tz)
    if ciudad.semana:
        en_paralelo(get_open_meteo, ciudad.lat, ciudad.lon, ciudad.tz)
    if ciudad.ens_ecmwf:
        en_paralelo(get_ensemble_ecmwf, ciudad.lat, ciudad.lon, ciudad.tz)
    if ciudad.gefs:  # las tablas de cada pase, no get_ensemble_gefs: una tarea del pool no debe esperar a otras
        for run in RUNS_GEFS:
            en_paralelo(get_meteociel_table, f"{url_gefs(ciudad.lat, ciudad.lon)}&run={run}", ciudad.tz)

    # Los avisos van arriba, pero se rellenan al final: el feed de Meteoalarm es grande y no debe frenar la página
    hueco_avisos = st.empty()

    variables = ["temperatura", "precipitacion", "rachas"] + (["presion", "mucape"] if ciudad.presion_y_cape else [])
    try:
        run, arome = get_ensemble_arome(ciudad.lat, ciudad.lon, ciudad.tz, variables)
    except Exception:
        st.error("No se ha podido descargar el ensemble AROME de Meteociel. Prueba a recargar en unos minutos.")
        _avisos(ciudad, ahora, hueco_avisos)
        return

    st.sidebar.subheader(f"Pase AROME de las {hora_local_run(run, ciudad.tz)} h")

    # --- Observaciones ---
    temp = arome["temperatura"]
    rachas = arome["rachas"]
    temp_actual = temp_ayer = None
    obs = None

    if ciudad.estacion_aemet:
        obs = cargar_aemet_horario(ciudad.estacion_aemet, ciudad.nombre)
        if obs is not None:
            st.sidebar.subheader(f"Observación AEMET de las {obs.index[-1].hour} h")
            temp["Observado"] = obs["temperatura"]
            rachas["Observado"] = obs["racha"]
            arome["precipitacion"]["Observado"] = obs["precipitacion"]
        else:
            st.sidebar.subheader("Observación AEMET no disponible")
        temp_actual, temp_ayer = temperatura_actual_y_ayer(obs)

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
    datos_hist = bandas = None
    percentiles = {}
    if ciudad.historico:
        datos_hist, bandas = get_historico(ciudad.historico)

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
        tarjetas.records(datos_hist[datos_hist["día_del_año"] == dia_historico(ahora)],
                         probabilidad_lluvia(datos_hist, ahora))

    # --- Tarjetas y avisos ---
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

    # --- 48 h: ensemble AROME ---
    st.plotly_chart(graficos.temperatura(temp, bandas, dia_historico(ahora)))
    st.plotly_chart(graficos.lluvia(arome["precipitacion"]))
    st.plotly_chart(graficos.viento(rachas, obs["dir_racha"] if obs is not None else None))
    if ciudad.presion_y_cape:
        st.plotly_chart(graficos.presion(arome["presion"]))
        st.plotly_chart(graficos.mucape(arome["mucape"]))
    st.divider()

    # --- Semana: multimodelo Open-Meteo ---
    if ciudad.semana:
        try:
            semana = get_open_meteo(ciudad.lat, ciudad.lon, ciudad.tz)
        except Exception:
            st.warning("No se ha podido descargar la previsión semanal de Open-Meteo.")
        else:
            st.plotly_chart(graficos.semana_temperatura(semana["temperatura"]))
            st.plotly_chart(graficos.semana_lluvia(semana["precipitacion"]))
            st.plotly_chart(graficos.semana_viento(semana["rachas"]))
        if detalle is not None:
            proximos = detalle["diario"][detalle["diario"].index >= ahora.tz_localize(None).normalize()].head(7)
            st.plotly_chart(graficos.semana_nubes_uv(proximos))
        st.divider()

    # --- Nieve ---
    if mostrar_nieve(ciudad, ahora, detalle):
        hoy = ahora.tz_localize(None).normalize()
        st.plotly_chart(graficos.nieve(detalle["horario"][detalle["horario"].index >= hoy],
                                       detalle["diario"][detalle["diario"].index >= hoy], detalle["elevacion"]))
        st.divider()

    # --- Histórico frente a la previsión ---
    if datos_hist is not None:
        desde = datos_hist.index.min().year
        st.subheader("Temperaturas Históricas vs. Previsión")
        st.markdown(f"Distribución de las temperaturas registradas un día como hoy desde {desde}. "
                    "Los puntos destacados indican la previsión para hoy y mañana.")
        prev_hoy = (np.nan, np.nan) if horas_hoy else (min_hoy, max_hoy)
        prev_mañana = (np.nan, np.nan) if horas_mañana else (min_mañana, max_mañana)
        fig = graficos.historico_vs_prevision(datos_hist, dia_historico(ahora), prev_hoy, prev_mañana)
        st.plotly_chart(fig)
        st.divider()

    # --- Calidad del aire y polen ---
    if aire is not None and aire["european_aqi"].notna().any():
        st.plotly_chart(graficos.calidad_aire(aire))
        con_polen = {f"{clave}_pollen": nombre for clave, nombre in POLENES.items() if aire[f"{clave}_pollen"].max() >= 1}
        if con_polen:
            st.plotly_chart(graficos.polen(aire, con_polen))
        st.divider()

    st.plotly_chart(graficos.elevacion_solar(ciudad.lat, ciudad.lon, ciudad.tz))

    # --- 15 días: ensembles ECMWF y GEFS ---
    if ciudad.ens_ecmwf:
        st.divider()
        try:
            ecmwf = get_ensemble_ecmwf(ciudad.lat, ciudad.lon, ciudad.tz)
        except Exception:
            st.warning("No se ha podido descargar el ensemble ECMWF de Open-Meteo.")
        else:
            st.plotly_chart(graficos.ecmwf_ensemble(ecmwf["temperatura"], ecmwf["precipitacion"]))

    if ciudad.gefs:
        st.divider()
        try:
            st.plotly_chart(graficos.gefs(get_ensemble_gefs(ciudad.lat, ciudad.lon, ciudad.tz)))
        except Exception:
            st.warning("No se ha podido descargar el ensemble GEFS de Meteociel.")

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


def render_pagina(ciudad, titulo=None):
    """Una ciudad en pestañas: previsión, radar y, si tiene, mapas AROME. Solo se descarga la pestaña abierta."""

    titulo = titulo or ciudad.nombre
    nombres = [":material/dashboard: Previsión", ":material/radar: Radar"]
    if ciudad.mapas_arome:
        nombres.append(":material/map: Mapas AROME")
    pestañas = st.tabs(nombres, key=f"vista_{ciudad.nombre}", on_change="rerun")

    if pestañas[0].open:
        with pestañas[0]:
            render_ciudad(ciudad, titulo)
    if pestañas[1].open:
        with pestañas[1]:
            render_radar([(ciudad.nombre, ciudad.lat, ciudad.lon)], ciudad.tz)
    if ciudad.mapas_arome and pestañas[2].open:
        from .mapas_arome import render_arome_maps

        with pestañas[2]:
            render_arome_maps(location=ciudad.mapas_arome)


def render_grupo(titulo, ciudades):
    """Varias localidades en pestañas, más una con el radar de la zona; solo se descarga la pestaña abierta."""

    st.header(titulo)
    pestañas = st.tabs([c.nombre for c in ciudades] + [":material/radar: Radar"], key=f"grupo_{titulo}",
                       on_change="rerun")
    for pestaña, ciudad in zip(pestañas, ciudades):
        if pestaña.open:
            with pestaña:
                render_ciudad(ciudad)
    if pestañas[-1].open:
        with pestañas[-1]:
            render_radar([(c.nombre, c.lat, c.lon) for c in ciudades], ciudades[0].tz)
