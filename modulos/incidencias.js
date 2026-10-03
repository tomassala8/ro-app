// modulos/incidencias.js · M14 «Incidencias y control de Operaciones» (E2 del plan v2 · puntos 7 y 9 de Mili, M5).
//
// Responde en segundos a la pregunta de Mili: ¿qué se incumple, quién es responsable, por qué, qué hizo Operaciones
// y si está resuelto o hay que escalar?
//   · Ficha de incidencia con ciclo: detectada → avisada → reiterada → escalada (decisión para Tomás con reloj de 48 h;
//     a Coti, 24 h) → resuelta con prueba → comprobada con el dato del día siguiente (si sigue, se reabre sola).
//   · Lo pedido vuelve arriba a los 2 días con «Toca escalarlo».
//   · Causa en dos campos (regla R13): dónde se rompe y por qué (sistema · configuración · ejecución · gestión de
//     Operaciones). La marca quien escala; Tomás la puede cambiar. Sin prueba de aviso, cuenta como gestión.
//   · Pestañas: Incidencias · Quién falla en qué (mapa de calor y mapa de control, del panel v27) · Incongruencias
//     ClickUp ↔ Desk ↔ CRM y accesos de quien ya no está · Traspasos de cartera · Quién vio primero · El mes.
// Datos: data/incidencias/incidencias.json (fuentes_incidencias/generar_incidencias.py, solo lectura), RECORTADO por
// servir.py (filas con cliente_id, solo si ve el cliente; con persona_id, solo si ve a esa persona).
// El ciclo se guarda como acciones del módulo en local.db (ctx.accion → estado «simulada», imborrable) y en el rastro.
// Nada se escribe en Desk, Zadarma, ClickUp ni el CRM.

import {
  h, fmt, tile, tiles, listaLoPrimero, chipEstado, chipsFiltro, vacio, botonConfirmar, avisoParcial, logoCliente, panel,
  frescura, icono, iniciales, pestanas, tablaDensa, copiar, avisoFlotante, barraEtapas, embudoBarras, fechas,
} from '../componentes.js';
import { conTickets, sinCodigos } from './_legible.js';

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

/** V2 (40_A B5): antigüedad en llano: a partir de 48 h, en días («478 h» → «20 días», la antigüedad común de fechas). */
const enDias = t => (typeof t === 'string' ? t.replace(/\b(\d{2,})\s?h\b(?!\s+laborables)/g, (m, n) => (Number(n) > 48 ? fechas.antiguedad(Number(n)) : m)) : t);

/** Revisión 44 (N3, N4): los textos que llegan de Desk o ClickUp traen los nombres sin tilde («Tomas Sala») y alguna
 *  concordancia rota («1 de 1 tickets abiertos»). Si la persona está en la tabla de personas, sale con su nombre bien escrito. */
const _sinAcento = s => String(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '');
let _reNombres = null;
function nombresBien(t, personas = []) {
  if (typeof t !== 'string' || !t) return t;
  if (!_reNombres) {
    _reNombres = [];
    for (const p of personas) for (const n of [p.nombre, p.alias]) if (n && _sinAcento(n) !== n) _reNombres.push([new RegExp(`(^|[^\\wáéíóúñ])${_sinAcento(n).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![\\wáéíóúñ])`, 'g'), n]);
    _reNombres.sort((a, b) => b[1].length - a[1].length);
  }
  for (const [re, n] of _reNombres) t = t.replace(re, (m, pre) => pre + n);
  return t.replace(/\b1 de 1 tickets abiertos\b/g, 'el único ticket abierto').replace(/\b(\d+) de 1 tickets\b/g, '$1 de 1 ticket');
}
let PERSONAS = [];

const ID = 'incidencias';
const H48 = 48 * 36e5;
const OPERACIONES = new Set(['mili', 'tomas', 'constanza']);

const DONDE = { publicidad: 'Publicidad', despacho: 'Despacho (el cliente)', integracion: 'Integración', produccion: 'Producción', contacto_cliente: 'Contacto con el cliente' };
const POR_QUE = { sistema: 'Sistema', configuracion: 'Configuración', ejecucion: 'Ejecución de una persona', gestion_operaciones: 'Gestión de Operaciones' };
const ICONO_POR_QUE = { sistema: 'plug', configuracion: 'aj', ejecucion: 'persona', gestion_operaciones: 'eq' };
const ICONO_ORIGEN = { desk: 'mail', zadarma: 'phone', alarma: 'fire' };
const TEXTO_ORIGEN = { desk: 'Desk', zadarma: 'Zadarma', alarma: 'Cliente crítico' };
const ETAPAS = [
  { texto: 'Detectada', icono: 'alert' }, { texto: 'Avisada', icono: 'send' }, { texto: 'Reiterada', icono: 'recargar' },
  { texto: 'Escalada', icono: 'sube' }, { texto: 'Resuelta', icono: 'check' }, { texto: 'Comprobada', icono: 'ok' },
];
const ESTADO = {
  detectada: { t: 'Detectada', c: 'ambar', i: 0 }, sin_avisar: { t: 'Sin avisar > 48 h', c: 'rojo', i: 0 },
  avisada: { t: 'Avisada', c: 'ambar', i: 1 }, reiterada: { t: 'Reiterada', c: 'ambar', i: 2 },
  toca_escalar: { t: 'Toca escalarlo', c: 'rojo', i: 2 }, escalada: { t: 'Escalada', c: 'ambar', i: 3 },
  escalada_vencida: { t: 'Escalado sin respuesta', c: 'rojo', i: 3 }, por_comprobar: { t: 'Resuelta · se comprueba mañana', c: 'azul', i: 4 },
  reabierta: { t: 'Reabierta: el dato dice que sigue', c: 'rojo', i: 2 }, comprobada: { t: 'Resuelta y comprobada', c: 'verde', i: 5 },
  no_aplica: { t: 'No aplica', c: 'gris', i: -1 },
};
const ORDEN_ESTADO = ['reabierta', 'escalada_vencida', 'toca_escalar', 'sin_avisar', 'escalada', 'detectada', 'reiterada', 'avisada', 'por_comprobar', 'comprobada', 'no_aplica'];
const CANALES = ['Chat de ClickUp', 'Correo (Desk)', 'WhatsApp', 'Llamada', 'Reunión o 1:1'];

// ------------------------------------------------------------------ utilidades de fecha
const fechaLocal = s => { if (!s) return null; const d = new Date(s.length <= 10 ? `${s}T00:00:00` : s.replace(' ', 'T')); return Number.isNaN(+d) ? null : d; };
const fechaServ = s => { if (!s) return null; const d = new Date(`${s.replace(' ', 'T')}Z`); return Number.isNaN(+d) ? null : d; };   // hora del servidor (UTC)
const diaISO = d => d ? `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` : null;
const fh = d => d ? `${d.getDate()}-${_MES3[d.getMonth()]}${d.getHours() || d.getMinutes() ? `, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` : ''}` : '—';   // §2.3
const dias = d => d ? Math.max(0, Math.floor((Date.now() - d) / 864e5)) : null;
const reloj = (desde, horas) => {
  const fin = +desde + horas * 36e5; const resta = (fin - Date.now()) / 36e5;
  return resta >= 0 ? { vencido: false, texto: `Quedan ${Math.ceil(resta)} h`, estado: resta < 12 ? 'ambar' : 'azul' }
    : { vencido: true, texto: `Vencido hace ${-resta < 48 ? `${Math.floor(-resta)} h` : `${Math.floor(-resta / 24)} días`}`, estado: 'rojo' };
};
const vp = a => { try { return typeof a.vista_previa === 'string' ? JSON.parse(a.vista_previa || '{}') || {} : a.vista_previa || {}; } catch { return {}; } };

// ------------------------------------------------------------------ maquetación (guía de la auditoría 30, N6)
// SIN hoja propia: la letra y el color los ponen las clases comunes (sub, titulo-seccion, chip, panel, campo…); aquí
// solo quedan rejillas y rellenos en estilo en línea, siempre con tokens (--s-*, --relleno, --r-*).
const PAD = { padding: 'var(--s-2) var(--relleno) var(--s-4)' };
const ACC = { padding: 'var(--s-3) var(--relleno)' };
const FORM = { display: 'grid', gap: 'var(--s-3)', padding: 'var(--s-4) var(--relleno)', background: 'var(--card-2)', borderTop: 'var(--borde-suave)' };
const DOS_C = { display: 'grid', gap: 'var(--s-3)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))' };
const ERR = { color: 'var(--bad-ink)' };
const META = { display: 'block', font: 'var(--t-meta)' };
const campoL = (et, el) => h('label', { class: 'campo' }, h('span', { class: 'campo-et' }, et), el);
/** Casilla de los mapas: el color dice la gravedad (verde a cero · ámbar · rojo · rojo fuerte · gris sin dato). */
const CELDA_BASE = { border: '0', borderRadius: 'var(--r-s)', padding: 'var(--s-2) var(--s-1)', fontWeight: '700', minHeight: '40px', display: 'grid', placeContent: 'center', textAlign: 'center', cursor: 'pointer', textDecoration: 'none' };
const CELDA = { '': { background: 'var(--good-soft)', color: 'var(--good-ink)' }, a: { background: 'var(--warn-soft)', color: 'var(--warn-ink)' }, r: { background: 'var(--bad-soft)', color: 'var(--bad-ink)' },
  rr: { background: 'var(--bad-ink)', color: 'var(--card)' }, na: { background: 'var(--off-soft)', color: 'var(--dim)', cursor: 'default' }, carga: { background: 'var(--card-2)', color: 'var(--ink)', cursor: 'default' } };
const celdaEst = (cls, activa) => ({ ...CELDA_BASE, ...(CELDA[cls] || CELDA['']), ...(activa ? { outline: '2px solid var(--accent)', outlineOffset: '1px' } : {}) });
const NOM = { display: 'flex', alignItems: 'center', gap: 'var(--s-2)', fontWeight: '600', minWidth: '0' };
const CAB = { textAlign: 'center', padding: 'var(--s-1) 0', alignSelf: 'end', overflowWrap: 'anywhere' };
/** Las alertas llevan cuatro botones: debajo del texto, no en una tercera columna estrecha. */
const botonesDebajo = nodo => { nodo.querySelectorAll?.('.primero > li').forEach(li => { li.style.gridTemplateColumns = '32px minmax(0, 1fr)'; const a = li.querySelector('.acc'); if (a) Object.assign(a.style, { gridColumn: '2', justifyContent: 'flex-start' }); }); return nodo; };
function estilos() { document.getElementById('inc-estilos')?.remove(); }   // hoja de antes de la guía 30

// ================================================================== estado (datos + ciclo)
function crearEstado(ctx, D, acciones) {
  PERSONAS = ctx.datos.personas || [];
  const personas = new Map((ctx.datos.personas || []).map(p => [p.id, p]));
  const nom = id => { if (!id) return 'sin responsable'; const p = personas.get(id); return p ? (p.alias || p.nombre) : id; };
  const cli = new Map(ctx.clientes.map(c => [c.id, c]));
  const datosDia = fechaLocal(D.generado);
  const porObjeto = new Map();
  for (const a of acciones) { if (!porObjeto.has(String(a.objeto))) porObjeto.set(String(a.objeto), []); porObjeto.get(String(a.objeto)).push(a); }
  for (const l of porObjeto.values()) l.sort((x, y) => (x.creada < y.creada ? -1 : 1));

  const incs = (D.incidencias || []).map(i => calcular(i));

  function calcular(i) {
    // Eventos: historia previa (rastro de ClickUp) + acciones de la app (local.db, hora del servidor).
    const evs = (i.historia || []).map(e => ({ ...e, t: fechaLocal(e.fecha), origen: 'rastro' }));
    if (i.estado_inicial) evs.push({ paso: i.estado_inicial.paso, quien: null, t: fechaLocal(i.estado_inicial.fecha), texto: i.estado_inicial.texto, enlace: i.estado_inicial.prueba, por: 'rastro de ClickUp', origen: 'rastro', inicial: true });
    const app = porObjeto.get(i.id) || [];
    for (const a of app) {
      const v = vp(a);
      const paso = { avisar: 'avisada', reiterar: 'reiterada', escalar: 'escalada', resolver: 'resuelta', no_aplica: 'no_aplica', decidir: 'decision', respuesta: 'respuesta', visto: 'visto', causa: 'causa', reabrir: 'reabierta' }[a.tipo] || a.tipo;
      evs.push({ paso, quien: a.quien, a: v.a, por: v.por, texto: a.texto, enlace: v.prueba || null, t: fechaServ(a.creada), origen: 'app', v, accion_id: a.id });
    }
    evs.sort((x, y) => (+x.t || 0) - (+y.t || 0));
    const det = fechaLocal(i.detectada);
    const avisos = evs.filter(e => ['avisada', 'reiterada', 'escalada', 'accion'].includes(e.paso) && OPERACIONES.has(e.quien));
    const ultAviso = avisos.length ? avisos[avisos.length - 1] : null;
    const cierres = evs.filter(e => ['resuelta', 'no_aplica', 'reabierta'].includes(e.paso));
    const cierre = cierres.length ? cierres[cierres.length - 1] : null;
    const escal = evs.filter(e => e.paso === 'escalada');
    const ultEsc = escal.length ? escal[escal.length - 1] : null;
    const decision = ultEsc ? evs.find(e => (e.paso === 'decision' || e.paso === 'respuesta') && +e.t > +ultEsc.t) : null;
    let estado, relojEsc = null;
    if (cierre?.paso === 'no_aplica') estado = 'no_aplica';
    else if (cierre?.paso === 'resuelta') {
      if (cierre.inicial) estado = 'comprobada';
      else estado = datosDia && diaISO(datosDia) > diaISO(cierre.t) ? 'reabierta' : 'por_comprobar';
    } else if (ultEsc && !decision) {
      const horas = ultEsc.v?.reloj_h || 48;
      relojEsc = { ...reloj(ultEsc.t, horas), a: ultEsc.a || ultEsc.v?.a, desde: ultEsc.t, horas };
      estado = relojEsc.vencido ? 'escalada_vencida' : 'escalada';
    } else if (cierre?.paso === 'reabierta') estado = 'reabierta';
    else if (avisos.length) {
      const viejo = ultAviso && Date.now() - ultAviso.t > H48;
      estado = viejo ? 'toca_escalar' : avisos.length > 1 ? 'reiterada' : 'avisada';
    } else estado = det && Date.now() - det > H48 ? 'sin_avisar' : 'detectada';
    // Causa: la confirmada (última «causa»), o la propuesta. Regla R13: sin prueba de aviso tras 48 h, una «ejecución»
    // cuenta como «gestión de Operaciones».
    const causas = evs.filter(e => e.paso === 'causa');
    const conf = causas.length ? causas[causas.length - 1] : null;
    let propuesta = { donde: i.donde, por_que: i.por_que, motivo: i.por_que_motivo };
    if (!avisos.length && i.por_que === 'ejecucion' && det && Date.now() - det > H48) {
      propuesta = { donde: i.donde, por_que: 'gestion_operaciones', motivo: 'Nadie de Operaciones avisó por escrito en 48 h: por la regla de los avisos por escrito cuenta como «gestión de Operaciones».' };
    }
    const causa = conf ? { donde: conf.v.donde, por_que: conf.v.por_que, explicacion: conf.v.explicacion, quien: conf.quien, t: conf.t, confirmada: true, cambiada: causas.length > 1 && conf.quien === 'tomas' && causas[causas.length - 2].quien !== 'tomas' } : { ...propuesta, confirmada: false };
    const vistos = evs.filter(e => e.paso === 'visto');
    const c = i.cliente_id ? cli.get(i.cliente_id) : null;
    const abiertoDias = dias(det);
    const abierta = !['comprobada', 'no_aplica', 'por_comprobar'].includes(estado);
    return { ...i, evs, det, avisos, ultAviso, estado, relojEsc, causa, vistos, c, abiertoDias, abierta,
      responsable: nom(i.responsable_id), primeroVisto: vistos[0] || null, resueltaEn: cierre?.paso === 'resuelta' ? cierre.t : null };
  }

  return { D, ctx, nom, cli, incs, acciones, personas, datosDia, porObjeto };
}

// ================================================================== render
export default {
  id: ID,
  titulo: 'Incidencias',
  grupo: 'Clientes',
  puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', proyectos: 'todo' },
  async render(cont, ctx) {
    vigilarCortes(cont);
    estilos();
    let D;
    try { D = await ctx.datosModulo('incidencias/incidencias'); }
    catch (e) {
      cont.append(vacio({ icono: 'alert', tono: 'aviso', borde: true, titulo: 'No se pudieron leer las incidencias', texto: String(e?.message || e), quien: 'Tomás (regenerar con fuentes_incidencias/generar_incidencias.py)' }));
      return;
    }
    // V2 (B5): textos con la antigüedad en días (los datos de antes de este cambio aún traen «478 h»)
    D = { ...D, incidencias: (D.incidencias || []).map(i => ({ ...i, texto: enDias(i.texto), titulo: enDias(i.titulo) })) };
    // V2: «Contesta» del mapa de control con LA MISMA vara que la Bandeja, «Tu cumplimiento» y el día de Mili (controlPersona
    // de mi_dia_bloques.js: sin automáticos, ni viejos, ni lo ya despachado en la cola de la Bandeja). Solo si se pinta el mapa.
    if ((D.control || []).length && !ctx.params[0] && ctx.veModulo('bandeja')) {
      try {
        const [MB, bj, accB] = await Promise.all([import('./mi_dia_bloques.js'), ctx.datosModulo('bandeja/bandeja'),
          ctx.servidor ? ctx.api('acciones?modulo=bandeja').then(r => r.acciones || []).catch(() => []) : Promise.resolve([])]);
        const Dm = { opcional: n => (n === 'bandeja/bandeja' ? bj : null), dato: n => { if (n === 'bandeja/bandeja' && bj) return bj; throw { falta: n }; } };
        D = { ...D, control: D.control.map(x => {
          if (!x.persona_ref) return x;
          const cp = MB.controlPersona(ctx, Dm, x.persona_ref, { accionesBandeja: accB });
          return cp.contesta ? { ...x, contesta: { ...x.contesta, mas48: cp.contesta.mas48, correos: cp.contesta.total } } : x;
        }) };
      } catch { /* sin la Bandeja: la cifra del generador (la misma regla, sin descontar la cola) */ }
    }
    const cargarAcciones = async () => {
      if (!ctx.servidor) return [];
      try { return (await ctx.api(`acciones?modulo=${ID}`)).acciones || []; } catch { return []; }
    };
    // Alertas de web y SEO (N4) del departamento de quien mira: data/alertas/p_<persona>.json (solo lo suyo, o su
    // departamento si es jefe; Mili y Tomás, todo) y la cola de acciones de «Alertas» (mismos tipos alerta_*).
    const alertas = await Promise.all([
      // barrido v1: no se pide lo que no se puede ver (los setters no tienen «Alertas»: antes salía un 403 en consola)
      ctx.veModulo('alertas') ? ctx.datosModulo(`alertas/p_${ctx.persona.id}`).catch(() => null) : Promise.resolve(null),
      ctx.servidor && ctx.veModulo('alertas') ? ctx.api('acciones?modulo=alertas').then(r => r.acciones || []).catch(() => []) : Promise.resolve([]),
    ]).then(([A, acc]) => ({ A, acc }));
    const rehacer = async () => {
      const S = crearEstado(ctx, D, await cargarAcciones());
      S.rehacer = rehacer;
      S.alertas = alertas;
      const y = window.scrollY;
      cont.replaceChildren();
      if (ctx.params[0]) pintarFicha(cont, S, ctx.params[0]);
      else pintarInicio(cont, S);
      for (const el of cont.children) el.style.minWidth = '0';
      window.scrollTo({ top: y });
    };
    await rehacer();
    sinRepetirConsejo(cont);
  },
};

/** A1 · misma regla que «Lo mío»: el consejo de la IA que pone la carcasa arriba («Qué haría yo hoy aquí») no repite una
 *  incidencia que ya está en «Para Tomás» o «Lo primero hoy». Se ocultan sus filas (y el bloque si no queda ninguna);
 *  el bloque se queda en su sitio, oculto, para que la carcasa no lo vuelva a poner. */
let OBS_CONSEJO = null;
function sinRepetirConsejo(main) {
  OBS_CONSEJO?.disconnect();
  const arreglar = () => {
    const c = main.querySelector(':scope > [data-ia="consejo"]');
    if (!c) return;
    const ya = new Set([...main.querySelectorAll('.panel .primero a[href^="#/incidencias/"]')].map(a => a.getAttribute('href')));
    const items = [...c.querySelectorAll('li.ia-accion')];
    let quedan = 0;
    for (const li of items) {
      const repe = ya.has(li.querySelector('a[data-ir]')?.getAttribute('href'));
      li.hidden = repe;
      if (!repe) { const n = li.querySelector('.n'); if (n) n.textContent = String(++quedan); }
    }
    const primera = items.find(li => !li.hidden)?.querySelector('b')?.textContent;
    const res = c.querySelector(':scope > .ia-sub');
    if (res && primera) res.replaceChildren(h('b', {}, primera), quedan > 1 ? ` · y ${quedan - 1} más` : '');
    if (c.hidden !== !quedan) c.hidden = !quedan;
  };
  let pend = null;
  const obs = new MutationObserver(() => {
    if (!location.hash.startsWith(`#/${ID}`)) { obs.disconnect(); return; }
    clearTimeout(pend); pend = setTimeout(arreglar, 30);
  });
  obs.observe(main, { childList: true });
  OBS_CONSEJO = obs;
  arreglar();
}

const gestiona = ctx => ctx.nivel === 'todo' && !ctx.soloLectura;
const NOMBRE_FUENTE = { desk: 'Desk', zadarma: 'Zadarma', zadarma_ext: 'Extensiones de Zadarma', panel: 'Panel de Operaciones', rastro: 'Rastro de ClickUp', desk_agentes: 'Agentes de Desk', crm_usuarios: 'Usuarios del CRM', clickup_miembros: 'Miembros de ClickUp' };
const fres = (D, k) => { const f = D.fuentes?.[k]; if (!f) return { fuente: NOMBRE_FUENTE[k] || k, estado: 'sin datos' }; const d = fechaLocal(f.hora); return { fuente: f.fuente, edad_h: d ? Math.max(0, (Date.now() - d) / 36e5) : null, estado: f.estado === 'bien' ? 'ok' : 'viejo' }; };

// ================================================================== alertas de web y SEO (N4)
const DEP_WEB = { web: 'Web', seo: 'SEO' };
const TIPO_ALERTA = { lo_tengo: 'alerta_lo_tengo', resuelta: 'alerta_resuelta', no_aplica: 'alerta_no_aplica' };
const DE_ALERTA = { alerta_vista: 'vista', alerta_lo_tengo: 'lo_tengo', alerta_resuelta: 'resuelta', alerta_no_aplica: 'no_aplica', alerta_reabrir: 'nueva' };
const CHIP_ALERTA = { lo_tengo: ['azul', 'Alguien la tiene'], reabierta: ['rojo', 'Reabierta'], resuelta: ['verde', 'Resuelta · se comprueba'], no_aplica: ['gris', 'No aplica'] };
function estadoAlerta(a, acc, generado) {
  const gen = generado ? new Date(String(generado).replace(' ', 'T')) : null;
  const ult = acc.filter(x => x.objeto === a.id && DE_ALERTA[x.tipo]).sort((p, q) => (p.creada === q.creada ? (Number(q.id) || 0) - (Number(p.id) || 0) : p.creada < q.creada ? 1 : -1))[0];
  if (ult && (!gen || new Date(`${String(ult.creada).replace(' ', 'T')}Z`) > gen)) return DE_ALERTA[ult.tipo];
  return a.estado || 'nueva';
}
/** La cola de alertas de web y SEO que esta persona ve (las suyas; su departamento si es jefe; todas para Mili y
 *  Tomás), lo más grave y lo vencido arriba, 10 visibles. Lo tengo · Resuelta · No aplica van a la pantalla
 *  «Alertas» (tipos alerta_*), así el escalado se para igual que allí. Sin alertas de web o SEO: no se pinta. */
function panelAlertasWeb(S, yaArriba = new Set()) {
  const { ctx } = S;
  const A = S.alertas?.A; const acc = S.alertas?.acc || [];
  const ahora = new Date();
  const todas = (A?.alertas || []).filter(a => DEP_WEB[a.departamento] && !(a.incidencia_id && yaArriba.has(a.incidencia_id))).map(a => ({ ...a, est: estadoAlerta(a, acc, A.generado), venceD: a.vence ? fechaLocal(a.vence) : null }));
  if (!todas.length) return null;
  const abiertas = todas.filter(a => !['resuelta', 'no_aplica'].includes(a.est));
  const pasada = a => a.venceD && a.venceD < ahora && a.est !== 'lo_tengo';
  abiertas.sort((a, b) => (b.gravedad === 'alta') - (a.gravedad === 'alta') || pasada(b) - pasada(a) || (+a.venceD || 0) - (+b.venceD || 0));
  const puede = ctx.veModulo('alertas') && !ctx.soloLectura;
  const marcar = (a, estado, texto) => async () => {
    await ctx.accion({ herramienta: 'app', modulo: 'alertas', tipo: TIPO_ALERTA[estado], objeto: a.id, cliente_id: a.cliente_id || null,
      texto: (texto || `${estado === 'lo_tengo' ? 'Lo tengo' : 'Resuelta'}: ${a.motivo}`).slice(0, 400), ...(estado === 'no_aplica' ? { motivo: texto } : {}),
      vista_previa: { alerta: a.id, departamento: a.departamento, motivo: a.motivo, estado, desde: 'incidencias' } });
    acc.push({ objeto: a.id, tipo: TIPO_ALERTA[estado], creada: new Date().toISOString().slice(0, 19).replace('T', ' ') });
    return estado === 'lo_tengo' ? 'Lo tienes tú · el escalado se para' : estado === 'resuelta' ? 'Resuelta · se comprueba con el dato siguiente' : 'No aplica · con su motivo';
  };
  const cuenta = k => abiertas.filter(a => a.departamento === k).length;
  const sub = `${Object.keys(DEP_WEB).filter(cuenta).map(k => `${DEP_WEB[k]} ${cuenta(k)}`).join(' · ') || 'Nada abierto'}${abiertas.filter(pasada).length ? ` · ${abiertas.filter(pasada).length} con el plazo pasado` : ''} · lo más grave arriba`;
  const sec = panel({ titulo: 'Alertas de web y SEO', icono: 'campana', sub,
    acciones: ctx.veModulo('alertas') ? h('a', { class: 'bt mini', href: '#/alertas' }, icono('derecha'), `Ver las ${fmt.num(todas.length)} en Alertas`) : null },
  listaLoPrimero(abiertas.slice(0, 5).map(a => {
    const chip = CHIP_ALERTA[a.est];
    return {
      estado: a.gravedad === 'alta' || pasada(a) ? 'rojo' : 'ambar', icono: a.departamento === 'web' ? 'globe' : 'buscar',
      motivo: `${a.cliente || 'Sin cliente'} · ${a.titulo}`,
      detalle: [h('span', {}, conTickets(enDias(a.motivo))), h('span', { class: 'sub', style: { display: 'block' } }, `${DEP_WEB[a.departamento]} · lo lleva ${S.nom(a.responsable_ahora || a.dueno_id)}${a.venceD ? ` · ${pasada(a) ? 'plazo pasado' : 'vence'} ${fh(a.venceD)}` : ''}`), chip ? chipEstado(chip[0], chip[1]) : null],
      botones: [
        a.abrir?.[0]?.url ? h('a', { class: 'bt mini', href: a.abrir[0].url, target: '_blank', rel: 'noopener' }, icono('ext'), a.abrir[0].texto || 'Abrir en la herramienta') : null,
        puede && a.est !== 'lo_tengo' ? botonConfirmar({ texto: 'Lo tengo', pregunta: '¿Te encargas tú?', confirmar: 'Sí', mini: true, alConfirmar: marcar(a, 'lo_tengo') }) : null,
        puede ? botonConfirmar({ texto: 'Resuelta', pregunta: '¿Resuelta? Se comprueba con el dato siguiente', confirmar: 'Sí', mini: true, alConfirmar: marcar(a, 'resuelta') }) : null,
        puede ? noAplicaAlerta(a, marcar) : null,
      ],
    };
  }), { vacio: { titulo: 'Todas marcadas', porque: 'Las alertas de web y SEO que ves están resueltas o no aplican.', celebrar: true } }),
  abiertas.length > 5 ? h('p', { class: 'sub', style: PAD }, `y ${abiertas.length - 5} más en Alertas del departamento.`) : null);
  botonesDebajo(sec);
  return sec;
}
function noAplicaAlerta(a, marcar) {
  const caja = h('span', { class: 'confirmar' });
  const ini = () => caja.replaceChildren(h('button', { type: 'button', class: 'bt mini', on: { click: preguntar } }, 'No aplica'));
  function preguntar() {
    const mot = h('input', { type: 'text', class: 'bt mini', style: { width: '160px', maxWidth: '100%', minWidth: '0' }, placeholder: 'Motivo (obligatorio)', 'aria-label': 'Motivo de «No aplica»' });
    const ok = h('button', { type: 'button', class: 'bt mini pri', on: { click: async () => {
      if (mot.value.trim().length < 4) { mot.focus(); mot.setAttribute('aria-invalid', 'true'); avisoFlotante('«No aplica» necesita un motivo', { icono: 'alert' }); return; }
      ok.disabled = true;
      try { const m = await marcar(a, 'no_aplica', `No aplica: ${mot.value.trim()}`)(); caja.replaceChildren(h('span', { class: 'estado', role: 'status' }, `✓ ${m}`)); }
      catch (e) { ok.disabled = false; avisoFlotante(`No se pudo: ${e?.message || e}`, { icono: 'alert' }); }
    } } }, 'Guardar');
    caja.replaceChildren(mot, ok, h('button', { type: 'button', class: 'bt mini', on: { click: ini } }, 'Cancelar'));
    mot.focus();
  }
  ini();
  return caja;
}

// ================================================================== inicio (pestañas)
function pintarInicio(cont, S) {
  const { ctx, D, incs } = S;
  const todo = ctx.nivel === 'todo';
  const abiertas = incs.filter(i => i.abierta);
  const mias = incs.filter(i => i.responsable_id === ctx.persona.id);
  ctx.titulo('Incidencias', todo
    ? `${abiertas.length} abiertas · ${abiertas.filter(i => ['toca_escalar', 'sin_avisar', 'reabierta', 'escalada_vencida'].includes(i.estado)).length} piden actuar hoy · datos de ${fh(fechaLocal(D.generado))}`
    : `Las incidencias de tus clientes y las tuyas · datos de ${fh(fechaLocal(D.generado))}`);

  // ---- Para Tomás (arriba del todo para él): escalados con reloj de 48 h
  if (ctx.persona.puestos.includes('direccion')) pintarParaTomas(cont, S);

  if (!todo && !incs.length && !(D.incongruencias || []).length && !(D.traspasos || []).length && !(D.mapa_calor || []).length) {
    const pAl = panelAlertasWeb(S, S.enParaTomas);
    if (pAl) cont.append(pAl);
    cont.append(vacio({ icono: 'ok', tono: 'celebrar', borde: true, titulo: 'No tienes incidencias',
      texto: 'Las incidencias son de clientes y de sistema. Tu puesto no lleva clientes, así que aquí solo aparecerán las que te nombren a ti.', quien: 'Mili (Operaciones)' }));
    return;
  }
  const nInc = (D.incongruencias || []).length;
  const nAcc = (D.accesos || []).filter(a => !a.ok).length;
  const lista = [
    { id: 'hoy', texto: 'Incidencias', icono: 'alert', cuenta: (todo ? abiertas : abiertas.filter(i => i.responsable_id === ctx.persona.id || i.c?.enCartera)).filter(i => ['toca_escalar', 'sin_avisar', 'reabierta', 'escalada_vencida'].includes(i.estado)).length, cuentaEstado: 'rojo' },
    { id: 'mapa', texto: 'Quién falla en qué', icono: 'grafico' },
    { id: 'incongruencias', texto: 'Incongruencias', icono: 'capas', cuenta: nInc + nAcc },
    { id: 'traspasos', texto: 'Traspasos', icono: 'users', cuenta: (D.traspasos || []).filter(t => estadoTraspaso(t, S).c === 'rojo').length, cuentaEstado: 'rojo' },
  ];
  if (todo && (D.vistos || []).length) lista.push({ id: 'vistos', texto: 'Quién vio primero', icono: 'ojo' });
  if (todo) lista.push({ id: 'mes', texto: 'El mes', icono: 'cal' });
  cont.append(pestanas({
    pestanas: lista, clave: 'incidencias.pestana', etiqueta: 'Apartados de incidencias',
    pintar: (id, zona) => {
      if (id === 'hoy') pintarHoy(zona, S, mias);
      else if (id === 'mapa') pintarMapa(zona, S);
      else if (id === 'incongruencias') pintarIncongruencias(zona, S);
      else if (id === 'traspasos') pintarTraspasos(zona, S);
      else if (id === 'vistos') pintarVistos(zona, S);
      else if (id === 'mes') pintarMes(zona, S);
      for (const el of zona.children) el.style.minWidth = '0';
    },
  }));
}

// ------------------------------------------------------------------ Para Tomás
function pintarParaTomas(cont, S) {
  const { ctx, incs } = S;
  const paraTomas = incs.filter(i => i.relojEsc && String(i.relojEsc.a || '').includes('tomas') && i.evs.some(e => e.paso === 'escalada' && e.origen === 'app'));
  const delRastro = incs.filter(i => ['escalada', 'escalada_vencida'].includes(i.estado) && !i.evs.some(e => e.origen === 'app' && e.paso === 'escalada') && String(ultimaEsc(i).a || '').includes('tomas'));
  S.enParaTomas = new Set(paraTomas.map(i => i.id));   // A1: lo de aquí no se repite en «Lo primero hoy»
  if (!paraTomas.length && !delRastro.length) return;
  cont.append(panel({ titulo: 'Para Tomás', icono: 'crown', sub: 'Lo que Operaciones te ha escalado: problema, recomendación y reloj de 48 h. Si vence, sale en rojo.' },
    paraTomas.length ? listaLoPrimero(paraTomas.map(i => ({
      estado: i.relojEsc.vencido ? 'rojo' : 'ambar', icono: 'sube',
      motivo: `${i.cliente || i.afectado || 'Sistema'} · ${i.titulo}`,
      // V2 (barrido v1): los tickets RO-#### del texto, como enlace a ese correo en la Bandeja (nunca un número suelto)
      detalle: conTickets(`${i.relojEsc.texto} · ${enDias(ultimaEsc(i).v?.problema || i.texto)}${ultimaEsc(i).v?.recomendacion ? ` — Recomendación: ${ultimaEsc(i).v.recomendacion}` : ''}`),
      botones: [h('a', { class: 'bt mini pri', href: `#/incidencias/${i.id}` }, icono('derecha'), 'Decidir')],
    }))) : null,
    delRastro.length ? h('p', { class: 'sub', style: PAD }, icono('hist', { clase: 's' }),
      ` Además, ${delRastro.length === 1 ? '1 cliente sigue abierto tras escalarlo' : `${delRastro.length} clientes siguen abiertos tras escalarlos`} Mili por ClickUp sin decisión escrita: ${delRastro.slice(0, 6).map(i => i.cliente).join(', ')}${delRastro.length > 6 ? '…' : ''}.`) : null));
}
const ultimaEsc = i => [...i.evs].reverse().find(e => e.paso === 'escalada') || {};

// ------------------------------------------------------------------ Incidencias (hoy)
function pintarHoy(zona, S, mias) {
  const { ctx, D, incs } = S;
  const todo = ctx.nivel === 'todo';
  const base = todo ? incs : incs;   // el servidor ya ha recortado: aquí solo llega lo que la persona puede ver
  const abiertas = base.filter(i => i.abierta);
  const cuenta = e => base.filter(i => i.estado === e).length;
  const toca = abiertas.filter(i => ['toca_escalar', 'sin_avisar'].includes(i.estado));
  const reab = base.filter(i => i.estado === 'reabierta');
  const escVenc = base.filter(i => i.estado === 'escalada_vencida');
  const sinCausa = abiertas.filter(i => !i.causa.confirmada);
  const gestion = abiertas.filter(i => i.causa.por_que === 'gestion_operaciones');

  if (!base.length) {
    const pAlertas = panelAlertasWeb(S, S.enParaTomas);
    if (pAlertas) zona.append(pAlertas);
    zona.append(vacio({ icono: 'ok', tono: 'celebrar', borde: true, titulo: 'No tienes incidencias abiertas',
      texto: ctx.ambito === 'ninguno' || ctx.ambito === 'tareas' ? 'Las incidencias son de clientes y de sistema. Tu puesto no lleva clientes, así que aquí solo verás las que te nombren a ti.' : 'Ninguno de tus clientes tiene una incidencia abierta hoy.', quien: 'Mili (Operaciones)' }));
    return;
  }

  // ---- 1 · cifras
  const t = [];
  if (todo) {
    t.push(tile({ icono: 'alert', etiqueta: 'Abiertas', valor: abiertas.length, unidad: `de ${base.length}`, estado: abiertas.length ? 'rojo' : 'verde',
      contexto: `${abiertas.filter(i => i.origen === 'desk').length} de Desk · ${abiertas.filter(i => i.origen === 'zadarma').length} de Zadarma · ${fmt.plural(abiertas.filter(i => i.origen === 'alarma').length, 'cliente crítico', 'clientes críticos')}`, medible: 'hoy', frescura: fres(D, 'desk'), ir: 'Ver la lista', alPulsar: () => elegirChip(zona, 'estado', '') }));
    t.push(tile({ icono: 'sube', etiqueta: 'Toca escalar o avisar', valor: toca.length, estado: toca.length ? 'rojo' : 'verde',
      contexto: 'Avisadas hace más de 48 h sin cambio, o sin avisar en 48 h', medible: 'hoy', ir: 'Ver cuáles', alPulsar: () => elegirChip(zona, 'estado', 'actuar') }));
    t.push(tile({ icono: 'clock', etiqueta: 'Escaladas vencidas', valor: escVenc.length, unidad: `de ${cuenta('escalada') + escVenc.length}`, estado: escVenc.length ? 'rojo' : 'verde',
      contexto: 'Tomás 48 h · Coti 24 h desde que se escala', medible: 'hoy', ir: 'Ver cuáles', alPulsar: () => elegirChip(zona, 'estado', 'escalada') }));
    t.push(tile({ icono: 'recargar', etiqueta: 'Reabiertas por el dato', valor: reab.length, unidad: `· ${cuenta('por_comprobar')} por comprobar`, estado: reab.length ? 'rojo' : 'verde',
      contexto: 'Marcadas como resueltas y el dato del día siguiente dice que siguen', medible: 'hoy', ir: 'Ver cuáles', alPulsar: () => elegirChip(zona, 'estado', 'reabierta') }));
    t.push(tile({ icono: 'eq', etiqueta: 'Gestión de Operaciones', valor: gestion.length, unidad: `de ${abiertas.length}`, estado: gestion.length ? 'ambar' : 'verde',
      contexto: 'Sin prueba de aviso escrito de Operaciones', medible: 'medias', medibleDetalle: 'Los avisos por WhatsApp o en persona no dejan prueba: regístralos con «Avisar»', ir: 'Ver cuáles', alPulsar: () => elegirChip(zona, 'causa', 'gestion_operaciones') }));
  } else {
    const delMio = abiertas.filter(i => i.responsable_id === ctx.persona.id);
    t.push(tile({ icono: 'alert', etiqueta: 'A mi nombre', valor: delMio.length, estado: delMio.length ? 'rojo' : 'verde', contexto: 'Incidencias en las que el responsable eres tú', medible: 'hoy', frescura: fres(D, 'desk') }));
    t.push(tile({ icono: 'cli', etiqueta: 'De mis clientes', valor: abiertas.length, estado: abiertas.length ? 'ambar' : 'verde', contexto: 'Incluye las de sistema que afectan a tus clientes', medible: 'hoy' }));
    t.push(tile({ icono: 'sube', etiqueta: 'Avisadas sin respuesta 48 h', valor: abiertas.filter(i => i.estado === 'toca_escalar').length, estado: abiertas.some(i => i.estado === 'toca_escalar') ? 'rojo' : 'verde', contexto: 'Si no contestas, Operaciones lo escala a Coti', medible: 'hoy' }));
  }
  // Guía 30 (3.6): lo que pide acción va primero; las cifras, debajo.

  // ---- 2 · lo primero hoy (máx. 7)
  // A1 (sin duplicados): lo que ya sale arriba en «Para Tomás» no se repite aquí
  const yaArriba = S.enParaTomas || new Set();
  const urgTodas = abiertas.filter(i => ['reabierta', 'escalada_vencida', 'toca_escalar', 'sin_avisar'].includes(i.estado));
  const urg = urgTodas.filter(i => !yaArriba.has(i.id))
    .sort((a, b) => ORDEN_ESTADO.indexOf(a.estado) - ORDEN_ESTADO.indexOf(b.estado) || (a.gravedad === 'rojo' ? -1 : 1) - (b.gravedad === 'rojo' ? -1 : 1) || (b.abiertoDias || 0) - (a.abiertoDias || 0))
    .slice(0, 7);
  const enParaTomas = urgTodas.length - urgTodas.filter(i => !yaArriba.has(i.id)).length;
  zona.append(panel({ titulo: 'Lo primero hoy', icono: 'zap', sub: `${todo ? 'Lo que vuelve arriba: avisado hace más de 2 días sin cambio, sin avisar, reabierto por el dato o escalado sin respuesta (máximo 7)' : 'Lo tuyo que pide respuesta'}${enParaTomas ? ` · ${enParaTomas} más ya están en «Para Tomás», arriba` : ''}` },
    listaLoPrimero(urg.map(i => ({
      estado: ESTADO[i.estado].c === 'rojo' ? 'rojo' : 'ambar', icono: ICONO_ORIGEN[i.origen] || 'alert',
      motivo: `${i.cliente || i.afectado || 'Centralita y Desk'} · ${ESTADO[i.estado].t}`,
      detalle: `${i.titulo}. ${sugerencia(i)}`,
      botones: [
        todo ? h('button', { type: 'button', class: 'bt mini', on: { click: () => copiar(mensajeListo(i, S), 'Mensaje copiado') } }, icono('copy'), 'Mensaje listo') : null,
        h('a', { class: 'bt mini pri', href: `#/incidencias/${i.id}`, 'aria-label': `Abrir la incidencia de ${i.cliente || i.afectado || 'la centralita'}` }, icono('derecha'), 'Abrir la incidencia'),
      ],
    })), { vacio: { titulo: 'Nada vuelve arriba hoy', porque: 'Todo lo avisado tiene menos de 2 días o ya está escalado con reloj.', celebrar: true } })));
  zona.append(tiles(t));
  // las alertas de web y SEO, sin las que apuntan a una incidencia que ya está arriba (Para Tomás o Lo primero hoy)
  const pAlertas = panelAlertasWeb(S, new Set([...yaArriba, ...urg.map(i => i.id)]));
  if (pAlertas) zona.append(pAlertas);

  // ---- 3 · la lista con chips (estado · origen · causa)
  const grupoEstado = i => ['toca_escalar', 'sin_avisar'].includes(i.estado) ? 'actuar' : ['escalada', 'escalada_vencida'].includes(i.estado) ? 'escalada' : i.estado === 'reabierta' ? 'reabierta' : ['detectada', 'avisada', 'reiterada'].includes(i.estado) ? 'en_curso' : 'cerrada';
  const cnt = (f) => base.filter(f).length;
  const chE = chipsFiltro({ etiqueta: 'Estado', clave: 'incidencias.estado', alCambiar: () => pintarTabla(), opciones: [
    { valor: '', texto: 'Abiertas', cuenta: abiertas.length },
    { valor: 'actuar', texto: 'Toca actuar', icono: 'sube', cuenta: cnt(i => grupoEstado(i) === 'actuar'), cuentaEstado: 'rojo' },
    { valor: 'escalada', texto: 'Escaladas', icono: 'crown', cuenta: cnt(i => grupoEstado(i) === 'escalada') },
    { valor: 'reabierta', texto: 'Reabiertas', icono: 'recargar', cuenta: cnt(i => grupoEstado(i) === 'reabierta'), cuentaEstado: 'rojo' },
    { valor: 'en_curso', texto: 'En curso', icono: 'clock', cuenta: cnt(i => grupoEstado(i) === 'en_curso') },
    { valor: 'cerrada', texto: 'Resueltas y no aplica', icono: 'check', cuenta: cnt(i => grupoEstado(i) === 'cerrada') },
  ] });
  chE.dataset.grupo = 'estado';
  const origenes = [...new Set(base.map(i => i.origen))];
  const chO = chipsFiltro({ etiqueta: 'Origen', clave: 'incidencias.origen', alCambiar: () => pintarTabla(), opciones: [
    { valor: '', texto: 'Todas' }, ...origenes.map(o => ({ valor: o, texto: TEXTO_ORIGEN[o] || o, icono: ICONO_ORIGEN[o], cuenta: abiertas.filter(i => i.origen === o).length })),
  ] });
  const chC = chipsFiltro({ etiqueta: 'Por qué', clave: 'incidencias.causa', alCambiar: () => pintarTabla(), opciones: [
    { valor: '', texto: 'Todas' }, ...Object.entries(POR_QUE).map(([k, v]) => ({ valor: k, texto: v, icono: ICONO_POR_QUE[k], cuenta: abiertas.filter(i => i.causa.por_que === k).length })),
  ] });
  chC.dataset.grupo = 'causa';
  const caja = h('div');
  const pintarTabla = () => {
    const e = chE.valor(), o = chO.valor(), c = chC.valor();
    const filas = base.filter(i => (e ? grupoEstado(i) === e : i.abierta) && (!o || i.origen === o) && (!c || i.causa.por_que === c))
      .sort((a, b) => ORDEN_ESTADO.indexOf(a.estado) - ORDEN_ESTADO.indexOf(b.estado) || (b.abiertoDias || 0) - (a.abiertoDias || 0));
    // Guía 30 (3.4) · rojo con cuentagotas: si más del 30 % de las filas son rojas, el rojo queda para el tercio más
    // grave (ya vienen ordenadas por gravedad y antigüedad) y el resto se pinta en ámbar. El texto del estado no cambia.
    const rojas = filas.filter(i => ESTADO[i.estado].c === 'rojo');
    const rojoFuerte = new Set(rojas.length > 0.3 * filas.length ? rojas.slice(0, Math.ceil(rojas.length / 3)).map(i => i.id) : rojas.map(i => i.id));
    const colorEst = i => (ESTADO[i.estado].c === 'rojo' && !rojoFuerte.has(i.id) ? 'ambar' : ESTADO[i.estado].c);
    caja.replaceChildren(tablaDensa({
      filas: filas.map(i => ({ ...i, _cli: i.cliente || i.afectado || 'Sistema', _resp: i.responsable, _est: ESTADO[i.estado].t, _causa: POR_QUE[i.causa.por_que] })),
      buscar: { campos: ['_cli', '_resp', 'titulo', 'texto'], placeholder: 'Buscar cliente, persona o texto' },
      filtros: [{ clave: '_resp', titulo: 'Responsable' }],
      columnas: [
        { clave: '_cli', titulo: 'Incidencia', principal: true, celda: i => h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap', alignItems: 'flex-start' } },
          i.c ? logoCliente(i.c) : h('span', { class: `ico-c s ${i.gravedad === 'rojo' ? 'rojo' : 'ambar'}` }, icono(ICONO_ORIGEN[i.origen] || 'alert')),
          h('span', { style: { minWidth: 0 } }, h('b', {}, i._cli), h('span', { class: 'sub', style: { display: 'block' } }, i.titulo))) },
        { clave: '_resp', titulo: 'Responsable', celda: i => h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(i._resp)), i._resp) },
        { clave: '_est', titulo: 'Estado', minAncho: '176px', valor: i => ORDEN_ESTADO.indexOf(i.estado), celda: i => h('span', { class: 'pila', style: { gap: 'var(--s-1)' } }, chipEstado(colorEst(i), ESTADO[i.estado].t), i.relojEsc ? h('span', { class: 'sub' }, i.relojEsc.texto) : null) },
        { clave: 'abiertoDias', titulo: 'Abierta', num: true, celda: i => i.abiertoDias === null ? '—' : `${fmt.num(i.abiertoDias)} d` },
        { clave: 'nav', titulo: 'Avisos', num: true, valor: i => i.avisos.length, celda: i => i.avisos.length ? `${i.avisos.length} · ${fmt.hace(diaISO(i.ultAviso.t))}` : h('span', { class: 'sub' }, 'ninguno') },
        { clave: '_causa', titulo: 'Por qué', celda: i => h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, icono(ICONO_POR_QUE[i.causa.por_que] || 'info', { clase: 's' }), i._causa, i.causa.confirmada ? null : h('span', { class: 'sub' }, '(propuesta)')) },
      ],
      alPulsar: i => ctx.navegar(`incidencias/${i.id}`),
      porPagina: 15,   // guía 30 (3.8): 15 visibles + «Ver más»
      etiquetaFila: i => `${i._cli}: ${i.titulo}, ${i._est}. Abrir la ficha`,
      vacio: { titulo: 'Nada con este filtro', porque: 'Cambia los chips de arriba para ver otras incidencias.', celebrar: e !== 'cerrada' },
    }));
  };
  pintarTabla();
  zona.append(panel({ titulo: 'Todas las incidencias', icono: 'alert', sub: 'Pulsa una fila para ver su ficha con la historia completa. Los filtros se quedan.' },
    h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-2)', paddingBottom: 'var(--s-1)' } }, chE, chO, chC), caja));

  zona.append(h('div', { class: 'fila' }, frescura(fres(D, 'desk')), frescura(fres(D, 'zadarma')), frescura(fres(D, 'zadarma_ext')), frescura(fres(D, 'panel')), frescura(fres(D, 'rastro'))));
  if (todo) zona.append(avisoParcial(`Lo que no se puede medir hoy: ${(D.no_medible || []).join(' · ')}`, { titulo: 'Fuera de las comprobaciones automáticas.' }));
}

function elegirChip(zona, grupo, valor) {
  const caja = grupo === 'estado' || grupo === 'causa' ? zona.querySelector(`.chips-f[data-grupo="${grupo}"]`) : null;
  if (!caja) return;
  const btn = [...caja.querySelectorAll('button')].find((b, i) => {
    const textos = { '': ['Abiertas', 'Todas'], actuar: ['Toca actuar'], escalada: ['Escaladas'], reabierta: ['Reabiertas'], gestion_operaciones: ['Gestión de Operaciones'] }[valor] || [];
    return textos.some(t => b.textContent.startsWith(t));
  });
  if (btn && btn.getAttribute('aria-pressed') !== 'true') btn.click();
  caja.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function sugerencia(i) {
  if (i.estado === 'reabierta') return 'Se marcó como resuelta y el dato de hoy dice que sigue: vuelve a avisar o escala.';
  if (i.estado === 'escalada_vencida') return `Escalada a ${i.relojEsc?.a?.includes('tomas') ? 'Tomás' : 'Coti'} y sin respuesta en plazo: recuérdalo hoy.`;
  if (i.estado === 'toca_escalar') return `Avisada ${fmt.hace(diaISO(i.ultAviso.t))} y sin cambio: escala a Coti con el plan y los números.`;
  if (i.estado === 'sin_avisar') return 'Nadie ha avisado por escrito todavía: avisa al responsable hoy (si no, cuenta como gestión de Operaciones).';
  if (i.estado === 'detectada') return 'Recién detectada: avisa al responsable.';
  if (['avisada', 'reiterada'].includes(i.estado)) return `Avisada ${fmt.hace(diaISO(i.ultAviso.t))}; si en 48 h no cambia, vuelve arriba.`;
  if (i.estado === 'escalada') return `Escalada: ${i.relojEsc.texto}.`;
  if (i.estado === 'por_comprobar') return 'Se comprueba mañana con el dato: si la detección sigue, se reabre sola.';
  return '';
}

function mensajeListo(i, S) {
  const r = i.responsable && i.responsable !== 'sin responsable' ? i.responsable.split(' ')[0] : null;
  const hola = r ? `Hola ${r}:` : 'Hola:';
  const n = i.numeros || {};
  const t0 = (i.tickets || [])[0];
  switch (i.regla) {
    case 'desk_48': return `${hola} ${i.cliente} tiene ${fmt.plural(n.correos, 'correo')} sin contestar; el más antiguo, ${t0?.numero} («${t0?.asunto}»), lleva ${n.dias_mas_antiguo} días. ¿Puedes contestar hoy y decirme cuándo está? Mañana lo compruebo con el dato de Desk.`;
    case 'desk_sin_agente': return `${hola} hay ${fmt.plural(n.tickets, 'ticket')} de ${i.cliente} sin agente en Desk (${t0?.numero}). ¿Lo asignas y lo contestas hoy? Mañana lo compruebo con el dato de Desk.`;
    case 'zadarma_perdida': return `Hola: tenemos una llamada perdida sin devolver (${i.texto.split(' sin contestar')[0].replace(/^\d+ llamada\(s\) entrante\(s\) /, '')}). ¿Quién la devuelve hoy? Avisadme cuando esté.`;
    case 'desk_agente_baja': return `${i.afectado} ya no está y sigue con ${fmt.plural(n.tickets, 'ticket')} de cliente a su nombre en Desk. Hay que reasignarlos hoy a su account: ${fmt.plural((i.clientes_afectados || []).length, 'cliente')}.`;
    default:
      if (i.origen === 'alarma') return `${hola} ${i.cliente} sigue crítico (${i.regla}). ${i.texto.split(';')[0]}. ¿Qué plan tienes y para cuándo? Lo reviso en 48 h; si sigue igual, lo escalo a Coti.`;
      return `${i.titulo}. ${i.texto} Hay que corregirlo; lo reviso mañana con el dato.`;
  }
}

// ================================================================== ficha de una incidencia
function pintarFicha(cont, S, id) {
  const { ctx, D, incs, nom } = S;
  const i = incs.find(x => x.id === id);
  const volver = h('a', { class: 'bt', href: '#/incidencias' }, icono('volver'), 'Volver a Incidencias');
  if (!i) {
    cont.append(vacio({ icono: 'candado', borde: true, titulo: 'Esta incidencia no está en tu lista', texto: 'O ya no existe en el dato de hoy, o es de un cliente o una persona que tu puesto no ve. Si la necesitas, pídesela a Mili.', quien: 'Mili (Operaciones)', accion: volver }));
    return;
  }
  const est = ESTADO[i.estado];
  ctx.titulo(i.cliente || i.afectado || 'Incidencia de sistema', `${i.titulo} · ${est.t}`);
  const puede = gestiona(ctx);
  const esResp = i.responsable_id === ctx.persona.id && !ctx.soloLectura;

  cont.append(h('nav', { class: 'migas', 'aria-label': 'Migas' }, h('a', { href: '#/incidencias' }, icono('alert', { clase: 's' }), 'Incidencias'), h('span', { 'aria-hidden': 'true' }, '›'), h('span', { 'aria-current': 'page' }, i.cliente || i.afectado || 'Sistema')));

  // ---- cabecera
  const etapa = i.estado === 'no_aplica' ? -1 : i.estado === 'reabierta' ? 2 : i.estado === 'toca_escalar' ? (i.avisos.length > 1 ? 2 : 1) : est.i;
  cont.append(h('section', { class: 'detalle-cab', style: { display: 'grid', gap: 'var(--s-4)' }, 'aria-label': 'Cabecera de la incidencia' },
    h('div', { class: 'fila', style: { gap: 'var(--s-4)', alignItems: 'center' } },
      i.c ? logoCliente(i.c, 'logo-cli xl') : h('span', { class: 'logo-cli xl', 'aria-hidden': 'true' }, icono(ICONO_ORIGEN[i.origen] || 'alert', { clase: 'l' })),
      h('div', { style: { minWidth: 0, flex: '1 1 280px' } },
        h('h2', {}, i.titulo),
        h('div', { class: 'meta-linea', style: { marginTop: 'var(--s-1)' } },
          i.cliente ? h('span', {}, icono('cli'), i.c?.detalle ? h('a', { href: `#/ficha/${i.cliente_id}`, style: { display: 'inline-flex', alignItems: 'center', minHeight: 'var(--s-8)', minWidth: 'var(--s-8)' } }, i.cliente) : i.cliente) : null,
          h('span', {}, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(i.responsable)), `Responsable: ${i.responsable}`),
          h('span', {}, icono('cal'), `Detectada el ${fh(i.det)}${i.abiertoDias !== null ? ` · hace ${i.abiertoDias} días` : ''}`),
          h('span', {}, icono(ICONO_ORIGEN[i.origen] || 'alert'), `Origen: ${TEXTO_ORIGEN[i.origen] || i.origen}`)),
        h('div', { class: 'fila', style: { marginTop: 'var(--s-3)' } },
          chipEstado(est.c, est.t), i.relojEsc ? chipEstado(i.relojEsc.estado, `Reloj: ${i.relojEsc.texto}`) : null,
          chipEstado(i.gravedad === 'rojo' ? 'rojo' : 'ambar', i.gravedad === 'rojo' ? 'Crítico' : 'Vigilar'),
          i.queja ? chipEstado('rojo', 'Hay una queja') : null)),
      h('div', { class: 'fila' }, i.prueba ? h('a', { class: 'bt', href: i.prueba, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir la prueba') : null,
        puede ? h('button', { type: 'button', class: 'bt', on: { click: () => copiar(mensajeListo(i, S), 'Mensaje copiado') } }, icono('copy'), 'Mensaje listo') : null)),
    etapa >= 0 ? barraEtapas(ETAPAS, etapa) : null));

  // ---- la respuesta en 10 segundos (pregunta de Mili)
  const ops = i.avisos;
  const opsTxt = ops.length
    ? `${fmt.plural(ops.length, 'aviso escrito', 'avisos escritos')} de Operaciones: ${ops.slice(-4).map(e => `${fh(e.t)} (${nom(e.quien)}${e.a ? ` → ${String(e.a).split(',').map(nom).join(' y ')}` : ''})`).join(' · ')}.`
    : 'Ningún aviso escrito de Operaciones todavía.';
  const resp = i.evs.filter(e => e.paso === 'respuesta');
  const filas10 = [
    ['alert', '¿Qué se incumple?', i.texto, i.umbral ? `Regla: ${sinCodigos(i.umbral)}` : null],
    ['persona', '¿Quién es responsable?', i.responsable, i.afectado ? `Afecta a: ${i.afectado}` : i.c ? `Lleva el cliente: ${i.c.responsable || '—'}` : null],
    [ICONO_POR_QUE[i.causa.por_que] || 'info', '¿Por qué?', `${POR_QUE[i.causa.por_que]} · se rompe en ${DONDE[i.causa.donde] || '—'}`,
      i.causa.confirmada ? `Confirmada por ${nom(i.causa.quien)} el ${fh(i.causa.t)}${i.causa.cambiada ? ' (cambiada por Tomás)' : ''}${i.causa.explicacion ? `: ${i.causa.explicacion}` : ''}` : `Propuesta: ${i.causa.motivo || ''} Falta que la confirme quien escala.`],
    ['eq', '¿Qué hizo Operaciones?', opsTxt, resp.length ? `Respuesta: ${resp[resp.length - 1].texto} (${nom(resp[resp.length - 1].quien)}, ${fh(resp[resp.length - 1].t)})` : 'Sin respuesta escrita del responsable.'],
    [i.abierta ? 'sube' : 'ok', '¿Resuelto o hay que escalar?', est.t, sugerencia(i)],
  ];
  cont.append(panel({ titulo: 'La respuesta en 10 segundos', icono: 'zap', sub: 'Qué se incumple, quién, por qué, qué hizo Operaciones y si está resuelto' },
    h('div', {}, filas10.map(([ic, p, v, s], n) => h('div', { style: { display: 'grid', gridTemplateColumns: '28px minmax(0, 1fr)', gap: 'var(--s-1) var(--s-3)', padding: 'var(--s-3) var(--relleno)', borderTop: n ? 'var(--borde-suave)' : '0', alignItems: 'start' } },
      h('span', { class: 'ico-c s' }, icono(ic)), h('span', { style: { display: 'grid', gap: 'var(--s-1)', minWidth: '0' } }, h('span', { class: 'titulo-seccion' }, p), h('b', { style: { maxWidth: '72ch' } }, conTickets(sinCodigos(String(v ?? '')))), s ? h('span', { class: 'sub', style: { maxWidth: '72ch' } }, conTickets(sinCodigos(String(s)))) : null))))));

  // ---- acciones (Operaciones) o respuesta (responsable)
  if (puede) cont.append(panelAcciones(i, S));
  else if (esResp && i.abierta) cont.append(panelRespuesta(i, S));
  else if (ctx.soloLectura) cont.append(avisoParcial('Estás en «ver como»: es solo lectura. Los botones del ciclo están apagados.', { tipo: 'info' }));

  // ---- pruebas y números · historia
  const tickets = (i.tickets || []).map(t => h('li', {},
    h('span', { class: `ico-c s ${t.horas > 48 ? 'rojo' : 'ambar'}` }, icono('mail')),
    h('span', { class: 't' }, h('a', { href: t.url, target: '_blank', rel: 'noopener' }, `${t.numero} · ${t.asunto || 'sin asunto'}`), h('span', { class: 'sub', style: { display: 'block' } }, `${t.agente || 'sin agente'} · desde ${fh(fechaLocal(t.desde))}`)),
    h('span', { class: 'x' }, `${Math.round(t.horas / 24)} d`)));
  const num = Object.entries(i.numeros || {}).filter(([, v]) => v !== null && v !== undefined && !(Array.isArray(v) && !v.length));
  cont.append(h('div', { class: 'dos' },
    panel({ titulo: 'Historia', icono: 'hist', sub: 'Nada se borra: cada paso con su fecha, quién y la prueba' }, h('div', { class: 'cuerpo' }, historia(i, S))),
    h('div', { class: 'pila' },
      panel({ titulo: 'Pruebas y números', icono: 'res' },
        num.length ? h('ul', { class: 'lista-i cuerpo', style: { paddingTop: 'var(--s-1)', paddingBottom: 'var(--s-1)' } }, num.map(([k, v]) => h('li', {}, h('span', { class: 'ico-c s gris' }, icono('info')), h('span', { class: 't' }, k.replace(/_/g, ' ')), h('span', { class: 'x' }, Array.isArray(v) ? v.join(', ') : String(v))))) : null,
        tickets.length ? h('ul', { class: 'lista-i cuerpo', style: { paddingTop: '0' } }, tickets) : null,
        !num.length && !tickets.length ? vacio({ icono: 'res', titulo: 'Sin números para esta incidencia', texto: 'La prueba es el enlace de la cabecera.' }) : null),
      h('div', { class: 'fila', style: { minWidth: '0' } }, frescoPartible(frescura(fres(D, i.origen === 'zadarma' ? 'zadarma' : i.origen === 'alarma' ? 'panel' : 'desk'))), frescoPartible(frescura(fres(D, 'rastro')))))));
}

/** Barrido v1: .fresco no parte línea (nowrap); en la columna estrecha de .dos a 1024 px desbordaba la página. */
function frescoPartible(f) { if (f?.style) { f.style.whiteSpace = 'normal'; f.style.minWidth = '0'; } return f; }

function historia(i, S) {
  const { nom } = S;
  const ev = [{ paso: 'detectada', t: i.det, texto: `Detectada por la regla: ${i.titulo}`, quien: null, por: TEXTO_ORIGEN[i.origen] }, ...i.evs.filter(e => e.paso !== 'detectada' || e.quien)];
  ev.sort((a, b) => (+a.t || 0) - (+b.t || 0));
  const PASO = { detectada: ['Detectada', 'ambar'], avisada: ['Avisada', 'ambar'], reiterada: ['Reiterada', 'ambar'], escalada: ['Escalada', 'rojo'], accion: ['Operaciones actúa', ''], respuesta: ['Respuesta', 'verde'], decision: ['Decisión', 'verde'], resuelta: ['Resuelta', 'verde'], no_aplica: ['No aplica', ''], causa: ['Causa', ''], visto: ['Vista', ''], reabierta: ['Reabierta', 'rojo'] };
  return h('ol', { class: 'tiempo' }, ev.map(e => {
    const [t, c] = PASO[e.paso] || [e.paso, ''];
    const extra = e.paso === 'causa' && e.v ? ` ${POR_QUE[e.v.por_que] || ''} · ${DONDE[e.v.donde] || ''}${e.v.explicacion ? ` — ${e.v.explicacion}` : ''}` : '';
    return h('li', { class: c },
      h('div', { class: 'f' }, fh(e.t)),
      h('div', { class: 't' }, `${t}${e.quien ? ` · ${nom(e.quien)}` : ''}${e.a ? ` → ${String(e.a).split(',').map(nom).join(' y ')}` : ''}`),
      h('div', { class: 'd' }, conTickets(sinCodigos((e.texto || '') + extra))),
      (e.enlace || e.por || e.origen === 'app' || e.origen === 'rastro') ? h('div', { class: 'd fila', style: { gap: 'var(--s-2)' } },
        e.enlace ? h('a', { class: 'bt mini', href: e.enlace, target: '_blank', rel: 'noopener' }, icono('ext', { clase: 's' }), 'Ver prueba') : null,
        h('span', { class: 'q' }, [e.por, e.origen === 'app' ? 'en la app' : e.origen === 'rastro' ? 'rastro' : ''].filter(Boolean).join(' · '))) : null);
  }));
}

// ------------------------------------------------------------------ panel de acciones (Operaciones)
function panelAcciones(i, S) {
  const { ctx, nom } = S;
  const zonaForm = h('div');
  const abrir = tipo => { zonaForm.replaceChildren(formulario(tipo, i, S, () => zonaForm.replaceChildren())); zonaForm.querySelector('textarea, input, select')?.focus(); };
  const bt = (tipo, ic, txt, pri) => h('button', { type: 'button', class: `bt${pri ? ' pri' : ''}`, on: { click: () => abrir(tipo) } }, icono(ic), txt);
  const yaVisto = i.vistos.some(v => v.quien === ctx.persona.id);
  const ab = i.abierta;
  const causaBloqueada = i.causa.confirmada && !ctx.persona.puestos.includes('direccion');
  const botones = [
    !yaVisto ? h('button', { type: 'button', class: 'bt', on: { click: async () => { await guardar(S, i, 'visto', 'La he visto', {}); } } }, icono('ojo'), 'La he visto') : chipEstado('verde', `Vista por ti · ${fh(i.vistos.find(v => v.quien === ctx.persona.id).t)}`),
    ab ? bt('avisar', 'send', i.avisos.length ? 'Reiterar' : 'Avisar al responsable', !i.avisos.length) : null,
    ab ? bt('escalar_coti', 'sube', 'Escalar a Coti · 24 h', i.estado === 'toca_escalar') : null,
    ab ? bt('escalar_tomas', 'crown', 'Escalar a Tomás · 48 h') : null,
    ab && i.relojEsc && ctx.persona.puestos.some(p => ['direccion', 'proyectos'].includes(p)) ? bt('decidir', 'check', 'Decidir lo escalado', true) : null,
    ab ? bt('resolver', 'check', 'Resuelta (con prueba)') : null,
    !ab && i.estado !== 'comprobada' ? bt('reabrir', 'recargar', 'Reabrir') : null,
    !causaBloqueada ? bt('causa', 'flag', i.causa.confirmada ? 'Cambiar la causa' : 'Confirmar la causa') : h('span', { class: 'sub' }, 'Causa confirmada: solo Tomás la cambia'),
    ab ? bt('no_aplica', 'cerrar', 'No aplica') : null,
  ];
  return panel({ titulo: 'Qué hago ahora', icono: 'zap', sub: 'Cada botón queda en el rastro con la hora del servidor. Nada se envía: el mensaje se copia y lo mandas tú.' },
    h('div', { class: 'fila', style: ACC }, botones), zonaForm);
}

function panelRespuesta(i, S) {
  const zonaForm = h('div');
  return panel({ titulo: 'Tu respuesta', icono: 'send', sub: 'Cuenta a Operaciones qué has hecho y deja la prueba (enlace al correo, la tarea o la llamada). Mañana se comprueba con el dato.' },
    h('div', { class: 'fila', style: ACC }, h('button', { type: 'button', class: 'bt pri', on: { click: () => { zonaForm.replaceChildren(formulario('respuesta', i, S, () => zonaForm.replaceChildren())); zonaForm.querySelector('textarea')?.focus(); } } }, icono('check'), 'Ya lo he hecho')), zonaForm);
}

async function guardar(S, i, tipo, texto, v) {
  const { ctx } = S;
  await ctx.accion({ herramienta: 'app', tipo, objeto: i.id, cliente_id: i.cliente_id || null, texto, vista_previa: { incidencia: i.id, titulo: i.titulo, ...v } });
  ctx.rastro({ accion: `incidencia_${tipo}`, objeto: i.id, detalle: texto });
  avisoFlotante('Guardado en el rastro');
  await S.rehacer();
}

function formulario(tipo, i, S, cerrar) {
  const { ctx, nom } = S;
  const campo = campoL;
  const sel = (opts, valor) => { const s = h('select', {}, opts.map(([v, t]) => h('option', { value: v }, t))); if (valor) s.value = valor; return s; };
  const err = h('span', { style: ERR, role: 'alert' });
  const quienes = [...new Set([i.responsable_id, 'mili', 'constanza', 'tomas'].filter(Boolean))].map(p => [p, nom(p)]);
  let cuerpo = [], hacer, titulo, boton = 'Guardar en el rastro';
  if (tipo === 'avisar') {
    titulo = i.avisos.length ? 'Reiterar el aviso' : 'Avisar al responsable';
    const a = sel(quienes, i.responsable_id); const por = sel(CANALES.map(c => [c, c]));
    const txt = h('textarea', {}); txt.value = mensajeListo(i, S);
    const prueba = h('input', { type: 'url', placeholder: 'Enlace al mensaje (ClickUp, Desk…). Opcional, pero es la prueba' });
    cuerpo = [h('div', { style: DOS_C }, campo('A quién', a), campo('Por dónde', por)), campo('Mensaje (cópialo y mándalo tú)', txt), campo('Prueba del aviso', prueba),
      h('div', { class: 'fila' }, h('button', { type: 'button', class: 'bt mini', on: { click: () => copiar(txt.value, 'Mensaje copiado') } }, icono('copy'), 'Copiar el mensaje'))];
    hacer = () => guardar(S, i, i.avisos.length ? 'reiterar' : 'avisar', `${i.avisos.length ? 'Reitera' : 'Avisa'} a ${nom(a.value)} por ${por.value}`, { a: a.value, por: por.value, mensaje: txt.value, prueba: prueba.value || null });
  } else if (tipo === 'escalar_coti' || tipo === 'escalar_tomas') {
    const aTomas = tipo === 'escalar_tomas';
    titulo = aTomas ? 'Escalar a Tomás: crea una decisión con reloj de 48 h' : 'Escalar a Coti: reloj de 24 h';
    const prob = h('textarea', {}); prob.value = `${i.cliente || i.afectado || 'Sistema'}: ${i.texto}${i.avisos.length ? ` Avisado ${fmt.plural(i.avisos.length, 'vez')}; la última, ${fh(i.ultAviso.t)}.` : ''}`;
    const rec = h('textarea', {}); rec.value = recomendacion(i);
    const donde = sel(Object.entries(DONDE), i.causa.donde); const pq = sel(Object.entries(POR_QUE), i.causa.por_que);
    cuerpo = [campo('Problema', prob), campo('Recomendación', rec), h('p', { class: 'sub' }, 'La causa la marca quien escala. Tomás la puede cambiar.'), h('div', { style: DOS_C }, campo('Dónde se rompe', donde), campo('Por qué', pq))];
    boton = aTomas ? 'Escalar a Tomás' : 'Escalar a Coti';
    hacer = async () => {
      if (!rec.value.trim()) throw new Error('Pon una recomendación: Tomás decide sobre una propuesta.');
      await ctx.accion({ herramienta: 'app', tipo: 'causa', objeto: i.id, cliente_id: i.cliente_id || null, texto: `Causa al escalar: ${POR_QUE[pq.value]} · ${DONDE[donde.value]}`, vista_previa: { donde: donde.value, por_que: pq.value, explicacion: 'Marcada al escalar' } });
      await guardar(S, i, 'escalar', `Escala a ${aTomas ? 'Tomás (48 h)' : 'Coti (24 h)'}`, { a: aTomas ? 'tomas' : 'constanza', reloj_h: aTomas ? 48 : 24, problema: prob.value, recomendacion: rec.value, decision_para_tomas: aTomas });
    };
  } else if (tipo === 'decidir') {
    titulo = 'Decidir lo escalado';
    const txt = h('textarea', { placeholder: 'Qué se hace, quién y para cuándo' });
    cuerpo = [h('p', { class: 'sub' }, `Recomendación de Operaciones: ${ultimaEsc(i).v?.recomendacion || '—'}`), campo('Decisión', txt)];
    hacer = () => { if (!txt.value.trim()) throw new Error('Escribe la decisión.'); return guardar(S, i, 'decidir', `Decide: ${txt.value.trim()}`, { decision: txt.value.trim() }); };
  } else if (tipo === 'resolver') {
    titulo = 'Marcar como resuelta (con prueba)';
    const prueba = h('input', { type: 'url', placeholder: 'Enlace al ticket contestado, la tarea cerrada, la llamada…' });
    const txt = h('textarea', { placeholder: 'Qué se hizo' });
    cuerpo = [campo('Prueba (obligatoria)', prueba), campo('Qué se hizo', txt), h('p', { class: 'sub' }, 'Mañana se contrasta con el dato: si la detección sigue, la incidencia se reabre sola.')];
    hacer = () => { if (!prueba.value.trim() && !txt.value.trim()) throw new Error('Sin prueba no se resuelve: pon el enlace o di qué se hizo y dónde se ve.'); return guardar(S, i, 'resolver', `Resuelta: ${txt.value.trim() || 'ver prueba'}`, { prueba: prueba.value.trim() || null, que: txt.value.trim() }); };
  } else if (tipo === 'causa') {
    titulo = i.causa.confirmada ? 'Cambiar la causa (queda registrado)' : 'Confirmar la causa';
    const donde = sel(Object.entries(DONDE), i.causa.donde); const pq = sel(Object.entries(POR_QUE), i.causa.por_que);
    const exp = h('textarea', { placeholder: 'Por qué: una frase' }); exp.value = i.causa.explicacion || '';
    cuerpo = [h('div', { style: DOS_C }, campo('Dónde se rompe', donde), campo('Por qué', pq)), campo('Explicación', exp),
      i.avisos.length ? null : h('p', { class: 'sub' }, 'No hay prueba de aviso de Operaciones: por la regla de los avisos por escrito, si era de una persona, cuenta como «gestión de Operaciones».')];
    hacer = () => guardar(S, i, 'causa', `Causa: ${POR_QUE[pq.value]} · ${DONDE[donde.value]}`, { donde: donde.value, por_que: pq.value, explicacion: exp.value.trim() });
  } else if (tipo === 'no_aplica') {
    titulo = 'No aplica (motivo obligatorio)';
    const mot = h('textarea', { placeholder: 'Por qué no aplica' });
    cuerpo = [campo('Motivo', mot)];
    hacer = async () => {
      if (!mot.value.trim()) throw new Error('«No aplica» necesita un motivo.');
      await ctx.api('rastro', { metodo: 'POST', cuerpo: { modulo: ID, accion: 'no_aplica', objeto: i.id, motivo: mot.value.trim() } }).catch(() => null);
      await guardar(S, i, 'no_aplica', `No aplica: ${mot.value.trim()}`, { motivo: mot.value.trim() });
    };
  } else if (tipo === 'reabrir') {
    titulo = 'Reabrir';
    const mot = h('textarea', { placeholder: 'Por qué se reabre' });
    cuerpo = [campo('Motivo', mot)];
    hacer = () => { if (!mot.value.trim()) throw new Error('Di por qué se reabre.'); return guardar(S, i, 'reabrir', `Reabierta: ${mot.value.trim()}`, { motivo: mot.value.trim() }); };
  } else if (tipo === 'respuesta') {
    titulo = 'Ya lo he hecho';
    const prueba = h('input', { type: 'url', placeholder: 'Enlace a la prueba' }); const txt = h('textarea', { placeholder: 'Qué has hecho' });
    cuerpo = [campo('Qué has hecho', txt), campo('Prueba', prueba)];
    hacer = () => { if (!txt.value.trim()) throw new Error('Cuéntalo en una frase.'); return guardar(S, i, 'respuesta', txt.value.trim(), { prueba: prueba.value.trim() || null, a: 'mili' }); };
  }
  const enviar = h('button', { type: 'submit', class: 'bt pri' }, icono('check'), boton);
  const form = h('form', { style: FORM, 'aria-label': titulo, on: { submit: async e => {
    e.preventDefault(); err.textContent = ''; enviar.disabled = true;
    try { await hacer(); } catch (x) { err.textContent = x?.message || String(x); enviar.disabled = false; }
  } } },
  h('b', {}, titulo), cuerpo, err,
  h('div', { class: 'fila' }, enviar, h('button', { type: 'button', class: 'bt', on: { click: cerrar } }, 'Cancelar')));
  form.addEventListener('keydown', e => { if (e.key === 'Escape') { e.stopPropagation(); cerrar(); } });
  return form;
}

function recomendacion(i) {
  if (i.regla === 'desk_agente_baja') return `Reasignar hoy los ${i.numeros?.tickets} tickets a su account y desactivar del todo el agente.`;
  if (i.regla === 'desk_departamentos') return 'Que Tomás haga miembro de esos departamentos al agente de la llave de lectura (5 minutos en Desk).';
  if (i.origen === 'zadarma') return 'Revisar la regla de la centralita hoy y dejar buzón fuera de horario.';
  if (i.causa.por_que === 'ejecucion') return `Reunión de 15 minutos con ${i.responsable} y Coti; plan escrito con fecha. Si en 48 h no cambia, cambio de account.`;
  return 'Corregir la configuración y comprobarlo mañana con el dato.';
}

// ================================================================== Quién falla en qué (mapas)
function pintarMapa(zona, S) {
  const { ctx, D } = S;
  const reglas = D.reglas_calor || [];
  const filas = (D.mapa_calor || []).slice().sort((a, b) => (b.alarmas_rojas || 0) - (a.alarmas_rojas || 0));
  let sel = { p: null, k: null };
  const lista = h('div');
  const clsCelda = (v, r) => v === null || v === undefined ? 'na' : !v ? '' : v >= (r.rojo_desde || 3) * 2 ? 'rr' : v >= (r.rojo_desde || 3) ? 'r' : 'a';
  const pintarAlarmas = () => {
    if (!sel.k) { lista.replaceChildren(h('p', { class: 'sub', style: PAD }, icono('info', { clase: 's' }), ' Pulsa una casilla y aquí salen las alarmas de ese account y esa regla.')); return; }
    const r = reglas.find(x => x.k === sel.k); const f = filas.find(x => x.nombre_completo === sel.p);
    const al = (ctx.datos.alarmas || []).filter(a => a.ambito === 'cliente' && r.tipos.includes(a.tipo) && (f.persona_ref ? a.responsable_id === f.persona_ref : !a.responsable_id));
    lista.replaceChildren(panel({ titulo: `${f.nombre} · ${r.t} ${r.s}`, icono: 'filtro', sub: fmt.plural(al.length, 'alarma'), acciones: h('button', { type: 'button', class: 'bt mini', on: { click: () => { sel = { p: null, k: null }; pintarRejilla(); pintarAlarmas(); } } }, icono('cerrar'), 'Quitar el filtro') },
      listaLoPrimero(al.map(a => ({ estado: a.gravedad === 'rojo' ? 'rojo' : 'ambar', icono: 'alert', motivo: `${a.cliente} · ${a.tipo}`, detalle: a.texto || 'El detalle lo ve quien lleva el cliente.',
        botones: [a.enlace ? h('a', { class: 'bt mini', href: a.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Prueba') : null,
          S.incs.find(i => i.cliente_id === a.cliente_id) ? h('a', { class: 'bt mini', href: `#/incidencias/${S.incs.find(i => i.cliente_id === a.cliente_id).id}` }, icono('alert'), 'Incidencia') : null] })),
      { vacio: { titulo: 'Sin alarmas con detalle para tu puesto', porque: 'O está a cero, o son clientes que no ves.', celebrar: true } })));
  };
  const COLS_CALOR = `minmax(150px, 1.4fr) 64px repeat(${reglas.length}, minmax(56px, 1fr))`;
  const filaCalor = { display: 'grid', gridTemplateColumns: COLS_CALOR, gap: 'var(--s-1)', alignItems: 'stretch', minWidth: `${280 + reglas.length * 64}px` };
  const rejilla = h('div', { role: 'table', 'aria-label': 'Accounts por regla', style: { display: 'grid', gap: 'var(--s-1)', padding: 'var(--s-3) var(--s-4)' } });
  const pintarRejilla = () => {
    rejilla.replaceChildren(
      h('div', { role: 'row', style: filaCalor }, h('span', { class: 'sub', role: 'columnheader', style: { ...CAB, textAlign: 'left' } }, 'Account'), h('span', { class: 'sub', role: 'columnheader', style: CAB }, 'Proyectos', h('small', { style: META }, 'tope 12')),
        reglas.map(r => h('span', { class: 'sub', role: 'columnheader', style: CAB }, r.t, h('small', { style: META }, r.s)))),
      ...filas.map(f => h('div', { role: 'row', style: filaCalor },
        h('span', { role: 'rowheader', style: NOM }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(f.nombre)), h('span', {}, f.nombre, h('small', { class: 'sub', style: META }, `${fmt.num(f.alarmas_rojas)} alarmas en rojo`))),
        h('span', { role: 'cell', style: celdaEst('carga'), title: `${f.proyectos} proyectos frente al tope de 12` }, f.proyectos ?? '—'),
        reglas.map(r => { const v = f.valores?.[r.k]; return h('button', { type: 'button', role: 'cell', style: celdaEst(clsCelda(v, r), sel.p === f.nombre_completo && sel.k === r.k), 'aria-pressed': String(sel.p === f.nombre_completo && sel.k === r.k),
          'aria-label': `${f.nombre}, ${r.t} ${r.s}: ${v ?? 'sin dato'}`, disabled: v === null || v === undefined || null,
          on: { click: () => { sel = { p: f.nombre_completo, k: r.k }; pintarRejilla(); pintarAlarmas(); lista.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } } }, v ?? '—'); }))));
  };
  pintarRejilla(); pintarAlarmas();
  if (!filas.length) {
    zona.append(vacio({ icono: 'grafico', borde: true, titulo: 'No hay ningún account que puedas ver aquí', texto: 'El mapa enseña a cada account su propia fila; Operaciones, sus jefes, RRHH y dirección ven todas.', quien: 'Mili (Operaciones)' }));
  } else {
    const cuadro = bg => h('i', { style: { display: 'inline-block', width: '12px', height: '12px', borderRadius: 'var(--r-s)', verticalAlign: '-2px', marginRight: 'var(--s-1)', background: bg } });
    zona.append(panel({ titulo: 'Quién falla en qué', icono: 'grafico', sub: 'Clientes por account que incumplen cada regla (panel de Operaciones). Pulsa una casilla para ver cuáles.' }, h('div', { class: 'tabla-scroll' }, rejilla),
      h('div', { class: 'fila sub', style: { gap: 'var(--s-3)', ...PAD } }, h('span', {}, cuadro('var(--good-soft)'), 'a cero'), h('span', {}, cuadro('var(--warn-soft)'), '1 o 2'), h('span', {}, cuadro('var(--bad-soft)'), '3 a 5'), h('span', {}, cuadro('var(--bad-ink)'), '6 o más'), h('span', {}, 'Revisión cuenta tareas: rojo desde 6, fuerte desde 12.')),
      lista));
  }

  // ---- mapa de control por persona
  const C = (D.control || []).slice();
  // R13: contesta, revisa y se reúne salen de las definiciones únicas (Bandeja, Producción, Reuniones), con el mismo
  // semáforo que «Tu cumplimiento» de Mi día. Imputa es solo aviso (regla de Tomás): ámbar como mucho y no ordena el mapa.
  const score = x => (x.revisa?.mas48 > 5 ? 2 : 0) + (x.llama?.sem === 0 ? 2 : 0) + (x.contesta?.mas48 ? 3 : 0) + (x.reune?.sin_reunion || 0) + (x.abandonados || []).length * 2;
  const mesReu = D.control_regla?.mes_pasado ? ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'][Number(D.control_regla.mes_pasado.slice(5)) - 1] : 'mes pasado';
  C.sort((a, b) => score(b) - score(a));
  const cel = (cls, v, sub, l, ir) => h(ir ? 'a' : 'span', { role: 'cell', href: ir || null, title: l, style: celdaEst(cls) }, v, sub ? h('small', { style: { ...META, fontWeight: '500' } }, sub) : null);
  const filaCtl = { display: 'grid', gridTemplateColumns: 'minmax(150px, 1.4fr) repeat(8, minmax(64px, 1fr))', gap: 'var(--s-1)', alignItems: 'stretch', minWidth: '760px' };
  const COLS = [['Imputa', 'h 7 días / 40'], ['Revisa', 'tareas +48 h'], ['Llama', 'salientes 7 días'], ['Contesta', 'correos +48 h'], ['Se reúne', `sin reunión ${mesReu}`], ['Contacto', 'sin correo semana'], ['Abandonados', 'sin horas ni correo 14 d'], ['Planifica', 'rompe el semanal']];
  if (C.length) {
    zona.append(panel({ titulo: 'Mapa de control por persona', icono: 'eq', sub: 'Quién no revisa, no llama, no contesta, no se reúne o tiene proyectos abandonados. Contesta, Revisa y Se reúne: las mismas cifras que Bandeja, Producción, Reuniones y Mi día. Rojo: habla hoy con esa persona.' },
      h('div', { class: 'tabla-scroll' }, h('div', { role: 'table', 'aria-label': 'Control por persona', style: { display: 'grid', gap: 'var(--s-1)', padding: 'var(--s-3) var(--s-4)' } },
        h('div', { role: 'row', style: filaCtl }, h('span', { class: 'sub', style: { ...CAB, textAlign: 'left' } }, 'Persona'), COLS.map(([t, s]) => h('span', { class: 'sub', role: 'columnheader', style: CAB }, t, h('small', { style: META }, s)))),
        C.map(x => h('div', { role: 'row', style: filaCtl },
          h('span', { role: 'rowheader', style: NOM }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(x.nombre)), h('span', {}, x.nombre, h('small', { class: 'sub', style: META }, `${x.clientes} clientes`))),
          cel(x.imputa?.pct_sem < 90 ? 'a' : '', `${fmt.num(x.imputa?.semana || 0)} h`, `${x.imputa?.pct_sem ?? '—'} %`, 'Imputa', '#/horas'),
          cel(x.revisa?.mas48 > 5 ? 'r' : x.revisa?.mas48 ? 'a' : '', x.revisa?.mas48 ?? '—', `de ${x.revisa?.total ?? '—'}`, 'Revisa', '#/produccion'),
          cel(x.llama?.sem === 0 ? 'r' : x.llama?.sem < 3 ? 'a' : '', x.llama?.sem ?? '—', `${x.llama?.sem_ok ?? 0} de +30 s`, 'Llama', null),
          cel(x.contesta?.mas48 ? 'r' : '', x.contesta?.mas48 ?? '—', `de ${x.contesta?.correos ?? 0}`, 'Contesta', '#/bandeja'),
          cel(x.reune?.sin_reunion ? 'r' : '', x.reune?.sin_reunion ?? '—', x.reune?.clientes !== undefined ? `de ${x.reune.clientes}` : null, 'Se reúne', '#/reuniones'),
          cel(x.reune?.sin_correo_sem > 2 ? 'r' : x.reune?.sin_correo_sem ? 'a' : '', x.reune?.sin_correo_sem ?? '—', null, 'Contacto', '#/en-rojo'),
          cel(x.abandonados?.length ? 'r' : '', x.abandonados?.length ?? 0, (x.abandonados || []).slice(0, 2).join(', ') || null, 'Abandonados', '#/en-rojo'),
          cel(x.planifica === null || x.planifica === undefined ? 'na' : x.planifica >= 3 ? 'r' : x.planifica ? 'a' : '', x.planifica ?? '—', x.planifica === null || x.planifica === undefined ? null : 'tareas', 'Planifica', '#/produccion')))))),
      h('div', { class: 'fila' }, frescura(fres(D, 'panel'))));
  } else if (filas.length) {
    zona.append(vacio({ icono: 'eq', titulo: 'El mapa de control por persona es de Operaciones', texto: 'Cada persona ve su fila en «Mi día»; el mapa completo lo ven Mili, los jefes, RRHH y dirección.' }));
  }
  zona.append(avisoParcial('«Quién falla en qué», Imputa, Llama, Contacto, Abandonados y Planifica salen del panel de Operaciones de Mili; Contesta, Revisa y Se reúne, de Bandeja, Producción y Reuniones. Las horas imputadas son solo aviso (regla de Tomás): nunca rojo.', { titulo: 'Dato a medias.' }));
}

// ================================================================== Incongruencias y accesos
function pintarIncongruencias(zona, S) {
  const { ctx, D, porObjeto, nom } = S;
  const puede = gestiona(ctx);
  const inc = D.incongruencias || [];
  const acc = D.accesos || [];
  const decidida = id => { const l = porObjeto.get(id) || []; const d = [...l].reverse().find(a => ['decidir_incongruencia', 'no_aplica', 'quitar_acceso'].includes(a.tipo)); return d ? { ...vp(d), quien: d.quien, t: fechaServ(d.creada), tipo: d.tipo } : null; };
  const ICO_H = { clickup: 'check', desk: 'mail', crm: 'base', sign: 'doc', app: 'aj', airtable: 'euro', holded: 'euro', hojas: 'doc', windsor: 'plug' };
  const TXT_H = { clickup: 'ClickUp', desk: 'Desk', crm: 'CRM', sign: 'Sign', app: 'App', airtable: 'Airtable', holded: 'Holded', hojas: 'Hojas', windsor: 'Windsor' };

  // ---- accesos de quien ya no está (lo de seguridad, arriba)
  const pend = acc.filter(a => !a.ok);
  const ok = acc.filter(a => a.ok);
  zona.append(panel({ titulo: 'Accesos de quien ya no está', icono: 'escudo', sub: 'Personas de baja o que no están en el equipo y siguen con algo abierto en Desk, CRM, ClickUp o Zadarma (leído en vivo hoy).' },
    pend.length ? listaLoPrimero(pend.map(a => {
      const d = decidida(a.id);
      return { estado: d ? 'hecho' : a.estado_herramienta === 'activo' ? 'rojo' : 'ambar', icono: 'key',
        motivo: `${a.persona} · ${a.herramienta} (${a.estado_herramienta})`, detalle: `${a.que_hacer}${a.estado_app ? ` En la app: ${a.estado_app}.` : ''}${d ? ` — Pedido por ${nom(d.quien)} el ${fh(d.t)}.` : ''}`,
        botones: [a.prueba ? h('a', { class: 'bt mini', href: a.prueba, target: '_blank', rel: 'noopener' }, icono('ext'), 'Ver la prueba') : null,
          puede && !d ? botonConfirmar({ texto: 'Pedir que se quite', pregunta: '¿A la cola?', confirmar: 'Sí', mini: true, soloLectura: ctx.soloLectura,
            alConfirmar: async () => { await ctx.accion({ herramienta: a.herramienta.toLowerCase().includes('desk') ? 'desk' : a.herramienta.toLowerCase().includes('zadarma') ? 'zadarma' : a.herramienta.toLowerCase().includes('clickup') ? 'clickup' : 'app', tipo: 'quitar_acceso', objeto: a.id, texto: `Quitar acceso de ${a.persona} en ${a.herramienta}`, vista_previa: { persona: a.persona, herramienta: a.herramienta, que: a.que_hacer } }); setTimeout(() => S.rehacer(), 700); return 'En la cola simulada'; } }) : null] };
    })) : vacio({ icono: 'escudo', tono: 'celebrar', titulo: 'Nadie que se haya ido conserva acceso', texto: 'Desk, CRM, ClickUp y Zadarma cuadran con la tabla de personas.' }),
    ok.length ? h('p', { class: 'sub', style: PAD }, icono('ok', { clase: 's' }), ` Sin acceso, como debe ser: ${[...new Set(ok.map(a => a.persona))].join(', ')}.`) : null,
    h('div', { class: 'fila', style: { padding: '0 var(--relleno) var(--s-4)' } }, frescura(fres(D, 'desk_agentes')), frescura(fres(D, 'crm_usuarios')), frescura(fres(D, 'clickup_miembros')), frescura(fres(D, 'zadarma_ext')))));

  if (!inc.length) { zona.append(vacio({ icono: 'capas', tono: 'celebrar', borde: true, titulo: 'Sin incongruencias que puedas ver', texto: 'ClickUp, Desk y el CRM dicen lo mismo de tus clientes.' })); return; }

  // ---- incongruencias por tipo (orden por cuántas hay)
  const tipos = Object.entries(inc.reduce((m, x) => (m[x.tipo] = (m[x.tipo] || 0) + 1, m), {})).sort((a, b) => b[1] - a[1]);
  const pendientes = inc.filter(x => !decidida(x.id));
  const chips = chipsFiltro({ etiqueta: 'Tipo', clave: 'incidencias.incong', alCambiar: () => pintarT(), opciones: [
    { valor: '', texto: 'Todas', cuenta: pendientes.length }, { valor: '__decididas', texto: 'Decididas', icono: 'check', cuenta: inc.length - pendientes.length },
    ...tipos.map(([t]) => ({ valor: t, texto: t, cuenta: pendientes.filter(x => x.tipo === t).length, cuentaEstado: 'rojo' })),
  ] });
  const caja = h('div');
  const pintarT = () => {
    const v = chips.valor();
    const filas = inc.filter(x => v === '__decididas' ? decidida(x.id) : !decidida(x.id) && (!v || x.tipo === v));
    caja.replaceChildren(tablaDensa({
      filas: filas.map(x => ({ ...x, _quien: x.cliente || '—' })),
      buscar: { campos: ['_quien', 'detalle', 'tipo'], placeholder: 'Buscar cliente o persona' },
      columnas: [
        { clave: '_quien', titulo: 'Cliente o persona', principal: true, celda: x => h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap', alignItems: 'flex-start' } }, x.cliente_id && S.cli.get(x.cliente_id) ? logoCliente(S.cli.get(x.cliente_id)) : h('span', { class: 'ico-c s gris' }, icono('persona')), h('span', { style: { minWidth: 0 } }, h('b', {}, x._quien), h('span', { class: 'sub', style: { display: 'block' } }, x.tipo))) },
        { clave: 'detalle', titulo: 'Qué no cuadra', celda: x => h('span', {}, nombresBien(x.detalle, PERSONAS)) },
        { clave: 'herramientas', titulo: 'Dónde', ordenable: false, celda: x => h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, (x.herramientas || []).map(t => h('span', { class: 'chip gris sin-punto' }, icono(ICO_H[t] || 'aj', { clase: 's' }), TXT_H[t] || t))) },
        { clave: 'decide', titulo: 'Decide', celda: x => { const d = decidida(x.id); return d ? h('span', { class: 'pila', style: { gap: 'var(--s-1)' } }, chipEstado('verde', d.opcion || 'No aplica'), h('span', { class: 'sub' }, `${nom(d.quien)} · ${fh(d.t)}`)) : x.decide; } },
        { clave: 'acc', titulo: '', ordenable: false, celda: x => decidida(x.id) || !puede ? null : h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, (x.opciones || []).filter(o => o !== 'No aplica').map(o => botonConfirmar({ texto: o, pregunta: '¿Decidido?', confirmar: 'Sí', mini: true, soloLectura: ctx.soloLectura,
          alConfirmar: async () => { await ctx.accion({ herramienta: 'app', tipo: 'decidir_incongruencia', objeto: x.id, cliente_id: x.cliente_id || null, texto: `${x.tipo} · ${x.cliente}: ${o}`, vista_previa: { opcion: o, tipo: x.tipo, detalle: x.detalle } }); setTimeout(() => S.rehacer(), 700); return 'Decidido'; } })),
          noAplica(x, S)) },
      ],
      vacio: { titulo: v === '__decididas' ? 'Todavía no has decidido ninguna' : 'Nada pendiente con este filtro', porque: 'Cada decisión queda en el rastro.', celebrar: v !== '__decididas' },
    }));
  };
  pintarT();
  zona.append(panel({ titulo: 'Incongruencias entre herramientas', icono: 'capas', sub: 'Cliente con distinto estado o persona según ClickUp, Desk, CRM, Sign o facturación. Cada una se decide con un clic (queda en el rastro); el cambio en la propia herramienta llegará cuando la app pueda escribir en ellas.' },
    h('div', { class: 'cuerpo', style: { paddingBottom: 'var(--s-1)' } }, chips), caja));
  zona.append(h('div', { class: 'fila' }, frescura(fres(D, 'panel')), frescura(fres(D, 'desk'))));
}

function noAplica(x, S) {
  const { ctx } = S;
  const caja = h('span', { class: 'fila', style: { gap: 'var(--s-1)' } });
  const ini = () => caja.replaceChildren(h('button', { type: 'button', class: 'bt mini', disabled: ctx.soloLectura || null, on: { click: preguntar } }, 'No aplica'));
  const preguntar = () => {
    const mot = h('input', { type: 'text', class: 'bt mini', style: { width: '160px', maxWidth: '100%', minWidth: '0' }, placeholder: 'Motivo', 'aria-label': 'Motivo de «No aplica»' });
    const ok = h('button', { type: 'button', class: 'bt mini pri', on: { click: async () => {
      if (!mot.value.trim()) { mot.focus(); mot.setAttribute('aria-invalid', 'true'); avisoFlotante('«No aplica» necesita un motivo', { icono: 'alert' }); return; }
      ok.disabled = true;
      await ctx.api('rastro', { metodo: 'POST', cuerpo: { modulo: ID, accion: 'no_aplica', objeto: x.id, motivo: mot.value.trim() } }).catch(() => null);
      await ctx.accion({ herramienta: 'app', tipo: 'no_aplica', objeto: x.id, cliente_id: x.cliente_id || null, texto: `No aplica: ${mot.value.trim()}`, vista_previa: { motivo: mot.value.trim(), tipo: x.tipo } });
      S.rehacer();
    } } }, 'Guardar');
    caja.replaceChildren(mot, ok, h('button', { type: 'button', class: 'bt mini', on: { click: ini } }, 'No'));
    mot.focus();
  };
  ini();
  return caja;
}

// ================================================================== Traspasos de cartera
function estadoTraspaso(t, S) {
  const l = S.porObjeto.get(t.id) || [];
  const revisado = [...l].reverse().find(a => a.tipo === 'traspaso_revisado');
  if (revisado) return { c: 'verde', t: `Revisado · ${fh(fechaServ(revisado.creada))}` };
  const pend = [t.estado_app, t.estado_desk, t.estado_crm].filter(e => e && e !== 'hecho' && e !== 'sin dato');
  if (pend.length) return { c: 'rojo', t: `${fmt.plural(pend.length, 'herramienta')} sin cambiar` };
  if (!t.fecha) return { c: 'ambar', t: 'Sin fecha registrada' };
  if (t.revision && t.revision < diaISO(new Date())) return { c: 'ambar', t: 'Toca revisarlo' };
  return { c: 'azul', t: `Revisión el ${fDiaRO(t.revision)}` };
}

function pintarTraspasos(zona, S) {
  const { ctx, D, nom } = S;
  const puede = gestiona(ctx);
  const tr = (D.traspasos || []).map(t => ({ ...t, _e: estadoTraspaso(t, S) }));
  const appT = S.acciones.filter(a => a.tipo === 'traspaso').map(a => ({ ...vp(a), quien: a.quien, t: fechaServ(a.creada) }));
  zona.append(tiles([
    tile({ icono: 'users', etiqueta: 'Traspasos registrados', valor: tr.length + appT.length, contexto: 'Del rastro de ClickUp, las asignaciones y la app', medible: 'medias', medibleDetalle: 'Antes del 2-oct los traspasos no tenían registro: se reconstruyen del rastro' }),
    tile({ icono: 'alert', etiqueta: 'Con alguna herramienta sin cambiar', valor: tr.filter(t => t._e.c === 'rojo').length, estado: tr.some(t => t._e.c === 'rojo') ? 'rojo' : 'verde', contexto: 'La app, Desk o el CRM siguen con la persona anterior', medible: 'hoy', frescura: fres(D, 'desk') }),
    tile({ icono: 'cal', etiqueta: 'Sin fecha', valor: tr.filter(t => !t.fecha).length, estado: tr.some(t => !t.fecha) ? 'ambar' : 'verde', contexto: 'Sin fecha no hay revisión a los 14 días', medible: 'hoy' }),
  ]));
  const chip = e => !e ? chipEstado('gris', 'sin dato') : e === 'hecho' ? chipEstado('verde', 'hecho') : chipEstado('rojo', e);
  zona.append(panel({ titulo: 'Traspasos de cartera', icono: 'users', sub: 'Quién pasa qué cliente a quién y cuándo, con su prueba y la revisión a los 14 días. Las asignaciones se cambian en Ajustes › Asignaciones.' },
    tablaDensa({
      filas: tr.map(t => ({ ...t, _de_a: `${t.de} → ${t.a}` })),
      buscar: { campos: ['cliente', '_de_a'], placeholder: 'Buscar cliente o persona' },
      columnas: [
        { clave: 'cliente', titulo: 'Cliente', principal: true, celda: t => h('span', { class: 'celda-cli' }, S.cli.get(t.cliente_id) ? logoCliente(S.cli.get(t.cliente_id)) : null, t.cliente) },
        { clave: '_de_a', titulo: 'De → a', celda: t => h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, h('span', { class: 'av s' }, iniciales(t.de)), icono('derecha', { clase: 's' }), h('span', { class: 'av s' }, iniciales(t.a)), `${t.de} → ${t.a}`) },
        { clave: 'fecha', titulo: 'Fecha', celda: t => t.fecha ? fDiaRO(t.fecha) : chipEstado('ambar', 'sin fecha') },
        { clave: 'estado_app', titulo: 'App', celda: t => chip(t.estado_app) },
        { clave: 'estado_desk', titulo: 'Desk', celda: t => chip(t.estado_desk) },
        { clave: 'estado_crm', titulo: 'CRM', celda: t => chip(t.estado_crm === 'sin dato' ? null : t.estado_crm) },
        { clave: '_e', titulo: 'Estado', valor: t => t._e.c, celda: t => h('span', { class: 'pila', style: { gap: 'var(--s-1)' } }, chipEstado(t._e.c, t._e.t),
          t.prueba ? h('a', { href: t.prueba, target: '_blank', rel: 'noopener', class: 'bt mini' }, icono('ext', { clase: 's' }), 'Ver prueba') : h('span', { class: 'sub', title: t.fuente }, 'sin prueba'),
          puede && t._e.c !== 'verde' ? botonConfirmar({ texto: 'Revisado', pregunta: '¿Comprobado en todas las herramientas?', confirmar: 'Sí', mini: true, soloLectura: ctx.soloLectura,
            alConfirmar: async () => { await ctx.accion({ herramienta: 'app', tipo: 'traspaso_revisado', objeto: t.id, cliente_id: t.cliente_id, texto: `Traspaso ${t.cliente} revisado`, vista_previa: { de: t.de_id, a: t.a_id } }); setTimeout(() => S.rehacer(), 700); return 'Revisado'; } }) : null) },
      ],
      vacio: { titulo: 'Ningún traspaso de tus clientes', porque: 'Cuando un cliente cambie de manos, aparecerá aquí con su fecha.', celebrar: true },
    })));
  if (puede) {
    const zf = h('div');
    const abrir = () => {
      const c = h('select', {}, ctx.clientesVisibles.slice().sort((a, b) => a.nombre.localeCompare(b.nombre)).map(x => h('option', { value: x.id }, x.nombre)));
      const ps = (ctx.datos.personas || []).filter(p => p.estado !== 'baja' && (p.puestos || []).some(q => ['account', 'trafficker', 'especialista_ghl', 'seo', 'web', 'redes', 'produccion', 'direccion'].includes(q)));
      const de = h('select', {}, ps.map(p => h('option', { value: p.id }, p.alias || p.nombre))); const a = h('select', {}, ps.map(p => h('option', { value: p.id }, p.alias || p.nombre)));
      const silla = h('select', {}, ['account', 'trafficker', 'crm', 'ghl', 'seo', 'web', 'redes', 'produccion'].map(s => h('option', { value: s }, s)));
      const f = h('input', { type: 'date', value: diaISO(new Date()) }); const err = h('span', { style: ERR, role: 'alert' });
      const sincro = () => { const cc = S.cli.get(c.value); if (cc?.responsable_id && [...de.options].some(o => o.value === cc.responsable_id)) de.value = cc.responsable_id; };
      c.addEventListener('change', sincro); sincro();
      zf.replaceChildren(h('form', { style: FORM, on: { submit: async e => {
        e.preventDefault(); if (de.value === a.value) { err.textContent = 'La persona de origen y la de destino son la misma.'; return; }
        await ctx.accion({ herramienta: 'app', tipo: 'traspaso', objeto: `${c.value}:${silla.value}`, cliente_id: c.value, texto: `Traspaso de ${S.cli.get(c.value)?.nombre}: ${nom(de.value)} → ${nom(a.value)} (${silla.value}) el ${f.value}`, vista_previa: { cliente_id: c.value, silla: silla.value, de: de.value, a: a.value, fecha: f.value, revision: diaISO(new Date(new Date(f.value).getTime() + 14 * 864e5)) } });
        avisoFlotante('Traspaso registrado · revisión a 14 días'); S.rehacer();
      } } }, h('b', {}, 'Registrar un traspaso'),
      h('div', { style: DOS_C }, campoL('Cliente', c), campoL('Silla', silla)),
      h('div', { style: DOS_C }, campoL('De', de), campoL('A', a)), campoL('Fecha', f), err,
      h('p', { class: 'sub' }, 'Queda en el rastro con revisión a los 14 días. La asignación de verdad la cambia Mili en Ajustes › Asignaciones (cierra la fila vieja con fecha y abre la nueva).'),
      h('div', { class: 'fila' }, h('button', { type: 'submit', class: 'bt pri' }, icono('check'), 'Registrar'), h('a', { class: 'bt', href: '#/ajustes' }, icono('aj'), 'Ir a Asignaciones'), h('button', { type: 'button', class: 'bt', on: { click: () => zf.replaceChildren() } }, 'Cancelar'))));
      zf.querySelector('select')?.focus();
    };
    zona.append(panel({ titulo: 'Traspasos registrados en la app', icono: 'hist', sub: 'Los que se apuntan desde aquí, con quién los registró', acciones: ctx.soloLectura ? null : h('button', { type: 'button', class: 'bt pri', on: { click: abrir } }, icono('mas'), 'Registrar traspaso') }, zf,
      appT.length ? h('ul', { class: 'lista-i cuerpo' }, appT.map(t => h('li', {}, h('span', { class: 'ico-c s' }, icono('users')), h('span', { class: 't' }, `${S.cli.get(t.cliente_id)?.nombre || t.cliente_id}: ${nom(t.de)} → ${nom(t.a)} (${t.silla})`), h('span', { class: 'x' }, `${fDiaRO(t.fecha)} · revisión ${fDiaRO(t.revision)} · ${nom(t.quien)}`))))
        : vacio({ icono: 'users', titulo: 'Todavía no se ha registrado ninguno desde la app', texto: 'Cuando Mili pase un cliente de un account a otro, que lo apunte aquí: queda la fecha y la revisión.' })));
  }
}

// ================================================================== Quién vio primero
function pintarVistos(zona, S) {
  const { D, incs, nom } = S;
  const v = D.vistos || [];
  const conAviso = v.filter(x => x.primero);
  const mili = conAviso.filter(x => x.primero === 'mili').length;
  const tomas = conAviso.filter(x => x.primero === 'tomas').length;
  const nadie = v.filter(x => !x.primero && x.en_rojo_hoy).length;
  const appVistos = incs.filter(i => i.primeroVisto);
  const appMili = appVistos.filter(i => i.primeroVisto.quien === 'mili').length;
  zona.append(tiles([
    tile({ icono: 'ojo', etiqueta: 'Mili lo vio primero', valor: mili, unidad: `de ${conAviso.length}`, estado: conAviso.length && mili / conAviso.length >= 0.9 ? 'verde' : mili / (conAviso.length || 1) >= 0.7 ? 'ambar' : 'rojo',
      contexto: 'Clientes críticos con aviso escrito, 14-sep → 2-oct. La idea: que detecte ella, no Tomás', medible: 'medias', medibleDetalle: 'Solo lo escrito en ClickUp; WhatsApp y llamadas no dejan rastro', frescura: fres(D, 'rastro') }),
    tile({ icono: 'crown', etiqueta: 'Lo vio antes Tomás', valor: tomas, unidad: `de ${conAviso.length}`, estado: tomas ? 'rojo' : 'verde', contexto: v.filter(x => x.primero === 'tomas').map(x => x.cliente).join(', ') || 'Ninguno', medible: 'medias' }),
    tile({ icono: 'alert', etiqueta: 'Críticos y sin aviso de nadie', valor: nadie, estado: nadie ? 'rojo' : 'verde', contexto: 'Cuentan como gestión de Operaciones (no hay aviso escrito)', medible: 'medias' }),
    tile({ icono: 'check', etiqueta: 'Marcadas «La he visto» en la app', valor: appVistos.length, unidad: appVistos.length ? `· Mili primera en ${appMili}` : '', contexto: 'Desde hoy, cada incidencia guarda quién la vio primero', medible: 'hoy' }),
  ]));
  zona.append(panel({ titulo: 'Quién vio primero cada cliente crítico', icono: 'ojo', sub: 'Primer aviso escrito de Mili, Tomás o Coti en ClickUp, con su enlace. Del 14-sep al 2-oct (los 19 clientes que pidió Tomás y los escalados).' },
    tablaDensa({
      filas: v.map(x => ({ ...x, _p: x.primero ? nom(x.primero) : 'nadie' })),
      orden: { clave: 'primero_fecha', dir: 'asc' },
      buscar: { campos: ['cliente', '_p'], placeholder: 'Buscar cliente' },
      filtros: [{ clave: '_p', titulo: 'Lo vio primero' }],
      columnas: [
        { clave: 'cliente', titulo: 'Cliente', principal: true, celda: x => h('span', { class: 'celda-cli' }, S.cli.get(x.cliente_id) ? logoCliente(S.cli.get(x.cliente_id)) : null, x.cliente) },
        { clave: '_p', titulo: 'Lo vio primero', celda: x => x.primero ? h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, chipEstado(x.primero === 'mili' ? 'verde' : 'rojo', nom(x.primero))) : chipEstado('rojo', 'nadie por escrito') },
        { clave: 'primero_fecha', titulo: 'Cuándo', celda: x => x.primero_fecha ? h('span', {}, fh(fechaLocal(x.primero_fecha)), ' ', x.primero_enlace ? h('a', { href: x.primero_enlace, target: '_blank', rel: 'noopener', class: 'sub' }, 'ver') : null) : '—' },
        { clave: 'mili_fecha', titulo: 'Mili', celda: x => x.mili_fecha ? `${fh(fechaLocal(x.mili_fecha))} · ${fmt.plural(x.avisos_mili || 0, 'aviso')}` : h('span', { class: 'sub' }, 'sin aviso') },
        { clave: 'tomas_fecha', titulo: 'Tomás', celda: x => x.tomas_fecha ? fh(fechaLocal(x.tomas_fecha)) : h('span', { class: 'sub' }, '—') },
        { clave: 'en_rojo_hoy', titulo: 'Hoy', valor: x => x.en_rojo_hoy ? 1 : 0, celda: x => x.en_rojo_hoy ? chipEstado('rojo', 'crítico') : chipEstado('verde', 'sin alarma roja') },
      ],
    })));
  zona.append(avisoParcial('Antes del 2-oct, «visto» solo existe donde alguien lo escribió en ClickUp (rastro_mili.md, leído por API). Desde hoy, el botón «La he visto» de cada ficha guarda la hora del servidor y quién fue el primero.', { tipo: 'info' }));
}

// ================================================================== El mes
function pintarMes(zona, S) {
  const { D, incs, nom } = S;
  const hoy = new Date();
  const mesIni = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
  const resueltas = incs.filter(i => i.resueltaEn);
  const tiempos = resueltas.map(i => (i.resueltaEn - i.det) / 864e5).filter(x => x >= 0);
  const media = tiempos.length ? tiempos.reduce((a, b) => a + b, 0) / tiempos.length : null;
  const abiertas = incs.filter(i => i.abierta);
  zona.append(tiles([
    tile({ icono: 'alert', etiqueta: 'Abiertas hoy', valor: abiertas.length, estado: abiertas.length ? 'rojo' : 'verde', contexto: `${incs.filter(i => i.det && i.det >= mesIni).length} detectadas este mes`, medible: 'hoy' }),
    tile({ icono: 'check', etiqueta: 'Resueltas', valor: resueltas.length, contexto: 'Con prueba (en la app o en el rastro)', medible: 'hoy' }),
    tile({ icono: 'clock', etiqueta: 'Tiempo medio de resolución', valor: media === null ? null : fmt.num(media, 1), unidad: 'días', contexto: tiempos.length ? `Sobre ${fmt.plural(tiempos.length, 'resuelta')}` : 'Sin resueltas todavía', medible: 'medias', medibleDetalle: 'Empieza a contar desde el 2-oct; antes, solo lo que dice el rastro' }),
    tile({ icono: 'flag', etiqueta: 'Con causa confirmada', valor: incs.filter(i => i.causa.confirmada).length, unidad: `de ${incs.length}`, estado: incs.every(i => i.causa.confirmada) ? 'verde' : 'ambar', contexto: 'Aceptación de M5: una semana con todas confirmadas', medible: 'hoy' }),
  ]));
  const porQue = Object.keys(POR_QUE).map(k => ({ etiqueta: POR_QUE[k], icono: ICONO_POR_QUE[k], valor: incs.filter(i => i.causa.por_que === k).length, estado: k === 'gestion_operaciones' ? 'rojo' : k === 'ejecucion' ? 'ambar' : null, nota: `${incs.filter(i => i.causa.por_que === k && i.causa.confirmada).length} confirmadas` }));
  const donde = Object.keys(DONDE).map(k => ({ etiqueta: DONDE[k], valor: incs.filter(i => i.causa.donde === k).length }));
  const porResp = Object.entries(abiertas.reduce((m, i) => (m[i.responsable] = (m[i.responsable] || 0) + 1, m), {})).sort((a, b) => b[1] - a[1]);
  zona.append(h('div', { class: 'dos' },
    panel({ titulo: 'Por qué se rompe', icono: 'flag', sub: 'Confirmada o, si no, propuesta. Gestión de Operaciones = sin prueba de aviso.' }, h('div', { class: 'cuerpo' }, embudoBarras(porQue))),
    panel({ titulo: 'Dónde se rompe', icono: 'pin' }, h('div', { class: 'cuerpo' }, embudoBarras(donde)))));
  zona.append(panel({ titulo: 'Abiertas por responsable', icono: 'eq', sub: 'Para la conversación del viernes' },
    h('ul', { class: 'lista-i cuerpo' }, porResp.map(([p, n]) => h('li', {}, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(p)), h('span', { class: 't' }, p), h('span', { class: 'x' }, `${n}`))))));

  // ---- informe de Operaciones del mes (se genera solo)
  const lineas = [];
  lineas.push(`INFORME DE OPERACIONES · ${hoy.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })} (generado el ${fh(hoy)})`, '');
  lineas.push(`Incidencias abiertas: ${abiertas.length}. Resueltas con prueba: ${resueltas.length}.${media !== null ? ` Tiempo medio: ${fmt.num(media, 1)} días.` : ''}`);
  lineas.push(`Por qué: ${porQue.filter(x => x.valor).map(x => `${x.etiqueta} ${x.valor}`).join(' · ')}.`, '');
  lineas.push('CLIENTES EN ROJO Y QUÉ HIZO OPERACIONES');
  for (const i of incs.filter(x => x.origen === 'alarma').sort((a, b) => (a.det || 0) - (b.det || 0))) {
    const av = i.avisos.filter(e => e.quien === 'mili');
    const r = i.evs.filter(e => e.paso === 'respuesta');
    lineas.push(`· ${i.cliente} (${i.responsable}): ${i.regla.toLowerCase()}, desde el ${fh(i.det)}. ${av.length ? `Mili avisó o escaló ${av.length} ${av.length === 1 ? 'vez' : 'veces'} (${av.map(e => fh(e.t).split(' ·')[0]).join(', ')})` : 'Sin aviso escrito de Operaciones'}. ${r.length ? `Respuesta: ${r[r.length - 1].texto.replace(/\.$/, '')}` : 'Sin respuesta escrita del responsable'}. Estado: ${ESTADO[i.estado].t.toLowerCase()}.`);
  }
  const sinAv = (D.vistos || []).filter(x => !x.primero && x.en_rojo_hoy);
  if (sinAv.length) lineas.push('', `Críticos sin ningún aviso escrito: ${sinAv.map(x => x.cliente).join(', ')}. Cuentan como gestión de Operaciones.`);
  lineas.push('', 'SISTEMA Y CONFIGURACIÓN');
  for (const i of incs.filter(x => x.origen !== 'alarma' && ['sistema', 'configuracion'].includes(x.causa.por_que) && x.abierta)) lineas.push(`· ${i.titulo}: ${i.texto}`);
  const d48 = incs.filter(x => x.regla === 'desk_48' && x.abierta);
  if (d48.length) lineas.push('', `CORREOS SIN CONTESTAR > 48 H: ${d48.length} clientes, ${d48.reduce((s, i) => s + (i.numeros?.correos || 0), 0)} correos. Más afectados: ${d48.slice().sort((a, b) => (b.numeros?.correos || 0) - (a.numeros?.correos || 0)).slice(0, 5).map(i => `${i.cliente} (${i.numeros.correos}, ${i.responsable})`).join(', ')}.`);
  const ta = h('textarea', { 'aria-label': 'Informe de Operaciones del mes', style: { minHeight: '260px' } }); ta.value = lineas.join('\n');
  zona.append(panel({ titulo: 'Informe de Operaciones del mes', icono: 'doc', sub: 'Se genera solo con el formato «Tribulex no se reunió y avisé 3 veces a X» (ideas D13 y D14). Revísalo, añade lo tuyo y cópialo.', acciones: h('button', { type: 'button', class: 'bt pri', on: { click: () => copiar(ta.value, 'Informe copiado') } }, icono('copy'), 'Copiar') },
    h('div', { class: 'cuerpo campo' }, ta)));

  // ---- revisión mensual de Zadarma (a mano) y extensiones
  const ext = D.extensiones || [];
  zona.append(h('div', { class: 'dos' },
    panel({ titulo: 'Revisión mensual de la centralita', icono: 'phone', sub: 'Lo que la API de Zadarma no da. Marca cada casilla al revisarla: queda en el rastro con la fecha.' },
      h('div', {}, (D.revision_mensual_zadarma || []).map((t, n) => {
        const k = `zadarma-${hoy.getFullYear()}-${hoy.getMonth() + 1}-${n}`;
        const hecho = (S.porObjeto.get(k) || []).length;
        const cb = h('input', { type: 'checkbox', checked: hecho ? true : null, disabled: hecho || !gestiona(S.ctx) || null, 'aria-label': t, on: { change: async () => { await S.ctx.accion({ herramienta: 'app', tipo: 'revision_zadarma', objeto: k, texto: `Revisión de la centralita: ${t}`, vista_previa: { casilla: t } }); avisoFlotante('Casilla guardada'); S.rehacer(); } } });
        return h('label', { class: 'fila', style: { flexWrap: 'nowrap', alignItems: 'flex-start', gap: 'var(--s-3)', padding: 'var(--s-2) var(--relleno)', borderTop: n ? 'var(--borde-suave)' : '0' } }, cb, h('span', {}, t, hecho ? h('span', { class: 'sub', style: { display: 'block' } }, `Revisado por ${nom((S.porObjeto.get(k) || [])[0].quien)}`) : null));
      }))),
    panel({ titulo: 'Extensiones de la centralita', icono: 'auricular', sub: 'Estado leído hoy en Zadarma y llamadas desde el 1-sep' },
      h('ul', { class: 'lista-i cuerpo' }, ext.map(e => h('li', {},
        h('span', { class: `ico-c s ${e.en_linea === 'true' ? 'verde' : e.llamadas_32d ? 'ambar' : 'rojo'}` }, icono('phone')),
        h('span', { class: 't' }, `${e.extension} · ${e.nombre || 'sin nombre'}`, h('span', { class: 'sub', style: { display: 'block' } }, e.en_linea === 'true' ? 'conectada' : 'desconectada')),
        h('span', { class: 'x' }, `${e.llamadas_32d} llamadas`)))),
      h('div', { class: 'fila', style: { padding: '0 var(--relleno) var(--s-4)' } }, frescura(fres(D, 'zadarma_ext')), frescura(fres(D, 'zadarma'))))));
}
