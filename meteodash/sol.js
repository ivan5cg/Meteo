// El Sol hoy (ver sol.py): la elevación a lo largo del día sobre las bandas de los crepúsculos y un cursor que da la
// altura, el azimut y la fase de luz de cada momento. Como en el meteograma, el ratón muestra la hora al pasar y pulsar la
// fija; el dedo, las flechas y «Ahora» también la fijan. Todo en el navegador, sin recargar Streamlit.

const IZQUIERDA = 36, DERECHA = 8, ALTO = 240;
const AMBAR = "#d97706", AZUL = "#0277bd", ROJO = "#d93856", TEXTO = "#2a241f";
// Fases de la luz según la altura del Sol: a partir de -0,833º asoma su borde superior (con la refracción)
const FASES = [[-0.833, "de día", AMBAR], [-6, "crepúsculo civil", AZUL], [-12, "crepúsculo náutico", "#1d4e89"],
               [-18, "crepúsculo astronómico", "#28386b"], [-91, "noche", "#1e293b"]];
const BANDAS = [[0, -6, 0.07, "civil"], [-6, -12, 0.11, "náutico"], [-12, -18, 0.15, "astronómico"],
                [-18, -90, 0.2, ""]];
let contador = 0;  // para que los recortes (clipPath) de varios visores no compartan identificador

const numero = (v, decimales) => v.toLocaleString("es-ES", {minimumFractionDigits: decimales,
                                                             maximumFractionDigits: decimales});
const fase = (elevacion) => FASES.find(([desde]) => elevacion >= desde);

const formatos = {};
function hora(t, tz) {
  return (formatos[tz] ??= new Intl.DateTimeFormat("es-ES", {timeZone: tz, hour: "2-digit", minute: "2-digit",
                                                             hourCycle: "h23"})).format(t);
}

// ---------------------------------------------------------------- Estructura

function fijar(s, i) {
  s.fijo = i;
  irA(s, i);
}

function crear(raiz) {
  const s = {raiz, i: 0, fijo: 0, id: `sol${++contador}`};
  raiz.addEventListener("keydown", (e) => {
    if (!s.d || e.ctrlKey || e.metaKey || e.altKey) return;
    const ultimo = s.d.puntos.length - 1;
    // Flechas: 15 min; Re Pág / Av Pág: 1 h
    const destino = {ArrowLeft: s.fijo - 3, ArrowRight: s.fijo + 3, PageUp: s.fijo - 12, PageDown: s.fijo + 12,
                     Home: 0, End: ultimo}[e.key];
    if (destino === undefined) return;
    e.preventDefault();
    fijar(s, Math.min(ultimo, Math.max(0, destino)));
  });
  raiz.addEventListener("pointerleave", (e) => { if (s.d && e.pointerType === "mouse") irA(s, s.fijo); });
  new ResizeObserver(() => dibujar(s)).observe(raiz);
  return s;
}

// El punto de la curva más cercano a un instante
function indice(d, t) {
  let mejor = 0;
  d.puntos.forEach(([momento], i) => { if (Math.abs(momento - t) < Math.abs(d.puntos[mejor][0] - t)) mejor = i; });
  return mejor;
}

function cargar(s, d) {
  // Se conserva la hora fijada salvo que fuera la de ahora (que avanza con cada recarga)
  const anterior = s.d && s.fijo !== indice(s.d, s.d.ahora[0]) ? s.d.puntos[s.fijo][0] : null;
  s.d = d;
  s.i = s.fijo = indice(d, anterior ?? d.ahora[0]);
  s.raiz.innerHTML = `<div class="sl-cabecera"><div class="sl-titulo">${d.titulo}</div>`
    + '<button class="sl-ahora">Ahora</button></div><div class="sl-lectura"></div><svg class="sl-svg"></svg>'
    + '<svg class="sl-eje"></svg>';
  s.raiz.querySelector(".sl-ahora").onclick = () => fijar(s, indice(d, d.ahora[0]));
  for (const svg of s.raiz.querySelectorAll("svg")) enlazar(s, svg);
  dibujar(s);
}

// Ratón: el cursor sigue al puntero y pulsar fija la hora. Dedo: tocar o arrastrar en horizontal la fija
function enlazar(s, svg) {
  let arrastrando = false;
  const punto = (e) => {
    const {t0, t1, ancho} = s.ejes, x = e.clientX - svg.getBoundingClientRect().left;
    return indice(s.d, t0 + (x - IZQUIERDA) / (ancho - IZQUIERDA - DERECHA) * (t1 - t0));
  };
  svg.addEventListener("pointerdown", (e) => {
    if (!s.ejes) return;
    if (e.pointerType !== "mouse") {
      arrastrando = true;
      svg.setPointerCapture(e.pointerId);
    }
    fijar(s, punto(e));
  });
  svg.addEventListener("pointermove", (e) => {
    if (!s.ejes || (e.pointerType !== "mouse" && !arrastrando)) return;
    const i = punto(e);
    if (arrastrando) {
      if (i !== s.fijo) fijar(s, i);
    } else if (i !== s.i) {
      irA(s, i);
    }
  });
  for (const evento of ["pointerup", "pointercancel"]) svg.addEventListener(evento, () => { arrastrando = false; });
}

// ---------------------------------------------------------------- Dibujo

function dibujar(s) {
  const {d, raiz} = s;
  const svg = raiz.querySelector(".sl-svg"), eje = raiz.querySelector(".sl-eje");
  if (!d || !svg || !svg.clientWidth) return;
  const ancho = svg.clientWidth, t0 = d.puntos[0][0], t1 = d.puntos.at(-1)[0];
  const elevaciones = d.puntos.map(p => p[1]);
  const min = Math.max(-90, Math.min(...elevaciones) - 4), max = Math.max(...elevaciones) + 10;
  const x = (t) => IZQUIERDA + (t - t0) / (t1 - t0) * (ancho - IZQUIERDA - DERECHA);
  const y = (e) => 4 + (1 - (e - min) / (max - min)) * (ALTO - 8);
  s.ejes = {t0, t1, ancho, x, y};
  const derecha = ancho - DERECHA, partes = [];

  // Bandas de los crepúsculos bajo el horizonte, con su nombre si caben
  for (const [arriba, abajo, opacidad, nombre] of BANDAS) {
    const ya = y(Math.min(arriba, max)), yb = y(Math.max(abajo, min));
    if (yb <= ya) continue;
    partes.push(`<rect x="${IZQUIERDA}" y="${ya}" width="${derecha - IZQUIERDA}" height="${yb - ya}" `
                + `fill="rgba(2, 119, 189, ${opacidad})"/>`);
    if (nombre && yb - ya >= 11) {
      partes.push(`<text class="sl-banda" x="${derecha - 4}" y="${(ya + yb) / 2 + 3.5}">${nombre}</text>`);
    }
  }
  // Rejilla: cada 20º, y una línea cada 3 h
  for (let e = Math.ceil(min / 20) * 20; e <= max; e += 20) {
    partes.push(`<line class="sl-guia" x1="${IZQUIERDA}" x2="${derecha}" y1="${y(e)}" y2="${y(e)}"/>`,
                `<text class="sl-valor-eje" x="${IZQUIERDA - 5}" y="${y(e) + 3.5}">${e}°</text>`);
  }
  const horas = [];
  for (let t = t0; t <= t1; t += 36e5) if (+hora(t, d.tz).slice(0, 2) % 3 === 0) horas.push(t);
  for (const t of horas) partes.push(`<line class="sl-guia" x1="${x(t)}" x2="${x(t)}" y1="0" y2="${ALTO}"/>`);

  // La curva: ámbar sobre el horizonte y azul por debajo, con su área hasta el horizonte
  const linea = d.puntos.map(([t, e], k) => `${k ? "L" : "M"}${x(t).toFixed(1)},${y(e).toFixed(1)}`).join("");
  const area = `${linea}L${x(t1)},${y(0)}L${x(t0)},${y(0)}Z`;
  partes.push(`<clipPath id="${s.id}-dia"><rect x="0" y="0" width="${ancho}" height="${y(0)}"/></clipPath>`,
              `<clipPath id="${s.id}-noche"><rect x="0" y="${y(0)}" width="${ancho}" height="${ALTO}"/></clipPath>`,
              `<path d="${area}" fill="rgba(217, 119, 6, 0.18)" clip-path="url(#${s.id}-dia)"/>`,
              `<path d="${area}" fill="rgba(2, 119, 189, 0.12)" clip-path="url(#${s.id}-noche)"/>`,
              `<path d="${linea}" fill="none" stroke="${AMBAR}" stroke-width="2.5" clip-path="url(#${s.id}-dia)"/>`,
              `<path d="${linea}" fill="none" stroke="${AZUL}" stroke-width="1.6" clip-path="url(#${s.id}-noche)"/>`,
              `<line class="sl-horizonte" x1="${IZQUIERDA}" x2="${derecha}" y1="${y(0)}" y2="${y(0)}"/>`);

  // Amanecer, cénit, atardecer y ahora
  const marca = (t, e, color, texto, debajo, r = 4.5) => {
    const px = Math.min(derecha - 40, Math.max(IZQUIERDA + 40, x(t)));
    partes.push(`<circle cx="${x(t)}" cy="${y(e)}" r="${r}" fill="${color}" stroke="#fff" stroke-width="1.5"/>`,
                `<text class="sl-marca" x="${px}" y="${y(e) + (debajo ? 16 : -9)}" fill="${color === AZUL ? AZUL : TEXTO}">`
                + `${texto}</text>`);
  };
  if (d.amanecer) marca(d.amanecer, 0, AMBAR, `Amanecer ${hora(d.amanecer, d.tz)}`, true);
  if (d.atardecer) marca(d.atardecer, 0, "#ea580c", `Atardecer ${hora(d.atardecer, d.tz)}`, true);
  marca(d.cenit[0], d.cenit[1], ROJO, `Cénit ${hora(d.cenit[0], d.tz)} (${numero(d.cenit[1], 1)}°)`, false);
  marca(d.ahora[0], d.ahora[1], AZUL, `Ahora (${numero(d.ahora[1], 1)}°)`, d.ahora[1] > max - 12, 6);

  partes.push(`<g class="sl-cursor"><line y1="0" y2="${ALTO}"/><circle r="4.5"/></g>`);
  svg.style.height = `${ALTO}px`;
  svg.innerHTML = partes.join("");

  eje.innerHTML = horas.map(t => `<text class="sl-hora" x="${x(t)}" y="15">${hora(t, d.tz).slice(0, 2)} h</text>`)
    .join("") + '<g class="sl-eje-cursor"><rect y="1" height="18" rx="6"/><text y="14"></text></g>';
  irA(s, s.i);
}

// ---------------------------------------------------------------- Cursor y lectura

function irA(s, i) {
  s.i = i;
  const {d, raiz, ejes} = s, [t, elevacion, azimut] = d.puntos[i], [, nombre, color] = fase(elevacion);
  const rumbo = d.rumbos[Math.floor((azimut % 360 + 22.5) / 45) % 8];
  raiz.querySelector(".sl-lectura").innerHTML = `<b>${hora(t, d.tz)}</b> · altura <b>${numero(elevacion, 1)}°</b>`
    + ` · azimut ${numero(azimut, 0)}° (${rumbo}) · <span style="color:${color}">${nombre}</span>`;
  if (!ejes) return;
  const cursor = raiz.querySelector(".sl-cursor");
  cursor.setAttribute("transform", `translate(${ejes.x(t)},0)`);
  const circulo = cursor.querySelector("circle");
  circulo.setAttribute("cy", ejes.y(elevacion));
  circulo.setAttribute("fill", elevacion >= 0 ? AMBAR : AZUL);
  const g = raiz.querySelector(".sl-eje-cursor"), texto = g.querySelector("text"), rect = g.querySelector("rect");
  texto.textContent = hora(t, d.tz);
  const w = texto.getComputedTextLength() + 14;
  const centro = Math.min(ejes.ancho - DERECHA - w / 2, Math.max(IZQUIERDA + w / 2, ejes.x(t)));
  rect.setAttribute("x", centro - w / 2);
  rect.setAttribute("width", w);
  texto.setAttribute("x", centro);
  for (const etiqueta of raiz.querySelectorAll(".sl-hora")) {
    etiqueta.style.visibility = Math.abs(+etiqueta.getAttribute("x") - centro) < w / 2 + 14 ? "hidden" : "";
  }
}

// ---------------------------------------------------------------- Streamlit

export default function (component) {
  const {data, parentElement} = component;
  const raiz = parentElement.querySelector(".sol");
  const s = raiz._sol ??= crear(raiz);
  if (s.clave === data.clave) return;  // los mismos datos: Streamlit ha recargado la página por otra cosa
  s.clave = data.clave;
  cargar(s, data);
}
