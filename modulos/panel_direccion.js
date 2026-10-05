// modulos/panel_direccion.js · «Panel de dirección» (carril C2 del superplan 24). SOLO TOMÁS.
//
// Petición de Tomás (2-oct): «arrastra todo lo que ya tenemos en el panel de control de toda la empresa, que ahí habíamos
// hecho un muy buen trabajo, volcado a esta herramienta, pero solamente con acceso para mí».
//
// Qué es: el panel de resultados v29/v30 (artefacto privado WeCVRWFTxD3MMdU2jb9siH) dentro de la app. Las cifras NO se
// recalculan aquí: las pinta el propio render() del panel en Chrome sin ventana (fuentes_panel_direccion/generar_panel_direccion.py)
// y este módulo las vuelve a montar con el sistema común de la app (N6, auditoría 30): sin hoja de estilos propia, solo
// componentes y clases de estilos.css. Cada pieza del panel (clases px-*) se traduce a su equivalente común: paneles, tarjetas,
// tablas densas, barras de progreso, chips de estado y un único motor de gráficos, grafico(), que vuelve a dibujar cada
// gráfico del panel con los valores leídos de su SVG (ejes, barras, líneas y puntos). Lo que no se puede traducir con
// seguridad se deja tal cual, con la letra a 12 px. Paridad: n6_paridad.py compara pestaña a pestaña las cifras de antes y después.
//
//   · La captación (lo de cada día, va primero): coste por cliente firmado (la cifra que manda, con colorCifra) + resumen +
//     cadena del coste; pestañas Resumen · Publicidad · De qué anuncio · Agenda · Ventas · Operativa, con 5 fotos de periodo.
//   · La empresa: Resumen financiero (gasto y beneficio SOLO de M19, corregidos por divisa) · Clientes · Plan y año, y en vivo
//     las cifras de M19. Ingresos y Caja y cobros viven en Finanzas (M19): aquí, enlace + la versión del panel.
//   · Coste del equipo por persona: solo dirección y RRHH → almacén privado data/sueldos/_privado/sueldos.json de E0, persona
//     a persona con ctx.verDato (con rastro). Nunca la hoja «Cuentas bancarias».
//   · Panel original (menú «Más»): enlace a su artefacto privado y descarga del .html.
//
// Permisos: puestos_que_lo_ven solo dirección; data/panel_direccion/* con {"puestos": ["direccion"]} en reglas_permisos.json.
// Periodo: el panel trae 5 FOTOS hechas por el generador (septiembre, octubre, desde el 1-ago, desde el 14-sep, 7 días); no
// son rangos que se puedan recalcular, así que no usa el periodo común (usa_periodo): «desde el 1-ago» y «desde el 14-sep» se perderían.

import { plegarSecundarias } from '../componentes.js';   // V2-E (M17): plegado común en el móvil
// Paneles v4 (48 §4.1, encargo del coordinador 3-oct) y Ronda U (50): arriba un RESUMEN nativo con la cifra que manda
// (beneficio del último mes cerrado), la cuota contra el objetivo de diciembre, seis tarjetas con su línea de 12 meses,
// comparación y umbral con fuente, «Lo que pide tu decisión» con su botón al lado, el puente de la cuota en cascada y los
// clientes (altas y bajas, cohortes). Mismas cifras que Finanzas (beneficio ene-ago 93.492 €): no se recalcula nada, se leen
// finanzas/direccion, cuadre, impagos, finanzas (admin) y ventas_ro. El panel portado (captación, empresa, original) sigue
// detrás, en sus chips.
import { tarjetaKpi, selectorComparar, lineaComparacion, minilinea, cascada, barraObjetivo, estadoObjetivo, barrasGanadoPerdido, mapaCalor,
  listaLoPrimero, enlaceFuente } from '../componentes.js';
import { FUENTES, UMBRALES, ESTADO, fuentesAlPie, mesMas, puenteCuota, separador } from './dinero_v4.js';
import { botonDeshacer } from './_deshacer.js';
import { consejoCompacto, filasFlexibles } from './_trabajo.js';
const filasLP = (...a) => filasFlexibles(listaLoPrimero(...a));   // Ronda U: botones debajo cuando no caben, a cualquier ancho
import { h, icono, fmt, tile, tiles, chipsFiltro, pestanas, panel, vacio, avisoParcial, frescura, selectorPeriodo, botonConfirmar,
  tablaApilable, chipEstado, colorCifra, cifraPrincipal, barraProgreso, grafico, menuMas, vacioLinea, esqueleto } from '../componentes.js';

// Revisión 44 (textos cortados): lo que la pantalla corta con «…» (una línea o el límite de líneas) lleva el texto entero
// en el title, para que la regla de la tarjeta o el nombre largo no se pierdan. Mira el contenedor mientras se pinta.
const _SEL_CORTE = '.tile .tx, .tile .tt span, .tile em, .det, .mot, .sub, .t, td, .chip, summary, b, small';
function vigilarCortes(raiz) {
  if (!raiz || raiz.__cortes) return;
  raiz.__cortes = true;
  let t = 0;
  const mirar = () => { t = 0; for (const el of raiz.querySelectorAll(_SEL_CORTE)) {
    if (el.title || el.closest('[title]') !== null && el.closest('[title]') !== el || !el.isConnected) continue;
    if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 2) { const s = el.textContent.trim(); if (s && s.length > 8) el.title = s; } } };
  new MutationObserver(() => { if (!t) t = setTimeout(mirar, 400); }).observe(raiz, { childList: true, subtree: true });
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => { if (!t) t = setTimeout(mirar, 400); }).observe(raiz);
}

// Revisión 44 (§2.3): fechas con el formato único de la app: «2-oct» y «2-oct, 17:34» (nunca «2 oct» ni «sept»).
const _MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _fechaDe = iso => (iso ? new Date(String(iso).length <= 10 ? `${iso}T12:00:00` : String(iso).replace(' ', 'T')) : null);
const fDiaRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}`; };
const fDiaHoraRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

const MUNDOS = [
  { valor: 'resumen', texto: 'Resumen', icono: 'hoy' },
  { valor: 'captacion', texto: 'La captación', icono: 'target' },
  { valor: 'empresa', texto: 'La empresa', icono: 'euro' },
];
const TABS_CAPTACION = [
  { id: 'sum', icono: 'hoy' }, { id: 'pub', icono: 'megafono' }, { id: 'atr', icono: 'target' },
  { id: 'res', icono: 'cal' }, { id: 'vent', icono: 'crown' }, { id: 'ope', icono: 'medidor' },
];
const TABS_EMPRESA = [
  { id: 'fres', icono: 'hoy', texto: 'Resumen financiero' },
  { id: 'cli', icono: 'users' },
  { id: 'emp', icono: 'flag', guarda: [/^Cuenta de resultados/, /^Real frente a presupuesto/, /^Por año/, /^Ingresos y gastos/, /^Cierre del año$/, /^Lo que hay que mirar/] },
  { id: 'fing', icono: 'euro', m19: { pestana: 'ingresos', texto: 'Ingresos y clientes' } },
  { id: 'fgas', icono: 'maletin', m19: { pestana: 'resultados', texto: 'Resultados y equipo' }, guarda: [/./] },
  { id: 'fcaja', icono: 'cartera', m19: { pestana: 'cobros', texto: 'Cobros y caja' }, guarda: [/^Entradas y salidas/] },
  { id: 'equipo', icono: 'eq', texto: 'Coste del equipo' },
];
// Error de divisa del cierre de Sofía (25_AUDITORIA_CIERRE_SOFIA.md): el v29 suma las facturas en dólares como euros.
const AVISO_DIVISA = 'Corregido respecto al panel antiguo por error de divisa: el cierre de Sofía, que el panel copia, suma las 695 facturas en dólares del equipo y de herramientas como si fueran euros (+39.663 € de gasto de enero a agosto). Gasto, beneficio, margen y peso del equipo: los buenos están en «Resumen financiero» y en Finanzas. Ingresos, cuota, caja y concentración sí valen.';
// Tiles del Resumen financiero del v29 que NO dependen del gasto (se portan tal cual)
const SIN_GASTO = t => !/margen|beneficio|aguanta|meses de caja|recuperar|valor frente|equipo|gasto|resultado|30 segundos/i.test(t);

// icono del panel según lo que cuenta (solo decorativo: el título manda)
const ICONO_TITULO = [
  [/retorno|roas/i, 'sube'], [/cuota|mrr|ingres|factur|cobr|dinero|pendiente de firma/i, 'euro'], [/inversi|gasto de meta|presupuesto|ritmo/i, 'cartera'],
  [/anuncio|capa|curso|desgaste|publicidad/i, 'megafono'], [/cita|agenda|reserva|hora/i, 'cal'], [/llamad|zadarma/i, 'phone'],
  [/reuni|graba/i, 'video'], [/client|potencial|cohorte|altas|bajas|activos/i, 'users'], [/propuesta|acuerdo|firma|circuito|ventas/i, 'crown'],
  [/caja|saldo|banco/i, 'cartera'], [/proveedor|gasto|categor/i, 'maletin'], [/equipo|persona/i, 'eq'], [/plan|año|cierre|150/i, 'flag'],
  [/contest|bandeja|mensaje|precall|recordatorio|reciben/i, 'chat'], [/fuente|medici|salud|comprob/i, 'escudo'], [/mirar|aviso|haría/i, 'alert'],
  [/embudo|paso/i, 'capas'], [/indicador|resultados/i, 'grafico'], [/crm|gohighlevel/i, 'base'],
];
const iconoDe = t => (ICONO_TITULO.find(([rx]) => rx.test(t || '')) || [null, 'grafico'])[1];

// ===================================================================== utilidades de lectura del HTML del panel
/** Barrido v1: el panel heredado trae referencias internas que no dicen nada a quien lee: listas de reuniones «(R31, R32)»,
 *  «capas.json» y códigos de anuncio delante del nombre («A2 · E2 · Ecom…» → «Ecom…»). Se quitan al pintar. */
const COD = '(?:[A-Z]{1,2}-?\\d+[a-z]?)';
const RX_PAREN_COD = new RegExp(`\\s*\\((?:${COD}(?:\\s*[,·]\\s*|\\s+y\\s+|…)?)+\\)`, 'g');
const RX_COD_DELANTE = new RegExp(`^\\s*(?:${COD}\\s*·\\s*)+`);
const sinRef = t => String(t).replace(RX_PAREN_COD, '').replace(/\bcapas\.json\b/g, 'la tabla de capas').replace(/\b[\w-]+\.(?:json|py|csv|md)\b/g, 'su fichero').replace(RX_COD_DELANTE, '').replace(/\bR\d{2}\b/g, 'una reunión');
const texto = el => sinRef((el?.textContent || '').replace(/\s+/g, ' ').trim());
const tieneCl = (el, c) => el?.classList?.contains(c);
const hijosEl = el => [...(el?.children || [])];

const ETIQUETAS_PERMITIDAS = new Set(['DIV', 'SPAN', 'P', 'B', 'STRONG', 'I', 'EM', 'U', 'SMALL', 'BR', 'HR', 'UL', 'OL', 'LI', 'TABLE', 'THEAD', 'TBODY', 'TFOOT', 'TR', 'TH', 'TD',
  'A', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'IMG', 'SECTION', 'ARTICLE', 'HEADER', 'FOOTER', 'NAV', 'MAIN', 'SUP', 'SUB', 'CODE', 'PRE', 'BLOCKQUOTE',
  'DETAILS', 'SUMMARY', 'BUTTON', 'INPUT', 'TITLE',   // los usa el panel de dirección (details/summary, selectores de días)
  'SVG', 'LINE', 'TEXT', 'PATH', 'CIRCLE', 'RECT', 'G', 'POLYLINE', 'POLYGON', 'TSPAN']);   // gráficos del panel (sin script ni foreignObject)

export function parsear(html) {
  const doc = new DOMParser().parseFromString(`<!doctype html><meta charset="utf-8"><body><div id="pdir-r">${html || ''}</div>`, 'text/html');
  const r = doc.getElementById('pdir-r');
  r.querySelectorAll('script,iframe,object,embed,link,style,form,meta').forEach(x => x.remove());
  // V2 (C-28): restos del dato en los nombres («Pinheiro Leonardo⁷»): fuera los superíndices pegados a un nombre
  r.querySelectorAll('.px-name').forEach(e => { const w = doc.createTreeWalker(e, NodeFilter.SHOW_TEXT); for (let n = w.nextNode(); n; n = w.nextNode()) n.nodeValue = n.nodeValue.replace(/([A-Za-zÁÉÍÓÚÑáéíóúñ])[⁰¹²³⁴⁵⁶⁷⁸⁹]+/g, '$1'); });
  // L-26: lista BLANCA. Etiqueta que no está en la lista → se queda su contenido, sin la etiqueta; atributos «on…» fuera;
  // href/src solo hacia «#», «/», http(s) o mailto. SVG y los controles del panel propio están en la lista porque los pinta el panel.
  r.querySelectorAll('*').forEach(e => {
    [...e.attributes].forEach(a => {
      if (/^on/i.test(a.name)) e.removeAttribute(a.name);
      else if (/^(href|src|xlink:href)$/i.test(a.name) && !/^\s*(#|\/|https?:\/\/|mailto:)/i.test(a.value)) e.removeAttribute(a.name);
    });
    if (!ETIQUETAS_PERMITIDAS.has(e.tagName.toUpperCase())) e.replaceWith(...e.childNodes);
  });
  return document.importNode(r, true);
}

/** «9.559 €», «57,93 €», «+50 %», «56,5k», «50 mil», «−14» → número (o null). */
function numero(t) {
  let s = String(t || '').trim();
  if (!s) return null;
  const neg = /^[−-]/.test(s);
  const mil = /\d\s*(k|mil)\b/i.test(s) || /\dk$/i.test(s);
  s = s.replace(/[^\d.,]/g, '');
  if (!/\d/.test(s)) return null;
  s = s.replace(/\./g, '').replace(',', '.');
  let v = Number(s);
  if (!Number.isFinite(v)) return null;
  if (mil) v *= 1000;
  return neg ? -v : v;
}

// Colores del panel → estado común (barras) y color de serie común (gráficos). Solo tokens.
const ESTADO_COLOR = c => (/--bad/.test(c) ? 'rojo' : /--good|--c3|--ok/.test(c) ? 'verde' : /--warn/.test(c) ? 'ambar' : null);
const SERIE_COLOR = c => (/--c1|--accent|--f[4-7]/.test(c) ? 'var(--accent)' : /--c2/.test(c) ? 'var(--serie-2)' : /--c3|--good/.test(c) ? 'var(--serie-3)'
  : /--bad/.test(c) ? 'var(--bad)' : /--ink/.test(c) ? 'var(--ink)' : 'var(--serie-4)');
const colorDe = el => (el?.getAttribute?.('fill') || el?.getAttribute?.('stroke') || el?.style?.background || el?.style?.backgroundColor || '').trim();
const ESTADO_TAG = el => (tieneCl(el, 'px-ok') || tieneCl(el, 'px-good') ? 'verde' : tieneCl(el, 'px-ko') || tieneCl(el, 'px-bad') ? 'rojo'
  : tieneCl(el, 'px-wait') || tieneCl(el, 'px-warn') ? 'ambar' : tieneCl(el, 'px-venta') ? 'azul' : 'gris');

// ===================================================================== gráficos del panel → grafico()
const MESES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const esMes = t => MESES3.indexOf(String(t).slice(0, 3).toLowerCase());

/** Rellena las etiquetas del eje X que el panel no pintaba (1 sep, 6 sep… → todos los días), para la burbuja. */
function completarEtiquetas(n, conocidas, anio) {
  const ks = [...conocidas.keys()].sort((a, b) => a - b);
  const out = Array.from({ length: n }, (_, i) => conocidas.get(i) ?? '');
  if (ks.length < 2) return out;
  const [i0, i1] = ks, t0 = conocidas.get(i0), t1 = conocidas.get(i1);
  let m;
  if ((m = /^(\d{1,2}) (\w{3})$/.exec(t0)) && /^(\d{1,2}) (\w{3})$/.test(t1) && esMes(m[2]) >= 0) {
    const m1 = /^(\d{1,2}) (\w{3})$/.exec(t1);
    const d0 = Date.UTC(anio, esMes(m[2]), +m[1]), d1 = Date.UTC(anio, esMes(m1[2]), +m1[1]);
    const paso = (d1 - d0) / 864e5 / (i1 - i0);
    if (paso > 0 && Number.isInteger(Math.round(paso * 100) / 100)) {
      for (let i = 0; i < n; i++) { const d = new Date(d0 + (i - i0) * paso * 864e5); out[i] = `${d.getUTCDate()} ${MESES3[d.getUTCMonth()]}`; }
    }
    return out;
  }
  if ((m = /^(\w{3})( (\d{2}))?$/.exec(t0)) && esMes(m[1]) >= 0 && esMes(t1) >= 0) {
    const m1 = /^(\w{3})( (\d{2}))?$/.exec(t1);
    const y0 = m[3] ? 2000 + +m[3] : anio, y1 = m1?.[3] ? 2000 + +m1[3] : anio;
    const a = y0 * 12 + esMes(m[1]), b = y1 * 12 + esMes(m1[1]);
    const paso = (b - a) / (i1 - i0);
    const mayus = /^[A-Z]/.test(t0);
    if (paso > 0 && Number.isInteger(paso)) {
      for (let i = 0; i < n; i++) {
        const k = a + (i - i0) * paso, mm = MESES3[((k % 12) + 12) % 12];
        const txt = mayus ? mm[0].toUpperCase() + mm.slice(1) : mm;
        out[i] = m[3] ? `${txt} ${String(Math.floor(k / 12)).slice(2)}` : txt;
      }
    }
    return out;
  }
  if (/^\d+( h)?$/.test(t0) && /^\d+( h)?$/.test(t1)) {
    const v0 = parseInt(t0, 10), v1 = parseInt(t1, 10), paso = (v1 - v0) / (i1 - i0), suf = / h$/.test(t0) ? ' h' : '';
    if (Number.isInteger(paso)) for (let i = 0; i < n; i++) out[i] = `${v0 + (i - i0) * paso}${suf}`;
  }
  return out;
}

/** Lee el SVG del panel (ejes, barras, líneas, puntos) y lo vuelve a dibujar con grafico(). Devuelve null si no se puede. */
function graficoDe(svg, { leyenda, contexto = '', anio = 2026, titulo } = {}) {
  // se mide en el documento (getBBox) sin que se vea
  const caja = h('div', { 'aria-hidden': 'true', style: { position: 'absolute', visibility: 'hidden', left: '0', top: '0', width: '1200px' } });
  const copia = svg.cloneNode(true);
  caja.append(copia); document.body.append(caja);
  try {
    const vb = (copia.getAttribute('viewBox') || '').split(/\s+/).map(Number);
    const W = vb[2] || 600;
    const lineas = [...copia.querySelectorAll('line')].map(l => ({ el: l, x1: +l.getAttribute('x1'), x2: +l.getAttribute('x2'), y1: +l.getAttribute('y1'), y2: +l.getAttribute('y2') }));
    const rejilla = lineas.filter(l => Math.abs(l.y1 - l.y2) < 0.01 && (l.x2 - l.x1) > W * 0.5 && !l.el.getAttribute('stroke-dasharray') && l.el.getAttribute('visibility') !== 'hidden');
    if (rejilla.length < 2) return null;
    const xIni = Math.min(...rejilla.map(l => l.x1)), xFin = Math.max(...rejilla.map(l => l.x2));
    const yBase = Math.max(...rejilla.map(l => l.y1));
    const textos = [...copia.querySelectorAll('text')].map(t => ({ el: t, x: +t.getAttribute('x'), y: +t.getAttribute('y'), t: texto(t), anchor: t.getAttribute('text-anchor') || 'start' }));
    const cercana = y => rejilla.reduce((a, l) => (Math.abs(l.y1 - y) < Math.abs(a - y) ? l.y1 : a), Infinity);
    const marcas = lado => textos.filter(t => (lado === 'izq' ? t.anchor === 'end' && t.x <= xIni + 1 : t.x >= xFin - 1 && t.anchor !== 'end') && numero(t.t) !== null && t.y <= yBase + 8)
      .map(t => ({ y: cercana(t.y - 3.5), v: numero(t.t), t }));
    const izq = marcas('izq'), der = marcas('der');
    if (izq.length < 2) return null;
    const mapa = m => { const a = m[0], b = m[m.length - 1]; const k = (b.v - a.v) / (a.y - b.y || 1); return { val: y => a.v + (a.y - y) * k, k: Math.abs(k), cero: a.y + a.v / (k || 1) }; };
    const MI = mapa(izq), MD = der.length >= 2 ? mapa(der) : null;
    const usados = new Set([...izq, ...der].map(m => m.t.el));
    // etiquetas del eje X: debajo de la base
    const etX = textos.filter(t => t.y > yBase + 4 && !usados.has(t.el) && t.t);
    etX.forEach(t => usados.add(t.el));
    // marcas de datos
    const rects = [...copia.querySelectorAll('rect')];
    const zonas = rects.filter(r => /transparent|none/.test(r.getAttribute('fill') || '')).map(r => +r.getAttribute('x') + (+r.getAttribute('width')) / 2);
    const barras = [];
    rects.filter(r => !/transparent|none/.test(r.getAttribute('fill') || '')).forEach(r => {
      const x = +r.getAttribute('x'), w = +r.getAttribute('width'), y = +r.getAttribute('y'), alto = +r.getAttribute('height');
      const tit = texto(r.querySelector('title'));
      barras.push({ x: x + w / 2, xi: x, w, y, alto, color: colorDe(r), tit });
    });
    [...copia.querySelectorAll('path')].forEach(p => {
      const fill = p.getAttribute('fill') || '';
      if (fill === 'none' || Number(p.getAttribute('opacity') ?? 1) < 0.5 || !/z\s*$/i.test(p.getAttribute('d') || '')) return;
      const b = p.getBBox();
      if (b.height <= 0 || b.width > W * 0.3) return;
      barras.push({ x: b.x + b.width / 2, xi: b.x, w: b.width, y: b.y, alto: b.height, color: fill, tit: '' });
    });
    const trazos = [];
    [...copia.querySelectorAll('path')].filter(p => (p.getAttribute('fill') || '') === 'none').forEach(p => {
      const pts = [...(p.getAttribute('d') || '').matchAll(/([ML])\s*(-?[\d.]+)[ ,](-?[\d.]+)/g)].map(m => ({ x: +m[2], y: +m[3] }));
      if (pts.length > 1) trazos.push({ color: p.getAttribute('stroke') || '', pts });
    });
    const puntos = new Map();
    [...copia.querySelectorAll('circle')].forEach(c => {
      const col = c.getAttribute('fill') || c.getAttribute('stroke') || '';
      if (!puntos.has(col)) puntos.set(col, []);
      puntos.get(col).push({ x: +c.getAttribute('cx'), y: +c.getAttribute('cy') });
    });
    // tramos cortos con <title> (p. ej. «ingresos del presupuesto» mes a mes)
    const tramos = lineas.filter(l => Math.abs(l.y1 - l.y2) < 0.01 && (l.x2 - l.x1) < W * 0.3 && l.el.querySelector('title'))
      .map(l => ({ x: (l.x1 + l.x2) / 2, y: l.y1, tit: texto(l.el.querySelector('title')), color: l.el.getAttribute('stroke') || '' }));
    // umbral: línea discontinua a todo lo ancho
    const umb = lineas.find(l => Math.abs(l.y1 - l.y2) < 0.01 && (l.x2 - l.x1) > W * 0.5 && l.el.getAttribute('stroke-dasharray'));
    // huecos (slots) del eje X
    let huecos;
    const centrosB = [...new Set(barras.map(b => Math.round(b.x * 10) / 10))].sort((a, b) => a - b);
    const agrupar = xs => xs.reduce((acc, x) => { if (!acc.length || x - acc[acc.length - 1] > 1.5) acc.push(x); return acc; }, []);
    const clB = agrupar(centrosB);
    if (zonas.length) huecos = zonas;
    else if (clB.length) {
      const L = etX.length;
      const agrupadas = L >= 2 && clB.length > L && clB.length % L === 0 && clB.length / L <= 3;
      huecos = agrupadas ? etX.map(t => t.x).sort((a, b) => a - b) : clB;
    } else {
      const xs = agrupar([...new Set([...trazos.flatMap(t => t.pts.map(p => Math.round(p.x * 10) / 10)), ...[...puntos.values()].flat().map(p => Math.round(p.x * 10) / 10)])].sort((a, b) => a - b));
      huecos = xs;
    }
    if (!huecos.length) return null;
    const hueco = x => huecos.reduce((a, hx, i) => (Math.abs(hx - x) < Math.abs(huecos[a] - x) ? i : a), 0);
    const n = huecos.length;
    // series
    const ley = new Map();
    (leyenda ? [...leyenda.querySelectorAll('span')] : []).forEach(s => { const i = s.querySelector('i'); const c = colorDe(i) || i?.getAttribute('style') || ''; const m = /var\(--[\w-]+\)/.exec(c); if (m) ley.set(m[0], texto(s)); });
    const nombre = (c, def) => { const m = /var\(--[\w-]+\)/.exec(c || ''); return (m && ley.get(m[0])) || def; };
    const decTit = t => { const m = [...String(t).matchAll(/[−-]?\d[\d.]*(?:,\d+)?/g)].pop(); return m ? numero(m[0]) : null; };
    const gruposB = new Map();
    barras.forEach(b => {
      const k = /var\(--[\w-]+\)/.exec(b.color)?.[0] || b.color;
      if (!gruposB.has(k)) gruposB.set(k, Array(n).fill(null));
      const neg = MI.cero !== undefined && b.y >= MI.cero - 0.6 && izq.some(m => m.v < 0);
      const v = (b.tit && decTit(b.tit) !== null) ? decTit(b.tit) : b.alto * MI.k * (neg ? -1 : 1);
      const i = hueco(b.x); const arr = gruposB.get(k);
      arr[i] = (arr[i] ?? 0) + v;
    });
    // la gráfica de concentración pinta el primero de otro color: si cada hueco tiene una sola barra, es una sola serie
    const apiladas = barras.some((b, i) => barras.some((c, j) => j !== i && Math.abs(c.x - b.x) < 0.5));
    let gruposBarras = [...gruposB.entries()];
    if (gruposBarras.length > 1 && !apiladas && barras.length === clB.length && clB.length === n) {
      const una = Array(n).fill(null); gruposBarras.forEach(([, a]) => a.forEach((v, i) => { if (v !== null) una[i] = v; }));
      gruposBarras = [[gruposBarras[0][0], una]];
    }
    const lineasS = [];
    const conDer = !!MD;
    const valY = y => (conDer ? MD.val(y) : MI.val(y));
    const nombreSolo = svg.getAttribute('aria-label') || contexto.split(' · ')[0] || 'Valor';
    trazos.forEach(t => { const arr = Array(n).fill(null); t.pts.forEach(p => { arr[hueco(p.x)] = valY(p.y); }); lineasS.push({ nombre: nombre(t.color, nombreSolo), color: SERIE_COLOR(t.color), y: arr, clave: /var\(--[\w-]+\)/.exec(t.color)?.[0] }); });
    puntos.forEach((pts, col) => {
      const k = /var\(--[\w-]+\)/.exec(col)?.[0];
      const ya = lineasS.find(l => l.clave === k);
      // los puntos (círculos) llevan la posición exacta: mandan sobre la línea, que va redondeada a una décima de píxel
      if (ya) { pts.forEach(p => { ya.y[hueco(p.x)] = valY(p.y); }); return; }
      const arr = Array(n).fill(null); pts.forEach(p => { arr[hueco(p.x)] = valY(p.y); });
      lineasS.push({ nombre: nombre(col, nombreSolo), color: SERIE_COLOR(col), y: arr, clave: k });
    });
    if (tramos.length) {
      const arr = Array(n).fill(null); tramos.forEach(t => { arr[hueco(t.x)] = decTit(t.tit) ?? MI.val(t.y); });
      const nom = (tramos[0].tit.split(':')[1] || 'Presupuesto').replace(/[\d.,]+\s*€.*$/, '').trim();
      lineasS.push({ nombre: nom ? nom[0].toUpperCase() + nom.slice(1) : 'Presupuesto', color: 'var(--bad)', y: arr, ant: true });
    }
    // etiquetas X completas
    const conocidas = new Map(); etX.forEach(t => conocidas.set(hueco(t.x), t.t));
    const x = completarEtiquetas(n, conocidas, anio);
    // formato
    const ticks = [...izq, ...der].map(m => m.t.t).join(' ');
    const esPct = /%/.test(ticks);
    const esEur = !esPct && (/€|k\b|mil/.test(ticks) || /€|inversi|coste|cuota|ingres|gasto|factur/i.test(contexto));
    const todos = [...gruposBarras.flatMap(([, a]) => a), ...lineasS.flatMap(l => l.y)].filter(v => v !== null);
    if (!todos.length) return null;
    const maxAbs = Math.max(...todos.map(Math.abs));
    const enteros = !esEur && !esPct && todos.every(v => Math.abs(v - Math.round(v)) < 0.06);
    const redondear = v => (v === null ? null : enteros ? Math.round(v) : v);
    const dec = enteros ? 0 : maxAbs < 100 ? (esEur ? 2 : 1) : 0;
    const formato = esPct ? v => fmt.pct(v, maxAbs < 10 ? 1 : 0) : esEur ? v => fmt.eur(v, Math.abs(v) < 100 && dec ? dec : 0) : v => fmt.num(v, dec);
    lineasS.forEach(l => { l.y = l.y.map(redondear); });
    // montar grafico(): una serie de barras como mucho; con barras apiladas o agrupadas, el total en barras y cada parte en línea
    let barrasO = null;
    const series = [...lineasS];
    if (gruposBarras.length === 1) {
      const [k, arr] = gruposBarras[0];
      barrasO = { nombre: nombre(k, contexto.split(' · ')[0] || nombreSolo), y: arr.map(redondear), formato, escalaPropia: conDer || undefined };
    } else if (gruposBarras.length > 1) {
      const signos = new Set(gruposBarras.map(([, arr]) => Math.sign(arr.reduce((a, v) => a + (v || 0), 0))));
      if (apiladas && !(signos.has(1) && signos.has(-1))) barrasO = { nombre: 'Total', y: Array.from({ length: n }, (_, i) => redondear(gruposBarras.reduce((a, [, arr]) => a + (arr[i] || 0), 0))), formato, escalaPropia: conDer || undefined };
      gruposBarras.forEach(([k, arr]) => series.push({ nombre: nombre(k, 'Serie'), color: SERIE_COLOR(k), y: arr.map(redondear) }));
    }
    if (series.length > 4) series.splice(4);
    // umbral y notas que el panel escribía dentro del gráfico (objetivo, Accountex…)
    let umbral = null;
    if (umb) {
      const tu = textos.find(t => !usados.has(t.el) && /fill:\s*var\(--bad\)/.test(t.el.getAttribute('style') || ''));
      if (tu) usados.add(tu.el);
      umbral = { y: MI.val(umb.y1), texto: tu?.t || '' };
    }
    const notas = textos.filter(t => !usados.has(t.el) && t.t && numero(t.t) === null).map(t => t.t);
    const fig = grafico({ titulo, x, series, barras: barrasO, formato, formatoX: v => v, umbral, alto: 200, leyenda: series.length + (barrasO ? 1 : 0) > 1 });
    if (!notas.length) return fig;
    return h('div', { class: 'pila' }, fig, h('p', { class: 'sub' }, `En el gráfico: ${notas.join(' · ')}.`));
  } catch (e) {
    console.warn('panel de dirección: gráfico sin traducir', e);
    return null;
  } finally { caja.remove(); }
}

/** Respaldo: el SVG del panel tal cual, sin escalar la letra (12 px reales) y con sus colores llevados a los tokens. */
function svgTalCual(svg) {
  const c = svg.cloneNode(true);
  const vb = (c.getAttribute('viewBox') || '0 0 600 200').split(/\s+/).map(Number);
  c.setAttribute('width', vb[2]); c.setAttribute('height', vb[3]);
  c.querySelectorAll('text').forEach(t => { t.setAttribute('font-size', '12'); t.setAttribute('fill', 'var(--dim)'); t.removeAttribute('class'); });
  return h('div', { class: 'tabla-scroll' }, c);
}

/** «A qué hora se reserva»: barras por hora (alturas relativas) → grafico() con el recuento por hora. */
function graficoHoras(el) {
  const barrasH = [...el.querySelectorAll('.px-hours > i')].map(i => parseFloat(i.style.height) || 0);
  const ejes = [...el.querySelectorAll('.px-hourax > span')].map(texto);
  if (!barrasH.length) return null;
  const min = Math.min(...barrasH.filter(v => v > 0));
  const enteros = barrasH.every(v => Math.abs(v / min - Math.round(v / min)) < 0.02);
  const y = barrasH.map(v => (enteros ? Math.round(v / min) : Math.round(v)));
  const conocidas = new Map(); ejes.forEach((t, i) => { if (t) conocidas.set(i, t); });
  const x = completarEtiquetas(barrasH.length, conocidas, 2026);
  return grafico({ x, barras: { nombre: enteros ? 'Reservas' : '% de la hora con más reservas', y }, formatoX: v => v, formato: v => fmt.num(v), alto: 200 });
}

// ===================================================================== del HTML del panel a los componentes de la app
const ETIQUETAS_OK = new Set(['p', 'b', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'br', 'code', 'details', 'summary', 'span', 'div', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'u']);
const RX_NUM = /^[−+-]?\d[\d.,]*\s?(€|%|h|k|mil|días|meses|€\/día)?$/;

function chipDe(el) {
  const t = texto(el).replace(/^[✕✓–⚑]\s*/, '');
  return chipEstado(ESTADO_TAG(el), t);
}

function filaBarra(etiqueta, valor, pct, estado, nota) {
  return h('div', { class: 'et' }, h('span', {}, etiqueta),
    barraProgreso({ valor: pct, max: 100, estado, etiqueta: `${etiqueta}: ${valor}` }),
    h('span', { class: 'n', title: nota || null }, valor));
}

/** Tabla del panel → table.densa (apilable en el móvil, cifras a la derecha, barras de las celdas como barra de progreso). */
function tablaDe(tabla, ctx) {
  const cabeza = [...tabla.querySelectorAll('thead th')].map(texto);
  const filas = [...tabla.querySelectorAll('tbody > tr, :scope > tr')];
  const numCol = cabeza.map((_, j) => filas.length && filas.filter(tr => RX_NUM.test(texto(tr.children[j]) || 'x') || texto(tr.children[j]) === '—').length >= filas.length * 0.6);
  const celda = (td, j) => {
    const v = texto(td);
    const attrs = { 'data-l': cabeza[j] || null, colspan: td.getAttribute('colspan') || null, title: td.getAttribute('title') || null };
    let cls = j === 0 ? 'principal' : '';
    if (numCol[j] || tieneCl(td, 'px-db')) cls += ' num';
    if (tieneCl(td, 'px-z')) return h('td', { ...attrs, class: `${cls} dim`.trim() }, v);
    if (tieneCl(td, 'px-db')) {
      const i = td.querySelector('i');
      const pct = i ? parseFloat(i.style.width) || 0 : 0;
      return h('td', { ...attrs, class: cls.trim() }, h('div', { class: 'pila' }, h('span', {}, [...td.childNodes].filter(x => x.nodeType === 3).map(x => x.textContent).join('').trim()),
        i ? barraProgreso({ valor: pct, max: 100, estado: ESTADO_COLOR(i.style.background || ''), etiqueta: v }) : null));
    }
    if (tieneCl(td, 'px-strong')) return h('td', { ...attrs, class: cls.trim() }, h('b', {}, v));
    if (tieneCl(td, 'px-name') || tieneCl(td, 'px-fuente')) return h('td', { ...attrs, class: cls.trim() || null },
      h('b', {}, texto(td.querySelector(':scope > b')) || v), [...td.querySelectorAll(':scope > span')].map(s => h('div', { class: 'sub' }, convertirHijos(s, ctx))));
    return apilarCelda(h('td', { ...attrs, class: cls.trim() || null }, convertirHijos(td, ctx)));
  };
  // más de 15 filas: 15 a la vista y «Ver las N filas» (guía 3.8); las demás siguen en la página, ocultas
  const trs = filas.map((tr, i) => h('tr', { hidden: i >= 15 || null }, [...tr.children].map(celda)));
  const mas = trs.length > 15 ? h('div', { class: 'tabla-mas' }, h('button', { type: 'button', class: 'bt', on: { click: e => { trs.forEach(x => { x.hidden = false; }); e.currentTarget.parentElement.remove(); } } },
    `Ver las ${fmt.num(trs.length)} filas`)) : null;
  return h('div', { class: 'pila' }, h('div', { class: 'tabla-scroll' }, h('table', { class: 'densa apilable' },
    cabeza.length ? h('thead', {}, h('tr', {}, cabeza.map((t, j) => h('th', { scope: 'col', class: numCol[j] ? 'num' : null }, t)))) : null,
    h('tbody', {}, trs))), mas);
}

/** El embudo paso a paso del Resumen (px-fun) → tabla: paso y fuente, cuántos (con barra), coste por cada uno; las pérdidas, en su fila. */
function embudoDe(el, ctx) {
  const filas = [];
  hijosEl(el).forEach(f => {
    if (tieneCl(f, 'px-funrow')) {
      const bar = f.querySelector('.px-funbar');
      const pct = parseFloat(bar?.style.width) || 0;
      const v = texto(f.querySelector('.px-funv'));
      filas.push(h('tr', {},
        h('td', { class: 'principal', 'data-l': 'Paso' }, h('b', {}, texto(f.querySelector('.px-funl b'))), h('div', { class: 'sub' }, texto(f.querySelector('.px-srcchip')))),
        h('td', { 'data-l': 'Cuántos', class: 'num' }, h('div', { class: 'pila' }, h('b', {}, v), barraProgreso({ valor: pct, max: 100, etiqueta: v }))),
        h('td', { 'data-l': 'Coste por cada uno', class: 'num' }, texto(f.querySelector('.px-func')) || '—'),
        texto(f.querySelector('.px-funp')) ? h('td', { 'data-l': '' }, texto(f.querySelector('.px-funp'))) : h('td', { 'data-l': '' })));
    } else if (tieneCl(f, 'px-funloss')) {
      filas.push(h('tr', {}, h('td', { colspan: '4', class: 'sub' }, convertirHijos(f.querySelector('span') || f, ctx))));
    }
  });
  return h('div', { class: 'tabla-scroll' }, h('table', { class: 'densa apilable' },
    h('thead', {}, h('tr', {}, ['Paso y fuente', 'Cuántos', 'Coste por cada uno', ''].map((t, j) => h('th', { scope: 'col', class: j ? 'num' : null }, t)))),
    h('tbody', {}, filas)));
}

/** Barra partida (celebradas · ausencias · sin marcar…) → una fila con barra por parte; la leyenda trae las cifras. */
function partidaDe(split, leyenda) {
  const partes = [...split.children].map(d => ({ t: d.getAttribute('title') || '', color: d.style.background || '', n: parseFloat(d.style.flex) || 0 }));
  const total = partes.reduce((a, p) => a + p.n, 0) || 1;
  const textosLey = leyenda ? [...leyenda.children].map(texto) : [];
  return h('div', { class: 'embudo-barras' }, partes.map((p, i) => {
    const [et, val] = p.t.split(':').map(s => s.trim());
    const ley = textosLey.find(t => t.startsWith(et)) || '';
    const pct = /·\s*([\d.,]+ %)/.exec(ley)?.[1];
    return filaBarra(pct ? `${et} · ${pct}` : et, val ?? fmt.num(p.n), (100 * p.n) / total, ESTADO_COLOR(p.color));
  }), textosLey.filter(t => !partes.some(p => t.startsWith((p.t.split(':')[0] || '').trim()))).map(t => h('p', { class: 'sub' }, t)));
}

/** Lista de barras horizontales (px-hlist) → filas con barra de progreso. */
function listaBarras(el) {
  return h('div', { class: 'embudo-barras' }, [...el.querySelectorAll('.px-hrow')].map(r => {
    const hv = r.querySelector('.px-hv');
    const extra = texto(hv?.querySelector('span'));
    const val = [...(hv?.childNodes || [])].filter(x => x.nodeType === 3).map(x => x.textContent).join('').trim() || texto(hv);
    const bar = r.querySelector('.px-htrack > div');
    return filaBarra(extra ? `${texto(r.querySelector('.px-hl'))} · ${extra}` : texto(r.querySelector('.px-hl')), val, parseFloat(bar?.style.width) || 0, ESTADO_COLOR(bar?.style.background || ''));
  }));
}

const tileFig = f => tile({ icono: 'grafico', etiqueta: texto(f.querySelector('span')) || '', valor: texto(f.querySelector('b')) });

/** Reunión (px-reu): resumen en una línea; las notas por fase (la «chispa») pasan a texto dentro. */
function reunionDe(el, ctx) {
  const sum = el.querySelector(':scope > summary');
  const quien = sum?.querySelector('.px-quien');
  const notas = sum?.querySelector('.px-spark')?.getAttribute('title');
  const cuerpo = el.querySelector(':scope > .px-body');
  return h('details', {},
    h('summary', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-1) var(--s-2)', minHeight: 'var(--s-8)' } }, h('b', {}, `${texto(sum?.querySelector('.px-fecha'))} · ${texto(quien?.querySelector('b'))}`),
      texto(quien?.querySelector('span')) ? ` · ${texto(quien.querySelector('span'))} ` : ' ',
      [...(sum?.querySelectorAll('.px-res .px-tag') || [])].map(t => [chipDe(t), ' '])),
    h('div', { class: 'pila' }, notas ? h('p', { class: 'sub' }, `Notas por fase: ${notas}`) : null, cuerpo ? convertirHijos(cuerpo, ctx) : null));
}

/** Barrido v1: celda con cifra en negrita y detalle debajo: el detalle en su línea (antes se pisaban al partir). */
function apilarCelda(td) {
  const hijos = [...td.children];
  if (hijos.length > 1 && hijos.some(x => x.tagName === 'B')) hijos.forEach(x => { if (x.tagName === 'SPAN' && !x.classList.contains('chip')) x.style.display = 'block'; });
  return td;
}
/** Barrido v1: en la frase grande cada cifra en negrita no se parte entre dos líneas (se pisaba con la de al lado). */
function sinPartir(p) { p.querySelectorAll(':scope > b').forEach(b => { b.style.whiteSpace = 'nowrap'; }); return p; }
/** Barrido v1: en las recomendaciones, cada explicación en su propia línea (no pegada a la anterior y pisándola). */
function subsEnBloque(li) { li.querySelectorAll(':scope > span.sub').forEach(s => { s.style.display = 'block'; s.style.marginTop = 'var(--s-1)'; }); return li; }

/** Traduce un nodo del panel. Devuelve un nodo, una lista o null. */
function convertir(el, ctx) {
  if (el.nodeType === 3) return sinRef(el.textContent);
  if (el.nodeType !== 1) return null;
  const tag = el.tagName.toLowerCase();
  if (tag === 'svg') return null;   // los SVG sueltos (chispas) no se pintan: su dato va en texto
  const c = el.classList;
  const sig = el.nextElementSibling;
  // --- piezas del panel
  if (c.contains('px-corr') && ctx.corr) return avisoParcial(`Frase del panel antiguo retirada: daba el margen y el beneficio con el error del dólar. Lo bueno: beneficio de enero a agosto ${fmt.eur(ctx.corr.beneficio)} (${fmt.num(ctx.corr.margen_pct, 1)} % de los ingresos), margen bruto ${fmt.num(ctx.corr.margen_bruto_pct, 1)} %. Fuente: ${ctx.corr.origen}.`, { titulo: 'Corregido por divisa.' });
  if (c.contains('px-panel')) return panelDe(el, ctx);
  if (c.contains('px-kpis')) return tilesDe(el, ctx);
  if (c.contains('px-kgrid')) return tiles(hijosEl(el).map(k => kcardDe(k)));
  if (c.contains('px-kcard')) return tiles([kcardDe(el)]);
  if (c.contains('px-chain') || c.contains('px-gauge') || c.contains('px-scroller')) return null;   // la cadena y el coste por cliente van arriba
  if (c.contains('px-lectura')) return lecturaDe(el, ctx);
  if (c.contains('px-sechead')) return h('div', { class: 'pila' }, el.querySelector('.px-kick') ? h('p', { class: 'sub' }, texto(el.querySelector('.px-kick'))) : null,
    h('h2', { style: H2_SECCION }, icono(iconoDe(texto(el.querySelector('h2'))), { clase: 's' }), texto(el.querySelector('h2'))),
    el.querySelector('.px-lede') ? h('p', { class: 'sub' }, convertirHijos(el.querySelector('.px-lede'), ctx)) : null,
    [...el.querySelectorAll('.px-corr')].map(x => convertir(x, ctx)));
  if (c.contains('px-band')) return h('h2', { style: H2_SECCION }, icono(iconoDe(texto(el)), { clase: 's' }), texto(el));
  if (c.contains('px-alerts')) return tiles(hijosEl(el).map(a => {
    const big = a.querySelector('.px-big');
    const uni = texto(big?.querySelector('small'));
    const ir = a.getAttribute('data-ir');
    return tile({ icono: 'alert', estado: 'ambar', etiqueta: texto(a.querySelector('b')), valor: texto(big).replace(uni, '').trim(), unidad: uni || null,
      ir: texto(a.querySelector('.px-go')).replace(/→/, '').trim() || 'Ver el detalle', alPulsar: ir ? () => ctx.alIr?.(ir) : null });
  }));
  if (c.contains('px-mrrbox')) {
    const big = el.querySelector('.px-mrrbig');
    return tiles([
      tile({ icono: 'euro', etiqueta: texto(big?.querySelector('.px-lab')), valor: texto(big?.querySelector('.px-v')), contexto: texto(big?.querySelector('.px-s')) || null }),
      ...[...el.querySelectorAll('.px-mrrrow')].map(r => tile({ icono: iconoDe(texto(r.querySelector('.px-l'))), etiqueta: texto(r.querySelector('.px-l')), valor: texto(r.querySelector('b')), contexto: texto(r.querySelector('.px-s')) || null })),
    ]);
  }
  if (c.contains('px-chart')) {
    const svg = el.querySelector('svg');
    if (!svg) return null;
    const esLey = x => x && (tieneCl(x, 'px-leg') || tieneCl(x, 'px-finleg'));
    const ley = el.querySelector('.px-leg, .px-finleg') || [el.nextElementSibling, el.parentElement?.nextElementSibling].find(esLey) || el.parentElement?.querySelector(':scope > .px-leg, :scope > .px-finleg');
    const prev = el.previousElementSibling;
    const contexto = [tieneCl(prev, 'px-minihead') ? texto(prev.querySelector('b')) : '', ctx.titulo || '', svg.getAttribute('aria-label') || '', tieneCl(prev, 'px-minihead') ? texto(prev) : ''].filter(Boolean).join(' · ');
    return graficoDe(svg, { leyenda: ley, contexto, anio: ctx.anio }) || svgTalCual(svg);
  }
  if (tag === 'div' && !c.length && el.querySelector(':scope > svg.px-finchart')) {
    const svg = el.querySelector(':scope > svg');
    const ley = [sig].find(x => x && tieneCl(x, 'px-finleg'));
    return graficoDe(svg, { leyenda: ley, contexto: `${ctx.titulo || ''} · ${svg.getAttribute('aria-label') || ''}`, anio: ctx.anio }) || svgTalCual(svg);
  }
  if (c.contains('px-leg') || c.contains('px-finleg')) {
    // leyenda ya usada por su gráfico; si no, en texto
    const prev = el.previousElementSibling;
    if (prev && (tieneCl(prev, 'px-chart') || prev.querySelector?.('svg'))) return null;
    if (el.parentElement && el.parentElement.querySelector('.px-chart')) return null;
    return h('p', { class: 'sub' }, [...el.children].map(texto).join(' · '));
  }
  if (c.contains('px-minihead')) { const tot = el.querySelector('.px-tot'); return h('p', { class: 'fila' }, h('b', {}, texto(el.querySelector('b'))),
    h('span', { class: 'sub' }, [...(tot?.childNodes || [])].map(x => texto(x)).filter(Boolean).join(' '))); }
  if (c.contains('px-split')) return partidaDe(el, tieneCl(sig, 'px-splitleg') ? sig : null);
  if (c.contains('px-splitleg')) return tieneCl(el.previousElementSibling, 'px-split') ? null : h('p', { class: 'sub' }, [...el.children].map(texto).join(' · '));
  if (c.contains('px-hlist')) return listaBarras(el);
  if (c.contains('px-fun')) return embudoDe(el, ctx);
  if (c.contains('px-funhead')) return null;
  if (c.contains('px-twrap')) { const t = el.querySelector('table'); return t ? tablaDe(t, ctx) : null; }
  if (tag === 'table') return tablaDe(el, ctx);
  if (c.contains('px-hourwrap')) return graficoHoras(el);
  if (c.contains('px-pasos')) return h('div', { class: 'pila' }, hijosEl(el).map(p => h('div', { class: 'pila' },
    h('p', {}, h('b', {}, texto(p.querySelector('.px-ph b'))), ' · ', h('b', {}, texto(p.querySelector('.px-pv b'))), h('span', { class: 'sub' }, ` (${texto(p.querySelector('.px-pv span'))})`)),
    h('p', { class: 'sub' }, texto(p.querySelector('.px-ph span'))),
    [...p.querySelectorAll('.px-split')].map(s => partidaDe(s, tieneCl(s.nextElementSibling, 'px-splitleg') ? s.nextElementSibling : null)))));
  if (c.contains('px-supuesto')) {
    const st = el.querySelector('.px-st');
    return h('div', { class: 'pila' },
      h('p', { class: 'fila' }, st?.querySelector('.px-tag2') ? chipEstado(/medido/i.test(texto(st.querySelector('.px-tag2'))) ? 'verde' : 'ambar', texto(st.querySelector('.px-tag2'))) : null, h('b', {}, texto(st?.querySelector('b')))),
      tiles([...el.querySelectorAll('.px-sv > div')].map(d => tile({ icono: iconoDe(texto(d.querySelector('span'))), etiqueta: texto(d.querySelector('span')), valor: texto(d.querySelector('b')) }))));
  }
  if (c.contains('px-best')) return h('div', { class: 'pila' },
    h('p', { class: 'sub' }, texto(el.querySelector('.px-tagline'))), h('p', {}, h('b', {}, texto(el.querySelector('.px-who')))),
    el.querySelector('.px-set') ? h('p', { class: 'sub' }, texto(el.querySelector('.px-set'))) : null,
    tiles([...el.querySelectorAll('.px-fig')].map(tileFig)));
  if (c.contains('px-figs')) return tiles([...el.querySelectorAll('.px-fig')].map(tileFig));
  if (c.contains('px-pat')) {
    // patrón de las reuniones: cifra + frase completa (con las reuniones de referencia, R31…, para buscarlas en Ventas)
    const nm = el.querySelector('.px-nm');
    const cuenta = [...(nm?.childNodes || [])].filter(x => x.nodeType === 3).map(x => x.textContent).join('').trim();
    return h('div', { class: 'pila' }, h('p', {}, h('b', {}, texto(el.querySelector('.px-tx b')))),
      h('p', { class: 'fila' }, h('b', {}, cuenta), texto(nm?.querySelector('small')) ? chipEstado('azul', texto(nm.querySelector('small'))) : null),
      texto(el.querySelector('.px-tx span')) ? h('p', { class: 'sub' }, texto(el.querySelector('.px-tx span'))) : null);
  }
  if (tag === 'details' && c.contains('px-reu')) return reunionDe(el, ctx);
  if (tag === 'details' && c.contains('px-srcd')) {
    const sum = el.querySelector(':scope > summary');
    return h('details', {}, h('summary', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-1) var(--s-2)', minHeight: 'var(--s-8)' } }, chipEstado(/✓/.test(texto(sum?.querySelector('.px-okdot'))) ? 'verde' : 'ambar', texto(sum?.querySelector('b'))), ' ', h('span', { class: 'sub' }, texto(sum?.querySelector('span:not(.px-okdot)')))),
      h('div', { class: 'pila' }, convertirHijos(el.querySelector('.px-srcb') || el, ctx)));
  }
  if (tag === 'details') {
    const sum = el.querySelector(':scope > summary');
    const resto = [...el.childNodes].filter(x => x !== sum);
    return h('details', { class: (c.contains('px-howd') || c.contains('px-fold') || c.contains('px-v29')) && texto(sum).length <= 36 ? 'que-es' : null }, h('summary', {}, texto(sum)),
      h('div', { class: 'pila' }, resto.map(x => convertir(x, ctx))));
  }
  if (c.contains('px-tag') || c.contains('px-pill') || c.contains('px-tag2')) return chipDe(el);
  if (c.contains('px-crmstrip') || c.contains('px-hnote') || c.contains('px-lede') || c.contains('px-aux') || c.contains('px-kick') || c.contains('px-kc-lee') || c.contains('px-kc-src'))
    return h('p', { class: 'sub' }, convertirHijos(el.matches('div') && el.querySelector('p') ? el.querySelector('p') : el, ctx));
  if (c.contains('px-empty')) return vacioLinea(h('span', {}, convertirHijos(el, ctx)));
  if (c.contains('px-big')) return sinPartir(h('p', { class: 'lead' }, convertirHijos(el, ctx)));
  if (c.contains('px-recs') || c.contains('px-avisos')) return h('ol', { class: 'pila' }, [...el.children].map(li => subsEnBloque(h('li', {}, convertirHijos(li, ctx)))));
  if (c.contains('px-n') || c.contains('px-c')) return h('span', { class: 'sub' }, ' ', convertirHijos(el, ctx));
  if (c.contains('px-quote')) return h('li', {}, convertirHijos(el, ctx));
  if (c.contains('px-meta')) return h('div', { class: 'meta-linea' }, [...el.children].map(s => h('span', {}, convertirHijos(s, ctx))));
  if (c.contains('px-grid2') || c.contains('px-grid3')) return h('div', { class: 'rejilla' }, hijosEl(el).map(x => h('div', { class: 'pila' }, convertir(x, ctx))));
  if (c.contains('px-name') || c.contains('px-fuente')) return [h('b', {}, texto(el.querySelector('b')) || texto(el)), ...[...el.querySelectorAll(':scope > span')].map(s => h('div', { class: 'sub' }, texto(s)))];
  if (c.contains('px-ic') || c.contains('px-chev') || c.contains('px-sw') || c.contains('px-spark') || c.contains('px-spark2') || c.contains('px-ring') || c.contains('px-zone') || c.contains('px-okdot')) return null;
  // --- etiquetas sueltas
  if (/^h[2-6]$/.test(tag)) return h('p', {}, h('b', {}, texto(el)));
  if (tag === 'small') return h('span', { class: 'sub' }, ' ', texto(el));
  if (tag === 'i' && !texto(el)) return null;
  if (tag === 'i') return h('em', {}, texto(el));
  if (tag === 'a') { const href = el.getAttribute('href'); return href ? h('a', { href, target: /^https?:/.test(href) ? '_blank' : null, rel: 'noopener' }, texto(el)) : texto(el); }
  if (tag === 'span' && /--(warn|bad)-ink/.test(el.getAttribute('style') || '')) return h('div', { class: 'sub' }, texto(el));
  if (tag === 'ul' || tag === 'ol') return h(tag, {}, [...el.children].map(li => convertir(li, ctx)));
  if (!ETIQUETAS_OK.has(tag)) return convertirHijos(el, ctx);
  if (tag === 'div') {
    const kids = convertirHijos(el, ctx);
    const bloques = hijosEl(el).length;
    return h('div', { class: bloques > 1 ? 'pila' : null }, kids);
  }
  return h(tag, { title: el.getAttribute('title') || null }, convertirHijos(el, ctx));
}
function convertirHijos(el, ctx) { return [...(el?.childNodes || [])].map(x => convertir(x, ctx)); }

/** Tarjeta de indicador del v29 (px-kcard) → tile. */
function kcardDe(k) {
  const etiqueta = texto(k.querySelector('.px-lab'));
  return tile({ icono: iconoDe(etiqueta), etiqueta, valor: texto(k.querySelector('.px-val')), estado: tieneCl(k, 'px-flag') ? 'ambar' : '',
    contexto: [texto(k.querySelector('.px-kc-lee')), texto(k.querySelector('.px-kc-src'))].filter(Boolean).join(' · ') || null });
}

/** Resumen del periodo (px-lectura): una frase a 15/22 con las cifras en 600; lo de apoyo, debajo y en gris. */
function lecturaDe(el, ctx) {
  return h('div', { class: 'pila' }, [...el.children].map(p => (tieneCl(p, 'px-corr') ? convertir(p, ctx) : tieneCl(p, 'px-big') ? sinPartir(h('p', { class: 'lead' }, convertirHijos(p, ctx))) : h('p', { class: 'sub' }, convertirHijos(p, ctx)))));
}

/** Tiles del v29 que dependen del gasto del cierre (error de divisa): se cambian por la cifra buena (corr) o se marcan. */
function corregirTile(etiqueta, valor, sub, corr) {
  if (!corr) return null;
  const pct = n => n == null ? '—' : `${fmt.num(n, 1)} %`;
  if (/^beneficio/i.test(etiqueta)) return { valor: fmt.eur(corr.beneficio), estado: colorCifra('beneficio', corr.beneficio), contexto: `ene-ago, ${pct(corr.margen_pct)} de los ingresos · con el gasto sin factura ${fmt.eur(corr.beneficio_real)} · corregido por divisa (el panel antiguo decía ${valor})` };
  if (/^margen/i.test(etiqueta) && !/que deja/i.test(etiqueta)) return { valor: pct(corr.margen_bruto_pct), estado: '', contexto: `corregido por divisa (el panel antiguo decía ${valor})` };
  if (/^caja a 31/i.test(etiqueta)) return { valor, estado: '', contexto: 'saldo en bancos a 31-ago (este sí vale) · los «meses sin cobrar» del cierre usaban el gasto inflado: no se enseñan' };
  if (/gasto|resultado/i.test(etiqueta)) return { valor, estado: 'ambar', contexto: `Cifra del cierre con el error del dólar: la buena, en «Resumen financiero». ${sub}` };
  return null;
}

/** R12 (A-A6): «Margen que deja, vida medida» del v29 usaba su margen bruto (29 %, con el error del dólar). Se rehace con el
 *  margen bruto ÚNICO de Finanzas (direccion.kpi.mb, el mismo de toda la app) y las tres cifras que el propio panel enseña en
 *  la tarjeta de al lado («22.050 €/mes × 7,2 meses ÷ 11.085 €»): cuota × vida × margen − inversión. Si no se pueden leer,
 *  «sin dato»: nunca la cifra con el margen malo. */
function margenQueDeja(kpis, mb) {
  if (mb === null || mb === undefined) return { valor: null, contexto: 'Sin el margen bruto de Finanzas no se calcula (el del panel antiguo lleva el error del dólar)' };
  const subs = [...kpis.querySelectorAll('.px-sub')].map(texto);
  const m = subs.map(t => t.match(/([\d.]+)\s*€\/mes\s*×\s*([\d.,]+)\s*meses\s*÷\s*([\d.]+)\s*€/)).find(Boolean);
  if (!m) return { valor: null, contexto: `Margen bruto ${fmt.num(mb, 1)} % (Finanzas); no se han podido leer cuota, vida e inversión del panel` };
  const n = t => Number(String(t).replace(/\./g, '').replace(',', '.'));
  const cuota = n(m[1]), vida = n(m[2]), inv = n(m[3]);
  const v = cuota * vida * (mb / 100) - inv;
  return { valor: fmt.eur(Math.round(v)), estado: colorCifra('beneficio', v),
    contexto: `${fmt.eur(cuota)}/mes × ${fmt.num(vida, 1)} meses × margen bruto ${fmt.num(mb, 1)} % − ${fmt.eur(inv)} de publicidad · el margen es el de Finanzas (ene-ago, gasto corregido), el mismo de toda la app` };
}

function tilesDe(kpis, ctx) {
  const { guardaTile, corr } = ctx;
  const lista = [...kpis.children].filter(x => x.classList.contains('px-tile')).map(t => {
    const val = t.querySelector('.px-val');
    const u = texto(val?.querySelector('.px-u'));
    const valor = texto(val).replace(u, '').trim();
    const etiqueta = texto(t.querySelector('.px-lab'));
    const sub = texto(t.querySelector('.px-sub')) || '';
    if (/margen que deja/i.test(etiqueta)) {
      const mq = margenQueDeja(kpis, ctx.mb ?? corr?.margen_bruto_pct);
      return tile({ icono: iconoDe(etiqueta), etiqueta, valor: mq.valor, sinDato: 'falta el margen bruto de Finanzas', estado: mq.estado || '', contexto: mq.contexto });
    }
    const c = corregirTile(etiqueta, valor, sub, corr);
    if (c) return tile({ icono: iconoDe(etiqueta), etiqueta: c.valor === valor ? etiqueta : `${etiqueta} · corregido`, valor: c.valor, unidad: c.valor === valor ? (u || null) : null, estado: c.estado, contexto: c.contexto });
    const tocado = guardaTile && guardaTile.test(etiqueta);
    // coste por cliente: la regla común (colorCifra), la misma en Ventas de RO
    const estado = /coste por cliente/i.test(etiqueta) ? colorCifra('coste_cliente', numero(valor)) : tocado ? 'ambar' : '';
    return tile({ icono: iconoDe(etiqueta), etiqueta, valor, unidad: u || null, estado,
      contexto: ((tocado ? `Cifra del panel antiguo con su margen bruto, que lleva el error del dólar; el bueno es el de Finanzas (${ctx.mb != null ? fmt.num(ctx.mb, 1) + ' %' : 'sin dato'}). ` : '') + sub) || null });
  });
  const resto = [...kpis.children].filter(x => !x.classList.contains('px-tile')).map(x => convertir(x, ctx));
  return lista.length ? h('div', { class: 'pila' }, tiles(lista), resto) : h('div', {}, resto);
}

function panelDe(p, ctx) {
  const cab = p.querySelector(':scope > .px-phead');
  const titulo = texto(cab?.querySelector('h3')) || null;
  const sub = texto(cab?.querySelector('.px-hint')) || null;
  const resto = [...p.childNodes].filter(x => x !== cab);
  const tocado = titulo && (ctx.guarda || []).some(rx => rx.test(titulo));
  const sctx = { ...ctx, titulo: titulo || ctx.titulo };
  const contenido = resto.map(x => convertir(x, sctx));
  const cuerpo = tocado
    ? h('div', { class: 'cuerpo pila' }, avisoParcial(AVISO_DIVISA, { titulo: 'No usar estas cifras de gasto.' }),
      h('details', { class: 'que-es' }, h('summary', {}, 'Ver la versión del panel antiguo'), h('div', { class: 'pila' }, contenido)))
    : h('div', { class: 'cuerpo pila' }, contenido);
  if (!titulo) return h('section', { class: 'panel' }, cuerpo);
  return panel({ titulo, sub: tocado ? `${sub ? sub + ' · ' : ''}corregido respecto al panel antiguo por error de divisa` : sub, icono: iconoDe(titulo) }, cuerpo);
}

/** Monta un fragmento del panel con los componentes de la app. ctx: { alIr, guarda, guardaTile, corr, anio, quitarLectura, primeroAvisos } */
function montar(html, ctx = {}) {
  const r = parsear(html);
  if (ctx.corr) {
    // frases del v29 que dan margen, beneficio o «meses sin cobrar» con el error del dólar: se retiran con la cifra buena al lado
    r.querySelectorAll('.px-lede, .px-big, .px-aux, .px-hnote, .px-lectura > p').forEach(p => {
      if (!/margen bruto|de beneficio|beneficio baja|meses sin cobrar|gasto medio|caja para/i.test(texto(p))) return;
      const nuevo = document.createElement('div'); nuevo.className = 'px-corr'; nuevo.dataset.texto = 'si';
      p.replaceWith(nuevo);
    });
  }
  if (ctx.quitarLectura) r.querySelectorAll(':scope > .px-lectura').forEach(x => x.remove());
  // lo que pide acción va lo primero (guía 3.6): «Qué mirar hoy» y sus avisos suben al principio de la pestaña
  if (ctx.primeroAvisos) {
    const alertas = r.querySelector(':scope > .px-alerts');
    if (alertas) { const banda = alertas.previousElementSibling; if (tieneCl(banda, 'px-band')) r.prepend(banda, alertas); else r.prepend(alertas); }
  }
  // V2-E (M17): en el móvil, de la 3.ª sección en adelante va plegada con su título y una línea (pieza común)
  return plegarSecundarias(prosaSinPisar(h('div', { class: 'pila' }, [...r.childNodes].map(x => convertir(x, ctx)))), { desde: 2 });
}

/** Barrido v1: en la prosa del panel, una negrita larga que parte línea se «pisaba» con el texto de al lado; como
 *  bloque en línea (inline-block) ocupa su propio rectángulo. Las cortas se ven igual. */
function prosaSinPisar(raiz) {
  raiz.querySelectorAll('p > b, p > span.sub, li > b').forEach(x => { if (!x.style.display) x.style.display = 'inline-block'; });
  return raiz;
}

// ===================================================================== carga
const cache = new Map();
async function cargar(ctx, nombre) {
  if (cache.has(nombre)) return cache.get(nombre);
  const p = ctx.datosModulo(`panel_direccion/${nombre}`).catch(e => { cache.delete(nombre); throw e; });
  cache.set(nombre, p);
  return p;
}

function pieFuentes(ind) {
  const hoy = (ind.ventana?.to || '').slice(0, 10);
  const fuentes = (ind.fuentes || []).map(([f, fecha, nota]) => {
    const viejo = fecha.slice(0, 10) < hoy && !['Excel de cierre', 'Airtable'].includes(f);
    const el = frescura({ fuente: f, fecha, estado: viejo ? 'viejo' : 'ok' });
    if (nota) el.title = `${f}: ${nota} (${fecha})`;
    return el;
  });
  return h('div', { class: 'pila' },
    h('p', { class: 'sub' }, `Foto del panel del ${fDiaRO(ind.foto_panel?.slice(0, 10))} a las ${ind.foto_panel?.slice(11, 16)} (hora de Madrid) · montado en la app el ${ind.generado}. Lleva nombres de personas: no se reenvía.`),
    h('div', { class: 'fila' }, fuentes));
}

// ===================================================================== la captación
/** Arriba de la captación: la cifra que manda (coste por cliente firmado, con la regla común) y el resumen del periodo. */
function cabeceraCaptacion(html, ctx) {
  const r = parsear(html);
  const gauge = r.querySelector('.px-gauge');
  const lectura = r.querySelector('.px-lectura');
  let cifra = null;
  if (gauge) {
    const v = gauge.querySelector('.px-v');
    const pill = v?.querySelector('.px-pill');
    const valor = texto(v).replace(texto(pill), '').trim();
    const n = numero(valor);
    const fill = gauge.querySelector('.px-fill');
    const marca = gauge.querySelector('.px-mark');
    const extremos = [...gauge.querySelectorAll('.px-ends span')].map(texto);
    const limite = numero(texto(marca)) ?? 700;
    const tope = numero(extremos[1]) ?? limite * 2;
    cifra = h('div', { class: 'pila' },
      cifraPrincipal({ etiqueta: texto(gauge.querySelector('.px-gt > b')) || 'Coste por cliente firmado', valor: valor.replace(/\s*€$/, ''), unidad: '€',
        estado: n === null ? 'gris' : colorCifra('coste_cliente', n), comparacion: `${texto(pill).replace(/^[✕✓–]\s*/, '')} · tu límite, firmado el 2-sep · la misma cuenta y el mismo color que Ventas de RO con el mismo periodo (allí, por defecto, los últimos 30 días)` }),
      barraProgreso({ valor: n ?? 0, max: tope, marca: limite, estado: n === null ? null : colorCifra('coste_cliente', n), etiqueta: `${valor} frente al límite de ${fmt.eur(limite)}` }),
      h('p', { class: 'sub' }, `${texto(gauge.querySelector('.px-s'))} · la barra va de ${extremos[0] || '0 €'} a ${extremos[1] || fmt.eur(tope)}; la marca es el límite de ${fmt.eur(limite)}${fill ? '' : ''}.`));
  }
  lectura?.querySelectorAll('.px-kick').forEach(k => k.remove());   // las fechas ya las dice el selector de periodo
  const resumen = lectura ? lecturaDe(lectura, ctx) : null;
  if (!cifra && !resumen) return null;
  return h('section', { class: 'panel' }, h('div', { class: 'cuerpo pila' }, cifra, resumen));
}

function tilesCadena(html, alIr) {
  // La cadena del coste del Resumen (inversión → citas → celebradas → de venta → firmados → cobrados), como tiles de la app.
  const r = parsear(html);
  const etapas = [...r.querySelectorAll('.px-chain .px-stage')];
  if (!etapas.length) return null;
  const IR = ['pub', 'res', 'res', 'vent', 'vent', 'vent'];
  return tiles(etapas.map((s, i) => {
    const etiqueta = texto(s.querySelector('.px-lab'));
    const coste = texto(s.querySelector('.px-cost'));
    const sub = [...s.querySelectorAll('.px-sub')].map(texto).filter(Boolean).join(' · ');
    const delta = texto(s.querySelector('.px-delta'));
    return tile({ icono: ['cartera', 'cal', 'video', 'crown', 'ok', 'euro'][i] || 'grafico', etiqueta, valor: texto(s.querySelector('.px-val')),
      comparacion: delta ? { texto: delta } : null,
      contexto: [coste, sub].filter(Boolean).join(' · ') || null, alPulsar: () => alIr(IR[i] || 'sum'), ir: 'Ver el detalle' });
  }));
}

async function pintarCaptacion(zona, ctx, ind) {
  const rangos = ind.rangos || {};
  const dias = id => { const r = rangos[id]; return r ? Math.round((new Date(r.hasta) - new Date(r.desde)) / 864e5) + 1 : 0; };
  const porDefecto = dias('oct') >= 7 ? 'oct' : 'sep';   // como el panel («este mes»), salvo los primeros días del mes
  // nombres cortos para que los 5 quepan en una fila también en el móvil
  const CORTO = { sep: 'Sept.', oct: 'Oct.', todo: 'Desde 1-ago', d14: 'Desde 14-sep', d7: '7 días' };
  const opciones = (ind.periodos || []).map(p => ({ valor: p.id, texto: CORTO[p.id] || p.texto,
    comparacion: rangos[p.id] ? `${p.texto} · ${fDiaRO(rangos[p.id].desde)} – ${fDiaRO(rangos[p.id].hasta)} · todas las capas · por fecha del hecho` : '' }));
  const cuerpo = h('div', { class: 'pila' });
  let tabsEl = null;
  const anio = Number((ind.ventana?.to || '2026').slice(0, 4));
  // R12 (A-A6): un solo margen bruto en toda la app, el de Finanzas (direccion.kpi.mb)
  const mb = await leerFinanzas(ctx).then(f => (Array.isArray(f?.direccion) ? f.direccion[0]?.kpi?.mb : null) ?? null).catch(() => null);
  const pintarPeriodo = async periodo => {
    cuerpo.replaceChildren(esqueleto({ lineas: 3, tarjetas: 3 }));
    let d;
    try { d = await cargar(ctx, `captacion_${periodo}`); }
    catch (e) { cuerpo.replaceChildren(vacio({ icono: 'alert', tono: 'aviso', titulo: 'No se han podido leer los datos de este periodo', texto: e.message, quien: 'el equipo técnico' })); return; }
    const P = d.pestanas || {};
    const alIr = id => tabsEl?.elegir(id);
    const etq = ind.etiquetas || {};
    const activa = tabsEl?.activa?.();
    tabsEl = pestanas({
      pestanas: TABS_CAPTACION.map(t => ({ id: t.id, texto: etq[t.id] || t.id, icono: t.icono })),
      activa, clave: 'panel-direccion-cap', etiqueta: 'La captación',
      pintar: (id, z) => {
        z.append(P[id] ? montar(P[id], { alIr, guardaTile: /margen/i, mb, anio, quitarLectura: id === 'sum', primeroAvisos: id === 'sum' })
          : vacioLinea('Esta pestaña no tiene datos en este periodo: el panel no pintó nada para estas fechas.'));
      },
    });
    cuerpo.replaceChildren(cabeceraCaptacion(P.sum, {}) || h('span'), tilesCadena(P.sum, alIr) || h('span'), tabsEl);
  };
  const sel = selectorPeriodo({ opciones, valor: porDefecto, clave: 'panel-direccion', alCambiar: v => pintarPeriodo(v) });
  zona.append(sel, cuerpo);
  await pintarPeriodo(sel.valor());
}

// ===================================================================== la empresa
function irAFinanzas(pestana) {
  try { sessionStorage.setItem('ro.pestana.finanzas', pestana); } catch { /* sin almacenamiento */ }
  location.hash = '#/finanzas';
}

/** Gasto, beneficio, margen, peso del equipo y meses de caja: UNA sola fuente, Finanzas (M19) recalculado (data/finanzas/finanzas.json →
 *  direccion[0]). Aquí no se calcula nada. «m19» dice si M19 ya lleva el arreglo de divisa (trae las cifras del cierre al lado). */
function corregidas(fin, cd) {
  const dir = Array.isArray(fin?.direccion) ? fin.direccion[0] : null;
  if (!dir) return null;
  const v29 = cd?.v29 || {};
  const m19 = dir.anio?.gas_cierre != null || (dir.anio?.bai != null && Math.abs(dir.anio.bai - v29.beneficio_ene_ago) > 1);
  return { m19, origen: m19 ? `Finanzas, recalculado con Holded convertido · ${fin.generado}` : `Finanzas · ${fin.generado} · AÚN SIN RECALCULAR: el gasto puede llevar el error del dólar`,
    ingresos: dir.anio?.ing, gastos: dir.anio?.gas, beneficio: dir.anio?.bai, beneficio_real: dir.anio?.real,
    gastos_v29: dir.anio?.gas_cierre ?? v29.gastos_ene_ago, beneficio_v29: dir.anio?.bai_cierre ?? v29.beneficio_ene_ago,
    margen_pct: dir.kpi?.bai, margen_real_pct: dir.kpi?.bai_real, margen_bruto_pct: dir.kpi?.mb,
    peso_equipo_anio: dir.kpi?.peso_equipo_anio, peso_equipo_mes: dir.equipo?.peso_ingresos, mes_cierre: dir.equipo?.cierre_mes || dir.numero?.mes,
    mes: dir.numero?.mes, beneficio_mes: dir.numero?.beneficio, beneficio_real_mes: dir.numero?.beneficio_real,
    meses_caja: dir.caja?.meses, caja_texto: dir.caja?.texto, filas: (dir.pyg || []).map(x => ({ m: x.m, ing: x.ing, gas: x.gas, bai: x.bai })) };
}
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const mesTxt = m => m ? `${MESES[+m.slice(5, 7) - 1]} ${m.slice(0, 4)}` : '—';

// M19 deja lo de dirección en data/finanzas/direccion.json ({"puestos": ["direccion", "finanzas_direccion"]}); si no está, en
// finanzas.json → direccion. Se devuelve siempre { generado, direccion: [ {...} ] }. Un fallo no se guarda (se reintenta).
let finCache = null;
async function leerFinanzas(ctx) {
  if (finCache) return finCache;
  const conDir = x => Array.isArray(x?.direccion) && x.direccion.length ? x : null;
  let f = conDir(await ctx.datosModulo('finanzas/direccion').catch(() => null));
  if (!f) f = conDir(await ctx.datosModulo('finanzas/finanzas').catch(() => null));
  if (f) finCache = f;
  return f;
}

async function tilesFinanzas(ctx) {
  // Las mismas cifras que Finanzas (en vivo): no se recalculan aquí. El beneficio, corregido por el error de divisa.
  const f = await leerFinanzas(ctx);
  const dir = Array.isArray(f?.direccion) ? f.direccion[0] : null;
  if (!dir) return null;
  const cr = dir.cuota_recurrente || {}, caja = dir.caja || {};
  const c = corregidas(f, null);
  return h('div', { class: 'pila' },
    h('h2', { style: H2_SECCION }, icono('zap', { clase: 's' }), `En vivo · Finanzas de la empresa · ${f.generado}`),
    tiles([
      c ? tile({ icono: 'grafico', etiqueta: `Beneficio de ${mesTxt(c.mes)}`, valor: fmt.eur(c.beneficio_mes), estado: colorCifra('beneficio', c.beneficio_mes), contexto: `${c.m19 ? 'corregido (el panel antiguo decía −61 €)' : 'Finanzas sin recalcular'} · con el gasto sin factura ${fmt.eur(c.beneficio_real_mes)}` }) : null,
      tile({ icono: 'euro', etiqueta: 'Cuota recurrente firmada', valor: fmt.eur(cr.actual), contexto: `${fmt.num(cr.clientes)} clientes · Airtable de octubre ${fmt.eur(cr.facturacion_airtable)} + firmas sin alta`, href: '#/finanzas', ir: 'Abrir Finanzas' }),
      tile({ icono: 'crown', etiqueta: 'Si firman los pendientes', valor: fmt.eur(cr.si_firman), contexto: `${(cr.pendientes || []).length} acuerdos enviados · objetivo de diciembre ${fmt.eur(cr.objetivo_dic)}`, href: '#/finanzas', ir: 'Abrir Finanzas' }),
      tile({ icono: 'cartera', etiqueta: 'Caja hoy', valor: fmt.eur(caja.total), contexto: c?.m19 && caja.meses ? `${fmt.num(caja.meses, 1)} meses si no entrara nada · Holded en vivo` : 'Holded en vivo · los «meses de caja» del cierre usan el gasto inflado: no se enseñan', href: '#/finanzas', ir: 'Abrir Finanzas' }),
    ]));
}

/** «Resumen financiero» nativo: cifras de gasto corregidas + lo que del v29 no depende del gasto + el v29 plegado. */
async function pintarResumenFinanciero(z, ctx, ind, htmlV29, alIr) {
  const cd = ind.correccion_divisa || {};
  const f = await leerFinanzas(ctx);
  const c = corregidas(f, cd);
  const v29 = cd.v29 || {};
  if (!c) { z.append(vacioLinea('Sin Finanzas: las cifras de gasto y beneficio salen solo de allí y no se han podido leer.', { icono: 'alert', quien: 'Agus' })); return; }
  const dir = Array.isArray(f?.direccion) ? f.direccion[0] : null;
  // tiles del v29 que no dependen del gasto (cuota, ingresos, clientes, retención, rotación, LTV, coste por cliente)
  const r = parsear(htmlV29);
  const portados = [...r.querySelectorAll('.px-tile, .px-kcard')].map(t => {
    const etiqueta = texto(t.querySelector('.px-lab'));
    if (!etiqueta || !SIN_GASTO(etiqueta)) return null;
    const val = t.querySelector('.px-val');
    const u = texto(val?.querySelector('.px-u'));
    const valor = texto(val).replace(u, '').trim();
    return tile({ icono: iconoDe(etiqueta), etiqueta, valor, unidad: u || null, estado: /coste por cliente/i.test(etiqueta) ? colorCifra('coste_cliente', numero(valor)) : '',
      contexto: [texto(t.querySelector('.px-sub, .px-kc-lee')), texto(t.querySelector('.px-kc-src'))].filter(Boolean).join(' · ') || null });
  }).filter(Boolean);
  z.append(h('div', { class: 'pila' },
    h('h2', { style: H2_SECCION }, icono('euro', { clase: 's' }), 'Dinero · enero a agosto de 2026 · corregido'),
    tiles([
      tile({ icono: 'grafico', etiqueta: 'Beneficio ene-ago', valor: fmt.eur(c.beneficio), estado: colorCifra('beneficio', c.beneficio), contexto: `${fmt.num(c.margen_pct, 1)} % de los ingresos · el panel antiguo decía ${fmt.eur(c.beneficio_v29)} (${fmt.num(v29.margen_pct, 1)} %)` }),
      tile({ icono: 'euro', etiqueta: 'Ingresos ene-ago', valor: fmt.eur(c.ingresos), contexto: 'Holded al céntimo · igual que el panel antiguo' }),
      tile({ icono: 'maletin', etiqueta: 'Gastos ene-ago', valor: fmt.eur(c.gastos), contexto: `el panel panel antiguo decía ${fmt.eur(c.gastos_v29)} (dólares como euros)` }),
      tile({ icono: 'alert', etiqueta: 'Beneficio con el gasto sin factura', valor: fmt.eur(c.beneficio_real), estado: colorCifra('beneficio', c.beneficio_real), contexto: `${fmt.num(c.margen_real_pct, 1)} % · el gasto sin factura es un techo · el panel antiguo decía ${fmt.eur(v29.beneficio_real_ene_ago)}` }),
      tile({ icono: 'sube', etiqueta: 'Margen bruto ene-ago', valor: c.margen_bruto_pct != null ? `${fmt.num(c.margen_bruto_pct, 1)} %` : null, contexto: `ingresos menos equipo y entrega · el panel antiguo decía ${fmt.num(v29.margen_bruto_pct, 1)} %` }),
      tile({ icono: 'eq', etiqueta: 'Peso del equipo', valor: c.peso_equipo_anio != null ? `${fmt.num(c.peso_equipo_anio, 1)} %` : null, contexto: `ene-ago · en ${mesTxt(c.mes_cierre)} ${fmt.num(c.peso_equipo_mes, 1)} % · el panel antiguo decía ${fmt.num(v29.peso_equipo_pct, 1)} % y ${fmt.num(v29.peso_equipo_ago_pct, 1)} %. Solo agregado` }),
      tile({ icono: 'cartera', etiqueta: 'Meses de caja si no entrara nada', valor: c.m19 && c.meses_caja != null ? fmt.num(c.meses_caja, 1) : null, unidad: 'meses', contexto: `caja de hoy ÷ gasto medio corregido · flujo neto del año ${fmt.eurSigno(dir?.caja?.flujo_neto_anio)} · el «1,4» del panel antiguo no vale` }),
      tile({ icono: 'escudo', etiqueta: 'Corrección por divisa', valor: fmt.eurSigno(-(cd.efecto_gasto_ene_ago || 0)), unidad: 'de gasto', contexto: `de enero a agosto · ${c.m19 ? 'ya aplicada' : 'aún sin aplicar'} · ${c.origen}` }),
    ]),
    panel({ titulo: 'Mes a mes · 2026 · corregido', icono: 'cal', sub: `Ingresos, gastos y beneficio según facturas · ${c.origen}` },
      h('div', { class: 'cuerpo pila' },
        grafico({ x: c.filas.map(x => x.m), series: [{ nombre: 'Ingresos', y: c.filas.map(x => x.ing) }, { nombre: 'Gastos', y: c.filas.map(x => x.gas) }],
          barras: { nombre: 'Beneficio', y: c.filas.map(x => x.bai), formato: v => fmt.eur(v) }, formato: v => fmt.eur(v), alto: 200 }),
        tablaApilable({ filas: c.filas, columnas: [
          { clave: 'm', titulo: 'Mes', principal: true, celda: x => mesTxt(x.m) },
          { clave: 'ing', titulo: 'Ingresos', num: true, celda: x => fmt.eur(x.ing) },
          { clave: 'gas', titulo: 'Gastos', num: true, celda: x => fmt.eur(x.gas) },
          { clave: 'bai', titulo: 'Beneficio', num: true, celda: x => chipEstado(colorCifra('beneficio', x.bai), fmt.eur(x.bai)) }],
        vacio: { titulo: 'Sin serie mensual', texto: 'Ni Finanzas ni la auditoría traen la serie.' } }))),
    h('h2', { style: H2_SECCION }, icono('users', { clase: 's' }), 'Cuota, clientes y captación · igual que el panel antiguo (no dependen del gasto)'),
    portados.length ? tiles(portados) : vacioLinea('No se han encontrado los indicadores del v29.'),
    dir ? avisoParcial(`Cuota firmada hoy ${fmt.eur(dir.cuota_recurrente?.actual)} (Finanzas, en vivo) frente a los ${texto(r.querySelector('.px-tile .px-val'))} de cuota de octubre del panel antiguo (Airtable del 27-sep): la de Finanzas suma las firmas que aún no tienen línea en facturación.`, { tipo: 'info', titulo: 'Cuota:' }) : null,
    avisoParcial(`${AVISO_DIVISA} Fuente única de gasto, beneficio, margen, peso del equipo y meses de caja: ${c.origen}.`, { tipo: c.m19 ? 'info' : 'parcial', titulo: c.m19 ? 'Corregido.' : 'Ojo.' }),
    h('details', { class: 'que-es' }, h('summary', {}, 'Ver el resumen del panel antiguo tal cual'),
      h('div', { class: 'pila' }, avisoParcial(`${AVISO_DIVISA} Tampoco valen sus «meses de caja» (usan todo el gasto como si no entrara nada).`, { titulo: 'No usar estas cifras de gasto.' }),
        montar(htmlV29, { alIr, anio: 2026 })))));
}

function bloqueEquipo(ctx) {
  // Regla del 2-oct: los sueldos se ven en la app, solo dirección y RRHH (Tomás y Cecilia), y cada apertura queda en el rastro.
  // Almacén privado de E0: data/sueldos/_privado/sueldos.json (tipo «sueldos»), persona a persona con ctx.verDato.
  // Nunca la hoja «Cuentas bancarias» (E0 no la lee). En «ver como» mandan los permisos de la persona vista.
  const personas = (ctx.datos.personas || []).filter(p => p.estado !== 'baja' && !p.prueba)
    .sort((a, b) => String(a.alias || a.nombre).localeCompare(String(b.alias || b.nombre), 'es'));
  const ALM = 'sueldos/_privado/sueldos';
  let declarado = null;
  const comprobar = async () => {
    if (declarado === null) declarado = ((await ctx.almacenesPrivados?.()) || []).some(k => k.startsWith('sueldos/'));   // L-26: por ctx, no por fetch
    return declarado;
  };
  const celdaCoste = p => {
    const caja = h('span', { class: 'fila' });
    caja.append(botonConfirmar({
      texto: 'Ver coste', pregunta: `¿Abrir el coste de ${p.alias || p.nombre}? Queda en el rastro.`, confirmar: 'Sí, abrir', mini: true, soloLectura: ctx.soloLectura,
      alConfirmar: async () => {
        if (!await comprobar()) throw new Error('El almacén de sueldos aún no está declarado');
        const r = await ctx.verDato({ almacen: ALM, ref: p.id, campo: 'meses' });
        const meses = r?.valor || {};
        const ult = Object.keys(meses).sort().pop();
        const m = ult ? meses[ult] : null;
        if (!m) throw new Error('Sin dato para esta persona');
        const eur = m.euros ?? m.pagado;
        caja.replaceChildren(h('span', {}, h('b', {}, eur != null ? fmt.eur(eur) : (m.salario_usd != null ? `${fmt.num(m.salario_usd, 0)} $` : '—')),
          h('span', { class: 'sub' }, ` · ${ult}${m.rol ? ' · ' + m.rol : ''}${m.bonus ? ' · bonus ' + (typeof m.bonus === 'number' ? fmt.eur(m.bonus) : m.bonus) : ''}`)));
        return 'Abierto (en el rastro)';
      },
    }));
    return caja;
  };
  return h('div', { class: 'pila' },
    avisoParcial('Los sueldos se ven en la app solo para dirección y RRHH (Tomás y Cecilia). Cada persona se abre con un clic y queda en el rastro. Sale del Excel de sueldos (enero a septiembre y proyección); la hoja «Cuentas bancarias» no se lee nunca.', { tipo: 'info', titulo: 'Solo tú.' }),
    panel({ titulo: 'Coste del equipo por persona', icono: 'eq', sub: `${personas.length} personas activas · el último mes con dato de cada una · el agregado por áreas sigue en «Plan y año» y en Finanzas › Resultados y equipo` },
      h('div', { class: 'cuerpo' }, personas.length ? tablaApilable({ filas: personas, columnas: [
        { clave: 'nombre', titulo: 'Persona', principal: true, celda: p => p.alias || p.nombre },
        { clave: 'puestos', titulo: 'Puesto', celda: p => (p.puestos || []).join(', ') || '—' },
        { clave: 'coste', titulo: 'Coste', celda: p => celdaCoste(p) }] })
        : vacioLinea('No hay personas en la app.', { quien: 'Mili' }))));
}

async function pintarEmpresa(zona, ctx, ind) {
  zona.append(esqueleto({ lineas: 2, tarjetas: 4 }));
  const vivo = await tilesFinanzas(ctx);
  let d;
  try { d = await cargar(ctx, 'empresa'); }
  catch (e) { zona.replaceChildren(vacio({ icono: 'alert', tono: 'aviso', titulo: 'No se han podido leer los datos de la empresa', texto: e.message, quien: 'el equipo técnico' })); return; }
  const P = d.pestanas || {}, etq = ind.etiquetas || {};
  const corr = corregidas(await leerFinanzas(ctx), ind.correccion_divisa);   // null si no hay Finanzas: entonces solo se pliega
  let tabsEl = null;
  const alIr = id => tabsEl?.elegir(id);
  tabsEl = pestanas({
    pestanas: TABS_EMPRESA.map(t => ({ id: t.id, texto: t.texto || etq[t.id] || t.id, icono: t.icono })),
    clave: 'panel-direccion-emp', etiqueta: 'La empresa',
    pintar: (id, z) => {
      const t = TABS_EMPRESA.find(x => x.id === id);
      if (id === 'equipo') { z.append(bloqueEquipo(ctx)); return; }
      if (id === 'fres') { pintarResumenFinanciero(z, ctx, ind, P.fres, alIr); return; }
      if (t?.m19) {
        z.append(h('div', { class: 'pila' },
          panel({ titulo: `Esto vive en Finanzas › ${t.m19.texto}`, icono: 'ext', sub: 'Para no tener dos versiones de lo mismo: allí, en vivo con Holded y Airtable; aquí, la foto del panel antiguo.' },
            h('div', { class: 'cuerpo fila' },
              h('button', { type: 'button', class: 'bt pri', on: { click: () => irAFinanzas(t.m19.pestana) } }, icono('derecha', { clase: 's' }), `Abrir Finanzas › ${t.m19.texto}`),
              h('span', { class: 'sub' }, t.guarda ? 'Las cifras de gasto del panel antiguo llevan el error del dólar: las buenas, allí y en «Resumen financiero».' : 'Mismas fuentes; las cifras de allí son de hoy y las del panel, de su foto (ver el pie).'))),
          t.guarda ? avisoParcial(AVISO_DIVISA, { titulo: 'Ojo con el v29.' }) : null,
          h('details', { class: 'que-es' }, h('summary', {}, 'Ver la versión del panel antiguo'), montar(P[id], { alIr, guarda: t.guarda, corr, anio: 2026 }))));
        return;
      }
      z.append(P[id] ? montar(P[id], { alIr, guarda: t?.guarda, corr, anio: 2026 }) : vacioLinea('El panel no pintó esta pestaña.'));
    },
  });
  zona.replaceChildren(vivo || avisoParcial('No se han podido leer las cifras en vivo de Finanzas.', { titulo: 'A medias.' }),
    h('h2', { style: H2_SECCION }, icono('euro', { clase: 's' }), 'La empresa · informe financiero del panel v30 (gasto corregido por divisa)'), tabsEl);
}

// ===================================================================== panel original
async function pintarOriginal(zona, ctx, ind) {
  // La app no admite marcos ni scripts en línea (seguridad). El v30 con TODOS sus filtros se abre en su artefacto privado
  // o se descarga como fichero para abrirlo en este Mac (queda en el rastro).
  const estado = h('p', { class: 'sub', role: 'status' });
  const descargar = h('button', { type: 'button', class: 'bt', disabled: ctx.soloLectura || null, on: { click: async () => {
    descargar.disabled = true; estado.textContent = 'Preparando el fichero…';
    try {
      const d = await cargar(ctx, 'original');
      const url = URL.createObjectURL(new Blob([d.html || ''], { type: 'text/html;charset=utf-8' }));
      const a = h('a', { href: url, download: `panel_resultados_v30_${(d.origen?.panel_modificado || '').slice(0, 10)}.html` });
      document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 4000);
      ctx.rastro({ accion: 'descarga', objeto: 'panel_direccion/original', detalle: `Panel v30 (${d.origen?.sha256 || ''}) descargado` });
      estado.textContent = `Descargado · foto ${d.origen?.panel_modificado || ''}. Lleva nombres de leads: no se reenvía.`;
    } catch (e) { estado.textContent = 'No se ha podido preparar: ' + e.message; }
    descargar.disabled = false;
  } } }, icono('descarga', { clase: 's' }), 'Descargar el panel');
  zona.append(
    avisoParcial('Aquí dentro van todas sus pestañas y cifras. Lo que solo tiene el original son los filtros finos: capa de publicidad, fechas a medida, «3 días», «por cohorte», los buscadores y el orden de las tablas. La app no abre páginas con código propio dentro (seguridad), así que el original se abre aparte.', { tipo: 'info', titulo: 'Panel original.' }),
    panel({ titulo: 'Abrir el panel v30 con todos sus filtros', icono: 'capas', sub: `Foto del ${fDiaRO(ind.foto_panel?.slice(0, 10))} a las ${ind.foto_panel?.slice(11, 16)}` },
      h('div', { class: 'cuerpo pila' },
        h('div', { class: 'fila' },
          h('a', { class: 'bt pri', href: ind.origen?.artefacto, target: '_blank', rel: 'noopener' }, icono('ext', { clase: 's' }), 'Abrir el panel privado'),
          descargar),
        estado,
        h('p', { class: 'sub' }, 'El panel privado solo lo abre tu cuenta. El fichero descargado se abre con doble clic en este Mac, sin conexión.'))));
}

// ===================================================================== pantalla
function panelNominal249(ctx) {
  if (ctx.real?.id !== 'tomas' || ctx.persona?.id !== 'tomas') return false;
  const activo = p => p?.estado === 'activo' && p.activo !== false && Array.isArray(p.puestos) && p.puestos.includes('direccion');
  if (!activo(ctx.real) || !activo(ctx.persona) || !Array.isArray(ctx.datos?.personas)) return false;
  const actuales = ctx.datos.personas.filter(p => p?.id === 'tomas');
  return actuales.length === 1 && activo(actuales[0]);
}
async function pintar(cont, ctx) {
  cont.classList.add('pila');
  if (!panelNominal249(ctx)) {
    cont.append(vacio({ icono: 'candado', titulo: 'Solo Tomás', texto: 'El panel de dirección solo lo ve Tomás, y no se abre con «ver como».' }));
    return;
  }
  ctx.titulo('Panel de dirección', 'Solo tú, con nombres reales · la empresa y la captación de RO del panel de resultados v29/v30');
  let ind;
  try { ind = await cargar(ctx, 'indice'); }
  catch (e) {
    cont.append(vacio({ icono: 'alert', tono: 'aviso', titulo: 'Sin datos del panel de dirección', texto: `${e.message}. Hay que volver a generar el panel y recargar.`, quien: 'el equipo técnico' }));
    return;
  }
  if (!panelNominal249(ctx) || (ctx.vigente && !ctx.vigente())) return;
  const zona = h('div', { class: 'pila' });
  let actual = null;
  let generacion = 0;
  const mundo = chipsFiltro({ opciones: MUNDOS, valor: 'resumen', clave: 'panel-direccion-mundo-v4', etiqueta: 'Qué quieres ver', alCambiar: v => cambiar(v) });
  async function cambiar(v) {
    const turno = ++generacion;
    actual = v;
    zona.replaceChildren();
    if (v === 'empresa') await pintarEmpresa(zona, ctx, ind);
    else if (v === 'original') await pintarOriginal(zona, ctx, ind);
    else if (v === 'captacion') await pintarCaptacion(zona, ctx, ind);
    else await pintarResumenV4(zona, { ...ctx, vigente: () => turno === generacion && (!ctx.vigente || ctx.vigente()) }, { irA: x => { mundo.querySelectorAll('button').forEach(b => { if (b.textContent.startsWith(MUNDOS.find(m => m.valor === x)?.texto || '¿')) b.click(); }); } });
  }
  const mas = menuMas({ texto: 'Panel original', etiqueta: 'Panel original y descarga', items: [
    { texto: 'Panel original y descarga', icono: 'capas', alPulsar: () => cambiar('original') },
    { texto: 'Abrir el panel privado', icono: 'ext', href: ind.origen?.artefacto },
  ] });
  cont.append(h('div', { class: 'fila' }, mundo, mas), zona, pieFuentes(ind));
  const inicial = mundo.valor();
  await cambiar(inicial === 'original' ? 'resumen' : inicial);
  void actual;
}

// ===================================================================== Resumen v4 (48 §4.1)
const MES_L = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const nomMesV = m => (m ? MES_L[Number(String(m).slice(5, 7)) - 1] : '—');
const pctV = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? '—' : `${fmt.num(v, d)} %`);
const eurV = v => (v === null || v === undefined ? '—' : `${v < 0 ? '−' : ''}${fmt.eur(Math.abs(v))}`);
const planDeV = t => { const m = /([\d.]+)\s*→\s*([\d.]+)\s*→\s*([\d.]+)/.exec(t || ''); return m ? m.slice(1, 4).map(x => Number(x.replace(/\./g, ''))) : []; };

// 246: conserva los mismos nodos y cálculos de tarjetaKpi, distribuidos en una
// fila comparable. Tendencia, umbral, contexto y fuente quedan en su detalle.
function indicadorDireccion246(opciones) {
  const tarjeta = tarjetaKpi(opciones);
  const titulo = tarjeta.querySelector(':scope > .tt');
  const valor = tarjeta.querySelector(':scope > .tv');
  const comparacion = tarjeta.querySelector(':scope > .tc');
  const detalle = [...tarjeta.children].filter(n => n !== titulo && n !== valor && n !== comparacion);
  if (valor) { valor.style.fontSize = '14px'; valor.style.lineHeight = '1.3'; }
  if (comparacion) { comparacion.style.fontSize = '12px'; comparacion.style.lineHeight = '1.3'; }
  const estilo = { padding: '7px 9px', verticalAlign: 'middle', whiteSpace: 'normal', fontSize: '13px', lineHeight: '1.3', overflowWrap: 'anywhere', textTransform: 'none', letterSpacing: 'normal' };
  return h('tr', {},
    h('th', { scope: 'row', style: { ...estilo, fontWeight: 'normal', width: '35%' } }, titulo),
    h('td', { style: { ...estilo, width: '22%' } }, valor),
    h('td', { style: { ...estilo, width: '31%' } }, comparacion),
    h('td', { style: { ...estilo, width: '12%' } }, h('details', {},
      h('summary', { 'aria-label': `Tendencia, fuente y límites de ${opciones.etiqueta}`, class: 'sub', style: { minHeight: '44px', display: 'flex', alignItems: 'center', cursor: 'pointer' } }, 'Detalle'),
      h('div', { class: 'pila', style: { minWidth: '0' } }, detalle))));
}

async function pintarResumenV4(zona, ctx, { irA } = {}) {
  const identidad = JSON.stringify([ctx.real?.id, ctx.persona?.id]);
  const vigente = () => zona.isConnected && panelNominal249(ctx) && (!ctx.vigente || ctx.vigente()) && identidad === JSON.stringify([ctx.real?.id, ctx.persona?.id]) && (!ctx.veModulo || ctx.veModulo('panel-direccion'));
  if (!vigente()) return;
  zona.append(esqueleto({ lineas: 2, tarjetas: 4 }));
  const leer = n => ctx.datosModulo(n).catch(() => null);
  const [f, cu, im, fin, vro] = await Promise.all([leerFinanzas(ctx), leer('finanzas/cuadre'), leer('finanzas/impagos'), leer('finanzas/finanzas'), ctx.veModulo('ventas-ro') ? leer('ventas_ro/ventas_ro') : null]);
  if (!vigente()) return;
  const dir = Array.isArray(f?.direccion) ? f.direccion[0] : null;
  if (!dir) { zona.replaceChildren(vacioLinea('Sin Finanzas de dirección: las cifras del resumen salen solo de allí y no se han podido leer.', { icono: 'alert', quien: 'Agus' })); return; }
  const n = dir.numero || {}, cr = dir.cuota_recurrente || {}, cj = dir.caja || {}, eq = dir.equipo || {}, kpi = dir.kpi || {};
  const a = fin?.admin || {}, imp = im?.resumen || {};
  const B = cu?.beneficio?.meses || [];
  const porMes = new Map(B.map(x => [x.m, x]));
  const ultM = n.mes || '2026-08', prevM = mesMas(ultM, -1), anioM = mesMas(ultM, -12);
  const m12 = Array.from({ length: 12 }, (_, i) => mesMas(ultM, i - 11));
  const pygDe = new Map((dir.pyg || []).map(x => [x.m, x]));
  const mb3 = m => { const w = [mesMas(m, -2), mesMas(m, -1), m].map(x => pygDe.get(x)).filter(Boolean); return w.length === 3 ? (100 * w.reduce((s2, x) => s2 + x.mb, 0)) / w.reduce((s2, x) => s2 + x.ing, 0) : null; };
  const eqDe = new Map((cu?.equipo_mes || []).map(x => [x.m, x]));
  const pesoDe = m => { const e = eqDe.get(m), b = porMes.get(m); return e && b?.ing && !b.estimado && e.estado !== 'provisional' ? (100 * e.usado) / b.ing : null; };
  const [planOct, planNov] = planDeV(cr.plan_texto);
  const P = puenteCuota(dir.puente || [], 6);
  const pDe = new Map((dir.puente || []).map(x => [x.m, x]));
  const perdidaDe = m => { const x = pDe.get(m); return x?.ini ? (100 * (-Math.min(0, x.bajadas || 0) - Math.min(0, x.bajas || 0))) / x.ini : null; };
  const mesesV = vro?.meses || {};
  const cpcDe = m => { const x = mesesV[m]; return x?.firmados ? x.inversion / x.firmados : null; };
  const mVro = Object.keys(mesesV).sort().filter(m => mesesV[m]?.hasta && mesesV[m].hasta < (ctx.hoy || '9999')).pop() || '2026-09';

  // ---- 1 · la cifra que manda + 2 · hacia el objetivo de diciembre
  const comp = selectorComparar({ clave: 'panel-direccion-comparar', alCambiar: c => pintarCifras(c) });
  const zonaCifras = h('div', { class: 'pila' });
  const cifraQueManda = c => {
    const ref = c === 'mes_ant' ? { ref: porMes.get(prevM)?.bai, texto: `frente a ${nomMesV(prevM)}` }
      : c === 'anio_ant' ? { ref: porMes.get(anioM)?.bai, texto: `frente a ${nomMesV(anioM)} de ${anioM.slice(0, 4)} (estimado)` }
        : { ref: n.plan_res, texto: `frente al plan del mes (${eurV(n.plan_res)})` };
    return panel({ titulo: `Beneficio de ${nomMesV(ultM)} · la cifra que manda`, icono: 'grafico', sub: 'Último mes cerrado, con los gastos convertidos a euros factura a factura. El mismo número que Finanzas y Mi día.' },
      h('div', { class: 'cuerpo pila' },
        cifraPrincipal({ etiqueta: `Margen ${pctV(n.margen_pct)} sobre ${fmt.eur(n.ingresos)} de ingresos`, valor: eurV(n.beneficio), estado: colorCifra('beneficio', n.beneficio),
          comparacion: lineaComparacion({ num: n.beneficio, ...ref, modo: 'abs', formato: v => fmt.eur(v), mejorSi: 'alto' }) || 'sin dato para comparar' }),
        h('p', { class: 'sub' }, `Con el gasto sin factura: ${eurV(n.beneficio_real)} · enero-agosto: ${eurV(dir.anio?.bai)} (${pctV(kpi.bai)}) · ${eurV(dir.anio?.real)} con el gasto sin factura.`),
        minilinea(m12.map(m => porMes.get(m)?.bai ?? null), { x: m12, formato: v => eurV(v), etiqueta: 'Beneficio de los 12 últimos meses (2025, estimado)', alto: 40 }),
        h('p', { class: 'kpi-pie' }, h('span', {}, `Norte: ${n.objetivo_texto || '30.000 € de beneficio al mes a final de 2027'}`), h('a', { class: 'bt mini', href: '#/finanzas' }, icono('derecha', { clase: 's' }), 'Abrir Finanzas'))));
  };
  const panelCuota = panel({ titulo: 'Hacia el objetivo de diciembre', icono: 'sube', sub: cr.plan_texto || 'Cuota mensual contra el plan del mes y el objetivo de diciembre' },
    h('div', { class: 'cuerpo pila' },
      h('p', { class: 'fila' }, h('b', {}, `${fmt.eur(cr.cuota_mes)} al mes`), h('span', { class: 'sub' }, `${planOct ? `${fmt.pct((100 * cr.cuota_mes) / planOct)} del plan del mes · ` : ''}${fmt.pct((100 * cr.cuota_mes) / (cr.objetivo_dic || 1))} del objetivo de diciembre`)),
      barraObjetivo({ etiqueta: 'Cuota del mes', valor: cr.cuota_mes, objetivo: planOct || cr.objetivo_dic, max: Math.max(cr.objetivo_dic || 0, planNov || 0) * 1.04, formato: v => fmt.eur(v),
        etiquetaValor: 'Hoy', etiquetaObjetivo: 'Plan del mes', extra: cr.si_firman_mes ? [{ valor: cr.si_firman_mes, texto: `Si firman los ${(cr.pendientes || []).length}` }] : [],
        marcas: [planNov ? { valor: planNov, texto: 'Plan de noviembre' } : null, cr.objetivo_dic ? { valor: cr.objetivo_dic, texto: 'Objetivo de diciembre' } : null].filter(Boolean) }),
      h('p', { class: 'kpi-umbral' }, h('span', {}, `Umbral: ${UMBRALES.cuota_objetivo.texto}`), ' · ', enlaceFuente(FUENTES.databox.href, FUENTES.databox.fuente)),
      h('div', { class: 'fila' }, ctx.veModulo('ventas-ro') && (cr.pendientes || []).length ? h('a', { class: 'bt mini pri', href: '#/ventas-ro' }, icono('phone', { clase: 's' }), `Llamar a los ${cr.pendientes.length} contratos pendientes`) : null,
        h('a', { class: 'bt mini', href: '#/finanzas' }, icono('euro', { clase: 's' }), 'Ver la cuota línea a línea'))));

  // ---- 3 · seis tarjetas
  const tarjetas = c => {
    const mbU = mb3(ultM), pesoU = eq.peso_ingresos ?? pesoDe(ultM);
    const mesesCuo = Array.from({ length: 12 }, (_, i) => mesMas(ultM, i - 11));
    const mV = Object.keys(mesesV).sort().filter(m => m <= mVro).slice(-12);
    const cpc = cpcDe(mVro);
    return h('div', { class: 'tabla-scroll', 'data-pd-tarjetas': '', style: { maxWidth: '100%', overflowX: 'auto' }, tabIndex: 0, 'aria-label': 'Indicadores de dirección comparables' },
      h('table', { class: 'densa', style: { width: '100%', minWidth: '580px', tableLayout: 'fixed' } },
      h('caption', { style: { textAlign: 'left', fontSize: '12px' } }, 'Indicadores · mismas fuentes y comparación seleccionada'),
      h('thead', {}, h('tr', {}, ['Indicador','Valor','Comparación','Fuente / detalle'].map(t => h('th', { scope: 'col', style: { fontSize: '12px', textTransform: 'none', letterSpacing: 'normal' } }, t)))),
      h('tbody', {},
      indicadorDireccion246({ icono: 'escudo', etiqueta: 'Caja y meses de caja', valor: fmt.num(cj.meses, 1), unidad: `meses · ${fmt.eur(cj.total)}`, num: cj.meses, estado: ESTADO.meses_caja(cj.meses), mejorSi: 'alto', comparar: c,
        comparaciones: { mes_ant: { ref: cj.meses_31ago, texto: 'frente al 31-ago', modo: 'abs', formato: v => `${fmt.num(v, 1)} meses` }, anio_ant: { sinDato: 'Sin saldo de bancos de hace un año en la app' }, objetivo: { ref: 2, texto: 'frente al mínimo de 2 meses', modo: 'abs', formato: v => `${fmt.num(v, 1)} meses` } },
        contexto: `Caja de hoy ÷ gasto medio ${fmt.eur(cj.gasto_medio)} al mes, si no entrara nada`, umbral: UMBRALES.meses_caja, fuente: { texto: 'Holded en vivo', href: '#/finanzas/cobros' }, alPulsar: () => { location.hash = '#/finanzas'; }, ir: 'Ver la caja a 90 días' }),
      indicadorDireccion246({ icono: 'euro', etiqueta: `Ingresos de ${nomMesV(ultM)}`, valor: fmt.eur(n.ingresos), num: n.ingresos, estado: '', mejorSi: 'alto', comparar: c,
        serie: m12.map(m => porMes.get(m)?.ing ?? null), serieX: m12, formatoSerie: v => fmt.eur(v),
        comparaciones: { mes_ant: { ref: porMes.get(prevM)?.ing, texto: `frente a ${nomMesV(prevM)}` }, anio_ant: { ref: porMes.get(anioM)?.ing, texto: `frente a ${nomMesV(anioM)} de ${anioM.slice(0, 4)}` }, objetivo: { ref: pygDe.get(ultM)?.plan_ing, texto: 'frente al plan del mes' } },
        contexto: `Enero-agosto: ${fmt.eur(dir.anio?.ing)} · sin IVA`, umbral: { texto: 'Sin umbral propio: se lee contra el plan del mes', colorea: false }, fuente: { texto: 'Holded', href: '#/finanzas' } }),
      indicadorDireccion246({ icono: 'sube', etiqueta: 'Margen bruto · media de 3 meses', valor: pctV(mbU), num: mbU, estado: ESTADO.margen_bruto(mbU), mejorSi: 'alto', comparar: c,
        serie: m12.map(mb3), serieX: m12, formatoSerie: v => pctV(v), umbralSerie: 35,
        comparaciones: { mes_ant: { ref: mb3(prevM), texto: `frente a la media hasta ${nomMesV(prevM)}`, modo: 'puntos' }, anio_ant: { sinDato: '2025 no tiene el coste de entrega fiable' }, objetivo: { ref: 35, texto: 'frente al 35 %', modo: 'puntos' } },
        contexto: `Ingresos menos el equipo de entrega · enero-agosto: ${pctV(kpi.mb)}`, umbral: UMBRALES.margen_bruto, fuente: { texto: 'cierre de Sofía', href: '#/finanzas/cuadre' } }),
      indicadorDireccion246({ icono: 'eq', etiqueta: 'Peso del equipo sobre ingresos', valor: pctV(pesoU), num: pesoU, estado: ESTADO.peso_equipo(pesoU), mejorSi: 'bajo', comparar: c,
        serie: m12.map(m => (m >= '2026-01' ? pesoDe(m) : null)), serieX: m12, formatoSerie: v => pctV(v), umbralSerie: 55,
        comparaciones: { mes_ant: { ref: pesoDe(prevM), texto: `frente a ${nomMesV(prevM)}`, modo: 'puntos' }, anio_ant: { sinDato: '2025: el equipo va repartido por ingresos' }, objetivo: { ref: 55, texto: 'frente al 55 %', modo: 'puntos' } },
        contexto: `Año: ${pctV(kpi.peso_equipo_anio)} · solo agregado, nunca sueldos de una persona`, umbral: UMBRALES.peso_equipo, fuente: { texto: 'cierre de Sofía, solo totales', href: '#/finanzas/cuadre' } }),
      indicadorDireccion246({ icono: 'baja', etiqueta: 'Pérdida de cuota al mes', valor: pctV(P.perdida_pct), num: P.perdida_pct, estado: '', mejorSi: 'bajo', comparar: c,
        serie: mesesCuo.map(perdidaDe), serieX: mesesCuo, formatoSerie: v => pctV(v),
        comparaciones: { mes_ant: { num: perdidaDe(ultM), ref: perdidaDe(prevM), texto: `${nomMesV(ultM)} frente a ${nomMesV(prevM)}`, modo: 'puntos' }, anio_ant: { sinDato: 'Sin la media de hace un año' }, objetivo: { sinDato: 'Sin objetivo firmado de pérdida de cuota' } },
        contexto: `Media de 6 meses: rebajas ${pctV(P.rebajas_pct)} + bajas ${pctV(P.bajas_pct)} · subidas +${pctV(P.subidas_pct)} · 12 meses: −${fmt.eur(P.rebajas_12)} en rebajas, −${fmt.eur(P.bajas_12)} en bajas`,
        umbral: UMBRALES.perdida_cuota, fuente: { texto: 'puente de Holded', href: '#/finanzas/ingresos' } }),
      indicadorDireccion246({ icono: 'target', etiqueta: `Coste de captar · ${nomMesV(mVro)}`, valor: cpc === null ? null : fmt.eur(cpc), num: cpc, sinDato: 'sin firmados en el mes', unidad: cpc === null ? '' : `${fmt.eur(mesesV[mVro]?.inversion)} ÷ ${mesesV[mVro]?.firmados}`,
        estado: cpc === null ? '' : colorCifra('coste_cliente', cpc), mejorSi: 'bajo', comparar: c, serie: mV.map(cpcDe), serieX: mV, formatoSerie: v => fmt.eur(v), umbralSerie: 700,
        comparaciones: { mes_ant: { ref: cpcDe(mesMas(mVro, -1)), texto: `frente a ${nomMesV(mesMas(mVro, -1))}`, formato: v => fmt.eur(v) }, anio_ant: { sinDato: 'El embudo de RO empieza en 2026' }, objetivo: { ref: 700, texto: 'frente a los 700 € de la regla', modo: 'abs', formato: v => fmt.eur(v) } },
        contexto: 'Solo publicidad de Meta ÷ firmados (el coste completo de ventas aún no está separado)', umbral: { texto: 'RO: verde ≤ 700 € · ámbar hasta 840 € · rojo por encima · parar por encima de 2.500 €' },
        fuente: { texto: 'Meta y GHL', href: '#/ventas-ro' }, alPulsar: () => { location.hash = '#/ventas-ro'; }, ir: 'Abrir Ventas de RO' }))));
  };
  const pintarCifras = c => { if (vigente()) zonaCifras.replaceChildren(h('div', { class: 'dos iguales' }, cifraQueManda(c), panelCuota), tarjetas(c)); };

  // ---- 5 · lo que pide tu decisión (máximo 5, con su botón al lado)
  const vencidos60 = imp.mas_60 ?? a.impagos?.mas_60 ?? 0;
  const sinAlta = a.firmas_sin_alta || [];
  const decide = [
    vencidos60 ? { estado: 'rojo', icono: 'alert', motivo: `${fmt.plural(vencidos60, 'recibo', 'recibos')} con más de 60 días`, detalle: `${fmt.eur(imp.vencido ?? a.impagos?.vencido_total)} vencidos en total · a 60 días decides tú: cortar, plan de pago o darlo por perdido.`,
      botones: [h('a', { class: 'bt mini pri', href: '#/finanzas/impagos' }, icono('derecha', { clase: 's' }), 'Decidir los impagos')] } : null,
    ...sinAlta.slice(0, 2).map(x => ({ estado: 'rojo', icono: 'doc', motivo: `${x.nombre} · firmado sin alta en facturación`, detalle: `Firmado el ${x.firma} · account ${x.account || 'sin account'}: no entra en la cuota que factura Sofía.`,
      botones: [h('a', { class: 'bt mini', href: `#/finanzas/cobros/${encodeURIComponent(x.cliente_id)}` }, icono('derecha', { clase: 's' }), 'Abrir el cobro')] })),
    cj.meses < 2 ? { estado: cj.meses < 1 ? 'rojo' : 'ambar', icono: 'escudo', motivo: `Caja para ${fmt.num(cj.meses, 1)} meses si no entrara nada`, detalle: 'Referencia de agencias: mínimo 2 meses de gasto fijo (3-4 si hay concentración).',
      botones: [h('a', { class: 'bt mini', href: '#/finanzas' }, icono('derecha', { clase: 's' }), 'Ver la caja a 90 días')] } : null,
    P.rebajas_pct > P.bajas_pct ? { estado: 'ambar', icono: 'baja', motivo: `Las rebajas de cuota pesan más que las bajas (${pctV(P.rebajas_pct)} frente a ${pctV(P.bajas_pct)} al mes)`, detalle: `−${fmt.eur(P.rebajas_12)} en 12 meses. ¿Reales (descuentos, cambios de plan) o ruido (prorrateos)?`,
      botones: [botonDeshacer({ texto: 'Pedir a Mili que lo revise', hecho: 'Pedido a Mili', soloLectura: ctx.soloLectura,
        alHacer: async () => { await ctx.accion({ herramienta: 'app', tipo: 'revisar_rebajas', objeto: 'rebajas_cuota', texto: `Revisar con los accounts las rebajas de cuota: ${pctV(P.rebajas_pct)} al mes, −${fmt.eur(P.rebajas_12)} en 12 meses. ¿Reales o ruido?`, vista_previa: { para: 'Mili', aviso: 'en su Mi día', desde: 'panel-direccion' } }); return 'Pedido a Mili (simulado)'; } })] } : null,
  ].filter(Boolean).slice(0, 5);
  const panelDecide = panel({ titulo: 'Lo que pide tu decisión', icono: 'flag', sub: 'Del dinero, lo que no se arregla solo · cada una con su botón' },
    filasLP(decide, { vacio: { titulo: 'Nada del dinero espera tu decisión', porque: 'Sin impagos de 60 días, firmados sin alta ni caja por debajo de 2 meses.', celebrar: true } }));

  // ---- 4 · de dónde sale el cambio de la cuota (cascada del último mes del puente)
  const ultP = (dir.puente || []).at(-1);
  const panelPuente = ultP ? panel({ titulo: `De dónde sale el cambio de la cuota · ${nomMesV(ultP.m)}`, icono: 'capas', sub: 'Cuota del mes anterior + altas + subidas − rebajas − bajas = cuota del mes (cuadra al euro con Holded)' },
    h('div', { class: 'cuerpo pila' },
      cascada({ zoom: true, formato: v => fmt.eur(v), pasos: [
        { texto: `Cuota de ${nomMesV(mesMas(ultP.m, -1))}`, valor: ultP.ini, tipo: 'total' }, { texto: 'Altas', valor: ultP.altas || 0 }, { texto: 'Subidas', valor: ultP.subidas || 0, estado: 'sube2' },
        { texto: 'Rebajas', valor: ultP.bajadas || 0, estado: 'ambar' }, { texto: 'Bajas', valor: ultP.bajas || 0 }, { texto: `Cuota de ${nomMesV(ultP.m)}`, valor: ultP.fin, tipo: 'total' }] }),
      h('p', { class: 'kpi-pie' }, h('span', {}, 'Cómo se dibuja: '), enlaceFuente(FUENTES.chartmogul_mov.href, FUENTES.chartmogul_mov.fuente), enlaceFuente(FUENTES.pigment.href, FUENTES.pigment.fuente),
        h('a', { class: 'bt mini', href: '#/finanzas/ingresos' }, icono('derecha', { clase: 's' }), 'Ver el puente de 12 meses')))) : null;

  // ---- 7 · clientes: altas y bajas de 12 meses y cohortes
  const AB = (dir.altas_bajas || []).filter(x => !x.curso).slice(-12);
  const coh = await leer('dinero_cliente/cohortes');
  if (!vigente()) return;
  const filasDe = blk => (blk?.filas || []).map(x => ({ etiqueta: `${nomMesV(x.m).slice(0, 3)} ${x.m.slice(2, 4)}`, n: x.n, valores: x.pct }));
  const panelClientes = panel({ titulo: 'Clientes: altas, bajas y cuánto se quedan', icono: 'users', sub: 'Cada mes, los que entran sobre cero y los que se van debajo · y, por mes de alta, el % que sigue (un solo color: más oscuro = más se queda)' },
    h('div', { class: 'cuerpo pila' },
      AB.length ? barrasGanadoPerdido({ x: AB.map(x => x.m), formato: v => fmt.num(v), ganado: [{ nombre: 'Altas', clase: 'sube', y: AB.map(x => x.altas || 0) }], perdido: [{ nombre: 'Bajas', clase: 'baja', y: AB.map(x => -(x.bajas || 0)) }],
        detalle: i => [`Clientes al cierre: ${AB[i]?.fin ?? '—'}`] }) : vacioLinea('Sin la serie de altas y bajas.'),
      coh ? mapaCalor({ clave: 'panel-direccion-cohortes', columnas: Array.from({ length: coh.columnas || 13 }, (_, i) => `Mes ${i}`), titulo: 'Retención por mes de alta', vistas: [
        { valor: 'clientes', texto: '% de clientes', icono: 'users', filas: filasDe(coh.clientes), media: coh.clientes?.media, nota: coh.clientes?.texto },
        { valor: 'cuota', texto: '% de la cuota de entrada', icono: 'euro', filas: filasDe(coh.cuota_entrada), media: coh.cuota_entrada?.media, nota: coh.cuota_entrada?.texto }] }) : vacioLinea('Sin las cohortes de Dinero por cliente.'),
      h('div', { class: 'fila' }, ctx.veModulo('en-rojo') ? h('a', { class: 'bt mini', href: '#/en-rojo' }, icono('alert', { clase: 's' }), 'Ver los clientes en riesgo hoy') : null,
        ctx.veModulo('dinero-cliente') ? h('a', { class: 'bt mini', href: '#/dinero-cliente' }, icono('users', { clase: 's' }), 'Ver la rentabilidad por cliente') : null)));

  zona.replaceChildren(
    h('div', { class: 'dos', 'data-pd-arriba': '' }, h('div', { class: 'pila' }, h('div', { class: 'fila' }, comp), zonaCifras), panelDecide),
    separador('El porqué de las cifras'),
    h('div', { class: 'dos iguales' }, panelPuente, panel({ titulo: 'Captación de hoy', icono: 'target', sub: 'Coste por cliente firmado, publicidad, de qué anuncio y agenda: el panel portado' },
      h('div', { class: 'cuerpo pila' }, h('p', { class: 'sub' }, 'La cadena del coste (publicidad → citas → firmados) con sus cinco fotos de periodo, tal cual el panel de resultados.'),
        h('div', { class: 'fila' }, h('button', { type: 'button', class: 'bt mini pri', on: { click: () => irA?.('captacion') } }, icono('derecha', { clase: 's' }), 'Ver la captación'),
          ctx.veModulo('ventas-ro') ? h('a', { class: 'bt mini', href: '#/ventas-ro' }, icono('phone', { clase: 's' }), 'Ventas de RO: a quién llamar') : null)))),
    panelClientes,
    fuentesAlPie(['baker', 'ami', 'ami_personal', 'parakeeto', 'scoro', 'saascapital', 'databox', 'chartmogul_mov', 'chartmogul_coh', 'pigment']));
  pintarCifras(comp.valor());
  consejoCompacto(zona, zona.firstElementChild);
}

// X6: los títulos de sección van como el resto de H2 de la app (15/700, en minúscula), no en mayúsculas de cabecera de tabla.
const H2_SECCION = { font: 'var(--t-h2)', margin: '0', display: 'flex', alignItems: 'center', gap: 'var(--s-2)' };
export default {
  id: 'panel-direccion',
  titulo: 'Panel de dirección',
  grupo: 'Dinero',
  puestos_que_lo_ven: { direccion: 'todo' },
  async render(contenedor, ctx) { vigilarCortes(contenedor); await pintar(contenedor, ctx); },
};
