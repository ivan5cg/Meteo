// Óvalo auroral (ver ovalo_auroral.py): la probabilidad de aurora de OVATION para la próxima hora sobre un globo de
// MapLibre, con el día y la noche de ese momento. Corre en el navegador: girar el globo, acercarlo o pasar el ratón no
// recarga Streamlit.

const MAPLIBRE = "https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.js";
const RAD = Math.PI / 180;
const LAT_MAX = 85;  // las imágenes se definen en Mercator, que no llega a los polos

const NOMBRE = ["coalesce", ["get", "name:es"], ["get", "name"]];
const TEXTO = {"text-color": "#7c8ba1", "text-halo-color": "#0a1124", "text-halo-width": 1.2};
// Fondo nocturno a juego con la pestaña: tierra, mar, fronteras, nombres de países y capitales y paralelos
const ESTILO = {
  version: 8,
  projection: {type: "globe"},
  glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
  sky: {"atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 1, 5, 1, 7, 0]},
  sources: {base: {type: "vector", url: "https://tiles.openfreemap.org/planet",
                   attribution: '<a href="https://openfreemap.org">OpenFreeMap</a> © OpenMapTiles © OpenStreetMap'}},
  layers: [
    {id: "tierra", type: "background", paint: {"background-color": "#1a2540"}},
    {id: "mar", type: "fill", source: "base", "source-layer": "water", paint: {"fill-color": "#0a1124"}},
    {id: "fronteras", type: "line", source: "base", "source-layer": "boundary",
     filter: ["all", ["==", ["get", "admin_level"], 2], ["!=", ["get", "maritime"], 1]],
     paint: {"line-color": "#334155", "line-width": 0.8}},
    {id: "paises", type: "symbol", source: "base", "source-layer": "place", filter: ["==", ["get", "class"], "country"],
     layout: {"text-field": NOMBRE, "text-font": ["Noto Sans Regular"], "text-size": 11, "text-max-width": 8},
     paint: TEXTO},
    {id: "capitales", type: "symbol", source: "base", "source-layer": "place", minzoom: 3.5,
     filter: ["all", ["==", ["get", "class"], "city"], ["==", ["get", "capital"], 2]],
     layout: {"text-field": NOMBRE, "text-font": ["Noto Sans Regular"], "text-size": 10.5}, paint: TEXTO},
  ],
};

// Probabilidad (%) -> color, como el mapa de Plotly al que sustituye: transparente por debajo del 3-5 %
const ESCALA = [[3, [45, 212, 191, 0]], [5, [45, 212, 191, 0.4]], [15, [52, 211, 153, 0.85]],
                [36, [250, 204, 21, 0.95]], [60, [244, 63, 94, 1]]];
const MARCAS = [5, 15, 30, 45, 60];

function cargarMaplibre() {
  window._cargaMaplibre ??= new Promise((ok, fallo) => {
    if (window.maplibregl) return ok(window.maplibregl);
    const script = Object.assign(document.createElement("script"), {src: MAPLIBRE});
    script.onload = () => ok(window.maplibregl);
    script.onerror = () => { window._cargaMaplibre = null; fallo(new Error("No se ha podido cargar MapLibre")); };
    document.head.appendChild(script);
  });
  return window._cargaMaplibre;
}

function color(p) {
  if (!(p > ESCALA[0][0])) return [0, 0, 0, 0];
  const i = ESCALA.findIndex(([v]) => p <= v);
  if (i < 0) return ESCALA.at(-1)[1];
  const [v0, c0] = ESCALA[i - 1], [v1, c1] = ESCALA[i], t = (p - v0) / (v1 - v0);
  return c0.map((c, k) => c + (c1[k] - c) * t);
}

// Probabilidad en (lat, lon) entre las celdas de 1º (bilineal; la longitud da la vuelta), o NaN fuera de la rejilla
function interpolar(d, lat, lon) {
  const y = lat - d.lat0, x = ((lon % 360) + 360) % 360, filas = d.valores.length / 360;
  if (y < 0 || y > filas - 1) return NaN;
  const i = Math.floor(x), j = Math.min(Math.floor(y), filas - 2), fx = x - i, fy = y - j;
  const v = (jj, ii) => d.valores[jj * 360 + ii % 360] ?? NaN;
  return (v(j, i) * (1 - fx) + v(j, i + 1) * fx) * (1 - fy) + (v(j + 1, i) * (1 - fx) + v(j + 1, i + 1) * fx) * fy;
}

// La rejilla con cada celda promediada con sus vecinas (1-2-1 en cada sentido, dos pasadas; la longitud da la vuelta).
// OVATION da porcentajes enteros y, sin suavizar, el borde del óvalo sale escalonado. Solo para la imagen: los valores
// que se leen son los de la celda
function suavizar(d, pasadas = 2) {
  const filas = d.valores.length / 360;
  let valores = Float32Array.from(d.valores, v => v ?? 0);
  for (let k = 0; k < pasadas; k++) {
    for (const [dj, di] of [[0, 1], [1, 0]]) {
      const antes = valores, v = (j, i) => antes[Math.min(filas - 1, Math.max(0, j)) * 360 + (i + 360) % 360];
      valores = new Float32Array(antes.length);
      for (let j = 0; j < filas; j++) for (let i = 0; i < 360; i++) {
        valores[j * 360 + i] = (v(j - dj, i - di) + 2 * v(j, i) + v(j + dj, i + di)) / 4;
      }
    }
  }
  return {...d, valores};
}

// La de la celda de 1º más cercana: lo que dice OVATION para ese punto (igual que la tarjeta de «Ahora»)
function celda(d, lat, lon) {
  const j = Math.round(lat) - d.lat0, i = ((Math.round(lon) % 360) + 360) % 360;
  return j < 0 || j >= d.valores.length / 360 ? null : d.valores[j * 360 + i];
}

const mercator = (lat) => Math.log(Math.tan(Math.PI / 4 + lat * RAD / 2));

// Imagen de todas las longitudes entre `sur` y `norte`, con las filas repartidas en Mercator (como las coloca MapLibre)
function imagen(ancho, sur, norte, pintar) {
  const arriba = mercator(norte), abajo = mercator(sur), alto = Math.round(ancho * (arriba - abajo) / (2 * Math.PI));
  const lienzo = Object.assign(document.createElement("canvas"), {width: ancho, height: alto});
  const contexto = lienzo.getContext("2d"), pixeles = contexto.createImageData(ancho, alto), p = pixeles.data;
  for (let f = 0; f < alto; f++) {
    const lat = (2 * Math.atan(Math.exp(arriba - (f + 0.5) / alto * (arriba - abajo))) - Math.PI / 2) / RAD;
    for (let c = 0; c < ancho; c++) {
      const [r, g, b, a] = pintar(lat, -180 + (c + 0.5) / ancho * 360), o = (f * ancho + c) * 4;
      p[o] = r;
      p[o + 1] = g;
      p[o + 2] = b;
      p[o + 3] = a * 255;
    }
  }
  contexto.putImageData(pixeles, 0, 0);
  return {url: lienzo.toDataURL(), coordinates: [[-180, norte], [180, norte], [180, sur], [-180, sur]]};
}

// Lado de día un poco más claro, con el crepúsculo (hasta el Sol 12º bajo el horizonte) en degradado. Posición del Sol
// con las fórmulas aproximadas del Almanaque Náutico
function dia(t) {
  const d = (t - 946728000000) / 864e5;  // días desde J2000.0
  const g = (357.529 + 0.98560028 * d) * RAD;
  const l = (280.459 + 0.98564736 * d + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) * RAD;
  const e = (23.439 - 0.00000036 * d) * RAD;
  const declinacion = Math.asin(Math.sin(e) * Math.sin(l));
  const ascension = Math.atan2(Math.cos(e) * Math.sin(l), Math.cos(l));
  const sidereo = (18.697374558 + 24.06570982441908 * d) * 15 * RAD - ascension;
  return imagen(360, -LAT_MAX, LAT_MAX, (lat, lon) => {
    const altura = Math.asin(Math.sin(lat * RAD) * Math.sin(declinacion)
                             + Math.cos(lat * RAD) * Math.cos(declinacion) * Math.cos(sidereo + lon * RAD)) / RAD;
    return [148, 186, 255, 0.17 * Math.min(1, Math.max(0, (altura + 12) / 12))];
  });
}

// Paralelos de 50º a 80º N, con muchos vértices para que se curven sobre el globo
function paralelos() {
  const features = [50, 60, 70, 80].map(lat => ({
    type: "Feature", properties: {etiqueta: `${lat}° N`},
    geometry: {type: "LineString", coordinates: Array.from({length: 181}, (_, k) => [-180 + 2 * k, lat])},
  }));
  return {type: "FeatureCollection", features};
}

const porcentaje = (v) => v === null || Number.isNaN(v) ? "sin dato" : `${Math.round(v)} %`;

function textos(o) {
  const {d, raiz} = o;
  const hora = new Intl.DateTimeFormat("es-ES", {timeZone: d.tz, hour: "2-digit", minute: "2-digit", hourCycle: "h23"})
    .format(d.momento);
  raiz.querySelector(".oa-fuente").textContent = `OVATION (NOAA) · para las ${hora} h`;
  raiz.querySelector(".oa-barra").style.background = `linear-gradient(90deg, ${ESCALA.slice(1).map(([v, c]) =>
    `rgba(${c.slice(0, 3)}, ${Math.max(c[3], 0.6)}) ${(100 * (v - 5) / 55).toFixed(1)}%`)})`;
  raiz.querySelector(".oa-marcas").innerHTML = MARCAS.map(m =>
    `<span style="left:${(100 * (m - 5) / 55).toFixed(1)}%">${m}</span>`).join("");
  o.lugar?.getElement().querySelector("b").replaceChildren(porcentaje(d.lugar.valor));
}

function capas(o) {
  const {mapa, d} = o, suave = suavizar(d);
  const aurora = imagen(1440, d.lat0, LAT_MAX, (lat, lon) => color(interpolar(suave, lat, lon)));
  if (mapa.getSource("dia")) {
    mapa.getSource("dia").updateImage(dia(d.momento));
    mapa.getSource("aurora").updateImage(aurora);
    return;
  }
  mapa.addSource("dia", {type: "image", ...dia(d.momento)});
  mapa.addLayer({id: "dia", type: "raster", source: "dia", paint: {"raster-fade-duration": 0}}, "fronteras");
  mapa.addSource("aurora", {type: "image", ...aurora});
  mapa.addLayer({id: "aurora", type: "raster", source: "aurora",
                 paint: {"raster-fade-duration": 0, "raster-resampling": "linear"}}, "fronteras");
  mapa.addSource("paralelos", {type: "geojson", data: paralelos()});
  mapa.addLayer({id: "paralelos", type: "line", source: "paralelos",
                 paint: {"line-color": "rgba(148, 163, 184, 0.3)", "line-width": 0.8, "line-dasharray": [3, 3]}},
                "paises");
  mapa.addLayer({id: "paralelos-etiquetas", type: "symbol", source: "paralelos",
                 layout: {"symbol-placement": "line", "symbol-spacing": 400, "text-field": ["get", "etiqueta"],
                          "text-font": ["Noto Sans Regular"], "text-size": 10},
                 paint: {"text-color": "#64748b", "text-halo-color": "#0a1124", "text-halo-width": 1}},
                "paises");
}

async function crearMapa(o) {
  const aviso = o.raiz.querySelector(".oa-aviso");
  o.mapa = null;  // creándose
  let maplibregl;
  try {
    maplibregl = await cargarMaplibre();
  } catch {
    aviso.textContent = "No se ha podido cargar el globo. Prueba a recargar la página.";
    return;
  }
  const {d} = o, contenedor = o.raiz.querySelector(".oa-mapa");
  // El encuadre que deja ver el óvalo entero, sea cual sea el tamaño del mapa (zoom 0,9 con unos 440 px)
  const zoom = 0.9 + Math.log2(Math.min(contenedor.clientWidth, contenedor.clientHeight) / 440);
  const mapa = o.mapa = new maplibregl.Map({
    container: contenedor, style: ESTILO,
    center: [d.lugar.lon, Math.min(d.lugar.lat + 8, LAT_MAX)], zoom, minZoom: 0, maxZoom: 6,
    keyboard: false, dragRotate: false, pitchWithRotate: false, touchPitch: false, cooperativeGestures: true,
    attributionControl: {compact: true},
    locale: {
      "NavigationControl.ZoomIn": "Acercar",
      "NavigationControl.ZoomOut": "Alejar",
      "FullscreenControl.Enter": "Pantalla completa",
      "FullscreenControl.Exit": "Salir de la pantalla completa",
      "AttributionControl.ToggleAttribution": "Créditos",
      "CooperativeGesturesHandler.WindowsHelpText": "Usa Ctrl + rueda del ratón para acercar o alejar el globo",
      "CooperativeGesturesHandler.MacHelpText": "Usa ⌘ + rueda del ratón para acercar o alejar el globo",
      "CooperativeGesturesHandler.MobileHelpText": "Usa dos dedos para girar el globo",
    },
  });
  mapa.touchZoomRotate.disableRotation();
  mapa.addControl(new maplibregl.NavigationControl({showCompass: false}), "top-right");
  mapa.addControl(new maplibregl.FullscreenControl({container: o.raiz}), "top-right");
  mapa.on("style.load", () => {
    capas(o);
    aviso.style.display = "none";
  });
  mapa.once("load", () => mapa.getContainer().querySelector(".maplibregl-ctrl-attrib")
    ?.classList.remove("maplibregl-compact-show"));
  // Si no llegan las teselas de OpenFreeMap: el fondo oscuro raster de CARTO, sin nombres
  mapa.on("error", (e) => {
    if (e.sourceId !== "base" || o.respaldo) return;
    o.respaldo = true;
    for (const id of ["mar", "fronteras", "paises", "capitales"]) mapa.removeLayer(id);
    mapa.removeSource("base");
    mapa.addSource("carto", {type: "raster", tileSize: 256, attribution: "© OpenStreetMap © CARTO",
                             tiles: ["a", "b", "c"].map(s =>
                               `https://${s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png`)});
    mapa.addLayer({id: "carto", type: "raster", source: "carto"}, "dia");
  });
  document.addEventListener("fullscreenchange", () => {
    const completa = document.fullscreenElement === o.raiz;
    o.raiz.classList.toggle("completa", completa);
    mapa.cooperativeGestures?.[completa ? "disable" : "enable"]();
  });

  // El lugar, con la probabilidad de su celda, y la de cualquier punto bajo el ratón
  const lugar = Object.assign(document.createElement("div"), {className: "oa-lugar"});
  lugar.innerHTML = `<i></i><span>${d.lugar.nombre}</span><b></b>`;
  o.lugar = new maplibregl.Marker({element: lugar, anchor: "left", offset: [-6, 0]})
    .setLngLat([d.lugar.lon, d.lugar.lat]).addTo(mapa);
  textos(o);
  const globo = o.raiz.querySelector(".oa-globo");
  mapa.on("mousemove", (e) => {
    const valor = celda(o.d, e.lngLat.lat, e.lngLat.lng);
    globo.style.display = valor === null ? "none" : "block";
    if (valor === null) return;
    globo.textContent = porcentaje(valor);
    globo.style.transform = `translate(${e.point.x + 14}px, ${e.point.y - 34}px)`;
  });
  mapa.getCanvasContainer().addEventListener("mouseleave", () => { globo.style.display = "none"; });
}

export default function (component) {
  const {data, parentElement} = component;
  const raiz = parentElement.querySelector(".ovalo-auroral");
  const o = raiz._ovalo ??= {raiz};
  if (o.momento === data.momento) return;  // la misma previsión: Streamlit ha recargado la página por otra cosa
  o.momento = data.momento;
  o.d = data;
  textos(o);
  if (o.mapa === undefined) crearMapa(o);
  else if (o.mapa?.getSource("aurora")) capas(o);
}
