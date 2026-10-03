// modulos/informe.js · M5 «Informe del cliente» (sustituto de Looker Studio) + comparador de paridad (2-oct-2026).
// Diseño: 10_FICHAS/G4_INFORME_DEL_CLIENTE_SUSTITUTO_LOOKER.md y E9 del plan v2. Inventario: 05_INVENTARIO_LOOKER_STUDIO.md.
// Rutas: #/informe-cliente/<cliente>/<periodo>/<comparar>   y   #/informe-cliente/paridad
//
// Datos (nada se lee de data/ a mano; todo sale recortado por servir.py):
//   · ctx.datosModulo('informe/p_<periodo>') .. una fila por cliente (cliente_id): GA4, Search Console (por web y por página),
//                                               SE Ranking, Meta, Google Ads (muestra), Snov.io, embudo GHL, avisos.
//                                               servir.py quita las filas de clientes que no lleva y el gasto, coste y cpl a
//                                               quien no ve la inversión (SEO, outreach).
//     Para abrir un cliente (auditoría 37): 'informe/i_<periodo>' (índice ligero) + 'informe/c_<periodo>/<cliente>' (su fila);
//     p_<periodo> entero solo para la comparación con Looker o si falta una pieza.
//   · ctx.datosModulo('informe/paridad' | 'informe/comun') .. los 22 Looker (G4 §8) y los periodos.
//   · ctx.api('acciones?modulo=informe-cliente') .. análisis del mes y marcas de «paridad comprobada» (cola simulada).
// Lo genera fuentes_informe/generar_informe.py (solo lectura: gg.py, mt.py, sv.py; SE Ranking por el conector).
// Diseño N6 (auditoría 30): sin hoja propia; un solo motor de gráficos (grafico()); periodo común de la carcasa
// (usa_periodo + ctx.periodo, sin selector propio); bloques sin datos o todo a cero, plegados en una línea.

import {
  h, fmt, chipEstado, chipsFiltro, selectorCliente, pestanas, vacio, botonConfirmar, avisoParcial, logoCliente,
  candado, panel, frescura, icono, iniciales, tablaApilable, avisoFlotante, copiar, variacion, selloMedible, tile as tileBase,
  grafico, rejillaTarjetas, vacioLinea, esqueleto, barraProgreso, colorCifra,
} from '../componentes.js';

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
const tiles = rejillaTarjetas;   // rejilla común sin huérfanas (auditoría 30, §3.5)
// Revisión 44 (I13): una cifra «—» no va nunca como número principal: tile() la pinta «Sin dato» en gris.
const tile = o => tileBase({ ...o, valor: o.valor === '—' ? null : o.valor });

// ------------------------------------------------------------------ impresión (revisión 44, I1-I7)
// El PDF es para el cliente: lo interno (avisos al equipo, «Sin fuente», formularios, buscadores, botones) lleva la clase
// común .no-imprimir (regla @media print de estilos.css). Lo que SOLO va en el papel (cabecera con la marca de RO, «Fuentes
// no incluidas», «Análisis del mes: pendiente») lleva data-solo-imprimir y hidden; se enseña al imprimir (beforeprint o
// media print) y se vuelve a esconder después. Sin hoja propia: solo atributos y clases.
const interno = el => { if (el?.classList) el.classList.add('no-imprimir'); return el; };
const soloPapel = el => { el.setAttribute('data-solo-imprimir', ''); el.classList.add('solo-imprimir'); el.hidden = !globalThis.matchMedia?.('print').matches; return el; };
// En el papel (A4, ~680 px) la columna principal de las tablas se estrecha para que no se salgan las de la derecha.
const papel = on => { document.querySelectorAll('[data-solo-imprimir]').forEach(e => { e.hidden = !on; }); document.querySelectorAll('[data-corte]').forEach(e => { e.style.maxWidth = on ? '150px' : '420px'; });
  // Tablas: en papel, celdas más juntas y cabeceras que pueden partir en dos líneas (si no, la última columna se sale del folio).
  document.querySelectorAll('[data-informe] table.densa').forEach(t => { t.style.fontSize = on ? '11px' : ''; });
  document.querySelectorAll('[data-informe] table.densa th, [data-informe] table.densa td').forEach(c => { c.style.padding = on ? '4px 6px' : ''; if (c.tagName === 'TH') { c.style.whiteSpace = on ? 'normal' : ''; c.style.letterSpacing = on ? '0' : ''; } });
  document.querySelectorAll('[data-informe] tr').forEach(r => { r.style.breakInside = on ? 'avoid' : ''; });
};
if (!globalThis.__roInformePapel && typeof window !== 'undefined') {
  globalThis.__roInformePapel = true;
  window.addEventListener('beforeprint', () => papel(true));
  window.addEventListener('afterprint', () => papel(false));
  try { window.matchMedia('print').addEventListener('change', e => papel(e.matches)); } catch { /* navegador viejo */ }
}
const SIN_CORTE = { breakInside: 'avoid', pageBreakInside: 'avoid' };
/** El periodo con su artículo (I10): «los últimos 30 días», «el 3.er trimestre 2026», «septiembre 2026». */
const artP = P => { const t = String(P?.texto || '').toLowerCase(); return /^últimos/.test(t) ? `los ${t}` : /trimestre/.test(t) ? `el ${t}` : t; };
const enP = P => `en ${artP(P)}`;
const deP = P => `de ${artP(P)}`.replace(/^de el /, 'del ');

// ------------------------------------------------------------------ constantes
const MOD = 'informe-cliente';
const BLOQUES = [
  { id: 'resumen', texto: 'Resumen del periodo', icono: 'res' },
  { id: 'embudo', texto: 'Embudo hasta la venta', icono: 'target' },
  { id: 'ga4', texto: 'Web (Analytics)', icono: 'grafico' },
  { id: 'gsc', texto: 'Google (Search Console)', icono: 'buscar' },
  { id: 'seranking', texto: 'Posiciones (SE Ranking)', icono: 'sube' },
  { id: 'google_ads', texto: 'Google Ads', icono: 'megafono' },
  { id: 'meta', texto: 'Meta Ads', icono: 'target' },
  { id: 'correo', texto: 'Correo en frío', icono: 'mail' },
  { id: 'linkedin', texto: 'LinkedIn', icono: 'users' },
  { id: 'ficha_google', texto: 'Ficha de Google', icono: 'pin' },
  { id: 'analisis', texto: 'Análisis del mes', icono: 'editar' },
  { id: 'glosario', texto: 'Glosario', icono: 'libro' },
];
// Quién ve qué (G4 §1). Varios puestos suman bloques.
const TODO = BLOQUES.map(b => b.id);
const PERFIL = {
  publicidad: ['resumen', 'embudo', 'google_ads', 'meta', 'analisis', 'glosario'],
  seo: ['resumen', 'ga4', 'gsc', 'seranking', 'ficha_google', 'analisis', 'glosario'],
  outreach: ['resumen', 'correo', 'linkedin', 'analisis', 'glosario'],
  crm: ['resumen', 'embudo', 'analisis', 'glosario'],
};
const PUESTO_PERFIL = {
  trafficker: 'publicidad', jefa_publicidad: 'publicidad', seo: 'seo', jefa_seo: 'seo', ficha_google: 'seo', web: 'seo',
  outreach: 'outreach', jefa_crm: 'outreach', especialista_ghl: 'crm', produccion: null,
};
const COMPARAR = [
  { valor: 'ant', texto: 'Periodo anterior' }, { valor: 'anio', texto: 'Año anterior' }, { valor: 'no', texto: 'Sin comparar' },
];
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const ESTADO_SNOV = { Active: 'Activa', Paused: 'En pausa', Draft: 'Borrador', Completed: 'Terminada', Stopped: 'Parada' };   // I11: Snov.io habla en inglés
const ESTADO_FUENTE = {
  bien: { chip: 'verde', texto: 'bien' }, a_cero: { chip: 'ambar', texto: 'a cero' }, rota: { chip: 'rojo', texto: 'rota' },
  dato_viejo: { chip: 'ambar', texto: 'dato viejo' }, sin_conectar: { chip: 'gris', texto: 'sin conectar' }, no_aplica: { chip: 'gris', texto: 'no aplica' },
};
const SELLOS = [
  ['ga4', 'Analytics', 'grafico'], ['gsc', 'Search Console', 'buscar'], ['seranking', 'SE Ranking', 'sube'], ['ghl', 'GHL', 'base'],
  ['meta', 'Meta', 'target'], ['google_ads', 'Google Ads', 'megafono'], ['snov', 'Snov.io', 'mail'], ['linkedin', 'LinkedIn', 'users'],
  ['ficha_google', 'Ficha de Google', 'pin'],
];
const SELLO_BLOQUE = { ga4: 'ga4', gsc: 'gsc', seranking: 'seranking', ghl: 'embudo', meta: 'meta', google_ads: 'google_ads', snov: 'correo', linkedin: 'linkedin', ficha_google: 'ficha_google' };
const APARTADOS = [
  ['mes', 'Cómo ha ido el mes'], ['funciona', 'Lo que funciona'], ['no_funciona', 'Lo que no'],
  ['perdidas', 'Llamadas perdidas o leads sin atender'], ['pasos', 'Próximos pasos'],
];
const RE_LEAD = /([\w.+-]+@[\w-]+(?:\.[\w-]+)+)|((?:\+?34[\s.-]?)?[6789](?:[\s.-]?\d){8})/;
const GLOSARIO = [
  ['Clics', 'Veces que alguien pulsa en la web desde Google o desde un anuncio.'],
  ['Impresiones', 'Veces que la web o el anuncio aparece en pantalla, aunque nadie pulse.'],
  ['CTR (tasa de clics)', 'Clics entre impresiones. Un 3 % es que de cada 100 que lo ven, 3 pulsan.'],
  ['CPC (coste por clic)', 'Lo que cuesta de media cada clic de un anuncio.'],
  ['Conversiones', 'Acciones que valen algo: un formulario enviado, una llamada, un clic en el teléfono o en WhatsApp.'],
  ['Coste por conversión', 'Inversión entre conversiones. Cuanto más bajo, mejor.'],
  ['Posición media', 'Puesto medio en Google. Más bajo es mejor: el 1 es el primero.'],
  ['Rebote', 'Visitas que se van sin hacer nada en la web. Más bajo es mejor.'],
  ['Duración media', 'Tiempo medio que cada usuario pasa con la web abierta y activa.'],
  ['Tráfico orgánico', 'Visitas que llegan desde Google sin pagar.'],
  ['Tráfico de pago', 'Visitas que llegan desde anuncios (Google Ads, Meta).'],
  ['Lead', 'Persona que deja sus datos (formulario, llamada o mensaje) y puede ser cliente del despacho.'],
  ['Cita', 'Reunión agendada entre el lead y el despacho, registrada en el CRM (GHL).'],
  ['Asistencia', 'Citas que se han celebrado entre citas con fecha en el periodo.'],
  ['Coste por cita', 'Inversión en publicidad entre citas agendadas.'],
  ['Coste por venta', 'Inversión entre clientes nuevos que el despacho ha marcado como ganados en el CRM.'],
  ['Alcance y frecuencia', 'Personas distintas que han visto el anuncio y cuántas veces de media lo han visto.'],
];

const CACHE = { periodo: new Map(), indice: new Map(), fila: new Map(), paridad: null, comun: null, acciones: null };
// Nombres siempre desde personas.json (ctx.nombre); si la persona vista no tiene esa ficha, el alias de reserva.
const RESERVA = { agustina: 'Agus', mili: 'Mili', tomas: 'Tomás', yessica: 'Yessica', bautista: 'Bautista' };
let CTX = null;
const nm = id => { const v = CTX?.nombre?.(id); return v && v !== 'persona sin ficha' && v !== '—' ? v : (RESERVA[id] || id); };
const ses = {
  leer: k => { try { return localStorage.getItem(k); } catch { return null; } },
  poner: (k, v) => { try { localStorage.setItem(k, v); } catch { /* sin almacenamiento */ } },
};
const rc = (el, ...xs) => el.replaceChildren(...xs.flat().filter(x => x !== null && x !== undefined && x !== false));
const n = v => (v === null || v === undefined || Number.isNaN(+v) ? null : +v);
const sum = xs => xs.reduce((a, b) => a + (n(b) || 0), 0);
const pct = (a, b) => (b ? (100 * a) / b : null);
// Punto de miles también con 4 cifras («4.801», no «4801»): es-ES no lo pone por defecto.
const num4 = (v, d = 0) => fmt.num(v === null || v === undefined || Number.isNaN(+v) ? null : +v, d);
const fNum = (v, d = 0) => num4(n(v), d);
// Espacio duro antes de % y € (no se parte «56,1 / %» en dos líneas en tablas estrechas ni en el PDF).
const fPct = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? '—' : `${num4(v, d)}\u00a0%`);
const fEur = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v) ? '—' : `${num4(v, d)}\u00a0€`);
const fSeg = s => { if (s === null || s === undefined) return '—'; const m = Math.floor(s / 60); return `${m} min ${String(Math.round(s % 60)).padStart(2, '0')} s`; };
const _M3M = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _partesMadrid = d => Object.fromEntries(new Intl.DateTimeFormat('es-ES', { timeZone: 'Europe/Madrid', day: 'numeric', month: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(d).map(x => [x.type, x.value]));
const _diaHoraMadrid = d => { const p = _partesMadrid(d); return `${+p.day}-${_M3M[+p.month - 1]}, ${p.hour}:${p.minute}`; };   // §2.3: «2-oct, 17:34»
const fHora = iso => { if (!iso) return '—'; const d = new Date(String(iso).replace(' ', 'T') + (/[zZ+]/.test(String(iso).slice(10)) ? '' : 'Z')); return Number.isNaN(+d) ? String(iso).slice(0, 16) : _diaHoraMadrid(d); };   // V2-E: hora de Madrid
const fLocal = t => { if (!t) return '—'; const [d, hh] = String(t).split(' '); return `${fDia(d.slice(0, 10))}${hh ? ', ' + hh.slice(0, 5) : ''}`; };
const fDia = iso => { const d = new Date(iso + 'T12:00:00'); return `${d.getDate()}-${MESES[d.getMonth()].slice(0, 3)}`; };
/** Rango que no se parte por el guion al final de la línea (I8): «3-ago – 1-sep» en un solo bloque. */
const fRango = (a, b) => h('span', { style: { whiteSpace: 'nowrap' } }, `${fDia(a)} – ${fDia(b)}`);

// ------------------------------------------------------------------ maquetación (en línea, solo tokens)
// Auditoría 30: ningún módulo trae hoja propia. Las rejillas van en estilo en línea con los tokens --s-*; el resto, clases comunes.
const PILA = (g = 4) => ({ display: 'grid', gap: `var(--s-${g})`, minWidth: '0' });
const REJ = min => ({ display: 'grid', gap: 'var(--s-4)', gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${min}px), 1fr))`, alignItems: 'start' });
const SUB = { class: 'titulo-seccion', style: { marginBottom: 'var(--s-2)', breakAfter: 'avoid' } };   // el subtítulo no se queda solo al pie del folio
const DELTA = { bien: 'var(--good-ink)', mal: 'var(--bad-ink)', igual: 'var(--dim)' };
const deltaEl = (k, txt) => h('span', { style: { font: 'var(--t-meta)', fontWeight: '700', color: DELTA[k], whiteSpace: 'nowrap' } }, txt);
const CORTE = { display: 'block', maxWidth: '420px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' };
const AVISO_ROJO = { background: 'var(--bad-soft)', borderColor: 'var(--bad-line)', color: 'var(--bad-ink)' };

// ------------------------------------------------------------------ gráficos: el motor único grafico() de componentes.js
/** lineas({ x, series: [{ nombre, y, color, ant }], formato, barras, titulo, leyenda }) → grafico() (letra de 12 px, marcas
 *  redondas, burbuja). Se queda el nombre para no tocar los bloques. Sin serie: una línea de 40 px, no un vacío grande. */
function lineas(o) {
  const series = (o.series || []).filter(s => s.y && s.y.some(v => v !== null && v !== undefined)).map(s => ({ ...s, color: s.ant ? undefined : s.color }));
  if ((!series.length && !o.barras) || (o.x || []).length < 2) return vacioLinea('Sin días que dibujar: la fuente no trae serie diaria en este periodo.', { icono: 'grafico' });
  return grafico({ x: o.x, series, barras: o.barras ? { ...o.barras, escalaPropia: true } : undefined, formato: o.formato, titulo: o.titulo && o.leyenda ? o.titulo : undefined, leyenda: o.leyenda, alto: o.alto || 200 });
}

function barras(items, { formato = v => fNum(v), max, fuente } = {}) {
  if (!items.length) return vacioLinea(`${fuente || 'La fuente'} no trae datos de estas fechas. Si esperabas datos, prueba con un periodo más largo.`, { icono: 'grafico' });
  const m = max || Math.max(...items.map(x => x.v || 0), 1);
  return h('div', { style: PILA(2) }, items.map(x => h('div', { title: `${x.t}: ${formato(x.v)}`, style: { display: 'grid', gridTemplateColumns: 'minmax(80px, 1.1fr) minmax(0, 1.6fr) minmax(56px, auto)', gap: 'var(--s-3)', alignItems: 'center' } },
    h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, x.t),
    barraProgreso({ valor: x.v || 0, max: m, etiqueta: `${x.t}: ${formato(x.v)}` }),
    h('b', { style: { textAlign: 'right', whiteSpace: 'nowrap' } }, formato(x.v), x.extra ? h('span', { class: 'sub', style: { marginLeft: 'var(--s-2)' } }, x.extra) : null))));
}

/** delta(actual, anterior, { mejorSi, puestos }) → span con ▲/▼ y el color según si subir es bueno. */
function delta(a, b, { mejorSi = 'alto', puestos = false } = {}) {
  if (a === null || a === undefined || b === null || b === undefined) return deltaEl('igual', '—');
  if (puestos) {
    const d = Math.round((b - a) * 10) / 10; // subir en Google = bajar el número
    if (!d) return deltaEl('igual', '=');
    return deltaEl(d > 0 ? 'bien' : 'mal', `${d > 0 ? '▲ +' : '▼ '}${num4(d, Math.abs(d) < 10 && d % 1 ? 1 : 0)} ${Math.abs(d) === 1 ? 'puesto' : 'puestos'}`);
  }
  if (!b && !a) return deltaEl('igual', 'sin actividad');
  if (!b) return deltaEl('bien', 'nuevo');
  const v = variacion(a, b);
  const bien = v === 0 ? 'igual' : (v > 0) === (mejorSi !== 'bajo') ? 'bien' : 'mal';
  return deltaEl(bien, `${v > 0 ? '▲' : v < 0 ? '▼' : '='} ${num4(Math.abs(v), Math.abs(v) < 10 ? 1 : 0)} %`);
}

/** comparación para tile(): con «nuevo» y «sin actividad» (G4 §3). */
function cmpTile(a, b, txt, { mejorSi = 'alto', puestos = false } = {}) {
  if (!txt) return undefined;
  if (a === null || a === undefined) return undefined;
  if (b === null || b === undefined) return { texto: `sin dato ${txt.replace(/^frente al /, 'del ').replace(/^frente a /, 'de ')}` };
  if (puestos) { const d = Math.round((b - a) * 10) / 10; return { delta: d, unidad: ' puestos', dec: 1, texto: txt, mejorSi: 'alto' }; }
  if (!a && !b) return { texto: 'sin actividad en los dos' };
  if (!b) return { texto: `nuevo (0 ${txt.replace(/^frente al /, 'en el ').replace(/^frente a /, 'en ')})` };
  return { delta: variacion(a, b), pct: true, texto: txt, mejorSi };
}

/** Tabla con buscador, «ver más» y apilado en móvil (las grandes: URLs, consultas, palabras clave). */
function tablaGrande({ columnas, filas, inicial = 10, buscar, vacio: v, titulo, fuente }) {
  if (window.matchMedia('(max-width: 640px)').matches) inicial = Math.min(inicial, 5);
  const caja = h('div', { style: PILA(2) });
  if (!filas.length) { caja.append(vacioLinea(v?.titulo || `${fuente || 'La fuente'} no trae ${titulo || 'filas'} de estas fechas. Es normal si la web o la campaña son nuevas; si no, prueba con un periodo más largo.`, { icono: v?.icono || 'vacio' })); return caja; }
  let q = ''; let todas = false;
  const zona = h('div', { style: PILA(2) });
  // La columna principal (URL, consulta) se corta con «…» y el texto entero va en el title.
  const cols = columnas.map(c => (c.principal ? { ...c, celda: r => { const x = c.celda(r); return typeof x === 'string' ? h('span', { style: { ...CORTE, maxWidth: globalThis.matchMedia?.('print').matches ? '150px' : '420px' }, title: x, 'data-corte': '' }, x) : x; } } : c));
  const pintar = () => {
    const fs = filas.filter(r => !q || String(buscar(r)).toLowerCase().includes(q));
    const vis = todas ? fs : fs.slice(0, inicial);
    rc(zona, tablaApilable({ columnas: cols, filas: vis, porPagina: 0, vacio: { titulo: 'Nada con ese texto' } }),
      fs.length > inicial ? h('div', { class: 'tabla-mas' }, h('button', { type: 'button', class: 'bt', on: { click: () => { todas = !todas; pintar(); } } },
        icono(todas ? 'chev' : 'mas'), todas ? 'Ver menos' : `Ver las ${num4(fs.length)} filas`)) : null);
  };
  if (buscar && filas.length > inicial) {
    const inp = h('input', { type: 'search', placeholder: `Buscar ${titulo || ''}…`.trim(), 'aria-label': `Buscar ${titulo || 'en la tabla'}` });
    inp.addEventListener('input', () => { q = inp.value.trim().toLowerCase(); pintar(); });
    caja.append(h('div', { class: 'fila no-imprimir', style: { justifyContent: 'space-between' } }, h('label', { class: 'campo', style: { flex: '0 1 280px' } }, inp), h('span', { class: 'sub' }, `${num4(filas.length)} filas`)));
  }
  caja.append(zona); pintar();
  return caja;
}
const barrita = (v, max) => h('span', { class: 'fila', style: { justifyContent: 'flex-end', flexWrap: 'nowrap' } }, h('span', { style: { width: '56px' } }, barraProgreso({ valor: v || 0, max: max || 1 })), fNum(v));

// ------------------------------------------------------------------ datos
async function periodo(ctx, pid) {
  if (!CACHE.periodo.has(pid)) CACHE.periodo.set(pid, ctx.datosModulo(`informe/p_${pid}`));
  return CACHE.periodo.get(pid);
}
// Auditoría 37 (causa 5): para abrir UN cliente no se baja el periodo entero (68 clientes, 1,7 MB): un índice ligero
// (i_<periodo>: qué fuentes trae cada cliente) y la fila de ese cliente (c_<periodo>/<cliente>), las dos recortadas por
// servir.py igual que p_<periodo> (fuentes_informe/partir_informe.py). Si falta una pieza, se usa el periodo entero.
const yoDe = ctx => ctx.persona?.id || '';
const NOTA_FUENTES = ['ga4', 'gsc', 'meta', 'seranking', 'snov', 'google_ads', 'embudo'];
async function indice(ctx, pid) {
  const k = `${yoDe(ctx)}|${pid}`;
  if (!CACHE.indice.has(k)) {
    CACHE.indice.set(k, ctx.datosModulo(`informe/i_${pid}`).catch(async () => {
      const d = await periodo(ctx, pid);
      return { ...d, filas: (d.filas || []).map(f => ({ cliente_id: f.cliente_id, con: NOTA_FUENTES.filter(x => f[x]) })) };
    }));
  }
  return CACHE.indice.get(k);
}
async function filaCliente(ctx, pid, cid) {
  const k = `${yoDe(ctx)}|${pid}|${cid}`;
  if (!CACHE.fila.has(k)) {
    CACHE.fila.set(k, ctx.datosModulo(`informe/c_${pid}/${encodeURIComponent(cid)}`)
      .then(d => (d.filas || []).find(x => x.cliente_id === cid) || null)
      .catch(async () => ((await periodo(ctx, pid)).filas || []).find(x => x.cliente_id === cid) || null));
  }
  return CACHE.fila.get(k);
}
async function acciones(ctx, recargar) {
  if (!ctx.servidor) return [];
  if (!CACHE.acciones || recargar) CACHE.acciones = ctx.api(`acciones?modulo=${MOD}`).then(d => d.acciones || []).catch(() => []);
  const vis = new Set(ctx.clientesVisibles.map(c => c.id));
  return (await CACHE.acciones).filter(a => !a.cliente_id || vis.has(a.cliente_id));
}
const vp = a => { try { return typeof a.vista_previa === 'string' ? JSON.parse(a.vista_previa) : a.vista_previa || {}; } catch { return {}; } };

function bloquesDe(ctx) {
  const ps = ctx.persona.puestos || [];
  const perfiles = ps.filter(p => PUESTO_PERFIL[p] !== null).map(p => PUESTO_PERFIL[p]);
  if (!perfiles.length || perfiles.some(x => !x)) return new Set(TODO);
  return new Set(perfiles.flatMap(p => PERFIL[p]));
}
const puedeEscribir = (ctx, cid) => !ctx.soloLectura && (ctx.nivel === 'todo' || ctx.carteraIds?.has?.(cid));
const puedeParidad = (ctx, cid) => {
  const ps = ctx.persona.puestos || [];
  if (ctx.soloLectura) return false;
  if (ps.some(p => ['direccion', 'operaciones'].includes(p))) return true;
  return ps.includes('account') && ctx.carteraPorSilla?.account?.has?.(cid);
};
const alias = (ctx, id) => { if (ctx.nombre) return ctx.nombre(id); const p = (ctx.datos.personas || []).find(x => x.id === id); return p ? (p.alias || p.nombre) : id; };

function equipoDe(ctx, c) {
  let eq = ctx.verdad?.(c.id)?.equipo || c.equipo;
  if (typeof eq === 'string') { try { eq = JSON.parse(eq.replace(/'/g, '"').replace(/\bTrue\b/g, 'true').replace(/\bFalse\b/g, 'false').replace(/\bNone\b/g, 'null')); } catch { eq = null; } }
  const out = [];
  for (const [silla, txt] of [['account', 'Account'], ['trafficker', 'Publicidad'], ['seo', 'SEO'], ['outreach', 'Outreach']]) {
    const p = (eq?.[silla] || []).find(x => x.principal) || (eq?.[silla] || [])[0];
    if (p) out.push(`${txt}: ${ctx.nombre ? ctx.nombre(p.persona_id) : alias(ctx, p.persona_id)}`);
  }
  if (!out.length && c.responsable) out.push(`Account: ${c.responsable}`);
  return out;
}

// ------------------------------------------------------------------ avisos (G4 §4)
function avisosDe(f, P, ana) {
  const out = (f.avisos || []).map(a => ({ ...a, fijo: true }));
  const F = f.fuentes || {};
  const nombre = { ga4: 'Analytics', gsc: 'Search Console', meta: 'Meta', snov: 'Snov.io' };
  for (const k of Object.keys(nombre)) {
    if (F[k]?.estado === 'rota') out.push({ color: 'rojo', tipo: 'rota', texto: `${nombre[k]}: la fuente falla (${F[k].nota || 'error'}).`, quien: `${nm('agustina')} (técnico) y el account; a las 48 h, ${nm('mili')}`, bloque: k === 'snov' ? 'correo' : k });
    if (F[k]?.estado === 'a_cero') out.push({ color: 'ambar', tipo: 'a_cero', texto: `${nombre[k]}: todo a cero ${enP(P)} con la fuente conectada.`, quien: k === 'meta' ? 'Account y trafficker: marcar «parado a propósito desde…»' : 'Dueño del bloque', bloque: k === 'snov' ? 'correo' : k });
  }
  const caida = (a, b, que, bloque) => { if (b > 20 && a !== null && a !== undefined && a < 0.2 * b) out.push({ color: 'ambar', tipo: 'caida', texto: `${que} cae un ${num4(100 - (100 * a) / b, 0)} % frente al periodo anterior (${fNum(a)} frente a ${fNum(b)}).`, quien: 'Dueño del bloque', bloque }); };
  caida(f.ga4?.actual?.usuarios, f.ga4?.anterior?.usuarios, 'Usuarios de la web', 'ga4');
  caida(f.gsc?.web?.actual?.clics, f.gsc?.web?.anterior?.clics, 'Clics desde Google', 'gsc');
  caida(f.meta?.actual?.leads, f.meta?.anterior?.leads, 'Leads de Meta', 'meta');
  if (f.meta?.actual && f.meta.conjuntos?.length && f.meta.actual.gasto !== undefined) {
    const s = sum(f.meta.conjuntos.map(x => x.gasto));
    if (f.meta.actual.gasto && Math.abs(s - f.meta.actual.gasto) / f.meta.actual.gasto > 0.01) out.push({ color: 'ambar', tipo: 'no_cuadra', texto: `Meta: la suma de los conjuntos (${fEur(s, 2)}) no da el total (${fEur(f.meta.actual.gasto, 2)}).`, quien: 'Trafficker', bloque: 'meta' });
  }
  if (P.id === 'u30' && f.gsc?.serie?.length) {
    const ult = f.gsc.serie.at(-1)[0]; const dias = Math.round((new Date(P.hasta) - new Date(ult)) / 864e5);
    if (dias > 4) out.push({ color: 'ambar', tipo: 'viejo', texto: `Search Console: último dato del ${fDia(ult)} (más de 4 días).`, quien: 'SEO del cliente', bloque: 'gsc' });
  }
  if (ana?.otro) out.push({ color: 'ambar', tipo: 'otro_mes', texto: `El último análisis escrito es de ${ana.otro}, no ${deP(P)}.`, quien: 'Account', bloque: 'analisis' });
  if (ana?.actual && RE_LEAD.test(Object.values(ana.actual.apartados || {}).join(' '))) out.push({ color: 'rojo', tipo: 'datos_leads', texto: 'El análisis lleva un correo o un teléfono: los datos de leads no van en el informe.', quien: 'Account', bloque: 'analisis' });
  return out;
}
const bloqueaPDF = av => av.some(a => a.color === 'rojo' && ['otro_cliente', 'datos_leads'].includes(a.tipo));

function aviso(a) {
  return h('div', { class: `aviso no-imprimir${a.color === 'azul' ? ' info' : ''}`, style: a.color === 'rojo' ? AVISO_ROJO : null, role: a.color === 'rojo' ? 'alert' : 'note' },
    h('span', { class: 'ico', 'aria-hidden': 'true' }, icono(a.color === 'azul' ? 'info' : 'alert')),
    h('div', {}, h('b', {}, a.titulo || ({ rota: 'Fuente rota.', a_cero: 'Todo a cero.', caida: 'Caída brusca.', viejo: 'Dato viejo.', otro_cliente: 'Cuenta que no es del cliente.', no_cuadra: 'Cifras que no cuadran.', otro_mes: 'Análisis de otro mes.', datos_leads: 'Datos de leads en un texto.', sin_acceso: 'Looker sin acceso.', sin_acceso_google: 'Falta acceso en Google.', rango: 'Rango mezclado en Looker.' }[a.tipo] || 'Aviso.')), ' ', a.texto,
      a.quien ? h('small', { style: { display: 'block', marginTop: 'var(--s-1)', font: 'var(--t-meta)' } }, `Le llega a: ${a.quien}`) : null));
}

// =================================================================== módulo
export default {
  id: MOD,
  titulo: 'Informe del cliente',
  grupo: 'Clientes',
  // Periodo común (ronda 9): la barra de la carcasa elige las fechas; el informe enseña el periodo cerrado que mejor casa.
  usa_periodo: ['30d', 'mes_ant', 'medida'],
  puestos_que_lo_ven: {
    direccion: 'todo', finanzas_direccion: 'todo', operaciones: 'todo', proyectos: 'todo', jefa_publicidad: 'todo', jefa_seo: 'todo',
    jefa_crm: 'todo', account: 'suyo', trafficker: 'suyo', seo: 'suyo', ficha_google: 'suyo', outreach: 'suyo',
  },

  async render(cont, ctx) {
    vigilarCortes(cont);
    CTX = ctx;
    document.getElementById('informe-estilos')?.remove();   // hoja de antes de la guía 30
    cont.replaceChildren(esqueleto({ tarjetas: 4, lineas: 4 }));
    try {
      CACHE.comun ??= ctx.datosModulo('informe/comun');
      // auditoría 37: lo que no depende del periodo sale a la vez (antes: comun → paridad → periodo, en serie)
      if (ctx.clientesVisibles.length) { CACHE.paridad ??= ctx.datosModulo('informe/paridad'); CACHE.paridad.catch(() => null); acciones(ctx); }
      const comun = await CACHE.comun;
      const [vista] = ctx.params;
      const raiz = h('div', { style: PILA(4), 'data-informe': '' });
      const tabs = h('div', { class: 'segm', role: 'group', 'aria-label': 'Vista' },
        h('button', { type: 'button', 'aria-pressed': String(vista !== 'paridad'), on: { click: () => ctx.navegar(MOD) } }, icono('grafico', { clase: 's' }), ' Informe'),
        h('button', { type: 'button', 'aria-pressed': String(vista === 'paridad'), on: { click: () => ctx.navegar(`${MOD}/paridad`) } }, icono('capas', { clase: 's' }), ' Comparación con Looker'));
      raiz.append(h('div', { class: 'no-imprimir' }, tabs));
      cont.replaceChildren(raiz);
      if (vista === 'paridad') await pintarParidad(raiz, ctx, comun);
      else await pintarInforme(raiz, ctx, comun);
    } catch (e) {
      cont.replaceChildren(vacio({ icono: 'alert', tono: 'aviso', titulo: 'No se ha podido cargar el informe', texto: String(e?.message || e), quien: 'Tomás' }));
    }
  },
};

// =================================================================== informe
async function pintarInforme(raiz, ctx, comun) {
  const visibles = ctx.clientesVisibles;
  if (!visibles.length) {
    raiz.append(vacio({ icono: 'cli', titulo: 'No llevas ningún cliente con informe', texto: 'El informe sale para los clientes de tu cartera. Si falta alguno, la asignación se cambia en Ajustes.', quien: nm('mili') }));
    return;
  }
  const par = await (CACHE.paridad ??= ctx.datosModulo('informe/paridad'));
  PARIDAD_BLOQUES = Object.fromEntries((par.filas || []).map(p => [p.cliente_id, p.bloques]));
  const P0 = comun.periodos;
  const clave = `ro.informe.${ctx.persona.id}`;
  let [cid] = ctx.params;
  const casa = periodoDelInforme(ctx.periodo, P0, comun.defecto);
  const pid = casa.pid;
  const cmp = casa.cmp;
  if (!cid || !visibles.some(c => c.id === cid)) {
    // Sin cliente en la dirección: el último que abrió; si no, el de su cartera con más fuentes (nunca uno vacío).
    const ultimoId = ses.leer(`${clave}.cliente`);
    if (visibles.some(c => c.id === ultimoId)) filaCliente(ctx, pid, ultimoId).catch(() => null);   // a la vez que el índice
    const docP = await indice(ctx, pid);
    const nota = id => { const f = (docP.filas || []).find(x => x.cliente_id === id); return f ? (f.con || []).length : 0; };
    const ord = [...visibles].sort((a, b) => (b.enCartera ? 1 : 0) - (a.enCartera ? 1 : 0) || nota(b.id) - nota(a.id));
    const ultimo = visibles.find(c => c.id === ses.leer(`${clave}.cliente`));
    cid = (ultimo && nota(ultimo.id) ? ultimo : ord.find(c => nota(c.id)) || ord[0]).id;
  }
  const estado = { cid, pid, cmp };
  const zona = h('div', { style: PILA(4) });
  const bloques = bloquesDe(ctx);
  // El selector de cliente ES el título de la cabecera del informe (el nombre sale una sola vez).
  const sel = selectorCliente({ clientes: visibles, actual: cid, etiqueta: 'Cliente del informe', alElegir: c => { estado.cid = c.id; repintar(); } });
  raiz.append(zona);

  async function repintar() {
    ses.poner(`${clave}.cliente`, estado.cid);
    try { const u = new globalThis.URL(location.href); u.hash = `#/${MOD}/${estado.cid}`; history.replaceState(null, '', u.toString()); } catch { /* nada */ }
    rc(zona, esqueleto({ tarjetas: 4, lineas: 3 }));
    const P = P0.find(p => p.id === estado.pid);
    const [f, acc] = await Promise.all([filaCliente(ctx, estado.pid, estado.cid), acciones(ctx)]);
    const doc = { filas: f ? [f] : [] };
    const c = visibles.find(x => x.id === estado.cid);
    ctx.titulo('Informe del cliente', P.texto);
    if (!f) {
      rc(zona, vacio({ icono: 'vacio', titulo: `Sin datos de ${c.nombre}`, texto: 'Este cliente no está en la capa de datos del informe.', quien: `${nm('agustina')} (emparejar sus cuentas)` }));
      return;
    }
    pintarCliente(zona, ctx, { c, f, P, P0, cmp: estado.cmp, acc, bloques, doc, sel, casa });
  }
  await repintar();
}

/** El informe tiene periodos cerrados (meses, 30 días, trimestre). Casa el periodo común de la carcasa con el suyo:
 *  igual de fechas → ese; «30 días» → los últimos 30; si no, el de más días en común (y lo dice). */
const _dia = s => Date.parse(`${s}T12:00:00Z`);
function periodoDelInforme(per, P0, defecto) {
  const cmp = ({ anterior: 'ant', anio_ant: 'anio', no: 'no' })[per?.comparar] || 'ant';
  if (!per?.desde) return { pid: defecto, cmp, exacto: true };
  if (per.id === '30d') return { pid: 'u30', cmp, exacto: true };
  const igual = P0.find(p => p.desde === per.desde && p.hasta === per.hasta);
  if (igual) return { pid: igual.id, cmp, exacto: true };
  const solape = p => Math.max(0, Math.min(_dia(p.hasta), _dia(per.hasta)) - Math.max(_dia(p.desde), _dia(per.desde)));
  const mejor = [...P0].sort((a, b) => solape(b) - solape(a) || (_dia(a.hasta) - _dia(a.desde)) - (_dia(b.hasta) - _dia(b.desde)))[0];
  return { pid: solape(mejor) > 0 ? mejor.id : defecto, cmp, exacto: false, pedido: per.texto || per.nombre || per.rango || '' };
}
/** Enlace al mismo informe con otro periodo cerrado (la barra común lo recoge del enlace: ?p=…&desde=…&hasta=…). */
function enlacePeriodo(p, cmp, cid) {
  try {
    const u = new globalThis.URL(location.href);
    if (p.id === 'u30') { u.searchParams.set('p', '30d'); u.searchParams.delete('desde'); u.searchParams.delete('hasta'); }
    else { u.searchParams.set('p', 'medida'); u.searchParams.set('desde', p.desde); u.searchParams.set('hasta', p.hasta); }
    u.searchParams.set('c', ({ ant: 'anterior', anio: 'anio_ant', no: 'no' })[cmp] || 'anterior');
    u.hash = `#/${MOD}/${cid}`;
    return u.toString();
  } catch { return null; }
}

function textoComparar(P, cmp) {
  if (cmp === 'no') return null;
  const [a, b] = cmp === 'anio' ? P.anio_anterior : P.anterior;
  const d1 = new Date(a + 'T12:00:00'), d2 = new Date(b + 'T12:00:00');
  if (d1.getDate() === 1 && d2.getMonth() === d1.getMonth() && new Date(d2.getTime() + 864e5).getDate() === 1) return `frente a ${MESES[d1.getMonth()]}${cmp === 'anio' ? ' ' + d1.getFullYear() : ''}`;
  // I8: en las tarjetas, «frente al periodo anterior» (las fechas van en la cabecera y no se parten en dos líneas).
  return cmp === 'anio' ? 'frente al año anterior' : 'frente al periodo anterior';
}
/** Las fechas de la comparación, para la cabecera: «frente a 3-ago – 1-sep». */
function rangoComparar(P, cmp) {
  if (cmp === 'no') return null;
  const [a, b] = cmp === 'anio' ? P.anio_anterior : P.anterior;
  return [' · frente a ', fRango(a, b), cmp === 'anio' ? ` ${new Date(a + 'T12:00:00').getFullYear()}` : ''];
}

function analisisDe(acc, cid, pid) {
  const todas = acc.filter(a => a.cliente_id === cid && a.tipo === 'analisis_mes').map(a => ({ ...a, vp: vp(a) }));
  const anuladas = new Set(todas.filter(a => a.vp.anula).map(a => Number(a.vp.anula)));
  const mias = todas.filter(a => !a.vp.anula && !anuladas.has(Number(a.id))).sort((a, b) => String(b.creada).localeCompare(String(a.creada)) || b.id - a.id);
  const actual = mias.find(a => a.vp.periodo === pid);
  const otro = !actual && mias[0] ? mias[0].vp.periodo_texto || mias[0].vp.periodo : null;
  return { actual: actual ? { ...actual.vp, quien: actual.quien, creada: actual.creada } : null, otro, historial: mias };
}

function pintarCliente(zona, ctx, X) {
  const { c, f, P, P0, cmp, acc, bloques } = X;
  const txt = textoComparar(P, cmp);
  const ana = analisisDe(acc, c.id, P.id);
  const av = avisosDe(f, P, ana);
  const veInversion = ctx.ver({ tipo: 'inversion', cliente_id: c.id }).ok;
  const S = { ...X, ctx, txt, ana, av, veInversion };

  // ---- cabecera: el selector de cliente es el título; el periodo lo pone la barra común; las fuentes, en un solo chip
  const fuentes = SELLOS.filter(([k]) => (bloques.has(SELLO_BLOQUE[k]) || (k === 'ghl' && bloques.has('embudo'))) && f.fuentes?.[k]?.estado !== 'no_aplica').map(([k, nom, ico]) => {
    const fu = f.fuentes?.[k] || { estado: 'sin_conectar' };
    return { k, nom, ico, fu, e: ESTADO_FUENTE[fu.estado] || ESTADO_FUENTE.sin_conectar };
  });
  const nBien = fuentes.filter(x => x.e.chip === 'verde').length;
  const peorChip = fuentes.some(x => x.e.chip === 'rojo') ? 'rojo' : fuentes.some(x => x.e.chip === 'ambar') ? 'ambar' : nBien ? 'verde' : 'gris';
  const chipFuentes = h('details', { class: 'no-imprimir' },
    h('summary', { class: `chip ${peorChip}`, style: { cursor: 'pointer', minHeight: '32px' } }, `Datos: ${nBien} de ${fuentes.length} fuentes al día`),
    h('div', { class: 'fila', style: { marginTop: 'var(--s-2)' } }, fuentes.map(x => h('button', { type: 'button', class: 'bt mini',
      title: [x.fu.nota, x.fu.hora ? `Último dato: ${fLocal(String(x.fu.hora).slice(0, 16))}` : null].filter(Boolean).join(' · ') || x.e.texto,
      on: { click: () => document.getElementById(`inf-b-${SELLO_BLOQUE[x.k]}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) } },
      chipEstado(x.e.chip, x.nom), h('span', { class: 'sub' }, x.fu.hora && !['sin_conectar', 'no_aplica'].includes(x.fu.estado) ? fLocal(String(x.fu.hora).slice(0, 16)) : x.e.texto)))));
  const pdfBloq = bloqueaPDF(av);
  const otros = P0.filter(p => p.id !== P.id).map(p => { const href = enlacePeriodo(p, cmp, c.id); return href ? h('a', { href }, p.texto.replace(' 2026', '').toLowerCase()) : null; }).filter(Boolean);
  const cab = h('section', { class: 'panel no-imprimir', 'aria-label': 'Cabecera del informe' },
    h('div', { class: 'cuerpo pila' },
      h('div', { class: 'fila', style: { justifyContent: 'space-between', alignItems: 'flex-start' } },
        h('div', { style: { ...PILA(1), flex: '1 1 320px' } }, X.sel,
          h('div', { class: 'fila sub' }, equipoDe(ctx, c).map(t => h('span', {}, t)), f.looker ? h('a', { href: f.looker.url, target: '_blank', rel: 'noopener', style: { display: 'inline-flex', alignItems: 'center', minHeight: '32px' } }, icono('ext', { clase: 's' }), ' Su Looker') : null)),
        h('div', { class: 'fila no-imprimir' },
          h('button', { type: 'button', class: 'bt', title: 'Copiar el enlace con este cliente y estas fechas', on: { click: () => copiar(location.href, 'Enlace copiado') } }, icono('link'), 'Copiar enlace'),
          h('button', { type: 'button', class: 'bt', on: { click: () => document.getElementById('inf-b-analisis')?.scrollIntoView({ behavior: 'smooth' }) } }, icono('editar'), 'Preparar el mes'),
          h('button', { type: 'button', class: 'bt pri', 'aria-disabled': pdfBloq ? 'true' : null, title: pdfBloq ? 'Bloqueado: hay un aviso rojo (cuenta de otro cliente o datos de leads)' : 'Imprimir o guardar como PDF',
            on: { click: () => { if (pdfBloq) { avisoFlotante('PDF bloqueado: arregla antes el aviso rojo', { icono: 'alert' }); return; } ctx.rastro({ accion: 'descargar_pdf', objeto: `${c.id}/${P.id}` }); window.print(); } } }, icono('descarga'), 'Descargar PDF'))),
      h('div', { class: 'fila', style: { justifyContent: 'space-between' } },
        h('p', { class: 'sub' }, `${P.texto} (`, fRango(P.desde, P.hasta), ')', rangoComparar(P, cmp), f.fuentes?.gsc?.hasta_dato && f.fuentes.gsc.hasta_dato < P.hasta ? ` · Search Console hasta el ${fDia(f.fuentes.gsc.hasta_dato)}` : ''),
        chipFuentes),
      X.casa && !X.casa.exacto ? avisoParcial(`El informe va por periodos cerrados: enseño ${artP(P)}, el que más se parece a lo elegido arriba.`, { tipo: 'info' }) : null,
      otros.length ? h('p', { class: 'sub no-imprimir', style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', columnGap: '4px' } }, 'Otros periodos con informe: ', otros.flatMap((a, i) => { a.style.display = 'inline-flex'; a.style.alignItems = 'center'; a.style.minHeight = '32px'; return i ? [' · ', a] : [a]; })) : null));   // V2: zona de toque de 32 px

  // I4: la cabecera del papel es la común de la carcasa (logo y nombre de RO, título, periodo y fecha de impresión): aquí
  // solo se le da el título con el cliente y las fechas. La cabecera de pantalla (selector ▾, botones, chips) no se imprime.
  const cmpTxt = cmp === 'no' ? '' : ` · frente a ${fDia((cmp === 'anio' ? P.anio_anterior : P.anterior)[0])} – ${fDia((cmp === 'anio' ? P.anio_anterior : P.anterior)[1])}`;
  ctx.titulo(`Informe de ${c.nombre}`, `${P.texto} (${fDia(P.desde)} – ${fDia(P.hasta)})${cmpTxt}`);
  rc(zona, cab);
  const enBloques = av.filter(a => !a.fijo && a.bloque && bloques.has(a.bloque));
  const arriba = av.filter(a => a.fijo || !a.bloque);
  if (enBloques.length) arriba.push({ color: enBloques.some(a => a.color === 'rojo') ? 'rojo' : 'ambar', titulo: `${fmt.plural(enBloques.length, 'aviso')} en:`, texto: enBloques.map(a => BLOQUES.find(b => b.id === a.bloque)?.texto).filter((x, i, xs) => xs.indexOf(x) === i).join(' · ') + '. El detalle va dentro de cada bloque.' });
  if (arriba.length) zona.append(h('div', { class: 'no-imprimir', style: PILA(2) }, arriba.map(aviso)));

  // G4 §2: un bloque sin fuente para ese cliente no se pinta vacío; se junta en una sola caja con quién lo arregla.
  const sinDatos = [];
  const sinPapel = [];
  const aCero = [];      // bloques plegados por estar a cero: en el papel, una línea (el plegado no se imprime)
  for (const b of BLOQUES) {
    if (!bloques.has(b.id)) continue;
    if (!tieneDatos(b.id, f)) { const fu = f.fuentes?.[FUENTE_DE[b.id]]; if (!(b.id === 'google_ads' && fu?.estado === 'no_aplica') && !(b.id === 'linkedin' && !PARIDAD_BLOQUES[c.id]?.includes('linkedin'))) sinDatos.push({ b, fu }); continue; }
    const el = PINTAR[b.id](S);
    if (!el) continue;
    if (el.dataset?.interno) { sinPapel.push(b.texto); zona.append(interno(h('section', { id: `inf-b-${b.id}`, style: { ...PILA(4), scrollMarginTop: '128px' } }, el))); continue; }
    const cero = todoACero(b.id, f);
    if (cero) aCero.push(`${b.texto}, ${cero}`);
    // Guía 30 (3.9): un bloque con todo a cero se pliega en una sola línea; el detalle, al abrirlo.
    zona.append(cero ? h('details', { class: 'panel', id: `inf-b-${b.id}`, style: { scrollMarginTop: '128px' } },
      h('summary', { class: 'fila', style: { padding: 'var(--s-3) var(--relleno)', cursor: 'pointer', minHeight: '44px' } },
        h('span', { class: 'ico-c s gris' }, icono(b.icono)), h('b', {}, b.texto), h('span', { class: 'sub' }, `· ${cero} ${enP(P)}`), h('span', { class: 'enlace no-imprimir', style: { marginLeft: 'auto' } }, 'Ver por qué')),
      el) : h('section', { id: `inf-b-${b.id}`, style: { ...PILA(4), scrollMarginTop: '128px' } }, el));
  }
  if (sinDatos.length) {
    const caja = panel({ titulo: 'Sin fuente para este cliente', icono: 'plug', sub: 'Cada uno dice qué falta y quién lo arregla.' },
      h('div', { class: 'cuerpo' }, tablaApilable({ columnas: [
        { titulo: 'Bloque', principal: true, celda: x => h('span', { class: 'fila', style: { flexWrap: 'nowrap' } }, h('span', { class: 'ico-c s gris' }, icono(x.b.icono)), x.b.texto) },
        { titulo: 'Qué falta', celda: x => h('span', { class: 'sub' }, FALTA_TEXTO(x.b.id, x.fu, f)) },
        { titulo: 'Lo arregla', celda: x => QUIEN_ARREGLA()[x.b.id] || nm('agustina') },
        { titulo: 'Abrir', celda: x => atajo(URL[x.b.id]?.(f), ABRIR[x.b.id]) || (f.looker ? atajo(f.looker.url, 'Ver en su Looker') : h('span', { class: 'sub' }, '—')) }], filas: sinDatos })));
    const ref = zona.querySelector('#inf-b-analisis');
    const sec = h('section', { id: 'inf-b-sin', class: 'no-imprimir', style: { ...PILA(4), scrollMarginTop: '128px' } }, caja);
    sinPapel.push(...sinDatos.map(x => x.b.texto));
    for (const x of sinDatos) { const ancla = h('span', { id: `inf-b-${x.b.id}` }); sec.prepend(ancla); }
    ref ? zona.insertBefore(sec, ref) : zona.append(sec);
  }
  if (sinPapel.length) {   // I1: en el papel, una línea en lugar de la caja con tareas del equipo
    const ref = zona.querySelector('#inf-b-analisis');
    const linea = soloPapel(h('p', { class: 'sub', style: SIN_CORTE }, h('b', {}, 'Fuentes no incluidas en este informe: '), `${sinPapel.join(', ')}.`));
    ref ? zona.insertBefore(linea, ref) : zona.append(linea);
  }
  if (aCero.length) {
    const ref = zona.querySelector('#inf-b-analisis');
    const linea = soloPapel(h('p', { class: 'sub', style: SIN_CORTE }, h('b', {}, `Sin actividad ${enP(P)}: `), `${aCero.join(' · ')}.`));
    ref ? zona.insertBefore(linea, ref) : zona.append(linea);
  }
  const fuera = BLOQUES.filter(b => !bloques.has(b.id)).map(b => b.texto);
  if (fuera.length) zona.append(h('p', { class: 'sub no-imprimir' }, icono('candado', { clase: 's' }), ` Tu puesto no ve: ${fuera.join(', ')}.`));
}

const FUENTE_DE = { embudo: 'ghl', ga4: 'ga4', gsc: 'gsc', seranking: 'seranking', google_ads: 'google_ads', meta: 'meta', correo: 'snov', linkedin: 'linkedin', ficha_google: 'ficha_google' };
const QUIEN_ARREGLA = () => ({ embudo: `${nm('agustina')} (emparejar Meta y GHL)`, ga4: `${nm('agustina')} · SEO`, gsc: `${nm('agustina')} · SEO`, seranking: `${nm('agustina')} · SEO`, google_ads: `${nm('tomas')} (clave de Windsor) · ${nm('agustina')} (token de Google Ads)`, meta: nm('agustina'), correo: `${nm('yessica')} y ${nm('bautista')} · ${nm('agustina')}`, linkedin: `${nm('yessica')} y ${nm('bautista')}`, ficha_google: `${nm('agustina')} (más adelante)` });
/** ¿Todo a cero con la fuente conectada? → texto corto para la línea plegada, o null. */
function todoACero(id, f) {
  const z = v => !n(v);
  if (id === 'ga4' && f.ga4 && (f.fuentes?.ga4?.estado === 'a_cero' || (z(f.ga4.actual?.usuarios) && z(f.ga4.actual?.conversiones)))) return 'todo a cero';
  if (id === 'gsc' && f.gsc && !f.bit24_propiedades && (f.fuentes?.gsc?.estado === 'a_cero' || (z(f.gsc.web?.actual?.clics) && z(f.gsc.web?.actual?.impresiones)))) return 'todo a cero';
  if (id === 'meta' && f.meta && (f.fuentes?.meta?.estado === 'a_cero' || (z(f.meta.actual?.impresiones) && z(f.meta.actual?.leads)))) return 'sin anuncios en marcha';
  if (id === 'correo' && f.snov && z(f.snov.actual?.emails_sent) && z(f.snov.historico?.emails_sent)) return 'sin envíos';
  return null;
}
function tieneDatos(id, f) {
  return {
    resumen: true, analisis: true, glosario: true, embudo: !!(f.meta || f.embudo || f.google_ads), ga4: !!f.ga4, gsc: !!f.gsc || !!f.bit24_propiedades,
    seranking: !!f.seranking || !!f.seranking_otro_periodo, google_ads: !!f.google_ads || (f.avisos || []).some(a => a.tipo === 'otro_cliente'), meta: !!f.meta,
    correo: !!f.snov, linkedin: false, ficha_google: false,
  }[id];
}
function FALTA_TEXTO(id, fu, f) {
  if (id === 'correo' && PARIDAD_BLOQUES[f.cliente_id]?.includes('correo')) return 'Su Looker lee una hoja de Google: falta el enlace de la hoja (el permiso ya está) o confirmar sus campañas en Snov.io.';
  if (id === 'linkedin') return 'Hoja de Linked Helper (no tiene API): falta el enlace de la hoja de este cliente o subir un CSV.';
  if (id === 'ficha_google') return 'Fase 2: permiso de Google Business Profile o SE Ranking Local.';
  if (id === 'embudo') return 'Sin cuenta de Meta ni subcuenta de GHL emparejadas.';
  return fu?.nota || 'Sin conectar.';
}

// ------------------------------------------------------------------ cabecera de bloque
function bloque(S, id, sub, cuerpo, { acciones: acc, frescor } = {}) {
  const b = BLOQUES.find(x => x.id === id);
  const avs = S.av.filter(a => a.bloque === id && !a.fijo);
  const el = panel({ titulo: b.texto, icono: b.icono, sub, acciones: h('div', { class: 'fila', style: { flexWrap: 'wrap', minWidth: '0', maxWidth: '100%' } }, frescor || null, acc ? interno(acc) : null) },
    h('div', { class: 'cuerpo', style: PILA(4) }, avs.map(aviso), cuerpo));
  // I7: un bloque largo puede seguir en la página siguiente (si no, deja medio folio en blanco); su cabecera no se queda sola.
  if (!['analisis', 'resumen'].includes(id)) el.style.breakInside = 'auto';
  el.querySelector(':scope > header')?.style.setProperty('break-after', 'avoid');
  return el;
}
/** Un bloque cuyo cuerpo es solo una nota para el equipo (sin datos del cliente): sale en pantalla, no en el papel. */
function bloqueInterno(S, id, sub, cuerpo) {
  const el = bloque(S, id, sub, cuerpo);
  el.dataset.interno = '1';
  return el;
}
const atajo = (href, texto) => (href ? h('a', { class: 'bt mini no-imprimir', href, target: '_blank', rel: 'noopener' }, icono('ext'), texto) : null);
const URL = {
  ga4: f => f.fuentes?.ga4?.propiedad && `https://analytics.google.com/analytics/web/#/p${String(f.fuentes.ga4.propiedad).replace('properties/', '')}/reports/intelligenthome`,
  gsc: f => f.fuentes?.gsc?.sitio && `https://search.google.com/search-console/performance/search-analytics?resource_id=${encodeURIComponent(f.fuentes.gsc.sitio)}`,
  seranking: f => (f.seranking?.site_id || f.seranking_proyecto) && `https://online.seranking.com/admin.site.rankings.site_id-${f.seranking?.site_id || f.seranking_proyecto}.html`,
  meta: f => f.fuentes?.meta?.cuenta?.id && `https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${String(f.fuentes.meta.cuenta.id).replace('act_', '')}`,
  embudo: f => f.ghl_subcuenta && `https://app.gohighlevel.com/v2/location/${f.ghl_subcuenta}/dashboard`,
  looker: f => f.looker?.url,
};
const ABRIR = { ga4: 'Abrir en Analytics', gsc: 'Abrir en Search Console', seranking: 'Abrir en SE Ranking', meta: 'Abrir en Meta', embudo: 'Abrir en GHL', looker: 'Abrir su Looker' };
const fresco = (fu, nom) => (fu?.hora ? frescura({ fuente: nom, fecha: fu.hora, estado: fu.estado === 'dato_viejo' ? 'viejo' : 'ok' }) : null);
const sinFuente = (fu, titulo, quien) => interno(vacioLinea([h('b', {}, titulo), ` · ${fu?.nota || 'Sin conectar para este cliente.'}`], { icono: 'plug', quien }));

// =================================================================== bloques
const PINTAR = {
  // ------------------------------------------------------------- 0 · Resumen
  resumen(S) {
    const { f, txt, ana, bloques } = S;
    const t = [];
    const ir = id => () => document.getElementById(`inf-b-${id}`)?.scrollIntoView({ behavior: 'smooth' });
    const cm = (k) => (S.cmp === 'anio' ? k.anio_anterior : k.anterior);
    if (f.ga4?.actual && bloques.has('ga4')) t.push(tile({ icono: 'users', etiqueta: 'Usuarios de la web', valor: fNum(f.ga4.actual.usuarios), comparacion: cmpTile(f.ga4.actual.usuarios, cm(f.ga4)?.usuarios, txt), alPulsar: ir('ga4'), ir: 'Analytics' }));
    if (f.ga4?.actual && bloques.has('ga4')) t.push(tile({ icono: 'zap', etiqueta: 'Conversiones web', valor: fNum(f.ga4.actual.conversiones), comparacion: cmpTile(f.ga4.actual.conversiones, cm(f.ga4)?.conversiones, txt), contexto: 'Eventos clave de Analytics', alPulsar: ir('ga4') }));
    if (f.gsc?.web?.actual && bloques.has('gsc')) t.push(tile({ icono: 'buscar', etiqueta: 'Clics desde Google', valor: fNum(f.gsc.web.actual.clics), comparacion: cmpTile(f.gsc.web.actual.clics, cm(f.gsc.web)?.clics, txt), contexto: `${fNum(f.gsc.web.actual.impresiones)} impresiones`, alPulsar: ir('gsc'), ir: 'Search Console' }));
    const sr = resumenSR(f.seranking);
    if (sr && bloques.has('seranking')) t.push(tile({ icono: 'sube', etiqueta: 'Posición media', valor: sr.media == null ? h('small', { class: 'dim' }, 'Fuera del top 100') : fNum(sr.media, 1), comparacion: sr.mediaIni ? cmpTile(sr.media, sr.mediaIni, 'frente al 31-ago', { puestos: true }) : undefined, contexto: `${sr.top10} de ${sr.total} palabras en el top 10`, alPulsar: ir('seranking') }));
    if (f.meta?.actual && bloques.has('meta')) {
      t.push(tile({ icono: 'target', etiqueta: 'Leads de Meta', valor: fNum(f.meta.actual.leads), comparacion: cmpTile(f.meta.actual.leads, S.cmp === 'ant' ? f.meta.anterior?.leads : null, S.cmp === 'ant' ? txt : null), alPulsar: ir('meta') }));
      if (S.veInversion && f.meta.actual.gasto !== undefined) t.push(tile({ icono: 'euro', etiqueta: 'Coste por lead (Meta)', valor: f.meta.actual.cpl != null ? fEur(f.meta.actual.cpl, 2) : null, estado: colorCifra('coste_lead', f.meta.actual.cpl), comparacion: cmpTile(f.meta.actual.cpl, S.cmp === 'ant' ? f.meta.anterior?.cpl : null, S.cmp === 'ant' ? txt : null, { mejorSi: 'bajo' }), contexto: `${fEur(f.meta.actual.gasto)} invertidos`, alPulsar: ir('meta') }));
    }
    if (f.embudo?.citas && bloques.has('embudo')) t.push(tile({ icono: 'cal', etiqueta: 'Citas agendadas', valor: fNum(f.embudo.citas.agendadas), contexto: `${fNum(f.embudo.citas.celebradas)} celebradas · ${fNum(f.embudo.citas.sin_estado)} sin marcar`, alPulsar: ir('embudo') }));
    if (f.google_ads && bloques.has('google_ads')) t.push(tile({ icono: 'megafono', etiqueta: 'Conversiones Google Ads', valor: fNum(f.google_ads.conversiones, 1), contexto: 'Muestra de septiembre (Windsor)', medible: 'medias', alPulsar: ir('google_ads') }));
    if (f.snov?.actual && bloques.has('correo')) t.push(tile({ icono: 'mail', etiqueta: 'Respuestas al correo en frío', valor: fNum(f.snov.actual.email_replies), comparacion: cmpTile(f.snov.actual.email_replies, S.cmp === 'ant' ? f.snov.anterior?.email_replies : null, S.cmp === 'ant' ? txt : null), contexto: `${fNum(f.snov.actual.emails_sent)} enviados`, alPulsar: ir('correo') }));
    const lineas3 = ana.actual ? APARTADOS.map(([k]) => ana.actual.apartados?.[k]).filter(Boolean).join(' ').split(/(?<=[.!?])\s+/).slice(0, 3).join(' ') : null;
    // Arriba, una frase de 15 px con lo que más pesa (guía 30, 3.9 · informes).
    const v = (a, b) => (a != null && b ? ` (${variacion(a, b) > 0 ? '+' : ''}${num4(variacion(a, b), 0)} %)` : '');
    const fr = [];
    if (f.gsc?.web?.actual && bloques.has('gsc')) fr.push(h('span', {}, h('b', {}, `${fNum(f.gsc.web.actual.clics)} clics`), ` desde Google${S.cmp !== 'no' ? v(f.gsc.web.actual.clics, cm(f.gsc.web)?.clics) : ''}`));
    if (f.ga4?.actual && bloques.has('ga4')) fr.push(h('span', {}, h('b', {}, `${fNum(f.ga4.actual.usuarios)} usuarios`), ` en la web${S.cmp !== 'no' ? v(f.ga4.actual.usuarios, cm(f.ga4)?.usuarios) : ''}`));
    if (f.meta?.actual && bloques.has('meta')) fr.push(h('span', {}, h('b', {}, `${fNum(f.meta.actual.leads)} leads`), ' de Meta'));
    const frase = fr.length ? h('p', { class: 'lead' }, `${enP(S.P).replace(' 2026', '').replace(/^e/, 'E')}, `, fr.slice(0, 3).flatMap((x, i) => (i ? [i === fr.slice(0, 3).length - 1 ? ' y ' : ', ', x] : [x])), '.') : null;
    return bloque(S, 'resumen', 'Lo que más importa del periodo, con su comparación.',
      [frase, t.length ? tiles(t.slice(0, 8)) : interno(vacioLinea('Ninguna fuente con datos para este cliente en tu vista: el chip «Datos» de arriba dice qué falta conectar.', { icono: 'res', quien: nm('agustina') })),
        lineas3 ? h('div', { style: PILA(1) }, h('p', SUB, icono('editar', { clase: 's' }), 'Del análisis del mes'), h('p', {}, lineas3))
          : interno(h('div', { style: PILA(1) }, h('p', SUB, icono('editar', { clase: 's' }), 'Del análisis del mes'),
            h('p', { class: 'sub' }, ana.otro ? `Sin análisis de este periodo (el último es de ${ana.otro}).` : 'Sin análisis escrito todavía: se escribe abajo, en «Análisis del mes».')))]);
  },

  // ------------------------------------------------------------- 1 · Embudo hasta la venta
  embudo(S) {
    const { f, P, veInversion } = S;
    const m = f.meta?.actual; const e = f.embudo; const g = f.google_ads;
    if (!m && !e && !g) return bloqueInterno(S, 'embudo', 'Gasto → leads → citas → asistidas → ventas, con el CRM del despacho (GHL).', sinFuente(f.fuentes?.ghl, 'Sin publicidad ni CRM conectados', `${nm('agustina')} (emparejar cuenta de Meta y subcuenta de GHL)`));
    const inversion = veInversion ? (sum([m?.gasto, g?.coste]) || null) : undefined;
    const pasos = [
      { t: 'Inversión', ico: 'euro', v: inversion, f: v => fEur(v), sub: [m ? 'Meta' : null, g ? 'Google Ads' : null].filter(Boolean).join(' + '), dinero: true },
      { t: 'Leads (publicidad)', ico: 'target', v: (m?.leads ?? null) !== null || g ? sum([m?.leads, g?.conversiones]) : null, sub: g ? 'Meta + conversiones de Google Ads' : 'Meta' },
      { t: 'Leads en el CRM', ico: 'base', v: e?.leads_ghl ?? null, sub: 'Contactos nuevos en GHL' },
      { t: 'Citas agendadas', ico: 'cal', v: e?.citas?.agendadas ?? null, sub: 'GHL' },
      { t: 'Citas asistidas', ico: 'ok', v: e?.citas?.celebradas ?? null, sub: e?.citas ? `${fNum(e.citas.sin_estado)} sin marcar` : 'GHL' },
      { t: 'Ventas', ico: 'crown', v: null, sub: 'El despacho aún no marca la venta en GHL' },
    ];
    const maxV = Math.max(...pasos.filter(p => !p.dinero).map(p => p.v || 0), 1);
    const esc = h('div', { style: PILA(3) }, pasos.map(p => h('div', { class: 'fila', style: { gap: 'var(--s-3)' } },
      h('span', { class: 'fila', style: { flex: '1 1 168px', flexWrap: 'nowrap', fontWeight: '600' } }, h('span', { class: 'ico-c s' }, icono(p.ico)), p.t),
      h('span', { style: { flex: '3 1 200px' } }, barraProgreso({ valor: p.dinero ? 1 : (p.v || 0), max: p.dinero ? 1 : maxV, estado: p.v === null || p.v === undefined ? null : null, etiqueta: `${p.t}: ${p.v ?? 'sin dato'}` })),
      h('span', { style: { flex: '0 0 128px', textAlign: 'right' } }, h('b', { style: { font: 'var(--t-h2)' } }, p.v === undefined ? candado('Sin permiso') : p.v === null ? 'sin dato' : (p.f || fNum)(p.v)), h('small', { class: 'sub', style: { display: 'block', font: 'var(--t-meta)' } }, p.sub)))));
    const citas = e?.citas?.agendadas; const asis = e?.citas?.celebradas;
    const costes = veInversion && inversion ? tiles([
      tile({ icono: 'euro', etiqueta: 'Coste por lead', valor: m?.leads ? fEur(inversion / sum([m?.leads, g?.conversiones]), 2) : null, estado: m?.leads ? colorCifra('coste_lead', inversion / sum([m?.leads, g?.conversiones])) : '', contexto: 'Inversión entre leads de publicidad' }),
      tile({ icono: 'cal', etiqueta: 'Coste por cita', valor: citas ? fEur(inversion / citas, 2) : null, contexto: citas ? 'Inversión entre citas agendadas' : 'Sin citas en el periodo', estado: citas ? '' : 'gris' }),
      tile({ icono: 'ok', etiqueta: 'Coste por cita asistida', valor: asis ? fEur(inversion / asis, 2) : null, contexto: 'Objetivo del día 0: pendiente de cargar' }),
    ]) : null;
    // dónde se rompe
    const tasas = [['de lead a cita', m?.leads, citas], ['de cita a asistida', citas, asis]].filter(([, a, b]) => a && b !== null && b !== undefined).map(([t, a, b]) => [t, b / a]);
    const peor = tasas.sort((a, b) => a[1] - b[1])[0];
    const frase = !e ? 'Sin CRM conectado: el embudo se queda en los leads de la publicidad.' : peor ? `Donde más se pierde: ${peor[0]} (${num4(100 * peor[1], 0)} %).` : (m?.leads && !citas ? `Con ${fNum(m.leads)} leads no hay ninguna cita en el CRM: o el despacho no agenda, o no lo registra.` : null);
    const sinMarcar = e?.citas?.con_fecha_en_ventana ? pct(e.citas.sin_estado, e.citas.con_fecha_en_ventana) : null;
    return bloque(S, 'embudo', 'Cuántos clientes trae la publicidad y a qué precio, hasta la cita en el CRM del despacho.', [
      P.id !== '2026-09' && (m || g) ? avisoParcial('Las citas del CRM salen solo del mes anterior (septiembre) por ahora: aquí se ve la parte de publicidad de este periodo.', { tipo: 'info' }) : null,
      esc,
      frase ? h('p', { style: { fontWeight: '600' } }, icono('flecha', { clase: 's' }), ' ', frase) : null,
      sinMarcar !== null ? h('p', { class: 'sub' }, `${num4(sinMarcar, 0)} % de las citas con fecha están sin marcar: la asistencia puede estar inflada o desinflada.`) : null,
      e?.funnel_90d ? h('div', {}, h('p', SUB, icono('base', { clase: 's' }), 'Oportunidades del CRM (últimos 90 días)'),
        barras(Object.entries(e.funnel_90d).map(([k, v]) => ({ t: k[0].toUpperCase() + k.slice(1), v })), { fuente: 'GoHighLevel' })) : null,
      e?.estancados_72h ? h('p', { class: 'sub' }, `Leads sin tocar más de 72 h: ${fNum(e.estancados_72h)} (${num4(e.pct_estancado, 0)} %). El que más lleva: ${num4(e.horas_max_parado / 24, 0)} días.`) : null,
      costes,
    ], { frescor: fresco(S.f.fuentes?.ghl, 'GHL'), acciones: h('span', { class: 'fila' }, atajo(URL.embudo(f), 'Abrir en GHL'), atajo(URL.meta(f), 'Abrir en Meta')) });
  },

  // ------------------------------------------------------------- 2 · GA4
  ga4(S) {
    const { f, txt } = S; const g = f.ga4; const fu = f.fuentes?.ga4;
    if (!g) return bloqueInterno(S, 'ga4', 'Visitas a la web y lo que hacen en ella (Google Analytics).', sinFuente(fu, 'Sin Analytics para este cliente', `${nm('agustina')} (emparejar la propiedad) · SEO`));
    const b = S.cmp === 'anio' ? g.anio_anterior : S.cmp === 'ant' ? g.anterior : null;
    const T = g.actual || {};
    const cards = tiles([
      tile({ icono: 'users', etiqueta: 'Usuarios activos', valor: fNum(T.usuarios), comparacion: cmpTile(T.usuarios, b?.usuarios, txt) }),
      tile({ icono: 'persona', etiqueta: 'Usuarios nuevos', valor: fNum(T.nuevos), comparacion: cmpTile(T.nuevos, b?.nuevos, txt) }),
      tile({ icono: 'mas', etiqueta: '% de usuarios nuevos', valor: fPct(T.pct_nuevos), comparacion: cmpTile(T.pct_nuevos, b?.pct_nuevos, txt) }),
      tile({ icono: 'zap', etiqueta: 'Tasa de interacción', valor: fPct(100 * T.interaccion), comparacion: cmpTile(T.interaccion, b?.interaccion, txt) }),
      tile({ icono: 'doc', etiqueta: 'Vistas por usuario', valor: fNum(T.vistas_usuario, 2), comparacion: cmpTile(T.vistas_usuario, b?.vistas_usuario, txt), contexto: 'Páginas vistas de media por cada usuario' }),
      tile({ icono: 'clock', etiqueta: 'Duración media', valor: fSeg(T.duracion), comparacion: cmpTile(T.duracion, b?.duracion, txt) }),
    ]);
    const serieB = S.cmp === 'anio' ? g.serie_anio : g.serie_ant;
    const graf = lineas({ x: g.dias, titulo: 'Usuarios por día', series: [{ nombre: 'Usuarios', y: (g.serie || []).map(r => r[1]) }, ...(S.cmp !== 'no' && serieB ? [{ nombre: S.cmp === 'anio' ? 'Año anterior' : 'Periodo anterior', y: serieB.map(r => r[1]), ant: true }] : [])] });
    const totS = sum(g.paginas.map(p => p.sesiones)) || 1; const maxS = Math.max(...g.paginas.map(p => p.sesiones), 1);
    const urls = tablaGrande({ titulo: 'páginas', fuente: 'Analytics', buscar: r => r.pagina, filas: g.paginas, columnas: [
      { titulo: 'Página de destino', principal: true, celda: r => r.pagina },
      { titulo: 'Sesiones', num: true, celda: r => barrita(r.sesiones, maxS) },
      { titulo: '% sesiones', num: true, celda: r => fPct(pct(r.sesiones, totS)) },
      { titulo: 'Eventos', num: true, celda: r => fNum(r.eventos) },
      { titulo: 'Rebote', num: true, celda: r => fPct(r.rebote != null ? 100 * r.rebote : null, 0) },
      { titulo: 'Conversiones', num: true, celda: r => fNum(r.conversiones) },
      { titulo: 'Cambio en sesiones', num: true, celda: r => delta(r.sesiones, r.sesiones_ant) }] });
    const CLAVE_EV = ['page_view', 'session_start', 'first_visit', 'user_engagement', 'scroll', 'click', 'form_start', 'submit_lead_form'];
    const evs = g.eventos.filter(e => CLAVE_EV.includes(e.evento) || /tel|mail|whats|lead|contact|form|llam/i.test(e.evento));
    const embudoEv = barras((evs.length ? evs : g.eventos.slice(0, 10)).map(e => ({ t: e.evento, v: e.n, extra: null })), { fuente: 'Analytics' });
    const evDia = lineas({ x: g.dias, series: Object.entries(g.eventos_dia || {}).slice(0, 6).map(([k, v]) => ({ nombre: k, y: v })), leyenda: true });
    const canDia = lineas({ x: g.dias, series: Object.entries(g.canales_dia || {}).sort((a, b) => sum(b[1]) - sum(a[1])).slice(0, 7).map(([k, v]) => ({ nombre: k, y: v })), leyenda: true });
    const canales = tablaGrande({ titulo: 'canales', fuente: 'Analytics', filas: g.canales, columnas: [
      { titulo: 'Canal', principal: true, celda: r => r.canal },
      { titulo: 'Sesiones', num: true, celda: r => fNum(r.sesiones) },
      { titulo: 'Eventos', num: true, celda: r => fNum(r.eventos) },
      { titulo: 'Eventos por sesión', num: true, celda: r => (r.sesiones ? fNum(r.eventos / r.sesiones, 1) : '—') },
      { titulo: 'Usuarios', num: true, celda: r => fNum(r.usuarios) },
      { titulo: 'Conversiones', num: true, celda: r => fNum(r.conversiones) },
      { titulo: 'Cambio en sesiones', num: true, celda: r => delta(r.sesiones, r.sesiones_ant) }] });
    const porCanal = {}; for (const [ca, , v] of g.canal_evento || []) porCanal[ca] = (porCanal[ca] || 0) + v;
    const detalle = h('details', { class: 'no-imprimir' }, h('summary', { class: 'sub', style: { cursor: 'pointer', minHeight: '32px' } }, 'Detalle canal × evento'),
      tablaGrande({ titulo: 'eventos por canal', fuente: 'Analytics', buscar: r => `${r[0]} ${r[1]}`, filas: g.canal_evento || [], columnas: [
        { titulo: 'Canal', principal: true, celda: r => r[0] }, { titulo: 'Evento', celda: r => r[1] }, { titulo: 'Eventos', num: true, celda: r => fNum(r[2]) }] }));
    return bloque(S, 'ga4', `Visitas a la web y lo que hacen en ella (Google Analytics${fu?.nombre ? `, propiedad «${fu.nombre}»` : ''}).`, [
      cards,
      h('div', {}, h('p', SUB, icono('grafico', { clase: 's' }), 'Usuarios por día'), graf),
      h('div', {}, h('p', SUB, icono('doc', { clase: 's' }), 'Principales URLs'), urls),
      h('div', { style: REJ(360) },
        h('div', {}, h('p', SUB, icono('filtro', { clase: 's' }), 'Embudo de eventos'), embudoEv),
        h('div', {}, h('p', SUB, icono('grafico', { clase: 's' }), 'Eventos en el tiempo'), evDia)),
      h('div', {}, h('p', SUB, icono('capas', { clase: 's' }), 'Conversión por grupo de canales'), canales),
      h('div', { style: REJ(360) },
        h('div', {}, h('p', SUB, icono('grafico', { clase: 's' }), 'Eventos por canal en el tiempo'), canDia),
        h('div', {}, h('p', SUB, icono('capas', { clase: 's' }), 'Eventos por canal'), barras(Object.entries(porCanal).sort((a, b) => b[1] - a[1]).map(([t, v]) => ({ t, v })), { fuente: 'Analytics' }), detalle)),
    ], { frescor: fresco(fu, 'Analytics'), acciones: fu?.propiedad ? h('a', { class: 'bt mini no-imprimir', href: `https://analytics.google.com/analytics/web/#/p${String(fu.propiedad).replace('properties/', '')}/reports/intelligenthome`, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en Analytics') : null });
  },

  // ------------------------------------------------------------- 3-4 · Search Console
  gsc(S) {
    const { f, txt, P } = S; const g = f.gsc; const fu = f.fuentes?.gsc;
    const extra = f.bit24_propiedades ? bit24(f.bit24_propiedades) : null;
    if (!g) return bloqueInterno(S, 'gsc', 'Cómo aparece la web en Google: clics, impresiones y posición (Search Console).', [sinFuente(fu, 'Sin Search Console para este cliente', `${nm('agustina')} (emparejar el sitio) · SEO`), extra]);
    const caja = h('div', {});
    const pintarModo = (modo, z) => {
      const tot = modo === 'web' ? g.web : g.url;
      const b = S.cmp === 'anio' ? tot.anio_anterior : S.cmp === 'ant' ? tot.anterior : null;
      const a = tot.actual || {};
      const serie = (modo === 'web' ? g.serie : g.serie_url) || [];
      const V = g.ventanas || { actual: [P.desde, P.hasta], anterior: P.anterior };
      const cur = serie.filter(r => r[0] >= V.actual[0] && r[0] <= V.actual[1]);
      const ant = S.cmp === 'anio' ? (g.serie_anio || []) : serie.filter(r => r[0] >= V.anterior[0] && r[0] <= V.anterior[1]);
      if (g.recortado) z.append(avisoParcial(`Datos hasta el ${fDia(g.hasta_dato)}: Google va 2-3 días por detrás. Para no comparar días vacíos con días llenos, el periodo anterior se corta a los mismos días (${fDia(V.anterior[0])} – ${fDia(V.anterior[1])}).`, { tipo: 'info' }));
      const x = cur.map(r => r[0]);
      z.append(tiles([
        tile({ icono: 'buscar', etiqueta: modo === 'web' ? 'Clics' : 'Clics de URL', valor: fNum(a.clics), comparacion: cmpTile(a.clics, b?.clics, txt) }),
        tile({ icono: 'ojo', etiqueta: 'Impresiones', valor: fNum(a.impresiones), comparacion: cmpTile(a.impresiones, b?.impresiones, txt) }),
        tile({ icono: 'zap', etiqueta: modo === 'web' ? 'CTR de la web' : 'CTR de URL', valor: fPct(100 * (a.ctr || 0), 2), comparacion: cmpTile(a.ctr, b?.ctr, txt) }),
        tile({ icono: 'sube', etiqueta: 'Posición media', valor: fNum(a.posicion, 1), comparacion: cmpTile(a.posicion, b?.posicion, txt, { puestos: true }), contexto: 'Más bajo es mejor' }),
      ]));
      z.append(h('div', { style: REJ(360) },
        h('div', {}, h('p', SUB, icono('grafico', { clase: 's' }), 'Clics por día'), lineas({ x, series: [{ nombre: 'Clics', y: cur.map(r => r[1]) }, ...(S.cmp !== 'no' ? [{ nombre: S.cmp === 'anio' ? 'Año anterior' : 'Periodo anterior', y: ant.map(r => r[1]), ant: true }] : [])] })),
        h('div', {}, h('p', SUB, icono('grafico', { clase: 's' }), 'CTR por día (%)'), lineas({ x, formato: v => num4(v, 1), series: [{ nombre: 'CTR', y: cur.map(r => 100 * r[3]), color: 'var(--good)' }, ...(S.cmp !== 'no' ? [{ nombre: S.cmp === 'anio' ? 'Año anterior' : 'Periodo anterior', y: ant.map(r => 100 * r[3]), ant: true }] : [])] }))));
      const disp = (g.dispositivos || []).map(d => ({ t: { DESKTOP: 'Ordenador', MOBILE: 'Móvil', TABLET: 'Tableta' }[d[0]] || d[0], c: d[1], i: d[2], ca: d[5] }));
      z.append(h('div', { style: REJ(360) },
        h('div', {}, h('p', SUB, icono('capas', { clase: 's' }), 'Clics por dispositivo'), barras(disp.map(d => ({ t: d.t, v: d.c, extra: null })), { fuente: 'Search Console' })),
        h('div', {}, h('p', SUB, icono('capas', { clase: 's' }), 'Impresiones por dispositivo'), barras(disp.map(d => ({ t: d.t, v: d.i })), { fuente: 'Search Console' }))));
      z.append(h('div', {}, h('p', SUB, icono('buscar', { clase: 's' }), 'Principales consultas'),
        tablaGrande({ titulo: 'consultas', fuente: 'Search Console', buscar: r => r[0], inicial: 15, filas: g.consultas || [], columnas: [
          { titulo: 'Consulta', principal: true, celda: r => r[0] }, { titulo: 'Clics', num: true, celda: r => fNum(r[1]) }, { titulo: 'Impresiones', num: true, celda: r => fNum(r[2]) },
          { titulo: 'CTR', num: true, celda: r => fPct(100 * r[3], 1) }, { titulo: 'Posición', num: true, celda: r => fNum(r[4], 1) }, { titulo: 'Cambio en clics', num: true, celda: r => delta(r[1], r[5]) }] })));
      if (modo === 'url') z.append(h('div', {}, h('p', SUB, icono('doc', { clase: 's' }), 'Principales URLs'),
        tablaGrande({ titulo: 'páginas', fuente: 'Search Console', buscar: r => r[0], inicial: 15, filas: g.paginas || [], columnas: [
          { titulo: 'Página', principal: true, celda: r => r[0].replace(/^https?:\/\/(www\.)?/, '') }, { titulo: 'Impresiones', num: true, celda: r => fNum(r[2]) }, { titulo: 'Clics', num: true, celda: r => fNum(r[1]) },
          { titulo: 'Posición', num: true, celda: r => fNum(r[4], 1) }, { titulo: 'Cambio en clics', num: true, celda: r => delta(r[1], r[5]) }] })));
    };
    const modoLooker = (S.f.looker && /gsc_url/.test(JSON.stringify(PARIDAD_BLOQUES[S.f.cliente_id] || ''))) ? 'url' : 'web';
    caja.append(pestanas({ etiqueta: 'Modo de Search Console', activa: modoLooker, clave: 'informe.gsc', pestanas: [{ id: 'web', texto: 'Por web', icono: 'globe' }, { id: 'url', texto: 'Por página', icono: 'doc' }], pintar: (id, z) => { z.style.display = 'grid'; z.style.gap = 'var(--s-4)'; pintarModo(id, z); } }));
    caja.querySelector('[role="tablist"]')?.classList.add('no-imprimir');
    return bloque(S, 'gsc', `Cómo aparece la web en Google: clics, impresiones y posición (Search Console${fu?.sitio ? `, ${String(fu.sitio).replace(/^sc-domain:|^https?:\/\/|\/$/g, '')}` : ''}).`, [caja, extra],
      { frescor: fresco(fu, 'Search Console'), acciones: fu?.sitio ? h('a', { class: 'bt mini no-imprimir', href: `https://search.google.com/search-console/performance/search-analytics?resource_id=${encodeURIComponent(fu.sitio)}`, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en Search Console') : null });
  },

  // ------------------------------------------------------------- 5 · SE Ranking
  seranking(S) {
    const { f } = S; const s = f.seranking; const fu = f.fuentes?.seranking;
    if (!s) {
      if (f.seranking_otro_periodo) return bloqueInterno(S, 'seranking', 'Posiciones de las palabras clave del proyecto.', vacioLinea([h('b', {}, 'SE Ranking, por ahora solo septiembre frente a agosto'), ' · Elige septiembre o los últimos 30 días; otros meses llegan cuando SE Ranking deje leer los proyectos.'], { icono: 'cal', quien: nm('agustina') }));
      return bloqueInterno(S, 'seranking', 'Posiciones de las palabras clave en Google (SE Ranking).', sinFuente(fu, 'Sin proyecto de SE Ranking leído', `${nm('agustina')} · SEO`));
    }
    const caja = h('div', { style: PILA(4) });
    const ops = [{ valor: '', texto: 'Todos los buscadores', icono: 'globe' }, ...(s.buscadores || []).map(b => ({ valor: String(b.id), texto: b.nombre, cuenta: s.palabras.filter(p => String(p[1]) === String(b.id)).length }))];
    const zona = h('div', { style: PILA(4) });
    const pintar = eng => {
      const pal = s.palabras.filter(p => !eng || String(p[1]) === eng);
      const r = resumenSR({ palabras: pal });
      const top15 = [...pal].sort((a, b) => (b[4] || 0) - (a[4] || 0)).slice(0, 15);
      const histK = eng && s.historia?.[eng] ? eng : (s.historia?.media ? 'media' : Object.keys(s.historia || {})[0]);
      const hist = s.historia?.[histK] || [];
      const caidas = r.dentroIni >= 8 && r.dentro < 0.5 * r.dentroIni;
      rc(zona, 
        caidas ? aviso({ color: 'ambar', tipo: 'caida', titulo: 'Caída a revisar antes de enseñarla.', texto: `De ${r.dentroIni} palabras dentro del top 100 el ${fDia(s.fecha_ini)} quedan ${r.dentro} el ${fDia(s.fecha_fin)}. Pasa a la vez en casi todos los proyectos desde el 25-26 de septiembre y sobre todo en Google escritorio (Bing y móvil aguantan): apunta a un cambio de Google o a un fallo de lectura de SE Ranking, no a que la web haya caído. La posición media sale de las pocas que quedan: léela junto al número de palabras dentro.`, quien: 'SEO del cliente · jefa de SEO' }) : null,
        tiles([
          tile({ icono: 'sube', etiqueta: 'Posición media', valor: fNum(r.media, 1), comparacion: r.mediaIni ? cmpTile(r.media, r.mediaIni, `frente al ${fDia(s.fecha_ini)}`, { puestos: true }) : undefined, contexto: 'Solo palabras dentro del top 100' }),
          tile({ icono: 'doc', etiqueta: 'Palabras en seguimiento', valor: fNum(r.total), contexto: `${fNum(r.dentro)} dentro del top 100 · ${fNum(r.fuera)} fuera` }),
          tile({ icono: 'star', etiqueta: 'En el top 10', valor: fNum(r.top10), comparacion: cmpTile(r.top10, r.top10Ini, `frente al ${fDia(s.fecha_ini)}`) }),
          tile({ icono: 'crown', etiqueta: 'Las 15 del informe en el top 5', valor: `${top15.filter(p => p[2] && p[2] <= 5).length} de ${top15.length}`, contexto: 'Propuesta: las 15 de más volumen, hasta que el account marque las suyas' }),
        ]),
        hist.length > 1 ? h('div', {}, h('p', SUB, icono('grafico', { clase: 's' }), 'Posición media en el tiempo (más bajo es mejor)'), lineas({ x: hist.map(p => p[0]), series: [{ nombre: 'Posición media', y: hist.map(p => p[1]) }], formato: v => num4(v, 0) })) : null,
        h('p', { class: 'sub' }, 'Cómo leer las flechas: ▲ verde = la palabra ha subido en Google (su número baja); ▼ rojo = ha bajado. «Fuera» = más allá del puesto 100.'),
        tablaGrande({ titulo: 'palabras', fuente: 'SE Ranking', buscar: p => p[0], inicial: 15, filas: [...pal].sort((a, b) => (a[2] || 999) - (b[2] || 999)), columnas: [
          { titulo: 'Palabra clave', principal: true, celda: p => p[0] },
          { titulo: 'Volumen', num: true, celda: p => fNum(p[4]) },
          { titulo: `Hoy (${fDia(s.fecha_fin)})`, num: true, celda: p => (p[2] ? fNum(p[2]) : 'fuera') },
          { titulo: `Hace un mes`, num: true, celda: p => (p[3] ? fNum(p[3]) : 'fuera') },
          { titulo: 'Variación mensual', num: true, celda: p => (p[2] && p[3] ? delta(p[2], p[3], { puestos: true }) : p[2] && !p[3] ? deltaEl('bien', 'entra') : !p[2] && p[3] ? deltaEl('mal', 'sale') : deltaEl('igual', '—')) },
        ] }));
    };
    caja.append(interno(chipsFiltro({ opciones: ops, etiqueta: 'Buscador', clave: `informe.sr.${f.cliente_id}`, alCambiar: v => pintar(v) })), zona);
    pintar(caja.firstChild.valor());
    return bloque(S, 'seranking', 'Posiciones de las palabras clave en Google y su cambio en el último mes (SE Ranking).', caja,
      { frescor: frescura({ fuente: 'SE Ranking', fecha: s.fecha_fin, estado: 'ok' }), acciones: h('a', { class: 'bt mini no-imprimir', href: `https://online.seranking.com/admin.site.rankings.site_id-${s.site_id}.html`, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en SE Ranking') });
  },

  // ------------------------------------------------------------- 6 · Google Ads
  google_ads(S) {
    const { f, veInversion } = S; const g = f.google_ads; const fu = f.fuentes?.google_ads;
    if (fu?.estado === 'no_aplica') return null;
    const otroCliente = (f.avisos || []).some(a => a.tipo === 'otro_cliente');
    if (!g) {
      return bloqueInterno(S, 'google_ads', 'Anuncios en Google.', vacioLinea([h('b', {}, otroCliente ? 'No se pinta: la cuenta de su Looker es de otro cliente' : 'Google Ads llega con su conexión'), ` · ${fu?.nota || 'Pendiente de conexión.'}`], { icono: otroCliente ? 'alert' : 'plug', quien: `${nm('tomas')} y ${nm('agustina')}` }));
    }
    const ctr = pct(g.clics, g.impresiones); const tconv = pct(g.conversiones, g.clics);
    return bloque(S, 'google_ads', `Último gasto: ${fDia(g.ultimo_gasto)}.`, [
      interno(avisoParcial('Muestra sellada de septiembre (Windsor, 2-oct): solo totales. Campañas, serie diaria, términos de búsqueda, dispositivo, edad, sexo, llamadas y formularios llegan con la clave de Windsor o la conexión directa de Google Ads. Solo vale con «Septiembre 2026».', { tipo: 'info', titulo: 'A medias.' })),
      soloPapel(h('p', { class: 'sub' }, 'Totales del mes; el detalle por campaña llega en próximos informes.')),
      tiles([
        tile({ icono: 'buscar', etiqueta: 'Clics', valor: fNum(g.clics), medible: 'medias' }),
        tile({ icono: 'ojo', etiqueta: 'Impresiones', valor: fNum(g.impresiones), medible: 'medias' }),
        tile({ icono: 'zap', etiqueta: 'CTR', valor: fPct(ctr, 2), medible: 'medias' }),
        tile({ icono: 'ok', etiqueta: 'Conversiones', valor: fNum(g.conversiones, 1), medible: 'medias' }),
        tile({ icono: 'flecha', etiqueta: 'Tasa de conversión', valor: fPct(tconv, 1), medible: 'medias' }),
        veInversion && g.coste !== undefined ? tile({ icono: 'euro', etiqueta: 'Coste', valor: fEur(g.coste, 2), medible: 'medias' }) : null,
        veInversion && g.coste !== undefined ? tile({ icono: 'euro', etiqueta: 'CPC medio', valor: g.clics ? fEur(g.coste / g.clics, 2) : null, medible: 'medias' }) : null,
        veInversion && g.coste !== undefined ? tile({ icono: 'euro', etiqueta: 'Coste por conversión', valor: g.conversiones ? fEur(g.coste / g.conversiones, 2) : null, medible: 'medias' }) : null,
      ].filter(Boolean)),
    ], { frescor: frescura({ fuente: 'Windsor', fecha: fu?.hora, estado: 'viejo' }) });
  },

  // ------------------------------------------------------------- 7 · Meta
  meta(S) {
    const { f, txt, veInversion } = S; const m = f.meta; const fu = f.fuentes?.meta;
    if (!m) return bloqueInterno(S, 'meta', 'Anuncios en Facebook e Instagram (Meta Ads).', sinFuente(fu, 'Sin cuenta de Meta para este cliente', `${nm('agustina')} (emparejar la cuenta publicitaria)`));
    const a = m.actual || {}; const b = S.cmp === 'ant' ? m.anterior : null; const t2 = S.cmp === 'ant' ? txt : null;
    // V2 (barrido v1): todo a cero → una línea llana, no seis tarjetas con «—»
    const todoCero = ['impresiones', 'alcance', 'leads', 'gasto'].every(k => !a[k]);
    const cards = todoCero ? vacioLinea(`Sin actividad en Meta en este periodo: 0 impresiones y 0 leads${veInversion ? ', 0 € gastados' : ''}.`, { icono: 'target' }) : tiles([
      veInversion && a.gasto !== undefined ? tile({ icono: 'euro', etiqueta: 'Importe gastado', valor: fEur(a.gasto, 2), comparacion: cmpTile(a.gasto, b?.gasto, t2) }) : null,
      tile({ icono: 'ojo', etiqueta: 'Impresiones', valor: fNum(a.impresiones), comparacion: cmpTile(a.impresiones, b?.impresiones, t2) }),
      tile({ icono: 'users', etiqueta: 'Alcance', valor: fNum(a.alcance), comparacion: cmpTile(a.alcance, b?.alcance, t2) }),
      tile({ icono: 'recargar', etiqueta: 'Frecuencia', valor: fNum(a.frecuencia, 2), comparacion: cmpTile(a.frecuencia, b?.frecuencia, t2, { mejorSi: 'bajo' }) }),
      tile({ icono: 'target', etiqueta: 'Leads', valor: fNum(a.leads), comparacion: cmpTile(a.leads, b?.leads, t2) }),
      veInversion && a.gasto !== undefined ? tile({ icono: 'euro', etiqueta: 'Coste por lead', valor: a.cpl != null ? fEur(a.cpl, 2) : null, estado: colorCifra('coste_lead', a.cpl), comparacion: cmpTile(a.cpl, b?.cpl, t2, { mejorSi: 'bajo' }), contexto: 'Objetivo del día 0: pendiente' }) : null,
    ].filter(Boolean));
    const ser = m.serie || [];
    const graf = lineas({ x: ser.map(r => r[0]), barras: { nombre: 'Leads por día (barras)', y: ser.map(r => r[2]) }, series: veInversion && ser.length && ser[0][1] !== undefined && ser.some(r => r[1] != null) ? [{ nombre: 'Gasto por día', y: ser.map(r => r[1]) }] : [], formato: v => fEur(v), leyenda: true });
    const filas = (m.conjuntos || []);
    const tabla = tablaGrande({ titulo: 'campañas', fuente: 'Meta', buscar: r => `${r.campana} ${r.conjunto}`, filas, vacio: { icono: 'target', titulo: 'Sin campañas con actividad en el periodo' }, columnas: [
      { titulo: 'Campaña', principal: true, celda: r => r.campana }, { titulo: 'Conjunto', celda: r => r.conjunto },
      ...(veInversion ? [{ titulo: 'Gasto', num: true, celda: r => (r.gasto !== undefined ? fEur(r.gasto, 2) : '—') }] : []),
      { titulo: 'Leads', num: true, celda: r => fNum(r.leads) },
      ...(veInversion ? [{ titulo: 'Coste por lead', num: true, celda: r => (r.leads && r.gasto !== undefined ? fEur(r.gasto / r.leads, 2) : '—') }] : []),
      { titulo: 'Frecuencia', num: true, celda: r => fNum(r.frecuencia, 2) }] });
    return bloque(S, 'meta', `Anuncios en Facebook e Instagram (Meta Ads)${fu?.cuenta?.nombre ? `, cuenta «${fu.cuenta.nombre}»` : ''}.`, [
      S.cmp === 'anio' ? avisoParcial('Meta solo trae la comparación con el periodo anterior.', { tipo: 'info' }) : null,
      !veInversion ? interno(avisoParcial('Tu puesto no ve la inversión: gasto y coste por lead quedan fuera (los quita el servidor).', { tipo: 'info' })) : null,
      cards, h('div', {}, h('p', SUB, icono('grafico', { clase: 's' }), 'Leads por día'), graf),
      h('div', {}, h('p', SUB, icono('capas', { clase: 's' }), 'Campañas y conjuntos'), tabla),
      interno(h('p', { class: 'sub' }, 'Calidad de los leads (válido, no contesta, no es cliente ideal…): sale de las etiquetas de GHL cuando la subcuenta esté emparejada.')),
    ], { frescor: fresco(fu, 'Meta'), acciones: fu?.cuenta?.id ? h('a', { class: 'bt mini no-imprimir', href: `https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${String(fu.cuenta.id).replace('act_', '')}`, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en Meta') : null });
  },

  // ------------------------------------------------------------- 8 · Correo en frío
  correo(S) {
    const { f, txt } = S; const s = f.snov; const fu = f.fuentes?.snov;
    const looker = PARIDAD_BLOQUES[f.cliente_id]?.includes('correo');
    if (!s) return bloqueInterno(S, 'correo', 'Campañas de correo en frío.',
      vacioLinea([h('b', {}, looker ? 'Su correo en frío no está en Snov.io' : 'Sin correo en frío para este cliente'), ` · ${looker ? 'Su Looker lee una hoja de Google: falta el enlace de esa hoja (el permiso ya está) o confirmar sus campañas en Snov.io.' : (fu?.nota || 'Sin campañas.')}`], { icono: 'mail', quien: `${nm('yessica')} y ${nm('bautista')}` }));
    const caja = h('div', { style: PILA(4) });
    const zona = h('div', { style: PILA(4) });
    const pintar = modo => {
      const a = modo === 'hist' ? s.historico : s.actual; const b = modo === 'hist' || S.cmp !== 'ant' ? null : s.anterior; const t2 = modo === 'hist' || S.cmp !== 'ant' ? null : txt;
      const env = a.emails_sent, ent = a.delivered;
      rc(zona, 
        tiles([
          tile({ icono: 'send', etiqueta: 'Correos enviados', valor: fNum(env), comparacion: cmpTile(env, b?.emails_sent, t2) }),
          tile({ icono: 'ok', etiqueta: 'Tasa de entrega', valor: fPct(pct(ent, env)) }),
          tile({ icono: 'ojo', etiqueta: 'Abiertos', valor: fNum(a.email_opens), contexto: `${fPct(pct(a.email_opens, ent))} de los entregados` }),
          tile({ icono: 'cerrar', etiqueta: 'Desuscritos', valor: fNum(a.unsubscribed), contexto: fPct(pct(a.unsubscribed, ent), 2) }),
          tile({ icono: 'alert', etiqueta: 'Rebotes', valor: fNum(a.bounced), contexto: fPct(pct(a.bounced, env), 1), estado: pct(a.bounced, env) > 5 ? 'ambar' : '' }),
          tile({ icono: 'mail', etiqueta: 'Respuestas', valor: fNum(a.email_replies), comparacion: cmpTile(a.email_replies, b?.email_replies, t2), contexto: `${fPct(pct(a.email_replies, ent), 1)} · bien desde el 5,5 %`, estado: ent ? (pct(a.email_replies, ent) >= 5.5 ? 'verde' : pct(a.email_replies, ent) >= 2 ? 'ambar' : 'rojo') : 'gris' }),
          tile({ icono: 'users', etiqueta: 'Contactos alcanzados', valor: fNum(a.total_contacted), contexto: 'Uso de la base de datos' }),
        ]),
        tablaGrande({ titulo: 'campañas', fuente: 'Snov.io', buscar: r => r.nombre, filas: s.campanas, columnas: [
          { titulo: 'Campaña', principal: true, celda: r => r.nombre }, { titulo: 'Estado', celda: r => chipEstado(r.estado === 'Active' ? 'verde' : 'gris', ESTADO_SNOV[r.estado] || r.estado || '—') },
          { titulo: 'Enviados', num: true, celda: r => fNum((modo === 'hist' ? r.historico : r.actual)?.emails_sent) },
          { titulo: 'Abiertos', num: true, celda: r => fNum((modo === 'hist' ? r.historico : r.actual)?.email_opens) },
          { titulo: 'Respuestas', num: true, celda: r => fNum((modo === 'hist' ? r.historico : r.actual)?.email_replies) },
          { titulo: 'Contactados', num: true, celda: r => fNum((modo === 'hist' ? r.historico : r.actual)?.total_contacted) }] }));
    };
    const seg = chipsFiltro({ opciones: [{ valor: 'periodo', texto: S.P.texto, icono: 'cal' }, { valor: 'hist', texto: 'Todo el histórico', icono: 'hist' }], etiqueta: 'Fechas', clave: 'informe.correo', alCambiar: pintar });
    caja.append(interno(seg), zona); pintar(seg.valor());
    return bloque(S, 'correo', 'Campañas de correo en frío, una a una (Snov.io).', caja, { frescor: fresco(fu, 'Snov.io') });
  },

  // ------------------------------------------------------------- 9 · LinkedIn
  linkedin(S) {
    const { f } = S;
    const looker = PARIDAD_BLOQUES[f.cliente_id]?.includes('linkedin');
    const viejo = { 'ayg-asesores': '30-mar', 'fitec-asesores': '21-may', 'centro-consulting': '19-may', oteca: '21-may', 'torrevieja-consult': '19-may', aselegal: '3-sep', octoedro: '2-sep' }[f.cliente_id];
    if (!looker && !viejo) return null;
    return bloqueInterno(S, 'linkedin', 'Prospección en LinkedIn.', [
      viejo ? aviso({ color: ['3-sep', '2-sep'].includes(viejo) ? 'ambar' : 'rojo', titulo: `Último dato en su Looker: ${viejo}.`, texto: 'Ámbar a los 14 días sin datos y rojo a los 30. Confirmar si el servicio sigue.' }) : null,
      vacioLinea([h('b', {}, 'LinkedIn se conecta con la hoja de cada cliente'), ' · Falta el enlace de la hoja de Linked Helper de este cliente (el permiso ya está) o subir un CSV.'], { icono: 'users', quien: `${nm('yessica')} y ${nm('bautista')}` }),
    ]);
  },

  // ------------------------------------------------------------- 10 · Ficha de Google
  ficha_google(S) {
    return bloqueInterno(S, 'ficha_google', 'Llamadas, rutas, clics a la web, vistas y reseñas de la ficha de Google.',
      vacioLinea([h('b', {}, 'Se conecta más adelante'), ' · Hace falta el permiso de Google Business Profile con RO como gestor de cada ficha, o leerlo de SE Ranking Local.'], { icono: 'pin', quien: nm('agustina') }));
  },

  // ------------------------------------------------------------- 11 · Análisis del mes
  analisis(S) {
    const { f, P, ctx, c, ana } = S;
    const puede = puedeEscribir(ctx, c.id);
    const caja = h('div', { style: PILA(3) });
    const leido = h('div', { style: PILA(3) });
    if (ana.actual) {
      leido.append(h('div', { class: 'fila sub' }, h('span', { class: 'av s' }, iniciales(alias(ctx, ana.actual.quien))), `Escrito por ${alias(ctx, ana.actual.quien)} el ${fHora(ana.actual.creada)} · ${P.texto}`, interno(chipEstado('azul', 'simulado: queda en la base local'))));
      for (const [k, t] of APARTADOS.concat(ana.actual.apartados?.secuencia ? [['secuencia', 'Secuencia en curso']] : [])) if (ana.actual.apartados?.[k]) leido.append(h('div', { style: { ...PILA(1), ...SIN_CORTE } }, h('h4', { class: 'titulo-seccion' }, t), h('p', { style: { whiteSpace: 'pre-wrap', maxWidth: '72ch' } }, ana.actual.apartados[k])));
    } else {
      leido.append(soloPapel(h('p', {}, h('b', {}, 'Análisis del mes: '), 'pendiente.')));
      leido.append(interno(vacioLinea([h('b', {}, `Sin análisis ${deP(P)}`), ` · ${ana.otro ? `El último escrito es de ${ana.otro}: no se copia, se escribe el de este periodo.` : 'Lo escribe el account y el SEO añade su párrafo. La app propone un borrador con las cifras.'}`], { icono: 'editar', quien: 'el account' })));
    }
    caja.append(leido);
    if (puede) {
      const campos = {};
      const form = h('div', { style: PILA(3) });
      const aps = APARTADOS.concat(f.snov ? [['secuencia', 'Secuencia en curso (correo en frío)']] : []);
      for (const [k, t] of aps) { campos[k] = h('textarea', { rows: 3, 'aria-label': t }); campos[k].value = ana.actual?.apartados?.[k] || ''; form.append(h('label', { class: 'campo' }, h('span', { class: 'campo-et' }, t), campos[k])); }
      const err = h('p', { class: 'sub', role: 'alert' });
      form.append(err, h('div', { class: 'fila' },
        h('button', { type: 'button', class: 'bt', on: { click: () => { const b = borrador(S); for (const k of Object.keys(b)) if (campos[k] && !campos[k].value.trim()) campos[k].value = b[k]; avisoFlotante('Borrador con las cifras puesto en los huecos vacíos'); } } }, icono('spark'), 'Proponer borrador con las cifras'),
        botonConfirmar({ texto: 'Guardar y firmar', pregunta: `¿Guardar el análisis ${deP(P)} con tu firma?`, confirmar: 'Sí, guardar', soloLectura: ctx.soloLectura,
          alConfirmar: async () => {
            const apartados = Object.fromEntries(Object.entries(campos).map(([k, el]) => [k, el.value.trim()]).filter(([, v]) => v));
            const todo = Object.values(apartados).join(' ');
            if (!todo) throw new Error('Está vacío.');
            if (RE_LEAD.test(todo)) { err.textContent = 'Lleva un correo o un teléfono. Los datos de leads no van en el informe: quítalos.'; throw new Error('datos de leads en el texto'); }
            await ctx.accion({ herramienta: 'app', tipo: 'analisis_mes', objeto: `informe/${c.id}/${P.id}`, cliente_id: c.id, texto: todo.slice(0, 2000),
              vista_previa: { periodo: P.id, periodo_texto: P.texto, apartados, que_hace: 'Guarda el análisis del mes en la base local con autor y fecha. No se envía a nadie.' } });
            CACHE.acciones = null;
            setTimeout(() => window.dispatchEvent(new HashChangeEvent('hashchange')), 700);
            return 'Guardado con tu firma (simulado en la base local)';
          } })));
      caja.append(h('details', { class: 'no-imprimir', open: !ana.actual || null }, h('summary', { class: 'bt', style: { width: 'fit-content', listStyle: 'none', cursor: 'pointer', marginBottom: 'var(--s-3)' } }, icono('editar'), ana.actual ? 'Escribir una versión nueva' : 'Escribir el análisis'), form));
    } else {
      caja.append(h('p', { class: 'sub no-imprimir' }, ctx.soloLectura ? 'Estás en «ver como»: solo lectura.' : 'Lo escribe quien lleva el cliente.'));
    }
    if (ana.historial.length > 1) caja.append(h('details', { class: 'no-imprimir' }, h('summary', { class: 'sub', style: { cursor: 'pointer', minHeight: '32px' } }, `Versiones anteriores (${ana.historial.length - 1})`),
      h('ul', { class: 'sub' }, ana.historial.slice(1).map(a => h('li', {}, `${a.vp.periodo_texto || a.vp.periodo} · ${alias(ctx, a.quien)} · ${fHora(a.creada)}`)))));
    return bloque(S, 'analisis', 'Cómo ha ido el periodo y los próximos pasos, escrito por tu equipo de RO.', caja);
  },

  // ------------------------------------------------------------- 12 · Glosario
  glosario(S) {
    return bloque(S, 'glosario', 'Cada término en una línea, en lenguaje llano.', h('dl', { style: { ...REJ(300), margin: '0' } }, GLOSARIO.map(([t, d]) => h('div', { style: { ...PILA(1), ...SIN_CORTE } }, h('dt', { style: { font: 'var(--t-h3)' } }, t), h('dd', { class: 'sub', style: { margin: '0' } }, d)))));
  },
};

function resumenSR(s) {
  if (!s?.palabras?.length) return null;
  const pal = s.palabras;
  const dentro = pal.filter(p => p[2]); const dentroIni = pal.filter(p => p[3]);
  const media = dentro.length ? sum(dentro.map(p => p[2])) / dentro.length : null;
  const mediaIni = dentroIni.length ? sum(dentroIni.map(p => p[3])) / dentroIni.length : null;
  return { total: pal.length, dentro: dentro.length, dentroIni: dentroIni.length, fuera: pal.length - dentro.length, media, mediaIni, top10: dentro.filter(p => p[2] <= 10).length, top10Ini: dentroIni.filter(p => p[3] <= 10).length };
}

function bit24(props) {
  return h('div', {}, h('p', SUB, icono('alert', { clase: 's' }), 'Arreglo de Bit24: ¿qué propiedad de Search Console es la buena?'),
    tablaApilable({ columnas: [
      { titulo: 'Propiedad', principal: true, celda: r => r.sitio },
      { titulo: 'Clics sep (web)', num: true, celda: r => fNum(r.sep?.clics) },
      { titulo: 'Impresiones sep (web)', num: true, celda: r => fNum(r.sep?.impresiones) },
      { titulo: 'Impresiones sep (por página)', num: true, celda: r => fNum(r.sep_url?.impresiones) },
      { titulo: 'Clics agosto', num: true, celda: r => fNum(r.ago?.clics) }], filas: props }),
    h('p', { class: 'sub' }, 'Su Looker enseña 1 clic y 43 impresiones en septiembre. La propiedad con más datos es casi seguro la buena: el SEO lo confirma y se cambia el emparejamiento.'));
}

function borrador(S) {
  const { f, P } = S;
  const g = f.ga4?.actual, ga = f.ga4?.anterior, s = f.gsc?.web?.actual, sa = f.gsc?.web?.anterior, m = f.meta?.actual, ma = f.meta?.anterior;
  const v = (a, b) => (a != null && b ? `${variacion(a, b) > 0 ? '+' : ''}${num4(variacion(a, b), 0)} %` : 'sin comparación');
  const mes = [];
  if (g) mes.push(`La web tuvo ${fNum(g.usuarios)} usuarios (${v(g.usuarios, ga?.usuarios)} frente al periodo anterior) y ${fNum(g.conversiones)} conversiones.`);
  if (s) mes.push(`Desde Google llegaron ${fNum(s.clics)} clics con ${fNum(s.impresiones)} impresiones (${v(s.clics, sa?.clics)}); posición media ${fNum(s.posicion, 1)}.`);
  if (m) mes.push(`En Meta, ${fNum(m.leads)} leads${m.cpl != null ? ` a ${fEur(m.cpl, 2)} cada uno` : ''} (${v(m.leads, ma?.leads)}).`);
  if (f.embudo?.citas) mes.push(`En el CRM, ${fNum(f.embudo.citas.agendadas)} citas agendadas y ${fNum(f.embudo.citas.celebradas)} celebradas.`);
  const top = (f.gsc?.consultas || []).slice(0, 3).map(q => `«${q[0]}»`).join(', ');
  return {
    mes: `${P.texto}: ${mes.join(' ')}`.trim(),
    funciona: top ? `Las búsquedas que más traen: ${top}.` : '',
    no_funciona: '',
    perdidas: f.embudo?.estancados_72h ? `${fNum(f.embudo.estancados_72h)} leads llevan más de 72 h sin tocar en el CRM.` : '',
    pasos: '',
  };
}

// =================================================================== paridad
let PARIDAD_BLOQUES = {};
const NOMBRE_BLOQUE = { ga4: 'Analytics', gsc_web: 'Search Console por web', gsc_url: 'Search Console por página', seranking: 'SE Ranking', google_ads: 'Google Ads', meta: 'Meta', correo: 'Correo en frío', linkedin: 'LinkedIn', analisis: 'Análisis', glosario: 'Glosario' };
const TOL = { ga4: 2, gsc_web: 2, gsc_url: 2, seranking: 0, google_ads: 1, meta: 1 };

function estadoBloque(k, f, el, anaSep) {
  const roto = el[k];
  const conDato = {
    ga4: !!f?.ga4?.actual?.usuarios, gsc_web: !!f?.gsc?.web?.actual?.impresiones, gsc_url: !!f?.gsc?.url?.actual?.impresiones,
    seranking: !!f?.seranking, google_ads: !!f?.google_ads, meta: !!f?.meta?.actual, correo: !!f?.snov, linkedin: false, analisis: !!anaSep, glosario: true,
  }[k];
  if (k === 'google_ads' && roto === 'otro_cliente') return { e: 'falta', t: 'cuenta de otro cliente: decidir antes' };
  if (k === 'google_ads' && !conDato && GADS_PARADA[f?.cliente_id]) return { e: 'medias', t: `campañas paradas desde el ${GADS_PARADA[f.cliente_id]}: a cero en Looker y en la app; el trafficker confirma si es a propósito` };
  if (k === 'google_ads' && conDato) return { e: 'medias', t: 'solo totales (muestra de Windsor); el resto llega con la conexión de Google Ads' };
  if (k === 'analisis') return anaSep ? { e: 'igual', t: 'escrito en la app' } : { e: 'medias', t: 'el campo está; falta escribir septiembre' };
  const sinAcceso = (f?.avisos || []).find(a => a.tipo === 'sin_acceso_google' && ((k === 'ga4' && /Analytics/.test(a.texto)) || (k.startsWith('gsc') && /Search Console/.test(a.texto))));
  if (!conDato && sinAcceso) return { e: 'falta', t: 'la cuenta de Google de la app no ve su propiedad: darle acceso de lector' };
  if (!conDato) return { e: 'falta', t: { google_ads: 'llega con la conexión de Google Ads', linkedin: 'falta el enlace de la hoja', correo: 'falta la hoja o Snov.io', meta: 'sin cuenta emparejada' }[k] || 'sin dato en la app' };
  if (roto) return { e: 'mejor', t: `en Looker: ${{ roto: 'roto', a_cero: 'a cero', viejo: 'parado', imagenes: 'imágenes pegadas', raro: 'cifra rara', tarjetas: 'tarjetas sin pintar', datos_leads: 'con datos de leads', no_cuadra: 'no cuadra' }[roto] || roto}; en la app sale bien` };
  return { e: 'igual', t: 'sale en la app' };
}
const GADS_PARADA = { aselegal: '30-jul', 'fitec-asesores': '3-jun', greconsult: '25-may', 'centro-consulting': '18-may', 'bit-24': '19-mar' };
const CHIP_E = { igual: ['verde', 'igual'], mejor: ['azul', 'mejor'], medias: ['ambar', 'a medias'], falta: ['rojo', 'falta'] };

function cifraApp(k, f) {
  const [b, m] = k.split('.');
  if (b === 'ga4') return f?.ga4?.actual?.[m];
  if (b === 'gsc_web') return f?.gsc?.web?.actual?.[m];
  if (b === 'gsc_url') return f?.gsc?.url?.actual?.[m];
  if (b === 'seranking' && m === 'palabras') return f?.seranking?.palabras?.length ? new Set(f.seranking.palabras.map(p => p[0])).size : null;
  if (b === 'google_ads') return f?.google_ads?.[m];
  return null;
}

async function pintarParidad(raiz, ctx, comun) {
  ctx.titulo('Comparación con Looker', 'Cliente a cliente: cada gráfico de su Looker, su equivalente en la app y si ya se puede archivar');
  const [par, sep, acc] = await Promise.all([CACHE.paridad ??= ctx.datosModulo('informe/paridad'), periodo(ctx, '2026-09'), acciones(ctx)]);
  const porId = Object.fromEntries((sep.filas || []).map(f => [f.cliente_id, f]));
  const filas = (par.filas || []).map(p => {
    const f = porId[p.cliente_id];
    const anaSep = analisisDe(acc, p.cliente_id, '2026-09').actual;
    const bl = p.bloques.map(k => ({ k, ...estadoBloque(k, f, p.estado_looker || {}, anaSep) }));
    const cifras = Object.entries(p.cifras_looker || {}).map(([k, vl]) => {
      const va = cifraApp(k, f); const tol = TOL[k.split('.')[0]] ?? 2;
      const dif = va == null ? null : vl ? (100 * (va - vl)) / vl : null;
      const redondeo = vl >= 1000 && vl % 100 === 0; // «2,1 mil» en Looker: tolerancia del redondeo
      const ok = dif === null ? null : Math.abs(dif) <= Math.max(tol, redondeo ? (100 * 50) / vl + 0.01 : 0) || (k.startsWith('seranking') && va === vl);
      return { k, vl, va, dif, ok, redondeo };
    });
    const avisoRojo = (f?.avisos || []).some(a => a.color === 'rojo');
    const marcas = acc.filter(a => a.cliente_id === p.cliente_id && a.tipo === 'paridad_comprobada');
    const crit = [
      { t: 'Mismos gráficos', ok: !bl.some(b => b.e === 'falta'), d: bl.filter(b => b.e === 'falta').map(b => NOMBRE_BLOQUE[b.k]).join(', ') || 'todos tienen bloque' },
      { t: 'Mismas cifras de septiembre', ok: cifras.length ? cifras.every(x => x.ok) : null, d: cifras.length ? `${cifras.filter(x => x.ok).length} de ${cifras.length} dentro de tolerancia` : 'el account apunta las cifras de su Looker' },
      { t: 'Fuentes suyas', ok: !(f?.avisos || []).some(a => a.tipo === 'otro_cliente'), d: 'cada cuenta por su identificador' },
      { t: 'Ningún aviso rojo abierto', ok: !avisoRojo, d: avisoRojo ? (f.avisos.find(a => a.color === 'rojo')?.tipo || '').replace('_', ' ') : 'sin rojos' },
      { t: 'Análisis de septiembre escrito', ok: !!anaSep, d: anaSep ? `por ${alias(ctx, anaSep.quien)}` : 'falta' },
      { t: 'Un mes en paralelo firmado', ok: marcas.length ? true : false, d: marcas.length ? `marcado por ${alias(ctx, marcas[0].quien)} el ${fHora(marcas[0].creada)}` : 'lo firma el account' },
    ];
    const listos5 = crit.slice(0, 5).every(x => x.ok);
    return { ...p, f, bl, cifras, crit, listos5, archivar: crit.every(x => x.ok), marcas };
  });
  PARIDAD_BLOQUES = Object.fromEntries((par.filas || []).map(p => [p.cliente_id, p.bloques]));
  if (!filas.length) {
    raiz.append(vacio({ icono: 'capas', titulo: 'Ninguno de tus clientes tiene Looker', texto: 'Los 22 informes de Looker son de clientes que no llevas.', tono: 'celebrar' }));
    return;
  }
  const cuenta = e => filas.reduce((a, r) => a + r.bl.filter(b => b.e === e).length, 0);
  raiz.append(tiles([
    tile({ icono: 'res', etiqueta: 'Informes de Looker', valor: fNum(filas.length), contexto: `De los 22 del inventario (2-oct)` }),
    tile({ icono: 'ok', etiqueta: 'Bloques iguales o mejores', valor: fNum(cuenta('igual') + cuenta('mejor')), estado: cuenta('igual') + cuenta('mejor') ? 'verde' : 'gris', contexto: `${fNum(cuenta('mejor'))} mejoran a Looker` }),
    tile({ icono: 'clock', etiqueta: 'Bloques a medias', valor: fNum(cuenta('medias')), estado: cuenta('medias') ? 'ambar' : '', contexto: 'Google Ads con muestra · análisis sin escribir' }),
    tile({ icono: 'alert', etiqueta: 'Bloques que faltan', valor: fNum(cuenta('falta')), estado: cuenta('falta') ? 'rojo' : '', contexto: 'Google Ads, LinkedIn, correo en hoja y propiedades sin acceso' }),
    tile({ icono: 'flag', etiqueta: 'Listos para el mes en paralelo', valor: fNum(filas.filter(r => r.listos5).length), contexto: 'Cumplen los criterios 1 a 5' }),
    tile({ icono: 'crown', etiqueta: 'Listos para archivar su Looker', valor: fNum(filas.filter(r => r.archivar).length), estado: filas.some(r => r.archivar) ? 'verde' : '', contexto: 'Los 6 criterios. Archivar lo decide ' + nm('tomas') }),
  ]));
  raiz.append(avisoParcial('Un cliente deja Looker solo con las seis: mismos gráficos · mismas cifras de un mes cerrado (Analytics y Search Console ±2 %, SE Ranking misma posición, Google Ads y Meta ±1 % en coste) · fuentes suyas · ningún aviso rojo · análisis escrito · un mes en paralelo firmado por el account. Su Looker se archiva sin borrar durante 3 meses.', { tipo: 'info', titulo: 'Cuándo se deja su Looker.' }));
  const lista = h('div', { style: PILA(3) });
  const TANDAS = { 1: 'Tanda 1 · ya (Google sin Ads)', 2: 'Tanda 2 · con Google Ads', 3: 'Tanda 3 · con outreach', 4: 'Tanda 4 · Google Ads y outreach', 5: 'Tanda 5 · casos aparte' };
  const chips = chipsFiltro({ etiqueta: 'Tanda', clave: 'informe.paridad.tanda', opciones: [{ valor: '', texto: 'Todas', cuenta: filas.length }, ...[1, 2, 3, 4, 5].map(t => ({ valor: String(t), texto: TANDAS[t], cuenta: filas.filter(r => r.tanda === t).length })).filter(o => o.cuenta)], alCambiar: v => pintar(v) });
  const pintar = t => {
    rc(lista, ...filas.filter(r => !t || String(r.tanda) === t).sort((a, b) => a.tanda - b.tanda || a.nombre.localeCompare(b.nombre)).map(r => tarjetaParidad(r, ctx)));
  };
  raiz.append(chips, lista); pintar(chips.valor());
}

function tarjetaParidad(r, ctx) {
  const cli = ctx.clientesVisibles.find(c => c.id === r.cliente_id) || { nombre: r.nombre };
  const okN = r.crit.filter(x => x.ok).length;
  return h('article', { class: 'panel', 'aria-label': `Comparación con Looker de ${r.nombre}`, style: { ...PILA(3), padding: 'var(--relleno)' } },
    h('div', { class: 'fila', style: { justifyContent: 'space-between' } },
      h('div', { class: 'fila', style: { flexWrap: 'nowrap' } }, logoCliente(cli), h('div', {}, h('b', { style: { font: 'var(--t-h2)' } }, r.nombre), h('div', { class: 'sub' }, `${r.bl.length} páginas en su Looker`))),
      h('div', { class: 'fila' },
        chipEstado('azul', `Tanda ${r.tanda}`, { punto: false }),
        chipEstado(r.archivar ? 'verde' : r.listos5 ? 'azul' : okN >= 4 ? 'ambar' : 'rojo', r.archivar ? 'Listo para archivar' : `${okN} de 6 criterios`),
        h('a', { class: 'bt mini', href: r.looker, target: '_blank', rel: 'noopener' }, icono('ext'), 'Su Looker'),
        h('a', { class: 'bt mini pri', href: `#/${MOD}/${r.cliente_id}/2026-09/ant` }, icono('grafico'), 'Ver en la app'))),
    r.bl.length ? h('div', {}, h('p', SUB, icono('capas', { clase: 's' }), 'Cada página de su Looker → en la app'),
      tablaApilable({ columnas: [
        { titulo: 'Bloque de Looker', principal: true, celda: b => h('span', {}, NOMBRE_BLOQUE[b.k] || b.k) },
        { titulo: 'Estado', celda: b => chipEstado(...CHIP_E[b.e]) },
        { titulo: 'Por qué', celda: b => h('span', { class: 'sub' }, b.t) }], filas: r.bl })) :
      vacioLinea([h('b', {}, 'No se sabe qué enseñaba'), ' · Su Looker no abre con las cuentas de RO. Hasta que lo compartan no se puede comparar.'], { icono: 'candado', quien: nm('agustina') }),
    r.cifras.length ? h('div', {}, h('p', SUB, icono('medidor', { clase: 's' }), 'Septiembre: cifra de Looker frente a la de la app'),
      tablaApilable({ columnas: [
        { titulo: 'Cifra', principal: true, celda: x => `${NOMBRE_BLOQUE[x.k.split('.')[0]]} · ${x.k.split('.')[1]}` },
        { titulo: 'Looker (2-oct)', num: true, celda: x => `${x.redondeo ? '≈ ' : ''}${fNum(x.vl, x.vl % 1 ? 2 : 0)}` },
        { titulo: 'App', num: true, celda: x => (x.va == null ? '—' : fNum(x.va, x.va % 1 ? 2 : 0)) },
        { titulo: 'Diferencia', num: true, celda: x => (x.dif == null ? '—' : `${x.dif > 0 ? '+' : ''}${num4(x.dif, 1)} %`) },
        { titulo: 'Tolerancia', celda: x => (x.ok === null ? chipEstado('gris', 'sin dato') : chipEstado(x.ok ? 'verde' : 'rojo', x.ok ? 'dentro' : 'fuera')) }], filas: r.cifras }),
      r.cifras.some(x => x.redondeo) ? h('p', { class: 'sub', style: { marginTop: 'var(--s-2)' } }, '≈ Looker enseña la cifra redondeada («2,1 mil»): se acepta la diferencia del redondeo.') : null) : null,
    h('ul', { style: { ...REJ(240), gap: 'var(--s-2)', margin: '0', padding: '0', listStyle: 'none' } }, r.crit.map((x, i) => h('li', { class: 'fila', style: { flexWrap: 'nowrap', alignItems: 'flex-start' } }, h('span', { class: `ico-c s ${x.ok ? 'verde' : x.ok === null ? 'gris' : 'rojo'}` }, icono(x.ok ? 'ok' : x.ok === null ? 'info' : 'cerrar')), h('span', {}, h('b', {}, `${i + 1}. ${x.t}`), h('br'), h('span', { class: 'sub' }, x.d))))),
    puedeParidad(ctx, r.cliente_id) ? h('div', {}, botonConfirmar({
      texto: r.marcas.length ? 'Volver a firmar el mes en paralelo' : 'Firmar «un mes en paralelo» (criterio 6)', mini: true,
      pregunta: r.listos5 ? `¿Firmas que el informe de septiembre de ${r.nombre} se ha hecho desde la app y es bueno?` : `Aún faltan criterios (${5 - r.crit.slice(0, 5).filter(x => x.ok).length}). ¿Firmar igualmente?`,
      confirmar: 'Sí, firmar', soloLectura: ctx.soloLectura,
      alConfirmar: async () => {
        await ctx.accion({ herramienta: 'app', tipo: 'paridad_comprobada', objeto: `paridad/${r.cliente_id}`, cliente_id: r.cliente_id, texto: `Mes en paralelo firmado: ${r.nombre}`,
          vista_previa: { criterios: r.crit.map(x => [x.t, x.ok]), looker: r.looker, que_hace: `Apunta la firma en la base local. Archivar su Looker lo decide ${nm('tomas')}; no se toca Looker.` } });
        CACHE.acciones = null;
        setTimeout(() => window.dispatchEvent(new HashChangeEvent('hashchange')), 900);
        return `Firmado (simulado en la base local). Archivar el Looker lo decide ${nm('tomas')}.`;
      } })) : null);
}
