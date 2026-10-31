"""Auroras boreales: puntuación de cada noche, viento solar, óvalo auroral y previsión a 27 días.

La puntuación combina, hora a hora, la actividad geomagnética prevista (NOAA SWPC), el cielo despejado (91 miembros
de ensemble y las capas de nubes de Open-Meteo), la oscuridad, la luna, la visibilidad y la cercanía a la medianoche
magnética. Sirve para lugares bajo el óvalo auroral (Laponia) o algo más al sur (sur de Finlandia, el Báltico y
Escocia): `Ciudad.kp_auroras` es el Kp a partir del cual suelen verse allí con el cielo despejado y oscuro (ver
lugares.py).
"""

import re

import numpy as np
import pandas as pd
import pytz
import streamlit as st
from astral import Observer, moon, sun

from . import graficos, luna, tarjetas
from .fuentes import descargar, en_paralelo, o_none
from .graficos import valoracion_kp

SWPC = "https://services.swpc.noaa.gov"

NOCHES = 7  # noches puntuadas: unas 3 con el Kp previsto cada 3 h y el resto con la previsión a 27 días
NOCHES_DETALLE = 3  # las que se muestran con todos sus factores
VENTANA = 3  # horas seguidas de la mejor ventana de la noche, la que da su puntuación

# Factores de la puntuación (0-1): la probabilidad de cada hora es su producto. Nombre, qué mide y qué resta
FACTORES = {
    "actividad": ("Actividad", "Kp previsto frente al que suele bastar aquí y probabilidad de tormenta geomagnética",
                  "la poca actividad"),
    "cielo": ("Cielo", "Parte del cielo despejada según 91 miembros de ensemble (ICON-EU y ECMWF) y las capas de "
                       "nubes: las altas y finas tapan menos", "las nubes"),
    "oscuridad": ("Oscuridad", "Lo bajo que está el sol: a más de 18º bajo el horizonte es noche cerrada",
                  "la claridad"),
    "luna": ("Luna", "Cuánto aclara el cielo la luna según su fase y su altura", "la luna"),
    "visibilidad": ("Visibilidad", "Niebla, bruma y probabilidad de precipitación", "la niebla o la precipitación"),
    "hora": ("Hora", "Cercanía a la medianoche magnética (hacia las 23 h solares), cuando suele haber más actividad",
             "la hora"),
}
PENDIENTE_KP = 1.2  # logística de la actividad: 50 % con un Kp por debajo del umbral, 77 % en el umbral
KP_27_DIAS = 2 / 3  # lo que se resta al Kp máximo del día de la previsión a 27 días para tenerlo hora a hora
HORA_PICO = 23  # hora solar local de máxima actividad: la medianoche magnética, en Escandinavia ~1 h antes que la solar
LUNA_MAX = 0.35  # lo que resta una luna llena a más de 30º de altura
ELEVACION_OSCURIDAD = -12  # sol por debajo (crepúsculo náutico): la noche oscura de las tarjetas
KP_LEJOS_DEL_OVALO = 4  # desde este kp_auroras el lugar queda al sur del óvalo: las auroras se ven hacia el norte

# (desde, valoración, color) de la puntuación de una noche
NIVELES_NOCHE = [(8, "Excelente", "#e879f9"), (6, "Buena", "#34d399"), (4, "Regular", "#a3e635"),
                 (2, "Difícil", "#fbbf24"), (0, "Muy difícil", "#94a3b8")]


# ---------------------------------------------------------------- Datos

@st.cache_data(ttl="15m", show_spinner=False)
def get_kp():
    """Kp planetario de los últimos días y previsto para los 3 próximos, por bloques de 3 h.

    Índice: inicio del bloque (UTC). Columnas: kp y tipo ("observado", "estimado" o "previsto").
    """

    filas = descargar(f"{SWPC}/products/noaa-planetary-k-index-forecast.json").json()
    if filas and isinstance(filas[0], list):  # formato antiguo: la primera fila es la cabecera
        filas = [dict(zip(filas[0], fila)) for fila in filas[1:]]
    df = pd.DataFrame(filas)
    tipos = {"observed": "observado", "estimated": "estimado", "predicted": "previsto"}
    return pd.DataFrame({"kp": pd.to_numeric(df["kp"], errors="coerce").to_numpy(),
                         "tipo": df["observed"].map(tipos).fillna("previsto").to_numpy()},
                        index=pd.DatetimeIndex(pd.to_datetime(df["time_tag"], utc=True))).dropna()


@st.cache_data(ttl="1h", show_spinner=False)
def get_prob_tormenta():
    """Probabilidad (%) de que el Kp llegue al menos a 4 (activo o tormenta) en cada uno de los 3 próximos días UTC,
    según la NOAA (Series indexada por fecha)."""

    texto = descargar(f"{SWPC}/text/3-day-geomag-forecast.txt").text
    emitido = pd.to_datetime(re.search(r":Issued: (\d{4} \w{3} \d{2})", texto).group(1), format="%Y %b %d")
    dia = re.search(r"Activity Probabilities (\d{2} \w{3})", texto).group(1)  # "27 Oct", sin año
    inicio = pd.to_datetime(f"{dia} {emitido.year}", format="%d %b %Y")
    if inicio < emitido - pd.Timedelta(days=10):  # el pronóstico de finales de diciembre empieza en enero
        inicio += pd.DateOffset(years=1)
    total = np.zeros(3)
    for nivel in ("Active", "Minor storm", "Moderate storm", "Strong-Extreme storm"):
        if (fila := re.search(rf"^{nivel}\s+(\d+)/(\d+)/(\d+)", texto, re.MULTILINE)) is not None:
            total += [int(v) for v in fila.groups()]
    return pd.Series(np.minimum(total, 100), index=pd.date_range(inicio, periods=3).date)


@st.cache_data(ttl="5m", show_spinner=False)
def get_viento_solar():
    """Último dato del viento solar en L1, desplazado a su llegada a la Tierra: dict(velocidad, densidad, bz, bt, llegada)."""

    filas = descargar(f"{SWPC}/products/geospace/propagated-solar-wind-1-hour.json").json()
    df = pd.DataFrame(filas[1:], columns=filas[0]).dropna(subset=["speed", "bz"])
    ultimo = df.iloc[-1]
    return {"velocidad": float(ultimo["speed"]), "densidad": float(ultimo["density"]), "bz": float(ultimo["bz"]),
            "bt": float(ultimo["bt"]), "llegada": pd.Timestamp(ultimo["propagated_time_tag"])}


@st.cache_data(ttl="10m", show_spinner=False)
def get_ovation():
    """Probabilidad de aurora (%) del modelo OVATION para la próxima hora en el hemisferio norte.

    (momento de la previsión, DataFrame lon (0-359), lat, prob), en una rejilla de 1º.
    """

    datos = descargar(f"{SWPC}/json/ovation_aurora_latest.json").json()
    df = pd.DataFrame(datos["coordinates"], columns=["lon", "lat", "prob"])
    return pd.Timestamp(datos["Forecast Time"]), df[df["lat"] >= 30].reset_index(drop=True)


@st.cache_data(ttl="6h", show_spinner=False)
def get_kp_27_dias():
    """Kp máximo previsto por la NOAA para cada uno de los próximos 27 días UTC (Series indexada por fecha)."""

    kp = {}
    for linea in descargar(f"{SWPC}/text/27-day-outlook.txt").text.splitlines():
        partes = linea.split()  # "2026 Oct 26      88           5          2"
        if len(partes) == 6 and partes[0].isdigit():
            kp[pd.to_datetime(" ".join(partes[:3]), format="%Y %b %d").date()] = int(partes[5])
    return pd.Series(kp, dtype=float)


@st.cache_data(ttl="1h", show_spinner=False)
def get_cielo(lat, lon, tz):
    """Nubes por capas, visibilidad, precipitación, sensación térmica y viento del mejor modelo de Open-Meteo, 8 días.

    Índice: hora local sin zona.
    """

    variables = {"nubes": "cloud_cover", "nubes_bajas": "cloud_cover_low", "nubes_medias": "cloud_cover_mid",
                 "nubes_altas": "cloud_cover_high", "visibilidad": "visibility", "prob_precipitacion":
                 "precipitation_probability", "sensacion": "apparent_temperature", "viento": "wind_speed_10m"}
    params = {"latitude": lat, "longitude": lon, "timezone": tz, "forecast_days": 8,
              "hourly": ",".join(variables.values())}
    horario = descargar("https://api.open-meteo.com/v1/forecast", params=params).json()["hourly"]
    df = pd.DataFrame({nombre: horario.get(v) for nombre, v in variables.items()}, index=pd.to_datetime(horario["time"]))
    return df[~df.index.duplicated()].apply(pd.to_numeric, errors="coerce")  # la hora repetida al atrasar el reloj


@st.cache_data(ttl="1h", show_spinner=False)
def get_nubes_ensemble(lat, lon, tz):
    """Nubosidad (%) de cada miembro de los ensembles ICON-EU (40, unos 5 días) y ECMWF (51), 8 días.

    Índice: hora local con zona; una columna por miembro.
    """

    params = {"latitude": lat, "longitude": lon, "timeformat": "unixtime", "forecast_days": 8,
              "hourly": "cloud_cover", "models": "icon_eu,ecmwf_ifs025"}
    horario = descargar("https://ensemble-api.open-meteo.com/v1/ensemble", params=params, timeout=60).json()["hourly"]
    indice = pd.to_datetime(horario["time"], unit="s", utc=True).tz_convert(tz)
    miembros = {clave: valores for clave, valores in horario.items() if clave.startswith("cloud_cover")}
    return pd.DataFrame(miembros, index=indice).apply(pd.to_numeric, errors="coerce").dropna(how="all")


# ---------------------------------------------------------------- Puntuación

def iluminacion_luna(fecha):
    """(fracción del disco iluminada, fase) de la Luna hacia la medianoche de la noche que empieza el día `fecha`."""

    iluminada, crece = luna.iluminacion(pd.Timestamp(fecha, tz="UTC") + pd.Timedelta(days=1))
    if iluminada < 0.03:
        fase = "nueva"
    elif iluminada > 0.97:
        fase = "llena"
    else:
        fase = "creciente" if crece else "menguante"
    return iluminada, fase


def _logistica(x):
    return 1 / (1 + np.exp(-x))


def horario_noches(ciudad, ahora, kp, kp_27, tormenta, cielo, nubes_ens):
    """Hora a hora, de ahora al final de la última noche: los factores de la puntuación (f_*, ver FACTORES), su
    producto (prob), los datos de los que salen y la noche a la que pertenece cada hora (la fecha de su tarde).

    Cualquiera de las fuentes puede ser None; sin Kp ni nubes no hay probabilidad (NaN).
    """

    primera = (ahora - pd.Timedelta(hours=12)).normalize()
    horas = pd.date_range(ahora.floor("h"), primera + pd.Timedelta(days=NOCHES, hours=12), freq="h", inclusive="left")
    utc = horas.tz_convert("UTC")
    observador = Observer(ciudad.lat, ciudad.lon)
    df = pd.DataFrame(index=horas)
    df["noche"] = (horas - pd.Timedelta(hours=12)).date
    df["sol"] = [sun.elevation(observador, h.to_pydatetime()) for h in horas]
    df["luna"] = [moon.elevation(observador, h.to_pydatetime()) for h in horas]
    df["iluminacion"] = [iluminacion_luna(fecha)[0] for fecha in df["noche"]]

    # Kp: el previsto cada 3 h y, después, el máximo del día de la previsión a 27 días algo rebajado
    df["kp"], df["tipo_kp"] = np.nan, None
    if kp is not None:
        bloque = kp.reindex(utc.floor("3h"))
        df["kp"], df["tipo_kp"] = bloque["kp"].to_numpy(), bloque["tipo"].to_numpy()
    if kp_27 is not None:
        sin_kp = df["kp"].isna().to_numpy()
        diario = kp_27.reindex(utc.date).to_numpy() - KP_27_DIAS
        df.loc[sin_kp, "kp"] = diario[sin_kp]
        df.loc[sin_kp & ~np.isnan(diario), "tipo_kp"] = "27 días"
    df["tormenta"] = tormenta.reindex(utc.date).fillna(0).to_numpy() if tormenta is not None else 0

    if cielo is not None:
        df = df.join(cielo.reindex(horas.tz_localize(None)).set_axis(horas))
    else:
        df = df.assign(**{c: np.nan for c in ["nubes", "nubes_bajas", "nubes_medias", "nubes_altas", "visibilidad",
                                              "prob_precipitacion", "sensacion", "viento"]})
    if nubes_ens is not None:
        abierto = 1 - nubes_ens.reindex(horas) / 100  # parte del cielo despejada en cada miembro
        df["cielo_ens"], df["cielo_dispersion"] = abierto.mean(axis=1), abierto.std(axis=1)
        df["nubes_p10"], df["nubes_p50"], df["nubes_p90"] = (100 * (1 - abierto.quantile(q, axis=1)) for q in (0.9, 0.5, 0.1))
    else:
        df["cielo_ens"] = df["cielo_dispersion"] = df["nubes_p10"] = df["nubes_p50"] = df["nubes_p90"] = np.nan

    # Factores
    actividad = _logistica(PENDIENTE_KP * (df["kp"] - (ciudad.kp_auroras - 1)))
    df["f_actividad"] = 1 - (1 - actividad) * (1 - df["tormenta"] / 100)
    capas = (1 - df["nubes_bajas"] / 100) * (1 - df["nubes_medias"] / 100) * (1 - 0.5 * df["nubes_altas"] / 100)
    df["f_cielo"] = pd.concat([df["cielo_ens"], capas], axis=1).mean(axis=1)
    df["f_oscuridad"] = np.interp(-df["sol"], [4, 12, 18], [0, 0.85, 1])
    altura_luna = np.clip(np.sin(np.radians(df["luna"])) / np.sin(np.radians(30)), 0, 1)
    df["f_luna"] = 1 - LUNA_MAX * df["iluminacion"] * altura_luna
    niebla = pd.Series(np.interp(df["visibilidad"] / 1000, [0.5, 2, 10], [0.2, 0.6, 1]), index=horas)
    precipitacion = 1 - 0.3 * df["prob_precipitacion"] / 100
    df["f_visibilidad"] = (niebla.where(df["visibilidad"].notna(), 1) * precipitacion.fillna(1))
    hora_solar = (utc.hour + utc.minute / 60 + ciudad.lon / 15) % 24
    distancia = np.abs((hora_solar - HORA_PICO + 12) % 24 - 12)
    df["f_hora"] = 0.55 + 0.45 * np.exp(-(distancia / 3.5) ** 2)
    df["prob"] = df[[f"f_{f}" for f in FACTORES]].prod(axis=1, skipna=False)
    return df


def nivel_noche(puntuacion):
    """(valoración, color) de la puntuación de una noche (0-10)."""

    return next((texto, color) for desde, texto, color in NIVELES_NOCHE if puntuacion >= desde)


def puntuar_noches(horario):
    """Puntuación (0-10) de cada noche: la probabilidad media de su mejor ventana de VENTANA horas seguidas.

    Cada noche: dict(fecha, puntuacion, valoracion, color, inicio y fin de la ventana, factores (0-1 en la ventana),
    confianza, limita (el factor que más resta), kp y kp_27 (si es el de la previsión a 27 días), tormenta, nubes,
    luna, sensacion, horas_oscuras).
    """

    noches = []
    for fecha, horas in horario[horario["f_oscuridad"] > 0].groupby("noche"):
        if horas["prob"].isna().all():
            continue
        media = horas["prob"].rolling(VENTANA, min_periods=min(VENTANA, len(horas))).mean()
        if media.isna().all():  # sin ninguna ventana completa con datos
            continue
        fin = media.idxmax()
        ventana = horas.loc[:fin].tail(VENTANA)
        puntuacion = round(10 * media.max(), 1)
        valoracion, color = nivel_noche(puntuacion)

        # Confianza: baja con el Kp a 27 días; media si los miembros del ensemble no se ponen de acuerdo en las nubes
        if (ventana["tipo_kp"] == "27 días").any():
            confianza = "baja"
        elif not (ventana["cielo_dispersion"].mean() < 0.3):
            confianza = "media"
        else:
            confianza = "alta"
        nubes = ventana["nubes_p50"] if ventana["nubes_p50"].notna().any() else ventana["nubes"]
        # El Kp de la noche: el previsto cada 3 h si cubre alguna hora; si no, el máximo del día a 27 días
        previsto = horas.loc[horas["tipo_kp"] != "27 días", "kp"]
        kp_27 = previsto.isna().all()
        factores = {f: ventana[f"f_{f}"].mean() for f in FACTORES}
        noches.append({
            "fecha": fecha, "puntuacion": puntuacion, "valoracion": valoracion, "color": color,
            "inicio": ventana.index[0], "fin": ventana.index[-1] + pd.Timedelta(hours=1),
            "factores": factores, "limita": min(factores, key=factores.get), "confianza": confianza,
            "kp": horas["kp"].max() + KP_27_DIAS if kp_27 else previsto.max(), "kp_27": kp_27,
            "tormenta": horas["tormenta"].max(),
            "nubes": nubes.mean(), "luna": horas["iluminacion"].iloc[0], "sensacion": ventana["sensacion"].min(),
            "horas_oscuras": int((horas["sol"] < ELEVACION_OSCURIDAD).sum()),
        })
    return noches


# ---------------------------------------------------------------- Pestaña

def _noche_oscura(ciudad, ahora):
    """(inicio, fin) de la noche oscura en curso o la siguiente, o None si el sol no baja a ELEVACION_OSCURIDAD."""

    observador, zona = Observer(ciudad.lat, ciudad.lon), pytz.timezone(ciudad.tz)
    tarde = (ahora - pd.Timedelta(hours=12)).date()
    try:
        inicio = sun.dusk(observador, date=tarde, depression=-ELEVACION_OSCURIDAD, tzinfo=zona)
        fin = sun.dawn(observador, date=tarde + pd.Timedelta(days=1), depression=-ELEVACION_OSCURIDAD, tzinfo=zona)
    except ValueError:  # noches claras de verano
        return None
    return inicio, fin


def _tarjetas_ahora(ciudad, ahora, kp, viento, ovation):
    """Kp del bloque actual, probabilidad OVATION en la ciudad, viento solar, noche oscura y luna."""

    lista = []
    if kp is not None and (pasado := kp[kp.index <= ahora.tz_convert("UTC")]).shape[0]:
        actual = pasado.iloc[-1]
        texto, color = valoracion_kp(actual["kp"], ciudad.kp_auroras)
        lista.append({"label": "Kp ahora", "valor": f"{actual['kp']:.1f}", "color": color,
                      "nota": f"{actual['tipo']} · {texto.lower()}",
                      "title": "Índice Kp planetario del bloque de 3 h en curso (0 tranquilo ... 9 tormenta extrema)"})
    if ovation is not None:
        momento, rejilla = ovation
        punto = rejilla[(rejilla["lon"] == round(ciudad.lon) % 360) & (rejilla["lat"] == round(ciudad.lat))]
        if not punto.empty:
            lista.append({"label": "Prob. próxima hora", "valor": f"{punto['prob'].iloc[0]:.0f}", "unidad": "%",
                          "nota": f"OVATION para las {momento.tz_convert(ciudad.tz):%H:%M} h",
                          "title": "Probabilidad de aurora en la vertical de la ciudad según el modelo OVATION de la "
                                   "NOAA, a partir del viento solar medido ahora"})
    if viento is not None:
        bz = viento["bz"]
        if bz <= -5:
            nota = "muy al sur: muy favorable"
        elif bz <= -2:
            nota = "al sur: favorable"
        elif bz >= 2:
            nota = "al norte: desfavorable"
        else:
            nota = "neutro"
        lista.append({"label": "Bz", "valor": f"{bz:+.1f}", "unidad": "nT", "nota": nota,
                      "title": "Componente norte-sur del campo magnético del viento solar: cuanto más negativa (hacia "
                               f"el sur), más auroras. Llega a la Tierra hacia las "
                               f"{viento['llegada'].tz_convert(ciudad.tz):%H:%M} h"})
        velocidad = viento["velocidad"]
        lista.append({"label": "Viento solar", "valor": f"{velocidad:.0f}", "unidad": "km/s",
                      "nota": "muy rápido" if velocidad >= 650 else "rápido" if velocidad >= 500 else "normal",
                      "title": f"Densidad: {viento['densidad']:.1f} protones/cm³. Más rápido y denso, más actividad"})

    oscura = _noche_oscura(ciudad, ahora)
    if oscura is None:
        lista.append({"label": "Noche oscura", "valor": "No hay", "nota": "el sol no baja lo suficiente"})
    else:
        inicio, fin = oscura
        lista.append({"label": "Noche oscura", "valor": f"{inicio:%H:%M}", "nota": f"hasta las {fin:%H:%M}",
                      "title": f"Sol más de {-ELEVACION_OSCURIDAD}º bajo el horizonte"})

    iluminada, fase = iluminacion_luna((ahora - pd.Timedelta(hours=12)).date())
    if oscura is not None:
        observador = Observer(ciudad.lat, ciudad.lon)
        horas = pd.date_range(*oscura, freq="h")
        arriba = sum(moon.elevation(observador, h.to_pydatetime()) > 0 for h in horas)
        if arriba == 0:
            fase += " · no sale"
        elif arriba == len(horas):
            fase += " · toda la noche"
        else:
            fase += f" · {arriba} h de noche"
    lista.append({"label": "Luna", "valor": f"{100 * iluminada:.0f}", "unidad": "%", "nota": fase,
                  "title": "Parte del disco iluminada y horas que está sobre el horizonte en la noche oscura: "
                           "una luna grande y alta apaga las auroras débiles"})
    tarjetas.condiciones(lista)


def render_auroras(ciudad):
    """Pestaña de auroras, con fondo de cielo nocturno: puntuación de las próximas noches y sus factores,
    probabilidad hora a hora, la situación ahora (viento solar, OVATION, oscuridad y luna), el óvalo auroral y el Kp
    máximo previsto a 27 días."""

    ahora = pd.Timestamp.now(tz=ciudad.tz)
    for funcion in (get_kp, get_prob_tormenta, get_viento_solar, get_ovation, get_kp_27_dias):
        en_paralelo(funcion)
    for funcion in (get_cielo, get_nubes_ensemble):
        en_paralelo(funcion, ciudad.lat, ciudad.lon, ciudad.tz)

    kp, kp_27, tormenta = o_none(get_kp), o_none(get_kp_27_dias), o_none(get_prob_tormenta)
    cielo = o_none(get_cielo, ciudad.lat, ciudad.lon, ciudad.tz)
    nubes_ens = o_none(get_nubes_ensemble, ciudad.lat, ciudad.lon, ciudad.tz)
    horario = horario_noches(ciudad, ahora, kp, kp_27, tormenta, cielo, nubes_ens)
    noches = puntuar_noches(horario)

    with st.container(key="auroras"):
        tarjetas.cabecera_auroras(ciudad.nombre, noches[0] if noches else None, ahora, FACTORES)
        if kp is None and kp_27 is None:
            st.warning("No se ha podido descargar la previsión del índice Kp de la NOAA: no hay puntuación.")
        elif cielo is None and nubes_ens is None:
            st.warning("No se ha podido descargar la nubosidad prevista: no hay puntuación.")
        elif not noches:
            st.info("Estos días no hay noche oscura: el sol no baja lo suficiente para ver auroras.",
                    icon=":material/light_mode:")
        else:
            st.subheader("Próximas noches")
            tarjetas.noches_aurora(noches[:NOCHES_DETALLE], ahora, FACTORES)
            if len(noches) > NOCHES_DETALLE:
                tarjetas.noches_aurora(noches[NOCHES_DETALLE:], ahora, FACTORES, compacta=True)
            with st.expander("Cómo se calcula la puntuación", icon=":material/calculate:"):
                st.markdown(
                    f"Cada hora de noche tiene una probabilidad de ver auroras: el producto de seis factores de 0 a 10. "
                    f"La puntuación de la noche es la de su mejor ventana de {VENTANA} h seguidas.\n\n"
                    + "\n".join(f"- **{nombre}**: {texto}." for nombre, texto, _ in FACTORES.values())
                    + f"\n\nEn {ciudad.nombre} suelen verse desde Kp {ciudad.kp_auroras} con el cielo despejado y "
                      "oscuro" + (", bajas sobre el horizonte norte salvo en las tormentas más fuertes"
                                  if ciudad.kp_auroras >= KP_LEJOS_DEL_OVALO else "")
                    + ". Las noches a partir de la cuarta usan la previsión a 27 días de la NOAA, mucho menos "
                      "fiable. Mejor lejos de las luces y mirando al norte.")
            st.plotly_chart(graficos.auroras(horario, kp, kp_27, ciudad.kp_auroras, ahora), theme=None)
        st.divider()

        st.subheader("Ahora")
        viento, ovation = o_none(get_viento_solar), o_none(get_ovation)
        _tarjetas_ahora(ciudad, ahora, kp, viento, ovation)
        if ovation is not None:
            st.plotly_chart(graficos.ovalo_auroral(ovation[1], ciudad.lat, ciudad.lon, ciudad.nombre), theme=None)
            st.caption("Probabilidad de ver auroras en la vertical de cada punto en la próxima hora, según el modelo "
                       "OVATION de la NOAA. Desde un lugar, también se ven las que quedan algo más al norte.")
        else:
            st.caption("No se ha podido descargar la previsión OVATION de la NOAA.")

        if kp_27 is not None and not kp_27.empty:
            st.divider()
            st.plotly_chart(graficos.kp_27_dias(kp_27, ciudad.kp_auroras, ahora.date()), theme=None)
            st.caption("Previsión de la NOAA a partir de la rotación del Sol (27 días): las zonas activas tienden a "
                       "repetirse, pero es muy aproximada. No tiene en cuenta las nubes.")
