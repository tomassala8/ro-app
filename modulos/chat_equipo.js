// modulos/chat_equipo.js · M24 «Chat del equipo» + N15 «Canales de avisos, grupos y alertas automáticas» (2-oct-2026).
//
// Encargo de Tomás (N15): «en ClickUp tenemos los canales de avisos y demás, grupos, alertas automáticas: que eso también
// exista». En esta pantalla, como en ClickUp o Slack:
//   · AVISOS: un canal por departamento (#avisos-web … #avisos-dirección) que se llena solo con el motor de alertas (N4) y
//     los eventos del sistema. Cada aviso trae dueño, plazo y mención; «Lo tengo» y «Resuelta» cambian la alerta de verdad
//     (la misma acción que la pantalla de Alertas). Se comenta en el hilo de cada aviso.
//   · #general (todo el equipo), grupos de equipo, de cliente y propios: aquí se escribe y queda en la base de la app, con
//     rastro. NUNCA sale a ClickUp ni a ningún sitio (eso lo decidirá Tomás).
//   · ClickUp: espejo de solo lectura de los canales de siempre. Índice ligero por persona y mensajes por canal, de 50 en 50
//     (auditoría de velocidad), con /api/canales/clickup.
// Servidor: avisos.py (rutas /api/canales/*). Datos de ClickUp: fuentes_chat_equipo/ (generar_chat_equipo.py + partir_chat.py).
// «Ver como»: solo lectura; se ven los canales de la app que ven las dos personas y el chat de ClickUp no se abre.
// R16 (contratos del servidor): «Añadir persona» solo sale si /api/canales trae `puede_anadir: true` en ese canal (RRHH y
// Dirección: solo Tomás, y Cecilia en RRHH; el resto de equipos: su jefe, Mili y Tomás). Un mensaje que dice lo que cobra
// alguien vuelve con 400 y el motivo en llano: se enseña tal cual debajo de la caja y el texto se queda para corregirlo.

import {
  h, fmt, icono, tile, tiles, chipEstado, chipsFiltro, vacio, vacioLinea, avisoParcial, frescura, iniciales, avisoFlotante,
  selectorPersona,
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

const ID = 'chat-equipo';

// Sin hoja propia: clases comunes (bt, chips-f, panel, tiles, av, ico-c, vacio-g) y estilos en línea con tokens.
const ANCHO = {
  estrecho: () => matchMedia('(max-width: 860px)').matches,
  movil: () => matchMedia('(max-width: 640px)').matches,
  tactil: () => matchMedia('(hover: none)').matches,
};
let oyenteAncho = null;   // uno solo, aunque el módulo se pinte muchas veces
function vigilarAncho(S) {
  if (oyenteAncho) oyenteAncho.quitar();
  const mqs = [matchMedia('(max-width: 860px)'), matchMedia('(max-width: 640px)')];
  const fn = () => { if (!S.raiz.isConnected) return oyenteAncho?.quitar(); pintar(S); };
  mqs.forEach(m => m.addEventListener('change', fn));
  oyenteAncho = { quitar: () => { mqs.forEach(m => m.removeEventListener('change', fn)); oyenteAncho = null; } };
}
/** Fondo al pasar el ratón (lo que haría :hover en una hoja). */
function realce(el, fondo = 'var(--hover)') {
  el.addEventListener('mouseenter', () => { el.dataset.fondo = el.style.background; el.style.background = fondo; });
  el.addEventListener('mouseleave', () => { el.style.background = el.dataset.fondo || ''; });
  return el;
}
const EST = {
  eyebrow: { font: 'var(--t-meta)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--dim)' },
  meta: { font: 'var(--t-meta)', color: 'var(--dim)' },
  cuenta: { font: 'var(--t-meta)', fontWeight: '700', background: 'var(--accent)', color: 'var(--card)', borderRadius: 'var(--r-full)', padding: '0 var(--s-2)', minWidth: 'var(--s-5)', textAlign: 'center', fontVariantNumeric: 'tabular-nums' },
  raya: { flex: '1', height: '1px', background: 'var(--line-soft)' },
  cab: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2) var(--s-4)', justifyContent: 'space-between', padding: 'var(--s-3) var(--s-5)', borderBottom: 'var(--borde)' },
  h2: { font: 'var(--t-h2)', display: 'flex', alignItems: 'center', gap: 'var(--s-2)', margin: '0', minWidth: '0', overflowWrap: 'anywhere' },
  msgs: { overflowY: 'auto', padding: 'var(--s-2) 0 var(--s-4)', minHeight: '0' },
  icoBt: { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', minWidth: 'var(--s-8)', minHeight: 'var(--s-8)', margin: 'calc(-1 * var(--s-2)) 0', border: '0', background: 'transparent', color: 'var(--dim)', borderRadius: 'var(--r-s)', cursor: 'pointer', padding: '0' },
  campo: { flex: '1', minWidth: '0', minHeight: 'var(--s-8)', border: 'var(--borde)', borderRadius: 'var(--r-m)', padding: 'var(--s-1) var(--s-3)', font: 'var(--t-cuerpo)', background: 'var(--card)', color: 'var(--ink)' },
  linkBt: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)', border: '0', background: 'transparent', color: 'var(--accent)', font: 'var(--t-meta)', fontWeight: '700', cursor: 'pointer', padding: '0 var(--s-2)', minHeight: 'var(--s-8)', borderRadius: 'var(--r-s)' },
};

// ===================================================================== utilidades
const leer = k => { try { return localStorage.getItem(k); } catch { return null; } };
const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch { /* sin almacenamiento */ } };
const diaDe = f => String(f || '').slice(0, 10);
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
function diaTxt(iso) {
  const hoy = new Date(); const d = new Date(iso + 'T12:00:00');
  const dif = Math.round((new Date(hoy.toDateString()) - new Date(d.toDateString())) / 864e5);
  if (dif === 0) return 'Hoy';
  if (dif === 1) return 'Ayer';
  return `${d.getDate()} de ${MESES[d.getMonth()]}`;
}
const norm = t => String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const dos = n => String(n).padStart(2, '0');
/** «2026-10-02T20:29:13Z» (hora del servidor) → «2026-10-02 22:29» en la hora de quien mira. */
function local(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso || '').slice(0, 16).replace('T', ' ');
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())} ${dos(d.getHours())}:${dos(d.getMinutes())}`;
}
function hace(dias) { const d = new Date(Date.now() - dias * 864e5); return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())} ${dos(d.getHours())}:${dos(d.getMinutes())}`; }
const plazoTxt = v => v ? `${v.slice(8, 10)}-${v.slice(5, 7)} ${v.slice(11, 16)}`.trim() : '';
const avisarCampana = () => window.dispatchEvent(new CustomEvent('ro:avisos'));

/** Texto → nodos (nunca innerHTML): enlaces [x](url) y sueltos, **negrita**, @menciones y lo buscado. */
function texto(t, { yo, buscar } = {}) {
  const out = h('div', { style: { font: 'var(--t-cuerpo)', color: 'var(--ink)', overflowWrap: 'anywhere', whiteSpace: 'pre-wrap', maxWidth: '80ch' } });
  const enlace = (href, ...hijos) => h('a', { href, target: '_blank', rel: 'noopener noreferrer', style: { color: 'var(--accent)', padding: 'var(--s-2) 0' } }, ...hijos);
  const rx = /\[([^\]]*)\]\((https?:\/\/[^)\s]+)\)|(https?:\/\/[^\s)]+)|\*\*([^*]+)\*\*|(@[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.]*(?: [A-ZÁÉÍÓÚÑ][\wáéíóúñ]+){0,2})/g;
  let i = 0, m;
  const plano = s => {
    if (!buscar) return out.append(s);
    const n = norm(s), q = norm(buscar); let j = 0, k;
    while ((k = n.indexOf(q, j)) >= 0) { out.append(s.slice(j, k), h('mark', { style: { background: 'var(--warn-soft)', color: 'inherit', borderRadius: 'var(--r-s)' } }, s.slice(k, k + q.length))); j = k + q.length; }
    out.append(s.slice(j));
  };
  const src = String(t || '');
  while ((m = rx.exec(src))) {
    plano(src.slice(i, m.index));
    if (m[2]) {
      const etiqueta = (m[1] || '').replace(/\\_/g, '_').trim();
      const adj = /clickup-attachments\.com/.test(m[2]);
      out.append(enlace(m[2], ...(adj ? [icono('link', { clase: 's' }), ` ${etiqueta.split('/').pop() || 'Adjunto'}`] : [etiqueta || m[2]])));
    } else if (m[3]) out.append(enlace(m[3], m[3].length > 60 ? m[3].slice(0, 57) + '…' : m[3]));
    else if (m[4]) out.append(h('b', {}, m[4]));
    else if (m[5]) {
      const yoM = yo && norm(m[5]).includes(norm(yo));
      out.append(h('span', { style: { fontWeight: '700', color: yoM ? 'var(--warn-ink)' : 'var(--accent-ink)', background: yoM ? 'var(--warn-soft)' : 'var(--accent-soft)', borderRadius: 'var(--r-s)', padding: '0 var(--s-1)' } }, m[5]));
    }
    i = rx.lastIndex;
  }
  plano(src.slice(i));
  return out;
}

// ===================================================================== módulo
export default {
  id: ID,
  titulo: 'Chat del equipo',
  grupo: 'Hoy',
  puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo' },
  async render(cont, ctx) {
    vigilarCortes(cont);
    const pid = ctx.persona.id;
    const S = { ctx, pid, D: null, A: null, cuError: null, sel: null, vista: 'todos', buscar: '', res: null, abiertos: new Set(),
      movilEnCanal: false, app: new Map(), cu: new Map(), filtroAviso: 'abiertos', verTodosCli: false, nuevoGrupo: false, anadir: false };
    // El índice de ClickUp (ligero) y los canales de la app, a la vez.
    // En «ver como» el chat de ClickUp de otra persona no se abre (el servidor da 403): ni se pide.
    const [rD, rA] = await Promise.allSettled([
      ctx.soloLectura ? Promise.reject(Object.assign(new Error('ver como'), { status: 403 })) : ctx.datosModulo(`chat_equipo/p_${pid}`),
      ctx.servidor ? ctx.api('canales') : Promise.reject(Object.assign(new Error('sin servidor'), { status: 0 })),
    ]);
    if (rD.status === 'fulfilled') S.D = rD.value;
    else if (rD.reason?.status === 404) S.D = { _meta: {}, canales: [], menciones: [] };
    else S.cuError = ctx.soloLectura ? 'ver_como' : 'error';
    if (rA.status === 'fulfilled') S.A = rA.value;
    if (!S.D && !S.A) {
      cont.append(vacio({ icono: 'candado', tono: 'aviso', borde: true, titulo: 'No puedo leer tus canales ahora mismo',
        texto: 'Recarga en un minuto. Si sigue igual, avisa a Tomás: el servidor no está dejando leer el chat.', quien: 'Tomás',
        accion: h('button', { type: 'button', class: 'bt', on: { click: () => location.reload() } }, icono('recargar'), 'Recargar') }));
      return;
    }
    const raiz = h('div', { style: { minWidth: '0', maxWidth: '100%', display: 'grid', gap: 'var(--s-4)', gridTemplateColumns: 'minmax(0, 1fr)' } });
    cont.append(raiz);
    S.raiz = raiz;
    // R15b: #/chat-equipo/nuevo abre «Nuevo grupo» con el nombre listo para escribir; #/chat-equipo/<canal>, ese canal.
    const p0 = (ctx.params || [])[0];
    const nuevo = p0 === 'nuevo' && !!S.A && !ctx.soloLectura;
    if (nuevo) { S.nuevoGrupo = true; S.movilEnCanal = true; }
    else if (p0 && appCanales(S).some(c => c.id === p0)) S.sel = { tipo: 'app', id: p0 };
    else if (p0 && cuCanales(S).some(c => c.id === p0)) S.sel = { tipo: 'cu', id: p0 };
    if (S.sel) S.movilEnCanal = true;
    vigilarAncho(S);
    pintar(S);
    if (p0 && !nuevo && !S.sel) {
      avisoFlotante(p0 === 'nuevo'
        ? (ctx.soloLectura ? 'Estás en «ver como»: los grupos los crea la persona real.' : 'Los grupos de la app necesitan el servidor.')
        : 'No encuentro ese canal entre los tuyos (o ya no existe).', { icono: 'alert' });
      history.replaceState(null, '', `#/${ID}`);
    }
    if (nuevo) {
      const nombre = raiz.querySelector('input[aria-label="Nombre del grupo"]');
      nombre?.scrollIntoView({ block: 'center' });
      nombre?.focus({ preventScroll: true });
    } else if (!S.sel && !ANCHO.estrecho()) {
      const c = appCanales(S).find(x => x.mios) || appCanales(S).find(x => x.no_leidos && !x.silenciado) || appCanales(S)[0];
      if (c) abrir(S, { tipo: 'app', id: c.id }, { sinHistoria: true });
      else if (cuCanales(S)[0]) abrir(S, { tipo: 'cu', id: cuCanales(S)[0].id }, { sinHistoria: true });
    } else if (S.sel) abrir(S, S.sel, { sinHistoria: true });
  },
};

// ===================================================================== listas
const ORDEN_TIPO = { avisos: 0, general: 1, equipo: 2, cliente: 3, propio: 4 };
function appCanales(S) {
  const deps = Object.fromEntries((S.A?.departamentos || []).map((d, i) => [d.id, i]));
  return (S.A?.canales || []).slice().sort((a, b) => (ORDEN_TIPO[a.tipo] - ORDEN_TIPO[b.tipo]) || ((deps[a.departamento] ?? 99) - (deps[b.departamento] ?? 99))
    || ((b.ultimo?.id || 0) - (a.ultimo?.id || 0)) || String(a.titulo).localeCompare(String(b.titulo)));
}
const cuCanales = S => (S.D?.canales || []).slice().sort((a, b) => (b.ultimo || '').localeCompare(a.ultimo || ''));
const canalApp = (S, id) => (S.A?.canales || []).find(c => c.id === id);
const canalCu = (S, id) => (S.D?.canales || []).find(c => c.id === id);
const iconoApp = (S, c) => c.tipo === 'avisos' ? ((S.A?.departamentos || []).find(d => d.id === c.departamento)?.icono || 'campana')
  : c.tipo === 'general' ? 'megafono' : c.tipo === 'equipo' ? 'eq' : c.tipo === 'cliente' ? 'cli' : 'chat';

// ClickUp: «sin leer» = llegó después de tu última visita a ese canal en esta app (primera visita: las últimas 48 h).
const visto = (S, c) => leer(`ro.chat.visto.${S.pid}.${c.id}`) || '';
function noLeidosCu(S, c) {
  const v = visto(S, c);
  return (c.recientes || []).filter(([f, a]) => a !== S.pid && (v ? (f || '') > v : (f || '') >= hace(2))).length;
}
const mencionesCu = (S, c) => (S.D?.menciones || []).filter(m => m.canal_id === c.id && (m.fecha || '') > (visto(S, c) || hace(7)) && !m.a_todos).length;

function pintar(S) {
  const { ctx, raiz } = S;
  const estrecho = ANCHO.estrecho();
  raiz.replaceChildren();
  ctx.titulo('Chat del equipo', 'Avisos de cada departamento, grupos de la app y el espejo de ClickUp');

  const camp = S.A?.campana || {};
  const cu = cuCanales(S);
  const noCu = cu.reduce((s, c) => s + noLeidosCu(S, c), 0);
  const mencCu = cu.reduce((s, c) => s + mencionesCu(S, c), 0);
  const app = appCanales(S);
  const nAvisos = app.filter(c => c.tipo === 'avisos').length;
  if (!ANCHO.movil()) raiz.append(tiles([
    tile({ icono: 'campana', etiqueta: 'Avisos para ti', valor: S.A ? fmt.num(camp.avisos_para_ti || 0) : null, sinDato: 'sin servidor',
      estado: camp.avisos_para_ti ? 'rojo' : 'verde', contexto: camp.avisos_para_ti ? 'Con tu nombre y sin «Lo tengo»' : 'Nada pendiente con tu nombre',
      alPulsar: () => { const c = app.find(x => x.mios) || app.find(x => x.tipo === 'avisos'); if (c) { S.filtroAviso = 'tuyos'; abrir(S, { tipo: 'app', id: c.id }); } }, ir: 'Ver tus avisos' }),
    tile({ icono: 'persona', etiqueta: 'Te han mencionado', valor: fmt.num((camp.menciones || 0) + mencCu), estado: (camp.menciones || mencCu) ? 'rojo' : 'verde',
      contexto: (camp.menciones || mencCu) ? 'Sin leer, aquí y en ClickUp' : 'Nada nuevo desde tu última visita', alPulsar: () => { S.vista = 'menciones'; S.sel = null; S.movilEnCanal = false; pintar(S); }, ir: 'Ver menciones' }),
    tile({ icono: 'chat', etiqueta: 'Sin leer', valor: fmt.num((camp.no_leidos || 0) + noCu), estado: (camp.no_leidos || noCu) ? 'ambar' : 'verde',
      contexto: 'Sin contar los canales que silencias', alPulsar: () => { S.vista = 'sin_leer'; pintar(S); } }),
    tile({ icono: 'eq', etiqueta: 'Tus canales', valor: fmt.num(app.length + cu.length),
      contexto: `${fmt.num(nAvisos)} de avisos · ${fmt.num(app.length - nAvisos)} de la app · ${fmt.num(cu.length)} de ClickUp` }),
  ]));

  const modo = !estrecho ? null : S.buscar ? 'buscar' : (S.vista === 'menciones' && !S.sel) ? 'menciones' : S.nuevoGrupo ? 'nuevo' : (S.movilEnCanal && S.sel) ? 'canal' : 'lista';
  const verLista = !estrecho || modo === 'lista' || modo === 'buscar';
  const verMain = !estrecho || modo !== 'lista';
  const caja = h('div', { style: estrecho
    ? { display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', border: 'var(--borde)', borderRadius: 'var(--r-l)', background: 'var(--card)', overflow: 'hidden', boxShadow: 'var(--sombra-1)' }
    : { display: 'grid', gridTemplateColumns: '300px minmax(0, 1fr)', minHeight: '620px', height: 'calc(100vh - 330px)', maxHeight: '880px', border: 'var(--borde)', borderRadius: 'var(--r-l)', background: 'var(--card)', overflow: 'hidden', boxShadow: 'var(--sombra-1)' } });
  if (verLista) caja.append(lateral(S, estrecho, { sinLista: modo === 'buscar' }));
  if (verMain) caja.append(principal(S, estrecho));
  raiz.append(caja);
  raiz.append(h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2) var(--s-4)', alignItems: 'center', justifyContent: 'space-between' } },
    avisoParcial('Los avisos y los grupos de la app se guardan aquí, con rastro de cada mensaje. Nada sale a ClickUp ni a ningún otro sitio. Los canales de ClickUp se ven en espejo, solo lectura.', { tipo: 'info', titulo: 'Qué se guarda y dónde' }),
    frescura({ fuente: 'ClickUp chat', fecha: S.D?._meta?.generado, estado: S.D ? 'ok' : 'sin_dato' })));
  if (S.A) raiz.append(panelPreferencias(S));
  raiz.append(panelEspejo(S));
  const msgs = raiz.querySelector('[role="log"]');
  if (msgs && S.sel && !S.buscar && !S.mantenerScroll) msgs.scrollTop = msgs.scrollHeight;
  S.mantenerScroll = false;
}

// ===================================================================== columna izquierda
function lateral(S, estrecho, { sinLista = false } = {}) {
  const input = h('input', { type: 'search', placeholder: 'Buscar en tus canales', 'aria-label': 'Buscar mensajes', value: S.buscar,
    style: { border: '0', outline: '0', font: 'var(--t-cuerpo)', width: '100%', minHeight: 'var(--s-8)', background: 'transparent', color: 'var(--ink)' } });
  let t;
  input.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => buscar(S, input.value.trim()), 300); });
  const caja = h('label', { style: { display: 'flex', alignItems: 'center', gap: 'var(--s-2)', border: 'var(--borde)', background: 'var(--card)', borderRadius: 'var(--r-m)', padding: '0 var(--s-3)', color: 'var(--dim)' } }, icono('buscar', { clase: 's' }), input);
  input.addEventListener('focus', () => { caja.style.borderColor = 'var(--accent-2)'; caja.style.boxShadow = 'var(--anillo)'; });
  input.addEventListener('blur', () => { caja.style.borderColor = ''; caja.style.boxShadow = ''; });

  const app = appCanales(S), cu = cuCanales(S);
  const conMenc = app.filter(c => c.menciones).length + cu.filter(c => mencionesCu(S, c)).length;
  const vistas = chipsFiltro({
    etiqueta: 'Vista', valor: S.vista,
    opciones: [
      { valor: 'todos', texto: 'Todo', icono: 'chat' },
      { valor: 'sin_leer', texto: 'Sin leer', icono: 'campana', cuenta: (app.filter(c => c.no_leidos && !c.silenciado).length + cu.filter(c => noLeidosCu(S, c)).length) || null, cuentaEstado: 'rojo' },
      { valor: 'menciones', texto: 'Menciones', icono: 'persona', cuenta: conMenc || null, cuentaEstado: 'rojo' },
    ],
    alCambiar: v => { S.vista = v; if (v === 'menciones') { S.sel = null; S.movilEnCanal = false; } pintar(S); },
  });
  vistas.querySelector('.et')?.remove();

  const lista = h('div', { role: 'navigation', 'aria-label': 'Canales', style: { overflowY: 'auto', minHeight: '0', padding: 'var(--s-1) 0 var(--s-3)' } });
  const sinLeer = S.vista === 'sin_leer';
  const filtraApp = cs => cs.filter(c => !sinLeer || (c.no_leidos && !c.silenciado) || c.mios);
  const grupoApp = (titulo, cs, extra) => {
    if (!cs.length && !extra) return;
    lista.append(h('div', { style: { ...EST.eyebrow, padding: 'var(--s-3) var(--s-4) var(--s-1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--s-2)' } }, titulo, extra || null));
    cs.forEach(c => lista.append(filaApp(S, c, estrecho)));
  };
  if (S.A) {
    grupoApp('Avisos', filtraApp(app.filter(c => c.tipo === 'avisos')));
    grupoApp('General', filtraApp(app.filter(c => c.tipo === 'general')));
    grupoApp('Grupos de equipo', filtraApp(app.filter(c => c.tipo === 'equipo')));
    // De cliente: primero los que tienen mensajes; el resto, plegado (dirección ve los 68).
    const cli = filtraApp(app.filter(c => c.tipo === 'cliente'));
    const vivos = cli.filter(c => c.ultimo || c.por_que === 'Llevas este cliente' || c.por_que === 'Te han añadido');
    const resto = cli.filter(c => !vivos.includes(c));
    const ver = S.verTodosCli ? [...vivos, ...resto] : vivos.slice(0, 8);
    const quedan = cli.length - ver.length;
    grupoApp('Grupos de cliente', ver, null);
    if (quedan > 0 || S.verTodosCli) {
      lista.append(h('div', { style: { padding: '0 var(--s-4)' } }, h('button', { type: 'button', style: EST.linkBt, 'aria-expanded': String(S.verTodosCli),
        on: { click: () => { S.verTodosCli = !S.verTodosCli; pintar(S); } } }, icono(S.verTodosCli ? 'up' : 'chev', { clase: 's' }), S.verTodosCli ? 'Ver menos' : `Ver los ${fmt.num(cli.length)} clientes`)));
    }
    const nuevo = S.ctx.soloLectura ? null : h('button', { type: 'button', style: { ...EST.linkBt, textTransform: 'none', letterSpacing: '0' }, on: { click: () => { S.nuevoGrupo = true; S.sel = null; S.movilEnCanal = true; history.replaceState(null, '', `#/${ID}/nuevo`); pintar(S); } } }, icono('mas', { clase: 's' }), 'Nuevo grupo');
    grupoApp('Tus grupos', filtraApp(app.filter(c => c.tipo === 'propio')), nuevo);
  }
  // ClickUp: espejo de solo lectura.
  if (S.cuError === 'ver_como') {
    lista.append(h('div', { style: { ...EST.eyebrow, padding: 'var(--s-3) var(--s-4) var(--s-1)' } }, 'ClickUp · solo lectura'),
      h('div', { style: { padding: '0 var(--s-4)' } }, vacioLinea('En «ver como» no se abre el chat de ClickUp de otra persona.', { icono: 'candado' })));
  } else if (S.cuError) {
    lista.append(h('div', { style: { padding: 'var(--s-2) var(--s-4)' } }, vacioLinea('No puedo leer tu chat de ClickUp ahora mismo. Recarga en un minuto.', { icono: 'alert', quien: 'Tomás' })));
  } else {
    const filtrados = cu.filter(c => !sinLeer || noLeidosCu(S, c));
    for (const [tipo, titulo] of [['canal', 'ClickUp · canales'], ['grupo', 'ClickUp · grupos'], ['directo', 'ClickUp · mensajes directos']]) {
      const de = filtrados.filter(c => c.tipo === tipo);
      if (!de.length) continue;
      lista.append(h('div', { style: { ...EST.eyebrow, padding: 'var(--s-3) var(--s-4) var(--s-1)' } }, titulo));
      de.forEach(c => lista.append(filaCu(S, c, estrecho)));
    }
  }
  if (!lista.querySelector('button[data-canal]')) lista.append(h('div', { style: { padding: '0 var(--s-4)' } }, vacioLinea(sinLeer ? 'Lo tienes todo leído.' : 'Sin canales.', { icono: 'ok' })));
  return h('aside', { style: { display: 'grid', gridTemplateRows: 'auto auto minmax(0, 1fr)', borderRight: estrecho ? '0' : 'var(--borde)', background: 'var(--card-2)', minHeight: '0', minWidth: '0' } },
    h('div', { style: { padding: 'var(--s-3)', borderBottom: 'var(--borde-suave)' } }, caja),
    sinLista ? null : h('div', { style: { padding: 'var(--s-2) var(--s-3)', borderBottom: 'var(--borde-suave)' } }, vistas),
    sinLista ? null : lista);
}

function fila(S, { id, tipo, actual, ico, av, titulo, sub, n, mm, mios, silenciado }, alPulsar) {
  const it = h('button', { type: 'button', 'data-canal': id, 'aria-current': String(!!actual), on: { click: alPulsar },
    style: { display: 'grid', gridTemplateColumns: '26px minmax(0, 1fr) auto', gap: '0 var(--s-2)', alignItems: 'center', width: '100%', textAlign: 'left', border: '0',
      background: actual ? 'var(--accent-soft)' : 'transparent', padding: 'var(--s-2) var(--s-4)', cursor: 'pointer', font: 'inherit', color: actual ? 'var(--accent-ink)' : 'var(--mid)', minHeight: 'var(--s-12)', opacity: silenciado ? '.7' : '1' } },
    av ? h('span', { class: 'av s' }, iniciales(av)) : h('span', { style: { display: 'inline-flex', justifyContent: 'center', color: 'var(--dim)' } }, icono(ico, { clase: 's' })),
    h('span', { style: { font: 'var(--t-h3)', fontWeight: n ? '700' : '600', color: n ? 'var(--ink)' : 'inherit', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, titulo),
    mios ? h('span', { style: { ...EST.cuenta, background: 'var(--bad)' }, title: 'Avisos con tu nombre', 'aria-label': `${mios} avisos tuyos` }, fmt.num(mios))
      : mm ? h('span', { style: { ...EST.cuenta, background: 'var(--bad)' }, title: 'Te han mencionado', 'aria-label': `${mm} menciones` }, `@${fmt.num(mm)}`)
        : (n && !silenciado) ? h('span', { style: EST.cuenta, title: 'Sin leer', 'aria-label': `${n} sin leer` }, fmt.num(n))
          : silenciado ? h('span', { style: { color: 'var(--dim)', display: 'inline-flex' }, title: 'Silenciado' }, icono('ojo', { clase: 's' })) : h('span', {}),
    h('span', { style: { ...EST.meta, gridColumn: '2 / -1', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, sub));
  if (!actual) realce(it);
  return it;
}

function filaApp(S, c, estrecho) {
  const ult = c.ultimo;
  const quien = ult?.quien ? S.ctx.nombre(ult.quien).split(' ')[0] + ': ' : '';
  const sub = c.tipo === 'avisos' ? (c.abiertos ? `${fmt.num(c.abiertos)} abiertos${c.mios ? ` · ${fmt.num(c.mios)} tuyos` : ''}` : 'Sin avisos abiertos')
    : ult ? `${quien}${ult.texto}` : (c.tipo === 'cliente' ? c.por_que : 'Sin mensajes todavía');
  return fila(S, { id: c.id, actual: S.sel?.tipo === 'app' && S.sel.id === c.id && !estrecho, ico: iconoApp(S, c), titulo: c.titulo, sub,
    n: c.no_leidos, mm: c.menciones, mios: c.tipo === 'avisos' ? c.mios : 0, silenciado: c.silenciado }, () => abrir(S, { tipo: 'app', id: c.id }));
}

function filaCu(S, c, estrecho) {
  const ult = c.ultimo_msg;
  const sub = ult ? `${(ult.autor_pid && S.ctx.nombre ? S.ctx.nombre(ult.autor_pid) : ult.autor || '').split(' ')[0]}: ${String(ult.texto || '').replace(/\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/\s+/g, ' ').slice(0, 60)}` : 'Sin mensajes recientes';
  return fila(S, { id: c.id, actual: S.sel?.tipo === 'cu' && S.sel.id === c.id && !estrecho, ico: c.privado ? 'candado' : c.tipo === 'grupo' ? 'eq' : 'chat',
    av: c.tipo === 'directo' ? c.nombre : null, titulo: c.tipo === 'canal' ? c.nombre : nombreConversacion(S, c), sub, n: noLeidosCu(S, c), mm: mencionesCu(S, c) },
  () => abrir(S, { tipo: 'cu', id: c.id }));
}

/** Directos y grupos de ClickUp: los nombres como los llama la app (ctx.nombre). */
function nombreConversacion(S, c) {
  if (c.tipo === 'canal' || !S.ctx.nombre) return c.nombre;
  const otros = (c.miembros || []).filter(g => g.pid !== S.pid).map(g => (g.pid ? S.ctx.nombre(g.pid) : g.nombre));
  return otros.length ? otros.slice(0, 4).join(', ') + (otros.length > 4 ? ` y ${otros.length - 4} más` : '') : c.nombre;
}

// ===================================================================== abrir y cargar
async function abrir(S, sel, { sinHistoria = false } = {}) {
  S.sel = sel; S.movilEnCanal = true; S.buscar = ''; S.res = null; S.nuevoGrupo = false; S.anadir = false;
  if (S.vista === 'menciones') S.vista = 'todos';
  if (!sinHistoria) history.replaceState(null, '', `#/${ID}/${sel.id}`);
  S.ctx.rastro?.({ accion: 'chat_abrir', objeto: sel.id, detalle: sel.tipo === 'app' ? 'canal de la app' : 'ClickUp' });
  if (sel.tipo === 'cu') {
    const c = canalCu(S, sel.id);
    S.marcarDesde = (c && visto(S, c)) || hace(2);
    if (!S.cu.has(sel.id)) { S.cargando = true; pintar(S); await cargarCu(S, sel.id); S.cargando = false; }
    if (c) guardar(`ro.chat.visto.${S.pid}.${c.id}`, c.ultimo_msg?.fecha || c.ultimo || hace(0));
    return pintar(S);
  }
  S.cargando = !S.app.has(sel.id);
  pintar(S);
  await cargarApp(S, sel.id);
  S.cargando = false;
  pintar(S);
  marcarLeido(S, sel.id);
}

async function cargarCu(S, id, antes) {
  try {
    const r = await S.ctx.api(`canales/clickup?canal=${encodeURIComponent(id)}${antes ? `&antes=${encodeURIComponent(antes)}` : ''}`);
    const prev = S.cu.get(id);
    S.cu.set(id, { mensajes: antes && prev ? [...r.mensajes, ...prev.mensajes] : r.mensajes, hay_mas: r.hay_mas });
  } catch (e) { S.cu.set(id, { mensajes: [], hay_mas: false, error: e?.message || 'No se pudo leer el canal' }); }
}

async function cargarApp(S, id, antes) {
  try {
    const r = await S.ctx.api(`canales/canal?id=${encodeURIComponent(id)}${antes ? `&antes=${antes}` : ''}`);
    const prev = S.app.get(id);
    const mensajes = antes && prev ? [...r.mensajes, ...prev.mensajes.filter(m => !r.mensajes.some(x => x.id === m.id))] : r.mensajes;
    S.app.set(id, { ...r, mensajes, desde: prev?.desde ?? r.leido_hasta });
    const i = (S.A?.canales || []).findIndex(c => c.id === id);
    if (i >= 0) S.A.canales[i] = { ...S.A.canales[i], ...r.canal, no_leidos: S.A.canales[i].no_leidos, menciones: S.A.canales[i].menciones };
  } catch (e) { S.app.set(id, { mensajes: [], hay_mas: false, miembros: [], error: e?.message || 'No se pudo leer el canal' }); }
}

async function marcarLeido(S, id) {
  const d = S.app.get(id);
  const c = canalApp(S, id);
  if (!d || !c || S.ctx.soloLectura) return;
  const hasta = Math.max(0, ...d.mensajes.map(m => m.id));
  if (!hasta) return;
  try {
    await S.ctx.api('canales/leido', { metodo: 'POST', cuerpo: { canal_id: id, hasta_id: hasta } });
    if (S.A?.campana && c.no_leidos && !c.silenciado) S.A.campana.no_leidos = Math.max(0, (S.A.campana.no_leidos || 0) - c.no_leidos);
    if (S.A?.campana && c.menciones) S.A.campana.menciones = Math.max(0, (S.A.campana.menciones || 0) - c.menciones);
    c.no_leidos = 0; c.menciones = 0;
    avisarCampana();
  } catch { /* se marca la próxima vez */ }
}

async function refrescarCanales(S) {
  try { S.A = await S.ctx.api('canales'); } catch { /* se queda lo que había */ }
}

async function buscar(S, q) {
  S.buscar = q; S.res = null;
  if (q) { S.sel = S.sel; }
  pintar(S);
  if (!q || q.length < 2) return;
  try { S.res = await S.ctx.api(`canales/buscar?q=${encodeURIComponent(q)}`); }
  catch { S.res = { resultados: [], clickup: [], error: true }; }
  if (S.buscar !== q) return;
  pintar(S);
  const i = S.raiz.querySelector('input[type="search"]'); i?.focus(); i?.setSelectionRange(i.value.length, i.value.length);
}

// ===================================================================== zona central
const botonVolver = (S, estrecho) => estrecho
  ? h('button', { type: 'button', class: 'bt icono', 'aria-label': 'Volver a la lista de canales', on: { click: () => { S.movilEnCanal = false; S.buscar = ''; if (S.nuevoGrupo) history.replaceState(null, '', `#/${ID}`); S.nuevoGrupo = false; if (S.vista === 'menciones') S.vista = 'todos'; pintar(S); } } }, icono('volver'))
  : null;

function principal(S, estrecho) {
  const main = h('section', { 'aria-label': 'Conversación', style: { display: 'grid', gridTemplateRows: 'auto minmax(0, 1fr) auto', minHeight: '0', minWidth: '0' } });
  if (S.buscar) return main.append(...vistaBusqueda(S, estrecho)), main;
  if (S.nuevoGrupo) return main.append(...vistaNuevoGrupo(S, estrecho)), main;
  if (!S.sel && S.vista === 'menciones') return main.append(...vistaMenciones(S, estrecho)), main;
  if (!S.sel) {
    main.append(h('div', {}), vacio({ icono: 'chat', titulo: 'Elige un canal', texto: 'A la izquierda tienes tus avisos, tus grupos y tus canales de ClickUp.' }), h('div', {}));
    return main;
  }
  return S.sel.tipo === 'app' ? principalApp(S, main, estrecho) : principalCu(S, main, estrecho);
}

function cabecera(S, estrecho, { ico, titulo, meta, botones = [], debajo }) {
  return h('header', { style: { ...EST.cab, display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)' } },
    h('div', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2) var(--s-4)', justifyContent: 'space-between' } },
      h('div', { style: { display: 'grid', gap: 'var(--s-1)', minWidth: '0' } },
        h('h2', { style: EST.h2 }, botonVolver(S, estrecho), h('span', { style: { color: 'var(--accent)', display: 'inline-flex' } }, icono(ico)), titulo),
        meta ? h('span', { style: EST.meta }, meta) : null),
      h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)', alignItems: 'center' } }, ...botones)),
    debajo || null);
}

function avatares(S, ids) {
  const gente = ids.slice(0, 6);
  return h('div', { style: { display: 'flex', alignItems: 'center' }, title: ids.map(x => S.ctx.nombre(x)).join(', ') },
    gente.map((g, i) => h('span', { class: 'av s', style: { marginLeft: i ? 'calc(-1 * var(--s-2))' : '0', border: '2px solid var(--card)' } }, iniciales(S.ctx.nombre(g)))),
    ids.length > 6 ? h('span', { style: { ...EST.meta, marginLeft: 'var(--s-1)' } }, `+${fmt.num(ids.length - 6)}`) : null);
}

// ------------------------------------------------------------- canal de la app (avisos, general, grupos)
function principalApp(S, main, estrecho) {
  const c = canalApp(S, S.sel.id);
  const d = S.app.get(S.sel.id);
  if (!c) { main.append(h('div', {}), vacio({ icono: 'candado', titulo: 'Ese canal no es tuyo', texto: 'Pide a su jefe, a Mili o a Tomás que te añadan.' }), h('div', {})); return main; }
  const miembros = d?.miembros || [];
  const esAvisos = c.tipo === 'avisos';
  const botones = [
    miembros.length ? avatares(S, miembros) : null,
    h('button', { type: 'button', class: 'bt mini', style: { minHeight: 'var(--s-8)' }, disabled: S.ctx.soloLectura || null, 'aria-pressed': String(!!c.silenciado),
      title: c.silenciado ? 'No suma en «sin leer» ni en la campana (las menciones sí)' : 'Deja de sumar en «sin leer» y en la campana; las menciones siguen llegando',
      on: { click: () => silenciar(S, c, !c.silenciado) } }, icono('ojo'), c.silenciado ? 'Silenciado' : 'Silenciar'),
    c.puede_anadir === true && !S.ctx.soloLectura ? h('button', { type: 'button', class: 'bt mini', style: { minHeight: 'var(--s-8)' }, 'aria-expanded': String(S.anadir), on: { click: () => { S.anadir = !S.anadir; S.mantenerScroll = true; pintar(S); } } }, icono('mas'), 'Añadir persona') : null,
  ];
  let debajo = null;
  if (S.anadir && c.puede_anadir === true && !S.ctx.soloLectura) debajo = selectorAnadir(S, c, miembros);
  else if (esAvisos) {
    const lista = (d?.mensajes || []).filter(m => m.aviso);
    const ab = lista.filter(m => abierto(m.aviso)), tuyos = ab.filter(m => m.aviso.responsable_id === S.pid);
    debajo = chipsFiltro({ etiqueta: 'Avisos', valor: S.filtroAviso, opciones: [
      { valor: 'abiertos', texto: 'Abiertos', icono: 'alert', cuenta: ab.length || null },
      { valor: 'tuyos', texto: 'Tuyos', icono: 'persona', cuenta: tuyos.length || null, cuentaEstado: 'rojo' },
      { valor: 'todos', texto: 'Todos', icono: 'hist', cuenta: lista.length || null },
    ], alCambiar: v => { S.filtroAviso = v; pintar(S); } });
    debajo.querySelector('.et')?.remove();
  }
  main.append(cabecera(S, estrecho, { ico: iconoApp(S, c), titulo: c.titulo,
    meta: [miembros.length ? `${fmt.num(miembros.length)} personas` : null, c.por_que, c.descripcion].filter(Boolean).join(' · '), botones, debajo }));

  const msgs = h('div', { role: 'log', 'aria-label': `Mensajes de ${c.titulo}`, style: estrecho ? { ...EST.msgs, maxHeight: '62vh' } : EST.msgs });
  if (S.cargando || !d) msgs.append(h('div', { style: { padding: 'var(--s-4) var(--s-5)' } }, vacioLinea('Cargando mensajes…', { icono: 'recargar' })));
  else if (d.error) msgs.append(h('div', { style: { padding: 'var(--s-4) var(--s-5)' } }, vacioLinea(d.error, { icono: 'alert' })));
  else {
    if (d.hay_mas) msgs.append(botonMas(S, () => cargarApp(S, c.id, Math.min(...d.mensajes.filter(m => !m.hilo_de).map(m => m.id)))));
    const raiz = d.mensajes.filter(m => !m.hilo_de);
    const hilos = new Map();
    d.mensajes.filter(m => m.hilo_de).forEach(m => { if (!hilos.has(m.hilo_de)) hilos.set(m.hilo_de, []); hilos.get(m.hilo_de).push(m); });
    let ver = raiz;
    if (esAvisos && S.filtroAviso !== 'todos') ver = raiz.filter(m => m.aviso ? (abierto(m.aviso) && (S.filtroAviso !== 'tuyos' || m.aviso.responsable_id === S.pid)) : S.filtroAviso === 'abiertos' && m.tipo === 'evento' && m.dueno_id);
    if (!ver.length) msgs.append(h('div', { style: { padding: 'var(--s-4) var(--s-5)' } }, vacioLinea(esAvisos
      ? (S.filtroAviso === 'tuyos' ? 'Ningún aviso abierto con tu nombre en este canal.' : 'Sin avisos abiertos en este canal.')
      : 'Todavía no hay mensajes. Escribe el primero abajo.', { icono: esAvisos ? 'ok' : 'chat' })));
    let dia = '', nuevos = false;
    for (const m of ver) {
      const f = local(m.hora);
      if (diaDe(f) !== dia) {
        dia = diaDe(f);
        msgs.append(h('div', { style: { ...EST.eyebrow, display: 'flex', alignItems: 'center', gap: 'var(--s-3)', padding: 'var(--s-4) var(--s-5) var(--s-1)' } }, h('span', { style: EST.raya }), diaTxt(dia), h('span', { style: EST.raya })));
      }
      if (!nuevos && d.desde !== undefined && d.desde !== null && m.id > d.desde && m.quien !== S.pid && d.desde > 0) {
        msgs.append(h('div', { style: { ...EST.eyebrow, color: 'var(--bad-ink)', display: 'flex', alignItems: 'center', gap: 'var(--s-3)', padding: 'var(--s-1) var(--s-5)' } }, 'Nuevos', h('span', { style: { ...EST.raya, background: 'var(--bad)' } })));
        nuevos = true;
      }
      msgs.append(m.aviso ? tarjetaAviso(S, c, m, hilos.get(m.id) || []) : mensajeApp(S, c, m, hilos.get(m.id) || []));
    }
  }
  main.append(msgs, esAvisos ? pieAvisos(S) : cajaEscribir(S, c));
  return main;
}

const abierto = a => ['nueva', 'vista', 'reabierta', 'lo_tengo'].includes(a.estado);
const COLOR_ESTADO = { nueva: 'ambar', vista: 'ambar', reabierta: 'rojo', lo_tengo: 'azul', resuelta: 'verde', no_aplica: 'gris', cerrada: 'gris' };
const FILETE = { alta: 'var(--bad)', media: 'var(--warn)', baja: 'var(--line)' };

function botonMas(S, cargar) {
  return h('div', { style: { display: 'flex', justifyContent: 'center', padding: 'var(--s-2)' } },
    h('button', { type: 'button', class: 'bt mini', style: { minHeight: 'var(--s-8)' }, on: { click: async () => { S.mantenerScroll = true; await cargar(); S.mantenerScroll = true; pintar(S); } } }, icono('up'), 'Cargar mensajes anteriores'));
}

/** Un aviso: dueño, plazo, estado y botones; el hilo (comentarios, «lo tengo», escalado) debajo. */
function tarjetaAviso(S, c, m, hilo) {
  const a = m.aviso;
  const yo = S.ctx.persona.alias || S.ctx.persona.nombre;
  const vencida = a.vencida;
  const estado = vencida && a.estado !== 'lo_tengo' ? 'rojo' : (COLOR_ESTADO[a.estado] || 'gris');
  const abiertoHilo = S.abiertos.has(m.id);
  const botones = [];
  if (a.puede?.includes('lo_tengo')) botones.push(h('button', { type: 'button', class: 'bt pri mini', style: { minHeight: 'var(--s-8)' }, disabled: S.ctx.soloLectura || null, on: { click: () => marcarAviso(S, c, m, 'lo_tengo') } }, icono('check'), 'Lo tengo'));
  if (a.puede?.includes('resuelta')) botones.push(h('button', { type: 'button', class: 'bt mini', style: { minHeight: 'var(--s-8)' }, disabled: S.ctx.soloLectura || null, on: { click: () => marcarAviso(S, c, m, 'resuelta') } }, icono('ok'), 'Resuelta'));
  (a.abrir || []).forEach(x => botones.push(h('a', { class: 'bt mini', style: { minHeight: 'var(--s-8)' }, href: x.url, target: '_blank', rel: 'noopener noreferrer' }, icono('ext'), x.texto || 'Abrir el enlace')));
  if (a.ir) botones.push(h('a', { class: 'bt mini', style: { minHeight: 'var(--s-8)' }, href: a.ir }, icono('derecha'), 'Ir a la pantalla'));
  const meta = h('div', { class: 'meta-linea', style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-1) var(--s-4)', alignItems: 'center', font: 'var(--t-meta)', color: 'var(--mid)' } },
    h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)' } }, icono('persona', { clase: 's' }), 'Dueño: ',
      h('b', { style: { color: a.dueno_id === S.pid ? 'var(--warn-ink)' : 'var(--accent-ink)', background: a.dueno_id === S.pid ? 'var(--warn-soft)' : 'var(--accent-soft)', borderRadius: 'var(--r-s)', padding: '0 var(--s-1)' } }, `@${S.ctx.nombre(a.dueno_id)}`)),
    a.responsable_id && a.responsable_id !== a.dueno_id ? h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)' } }, icono('flag', { clase: 's' }), `Ahora lo tiene que mirar ${S.ctx.nombre(a.responsable_id)}`) : null,
    a.vence ? h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)', color: vencida ? 'var(--bad-ink)' : 'inherit', fontWeight: vencida ? '700' : '400' } }, icono('clock', { clase: 's' }), vencida ? `Plazo pasado (${plazoTxt(a.vence)})` : `Vence el ${plazoTxt(a.vence)}`) : null,
    a.cliente ? h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)' } }, icono('cli', { clase: 's' }), a.cliente) : null);
  const n = hilo.length;
  const el = h('article', { class: 'panel', style: { margin: 'var(--s-2) var(--s-4)', padding: 'var(--s-3) var(--s-4)', display: 'grid', gap: 'var(--s-2)', borderLeft: `4px solid ${FILETE[a.gravedad] || 'var(--line)'}`,
    background: m.te_menciona && abierto(a) ? 'linear-gradient(90deg, var(--warn-soft), var(--card) 60%)' : 'var(--card)' } },
    h('div', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2)', justifyContent: 'space-between' } },
      h('div', { style: { display: 'flex', alignItems: 'center', gap: 'var(--s-2)', minWidth: '0', font: 'var(--t-h3)', fontWeight: '700', color: 'var(--ink)' } },
        h('span', { class: `ico-c s ${estado === 'rojo' ? 'rojo' : estado === 'verde' ? 'verde' : estado === 'gris' ? 'gris' : 'ambar'}` }, icono('alert', { clase: 's' })), a.titulo || 'Aviso'),
      h('div', { style: { display: 'flex', alignItems: 'center', gap: 'var(--s-2)' } }, chipEstado(estado, a.estado_texto), h('span', { style: { ...EST.meta, fontVariantNumeric: 'tabular-nums' } }, local(m.hora).slice(11)))),
    texto(m.texto.startsWith(`${a.titulo}. `) ? m.texto.slice(a.titulo.length + 2) : m.texto, { yo }),
    meta,
    a.escalado && abierto(a) && a.estado !== 'lo_tengo' ? h('div', { style: { ...EST.meta, color: 'var(--bad-ink)', display: 'flex', alignItems: 'center', gap: 'var(--s-1)' } }, icono('flag', { clase: 's' }), a.escalado) : null,
    botones.length ? h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)' } }, ...botones) : null,
    h('div', {},
      h('button', { type: 'button', style: EST.linkBt, 'aria-expanded': String(abiertoHilo), on: { click: () => { abiertoHilo ? S.abiertos.delete(m.id) : S.abiertos.add(m.id); S.mantenerScroll = true; pintar(S); } } },
        icono('chat', { clase: 's' }), n ? `${fmt.num(n)} en el hilo` : 'Comentar', icono(abiertoHilo ? 'up' : 'chev', { clase: 's' })),
      abiertoHilo ? h('div', { style: { margin: 'var(--s-1) 0 0', borderLeft: '2px solid var(--line)', paddingLeft: 'var(--s-3)', display: 'grid', gap: 'var(--s-1)' } },
        hilo.map(r => r.tipo === 'evento' ? lineaEvento(S, r) : mensajeApp(S, c, r, [], { enHilo: true })),
        cajaRespuesta(S, c, m)) : null));
  return el;
}

async function marcarAviso(S, c, m, estado) {
  if (S.ctx.soloLectura) return avisoFlotante('Estás en «ver como»: es solo lectura.', { icono: 'candado' });
  try {
    const r = await S.ctx.api('canales/estado', { metodo: 'POST', cuerpo: { mensaje_id: m.id, estado } });
    m.aviso = r.aviso;
    avisoFlotante(estado === 'lo_tengo' ? 'Anotado: lo tienes tú. El escalado se para.' : 'Marcada resuelta: se comprueba con el dato siguiente.');
    S.mantenerScroll = true;
    await cargarApp(S, c.id);
    await refrescarCanales(S);
    S.mantenerScroll = true;
    pintar(S);
    avisarCampana();
  } catch (e) { avisoFlotante(String(e?.message || 'No se pudo anotar'), { icono: 'alert' }); }
}

function lineaEvento(S, m) {
  return h('div', { style: { display: 'flex', alignItems: 'flex-start', gap: 'var(--s-2)', padding: 'var(--s-1) 0', font: 'var(--t-meta)', color: 'var(--mid)' } },
    h('span', { style: { display: 'inline-flex', color: 'var(--dim)' } }, icono(m.icono || 'info', { clase: 's' })),
    h('span', { style: { minWidth: '0', overflowWrap: 'anywhere' } }, m.texto, ' ', h('span', { style: { color: 'var(--dim)', fontVariantNumeric: 'tabular-nums' } }, `· ${local(m.hora).slice(11)}`),
      m.te_menciona ? h('span', { style: { marginLeft: 'var(--s-1)' } }, chipEstado('ambar', 'Te menciona')) : null));
}

/** Un mensaje de la app (o un evento del sistema fuera de un hilo). */
function mensajeApp(S, c, m, hilo, { enHilo = false, donde, resultado = false } = {}) {
  if (m.tipo === 'evento' && !resultado) {
    const ev = h('div', { style: { padding: enHilo ? '0' : 'var(--s-2) var(--s-5)' } },
      h('div', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2)', border: 'var(--borde-suave)', background: 'var(--card-2)', borderRadius: 'var(--r-m)', padding: 'var(--s-2) var(--s-3)' } },
        h('span', { class: 'ico-c s' }, icono(m.icono || 'campana', { clase: 's' })),
        h('span', { style: { flex: '1 1 220px', minWidth: '0', font: 'var(--t-cuerpo)', color: 'var(--ink)', overflowWrap: 'anywhere' } }, m.texto),
        m.te_menciona ? chipEstado('ambar', 'Te menciona') : null,
        m.dueno_id ? h('span', { style: EST.meta }, `Dueño: ${S.ctx.nombre(m.dueno_id)}${m.vence ? ` · antes del ${plazoTxt(m.vence).slice(0, 5)}` : ''}`) : null,
        m.ir ? h('a', { class: 'bt mini', style: { minHeight: 'var(--s-8)' }, href: m.ir }, icono('derecha'), 'Abrir el mensaje') : null,
        h('span', { style: { ...EST.meta, fontVariantNumeric: 'tabular-nums' } }, local(m.hora).slice(11))));
    return ev;
  }
  const yo = S.ctx.persona.alias || S.ctx.persona.nombre;
  const autor = m.quien ? S.ctx.nombre(m.quien) : 'Avisos de la app';
  const n = hilo.length;
  const abiertoHilo = S.abiertos.has(m.id);
  const fondo = m.te_menciona ? 'linear-gradient(90deg, var(--warn-soft), transparent 70%)' : '';
  const el = h('div', { style: { display: 'grid', gridTemplateColumns: `${enHilo && !resultado ? 26 : 34}px minmax(0, 1fr)`, gap: '0 var(--s-3)', padding: enHilo && !resultado ? 'var(--s-1) 0' : 'var(--s-2) var(--s-5)', background: fondo } },
    m.quien ? h('span', { class: enHilo && !resultado ? 'av s' : 'av', style: { gridRow: 'span 4', alignSelf: 'start' } }, iniciales(autor))
      : h('span', { class: 'ico-c s', style: { gridRow: 'span 4', alignSelf: 'start' } }, icono('campana', { clase: 's' })),
    h('div', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-1) var(--s-2)', font: 'var(--t-cuerpo)', minWidth: '0' } },
      h('b', { style: { fontWeight: '700', color: 'var(--ink)' } }, autor),
      h('span', { style: { ...EST.meta, fontVariantNumeric: 'tabular-nums' } }, resultado ? local(m.hora) : local(m.hora).slice(11)),
      donde ? h('span', { style: { ...EST.meta, fontWeight: '700', color: 'var(--accent-ink)' } }, donde) : null,
      m.te_menciona ? chipEstado('ambar', 'Te menciona') : null),
    texto(m.texto, { yo, buscar: resultado ? S.buscar : '' }));
  if (!enHilo && !resultado) {
    el.append(h('button', { type: 'button', 'aria-expanded': String(abiertoHilo), on: { click: () => { abiertoHilo ? S.abiertos.delete(m.id) : S.abiertos.add(m.id); S.mantenerScroll = true; pintar(S); } },
      style: { ...EST.linkBt, gridColumn: '2', justifySelf: 'start', margin: '0 calc(-1 * var(--s-2))' } },
    icono('chat', { clase: 's' }), n ? `${fmt.num(n)} ${n === 1 ? 'respuesta' : 'respuestas'}` : 'Responder en un hilo', icono(abiertoHilo ? 'up' : 'chev', { clase: 's' })));
    if (abiertoHilo) {
      el.append(h('div', { style: { gridColumn: '2', margin: 'var(--s-1) 0', borderLeft: '2px solid var(--line)', paddingLeft: 'var(--s-3)', display: 'grid', gap: 'var(--s-1)' } },
        hilo.map(r => r.tipo === 'evento' ? lineaEvento(S, r) : mensajeApp(S, c, r, [], { enHilo: true })), cajaRespuesta(S, c, m)));
    }
  }
  return el;
}

/** Escribir en la app: queda en la base de la app (nunca sale fuera). En «ver como», desactivado (y el servidor lo rechaza). */
async function escribir(S, c, textoMsg, hiloDe, motivoEl) {
  const t = (textoMsg || '').trim();
  if (!t) return false;
  if (S.ctx.soloLectura) { avisoFlotante('Estás en «ver como»: es solo lectura.', { icono: 'candado' }); return false; }
  try {
    const r = await S.ctx.api('canales/mensaje', { metodo: 'POST', cuerpo: { canal_id: c.id, texto: t, hilo_de: hiloDe || null } });
    if (r.no_lo_veran?.length) avisoFlotante(`${r.no_lo_veran.join(', ')} no está en este canal: no lo verá. Añádelo si hace falta.`, { icono: 'alert' });
    else avisoFlotante('Enviado. Queda en la app, con rastro.', { icono: 'send' });
    if (hiloDe) S.abiertos.add(hiloDe);
    await cargarApp(S, c.id);
    return true;
  } catch (e) {
    const motivo = String(e?.message || 'No se pudo enviar');
    // 400 = el servidor lo rechaza por lo que dice (p. ej. un sueldo): su motivo, tal cual y fijo junto a la caja.
    if (e?.status === 400 && motivoEl) motivoEl.mostrar(motivo);
    avisoFlotante(e?.status === 400 ? 'No se ha enviado: lee el motivo debajo de la caja.' : motivo, { icono: 'alert' });
    return false;
  }
}

/** Línea fija bajo la caja con el motivo del rechazo (se borra al volver a escribir). */
function lineaMotivo() {
  const el = h('div', { role: 'alert', style: { display: 'none', alignItems: 'flex-start', gap: 'var(--s-2)', color: 'var(--bad-ink)', font: 'var(--t-cuerpo)' } });
  el.mostrar = texto => { el.replaceChildren(icono('alert', { clase: 's' }), h('span', {}, `No se ha enviado. ${texto}`)); el.style.display = 'flex'; };
  el.ocultar = () => { el.style.display = 'none'; el.replaceChildren(); };
  return el;
}

/** Sugerencias de @menciones con los miembros del canal. */
function conMenciones(S, c, campo) {
  const caja = h('div', { role: 'listbox', 'aria-label': 'Mencionar a', style: { display: 'none', flexWrap: 'wrap', gap: 'var(--s-1)' } });
  const miembros = S.app.get(c.id)?.miembros || [];
  campo.addEventListener('input', () => {
    const antes = campo.value.slice(0, campo.selectionStart);
    const m = antes.match(/@([\wÁÉÍÓÚÑáéíóúñ]{0,20})$/);
    caja.replaceChildren();
    if (!m) { caja.style.display = 'none'; return; }
    const q = norm(m[1]);
    const opciones = miembros.filter(id => id !== S.pid && norm(S.ctx.nombre(id)).startsWith(q)).slice(0, 6);
    caja.style.display = opciones.length ? 'flex' : 'none';
    opciones.forEach(id => caja.append(h('button', { type: 'button', class: 'bt mini', role: 'option', style: { minHeight: 'var(--s-8)' }, on: { click: () => {
      const nom = S.ctx.nombre(id);
      campo.value = antes.slice(0, antes.length - m[0].length) + `@${nom} ` + campo.value.slice(campo.selectionStart);
      caja.style.display = 'none'; campo.focus();
    } } }, h("span", { class: "av s" }, iniciales(S.ctx.nombre(id))), S.ctx.nombre(id))));
  });
  return caja;
}

function cajaEscribir(S, c) {
  const ta = h('textarea', { rows: '1', placeholder: S.ctx.soloLectura ? 'En «ver como» no se escribe' : `Escribe en ${c.titulo}… (@nombre para mencionar)`, 'aria-label': 'Mensaje', disabled: S.ctx.soloLectura || null,
    style: { border: '0', outline: '0', resize: 'none', font: 'var(--t-cuerpo)', minHeight: 'var(--s-10)', maxHeight: '140px', padding: 'var(--s-2) 0', background: 'transparent', color: 'var(--ink)', minWidth: '0' } });
  const motivo = lineaMotivo();
  const enviar = async () => { motivo.ocultar(); if (await escribir(S, c, ta.value, null, motivo)) { ta.value = ''; pintar(S); } };
  ta.addEventListener('input', () => { motivo.ocultar(); ta.style.height = 'auto'; ta.style.height = Math.min(140, ta.scrollHeight) + 'px'; });
  ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(); } });
  const caja = h('div', { style: { display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 'var(--s-2)', alignItems: 'end', border: 'var(--borde)', borderRadius: 'var(--r-m)', padding: 'var(--s-1) var(--s-1) var(--s-1) var(--s-3)', background: 'var(--card)' } },
    ta, h('button', { type: 'button', class: 'bt pri', disabled: S.ctx.soloLectura || null, on: { click: enviar } }, icono('send'), 'Enviar'));
  ta.addEventListener('focus', () => { caja.style.borderColor = 'var(--accent-2)'; caja.style.boxShadow = 'var(--anillo)'; });
  ta.addEventListener('blur', () => { caja.style.borderColor = ''; caja.style.boxShadow = ''; });
  return h('div', { style: { borderTop: 'var(--borde)', padding: 'var(--s-3) var(--s-4)', display: 'grid', gap: 'var(--s-2)', background: 'var(--card)' } },
    conMenciones(S, c, ta), caja, motivo,
    h('span', { style: { ...EST.meta, display: 'flex', alignItems: 'center', gap: 'var(--s-2)', flexWrap: 'wrap' } }, icono('candado', { clase: 's' }), 'Intro envía · Mayús+Intro, salto de línea · queda en la app, nunca sale a ClickUp · contraseñas, correos y teléfonos se tapan solos'));
}

function cajaRespuesta(S, c, m) {
  const i = h('input', { type: 'text', placeholder: S.ctx.soloLectura ? 'En «ver como» no se escribe' : 'Comentar en el hilo…', 'aria-label': 'Respuesta', disabled: S.ctx.soloLectura || null, style: EST.campo });
  const motivo = lineaMotivo();
  const ir = async () => { motivo.ocultar(); if (await escribir(S, c, i.value, m.id, motivo)) { S.mantenerScroll = true; pintar(S); } };
  i.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); ir(); } });
  i.addEventListener('input', () => motivo.ocultar());
  return h('div', { style: { display: 'grid', gap: 'var(--s-1)', marginTop: 'var(--s-1)' } }, conMenciones(S, c, i),
    h('div', { style: { display: 'flex', gap: 'var(--s-2)', alignItems: 'center' } }, i,
      h('button', { type: 'button', class: 'bt mini', style: { minHeight: 'var(--s-8)' }, disabled: S.ctx.soloLectura || null, on: { click: ir } }, icono('send'), 'Enviar')), motivo);
}

function pieAvisos(S) {
  return h('div', { style: { borderTop: 'var(--borde)', padding: 'var(--s-3) var(--s-4)', background: 'var(--card-2)', ...EST.meta, display: 'flex', alignItems: 'center', gap: 'var(--s-2)', flexWrap: 'wrap' } },
    icono('info', { clase: 's' }), 'Los avisos los escribe la app (motor de alertas y eventos). Comenta en el hilo de cada aviso; «Lo tengo» y «Resuelta» cambian la alerta de verdad.');
}

async function silenciar(S, c, si) {
  if (S.ctx.soloLectura) return;
  const sil = new Set(S.A?.preferencias?.silenciados || []);
  si ? sil.add(c.id) : sil.delete(c.id);
  try {
    const r = await S.ctx.api('canales/preferencias', { metodo: 'POST', cuerpo: { silenciados: [...sil], hora_resumen: S.A.preferencias.hora_resumen } });
    S.A.preferencias = r.preferencias;
    await refrescarCanales(S);
    avisoFlotante(si ? `${c.titulo}: silenciado. Las menciones siguen llegando.` : `${c.titulo}: vuelve a sumar en «sin leer».`, { icono: 'ojo' });
    S.mantenerScroll = true;
    pintar(S);
    avisarCampana();
  } catch (e) { avisoFlotante(String(e?.message || 'No se pudo guardar'), { icono: 'alert' }); }
}

function personasActivas(S) {
  return (S.ctx.datos.personas || []).filter(p => p.activo && p.estado !== 'baja' && p.id !== S.pid)
    .map(p => ({ ...p, nombre: p.alias || p.nombre, puesto: (p.puestos || []).join(' · ').replace(/_/g, ' ') }));
}

function selectorAnadir(S, c, miembros) {
  const lista = personasActivas(S).filter(p => !miembros.includes(p.id));
  const sel = selectorPersona({ personas: lista, etiqueta: 'Añadir a', placeholder: 'Buscar persona…', alElegir: async p => {
    try {
      await S.ctx.api('canales/miembro', { metodo: 'POST', cuerpo: { canal_id: c.id, persona_id: p.id } });
      avisoFlotante(`${p.nombre} ya está en ${c.titulo}.`);
      S.anadir = false;
      await cargarApp(S, c.id);
      pintar(S);
    } catch (e) {
      avisoFlotante(String(e?.message || 'No se pudo añadir'), { icono: 'alert' });
      if (e?.status === 403) { S.anadir = false; await refrescarCanales(S); S.mantenerScroll = true; pintar(S); }   // el permiso cambió: fuera el botón
    }
  } });
  return h('div', { style: { display: 'grid', gap: 'var(--s-1)' } }, h('span', { style: EST.meta }, c.cliente_id ? 'Solo entra quien puede abrir este cliente.' : 'Verá lo que ya hay en el canal (los avisos, solo los suyos).'), sel);
}

// ------------------------------------------------------------- nuevo grupo
function vistaNuevoGrupo(S, estrecho) {
  const elegidos = S.elegidos || (S.elegidos = []);
  const nombre = h('input', { type: 'text', placeholder: 'Por ejemplo: Lanzamiento de octubre', 'aria-label': 'Nombre del grupo', value: S.nombreGrupo || '', style: EST.campo,
    on: { input: e => { S.nombreGrupo = e.target.value; } } });
  const chips = h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)' } },
    elegidos.length ? elegidos.map(p => h('button', { type: 'button', class: 'bt mini', style: { minHeight: 'var(--s-8)' }, title: 'Quitar', on: { click: () => { S.elegidos = elegidos.filter(x => x.id !== p.id); pintar(S); } } },
      h('span', { class: 'av s' }, iniciales(p.nombre)), p.nombre, icono('cerrar', { clase: 's' }))) : h('span', { style: EST.meta }, 'Nadie todavía (tú entras siempre).'));
  const sel = selectorPersona({ personas: personasActivas(S).filter(p => !elegidos.some(x => x.id === p.id)), etiqueta: 'Añadir', placeholder: 'Buscar persona…',
    alElegir: p => { S.elegidos = [...elegidos, p]; pintar(S); } });
  const crear = async () => {
    try {
      const r = await S.ctx.api('canales/grupo', { metodo: 'POST', cuerpo: { nombre: S.nombreGrupo || '', miembros: elegidos.map(p => p.id) } });
      S.elegidos = []; S.nombreGrupo = ''; S.nuevoGrupo = false;
      await refrescarCanales(S);
      abrir(S, { tipo: 'app', id: r.id });
    } catch (e) { avisoFlotante(String(e?.message || 'No se pudo crear'), { icono: 'alert' }); }
  };
  return [cabecera(S, estrecho, { ico: 'eq', titulo: 'Nuevo grupo', meta: 'Lo que se escriba queda en la app, con rastro. No sale a ClickUp.' }),
    h('div', { style: { padding: 'var(--s-4) var(--s-5)', display: 'grid', gap: 'var(--s-4)', alignContent: 'start', overflowY: 'auto' } },
      h('label', { style: { display: 'grid', gap: 'var(--s-1)', font: 'var(--t-meta)', color: 'var(--mid)' } }, 'Nombre', nombre),
      h('div', { style: { display: 'grid', gap: 'var(--s-2)' } }, h('span', { style: { font: 'var(--t-meta)', color: 'var(--mid)' } }, 'Personas'), chips, sel),
      avisoParcial('Para hablar de un cliente usa su grupo de cliente: ahí solo entra quien puede abrir ese cliente.', { tipo: 'info' })),
    h('div', { style: { borderTop: 'var(--borde)', padding: 'var(--s-3) var(--s-4)', display: 'flex', gap: 'var(--s-2)', justifyContent: 'flex-end', flexWrap: 'wrap' } },
      h('button', { type: 'button', class: 'bt', on: { click: () => { S.nuevoGrupo = false; S.movilEnCanal = false; history.replaceState(null, '', `#/${ID}`); pintar(S); } } }, 'Cancelar'),
      h('button', { type: 'button', class: 'bt pri', disabled: S.ctx.soloLectura || null, on: { click: crear } }, icono('mas'), 'Crear grupo'))];
}

// ------------------------------------------------------------- espejo de ClickUp (solo lectura)
function principalCu(S, main, estrecho) {
  const c = canalCu(S, S.sel.id);
  if (!c) { main.append(h('div', {}), vacio({ icono: 'candado', titulo: 'Ese canal no es tuyo' }), h('div', {})); return main; }
  const d = S.cu.get(c.id);
  const gente = (c.miembros || []).map(g => g.pid).filter(Boolean);
  const esDirecto = c.tipo !== 'canal';
  main.append(cabecera(S, estrecho, { ico: esDirecto ? 'persona' : c.privado ? 'candado' : 'chat', titulo: nombreConversacion(S, c),
    meta: `ClickUp · solo lectura · ${fmt.num(c.n_miembros)} personas${c.privado ? ' · privado' : ''}${c.descripcion ? ' · ' + c.descripcion : ''}`,
    botones: [gente.length ? avatares(S, gente) : null,
      esDirecto ? h('a', { class: 'bt mini', style: { minHeight: 'var(--s-8)' }, href: 'https://zoom.us/start/videomeeting', target: '_blank', rel: 'noopener', title: 'Abre Zoom con tu cuenta' }, icono('video'), 'Videollamada Zoom') : null,
      h('a', { class: 'bt mini', style: { minHeight: 'var(--s-8)' }, href: c.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en ClickUp')] }));
  const msgs = h('div', { role: 'log', 'aria-label': `Mensajes de ${c.nombre}`, style: estrecho ? { ...EST.msgs, maxHeight: '62vh' } : EST.msgs });
  if (S.cargando || !d) msgs.append(h('div', { style: { padding: 'var(--s-4) var(--s-5)' } }, vacioLinea('Cargando mensajes…', { icono: 'recargar' })));
  else if (d.error) msgs.append(h('div', { style: { padding: 'var(--s-4) var(--s-5)' } }, vacioLinea(d.error, { icono: 'alert' })));
  else {
    if (d.hay_mas) msgs.append(botonMas(S, () => cargarCu(S, c.id, d.mensajes[0]?.id)));
    if (!d.mensajes.length) msgs.append(h('div', { style: { padding: '0 var(--s-5)' } }, vacioLinea('Sin mensajes recientes en este canal.', { icono: 'chat' })));
    let dia = '', nuevos = false;
    for (const m of d.mensajes) {
      if (diaDe(m.fecha) !== dia) {
        dia = diaDe(m.fecha);
        msgs.append(h('div', { style: { ...EST.eyebrow, display: 'flex', alignItems: 'center', gap: 'var(--s-3)', padding: 'var(--s-4) var(--s-5) var(--s-1)' } }, h('span', { style: EST.raya }), diaTxt(dia), h('span', { style: EST.raya })));
      }
      if (!nuevos && S.marcarDesde && m.fecha > S.marcarDesde && m.autor_pid !== S.pid) {
        msgs.append(h('div', { style: { ...EST.eyebrow, color: 'var(--bad-ink)', display: 'flex', alignItems: 'center', gap: 'var(--s-3)', padding: 'var(--s-1) var(--s-5)' } }, 'Nuevos', h('span', { style: { ...EST.raya, background: 'var(--bad)' } })));
        nuevos = true;
      }
      msgs.append(mensajeCu(S, c, m));
    }
  }
  main.append(msgs, h('div', { style: { borderTop: 'var(--borde)', padding: 'var(--s-3) var(--s-4)', background: 'var(--card-2)', display: 'flex', alignItems: 'center', gap: 'var(--s-2) var(--s-3)', flexWrap: 'wrap', justifyContent: 'space-between' } },
    h('span', { style: { ...EST.meta, display: 'flex', alignItems: 'center', gap: 'var(--s-2)', flex: '1 1 260px' } }, icono('candado', { clase: 's' }), 'Espejo de ClickUp: solo lectura. Desde la app no se escribe en ClickUp (lo decide Tomás). Para contestar, ábrelo en ClickUp o escribe en un grupo de la app.'),
    h('a', { class: 'bt mini', style: { minHeight: 'var(--s-8)' }, href: c.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Contestar en ClickUp')));
  return main;
}

function mensajeCu(S, c, m, { enHilo = false, donde, resultado = false } = {}) {
  const yo = S.ctx.persona.alias || S.ctx.persona.nombre;
  const mio = m.menciones?.includes(S.pid);
  const autor = m.autor_pid && S.ctx.nombre ? S.ctx.nombre(m.autor_pid) : m.autor;
  const ws = S.D?._meta?.workspace;
  const enlaceMsg = ws && c?.id && m.id ? `https://app.clickup.com/${ws}/chat/r/${c.id}/t/${m.id}` : null;
  const resp = m.respuestas || [];
  const n = m.n_respuestas || 0;
  const abiertoHilo = S.abiertos.has(m.id);
  const fondoBase = mio ? 'linear-gradient(90deg, var(--warn-soft), transparent 70%)' : '';
  const enHiloDe = enHilo && !resultado;
  const el = h('div', { style: { display: 'grid', gridTemplateColumns: `${enHiloDe ? 26 : 34}px minmax(0, 1fr)`, gap: '0 var(--s-3)', padding: enHiloDe ? 'var(--s-1) 0' : 'var(--s-2) var(--s-5)', background: fondoBase } },
    h('span', { class: enHiloDe ? 'av s' : 'av', style: { gridRow: 'span 4', alignSelf: 'start' } }, iniciales(autor)),
    h('div', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-1) var(--s-2)', font: 'var(--t-cuerpo)', minWidth: '0' } },
      h('b', { style: { fontWeight: '700', color: 'var(--ink)' } }, autor),
      h('span', { style: { ...EST.meta, fontVariantNumeric: 'tabular-nums' } }, resultado ? (m.fecha || '') : (m.fecha || '').slice(11, 16)),
      donde ? h('span', { style: { ...EST.meta, fontWeight: '700', color: 'var(--accent-ink)' } }, donde) : null,
      mio ? chipEstado('ambar', 'Te menciona') : null,
      enlaceMsg ? h('a', { href: enlaceMsg, target: '_blank', rel: 'noopener', title: 'Abrir este mensaje en ClickUp', 'aria-label': 'Abrir este mensaje en ClickUp', style: EST.icoBt }, icono('ext', { clase: 's' })) : null),
    texto(m.texto, { yo, buscar: resultado ? S.buscar : '' }));
  if (!enHilo && n) {
    el.append(h('button', { type: 'button', 'aria-expanded': String(abiertoHilo), on: { click: () => { abiertoHilo ? S.abiertos.delete(m.id) : S.abiertos.add(m.id); S.mantenerScroll = true; pintar(S); } },
      style: { ...EST.linkBt, gridColumn: '2', justifySelf: 'start', margin: '0 calc(-1 * var(--s-2))' } },
    icono('chat', { clase: 's' }), `${fmt.num(n)} ${n === 1 ? 'respuesta' : 'respuestas'}`, icono(abiertoHilo ? 'up' : 'chev', { clase: 's' })));
    if (abiertoHilo) {
      el.append(h('div', { style: { gridColumn: '2', margin: 'var(--s-1) 0', borderLeft: '2px solid var(--line)', paddingLeft: 'var(--s-3)', display: 'grid', gap: 'var(--s-1)' } },
        resp.map(r => mensajeCu(S, c, r, { enHilo: true })),
        n > resp.length ? h('span', { style: EST.meta }, `Hay ${fmt.num(n - resp.length)} respuestas más en ClickUp.`) : null));
    }
  }
  return el;
}

// ===================================================================== búsqueda y menciones
function filaPulsable(el, ir) {
  el.tabIndex = 0; el.setAttribute('role', 'button'); el.style.cursor = 'pointer';
  el.addEventListener('click', e => { if (!e.target.closest('a, button')) ir(); });
  el.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target === el) ir(); });
  return el;
}

function vistaBusqueda(S, estrecho) {
  const zona = h('div', { style: { ...EST.msgs, paddingTop: 'var(--s-1)' } });
  const r = S.res;
  const app = r?.resultados || [], cu = r?.clickup || [];
  if (S.buscar.length < 2) zona.append(h('div', { style: { padding: '0 var(--s-5)' } }, vacioLinea('Escribe al menos dos letras.', { icono: 'buscar' })));
  else if (!r) zona.append(h('div', { style: { padding: '0 var(--s-5)' } }, vacioLinea('Buscando…', { icono: 'buscar' })));
  else if (!app.length && !cu.length) zona.append(h('div', { style: { padding: '0 var(--s-5)' } }, vacioLinea(`Nada con «${S.buscar}» en tus canales de la app ni en tu ClickUp.`, { icono: 'buscar' })));
  app.forEach(m => {
    const c = canalApp(S, m.canal_id);
    zona.append(filaPulsable(mensajeApp(S, c, m, [], { enHilo: true, resultado: true, donde: c?.titulo }), () => { if (m.hilo_de) S.abiertos.add(m.hilo_de); abrir(S, { tipo: 'app', id: m.canal_id }); }));
  });
  cu.forEach(m => {
    const c = canalCu(S, m.canal_id);
    zona.append(filaPulsable(mensajeCu(S, c, m, { enHilo: true, resultado: true, donde: `ClickUp · ${m.tipo_canal === 'canal' ? '#' : ''}${m.canal}` }), () => abrir(S, { tipo: 'cu', id: m.canal_id })));
  });
  return [h('header', { style: EST.cab }, h('h2', { style: EST.h2 }, botonVolver(S, estrecho), h('span', { style: { color: 'var(--accent)', display: 'inline-flex' } }, icono('buscar')), r ? `${fmt.num(app.length + cu.length)} resultados` : 'Buscando'), h('span', { style: EST.meta }, `«${S.buscar}»`)), zona, h('div', {})];
}

function vistaMenciones(S, estrecho) {
  const zona = h('div', { style: { ...EST.msgs, paddingTop: 'var(--s-1)' } });
  const app = (S.A?.campana?.items || []);
  const cu = S.D?.menciones || [];
  if (!app.length && !cu.length) zona.append(h('div', { style: { padding: '0 var(--s-5)' } }, vacioLinea('Nadie te ha mencionado en tus canales.', { icono: 'ok' })));
  app.forEach(x => {
    const c = canalApp(S, x.canal_id);
    const m = { id: x.id, tipo: 'mensaje', quien: x.quien, hora: x.hora, texto: x.texto, te_menciona: true };
    zona.append(filaPulsable(mensajeApp(S, c, m, [], { enHilo: true, resultado: true, donde: `${x.canal}${x.tipo === 'aviso' ? ' · aviso para ti' : x.tipo === 'escalado' ? ' · te sube a ti' : ''}` }),
      () => { if (x.hilo_de) S.abiertos.add(x.hilo_de); abrir(S, { tipo: 'app', id: x.canal_id }); }));
  });
  cu.forEach(m => {
    const c = canalCu(S, m.canal_id);
    zona.append(filaPulsable(mensajeCu(S, c, { autor: m.autor, fecha: m.fecha, texto: m.texto, menciones: m.a_todos ? [] : [S.pid] }, { enHilo: true, resultado: true,
      donde: `ClickUp · ${c?.tipo === 'canal' ? '#' : ''}${m.canal}${m.hilo_de ? ' · en un hilo' : ''}${m.a_todos ? ' · a todo el canal' : ''}` }),
    () => { if (!c) return; if (m.hilo_de) S.abiertos.add(m.hilo_de); abrir(S, { tipo: 'cu', id: c.id }); }));
  });
  return [h('header', { style: EST.cab }, h('h2', { style: EST.h2 }, botonVolver(S, estrecho), h('span', { style: { color: 'var(--accent)', display: 'inline-flex' } }, icono('campana')), 'Te han mencionado'), h('span', { style: EST.meta }, 'Lo más reciente arriba. Pulsa para ir al canal.')), zona, h('div', {})];
}

// ===================================================================== preferencias y espejo (plegados al pie)
function plegable(icon, titulo, ...cuerpo) {
  return h('details', { class: 'panel' },
    h('summary', { style: { display: 'flex', alignItems: 'center', gap: 'var(--s-2)', padding: 'var(--s-4) var(--relleno)', minHeight: 'var(--s-12)', cursor: 'pointer', font: 'var(--t-h2)', listStyle: 'none' } },
      h('span', { style: { color: 'var(--accent)', display: 'inline-flex' } }, icono(icon)), titulo,
      h('span', { style: { marginLeft: 'auto', color: 'var(--dim)', display: 'inline-flex' } }, icono('chev', { clase: 's' }))),
    h('div', { style: { display: 'grid', gap: 'var(--s-3)', padding: '0 var(--relleno) var(--relleno)', font: 'var(--t-cuerpo)', color: 'var(--mid)' } }, ...cuerpo));
}

function panelPreferencias(S) {
  const pref = S.A.preferencias || {};
  const sil = new Set(pref.silenciados || []);
  const hora = h('input', { type: 'time', value: pref.hora_resumen || '08:30', 'aria-label': 'Hora del resumen diario', disabled: S.ctx.soloLectura || null, style: { ...EST.campo, flex: '0 0 auto', width: 'auto' } });
  const marcas = appCanales(S).filter(c => c.tipo !== 'cliente' || c.ultimo).map(c => {
    const cb = h('input', { type: 'checkbox', checked: sil.has(c.id) || null, disabled: S.ctx.soloLectura || null, 'data-canal': c.id });
    return h('label', { style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-2)', minHeight: 'var(--s-8)', font: 'var(--t-cuerpo)', color: 'var(--ink)' } }, cb, c.titulo);
  });
  const guardarPref = async () => {
    const silenciados = [...S.raiz.querySelectorAll('input[type=checkbox][data-canal]')].filter(x => x.checked).map(x => x.dataset.canal);
    try {
      const r = await S.ctx.api('canales/preferencias', { metodo: 'POST', cuerpo: { silenciados, hora_resumen: hora.value } });
      S.A.preferencias = r.preferencias;
      await refrescarCanales(S);
      avisoFlotante('Guardado.');
      pintar(S);
      avisarCampana();
    } catch (e) { avisoFlotante(String(e?.message || 'No se pudo guardar'), { icono: 'alert' }); }
  };
  const res = S.A.campana?.resumen;
  return plegable('campana', 'Tus avisos: canales silenciados y resumen diario',
    h('p', { style: { margin: '0' } }, `Cada día, a tu hora (${pref.zona || 'Europe/Madrid'}), la campana te deja un resumen: tus avisos abiertos, los que tienen el plazo pasado y tus menciones. Los canales silenciados no suman en «sin leer» ni en la campana; las menciones y los avisos con tu nombre siguen llegando.`),
    h('div', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2) var(--s-3)' } }, h('span', {}, 'Hora del resumen'), hora),
    h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-1) var(--s-4)' } }, h('span', { style: { ...EST.eyebrow, flexBasis: '100%' } }, 'Silenciar'), ...marcas),
    h('div', {}, h('button', { type: 'button', class: 'bt pri', disabled: S.ctx.soloLectura || null, on: { click: guardarPref } }, icono('ok'), 'Guardar')),
    res ? h('div', { style: { display: 'grid', gap: 'var(--s-1)' } }, h('span', { style: EST.eyebrow }, 'Tu resumen de hoy'),
      h('pre', { style: { margin: '0', whiteSpace: 'pre-wrap', font: 'var(--t-cuerpo)', color: 'var(--ink)', background: 'var(--card-2)', border: 'var(--borde-suave)', borderRadius: 'var(--r-m)', padding: 'var(--s-3)' } }, res.texto))
      : h('span', { style: EST.meta }, `Tu resumen de hoy sale a las ${pref.hora_resumen || '08:30'}.`));
}

function panelEspejo(S) {
  const meta = S.D?._meta || {};
  const num = v => (v === null || v === undefined ? null : fmt.num(v));
  const datos = [
    num(meta.canales_total) && `${num(meta.canales_total)} canales en ClickUp`,
    num(meta.canales_de_cliente) && `${num(meta.canales_de_cliente)} de clientes (están en su ficha)`,
    num(meta.canales_internos_activos) && `${num(meta.canales_internos_activos)} internos con actividad`,
    num(meta.canales_dormidos) && `${num(meta.canales_dormidos)} sin actividad en ${meta.dias || 120} días`,
  ].filter(Boolean);
  return plegable('key', 'Espejo de ClickUp: qué se ve y qué no',
    h('p', { style: { margin: '0', maxWidth: '72ch' } }, 'Los canales de ClickUp se leen con la llave de Tomás, solo lectura, y aquí salen los que son tuyos. Desde la app no se escribe en ClickUp: los mensajes de los grupos de la app se quedan en la app. Si un día se quiere escribir en ClickUp desde aquí, cada persona tendría que conectar su propia cuenta para que el mensaje salga con su nombre; eso lo decide Tomás.'),
    datos.length ? h('p', { style: { ...EST.meta, margin: '0' } }, `Datos de hoy: ${datos.join(' · ')}.`) : null);
}
