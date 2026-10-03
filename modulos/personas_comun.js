// modulos/personas_comun.js · piezas locales de M20 Personas, M21 Decisiones y M22 Conexiones (mismo agente).
// Solo tokens de estilos.css. Si alguna sirve a más módulos, pasa a componentes.js (ver dudas_pintura.md · D-P-PER1).

import { h as hBase, icono, iniciales, chipEstado, chipsFiltro, fmt, hoyMadrid } from '../componentes.js';

// Ronda N6 (auditoría 30): sin hoja propia. Las piezas «pm-*» se pintan con atributos de estilo que usan SOLO tokens
// de estilos.css (letra --t-*, espacios --s-*, radios --r-*, sombras --sombra-*, colores de :root). Se aplican al crear
// el elemento con h() de este fichero (mismo contrato que el h() común: lo reexportan Personas, Decisiones y Ajustes).
const TARJETAS = { display: 'grid', gap: 'var(--s-4)', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))' };
const DENTRO_DE_PANEL = { margin: 'var(--s-3) var(--relleno) var(--relleno)' };
const ESTADO_BORDE = { rojo: 'var(--bad)', ambar: 'var(--warn)', verde: 'var(--good)', gris: 'var(--off)' };
const todos = (el, sel, est) => el.querySelectorAll(sel).forEach(x => Object.assign(x.style, est));
const PIEZAS = {
  'pm-form': el => {
    Object.assign(el.style, { display: 'grid', gap: 'var(--s-3)', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 200px), 1fr))', alignItems: 'end' });
    todos(el, ':scope > .ancho', { gridColumn: '1 / -1' });
  },
  'pm-tarjetas': el => Object.assign(el.style, TARJETAS),
  'pm-conex': el => Object.assign(el.style, { ...TARJETAS, gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))' }),
  'pm-tarjeta': el => {
    Object.assign(el.style, { border: 'var(--borde)', borderRadius: 'var(--r-l)', background: 'var(--card)', padding: 'var(--s-4) var(--relleno)',
      display: 'grid', gap: 'var(--s-3)', boxShadow: 'var(--sombra-1)', minWidth: '0', alignContent: 'start' });
    const est = Object.keys(ESTADO_BORDE).find(k => el.classList.contains(k));
    if (est) el.style.borderLeft = `var(--s-1) solid ${ESTADO_BORDE[est]}`;
  },
  'pm-cab': el => {
    Object.assign(el.style, { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2) var(--s-3)', alignItems: 'center', minWidth: '0' });
    todos(el, ':scope > .t', { display: 'grid', minWidth: '0', flex: '1 1 160px' });
    todos(el, ':scope > .t > b', { font: 'var(--t-h3)', fontWeight: '700', color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' });
    todos(el, ':scope > .t > span', { font: 'var(--t-meta)', color: 'var(--mid)' });
    todos(el, ':scope > .der', { marginLeft: 'auto', flex: 'none' });
  },
  'pm-motivos': el => {
    Object.assign(el.style, { display: 'grid', gap: 'var(--s-1)', margin: '0', padding: '0', listStyle: 'none', font: 'var(--t-cuerpo)', color: 'var(--ink)' });
    todos(el, ':scope > li', { display: 'flex', gap: 'var(--s-2)', alignItems: 'flex-start' });
    el.querySelectorAll(':scope > li > svg.i').forEach(s => { s.classList.add('s'); Object.assign(s.style, { color: 'var(--bad)', marginTop: 'var(--s-1)' }); });
  },
  'pm-reloj': el => Object.assign(el.style, { fontVariantNumeric: 'tabular-nums', fontWeight: '700' }),
  'pm-texto': el => Object.assign(el.style, { whiteSpace: 'pre-wrap', font: 'var(--t-cuerpo)', background: 'var(--card-2)', border: 'var(--borde-suave)',
    borderRadius: 'var(--r-m)', padding: 'var(--s-3) var(--s-4)', maxHeight: '60vh', overflow: 'auto', color: 'var(--ink)', maxWidth: '100%' }),
  'pm-barra': el => Object.assign(el.style, { display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 'var(--s-2)', alignItems: 'center',
    fontVariantNumeric: 'tabular-nums', font: 'var(--t-meta)', minWidth: '120px' }),
  'pm-kv': el => {
    Object.assign(el.style, { display: 'grid', gridTemplateColumns: 'fit-content(40%) minmax(0, 1fr)', gap: 'var(--s-1) var(--s-3)', font: 'var(--t-cuerpo)', margin: '0' });
    todos(el, ':scope > dt', { color: 'var(--mid)' });
    todos(el, ':scope > dd', { margin: '0', color: 'var(--ink)', overflowWrap: 'anywhere' });
  },
  'pm-dec': el => {
    Object.assign(el.style, { display: 'grid', gap: 'var(--s-2)' });
    todos(el, 'h3', { margin: '0', font: 'var(--t-h2)', color: 'var(--ink)' });
    todos(el, 'p', { margin: '0', font: 'var(--t-cuerpo)', color: 'var(--ink)', maxWidth: '72ch' });
    todos(el, '.rec', { background: 'var(--accent-soft)', borderRadius: 'var(--r-m)', padding: 'var(--s-2) var(--s-3)' });
  },
  'pm-dos': el => Object.assign(el.style, { display: '-webkit-box', WebkitLineClamp: '2', WebkitBoxOrient: 'vertical', whiteSpace: 'normal', overflow: 'hidden' }),
  'pm-pad': el => Object.assign(el.style, { padding: 'var(--s-3) var(--relleno) 0' }),
};
const EN_PANEL = ['pm-conex', 'pm-tarjetas', 'pm-kv', 'pm-form', 'pm-texto'];

/** h() común + las piezas «pm-*» con sus estilos de tokens (y el margen de panel si va suelta dentro de un panel). */
export function h(tag, attrs = {}, ...hijos) {
  const el = hBase(tag, attrs, ...hijos);
  const cls = typeof attrs?.class === 'string' ? attrs.class.split(/\s+/).filter(c => PIEZAS[c]) : [];
  if (!cls.length) return el;
  cls.forEach(c => PIEZAS[c](el));
  if (cls.some(c => EN_PANEL.includes(c))) queueMicrotask(() => { if (el.parentElement?.matches('section.panel')) Object.assign(el.style, DENTRO_DE_PANEL); });
  return el;
}

/** Compatibilidad: ya no hay hoja que inyectar. */
export function estilosLocales() {}

/** Avatar con iniciales. */
export const avatar = (nombre, s = false) => h('span', { class: `av${s ? ' s' : ''}`, 'aria-hidden': 'true' }, iniciales(nombre));

/** Cabecera de tarjeta de persona: avatar + nombre + segunda línea + algo a la derecha. */
export function cabPersona(nombre, linea, der) {
  return h('div', { class: 'pm-cab' }, avatar(nombre), h('span', { class: 't' }, h('b', {}, nombre), linea ? h('span', {}, linea) : null), der ? h('span', { class: 'der' }, der) : null);
}

/** Campo de formulario con su etiqueta. */
export function campo(texto, control, { ancho = false } = {}) {
  const nativo = control?.matches?.('input, select, textarea');
  if (control?.matches?.('input:not([type=checkbox]):not([type=radio]), select, textarea')) control.style.minHeight = 'var(--s-10)';
  // Con chips (botones) no va <label>: pulsar el texto activaría el primer chip.
  return h(nativo ? 'label' : 'div', { class: `campo${ancho ? ' ancho' : ''}`, role: nativo ? null : 'group', 'aria-label': nativo ? null : texto },
    h('span', { class: 'campo-et' }, texto), control);
}

/** Elegir entre pocas opciones con chips (en vez de un desplegable nativo). Se lee igual que un <select>: el.value.
 *  opciones: ['A', 'B'] o [{ valor, texto, icono }]. */
export function elegir(opciones, { valor, etiqueta, alCambiar, desactivado = false } = {}) {
  const ops = opciones.map(o => (typeof o === 'string' ? { valor: o, texto: o } : o));
  const el = chipsFiltro({ etiqueta, opciones: ops, valor: valor ?? ops[0]?.valor, alCambiar });
  Object.defineProperty(el, 'value', { get: () => el.valor(), configurable: true });
  if (desactivado) el.querySelectorAll('button').forEach(b => { b.disabled = true; });
  return el;
}

/** Días entre dos fechas ISO (b − a). */
export function dias(a, b = hoyMadrid()) {   // V2: hoy real de Madrid
  if (!a) return null;
  return Math.round((new Date(b.slice(0, 10) + 'T12:00:00') - new Date(a.slice(0, 10) + 'T12:00:00')) / 864e5);
}

/** «hace 3 h», «en 41 h» a partir de horas. */
export function horasTxt(h_) {
  if (h_ === null || h_ === undefined) return '—';
  const a = Math.abs(h_);
  return a < 48 ? `${fmt.num(a, a < 10 ? 1 : 0)} h` : `${fmt.num(a / 24, 1)} días`;
}

/** Chip de reloj de una decisión. */
export function chipReloj(d) {
  const mapa = { 'en plazo': 'verde', 'por caducar': 'ambar', caducada: 'rojo', 'contestada a tiempo': 'verde', 'contestada tarde': 'ambar' };
  return chipEstado(mapa[d.estado] || 'gris', d.estado);
}

/** Lee la cola de acciones simuladas de un módulo (o las propias) sin romper la pantalla si falla. */
export async function leerCola(ctx, modulo) {
  if (!ctx.servidor) return [];
  try { return (await ctx.api(modulo ? `acciones?modulo=${modulo}` : 'acciones')).acciones || []; }
  catch { return []; }
}

export function vp(a) {
  try { let v = JSON.parse(a.vista_previa || 'null'); if (typeof v === 'string') v = JSON.parse(v); return v && typeof v === 'object' ? v : {}; }
  catch { return {}; }
}

export { icono };
