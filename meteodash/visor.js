// Visor de series en paneles apilados con un solo cursor (ver visor.py), como el meteograma de las 48 h: el medio plazo
// hora a hora, el mar, la calidad del aire, el largo plazo día a día y el año hidrológico. El ratón muestra cada momento
// al pasar y pulsar lo fija; el dedo (arrastrando en horizontal: en vertical sigue desplazando la página), las flechas y
// «Ahora» o «Hoy» también lo fijan. Todo en el navegador, sin recargar Streamlit.
//
// Python manda las series con nombre y, para cada panel, sus zonas (normalmente una; la lluvia, dos: la cantidad y la
// probabilidad), cada una con su escala y sus capas (miembros, líneas, bandas, barras, franjas, referencias y
// etiquetas), y lo que se lee encima del panel en el momento del cursor.

const IZQUIERDA = 36, DERECHA = 8;  // márgenes del dibujo: a la izquierda, los valores del eje
const ARRIBA = 16;  // hueco sobre las curvas para las etiquetas de los máximos
const HUECO = 10;  // entre las zonas de un panel
const HORA = 36e5, DIA = 864e5, RAD = Math.PI / 180;
const TRAZOS = {discontinua: "6 4", punteada: "2 3"};

const numero = (v, decimales) => v.toLocaleString("es-ES", {minimumFractionDigits: decimales,
                                                             maximumFractionDigits: decimales});
const valido = (v) => v !== null && v !== undefined && v !== "" && !Number.isNaN(v);

// Marcas redondas del eje (×1, 2, 2,5 o 5 por potencia de 10; 2,5 solo desde 25, que no lleva decimales), unas `n`
function marcas(min, max, n) {
  const bruto = (max - min) / n, potencia = 10 ** Math.floor(Math.log10(bruto));
  const paso = (potencia >= 10 ? [1, 2, 2.5, 5, 10] : [1, 2, 5, 10]).map(m => m * potencia).find(p => p >= bruto);
  const lista = [];
  for (let v = Math.ceil(min / paso) * paso; v <= max + 1e-9; v += paso) lista.push(+v.toFixed(6) + 0);
  return {lista, decimales: Math.max(0, -Math.floor(Math.log10(paso) + 1e-9))};
}

// ---------------------------------------------------------------- Fechas y sol

const formatos = {};
function formato(tz, opciones) {
  const clave = tz + JSON.stringify(opciones);
  return formatos[clave] ??= new Intl.DateTimeFormat("es-ES", {timeZone: tz, ...opciones});
}
const partes = (t, tz, opciones) => Object.fromEntries(formato(tz, opciones).formatToParts(t)
  .map(({type, value}) => [type, value]));
const horaLocal = (t, tz) => +formato(tz, {hour: "numeric", hourCycle: "h23"}).format(t);
const diaCorto = (t, tz) => formato(tz, {weekday: "short", day: "numeric"}).format(t).replace(".", "");
const mesCorto = (t, tz) => formato(tz, {month: "short"}).format(t).replace(".", "");

// Número del día local, para contar días entre fechas
function diaLocal(t, tz) {
  const p = partes(t, tz, {year: "numeric", month: "numeric", day: "numeric"});
  return Date.UTC(+p.year, p.month - 1, +p.day) / DIA;
}
const nombreDia = (t, tz) => diaLocal(t, tz) === diaLocal(Date.now(), tz) ? "Hoy" : diaCorto(t, tz);

// Lo que dice la cabecera: el momento del cursor y, salvo que se pida lo contrario, cuánto falta
function fecha(v, t) {
  const {modo, eje, tz} = v.d;
  if (modo === "hora") {
    const p = partes(t, tz, {weekday: "long", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
                             hourCycle: "h23"});
    return `${p.weekday} ${p.day} ${p.month.replace(".", "")} · ${p.hour}:${p.minute}`;
  }
  if (eje === "meses") return formato(tz, {day: "numeric", month: "long"}).format(t);
  const p = partes(t, tz, {weekday: "long", day: "numeric", month: "short"});
  return `${p.weekday} ${p.day} ${p.month.replace(".", "")}`;
}

function relativa(v, t) {
  const {modo, tz, relativa} = v.d;
  if (relativa === false) return "";
  if (modo === "hora") {
    const horas = Math.round((t - Date.now()) / HORA);
    return horas === 0 ? "ahora" : horas > 0 ? `dentro de ${horas} h` : `hace ${-horas} h`;
  }
  const dias = diaLocal(t, tz) - diaLocal(Date.now(), tz);
  return {0: "hoy", 1: "mañana", [-1]: "ayer"}[dias] ?? (dias > 0 ? `dentro de ${dias} días` : `hace ${-dias} días`);
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

// Tramos [inicio, fin] de noche en el lugar, cada 10 min (solo hora a hora)
function noches(d) {
  if (d.modo !== "hora" || !valido(d.lat)) return [];
  const tramos = [], h0 = d.horas[0], h1 = d.horas.at(-1);
  let inicio = null;
  for (let t = h0; t <= h1; t += 6e5) {
    const noche = alturaSol(t, d.lat, d.lon) < -0.833 * RAD;
    if (noche && inicio === null) inicio = t;
    if (!noche && inicio !== null) { tramos.push([inicio, t]); inicio = null; }
  }
  if (inicio !== null) tramos.push([inicio, h1]);
  return tramos;
}

// Separadores verticales: las medianoches (hora a hora), los lunes (día a día) o el día 1 de cada mes
function cortes(d) {
  const {horas, tz} = d;
  const corte = d.modo === "hora" ? (h) => horaLocal(h, tz) === 0
    : d.eje === "meses" ? (h) => +formato(tz, {day: "numeric"}).format(h) === 1
    : (h) => partes(h, tz, {weekday: "short"}).weekday.startsWith("lun");
  return horas.filter((h, i) => i && corte(h));
}

// ---------------------------------------------------------------- Estructura

// El cursor marca el momento fijado (al empezar, ahora). Con el ratón, pasar por encima lo muestra sin fijarlo, como el
// hover de un gráfico, y al salir vuelve al fijado; pulsar lo fija. El dedo, las flechas y el botón también lo fijan
function fijar(v, t) {
  v.fijo = t;
  irA(v, t);
}

function crear(raiz) {
  const v = {raiz, t: 0, fijo: 0, desplegados: {}};
  raiz.addEventListener("keydown", (e) => {
    if (!v.d || e.ctrlKey || e.metaKey || e.altKey) return;
    const ultimo = v.d.horas.length - 1, salto = v.d.modo === "dia" ? 7 : 6;
    const destino = {ArrowLeft: v.fijo - 1, ArrowRight: v.fijo + 1, PageUp: v.fijo - salto, PageDown: v.fijo + salto,
                     Home: 0, End: ultimo}[e.key];
    if (destino === undefined) return;
    e.preventDefault();
    fijar(v, Math.min(ultimo, Math.max(0, destino)));
  });
  raiz.addEventListener("pointerleave", (e) => { if (v.d && e.pointerType === "mouse") irA(v, v.fijo); });
  new ResizeObserver(() => dibujarTodo(v)).observe(raiz);
  return v;
}

const panel = (p) => `<section class="vs-panel" data-id="${p.id}"><div class="vs-lectura"><b>${p.titulo}</b>`
  + `<span></span></div><svg class="vs-svg"></svg></section>`;

// Muestra de la leyenda: una línea (continua, discontinua o punteada) o un área
function muestra({texto, color, trazo, tipo, grosor}) {
  const estilo = tipo === "area" ? `height:9px;border-radius:2px;background:${color}`
    : `border-top:${Math.max(2, Math.round(grosor ?? 2))}px ${{discontinua: "dashed", punteada: "dotted"}[trazo] ?? "solid"} ${color}`;
  return `<span><i style="${estilo}"></i>${texto}</span>`;
}

function construir(v) {
  const {d, raiz} = v, grupos = d.grupos ?? [];
  const boton = d.boton ?? (d.modo === "dia" ? "Hoy" : "Ahora");
  let html = (d.titulo ? `<div class="vs-titulo">${d.titulo}</div>` : "")
    + `<div class="vs-cabecera"><div class="vs-hora"></div><button class="vs-ahora">${boton}</button></div>`
    + (d.leyenda?.length ? `<div class="vs-leyenda">${d.leyenda.map(muestra).join("")}</div>` : "")
    + d.paneles.map(panel).join("") + '<svg class="vs-eje"></svg>';
  grupos.forEach((g, k) => {
    html += `<button class="vs-plegable" data-grupo="${k}" aria-expanded="false"><span class="vs-flecha">▸</span>`
      + `${g.titulo}${g.aviso ? `<em>${g.aviso}</em>` : ""}</button>`
      + `<div class="vs-grupo" data-grupo="${k}">${g.paneles.map(panel).join("")}<svg class="vs-eje"></svg></div>`;
  });
  raiz.innerHTML = html;
  v.paneles = Object.fromEntries([...d.paneles, ...grupos.flatMap(g => g.paneles)].map(p => [p.id, p]));
  raiz.querySelector(".vs-ahora").onclick = () => fijar(v, inicio(v));
  for (const plegable of raiz.querySelectorAll(".vs-plegable")) {
    const k = plegable.dataset.grupo, grupo = raiz.querySelector(`.vs-grupo[data-grupo="${k}"]`);
    v.desplegados[k] ??= Boolean(grupos[k].desplegado);  // al recargar los datos se queda como lo dejó la persona
    const aplicar = () => {
      plegable.setAttribute("aria-expanded", v.desplegados[k]);
      grupo.hidden = !v.desplegados[k];
    };
    plegable.onclick = () => {
      v.desplegados[k] = !v.desplegados[k];
      aplicar();
      dibujarTodo(v);
    };
    aplicar();
  }
  for (const svg of raiz.querySelectorAll(".vs-svg, .vs-eje")) enlazar(v, svg);
}

// Ratón: el cursor sigue al puntero y pulsar fija el momento. Dedo: tocar o arrastrar en horizontal lo fija (en
// vertical, la página se desplaza)
function enlazar(v, svg) {
  let arrastrando = false;
  const indice = (e) => {
    const {h0, h1, ancho, centro} = v.ejes, x = e.clientX - svg.getBoundingClientRect().left;
    const instante = h0 + (x - IZQUIERDA) / (ancho - IZQUIERDA - DERECHA) * (h1 - h0) - centro;
    let mejor = 0;
    v.d.horas.forEach((h, i) => { if (Math.abs(h - instante) < Math.abs(v.d.horas[mejor] - instante)) mejor = i; });
    return mejor;
  };
  svg.addEventListener("pointerdown", (e) => {
    if (!v.ejes) return;
    if (e.pointerType !== "mouse") {
      arrastrando = true;
      try {
        svg.setPointerCapture(e.pointerId);
      } catch {
        // sin captura, el arrastre sigue funcionando mientras el dedo no salga del panel
      }
    }
    fijar(v, indice(e));
  });
  svg.addEventListener("pointermove", (e) => {
    if (!v.ejes || (e.pointerType !== "mouse" && !arrastrando)) return;
    const i = indice(e);
    if (arrastrando) {
      if (i !== v.fijo) fijar(v, i);
    } else if (i !== v.t) {
      irA(v, i);
    }
  });
  for (const evento of ["pointerup", "pointercancel"]) svg.addEventListener(evento, () => { arrastrando = false; });
}

// Hora a hora, la hora más cercana a ahora (a las 20:47, las 21:00); día a día, hoy. Python puede pedir otro momento
function inicio(v) {
  const {horas, modo} = v.d, ahora = Date.now();
  if (valido(v.d.inicio)) return v.d.inicio;
  const i = modo === "dia" ? horas.findLastIndex(h => h <= ahora) : horas.findIndex(h => h >= ahora - 18e5);
  return i < 0 ? (modo === "dia" ? 0 : horas.length - 1) : i;
}

function cargar(v, d) {
  const momento = v.d ? v.d.horas[v.fijo] : null;
  v.d = d;
  v.noches = noches(d);
  v.cortes = cortes(d);
  const t = d.horas.indexOf(momento);
  v.t = v.fijo = t < 0 ? inicio(v) : t;
  construir(v);
  dibujarTodo(v);
}

// ---------------------------------------------------------------- Dibujo

// Posición en píxeles del punto i: el instante (hora a hora) o el centro de su día
const xi = (v, i) => v.ejes.x(v.d.horas[i] + v.ejes.centro);

function dibujarTodo(v) {
  const {d, raiz} = v;
  if (!d) return;
  const primero = [...raiz.querySelectorAll(".vs-svg")].find(svg => !svg.closest("[hidden]"));
  const ancho = primero?.clientWidth;
  if (!ancho) return;
  const dia = d.modo === "dia", h0 = d.horas[0];
  const h1 = Math.max(d.horas.at(-1) + (dia ? DIA : 0), h0 + HORA), util = ancho - IZQUIERDA - DERECHA;
  v.ejes = {h0, h1, ancho, util, centro: dia ? DIA / 2 : 0, x: (t) => IZQUIERDA + (t - h0) / (h1 - h0) * util};
  // Hueco de cada punto: el ancho de un día o la distancia entre dos horas
  v.ejes.paso = dia ? util * DIA / (h1 - h0) : util / Math.max(1, d.horas.length - 1);
  v.escalas = {};
  for (const seccion of raiz.querySelectorAll(".vs-panel")) {
    if (seccion.closest("[hidden]")) continue;
    seccion.querySelector("svg").innerHTML = dibujarPanel(v, v.paneles[seccion.dataset.id], seccion.querySelector("svg"));
  }
  for (const eje of raiz.querySelectorAll(".vs-eje")) if (!eje.closest("[hidden]")) eje.innerHTML = dibujarEje(v);
  irA(v, v.t);
}

// Lo común a todo el panel: noches, separadores de días o meses y la línea de ahora (día a día, solo con meses: con
// días, hoy ya se ve en el eje)
function fondo(v, alto) {
  const {x, h0, h1} = v.ejes, {modo, eje} = v.d, lista = [];
  for (const [a, b] of v.noches) lista.push(`<rect class="vs-noche" x="${x(a)}" y="0" width="${x(b) - x(a)}" height="${alto}"/>`);
  for (const h of v.cortes) lista.push(`<line class="vs-dia" x1="${x(h)}" x2="${x(h)}" y1="0" y2="${alto}"/>`);
  const ahora = Date.now();
  if (ahora > h0 && ahora < h1 && (modo === "hora" || eje === "meses")) {
    lista.push(`<line class="vs-ahora-linea" x1="${x(ahora)}" x2="${x(ahora)}" y1="0" y2="${alto}"/>`);
  }
  return lista;
}

// Escala vertical de una zona del panel, que empieza en y0: fija o con los valores de sus capas y un margen
function escala(v, zona, y0) {
  const e = zona.escala ?? {}, {series} = v.d;
  let min, max;
  if (e.fijo) {
    [min, max] = e.fijo;
  } else {
    const valores = [...(e.incluir ?? [])];
    for (const capa of zona.capas) {
      for (const nombre of [capa.serie, capa.series, capa.bajo, capa.alto]) {
        if (nombre && series[nombre]) valores.push(...series[nombre].flat().filter(n => typeof n === "number"));
      }
      if (capa.tipo === "referencia") valores.push(capa.valor);
    }
    min = valores.length ? Math.min(...valores) : 0;
    max = valores.length ? Math.max(...valores) : 1;
    if (e.cero) {  // desde 0, con un máximo mínimo para que unas décimas no llenen el panel
      min = 0;
      max = Math.max(max, e.max_minimo ?? 0, 1e-6) * (1 + (e.margen ?? 0.1));
    } else {
      const margen = Math.max(max - min, (e.paso ?? 1) * 2) * (e.margen ?? 0.08);
      min -= margen;
      max += margen;
      if (valido(e.piso)) min = Math.max(e.piso, min);
    }
  }
  const arriba = y0 + (e.arriba ?? ARRIBA), abajo = y0 + zona.alto - (e.abajo ?? 4);
  const y = (val) => arriba + (1 - (val - min) / (max - min)) * (abajo - arriba);
  let guias = e.guias, decimales = e.decimales ?? 0;
  if (!guias) ({lista: guias, decimales} = marcas(min, max, zona.alto > 120 ? 4 : 3));
  if (e.sin_cero) guias = guias.filter(g => g !== 0);
  return {y, min, max, guias, decimales, sufijo: e.sufijo ?? "", y0, alto: zona.alto};
}

// Línea por los valores (con huecos donde faltan); con `base`, cerrada hasta ella como un área
function trazo(v, valores, y, base = null) {
  let d = "", tramo = [];
  const cerrar = () => {
    if (tramo.length > 1) {
      d += tramo.map(([px, py], k) => `${k ? "L" : "M"}${px.toFixed(1)},${py.toFixed(1)}`).join("");
      if (base !== null) d += `L${tramo.at(-1)[0].toFixed(1)},${base}L${tramo[0][0].toFixed(1)},${base}Z`;
    }
    tramo = [];
  };
  valores.forEach((val, i) => valido(val) ? tramo.push([xi(v, i), y(val)]) : cerrar());
  cerrar();
  return d;
}

const raya = (capa) => capa.trazo ? ` stroke-dasharray="${TRAZOS[capa.trazo] ?? capa.trazo}"` : "";

const CAPAS = {
  // Todos los miembros del ensemble en un solo trazo fino
  miembros: (v, c, e) => `<path d="${v.d.series[c.series].map(s => trazo(v, s, e.y)).join("")}" fill="none" `
    + `stroke="${c.color}" stroke-width="1"/>`,

  linea: (v, c, e) => {
    const s = v.d.series[c.serie];
    let html = "";
    if (c.area) html += `<path d="${trazo(v, s, e.y, e.y(Math.max(e.min, 0)))}" fill="${c.area}"/>`;
    html += `<path d="${trazo(v, s, e.y)}" fill="none" stroke="${c.color}" stroke-width="${c.ancho ?? 2}" `
      + `stroke-linejoin="round"${raya(c)}/>`;
    s.forEach((val, i) => {
      // `puntos`: donde no es cero (la lluvia); `marcas`: en todos (un punto por día)
      if (valido(val) && (c.marcas || (c.puntos && val > 0))) {
        html += `<circle cx="${xi(v, i)}" cy="${e.y(val)}" r="${c.marcas ? 3 : 2}" fill="${c.color}"/>`;
      }
    });
    return html;
  },

  // Rango entre dos series (10-90 %): ida por la de arriba y vuelta por la de abajo
  banda: (v, c, e) => {
    const alto = v.d.series[c.alto], bajo = v.d.series[c.bajo];
    let d = "", tramo = [];
    const cerrar = () => {
      if (tramo.length > 1) {
        d += tramo.map((i, k) => `${k ? "L" : "M"}${xi(v, i).toFixed(1)},${e.y(alto[i]).toFixed(1)}`).join("")
          + tramo.slice().reverse().map(i => `L${xi(v, i).toFixed(1)},${e.y(bajo[i]).toFixed(1)}`).join("") + "Z";
      }
      tramo = [];
    };
    alto.forEach((a, i) => valido(a) && valido(bajo[i]) ? tramo.push(i) : cerrar());
    cerrar();
    return `<path d="${d}" fill="${c.color}"/>`;
  },

  // Barras desde 0; `grupo` [k, n]: la k-ésima de n barras juntas en cada punto (una por modelo)
  barras: (v, c, e) => {
    const [k, n] = c.grupo ?? [0, 1], total = Math.max(1.5, v.ejes.paso * (c.ancho ?? 0.7));
    const w = Math.max(1.5, total / n), base = e.y(Math.max(e.min, 0));
    return v.d.series[c.serie].map((val, i) => {
      if (!valido(val) || val <= 0) return "";
      const py = e.y(val);
      return `<rect x="${xi(v, i) - total / 2 + k * total / n}" y="${py}" width="${w}" height="${base - py}" `
        + `fill="${c.color}"${c.opacidad ? ` fill-opacity="${c.opacidad}"` : ""}/>`;
    }).join("");
  },

  // Franjas horizontales [desde, hasta (null: sin tope), color, opacidad]: rangos habituales, categorías...
  franjas: (v, c, e) => c.franjas.map(([a, b, color, opacidad]) => {
    const arriba = Math.max(e.y0, b === null ? e.y0 : e.y(b)), abajo = Math.min(e.y0 + e.alto, e.y(a));
    if (abajo <= arriba) return "";
    return `<rect x="${IZQUIERDA}" y="${arriba}" width="${v.ejes.util}" height="${abajo - arriba}" fill="${color}" `
      + `fill-opacity="${opacidad ?? 0.1}"/>`;
  }).join(""),

  // Línea horizontal con su texto (la altitud del lugar en la cota de nieve)
  referencia: (v, c, e) => {
    const py = e.y(c.valor);
    return `<line class="vs-referencia" x1="${IZQUIERDA}" x2="${v.ejes.ancho - DERECHA}" y1="${py}" y2="${py}" `
      + `stroke="${c.color}"/><text class="vs-referencia-texto" x="${IZQUIERDA + 4}" y="${py - 4}" `
      + `fill="${c.color}">${c.texto}</text>`;
  },

  // Textos sobre (o bajo) un punto: [posición, valor, texto, "arriba" | "abajo", color]. Si no caben, se salta alguno
  etiquetas: (v, c, e) => {
    const ultimo = {arriba: -Infinity, abajo: -Infinity};
    let html = "";
    for (const [i, val, texto, lado = "arriba", color = c.color] of c.puntos) {
      const w = texto.length * 6.5 + 6;
      const px = Math.min(v.ejes.ancho - DERECHA - w / 2, Math.max(IZQUIERDA + w / 2, xi(v, i)));
      if (px - ultimo[lado] < w) continue;
      ultimo[lado] = px;
      const py = lado === "arriba" ? Math.max(e.y0 + 11, e.y(val) - 7) : Math.min(e.y0 + e.alto - 2, e.y(val) + 14);
      html += `<text class="vs-etiqueta" x="${px}" y="${py}" fill="${color}">${texto}</text>`;
    }
    return html;
  },
};

function dibujarPanel(v, p, svg) {
  const alto = p.zonas.reduce((suma, z) => suma + z.alto, 0) + HUECO * (p.zonas.length - 1), {ancho} = v.ejes;
  svg.style.height = `${alto}px`;
  const lista = fondo(v, alto), escalas = [];
  let y0 = 0;
  p.zonas.forEach((zona, k) => {
    if (k) {
      lista.push(`<line class="vs-separador" x1="${IZQUIERDA}" x2="${ancho - DERECHA}" y1="${y0 - HUECO}" `
                 + `y2="${y0 - HUECO}"/>`);
    }
    const e = escala(v, zona, y0);
    escalas.push(e.y);
    for (const g of e.guias) {
      const py = e.y(g);
      if (py < y0 + 2 || py > y0 + zona.alto + 0.5) continue;
      lista.push(`<line class="vs-guia" x1="${IZQUIERDA}" x2="${ancho - DERECHA}" y1="${py}" y2="${py}"/>`,
                 `<text class="vs-valor-eje" x="${IZQUIERDA - 5}" y="${py + 3.5}">${numero(g, e.decimales)}${e.sufijo}</text>`);
    }
    for (const capa of zona.capas) lista.push(CAPAS[capa.tipo](v, capa, e));
    y0 += zona.alto + HUECO;
  });
  v.escalas[p.id] = escalas;
  const circulos = p.zonas.flatMap((zona, k) => zona.capas.filter(c => c.cursor)
    .map(c => `<circle data-serie="${c.serie}" data-zona="${k}" r="4" fill="${c.color}"/>`));
  lista.push(`<g class="vs-cursor"><line y1="0" y2="${alto}"/>${circulos.join("")}</g>`);
  return lista.join("");
}

// Eje de tiempo: hora a hora, el nombre de cada día en medio de su tramo y las 12 h; día a día, los días que quepan;
// con meses, el nombre de cada mes. Y el momento del cursor
function dibujarEje(v) {
  const {x, h0, h1, paso} = v.ejes, {d} = v, {horas, tz} = d, lista = [];
  const texto = (px, contenido) => `<text class="vs-dia-texto" x="${px}" y="16">${contenido}</text>`;
  if (d.modo === "hora" || d.eje === "meses") {
    const tramos = [h0, ...v.cortes, h1], minimo = d.modo === "hora" ? 42 : 24;
    tramos.slice(0, -1).forEach((a, k) => {
      const b = tramos[k + 1];
      if (x(b) - x(a) > minimo) lista.push(texto((x(a) + x(b)) / 2, d.modo === "hora" ? diaCorto(a, tz) : mesCorto(a, tz)));
    });
    if (d.modo === "hora") {
      for (const h of horas) {
        if (horaLocal(h, tz) === 12) lista.push(`<line class="vs-dia" x1="${x(h)}" x2="${x(h)}" y1="0" y2="4"/>`);
      }
    }
  } else {
    const cada = Math.ceil(40 / paso);
    horas.forEach((h, i) => { if (i % cada === 0) lista.push(texto(xi(v, i), nombreDia(h, tz))); });
  }
  lista.push('<g class="vs-eje-cursor"><rect y="1" height="18" rx="6"/><text y="14"></text></g>');
  return lista.join("");
}

// ---------------------------------------------------------------- Cursor y lecturas

function etiquetaEje(v, h) {
  const {modo, eje, tz} = v.d;
  if (modo === "hora") return `${diaCorto(h, tz)} · ${String(horaLocal(h, tz)).padStart(2, "0")} h`;
  return eje === "meses" ? formato(tz, {day: "numeric", month: "short"}).format(h).replace(".", "") : nombreDia(h, tz);
}

function irA(v, t) {
  v.t = t;
  const {d, raiz} = v;
  if (!d) return;
  const h = d.horas[t], cuando = relativa(v, h);
  raiz.querySelector(".vs-hora").innerHTML = `${fecha(v, h)}${cuando ? `<small>${cuando}</small>` : ""}`;
  lecturas(v);
  if (!v.ejes) return;
  const px = xi(v, t);
  for (const seccion of raiz.querySelectorAll(".vs-panel")) {
    const g = seccion.querySelector(".vs-cursor"), escalas = v.escalas[seccion.dataset.id];
    if (!g || !escalas) continue;
    g.setAttribute("transform", `translate(${px},0)`);
    for (const circulo of g.querySelectorAll("circle")) {
      const val = d.series[circulo.dataset.serie]?.[t];
      circulo.style.display = valido(val) ? "" : "none";
      if (valido(val)) circulo.setAttribute("cy", escalas[+circulo.dataset.zona](val));
    }
  }
  for (const eje of raiz.querySelectorAll(".vs-eje")) {
    const g = eje.querySelector(".vs-eje-cursor");
    if (!g) continue;
    const texto = g.querySelector("text"), rect = g.querySelector("rect");
    texto.textContent = etiquetaEje(v, h);
    const w = texto.getComputedTextLength() + 14;
    const centro = Math.min(v.ejes.ancho - DERECHA - w / 2, Math.max(IZQUIERDA + w / 2, px));
    rect.setAttribute("x", centro - w / 2);
    rect.setAttribute("width", w);
    texto.setAttribute("x", centro);
    // Los nombres de días o meses que quedan debajo del momento del cursor se esconden
    for (const dia of eje.querySelectorAll(".vs-dia-texto")) {
      dia.style.visibility = Math.abs(+dia.getAttribute("x") - centro) < w / 2 + 20 ? "hidden" : "";
    }
  }
}

// Cada lectura es [plantilla, serie o series, decimales (uno o uno por serie)]: cada {} de la plantilla se cambia por
// el valor de su serie en ese momento (los números, con coma decimal) y, si falta alguno, la lectura no sale
function rellenar(d, [plantilla, nombres, decimales], t) {
  const valores = [nombres].flat().map(n => d.series[n]?.[t]);
  if (!valores.every(valido)) return null;
  let k = 0;
  return plantilla.replace(/\{\}/g, () => {
    const val = valores[k], dec = Array.isArray(decimales) ? decimales[k] : decimales;
    k++;
    return typeof val === "number" ? numero(val, dec ?? 0) : val;
  });
}

function lecturas(v) {
  const {d, raiz, t} = v;
  for (const seccion of raiz.querySelectorAll(".vs-panel")) {
    const textos = (v.paneles[seccion.dataset.id].lectura ?? []).map(l => rellenar(d, l, t)).filter(Boolean);
    // Cada dato, entero en su línea: el color de una serie no se separa de su nombre
    seccion.querySelector(".vs-lectura span").innerHTML = textos.length
      ? textos.map(texto => `<span class="vs-dato">${texto}</span>`).join(" · ") : "sin dato";
  }
}

// ---------------------------------------------------------------- Streamlit

export default function (component) {
  const {data, parentElement} = component;
  const raiz = parentElement.querySelector(".visor");
  const v = raiz._visor ??= crear(raiz);
  if (v.clave === data.clave) return;  // los mismos datos: Streamlit ha recargado la página por otra cosa
  v.clave = data.clave;
  cargar(v, data);
}
