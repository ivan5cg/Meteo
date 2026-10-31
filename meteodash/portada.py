"""Portada: hoy y mañana en todos los lugares de un vistazo, con un enlace a la página de cada uno.

Usa las mismas fuentes (y la misma caché) que las páginas: al abrir una después, ya está casi todo descargado.
"""

from html import escape
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

from .avisos import NIVELES, TIPOS, avisos_vigentes, get_avisos
from .fuentes import (UMBRAL_LLUVIA, en_paralelo, extremos_diarios, get_ensemble, get_open_meteo_detalle, o_none,
                      prob_diaria)
from .actualizar import antiguedad, linea_datos
from .lugares import SECCIONES
from .observaciones import descargar_en, temperatura_reciente
from .tarjetas import tiempo_wmo, tono_temperatura


def _descargar_todo(lugares):
    """Lanza en paralelo todas las descargas de la portada; luego se leen de la caché."""

    for ciudad in lugares:
        en_paralelo(get_ensemble, ciudad.lat, ciudad.lon, ciudad.tz, "icon_eu")
        en_paralelo(get_open_meteo_detalle, ciudad.lat, ciudad.lon, ciudad.tz)
        for estacion in ciudad.observaciones:
            en_paralelo(*descargar_en(estacion))
    for pais in {c.pais for c in lugares if c.con_avisos}:
        en_paralelo(get_avisos, pais)


def resumen_lugar(ciudad, ahora):
    """Temperatura observada (valor, momento) o None; hoy y mañana según el ensemble ICON-EU, como en el medio plazo de
    cada página (dict(tmax, tmin, prob, codigo), o falta el día); y los avisos oficiales que tocan hoy o mañana."""

    hoy, mañana = ahora.date(), (ahora + pd.Timedelta(days=1)).date()
    dias = {}
    ensemble = o_none(get_ensemble, ciudad.lat, ciudad.lon, ciudad.tz, "icon_eu")
    if ensemble is not None:
        detalle = o_none(get_open_meteo_detalle, ciudad.lat, ciudad.lon, ciudad.tz)
        codigos = detalle["diario"]["codigo"] if detalle is not None else pd.Series(dtype=float)
        maximas, minimas = extremos_diarios(ensemble["temperatura"], [hoy, mañana], minimo_horas=20)
        prob = prob_diaria(ensemble["precipitacion"], ahora.floor("h"))  # de hoy, solo lo que queda
        for clave, fecha in [("hoy", hoy), ("mañana", mañana)]:
            if fecha in maximas.index:
                dias[clave] = {"tmax": maximas.loc[fecha].median(), "tmin": minimas.loc[fecha].median(),
                               "prob": prob.get(fecha), "codigo": codigos.get(pd.Timestamp(fecha))}

    avisos = []
    if ciudad.con_avisos:
        punto = (ciudad.lat, ciudad.lon) if ciudad.avisos_por_poligono else None
        fin_de_mañana = ahora.normalize() + pd.Timedelta(days=2)
        avisos = [a for a in o_none(avisos_vigentes, ciudad.pais, ciudad.zonas_aviso, ahora, punto) or []
                  if a["inicio"] < fin_de_mañana]
    descargado = ensemble["temperatura"].attrs.get("descargado") if ensemble is not None else None
    return {"actual": o_none(temperatura_reciente, ciudad.observaciones, ciudad.tz), "dias": dias, "avisos": avisos,
            "descargado": descargado}


def _celda_dia(dia):
    if dia is None or pd.isna(dia["tmax"]) or pd.isna(dia["tmin"]):
        return '<div class="pl-dia vacio">–</div>'
    emoji, texto = tiempo_wmo(dia["codigo"])
    p = dia["prob"]
    lluvia = (f'<span class="pl-lluvia">{p:.0f} %</span>' if p is not None and not pd.isna(p) and p >= 10
              else '<span class="pl-lluvia vacia">–</span>')
    return (f'<div class="pl-dia" title="{texto}"><span class="pl-icono">{emoji}</span>'
            f'<span class="pl-temps"><b>{dia["tmax"]:.0f}º</b> <span>{dia["tmin"]:.0f}º</span></span>{lluvia}</div>')


def _celda_ahora(actual, ciudad):
    if actual is None:
        motivo = "sin estación cercana y representativa" if not ciudad.observaciones else "sin observación reciente"
        return f'<div class="pl-ahora vacio" title="{motivo}">–</div>'
    valor, momento = actual
    return (f'<div class="pl-ahora" style="--hue: {tono_temperatura(valor)}" title="Observada a las {momento:%H:%M} '
            f'(hora local)">{valor:.0f}º<small>{momento:%H:%M}</small></div>')


def _aviso(avisos, ahora):
    """Insignia con el fenómeno del aviso de más nivel y, en el título, todos."""

    if not avisos:
        return ""
    peor = max(avisos, key=lambda a: a["nivel"])
    lineas = []
    for a in avisos:
        nivel = NIVELES[a["nivel"]][0]
        fenomeno, _ = TIPOS.get(a["tipo"], ("fenómenos adversos", "⚠️"))
        cuando = "ahora" if a["inicio"] <= ahora else "hoy" if a["inicio"].tz_convert(ahora.tz).date() == ahora.date() \
            else "mañana"
        lineas.append(f"Aviso {nivel} por {fenomeno} ({cuando})")
    _, emoji = TIPOS.get(peor["tipo"], ("", "⚠️"))
    return (f'<span class="pl-aviso" style="--aviso: {NIVELES[peor["nivel"]][1]}" '
            f'title="{escape("; ".join(lineas))}">{emoji}</span>')


def _fila(ciudad, pagina, grupo, resumen, ahora):
    """Fila de un lugar: un enlace a su página (en una página de grupo, con ?lugar= para abrir su pestaña), que al
    pulsarlo sin teclas se abre dentro de la app (ver TABLA)."""

    ruta = Path(pagina).stem  # la URL de la página en st.navigation
    lugar = escape(ciudad.nombre) if grupo else ""
    href = f"{ruta}?lugar={quote(ciudad.nombre)}" if grupo else ruta
    grupo = f"<small>{escape(grupo)}</small>" if grupo else ""
    return (f'<a class="pl-fila" href="{href}" target="_self" data-pagina="{pagina}" data-lugar="{lugar}">'
            f'<div class="pl-nombre">{escape(ciudad.nombre)}{_aviso(resumen["avisos"], ahora)}{grupo}</div>'
            f'{_celda_ahora(resumen["actual"], ciudad)}'
            f'{_celda_dia(resumen["dias"].get("hoy"))}{_celda_dia(resumen["dias"].get("mañana"))}</a>')


# Las filas de una sección: un componente que devuelve a Python la fila pulsada, para cambiar de página con
# st.switch_page sin recargar la app (un enlace normal la recargaría entera). Con Ctrl, Mayús o el botón central, el
# enlace se abre como siempre (en otra pestaña). La insignia de avisos, en pantallas táctiles, muestra su burbuja (ver
# estilo.TOQUES, que la atiende antes)
JS_TABLA = """
export default function(component) {
  const { data, parentElement, setTriggerValue } = component;
  const tabla = parentElement.querySelector(".portada");
  tabla.innerHTML = data.html;
  if (tabla._escucha) return;
  tabla._escucha = true;
  tabla.addEventListener("click", (e) => {
    const fila = e.target.closest("a.pl-fila");
    if (!fila || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    setTriggerValue("abrir", {pagina: fila.dataset.pagina, lugar: fila.dataset.lugar});
  });
}
"""
TABLA = st.components.v2.component("portada", html='<div class="rejilla"><div class="portada"></div></div>',
                                   js=JS_TABLA, isolate_styles=False)


def _seccion(filas, clave):
    """Muestra las filas y, si se acaba de pulsar una, abre su página (y en ella, su pestaña)."""

    pulsada = TABLA(data={"html": filas}, key=clave, on_abrir_change=lambda: None).abrir
    if pulsada:
        st.switch_page(pulsada["pagina"], query_params={"lugar": pulsada["lugar"]} if pulsada["lugar"] else None)


GRUPOS = {"paginas/pirineos.py": "Pirineos", "paginas/eslovenia.py": "Eslovenia", "paginas/belgica.py": "Bélgica",
          "paginas/escocia.py": "Escocia"}


def render_portada():
    st.header("Meteo Dash")
    st.caption("Hoy y mañana en todos los lugares. Pulsa en uno para ver su previsión completa.")
    hueco_datos = st.empty()  # la antigüedad de los datos, que se sabe al final

    ahora = pd.Timestamp.now(tz="Europe/Madrid")
    lugares = [c for paginas in SECCIONES.values() for _, ciudades in paginas for c in ciudades]
    _descargar_todo(lugares)

    cabecera = ('<div class="pl-fila pl-cabecera"><div>Lugar</div><div>Ahora</div><div>Hoy</div>'
                '<div>Mañana</div></div>')
    descargas = []
    with st.spinner("Descargando la previsión de todos los lugares…", show_time=True):
        for seccion, paginas in SECCIONES.items():
            filas = ""
            for pagina, ciudades in paginas:
                for ciudad in ciudades:
                    local = ahora.tz_convert(ciudad.tz)
                    resumen = resumen_lugar(ciudad, local)
                    descargas.append(resumen["descargado"])
                    filas += _fila(ciudad, pagina, GRUPOS.get(pagina), resumen, local)
            st.subheader(seccion)
            _seccion(cabecera + filas, f"portada_{seccion}")

    hace = antiguedad(min((d for d in descargas if d is not None), default=None))
    with hueco_datos.container():
        linea_datos(f"Previsión descargada {hace}" if hace else "Previsión del ensemble ICON-EU", "portada")

    st.caption("**Ahora**: última observación oficial de la estación de cada página (– si no hay una cercana y "
               "representativa). **Hoy y mañana**: mediana de las máximas y mínimas y probabilidad de al menos "
               f"{UMBRAL_LLUVIA} L/m² (de hoy, lo que queda) según los 40 miembros del ensemble ICON-EU, como en el "
               "medio plazo de cada página; el icono, el tiempo previsto por Open-Meteo. **Avisos**: los oficiales "
               "de hoy y mañana (Meteoalarm).")
    st.page_link("paginas/punto.py", label="Ver otro punto de Europa", icon=":material/add_location_alt:")
