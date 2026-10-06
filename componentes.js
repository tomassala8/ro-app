// componentes.js · piezas reutilizables de la app de RO.
//
// Reglas para quien construye un módulo:
//  · Cada componente devuelve un HTMLElement (nunca HTML en texto): así no hay inyección de código
//    con nombres de clientes o asuntos de correo.
//  · Estados de color: 'verde' | 'ambar' | 'rojo' | 'gris'. Medible: 'hoy' | 'medias' | 'no'.
//  · Nada de alert(), confirm() ni prompt(): para confirmar, botonConfirmar().
//  · Todo lo que se pulsa es <button> o <a> (teclado gratis). Nada de div con onclick.
//  · Catálogo vivo con ejemplos: abre la app como Tomás → Sistema → Componentes.

import { diaRO, horaRO, instanteRO, horasDesdeRO, horasHastaRO, fechaCivilRO, mesRO, nombreMesRO, zonaFechaRO } from './_fechas_ro.js';

import { telefono as telefonoComun } from './modulos/_telefono.js';   // regla común de teléfonos (3-oct)
import { SALUD } from './modulos/_constantes_ro.js';   // L-34 (hoja sin imports: no hay ciclo)

/**
 * h(etiqueta, atributos, ...hijos) · crea elementos.
 *  atributos: { class, text, html: NO existe a propósito, on: {click: fn}, data-*, aria-*, ... }
 *  hijos: elementos, textos, números, null/false (se ignoran) o arrays.
 */
/**
 * urlSegura(u) · ronda 6 (A4): solo http, https, mailto, tel, sip (wa.me va por https), anclas «#», rutas relativas y
 * data:image en «src». Cualquier otro esquema (javascript:, data:text/html, vbscript:…) se cambia por «#».
 */
export function urlSegura(u, atributo = 'href') {
  const t = String(u ?? '').trim();
  if (/^(https?:|mailto:|tel:|sip:|#|\/(?!\/)|\.{1,2}\/|[\w\-./]+\.(html|js|css|png|svg|jpg|jpeg|webp)(\?|#|$)|\?)/i.test(t)) return t;
  if (atributo === 'src' && /^data:image\/(png|jpe?g|gif|webp|svg\+xml);/i.test(t)) return t;
  if (/^[\w\-]+(\/[\w\-.]*)*$/.test(t) && !/^[a-z][\w+.-]*:/i.test(t)) return t;   // ruta relativa sin esquema
  return '#';
}

export function h(tag, attrs = {}, ...hijos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'text') el.textContent = v;
    else if (k === 'on') for (const [ev, fn] of Object.entries(v)) el.addEventListener(ev, fn);
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (v === true) el.setAttribute(k, '');
    else if (k === 'href' || k === 'src' || k === 'action' || k === 'formaction') el.setAttribute(k, urlSegura(v, k));
    else if (/^on/i.test(k)) continue;   // nunca atributos on* en texto: los eventos van por «on: {…}»
    else el.setAttribute(k, v);
  }
  const meter = x => {
    if (x === null || x === undefined || x === false) return;
    if (Array.isArray(x)) return x.forEach(meter);
    el.append(x instanceof Node ? x : document.createTextNode(String(x)));
  };
  hijos.forEach(meter);
  return el;
}

const svgNS = 'http://www.w3.org/2000/svg';
function s(tag, attrs = {}) {
  const el = document.createElementNS(svgNS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined) el.setAttribute(k, v);
  return el;
}

// ------------------------------------------------------------------ iconos
/**
 * Un único juego de iconos (trazo 1,8 px, estilo Lucide). Base: el objeto P de la ficha v3
 * (HERRAMIENTA_RO_2026-10-02/plantilla.html) más los que faltaban para la app. Cadenas fijas, nunca datos.
 * icono('phone') · icono('alert', { clase: 's', titulo: 'Aviso' }) → <svg class="i">.
 * Tamaños: por defecto 18 px; clase 's' = 15 px; 'l' = 24 px.
 */
export const ICONOS = {
  // de la ficha v3 (objeto P)
  hoy: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
  cli: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 10h18"/>',
  cap: '<path d="M3 4h18l-7 9v6l-4 2v-8z"/>',
  eq: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5"/><circle cx="17.5" cy="9" r="2.5"/><path d="M16 14.6c2.9.2 5 2.2 5 5.4"/>',
  dir: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  aj: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>',
  fire: '<path d="M12 3c2 4 6 6 6 11a6 6 0 0 1-12 0c0-3 2-5 3-7 1 2 2 3 3 3 0-2 0-4 0-7z"/>',
  star: '<path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z"/>',
  res: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  heart: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z"/>',
  chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z"/>',
  check: '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 12l3 3 5-6"/>',
  casilla: '<rect x="3" y="3" width="18" height="18" rx="3"/>',   // 3-oct: casilla sin marcar (0 elegidas)
  casilla_media: '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 12h8"/>',   // 3-oct: algunas elegidas
  doc: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
  hist: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
  phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
  video: '<rect x="2" y="6" width="14" height="12" rx="2"/><path d="M16 10l6-3v10l-6-3"/>',
  euro: '<path d="M17 6.5A7 7 0 1 0 17 17.5M4 10h9M4 14h9"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  users: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5"/>',
  zap: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
  alert: '<path d="M12 3l10 18H2z"/><path d="M12 10v4M12 17.5h.01"/>',
  drive: '<path d="M8 3h8l6 10-4 7H6l-4-7z"/><path d="M8 3l6 10M16 3l-6 10M2 13h20"/>',
  link: '<path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>',
  ext: '<path d="M14 4h6v6M20 4l-9 9M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
  chev: '<path d="M6 9l6 6 6-6"/>',
  cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
  flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
  rocket: '<path d="M5 15c-1.5 1.5-2 5-2 5s3.5-.5 5-2M9 15l-3-3c2-6 7-9 13-9 0 6-3 11-9 13z"/><circle cx="14.5" cy="9.5" r="1.5"/>',
  spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6"/>',
  plug: '<path d="M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4"/>',
  wa: '<path d="M3 21l1.7-5A8.5 8.5 0 1 1 8 19.4z"/><path d="M9 9.5c.3 2 2.3 4.2 4.5 4.6l1.2-1.1 1.8.8c-.3 1.3-1.4 1.9-2.6 1.6-3.2-.8-5.8-3.4-6.4-6.5-.2-1.2.5-2.2 1.7-2.4l.8 1.8z"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  send: '<path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/>',
  crown: '<path d="M3 8l4 4 5-7 5 7 4-4-2 11H5z"/>',
  key: '<circle cx="8" cy="15" r="4"/><path d="M10.8 12.2L21 2M17 6l3 3M14 9l2 2"/>',
  up: '<path d="M7 17L17 7M9 7h8v8"/>',
  // añadidos para la app
  buscar: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  cerrar: '<path d="M18 6L6 18M6 6l12 12"/>',
  derecha: '<path d="M9 6l6 6-6 6"/>',
  izquierda: '<path d="M15 6l-6 6 6 6"/>',
  flecha: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  volver: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  opciones: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  mas: '<path d="M12 5v14M5 12h14"/>',
  ok: '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5h.01"/>',
  ojo: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  candado: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  escudo: '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/>',
  filtro: '<path d="M4 5h16M7 12h10M10 19h4"/>',
  marcador: '<path d="M6 3h12v18l-6-4-6 4z"/>',
  campana: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
  sube: '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
  baja: '<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>',
  grafico: '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
  megafono: '<path d="M3 11v2a2 2 0 0 0 2 2h2l5 4V5L7 9H5a2 2 0 0 0-2 2z"/><path d="M16 8a5 5 0 0 1 0 8M19 5a9 9 0 0 1 0 14"/>',
  base: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  pin: '<path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
  // R15 (E0): «Conexiones» (dos enchufes unidos), «Algo va mal / Tengo una idea» (bocadillo con aviso), fijar (chincheta),
  // teclado (chuleta de atajos).
  conexiones: '<path d="M7 7l3 3M4 10l3-3 3 3-3 3zM17 17l-3-3M20 14l-3 3-3-3 3-3zM9.5 14.5l5-5"/>',
  opinion: '<path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z"/><path d="M12 8v4M12 15.5v.01"/>',
  fijar: '<path d="M9 4h6l-1 6 3 3H7l3-3zM12 13v8"/>',
  teclado: '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
  capas: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
  maletin: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
  cartera: '<path d="M20 7H5a2 2 0 0 1 0-4h13v4"/><path d="M3 5v14a2 2 0 0 0 2 2h15V7"/><circle cx="16" cy="14" r="1.2"/>',
  persona: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5"/>',
  auricular: '<path d="M3 14v-2a9 9 0 0 1 18 0v2"/><path d="M21 15a2 2 0 0 1-2 2h-1v-6h1a2 2 0 0 1 2 2zM3 15a2 2 0 0 0 2 2h1v-6H5a2 2 0 0 0-2 2z"/><path d="M19 17v1a3 3 0 0 1-3 3h-3"/>',
  libro: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>',
  medidor: '<path d="M12 14l4-4"/><path d="M3.3 17a10 10 0 1 1 17.4 0"/>',
  mundo_web: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M7 6.5h.01M10 6.5h.01"/>',
  compartir: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>',
  recargar: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
  descarga: '<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>',
  editar: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  basura: '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
  componentes: '<path d="M12 2l4 4-4 4-4-4zM6 8l4 4-4 4-4-4zM18 8l4 4-4 4-4-4zM12 14l4 4-4 4-4-4z"/>',
  vacio: '<rect x="3" y="3" width="18" height="18" rx="3" stroke-dasharray="3 3"/>',
};

/** icono(nombre, { clase, titulo }) · SVG del juego único. Si el nombre no existe, pinta un cuadrado discontinuo. */
export function icono(nombre, { clase = '', titulo } = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  el.setAttribute('class', `i${clase ? ' ' + clase : ''}`);
  el.setAttribute('viewBox', '0 0 24 24');
  if (titulo) { el.setAttribute('role', 'img'); el.setAttribute('aria-label', titulo); }
  else el.setAttribute('aria-hidden', 'true');
  el.innerHTML = ICONOS[nombre] || ICONOS.vacio;   // solo cadenas fijas de ICONOS: nunca datos
  return el;
}

/** Icono de cada pantalla del menú (por id de módulo) y, si falta, por grupo. Lo usa la carcasa y ⌘K. */
export const ICONO_MODULO = {
  'mi-dia': 'hoy', 'mi-trabajo': 'casilla', 'en-rojo': 'fire', bandeja: 'inbox', ficha: 'cli', 'ficha-cliente': 'cli', 'informe-cliente': 'grafico',
  'clientes-nuevos': 'rocket', 'informes-mensuales': 'doc', incidencias: 'alert', captacion: 'target', 'salud-crm': 'base',
  'seo-web': 'globe', redes: 'heart', produccion: 'check', horas: 'clock', reuniones: 'video', personas: 'eq',
  setters: 'auricular', 'ventas-ro': 'megafono', prospeccion: 'send', 'dinero-cliente': 'euro', finanzas: 'cartera',
  rastro: 'hist', decisiones: 'flag', agenda: 'cal', 'chat-equipo': 'chat', 'panel-direccion': 'medidor', ajustes: 'aj', indicadores: 'filtro', componentes: 'componentes',
  // Ronda 9 (D-P-IA1, D-P-AL1, N1): pantallas nuevas con icono propio (antes caían al de su grupo).
  'asistente-ia': 'spark', alertas: 'campana', paneles: 'capas',
  conexiones: 'conexiones',   // R15: Ajustes › Conexiones (antes caía al icono del grupo «Sistema»)
};
export const ICONO_GRUPO = { Hoy: 'hoy', Clientes: 'cli', 'Captación y CRM': 'cap', 'SEO, web y redes': 'globe', Equipo: 'eq', 'Ventas de RO': 'megafono', Dinero: 'euro', Sistema: 'aj' };

/** Marca de RO (hexágono con barras), en blanco para el menú marino. */
export function marcaRO({ tam = 30 } = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  el.setAttribute('class', 'marca'); el.setAttribute('viewBox', '0 0 32 32'); el.setAttribute('aria-hidden', 'true');
  el.setAttribute('width', tam); el.setAttribute('height', tam);
  el.innerHTML = '<path d="M16 2l12 7v14l-12 7-12-7V9z" fill="#fff"/><rect x="10" y="17" width="3" height="6" fill="#16205e"/><rect x="14.5" y="13" width="3" height="10" fill="#16205e"/><rect x="19" y="10" width="3" height="13" fill="#16205e"/>';
  return el;
}

/** iniciales('Lucía Caso') → 'LC' (avatares y logos sin imagen). */
export const iniciales = t => String(t || '').replace(/\(.*?\)/g, '').trim().split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0]).join('').toUpperCase() || '?';

// ----------------------------------------------------------------- formatos
// Ronda 9 (auditoría 30, P0-4): punto de miles SIEMPRE («3.860 €», no «3860 €») y signo menos tipográfico «−».
// En es-ES, Intl no agrupa los números de 4 cifras salvo con useGrouping: 'always'. Un solo formateador para toda la app.
const _nfs = new Map();
const _nfDe = dec => { const k = String(dec); if (!_nfs.has(k)) _nfs.set(k, new Intl.NumberFormat('es-ES', { maximumFractionDigits: dec, minimumFractionDigits: dec, useGrouping: 'always' })); return _nfs.get(k); };
const _menos = t => t.replace(/^-/, '\u2212');
const nf = { format: n => _menos(_nfDe(0).format(n)) };
const _nada = n => n === null || n === undefined || Number.isNaN(n) || (typeof n !== 'number' && Number.isNaN(Number(n)));
/** pluralDe('cita') → 'citas' · 'mes' → 'meses' · 'acción' → 'acciones' · 'vez' → 'veces' (para fmt.plural sin «varios»). */
export function pluralDe(p) {
  const t = String(p || '');
  if (!t) return t;
  if (/[aeiouáéó]$/i.test(t)) return t + 's';
  if (/z$/i.test(t)) return t.slice(0, -1) + 'ces';
  if (/ión$/i.test(t)) return t.slice(0, -3) + 'iones';
  if (/[sx]$/i.test(t) && !/(és|ás|ís|ós|ús|mes)$/i.test(t)) return t;   // «el lunes / los lunes», «análisis»
  return t + 'es';
}
// V2-E (B1 de 40_A y B2 de 40_B): red de seguridad común para «1 correos», «1 leads», «hace 1 días»… que lleguen escritos
// a mano o desde los datos. Solo cambia la palabra que va justo detrás de un «1» suelto (no «21», «1,5» ni «1.200»).
const SINGULAR = { leads: 'lead', citas: 'cita', correos: 'correo', contactos: 'contacto', usuarios: 'usuario', mensajes: 'mensaje',
  cambios: 'cambio', subcuentas: 'subcuenta', técnicas: 'técnica', pospuestas: 'pospuesta', indicadores: 'indicador', tareas: 'tarea',
  clientes: 'cliente', alertas: 'alerta', días: 'día', horas: 'hora', personas: 'persona', piezas: 'pieza', palabras: 'palabra',
  cuentas: 'cuenta', webs: 'web', semanas: 'semana', meses: 'mes', veces: 'vez', quejas: 'queja', llamadas: 'llamada', reuniones: 'reunión',
  respuestas: 'respuesta', campañas: 'campaña', anuncios: 'anuncio', facturas: 'factura', altas: 'alta', bajas: 'baja', revisiones: 'revisión',
  menciones: 'mención', decisiones: 'decisión', publicaciones: 'publicación', huecos: 'hueco', fallos: 'fallo', avisos: 'aviso', cosas: 'cosa',
  oportunidades: 'oportunidad', tickets: 'ticket', grabadas: 'grabada', grabaciones: 'grabación', conversaciones: 'conversación', visitas: 'visita', clics: 'clic', reseñas: 'reseña', entradas: 'entrada' };
const ADJ_SINGULAR = { bruscos: 'brusco', bruscas: 'brusca', abiertas: 'abierta', abiertos: 'abierto', vencidas: 'vencida', vencidos: 'vencido',
  pendientes: 'pendiente', nuevos: 'nuevo', nuevas: 'nueva', fallidos: 'fallido', fallidas: 'fallida', activos: 'activo', activas: 'activa',
  tuyas: 'tuya', tuyos: 'tuyo', devueltas: 'devuelta', devueltos: 'devuelto', marcadas: 'marcada', marcados: 'marcado', perdidas: 'perdida',
  críticos: 'crítico', críticas: 'crítica', parados: 'parado', paradas: 'parada', aparte: 'aparte' };
const RE_UNO = new RegExp(`(^|[^\\d.,\\u2212-])1 (${Object.keys(SINGULAR).join('|')})(?: (${Object.keys(ADJ_SINGULAR).join('|')}))?(?![\\wáéíóúñ])`, 'g');
// V3a (44 C2): también el adjetivo suelto tras «1» («1 vencidas» → «1 vencida»), y «1 de 1 tickets» → «1 de 1 ticket»
const RE_UNO_ADJ = new RegExp(`(^|[^\\d.,\\u2212-])1 (${Object.keys(ADJ_SINGULAR).filter(a => a !== 'aparte').join('|')})(?![\\wáéíóúñ])`, 'g');
const RE_DE_UNO = new RegExp(`\\b(\\d+) de 1 (${Object.keys(SINGULAR).join('|')})(?![\\wáéíóúñ])`, 'g');
const _singular1 = t => t.replace(RE_UNO, (_, pre, s, a) => `${pre}1 ${SINGULAR[s]}${a ? ` ${ADJ_SINGULAR[a]}` : ''}`)
  .replace(RE_UNO_ADJ, (_, pre, a) => `${pre}1 ${ADJ_SINGULAR[a]}`).replace(RE_DE_UNO, (_, n, s) => `${n} de 1 ${SINGULAR[s]}`);
export const singularTras1 = t => (typeof t === 'string' && t.includes('1 ') ? _singular1(t) : t);
export const fmt = {
  num: (n, dec = 0) => (_nada(n) ? '—' : _menos(_nfDe(dec).format(Number(n)))),
  eur: (n, dec = 0) => (_nada(n) ? '—' : `${_menos(_nfDe(dec).format(dec ? Number(n) : Math.round(Number(n))))} €`),
  pct: (n, dec = 0) => (_nada(n) ? '—' : `${_menos(_nfDe(dec).format(dec ? Number(n) : Math.round(Number(n))))} %`),
  /** con signo siempre: «+1.470 €», «−3.428 €» (desgloses y diferencias). */
  eurSigno: (n, dec = 0) => (_nada(n) ? '—' : `${Number(n) > 0 ? '+' : ''}${fmt.eur(n, dec)}`),
  fecha: iso => {
    if (!iso) return '—';
    const d = new Date(iso.length <= 10 ? iso + 'T12:00:00' : iso.replace(' ', 'T'));
    return Number.isNaN(+d) ? iso : `${d.getDate()}-${MESES_CORTOS[d.getMonth()]}`;   // V3a (44 §2.3): «2-oct», «sep» siempre
  },
  // V2-E: «hoy/ayer» por el calendario de Madrid (fechas.diasDesde), no por las 24 h desde ahora ni la zona del Mac.
  hace: iso => {
    if (!iso) return 'sin dato';
    const dias = fechas.diasDesde(iso);
    if (dias === null) return iso;
    return dias <= 0 ? 'hoy' : dias === 1 ? 'ayer' : `hace ${dias} días`;
  },
  /** antiguedad(horas) → «5 h» hasta 48 h y luego «3 días» (nunca «478 h»). */
  antiguedad: horas => fechas.antiguedad(horas),
  // ---- ronda 6 (auditoría 29, F-15): formato es-ES común ----
  /** fechaHora('2026-10-02 16:04') → «2-oct, 16:04» (V3a, 44 §2.3) */
  fechaHora: iso => {
    if (!iso) return '—';
    const d = new Date(String(iso).replace(' ', 'T'));
    if (Number.isNaN(+d)) return iso;
    return `${d.getDate()}-${MESES_CORTOS[d.getMonth()]}, ${d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}`;   // «2-oct, 17:34»
  },
  /** plural(2, 'correo', 'correos') → «2 correos»; nunca «correo(s)» ni «1 correos». Sin «varios», lo forma solo
   *  (cita → citas, mes → meses, acción → acciones, vez → veces). Úsalo SIEMPRE que la cifra venga de un dato. */
  plural: (n, uno, varios) => `${_menos(_nfDe(0).format(n))} ${Number(n) === 1 ? uno : (varios || pluralDe(uno))}`,
};

/** Estado de color a partir de un valor y umbrales. mejorSi: 'alto' | 'bajo'. */
export function semaforo(valor, { verde, ambar, mejorSi = 'alto' }) {
  if (valor === null || valor === undefined) return 'gris';
  if (mejorSi === 'alto') return valor >= verde ? 'verde' : valor >= ambar ? 'ambar' : 'rojo';
  return valor <= verde ? 'verde' : valor <= ambar ? 'ambar' : 'rojo';
}

/**
 * cuentagotas(valores, umbral, { mejorSi = 'bajo' }) · Ronda 10 (guía 3.4, de produccion_comun.js): «rojo con cuentagotas».
 *   Devuelve el corte a partir del cual una fila va en rojo. Si las que pasan del umbral son como mucho un tercio, el corte
 *   es el umbral; si son más, solo el tercio peor. mejorSi: 'alto' (cuanto más, mejor) invierte el sentido: el corte es el
 *   valor por DEBAJO del cual va en rojo. La decide el dueño del módulo: semaforo() y las tablas no la aplican solas.
 */
export function cuentagotas(valores, umbral = 14, { mejorSi = 'bajo' } = {}) {
  const v = (valores || []).filter(x => typeof x === 'number' && Number.isFinite(x));
  const n = v.length;
  const malo = x => (mejorSi === 'alto' ? x < umbral : x > umbral);
  if (!n || v.filter(malo).length <= n / 3) return umbral;
  const k = Math.floor(n / 3);
  if (!k) return mejorSi === 'alto' ? -Infinity : Infinity;
  return mejorSi === 'alto' ? Math.min(umbral, [...v].sort((a, b) => a - b)[k]) : Math.max(umbral, [...v].sort((a, b) => b - a)[k]);
}

// --------------------------------------------------------- chip de estado
/** chipEstado('rojo', 'Sin responder') · estados: verde | ambar | rojo | gris | azul */
export function chipEstado(estado = 'gris', texto, { punto = true } = {}) {
  if (estado === 'ambar' && typeof texto === 'string' && /\bcrític/i.test(texto)) estado = 'rojo';   // V3a (44 §2.1): «Crítico» nunca en ámbar
  // Glosario del coordinador (3-oct, 44 §2.1): el segundo nivel se llama «Vigilar» en toda la app (el dato sigue siendo «atencion»)
  if (typeof texto === 'string' && /^\s*atención\s*$/i.test(texto)) texto = /^\s*A/.test(texto) ? 'Vigilar' : 'vigilar';
  return h('span', { class: `chip ${estado}${punto ? '' : ' sin-punto'}` }, texto);
}

// ------------------------------------------------------- sello «medible»
const SELLOS = { hoy: 'Se mide hoy', medias: 'A medias', no: 'Todavía no' };
/** selloMedible('hoy' | 'medias' | 'no', detalle?) · el detalle va en el title (p. ej. qué falta). */
export function selloMedible(medible = 'hoy', detalle) {
  return h('span', { class: `sello ${medible}`, title: (typeof detalle === 'string' ? limpiaTexto(detalle) : detalle) || SELLOS[medible] }, h('i', { 'aria-hidden': 'true' }), SELLOS[medible]);
}

// ---------------------------------------------------------------- frescura
/** frescura({fuente, fecha, estado: 'ok'|'viejo'|'roto'}) · «Desk · hace 4 h». */
export function frescura({ fuente, fecha, edad_h, estado = 'ok' }) {
  let cuando = fecha ? fmt.hace(fecha) : '';
  if (edad_h !== undefined && edad_h !== null) cuando = edad_h < 1 ? 'hace menos de 1 h' : `hace ${fmt.num(edad_h, edad_h < 10 ? 1 : 0)} h`;
  if (estado === 'sin datos') { estado = 'roto'; cuando = 'sin datos'; }
  const cls = estado === 'ok' ? '' : estado === 'viejo' ? ' viejo' : ' roto';
  return h('span', { class: `fresco${cls}`, title: estado === 'viejo' ? 'Dato más viejo de lo normal para esta fuente' : null }, `${fuente} · ${cuando}`);
}

// ------------------------------------------------------- aviso dato parcial
/** avisoParcial(texto, {tipo: 'parcial'|'info', fuente}) · «con el 52 % de horas imputadas, orientativo». */
export function avisoParcial(texto, { tipo = 'parcial', titulo } = {}) {
  return h('div', { class: `aviso${tipo === 'info' ? ' info' : ''}`, role: 'note' },
    h('span', { class: 'ico', 'aria-hidden': 'true' }, icono(tipo === 'info' ? 'info' : 'alert')),
    h('div', {}, titulo ? h('b', {}, titulo + ' ') : null, typeof texto === 'string' ? limpiaTexto(texto) : texto));
}

// ------------------------------------------------------ ficha de indicador
/**
 * fichaIndicador({
 *   titulo: 'Clientes en rojo', valor: 18, unidad: 'de 66', estado: 'rojo',
 *   tendencia: { delta: +3, texto: 'frente a ayer', mejorSi: 'bajo' },
 *   umbral: 'verde ≤ 5 · rojo > 10', medible: 'hoy' | 'medias' | 'no', medibleDetalle,
 *   frescura: { fuente, fecha | edad_h, estado }, prueba: { texto, href | onClick }
 * })
 * Si hay prueba, la ficha entera es un enlace o botón (clic a la prueba, patrón C4).
 */
/** Línea de apoyo compacta: sello solo si no se mide hoy y un «i» con umbral, medición y frescura en el title. */
function infoCompacta(o, clase = 'pie') {
  const partes = [];
  if (o.umbral && typeof o.umbral === 'string') partes.push(limpiaTexto(o.umbral));
  if (o.medible && o.medible !== 'hoy') partes.push(`${({ medias: 'A medias', no: 'Todavía no' })[o.medible] || ''}${o.medibleDetalle ? ': ' + limpiaTexto(o.medibleDetalle) : ''}`);
  if (o.frescura) partes.push(frescura(o.frescura).textContent);
  const sello = o.medible && o.medible !== 'hoy' ? selloMedible(o.medible, o.medibleDetalle) : null;
  if (!partes.length && !sello) return null;
  return h('span', { class: `${clase} compacta` }, sello,
    partes.length ? h('span', { class: 'info-i', title: partes.join(' · '), 'aria-label': partes.join(' · '), role: 'img' }, 'i') : null);
}

export function fichaIndicador(o) {
  const t = o.tendencia;
  let tend = null;
  if (t && t.delta !== undefined && t.delta !== null) {
    const bien = t.delta === 0 ? 'igual' : (t.delta > 0) === (t.mejorSi !== 'bajo') ? 'bien' : 'mal';
    const flecha = t.delta > 0 ? '▲' : t.delta < 0 ? '▼' : '=';
    tend = h('span', { class: `tend ${bien}` }, `${flecha} ${t.delta > 0 ? '+' : ''}${fmt.num(t.delta, t.dec || 0)}${t.unidad || ''} ${t.texto || ''}`);
  }
  const hijos = [
    h('span', { class: 'l' }, o.icono ? h('span', { class: `ico-c s ${o.estado || ''}` }, icono(o.icono)) : null, o.titulo),
    o.valor === null || o.valor === undefined || o.valor === '' ? h('span', { class: 'v sin-dato' }, h('small', {}, o.sinDato ? `Sin dato · ${o.sinDato}` : 'Sin dato'))
      : h('span', { class: 'v' }, o.valor, o.unidad ? h('small', {}, o.unidad) : null),
    tend,
    // Ronda 6 (auditoría 29, F-08): tarjeta de 3 líneas. Umbral, sello y frescura van al icono «i» (title); el sello
    // solo se ve si NO se mide hoy (el estado normal no se anuncia). o.completa = true para el formato largo de antes.
    o.completa && o.umbral ? h('span', { class: 'umbral' }, typeof o.umbral === 'string' ? limpiaTexto(o.umbral) : o.umbral) : null,
    o.completa ? h('span', { class: 'pie' }, selloMedible(o.medible || 'hoy', o.medibleDetalle), o.frescura ? frescura(o.frescura) : null)
      : infoCompacta(o),
    o.prueba ? h('span', { class: 'prueba' }, (o.prueba.texto || 'Ver la prueba') + ' →') : null,
  ];
  const cls = `ind ${o.estado || 'gris'}${o.icono ? ' con-ico' : ''}`;
  const etiqueta = `${o.titulo}: ${o.valor ?? 'sin dato'} ${o.unidad || ''}`.trim();
  if (o.prueba?.href) return h('a', { class: cls, href: o.prueba.href, 'aria-label': etiqueta + '. ' + (o.prueba.texto || 'Ver la prueba') }, hijos);
  if (o.prueba?.onClick) return h('button', { class: cls, type: 'button', on: { click: o.prueba.onClick }, 'aria-label': etiqueta + '. ' + (o.prueba.texto || 'Ver la prueba') }, hijos);
  return h('div', { class: cls }, hijos);
}

// ------------------------------------------------------------------- logo
/** logoCliente({nombre, logo}) · imagen o iniciales si no hay logo. */
export function logoCliente({ nombre = '', logo }, clase = 'logo-cli') {
  if (logo) return h('img', { class: clase, src: logo, alt: '', loading: 'lazy', decoding: 'async' });
  const ini = nombre.split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0]).join('').toUpperCase();
  return h('span', { class: clase, 'aria-hidden': 'true' }, ini || '?');
}

/** saludCliente(0-100) · barra + número; verde ≥ 60, ámbar 40-59, rojo < 40 (D-02 provisional). */
export function saludCliente(valor, { etiqueta = 'Salud' } = {}) {
  const est = semaforo(valor, SALUD);
  return h('span', { class: `salud ${est}`, title: `${etiqueta} ${valor ?? '—'} de 100` },
    h('span', {}, etiqueta + ' ', h('b', {}, valor ?? '—')),
    h('span', { class: 'barra', 'aria-hidden': 'true' }, h('i', { style: { width: `${Math.max(0, Math.min(100, valor || 0))}%` } })));
}

// --------------------------------------------------------- tarjeta cliente
/** tarjetaCliente({nombre, logo, salud, motivo, extra, onAbrir}) · si hay onAbrir es un botón. */
export function tarjetaCliente(c) {
  const hijos = [
    logoCliente(c, 'logo'),
    h('span', { class: 'nom' }, c.nombre),
    saludCliente(c.salud),
    h('span', { class: 'mot' }, c.motivo || '', c.extra ? [' · ', c.extra] : null),
  ];
  return c.onAbrir
    ? h('button', { class: 'tcli', type: 'button', on: { click: c.onAbrir } }, hijos)
    : h('div', { class: 'tcli' }, hijos);
}

// ----------------------------------------------------------- lo primero hoy
/**
 * listaLoPrimero(items, {vacio})
 *   item = { motivo, detalle, estado: 'rojo'|'ambar', botones: [elementos] }
 * Máximo recomendado: 7 (patrón C1). Si no hay nada, estado vacío que celebra.
 */
// Ronda 10: estado 'gris' | 'info' para motivos informativos; { subir: false } para que en el móvil el panel NO suba
// arriba del todo (solo «Lo primero hoy» debe subir; Hallazgos y listas parecidas, no).
export function listaLoPrimero(items, { vacio, subir = true } = {}) {
  if (!items.length) return estadoVacio(vacio || { titulo: 'Nada crítico hoy', porque: 'No tienes nada crítico a tu nombre.', celebrar: true });
  return h('ol', { class: `primero${subir ? '' : ' no-subir'}` }, items.map((it, i) =>
    h('li', { class: it.estado || 'rojo' },
      h('span', { class: 'num', 'aria-hidden': 'true' }, it.icono ? icono(it.icono) : i + 1),
      h('div', {}, h('div', { class: 'mot' }, it.motivo), it.detalle ? h('div', { class: 'det' }, it.detalle) : null),
      h('div', { class: 'acc' }, it.botones || []))));
}

// ------------------------------------------------------------- tabla densa
/**
 * tablaDensa({
 *   columnas: [{ clave, titulo, num?: bool, ordenable?: true, valor?: fila => comparable,
 *                celda?: fila => Node|texto, principal?: bool }],
 *   filas, filtros: [{ clave, titulo, opciones?: [..] (si no, se sacan de las filas) }],
 *   buscar: { campos: ['nombre'], placeholder }, orden: { clave, dir: 'asc'|'desc' },
 *   alPulsar: fila => {}, etiquetaFila: fila => 'texto para lectores de pantalla',
 *   vacio: { titulo, porque, que_hacer }, apilable: true (en móvil pasa a tarjetas)
 * })
 * Devuelve un <div> con controles + tabla. El estado (orden, filtros) vive dentro.
 */
/** Ronda 6 (F-15): una celda sin «celda» propia sale en es-ES: números con coma y punto de miles, fechas legibles. */
function celdaPorDefecto(v) {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'number') return fmt.num(v, Number.isInteger(v) ? 0 : 1);
  if (typeof v === 'string') return formatoTexto(v);
  return v;
}

export function tablaDensa(o) {
  // Ronda 5 (I-08): paginación común. porPagina por defecto 50; 0 = sin paginar. «Ver más» añade otra página.
  // Ronda 10 (N6): columnas sin «clave» no rompen (no son ordenables salvo que traigan valor()); filtros con chips
  // (≤ 4 opciones) o con el menú común «Puesto: Todos ▾» (nunca <select> nativo); en el móvil los filtros se pliegan
  // tras «Filtros ▾» y la tabla apilada se ordena con «Ordenar ▾»; cabecera ordenable = celda entera (≥ 32 px);
  // verTodas: true → «Ver las N filas» de una vez; columna.minAncho = '160px' pone el ancho mínimo en th y td.
  const porPagina = o.porPagina === undefined ? 50 : o.porPagina;
  const columnas = (o.columnas || []).map(cabeceraCompacta421);
  const ordenable = c => c.ordenable !== false && (c.clave !== undefined || typeof c.valor === 'function');
  const claveCol = (c, i) => (c.clave !== undefined ? c.clave : `__col${i}`);
  const estado = { orden: o.orden || null, filtros: {}, q: '', paginas: 1 };
  const raiz = h('div', { class: 'tabla-densa' });
  const cuerpo = h('tbody');
  const cuenta = h('span', { class: 'cuenta', 'aria-live': 'polite' });
  const ctl = h('div', { class: 'tabla-ctl' });

  if (o.buscar) {
    const id = uid('q');
    ctl.append(h('label', { for: id, class: 'sr' }, 'Buscar en la tabla'),
      h('input', { id, type: 'search', placeholder: o.buscar.placeholder || 'Buscar…', on: { input: e => { estado.q = e.target.value.trim().toLowerCase(); estado.paginas = 1; pintar(); } } }));
  }
  const filtrosCaja = h('div', { class: 'tabla-filtros', id: uid('tf') });
  const btFiltros = h('button', { type: 'button', class: 'bt mini tabla-filtros-bt', 'aria-expanded': 'false', 'aria-controls': filtrosCaja.id,
    on: { click: () => { const ab = !filtrosCaja.classList.contains('abierto'); filtrosCaja.classList.toggle('abierto', ab); btFiltros.setAttribute('aria-expanded', String(ab)); } } });
  const pintarBtFiltros = () => {
    const n = Object.values(estado.filtros).filter(Boolean).length;
    btFiltros.replaceChildren(icono('filtro', { clase: 's' }), n ? `Filtros · ${n}` : 'Filtros', icono('chev', { clase: 's' }));
  };
  for (const f of o.filtros || []) {
    const opciones = f.opciones || [...new Set((o.filas || []).map(r => r[f.clave]).filter(v => v !== null && v !== undefined && v !== ''))].sort((a, b) => String(a).localeCompare(String(b), 'es'));
    const alCambiar = v => { estado.filtros[f.clave] = v; estado.paginas = 1; pintarBtFiltros(); pintar(); };
    filtrosCaja.append(opciones.length <= 4 && !f.menu
      ? chipsFiltro({ etiqueta: f.titulo, opciones: [{ valor: '', texto: 'Todos' }, ...opciones.map(v => ({ valor: v, texto: String(v) }))], valor: '', alCambiar })
      : menuElegir({ etiqueta: f.titulo, opciones: opciones.map(v => ({ valor: v, texto: String(v) })), alCambiar }));
  }
  const conOrden = columnas.filter(ordenable);
  if (o.apilable !== false && conOrden.length > 1) {
    filtrosCaja.append(h('span', { class: 'solo-movil' }, menuElegir({ etiqueta: 'Ordenar por', todos: 'Sin ordenar', opciones: conOrden.map(c => ({ valor: claveCol(c, columnas.indexOf(c)), texto: c.titulo })),
      valor: estado.orden ? String(estado.orden.clave) : '', alCambiar: v => { estado.orden = v ? { clave: v, dir: 'desc' } : null; pintar(); } })));
  }
  if (filtrosCaja.childElementCount) { pintarBtFiltros(); ctl.append(btFiltros, filtrosCaja); }
  ctl.append(cuenta);

  const cabeceras = columnas.map((c, i) => {
    const th = h('th', { scope: 'col', class: c.num ? 'num' : null, title:c.tituloCompleto||null, 'aria-label':c.tituloCompleto||null, style: c.minAncho ? { minWidth: c.minAncho } : null });
    if (!ordenable(c)) th.textContent = c.titulo;
    else th.append(h('button', { type: 'button',title:c.tituloCompleto||null,'aria-label':c.tituloCompleto||null, on: { click: () => {
      const k = claveCol(c, i);
      const dir = estado.orden && estado.orden.clave === k && estado.orden.dir === 'desc' ? 'asc' : 'desc';
      estado.orden = { clave: k, dir }; pintar();
    } } }, c.titulo));
    return th;
  });
  const tabla = h('table', { class: `densa${columnas.length>=9?' compacta-421':''}${o.apilable !== false ? ' apilable' : ''}` }, h('thead', {}, h('tr', {}, cabeceras)), cuerpo);
  raiz.append(ctl, h('div', { class: 'tabla-scroll' }, tabla));
  const hueco = h('div', { class: 'cuerpo' });
  const mas = h('div', { class: 'tabla-mas' });
  raiz.append(hueco, mas);

  function pintar() {
    let filas = (o.filas || []).filter(r => Object.entries(estado.filtros).every(([k, v]) => !v || String(r[k]) === String(v)));
    if (estado.q) filas = filas.filter(r => (o.buscar.campos || []).some(k => String(r[k] ?? '').toLowerCase().includes(estado.q)));
    if (estado.orden) {
      const i = columnas.findIndex((c, j) => claveCol(c, j) === estado.orden.clave);
      const col = columnas[i];
      const val = col?.valor || (r => r[estado.orden.clave]);
      const m = estado.orden.dir === 'asc' ? 1 : -1;
      filas = [...filas].sort((a, b) => {
        const x = val(a), y = val(b);
        if (x === y) return 0; if (x === null || x === undefined) return 1; if (y === null || y === undefined) return -1;
        return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), 'es')) * m;
      });
    }
    const total = filas.length;
    const visibles = porPagina ? filas.slice(0, porPagina * estado.paginas) : filas;
    cabeceras.forEach((th, i) => th.setAttribute('aria-sort', estado.orden && estado.orden.clave === claveCol(columnas[i], i) ? (estado.orden.dir === 'asc' ? 'ascending' : 'descending') : 'none'));
    cuerpo.replaceChildren(...visibles.map(r => {
      const tr = h('tr', {}, columnas.map(c => h('td', { class: [c.num ? 'num' : '', c.principal ? 'principal' : ''].join(' ').trim() || null, 'data-l': c.tituloMovil||c.titulo,title:c.tituloCompleto||null, style: c.minAncho ? { minWidth: c.minAncho } : null }, c.celda ? c.celda(r) : celdaPorDefecto(r[c.clave]))));
      if (o.alPulsar && (!o.puedePulsar || o.puedePulsar(r))) {
        tr.classList.add('clic'); tr.tabIndex = 0;
        if (o.etiquetaFila) tr.setAttribute('aria-label', o.etiquetaFila(r));
        tr.addEventListener('click', e => { if (!e.target.closest('a,button')) o.alPulsar(r); });
        tr.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target === tr) { e.preventDefault(); o.alPulsar(r); } });
      }
      return tr;
    }));
    const n = o.filas?.length || 0;
    cuenta.textContent = visibles.length < total ? `${fmt.num(visibles.length)} de ${fmt.num(total)} (de ${fmt.num(n)})` : `${fmt.num(total)} de ${fmt.num(n)}`;
    const quedan = total - visibles.length;
    poner(mas, quedan > 0 ? (o.verTodas
      ? h('button', { type: 'button', class: 'bt', on: { click: () => { estado.paginas = Infinity; pintar(); } } }, `Ver las ${fmt.num(total)} filas`)
      : h('button', { type: 'button', class: 'bt', on: { click: () => { estado.paginas += 1; pintar(); } } },
        `Ver ${fmt.num(Math.min(porPagina, quedan))} más`, h('span', { class: 'sub' }, ` · quedan ${fmt.num(quedan)}`))) : null);
    tabla.hidden = !filas.length;
    poner(hueco, filas.length ? null : estadoVacio(n
      ? { titulo: 'Ningún resultado con estos filtros', porque: 'Quita un filtro o cambia la búsqueda.' }
      : (o.vacio || { titulo: 'No hay nada que enseñar', porque: '' })));
    hueco.hidden = !!filas.length;
  }
  pintar();
  return raiz;
}

//421 · vocabulario compartido: abreviar sin cortar palabras ni ocultar unidades/periodos.
function cabeceraCompacta421(c){
  const nombres={
    'Trafficker':'Traf.','Trafficker (asignaciones)':'Traf. (asig.)','Semáforo':'Estado',
    'Interacciones':'Interac.','Frecuencia':'Frec.','Impresiones':'Impr.',
    'Bloqueadas':'Bloq.','Devueltas':'Dev.','En fecha 30 d':'En fecha 30d','A la primera':'1.ª vez',
    'Reuniones celebradas':'Reu. hechas','Reuniones por confirmar':'Reu. pendientes',
    'Reunión mensual':'Reu. mes','Contacto semanal':'Contacto sem.',
    'Revisión account':'Rev. account','Revisión técnica':'Rev. técnica',
    'Horas imputadas':'H. imput.','Horas presupuestadas':'H. presup.',
    'Horas consumidas':'H. consum.','Horas del mes':'Horas mes',
    'Horas sep. / pautadas':'H. sep. / pauta','Porcentaje imputado':'% imput.',
    'Último registro':'Últ. registro','Último registro encontrado':'Últ. registro',
    'Último día con gasto':'Últ. gasto','Siguiente revisión':'Próx. rev.',
    'Diferencia observada':'Dif. observada','Fuente y lectura':'Fuente / fecha',
    'Tipo de tarea':'Tipo','Mediana del tipo':'Mediana / tipo',
    'Tokens entrada / salida':'Tokens E/S','Respuestas 30 días':'Resp. 30d',
    'WhatsApp 7 días':'WA 7d','WhatsApp fallido':'WA fallido',
    'Correos fallidos':'Email fallido','Número WhatsApp':'N.º WA',
    'Mensaje automático':'Msg. auto.','Automático en < 5 min':'Auto. <5min',
    'Leads sin tocar':'Leads sin gestión','Sin subcuenta emparejada':'Sin subcuenta',
    'Asistencia 14 d':'Asist. 14d','Llamadas semana':'Llam. sem.',
    'Informado al cliente':'Cliente informado','Coste (índice)':'Índ. coste',
    'Clics (índice)':'Índ. clics','Referencia estimada':'Ref. estimada',
    'Comparación / referencias':'Compar. / ref.',
    'Coste registrado · unidad pendiente':'Coste (ref.)',
    'Coste registrado 7 d · unidad pendiente':'Coste 7d (ref.)',
    'Coste registrado sept. · unidad pendiente':'Coste sep. (ref.)',
    //441 · títulos exactos verificados en Personas, altas, sistema, informes y SEO.
    'Registro del último laborable':'Reg. últ. laborable',
    'Semana de la fuente':'Sem. fuente',
    'Días con 0 en la foto (últimos 5)':'Días 0 foto (últ.5)',
    'Revisión de cartera':'Rev. cartera',
    'Configuración básica':'Config. básica',
    'Estado y paso (equipo)':'Estado/paso equipo',
    'Terminada (Madrid)':'Fin (Madrid)',
    'Aceptadas en LinkedIn':'Acept. LinkedIn',
    'Errores al guardar o cargar':'Errores guardar/cargar',
    'Cambio en sesiones':'Δ sesiones',
    'Eventos por sesión':'Eventos/sesión',
    'Resultados Meta · referencia':'Res. Meta (ref.)',
    'Coste por evento lead':'Coste/evento lead',
    'Impresiones sep (web)':'Impr. sep (web)',
    'Impresiones sep (por página)':'Impr. sep/pág.',
    'Consultas org. / Maps':'Cons. org./Maps',
    'Plugins / rendimiento':'Plugins/rend.',
    //457 · vocabulario transversal: mismo indicador, título breve y significado accesible.
    'Especialista':'Espec.',
    'Actualizaciones':'Actualiz.',
    'Respuesta HTML':'Resp. HTML',
    'Objetivo / páginas':'Obj. / pág.',
    'Orgánico · mejor lectura':'Org. · mejor lectura',
    'Maps · observado':'Maps · obs.',
    'Cambio acreditado · 7 d':'Δ acreditado 7d',
    'El lead escribió':'Lead escribió',
    'Clientes +48 h sin respuesta':'Clientes sin resp. +48h',
    'Tareas en revisión +48 h':'Rev. +48h',
    'Nota media de accounts':'Nota media acc.',
    'Semáforos sin rellenar':'Semáf. vacíos',
    'Acciones con rastro (acumulado)':'Acciones acum.'
  };
  const breve=typeof c.titulo==='string'?nombres[c.titulo]:null;
  return breve&&breve.length<c.titulo.length?{...c,titulo:breve,tituloCompleto:c.tituloCompleto||c.titulo}:c;
}

// ------------------------------------------------------------ capas flotantes (V3a)
/**
 * capaFlotante(el, ancla, { derecha, cerrar })
 *   V3a (Tomás, 3-oct: «el desplegable se queda a medias»): TODO desplegable (selectorCliente/selectorPersona, menuElegir,
 *   menuMas, «Más» y botón del periodo, menús «⋯» con <details> de los módulos, menú del avatar) se abre como CAPA por encima
 *   de todo, fuera de cualquier overflow de su tarjeta: capa superior del navegador (popover) y, si no la hay, fixed con
 *   z-index propio. Se coloca según el espacio: debajo del botón o, si no cabe y arriba hay más sitio, encima; nunca se sale
 *   por la derecha ni por la izquierda; altura máxima = el sitio que hay, con scroll dentro (el buscador queda fijo arriba).
 *   A ≤ 640 px es una hoja inferior a todo lo ancho con velo detrás (tocar el velo cierra). Sigue en su sitio del DOM, así
 *   que «pulsar fuera», Esc y el foco de cada componente funcionan igual. Flechas ↑ ↓ (e Inicio/Fin) recorren sus opciones
 *   si el componente no lo hace ya.
 *   No hace falta llamarla: vigilarCapas() (abajo) la aplica sola a .menu-flot, .selcli .pop y #yo-pop en cuanto aparecen.
 *   Un menú que quiera quedarse dentro de su caja (p. ej. un «⋯» desplegado en línea) lleva style position: static.
 */
const CAPA_MARGEN = 8, CAPA_HUECO = 6;
const capaHoja = () => innerWidth <= 640;
export function capaFlotante(el, ancla, { derecha = false, cerrar = null } = {}) {
  if (!el || !el.isConnected || el._capa) return el;
  const popover = typeof el.showPopover === 'function';
  el._capa = true;
  el.classList.add('capa-flot');
  if (popover) { el.setAttribute('popover', 'manual'); try { el.showPopover(); } catch { /* ya abierta o fuera del DOM */ } }
  const colocar = () => {
    if (!el.isConnected) { quitar(); return; }
    const W = document.documentElement.clientWidth || innerWidth, H = innerHeight;
    const hoja = capaHoja();
    el.classList.toggle('hoja', hoja);
    const s = el.style;
    ponerVelo(hoja);
    if (hoja) { Object.assign(s, { left: '0px', right: '0px', top: 'auto', bottom: '0px', width: '100%', maxWidth: '100%', maxHeight: `${Math.round(H * 0.86)}px` }); return; }
    Object.assign(s, { left: '0px', top: '0px', right: 'auto', bottom: 'auto', width: '', maxWidth: `${W - 2 * CAPA_MARGEN}px`, maxHeight: 'none' });
    const r = (ancla && ancla.isConnected ? ancla : el.parentElement || el).getBoundingClientRect();
    const alto = el.scrollHeight;
    const abajo = H - r.bottom - CAPA_HUECO - CAPA_MARGEN, arriba = r.top - CAPA_HUECO - CAPA_MARGEN;
    const subir = alto > abajo && arriba > abajo;
    const tope = Math.max(120, Math.floor(subir ? arriba : abajo));
    s.maxHeight = `${tope}px`;
    const w = Math.min(el.offsetWidth, W - 2 * CAPA_MARGEN), hh = Math.min(el.offsetHeight, tope);
    let x = derecha ? r.right - w : r.left;
    x = Math.max(CAPA_MARGEN, Math.min(x, W - w - CAPA_MARGEN));
    // siempre dentro de la ventana, aunque el botón se haya ido de la vista
    const y = Math.max(CAPA_MARGEN, Math.min(subir ? r.top - CAPA_HUECO - hh : r.bottom + CAPA_HUECO, H - hh - CAPA_MARGEN));
    Object.assign(s, { left: `${Math.round(x)}px`, top: `${Math.round(y)}px` });
    el.classList.toggle('arriba', subir);
  };
  const enTeclas = e => {
    if (e.defaultPrevented || !['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return;
    if (e.target.matches?.('input, textarea, select')) {
      if (e.key !== 'ArrowDown' || e.target.getAttribute('role') === 'combobox') return;   // del buscador a la primera opción
    }
    const ops = [...el.querySelectorAll('[role^="menuitem"], [role="option"]:not([aria-disabled="true"]), :scope > a, :scope > button')].filter(x => x.offsetParent !== null || el.classList.contains('hoja'));
    if (!ops.length) return;
    const i = ops.indexOf(document.activeElement);
    const j = e.key === 'Home' ? 0 : e.key === 'End' ? ops.length - 1 : e.key === 'ArrowDown' ? Math.min(ops.length - 1, i + 1) : Math.max(0, i - 1);
    e.preventDefault(); ops[j]?.focus?.();
  };
  // en la hoja, un velo de verdad debajo (el ::backdrop de un popover deja pasar el toque a lo de debajo): tocarlo cierra
  // como «pulsar fuera» (el toque llega al velo, fuera de la caja del componente) y no pulsa nada de la página.
  let velo = null;
  const ponerVelo = si => {
    if (!si) { velo?.remove(); velo = null; return; }
    if (velo) return;
    velo = h('div', { class: 'capa-velo', 'aria-hidden': 'true', on: { click: () => { if (cerrar) cerrar(); } } });
    document.body.append(velo);
    if (popover) {
      velo.setAttribute('popover', 'manual');
      try {
        velo.showPopover();
        const foco = document.activeElement;
        el.hidePopover(); el.showPopover();          // la hoja, encima del velo
        if (foco && el.contains(foco)) foco.focus({ preventScroll: true });
      } catch { /* sin capa superior: z-index */ }
    }
  };
  // Esc cierra aunque el foco siga en el botón que lo abrió (menús de <details> y del avatar, que no lo hacían)
  const enEsc = e => {
    if (e.key !== 'Escape' || !cerrar || e.defaultPrevented || !el.isConnected) return;
    if (el.contains(e.target) || ancla?.contains?.(e.target) || e.target === document.body) { e.preventDefault(); cerrar(); }
  };
  let pend = 0;
  const pronto = () => { if (!pend) pend = requestAnimationFrame(() => { pend = 0; colocar(); }); };
  const vigia = typeof ResizeObserver === 'function' ? new ResizeObserver(pronto) : null;
  function quitar() {
    removeEventListener('scroll', pronto, true); removeEventListener('resize', pronto);
    el.removeEventListener('keydown', enTeclas); document.removeEventListener('keydown', enEsc, true);
    vigia?.disconnect();
    ponerVelo(false);
    el._capa = false;
  }
  el._capaQuitar = quitar;
  el._capaColocar = colocar;
  addEventListener('scroll', pronto, true); addEventListener('resize', pronto);
  el.addEventListener('keydown', enTeclas); document.addEventListener('keydown', enEsc, true);
  vigia?.observe(el);
  colocar();
  return el;
}

/** Cierra (oculta) una capa sin quitarla del DOM (menús que se esconden en vez de borrarse: <details>, #yo-pop). */
function soltarCapa(el) {
  if (!el?._capa) return;
  try { if (el.matches(':popover-open')) el.hidePopover(); } catch { /* sin popover */ }
  el._capaQuitar?.();
  el.removeAttribute('popover');
  el.classList.remove('capa-flot', 'hoja', 'arriba');
  for (const k of ['left', 'right', 'top', 'bottom', 'width', 'maxWidth', 'maxHeight']) el.style[k] = '';
}

/** El botón que abre un desplegable: el de delante (botón o <summary>) o el primero de su caja. */
function anclaDe(el) {
  const prev = el.previousElementSibling;
  if (prev && prev.matches('button, summary, a, .sel-bt')) return prev;
  return el.parentElement?.querySelector(':scope > button, :scope > summary, :scope > .sel-bt') || el.parentElement;
}
const CAPA_SEL = '.menu-flot, .selcli > .pop, #yo-pop';
function activarCapa(el) {
  if (el._capa || el.style.position === 'static' || el.hidden) return;
  const det = el.parentElement?.closest('details');
  if (det && el.parentElement === det && !det.open) return;
  const derecha = !!el.closest('.menu-mas, .yo-menu') || el.style.right === '0px' || el.style.right === '0';
  let cerrar = null;
  if (det && el.parentElement === det) cerrar = () => { det.open = false; det.querySelector(':scope > summary')?.focus(); };
  if (el.id === 'yo-pop') cerrar = () => { el.hidden = true; document.getElementById('yo-btn')?.setAttribute('aria-expanded', 'false'); document.getElementById('yo-btn')?.focus(); };
  capaFlotante(el, el.id === 'yo-pop' ? document.getElementById('yo-btn') : anclaDe(el), { derecha, cerrar });
}
/** vigilarCapas() · una sola vez (al cargar componentes.js): convierte en capa cualquier desplegable común que aparezca. */
export function vigilarCapas() {
  if (typeof document === 'undefined' || window.__roCapas) return;
  window.__roCapas = true;
  const mirar = n => {
    if (!(n instanceof Element)) return;
    if (n.matches(CAPA_SEL)) activarCapa(n);
    n.querySelectorAll?.(CAPA_SEL).forEach(activarCapa);
  };
  const empezar = () => {
    new MutationObserver(ls => {
      for (const m of ls) {
        if (m.type === 'attributes') {
          const el = m.target;
          if (el.id === 'yo-pop') { if (el.hidden) soltarCapa(el); else activarCapa(el); }
          continue;
        }
        m.addedNodes.forEach(mirar);
        m.removedNodes.forEach(n => {   // un desplegable que el componente quita: fuera su velo y sus escuchas
          if (!(n instanceof Element)) return;
          if (n._capa) n._capaQuitar?.();
          n.querySelectorAll?.('.capa-flot').forEach(x => x._capa && x._capaQuitar?.());
        });
      }
    }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden'] });
    document.addEventListener('toggle', e => {
      const det = e.target;
      if (!(det instanceof HTMLDetailsElement)) return;
      const menu = det.querySelector(':scope > .menu-flot');
      if (!menu) return;
      if (det.open) activarCapa(menu); else soltarCapa(menu);
    }, true);
    document.querySelectorAll(CAPA_SEL).forEach(activarCapa);
  };
  if (document.body) empezar(); else document.addEventListener('DOMContentLoaded', empezar, { once: true });
}
vigilarCapas();

/**
 * menuElegir({ etiqueta, opciones: [{ valor, texto }], valor = '', todos = 'Todos', alCambiar })
 *   Ronda 10 · el filtro común de lista larga (sustituye al <select> nativo): botón «Puesto: Todos ▾» con su menú
 *   flotante (menuitemradio). Con más de 10 opciones lleva buscador. Teclado: ↑ ↓ en la lista, Esc cierra.
 *   el.valor() da el elegido ('' = todos).
 */
export function menuElegir({ etiqueta = 'Filtro', opciones = [], valor = '', todos = 'Todos', alCambiar } = {}) {
  const caja = h('div', { class: 'periodo-mas menu-elegir' });
  let actual = String(valor ?? ''), abierto = false, q = '';
  const texto = () => (actual === '' ? todos : (opciones.find(x => String(x.valor) === actual)?.texto ?? actual));
  const elegir = v => { actual = String(v); abierto = false; q = ''; pintar(); caja.querySelector('button')?.focus(); alCambiar?.(actual); };
  const pintar = () => {
    const btn = h('button', { type: 'button', class: 'bt mini', 'aria-haspopup': 'menu', 'aria-expanded': String(abierto), 'aria-pressed': actual !== '' ? 'true' : null,
      on: { click: e => { e.stopPropagation(); abierto = !abierto; pintar(); } } },
      h('span', { class: 'et' }, `${etiqueta}:`), h('b', {}, texto()), icono('chev', { clase: 's' }));
    if (!abierto) { caja.replaceChildren(btn); return; }
    const visibles = opciones.filter(x => !q || normalTxt(x.texto).includes(normalTxt(q)));
    const item = (v, t) => h('button', { type: 'button', role: 'menuitemradio', 'aria-checked': String(actual === String(v)), on: { click: () => elegir(v) } }, h('span', {}, t));
    const buscador = opciones.length > 10 ? h('input', { type: 'search', class: 'menu-buscar', placeholder: `Buscar ${etiqueta.toLowerCase()}…`, 'aria-label': `Buscar en ${etiqueta}`, value: q,
      on: { input: e => { q = e.target.value; const pos = e.target.selectionStart; pintar(); const i = caja.querySelector('.menu-buscar'); i?.focus(); i?.setSelectionRange(pos, pos); } } }) : null;
    const menu = h('div', { class: 'menu-flot menu-largo', role: 'menu', 'aria-label': etiqueta, on: { keydown: e => {
      if (e.key === 'Escape') { abierto = false; pintar(); caja.querySelector('button')?.focus(); return; }
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
      const bs = [...caja.querySelectorAll('[role=menuitemradio]')]; const i = bs.indexOf(document.activeElement);
      e.preventDefault(); bs[e.key === 'ArrowDown' ? Math.min(bs.length - 1, i + 1) : Math.max(0, i - 1)]?.focus();
    } } }, buscador, item('', todos), visibles.map(x => item(x.valor, x.texto)),
      !visibles.length ? h('span', { class: 'sub menu-nada' }, 'Nada con ese nombre') : null);
    caja.replaceChildren(btn, menu);
    capaFlotante(menu, btn);   // V3a: capa por encima de todo antes de enfocar (así el foco no mueve la página)
    if (!q) (buscador || menu.querySelector('[aria-checked="true"]') || menu.querySelector('button'))?.focus({ preventScroll: true });
  };
  document.addEventListener('click', e => { if (abierto && !caja.contains(e.target)) { abierto = false; q = ''; pintar(); } });
  pintar();
  caja.valor = () => actual;
  return caja;
}

/** poner(el, ...hijos) · Ronda 10 (D-P-DS-FB): como el.replaceChildren pero sin escribir «null» ni «undefined»
 *  (replaceChildren y append convierten null en texto). Úsalo siempre que un hijo pueda faltar. */
export function poner(el, ...hijos) {
  el.replaceChildren(...hijos.flat(Infinity).filter(x => x !== null && x !== undefined && x !== false && x !== '')
    .map(x => (x instanceof Node ? x : document.createTextNode(String(x)))));
  return el;
}

// ---------------------------------------------------------- línea de tiempo
/** lineaTiempo([{ fecha, titulo, detalle, estado }]) · de más reciente a más antiguo. */
export function lineaTiempo(eventos) {
  if (!eventos.length) return estadoVacio({ titulo: 'Sin historia todavía', porque: 'Aquí aparecerá cada hito o aviso con su fecha.' });
  return h('ol', { class: 'tiempo' }, eventos.map(e =>
    h('li', { class: e.estado || '' },
      h('div', { class: 'f' }, fmt.fecha(e.fecha)),
      h('div', { class: 't' }, e.titulo),
      e.detalle ? h('div', { class: 'd' }, e.detalle) : null)));
}

// ---------------------------------------------------------- gráfico de serie
/**
 * graficoSerie({ puntos: [{x: '2026-10-01', y: 12}], titulo, umbral?: {y, texto}, alto: 140, formato: n => '' })
 * Línea + área en SVG, sin librerías. Con menos de 2 puntos enseña un estado vacío útil.
 * Patrón C5: longitud y posición; nada de tartas ni relojes.
 */
export function graficoSerie(o) {
  // Ronda 9: usa el motor único grafico() (letra de 12 px, marcas redondas, burbuja). Misma firma que antes.
  const pts = (o.puntos || []).filter(p => p.y !== null && p.y !== undefined);
  if (pts.length < 2) {
    const caja = h('figure', { class: 'serie', style: { margin: 0 } });
    if (o.titulo) caja.append(h('figcaption', { class: 'sub' }, o.titulo));
    caja.append(estadoVacio({ titulo: pts.length ? `Solo hay ${pts.length} día de histórico` : 'Sin histórico todavía', porque: 'La serie se llena sola: cada recarga guarda un punto. Vuelve en unos días.' }));
    return caja;
  }
  return grafico({ titulo: o.titulo, x: pts.map(p => p.x), series: [{ nombre: o.nombre || '', y: pts.map(p => p.y) }], formato: o.formato, umbral: o.umbral, alto: o.alto || 160 });
}
// ------------------------------------------------------- gráfico único (ronda 9)
/**
 * grafico({ x, series, barras, tipo, alto, formato, formatoX, umbral, titulo, unidad, leyenda, etiquetaUltimo })
 *   EL motor de gráficos de la app (auditoría 30, §3.9). Mide su caja y dibuja en píxeles reales, así la letra de los
 *   ejes es SIEMPRE de 12 px (a 1280 y a 2560), con marcas en valores redondos (0 · 25.000 · 50.000), 4-6 fechas en
 *   el eje X, etiquetas que no se pisan y una burbuja con el valor exacto al pasar el ratón.
 *   x: ['AAAA-MM-DD' | texto…]   series: [{ nombre, y: [n…], color?, ant?: true (periodo anterior, discontinua) }]
 *   barras: { nombre, y: [n…], escalaPropia?: true } (negativas en rojo)   tipo: 'linea' (defecto) | 'barras'
 *   umbral: { y, texto }   formato: n → texto del eje Y y de la burbuja (defecto fmt.num)   alto: 200 (240 informe, 120 tarjeta)
 *   Sin datos: una línea de 40 px («Sin datos en este periodo»), no un estado vacío grande.
 *   Finanzas v3 (opcionales): barras.clase(i, v) → 'pos' | 'est' | '' · barras.leyenda: [{ nombre, clase }] · barras.nombreDe(i, v)
 *   · barras2 (otra tanda en el mismo hueco: altas arriba, bajas abajo) · serie.escalaPropia + serie.formato (eje a la derecha)
 *   · detalle(i) → [texto…] (líneas extra en la burbuja) · barrasPrimero (las barras encabezan la burbuja).
 */
const COLORES_SERIE = ['var(--accent)', 'var(--serie-2)', 'var(--serie-3)', 'var(--serie-4)'];
/** marcasRedondas(min, max, n=5) → { min, max, paso, marcas } con valores «bonitos» (1, 2, 2,5, 5 × 10^k). */
export function marcasRedondas(min, max, n = 5) {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return { min: 0, max: 1, paso: 1, marcas: [0, 1] };
  if (min === max) { if (max === 0) max = 1; else if (max > 0) min = 0; else max = 0; }
  const bonito = (v, redondear) => {
    const e = Math.floor(Math.log10(v)); const f = v / 10 ** e;
    const nf = redondear ? (f < 1.5 ? 1 : f < 2.25 ? 2 : f < 3.5 ? 2.5 : f < 7.5 ? 5 : 10) : (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10);
    return nf * 10 ** e;
  };
  const paso = bonito(bonito(max - min, false) / Math.max(1, n - 1), true);
  const a = Math.floor(min / paso) * paso, b = Math.ceil(max / paso) * paso;
  const marcas = []; for (let v = a; v <= b + paso / 2; v += paso) marcas.push(Math.round(v / paso) * paso);
  return { min: a, max: b, paso, marcas };
}
const _MESES_EJE = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _etiquetaX = x => {
  const m = /^(\d{4})-(\d{2})(?:-(\d{2}))?$/.exec(String(x || ''));
  if (!m) return String(x ?? '');
  return m[3] ? `${Number(m[3])} ${_MESES_EJE[Number(m[2]) - 1]}` : _MESES_EJE[Number(m[2]) - 1];
};
export function grafico(o = {}) {
  const x = o.x || [];
  const series = (o.series || []).filter(sr => sr && Array.isArray(sr.y)).slice(0, 4);
  const barras = o.barras && Array.isArray(o.barras.y) ? o.barras : (o.tipo === 'barras' && series[0] ? { ...series.shift() } : null);
  // Finanzas v3 (3-oct): barras2 = segunda tanda de barras en el MISMO hueco y la misma escala (altas hacia arriba, bajas
  // hacia abajo). barras.clase(i, v) / barras2.clase(i, v) → 'pos' (verde) | 'est' (gris, estimado) | '' (por defecto).
  // Una serie con escalaPropia: true lleva su propio eje a la derecha (el margen % sobre barras en euros). detalle(i) añade
  // líneas a la burbuja (el desglose del mes). Todo opcional: las llamadas de antes no cambian.
  const barras2 = barras && o.barras2 && Array.isArray(o.barras2.y) ? o.barras2 : null;
  const propias = series.filter(sr => sr.escalaPropia);
  const caja = h('figure', { class: 'grafico', style: { margin: 0 } });
  if (o.titulo) caja.append(h('figcaption', { class: 'grafico-tit' }, o.titulo));
  const valores = [...series.filter(sr => !sr.escalaPropia).flatMap(sr => sr.y), ...(barras && !barras.escalaPropia ? barras.y : []), ...(barras2 ? barras2.y : [])].filter(v => typeof v === 'number' && Number.isFinite(v));
  const hayBarras = barras && barras.y.some(v => typeof v === 'number' && v !== 0);
  if (!x.length || (!valores.some(v => v !== 0) && !hayBarras)) {
    caja.append(h('p', { class: 'grafico-vacio' }, icono('grafico', { clase: 's' }), o.vacio || 'Sin datos en este periodo'));
    return caja;
  }
  const f = o.formato || (n => fmt.num(n));
  const fx = o.formatoX || _etiquetaX;
  const ALTO = o.alto || 200;
  const leyBarras = b => (b.leyenda ? b.leyenda.map(l => ({ nombre: l.nombre, barra: true, clase: l.clase })) : [{ nombre: b.nombre, color: b.color || 'var(--serie-barra)', barra: true }]);
  const leyendaItems = [...series.map((sr, i) => ({ nombre: sr.nombre, color: sr.color || (sr.ant ? 'var(--off)' : COLORES_SERIE[i]), ant: sr.ant })),
    ...(barras ? leyBarras(barras) : []), ...(barras2 ? leyBarras(barras2) : [])].filter(l => l.nombre);
  if (leyendaItems.length > 1 || (o.leyenda && leyendaItems.length)) {
    caja.append(h('div', { class: 'grafico-ley' }, leyendaItems.map(l => h('span', {}, h('i', { class: l.barra ? `b${l.clase ? ' ' + l.clase : ''}` : l.ant ? 'a' : '', style: l.clase ? null : { background: l.ant ? 'none' : l.color, borderColor: l.color } }), l.nombre))));
  }
  const lienzo = h('div', { class: 'grafico-lienzo', style: { height: `${ALTO}px` } });
  const burbuja = h('div', { class: 'grafico-burbuja', hidden: true, role: 'status' });
  lienzo.append(burbuja);
  caja.append(lienzo);
  const etiquetaAria = `${o.titulo || 'Gráfico'}: ${x.length} puntos, de ${fx(x[0])} a ${fx(x.at(-1))}`;

  const dibujar = W => {
    lienzo.querySelector('svg')?.remove();
    if (!W || W < 60) return;
    const H = ALTO;
    const ysTodo = [...valores, ...(o.umbral && Number.isFinite(o.umbral.y) ? [o.umbral.y] : [])];
    const esc = marcasRedondas(Math.min(0, ...ysTodo), Math.max(0, ...ysTodo), H >= 160 ? 5 : 3);
    const anchoEtiq = Math.max(...esc.marcas.map(v => String(f(v)).length)) * 7.2 + 8;
    // eje propio a la derecha para las series con escalaPropia (margen %)
    const vp = propias.flatMap(sr => sr.y).filter(v => typeof v === 'number' && Number.isFinite(v));
    const esc2 = vp.length ? marcasRedondas(Math.min(0, ...vp), Math.max(0, ...vp), H >= 160 ? 5 : 3) : null;
    const f2 = propias[0]?.formato || f;
    const ancho2 = esc2 ? Math.max(...esc2.marcas.map(v => String(f2(v)).length)) * 7.2 + 10 : 0;
    const pl = Math.min(96, Math.max(28, anchoEtiq)), pr = esc2 ? Math.min(72, Math.max(28, ancho2)) : o.etiquetaUltimo === false ? 8 : 12, pt = 12, pb = 24;
    const n = x.length;
    const slot = (W - pl - pr) / Math.max(1, barras ? n : n - 1);
    const X = i => (barras ? pl + slot * (i + 0.5) : pl + (n === 1 ? (W - pl - pr) / 2 : i * slot));
    const Y = v => pt + (H - pt - pb) * (1 - (v - esc.min) / (esc.max - esc.min || 1));
    const Y2 = v => pt + (H - pt - pb) * (1 - (v - esc2.min) / (esc2.max - esc2.min || 1));
    const svg = s('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': etiquetaAria });
    // rejilla horizontal y eje Y (marcas redondas; si dos etiquetas quedan a < 16 px, se quita la de menos peso)
    let ultimaY = Infinity;
    for (const v of esc.marcas) {
      const y = Y(v);
      svg.append(s('line', { class: v === 0 ? 'cero' : 'rejilla-l', x1: pl, x2: W - pr, y1: y, y2: y }));
      if (Math.abs(ultimaY - y) < 16 && v !== 0) continue;
      const t = s('text', { x: pl - 8, y: y + 4, 'text-anchor': 'end' }); t.textContent = f(v); svg.append(t); ultimaY = y;
    }
    if (esc2) {
      let ult2 = Infinity;
      for (const v of esc2.marcas) {
        const y = Y2(v); if (Math.abs(ult2 - y) < 16) continue;
        const t = s('text', { class: 'eje-der', x: W - pr + 6, y: y + 4, 'text-anchor': 'start' }); t.textContent = f2(v); svg.append(t); ult2 = y;
      }
    }
    // eje X: 4-6 etiquetas como mucho, sin pisarse
    const maxEtiq = Math.max(2, Math.min(6, Math.floor((W - pl - pr) / 64)));
    const pasoX = Math.max(1, Math.ceil((n - 1) / (maxEtiq - 1)));
    const idx = []; for (let i = 0; i < n; i += pasoX) idx.push(i);
    // Ronda 10 (N6): la última fecha va pegada a la derecha («end») y la anterior centrada: se mide el ancho de las dos
    // etiquetas (≈ 7 px por letra a 12 px) y, si no caben con 8 px de aire, se quita la anterior.
    const anchoTxt = i => String(fx(x[i])).length * 7 + 2;
    const caben = (a, b) => {
      const ocupa = barras ? anchoTxt(a) / 2 + anchoTxt(b) / 2 : (a === 0 ? anchoTxt(a) : anchoTxt(a) / 2) + (b === n - 1 ? anchoTxt(b) : anchoTxt(b) / 2);
      return Math.abs(X(b) - X(a)) >= ocupa + 8;
    };
    if (n > 1 && idx.at(-1) !== n - 1) idx.push(n - 1);
    while (idx.length > 2 && !caben(idx.at(-2), idx.at(-1))) idx.splice(-2, 1);
    for (let k = idx.length - 2; k > 0; k--) if (!caben(idx[k - 1], idx[k])) idx.splice(k, 1);
    for (const i of idx) {
      let anchor = barras ? 'middle' : i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle';
      let xi = X(i);
      // 44 · I9 (3-oct): con barras, la primera y la última etiqueta centradas se salían del dibujo («29 se»): se pegan al borde
      if (barras && xi + anchoTxt(i) / 2 > W - 2) { anchor = 'end'; xi = W - 2; }
      if (barras && xi - anchoTxt(i) / 2 < 2) { anchor = 'start'; xi = 2; }
      const t = s('text', { x: xi, y: H - 6, 'text-anchor': anchor }); t.textContent = fx(x[i]); svg.append(t);
    }
    // barras (escala propia: se dibujan a su altura relativa, sin eje)
    for (const b of [barras, barras2].filter(Boolean)) {
      const bmax = Math.max(1, ...b.y.map(v => Math.abs(v || 0)));
      const anchoB = Math.max(2, slot * 0.6);
      b.y.forEach((v, i) => {
        if (typeof v !== 'number' || !v) return;
        const y0 = b.escalaPropia ? H - pb : Y(0);
        const y1 = b.escalaPropia ? H - pb - (H - pt - pb) * (Math.abs(v) / bmax) * 0.9 : Y(v);
        const top = Math.min(y0, y1), alto = Math.max(1, Math.abs(y1 - y0));
        const extra = b.clase ? b.clase(i, v) : '';
        svg.append(s('rect', { class: `barra${extra ? ' ' + extra : v < 0 ? ' neg' : ''}`, x: X(i) - anchoB / 2, y: top, width: anchoB, height: alto, rx: Math.min(3, anchoB / 3), style: b.color && v >= 0 && !extra ? `fill:${b.color}` : null }));
      });
    }
    // umbral
    if (o.umbral && Number.isFinite(o.umbral.y)) {
      const y = Y(o.umbral.y);
      svg.append(s('line', { class: 'umbral-l', x1: pl, x2: W - pr, y1: y, y2: y }));
      if (o.umbral.texto) {
        // 44 · I9: si el valor final de la primera línea cae a menos de 18 px del umbral, el texto del umbral va a la izquierda
        const s0 = series.find(sr => !sr.ant && !sr.escalaPropia);
        const ult = s0 ? [...s0.y].reverse().find(v => typeof v === 'number' && Number.isFinite(v)) : undefined;
        const choca = ult !== undefined && o.etiquetaUltimo !== false && Math.abs(Y(ult) - y) < 18;
        const t = s('text', { class: 'umbral-t', x: choca ? pl + 4 : W - pr, y: y - 6, 'text-anchor': choca ? 'start' : 'end' }); t.textContent = o.umbral.texto; svg.append(t);
      }
    }
    // líneas
    series.forEach((sr, k) => {
      const color = sr.color || (sr.ant ? 'var(--off)' : COLORES_SERIE[k]);
      let d = '', abierto = false;
      const Ys = sr.escalaPropia && esc2 ? Y2 : Y;
      sr.y.forEach((v, i) => {
        if (typeof v !== 'number' || !Number.isFinite(v)) { abierto = false; return; }
        d += `${abierto ? 'L' : 'M'}${X(i).toFixed(1)},${Ys(v).toFixed(1)}`; abierto = true;
      });
      if (!d) return;
      svg.append(s('path', { class: `linea${sr.ant ? ' ant' : ''}`, d, style: `stroke:${color}` }));
      if (!sr.ant && k === 0 && o.etiquetaUltimo !== false) {
        let u = sr.y.length - 1; while (u >= 0 && !(typeof sr.y[u] === 'number')) u--;
        if (u >= 0) {
          svg.append(s('circle', { class: 'punto', cx: X(u), cy: Y(sr.y[u]), r: 4, style: `stroke:${color}` }));
          const t = s('text', { class: 'valor-ult', x: X(u) - 6, y: Y(sr.y[u]) - 8, 'text-anchor': 'end' }); t.textContent = f(sr.y[u]); svg.append(t);
        }
      }
    });
    // burbuja al pasar el ratón
    const guia = s('line', { class: 'guia', x1: 0, x2: 0, y1: pt, y2: H - pb, visibility: 'hidden' });
    svg.append(guia);
    const zona = s('rect', { x: pl, y: 0, width: Math.max(1, W - pl - pr), height: H, fill: 'transparent' });
    const mostrar = ev => {
      const r = svg.getBoundingClientRect();
      const px = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
      const i = Math.max(0, Math.min(n - 1, Math.round(barras ? (px - pl) / slot - 0.5 : (px - pl) / (slot || 1))));
      guia.setAttribute('x1', X(i)); guia.setAttribute('x2', X(i)); guia.setAttribute('visibility', 'visible');
      const linB = b => h('span', {}, h('i', { class: `b${b.clase ? ' ' + (b.clase(i, b.y[i]) || '') : ''}`.trim() }), `${(b.nombreDe ? b.nombreDe(i, b.y[i]) : b.nombre) ? (b.nombreDe ? b.nombreDe(i, b.y[i]) : b.nombre) + ': ' : ''}${typeof b.y[i] === 'number' ? (b.formato || f)(b.y[i]) : '—'}`);
      const linS = series.map((sr, k) => h('span', {}, h('i', { style: { background: sr.color || (sr.ant ? 'var(--off)' : COLORES_SERIE[k]) } }), `${sr.nombre ? sr.nombre + ': ' : ''}${typeof sr.y[i] === 'number' ? (sr.formato || f)(sr.y[i]) : '—'}`));
      const linBs = [...(barras ? [linB(barras)] : []), ...(barras2 ? [linB(barras2)] : [])];
      burbuja.replaceChildren(h('b', {}, fx(x[i])), ...(o.barrasPrimero ? [...linBs, ...linS] : [...linS, ...linBs]),
        ...(o.detalle ? (o.detalle(i) || []).map(t => h('span', { class: 'sub' }, t)) : []));
      burbuja.hidden = false;
      const bx = Math.min(Math.max(8, X(i) + 12), W - burbuja.offsetWidth - 8);
      burbuja.style.left = `${X(i) + 12 + burbuja.offsetWidth > W - 8 ? Math.max(8, X(i) - burbuja.offsetWidth - 12) : bx}px`;
    };
    const ocultar = () => { guia.setAttribute('visibility', 'hidden'); burbuja.hidden = true; };
    zona.addEventListener('mousemove', mostrar); zona.addEventListener('touchstart', mostrar, { passive: true });
    zona.addEventListener('mouseleave', ocultar);
    svg.append(zona);
    lienzo.prepend(svg);
  };
  let ultimoW = 0;
  if (typeof ResizeObserver === 'function') {
    new ResizeObserver(ent => { const W = Math.round(ent[0].contentRect.width); if (W && W !== ultimoW) { ultimoW = W; dibujar(W); } }).observe(lienzo);
  } else requestAnimationFrame(() => dibujar(lienzo.clientWidth || 600));
  return caja;
}

// --------------------------------------------- color de una cifra (regla única)
/**
 * colorCifra(tipo, valor, contexto?) → 'verde' | 'ambar' | 'rojo' | 'gris'
 *   LA regla de color por cifra (auditoría 30, §3.4): el mismo número no puede ser verde en una pantalla y rojo en otra.
 *   Ningún módulo calcula verde/rojo de estas cifras por su cuenta: llama a colorCifra() y pasa el estado a tile().
 */
export const REGLAS_COLOR = {
  /** Beneficio del mes: positivo = verde, pérdidas = rojo (orden de 2-oct: «beneficio positivo verde en todas partes»). */
  beneficio: v => (v > 0 ? 'verde' : v < 0 ? 'rojo' : 'gris'),
  /** Margen sobre ingresos: igual que el beneficio (lo que cuenta es si se gana dinero). */
  margen: v => (v > 0 ? 'verde' : v < 0 ? 'rojo' : 'gris'),
  /** Coste por cliente firmado: umbral firmado 700 €; la banda ámbar (hasta 840 €, +20 %) es propuesta sin firmar. */
  coste_cliente: v => semaforo(v, { verde: 700, ambar: 840, mejorSi: 'bajo' }),
  /** Coste por lead en Meta: techo de la casa 35 €/lead (D-P-CAP5: sin tiendas online como Kiosko). */
  coste_lead: v => semaforo(v, { verde: 35, ambar: 45, mejorSi: 'bajo' }),
  /** Diferencia (delta) de dinero: subir es bueno salvo que se diga lo contrario. */
  delta: (v, { mejorSi = 'alto' } = {}) => (!v ? 'gris' : (v > 0) === (mejorSi !== 'bajo') ? 'verde' : 'rojo'),
};
export function colorCifra(tipo, valor, contexto) {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return 'gris';
  const r = REGLAS_COLOR[tipo];
  return r ? r(Number(valor), contexto || {}) : 'gris';
}

// ------------------------------------------------------------ estado vacío
/**
 * estadoVacio({ titulo, porque, que_hacer, accion?: Node, celebrar?: bool })
 * Patrón C9: dice POR QUÉ está vacío y QUÉ hacer; celebra cuando es buena noticia.
 */
/** «Lo arregla: Claude (regenerar con fuentes_x.py)» no es para el equipo: se queda el nombre de la persona, o nada. */
function quienHumano(q) {
  if (!q || typeof q !== 'string') return q;
  if (NOMBRE_DEPARTAMENTO[q]) return NOMBRE_DEPARTAMENTO[q];
  if (/claude|\.py\b|\.json\b|regenerar|E\d\b/i.test(q)) {
    const limpio = q.replace(/\(.*?\)/g, '').replace(/\b(Claude|E\d+)\b/gi, '').trim();
    return limpio && !/\.py|\.json/i.test(limpio) ? limpio : 'el equipo técnico';
  }
  return q;
}

export function estadoVacio({ titulo, porque, que_hacer, accion, celebrar = false, icono: ico, quien, tecnico }) {
  return h('div', { class: `vacio${celebrar ? ' celebrar' : ''}`, role: 'status' },
    h('span', { class: 'ico', 'aria-hidden': 'true' }, icono(ico || (celebrar ? 'ok' : 'info'))),
    h('h3', {}, titulo),
    porque ? h('p', {}, typeof porque === 'string' ? (limpiaTexto(porque) || 'Todavía no hay datos de hoy.') : porque) : null,
    que_hacer ? h('p', {}, h('b', {}, 'Qué hacer: '), typeof que_hacer === 'string' ? limpiaTexto(que_hacer) : que_hacer) : null,
    quienHumano(quien) ? h('span', { class: 'quien' }, icono('persona', { clase: 's' }), `Lo arregla: ${quienHumano(quien)}`) : null,
    accion || null,
    tecnico && VISTA.direccion ? h('details', { class: 'que-es' }, h('summary', {}, 'Detalle técnico'), h('p', { class: 'sub' }, tecnico)) : null);
}

// ------------------------------------------------- botón con confirmación
/**
 * botonConfirmar({ texto, pregunta, confirmar: 'Sí, marcar', cancelar: 'No',
 *                  alConfirmar: async () => 'mensaje de hecho', peligro, mini, soloLectura })
 * Primer clic: muestra la pregunta en la propia página con «Sí / No» (foco en «No»).
 * Esc o «No» vuelven atrás. Si soloLectura (ver como), queda desactivado con el motivo.
 * Cada escritura real debe registrarse en el rastro (en producción, en el servidor).
 */
export function botonConfirmar(o) {
  const caja = h('span', { class: 'confirmar' });
  const clsBase = `bt${o.mini ? ' mini' : ''}${o.peligro ? ' peligro' : ''}`;
  const inicial = () => {
    const b = h('button', { type: 'button', class: clsBase, 'aria-disabled': o.soloLectura ? 'true' : null,
      title: o.soloLectura ? 'Estás en «ver como»: solo lectura' : null,
      on: { click: () => { if (!o.soloLectura) preguntar(); } } }, o.texto);
    caja.replaceChildren(b);
    return b;
  };
  const preguntar = () => {
    const no = h('button', { type: 'button', class: `bt${o.mini ? ' mini' : ''}`, on: { click: () => inicial().focus() } }, o.cancelar || 'No');
    const si = h('button', { type: 'button', class: `${clsBase} pri`, on: { click: async () => {
      si.disabled = true; no.disabled = true;
      try {
        const msg = await o.alConfirmar?.();
        caja.replaceChildren(h('span', { class: 'estado', role: 'status' }, '✓ ' + (msg || 'Hecho')));
      } catch (err) {
        caja.replaceChildren(h('span', { class: 'estado error', role: 'alert' }, 'No se pudo: ' + (err?.message || err)));
      }
    } } }, o.confirmar || 'Sí');
    caja.replaceChildren(h('span', { class: 'preg' }, o.pregunta || '¿Seguro?'), si, no);
    caja.addEventListener('keydown', e => { if (e.key === 'Escape') { e.stopPropagation(); inicial().focus(); } }, { once: true });
    no.focus();
  };
  inicial();
  return caja;
}

/** candado(texto) · marca en línea un dato que este puesto no ve (sin enseñar el dato). */
export function candado(texto = 'No visible para tu puesto') {
  return h('span', { class: 'candado' }, texto);
}

/** panel({ titulo, sub, acciones, id, icono }, ...cuerpo) · caja estándar con cabecera (icono opcional en azul). */
export function panel({ titulo, sub, acciones, id, icono: ico, pie, verTodo }, ...cuerpo) {
  // Ronda 9 (D-P-MID2): pie común opcional. verTodo: { texto = 'Ver todo', href } → enlace a la derecha; pie: nodo libre a la izquierda.
  const pieEl = pie || verTodo ? h('footer', { class: 'panel-pie' }, pie || h('span'),
    verTodo ? h('a', { class: 'bt', href: verTodo.href }, verTodo.texto || 'Ver todo', icono('derecha', { clase: 's' })) : null) : null;
  return h('section', { class: 'panel', 'aria-labelledby': id || null },
    titulo ? h('header', {}, h('div', {}, h('h2', { id: id || null }, ico ? icono(ico) : null, titulo), sub ? h('p', { class: 'sub' }, typeof sub === 'string' ? limpiaTexto(sub) : sub) : null), acciones || null) : null,
    cuerpo, pieEl);
}

/**
 * plegadoMovil(seccion, { titulo, resumen, ancho = 640 }) · V2-E (40_A M17: páginas de 10.000-14.000 px en el móvil).
 *   Envuelve una sección SECUNDARIA (histórico, tablas largas, desgloses): en el móvil sale plegada como una fila con su
 *   título y una línea de resumen («12 meses · el peor, agosto»), y se abre con un toque; en pantalla ancha sale tal cual,
 *   abierta y sin la fila. Sin «resumen», usa el subtítulo del panel. Lo que pide acción (Lo primero, el número que manda,
 *   impagos…) NUNCA se pliega. Devuelve la sección envuelta; null/'' pasan tal cual.
 */
export function plegadoMovil(seccion, { titulo, resumen, ancho = 640 } = {}) {
  if (!seccion || typeof seccion !== 'object') return seccion;
  const t = titulo || seccion.querySelector?.('h2, h3')?.textContent?.trim() || 'Más detalle';
  const r = resumen ?? seccion.querySelector?.(':scope > header .sub, .sub')?.textContent?.trim() ?? '';
  let movil = false;
  try { movil = matchMedia(`(max-width: ${ancho}px)`).matches; } catch { /* sin matchMedia: abierto */ }
  const d = h('details', { class: 'pleg-movil' },
    h('summary', {}, h('span', { class: 'pm-t' }, t), r ? h('span', { class: 'pm-r' }, limpiaTexto(r)) : null), seccion);
  if (!movil) d.open = true;
  return d;
}

/**
 * plegarSecundarias(raiz, { desde = 2, titulos, ancho = 640 }) · V2-E (M17) · llama a plegadoMovil() sobre los paneles de
 *   «raiz» que NO piden acción: a partir del n.º «desde» (los primeros se quedan abiertos), o solo los que casan con
 *   «titulos» (RegExp sobre el título). Solo actúa en el móvil: en ancho no toca nada. Llamarlo al final del pintado (y en
 *   cada pestaña que se pinte después). No pliega paneles dentro de otro panel ni los ya plegados.
 */
export function plegarSecundarias(raiz, { desde = 2, titulos = null, ancho = 640 } = {}) {
  if (!raiz?.querySelectorAll) return raiz;
  try { if (!matchMedia(`(max-width: ${ancho}px)`).matches) return raiz; } catch { return raiz; }
  const paneles = [...raiz.querySelectorAll('section.panel')].filter(p => !p.parentElement?.closest('section.panel, .pleg-movil'));
  const elegidos = titulos ? paneles.filter(p => titulos.test(p.querySelector('h2, h3')?.textContent || '')) : paneles.slice(desde);
  for (const p of elegidos) { const sitio = p.parentNode, sig = p.nextSibling; const d = plegadoMovil(p, { ancho }); sitio?.insertBefore(d, sig); }
  return raiz;
}

/** cifraPrincipal({ etiqueta, valor, unidad, estado, comparacion }) · ronda 9 (D-P-MID2): LA cifra que manda de una pantalla,
 *  a 32 px (--t-display). Una por pantalla. estado: 'verde' | 'ambar' | 'rojo' | 'gris' (usa colorCifra() para decidirlo). */
export function cifraPrincipal({ etiqueta, valor, unidad, estado = '', comparacion } = {}) {
  return h('div', { class: `cifra-principal ${estado}`.trim() },
    etiqueta ? h('span', { class: 'cifra-et' }, etiqueta) : null,
    h('span', { class: 'cifra-display' }, valor ?? '—', unidad ? h('small', {}, unidad) : null),
    comparacion ? h('span', { class: 'cifra-comp' }, comparacion) : null);
}

/** vacioLinea(texto, { icono = 'info', quien }) · ronda 9 (D-P-MID2, guía 3.10): vacío DENTRO de un bloque, en una línea
 *  (icono 16 + frase 13 + quién lo arregla). El grande (vacio / estadoVacio) solo cuando toda la pantalla está vacía. */
export function vacioLinea(texto, { icono: ico = 'info', quien, que_hacer } = {}) {
  // N12: que_hacer = el paso («Meta caído desde 21:05 · lo revisa Agus · mientras, cifras de las 18:05»). Si falta, la
  // carcasa lo añade sola cuando el texto nombra una fuente caída (ia_componentes.js › enriquecerErrores).
  return h('p', { class: 'vacio-linea', role: 'status', 'data-qh': que_hacer ? '1' : null }, icono(ico, { clase: 's' }), h('span', {}, typeof texto === 'string' ? limpiaTexto(texto) : texto),
    quienHumano(quien) ? h('small', {}, `Lo arregla: ${quienHumano(quien)}`) : null,
    que_hacer ? h('small', { class: 'que-hacer' }, `Qué hacer: ${typeof que_hacer === 'string' ? limpiaTexto(que_hacer) : que_hacer?.texto || ''}`) : null);
}

// ------------------------------------------------ indicador del catálogo (E0)
/**
 * fichaCatalogo(ind, { valor, unidad, estado, tendencia, frescura, prueba, parcial })
 *   ind = ctx.indicador('<id>') (fila de indicadores.json). Pone el nombre, el umbral firmado y el sello
 *   de medición del catálogo, y debajo «¿Qué es?» con la fórmula, el umbral, su origen, la fuente y la frecuencia.
 *   Regla R5: si el catálogo dice «todavía no», NO pinta número: devuelve una ficha «va a Fase 2».
 *   `parcial`: frase de dato parcial («con el 52 % de horas imputadas, orientativo»).
 * Si ind es null (no está en el catálogo o no es de su puesto), pinta la ficha sin «¿Qué es?» y avisa.
 */
// V2-E (39b, defecto 3): el «¿Qué es?» del catálogo lo ve todo el equipo. Fuera los códigos de obra (D-58, C-G1-15,
// SOP-TR-02, «07 §1», «FIN §4.6», mc.py) y los enlaces Markdown pasan a enlaces de verdad con texto corto (nada de URL larga
// que ensanche la tarjeta). Lo de entre «» no se toca.
const RE_MD = /\[([^\]]+)\]\((https?:[^)\s]+)\)|(https?:\/\/[^\s)»]+)/g;
function limpiaCatalogo(t) {
  return String(t).split(/(«[^»]*»)/).map(x => (x.startsWith('«') ? x : x
    .replace(/\b[\w./-]+\.(?:json|py|md|js|csv|xlsx|sql)\b/g, '')
    .replace(/\b[A-Z]{1,5}(?:-[A-Z0-9]{1,6})+\b(?:\s+[A-Z]\d{1,2}\b)?/g, '')
    .replace(/\b(?:\d{2}|[A-Z]{2,6})\s*§\s*[\d.]+/g, '')
    .replace(/,?\s*líneas?\s+\d+(?:-\d+)?/g, '')
    .replace(/,?\s*§\s*[\d.]+/g, '')
    .replace(/\s*\(\d\d:[A-Z]{0,2}\d\d\.\d{3}\)|,?\s*\b\d\d:[A-Z]{0,2}\d\d\.\d{3}\b/g, '')
  )).join('')
    .replace(/\(\s*[,;:·]?\s*\)/g, '').replace(/\(\s+/g, '(').replace(/\(:\s*/g, '(').replace(/\(\s*[,;·]\s*/g, '(').replace(/\s*[,;·]\s*\)/g, ')')
    .replace(/(\s*·\s*){2,}/g, ' · ').replace(/\s+([,.;)])/g, '$1').replace(/\s{2,}/g, ' ')
    .trim().replace(/^[\s·,;:]+|[\s·,;:]+$/g, '')
    .replace(/^\(([^()]*)\)/, (_, d) => d.charAt(0).toUpperCase() + d.slice(1)) || '—';
}
function textoCatalogo(t) {
  if (t === null || t === undefined || t === '') return '—';
  const s = String(t), out = [];
  let i = 0;
  for (const m of s.matchAll(RE_MD)) {
    if (m.index > i) out.push(limpiaCatalogo(s.slice(i, m.index)));
    const url = m[2] || m[3];
    let txt = m[1] ? m[1].replace(/\s*↗\s*$/, '') : '';
    if (!txt) { try { txt = new URL(url).hostname.replace(/^www\./, ''); } catch { txt = 'enlace'; } }
    out.push(' ', h('a', { href: urlSegura(url), target: '_blank', rel: 'noopener noreferrer' }, `${txt} ↗`), ' ');
    i = m.index + m[0].length;
  }
  if (i < s.length) out.push(limpiaCatalogo(s.slice(i)));
  const limpio = out.filter(x => x !== '—' || out.length === 1);
  return limpio.length ? limpio : '—';
}

export function fichaCatalogo(ind, o = {}) {
  if (!ind) {
    return h('div', { class: 'ind-cat' }, fichaIndicador({ ...o, titulo: o.titulo || 'Indicador', medible: o.medible || 'medias', medibleDetalle: 'No está en el catálogo de indicadores' }));
  }
  const queEs = h('details', { class: 'que-es' },
    h('summary', {}, '¿Qué es?'),
    h('dl', {},
      h('dt', {}, 'Qué mide'), h('dd', {}, textoCatalogo(ind.formula)),
      h('dt', {}, 'Verde / ámbar / rojo'), h('dd', {}, textoCatalogo(ind.umbral)),
      h('dt', {}, 'De dónde sale el umbral'), h('dd', {}, textoCatalogo(ind.umbral_origen)),
      ind.regla_firmada ? [h('dt', {}, 'Regla firmada'), h('dd', {}, textoCatalogo(ind.regla_firmada))] : null,
      h('dt', {}, 'Fuente y frecuencia'), h('dd', {}, textoCatalogo(ind.fuente), ` · ${ind.frecuencia || '—'}`),
      h('dt', {}, '¿Se mide hoy?'), h('dd', {}, textoCatalogo(ind.medible_texto)),
      // Ronda 12 (R13): indicador de varias partes (leads, citas, ventas, objetivo) → «¿se mide hoy?» de cada una
      Array.isArray(ind.partes) && ind.partes.length ? [h('dt', {}, 'Por partes'), h('dd', {}, h('ul', { class: 'partes-ind' },
        ind.partes.map(p => h('li', {}, h('b', {}, p.que), ' · ', selloMedible(p.medible, p.porque), p.porque ? ` ${p.porque}` : ''))))] : null,
      ind.regla ? [h('dt', {}, 'Por qué está aquí'), h('dd', {}, textoCatalogo(`${ind.regla}.${ind.antes ? ` ${ind.antes}` : ''}`))] : null));
  if (ind.medible === 'no') {
    return h('div', { class: 'ind-cat' },
      h('div', { class: 'ind gris fase2' },
        h('span', { class: 'l' }, ind.nombre),
        h('span', { class: 'v' }, h('small', {}, 'Todavía no se puede medir')),
        h('span', { class: 'umbral' }, ind.medible_porque || 'Todavía no se puede medir'),
        h('span', { class: 'pie' }, selloMedible('no', ind.medible_porque))),
      queEs);
  }
  const ficha = fichaIndicador({
    titulo: ind.nombre, umbral: ind.umbral, medible: ind.medible,
    medibleDetalle: ind.medible === 'medias' ? `A medias: ${ind.medible_porque || ''}` : ind.medible_porque,
    ...o,
  });
  return h('div', { class: 'ind-cat' }, ficha, o.parcial ? h('p', { class: 'parcial' }, o.parcial) : null, queEs);
}

// L-38: «Fase 2» es un nombre interno de la hoja de ruta; solo lo ve dirección. El resto ve la misma lista sin ese rótulo.
const esDireccion = () => !!window.RO?.estado?.persona?.puestos?.includes?.('direccion');

/** pieFase2(indicadores) · lista al pie de la pantalla de lo que «todavía no» se mide (regla R5). */
export function pieFase2(indicadores = []) {
  const no = indicadores.filter(i => i && (i.medible === 'no' || i.fase2));
  if (!no.length) return null;
  return h('details', { class: 'pie-fase2' },
    h('summary', {}, `${esDireccion() ? 'Fase 2 · ' : ''}${no.length} indicador${no.length === 1 ? ' que todavía no se puede medir' : 'es que todavía no se pueden medir'}`),
    h('ul', {}, no.map(i => h('li', {}, h('b', {}, i.nombre), ` — ${i.medible_porque || i.medible_texto || 'todavía no'}`))));
}

// ============================================================================
// OLA 0 · sistema visual (2-oct-2026). Componentes nuevos para las olas siguientes.
// Todos devuelven HTMLElement, con teclado y sin colores sueltos. Documentados en LEEME.md → Componentes.
// ============================================================================

const leerSesion = k => { try { return sessionStorage.getItem(k); } catch { return null; } };
const guardarSesion = (k, v) => { try { sessionStorage.setItem(k, v); } catch { /* sin almacenamiento */ } };
const normalTxt = t => String(t ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
let _n = 0; const uid = p => `${p}-${(++_n).toString(36)}${Math.random().toString(36).slice(2, 5)}`;

/** variacion(actual, anterior) → % de cambio (redondeo a 1 decimal) o null si no se puede calcular. */
export function variacion(actual, anterior) {
  if (actual === null || actual === undefined || !anterior) return null;
  return Math.round(((actual - anterior) / Math.abs(anterior)) * 1000) / 10;
}

// -------------------------------------------------------------------- tile
/**
 * tile({ icono, etiqueta, valor, unidad, estado, comparacion, contexto, medible, medibleDetalle, frescura,
 *        alPulsar | href, activo, ir })
 *   El indicador de la ficha v3: icono en cuadrado suave según estado + etiqueta + cifra grande (números tabulares)
 *   + comparación con el periodo anterior + una línea de contexto. Pulsar lleva a su detalle.
 *   estado: 'verde' | 'ambar' | 'rojo' | 'gris' | '' (sin estado = azul neutro de RO; color solo con significado).
 *   comparacion: { delta, pct?: true, unidad?, dec?, texto: 'frente a agosto', mejorSi: 'alto' | 'bajo' }
 *     ▲ verde / ▼ rojo; con mejorSi: 'bajo' se invierte (bajar es bueno).
 *   alPulsar → <button> (con activo: true|false pinta aria-pressed, para tiles que cambian un gráfico);
 *   href → <a>; ninguno → <div>. ir: texto del enlace al pie («Ver detalle»).
 */
export function tile(o) {
  // Ronda 11 (D-P-N6 4): { crudo: true } deja el contexto tal cual (p. ej. referencias «(R31, R32)» del panel de Tomás).
  o = { ...o, contexto: typeof o.contexto === 'string' && !o.crudo ? limpiaTexto(o.contexto) : o.contexto, etiqueta: typeof o.etiqueta === 'string' ? limpiaTexto(o.etiqueta) : o.etiqueta };
  const est = o.estado || '';
  const c = o.comparacion;
  let comp = null;
  if (c && c.delta !== null && c.delta !== undefined && !Number.isNaN(c.delta)) {
    const sentido = c.delta === 0 ? 'igual' : (c.delta > 0) === (c.mejorSi !== 'bajo') ? 'bien' : 'mal';
    const flecha = c.delta > 0 ? '▲' : c.delta < 0 ? '▼' : '=';
    const num = `${fmt.num(Math.abs(c.delta), c.dec ?? (c.pct ? (Math.abs(c.delta) < 10 ? 1 : 0) : 0))}${c.pct ? ' %' : (c.unidad || '')}`;
    comp = h('span', { class: 'tc' }, h('span', { class: sentido, title: sentido === 'bien' ? 'Va a mejor' : sentido === 'mal' ? 'Va a peor' : 'Igual' }, `${flecha} ${num}`), c.texto ? h('em', {}, c.texto) : null);
  } else if (c?.texto) comp = h('span', { class: 'tc' }, h('em', {}, c.texto));
  const vacioValor = o.valor === null || o.valor === undefined || o.valor === '';
  const hijos = [
    h('span', { class: 'tt' }, h('span', { class: `ico-c ${vacioValor ? 'gris' : est}` }, icono(o.icono || 'res')), h('span', {}, o.etiqueta)),
    // Ronda 10 (guía 3.7): sin dato = «Sin dato» pequeño y gris (no un «—» de 24 px); sinDato: 'falta X' dice por qué.
    vacioValor ? h('span', { class: 'tv sin-dato' }, h('small', {}, o.sinDato ? `Sin dato · ${o.sinDato}` : 'Sin dato'))
      : h('span', { class: 'tv' }, o.valor, o.unidad && !vacioValor ? h('small', {}, o.unidad) : null),
    comp,
    o.contexto ? h('span', { class: 'tx' }, o.contexto) : null,
    o.completa ? ((o.medible || o.frescura) ? h('span', { class: 'tp' }, o.medible ? selloMedible(o.medible, o.medibleDetalle) : null, o.frescura ? frescura(o.frescura) : null) : null)
      : infoCompacta(o, 'tp'),
    o.ir ? h('span', { class: 'ir' }, o.ir, icono('derecha', { clase: 's' })) : null,
  ];
  const cls = `tile ${vacioValor ? 'gris' : est}`.trim();
  const valorTxt = o.valor instanceof Node ? o.valor.textContent : o.valor;   // un nodo como valor ya no sale «[object …]»
  const etiquetaTxt = o.etiqueta instanceof Node ? o.etiqueta.textContent : o.etiqueta;
  const etiqueta = `${etiquetaTxt}: ${vacioValor ? `sin dato${o.sinDato ? ' · ' + o.sinDato : ''}` : valorTxt}${o.unidad && !vacioValor ? ' ' + o.unidad : ''}`;
  if (o.href) return h('a', { class: cls, href: o.href, 'aria-label': `${etiqueta}. ${o.ir || 'Ver detalle'}` }, hijos);
  if (o.alPulsar) return h('button', { class: cls, type: 'button', 'aria-pressed': o.activo === undefined ? null : String(!!o.activo), on: { click: o.alPulsar } }, hijos);
  return h('div', { class: cls }, hijos);
}

/** tiles([...]) · rejilla de tiles (2 × 2 en el móvil desde la ronda 10; antes, carrusel que cortaba la segunda). */
export const tiles = lista => h('div', { class: 'tiles' }, lista);
/** rejillaTarjetas([...]) · ronda 9 (auditoría 30, §3.5): la rejilla de tarjetas SIN huérfanas. Columnas por cantidad
 *  (5 → 5, 6 → 3, 7 → 4 + 3, 8 → 4, 9 → 3, 10 → 5); si aun así queda una sola en la última fila, ocupa la fila entera.
 *  Pon primero la cifra que manda. Es la misma clase .tiles: las rejillas de siempre ya se comportan así. */
export const rejillaTarjetas = lista => h('div', { class: 'tiles' }, lista);

/**
 * menuMas({ texto = 'Más', etiqueta, items: [{ texto, icono?, alPulsar | href, activo? }], activo })
 *   Botón «Más ▾» con su menú flotante (pestañas que no caben, acciones secundarias, filtros de más). Teclado: Esc cierra.
 */
export function menuMas({ texto = 'Más', etiqueta = 'Más opciones', items = [], activo = false } = {}) {
  // items: [{ texto, icono?, href? | alPulsar?, activo?, confirmar?: '¿Quitar el acceso?', si?: 'Sí, quitar' }] · R15: con
  // «confirmar», el primer clic pregunta dentro del menú y solo «Sí» hace la acción (para lo que no se deshace).
  const caja = h('div', { class: 'periodo-mas menu-mas' });
  let abierto = false;
  let confirmando = null;
  const pintar = () => {
    const btn = h('button', { type: 'button', class: 'bt', 'aria-haspopup': 'menu', 'aria-expanded': String(abierto), 'aria-pressed': activo ? 'true' : null, 'aria-label': etiqueta,
      on: { click: e => { e.stopPropagation(); abierto = !abierto; confirmando = null; pintar(); } } }, texto, icono('chev', { clase: 's' }));
    const menu = abierto ? h('div', { class: 'menu-flot', role: 'menu', on: { keydown: e => { if (e.key === 'Escape') { abierto = false; pintar(); caja.querySelector('button')?.focus(); } } } },
      items.map(it => it.href
        ? h('a', { role: 'menuitem', href: it.href, class: it.activo ? 'activo' : null }, it.icono ? icono(it.icono, { clase: 's' }) : null, h('span', {}, it.texto))
        : confirmando === it
          // R15: un elemento con «confirmar» pregunta antes de hacer nada («¿Seguro?» · Sí · No), dentro del mismo menú.
          ? h('div', { class: 'menu-confirma', role: 'group', 'aria-label': it.confirmar },
            h('span', {}, it.confirmar),
            h('span', { class: 'fila' },
              h('button', { type: 'button', role: 'menuitem', class: 'bt mini pri', on: { click: () => { confirmando = null; abierto = false; pintar(); caja.querySelector('button')?.focus(); it.alPulsar?.(); } } }, it.si || 'Sí'),
              h('button', { type: 'button', role: 'menuitem', class: 'bt mini', on: { click: e => { e.stopPropagation(); confirmando = null; pintar(); } } }, 'No')))
          : h('button', { type: 'button', role: 'menuitem', 'aria-checked': it.activo ? 'true' : null,
            on: { click: e => { if (it.confirmar) { e.stopPropagation(); confirmando = it; pintar(); caja.querySelector('.menu-confirma button')?.focus(); return; } abierto = false; pintar(); caja.querySelector('button')?.focus(); it.alPulsar?.(); } } },
          h('span', {}, it.icono ? icono(it.icono, { clase: 's' }) : null, it.texto)))) : null;
    if (menu) { caja.replaceChildren(btn, menu); capaFlotante(menu, btn, { derecha: true }); } else caja.replaceChildren(btn);  // sin «null» con el menú cerrado
    if (abierto) menu.querySelector('button, a')?.focus({ preventScroll: true });
  };
  document.addEventListener('click', e => { if (abierto && !caja.contains(e.target)) { abierto = false; confirmando = null; pintar(); } });
  pintar();
  return caja;
}

/** campoTexto({ etiqueta, nombre, valor, tipo = 'text', ayuda, placeholder, alCambiar, filas }) · campo con su etiqueta
 *  (filas > 1 → textarea). Estilo común .campo: 36 px de alto, radio --r-m, foco con anillo. */
export function campoTexto({ etiqueta, nombre, valor = '', tipo = 'text', ayuda, placeholder, alCambiar, filas, requerido = false } = {}) {
  const id = uid('campo');
  const control = filas > 1
    ? h('textarea', { id, name: nombre, rows: filas, placeholder, required: requerido || null, on: { input: e => alCambiar?.(e.target.value) } }, valor)
    : h('input', { id, name: nombre, type: tipo, value: valor, placeholder, required: requerido || null, on: { input: e => alCambiar?.(e.target.value) } });
  return h('label', { class: 'campo', for: id }, etiqueta ? h('span', { class: 'campo-et' }, etiqueta) : null, control, ayuda ? h('small', {}, ayuda) : null);
}

/** esqueleto({ lineas = 3, tarjetas = 0 }) · estado de carga con la forma del contenido (barras con brillo suave). */
export function esqueleto({ lineas = 3, tarjetas = 0 } = {}) {
  return h('div', { class: 'esqueleto', role: 'status', 'aria-label': 'Cargando' },
    tarjetas ? h('div', { class: 'tiles' }, Array.from({ length: tarjetas }, () => h('div', { class: 'esq-tarjeta' }))) : null,
    Array.from({ length: lineas }, (_, i) => h('div', { class: 'esq-linea', style: { width: `${[92, 76, 84, 60][i % 4]}%` } })));
}

// ------------------------------------------------------------ chips de filtro
/**
 * chipsFiltro({ opciones: [{ valor, texto, cuenta?, cuentaEstado?: 'rojo', icono? }], valor, multiple, alCambiar,
 *               etiqueta, clave, limpiar })
 *   Filtros como chips que SE QUEDAN (con clave, se recuerdan en la pestaña del navegador) y su contador al lado,
 *   como las vistas guardadas de Zoho Desk. Para una vista «Todos», pon una opción con valor ''.
 *   Selección única por defecto; multiple: true para combinar (y botón «Quitar filtros»).
 *   alCambiar(valor | [valores]) en cada cambio. Valor inicial (p. ej. el recordado): el.valor().
 */
export function chipsFiltro(o) {
  const multiple = !!o.multiple;
  const validos = new Set(o.opciones.map(x => String(x.valor)));
  let sel = new Set();
  const recordado = o.clave ? leerSesion(`ro.chips.${o.clave}`) : null;
  const inicial = recordado !== null ? JSON.parse(recordado || '[]') : (o.valor === undefined ? (multiple ? [] : [o.opciones[0]?.valor]) : [].concat(o.valor));
  for (const v of inicial) if (validos.has(String(v))) sel.add(String(v));
  if (!multiple && !sel.size && o.opciones.length) sel.add(String(o.opciones[0].valor));
  const caja = h('div', { class: 'chips-f', role: 'group', 'aria-label': o.etiqueta || 'Filtros' });
  const valor = () => (multiple ? [...sel] : [...sel][0] ?? '');
  const pintar = () => {
    caja.replaceChildren(...[
      o.etiqueta ? h('span', { class: 'et', 'aria-hidden': 'true' }, o.etiqueta) : null,
      o.opciones.map(op => h('button', { type: 'button', 'aria-pressed': String(sel.has(String(op.valor))),
        on: { click: () => {
          const v = String(op.valor);
          if (multiple) sel.has(v) ? sel.delete(v) : sel.add(v);
          else sel = new Set([v]);
          cambiar();
        } } },
        op.icono ? icono(op.icono) : null, op.texto,
        op.cuenta !== undefined && op.cuenta !== null ? h('span', { class: `cu${op.cuentaEstado === 'rojo' && op.cuenta ? ' rojo' : ''}`, 'aria-label': `${op.cuenta} elementos` }, fmt.num(op.cuenta)) : null)),
      multiple && (o.limpiar !== false) && sel.size ? h('button', { type: 'button', class: 'limpiar', on: { click: () => { sel.clear(); cambiar(); } } }, icono('cerrar', { clase: 's' }), 'Quitar filtros') : null,
    ].flat().filter(Boolean));
  };
  const cambiar = () => {
    if (o.clave) guardarSesion(`ro.chips.${o.clave}`, JSON.stringify([...sel]));
    const foco = document.activeElement && caja.contains(document.activeElement) ? [...caja.querySelectorAll('button')].indexOf(document.activeElement) : -1;
    pintar();
    if (foco >= 0) caja.querySelectorAll('button')[Math.min(foco, caja.querySelectorAll('button').length - 1)]?.focus();
    o.alCambiar?.(valor());
  };
  pintar();
  caja.valor = valor;
  return caja;
}

// ------------------------------------------------- periodo con comparación
/**
 * selectorPeriodo({ opciones, valor, alCambiar, clave, comparacion: true })
 *   Un periodo único arriba para toda la pantalla, con su comparación (como Analytics).
 *   Opciones por defecto: 7 días · 30 días · Este mes. alCambiar(valor). el.valor() da el actual.
 */
// ------------------------------------------------- periodo común (D-P-N1 · ronda 9)
// Misma regla que fuentes_paneles/periodos.py y modulos/paneles_periodo.js (si cambias una, cambia las otras):
//   hoy · ayer · 7d [hoy−7, ayer] · 30d [hoy−30, ayer] · mes [día 1, hoy] · mes_ant [mes anterior entero]
//   · trim [día 1 del trimestre natural, hoy] · anio [1-ene, hoy] · medida [desde, hasta] (máx. 2 años).
//   Comparación «anterior»: mismos días justo antes (mes → del 1 al mismo día del mes pasado; mes_ant → el mes anterior
//   entero; trim → mismos días del trimestre anterior; anio → mismo tramo del año pasado). «anio_ant»: un año antes. «no».
// Fechas AAAA-MM-DD en hora de Madrid. Se recuerda POR PERSONA (localStorage ro.periodo.<persona>).
export const PERIODO_IDS = ['hoy', 'ayer', '7d', '30d', 'mes', 'mes_ant', 'trim', 'anio', 'medida'];
export const PERIODO_TEXTO = { hoy: 'Hoy', ayer: 'Ayer', '7d': '7 días', '30d': '30 días', mes: 'Este mes', mes_ant: 'Mes anterior', trim: 'Este trimestre', anio: 'Este año', medida: 'A medida' };
export const COMPARACIONES = [['anterior', 'Periodo anterior'], ['anio_ant', 'Año anterior'], ['no', 'Sin comparar']];
const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
// ------------------------------------------------------------------ fechas comunes (V2-E, 3-oct)
// UNA SOLA VARA para «hoy», «ayer», «vencida», «esta semana» y «último laborable»: el calendario de la agencia, en hora de
// Madrid, el mismo en todas las pantallas aunque el Mac o la persona estén en otra zona (Tomás en Bali, accounts en
// Argentina). Los módulos lo leen de ctx.hoy (texto) y ctx.fechas (funciones); fuera de un módulo, fechasDe(). Las fechas
// de los datos sin zona («2026-10-02 23:14») ya están en hora de Madrid: se toma su día tal cual. Ver LEEME › Fechas.
const ZONA_RO = 'Europe/Madrid';
function _diaEn(zona, d) { return diaRO(d, zona); }
let _hoyFijo = null;   // solo prototipo: ?hoy=AAAA-MM-DD en 127.0.0.1 para probar un lunes o un fin de mes (lo fija app.js)
/** fijarHoy('2026-10-05') · solo pruebas en local: todas las pantallas creen que hoy es ese día. null lo quita. */
export function fijarHoy(t) { _hoyFijo = typeof t === 'string' && /^\d{4}-\d\d-\d\d$/.test(t) ? fechaCivilRO(t) : null; }
export function hoyMadrid() { return _hoyFijo || _diaEn(ZONA_RO, new Date()); }
const DIA_CORTO = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const DIA_LARGO = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
/**
 * fechasDe(zona = 'Europe/Madrid') → helpers de fecha con UNA definición para toda la app:
 *   hoy() · ayer() · manana()                       'AAAA-MM-DD' del calendario de la agencia
 *   dia(t)                                          día de una fecha de los datos ('2026-10-02 23:14' → '2026-10-02'; ISO con zona → su día en Madrid)
 *   diasDesde(t)                                    días naturales de t a hoy (0 hoy, 1 ayer, −1 mañana)
 *   esHoy(t) · esAyer(t) · vencida(t) · venceHoy(t) vencida = su día es ANTERIOR a hoy (lo de ayer ya está vencido; lo de hoy, no)
 *   semana() → { desde: lunes, hasta: domingo }     estaSemana(t)
 *   laborable(t) · ultimoLaborable()                lunes a viernes; el último laborable ANTES de hoy (sábado 3 → viernes 2)
 *   diaSemana(t, largo?)                            'vie' / 'viernes'
 *   relativo(t)                                     'hoy' · 'ayer' · 'mañana' · 'el vie 2' (±6 días) · '28-sep'
 *   instante(t)                                     Date|null; sin zona = Madrid, sólo-fecha/hueco/hora DST repetida = null
 *   horasDesde(t, ahora?) · horasHasta(t, ahora?)     duración real en horas, null sin instante; ahora inyectable
 *   fechaCivil(t) · mes(t?) · nombreMes(t?)           civil válido, 'AAAA-MM', mes en español; sin zona del navegador
 *   hora(t)                                         'HH:MM' del instante en zona; '' sin instante
 *   diaDatos(generado)                              { dia, esHoy, texto: '' | 'datos de ayer (vie 2)' | 'datos del 28-sep' }
 *   antiguedad(horas)                               '5 h' hasta 48 h; luego '3 días' (nada de «478 h»)
 *   plazo(t)                                        'hoy a las 18:00' · 'mañana a las 10:00' · 'el lun 5 a las 9:00' (hora en punto)
 */
export function fechasDe(zona = ZONA_RO) {
  const z = zonaFechaRO(zona);
  const hoy = () => _hoyFijo || _diaEn(z, new Date());
  const dia = t => diaRO(t, z);
  const hora = t => horaRO(t, z);
  const diasDesde = t => { const d = dia(t); return d ? _dias(d, hoy()) : null; };
  const semana = () => { const h0 = hoy(); const dw = (_D(h0).getUTCDay() + 6) % 7; const desde = sumarDias(h0, -dw); return { desde, hasta: sumarDias(desde, 6) }; };
  const laborable = t => { const d = dia(t); if (!d) return false; const w = _D(d).getUTCDay(); return w >= 1 && w <= 5; };
  const diaSemana = (t, largo = false) => { const d = dia(t); return d ? (largo ? DIA_LARGO : DIA_CORTO)[_D(d).getUTCDay()] : ''; };
  const relativo = t => {
    const d = dia(t); if (!d) return '—';
    const n = _dias(d, hoy());
    if (n === 0) return 'hoy';
    if (n === 1) return 'ayer';
    if (n === -1) return 'mañana';
    if (Math.abs(n) <= 6) return `el ${diaSemana(d)} ${Number(d.slice(8, 10))}`;   // «el vie 2» (contrato V2-E, pruebas_coherencia)
    return fechaCorta(d, d.slice(0, 4) !== hoy().slice(0, 4));
  };
  return {
    zona: z, hoy, dia, diasDesde, semana, laborable, diaSemana, relativo,
    instante: instanteRO, horasDesde: horasDesdeRO, horasHasta: horasHastaRO, fechaCivil: fechaCivilRO,
    mes: (t = hoy()) => mesRO(t, z), nombreMes: (t = hoy()) => nombreMesRO(t, z),
    ayer: () => sumarDias(hoy(), -1),
    manana: () => sumarDias(hoy(), 1),
    esHoy: t => dia(t) === hoy(),
    esAyer: t => dia(t) === sumarDias(hoy(), -1),
    vencida: t => { const d = dia(t); return !!d && d < hoy(); },
    venceHoy: t => dia(t) === hoy(),
    estaSemana: t => { const d = dia(t); const s = semana(); return !!d && d >= s.desde && d <= s.hasta; },
    ultimoLaborable: () => { let d = sumarDias(hoy(), -1); for (let i = 0; i < 7 && !laborable(d); i++) d = sumarDias(d, -1); return d; },
    hora,
    diaDatos: generado => {
      const d = dia(generado); if (!d) return { dia: null, esHoy: false, texto: '' };
      const n = _dias(d, hoy());
      return { dia: d, esHoy: n === 0, texto: n === 0 ? '' : n < 0 ? `datos futuros (${fechaCorta(d, d.slice(0, 4) !== hoy().slice(0, 4))})` : n === 1 ? `datos de ayer (${diaSemana(d)} ${Number(d.slice(8, 10))})` : `datos del ${n <= 6 ? `${diaSemana(d)} ${Number(d.slice(8, 10))}` : fechaCorta(d)}` };
    },
    /** plazo(t) → «hoy a las 18:00», «mañana a las 10:00», «el lun 5 a las 9:00», «28-sep» (40_A B2: sin minutos raros
     *  como «17:53»: se redondea a la hora en punto siguiente). */
    plazo: t => {
      const d = dia(t); if (!d) return '—';
      const hm = (hora(t).match(/^(\d\d):(\d\d)$/) || []);
      let hh = hm[1] ? Number(hm[1]) + (Number(hm[2]) > 0 ? 1 : 0) : null;
      if (hh === 24) hh = 23;
      const rel = relativo(d);
      return hh === null || /^\d/.test(rel) ? rel : `${rel} a las ${hh}:00`;
    },
    antiguedad: horas => {
      const n = typeof horas === 'number' || (typeof horas === 'string' && horas.trim()) ? Number(horas) : NaN;
      if (!Number.isFinite(n)) return '—';
      if (n < 48) return `${Math.max(0, Math.round(n))} h`;
      const d = Math.round(n / 24);
      return `${d} días`;
    },
  };
}
/** fechas · los helpers con la zona de la agencia (Madrid). Para un módulo: ctx.fechas (la misma definición). */
export const fechas = fechasDe(ZONA_RO);
const _D = t => { const civil = fechaCivilRO(t); if (!civil) return new Date(NaN); const [a, m, d] = civil.split('-').map(Number); const fecha = new Date(0); fecha.setUTCFullYear(a, m - 1, d); fecha.setUTCHours(0, 0, 0, 0); return fecha; };
const _S = d => d.toISOString().slice(0, 10);
export const sumarDias = (t, n) => { const d = _D(t); if (!Number.isFinite(+d) || !Number.isInteger(n)) return null; d.setUTCDate(d.getUTCDate() + n); return _S(d); };
const _dias = (a, b) => Math.round((_D(b) - _D(a)) / 864e5);
const _finMes = (a, m) => new Date(Date.UTC(a, m + 1, 0)).getUTCDate();
function _menosMeses(t, n) { const d = _D(t); let m = d.getUTCMonth() - n, a = d.getUTCFullYear(); while (m < 0) { m += 12; a -= 1; } return _S(new Date(Date.UTC(a, m, Math.min(d.getUTCDate(), _finMes(a, m))))); }
function _menosAnio(t) { const d = _D(t); const a = d.getUTCFullYear() - 1, m = d.getUTCMonth(); return _S(new Date(Date.UTC(a, m, Math.min(d.getUTCDate(), _finMes(a, m))))); }
/** fechaCorta('2026-09-02') → «2-sep» · con año: «2-sep-26». */
export const fechaCorta = (t, conAnio = false) => { const d = _D(t); if (!Number.isFinite(+d)) return '—'; return `${d.getUTCDate()}-${MESES_CORTOS[d.getUTCMonth()]}${conAnio ? `-${d.getUTCFullYear()}` : ''}`; };   // «1-dic-2025» (44 §2.3)
const _rango = (a, b, anio = false) => (a === b ? fechaCorta(a, anio) : `${fechaCorta(a, anio)} a ${fechaCorta(b, anio)}`);

/** rangoPeriodo(id, { hoy, desde, hasta }) → { id, desde, hasta, dias, nombre, rango, texto } */
export function rangoPeriodo(id, { hoy = hoyMadrid(), desde, hasta } = {}) {
  const ayer = sumarDias(hoy, -1);
  let a, b;
  switch (id) {
    case 'hoy': a = b = hoy; break;
    case 'ayer': a = b = ayer; break;
    case '7d': a = sumarDias(hoy, -7); b = ayer; break;
    case '30d': a = sumarDias(hoy, -30); b = ayer; break;
    case 'mes': a = hoy.slice(0, 8) + '01'; b = hoy; break;
    case 'mes_ant': b = sumarDias(hoy.slice(0, 8) + '01', -1); a = b.slice(0, 8) + '01'; break;
    case 'trim': { const m = Number(hoy.slice(5, 7)); a = `${hoy.slice(0, 4)}-${String(3 * Math.floor((m - 1) / 3) + 1).padStart(2, '0')}-01`; b = hoy; break; }
    case 'anio': a = hoy.slice(0, 4) + '-01-01'; b = hoy; break;
    case 'medida': {
      a = desde || sumarDias(hoy, -30); b = hasta || ayer; if (a > b) [a, b] = [b, a];
      if (b > hoy) b = hoy; if (_dias(a, b) > 731) a = sumarDias(b, -731);     // máximo 2 años
      break;
    }
    default: return rangoPeriodo('30d', { hoy });
  }
  const nombre = PERIODO_TEXTO[id];
  return { id, desde: a, hasta: b, dias: _dias(a, b) + 1, nombre, rango: _rango(a, b), texto: `${nombre} · ${_rango(a, b)}` };
}

/** rangoComparacion(p, 'anterior' | 'anio_ant' | 'no') → { modo, desde, hasta, rango, texto } o null */
export function rangoComparacion(p, modo = 'anterior') {
  if (!p || modo === 'no') return null;
  let a, b;
  if (modo === 'anio_ant') { a = _menosAnio(p.desde); b = _menosAnio(p.hasta); }
  else if (p.id === 'mes') { a = _menosMeses(p.desde, 1); b = _menosMeses(p.hasta, 1); }
  else if (p.id === 'mes_ant') { b = sumarDias(p.desde, -1); a = b.slice(0, 8) + '01'; }
  else if (p.id === 'trim') { a = _menosMeses(p.desde, 3); b = sumarDias(a, p.dias - 1); }
  else if (p.id === 'anio') { a = _menosAnio(p.desde); b = _menosAnio(p.hasta); }
  else { b = sumarDias(p.desde, -1); a = sumarDias(p.desde, -p.dias); }
  const anio = a.slice(0, 4) !== p.desde.slice(0, 4);     // otro año: se dice («1-ene-25 a 2-oct-25»)
  return { modo, desde: a, hasta: b, rango: _rango(a, b, anio), texto: `frente a ${_rango(a, b, anio)}` };
}

/** periodoCompleto({ id, comparar, desde, hasta }) → rangoPeriodo + { comparar, comp, texto completo } */
export function periodoCompleto(v = {}, hoy) {
  const p = rangoPeriodo(PERIODO_IDS.includes(v.id) ? v.id : '30d', { hoy, desde: v.desde, hasta: v.hasta });
  const comparar = ['anterior', 'anio_ant', 'no'].includes(v.comparar) ? v.comparar : 'anterior';
  const comp = rangoComparacion(p, comparar);
  return { ...p, comparar, comp, texto: `${p.nombre} · ${p.rango}${comp ? ` · ${comp.texto}` : ''}` };
}
const _clavePeriodo = persona => `ro.periodo.${persona || 'anon'}`;
export function leerPeriodo(persona) {
  try { const v = JSON.parse(localStorage.getItem(_clavePeriodo(persona)) || 'null'); if (v && PERIODO_IDS.includes(v.id)) return v; } catch { /* sin almacenamiento */ }
  return { id: '30d', comparar: 'anterior' };
}
export function guardarPeriodo(persona, v) { try { localStorage.setItem(_clavePeriodo(persona), JSON.stringify({ id: v.id, comparar: v.comparar, desde: v.id === 'medida' ? v.desde : undefined, hasta: v.id === 'medida' ? v.hasta : undefined })); } catch { /* sin almacenamiento */ } }

/** sumarSerie({ 'AAAA-MM-DD': n | [n…] }, p, idx?) → suma del periodo (número o lista); null si no hay datos.
 *  N-11: un día sin dato (o un hueco `null` dentro de la lista) se SALTA, no suma 0; un día con 0 sí suma 0.
 *  Si una columna de la lista no tiene ningún dato en todo el periodo, esa columna sale null (no 0). */
export function sumarSerie(serie, p, idx = null) {
  if (!serie || !p) return null;
  let tot = null;
  for (const [d, v] of Object.entries(serie)) {
    if (d < p.desde || d > p.hasta) continue;
    const x = idx === null ? v : v?.[idx];
    const suma = (a, b) => (a === null || a === undefined ? (typeof b === 'number' ? b : null) : (typeof b === 'number' ? a + b : a));
    if (Array.isArray(x)) tot = tot ? tot.map((t, i) => suma(t, x[i])) : x.map(n => (typeof n === 'number' ? n : null));
    else if (typeof x === 'number') tot = (tot || 0) + x;
  }
  return tot;
}
/** sumarSerieDetalle(serie, p, idx?) → { total, dias, faltan, completo } (N-11): `total` es el de sumarSerie; `dias` son los del
 *  periodo; `faltan` los días del periodo sin dato (ni número ni lista); `completo` = faltan === 0. */
export function sumarSerieDetalle(serie, p, idx = null) {
  const total = sumarSerie(serie, p, idx);
  if (!serie || !p) return { total, dias: 0, faltan: 0, completo: true };
  let dias = 0, faltan = 0;
  for (let d = p.desde, i = 0; d <= p.hasta && i < 800; d = sumarDias(d, 1), i++) {
    dias++;
    const v = serie[d];
    const x = idx === null ? v : v?.[idx];
    if (!(typeof x === 'number' || (Array.isArray(x) && x.some(n => typeof n === 'number')))) faltan++;
  }
  return { total, dias, faltan, completo: faltan === 0 };
}
/** serieDelPeriodo(serie, p, idx?, { huecos }) → [{ x: 'AAAA-MM-DD', y }] día a día, para grafico().
 *  Sin `huecos` (series de sucesos: un día sin filas es 0 sucesos) un día sin dato vale 0, como siempre.
 *  Con `huecos: true` (series diarias medidas: Analytics) un día sin dato es null: hueco en el gráfico, no un 0 (N-11). */
export function serieDelPeriodo(serie, p, idx = null, { huecos = false } = {}) {
  if (!serie || !p) return [];
  const out = [];
  for (let d = p.desde, i = 0; d <= p.hasta && i < 800; d = sumarDias(d, 1), i++) {
    const v = serie[d];
    const y = v === undefined ? (huecos ? null : 0) : idx === null ? v : (v?.[idx] ?? (huecos ? null : 0));
    out.push({ x: d, y });
  }
  return out;
}
/** deltaPeriodo(actual, anterior, { mejorSi, pct = true, texto }) → objeto listo para tile({ comparacion }). */
export function deltaPeriodo(actual, anterior, { mejorSi = 'alto', pct = true, texto = 'frente al periodo anterior' } = {}) {
  if (actual === null || actual === undefined || anterior === null || anterior === undefined) return { delta: null, texto: 'sin periodo anterior' };
  return pct ? { delta: variacion(actual, anterior), pct: true, mejorSi, texto } : { delta: actual - anterior, mejorSi, texto };
}

/** Selector común: 4 periodos a la vista + «Más ▾» (mes anterior, trimestre, año y «A medida» con dos fechas)
 *  y la comparación como segmentado (Periodo anterior · Año anterior · Sin comparar). el.valor() = periodoCompleto. */
function selectorPeriodoComun(o) {
  const ids = (o.ids || PERIODO_IDS).filter(i => PERIODO_IDS.includes(i));
  let v = o.valorInicial || leerPeriodo(o.persona);
  if (!ids.includes(v.id)) v = { ...v, id: ids.includes('30d') ? '30d' : ids[0] };
  // Ronda 12 (R13): con 4 periodos o menos, todos a la vista (nada escondido en «Más»); «A medida» sigue en «Más».
  const fijos = ids.filter(i => i !== 'medida');
  const visibles = fijos.length <= 4 ? fijos : ids.filter(i => ['hoy', '7d', '30d', 'mes'].includes(i)).slice(0, 4);
  const resto = ids.filter(i => !visibles.includes(i));
  const conDatos = (o.conDatos || []).filter(d => d && d.desde && d.hasta && d.nombre);
  if (conDatos.length && !resto.includes('medida')) resto.push('medida');
  const hayMedida = resto.includes('medida') || ids.includes('medida');
  const esConDatos = d => v.id === 'medida' && v.desde === d.desde && v.hasta === d.hasta;
  const caja = h('div', { class: 'periodo periodo-comun', role: 'group', 'aria-label': 'Periodo y comparación' });
  // V2-E (40_B M13): en el móvil, UN botón «30 días · frente al anterior ▾» (una fila de 40 px) que abre todo en un menú;
  // en pantalla ancha, lo de siempre (segmentado + «Más ▾» + comparación). Las dos vistas comparten estado y CSS decide.
  let abierto = false, abiertoMovil = false;
  const cambiar = nuevo => { v = { ...v, ...nuevo }; if (o.persona !== false) guardarPeriodo(o.persona, v); pintar(); o.alCambiar?.(periodoCompleto(v, o.hoy)); };
  const cerrar = () => { if (abierto || abiertoMovil) { abierto = false; abiertoMovil = false; pintar(); } };
  const elegir = nuevo => {   // V3a: al elegir en un menú, el foco vuelve a su botón
    const venia = abiertoMovil ? '.periodo-movil > button' : abierto ? '.periodo-mas > button' : null;
    abierto = false; abiertoMovil = false; cambiar(nuevo);
    if (venia) caja.querySelector(venia)?.focus();
  };
  const formMedida = p => h('form', { class: 'periodo-medida', on: { submit: e => { e.preventDefault(); const f = e.target; elegir({ id: 'medida', desde: f.desde.value, hasta: f.hasta.value }); } } },
    h('b', {}, 'A medida'),
    h('label', {}, 'Desde', h('input', { type: 'date', name: 'desde', value: v.desde || p.desde, min: '2024-01-01', max: o.hoy || hoyMadrid(), required: true })),
    h('label', {}, 'Hasta', h('input', { type: 'date', name: 'hasta', value: v.hasta || p.hasta, min: '2024-01-01', max: o.hoy || hoyMadrid(), required: true })),
    h('button', { type: 'submit', class: 'bt pri mini' }, 'Aplicar'));
  // Ronda 10: «periodos con datos» del módulo (meses cerrados del Informe, etc.): un clic y queda «A medida» con esas fechas
  const bloqueDatos = () => (conDatos.length ? h('div', { class: 'periodo-datos', role: 'group', 'aria-label': 'Periodos con datos' }, h('b', {}, o.tituloConDatos || 'Con datos'),
    conDatos.map(d => h('button', { type: 'button', role: 'menuitemradio', 'aria-checked': String(esConDatos(d)), on: { click: () => elegir({ id: 'medida', desde: d.desde, hasta: d.hasta }) } },
      h('span', {}, d.nombre), h('small', {}, rangoPeriodo('medida', { hoy: o.hoy, desde: d.desde, hasta: d.hasta }).rango)))) : null);
  const opcion = (id, txt, marcado, alPulsar, detalle) => h('button', { type: 'button', role: 'menuitemradio', 'aria-checked': String(marcado), on: { click: alPulsar } },
    h('span', {}, txt), detalle ? h('small', {}, detalle) : null);
  const escMenu = sel => ({ keydown: e => { if (e.key === 'Escape') { cerrar(); caja.querySelector(sel)?.focus(); } } });
  const COMP_CORTA = { anterior: 'frente al anterior', anio_ant: 'frente al año pasado', no: 'sin comparar' };
  const pintar = () => {
    const p = periodoCompleto(v, o.hoy);
    const bt = id => h('button', { type: 'button', 'aria-pressed': String(v.id === id), on: { click: () => elegir({ id }) } }, PERIODO_TEXTO[id]);
    const menu = abierto ? h('div', { class: 'menu-flot', role: 'menu', on: escMenu('.periodo-mas > button') },
      resto.filter(i => i !== 'medida').map(id => opcion(id, PERIODO_TEXTO[id], v.id === id, () => elegir({ id }), rangoPeriodo(id, { hoy: o.hoy }).rango)),
      resto.includes('medida') ? formMedida(p) : null,
      bloqueDatos()) : null;
    const nombreAct = conDatos.find(esConDatos)?.nombre || PERIODO_TEXTO[v.id];
    const menuMovil = abiertoMovil ? h('div', { class: 'menu-flot periodo-menu-movil', role: 'menu', on: escMenu('.periodo-movil > button') },
      h('b', { class: 'periodo-menu-t' }, 'Periodo'),
      fijos.map(id => opcion(id, PERIODO_TEXTO[id], v.id === id, () => elegir({ id }), rangoPeriodo(id, { hoy: o.hoy }).rango)),
      o.comparar === false ? null : [h('b', { class: 'periodo-menu-t' }, 'Comparar con'),
        COMPARACIONES.map(([k, t]) => opcion(k, t, p.comparar === k, () => elegir({ comparar: k })))],
      hayMedida ? formMedida(p) : null,
      bloqueDatos()) : null;
    poner(caja,
      icono('cal', { clase: 's' }),
      h('div', { class: 'segm' }, visibles.map(bt),
        resto.length ? h('div', { class: 'periodo-mas' },
          h('button', { type: 'button', 'aria-haspopup': 'menu', 'aria-expanded': String(abierto), 'aria-pressed': String(resto.includes(v.id) || !!conDatos.find(esConDatos)), on: { click: e => { e.stopPropagation(); abierto = !abierto; abiertoMovil = false; pintar(); } } },
            conDatos.find(esConDatos)?.nombre || (resto.includes(v.id) ? PERIODO_TEXTO[v.id] : 'Más periodos'), icono('chev', { clase: 's' })), menu) : null),
      o.comparar === false ? null : h('div', { class: 'segm segm-comp', role: 'group', 'aria-label': 'Comparar con' },
        COMPARACIONES.map(([k, t]) => h('button', { type: 'button', 'aria-pressed': String(p.comparar === k), on: { click: () => cambiar({ comparar: k }) } }, t))),
      h('span', { class: 'comp', 'aria-live': 'polite', title: p.texto }, `${p.rango}${p.comp ? ` · frente a ${p.comp.rango}` : ''}`),
      h('div', { class: 'periodo-movil' },
        h('button', { type: 'button', 'aria-haspopup': 'menu', 'aria-expanded': String(abiertoMovil), 'aria-label': `Periodo: ${p.texto}. Cambiar`,
          on: { click: e => { e.stopPropagation(); abiertoMovil = !abiertoMovil; abierto = false; pintar(); } } },
          icono('cal', { clase: 's' }),
          h('span', { class: 'pm-txt' }, h('b', {}, nombreAct), o.comparar === false ? '' : ` · ${COMP_CORTA[p.comparar] || ''}`),
          h('small', { class: 'pm-rango' }, p.rango),
          icono('chev', { clase: 's' })),
        menuMovil));
    for (const m of caja.querySelectorAll('.menu-flot')) capaFlotante(m, m.previousElementSibling);   // V3a: capa por encima de todo
    if (abierto || abiertoMovil) caja.querySelector('.menu-flot button, .menu-flot input')?.focus({ preventScroll: true });
  };
  document.addEventListener('click', e => { if ((abierto || abiertoMovil) && !caja.contains(e.target)) cerrar(); });
  pintar();
  caja.valor = () => periodoCompleto(v, o.hoy);
  caja.poner = nuevo => { v = { ...v, ...nuevo }; pintar(); };
  return caja;
}

/**
 * selectorPeriodo({ opciones, valor, clave, alCambiar, comparacion })  · el de siempre (compatible).
 * selectorPeriodo({ comun: true, persona, ids, alCambiar, comparar, conDatos })   · el COMÚN (D-P-N1): 9 periodos + comparación,
 *   conDatos: [{ nombre: 'Septiembre', desde: '2026-09-01', hasta: '2026-09-30' }] añade «Con datos» al menú «Más» (ronda 10),
 *   recordado por persona; el.valor() = { id, desde, hasta, dias, nombre, rango, comparar, comp, texto }.
 *   Lo pinta la carcasa sola si el módulo exporta usa_periodo (ver LEEME); los módulos leen ctx.periodo.
 */
export function selectorPeriodo(o = {}) {
  if (o.comun) return selectorPeriodoComun(o);
  const opciones = o.opciones || [
    { valor: '7', texto: '7 días', comparacion: 'frente a los 7 anteriores' },
    { valor: '30', texto: '30 días', comparacion: 'frente a los 30 anteriores' },
    { valor: 'mes', texto: 'Este mes', comparacion: 'frente al mes pasado hasta el mismo día' },
  ];
  let actual = (o.clave && leerSesion(`ro.periodo.${o.clave}`)) || o.valor || opciones[1]?.valor || opciones[0].valor;
  if (!opciones.some(x => x.valor === actual)) actual = opciones[0].valor;
  const comp = h('span', { class: 'comp', 'aria-live': 'polite' });
  const segm = h('div', { class: 'segm', role: 'group', 'aria-label': 'Periodo' });
  const pintar = () => {
    segm.replaceChildren(...opciones.map(op => h('button', { type: 'button', 'aria-pressed': String(op.valor === actual),
      on: { click: () => { actual = op.valor; if (o.clave) guardarSesion(`ro.periodo.${o.clave}`, actual); pintar(); o.alCambiar?.(actual); } } }, op.texto)));
    comp.textContent = o.comparacion === false ? '' : (opciones.find(x => x.valor === actual)?.comparacion || '');
  };
  pintar();
  const el = h('div', { class: 'periodo' }, icono('cal', { clase: 's' }), segm, comp);
  el.valor = () => actual;
  return el;
}

// ------------------------------------------------------------------ pestañas
/**
 * pestanas({ pestanas: [{ id, texto, icono, cuenta?, cuentaEstado?: 'rojo' }], activa, alCambiar, pintar, clave, etiqueta })
 *   Pestañas con icono y contador (rojo si hay que actuar), como la ficha v3. Teclado: ← → Inicio Fin.
 *   Con pintar(id, contenedor) devuelve barra + panel y pinta el contenido al cambiar (instantáneo).
 *   Sin pintar, solo la barra y avisa con alCambiar(id). Con clave, recuerda la pestaña. el.activa() da la actual.
 *   unaFila: true (ronda 10) → nunca baja a una segunda línea ni se desplaza: lo que no cabe va a «Más (n) ▾».
 */
export function pestanas(o) {
  const base = uid('pt');
  const ids = o.pestanas.map(p => p.id);
  let activa = (o.clave && leerSesion(`ro.pestana.${o.clave}`)) || o.activa || ids[0];
  if (!ids.includes(activa)) activa = ids[0];
  const barra = h('div', { class: 'pestanas', role: 'tablist', 'aria-label': o.etiqueta || 'Pestañas' });
  const zona = o.pintar ? h('div', { class: 'pestana-panel', role: 'tabpanel', tabindex: '-1' }) : null;
  const botones = o.pestanas.map(p => {
    const b = h('button', { type: 'button', role: 'tab', id: `${base}-${p.id}`, 'aria-controls': zona ? `${base}-panel` : null,
      on: { click: () => elegir(p.id), keydown: e => {
        const i = ids.indexOf(p.id);
        const j = e.key === 'ArrowRight' ? (i + 1) % ids.length : e.key === 'ArrowLeft' ? (i - 1 + ids.length) % ids.length : e.key === 'Home' ? 0 : e.key === 'End' ? ids.length - 1 : -1;
        if (j < 0) return;
        e.preventDefault(); elegir(ids[j]); botones[j].focus();
      } } },
      p.icono ? icono(p.icono) : null, p.texto,
      p.cuenta ? h('span', { class: `c${p.cuentaEstado === 'rojo' ? ' rojo' : ''}`, 'aria-label': `${p.cuenta} pendientes` }, fmt.num(p.cuenta)) : null);
    return b;
  });
  barra.append(...botones);
  if (zona) zona.id = `${base}-panel`;
  function marcar() {
    botones.forEach((b, i) => { const on = ids[i] === activa; b.setAttribute('aria-selected', String(on)); b.tabIndex = on ? 0 : -1; });
    if (zona) zona.setAttribute('aria-labelledby', `${base}-${activa}`);
  }
  function elegir(id) {
    if (id === activa && zona?.childNodes.length) return;
    activa = id;
    if (o.clave) guardarSesion(`ro.pestana.${o.clave}`, id);
    marcar();
    if (zona) { zona.replaceChildren(); o.pintar(id, zona); }
    o.alCambiar?.(id);
  }
  marcar();
  if (zona) o.pintar(activa, zona);
  // Ronda 10 (D-P-DS-FB 1): unaFila: true → las pestañas que no caben van a «Más (n) ▾» (la activa nunca se esconde).
  // Es el pestanasEnUnaFila() de la ficha, ya común.
  let cabeza = barra;
  if (o.unaFila) {
    cabeza = h('div', { class: 'pestanas-fila' });
    const hueco = h('div', { class: 'pestanas-mas' });
    cabeza.append(barra, hueco);
    const menu = ocultas => menuMas({ texto: `Más (${ocultas.length})`, etiqueta: 'Más pestañas',
      items: ocultas.map(d => ({ texto: d.cuenta ? `${d.texto} · ${fmt.num(d.cuenta)}${d.cuentaEstado === 'rojo' ? ' (en rojo)' : ''}` : d.texto, icono: d.icono, alPulsar: () => elegir(d.id) })) });
    const ajustar = () => {
      botones.forEach(b => { b.hidden = false; });
      hueco.replaceChildren();
      if (barra.scrollWidth <= barra.clientWidth + 1) return;
      hueco.replaceChildren(menu(o.pestanas));            // ocupa su sitio antes de medir
      for (let i = botones.length - 1; i >= 0 && barra.scrollWidth > barra.clientWidth + 1; i--) {
        if (ids[i] === activa) continue;
        botones[i].hidden = true;
      }
      hueco.replaceChildren(menu(o.pestanas.filter((_, i) => botones[i].hidden)));
    };
    const alCambiarAntes = o.alCambiar;
    o = { ...o, alCambiar: id => { ajustar(); alCambiarAntes?.(id); } };
    if (typeof ResizeObserver === 'function') new ResizeObserver(() => ajustar()).observe(cabeza);
    requestAnimationFrame(ajustar);
    cabeza.ajustar = ajustar;
  }
  const el = zona ? h('div', { class: 'pestanas-caja' }, cabeza, zona) : cabeza;
  el.activa = () => activa;
  el.elegir = elegir;
  return el;
}

// ---------------------------------------------------------- estado vacío grande
/**
 * vacio({ icono, titulo, texto, quien, accion, tono: 'neutro' | 'celebrar' | 'aviso', borde })
 *   Estado vacío que explica qué hacer: icono grande + frase + quién lo arregla. Nunca una caja en blanco.
 *   Para huecos dentro de un panel o una pestaña. (estadoVacio sigue valiendo para el formato compacto.)
 */
export function vacio(o) {
  const tono = o.tono || 'neutro';
  return h('div', { class: `vacio-g${tono !== 'neutro' ? ' ' + tono : ''}${o.borde ? ' borde' : ''}`, role: 'status' },
    h('span', { class: 'big', 'aria-hidden': 'true' }, icono(o.icono || (tono === 'celebrar' ? 'ok' : tono === 'aviso' ? 'alert' : 'info'))),
    h('b', {}, o.titulo),
    o.texto ? h('p', {}, typeof o.texto === 'string' ? (limpiaTexto(o.texto) || 'Todavía no hay datos de hoy.') : o.texto) : null,
    quienHumano(o.quien) ? h('span', { class: 'quien' }, h('span', { class: 'av' }, iniciales(quienHumano(o.quien))), `Lo arregla: ${quienHumano(o.quien)}`) : null,
    o.accion || null,
    o.tecnico && VISTA.direccion ? h('details', { class: 'que-es' }, h('summary', {}, 'Detalle técnico'), h('p', { class: 'sub' }, o.tecnico)) : null);
}

// ------------------------------------------------------- selector de cliente
/**
 * selectorCliente({ clientes, actual, alElegir, detalle, insignia, etiqueta })
 *   Igual al de la ficha v3: botón con logo, nombre y account; al pulsar, buscador con la lista (logo, nombre,
 *   account y salud). Teclado: ↑ ↓ Intro Esc. Pásale SOLO ctx.clientesVisibles (lo que la persona puede abrir).
 *   detalle(c) → texto de la segunda línea (por defecto el responsable). insignia(c) → Node a la derecha
 *   (por defecto la salud en un chip de color). alElegir(cliente). el.cliente() da el actual.
 *   Ronda 10: placeholder, etiquetaBuscar, etiquetaLista, nada (texto sin resultados) y logo(c) → Node, para usarlo con
 *   otras listas (selectorPersona lo usa con avatares).
 */
export function selectorCliente(o) {
  const lista = o.clientes || [];
  const det = o.detalle || (c => c.responsable || c.responsable_texto || 'sin account');
  const insignia = o.insignia || (c => (c.salud === null || c.salud === undefined) ? null
    : chipEstado(semaforo(c.salud, SALUD), String(c.salud)));
  let actual = lista.find(c => c.id === o.actual) || lista[0] || null;
  const logo = o.logo || (c => logoCliente(c));
  const base = uid('sc');
  const caja = h('div', { class: 'selcli' });
  const boton = h('button', { type: 'button', class: 'sel-bt', 'aria-haspopup': 'listbox', 'aria-expanded': 'false', disabled: !lista.length || null });
  let pop = null, filtrados = [], sel = 0;
  const pintarBoton = () => boton.replaceChildren(
    actual ? logo(actual) : h('span', { class: 'logo-cli' }, icono(o.iconoVacio || 'cli', { clase: 's' })),
    h('span', { class: 't' }, h('b', {}, actual ? actual.nombre : (o.sinNada || 'Sin clientes')), h('span', {}, actual ? det(actual) : (o.sinNadaTexto || 'No tienes clientes que abrir'))),
    h('span', { class: 'sr' }, `. ${o.etiqueta || 'Cambiar de cliente'}`),
    icono('chev'));
  const cerrar = (foco = true) => {
    if (!pop) return;
    pop.remove(); pop = null; boton.setAttribute('aria-expanded', 'false');
    document.removeEventListener('pointerdown', fuera, true);
    if (foco) boton.focus();
  };
  const fuera = e => { if (!caja.contains(e.target)) cerrar(false); };
  const elegir = c => { if (!c) return; actual = c; pintarBoton(); cerrar(); o.alElegir?.(c); };
  const abrir = () => {
    if (pop || !lista.length) return;
    const input = h('input', { type: 'text', role: 'combobox', 'aria-expanded': 'true', 'aria-controls': `${base}-ls`, 'aria-autocomplete': 'list', autocomplete: 'off', placeholder: o.placeholder || 'Buscar cliente o account…', 'aria-label': o.etiquetaBuscar || 'Buscar cliente' });
    const ul = h('ul', { class: 'ls', id: `${base}-ls`, role: 'listbox', 'aria-label': o.etiquetaLista || 'Clientes' });
    const pintarLista = () => {
      const q = normalTxt(input.value.trim());
      filtrados = lista.filter(c => !q || normalTxt(c.nombre).includes(q) || normalTxt(det(c)).includes(q));
      sel = Math.min(sel, Math.max(0, filtrados.length - 1));
      if (!filtrados.length) { ul.replaceChildren(h('li', { class: 'nada', role: 'option', 'aria-disabled': 'true' }, o.nada || 'Ningún cliente con ese nombre entre los tuyos.')); input.removeAttribute('aria-activedescendant'); return; }
      ul.replaceChildren(...filtrados.map((c, i) => h('li', { id: `${base}-o${i}`, role: 'option', 'aria-selected': String(i === sel), class: c === actual ? 'actual' : null,
        on: { click: () => elegir(c), mousemove: () => { if (sel !== i) { sel = i; marcar(); } } } },
        logo(c), h('span', { class: 't' }, h('b', {}, c.nombre), h('span', {}, det(c))), h('span', { class: 'x' }, insignia(c)))));
      marcar();
    };
    const marcar = () => {
      ul.querySelectorAll('[role=option]').forEach((li, i) => li.setAttribute('aria-selected', String(i === sel)));
      if (filtrados.length) { input.setAttribute('aria-activedescendant', `${base}-o${sel}`); document.getElementById(`${base}-o${sel}`)?.scrollIntoView({ block: 'nearest' }); }
    };
    input.addEventListener('input', () => { sel = 0; pintarLista(); });
    input.addEventListener('keydown', e => {
      if (e.key === 'ArrowDown') { e.preventDefault(); sel = Math.min(filtrados.length - 1, sel + 1); marcar(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); sel = Math.max(0, sel - 1); marcar(); }
      else if (e.key === 'Enter') { e.preventDefault(); elegir(filtrados[sel]); }
      else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); cerrar(); }
      else if (e.key === 'Tab') cerrar(false);
    });
    pop = h('div', { class: 'pop' }, input, ul);
    sel = Math.max(0, lista.indexOf(actual));
    caja.append(pop);
    capaFlotante(pop, boton);   // V3a: capa por encima de todo ANTES de pintar la lista (si no, el scroll a la opción elegida movía la página)
    boton.setAttribute('aria-expanded', 'true');
    pintarLista();
    input.focus({ preventScroll: true });
    document.addEventListener('pointerdown', fuera, true);
  };
  boton.addEventListener('click', () => (pop ? cerrar() : abrir()));
  pintarBoton();
  caja.append(boton);
  caja.cliente = () => actual;
  caja.abrir = abrir;
  return caja;
}

/**
 * selectorPersona({ personas, actual, alElegir, etiqueta = 'Cambiar de persona', placeholder = 'Buscar persona…', detalle })
 *   Ronda 10 (N6 · Agenda, Horas): el selector de persona CON BUSCADOR (el de cliente con avatares de iniciales).
 *   personas: [{ id | persona_id, nombre, puesto?, grupo? }]. detalle(p) → segunda línea (por defecto puesto o grupo).
 *   alElegir(persona original). el.persona() da la actual; el.valor() su id.
 */
export function selectorPersona(o = {}) {
  const lista = (o.personas || []).map(p => ({ ...p, id: p.id ?? p.persona_id, _orig: p }));
  const el = selectorCliente({ clientes: lista, actual: o.actual, etiqueta: o.etiqueta || 'Cambiar de persona',
    placeholder: o.placeholder || 'Buscar persona…', etiquetaBuscar: 'Buscar persona', etiquetaLista: 'Personas',
    nada: 'Nadie con ese nombre.', sinNada: 'Sin personas', sinNadaTexto: 'No hay personas que elegir', iconoVacio: 'eq',
    detalle: o.detalle || (p => p.puesto || p.grupo || ''), insignia: o.insignia || (() => null),
    logo: p => h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(p.nombre)),
    alElegir: p => o.alElegir?.(p._orig) });
  el.classList.add('selper');
  el.persona = () => el.cliente()?._orig || null;
  el.valor = () => el.cliente()?.id ?? null;
  return el;
}

// ------------------------------------------------------------ tabla apilable
/**
 * tablaApilable({ columnas, filas, alPulsar, puedePulsar, etiquetaFila, vacio, controles })
 *   Tabla sencilla (sin barra de filtros) que en móvil (< 640 px) se apila en tarjetas: cada celda lleva su
 *   etiqueta y la columna principal: true hace de título. Para listas cortas dentro de un panel o una pestaña.
 *   Con controles: true (o con buscar/filtros) es tablaDensa con búsqueda, filtros y orden.
 *   columnas: [{ clave, titulo, num?, principal?, celda?: fila => Node|texto }]
 */
export function tablaApilable(o) {
  if (o.controles || o.buscar || o.filtros) return tablaDensa({ ...o, apilable: true });
  if (!o.filas?.length) return vacio({ icono: 'vacio', titulo: 'No hay nada que enseñar', ...(o.vacio || {}), texto: o.vacio?.texto || o.vacio?.porque });
  // Ronda 5: más de 50 filas → misma paginación que tablaDensa (porPagina, «Ver más»).
  if ((o.porPagina === undefined ? 50 : o.porPagina) && o.filas.length > (o.porPagina || 50)) return tablaDensa({ ...o, apilable: true });
  const columnas=(o.columnas||[]).map(cabeceraCompacta421);
  const thead = h('thead', {}, h('tr', {}, columnas.map(c => h('th', { scope: 'col', class: c.num ? 'num' : null,title:c.tituloCompleto||null,'aria-label':c.tituloCompleto||null }, c.titulo))));
  const tbody = h('tbody', {}, o.filas.map(r => {
    const tr = h('tr', {}, columnas.map(c => h('td', { class: [c.num ? 'num' : '', c.principal ? 'principal' : ''].join(' ').trim() || null, 'data-l': c.tituloMovil||c.titulo,title:c.tituloCompleto||null }, c.celda ? c.celda(r) : celdaPorDefecto(r[c.clave]))));
    if (o.alPulsar && (!o.puedePulsar || o.puedePulsar(r))) {
      tr.classList.add('clic'); tr.tabIndex = 0;
      if (o.etiquetaFila) tr.setAttribute('aria-label', o.etiquetaFila(r));
      tr.addEventListener('click', e => { if (!e.target.closest('a,button')) o.alPulsar(r); });
      tr.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target === tr) { e.preventDefault(); o.alPulsar(r); } });
    }
    return tr;
  }));
  return h('div', { class: 'tabla-scroll' }, h('table', { class: 'densa apilable' }, thead, tbody));
}

// --------------------------------------------------- contacto: llamar, WhatsApp, correo
/**
 * normalizarTelefono('6XX XX XX XX') → { e164: '+346XXXXXXXX', intl: '346XXXXXXXX', mostrar: '+34 6XX XX XX XX',
 *   tel, sip, wa, extension } | null. La regla vive en modulos/_telefono.js (gemelo de telefono.py, 3-oct):
 *   guardar y marcar con «+» y sin espacios; enseñar con espacios; lo que no cuadra → null (no se marca).
 */
export function normalizarTelefono(t) {
  return telefonoComun(t);
}

/** avisoFlotante('Copiado') · aviso breve abajo (2,4 s), leído por lectores de pantalla. */
export function avisoFlotante(texto, { icono: ico = 'ok' } = {}) {
  document.querySelector('.tostada')?.remove();
  const el = h('div', { class: 'tostada', role: 'status', 'aria-live': 'polite' }, icono(ico, { clase: 's' }), texto);
  document.body.append(el);
  setTimeout(() => el.remove(), 2400);
  return el;
}

/** copiar(texto, que) · copia al portapapeles y avisa. Nunca la uses con contraseñas ni claves (R10). */
export async function copiar(texto, que = 'Copiado') {
  try { await navigator.clipboard.writeText(texto); avisoFlotante(`${que}: ${String(texto).slice(0, 60)}`); }
  catch {
    const t = h('textarea', { style: { position: 'fixed', opacity: '0' } }); t.value = texto; document.body.append(t); t.select();
    let ok = false; try { ok = document.execCommand('copy'); } catch { /* nada */ }
    t.remove(); avisoFlotante(ok ? `${que}: ${String(texto).slice(0, 60)}` : 'No se pudo copiar', { icono: ok ? 'ok' : 'alert' });
  }
}

/**
 * botonesContacto({ nombre, telefono, correo, modo: 'lista' | 'cabecera', whatsapp: true, fuente })
 *   Lo mismo que el portal de clientes: llamar (sip: → app de Zadarma), WhatsApp (wa.me) y copiar; correo (mailto:) y copiar.
 *   modo 'lista': filas anchas con el número o el correo a la vista (pestaña Contactos).
 *   modo 'cabecera': botones «Llamar a Ana» (principal), «WhatsApp» y «Correo» (cabecera de la ficha).
 *   Llamar de un clic con «callback» de Zadarma y enviar llegan en W1: entonces cambia solo este componente.
 *   El módulo decide si la persona puede ver el teléfono (ctx.ver) ANTES de pasarlo.
 */
export function botonesContacto(o) {
  const tel = normalizarTelefono(o.telefono);
  const quien = String(o.nombre || '').trim();
  const corto = quien.split(/\s+/)[0] || 'cliente';
  if (o.modo === 'cabecera') {
    return h('div', { class: 'contacto-cab' },
      tel ? h('a', { class: 'bt pri', href: tel.sip, title: `Llamar a ${quien || tel.mostrar} con Zadarma` }, icono('phone'), `Llamar a ${corto}`) : null,
      tel && o.whatsapp !== false ? h('a', { class: 'bt wa', href: tel.wa, target: '_blank', rel: 'noopener', title: `WhatsApp a ${quien || tel.mostrar}` }, icono('wa'), 'WhatsApp') : null,
      o.correo ? h('a', { class: 'bt', href: `mailto:${o.correo}`, title: `Escribir a ${o.correo}` }, icono('mail'), 'Correo') : null,
      ...llamadasCliente(o, tel),
      !tel && !o.correo ? h('span', { class: 'sub' }, 'Sin teléfono ni correo de contacto') : null);
  }
  const filas = [];
  if (tel) filas.push(h('div', { class: 'contacto' },
    h('a', { class: 'main', href: tel.sip, title: 'Llamar con Zadarma' }, icono('phone'), h('span', {}, quien ? [h('b', {}, quien), ' · '] : null, tel.mostrar)),
    o.whatsapp !== false ? h('a', { class: 'sq wa', href: tel.wa, target: '_blank', rel: 'noopener', 'aria-label': `WhatsApp a ${quien || tel.mostrar}`, title: 'Abrir WhatsApp' }, icono('wa')) : null,
    h('button', { type: 'button', class: 'sq', 'aria-label': `Copiar el teléfono ${tel.mostrar}`, title: 'Copiar teléfono', on: { click: () => copiar(tel.e164, 'Teléfono copiado') } }, icono('copy'))));
  if (o.correo) filas.push(h('div', { class: 'contacto' },
    h('a', { class: 'main', href: `mailto:${o.correo}`, title: 'Escribir correo' }, icono('mail'), h('span', {}, !tel && quien ? [h('b', {}, quien), ' · '] : null, o.correo)),
    h('button', { type: 'button', class: 'sq', 'aria-label': `Copiar el correo ${o.correo}`, title: 'Copiar correo', on: { click: () => copiar(o.correo, 'Correo copiado') } }, icono('copy'))));
  if (!filas.length) filas.push(h('p', { class: 'sub' }, `Sin teléfono ni correo${quien ? ` de ${quien}` : ''}.`));
  if (o.fuente) filas.push(h('span', { class: 'sub', style: { fontSize: '12px' } }, `Fuente: ${o.fuente}`));
  return h('div', { class: 'contactos' }, filas);
}

/** 3-oct · «Te llamo y te conecto» (Zadarma, hoy simulado) y «Videollamada» con el cliente (Zoom), en la cabecera de la
 *  ficha. El servidor decide (avisos.py → llamadas.py): solo quien lleva el cliente, y solo números de sus contactos. */
function llamadasCliente(o, tel) {
  const RO = window.RO;
  if (!RO?.api || !RO.estado?.servidor) return [];
  let cid = o.cliente_id;
  if (!cid) { const m = /^#\/ficha\/([^/?]+)/.exec(location.hash || ''); try { cid = m ? decodeURIComponent(m[1]) : null; } catch { cid = null; } }
  if (!cid) return [];
  const verComo = RO.estado.persona?.id !== RO.estado.real?.id;
  const pedir = async (ruta, cuerpo) => {
    if (verComo) { avisoFlotante('Estás en «ver como»: es solo lectura.', { icono: 'candado' }); return null; }
    try { return await RO.api(ruta, { metodo: 'POST', cuerpo }); } catch (e) { avisoFlotante(String(e?.message || 'No se pudo'), { icono: 'alert' }); return null; }
  };
  return [
    tel ? h('button', { type: 'button', class: 'bt', title: 'Zadarma llama primero a tu extensión y, al descolgar, al cliente (hoy simulado)',
      on: { click: async () => { const r = await pedir('canales/llamar', { cliente_id: cid, telefono: tel.e164 }); if (r) avisoFlotante(r.texto, { icono: 'phone' }); } } }, icono('auricular'), 'Te llamo y te conecto') : null,
    h('button', { type: 'button', class: 'bt', title: 'Videollamada con el cliente: abre Zoom con tu cuenta para mandarle el enlace',
      on: { click: async () => { const r = await pedir('canales/videollamada', { para: 'cliente', cliente_id: cid }); if (r?.url) { window.open(r.url, '_blank', 'noopener'); avisoFlotante(r.texto || 'Videollamada abierta.', { icono: 'video' }); } } } }, icono('video'), 'Videollamada'),
  ].filter(Boolean);
}

// ------------------------------------------------------ extras de la ficha v3
/**
 * barraEtapas(etapas, actual) · Firma → Arranque · 14 días → Optimización · día 90 → Consolidado.
 *   etapas: [{ texto, icono }] · actual: índice (las anteriores salen hechas). Sin argumentos usa las de la ficha v3.
 */
export function barraEtapas(etapas, actual = -1) {
  const lista = etapas || [{ texto: 'Firma', icono: 'flag' }, { texto: 'Arranque · 14 días', icono: 'rocket' }, { texto: 'Optimización · día 90', icono: 'zap' }, { texto: 'Cliente consolidado', icono: 'heart' }];
  return h('ol', { class: 'etapas', 'aria-label': 'Etapa del cliente' },
    lista.map((e, i) => h('li', { class: i < actual ? 'hecha' : i === actual ? 'actual' : null, 'aria-current': i === actual ? 'step' : null }, icono(e.icono || 'flag', { clase: 's' }), h('span', {}, e.texto))));
}

/** listaConIcono([{ icono, texto, extra, href, estado }]) · filas con icono (últimos movimientos, accesos…). */
export function listaConIcono(items, { vacio: v } = {}) {
  if (!items.length) return vacio(v || { titulo: 'Nada todavía', icono: 'vacio' });
  return h('ul', { class: 'lista-i' }, items.map(it => h('li', {},
    h('span', { class: `ico-c s ${it.estado || 'gris'}` }, icono(it.icono || 'doc')),
    h('span', { class: 't' }, it.href ? h('a', { href: it.href, target: /^https?:/.test(it.href) ? '_blank' : null, rel: /^https?:/.test(it.href) ? 'noopener' : null }, it.texto) : it.texto),
    it.extra ? h('span', { class: 'x' }, it.extra) : null)));
}

// ---------------------------------------------- barras, embudo y ventanas (E0 ronda 3, D-P-CAP3)
// Sacados de Captación para que Informe del cliente, Salud del CRM, Bandeja o Mi día los reutilicen.

/**
 * barraProgreso({ valor, max = 100, estado: 'verde'|'ambar'|'rojo'|null, marca, etiqueta })
 *   marca = posición de una línea de referencia (p. ej. el objetivo o el ritmo del mes), en las mismas unidades.
 */
export function barraProgreso({ valor = 0, max = 100, estado = null, marca = null, etiqueta } = {}) {
  const pct = v => Math.max(0, Math.min(100, max ? (Number(v) / max) * 100 : 0));
  return h('div', { class: 'barra-prog', role: 'img', 'aria-label': etiqueta || `${fmt.num(valor)} de ${fmt.num(max)}` },
    h('i', { class: estado || null, style: { width: `${pct(valor)}%` } }),
    marca !== null && marca !== undefined ? h('b', { style: { left: `${pct(marca)}%` }, 'aria-hidden': 'true' }) : null);
}

/**
 * barraApilada({ partes: [{ valor, texto, estado?: 'verde'|'ambar'|'rojo'|'gris'|'azul' }], total?, etiqueta, leyenda = true })
 *   Ronda 10 (N6): una barra horizontal con sus partes (p. ej. horas facturables / internas / sin imputar) y la leyenda
 *   con cifra y %. Sin estado, las partes van en los colores de serie (azul de RO, naranja, verde azulado, violeta).
 */
export function barraApilada({ partes = [], total, etiqueta, leyenda = true, formato = v => fmt.num(v) } = {}) {
  const ok = partes.filter(x => typeof x.valor === 'number' && x.valor > 0);
  const suma = total || ok.reduce((a, x) => a + x.valor, 0);
  const clase = (x, i) => (x.estado ? `e-${x.estado}` : `s-${(i % 4) + 1}`);
  const pct = v => (suma ? (v / suma) * 100 : 0);
  const texto = ok.map(x => `${x.texto}: ${formato(x.valor)} (${fmt.num(pct(x.valor), 0)} %)`).join(' · ');
  return h('div', { class: 'barra-apil' },
    h('div', { class: 'barra-apil-b', role: 'img', 'aria-label': `${etiqueta ? etiqueta + ': ' : ''}${texto || 'sin dato'}` },
      ok.map((x, i) => h('i', { class: clase(x, partes.indexOf(x)), style: { width: `${pct(x.valor)}%` }, title: `${x.texto}: ${formato(x.valor)}` }))),
    leyenda && ok.length ? h('ul', { class: 'barra-apil-ley' }, ok.map(x => h('li', {}, h('i', { class: clase(x, partes.indexOf(x)), 'aria-hidden': 'true' }),
      h('span', {}, x.texto), h('b', {}, formato(x.valor)), h('small', {}, `${fmt.num(pct(x.valor), 0)} %`)))) : null);
}

/**
 * embudoBarras([{ etiqueta, valor, estado?, icono?, nota? }], { max? })
 *   Una fila por paso (contactos → citas → celebradas → …) con su barra proporcional al primero (o a max).
 */
export function embudoBarras(pasos = [], { max } = {}) {
  const tope = max ?? Math.max(1, ...pasos.map(p => Number(p.valor) || 0));
  return h('div', { class: 'embudo-barras' }, pasos.map(p => h('div', { class: 'et' },
    h('span', {}, p.icono ? icono(p.icono) : null, p.etiqueta),
    barraProgreso({ valor: p.valor || 0, max: tope, estado: p.estado || null, etiqueta: `${p.etiqueta}: ${fmt.num(p.valor)}` }),
    h('span', { class: 'n', title: p.nota || null }, p.valor === null || p.valor === undefined ? '—' : fmt.num(p.valor)))));
}

/**
 * ventanas([{ titulo: '7 días', valor, unidad?, sub? }]) · cifras de la misma métrica en varias ventanas (7/14/30/90 días).
 */
export function ventanas(items = []) {
  return h('div', { class: 'ventanas', style: { gridTemplateColumns: `repeat(${Math.min(items.length || 1, 4)}, minmax(0, 1fr))` } },
    items.map(it => h('div', {}, h('small', {}, it.titulo),
      h('b', {}, it.valor === null || it.valor === undefined ? '—' : it.valor, it.unidad ? h('small', {}, ` ${it.unidad}`) : null),
      it.sub ? h('em', {}, it.sub) : null)));
}


// ------------------------------------------------------------- textos limpios (E0 ronda 5, I-03)
/**
 * limpiaTexto(t) · regla de estilo de la app: fuera códigos internos (D-29, G2, W3, C-D3, E10…), nombres de fichero
 * (data/alarmas.json), ⭐ y ⚠️. Lo que va entre «» es texto del cliente y no se toca. Los códigos y ficheros se pueden
 * enseñar solo en un «¿De dónde sale?» plegado (deDondeSale()). Misma regla que limpia_texto() de build_data.py.
 * Tile y fichaIndicador ya la aplican a etiqueta, contexto y umbral.
 */
export function formatoTexto(t) {
  if (typeof t !== 'string' || !t) return t;
  const mes = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  const fecha = (a, m, d) => `${Number(d)}-${mes[Number(m) - 1] || m}`;   // V3a (44 §2.3): «2-oct», «sep» (nunca «sept.»)
  const formatea = x => x
    // «2026-10-02 16:04» → «2-oct, 16:04» · «2026-10-02» → «2-oct» · «2026-08» → «agosto de 2026»
    // V3a (44 §2.3): «sept.»/«sept»/«SEPT» → «sep»; «2 oct» → «2-oct» (un solo formato de día y mes)
    .replace(/\b(sept|SEPT|Sept)\.?(?=[\s,;)\d-]|$)/g, m => (m[0] === 'S' && m[1] === 'E' ? 'SEP' : m[0] === 'S' ? 'Sep' : 'sep'))
    .replace(/\b(\d{1,2}) (ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\b(?![\wáéíóúñ])(?!\s+de\b)/g, '$1-$2')
    .replace(/\b(20\d\d)-(\d\d)-(\d\d)[ T](\d\d:\d\d)(?::\d\d)?\b/g, (_, a, m, d, hm) => `${fecha(a, m, d)}, ${hm}`)
    .replace(/\b(20\d\d)-(\d\d)-(\d\d)\b/g, (_, a, m, d) => fecha(a, m, d))
    .replace(/\b(20\d\d)-(0[1-9]|1[0-2])\b(?!-)/g, (_, a, m) => `${['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'][Number(m) - 1]} de ${a}`)
    // «1 tarea(s)» → «1 tarea» · «2 correo(s)» → «2 correos»
    .replace(/\b(\d+)\s+([a-záéíóúñ]+)\((e?s)\)/gi, (_, n, pal, suf) => `${n} ${pal}${Number(n) === 1 ? '' : suf}`)
    .replace(/([a-záéíóúñ]+)\((e?s)\)/gi, '$1$2')
    // V2-E (40_A B5): antigüedad de más de 48 h en días («lleva 478 h» → «lleva 20 días»); las horas imputadas no se tocan
    .replace(/\b(lleva|llevan|hace|espera|esperan|desde hace)\s+(\d{2,})\s?h\b/g, (m, pre, n) => (Number(n) >= 48 ? `${pre} ${Math.round(Number(n) / 24)} días` : m))
    .replace(/\b(\d{2,})\s?h\s+(sin contestar|sin respuesta|sin agente|de la firma|esperando|parad[ao]s?)\b/g, (m, n, pos) => (Number(n) >= 48 ? `${Math.round(Number(n) / 24)} días ${pos}` : m))
    // «1 correos» → «1 correo», «hace 1 días» → «hace 1 día» (V2-E, plural común)
    // decimales con coma: «7.5 h», «−51.9 %», «1.7» (no versiones v2.1 ni IP)
    .replace(/(^|[\s(−-])(\d+)\.(\d{1,2})(?=\s?(?:h\b|%|€|días?\b|x\b|veces\b|$|[\s),;]))/g, (_, pre, e, d) => `${pre}${e},${d}`)
    // miles con punto en importes y cifras grandes: «2535 €» → «2.535 €», «−7349 €» → «−7.349 €»
    .replace(/(^|[^\d.,])(\d{4,})(?=\s?(?:€|euros?\b))/g, (_, pre, n) => `${pre}${_nfDe(0).format(Number(n))}`)
    // V3a (44 §2.1): «cliente en crítico» → «cliente crítico», «3 en crítico» → «3 críticos» (un solo nombre: Crítico)
    .replace(/\b(clientes?|cuentas?)\s+en\s+crítico\b/gi, (_, n) => `${n} ${/s$/i.test(n) ? (/^c[uU]/.test(n) ? 'críticas' : 'críticos') : (/^c[uU]/.test(n) ? 'crítica' : 'crítico')}`)
    .replace(/\b(\d+)\s+en\s+crítico\b/g, (_, n) => `${n} ${Number(n) === 1 ? 'crítico' : 'críticos'}`)
    // Glosario del coordinador (3-oct): Crítico · Vigilar · Bien. «cliente en atención» → «cliente a vigilar», «3 en atención»
    // → «3 a vigilar», «crítico · atención · bien» → «crítico · vigilar · bien». «30 de atención» (salud) no se toca.
    .replace(/\b(clientes?|cuentas?|\d+)\s+en\s+atención\b/gi, '$1 a vigilar')
    .replace(/\b(crítico|Crítico|CRÍTICO)(\s*(?:,|·|\/|y|o)\s*)(atención|Atención|ATENCIÓN)\b/g, (_, c, sep, a) => `${c}${sep}${a[0] === 'a' ? 'vigilar' : a[1] === 'T' ? 'VIGILAR' : 'Vigilar'}`)
    // dos puntos sueltos y huecos vacíos: «Propuesta : verde» → «Propuesta: verde»
    .replace(/\s+:\s/g, ': ')
    .replace(/^\s*:\s*/, '')
    .replace(/\(\s*\)/g, '')
    .replace(/\s{2,}/g, ' ');
  // «1 correos» → «1 correo», «hace 1 días» → «hace 1 día», «1 vencidas» → «1 vencida» (plural común, V2-E + V3a)
  return t.split(/(«[^»]*»)/).map(x => (x.startsWith('«') ? x : _singular1(formatea(x)))).join('').trim();
}

export function limpiaTexto(t) {
  if (typeof t !== 'string' || !t) return t;
  t = formatoTexto(t);
  const limpia = x => x
    .replace(/\b[\w./-]+\.(?:json|py|md|js|csv|xlsx)\b/g, '')
    // V3a (44 §0.2): sin huecos al quitar un código («llega con W1.» → «llega más adelante.»; «… en G2.» → «….»)
    .replace(/\b(llega|llegan|llegará|llegarán|vendrá|vendrán|irá|irán|saldrá|saldrán|estará|estarán)\s+con\s+(?!M365\b)(?:D|G|W|C|E|M|P|B|I)-?[A-Z]{0,2}\d{1,3}\b/g, '$1 más adelante')
    .replace(/\s+(?:con|en|de|tras|hasta|desde|por|para|a|según)\s+(?!M365\b)(?:D|G|W|C|E|M|P|B|I)-?[A-Z]{0,2}\d{1,3}\b(?=\s*(?:[.,;:)]|$))/g, '')
    .replace(/\s*\((?:[A-Z]{1,2}-?[A-Z]?\d+[a-z]?(?:[,·/ y]+)?)+\)/g, '')
    .replace(/\b(?:D|G|W|C|E|M|P|B|I)-?[A-Z]{0,2}\d{1,3}\b(?:\s*§\s*\d+)?/g, '')
    .replace(/⭐|⚠️|⚠/g, '')
    .replace(/\(\s*\)/g, '')
    .replace(/\s+([,.;:)])/g, '$1')
    .replace(/\s{2,}/g, ' ')
    // L-39: un vacío no cuenta cómo se genera el dato. Sin el nombre del fichero, «No existe. Se generan con.» no dice nada.
    .replace(/\bSe generan?\s+con\s*\.?\s*/gi, '');
  return t.split(/(«[^»]*»)/).map(x => (x.startsWith('«') ? x : limpia(x))).join('').trim().replace(/^[\s·,;]+|[\s·,;]+$/g, '')
    .replace(/^No existe\.?$/i, 'Todavía no hay datos de esta pantalla. Los genera la tubería (operaciones).');
}

/** deDondeSale(texto) · plegado «¿De dónde sale?» para la referencia técnica (decisión, fichero, regla). */
/** Ronda 6 (F-05): la carcasa dice quién mira. Lo técnico (ficheros, reglas, «Lo arregla: Claude») solo para dirección. */
const VISTA = { direccion: false };
export function configurarVista({ direccion = false } = {}) { VISTA.direccion = !!direccion; }

export function deDondeSale(texto) {
  if (!texto || !VISTA.direccion) return null;
  return h('details', { class: 'que-es' }, h('summary', {}, '¿De dónde sale?'), h('p', { class: 'sub', style: { margin: '6px 0 0' } }, texto));
}

/** V2-E (40_A M6) · nombre del departamento para la persona («administracion» → «Administración», «rrhh» → «RRHH»).
 *  Los ids internos de departamento nunca salen a la vista: quitaPrefijoDepartamento() los cambia al pintar. */
export const NOMBRE_DEPARTAMENTO = { web: 'Web', seo: 'SEO', crm: 'CRM', publicidad: 'Publicidad', redes: 'Redes', accounts: 'Accounts',
  altas: 'Altas', administracion: 'Administración', rrhh: 'RRHH', direccion: 'Dirección', operaciones: 'Operaciones', produccion: 'Producción',
  proyectos: 'Proyectos', ventas: 'Ventas', outreach: 'Prospección', setters: 'Setters' };
export const nombreDepartamento = id => NOMBRE_DEPARTAMENTO[id] || (id ? String(id).replace(/_/g, ' ') : '');
const RE_DEP = new RegExp(`^(\\s*)(?:(${Object.keys(NOMBRE_DEPARTAMENTO).join('|')})(\\s+·\\s+)|(administracion|rrhh|direccion|produccion)(\\s*)$)`);
/** «administracion · POWER GLOBAL…» → «Administración · POWER GLOBAL…» (solo al principio y con el id en minúsculas). */
export const quitaPrefijoDepartamento = t => (typeof t === 'string' ? t.replace(RE_DEP, (_, sp, id, sep, id2, fin) => `${sp}${NOMBRE_DEPARTAMENTO[id || id2]}${sep || fin || ''}`) : t);

/** nombrePersona(id, personas) · nombre corto de personas.json; nunca el id crudo («mili» → «Mili»). */
export function nombrePersona(id, personas = []) {
  if (!id) return '—';
  const p = personas.find(x => x.id === id);
  return p ? (p.alias || p.nombre) : 'persona sin ficha';
}

// ============================================================================
// PANELES V4 (3-oct-2026) · piezas de los paneles de dinero, al nivel de QuickBooks, Xero, ChartMogul, Pigment y Databox.
// Especificación: ../48_BENCHMARK_DASHBOARDS.md §2 (patrones) y §4 (pantalla a pantalla). Las usan Finanzas y Dinero por
// cliente; el Panel de dirección y Ventas de RO las reutilizarán. Todas devuelven HTMLElement, sin colores sueltos (clases de
// estilos.css, bloque «Paneles v4») y con el texto entero en aria-label. Umbrales: SOLO con la fuente del 48; los que el 48
// marca «no colorear» van en gris (umbral.colorea: false). Ejemplos en vivo: Sistema › Componentes.
// ============================================================================

/** alMedir(el, dibujar) · llama a dibujar(ancho) cada vez que el elemento cambia de ancho (dibujo en píxeles reales). */
function alMedir(el, dibujar) {
  let ultimo = 0;
  if (typeof ResizeObserver === 'function') {
    new ResizeObserver(ent => { const W = Math.round(ent[0].contentRect.width); if (W && W !== ultimo) { ultimo = W; dibujar(W); } }).observe(el);
  } else requestAnimationFrame(() => dibujar(el.clientWidth || 600));
}
const _num = v => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const _signo = (v, f) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${f(Math.abs(v))}`;

/** enlaceFuente(href, quien) · «Quien · Ver fuente ↗» (fuera de la app, en otra pestaña; dentro, en la misma). */
export function enlaceFuente(href, quien) {
  if (!href) return quien ? h('span', { class: 'fuente-t' }, quien) : null;
  const fuera = /^https?:/i.test(href);
  return h('a', { class: 'fuente-a', href, target: fuera ? '_blank' : null, rel: fuera ? 'noopener noreferrer' : null, title: quien ? `Fuente: ${quien}` : null },
    `${quien ? `${quien} · ` : ''}Ver fuente ↗`);
}

/**
 * minilinea(valores, { x, formato, formatoX, umbral, etiqueta, alto = 32 }) · la línea pequeña de tendencia (12 meses) que
 *   llevan las tarjetas de Geckoboard, Databox y Pigment. Sin ejes: punto en el último valor y, si se da, el umbral discontinuo.
 *   Con menos de 2 valores devuelve null (no se pinta nada). El resumen («de X a Y, mínimo, máximo») va en aria-label y title.
 */
export function minilinea(valores = [], { x = [], formato = v => fmt.num(v), formatoX = _etiquetaX, umbral = null, etiqueta = 'Tendencia', alto = 32 } = {}) {
  const ys = valores.map(_num);
  const ok = ys.filter(v => v !== null);
  if (ok.length < 2) return null;
  const ini = ys.find(v => v !== null), fin = [...ys].reverse().find(v => v !== null);
  const conU = Number.isFinite(umbral) ? [umbral] : [];
  const min = Math.min(...ok, ...conU), max = Math.max(...ok, ...conU);
  const desde = x.length ? ` (${formatoX(x[0])} a ${formatoX(x[x.length - 1])})` : '';
  const txt = `${etiqueta}${desde}: de ${formato(ini)} a ${formato(fin)} · mínimo ${formato(Math.min(...ok))} · máximo ${formato(Math.max(...ok))}`;
  const caja = h('div', { class: 'kpi-spark', role: 'img', 'aria-label': txt, title: txt, style: { height: `${alto}px` } });
  alMedir(caja, W => {
    caja.querySelector('svg')?.remove();
    const H = alto, p = 4, n = ys.length;
    const X = i => p + (W - 2 * p) * (n === 1 ? 0.5 : i / (n - 1));
    const Y = v => p + (H - 2 * p) * (1 - (v - min) / ((max - min) || 1));
    const svg = s('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, 'aria-hidden': 'true' });
    if (conU.length) svg.append(s('line', { class: 'umbral-l', x1: p, x2: W - p, y1: Y(umbral), y2: Y(umbral) }));
    let d = '', abierto = false;
    ys.forEach((v, i) => { if (v === null) { abierto = false; return; } d += `${abierto ? 'L' : 'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; abierto = true; });
    svg.append(s('path', { class: 'linea', d }));
    let u = n - 1; while (u >= 0 && ys[u] === null) u--;
    svg.append(s('circle', { class: 'punto', cx: X(u), cy: Y(ys[u]), r: 3 }));
    caja.append(svg);
  });
  return caja;
}

/** Las tres comparaciones de los buenos (Jirav, Databox, Fathom): mes anterior · mismo mes del año pasado · objetivo o plan. */
export const COMPARAR_CON = [['mes_ant', 'Mes anterior', 'cal'], ['anio_ant', 'Mismo mes del año pasado', 'hist'], ['objetivo', 'Objetivo o plan', 'flag']];
const NOMBRE_COMPARAR = { mes_ant: 'mes anterior', anio_ant: 'dato del año pasado', objetivo: 'objetivo' };
/** selectorComparar({ clave, valor = 'mes_ant', alCambiar }) · «Comparar con» arriba de cada pantalla de dinero (se recuerda). */
export function selectorComparar({ clave = 'comparar-con', valor = 'mes_ant', alCambiar, opciones = COMPARAR_CON } = {}) {
  return chipsFiltro({ etiqueta: 'Comparar con', clave, valor, alCambiar, opciones: opciones.map(([v, t, ico]) => ({ valor: v, texto: t, icono: ico || 'cal' })) });
}

/**
 * lineaComparacion({ num, ref, modo = 'pct' | 'abs' | 'puntos', mejorSi = 'alto' | 'bajo' | 'neutro', texto, formato })
 *   «▲ 12 % frente a julio» con el color según la dirección buena de la métrica (Geckoboard, Jirav: un gasto que baja es
 *   verde). Devuelve null si falta alguna de las dos cifras. La usan tarjetaKpi() y la cifra que manda de cada pantalla.
 */
export function lineaComparacion({ num, ref, modo = 'pct', mejorSi = 'alto', texto, formato } = {}) {
  if (_num(ref) === null || _num(num) === null) return null;
  const delta = modo === 'pct' ? variacion(num, ref) : Math.round((num - ref) * 100) / 100;
  if (delta === null) return null;
  const sentido = mejorSi === 'neutro' || !delta ? 'igual' : (delta > 0) === (mejorSi !== 'bajo') ? 'bien' : 'mal';
  const flecha = delta > 0 ? '▲' : delta < 0 ? '▼' : '=';
  const cifra = modo === 'pct' ? `${fmt.num(Math.abs(delta), Math.abs(delta) < 10 ? 1 : 0)} %` : modo === 'puntos' ? `${fmt.num(Math.abs(delta), 1)} puntos`
    : (formato || (v => fmt.num(v)))(Math.abs(delta));
  return h('span', { class: 'tc' }, h('span', { class: sentido, title: sentido === 'bien' ? 'Va a mejor' : sentido === 'mal' ? 'Va a peor' : 'Sin juicio de mejor o peor' }, `${flecha} ${cifra}`),
    texto ? h('em', {}, texto) : null);
}

/**
 * tarjetaKpi({ icono, etiqueta, valor, unidad, num, estado, mejorSi, serie, serieX, formatoSerie, umbralSerie,
 *              comparar, comparaciones, umbral, fuente, contexto, medible, medibleDetalle, frescura, alPulsar, ir })
 *   La tarjeta estándar de un panel de dinero (48 §4): cifra grande · línea de 12 meses · comparación con flecha · contra qué
 *   se compara, en palabras · umbral escrito con su fuente · «Ver fuente ↗».
 *   · valor: el texto de la cifra («1,3»); num: el mismo número para calcular la comparación (1.32).
 *   · mejorSi: 'alto' (subir es bueno) | 'bajo' (bajar es bueno: gasto, vencido, peso del equipo) | 'neutro' (flecha en gris).
 *   · comparaciones: { mes_ant | anio_ant | objetivo: { ref, texto: 'frente a julio', modo: 'pct' | 'abs' | 'puntos', formato } };
 *     comparar: la que se enseña (la del selectorComparar). Si la tarjeta no tiene esa, lo dice en gris («sin objetivo»).
 *   · estado: lo decide quien llama con el umbral (colorCifra, semaforo); sin umbral, '' (azul neutro). Gris = no colorea.
 *   · umbral: { texto, fuente, href, fuentes: [{ fuente, href }], colorea = true } · colorea: false → «Referencia, no colorea».
 *   · fuente: { texto, href } del dato (Holded, cierre de Sofía…); href a la pestaña de la app donde está el detalle.
 *   · nota: una línea que no se corta (p. ej. «fórmula pendiente de confirmar por Tomás»), en ámbar oscuro.
 *   No es un botón entero (lleva enlaces dentro): con alPulsar sale un botón «ir» al pie.
 */
export function tarjetaKpi(o = {}) {
  const vacioValor = o.valor === null || o.valor === undefined || o.valor === '';
  const est = vacioValor ? 'gris' : (o.estado || '');
  const mejor = o.mejorSi || 'alto';
  const comps = o.comparaciones || {};
  const elegido = o.comparar || Object.keys(comps)[0];
  const c = elegido ? comps[elegido] : null;
  let comp = c ? lineaComparacion({ num: o.num, ...c, formato: c.formato || o.formatoDelta, mejorSi: mejor }) : null;
  if (!comp && elegido) comp = h('span', { class: 'tc' }, h('em', {}, c ? (c.sinDato || `${c.texto ? `${c.texto}: ` : ''}sin dato para comparar`) : `Sin ${NOMBRE_COMPARAR[elegido] || 'comparación'} para esta cifra`));
  const u = o.umbral;
  const fuentesU = u ? (u.fuentes || (u.href || u.fuente ? [{ fuente: u.fuente, href: u.href }] : [])) : [];
  const umbralEl = u ? h('p', { class: `kpi-umbral${u.colorea === false ? ' ref' : ''}` },
    h('span', {}, `${u.colorea === false ? 'Referencia, no colorea: ' : 'Umbral: '}${limpiaTexto(u.texto || '')}`),
    fuentesU.map(f => [' · ', enlaceFuente(f.href, f.fuente)])) : null;
  const sello = o.medible && o.medible !== 'hoy' ? selloMedible(o.medible, o.medibleDetalle) : null;
  const pie = o.fuente || sello || o.frescura ? h('p', { class: 'kpi-pie' },
    o.fuente ? h('span', {}, 'Dato: ', o.fuente.href ? enlaceFuente(o.fuente.href, o.fuente.texto) : o.fuente.texto) : null,
    sello, o.frescura ? frescura(o.frescura) : null) : null;
  const linea = o.serie ? minilinea(o.serie, { x: o.serieX || [], formato: o.formatoSerie || (v => fmt.num(v)), umbral: o.umbralSerie ?? null, etiqueta: `Tendencia de ${o.etiqueta}` }) : null;
  const etqTxt = typeof o.etiqueta === 'string' ? limpiaTexto(o.etiqueta) : o.etiqueta;
  return h('div', { class: `tile kpi ${est}`.trim(), role: 'group', 'aria-label': `${etqTxt}: ${vacioValor ? 'sin dato' : `${o.valor}${o.unidad ? ` ${o.unidad}` : ''}`}` },
    h('span', { class: 'tt' }, h('span', { class: `ico-c ${est}` }, icono(o.icono || 'res')), h('span', {}, etqTxt)),
    vacioValor ? h('span', { class: 'tv sin-dato' }, h('small', {}, o.sinDato ? `Sin dato · ${o.sinDato}` : 'Sin dato'))
      : h('span', { class: 'tv' }, o.valor, o.unidad ? h('small', {}, o.unidad) : null),
    linea, comp,
    o.contexto ? h('span', { class: 'tx' }, typeof o.contexto === 'string' ? limpiaTexto(o.contexto) : o.contexto) : null,
    o.nota ? h('p', { class: 'kpi-nota' }, icono('info', { clase: 's' }), h('span', {}, o.nota)) : null,
    umbralEl, pie,
    o.alPulsar ? h('button', { type: 'button', class: 'ir kpi-ir', on: { click: o.alPulsar } }, o.ir || 'Ver detalle', icono('derecha', { clase: 's' })) : null);
}

/**
 * cascada({ pasos: [{ texto, valor, tipo: 'total' | 'cambio', estado?: 'sube' | 'sube2' | 'ambar' | 'baja' }], formato, titulo,
 *           alto = 240, anchoFilas = 440, zoom, leyenda })
 *   El puente (Pigment, Baremetrics): los totales en gris desde 0; cada cambio flota desde donde acabó el anterior (verde si
 *   suma, rojo si resta; estado lo cambia, p. ej. las rebajas en ámbar). Cuota: inicial + altas + subidas − rebajas − bajas =
 *   final; beneficio: ingresos − entrega = margen bruto − estructura = beneficio. Por debajo de anchoFilas (móvil) se dibuja en
 *   filas horizontales. Pasa el ratón (o el dedo) por un paso para ver su cifra.
 */
export function cascada(o = {}) {
  const pasos = (o.pasos || []).filter(p => p && _num(p.valor) !== null);
  const f = o.formato || (v => fmt.num(v));
  const caja = h('figure', { class: 'grafico cascada', style: { margin: 0 } });
  if (o.titulo) caja.append(h('figcaption', { class: 'grafico-tit' }, o.titulo));
  if (pasos.length < 2) { caja.append(h('p', { class: 'grafico-vacio' }, icono('grafico', { clase: 's' }), o.vacio || 'Sin datos para el puente')); return caja; }
  let acum = 0;
  const T = pasos.map(p => {
    if (p.tipo === 'total') { acum = p.valor; return { ...p, a: 0, b: p.valor, cls: p.estado || 'total' }; }
    const a = acum; acum += p.valor;
    return { ...p, a, b: acum, cls: p.estado || (p.valor >= 0 ? 'sube' : 'baja') };
  });
  const txtPaso = t => `${t.texto}: ${t.tipo === 'total' ? f(t.valor) : _signo(t.valor, f)}`;
  // zoom: true → el eje no empieza en 0 (puentes con una base grande y cambios pequeños, como la cuota); los saldos se cortan
  // en el suelo del eje y se dice debajo («El eje empieza en 30.000 €»).
  const ext = T.flatMap(t => (t.tipo === 'total' ? [t.b] : [t.a, t.b]));
  let suelo = Math.min(0, ...T.flatMap(t => [t.a, t.b]));
  if (o.zoom && Math.min(...ext) > 0) {
    const mn = Math.min(...ext), mx = Math.max(...ext);
    suelo = Math.max(0, marcasRedondas(mn - (mx - mn) * 0.6, mx, 5).min);
    T.forEach(t => { if (t.tipo === 'total') t.a = suelo; });
  }
  const esc = marcasRedondas(suelo, Math.max(0, ...T.flatMap(t => [t.a, t.b])), 4);
  if (o.zoom && esc.min > 0) T.forEach(t => { if (t.tipo === 'total') t.a = esc.min; });
  // leyenda: «Saldo» para los totales y el nombre de cada paso que suma o resta (Altas, Rebajas…), sin repetir
  const ley = o.leyenda || [...new Map(T.map(t => (t.tipo === 'total' ? ['__total', { clase: t.cls, nombre: 'Saldo' }] : [t.texto, { clase: t.cls, nombre: t.texto }]))).values()];
  if (ley.length > 1) caja.append(h('div', { class: 'grafico-ley' }, ley.map(l => h('span', {}, h('i', { class: `b ${l.clase}` }), l.nombre))));
  const lienzo = h('div', { class: 'grafico-lienzo', role: 'img', 'aria-label': `${o.titulo || 'Puente'}: ${T.map(txtPaso).join(' · ')}` });
  caja.append(lienzo);
  const pct = v => ((v - esc.min) / ((esc.max - esc.min) || 1)) * 100;
  const filas = () => h('ul', { class: 'cascada-filas', 'aria-hidden': 'true' }, T.map(t => h('li', { class: t.tipo === 'total' ? 'es-total' : null },
    h('span', { class: 'cf-et' }, t.texto),
    h('span', { class: 'cf-pista' }, esc.min < 0 ? h('i', { class: 'cf-cero', style: { left: `${pct(0)}%` } }) : null,
      h('i', { class: `cf-seg ${t.cls}`, style: { left: `${pct(Math.min(t.a, t.b))}%`, width: `${Math.max(0.6, pct(Math.max(t.a, t.b)) - pct(Math.min(t.a, t.b)))}%` }, title: txtPaso(t) })),
    h('b', { class: 'cf-v' }, t.tipo === 'total' ? f(t.valor) : _signo(t.valor, f)))));
  alMedir(lienzo, W => {
    lienzo.replaceChildren();
    lienzo.style.height = '';
    if (W < (o.anchoFilas || 440)) { lienzo.append(filas()); return; }
    const H = o.alto || 240;
    lienzo.style.height = `${H}px`;
    const anchoEtiq = Math.max(...esc.marcas.map(v => String(f(v)).length)) * 7.2 + 8;
    const pl = Math.min(96, Math.max(28, anchoEtiq)), pr = 8, pt = 22, pb = 38;
    const n = T.length, slot = (W - pl - pr) / n, ancho = Math.min(64, slot * 0.62);
    const X = i => pl + slot * (i + 0.5);
    const Y = v => pt + (H - pt - pb) * (1 - (v - esc.min) / ((esc.max - esc.min) || 1));
    const svg = s('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}` });
    for (const v of esc.marcas) {
      svg.append(s('line', { class: v === 0 ? 'cero' : 'rejilla-l', x1: pl, x2: W - pr, y1: Y(v), y2: Y(v) }));
      const t = s('text', { x: pl - 8, y: Y(v) + 4, 'text-anchor': 'end' }); t.textContent = f(v); svg.append(t);
    }
    T.forEach((t, i) => {
      const y1 = Y(Math.max(t.a, t.b)), y2 = Y(Math.min(t.a, t.b));
      const r = s('rect', { class: `seg ${t.cls}`, x: X(i) - ancho / 2, y: y1, width: ancho, height: Math.max(1, y2 - y1), rx: Math.min(3, ancho / 4) });
      const tt = s('title'); tt.textContent = txtPaso(t); r.append(tt); svg.append(r);
      if (i < n - 1) svg.append(s('line', { class: 'conector', x1: X(i) + ancho / 2, x2: X(i + 1) - ancho / 2, y1: Y(t.b), y2: Y(t.b) }));
      const v = s('text', { class: 'valor-ult', x: X(i), y: y1 - 6, 'text-anchor': 'middle' });
      v.textContent = t.tipo === 'total' ? f(t.valor) : _signo(t.valor, f); svg.append(v);
      // etiqueta en 1-2 líneas que quepan en su hueco (≈ 7 px por letra a 12 px)
      const cabe = Math.max(4, Math.floor(slot / 7));
      const palabras = String(t.texto).split(/\s+/); const lineas = [''];
      for (const p of palabras) { const l = lineas[lineas.length - 1]; if (!l || (l + ' ' + p).length <= cabe) lineas[lineas.length - 1] = l ? `${l} ${p}` : p; else if (lineas.length < 2) lineas.push(p); else lineas[1] = `${lineas[1]} ${p}`; }
      lineas.forEach((l, k) => { const e = s('text', { x: X(i), y: H - pb + 16 + k * 14, 'text-anchor': 'middle' }); e.textContent = l.length > cabe + 2 ? `${l.slice(0, cabe)}…` : l; svg.append(e); });
    });
    lienzo.append(svg);
  });
  if (o.zoom && esc.min > 0) caja.append(h('p', { class: 'grafico-nota' }, `El eje empieza en ${f(esc.min)} para que se vean los cambios; los saldos van cortados.`));
  return caja;
}

/**
 * barrasGanadoPerdido({ x, ganado: [{ nombre, y, clase }], perdido: [{ nombre, y, clase }], neto = true, enCurso, formato,
 *                       formatoX, alto = 220, titulo, notaCurso })
 *   Los movimientos de la cuota de ChartMogul: lo ganado (altas, subidas) apilado por encima de 0 y lo perdido (rebajas,
 *   bajas) por debajo; la línea es el neto. El periodo en curso va RAYADO (es estimación): enCurso = n.º de periodos del final
 *   (1 = el último) o lista de índices. clase: 'sube' | 'sube2' | 'ambar' | 'baja'. «perdido» admite valores en negativo o
 *   positivo (se dibujan siempre hacia abajo). Burbuja con el desglose al pasar el ratón.
 */
export function barrasGanadoPerdido(o = {}) {
  const x = o.x || [], n = x.length;
  const f = o.formato || (v => fmt.num(v));
  const fx = o.formatoX || _etiquetaX;
  const gan = (o.ganado || []).filter(sr => Array.isArray(sr?.y));
  const per = (o.perdido || []).filter(sr => Array.isArray(sr?.y)).map(sr => ({ ...sr, y: sr.y.map(v => (_num(v) === null ? null : Math.abs(v))) }));
  const curso = new Set(Array.isArray(o.enCurso) ? o.enCurso : Number.isFinite(o.enCurso) ? Array.from({ length: o.enCurso }, (_, k) => n - 1 - k) : []);
  const sumG = i => gan.reduce((a, sr) => a + (sr.y[i] || 0), 0), sumP = i => per.reduce((a, sr) => a + (sr.y[i] || 0), 0);
  const neto = o.neto === false ? null : Array.isArray(o.neto) ? o.neto : x.map((_, i) => sumG(i) - sumP(i));
  const caja = h('figure', { class: 'grafico gp', style: { margin: 0 } });
  if (o.titulo) caja.append(h('figcaption', { class: 'grafico-tit' }, o.titulo));
  if (!n) { caja.append(h('p', { class: 'grafico-vacio' }, icono('grafico', { clase: 's' }), o.vacio || 'Sin datos en este periodo')); return caja; }
  caja.append(h('div', { class: 'grafico-ley' }, [...gan, ...per].map(sr => h('span', {}, h('i', { class: `b ${sr.clase || ''}` }), sr.nombre)),
    neto ? h('span', {}, h('i', { style: { background: 'var(--accent)' } }), 'Neto') : null,
    curso.size ? h('span', {}, h('i', { class: 'b rayado' }), o.notaCurso || 'En curso (estimado)') : null));
  const lienzo = h('div', { class: 'grafico-lienzo', style: { height: `${o.alto || 220}px` } });
  const burbuja = h('div', { class: 'grafico-burbuja', hidden: true, role: 'status' });
  lienzo.append(burbuja); caja.append(lienzo);
  const ultimo = n - 1;
  lienzo.setAttribute('aria-label', `${o.titulo || 'Movimientos'}: ${fx(x[0])} a ${fx(x[ultimo])}; último, ${[...gan, ...per].map(sr => `${sr.nombre} ${f(sr.y[ultimo] || 0)}`).join(', ')}${neto ? `, neto ${_signo(neto[ultimo], f)}` : ''}`);
  lienzo.setAttribute('role', 'img');
  const uid2 = uid('raya');
  alMedir(lienzo, W => {
    lienzo.querySelector('svg')?.remove();
    const H = o.alto || 220;
    const altos = x.map((_, i) => sumG(i)), bajos = x.map((_, i) => -sumP(i));
    const esc = marcasRedondas(Math.min(0, ...bajos, ...(neto || [])), Math.max(0, ...altos, ...(neto || [])), H >= 160 ? 5 : 3);
    const anchoEtiq = Math.max(...esc.marcas.map(v => String(f(v)).length)) * 7.2 + 8;
    const pl = Math.min(96, Math.max(28, anchoEtiq)), pr = 8, pt = 12, pb = 24;
    const slot = (W - pl - pr) / n, ancho = Math.max(3, Math.min(40, slot * 0.6));
    const X = i => pl + slot * (i + 0.5);
    const Y = v => pt + (H - pt - pb) * (1 - (v - esc.min) / ((esc.max - esc.min) || 1));
    const svg = s('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}` });
    const defs = s('defs'); const pat = s('pattern', { id: uid2, patternUnits: 'userSpaceOnUse', width: 6, height: 6, patternTransform: 'rotate(45)' });
    pat.append(s('line', { class: 'rayado-l', x1: 0, y1: 0, x2: 0, y2: 6 })); defs.append(pat); svg.append(defs);
    let ultY = Infinity;
    for (const v of esc.marcas) {
      svg.append(s('line', { class: v === 0 ? 'cero' : 'rejilla-l', x1: pl, x2: W - pr, y1: Y(v), y2: Y(v) }));
      if (Math.abs(ultY - Y(v)) < 16 && v !== 0) continue;
      const t = s('text', { x: pl - 8, y: Y(v) + 4, 'text-anchor': 'end' }); t.textContent = f(v); svg.append(t); ultY = Y(v);
    }
    const maxEtiq = Math.max(2, Math.min(8, Math.floor((W - pl - pr) / 56)));
    const paso = Math.max(1, Math.ceil(n / maxEtiq));
    for (let i = n - 1; i >= 0; i -= paso) {
      let xi = X(i), anchor = 'middle'; const ancho2 = String(fx(x[i])).length * 7 + 2;
      if (xi + ancho2 / 2 > W - 2) { xi = W - 2; anchor = 'end'; }
      if (xi - ancho2 / 2 < 2) { xi = 2; anchor = 'start'; }
      const t = s('text', { x: xi, y: H - 6, 'text-anchor': anchor }); t.textContent = fx(x[i]); svg.append(t);
    }
    for (let i = 0; i < n; i++) {
      let arriba = 0, abajo = 0;
      for (const sr of gan) { const v = sr.y[i] || 0; if (!v) continue; svg.append(s('rect', { class: `seg ${sr.clase || 'sube'}${curso.has(i) ? ' curso' : ''}`, x: X(i) - ancho / 2, y: Y(arriba + v), width: ancho, height: Math.max(1, Y(arriba) - Y(arriba + v)) })); arriba += v; }
      for (const sr of per) { const v = sr.y[i] || 0; if (!v) continue; svg.append(s('rect', { class: `seg ${sr.clase || 'baja'}${curso.has(i) ? ' curso' : ''}`, x: X(i) - ancho / 2, y: Y(-abajo), width: ancho, height: Math.max(1, Y(-abajo - v) - Y(-abajo)) })); abajo += v; }
      if (curso.has(i) && (arriba || abajo)) svg.append(s('rect', { class: 'rayado', x: X(i) - ancho / 2, y: Y(arriba), width: ancho, height: Math.max(1, Y(-abajo) - Y(arriba)), fill: `url(#${uid2})` }));
    }
    if (neto) {
      let d = ''; neto.forEach((v, i) => { if (_num(v) !== null) d += `${d ? 'L' : 'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; });
      svg.append(s('path', { class: 'linea', d, style: 'stroke:var(--accent)' }));
      neto.forEach((v, i) => { if (_num(v) !== null) svg.append(s('circle', { class: `punto${curso.has(i) ? ' curso' : ''}`, cx: X(i), cy: Y(v), r: 3, style: 'stroke:var(--accent)' })); });
    }
    const guia = s('line', { class: 'guia', x1: 0, x2: 0, y1: pt, y2: H - pb, visibility: 'hidden' }); svg.append(guia);
    const zona = s('rect', { x: pl, y: 0, width: Math.max(1, W - pl - pr), height: H, fill: 'transparent' });
    const mostrar = ev => {
      const r = svg.getBoundingClientRect();
      const px = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
      const i = Math.max(0, Math.min(n - 1, Math.floor((px - pl) / slot)));
      guia.setAttribute('x1', X(i)); guia.setAttribute('x2', X(i)); guia.setAttribute('visibility', 'visible');
      burbuja.replaceChildren(h('b', {}, `${fx(x[i])}${curso.has(i) ? ' · en curso (estimado)' : ''}`),
        ...gan.map(sr => h('span', {}, h('i', { class: `b ${sr.clase || 'sube'}` }), `${sr.nombre}: +${f(sr.y[i] || 0)}`)),
        ...per.map(sr => h('span', {}, h('i', { class: `b ${sr.clase || 'baja'}` }), `${sr.nombre}: −${f(sr.y[i] || 0)}`)),
        neto ? h('span', {}, h('i', { style: { background: 'var(--accent)' } }), `Neto: ${_signo(neto[i] || 0, f)}`) : null,
        ...(o.detalle ? (o.detalle(i) || []).map(t => h('span', { class: 'sub' }, t)) : []));
      burbuja.hidden = false;
      const bw = burbuja.offsetWidth;
      burbuja.style.left = `${X(i) + 12 + bw > W - 8 ? Math.max(8, X(i) - bw - 12) : X(i) + 12}px`;
    };
    const ocultar = () => { guia.setAttribute('visibility', 'hidden'); burbuja.hidden = true; };
    zona.addEventListener('mousemove', mostrar); zona.addEventListener('touchstart', mostrar, { passive: true }); zona.addEventListener('mouseleave', ocultar);
    svg.append(zona);
    lienzo.prepend(svg);
  });
  return caja;
}

/**
 * mapaCalor({ columnas, filas: [{ etiqueta, n, valores }], media, vistas: [{ valor, texto, filas, media, nota }], clave,
 *             min = 0, max = 100, formato, etiquetaFila = 'Mes de alta', etiquetaN = 'Clientes', nota })
 *   La tabla de cohortes de ChartMogul y ProfitWell: filas = mes de alta, columnas = meses de vida (0..N), cada celda con su
 *   %. Escala de UN solo color (más oscuro = más se queda; nunca rojo ni verde: 48 §4.1). Fila «Media» al pie. Con «vistas»
 *   sale el interruptor (% de clientes / % de cuota). Las celdas sin dato todavía (meses que no han pasado) van vacías.
 *   Scroll horizontal DENTRO de su caja en el móvil (la página no se ensancha).
 */
export function mapaCalor(o = {}) {
  const vistas = o.vistas?.length ? o.vistas : [{ valor: 'unica', texto: '', filas: o.filas || [], media: o.media, nota: o.nota }];
  const fmtV = o.formato || (v => fmt.pct(v));
  const min = o.min ?? 0, max = o.max ?? 100;
  const nivel = v => (_num(v) === null ? 'nd' : `c${Math.max(0, Math.min(5, Math.round(((v - min) / ((max - min) || 1)) * 5)))}`);
  const tablaDe = V => {
    const cols = o.columnas || [];
    const fila = (r, media) => h('tr', { class: media ? 'media' : null },
      h('th', { scope: 'row' }, r.etiqueta),
      h('td', { class: 'num n' }, r.n === undefined || r.n === null ? '' : fmt.num(r.n)),
      cols.map((col, k) => { const v = r.valores?.[k]; return h('td', { class: `celda ${nivel(v)}`, title: _num(v) === null ? `${r.etiqueta} · ${col}: aún no ha pasado` : `${r.etiqueta} · ${col}: ${fmtV(v)}` }, _num(v) === null ? '' : fmtV(v)); }));
    const media = V.media ? { etiqueta: 'Media', n: (V.filas || []).reduce((a, r) => a + (r.n || 0), 0), valores: V.media } : null;
    return h('div', { class: 'pila' },
      h('div', { class: 'calor-scroll', tabindex: '0', role: 'region', 'aria-label': `${o.titulo || 'Cohortes'}${V.texto ? ` · ${V.texto}` : ''}` },
        h('table', { class: 'calor' },
          h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, o.etiquetaFila || 'Mes de alta'), h('th', { scope: 'col', class: 'num' }, o.etiquetaN || 'Clientes'), cols.map(col => h('th', { scope: 'col', class: 'num' }, col)))),
          h('tbody', {}, (V.filas || []).map(r => fila(r)), media ? fila(media, true) : null))),
      h('p', { class: 'calor-ley' }, h('span', {}, fmtV(min)), [1, 2, 3, 4, 5].map(k => h('i', { class: `celda c${k}`, 'aria-hidden': 'true' })), h('span', {}, fmtV(max)),
        (V.nota || o.nota) ? h('span', { class: 'sub' }, ` · ${V.nota || o.nota}`) : null));
  };
  const caja = h('div', { class: 'calor-caja pila' });
  const zona = h('div');
  const pintar = v => zona.replaceChildren(tablaDe(vistas.find(x => x.valor === v) || vistas[0]));
  if (vistas.length > 1) {
    const ch = chipsFiltro({ opciones: vistas.map(v => ({ valor: v.valor, texto: v.texto, icono: v.icono })), clave: o.clave, etiqueta: o.etiquetaVistas || 'Ver', alCambiar: pintar });
    caja.append(ch); pintar(ch.valor());
  } else pintar(vistas[0].valor);
  caja.append(zona);
  return caja;
}

/** bandasObjetivo(objetivo) · las bandas de Databox contra objetivo: rojo < 75 %, ámbar 75-99 %, verde ≥ 100 % (48 §2.1). */
export const FUENTE_BANDAS = { fuente: 'Databox', href: 'https://help.databox.com/article/245-overview-visualization-types' };
export function bandasObjetivo(objetivo) {
  return [{ hasta: objetivo * 0.75, estado: 'rojo' }, { hasta: objetivo, estado: 'ambar' }, { hasta: Infinity, estado: 'verde' }];
}
export function estadoObjetivo(valor, objetivo) {
  if (_num(valor) === null || !objetivo) return 'gris';
  return valor >= objetivo ? 'verde' : valor >= objetivo * 0.75 ? 'ambar' : 'rojo';
}

/**
 * barraObjetivo({ valor, objetivo, max, bandas, marcas: [{ valor, texto }], extra: [{ valor, texto }], etiqueta, formato,
 *                 colorea = true })
 *   La barra contra objetivo (bullet chart): bandas de fondo (por defecto las de Databox: < 75 % rojo, 75-99 ámbar, ≥ 100
 *   verde, en tonos suaves), la cifra en una barra oscura y el objetivo como marca vertical. «marcas» son referencias pequeñas
 *   (el plan de cada mes); «extra» una segunda cifra en trazo fino (p. ej. «si firman»). colorea: false → bandas en gris.
 */
export function barraObjetivo(o = {}) {
  const f = o.formato || (v => fmt.num(v));
  const v = _num(o.valor) ?? 0, obj = _num(o.objetivo);
  const marcas = (o.marcas || []).filter(m => _num(m.valor) !== null);
  const extra = (o.extra || []).filter(m => _num(m.valor) !== null);
  const tope = o.max || Math.max(v, obj || 0, ...marcas.map(m => m.valor), ...extra.map(m => m.valor)) * 1.04 || 1;
  const pct = x => Math.max(0, Math.min(100, (x / tope) * 100));
  const bandas = o.colorea === false ? [{ hasta: tope, estado: 'gris' }] : (o.bandas || (obj ? bandasObjetivo(obj) : [{ hasta: tope, estado: 'gris' }]));
  let desde = 0;
  const texto = `${o.etiqueta ? `${o.etiqueta}: ` : ''}${f(v)}${obj ? ` de ${f(obj)} (${fmt.num((100 * v) / obj, 0)} %)` : ''}${marcas.length ? ` · ${marcas.map(m => `${m.texto} ${f(m.valor)}`).join(' · ')}` : ''}`;
  return h('div', { class: 'bullet', role: 'img', 'aria-label': texto, title: texto },
    h('div', { class: 'bullet-pista' },
      bandas.map(b => { const a = desde, z = Math.min(tope, b.hasta); desde = z; return z > a ? h('i', { class: `bb e-${b.estado}`, style: { left: `${pct(a)}%`, width: `${pct(z) - pct(a)}%` } }) : null; }),
      extra.map(m => h('i', { class: 'bx', style: { width: `${pct(m.valor)}%` }, title: `${m.texto}: ${f(m.valor)}` })),
      h('i', { class: 'bv', style: { width: `${pct(v)}%` } }),
      marcas.map(m => h('b', { class: 'bm', style: { left: `${pct(m.valor)}%` }, title: `${m.texto}: ${f(m.valor)}` })),
      obj ? h('b', { class: 'bo', style: { left: `${pct(obj)}%` }, title: `Objetivo: ${f(obj)}` }) : null),
    marcas.length || obj ? h('div', { class: 'bullet-ley' },
      h('span', {}, h('i', { class: 'bv' }), `${o.etiquetaValor || 'Hoy'} ${f(v)}`),
      extra.map(m => h('span', {}, h('i', { class: 'bx' }), `${m.texto} ${f(m.valor)}`)),
      marcas.length ? h('span', {}, h('i', { class: 'bm' }), marcas.map(m => `${m.texto} ${f(m.valor)}`).join(' · ')) : null,
      obj ? h('span', {}, h('i', { class: 'bo' }), `${o.etiquetaObjetivo || 'Objetivo'} ${f(obj)}`) : null) : null);
}

/**
 * previsionCaja({ puntos: [{ fecha: 'AAAA-MM-DD', saldo }], minimo, eventos: [{ fecha, texto }], formato, alto = 220,
 *                 textoMinimo })
 *   La caja proyectada de QuickBooks (planificador con umbral) y Xero (previsión a 90 días): una línea por día con la línea
 *   del MÍNIMO discontinua; por debajo del mínimo, la franja en rojo suave y el tramo de la línea en rojo. Los eventos
 *   (cargo SEPA, nóminas) llevan su punto. Burbuja con la fecha y el saldo al pasar el ratón.
 */
export function previsionCaja(o = {}) {
  const P = (o.puntos || []).filter(p => p && _num(p.saldo) !== null);
  const f = o.formato || (v => fmt.eur(v));
  const min = _num(o.minimo);
  const caja = h('figure', { class: 'grafico prevision', style: { margin: 0 } });
  if (o.titulo) caja.append(h('figcaption', { class: 'grafico-tit' }, o.titulo));
  if (P.length < 2) { caja.append(h('p', { class: 'grafico-vacio' }, icono('grafico', { clase: 's' }), o.vacio || 'Sin datos para la previsión')); return caja; }
  const bajo = P.filter(p => min !== null && p.saldo < min).length;
  caja.append(h('div', { class: 'grafico-ley' },
    h('span', {}, h('i', { style: { background: 'var(--accent)' } }), 'Caja prevista'),
    min !== null ? h('span', {}, h('i', { style: { background: 'var(--bad)' } }), 'Por debajo del mínimo') : null,
    min !== null ? h('span', {}, h('i', { class: 'a', style: { borderColor: 'var(--bad)' } }), o.textoMinimo || `Mínimo ${f(min)}`) : null,
    (o.eventos || []).length ? h('span', {}, h('i', { class: 'b ev' }), 'Cobro o pago previsto') : null));
  const lienzo = h('div', { class: 'grafico-lienzo', style: { height: `${o.alto || 220}px` }, role: 'img',
    'aria-label': `Caja prevista: ${f(P[0].saldo)} el ${fechaCorta(P[0].fecha)} y ${f(P[P.length - 1].saldo)} el ${fechaCorta(P[P.length - 1].fecha)}${min !== null ? `; ${bajo} de ${P.length} días por debajo del mínimo (${f(min)})` : ''}` });
  const burbuja = h('div', { class: 'grafico-burbuja', hidden: true, role: 'status' });
  lienzo.append(burbuja); caja.append(lienzo);
  const evPor = new Map((o.eventos || []).map(e => [e.fecha, e.texto]));
  alMedir(lienzo, W => {
    lienzo.querySelector('svg')?.remove();
    const H = o.alto || 220, n = P.length;
    const esc = marcasRedondas(Math.min(0, ...P.map(p => p.saldo)), Math.max(...P.map(p => p.saldo), min ?? 0), H >= 160 ? 5 : 3);
    const anchoEtiq = Math.max(...esc.marcas.map(v => String(f(v)).length)) * 7.2 + 8;
    const pl = Math.min(96, Math.max(28, anchoEtiq)), pr = 12, pt = 12, pb = 24;
    const X = i => pl + (W - pl - pr) * (i / (n - 1));
    const Y = v => pt + (H - pt - pb) * (1 - (v - esc.min) / ((esc.max - esc.min) || 1));
    const svg = s('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}` });
    if (min !== null) svg.append(s('rect', { class: 'zona-min', x: pl, y: Y(min), width: W - pl - pr, height: Math.max(0, Y(esc.min) - Y(min)) }));
    let ultY = Infinity;
    for (const v of esc.marcas) {
      svg.append(s('line', { class: v === 0 ? 'cero' : 'rejilla-l', x1: pl, x2: W - pr, y1: Y(v), y2: Y(v) }));
      if (Math.abs(ultY - Y(v)) < 16 && v !== 0) continue;
      const t = s('text', { x: pl - 8, y: Y(v) + 4, 'text-anchor': 'end' }); t.textContent = f(v); svg.append(t); ultY = Y(v);
    }
    const maxEtiq = Math.max(2, Math.min(6, Math.floor((W - pl - pr) / 64)));
    const paso = Math.max(1, Math.ceil((n - 1) / (maxEtiq - 1)));
    const idx = []; for (let i = 0; i < n; i += paso) idx.push(i);
    if (idx[idx.length - 1] !== n - 1) { if ((n - 1) - idx[idx.length - 1] < paso / 2) idx.pop(); idx.push(n - 1); }
    for (const i of idx) { const t = s('text', { x: X(i), y: H - 6, 'text-anchor': i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle' }); t.textContent = fechaCorta(P[i].fecha); svg.append(t); }
    if (min !== null) {
      svg.append(s('line', { class: 'min-l', x1: pl, x2: W - pr, y1: Y(min), y2: Y(min) }));
      const t = s('text', { class: 'min-t', x: W - pr, y: Y(min) - 6, 'text-anchor': 'end' }); t.textContent = o.textoMinimo || `Mínimo ${f(min)}`; svg.append(t);
    }
    // tramos: azul por encima del mínimo, rojo por debajo (cada tramo empieza en el último punto del anterior)
    let d = '', clase = null;
    const cerrar = () => { if (d) svg.append(s('path', { class: `linea caja-l${clase === 'bajo' ? ' bajo' : ''}`, d })); };
    P.forEach((p, i) => {
      const c = min !== null && p.saldo < min ? 'bajo' : 'ok';
      const pt2 = `${X(i).toFixed(1)},${Y(p.saldo).toFixed(1)}`;
      if (c !== clase) { const prev = i ? `M${X(i - 1).toFixed(1)},${Y(P[i - 1].saldo).toFixed(1)}L${pt2}` : `M${pt2}`; cerrar(); d = prev; clase = c; } else d += `L${pt2}`;
    });
    cerrar();
    P.forEach((p, i) => { if (evPor.has(p.fecha)) { const c = s('circle', { class: 'evento', cx: X(i), cy: Y(p.saldo), r: 4 }); const tt = s('title'); tt.textContent = `${fechaCorta(p.fecha)} · ${evPor.get(p.fecha)}`; c.append(tt); svg.append(c); } });
    const guia = s('line', { class: 'guia', x1: 0, x2: 0, y1: pt, y2: H - pb, visibility: 'hidden' }); svg.append(guia);
    const zona = s('rect', { x: pl, y: 0, width: Math.max(1, W - pl - pr), height: H, fill: 'transparent' });
    const mostrar = ev => {
      const r = svg.getBoundingClientRect();
      const px = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
      const i = Math.max(0, Math.min(n - 1, Math.round(((px - pl) / ((W - pl - pr) || 1)) * (n - 1))));
      guia.setAttribute('x1', X(i)); guia.setAttribute('x2', X(i)); guia.setAttribute('visibility', 'visible');
      const p = P[i];
      burbuja.replaceChildren(h('b', {}, fechaCorta(p.fecha)), h('span', {}, `Caja prevista: ${f(p.saldo)}`),
        min !== null && p.saldo < min ? h('span', { class: 'sub' }, `${f(min - p.saldo)} por debajo del mínimo`) : null,
        evPor.has(p.fecha) ? h('span', { class: 'sub' }, evPor.get(p.fecha)) : null);
      burbuja.hidden = false;
      const bw = burbuja.offsetWidth;
      burbuja.style.left = `${X(i) + 12 + bw > W - 8 ? Math.max(8, X(i) - bw - 12) : X(i) + 12}px`;
    };
    zona.addEventListener('mousemove', mostrar); zona.addEventListener('touchstart', mostrar, { passive: true });
    zona.addEventListener('mouseleave', () => { guia.setAttribute('visibility', 'hidden'); burbuja.hidden = true; });
    svg.append(zona);
    lienzo.prepend(svg);
  });
  return caja;
}

/**
 * barrasDivergentes({ filas: [{ etiqueta, sub, valor, estado, titulo }], formato, max, etiqueta, alPulsar })
 *   Ranking en barras horizontales con el cero en medio (Scoro, Productive): negativas a la izquierda en rojo, positivas a la
 *   derecha en verde (estado lo cambia). Ordena quien llama. alPulsar(fila) hace cada fila un botón (abrir la ficha).
 */
export function barrasDivergentes({ filas = [], formato = v => fmt.num(v), max, etiqueta, alPulsar } = {}) {
  const ok = filas.filter(r => _num(r.valor) !== null);
  const tope = max || Math.max(1, ...ok.map(r => Math.abs(r.valor)));
  const neg = ok.some(r => r.valor < 0), pos = ok.some(r => r.valor > 0);
  const cero = neg && pos ? 50 : neg ? 100 : 0;
  const escala = neg && pos ? 50 : 100;
  return h('ul', { class: `diverg${neg && pos ? ' doble' : ''}`, role: 'list', 'aria-label': etiqueta || 'Ranking' }, ok.map(r => {
    const w = (Math.abs(r.valor) / tope) * escala;
    const est = r.estado || (r.valor < 0 ? 'rojo' : 'verde');
    const cuerpo = [h('span', { class: 'dv-et' }, h('b', {}, r.etiqueta), r.sub ? h('small', {}, r.sub) : null),
      h('span', { class: 'dv-pista', 'aria-hidden': 'true' }, neg && pos ? h('i', { class: 'dv-cero', style: { left: `${cero}%` } }) : null,
        h('i', { class: `dv-b e-${est}`, style: r.valor < 0 ? { right: `${100 - cero}%`, width: `${w}%` } : { left: `${cero}%`, width: `${w}%` } })),
      h('span', { class: `dv-v ${est}` }, formato(r.valor))];
    return h('li', { title: r.titulo || null }, alPulsar ? h('button', { type: 'button', class: 'dv-fila', 'aria-label': `${r.etiqueta}: ${formato(r.valor)}`, on: { click: () => alPulsar(r) } }, cuerpo) : h('div', { class: 'dv-fila' }, cuerpo));
  }));
}
