// Meteograma de las 48 h (ver meteograma.py): paneles apilados de temperatura, lluvia, rachas y, si los hay, presión y
// MUCAPE, con un solo cursor. El ratón, el dedo (arrastrando en horizontal) o las flechas lo mueven en el navegador, sin
// recargar Streamlit, y encima de cada panel salen los valores de esa hora.

const IZQUIERDA = 36, DERECHA = 8;  // márgenes del dibujo: a la izquierda, los valores del eje
const ARRIBA = 16;  // hueco sobre las curvas para las etiquetas de los máximos

const PANELES = {
  temperatura: {titulo: "Temperatura", unidad: "°C", decimales: 1, alto: 260, paso: 1,
                miembros: "rgba(99, 91, 83, 0.22)", media: "#635b53", control: "#d97706"},
  rachas: {titulo: "Rachas", unidad: "km/h", decimales: 0, alto: 160, paso: 5,
           miembros: "rgba(217, 119, 6, 0.22)", media: "#b45309", control: "#d97706"},
  presion: {titulo: "Presión", unidad: "hPa", decimales: 1, alto: 150, paso: 1,
            miembros: "rgba(99, 91, 83, 0.22)", media: "#635b53", control: "#d97706"},
  mucape: {titulo: "Potencial de tormentas (MUCAPE)", unidad: "J/kg", decimales: 0, alto: 150, paso: 100,
           miembros: "rgba(225, 29, 72, 0.2)", media: "#d97706", control: "#d93856"},
};
const ALTO_LLUVIA = 110, ALTO_PROBABILIDAD = 70, HUECO_LLUVIA = 10;  // 190 px entre los dos
const ROJO = "#d93856", AZUL = "#0277bd", TEXTO = "#2a241f";
// Zonas de riesgo del MUCAPE, muy sutiles
const ZONAS_CAPE = [[0, 300, "#10b981"], [300, 1000, "#fbbf24"], [1000, 3000, "#ef4444"]];
const RAD = Math.PI / 180;

const numero = (v, decimales) => v.toLocaleString("es-ES", {minimumFractionDigits: decimales,
                                                             maximumFractionDigits: decimales});
const valido = (v) => v !== null && v !== undefined && !Number.isNaN(v);

// Marcas redondas del eje (×1, 2, 2,5 o 5 por potencia de 10), unas `n`
function marcas(min, max, n) {
  const bruto = (max - min) / n, potencia = 10 ** Math.floor(Math.log10(bruto));
  const paso = [1, 2, 2.5, 5, 10].map(m => m * potencia).find(p => p >= bruto);
  const lista = [];
  for (let v = Math.ceil(min / paso) * paso; v <= max + 1e-9; v += paso) lista.push(+v.toFixed(6) + 0);
  return {lista, decimales: paso < 1 ? 1 : 0};
}

// ---------------------------------------------------------------- Fechas y sol

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

// Tramos [inicio, fin] de noche en el lugar, cada 10 min
function noches(d) {
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

// ---------------------------------------------------------------- Estructura

// El cursor marca la hora fijada (al empezar, la de ahora). Con el ratón, pasar por encima la muestra sin fijarla, como
// el hover de un gráfico, y al salir vuelve a la fijada; pulsar la fija. El dedo, las flechas y «Ahora» también la fijan
function fijar(m, t) {
  m.fijo = t;
  irA(m, t);
}

function crear(raiz) {
  const m = {raiz, t: 0, fijo: 0};
  raiz.addEventListener("keydown", (e) => {
    if (!m.d || e.ctrlKey || e.metaKey || e.altKey) return;
    const ultimo = m.d.horas.length - 1;
    const destino = {ArrowLeft: m.fijo - 1, ArrowRight: m.fijo + 1, PageUp: m.fijo - 6, PageDown: m.fijo + 6, Home: 0,
                     End: ultimo}[e.key];
    if (destino === undefined) return;
    e.preventDefault();
    fijar(m, Math.min(ultimo, Math.max(0, destino)));
  });
  raiz.addEventListener("pointerleave", (e) => { if (m.d && e.pointerType === "mouse") irA(m, m.fijo); });
  new ResizeObserver(() => dibujarTodo(m)).observe(raiz);
  return m;
}

const panel = (id, titulo) => `<section class="mg-panel" data-id="${id}"><div class="mg-lectura"><b>${titulo}</b>`
  + `<span></span></div><svg class="mg-svg"></svg></section>`;

function construir(m) {
  const {d, raiz} = m;
  const leyenda = [["mg-l-media", "media"], ...(d.temperatura.control ? [["mg-l-control", "control"]] : []),
                   ["mg-l-miembros", "miembros"],
                   ...(d.temperatura.observado || d.rachas.observado ? [["mg-l-observado", "observado"]] : []),
                   ...(d.temperatura.bandas ? [["mg-l-max", "máx. habitual"], ["mg-l-min", "mín. habitual"]] : [])];
  let html = '<div class="mg-cabecera"><div class="mg-hora"></div><button class="mg-ahora">Ahora</button></div>'
    + `<div class="mg-leyenda">${leyenda.map(([clase, texto]) => `<span><i class="${clase}"></i>${texto}</span>`)
      .join("")}</div>`
    + panel("temperatura", "Temperatura") + panel("lluvia", "Lluvia") + panel("rachas", "Rachas")
    + '<svg class="mg-eje"></svg>';
  if (d.presion) {
    html += `<button class="mg-plegable" aria-expanded="false"><span class="mg-flecha">▸</span>Presión y tormentas`
      + `${d.tormenta ? '<em>potencial de tormenta</em>' : ""}</button>`
      + `<div class="mg-grupo">${panel("presion", "Presión")}${panel("mucape", "MUCAPE")}<svg class="mg-eje"></svg></div>`;
  }
  raiz.innerHTML = html;
  raiz.querySelector(".mg-ahora").onclick = () => fijar(m, indiceAhora(d));
  const plegable = raiz.querySelector(".mg-plegable");
  if (plegable) {
    const aplicar = () => {
      plegable.setAttribute("aria-expanded", m.desplegado);
      raiz.querySelector(".mg-grupo").hidden = !m.desplegado;
    };
    plegable.onclick = () => {
      m.desplegado = !m.desplegado;
      aplicar();
      dibujarTodo(m);
    };
    aplicar();
  }
  for (const svg of raiz.querySelectorAll(".mg-svg, .mg-eje")) enlazar(m, svg);
}

// Ratón: el cursor sigue al puntero y pulsar fija la hora. Dedo: tocar o arrastrar en horizontal la fija (en vertical,
// la página se desplaza)
function enlazar(m, svg) {
  let arrastrando = false;
  const indice = (e) => {
    const {h0, h1, ancho} = m.ejes, x = e.clientX - svg.getBoundingClientRect().left;
    const instante = h0 + (x - IZQUIERDA) / (ancho - IZQUIERDA - DERECHA) * (h1 - h0);
    let mejor = 0;
    m.d.horas.forEach((h, i) => { if (Math.abs(h - instante) < Math.abs(m.d.horas[mejor] - instante)) mejor = i; });
    return mejor;
  };
  svg.addEventListener("pointerdown", (e) => {
    if (!m.ejes) return;
    if (e.pointerType !== "mouse") {
      arrastrando = true;
      svg.setPointerCapture(e.pointerId);
    }
    fijar(m, indice(e));
  });
  svg.addEventListener("pointermove", (e) => {
    if (!m.ejes || (e.pointerType !== "mouse" && !arrastrando)) return;
    const i = indice(e);
    if (arrastrando) {
      if (i !== m.fijo) fijar(m, i);
    } else if (i !== m.t) {
      irA(m, i);
    }
  });
  for (const evento of ["pointerup", "pointercancel"]) svg.addEventListener(evento, () => { arrastrando = false; });
}

// La hora más cercana a ahora (a las 20:47, las 21:00)
function indiceAhora(d) {
  const i = d.horas.findIndex(h => h >= Date.now() - 18e5);
  return i < 0 ? d.horas.length - 1 : i;
}

function cargar(m, d) {
  const hora = m.d ? m.d.horas[m.fijo] : null;
  m.d = d;
  m.noches = noches(d);
  m.desplegado ??= Boolean(d.tormenta);
  const t = d.horas.indexOf(hora);
  m.t = m.fijo = t < 0 ? indiceAhora(d) : t;
  construir(m);
  dibujarTodo(m);
}

// ---------------------------------------------------------------- Dibujo

function dibujarTodo(m) {
  const {d, raiz} = m;
  if (!d) return;
  const ancho = raiz.querySelector(".mg-svg").clientWidth;
  if (!ancho) return;
  const h0 = d.horas[0], h1 = d.horas.at(-1);
  m.ejes = {h0, h1, ancho, x: (t) => IZQUIERDA + (t - h0) / (h1 - h0) * (ancho - IZQUIERDA - DERECHA)};
  m.escalas = {};
  for (const seccion of raiz.querySelectorAll(".mg-panel")) {
    if (seccion.closest("[hidden]")) continue;
    const id = seccion.dataset.id, svg = seccion.querySelector("svg");
    svg.innerHTML = id === "lluvia" ? dibujarLluvia(m, svg) : dibujarEnsemble(m, id, svg);
  }
  for (const eje of raiz.querySelectorAll(".mg-eje")) if (!eje.closest("[hidden]")) eje.innerHTML = dibujarEje(m, eje);
  irA(m, m.t);
}

// Lo común a todos los paneles: noches, medianoches, rejilla horizontal con sus valores y la línea de ahora
function fondo(m, alto, y, guias, decimales, abajo = alto) {
  const {x, ancho} = m.ejes, partes = [];
  for (const [a, b] of m.noches) partes.push(`<rect class="mg-noche" x="${x(a)}" y="0" width="${x(b) - x(a)}" height="${alto}"/>`);
  for (const h of m.d.horas) {
    if (h > m.ejes.h0 && horaLocal(h, m.d.tz) === 0) partes.push(`<line class="mg-dia" x1="${x(h)}" x2="${x(h)}" y1="0" y2="${alto}"/>`);
  }
  for (const v of guias) {
    if (y(v) < 2 || y(v) > abajo + 0.5) continue;
    partes.push(`<line class="mg-guia" x1="${IZQUIERDA}" x2="${ancho - DERECHA}" y1="${y(v)}" y2="${y(v)}"/>`,
                `<text class="mg-valor-eje" x="${IZQUIERDA - 5}" y="${y(v) + 3.5}">${numero(v, decimales)}</text>`);
  }
  const ahora = Date.now();
  if (ahora > m.ejes.h0 && ahora < m.ejes.h1) {
    partes.push(`<line class="mg-ahora-linea" x1="${x(ahora)}" x2="${x(ahora)}" y1="0" y2="${alto}"/>`);
  }
  return partes;
}

// Línea por los valores (con huecos donde faltan); `cerrar` la baja hasta `base` para hacer un área
function trazo(m, valores, y, base = null) {
  let d = "", tramo = [];
  const cerrar = () => {
    if (tramo.length > 1) {
      d += tramo.map(([px, py], k) => `${k ? "L" : "M"}${px.toFixed(1)},${py.toFixed(1)}`).join("");
      if (base !== null) d += `L${tramo.at(-1)[0].toFixed(1)},${base}L${tramo[0][0].toFixed(1)},${base}Z`;
    }
    tramo = [];
  };
  valores.forEach((v, i) => valido(v) ? tramo.push([m.ejes.x(m.d.horas[i]), y(v)]) : cerrar());
  cerrar();
  return d;
}

function cursor(alto, puntos) {
  return `<g class="mg-cursor"><line y1="0" y2="${alto}"/>${puntos.map(([clase, color]) =>
    `<circle class="${clase}" r="4" fill="${color}"/>`).join("")}</g>`;
}

function dibujarEnsemble(m, id, svg) {
  const cfg = PANELES[id], s = m.d[id], alto = cfg.alto;
  svg.style.height = `${alto}px`;
  const series = [...s.miembros, s.control ?? [], s.observado ?? [], s.media];
  const valores = series.flat().filter(valido);
  let min = valores.length ? Math.min(...valores) : 0, max = valores.length ? Math.max(...valores) : 1;
  for (const [bajo, alto_] of Object.values(s.bandas ?? {})) {
    min = Math.min(min, bajo);
    max = Math.max(max, alto_);
  }
  if (s.rango) {
    [min, max] = s.rango;
  } else {
    const margen = Math.max(max - min, cfg.paso * 2) * 0.08;
    min -= margen;
    max += margen;
    if (id === "rachas" || id === "mucape") min = Math.max(0, min);
  }
  const abajo = alto - 4, y = (v) => ARRIBA + (1 - (v - min) / (max - min)) * (abajo - ARRIBA);
  m.escalas[id] = y;
  const {lista, decimales} = marcas(min, max, alto > 120 ? 4 : 3);
  const partes = fondo(m, alto, y, lista, decimales, abajo);
  const {x, ancho} = m.ejes, ancho_ = ancho - IZQUIERDA - DERECHA;
  if (id === "mucape") {
    for (const [a, b, color] of ZONAS_CAPE) {
      if (a >= max) continue;
      partes.unshift(`<rect x="${IZQUIERDA}" y="${y(Math.min(b, max))}" width="${ancho_}" `
                     + `height="${y(a) - y(Math.min(b, max))}" fill="${color}" opacity="0.06"/>`);
    }
  }
  for (const [clase, [bajo, alto_]] of Object.entries(s.bandas ?? {})) {
    partes.unshift(`<rect class="mg-banda-${clase}" x="${IZQUIERDA}" y="${y(alto_)}" width="${ancho_}" `
                   + `height="${y(bajo) - y(alto_)}"/>`);
  }
  partes.push(`<path d="${s.miembros.map(serie => trazo(m, serie, y)).join("")}" fill="none" stroke="${cfg.miembros}" `
              + `stroke-width="1"/>`);
  partes.push(`<path d="${trazo(m, s.media, y)}" fill="none" stroke="${cfg.media}" stroke-width="1.8" `
              + `stroke-dasharray="2 3"/>`);
  if (s.control) {
    partes.push(`<path d="${trazo(m, s.control, y)}" fill="none" stroke="${cfg.control}" stroke-width="2.2" `
                + `stroke-dasharray="6 4"/>`);
  }
  if (s.observado) {
    partes.push(`<path d="${trazo(m, s.observado, y)}" fill="none" stroke="${TEXTO}" stroke-width="2.8" `
                + `stroke-linejoin="round"/>`);
  }
  for (const [t, valor, tipo] of s.extremos ?? []) {
    const py = tipo === "max" ? Math.max(11, y(valor) - 7) : Math.min(alto - 2, y(valor) + 14);
    const px = Math.min(ancho - DERECHA - 14, Math.max(IZQUIERDA + 14, x(t)));
    partes.push(`<text class="mg-extremo" x="${px}" y="${py}" fill="${tipo === "max" ? ROJO : AZUL}">`
                + `${numero(valor, cfg.decimales)}${id === "temperatura" ? "°" : ""}</text>`);
  }
  partes.push(cursor(alto, [["media", cfg.media], ...(s.observado ? [["observado", TEXTO]] : [])]));
  return partes.join("");
}

function dibujarLluvia(m, svg) {
  const s = m.d.lluvia, alto = ALTO_LLUVIA + HUECO_LLUVIA + ALTO_PROBABILIDAD;
  svg.style.height = `${alto}px`;
  const {x, ancho} = m.ejes;
  // Arriba, la cantidad (L/m²); abajo, la probabilidad (%)
  const cantidades = [...s.media, ...(s.observado ?? [])].filter(valido);
  const max = Math.max(1, ...cantidades) * 1.15;
  const y = (v) => ARRIBA - 6 + (1 - v / max) * (ALTO_LLUVIA - ARRIBA + 6);
  const base2 = alto, alto2 = ALTO_PROBABILIDAD - 4, y2 = (p) => base2 - p / 100 * alto2;
  m.escalas.lluvia = y;
  const {lista, decimales} = marcas(0, max, 3);
  const partes = fondo(m, alto, y, lista.filter(v => v > 0), decimales, ALTO_LLUVIA);
  for (const p of [50, 100]) {
    partes.push(`<line class="mg-guia" x1="${IZQUIERDA}" x2="${ancho - DERECHA}" y1="${y2(p)}" y2="${y2(p)}"/>`,
                `<text class="mg-valor-eje" x="${IZQUIERDA - 5}" y="${y2(p) + 3.5}">${p} %</text>`);
  }
  partes.push(`<line class="mg-separador" x1="${IZQUIERDA}" x2="${ancho - DERECHA}" y1="${ALTO_LLUVIA}" `
              + `y2="${ALTO_LLUVIA}"/>`);
  const paso = (ancho - IZQUIERDA - DERECHA) / Math.max(1, m.d.horas.length - 1), barra = Math.max(1.5, paso * 0.7);
  s.probabilidad.forEach((p, i) => {
    if (valido(p) && p > 0) {
      partes.push(`<rect class="mg-prob" x="${x(m.d.horas[i]) - barra / 2}" y="${y2(p)}" width="${barra}" `
                  + `height="${base2 - y2(p)}"/>`);
    }
  });
  (s.observado ?? []).forEach((v, i) => {
    if (valido(v) && v > 0) {
      partes.push(`<rect class="mg-obs-lluvia" x="${x(m.d.horas[i]) - barra / 2}" y="${y(v)}" width="${barra}" `
                  + `height="${y(0) - y(v)}"/>`);
    }
  });
  partes.push(`<path class="mg-lluvia-area" d="${trazo(m, s.media, y, y(0))}"/>`,
              `<path class="mg-lluvia-linea" d="${trazo(m, s.media, y)}"/>`);
  s.media.forEach((v, i) => {
    if (valido(v) && v > 0) partes.push(`<circle class="mg-lluvia-punto" cx="${x(m.d.horas[i])}" cy="${y(v)}" r="2"/>`);
  });
  partes.push(cursor(alto, [["media", AZUL]]));
  return partes.join("");
}

// Eje de tiempo: el nombre de cada día en medio de su tramo, las 12 h y la hora del cursor
function dibujarEje(m, eje) {
  const {x} = m.ejes, {horas, tz} = m.d, partes = [];
  const cortes = [horas[0], ...horas.filter(h => h > horas[0] && horaLocal(h, tz) === 0), horas.at(-1)];
  cortes.slice(0, -1).forEach((a, k) => {
    const b = cortes[k + 1];
    if (x(b) - x(a) > 42) partes.push(`<text class="mg-dia-texto" x="${(x(a) + x(b)) / 2}" y="16">${diaCorto(a, tz)}</text>`);
  });
  for (const h of horas) {
    if (horaLocal(h, tz) === 12) {
      partes.push(`<line class="mg-dia" x1="${x(h)}" x2="${x(h)}" y1="0" y2="4"/>`);
    }
  }
  partes.push('<g class="mg-eje-cursor"><rect y="1" height="18" rx="6"/><text y="14"></text></g>');
  return partes.join("");
}

// ---------------------------------------------------------------- Cursor y lecturas

function irA(m, t) {
  m.t = t;
  const {d, raiz} = m;
  if (!d) return;
  const h = d.horas[t];
  raiz.querySelector(".mg-hora").innerHTML = `${fechaLarga(h, d.tz)}<small>${relativa(h)}</small>`;
  lecturas(m);
  if (!m.ejes) return;
  const px = m.ejes.x(h);
  for (const seccion of raiz.querySelectorAll(".mg-panel")) {
    const id = seccion.dataset.id, g = seccion.querySelector(".mg-cursor"), y = m.escalas[id];
    if (!g || !y) continue;
    g.setAttribute("transform", `translate(${px},0)`);
    const s = id === "lluvia" ? d.lluvia : d[id];
    for (const circulo of g.querySelectorAll("circle")) {
      const v = s[circulo.getAttribute("class")]?.[t];
      circulo.style.display = valido(v) ? "" : "none";
      if (valido(v)) circulo.setAttribute("cy", y(v));
    }
  }
  for (const eje of raiz.querySelectorAll(".mg-eje")) {
    const g = eje.querySelector(".mg-eje-cursor");
    if (!g) continue;
    const texto = g.querySelector("text"), rect = g.querySelector("rect");
    texto.textContent = `${diaCorto(h, d.tz)} · ${String(horaLocal(h, d.tz)).padStart(2, "0")} h`;
    const w = texto.getComputedTextLength() + 14;
    const centro = Math.min(m.ejes.ancho - DERECHA - w / 2, Math.max(IZQUIERDA + w / 2, px));
    rect.setAttribute("x", centro - w / 2);
    rect.setAttribute("width", w);
    texto.setAttribute("x", centro);
    // Los nombres de los días que quedan debajo de la hora del cursor se esconden
    for (const dia of eje.querySelectorAll(".mg-dia-texto")) {
      dia.style.visibility = Math.abs(+dia.getAttribute("x") - centro) < w / 2 + 24 ? "hidden" : "";
    }
  }
}

function lecturas(m) {
  const {d, raiz, t} = m;
  const valor = (v, decimales, unidad = "") => valido(v) ? `${numero(v, decimales)}${unidad}` : null;
  const partes = {
    temperatura: (s) => [
      valor(s.media[t], 1, " °C") && `<b>${valor(s.media[t], 1, " °C")}</b>`,
      valido(s.p10[t]) && `10-90 %: ${valor(s.p10[t], 1)} a ${valor(s.p90[t], 1)}`,
      s.control && valor(s.control[t], 1) && `control ${valor(s.control[t], 1)}`,
      s.observado && valor(s.observado[t], 1) && `observada ${valor(s.observado[t], 1)}`,
    ],
    lluvia: (s) => [
      valido(s.probabilidad[t]) && `<b>${s.probabilidad[t]} %</b> de prob.`,
      s.probabilidad[t] > 0 && `${valor(s.media[t], 1)} L/m² de media si llueve`,
      s.observado && valor(s.observado[t], 1) && `observada ${valor(s.observado[t], 1)} L/m²`,
    ],
    rachas: (s) => [
      valor(s.media[t], 0, " km/h") && `<b>${valor(s.media[t], 0, " km/h")}</b>`,
      s.control && valor(s.control[t], 0) && `control ${valor(s.control[t], 0)}`,
      s.observado && valor(s.observado[t], 0) && `observada ${valor(s.observado[t], 0)}`
        + (s.direccion?.[t] ? ` del ${s.direccion[t]}` : ""),
    ],
    presion: (s) => [
      valor(s.media[t], 1, " hPa") && `<b>${valor(s.media[t], 1, " hPa")}</b>`,
      s.control && valor(s.control[t], 1) && `control ${valor(s.control[t], 1)}`,
    ],
    mucape: (s) => [
      valor(s.media[t], 0, " J/kg") && `<b>${valor(s.media[t], 0, " J/kg")}</b>`,
      valor(s.maximo[t], 0) && `máx. del ensemble ${valor(s.maximo[t], 0)}`,
    ],
  };
  for (const seccion of raiz.querySelectorAll(".mg-panel")) {
    const id = seccion.dataset.id, texto = partes[id](d[id]).filter(Boolean);
    seccion.querySelector(".mg-lectura span").innerHTML = texto.length ? texto.join(" · ") : "sin dato";
  }
}

// ---------------------------------------------------------------- Streamlit

export default function (component) {
  const {data, parentElement} = component;
  const raiz = parentElement.querySelector(".meteograma");
  const m = raiz._meteograma ??= crear(raiz);
  if (m.clave === data.clave) return;  // los mismos datos: Streamlit ha recargado la página por otra cosa
  m.clave = data.clave;
  cargar(m, data);
}
