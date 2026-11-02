// Probabilidad de ver auroras hora a hora (ver horas_auroras.py): probabilidad, Kp y nubosidad apilados, con las noches
// sombreadas y un solo cursor. Como en el meteograma, el ratón muestra la hora al pasar y pulsar la fija; el dedo, las
// flechas y «Ahora» también la fijan. Encima de cada panel salen los valores de esa hora y, arriba, sus seis factores.

const IZQUIERDA = 36, DERECHA = 8;
const ALTOS = {prob: 170, kp: 120, nubes: 110};
const AURORA = "#34d399";
let contador = 0;  // para que los degradados y tramas de varios visores no compartan identificador

const numero = (v, decimales) => v.toLocaleString("es-ES", {minimumFractionDigits: decimales,
                                                             maximumFractionDigits: decimales});
const valido = (v) => v !== null && v !== undefined && !Number.isNaN(v);
// Los colores de los factores de las tarjetas de las noches
const colorFactor = (v) => v >= 0.7 ? "#34d399" : v >= 0.4 ? "#fbbf24" : "#f87171";

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

// ---------------------------------------------------------------- Estructura

function fijar(a, t) {
  a.fijo = t;
  irA(a, t);
}

function crear(raiz) {
  const a = {raiz, t: 0, fijo: 0, id: `ha${++contador}`};
  raiz.addEventListener("keydown", (e) => {
    if (!a.d || e.ctrlKey || e.metaKey || e.altKey) return;
    const ultimo = a.d.horas.length - 1;
    const destino = {ArrowLeft: a.fijo - 1, ArrowRight: a.fijo + 1, PageUp: a.fijo - 6, PageDown: a.fijo + 6, Home: 0,
                     End: ultimo}[e.key];
    if (destino === undefined) return;
    e.preventDefault();
    fijar(a, Math.min(ultimo, Math.max(0, destino)));
  });
  raiz.addEventListener("pointerleave", (e) => { if (a.d && e.pointerType === "mouse") irA(a, a.fijo); });
  new ResizeObserver(() => dibujarTodo(a)).observe(raiz);
  return a;
}

const panel = (id, titulo) => `<section class="ha-panel" data-id="${id}"><div class="ha-lectura"><b>${titulo}</b>`
  + `<span></span></div><svg class="ha-svg"></svg></section>`;

// La hora más cercana a ahora
function indiceAhora(d) {
  const i = d.horas.findIndex(h => h >= Date.now() - 18e5);
  return i < 0 ? d.horas.length - 1 : i;
}

function cargar(a, d) {
  const hora = a.d ? a.d.horas[a.fijo] : null;
  a.d = d;
  const t = d.horas.indexOf(hora);
  a.t = a.fijo = t < 0 ? indiceAhora(d) : t;
  a.raiz.innerHTML = '<div class="ha-cabecera"><div class="ha-hora"></div><button class="ha-ahora">Ahora</button></div>'
    + '<div class="ha-factores"></div>' + panel("prob", "Probabilidad de verlas") + panel("kp", "Kp")
    + panel("nubes", "Nubes") + '<svg class="ha-eje"></svg>';
  a.raiz.querySelector(".ha-ahora").onclick = () => fijar(a, indiceAhora(d));
  for (const svg of a.raiz.querySelectorAll("svg")) enlazar(a, svg);
  dibujarTodo(a);
}

// Ratón: el cursor sigue al puntero y pulsar fija la hora. Dedo: tocar o arrastrar en horizontal la fija
function enlazar(a, svg) {
  let arrastrando = false;
  const indice = (e) => {
    const {h0, h1, ancho} = a.ejes, x = e.clientX - svg.getBoundingClientRect().left;
    const instante = h0 + (x - IZQUIERDA) / (ancho - IZQUIERDA - DERECHA) * (h1 - h0);
    let mejor = 0;
    a.d.horas.forEach((h, i) => { if (Math.abs(h + 18e5 - instante) < Math.abs(a.d.horas[mejor] + 18e5 - instante)) mejor = i; });
    return mejor;
  };
  svg.addEventListener("pointerdown", (e) => {
    if (!a.ejes) return;
    if (e.pointerType !== "mouse") {
      arrastrando = true;
      svg.setPointerCapture(e.pointerId);
    }
    fijar(a, indice(e));
  });
  svg.addEventListener("pointermove", (e) => {
    if (!a.ejes || (e.pointerType !== "mouse" && !arrastrando)) return;
    const i = indice(e);
    if (arrastrando) {
      if (i !== a.fijo) fijar(a, i);
    } else if (i !== a.t) {
      irA(a, i);
    }
  });
  for (const evento of ["pointerup", "pointercancel"]) svg.addEventListener(evento, () => { arrastrando = false; });
}

// ---------------------------------------------------------------- Dibujo

function dibujarTodo(a) {
  const {d, raiz} = a;
  const primero = raiz.querySelector(".ha-svg");
  if (!d || !primero || !primero.clientWidth) return;
  // Cada hora ocupa su tramo [h, h + 1 h): el eje va hasta el final de la última
  const ancho = primero.clientWidth, h0 = d.horas[0], h1 = d.horas.at(-1) + 36e5;
  a.ejes = {h0, h1, ancho, x: (t) => IZQUIERDA + (t - h0) / (h1 - h0) * (ancho - IZQUIERDA - DERECHA)};
  a.escalas = {};
  for (const seccion of raiz.querySelectorAll(".ha-panel")) {
    const id = seccion.dataset.id, svg = seccion.querySelector("svg");
    svg.style.height = `${ALTOS[id]}px`;
    svg.innerHTML = {prob: dibujarProb, kp: dibujarKp, nubes: dibujarNubes}[id](a, ALTOS[id]);
  }
  raiz.querySelector(".ha-eje").innerHTML = dibujarEje(a);
  irA(a, a.t);
}

// Lo común: noches, medianoches, rejilla horizontal con sus valores y la línea de ahora
function fondo(a, alto, y, guias, sufijo = "") {
  const {x, ancho, h0, h1} = a.ejes, {d} = a, partes = [];
  // Cada noche, un solo rectángulo (uno por hora deja rayas finas entre ellos)
  let inicio = null;
  d.horas.forEach((h, i) => {
    if (d.oscuro[i] && inicio === null) inicio = h;
    if (inicio !== null && (!d.oscuro[i + 1] || i === d.horas.length - 1)) {
      partes.push(`<rect class="ha-noche" x="${x(inicio)}" y="0" width="${x(h + 36e5) - x(inicio)}" height="${alto}"/>`);
      inicio = null;
    }
    if (i && horaLocal(h, d.tz) === 0) partes.push(`<line class="ha-dia" x1="${x(h)}" x2="${x(h)}" y1="0" y2="${alto}"/>`);
  });
  for (const v of guias) {
    partes.push(`<line class="ha-guia" x1="${IZQUIERDA}" x2="${ancho - DERECHA}" y1="${y(v)}" y2="${y(v)}"/>`,
                `<text class="ha-valor-eje" x="${IZQUIERDA - 5}" y="${y(v) + 3.5}">${v}${sufijo}</text>`);
  }
  const ahora = Date.now();
  if (ahora > h0 && ahora < h1) partes.push(`<line class="ha-ahora-linea" x1="${x(ahora)}" x2="${x(ahora)}" y1="0" y2="${alto}"/>`);
  return partes;
}

// Línea por el centro de cada hora (con huecos donde faltan); con `base`, cerrada como área
function trazo(a, valores, y, base = null) {
  let d = "", tramo = [];
  const cerrar = () => {
    if (tramo.length > 1) {
      d += tramo.map(([px, py], k) => `${k ? "L" : "M"}${px.toFixed(1)},${py.toFixed(1)}`).join("");
      if (base !== null) d += `L${tramo.at(-1)[0].toFixed(1)},${base}L${tramo[0][0].toFixed(1)},${base}Z`;
    }
    tramo = [];
  };
  valores.forEach((v, i) => valido(v) ? tramo.push([a.ejes.x(a.d.horas[i] + 18e5), y(v)]) : cerrar());
  cerrar();
  return d;
}

const cursor = (alto, color) => `<g class="ha-cursor"><line y1="0" y2="${alto}"/>`
  + (color ? `<circle r="4" fill="${color}"/>` : "") + "</g>";

function dibujarProb(a, alto) {
  const y = (p) => 6 + (1 - p / 100) * (alto - 8);
  a.escalas.prob = y;
  const partes = fondo(a, alto, y, [50, 100], " %");
  partes.push(`<linearGradient id="${a.id}-prob" x1="0" y1="1" x2="0" y2="0">`
              + '<stop offset="0" stop-color="rgba(45, 212, 191, 0.04)"/>'
              + '<stop offset="0.5" stop-color="rgba(52, 211, 153, 0.35)"/>'
              + '<stop offset="1" stop-color="rgba(232, 121, 249, 0.6)"/></linearGradient>',
              `<path d="${trazo(a, a.d.prob, y, y(0))}" fill="url(#${a.id}-prob)"/>`,
              `<path d="${trazo(a, a.d.prob, y)}" fill="none" stroke="${AURORA}" stroke-width="2" stroke-linejoin="round"/>`,
              cursor(alto, AURORA));
  return partes.join("");
}

function dibujarKp(a, alto) {
  const {d} = a, {x} = a.ejes, y = (k) => 6 + (1 - k / d.kp_max) * (alto - 8);
  a.escalas.kp = y;
  const guias = [], paso = d.kp_max <= 6 ? 1 : 3;  // con un Kp máximo bajo, cada unidad
  for (let k = paso; k <= d.kp_max; k += paso) guias.push(k);
  const partes = fondo(a, alto, y, guias);
  // Rayado para el previsto (el observado y el estimado, lisos); punteado y tenue para la previsión a 27 días
  partes.push(`<pattern id="${a.id}-rayas" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">`
              + '<line x1="0" y1="0" x2="0" y2="6" stroke="rgba(7, 11, 24, 0.45)" stroke-width="2.5"/></pattern>',
              `<pattern id="${a.id}-puntos" width="6" height="6" patternUnits="userSpaceOnUse">`
              + '<circle cx="3" cy="3" r="1.1" fill="rgba(7, 11, 24, 0.45)"/></pattern>');
  for (const [inicio, fin, valor, color] of d.kp27) {
    const x0 = Math.max(x(inicio), IZQUIERDA), x1 = Math.min(x(fin), a.ejes.ancho - DERECHA), w = (x1 - x0) * 0.98;
    if (w <= 0) continue;
    partes.push(`<g opacity="0.3"><rect x="${x0}" y="${y(valor)}" width="${w}" height="${y(0) - y(valor)}" fill="${color}"/>`
                + `<rect x="${x0}" y="${y(valor)}" width="${w}" height="${y(0) - y(valor)}" fill="url(#${a.id}-puntos)"/></g>`);
  }
  for (const [inicio, valor, tipo, color] of d.kp) {
    const x0 = Math.max(x(inicio), IZQUIERDA), x1 = Math.min(x(inicio + 3 * 36e5), a.ejes.ancho - DERECHA);
    const w = (x1 - x0) * 0.9;
    if (w <= 0) continue;
    partes.push(`<rect x="${x0}" y="${y(valor)}" width="${w}" height="${y(0) - y(valor)}" fill="${color}"/>`);
    if (tipo === "previsto") {
      partes.push(`<rect x="${x0}" y="${y(valor)}" width="${w}" height="${y(0) - y(valor)}" fill="url(#${a.id}-rayas)"/>`);
    }
  }
  partes.push(`<line class="ha-umbral" x1="${IZQUIERDA}" x2="${a.ejes.ancho - DERECHA}" y1="${y(d.umbral)}" y2="${y(d.umbral)}"/>`,
              `<text class="ha-umbral-texto" x="${IZQUIERDA + 4}" y="${y(d.umbral) - 4}">Kp ${d.umbral}</text>`,
              cursor(alto, null));
  return partes.join("");
}

function dibujarNubes(a, alto) {
  const {p50, p10, p90} = a.d.nubes, y = (n) => 6 + (1 - n / 100) * (alto - 8);
  a.escalas.nubes = y;
  const partes = fondo(a, alto, y, [50, 100], " %");
  if (p10) {
    // Rango 10-90 %: ida por el 90 y vuelta por el 10
    const ida = trazo(a, p90, y), vuelta = [];
    p10.forEach((v, i) => valido(v) && vuelta.push(`L${a.ejes.x(a.d.horas[i] + 18e5).toFixed(1)},${y(v).toFixed(1)}`));
    if (ida) partes.push(`<path d="${ida}${vuelta.reverse().join("")}Z" fill="rgba(148, 163, 184, 0.2)"/>`);
  } else {
    partes.push(`<path d="${trazo(a, p50, y, y(0))}" fill="rgba(148, 163, 184, 0.2)"/>`);
  }
  partes.push(`<path d="${trazo(a, p50, y)}" fill="none" stroke="#e2e8f0" stroke-width="1.5"/>`, cursor(alto, "#e2e8f0"));
  return partes.join("");
}

// Eje de tiempo: el nombre de cada día en medio de su tramo y la hora del cursor
function dibujarEje(a) {
  const {x, h1} = a.ejes, {horas, tz} = a.d, partes = [];
  const cortes = [horas[0], ...horas.filter((h, i) => i && horaLocal(h, tz) === 0), h1];
  cortes.slice(0, -1).forEach((inicio, k) => {
    const fin = cortes[k + 1];
    if (x(fin) - x(inicio) > 42) {
      partes.push(`<text class="ha-dia-texto" x="${(x(inicio) + x(fin)) / 2}" y="16">${diaCorto(inicio, tz)}</text>`);
    }
  });
  partes.push('<g class="ha-eje-cursor"><rect y="1" height="18" rx="6"/><text y="14"></text></g>');
  return partes.join("");
}

// ---------------------------------------------------------------- Cursor y lecturas

function irA(a, t) {
  a.t = t;
  const {d, raiz} = a, h = d.horas[t];
  raiz.querySelector(".ha-hora").innerHTML = `${fechaLarga(h, d.tz)}<small>${relativa(h)}</small>`;
  lecturas(a);
  if (!a.ejes) return;
  const px = a.ejes.x(h + 18e5), valores = {prob: d.prob[t], kp: null, nubes: d.nubes.p50[t]};
  for (const seccion of raiz.querySelectorAll(".ha-panel")) {
    const id = seccion.dataset.id, g = seccion.querySelector(".ha-cursor"), circulo = g?.querySelector("circle");
    if (!g) continue;
    g.setAttribute("transform", `translate(${px},0)`);
    if (circulo) {
      circulo.style.display = valido(valores[id]) ? "" : "none";
      if (valido(valores[id])) circulo.setAttribute("cy", a.escalas[id](valores[id]));
    }
  }
  const eje = raiz.querySelector(".ha-eje"), g = eje.querySelector(".ha-eje-cursor");
  const texto = g.querySelector("text"), rect = g.querySelector("rect");
  texto.textContent = `${diaCorto(h, d.tz)} · ${String(horaLocal(h, d.tz)).padStart(2, "0")} h`;
  const w = texto.getComputedTextLength() + 14;
  const centro = Math.min(a.ejes.ancho - DERECHA - w / 2, Math.max(IZQUIERDA + w / 2, px));
  rect.setAttribute("x", centro - w / 2);
  rect.setAttribute("width", w);
  texto.setAttribute("x", centro);
  for (const dia of eje.querySelectorAll(".ha-dia-texto")) {
    dia.style.visibility = Math.abs(+dia.getAttribute("x") - centro) < w / 2 + 24 ? "hidden" : "";
  }
}

function lecturas(a) {
  const {d, raiz, t} = a, h = d.horas[t], tz = d.tz, partes = {};

  // Probabilidad y el factor que más resta a esa hora
  const factores = d.factores.filter(([, , valores]) => valido(valores[t]));
  const peor = factores.reduce((m, f) => !m || f[2][t] < m[2][t] ? f : m, null);
  partes.prob = !d.oscuro[t] ? ["sin oscuridad: el sol está demasiado alto"]
    : !valido(d.prob[t]) ? ["sin datos"]
    : [`<b>${d.prob[t]} %</b>`, peor && peor[2][t] < 0.95 && `lo que más resta: ${peor[1]}`];

  // Kp: el bloque de 3 h de esa hora o, si no hay, el día de la previsión a 27 días
  const bloque = d.kp.find(([inicio]) => h >= inicio && h < inicio + 3 * 36e5);
  const dia = d.kp27.find(([inicio, fin]) => h >= inicio && h < fin);
  if (bloque) {
    const [inicio, valor, tipo, , texto] = bloque;
    const hasta = String(horaLocal(inicio + 3 * 36e5, tz)).padStart(2, "0");
    partes.kp = [`<b>${numero(valor, 1)}</b>`, `${tipo}, de ${String(horaLocal(inicio, tz)).padStart(2, "0")} a ${hasta} h`,
                 texto.toLowerCase()];
  } else if (dia) {
    partes.kp = [`<b>${numero(dia[2], 0)}</b> de máximo en el día`, "previsión a 27 días", dia[4].toLowerCase()];
  } else {
    partes.kp = ["sin datos"];
  }

  const {p50, p10, p90} = d.nubes;
  partes.nubes = valido(p50[t]) ? [`<b>${p50[t]} %</b>`, p10 && valido(p10[t]) && `10-90 %: ${p10[t]} a ${p90[t]} %`]
    : ["sin datos"];

  for (const seccion of raiz.querySelectorAll(".ha-panel")) {
    seccion.querySelector(".ha-lectura span").innerHTML = partes[seccion.dataset.id].filter(Boolean).join(" · ");
  }
  raiz.querySelector(".ha-factores").innerHTML = d.factores.map(([nombre, , valores]) => {
    const v = valores[t];
    return valido(v) ? `<span><i style="background:${colorFactor(v)}"></i>${nombre} <b>${Math.round(10 * v)}</b></span>`
      : `<span><i></i>${nombre} <b>–</b></span>`;
  }).join("");
}

// ---------------------------------------------------------------- Streamlit

export default function (component) {
  const {data, parentElement} = component;
  const raiz = parentElement.querySelector(".horas-auroras");
  const a = raiz._auroras ??= crear(raiz);
  if (a.clave === data.clave) return;  // los mismos datos: Streamlit ha recargado la página por otra cosa
  a.clave = data.clave;
  cargar(a, data);
}
