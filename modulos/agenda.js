// modulos/agenda.js · M23 «Agenda» (petición de Tomás, 2-oct-2026).
// Cada persona ve su calendario: citas con clientes y prospectos y sus reuniones. Vistas Hoy y Semana, huecos libres,
// cruce con «En rojo» (cliente en rojo con reunión hoy) y enlace a la ficha del cliente.
// Datos: data/agenda/agenda.json (fuentes_agenda/generar_agenda.py): Zoho CRM (eventos del calendario de Zoho, incluidas
// las citas de Zoho Bookings que pasan al CRM), GoHighLevel de RO (citas de venta y talleres de Tomás; y de la setter que
// las agendó), Zoho Bookings (todo el personal) y Zoho Calendar (el de Tomás) con zbookings.py, y Zoom (grabadas, M15).
// Una cita que llega por varias puertas se junta en una sola con todos sus atajos «Abrir en…».
// Permisos (servir.py): cada fila lleva persona_id → la persona, su jefe, operaciones, RRHH y dirección. La pantalla
// enseña a cada uno la suya; a los jefes, su equipo; a Mili y Tomás, todos. Prospectos con iniciales: los nombres, solo
// su dueño con «Ver nombres» (ctx.verDato, queda en el rastro).

import { plegarConsejo } from './_plegar_consejo.js';
import {
  h, fmt, icono, tile, tiles, chipEstado, chipsFiltro, pestanas, vacio, avisoParcial, panel, frescura, iniciales,
  avisoFlotante, copiar, tablaApilable, vacioLinea, selectorPersona, menuMas,
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

// Revisión 44 (§2.3): fechas con el formato único de la app: «2-oct» y «2-oct, 17:34» (nunca «2 oct» ni «sept»).
const _MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _fechaDe = iso => (iso ? new Date(String(iso).length <= 10 ? `${iso}T12:00:00` : String(iso).replace(' ', 'T')) : null);
const fDiaRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}`; };
const fDiaHoraRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

const ID = 'agenda';
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const DIAS_C = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const TIPO = {
  cliente: { texto: 'Cliente', icono: 'maletin', estado: 'azul' },
  prospecto: { texto: 'Lead', icono: 'target', estado: 'gris' },
  interna: { texto: 'Interna', icono: 'eq', estado: 'gris' },
  fuera: { texto: 'De fuera', icono: 'mundo_web', estado: 'gris' },
};
const FUENTE = {
  crm: { texto: 'Zoho', icono: 'cal', abrir: 'Abrir en Zoho CRM' },
  ghl: { texto: 'GoHighLevel', icono: 'base', abrir: 'Abrir en GHL' },
  zoom: { texto: 'Zoom', icono: 'video', abrir: 'Ver grabación' },
  bookings: { texto: 'Bookings', icono: 'cal', abrir: 'Abrir en Bookings' },
  calendar: { texto: 'Zoho Calendar', icono: 'cal', abrir: 'Abrir en Zoho Calendar' },
};
// Atajos «Abrir en…» de cada cita (formatos del 26, parte C): el sitio exacto en la herramienta de origen.
const ATAJO = {
  ghl: { texto: 'Contacto en GHL', icono: 'base' },
  ghl_calendario: { texto: 'Calendario en GHL', icono: 'cal' },
  crm: { texto: 'Evento en Zoho CRM', icono: 'cal' },
  crm_contacto: { texto: 'Contacto en Zoho CRM', icono: 'persona' },
  bookings: { texto: 'Zoho Bookings', icono: 'cal' },
  calendar: { texto: 'Zoho Calendar', icono: 'cal' },
  zoom: { texto: 'Grabación de Zoom', icono: 'video' },
};
const atajosDe = e => (e.atajos || (e.enlace ? [{ h: e.fuente, url: e.enlace }] : [])).filter(a => /^https:\/\//.test(a.url || ''));
/** En rojo = la verdad única (gravedad «crítico» y su motivo); si no hay verdad cargada, lo que trae el fichero. */
const enRojo = (S, e) => {
  if (!e.cliente_ref) return null;
  const v = S.ctx.verdad?.(e.cliente_ref);
  if (v) return v.gravedad === 'critico' ? [v.motivo || (v.motivos || [])[0] || 'Cliente en crítico'] : null;
  return e.en_rojo?.length ? e.en_rojo : null;
};
const H_INI = 8, H_FIN = 20, PX_H = 46;     // rejilla de la semana: de 8:00 a 20:00


// N6 (2-oct): sin hoja propia. Clases comunes (bt, chips-f, pestanas, panel, tiles, av, ico-c, chip, selcli, menu-flot)
// y estilos en línea que solo usan tokens. Lo que hacía @media lo decide ANCHO al pintar (y se repinta al cambiar de ancho).
const ANCHO = {
  estrecho: () => matchMedia('(max-width: 860px)').matches,
  movil: () => matchMedia('(max-width: 640px)').matches,
};
let oyenteAncho = null;
function vigilarAncho(raiz, S) {
  if (oyenteAncho) oyenteAncho.quitar();
  const mqs = [matchMedia('(max-width: 860px)'), matchMedia('(max-width: 640px)')];
  const fn = () => { if (!raiz.isConnected) return oyenteAncho?.quitar(); S.pintar(); };
  mqs.forEach(m => m.addEventListener('change', fn));
  oyenteAncho = { quitar: () => { mqs.forEach(m => m.removeEventListener('change', fn)); oyenteAncho = null; } };
}
const EST = {
  meta: { font: 'var(--t-meta)', color: 'var(--dim)' },
  eyebrow: { font: 'var(--t-eyebrow)', textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--dim)' },
  conIco: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)' },
  sep: { borderTop: 'var(--borde-suave)' },
};


// ===================================================================== fechas
const pad = n => String(n).padStart(2, '0');
const isoDia = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const aFecha = s => new Date(String(s).slice(0, 10) + 'T12:00:00');
const minutos = s => { const m = /(\d{2}):(\d{2})/.exec(String(s || '').slice(11)); return m ? +m[1] * 60 + +m[2] : 0; };
const aMin = t => { const m = /(\d{1,2}):(\d{2})/.exec(String(t || '')); return m ? +m[1] * 60 + +m[2] : null; };
const hhmm = m => `${pad(Math.floor(m / 60))}:${pad(m % 60)}`;
const sumarDias = (iso, n) => { const d = aFecha(iso); d.setDate(d.getDate() + n); return isoDia(d); };
const lunesDe = iso => { const d = aFecha(iso); const w = (d.getDay() + 6) % 7; d.setDate(d.getDate() - w); return isoDia(d); };
const diaLargo = iso => { const d = aFecha(iso); return `${DIAS[d.getDay()]} ${d.getDate()} de ${MESES[d.getMonth()]}`; };
const diaCorto = iso => { const d = aFecha(iso); return `${DIAS_C[d.getDay()]} ${d.getDate()} ${MESES[d.getMonth()]}`; };
const durTxt = m => m < 60 ? `${m} min` : `${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60}` : ''}`;

/** Huecos libres de un día dentro de la jornada (L-V, 9-18), desde «ahora» si es hoy. */
function huecosDia(evs, iso, jornada, desdeMin = 0) {
  const d = aFecha(iso).getDay();
  if (!(jornada.dias || [0, 1, 2, 3, 4]).includes((d + 6) % 7)) return [];
  const ini = Math.max(aMin(jornada.inicio) ?? 540, desdeMin), fin = aMin(jornada.fin) ?? 1080;
  const ocup = evs.filter(e => !e.todo_el_dia && e.inicio?.startsWith(iso)).map(e => [minutos(e.inicio), Math.max(minutos(e.fin || e.inicio), minutos(e.inicio) + 15)])
    .sort((a, b) => a[0] - b[0]);
  const out = []; let t = Math.ceil(ini / 15) * 15;
  for (const [a, b] of ocup) {
    if (a > t && a - t >= 15) out.push([t, Math.min(a, fin)]);
    t = Math.max(t, b);
    if (t >= fin) break;
  }
  if (fin - t >= 15) out.push([t, fin]);
  return out.filter(([a, b]) => b > a);
}


// ===================================================================== módulo
export default {
  id: ID,
  titulo: 'Agenda',
  grupo: 'Hoy',
  puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo' },
  async render(cont, ctx) {
    plegarConsejo(cont);   // ronda U (#1): el consejo de la carcasa, en una línea
    vigilarCortes(cont);
    let D;
    try { D = await ctx.datosModulo('agenda/agenda'); }
    catch (e) {
      const no = e?.status === 403;
      cont.append(vacio({ icono: no ? 'candado' : 'cal', tono: 'aviso', borde: true,
        titulo: no ? 'No puedo leer tu agenda ahora mismo' : 'La agenda no ha cargado',
        texto: no ? 'Recarga en un minuto. Si sigue igual, avisa a Tomás: el servidor no está dejando leer la agenda.' : 'Falta preparar los datos de la agenda de hoy. Ya está avisado quien la mantiene.',
        quien: 'Tomás', accion: h('button', { type: 'button', class: 'bt', on: { click: () => location.reload() } }, icono('recargar'), 'Recargar') }));
      return;
    }
    const yo = ctx.persona.id;
    const personas = new Map((ctx.datos.personas || []).map(p => [p.id, p]));
    const todo = ctx.nivel === 'todo';
    // Lo que el servidor manda ya viene recortado; la pantalla además se ciñe a la regla de Tomás:
    // cada uno la suya, los jefes su equipo, Mili y Tomás todos (RRHH recibe más del servidor: ver _ESTADO_agenda.md).
    const equipo = new Set([yo, ...[...personas.values()].filter(p => p.jefe === yo).map(p => p.id)]);
    const evs = (D.eventos || []).filter(e => todo || equipo.has(e.persona_id));
    const ids = [...new Set([yo, ...evs.map(e => e.persona_id)])];
    const cuenta = id => evs.filter(e => e.persona_id === id && e.inicio?.startsWith(isoDia(new Date()))).length;
    const S = {
      D, evs, personas, yo, ids, todo, ctx,
      quien: ids.includes(sessionStorage.getItem?.('ro.agenda.quien')) ? sessionStorage.getItem('ro.agenda.quien') : yo,
      filtro: '', semana: lunesDe(isoDia(new Date())), nombres: {},
    };
    if (!ids.includes(S.quien)) S.quien = yo;
    S.cuenta = cuenta;
    const raiz = h('div', { style: { minWidth: '0', maxWidth: '100%', display: 'grid', gap: 'var(--s-5)', gridTemplateColumns: 'minmax(0, 1fr)' } });
    cont.append(raiz);
    S.pintar = (p) => { const act = raiz.querySelector('.pestanas-caja')?.activa?.(); raiz.replaceChildren(); pintar(raiz, S, p || act); };
    vigilarAncho(raiz, S);
    pintar(raiz, S);
  },
};

const nombreP = (S, id) => S.ctx.nombre ? S.ctx.nombre(id) : (S.personas.get(id)?.alias || S.personas.get(id)?.nombre || id);

/** De quién es la agenda: el selector de persona común (ronda 10), con buscador y avatares, en lugar de 15 chips. */
function selectorAgenda(S) {
  const orden = S.ids.slice().sort((a, b) => (a === S.yo ? -1 : b === S.yo ? 1 : nombreP(S, a).localeCompare(nombreP(S, b))));
  const lista = orden.map(id => ({ id, nombre: nombreP(S, id) }));
  return selectorPersona({
    personas: lista, actual: S.quien, etiqueta: 'Cambiar de persona',
    detalle: p => { const n = S.cuenta(p.id); return `${p.id === S.yo ? 'Mi agenda · ' : ''}${n ? `${fmt.num(n)} ${n === 1 ? 'cita' : 'citas'} hoy` : 'sin citas hoy'}`; },
    insignia: p => (S.evs.some(e => e.persona_id === p.id && e.inicio?.startsWith(isoDia(new Date())) && enRojo(S, e)) ? chipEstado('rojo', 'Cliente crítico') : null),
    alElegir: p => { S.quien = p.id; try { sessionStorage.setItem('ro.agenda.quien', p.id); } catch { /* */ } S.pintar(); },
  });
}

function pintar(raiz, S, pestanaInicial) {
  const { ctx } = S;
  const hoy = isoDia(new Date());
  const ahoraMin = new Date().getHours() * 60 + new Date().getMinutes();
  const meta = S.D._meta || {};
  const mias = S.evs.filter(e => e.persona_id === S.quien);
  const filtrar = l => S.filtro ? l.filter(e => e.tipo === S.filtro) : l;
  const deHoy = mias.filter(e => e.inicio?.startsWith(hoy));
  const proxima = mias.find(e => (e.inicio || '') >= `${hoy} ${hhmm(ahoraMin)}`);
  const rojosHoy = deHoy.filter(e => enRojo(S, e));
  const libresHoy = huecosDia(mias, hoy, meta.jornada || {}, ahoraMin).reduce((s, [a, b]) => s + (b - a), 0);
  const semIni = lunesDe(hoy), semFin = sumarDias(semIni, 6);
  const deSemana = mias.filter(e => e.inicio >= semIni && e.inicio <= semFin + ' 99');
  const esMia = S.quien === S.yo;
  const quienTxt = esMia ? 'tu' : `la de ${nombreP(S, S.quien)}`;
  ctx.titulo('Agenda', esMia ? 'Tus citas con clientes y leads y tus reuniones' : `Agenda de ${nombreP(S, S.quien)}`);

  // ---------- cabecera: de quién es la agenda + frescura
  const fu = (meta.fuentes || []).filter(f => ['crm', 'ghl', 'bookings', 'calendar', 'zoom'].includes(f.id));
  raiz.append(h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-3) var(--s-4)', alignItems: 'center', justifyContent: 'space-between' } },
    S.ids.length > 1 ? selectorAgenda(S) : h('span', {}),
    h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-1) var(--s-3)', alignItems: 'center' } }, fu.map(f => frescura({ fuente: f.fuente.split(' · ')[0], fecha: f.hora, estado: f.estado === 'bien' ? 'ok' : 'retraso' })))));

  // ---------- indicadores
  raiz.append(tiles([
    tile({ icono: 'cal', etiqueta: 'Citas hoy', valor: fmt.num(deHoy.length), contexto: deHoy.length ? `${fmt.num(deHoy.filter(e => e.tipo === 'cliente').length)} con clientes · ${fmt.num(deHoy.filter(e => e.tipo === 'prospecto').length)} con prospectos` : 'Nada en el calendario hoy', alPulsar: () => S.pintar('hoy'), ir: 'Ver el día' }),
    tile({ icono: 'clock', etiqueta: 'Próxima', valor: proxima ? proxima.inicio.slice(11, 16) : 'Ninguna', estado: proxima ? '' : 'gris', contexto: proxima ? `${proxima.inicio.startsWith(hoy) ? 'Hoy' : diaCorto(proxima.inicio)} · ${tituloBonito(proxima.titulo)}` : 'Sin citas por delante en 3 semanas' }),
    tile({ icono: 'fire', etiqueta: 'Clientes críticos con reunión hoy', valor: fmt.num(rojosHoy.length), estado: rojosHoy.length ? 'rojo' : 'verde', contexto: rojosHoy.length ? rojosHoy.map(e => e.cliente_nombre).filter(Boolean).join(', ') : 'Ninguna reunión de hoy es con un cliente en rojo', alPulsar: rojosHoy.length ? () => { S.filtro = 'cliente'; S.pintar('hoy'); } : null }),
    tile({ icono: 'ok', etiqueta: 'Huecos libres hoy', valor: durTxt(libresHoy), estado: libresHoy >= 120 ? 'verde' : libresHoy >= 30 ? 'ambar' : 'rojo', contexto: 'De aquí a las 18:00, en tramos de 15 min o más', alPulsar: () => S.pintar('huecos'), ir: 'Ver huecos' }),
    tile({ icono: 'hist', etiqueta: 'Esta semana', valor: fmt.num(deSemana.length), contexto: `${fmt.num(deSemana.filter(e => e.tipo === 'cliente').length)} con clientes · ${durTxt(deSemana.reduce((s, e) => s + Math.max(0, minutos(e.fin) - minutos(e.inicio)), 0))} reunido`, alPulsar: () => S.pintar('semana'), ir: 'Ver la semana' }),
  ]));

  // ---------- filtros por tipo (se aplican a Hoy y Semana)
  const base = mias.filter(e => e.inicio >= sumarDias(hoy, -14));
  const chips = chipsFiltro({
    etiqueta: 'Con quién', clave: 'agenda-tipo', valor: S.filtro,
    opciones: [{ valor: '', texto: 'Todas', cuenta: base.length },
      ...['cliente', 'prospecto', 'interna', 'fuera'].map(t => ({ valor: t, texto: TIPO[t].texto, icono: TIPO[t].icono, cuenta: base.filter(e => e.tipo === t).length }))
        .filter(o => o.cuenta)],
    alCambiar: v => { S.filtro = v; S.pintar(); },
  });
  S.filtro = chips.valor();

  const pests = [
    { id: 'hoy', texto: 'Hoy', icono: 'hoy', cuenta: deHoy.length, cuentaEstado: rojosHoy.length ? 'rojo' : null },
    { id: 'semana', texto: 'Semana', icono: 'cal' },
    { id: 'huecos', texto: 'Huecos libres', icono: 'ok' },
    ...(S.ids.length > 1 ? [{ id: 'equipo', texto: S.todo ? 'Todo el equipo' : 'Mi equipo', icono: 'eq' }] : []),
    { id: 'fuentes', texto: 'Fuentes', icono: 'plug', cuenta: (meta.fuentes || []).filter(f => f.estado !== 'bien').length || null },
  ];
  raiz.append(chips, pestanas({
    pestanas: pests, activa: pestanaInicial || 'hoy', clave: pestanaInicial ? null : 'agenda', etiqueta: 'Vistas de la agenda',
    pintar: (id, zona) => {
      if (id === 'hoy') zona.append(vistaDia(S, filtrar(mias), hoy, ahoraMin, quienTxt));
      if (id === 'semana') zona.append(vistaSemana(S, filtrar(mias), hoy, ahoraMin));
      if (id === 'huecos') zona.append(vistaHuecos(S, mias, hoy, ahoraMin, meta));
      if (id === 'equipo') zona.append(vistaEquipo(S, hoy, ahoraMin, meta));
      if (id === 'fuentes') zona.append(vistaFuentes(S, meta));
    },
  }));
  // El aviso de la fuente a medias va al pie: arriba, lo de cada día (orden por frecuencia).
  if ((meta.fuentes || []).some(f => ['bookings', 'calendar'].includes(f.id) && f.estado !== 'bien')) {
    raiz.append(avisoParcial('Zoho Bookings o Zoho Calendar no han cargado en la última lectura: puede faltar alguna cita. El detalle, en la pestaña «Fuentes».', { tipo: 'parcial', titulo: 'Agenda a medias' }));
  }
}

// ===================================================================== una cita
/** Acciones de una cita: «Ficha del cliente» (la que más se usa), la grabación como ▶ y el resto dentro de «Abrir ▾». */
function accionesCita(S, e, visible, f) {
  const atajos = atajosDe(e);
  const zoom = atajos.find(a => a.h === 'zoom');
  const resto = atajos.filter(a => a !== zoom);
  return h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)', justifyContent: 'flex-end', alignItems: 'center' } },
    // Ronda U (#5): una reunión con cliente lleva a su hoja de reunión (ficha › Reunión), el mismo destino que Reuniones.
    visible ? h('a', { class: 'bt', href: `#/ficha/${e.cliente_ref}/reunion` }, icono('video'), 'Preparar la reunión') : null,
    e.cliente_ref && !visible && e.tipo === 'cliente' ? h('span', { style: { ...EST.meta, display: 'inline-flex' }, title: 'El detalle de este cliente solo lo ve quien lo lleva', 'aria-label': 'El detalle de este cliente solo lo ve quien lo lleva' }, icono('candado', { clase: 's' })) : null,
    zoom ? h('a', { class: 'bt icono', href: zoom.url, target: '_blank', rel: 'noopener', title: 'Ver la grabación de Zoom', 'aria-label': 'Ver la grabación de Zoom', style: { minWidth: 'var(--s-8)', justifyContent: 'center' } }, '▶') : null,
    resto.length === 1
      ? h('a', { class: 'bt', href: resto[0].url, target: '_blank', rel: 'noopener', title: `Abrir en ${ATAJO[resto[0].h]?.texto || f.texto}` }, icono('ext'), `Abrir en ${ATAJO[resto[0].h]?.texto || f.texto}`)
      : resto.length > 1 ? menuAbrir(resto.map(a => ({ texto: ATAJO[a.h]?.texto || f.abrir, icono: ATAJO[a.h]?.icono || 'ext', href: a.url }))) : null);
}

/** «Abrir ▾» con los enlaces de la cita: el menuMas() común (ronda 10); cada enlace se abre en otra pestaña. */
function menuAbrir(items) {
  return menuMas({ texto: 'Abrir', etiqueta: 'Abrir la cita en sus herramientas',
    items: items.map(it => ({ texto: it.texto, icono: it.icono, alPulsar: () => window.open(it.href, '_blank', 'noopener') })) });
}

function tarjeta(S, e, { ahoraMin, hoy, conDia = false } = {}) {
  const { ctx } = S;
  const t = TIPO[e.tipo] || TIPO.fuera;
  const ini = minutos(e.inicio), fin = minutos(e.fin || e.inicio);
  const pasada = e.inicio.slice(0, 10) < hoy || (e.inicio.startsWith(hoy) && fin <= ahoraMin);
  const ahora = e.inicio.startsWith(hoy) && ini <= ahoraMin && fin > ahoraMin;
  const visible = e.cliente_ref && ctx.clientesVisibles.some(c => c.id === e.cliente_ref);
  const titulo = tituloBonito(S.nombres[e.id] || e.titulo);
  const f = FUENTE[e.fuente] || FUENTE.crm;
  const rojo = enRojo(S, e);
  const movil = ANCHO.movil();
  const acc = accionesCita(S, e, visible, f);
  if (movil) { acc.style.gridColumn = '2'; acc.style.justifyContent = 'flex-start'; }
  const meta1 = (ico, txt, extra = {}) => h('span', { style: EST.conIco, ...extra }, icono(ico, { clase: 's' }), txt);
  return h('div', { style: {
    display: 'grid', gridTemplateColumns: movil ? '56px minmax(0, 1fr)' : '72px minmax(0, 1fr) auto', gap: 'var(--s-2) var(--s-4)', alignItems: 'start',
    padding: 'var(--s-3) var(--s-5)', borderLeft: `3px solid ${rojo ? 'var(--bad)' : e.tipo === 'cliente' ? 'var(--accent)' : 'transparent'}`,
    // barrido v1: la cita pasada ya no se apaga con opacidad (bajaba el contraste a 2,6:1); lleva fondo gris suave
    background: rojo ? 'linear-gradient(90deg, var(--bad-soft), transparent 55%)' : ahora ? 'var(--accent-soft)' : pasada ? 'var(--card-2)' : '' } },
    h('div', { style: { display: 'grid', gap: 'var(--s-1)', font: 'var(--t-h2)', fontVariantNumeric: 'tabular-nums', color: 'var(--ink)' } },
      e.todo_el_dia ? 'Todo el día' : e.inicio.slice(11, 16),
      h('span', { style: EST.meta }, conDia ? diaCorto(e.inicio) : (!e.todo_el_dia && fin > ini ? durTxt(fin - ini) : ''))),
    h('div', { style: { display: 'grid', gap: 'var(--s-2)', minWidth: '0' } },
      h('b', { style: { font: 'var(--t-h3)', overflowWrap: 'anywhere' } }, titulo),
      h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-1) var(--s-3)', alignItems: 'center', ...EST.meta, color: 'var(--mid)', minWidth: '0' } },
        chipEstado(t.estado, t.texto),
        rojo ? h('span', { class: 'chip rojo sin-punto', style: { overflowWrap: 'anywhere', whiteSpace: 'normal' } }, icono('fire', { clase: 's' }), `Crítico · ${rojo.join(' · ')}`) : null,
        e.cliente_nombre && e.tipo === 'cliente' ? meta1('maletin', e.cliente_nombre) : null,
        e.con_quien_m && !S.nombres[e.id] ? meta1('persona', e.con_quien_m, { title: e.nombre_completo ? 'Es tu cita: ves el nombre completo (queda en el rastro)' : 'Lead con iniciales: el nombre solo lo ve el dueño de la cita' }) : null,
        e.calendario ? meta1('cal', e.calendario) : null,
        e.estado_cita && e.estado_cita !== 'confirmed' ? meta1('info', { new: 'Sin confirmar', showed: 'Se presentó', noshow: 'No se presentó', booked: 'Reservada', sin_marcar: 'Sin marcar si vino' }[e.estado_cita] || e.estado_cita) : null,
        e.agendada_por_ti ? meta1('auricular', 'La agendaste tú') : null,
        e.video && e.fuente !== 'zoom' ? meta1('video', e.video === 'zoom' ? 'Zoom' : 'Google Meet') : null,
        e.con_ro?.length > 1 ? meta1('eq', e.con_ro.join(', ')) : null,
        meta1(f.icono, f.texto, { title: e.origen }),
        ahora ? chipEstado('azul', 'Ahora') : null)),
    acc);
}

/** Las citas de Zoho Bookings entran al CRM como «<cliente> and <servicio>»: se leen mejor al revés. */
function tituloBonito(t) {
  const m = /^(.+?) and (.+)$/.exec(t || '');
  return m ? `${m[2]} · ${m[1]}` : t;
}

const lineaAhora = txt => h('div', { 'aria-label': 'Ahora', style: { display: 'flex', alignItems: 'center', gap: 'var(--s-2)', padding: '0 var(--s-5)', font: 'var(--t-meta)', fontWeight: '700', color: 'var(--bad-ink)', fontVariantNumeric: 'tabular-nums' } },
  txt, h('span', { style: { flex: '1', height: '2px', background: 'var(--bad)', borderRadius: 'var(--r-full)' } }));
const separadorDia = (izq, der, { esHoy = false, primero = false } = {}) => h('div', { style: { ...EST.eyebrow, color: esHoy ? 'var(--accent)' : 'var(--dim)', padding: 'var(--s-3) var(--s-5) var(--s-1)', borderTop: primero ? '0' : 'var(--borde-suave)', display: 'flex', justifyContent: 'space-between', gap: 'var(--s-2)' } }, h('span', {}, izq), der ? h('span', {}, der) : null);
/** Lista de citas con filete entre una y otra. */
const listaCitas = nodos => { const l = h('div', { style: { display: 'grid' } }); nodos.forEach((n, i) => { if (i && n.style && !n.getAttribute('aria-label') && l.lastChild?.getAttribute?.('aria-label') !== 'Ahora') n.style.borderTop = 'var(--borde-suave)'; l.append(n); }); return l; };

// ===================================================================== Hoy
function vistaDia(S, lista, hoy, ahoraMin, quienTxt) {
  const del = lista.filter(e => e.inicio?.startsWith(hoy));
  const caja = panel({ titulo: diaLargo(hoy)[0].toUpperCase() + diaLargo(hoy).slice(1), icono: 'hoy', sub: `Las citas de ${quienTxt === 'tu' ? 'tu' : quienTxt.replace('la de ', 'la agenda de ')} agenda, por hora. La línea roja es ahora.`, acciones: botonNombres(S, lista) });
  if (!del.length) {
    const sig = lista.find(e => e.inicio > `${hoy} 99`);
    caja.append(h('div', { style: { padding: '0 var(--relleno)' } }, vacioLinea(
      (S.filtro ? `Hoy no hay citas de tipo «${TIPO[S.filtro]?.texto}». ` : 'Hoy no tienes citas en el calendario. ') +
      (sig ? `La siguiente: ${diaLargo(sig.inicio)} a las ${sig.inicio.slice(11, 16)} · ${tituloBonito(S.nombres[sig.id] || sig.titulo)}.` : vacioSinCitas(S)),
      { icono: 'cal', quien: sig ? null : quienArregla(S) })));
  } else {
    const nodos = [];
    let lineaPuesta = false;
    for (const e of del) {
      if (!lineaPuesta && minutos(e.inicio) > ahoraMin) { nodos.push(lineaAhora(hhmm(ahoraMin))); lineaPuesta = true; }
      nodos.push(tarjeta(S, e, { ahoraMin, hoy }));
    }
    if (!lineaPuesta) nodos.push(lineaAhora(hhmm(ahoraMin)));
    caja.append(listaCitas(nodos));
  }
  // Mañana, para no llegar en frío
  const man = lista.filter(e => e.inicio > `${hoy} 99`).slice(0, 6);
  const cont = h('div', { style: { display: 'grid', gap: 'var(--s-4)' } }, caja);
  if (man.length) {
    const lst = h('div', { style: { display: 'grid' } });
    let dia = '';
    for (const e of man) {
      if (e.inicio.slice(0, 10) !== dia) { lst.append(separadorDia(diaLargo(e.inicio.slice(0, 10)), null, { primero: !dia })); dia = e.inicio.slice(0, 10); }
      const t = tarjeta(S, e, { ahoraMin, hoy });
      lst.append(t);
    }
    cont.append(panel({ titulo: 'Lo siguiente', icono: 'derecha', sub: 'Las próximas seis citas, para prepararlas con tiempo.' }, lst));
  }
  return cont;
}

function vacioSinCitas(S) {
  const p = S.personas.get(S.quien);
  if ((p?.puestos || []).includes('setters')) return 'Cuando agendes una cita con la etiqueta setter:<tu nombre> en GoHighLevel, saldrá aquí con su hora.';
  return 'No hay nada en las tres próximas semanas ni en Zoho (CRM, Bookings) ni en GoHighLevel. Si tienes una cita que no sale aquí, mira la pestaña «Fuentes».';
}
function quienArregla(S) {
  return (S.D._meta?.fuentes || []).some(f => f.id === 'bookings' && f.estado !== 'bien') ? 'Tomás' : null;
}

/** «Ver nombres»: solo el dueño de la agenda (o dirección); una sola lectura que queda en el rastro. */
function botonNombres(S, lista) {
  const pros = lista.filter(e => e.tipo === 'prospecto' || e.tipo === 'fuera');
  if (!pros.length) return null;
  // El servidor ya manda los nombres completos al dueño de cada cita (ronda 6); el botón solo hace falta si no llegaron.
  if (pros.every(e => e.nombre_completo)) return h('span', { style: { ...EST.meta, ...EST.conIco }, title: 'El servidor te los da porque son tus citas; cada lectura queda en el rastro' }, icono('ojo', { clase: 's' }), 'Nombres completos: son tus citas');
  if (Object.keys(S.nombres).length) return chipEstado('azul', 'Nombres a la vista · queda en el rastro');
  const puede = S.quien === S.yo;   // «solo lo tuyo»: los nombres de los prospectos los abre solo el dueño de la agenda
  if (!puede) return h('span', { style: { ...EST.meta, ...EST.conIco }, title: 'Los nombres de los leads solo los ve el dueño de la agenda' }, icono('candado', { clase: 's' }), 'Leads con iniciales');
  return h('button', { type: 'button', class: 'bt', on: { click: async ev => {
    ev.currentTarget.disabled = true;
    try {
      const r = await S.ctx.verDato({ almacen: `agenda/_privado/${S.quien}`, ref: S.quien, campo: 'titulos' });
      S.nombres = r.valor || {};
      avisoFlotante('Nombres a la vista. Queda en el rastro.', { icono: 'ojo' });
      S.pintar();
    } catch (e) {
      ev.currentTarget.disabled = false;
      avisoFlotante(String(e?.message || 'No se pueden ver los nombres'), { icono: 'candado' });
    }
  } } }, icono('ojo'), 'Ver nombres');
}

// ===================================================================== Semana
function vistaSemana(S, lista, hoy, ahoraMin) {
  const meta = S.D._meta || {};
  const min = lunesDe(meta.desde || hoy), max = lunesDe(meta.hasta || hoy);
  const lun = S.semana;
  const dias = [...Array(7)].map((_, i) => sumarDias(lun, i));
  const enSem = lista.filter(e => e.inicio >= dias[0] && e.inicio <= dias[6] + ' 99');
  const estrecho = ANCHO.estrecho();
  const nav = h('div', { style: { display: 'flex', alignItems: 'center', gap: 'var(--s-2)', flexWrap: 'wrap', padding: 'var(--s-4) var(--relleno) 0' } },
    h('button', { type: 'button', class: 'bt icono', 'aria-label': 'Semana anterior', disabled: lun <= min || null, on: { click: () => { S.semana = sumarDias(lun, -7); S.pintar('semana'); } } }, icono('izquierda')),
    h('b', { style: { font: 'var(--t-h3)', minWidth: estrecho ? '0' : '168px', textAlign: 'center' } }, `${diaCorto(dias[0])} – ${diaCorto(dias[6])}`),
    h('button', { type: 'button', class: 'bt icono', 'aria-label': 'Semana siguiente', disabled: lun >= max || null, on: { click: () => { S.semana = sumarDias(lun, 7); S.pintar('semana'); } } }, icono('derecha')),
    lun !== lunesDe(hoy) ? h('button', { type: 'button', class: 'bt', on: { click: () => { S.semana = lunesDe(hoy); S.pintar('semana'); } } }, 'Esta semana') : null,
    h('span', { style: EST.meta }, `${fmt.num(enSem.length)} ${enSem.length === 1 ? 'cita' : 'citas'}`));

  const cuerpo = h('div', { style: { padding: 'var(--s-3) var(--relleno) var(--relleno)', display: 'grid', gap: 'var(--s-3)' } });
  if (!enSem.length) cuerpo.append(vacioLinea(S.filtro ? 'Semana sin citas de este tipo. Quita el filtro de arriba para ver todas.' : 'Semana sin citas en el calendario. Si esperabas alguna, revisa que tu calendario esté conectado en Ajustes.', { icono: 'cal' }));

  if (!estrecho) {
    // rejilla de escritorio
    const grid = h('div', { role: 'grid', 'aria-label': 'Semana', style: { display: 'grid', gridTemplateColumns: '48px repeat(7, minmax(0, 1fr))', border: 'var(--borde)', borderRadius: 'var(--r-m)', overflow: 'hidden', background: 'var(--card)' } });
    const alto = (H_FIN - H_INI) * PX_H;
    const rayas = `repeating-linear-gradient(to bottom, transparent 0, transparent ${PX_H - 1}px, var(--line-soft) ${PX_H - 1}px, var(--line-soft) ${PX_H}px)`;
    const cabDia = (hijos, esHoy) => h('div', { style: { height: '48px', display: 'grid', placeContent: 'center', textAlign: 'center', ...EST.meta, color: esHoy ? 'var(--accent-ink)' : 'var(--dim)', borderBottom: 'var(--borde)', background: esHoy ? 'var(--accent-soft)' : 'var(--card-2)' } }, hijos);
    grid.append(h('div', { style: { minWidth: '0' } }, cabDia(''),
      h('div', { style: { position: 'relative', height: `${alto}px` } }, [...Array(H_FIN - H_INI)].map((_, i) => i ? h('span', { style: { position: 'absolute', right: 'var(--s-1)', top: `${i * PX_H - 8}px`, ...EST.meta, fontVariantNumeric: 'tabular-nums' } }, `${H_INI + i}:00`) : null))));
    for (const d of dias) {
      const dd = aFecha(d);
      const finde = dd.getDay() === 0 || dd.getDay() === 6;
      const col = h('div', { style: { position: 'relative', height: `${alto}px`, backgroundImage: rayas, backgroundColor: finde ? 'var(--card-2)' : '' } });
      const delDia = enSem.filter(e => e.inicio.startsWith(d) && !e.todo_el_dia);
      // carriles para solapes, por grupo de citas que se pisan (las sueltas ocupan todo el ancho)
      const orden = delDia.map(e => { const a = minutos(e.inicio); return { e, a, b: Math.max(minutos(e.fin || e.inicio), a + 20) }; }).sort((x, y) => x.a - y.a || y.b - x.b);
      const pos = [];
      let grupo = [], finGrupo = -1;
      const cerrar = () => { const carr = []; for (const x of grupo) { let c = carr.findIndex(f => f <= x.a); if (c < 0) { carr.push(x.b); c = carr.length - 1; } else carr[c] = x.b; x.c = c; } grupo.forEach(x => { x.n = carr.length; pos.push(x); }); grupo = []; };
      for (const x of orden) { if (grupo.length && x.a >= finGrupo) cerrar(); grupo.push(x); finGrupo = Math.max(finGrupo, x.b); }
      if (grupo.length) cerrar();
      for (const { e, a, b, c, n } of pos) {
        const top = Math.max(0, (a - H_INI * 60) / 60 * PX_H), alt = Math.max(24, (b - a) / 60 * PX_H - 2);
        const pasada = d < hoy || (d === hoy && b <= ahoraMin);
        const rojo = enRojo(S, e);
        // barrido v1: la pasada va en gris (sin opacidad, que dejaba la hora a 2,8:1)
        const tono = pasada ? { background: 'var(--card-2)', borderColor: 'var(--line)', color: 'var(--mid)' } : rojo ? { background: 'var(--bad-soft)', borderColor: 'var(--bad-line)', color: 'var(--bad-ink)' }
          : e.tipo === 'cliente' ? { background: 'var(--accent-soft)', borderColor: 'var(--accent-line)', color: 'var(--accent-ink)' }
            : { background: 'var(--off-soft)', borderColor: 'var(--line)', color: 'var(--ink)' };
        const blq = h('button', { type: 'button',
          style: { position: 'absolute', top: `${top}px`, height: `${alt}px`, left: `calc(${(c / n) * 100}% + 2px)`, width: `calc(${100 / n}% - 4px)`, borderRadius: 'var(--r-s)', padding: '0 var(--s-1)', font: 'var(--t-meta)', overflow: 'hidden', border: '1px solid', textAlign: 'left', cursor: 'pointer', ...tono },
          title: `${e.inicio.slice(11, 16)} · ${S.nombres[e.id] || e.titulo}${rojo ? ' · cliente crítico' : ''}`,
          on: { click: () => abrirCita(S, e) } }, h('b', { style: { display: 'block', fontWeight: '700', fontVariantNumeric: 'tabular-nums' } }, e.inicio.slice(11, 16)), tituloBonito(S.nombres[e.id] || e.titulo));
        blq.addEventListener('mouseenter', () => { blq.style.boxShadow = 'var(--sombra-2)'; });
        blq.addEventListener('mouseleave', () => { blq.style.boxShadow = ''; });
        col.append(blq);
      }
      if (d === hoy && ahoraMin > H_INI * 60 && ahoraMin < H_FIN * 60) col.append(h('div', { style: { position: 'absolute', left: '0', right: '0', height: '2px', background: 'var(--bad)', zIndex: '2', top: `${(ahoraMin - H_INI * 60) / 60 * PX_H}px` } }));
      grid.append(h('div', { style: { borderLeft: 'var(--borde-suave)', minWidth: '0' } },
        cabDia([DIAS_C[dd.getDay()], h('b', { style: { display: 'block', font: 'var(--t-h2)', color: d === hoy ? 'var(--accent)' : 'var(--ink)', fontVariantNumeric: 'tabular-nums' } }, dd.getDate())], d === hoy), col));
    }
    cuerpo.append(grid);
  }
  // en el móvil, lista por días
  let movil = null;
  if (estrecho) {
    movil = h('div', { style: { display: 'grid', borderTop: 'var(--borde-suave)' } });
    dias.forEach((d, i) => {
      const delDia = enSem.filter(e => e.inicio.startsWith(d));
      movil.append(separadorDia(diaLargo(d), delDia.length ? `${fmt.num(delDia.length)} ${delDia.length === 1 ? 'cita' : 'citas'}` : 'libre', { esHoy: d === hoy, primero: !i }));
      delDia.forEach(e => movil.append(tarjeta(S, e, { ahoraMin, hoy })));
    });
  }
  const detalle = h('div', { 'aria-live': 'polite' });
  S.abrirEn = detalle;
  cuerpo.append(detalle);
  return panel({ titulo: 'Semana', icono: 'cal', sub: estrecho ? 'Las citas de la semana, día a día.' : 'Pulsa una cita para ver su detalle. Azul, cliente; rojo, cliente crítico; gris, leads y reuniones internas.', acciones: botonNombres(S, lista) },
    nav, cuerpo, movil);
}

function abrirCita(S, e) {
  const hoy = isoDia(new Date());
  const ahoraMin = new Date().getHours() * 60 + new Date().getMinutes();
  if (!S.abrirEn) return;
  S.abrirEn.replaceChildren(h('div', { style: { border: 'var(--borde)', borderRadius: 'var(--r-m)', boxShadow: 'var(--sombra-1)' } }, tarjeta(S, e, { ahoraMin, hoy, conDia: true })));
  S.abrirEn.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

// ===================================================================== Huecos libres
function vistaHuecos(S, mias, hoy, ahoraMin, meta) {
  const jornada = meta.jornada || { inicio: '09:00', fin: '18:00', dias: [0, 1, 2, 3, 4] };
  const dias = [];
  for (let i = 0; dias.length < 7 && i < 14; i++) {
    const d = sumarDias(hoy, i);
    if (!(jornada.dias || []).includes((aFecha(d).getDay() + 6) % 7)) continue;
    if (d > (meta.hasta || d)) break;
    dias.push(d);
  }
  const jorMin = (aMin(jornada.fin) ?? 1080) - (aMin(jornada.inicio) ?? 540);
  const filas = dias.map(d => {
    const hs = huecosDia(mias, d, jornada, d === hoy ? ahoraMin : 0);
    const libres = hs.reduce((s, [a, b]) => s + (b - a), 0);
    const ocupado = d === hoy ? null : Math.max(0, jorMin - libres);
    return { d, hs, libres, ocupado };
  });
  const texto = filas.filter(f => f.hs.some(([a, b]) => b - a >= 30)).map(f => `${diaCorto(f.d)}: ${f.hs.filter(([a, b]) => b - a >= 30).map(([a, b]) => `${hhmm(a)}-${hhmm(b)}`).join(', ')}`).join('\n');
  const movil = ANCHO.movil();
  const lista = h('div', { style: { display: 'grid' } }, filas.map((f, i) => h('div', { style: { display: 'grid', gridTemplateColumns: movil ? 'minmax(0, 1fr)' : '128px minmax(0, 1fr) auto', gap: 'var(--s-2) var(--s-4)', alignItems: 'center', padding: 'var(--s-3) var(--relleno)', borderTop: i ? 'var(--borde-suave)' : '0' } },
    h('div', { style: { display: 'grid', font: 'var(--t-h3)', fontWeight: '700' } }, f.d === hoy ? 'Hoy' : diaCorto(f.d)[0].toUpperCase() + diaCorto(f.d).slice(1), h('span', { style: EST.meta }, `${durTxt(f.libres)} libres`)),
    f.hs.length ? h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)' } }, f.hs.map(([a, b]) => h('span', { class: `chip sin-punto ${b - a < 30 ? 'gris' : 'verde'}`, style: { fontVariantNumeric: 'tabular-nums' }, title: durTxt(b - a) }, `${hhmm(a)} – ${hhmm(b)}`)))
      : h('span', { style: EST.meta }, f.d === hoy ? 'Ya no queda jornada libre hoy' : 'Día completo'),
    f.ocupado !== null ? h('div', { title: 'Parte de la jornada (9:00-18:00) con reuniones', style: { display: 'grid', gridTemplateColumns: 'minmax(72px, 1fr) auto', gap: 'var(--s-2)', alignItems: 'center', minWidth: '140px' } },
      h('span', { style: { height: '8px', borderRadius: 'var(--r-full)', background: 'var(--good-soft)', overflow: 'hidden' } }, h('i', { style: { display: 'block', height: '100%', background: 'var(--accent)', borderRadius: 'var(--r-full)', width: `${Math.min(100, Math.round(f.ocupado / jorMin * 100))}%` } })),
      h('span', { style: EST.meta }, `${fmt.num(Math.round(f.ocupado / jorMin * 100))} % reunido`)) : h('span', {}))));
  return h('div', { style: { display: 'grid', gap: 'var(--s-4)' } },
    panel({ titulo: 'Huecos libres', icono: 'ok', sub: `Jornada de ${jornada.inicio} a ${jornada.fin}, de lunes a viernes. En verde, tramos de 30 min o más; en gris, los cortos.`,
      acciones: texto ? h('button', { type: 'button', class: 'bt', on: { click: () => copiar(`Huecos libres de ${nombreP(S, S.quien)}:\n${texto}`, 'Huecos copiados') } }, icono('copy'), 'Copiar huecos') : null },
    lista),
    avisoParcial('Los huecos se calculan con lo que la app ve de tu calendario: Zoho CRM, Bookings, GoHighLevel y Zoom (y Zoho Calendar en el caso de Tomás). Un evento personal que solo esté en tu Zoho Calendar todavía no resta.', { tipo: 'parcial' }));
}

// ===================================================================== Equipo
function vistaEquipo(S, hoy, ahoraMin, meta) {
  const filas = S.ids.map(id => {
    const ev = S.evs.filter(e => e.persona_id === id);
    const hoyL = ev.filter(e => e.inicio?.startsWith(hoy));
    const prox = ev.find(e => e.inicio >= `${hoy} ${hhmm(ahoraMin)}`);
    const libres = huecosDia(ev, hoy, meta.jornada || {}, ahoraMin).reduce((s, [a, b]) => s + (b - a), 0);
    return { id, nombre: nombreP(S, id), hoy: hoyL.length, clientes: hoyL.filter(e => e.tipo === 'cliente').length,
      rojos: hoyL.filter(e => enRojo(S, e)).length, prox, libres, semana: ev.filter(e => e.inicio >= lunesDe(hoy) && e.inicio <= sumarDias(lunesDe(hoy), 6) + ' 99').length };
  }).sort((a, b) => b.rojos - a.rojos || b.hoy - a.hoy || a.nombre.localeCompare(b.nombre));
  return panel({ titulo: S.todo ? 'Todo el equipo hoy' : 'Tu equipo hoy', icono: 'eq', sub: 'Quién está reunido hoy, con quién y cuándo tiene hueco. Pulsa una persona para abrir su agenda.' },
    tablaApilable({
      columnas: [
        { titulo: 'Persona', principal: true, celda: f => h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-2)', font: 'var(--t-h3)' } }, h('span', { class: 'av s' }, iniciales(S.personas.get(f.id)?.nombre || f.id)), f.nombre) },
        { titulo: 'Hoy', num: true, celda: f => fmt.num(f.hoy) },
        { titulo: 'Con clientes', num: true, celda: f => fmt.num(f.clientes) },
        { titulo: 'Críticos', celda: f => f.rojos ? chipEstado('rojo', fmt.num(f.rojos)) : h('span', { style: EST.meta }, 'Ninguno') },
        { titulo: 'Próxima', celda: f => f.prox ? `${f.prox.inicio.startsWith(hoy) ? 'hoy' : diaCorto(f.prox.inicio)} ${f.prox.inicio.slice(11, 16)}` : h('span', { style: EST.meta }, 'Sin citas') },
        { titulo: 'Libre hoy', celda: f => durTxt(f.libres) },
        { titulo: 'Semana', num: true, celda: f => fmt.num(f.semana) },
      ],
      filas, etiquetaFila: f => `Abrir la agenda de ${f.nombre}`,
      alPulsar: f => { S.quien = f.id; try { sessionStorage.setItem('ro.agenda.quien', f.id); } catch { /* */ } S.pintar('hoy'); },
    }));
}

// ===================================================================== Fuentes
function vistaFuentes(S, meta) {
  const est = { bien: ['verde', 'Conectada'], a_cero: ['ambar', 'Sin datos'], rota: ['rojo', 'Rota'], sin_conectar: ['gris', 'Sin conectar'] };
  const lista = h('div', {}, (meta.fuentes || []).map((f, i) => h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2) var(--s-3)', alignItems: 'flex-start', padding: 'var(--s-3) var(--relleno)', borderTop: i ? 'var(--borde-suave)' : '0' } },
    h('span', { class: `ico-c s ${est[f.estado]?.[0] || 'gris'}` }, icono({ crm: 'cal', ghl: 'base', zoom: 'video', bookings: 'cal', calendar: 'cal', dedup: 'capas' }[f.id] || 'plug')),
    h('div', { style: { flex: '1 1 240px', minWidth: '0' } }, h('b', { style: { font: 'var(--t-h3)' } }, f.fuente), h('p', { style: { margin: 'var(--s-1) 0 0', font: 'var(--t-cuerpo)', color: 'var(--mid)', maxWidth: '72ch' } }, f.detalle)),
    chipEstado(est[f.estado]?.[0] || 'gris', est[f.estado]?.[1] || f.estado))));
  const paso = h('div', { style: { display: 'grid', gap: 'var(--s-3)', font: 'var(--t-cuerpo)', color: 'var(--mid)', padding: 'var(--relleno)', maxWidth: '80ch' } },
    h('p', { style: { margin: '0' } }, h('b', {}, 'Lo que todavía no entra en la agenda:')),
    h('ol', { style: { margin: '0', paddingLeft: 'var(--s-5)', display: 'grid', gap: 'var(--s-2)' } },
      h('li', {}, 'El calendario de Zoho de cada persona: la llave de Zoho es de Tomás y Calendar solo da el suyo. El de cada uno llega cuando la app se publique y cada persona entre con su cuenta. Mientras, sus citas de Bookings y del CRM sí salen.'),
      h('li', { title: 'Permiso de Zoom que falta: meeting:read:list_meetings:admin' }, 'Las reuniones de Zoom programadas (hoy solo las grabadas). A la app de Zoom de RO le falta el permiso de leer las reuniones programadas; lo da Tomás en el panel de Zoom.')),
    h('p', { style: { margin: '0' } }, 'Bookings y Calendar están conectados desde el 2 de octubre por la tarde (Tomás dio el permiso a la llave de Zoho).'));
  const gen = meta.generado ? fechaHora(meta.generado) : null;
  return h('div', { style: { display: 'grid', gap: 'var(--s-4)' } },
    panel({ titulo: 'De dónde sale la agenda', icono: 'plug', sub: `${gen ? `Leída el ${gen} · ` : ''}ventana del ${fDiaRO(meta.desde)} al ${fDiaRO(meta.hasta)}.` }, lista),
    panel({ titulo: 'Lo que falta conectar', icono: 'key' }, paso));
}

/** «2 oct, 17:12» (nunca ISO). */
function fechaHora(s) {
  const t = String(s || '');
  const m = /(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(t);
  if (!m) return t;
  return `${+m[3]} ${MESES[+m[2] - 1]}, ${m[4]}:${m[5]}`;
}
