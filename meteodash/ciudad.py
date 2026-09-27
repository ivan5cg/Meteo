"""Página de previsión de una ciudad, montada según las fuentes de datos que tenga configuradas."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st
from scipy.stats import percentileofscore

from . import graficos, tarjetas
from .aemet import cargar_aemet_horario, temperatura_actual_y_ayer
from .fuentes import dia_historico, get_ensemble_arome, get_ensemble_gefs, get_historico, get_open_meteo, hora_local_run


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
    mapas_arome: str | None = None  # clave de arome_maps.LOCATIONS


def render_ciudad(ciudad, titulo=None):
    if titulo:
        st.header(titulo)

    ahora = pd.Timestamp.now(tz=ciudad.tz)
    mañana = ahora + pd.Timedelta(days=1)

    variables = ["temperatura", "precipitacion", "rachas"] + (["presion", "mucape"] if ciudad.presion_y_cape else [])
    try:
        run, arome = get_ensemble_arome(ciudad.lat, ciudad.lon, ciudad.tz, variables)
    except Exception:
        st.error("No se ha podido descargar el ensemble AROME de Meteociel. Prueba a recargar en unos minutos.")
        return

    st.sidebar.subheader(f"Previsión más reciente: {hora_local_run(run, ciudad.tz)} horas")

    # --- Observaciones ---
    temp = arome["temperatura"]
    rachas = arome["rachas"]
    obs = None
    temp_actual = temp_ayer = None

    if ciudad.estacion_aemet:
        obs = cargar_aemet_horario(ciudad.estacion_aemet, ciudad.nombre)
        if obs is not None:
            st.sidebar.subheader(f"Datos más recientes: {obs.index[0].hour} horas")
            temp["Actual data"] = obs["Temperatura (ºC)"]
            rachas["Actual data"] = obs["Racha (km/h)"]
        else:
            st.sidebar.subheader("Datos más recientes: no disponibles")
        temp_actual, temp_ayer = temperatura_actual_y_ayer(obs, temp)

    # --- Previsión a partir del ensemble ---
    ensemble = temp.drop(columns="Actual data", errors="ignore")
    media = ensemble.mean(axis=1)

    fila_mañana = ensemble.iloc[ensemble.index.get_indexer([mañana.floor("h")], method="nearest")[0]]
    temp_mañana = round(fila_mañana.mean(), 1)
    fiabilidad = round(10 * np.exp(-0.05 * round(fila_mañana.std(), 1) ** 2.5), 1)

    def extremo(fecha, funcion):
        del_dia = media[media.index.date == fecha.date()]
        return round(getattr(del_dia, funcion)(), 1) if not del_dia.empty else np.nan

    max_hoy, min_hoy = extremo(ahora, "max"), extremo(ahora, "min")
    max_mañana, min_mañana = extremo(mañana, "max"), extremo(mañana, "min")

    # --- Histórico ---
    datos_hist = bandas = None
    percentiles = {}
    if ciudad.historico:
        datos_hist, bandas = get_historico(ciudad.historico)

        def percentil(fecha, columna, valor):
            registros = datos_hist.loc[datos_hist["día_del_año"] == dia_historico(fecha), columna].dropna()
            return percentileofscore(registros, valor) if len(registros) and not pd.isna(valor) else None

        percentiles = {
            "max_hoy": percentil(ahora, "tmax", max_hoy),
            "min_hoy": percentil(ahora, "tmin", min_hoy),
            "max_mañana": percentil(mañana, "tmax", max_mañana),
            "min_mañana": percentil(mañana, "tmin", min_mañana),
        }
        tarjetas.records(datos_hist[datos_hist["día_del_año"] == dia_historico(ahora)])

    # --- Tarjetas y avisos ---
    tarjetas.principales(temp_mañana, fiabilidad, temp_actual, temp_ayer)
    st.divider()

    extremos = [
        {"label": "Máxima hoy", "temp": max_hoy, "perc": percentiles.get("max_hoy")},
        {"label": "Mínima mañana", "temp": min_mañana, "perc": percentiles.get("min_mañana")},
        {"label": "Máxima mañana", "temp": max_mañana, "perc": percentiles.get("max_mañana")},
    ]
    if ahora.hour < 9:
        extremos.insert(0, {"label": "Mínima hoy", "temp": min_hoy, "perc": percentiles.get("min_hoy")})
    tarjetas.extremos(extremos)
    st.divider()

    if percentiles.get("max_hoy") is not None and percentiles.get("max_mañana") is not None:
        if tarjetas.avisos(percentiles["max_hoy"], percentiles["max_mañana"]):
            st.divider()

    # --- 48 h: ensemble AROME ---
    dia_bandas = dia_historico(temp.index[min(27, len(temp) - 1)]) if bandas is not None else None
    st.plotly_chart(graficos.temperatura(temp, bandas, dia_bandas), use_container_width=True)
    st.plotly_chart(graficos.lluvia(arome["precipitacion"]), use_container_width=True)
    st.plotly_chart(graficos.viento(rachas), use_container_width=True)
    if ciudad.presion_y_cape:
        st.plotly_chart(graficos.presion(arome["presion"]), use_container_width=True)
        st.plotly_chart(graficos.mucape(arome["mucape"]), use_container_width=True)
    st.divider()

    # --- Semana: multimodelo Open-Meteo ---
    if ciudad.semana:
        try:
            semana = get_open_meteo(ciudad.lat, ciudad.lon, ciudad.tz)
        except Exception:
            st.warning("No se ha podido descargar la previsión semanal de Open-Meteo.")
        else:
            st.plotly_chart(graficos.semana_temperatura(semana["temperatura"]), use_container_width=True)
            st.plotly_chart(graficos.semana_lluvia(semana["precipitacion"]), use_container_width=True)
            st.plotly_chart(graficos.semana_viento(semana["rachas"]), use_container_width=True)
        st.divider()

    # --- Histórico frente a la previsión ---
    if datos_hist is not None:
        desde = datos_hist.index.min().year
        st.subheader("Temperaturas Históricas vs. Previsión")
        st.markdown(f"Distribución de las temperaturas registradas un día como hoy desde {desde}. "
                    "Los puntos destacados indican la previsión para hoy y mañana.")
        fig = graficos.historico_vs_prevision(datos_hist, dia_historico(ahora), (min_hoy, max_hoy), (min_mañana, max_mañana))
        st.plotly_chart(fig, use_container_width=True)
        st.divider()

    st.plotly_chart(graficos.elevacion_solar(ciudad.lat, ciudad.lon, ciudad.tz), use_container_width=True)

    # --- 15 días: GEFS ---
    if ciudad.gefs:
        st.divider()
        try:
            st.plotly_chart(graficos.gefs(get_ensemble_gefs(ciudad.lat, ciudad.lon, ciudad.tz)), use_container_width=True)
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

    from arome_maps import render_arome_maps

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
