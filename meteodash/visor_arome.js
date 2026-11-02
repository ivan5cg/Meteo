// Visor de los mapas AROME (ver mapas_arome.py), con MapLibre. Todo corre en el navegador: el campo se interpola y se
// colorea aquí, las isolíneas salen de un marching squares y la línea de tiempo es a la vez la serie del punto elegido.
// Cambiar de hora o de punto, o reproducir, no recarga Streamlit; al cambiar de variable llegan datos nuevos y se
// conservan el encuadre, la hora y el punto.

const MAPLIBRE = "https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.js";
const ESTILO = "https://tiles.openfreemap.org/styles/positron";
// Si OpenFreeMap falla: teselas raster de CARTO. No trae tipografías, así que las isolíneas van sin etiquetas
const ESTILO_RESPALDO = {
  version: 8,
  sources: {base: {type: "raster", tileSize: 256, maxzoom: 19, attribution: "© OpenStreetMap © CARTO",
                   tiles: ["a", "b", "c"].map(s => `https://${s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png`)}},
  layers: [{id: "base", type: "raster", source: "base"}],
};
const RELIEVE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png";
const PASO_MS = 700, PAUSA_FINAL_MS = 1600;
const RAD = Math.PI / 180;

// Temperatura y rachas: la escala se estira al rango de la pasada (igual para todas las horas). Lluvia: escala fija y
// transparente donde no llueve
const PALETAS = {
  temperatura: ["#313695", "#4575b4", "#74add1", "#abd9e9", "#e0f3f8", "#ffffbf", "#fee090", "#fdae61", "#f46d43",
                "#d73027", "#a50026"],
  rachas: ["#ffffcc", "#ffeda0", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#bd0026", "#800026"],
};
const LLUVIA = [[0.1, "#bfe6f7"], [0.3, "#7fcbed"], [0.6, "#3ba7e0"], [1, "#1f78c8"], [2, "#2547a8"], [4, "#6a2ea8"],
                [8, "#a8259a"], [15, "#e0337a"]];
const NIVELES_LLUVIA = [0.2, 0.5, 1, 2, 5, 10, 20];

const ICONO_PLAY = '<svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M8 5.5v13l10.5-6.5z"/></svg>';
const ICONO_PAUSA = '<svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M7 5h3.6v14H7zm6.4 0H17v14h-3.6z"/></svg>';

const numero = (v, decimales) => v.toLocaleString("es-ES", {minimumFractionDigits: decimales,
                                                             maximumFractionDigits: decimales});
// Primer múltiplo "redondo" de `base` (×1, 2, 5, 10...) con el que `rango` se divide en `maximo` tramos o menos
const pasoRedondo = (base, rango, maximo) =>
  [1, 2, 5, 10, 20, 50, 100, 200].map(m => m * base).find(paso => rango / paso <= maximo) ?? base * 500;

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

// ---------------------------------------------------------------- Rejilla

// Catmull-Rom: cúbica que pasa por los nodos, así que el campo sale suave pero respeta los valores de la rejilla
function cubica(p0, p1, p2, p3, t) {
  return p1 + 0.5 * t * (p2 - p0 + t * (2 * p0 - 5 * p1 + 4 * p2 - p3 + t * (3 * (p1 - p2) + p3 - p0)));
}

// Valor en (x, y), en índices de la rejilla g (nx × ny, fila 0 al sur)
function interpolar(g, nx, ny, x, y) {
  const fila = (j) => {
    const base = Math.min(ny - 1, Math.max(0, j)) * nx, i = Math.min(nx - 2, Math.floor(x));
    const p = (k) => g[base + Math.min(nx - 1, Math.max(0, k))];
    return cubica(p(i - 1), p(i), p(i + 1), p(i + 2), x - i);
  };
  const j = Math.min(ny - 2, Math.floor(y));
  return cubica(fila(j - 1), fila(j), fila(j + 1), fila(j + 2), y - j);
}

// La rejilla con k muestras por intervalo entre nodos
function remuestrear(g, nx, ny, k) {
  const W = (nx - 1) * k + 1, H = (ny - 1) * k + 1, v = new Float32Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) v[y * W + x] = interpolar(g, nx, ny, x / k, y / k);
  return {W, H, v};
}

// Puntos sin dato (Meteociel no respondió o dio una celda vacía): la media de sus vecinos, hasta cubrirlos todos
function rellenar(g, nx, ny) {
  for (let vuelta = 0; vuelta < nx + ny && g.some(Number.isNaN); vuelta++) {
    const antes = g.slice();
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      if (!Number.isNaN(antes[j * nx + i])) continue;
      let suma = 0, n = 0;
      for (let jj = Math.max(0, j - 1); jj <= Math.min(ny - 1, j + 1); jj++)
        for (let ii = Math.max(0, i - 1); ii <= Math.min(nx - 1, i + 1); ii++)
          if (!Number.isNaN(antes[jj * nx + ii])) { suma += antes[jj * nx + ii]; n++; }
      if (n) g[j * nx + i] = suma / n;
    }
  }
  return g;
}

// Isolíneas de nivel `nivel` del campo f (W × H) por marching squares: listas de puntos [x, y] en índices de f
function isolineas(f, W, H, nivel) {
  const puntos = new Map(), vecinos = new Map();
  const cruce = (id, x0, y0, v0, x1, y1, v1) => {
    if (!puntos.has(id)) {
      const t = (nivel - v0) / (v1 - v0);
      puntos.set(id, [x0 + t * (x1 - x0), y0 + t * (y1 - y0)]);
    }
    return id;
  };
  const une = (a, b) => {
    for (const [p, q] of [[a, b], [b, a]]) {
      if (!vecinos.has(p)) vecinos.set(p, []);
      vecinos.get(p).push(q);
    }
  };
  for (let y = 0; y < H - 1; y++) for (let x = 0; x < W - 1; x++) {
    const a = f[y * W + x], b = f[y * W + x + 1], c = f[(y + 1) * W + x + 1], d = f[(y + 1) * W + x];
    const caso = (a >= nivel) | (b >= nivel) << 1 | (c >= nivel) << 2 | (d >= nivel) << 3;
    if (caso === 0 || caso === 15) continue;
    // Aristas de la celda (cada una con un identificador único en la rejilla): abajo, derecha, arriba e izquierda
    const ab = () => cruce(y * W + x, x, y, a, x + 1, y, b);
    const bc = () => cruce(W * H + y * W + x + 1, x + 1, y, b, x + 1, y + 1, c);
    const dc = () => cruce((y + 1) * W + x, x, y + 1, d, x + 1, y + 1, c);
    const ad = () => cruce(W * H + y * W + x, x, y, a, x, y + 1, d);
    const centro = (a + b + c + d) / 4 >= nivel;  // desempata las sillas
    switch (caso) {
      case 1: case 14: une(ad(), ab()); break;
      case 2: case 13: une(ab(), bc()); break;
      case 3: case 12: une(ad(), bc()); break;
      case 4: case 11: une(bc(), dc()); break;
      case 6: case 9: une(ab(), dc()); break;
      case 7: case 8: une(dc(), ad()); break;
      case 5: if (centro) { une(ab(), bc()); une(dc(), ad()); } else { une(ad(), ab()); une(bc(), dc()); } break;
      case 10: if (centro) { une(ad(), ab()); une(bc(), dc()); } else { une(ab(), bc()); une(dc(), ad()); } break;
    }
  }
  // Se encadenan los segmentos: primero las líneas que acaban en el borde (un extremo con un solo vecino), luego los
  // anillos cerrados
  const usados = new Set(), lineas = [];
  const recorrer = (inicio) => {
    const linea = [puntos.get(inicio)];
    usados.add(inicio);
    for (let actual = inicio; ;) {
      const siguiente = vecinos.get(actual).find(id => !usados.has(id));
      if (siguiente === undefined) {
        if (linea.length > 2 && vecinos.get(actual).includes(inicio)) linea.push(puntos.get(inicio));
        return linea;
      }
      usados.add(siguiente);
      linea.push(puntos.get(siguiente));
      actual = siguiente;
    }
  };
  for (const [id, v] of vecinos) if (v.length === 1 && !usados.has(id)) lineas.push(recorrer(id));
  for (const id of vecinos.keys()) if (!usados.has(id)) lineas.push(recorrer(id));
  return lineas.filter(linea => linea.length > 1);
}

function hexRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [n >> 16, (n >> 8) & 255, n & 255];
}

// Escala de colores: `paradas` [[valor, color]] crecientes, equiespaciadas en la barra de la leyenda; `umbral`
// [transparente, opaco] para la lluvia
function escala(paradas, niveles, marcas, umbral = null) {
  const valores = paradas.map(p => p[0]), colores = paradas.map(p => hexRgb(p[1])), n = paradas.length;
  const posicion = (v) => {
    if (!(v > valores[0])) return 0;
    if (v >= valores[n - 1]) return 1;
    let i = 0;
    while (v > valores[i + 1]) i++;
    return (i + (v - valores[i]) / (valores[i + 1] - valores[i])) / (n - 1);
  };
  const tabla = new Uint8ClampedArray(256 * 3);
  for (let k = 0; k < 256; k++) {
    const s = k / 255 * (n - 1), i = Math.min(n - 2, Math.floor(s)), t = s - i;
    for (let c = 0; c < 3; c++) tabla[k * 3 + c] = colores[i][c] + (colores[i + 1][c] - colores[i][c]) * t;
  }
  const alfa = (v) => Number.isNaN(v) ? 0 : !umbral || v >= umbral[1] ? 255
    : v <= umbral[0] ? 0 : 255 * (v - umbral[0]) / (umbral[1] - umbral[0]);
  const gradiente = `linear-gradient(90deg, ${paradas.map((p, i) => `${p[1]} ${(100 * i / (n - 1)).toFixed(1)}%`)})`;
  return {posicion, tabla, alfa, gradiente, niveles, marcas};
}

function crearEscala(d, rejillas) {
  if (d.paleta === "precipitacion") {
    return escala(LLUVIA, NIVELES_LLUVIA, LLUVIA.map(p => p[0]), [0.05, LLUVIA[0][0]]);
  }
  const valores = rejillas.flatMap(g => Array.from(g)).filter(Number.isFinite).sort((a, b) => a - b);
  if (!valores.length) valores.push(0, d.paso);
  const cuantil = (q) => valores[Math.min(valores.length - 1, Math.floor(q * valores.length))];
  const minimo = valores[0], maximo = valores.at(-1);
  // Colores entre los percentiles 2 y 98 de toda la pasada: un valor extremo no aplana el resto
  const bajo = Math.floor(cuantil(0.02) / d.paso) * d.paso;
  const alto = Math.max(Math.ceil(cuantil(0.98) / d.paso) * d.paso, bajo + d.paso);
  const colores = PALETAS[d.paleta];
  const paradas = colores.map((c, i) => [bajo + (alto - bajo) * i / (colores.length - 1), c]);
  // Isolíneas cada `paso` (o más separadas si saldrían demasiadas) en todo el rango; marcas de la leyenda, unas 5
  const equidistancia = pasoRedondo(d.paso, maximo - minimo, 30);
  const niveles = [];
  for (let v = Math.floor(minimo / equidistancia) * equidistancia; v <= maximo; v += equidistancia) {
    niveles.push(+v.toFixed(3));
  }
  const cada = pasoRedondo(d.paso, alto - bajo, 5), marcas = [];
  for (let v = Math.ceil(bajo / cada) * cada; v <= alto + 1e-9; v += cada) marcas.push(+v.toFixed(3));
  return escala(paradas, niveles, marcas);
}

// ---------------------------------------------------------------- Datos de una variable

function preparar(d) {
  const nx = d.lons.length, ny = d.lats.length;
  const rejillas = d.valores.map(fila => rellenar(Float32Array.from(fila, v => v ?? NaN), nx, ny));
  const dlon = (d.lons[nx - 1] - d.lons[0]) / (nx - 1), dlat = (d.lats[ny - 1] - d.lats[0]) / (ny - 1);
  const kImagen = Math.max(2, Math.ceil(360 / Math.max(nx - 1, ny - 1)));
  // La imagen cubre medio píxel más allá de los nodos del borde: los centros de sus píxeles caen sobre los nodos
  const mx = dlon / kImagen / 2, my = dlat / kImagen / 2;
  const [oeste, este, sur, norte] = [d.lons[0] - mx, d.lons[nx - 1] + mx, d.lats[0] - my, d.lats[ny - 1] + my];
  const temperatura = d.paleta === "temperatura";
  return {
    ...d, nx, ny, rejillas, kImagen, fotogramas: [],
    escala: crearEscala(d, rejillas),
    lon: (x) => d.lons[0] + x * dlon,
    lat: (y) => d.lats[0] + y * dlat,
    x: (lon) => (lon - d.lons[0]) / dlon,
    y: (lat) => (lat - d.lats[0]) / dlat,
    esquinas: [[oeste, norte], [este, norte], [este, sur], [oeste, sur]],
    caja: [[d.lons[0], d.lats[0]], [d.lons[nx - 1], d.lats[ny - 1]]],
    etiqueta: (nivel) => temperatura ? `${numero(nivel, 0)}°` : numero(nivel, nivel % 1 ? 1 : 0),
    mayor: (nivel) => temperatura && nivel % 5 === 0,
    formato: (v) => v === null ? "sin dato" : `${numero(v, d.decimales)} ${d.unidad}`,
    noches: noches(d),
  };
}

// Valor interpolado en (lat, lon) a la hora t, o null fuera de la rejilla
function valorEn(ds, t, lat, lon) {
  const x = ds.x(lon), y = ds.y(lat);
  if (x < 0 || y < 0 || x > ds.nx - 1 || y > ds.ny - 1) return null;
  const v = interpolar(ds.rejillas[t], ds.nx, ds.ny, x, y);
  if (Number.isNaN(v)) return null;
  return ds.paleta === "precipitacion" ? Math.max(0, v) : v;
}

// Imagen del campo e isolíneas de la hora t, calculadas al pedirlas y guardadas
function fotograma(ds, t) {
  if (ds.fotogramas[t]) return ds.fotogramas[t];
  const g = ds.rejillas[t], {nx, ny, escala} = ds;
  const img = remuestrear(g, nx, ny, ds.kImagen);
  const lienzo = Object.assign(document.createElement("canvas"), {width: img.W, height: img.H});
  const contexto = lienzo.getContext("2d"), pixeles = contexto.createImageData(img.W, img.H), p = pixeles.data;
  for (let y = 0; y < img.H; y++) {
    const fila = (img.H - 1 - y) * img.W;  // la imagen empieza por el norte; la rejilla, por el sur
    for (let x = 0; x < img.W; x++) {
      const v = img.v[fila + x], k = Math.round(escala.posicion(v) * 255) * 3, o = (y * img.W + x) * 4;
      p[o] = escala.tabla[k];
      p[o + 1] = escala.tabla[k + 1];
      p[o + 2] = escala.tabla[k + 2];
      p[o + 3] = escala.alfa(v);
    }
  }
  contexto.putImageData(pixeles, 0, 0);
  const fino = remuestrear(g, nx, ny, 4);
  const features = escala.niveles.flatMap(nivel => isolineas(fino.v, fino.W, fino.H, nivel).map(linea => ({
    type: "Feature",
    properties: {etiqueta: ds.etiqueta(nivel), mayor: ds.mayor(nivel)},
    geometry: {type: "LineString", coordinates: linea.map(([x, y]) => [ds.lon(x / 4), ds.lat(y / 4)])},
  })));
  return ds.fotogramas[t] = {url: lienzo.toDataURL(), lineas: {type: "FeatureCollection", features}};
}

// ---------------------------------------------------------------- Fechas

const formatos = {};
function formato(tz, opciones) {
  const clave = tz + JSON.stringify(opciones);
  return formatos[clave] ??= new Intl.DateTimeFormat("es-ES", {timeZone: tz, ...opciones});
}

const horaLocal = (t, tz) => +formato(tz, {hour: "numeric", hourCycle: "h23"}).format(t);
const diaCorto = (t, tz) => formato(tz, {weekday: "short", day: "numeric"}).format(t).replace(".", "");

function fechaLarga(t, tz) {
  const p = Object.fromEntries(formato(tz, {weekday: "long", day: "numeric", month: "short", hour: "2-digit",
                                            minute: "2-digit", hourCycle: "h23"}).formatToParts(t)
    .map(({type, value}) => [type, value]));
  return `${p.weekday} ${p.day} ${p.month.replace(".", "")} · ${p.hour}:${p.minute}`;
}

function relativa(t) {
  const horas = Math.round((t - Date.now()) / 36e5);
  return horas === 0 ? "ahora" : horas > 0 ? `dentro de ${horas} h` : `hace ${-horas} h`;
}

// Altura del Sol (radianes) en el instante t (ms), con las fórmulas aproximadas del Almanaque Náutico
function alturaSol(t, lat, lon) {
  const d = (t - 946728000000) / 864e5;  // días desde J2000.0
  const g = (357.529 + 0.98560028 * d) * RAD;
  const l = (280.459 + 0.98564736 * d + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) * RAD;
  const e = (23.439 - 0.00000036 * d) * RAD;
  const declinacion = Math.asin(Math.sin(e) * Math.sin(l));
  const ascension = Math.atan2(Math.cos(e) * Math.sin(l), Math.cos(l));
  const angulo = (18.697374558 + 24.06570982441908 * d) * 15 * RAD + lon * RAD - ascension;
  return Math.asin(Math.sin(lat * RAD) * Math.sin(declinacion)
                   + Math.cos(lat * RAD) * Math.cos(declinacion) * Math.cos(angulo));
}

// Tramos [inicio, fin] de noche en el lugar, cada 10 min, para sombrearlos en la línea de tiempo
function noches(d) {
  const tramos = [], h0 = d.horas[0], h1 = d.horas.at(-1);
  let inicio = null;
  for (let t = h0; t <= h1; t += 6e5) {
    const noche = alturaSol(t, d.lugar.lat, d.lugar.lon) < -0.833 * RAD;
    if (noche && inicio === null) inicio = t;
    if (!noche && inicio !== null) { tramos.push([inicio, t]); inicio = null; }
  }
  if (inicio !== null) tramos.push([inicio, h1]);
  return tramos;
}

// ---------------------------------------------------------------- Visor

function crearVisor(raiz) {
  const $ = (selector) => raiz.querySelector(selector);
  const v = {raiz, t: 0, punto: null, reproduciendo: false, svg: $(".va-serie"), globo: $(".va-globo")};

  $(".va-play").innerHTML = ICONO_PLAY;
  $(".va-play").onclick = () => v.reproduciendo ? pausar(v) : reproducir(v);

  raiz.addEventListener("keydown", (e) => {
    if (!v.ds || e.ctrlKey || e.metaKey || e.altKey) return;
    const ultimo = v.ds.horas.length - 1;
    const destino = {ArrowLeft: v.t - 1, ArrowRight: v.t + 1, PageUp: v.t - 6, PageDown: v.t + 6, Home: 0,
                     End: ultimo}[e.key];
    if (e.key === " ") {
      if (e.target.closest("button")) return;  // el botón ya responde a la barra espaciadora
      v.reproduciendo ? pausar(v) : reproducir(v);
    } else if (destino !== undefined) {
      pausar(v);
      irA(v, Math.min(ultimo, Math.max(0, destino)));
    } else {
      return;
    }
    e.preventDefault();
  });

  // Línea de tiempo: pulsar o arrastrar cambia la hora; pasar por encima la muestra arriba sin cambiarla
  const indice = (e) => {
    const {izquierda, ancho} = v.ejes, n = v.ds.horas.length - 1;
    const x = e.clientX - v.svg.getBoundingClientRect().left - izquierda;
    return Math.min(n, Math.max(0, Math.round(x / ancho * n)));
  };
  v.svg.addEventListener("pointerdown", (e) => {
    if (!v.ds || !v.ejes) return;
    v.svg.setPointerCapture(e.pointerId);
    v.arrastrando = true;
    pausar(v);
    irA(v, indice(e));
  });
  v.svg.addEventListener("pointermove", (e) => {
    if (!v.ds || !v.ejes) return;
    const i = indice(e);
    if (v.arrastrando && i !== v.t) irA(v, i);
    previa(v, v.arrastrando ? null : i);
  });
  for (const evento of ["pointerup", "pointercancel"]) v.svg.addEventListener(evento, () => { v.arrastrando = false; });
  v.svg.addEventListener("pointerleave", () => previa(v, null));
  new ResizeObserver(() => dibujarSerie(v)).observe(v.svg);

  document.addEventListener("fullscreenchange", () => {
    const completa = document.fullscreenElement === raiz;
    raiz.classList.toggle("completa", completa);
    // En pantalla completa la rueda y un dedo mueven el mapa; incrustado en la página, no (la página tiene que
    // poder desplazarse)
    v.mapa?.cooperativeGestures?.[completa ? "disable" : "enable"]();
  });
  return v;
}

function cargarDatos(v, d) {
  if (d.clave === v.clave) return;  // la misma rejilla: Streamlit ha recargado la página por otra cosa
  v.clave = d.clave;
  const anterior = v.ds, ds = v.ds = preparar(d);
  // Se mantiene la hora vista; si es la primera vez (o ya no está), la más cercana a ahora
  let t = anterior ? ds.horas.indexOf(anterior.horas[v.t]) : -1;
  if (t < 0) {
    t = ds.horas.findIndex(h => h >= Date.now() - 18e5);
    if (t < 0) t = ds.horas.length - 1;
  }
  v.t = t;
  leyenda(v);
  calcularSerie(v);
  dibujarSerie(v);
  if (v.mapa === undefined) crearMapa(v);
  else if (v.mapa?.getSource("arome")) v.mapa.getSource("dominio").setData(dominio(ds));
  irA(v, t);
}

function leyenda(v) {
  const {ds, raiz} = v, $ = (selector) => raiz.querySelector(selector);
  $(".va-titulo b").textContent = ds.variable;
  $(".va-titulo span").textContent = ds.unidad;
  $(".va-barra").style.background = ds.escala.gradiente;
  $(".va-marcas").innerHTML = ds.escala.marcas.map(m =>
    `<span style="left:${(100 * ds.escala.posicion(m)).toFixed(1)}%">${numero(m, m % 1 ? 1 : 0)}</span>`).join("");
  // Con la lluvia, el máximo de la pasada: si no llueve, el mapa sale vacío y así se ve que no es un fallo
  let nota = "";
  if (ds.paleta === "precipitacion") {
    const maximo = ds.rejillas.reduce((m, g) => g.reduce((n, v) => v > n ? v : n, m), 0);
    nota = maximo < LLUVIA[0][0] ? " · sin lluvia en toda la pasada"
      : ` · máximo, ${numero(maximo, 1)} ${ds.unidad} en una hora`;
  }
  $(".va-fuente").textContent = `Media del PE-AROME · pasada ${ds.pasada}${nota}`;
}

function puntoActual(v) {
  return v.punto ?? v.ds.lugar;
}

function calcularSerie(v) {
  const {lat, lon} = puntoActual(v);
  v.serie = v.ds.rejillas.map((_, t) => valorEn(v.ds, t, lat, lon));
}

function elegirPunto(v, punto) {
  v.punto = punto;
  calcularSerie(v);
  if (v.chincheta) {
    if (punto) v.chincheta.setLngLat([punto.lon, punto.lat]).addTo(v.mapa);
    else v.chincheta.remove();
    v.ciudad.getElement().classList.toggle("elegido", !punto);
  }
  dibujarSerie(v);
  textos(v);
  etiquetas(v);
}

// Valor de la hora vista junto al lugar y junto a la chincheta
function etiquetas(v) {
  if (!v.ciudad) return;
  const {ds, t} = v, valor = ({lat, lon}) => ds.formato(valorEn(ds, t, lat, lon));
  v.ciudad.getElement().querySelector("b").textContent = valor(ds.lugar);
  if (v.punto) v.chincheta.getElement().querySelector("b").textContent = valor(v.punto);
}

function irA(v, t) {
  const ds = v.ds;
  v.t = t;
  const f = fotograma(ds, t), fuente = v.mapa?.getSource("arome");
  if (fuente) {
    fuente.updateImage({url: f.url, coordinates: ds.esquinas});
    v.mapa.getSource("isolineas").setData(f.lineas);
  }
  textos(v);
  etiquetas(v);
  moverCursor(v);
  if (v.raton) globo(v, v.raton);
  // La hora siguiente se prepara en un rato libre: así la reproducción y las flechas van fluidas
  const siguiente = (t + 1) % ds.horas.length;
  (window.requestIdleCallback ?? setTimeout)(() => fotograma(ds, siguiente));
}

function reproducir(v) {
  v.reproduciendo = true;
  v.raiz.querySelector(".va-play").innerHTML = ICONO_PAUSA;
  const ultimo = v.ds.horas.length - 1;
  if (v.t === ultimo) irA(v, 0);
  const paso = () => {
    if (!v.reproduciendo) return;
    irA(v, v.t === ultimo ? 0 : v.t + 1);
    v.temporizador = setTimeout(paso, v.t === ultimo ? PAUSA_FINAL_MS : PASO_MS);  // pausa en la última hora
  };
  v.temporizador = setTimeout(paso, PASO_MS);
}

function pausar(v) {
  v.reproduciendo = false;
  clearTimeout(v.temporizador);
  v.raiz.querySelector(".va-play").innerHTML = ICONO_PLAY;
}

function textos(v, i = null) {
  const {ds, raiz} = v, t = i ?? v.t, hora = ds.horas[t], punto = puntoActual(v);
  const nombre = punto.nombre ?? `${numero(Math.abs(punto.lat), 2)}° ${punto.lat >= 0 ? "N" : "S"}, `
    + `${numero(Math.abs(punto.lon), 2)}° ${punto.lon >= 0 ? "E" : "O"}`;
  raiz.querySelector(".va-hora").innerHTML = `${fechaLarga(hora, ds.tz)}<small>${relativa(hora)}</small>`;
  raiz.querySelector(".va-lectura").innerHTML = `${nombre} <b>${ds.formato(v.serie[t])}</b>`;
  raiz.querySelector(".va-cabecera").classList.toggle("previa", i !== null);
}

function previa(v, i) {
  textos(v, i === v.t ? null : i);
  const fantasma = v.svg.querySelector(".fantasma");
  if (!fantasma) return;
  fantasma.style.display = i === null || i === v.t ? "none" : "";
  if (i !== null) fantasma.setAttribute("transform", `translate(${v.ejes.x(v.ds.horas[i])},0)`);
}

function globo(v, {lngLat, point}) {
  const valor = v.ds && valorEn(v.ds, v.t, lngLat.lat, lngLat.lng);
  v.globo.style.display = valor === null || !v.ds ? "none" : "block";
  if (valor === null || !v.ds) return;
  v.globo.textContent = v.ds.formato(valor);
  v.globo.style.transform = `translate(${point.x + 14}px, ${point.y - 34}px)`;
}

// ---------------------------------------------------------------- Línea de tiempo

function dibujarSerie(v) {
  const {ds, svg, serie} = v, ancho = svg.clientWidth, alto = svg.clientHeight;
  if (!ds || !ancho) return;
  const h0 = ds.horas[0], h1 = ds.horas.at(-1), base = alto - 16, izquierda = 2, util = ancho - 4;
  const x = (t) => izquierda + (t - h0) / (h1 - h0) * util;
  const lluvia = ds.paleta === "precipitacion", validos = serie.filter(s => s !== null);
  let minimo = validos.length ? Math.min(...validos) : 0, maximo = validos.length ? Math.max(...validos) : 1;
  if (lluvia) {
    minimo = 0;
    maximo = Math.max(maximo, 0.5) * 1.15;
  } else {
    const margen = Math.max(maximo - minimo, ds.paso) * 0.18;
    minimo -= margen;
    maximo += margen;
  }
  const y = (valor) => 3 + (1 - (valor - minimo) / (maximo - minimo)) * (base - 3);
  v.ejes = {x, y, izquierda, ancho: util};

  const partes = v.ds.noches.map(([a, b]) =>
    `<rect class="noche" x="${x(a)}" y="0" width="${x(b) - x(a)}" height="${base}"/>`);
  const cada = pasoRedondo(ds.paso, maximo - minimo, 3);
  for (let valor = Math.ceil(minimo / cada) * cada + 0; valor < maximo; valor += cada) {  // + 0: sin "-0"
    if (lluvia && valor === 0) continue;
    partes.push(`<line class="guia" x1="0" x2="${ancho}" y1="${y(valor)}" y2="${y(valor)}"/>`);
    if (y(valor) > 13) {  // la etiqueta va encima de la línea: arriba del todo no cabe
      partes.push(`<text class="guia-texto" x="5" y="${y(valor) - 3}">${numero(valor, cada % 1 ? 1 : 0)}</text>`);
    }
  }
  // Días: separador a medianoche y su nombre en medio de su tramo, si cabe
  const cortes = [h0, ...ds.horas.filter(h => h > h0 && horaLocal(h, ds.tz) === 0), h1];
  cortes.forEach((a, k) => {
    if (k && k < cortes.length - 1) partes.push(`<line class="dia" x1="${x(a)}" x2="${x(a)}" y1="0" y2="${alto}"/>`);
    const b = cortes[k + 1];
    if (b !== undefined && x(b) - x(a) > 38) {
      partes.push(`<text class="dia-texto" x="${(x(a) + x(b)) / 2}" y="${alto - 3}">${diaCorto(a, ds.tz)}</text>`);
    }
  });
  if (lluvia) {
    const barra = Math.max(1.5, util / (ds.horas.length - 1) * 0.7);
    serie.forEach((s, t) => {
      if (s >= 0.05) {
        partes.push(`<rect class="barra" x="${x(ds.horas[t]) - barra / 2}" y="${y(s)}" width="${barra}" `
                    + `height="${base - y(s)}"/>`);
      }
    });
  } else {
    // Tramos seguidos con dato: un área bajo la curva y la línea encima
    let tramo = [];
    const cerrar = () => {
      if (tramo.length > 1) {
        const linea = tramo.map(([px, py], k) => `${k ? "L" : "M"}${px.toFixed(1)},${py.toFixed(1)}`).join("");
        partes.push(`<path class="area" d="${linea}L${tramo.at(-1)[0]},${base}L${tramo[0][0]},${base}Z"/>`,
                    `<path class="curva" d="${linea}"/>`);
      }
      tramo = [];
    };
    serie.forEach((s, t) => s === null ? cerrar() : tramo.push([x(ds.horas[t]), y(s)]));
    cerrar();
  }
  const ahora = Date.now();
  if (ahora > h0 && ahora < h1) {
    partes.push(`<line class="ahora" x1="${x(ahora)}" x2="${x(ahora)}" y1="0" y2="${base}"/>`);
  }
  partes.push(`<line class="fantasma" y1="0" y2="${base}" style="display:none"/>`,
              `<g class="cursor"><line y1="0" y2="${base}"/><circle r="4.5"/></g>`);
  svg.innerHTML = partes.join("");
  moverCursor(v);
}

function moverCursor(v) {
  const cursor = v.svg.querySelector(".cursor");
  if (!cursor || !v.ejes) return;
  const valor = v.serie[v.t];
  cursor.setAttribute("transform", `translate(${v.ejes.x(v.ds.horas[v.t])},0)`);
  const circulo = cursor.querySelector("circle");
  circulo.style.display = valor === null ? "none" : "";
  if (valor !== null) circulo.setAttribute("cy", v.ejes.y(valor));
}

// ---------------------------------------------------------------- Mapa

function dominio(ds) {
  const [[oeste, sur], [este, norte]] = ds.caja;
  return {type: "Feature", properties: {},
          geometry: {type: "LineString", coordinates: [[oeste, sur], [este, sur], [este, norte], [oeste, norte],
                                                       [oeste, sur]]}};
}

async function crearMapa(v) {
  v.mapa = null;  // creándose
  const aviso = v.raiz.querySelector(".va-aviso");
  let maplibregl;
  try {
    maplibregl = await cargarMaplibre();
  } catch {
    aviso.textContent = "No se ha podido cargar el mapa. Prueba a recargar la página.";
    return;
  }
  const mapa = v.mapa = new maplibregl.Map({
    container: v.raiz.querySelector(".va-mapa"), style: ESTILO,
    bounds: v.ds.caja, fitBoundsOptions: {padding: {top: 30, bottom: 20, left: 20, right: 20}},
    minZoom: 5, maxZoom: 13, keyboard: false, dragRotate: false, pitchWithRotate: false, touchPitch: false,
    cooperativeGestures: true, attributionControl: {compact: true},
    locale: {
      "NavigationControl.ZoomIn": "Acercar",
      "NavigationControl.ZoomOut": "Alejar",
      "FullscreenControl.Enter": "Pantalla completa",
      "FullscreenControl.Exit": "Salir de la pantalla completa",
      "AttributionControl.ToggleAttribution": "Créditos",
      "CooperativeGesturesHandler.WindowsHelpText": "Usa Ctrl + rueda del ratón para acercar o alejar el mapa",
      "CooperativeGesturesHandler.MacHelpText": "Usa ⌘ + rueda del ratón para acercar o alejar el mapa",
      "CooperativeGesturesHandler.MobileHelpText": "Usa dos dedos para mover el mapa",
    },
  });
  mapa.touchZoomRotate.disableRotation();
  mapa.addControl(new maplibregl.NavigationControl({showCompass: false}), "top-right");
  mapa.addControl(new maplibregl.FullscreenControl({container: v.raiz}), "top-right");
  mapa.on("error", () => {
    if (!v.estiloListo && !v.respaldo) {
      v.respaldo = true;
      mapa.setStyle(ESTILO_RESPALDO);
    }
  });
  mapa.on("style.load", () => {
    v.estiloListo = true;
    capas(v);
    aviso.style.display = "none";
  });
  // Los créditos, plegados en su botón (MapLibre los abre al cargar si el mapa es ancho)
  mapa.once("load", () => mapa.getContainer().querySelector(".maplibregl-ctrl-attrib")
    ?.classList.remove("maplibregl-compact-show"));

  // El lugar de la página (pulsarlo vuelve a él) y la chincheta del punto elegido, que se puede arrastrar. Los dos
  // llevan al lado el valor de la hora vista
  const lugar = Object.assign(document.createElement("div"), {className: "va-lugar elegido",
                                                              title: "Ver la serie de este punto"});
  lugar.innerHTML = `<i></i><span>${v.ds.lugar.nombre}</span><b></b>`;
  lugar.addEventListener("click", (e) => { e.stopPropagation(); elegirPunto(v, null); });
  v.ciudad = new maplibregl.Marker({element: lugar, anchor: "left", offset: [-6, 0]})
    .setLngLat([v.ds.lugar.lon, v.ds.lugar.lat]).addTo(mapa);
  const chincheta = Object.assign(document.createElement("div"), {className: "va-chincheta elegido",
                                                                  title: "Arrástrala para ver otro punto"});
  chincheta.innerHTML = "<i></i><b></b>";
  v.chincheta = new maplibregl.Marker({element: chincheta, anchor: "left", offset: [-7, 0], draggable: true});
  etiquetas(v);
  const dentro = ({lng, lat}) => {
    const [[oeste, sur], [este, norte]] = v.ds.caja;
    return {lat: Math.min(norte, Math.max(sur, lat)), lon: Math.min(este, Math.max(oeste, lng))};
  };
  v.chincheta.on("drag", () => elegirPunto(v, dentro(v.chincheta.getLngLat())));
  mapa.on("click", (e) => {
    if (valorEn(v.ds, v.t, e.lngLat.lat, e.lngLat.lng) !== null) elegirPunto(v, dentro(e.lngLat));
  });
  mapa.on("mousemove", (e) => { v.raton = e; globo(v, e); });
  mapa.getCanvasContainer().addEventListener("mouseleave", () => { v.raton = null; v.globo.style.display = "none"; });
}

function capas(v) {
  const {mapa, ds} = v, f = fotograma(ds, v.t);
  const antes = (id) => mapa.getLayer(id) ? id : undefined;
  // Orden: fondo y agua, el campo, el relieve sombreado encima (se ve a través de los colores), carreteras y
  // límites, isolíneas y, arriba del todo, los nombres de los pueblos
  mapa.addSource("arome", {type: "image", url: f.url, coordinates: ds.esquinas});
  mapa.addLayer({id: "arome", type: "raster", source: "arome",
                 paint: {"raster-opacity": 0.8, "raster-fade-duration": 0, "raster-resampling": "linear"}},
                antes("waterway"));
  mapa.addSource("relieve", {type: "raster-dem", tiles: [RELIEVE], encoding: "terrarium", tileSize: 256, maxzoom: 13,
                             attribution: '<a href="https://registry.opendata.aws/terrain-tiles/">Relieve: Terrain Tiles</a>'});
  mapa.addLayer({id: "relieve", type: "hillshade", source: "relieve",
                 paint: {"hillshade-exaggeration": 0.4, "hillshade-shadow-color": "rgba(52, 40, 28, 0.6)",
                         "hillshade-highlight-color": "rgba(255, 255, 255, 0.3)",
                         "hillshade-accent-color": "rgba(52, 40, 28, 0.25)"}},
                antes("waterway"));
  for (const capa of mapa.getStyle().layers) {
    // Las carreteras, más tenues: sobre el campo de colores distraen
    if (capa.type === "line" && /^(highway|tunnel|railway|road|aeroway)/.test(capa.id)) {
      mapa.setPaintProperty(capa.id, "line-opacity", 0.4);
    }
  }
  mapa.addSource("dominio", {type: "geojson", data: dominio(ds)});
  mapa.addLayer({id: "dominio", type: "line", source: "dominio",
                 paint: {"line-color": "#635b53", "line-width": 1.2, "line-dasharray": [3, 3], "line-opacity": 0.7}});
  mapa.addSource("isolineas", {type: "geojson", data: f.lineas});
  const primeraEtiqueta = mapa.getStyle().layers.find(capa => capa.type === "symbol")?.id;
  mapa.addLayer({id: "isolineas", type: "line", source: "isolineas", layout: {"line-join": "round", "line-cap": "round"},
                 paint: {"line-color": "#2a241f", "line-opacity": 0.6,
                         "line-width": ["case", ["get", "mayor"], 1.6, 0.8]}},
                primeraEtiqueta);
  if (!v.respaldo) {
    mapa.addLayer({id: "isolineas-etiquetas", type: "symbol", source: "isolineas",
                   layout: {"symbol-placement": "line", "text-field": ["get", "etiqueta"],
                            "text-font": ["Noto Sans Bold"], "text-size": 11, "symbol-spacing": 220,
                            "text-max-angle": 35, "text-padding": 4},
                   paint: {"text-color": "#2a241f", "text-halo-color": "rgba(255, 255, 255, 0.9)",
                           "text-halo-width": 1.5}},
                  primeraEtiqueta);
  }
}

// ---------------------------------------------------------------- Streamlit

export default function (component) {
  const {data, parentElement} = component;
  const raiz = parentElement.querySelector(".visor-arome");
  raiz._visor ??= crearVisor(raiz);
  cargarDatos(raiz._visor, data);
}
