"""Página de previsión de una ciudad, montada según las fuentes de datos que tenga configuradas."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

from . import graficos, tarjetas
from .aemet import cargar_aemet_horario, get_aemet_horario, temperatura_actual_y_ayer
from .fuentes import (RUNS_GEFS, dia_historico, en_paralelo, get_ensemble_arome, get_ensemble_gefs, get_historico,
                      get_meteociel_table, get_open_meteo, hora_local_run, url_gefs)


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


def render_ciudad(ciudad, titulo=None):
    if titulo:
        st.header(titulo)

    ahora = pd.Timestamp.now(tz=ciudad.tz)
    mañana = ahora + pd.Timedelta(days=1)

    # Las demás fuentes se descargan mientras llega AROME; luego se leen de la caché (los errores se ven al leerlas)
    if ciudad.estacion_aemet:
        en_paralelo(get_aemet_horario, ciudad.estacion_aemet)
    if ciudad.semana:
        en_paralelo(get_open_meteo, ciudad.lat, ciudad.lon, ciudad.tz)
    if ciudad.gefs:  # las tablas de cada pase, no get_ensemble_gefs: una tarea del pool no debe esperar a otras
        for run in RUNS_GEFS:
            en_paralelo(get_meteociel_table, f"{url_gefs(ciudad.lat, ciudad.lon)}&run={run}", ciudad.tz)

    variables = ["temperatura", "precipitacion", "rachas"] + (["presion", "mucape"] if ciudad.presion_y_cape else [])
    try:
        run, arome = get_ensemble_arome(ciudad.lat, ciudad.lon, ciudad.tz, variables)
    except Exception:
        st.error("No se ha podido descargar el ensemble AROME de Meteociel. Prueba a recargar en unos minutos.")
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
        tarjetas.records(datos_hist[datos_hist["día_del_año"] == dia_historico(ahora)])

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

    # --- 48 h: ensemble AROME ---
    st.plotly_chart(graficos.temperatura(temp, bandas, dia_historico(ahora)))
    st.plotly_chart(graficos.lluvia(arome["precipitacion"]))
    st.plotly_chart(graficos.viento(rachas))
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

    st.plotly_chart(graficos.elevacion_solar(ciudad.lat, ciudad.lon, ciudad.tz))

    # --- 15 días: GEFS ---
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


def render_pagina(ciudad, titulo=None):
    """Una ciudad; si tiene mapas AROME, en dos pestañas (previsión y mapas)."""

    titulo = titulo or ciudad.nombre
    if not ciudad.mapas_arome:
        render_ciudad(ciudad, titulo)
        return

    from .mapas_arome import render_arome_maps

    prevision, mapas = st.tabs(
        [":material/dashboard: Previsión", ":material/map: Mapas AROME"],
        key=f"vista_{ciudad.nombre}",
        on_change="rerun",
    )
    if prevision.open:
        with prevision:
            render_ciudad(ciudad, titulo)
    if mapas.open:
        with mapas:
            render_arome_maps(location=ciudad.mapas_arome)


def render_grupo(titulo, ciudades):
    """Varias localidades en pestañas; solo se descarga la pestaña abierta."""

    st.header(titulo)
    pestañas = st.tabs([c.nombre for c in ciudades], key=f"grupo_{titulo}", on_change="rerun")
    for pestaña, ciudad in zip(pestañas, ciudades):
        if pestaña.open:
            with pestaña:
                render_ciudad(ciudad)
