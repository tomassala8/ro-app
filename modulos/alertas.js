// modulos/alertas.js · «Alertas del departamento» (carril N4, 2-oct-2026 noche; A2 y A8 de 43_IDEAS_MEJORA, misma noche).
// Motor ÚNICO de alertas: no recalcula nada. fuentes_alertas/generar_alertas.py reúne lo que ya calculan los módulos
// (verdad única, En rojo, Bandeja, Clientes nuevos, Captación, Salud del CRM, SEO y webs, Redes, Informes, Reuniones,
// Horas, Personas, Finanzas, Incidencias, Decisiones y la salud de conexiones) y asigna cada alerta a su departamento y a
// su dueño (la silla del cliente en asignaciones o, si no hay, el jefe del departamento).
// Datos: data/alertas/p_<persona>.json (solo_propio: las suyas, las de su departamento si es jefe; Mili y Tomás todas).
// Estados (nueva · vista · lo tengo · resuelta · no aplica · pospuesta) = acciones del módulo en la cola simulada, con rastro.
// Escalado en vivo: pasado el plazo sin «Lo tengo» sube al jefe; pasado otro plazo igual, a Mili. Lo pospuesto no escala.
// A2: «Ir» abre el OBJETO (el correo con la caja de respuesta, la ficha en su pestaña, la subcuenta, la campaña…).
// A8: selección múltiple con lote (Lo tengo · Resuelta · No aplica con motivo · Posponer), «Posponer» (mañana, el
// lunes o una fecha) y cifras con UNA sola definición: la del generador (D.definiciones), interpretada abajo tal cual.

import { franjaCifras, consejoCompacto } from './_trabajo.js';   // Ronda U (molde de pantalla de trabajo)
import {
  h, fmt, tile, listaLoPrimero, chipEstado, chipsFiltro, pestanas, vacio, avisoParcial, logoCliente, panel,
  icono, iniciales, limpiaTexto, tablaApilable, copiar, avisoFlotante, frescura,
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

const ID = 'alertas';
const GRAV = {
  alta: { texto: 'Crítica', color: 'rojo', orden: 0 },   // §2.1: el nivel máximo es «crítico»; «urgente» solo para plazos
  media: { texto: 'Vigilar', color: 'ambar', orden: 1 },
  baja: { texto: 'Aviso', color: 'gris', orden: 2 },
};
const ESTADO = {
  reabierta: { texto: 'Reabierta', color: 'rojo', orden: 0 },
  nueva: { texto: 'Nueva', color: 'azul', orden: 1 },
  vista: { texto: 'Vista', color: 'gris', orden: 2 },
  lo_tengo: { texto: 'Lo tengo', color: 'verde', orden: 3 },
  pospuesta: { texto: 'Pospuesta', color: 'gris', orden: 4 },
  resuelta: { texto: 'Resuelta · se comprueba con el dato siguiente', color: 'verde', orden: 5 },
  no_aplica: { texto: 'No aplica', color: 'gris', orden: 6 },
};
const ABIERTAS = new Set(['nueva', 'vista', 'reabierta', 'lo_tengo']);
const TIPO_ACCION = { vista: 'alerta_vista', lo_tengo: 'alerta_lo_tengo', resuelta: 'alerta_resuelta', no_aplica: 'alerta_no_aplica', nueva: 'alerta_reabrir', pospuesta: 'alerta_posponer' };
const DE_ACCION = { alerta_vista: 'vista', alerta_lo_tengo: 'lo_tengo', alerta_resuelta: 'resuelta', alerta_no_aplica: 'no_aplica', alerta_reabrir: 'nueva', alerta_posponer: 'pospuesta' };
const DE_LOTE = { lo_tengo: 'lo_tengo', resuelta: 'resuelta', no_aplica: 'no_aplica', posponer: 'pospuesta' };
const ICONO_HERR = { web: 'mundo_web', desk: 'inbox', clickup: 'check', ghl: 'base', meta: 'target', zadarma: 'phone', holded: 'euro', airtable: 'base', metricool: 'heart', searchConsole: 'globe', analytics: 'grafico', seranking: 'sube', modular: 'mundo_web' };
const NOMBRE_MOD = { 'seo-web': 'SEO y webs', 'salud-crm': 'Salud del CRM', captacion: 'Captación', redes: 'Redes', 'en-rojo': 'En rojo', bandeja: 'Bandeja', reuniones: 'Reuniones', 'informes-mensuales': 'Informes mensuales', incidencias: 'Incidencias', 'clientes-nuevos': 'Clientes nuevos', finanzas: 'Finanzas', personas: 'Personas', horas: 'Horas', decisiones: 'Decisiones', ajustes: 'Ajustes', ficha: 'la ficha' };
const MAX_LOTE = 200;

// Diseño (auditoría 30, N6): sin hoja propia. Tarjeta = clase común .panel; el resto, estilo en línea con tokens.
const PILA = g => ({ display: 'grid', gap: `var(--s-${g})`, minWidth: '0' });
const BORDE_GRAV = { alta: 'var(--bad)', media: 'var(--warn)', baja: 'var(--off)' };
const META = { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2) var(--s-4)', alignItems: 'center', font: 'var(--t-meta)', color: 'var(--mid)' };

// --------------------------------------------------------------------- utilidades
const aFecha = s => (s ? new Date(String(s).replace(' ', 'T')) : null);
const corto = (ctx, id) => (id ? ctx.nombre(id) : '—');
const dos = n => String(n).padStart(2, '0');
const aTexto = d => `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())} ${dos(d.getHours())}:${dos(d.getMinutes())}`;
const modDe = r => String(r || '').replace('#/', '').split('/')[0];
function horasTexto(h) {
  if (h < 1) return 'menos de 1 h';
  if (h < 48) return `${Math.round(h)} h`;
  return `${Math.round(h / 24)} días`;
}

// --------------------------------------------------------------------- <contar> · definición ÚNICA de las cifras
// No se cambia aquí: la definición vive en fuentes_alertas/generar_alertas.py (DEFINICIONES y CONTADORES) y llega en
// D.definiciones y D.contadores_def. Esto solo la interpreta, igual que el generador. pruebas_coherencia.py ejecuta
// este bloque en el navegador con los ficheros y comprueba que da lo mismo que el generador y que Mi día.
function cumpleDef(defs, nombre, H, yo) {
  return ((defs[nombre] || {}).si || []).every(c => condDef(defs, c, H, yo));
}
function condDef(defs, c, H, yo) {
  if (c.length === 1) return cumpleDef(defs, c[0], H, yo);
  if (c[0] === 'alguna') return c[1].some(x => condDef(defs, x, H, yo));
  const [campo, op, v0] = c;
  const v = v0 === 'yo' ? yo : v0;
  const x = H[campo];
  if (op === '=') return x === v;
  if (op === '!=') return x !== v;
  if (op === 'en') return v.includes(x);
  if (op === '>') return (x || 0) > v;
  return false;
}
function cumpleTodas(defs, nombres, H, yo) { return nombres.every(d => cumpleDef(defs, d, H, yo)); }
// </contar>

// --------------------------------------------------------------------- estado de la pantalla
const S = { ctx: null, D: null, acc: new Map(), local: new Map(), ahora: new Date(), visibles: 30, sel: new Set(), porId: new Map(), refrescar: null };

/** Lo que ya trae el fichero (local.db al generar), si no hay nada más nuevo. */
function delFichero(a) {
  return { estado: a.estado || 'nueva', quien: a.estado_por?.quien, hora: aFecha(a.estado_por?.hora), texto: a.estado_por?.texto, hasta: a.pospuesta?.hasta || null };
}
/** Estado de cada alerta: lo pulsado aquí, la cola en vivo (posterior al fichero) o el fichero. Lo pospuesto vuelve solo. */
function estadoDe(a) {
  let e = S.local.get(a.id);
  if (!e) { const viva = S.acc.get(a.id); e = viva && (!S.D.generado || viva.hora > aFecha(S.D.generado)) ? viva : delFichero(a); }
  if (e.estado === 'pospuesta' && e.hasta && aFecha(e.hasta) <= S.ahora) return { ...e, estado: 'nueva', volvio: true };
  return e;
}
/** Vencimiento: al volver de «posponer», el plazo empieza de nuevo (como el generador). */
function venceDe(a, est) {
  const base = aFecha(a.vence_antes || a.vence);
  if (!base) return null;
  if (est.hasta && a.plazo_h) { const v2 = new Date(aFecha(est.hasta).getTime() + a.plazo_h * 36e5); return v2 > base ? v2 : base; }
  return base;
}
/** Escalado en vivo: pasado el plazo sin «Lo tengo» → jefe; pasado otro plazo igual → Mili. Ni cerradas ni pospuestas. */
function nivelEscalado(a, est, ahora) {
  if (!['nueva', 'vista', 'reabierta'].includes(est.estado)) return 0;
  const v = venceDe(a, est);
  if (!v) return 0;
  const p = (a.plazo_h || 24) * 36e5;
  let n = 0;
  if (ahora >= v) n = 1;
  if (ahora - v >= p) n = 2;
  return Math.min(n, (a.escalado_cadena || []).length - 1);
}
/** Los hechos de una alerta que usa la definición única (los mismos que hechos() del generador). */
function hechos(a) {
  const est = estadoDe(a);
  const nivel = nivelEscalado(a, est, S.ahora);
  const v = venceDe(a, est);
  return { estado: est.estado, gravedad: a.gravedad, dueno: a.dueno_id, responsable: (a.escalado_cadena || [])[nivel] || a.dueno_id, nivel, vencida: !!(v && v <= S.ahora) };
}
const cumple = (a, nombres) => cumpleTodas(S.D.definiciones || {}, nombres, hechos(a), S.ctx.persona.id);
const cuenta = (lista, nombre) => lista.filter(a => cumple(a, S.D.contadores_def?.[nombre] || [])).length;
const de = (lista, nombre) => lista.filter(a => cumple(a, S.D.contadores_def?.[nombre] || []));

/** Quién puede posponer o despachar en lote (la misma regla que el generador y la guardia del servidor). */
function puedeActuar(pid, a) {
  const p = (S.ctx.datos?.personas || []).find(x => x.id === pid);
  return (a.escalado_cadena || []).includes(pid) || a.jefe_id === pid || !!(p && (p.puestos || []).some(x => x === 'direccion' || x === 'operaciones'));
}
const puedo = a => !S.ctx.soloLectura && puedeActuar(S.ctx.real.id, a);

async function cargar(ctx) {
  S.ctx = ctx; S.ahora = new Date(); S.local = new Map(); S.acc = new Map(); S.visibles = 30; S.sel = new Set();
  try { S.D = await ctx.datosModulo(`alertas/p_${ctx.persona.id}`); }
  catch (e) { S.D = null; S.error = e?.message || String(e); return; }
  S.porId = new Map((S.D.alertas || []).map(a => [a.id, a]));
  if (ctx.servidor) {
    try {
      const r = await ctx.api(`acciones?modulo=${ID}`);
      for (const x of [...(r.acciones || [])].sort((p, q) => p.id - q.id)) {
        const hora = new Date(String(x.creada).replace(' ', 'T') + 'Z');
        let vp = {};
        try { vp = typeof x.vista_previa === 'string' ? JSON.parse(x.vista_previa || '{}') || {} : x.vista_previa || {}; } catch { vp = {}; }
        const entradas = x.tipo === 'alerta_lote'
          ? (DE_LOTE[vp.accion] ? (vp.ids || []).map(id => ({ id: String(id), estado: DE_LOTE[vp.accion], lote: true })) : [])
          : (DE_ACCION[x.tipo] ? [{ id: x.objeto, estado: DE_ACCION[x.tipo] }] : []);
        for (const en of entradas) {
          const a = S.porId.get(en.id);
          if (!a) continue;
          // nadie pospone ni despacha en lote alertas ajenas (lo mismo que el generador: se ignora)
          if ((en.estado === 'pospuesta' || en.lote) && !puedeActuar(x.quien, a)) continue;
          if (en.estado === 'pospuesta') {
            const ha = aFecha(vp.hasta);
            if (!ha || ha <= hora || ha - hora > (S.D.posponer_max_dias || 31) * 864e5) continue;
          }
          S.acc.set(en.id, { estado: en.estado, quien: x.quien, hora, texto: x.texto, hasta: en.estado === 'pospuesta' ? vp.hasta : null });
        }
      }
    } catch { /* sin cola: valen los estados del fichero */ }
  }
}

// --------------------------------------------------------------------- posponer: mañana, el lunes o una fecha
function fechaVuelta(cuando, dia) {
  const d = new Date(S.ahora); d.setSeconds(0, 0);
  if (cuando === 'manana') { d.setDate(d.getDate() + 1); d.setHours(9, 0); }
  else if (cuando === 'lunes') { const n = ((8 - d.getDay()) % 7) || 7; d.setDate(d.getDate() + n); d.setHours(9, 0); }
  else { const [y, m, dd] = String(dia).split('-').map(Number); d.setFullYear(y, m - 1, dd); d.setHours(9, 0); }
  return d;
}
const TXT_CUANDO = { manana: 'mañana', lunes: 'el lunes', fecha: 'esa fecha' };
const hoyMas = n => { const d = new Date(S.ahora); d.setDate(d.getDate() + n); return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`; };

async function marcar(a, estado, texto, extra = {}) {
  const ctx = S.ctx;
  const t = texto || `${ESTADO[estado]?.texto || estado}: ${a.motivo}`;
  await ctx.accion({ herramienta: 'app', tipo: TIPO_ACCION[estado], objeto: a.id, cliente_id: a.cliente_id || null, texto: t.slice(0, 400),
    ...(estado === 'no_aplica' ? { motivo: t } : {}),
    vista_previa: { alerta: a.id, departamento: a.departamento, motivo: a.motivo, estado, ...extra } });
  S.local.set(a.id, { estado, quien: ctx.real.id, hora: new Date(), texto: t, hasta: extra.hasta || null });
  S.sel.delete(a.id);
  avisoFlotante(estado === 'lo_tengo' ? 'Anotado: lo tienes tú. El escalado se para.' : estado === 'resuelta' ? 'Marcada resuelta: se comprueba con el dato siguiente'
    : estado === 'no_aplica' ? 'Marcada «no aplica», con su motivo' : estado === 'pospuesta' ? `Pospuesta hasta el ${fDiaHoraRO(extra.hasta)}: no cuenta ni escala hasta entonces`
      : estado === 'nueva' ? 'Reabierta' : 'Marcada como vista');
}
async function posponer(a, cuando, dia) {
  const d = fechaVuelta(cuando, dia);
  const hasta = aTexto(d);
  await marcar(a, 'pospuesta', `Pospuesta hasta el ${fDiaHoraRO(hasta)}: ${a.motivo}`, { hasta, cuando });
}

/** Lote: UNA acción «alerta_lote» con las ids (la cola y el rastro la guardan entera); el generador la despliega. */
async function lote(accion, { motivo, cuando, dia } = {}) {
  const ctx = S.ctx;
  const ids = [...S.sel].filter(id => S.porId.has(id) && puedo(S.porId.get(id))).slice(0, MAX_LOTE);
  if (!ids.length) return;
  const hasta = accion === 'posponer' ? aTexto(fechaVuelta(cuando, dia)) : null;
  const que = { lo_tengo: 'Lo tengo', resuelta: 'Resueltas', no_aplica: 'No aplica', posponer: 'Pospuestas' }[accion];
  const texto = `${que} · ${fmt.plural(ids.length, 'alerta')}${motivo ? `: ${motivo}` : ''}${hasta ? ` hasta el ${fDiaHoraRO(hasta)}` : ''}`;
  await ctx.accion({ herramienta: 'app', tipo: 'alerta_lote', objeto: `lote:${ids.length}:${ids[0]}`, cliente_id: null, texto: texto.slice(0, 400),
    vista_previa: { ids, accion, motivo: motivo || null, hasta, cuando: cuando || null, n: ids.length } });
  const est = DE_LOTE[accion];
  for (const id of ids) S.local.set(id, { estado: est, quien: ctx.real.id, hora: new Date(), texto, hasta });
  S.sel.clear();
  avisoFlotante(`${texto}. Queda en el rastro.`);
}

// --------------------------------------------------------------------- «Ir» al objeto (A2)
function irDe(a) {
  const ctx = S.ctx;
  if (a.ir && ctx.veModulo(modDe(a.ir))) return { href: a.ir, texto: a.ir_texto || `Abrir ${NOMBRE_MOD[modDe(a.ir)] || 'pantalla'}` };
  if (a.ir_alt && ctx.veModulo(modDe(a.ir_alt))) return { href: a.ir_alt, texto: `Abrir ${NOMBRE_MOD[modDe(a.ir_alt)] || 'pantalla'}` };
  return null;
}
function botonIr(a, { pri = true } = {}) {
  const ir = irDe(a);
  if (!ir) return null;
  return h('a', { class: `bt mini${pri ? ' pri' : ''}`, href: ir.href, 'data-ir': 'objeto', title: `Ir: ${ir.texto.toLowerCase()}`,
    on: { click: () => S.ctx.rastro({ accion: 'ir', objeto: a.id, detalle: ir.href }) } }, icono('flecha', { clase: 's' }), ir.texto);
}

function plazoDe(a, est) {
  if (est.estado === 'lo_tengo') return { texto: `Lo tiene ${est.quien ? corto(S.ctx, est.quien) : 'su dueño'}`, color: 'verde' };
  if (est.estado === 'pospuesta') return { texto: `Pospuesta hasta el ${fDiaHoraRO(est.hasta)}`, color: 'gris' };
  if (!ABIERTAS.has(est.estado)) return { texto: ESTADO[est.estado]?.texto || est.estado, color: 'gris' };
  const v = venceDe(a, est);
  if (!v) return { texto: 'Aviso sin plazo', color: 'gris' };
  const hh = (v - S.ahora) / 36e5;
  if (hh < 0) return { texto: `Plazo pasado hace ${horasTexto(-hh)}`, color: 'rojo' };
  if (hh < 24) return { texto: `Vence en ${horasTexto(hh)}`, color: 'ambar' };
  return { texto: `Vence el ${fDiaRO(aTexto(v))}`, color: 'gris' };
}

// --------------------------------------------------------------------- controles compartidos (tarjeta y barra de lote)
/** «Posponer»: Mañana · El lunes · Elegir fecha (de mañana a 31 días). */
function controlPosponer(alElegir, { mini = true } = {}) {
  const ro = S.ctx.soloLectura;
  const caja = h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'wrap', alignItems: 'center' } });
  const inicial = () => caja.replaceChildren(
    h('span', { class: 'sub' }, 'Posponer:'),
    ...[['manana', 'Mañana'], ['lunes', 'El lunes']].map(([k, t]) => h('button', { type: 'button', class: `bt${mini ? ' mini' : ''}`, 'aria-disabled': ro ? 'true' : null,
      title: ro ? 'Estás en «ver como»: solo lectura' : `Vuelve ${TXT_CUANDO[k]} a las 9:00; mientras, no cuenta ni escala`,
      on: { click: async e => { if (ro) return; e.currentTarget.disabled = true; await alElegir(k); } } }, icono('clock', { clase: 's' }), t)),
    h('button', { type: 'button', class: `bt${mini ? ' mini' : ''}`, 'aria-disabled': ro ? 'true' : null, on: { click: () => { if (!ro) fecha(); } } }, icono('cal', { clase: 's' }), 'Elegir fecha'));
  function fecha() {
    const inp = h('input', { type: 'date', min: hoyMas(1), max: hoyMas(S.D.posponer_max_dias || 31), value: hoyMas(7), 'aria-label': 'Fecha en que vuelve la alerta' });
    const ok = h('button', { type: 'button', class: `bt${mini ? ' mini' : ''} pri`, on: { click: async () => {
      if (!inp.value || inp.value < inp.min || inp.value > inp.max) { inp.focus(); avisoFlotante(`Elige una fecha de mañana a ${S.D.posponer_max_dias || 31} días`, { icono: 'alert' }); return; }
      ok.disabled = true; await alElegir('fecha', inp.value);
    } } }, 'Posponer');
    caja.replaceChildren(h('span', { class: 'sub' }, 'Vuelve el'), h('label', { class: 'campo', style: { maxWidth: '180px' } }, inp), ok,
      h('button', { type: 'button', class: `bt${mini ? ' mini' : ''}`, on: { click: inicial } }, 'Cancelar'));
    inp.focus();
  }
  inicial();
  return caja;
}
/** «No aplica» pide un motivo, en la propia fila (nada de prompt()). */
function controlNoAplica(alGuardar, { mini = true, texto = 'No aplica' } = {}) {
  const ro = S.ctx.soloLectura;
  const caja = h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'wrap' } });
  const inicial = () => caja.replaceChildren(h('button', { type: 'button', class: `bt${mini ? ' mini' : ''}`, 'aria-disabled': ro ? 'true' : null,
    title: ro ? 'Estás en «ver como»: solo lectura' : null, on: { click: () => { if (!ro) pedir(); } } }, icono('cerrar', { clase: 's' }), texto));
  function pedir() {
    const inp = h('input', { type: 'text', placeholder: 'Por qué no aplica (obligatorio)', 'aria-label': 'Motivo de «no aplica»', maxlength: '200' });
    const guardar = h('button', { type: 'button', class: `bt${mini ? ' mini' : ''} pri`, on: { click: async () => {
      const m = inp.value.trim();
      if (m.length < 4) { inp.focus(); avisoFlotante('Escribe el motivo', { icono: 'alert' }); return; }
      guardar.disabled = true;
      try { await alGuardar(m); } catch (err) { guardar.disabled = false; avisoFlotante('No se pudo: ' + (err?.message || err), { icono: 'alert' }); }
    } } }, 'Guardar');
    const cancelar = h('button', { type: 'button', class: `bt${mini ? ' mini' : ''}`, on: { click: () => { inicial(); caja.querySelector('button')?.focus(); } } }, 'Cancelar');
    inp.addEventListener('keydown', e => { if (e.key === 'Enter') guardar.click(); if (e.key === 'Escape') cancelar.click(); });
    caja.replaceChildren(h('label', { class: 'campo', style: { flex: '1 1 200px', minWidth: '0' } }, inp), guardar, cancelar);
    inp.focus();
  }
  inicial();
  return caja;
}
const conError = fn => async (...xs) => {
  try { await fn(...xs); S.refrescar?.(); }
  catch (err) { avisoFlotante('No se pudo: ' + (err?.message || err), { icono: 'alert' }); S.refrescar?.(); }
};

// --------------------------------------------------------------------- tarjeta de una alerta
function tarjeta(a) {
  const ctx = S.ctx;
  const deps = S.D.departamentos || {};
  const dep = deps[a.departamento] || { nombre: a.departamento, icono: 'alert' };
  const est = estadoDe(a);
  const g = GRAV[a.gravedad] || GRAV.baja;
  const pl = plazoDe(a, est);
  const nivel = nivelEscalado(a, est, S.ahora);
  const responsable = (a.escalado_cadena || [a.dueno_id])[nivel];
  const cli = a.cliente_id ? (ctx.clientes.find(c => c.id === a.cliente_id) || { nombre: a.cliente || a.cliente_id }) : null;
  const abierta = ABIERTAS.has(est.estado);
  const ro = ctx.soloLectura;
  const actuo = puedo(a);
  const tituloRO = ro ? 'Estás en «ver como»: solo lectura' : null;
  const boton = (estado, texto, ico, extra = {}) => h('button', { type: 'button', class: `bt mini${extra.pri ? ' pri' : ''}`, 'aria-disabled': ro ? 'true' : null, title: tituloRO,
    on: { click: async e => { if (ro) return; e.currentTarget.disabled = true; await conError(() => marcar(a, estado))(); } } }, icono(ico, { clase: 's' }), texto);

  // A8: casilla para el lote (solo lo que puedes despachar)
  const casilla = (abierta || est.estado === 'pospuesta') && actuo
    ? h('label', { class: 'fila', style: { minHeight: '32px', minWidth: '32px', justifyContent: 'center', cursor: 'pointer', flex: '0 0 auto' }, title: 'Elegir para hacer lo mismo con varias' },
      h('input', { type: 'checkbox', 'data-sel': a.id, 'aria-label': `Elegir: ${limpiaTexto(a.motivo)}`, checked: S.sel.has(a.id) || null, style: { width: '20px', height: '20px', accentColor: 'var(--accent)' },
        on: { change: e => { if (e.target.checked) S.sel.add(a.id); else S.sel.delete(a.id); S.pintarBarra?.(); } } }))
    : null;

  // A2: «Ir» al objeto, primero; «Lo tengo» al lado; lo demás, en «Más» (antes 5-6 botones en fila).
  const acciones = h('div', { class: 'fila', style: { gap: 'var(--s-2)' } });
  acciones.append(...[botonIr(a)].filter(Boolean));
  const mas = h('div', { style: { ...PILA(2), padding: 'var(--s-2) 0 0' } });
  if (abierta) {
    if (est.estado !== 'lo_tengo') acciones.append(boton('lo_tengo', 'Lo tengo', 'persona', { pri: !irDe(a) && (a.dueno_id === ctx.persona.id || responsable === ctx.persona.id) }));
    mas.append(h('div', { class: 'fila', style: { gap: 'var(--s-2)' } },
      est.estado === 'nueva' || est.estado === 'reabierta' ? boton('vista', 'Vista', 'ojo') : null,
      boton('resuelta', 'Resuelta', 'ok'),
      controlNoAplica(m => conError(() => marcar(a, 'no_aplica', `No aplica: ${m}`))())));
    if (actuo) mas.append(controlPosponer((k, dia) => conError(() => posponer(a, k, dia))()));
  } else {
    acciones.append(boton('nueva', est.estado === 'pospuesta' ? 'Traer ya' : 'Reabrir', 'recargar'));
    if (est.estado === 'pospuesta' && actuo) mas.append(controlPosponer((k, dia) => conError(() => posponer(a, k, dia))()));
  }
  const fuera = (a.abrir || []).map(ab => h('a', { class: 'bt mini', href: ab.url, target: '_blank', rel: 'noopener', title: ab.texto,
    on: { click: () => ctx.rastro({ accion: 'abrir', objeto: a.id, detalle: ab.texto }) } }, icono(ICONO_HERR[ab.herramienta] || 'ext', { clase: 's' }), ab.texto, icono('ext', { clase: 's' })));
  if (fuera.length) mas.append(h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, ...fuera));
  const det = [
    ...(a.detalle || []).map(limpiaTexto),
    a.reabierta && est.estado === 'reabierta' ? a.reabierta : null,
    a.volvio || (est.volvio ? 'Vuelve de «posponer»: el plazo empieza de nuevo.' : null),
    est.texto && !ABIERTAS.has(est.estado) ? est.texto : null,
    `Dueño: ${corto(ctx, a.dueno_id)} · ${a.dueno_origen}`,
    `Escalado: ${(a.escalado_cadena || []).map(x => corto(ctx, x)).join(' → ')} (pasado el plazo sin «Lo tengo»; lo pospuesto no escala)`,
    `Cómo se da por resuelta: ${a.comprueba}`,
    `De dónde sale: ${a.fuente}`,
  ].filter(Boolean);

  // Ronda U (50 #1, Alertas «entre 4 y 10 pantallas»): la alerta en DOS líneas (qué + plazo · de dónde, quién y desde) con
  // «Ir» y «Lo tengo» a la derecha; el resto de acciones y el porqué, en un solo plegable «Más». Antes ~244 px por alerta.
  const UNA = { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: '0' };
  const movil = typeof matchMedia === 'function' && matchMedia('(max-width: 640px)').matches;
  const masDet = h('details', { class: 'que-es', style: { flex: '1 1 100%', minWidth: '0' } },
    h('summary', { style: { minHeight: '32px', display: 'inline-flex', alignItems: 'center' } }, abierta ? 'Más: resuelta, no aplica, posponer y por qué' : 'Más y por qué'),
    mas.childElementCount ? mas : null,
    h('ul', { class: 'sub', style: { ...PILA(1), margin: 'var(--s-1) 0 0', paddingLeft: 'var(--s-4)' } }, det.map(x => h('li', {}, x))));
  return h('article', { class: 'panel', 'data-alerta': a.id, 'aria-label': `${g.texto}: ${a.motivo}`,
    // Ronda U: flex con salto (no rejilla): si los botones no caben al lado del texto (≥ 260 px), bajan a su línea, a cualquier ancho
    style: { display: 'flex', flexWrap: 'wrap', columnGap: 'var(--s-3)', rowGap: 'var(--s-1)', alignItems: 'center', padding: 'var(--s-2) var(--s-4)',
      borderLeft: `4px solid ${BORDE_GRAV[a.gravedad] || 'var(--off)'}`, background: abierta ? null : 'var(--card-2)', boxShadow: 'none' } },
    casilla,
    h('span', { class: `ico-c s ${g.color === 'gris' ? '' : g.color}` }, icono(dep.icono || 'alert', { clase: 's' })),
    h('div', { style: { minWidth: '0', flex: '1 1 260px' } },
      h('div', { class: 'fila', style: { gap: 'var(--s-1) var(--s-2)', flexWrap: 'wrap', minWidth: '0' } },
        // en el móvil el qué ocupa su línea entera (2 como mucho) y los chips bajan debajo
        h('b', { style: movil ? { flex: '1 1 100%', display: '-webkit-box', WebkitLineClamp: '2', WebkitBoxOrient: 'vertical', overflow: 'hidden', font: 'var(--t-h3)', fontWeight: '700', overflowWrap: 'anywhere' }
          : { ...UNA, flex: '1 1 200px', font: 'var(--t-h3)', fontWeight: '700' }, title: limpiaTexto(a.motivo) }, limpiaTexto(a.motivo)),   // ≥ 200 px: si no caben los chips, bajan
        h('span', { style: { flex: 'none' } }, chipEstado(pl.color, pl.texto)),
        nivel ? h('span', { style: { flex: 'none' } }, chipEstado('rojo', `Escalada a ${corto(ctx, responsable)}`)) : null,
        est.estado !== 'nueva' ? h('span', { style: { flex: 'none' } }, chipEstado(ESTADO[est.estado]?.color || 'gris', ESTADO[est.estado]?.texto || est.estado)) : null),
      h('div', { class: 'sub', style: UNA }, [`${dep.nombre} · ${a.titulo}`, cli ? cli.nombre : a.persona || null, `de ${a.dueno_id === ctx.persona.id ? 'ti' : corto(ctx, a.dueno_id)}`,
        a.desde ? `desde ${fmt.hace(a.desde) === 'hoy' ? 'hoy' : fmt.hace(a.desde)}` : null, g.texto].filter(Boolean).join(' · '))),
    Object.assign(acciones, { style: 'display: flex; flex-wrap: wrap; gap: var(--s-2); flex: 0 1 auto; margin-left: auto' }),
    masDet);
}

// --------------------------------------------------------------------- lista con filtros, selección y lote
let LISTA = null;

// Filtros = definiciones del generador (las mismas que las tarjetas de arriba y Mi día).
const QUIEN = { mias: ['mia'], dep: [] };
const ESTADOS_FILTRO = quien => ({
  abiertas: ['abierta'], pasadas: ['plazo_pasado'], escaladas: quien === 'mias' ? ['escalada_a_mi'] : ['escalada'],
  pospuestas: ['pospuesta'], cerradas: ['cerrada'], todas: [],
});

function pintarLista(zona) {
  const ctx = S.ctx; const D = S.D;
  const deps = D.departamentos || {};
  const todas = D.alertas || [];
  const yo = ctx.persona.id;
  const quienOps = [{ valor: 'mias', texto: 'Mías', icono: 'persona' }];
  if (D.alcance !== 'mias') quienOps.push({ valor: 'dep', texto: D.alcance === 'todas' ? 'Todas' : 'Mi departamento', icono: D.alcance === 'todas' ? 'res' : 'eq' });
  S.quien = S.quien || (D.alcance === 'mias' || cuenta(todas, 'mias') ? 'mias' : 'dep');
  if (!quienOps.some(o => o.valor === S.quien)) S.quien = 'mias';

  const caja = h('div', { role: 'list', 'aria-label': 'Alertas', style: { ...PILA(3), padding: 'var(--s-4) var(--relleno)' } });
  const masBoton = h('div', { class: 'tabla-mas', style: { padding: '0 var(--relleno) var(--s-4)' } });
  const buscar = h('input', { type: 'search', placeholder: 'Buscar cliente, persona o motivo', 'aria-label': 'Buscar en las alertas' });
  const filtros = h('div', { style: { ...PILA(2), padding: 'var(--s-3) var(--relleno)', borderBottom: 'var(--borde-suave)' } });
  // Flotante abajo (el panel de pestañas recorta con overflow, así que «sticky» no se queda a la vista).
  const barra = h('div', { role: 'region', 'aria-label': 'Hacer lo mismo con las elegidas', 'aria-live': 'polite', hidden: true,
    style: { position: 'fixed', bottom: 'var(--s-4)', left: '50%', transform: 'translateX(-50%)', width: 'min(920px, calc(100vw - 32px))', zIndex: '30',
      background: 'var(--card)', border: 'var(--borde)', borderRadius: 'var(--r-l)', boxShadow: 'var(--sombra-3)', padding: 'var(--s-3) var(--s-4)', ...PILA(2), display: 'none' } });
  let chQuien, chDep, chEst, filasActuales = [];

  const conQuien = a => cumple(a, QUIEN[S.quien] || []);
  const pintarFiltros = () => {
    const base = todas.filter(conQuien);
    chQuien = quienOps.length > 1 ? chipsFiltro({ etiqueta: 'Ver', clave: `${ID}.quien.${yo}`, valor: S.quien,
      opciones: quienOps.map(o => ({ ...o, cuenta: cuenta(todas, o.valor === 'mias' ? 'mias' : 'en_vista') })),
      alCambiar: v => { S.quien = v; S.visibles = 30; pintarFiltros(); pintar(); } }) : null;
    if (chQuien) S.quien = chQuien.valor();
    const EF = ESTADOS_FILTRO(S.quien);
    const presentes = Object.keys(deps).filter(d => base.some(a => a.departamento === d));
    chDep = chipsFiltro({ etiqueta: 'Departamento', clave: `${ID}.dep.${yo}`, valor: '',
      opciones: [{ valor: '', texto: 'Todos', cuenta: base.filter(a => cumple(a, EF.abiertas)).length },
        ...presentes.map(d => ({ valor: d, texto: deps[d].nombre, icono: deps[d].icono,
          cuenta: base.filter(a => a.departamento === d && cumple(a, EF.abiertas)).length,
          cuentaEstado: base.some(a => a.departamento === d && cumple(a, ['abierta', 'urgente'])) ? 'rojo' : null }))],
      alCambiar: () => { S.visibles = 30; pintar(); } });
    const n = k => base.filter(a => cumple(a, EF[k])).length;
    chEst = chipsFiltro({ etiqueta: 'Estado', clave: `${ID}.estado.${yo}`, valor: 'abiertas',
      opciones: [
        { valor: 'abiertas', texto: 'Abiertas', icono: 'campana', cuenta: n('abiertas') },
        { valor: 'pasadas', texto: 'Plazo pasado', icono: 'clock', cuenta: n('pasadas'), cuentaEstado: 'rojo' },
        { valor: 'escaladas', texto: S.quien === 'mias' ? 'Escaladas a ti' : 'Escaladas', icono: 'sube', cuenta: n('escaladas'), cuentaEstado: 'rojo' },
        { valor: 'pospuestas', texto: 'Pospuestas', icono: 'clock', cuenta: n('pospuestas') },
        { valor: 'cerradas', texto: 'Resueltas y no aplica', icono: 'ok', cuenta: n('cerradas') },
        { valor: 'todas', texto: 'Todas', cuenta: base.length },
      ], alCambiar: () => { S.visibles = 30; pintar(); } });
    // Ronda U (molde, móvil): a 390 px los tres grupos de chips medían ~400 px antes de la primera alerta; en el móvil van
    // plegados en «Filtros» (la franja de cifras de arriba ya filtra lo de cada día) y el buscador queda a la vista.
    const grupos = [chQuien, chDep, chEst].filter(Boolean);
    const movilF = typeof matchMedia === 'function' && matchMedia('(max-width: 640px)').matches;
    const resumenF = grupos.map(g => g.querySelector('button[aria-pressed="true"]')?.textContent.replace(/\d+$/, '').trim()).filter(Boolean).join(' · ');
    filtros.replaceChildren(...(movilF ? [h('details', { class: 'que-es' }, h('summary', {}, `Filtros · ${resumenF}`), h('div', { style: { ...PILA(2), marginTop: 'var(--s-2)' } }, grupos))] : grupos),
      h('label', { class: 'campo', style: { maxWidth: '420px' } }, buscar));
  };
  S.elegirDep = d => { const i = [...chDep.querySelectorAll('button')].findIndex(b => b.textContent.startsWith(d ? (deps[d]?.nombre || d) : 'Todos')); chDep.querySelectorAll('button')[i]?.click(); };

  // A8: barra de lote (aparece al elegir una): Lo tengo · Resuelta · No aplica (motivo) · Posponer (mañana, lunes, fecha)
  S.pintarBarra = () => {
    for (const id of [...S.sel]) if (!S.porId.has(id)) S.sel.delete(id);
    const n = S.sel.size;
    barra.hidden = !n;
    barra.style.display = n ? 'grid' : 'none';             // el estilo en línea manda sobre «hidden»
    masBoton.style.paddingBottom = n ? 'calc(var(--s-16) * 3)' : '';      // que la barra flotante no tape la última tarjeta
    if (!n) { barra.replaceChildren(); return; }
    const elegibles = filasActuales.filter(a => puedo(a) && (ABIERTAS.has(estadoDe(a).estado) || estadoDe(a).estado === 'pospuesta'));
    const todasElegidas = elegibles.length && elegibles.every(a => S.sel.has(a.id));
    const hacer = (accion, extra) => conError(async () => { await lote(accion, extra); })();
    barra.replaceChildren(
      h('div', { class: 'fila', style: { gap: 'var(--s-2)', alignItems: 'center' } },
        h('b', {}, `${fmt.plural(n, 'elegida', 'elegidas')}`),
        !todasElegidas && elegibles.length > n ? h('button', { type: 'button', class: 'bt mini', on: { click: () => { elegibles.slice(0, MAX_LOTE).forEach(a => S.sel.add(a.id)); repintarCasillas(); } } },
          `Elegir las ${fmt.num(Math.min(elegibles.length, MAX_LOTE))} de este filtro`) : null,
        h('button', { type: 'button', class: 'bt mini', on: { click: () => { S.sel.clear(); repintarCasillas(); } } }, icono('cerrar', { clase: 's' }), 'Quitar la selección')),
      h('div', { class: 'fila', style: { gap: 'var(--s-2)', alignItems: 'center' } },
        h('button', { type: 'button', class: 'bt mini pri', on: { click: e => { e.currentTarget.disabled = true; hacer('lo_tengo'); } } }, icono('persona', { clase: 's' }), 'Lo tengo'),
        h('button', { type: 'button', class: 'bt mini', on: { click: e => { e.currentTarget.disabled = true; hacer('resuelta'); } } }, icono('ok', { clase: 's' }), 'Resueltas'),
        controlNoAplica(m => hacer('no_aplica', { motivo: m }), { texto: 'No aplica…' })),
      controlPosponer((k, dia) => hacer('posponer', { cuando: k, dia })));
  };
  const repintarCasillas = () => {
    caja.querySelectorAll('input[data-sel]').forEach(i => { i.checked = S.sel.has(i.dataset.sel); });
    S.pintarBarra();
  };

  const pintar = () => {
    const q = buscar.value.trim().toLowerCase();
    const dep = chDep.valor(); const e = chEst.valor();
    const EF = ESTADOS_FILTRO(S.quien);
    const filas = todas.filter(a => conQuien(a) && (!dep || a.departamento === dep) && cumple(a, EF[e] || [])
      && (!q || [a.motivo, a.cliente, a.titulo, a.persona, corto(ctx, a.dueno_id)].some(x => String(x || '').toLowerCase().includes(q))))
      .map(a => ({ a, est: estadoDe(a) }))
      .sort((x, y) => nivelEscalado(y.a, y.est, S.ahora) - nivelEscalado(x.a, x.est, S.ahora)
        || (GRAV[x.a.gravedad]?.orden ?? 3) - (GRAV[y.a.gravedad]?.orden ?? 3)
        || (ESTADO[x.est.estado]?.orden ?? 9) - (ESTADO[y.est.estado]?.orden ?? 9)
        || (venceDe(x.a, x.est) || 9e15) - (venceDe(y.a, y.est) || 9e15))
      .map(x => x.a);
    filasActuales = filas;
    if (!filas.length) {
      const celebrar = e === 'abiertas' || e === 'pasadas' || e === 'escaladas';
      caja.replaceChildren(vacio({ icono: celebrar ? 'ok' : 'filtro', tono: celebrar && !q ? 'celebrar' : 'neutro',
        titulo: q ? 'Nada con esa búsqueda' : celebrar ? (S.quien === 'mias' ? 'No tienes alertas aquí' : 'Ninguna alerta aquí') : 'Nada en este filtro',
        texto: q ? 'Prueba con otro cliente o motivo.' : celebrar ? 'Cuando un módulo detecte algo de tu departamento, saldrá aquí con su plazo.' : 'Cambia de chip para ver el resto.' }));
      masBoton.replaceChildren();
      S.pintarBarra();
      return;
    }
    caja.replaceChildren(...filas.slice(0, S.visibles).map(a => { const t = tarjeta(a); t.setAttribute('role', 'listitem'); return t; }));
    masBoton.replaceChildren(...[filas.length > S.visibles ? h('button', { type: 'button', class: 'bt', on: { click: () => { S.visibles += 30; pintar(); } } }, icono('mas', { clase: 's' }), `Ver ${Math.min(30, filas.length - S.visibles)} más de ${filas.length}`) : null].filter(Boolean));
    S.pintarBarra();
  };
  buscar.addEventListener('input', pintar);
  pintarFiltros();
  LISTA = () => { pintarFiltros(); pintar(); };
  pintar();
  zona.append(filtros, caja, masBoton, barra);
}

// --------------------------------------------------------------------- por departamento
function pintarDepartamentos(zona, irALista) {
  const D = S.D;
  const filas = Object.entries(D.departamentos || {}).map(([id, d]) => {
    const deDep = (D.alertas || []).filter(a => a.departamento === id);
    return { id, ...d, n: cuenta(deDep, 'en_vista'), urg: cuenta(deDep, 'urgentes_en_vista'),
      pas: deDep.filter(a => cumple(a, ['plazo_pasado'])).length, esc: cuenta(deDep, 'escaladas_en_vista'),
      pos: deDep.filter(a => cumple(a, ['pospuesta'])).length,
      tengo: deDep.filter(a => estadoDe(a).estado === 'lo_tengo').length, total: deDep.length };
  }).filter(f => f.total || S.D.alcance === 'todas');
  zona.append(panel({ titulo: 'Cola por departamento', icono: 'eq', sub: 'Abiertas, críticas, con el plazo pasado, escaladas y pospuestas. Pulsa un departamento para ver sus alertas.' },
    tablaApilable({
      filas,
      columnas: [
        { clave: 'nombre', titulo: 'Departamento', principal: true, celda: f => h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, h('span', { class: `ico-c s ${f.urg ? 'rojo' : f.n ? 'ambar' : 'verde'}` }, icono(f.icono, { clase: 's' })), f.nombre) },
        { clave: 'jefe', titulo: 'Jefe (escalado)', celda: f => h('span', { class: 'pila', style: { gap: 'var(--s-1)' } }, h('span', { title: limpiaTexto(f.jefe_origen) }, f.jefe), f.pendiente ? chipEstado('ambar', 'Pendiente de Tomás') : null) },
        { clave: 'n', titulo: 'Abiertas', num: true },
        { clave: 'urg', titulo: 'Críticas', num: true, celda: f => (f.urg ? chipEstado('rojo', fmt.num(f.urg)) : '0') },
        { clave: 'pas', titulo: 'Plazo pasado', num: true, celda: f => (f.pas ? chipEstado('rojo', fmt.num(f.pas)) : '0') },
        { clave: 'esc', titulo: 'Escaladas', num: true },
        { clave: 'pos', titulo: 'Pospuestas', num: true },
        { clave: 'tengo', titulo: 'Con «Lo tengo»', num: true },
      ],
      alPulsar: f => irALista(f.id),
      etiquetaFila: f => `${f.nombre}: ${fmt.plural(f.n, 'abierta')}, ${fmt.plural(f.urg, 'crítica')}. Ver sus alertas`,
      vacio: { titulo: 'Sin departamentos', texto: 'No hay alertas de ningún departamento para ti.' },
    })));
  const nm = (D.no_medible || []).filter(x => D.alcance === 'todas' || Object.keys(D.departamentos || {}).includes(x.dep));
  if (nm.length) {
    zona.append(panel({ titulo: 'Todavía no se mide', icono: 'info', sub: 'Alertas pedidas que no tienen dato fiable hoy. No se inventan: sale aquí qué falta y quién lo desbloquea.' },
      h('ul', { class: 'lista-i' }, nm.map(x => h('li', {}, h('span', { class: 'ico-c s gris' }, icono('vacio', { clase: 's' })),
        h('span', { class: 't' }, h('b', {}, `${D.departamentos?.[x.dep]?.nombre || x.dep} · ${x.que}. `), x.porque), h('span', { class: 'x' }, `Lo desbloquea: ${x.quien}`))))));
  }
}

// --------------------------------------------------------------------- resumen del día
function pintarResumen(zona) {
  const ctx = S.ctx; const D = S.D; const rd = D.resumen_diario || {};
  const texto = rd.texto || 'Sin resumen todavía.';
  zona.append(panel({ titulo: 'Tu resumen de hoy', icono: 'campana', sub: 'El texto que te llegará como notificación cada mañana. Hoy se copia a mano: el envío (escritorio, móvil o correo) llega con el servidor.',
    acciones: h('button', { type: 'button', class: 'bt', on: { click: () => copiar(texto, 'Resumen copiado') } }, icono('copy', { clase: 's' }), 'Copiar') },
  h('div', { style: { padding: 'var(--s-4) var(--relleno)' } }, h('pre', { style: { whiteSpace: 'pre-wrap', background: 'var(--card-2)', border: 'var(--borde)', borderRadius: 'var(--r-m)', padding: 'var(--s-4)', font: 'var(--t-cuerpo)', margin: '0', overflowWrap: 'anywhere' } }, texto))));
  if (D.equipo_resumen?.length) {
    const filas = D.equipo_resumen.filter(x => x.n !== undefined).sort((a, b) => (b.urgentes || 0) - (a.urgentes || 0) || (b.n || 0) - (a.n || 0));
    zona.append(panel({ titulo: 'Resumen de cada persona', icono: 'eq', sub: 'Lo que recibirá cada uno mañana a primera hora (solo lo ven Mili y Tomás).' },
      tablaApilable({ filas, porPagina: 0,
        columnas: [
          { clave: 'persona_id', titulo: 'Persona', principal: true, celda: f => h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(corto(ctx, f.persona_id))), corto(ctx, f.persona_id)) },
          { clave: 'n', titulo: 'Abiertas', num: true },
          { clave: 'urgentes', titulo: 'Críticas', num: true, celda: f => (f.urgentes ? chipEstado('rojo', fmt.num(f.urgentes)) : '0') },
          { clave: 'pasadas', titulo: 'Plazo pasado', num: true, celda: f => (f.pasadas ? chipEstado('rojo', fmt.num(f.pasadas)) : '0') },
          { clave: 'titulo', titulo: 'Notificación', celda: f => h('span', { class: 'sub' }, f.titulo) },
        ] })));
  }
  if (D.proximos_rrhh?.length) {
    zona.append(panel({ titulo: 'Próximos cumpleaños y aniversarios', icono: 'star', sub: 'Aviso a Cecilia y a Tomás 7 días antes y el mismo día.' },
      h('ul', { class: 'lista-i' }, D.proximos_rrhh.slice(0, 8).map(x => h('li', {},
        h('span', { class: `ico-c s ${x.dias <= 7 ? 'ambar' : 'gris'}` }, icono(x.tipo === 'cumpleaños' ? 'star' : 'flag', { clase: 's' })),
        h('span', { class: 't' }, `${x.persona} · ${x.tipo === 'cumpleaños' ? 'cumpleaños' : `${x.anos} ${x.anos === 1 ? 'año' : 'años'} en RO`}`),
        h('span', { class: 'x' }, x.dias === 0 ? 'hoy' : x.dias === 1 ? 'mañana' : `${fDiaRO(x.fecha)} · en ${x.dias} días`))))));
  }
}

// --------------------------------------------------------------------- reglas
function pintarReglas(zona) {
  const D = S.D;
  zona.append(avisoParcial(`${D.escalado} Estados: nueva, vista, «Lo tengo» (para el escalado), pospuesta (vuelve sola en su fecha y, mientras, no cuenta ni escala), resuelta (se comprueba con el dato siguiente: si sigue, se reabre sola) y no aplica (siempre con motivo). Todo queda en el rastro.`, { tipo: 'info', titulo: 'Cómo funciona.' }));
  const defs = Object.entries(D.definiciones || {});
  if (defs.length) {
    zona.append(panel({ titulo: 'Cómo se cuentan las cifras', icono: 'check', sub: 'Una sola definición para la cabecera, las tarjetas, los chips y Mi día. Sale del motor de alertas, no de cada pantalla.' },
      h('ul', { class: 'lista-i' }, defs.map(([k, d]) => h('li', {}, h('span', { class: 'ico-c s' }, icono('info', { clase: 's' })), h('span', { class: 't' }, d.texto || k))))));
  }
  zona.append(panel({ titulo: 'Reglas, plazos y de dónde sale cada alerta', icono: 'libro', sub: 'El motor no calcula nada: copia la regla del módulo que ya la mide. El dueño es quien ocupa esa silla del cliente; si no hay nadie, el jefe del departamento.' },
    tablaApilable({ filas: D.reglas || [], porPagina: 0,
      columnas: [
        { clave: 'departamento', titulo: 'Departamento', principal: true },
        { clave: 'titulo', titulo: 'Alerta', celda: r => h('b', {}, r.titulo) },
        { clave: 'regla', titulo: 'Cuándo salta', celda: r => h('span', { class: 'sub' }, limpiaTexto(r.regla)) },
        { clave: 'plazo_h', titulo: 'Plazo', celda: r => (r.plazo_h ? (r.plazo_h < 48 ? `${r.plazo_h} h` : `${Math.round(r.plazo_h / 24)} días`) : (r.dep === 'direccion' ? 'el del reloj' : 'el día')) },
        { clave: 'gravedad', titulo: 'Gravedad', celda: r => chipEstado(GRAV[r.gravedad].color, GRAV[r.gravedad].texto) },
        { clave: 'fuente', titulo: 'Sale de', celda: r => h('span', { class: 'sub' }, r.fuente) },
      ] })));
}

// --------------------------------------------------------------------- comprobación (Mili y Tomás)
function pintarComprobacion(zona) {
  const ctx = S.ctx; const D = S.D;
  const ok = (D.coherencia || []).filter(x => x.ok).length;
  zona.append(panel({ titulo: 'Las cifras de alertas cuadran con cada módulo', icono: 'check', sub: `${ok} de ${(D.coherencia || []).length} cifras iguales a las de su pantalla. Si una no cuadra, el motor se ha comido o duplicado algo.` },
    tablaApilable({ filas: D.coherencia || [], porPagina: 0,
      columnas: [
        { clave: 'que', titulo: 'Qué', principal: true },
        { clave: 'modulo', titulo: 'Pantalla' },
        { clave: 'cifra_modulo', titulo: 'En la pantalla', num: true },
        { clave: 'cifra_alertas', titulo: 'En alertas', num: true },
        { clave: 'ok', titulo: '¿Cuadra?', celda: x => chipEstado(x.ok ? 'verde' : 'rojo', x.ok ? 'Cuadra' : 'No cuadra') },
        { clave: 'nota', titulo: 'Nota', celda: x => h('span', { class: 'sub' }, x.nota || '') },
      ] })));
  if ((D.rechazadas || []).length) {
    zona.append(panel({ titulo: 'Intentos que no se aplicaron', icono: 'candado', sub: 'Nadie pospone ni despacha en lote alertas ajenas, y «posponer» va de mañana a un mes. Quedan aquí y en el rastro.' },
      h('ul', { class: 'lista-i' }, D.rechazadas.slice(-15).reverse().map(x => h('li', {},
        h('span', { class: 'ico-c s ambar' }, icono('candado', { clase: 's' })),
        h('span', { class: 't' }, `${corto(ctx, x.quien)} · ${x.tipo} · ${limpiaTexto(x.motivo)}`), h('span', { class: 'x' }, fDiaHoraRO(x.hora)))))));
  }
  zona.append(panel({ titulo: 'Fuentes leídas', icono: 'base', sub: 'Cada fuente con su hora. Las que faltan salen en gris con el motivo.' },
    h('ul', { class: 'lista-i' }, (D.fuentes || []).map(f => h('li', {},
      h('span', { class: `ico-c s ${f.leido ? 'verde' : 'gris'}` }, icono(f.leido ? 'ok' : 'plug', { clase: 's' })),
      h('span', { class: 't' }, h('b', {}, f.modulo), ` · ${fmt.plural(f.alertas || 0, 'alerta')}`, f.nota ? h('span', { class: 'sub' }, ` · ${limpiaTexto(f.nota)}`) : null),
      h('span', { class: 'x' }, f.generado ? frescura({ fuente: 'dato', fecha: f.generado }) : 'sin leer'))))));
  if ((D.cerradas || []).length) {
    zona.append(panel({ titulo: 'Cerradas en los últimos 14 días', icono: 'hist', sub: '«Comprobada» = alguien la marcó resuelta y el dato siguiente lo confirma. «Se fue sola» = el dato dejó de verla sin que nadie la marcara.' },
      h('ul', { class: 'lista-i' }, D.cerradas.slice(-15).reverse().map(c => h('li', {},
        h('span', { class: `ico-c s ${c.como === 'comprobada' ? 'verde' : 'gris'}` }, icono('ok', { clase: 's' })),
        h('span', { class: 't' }, limpiaTexto(c.motivo || c.id)), h('span', { class: 'x' }, `${c.como === 'comprobada' ? 'Comprobada' : 'Se fue sola'} · ${fDiaHoraRO(c.cerrada)}`))))));
  }
}

// --------------------------------------------------------------------- render
async function render(cont, ctx) {
    vigilarCortes(cont);
  document.getElementById('al-estilos')?.remove();   // hoja de antes de la guía 30
  await cargar(ctx);
  if (!S.D) {
    ctx.titulo('Alertas del departamento', 'Sin datos de alertas');
    cont.append(vacio({ icono: 'plug', borde: true, titulo: 'Todavía no hay alertas para ti',
      texto: `No ha llegado tu fichero de alertas (${limpiaTexto(S.error || 'sin respuesta')}). Se genera con la recarga de datos.`, quien: 'Mili' }));
    return;
  }
  const D = S.D;
  const todas = D.alertas || [];
  const nombresDep = (D.jefe_de || []).map(d => D.departamentos?.[d]?.nombre).filter(Boolean);

  cont.append(h('p', { class: 'fila sub' }, icono(D.alcance === 'todas' ? 'res' : D.alcance === 'departamento' ? 'eq' : 'persona', { clase: 's' }),
    h('span', { style: { flex: '1 1 220px', minWidth: '0' } }, D.alcance === 'todas' ? 'Ves las alertas de toda la agencia (dirección y operaciones).'
      : D.alcance === 'departamento' ? `Ves las tuyas y las de ${nombresDep.length ? nombresDep.join(', ') : 'tu departamento'}${nombresDep.length ? ' (eres quien recibe el escalado)' : ''}.`
        : 'Ves las alertas de las que eres dueño. Si pasa el plazo sin «Lo tengo», sube a tu jefe.'),
    frescura({ fuente: 'Alertas', fecha: D.generado })));

  // ---- 1 · lo primero hoy + cifras (se repintan tras cada marca: mismas definiciones que chips y Mi día) ----
  const arriba = h('div', { style: PILA(4) });
  cont.append(arriba);
  let irA = null;
  const pintarArriba = () => {
    S.ahora = new Date();
    const K = Object.fromEntries(Object.keys(D.contadores_def || {}).map(k => [k, cuenta(todas, k)]));
    const mias = de(todas, 'mias');
    const escaladasAMi = de(todas, 'escaladas_a_mi');
    ctx.titulo('Alertas del departamento', `${fmt.plural(K.mias, 'alerta tuya abierta', 'alertas tuyas abiertas')}${K.urgentes ? ` · ${fmt.plural(K.urgentes, 'crítica')}` : ''}${K.plazo_pasado ? ` · ${fmt.num(K.plazo_pasado)} con el plazo pasado` : ''}${D.alcance !== 'mias' ? ` · ${fmt.num(K.en_vista)} en tu vista` : ''}. Dato de las ${String(D.generado).slice(11)}.`);
    // Ronda U (50 #1, molde): «Lo mío» de Mi día ya trae lo tuyo con su verbo; aquí la pantalla es la LISTA con sus filtros.
    // Las cuatro tarjetas (≈ 250 px) y «Lo primero hoy» (que repetía Lo mío) pasan a una franja de cifras que SON los filtros
    // de la lista (mismas definiciones; data-contadores lo sigue leyendo pruebas_coherencia).
    const franja = franjaCifras([
      { etiqueta: 'Mías abiertas', valor: K.mias, estado: K.urgentes ? 'rojo' : '', alPulsar: () => irA?.('mias', '', 'abiertas'),
        titulo: `${K.urgentes ? fmt.plural(K.urgentes, 'crítica') : 'Ninguna crítica'}${K.pospuestas ? ` · ${fmt.num(K.pospuestas)} pospuestas aparte` : ''}` },
      { etiqueta: 'Plazo pasado', valor: K.plazo_pasado, estado: K.plazo_pasado ? 'rojo' : '', alPulsar: () => irA?.('mias', '', 'pasadas'), titulo: 'De las tuyas. Sin «Lo tengo», suben al siguiente' },
      { etiqueta: 'Escaladas a ti', valor: K.escaladas_a_mi, estado: K.escaladas_a_mi ? 'rojo' : '', alPulsar: () => irA?.('mias', '', 'escaladas'), titulo: 'Ya cuentan en «mías»: pasaron el plazo de su dueño' },
      D.alcance !== 'mias'
        ? { etiqueta: D.alcance === 'todas' ? 'Abiertas en la agencia' : 'En tu departamento', valor: K.en_vista, alPulsar: () => irA?.('dep', '', 'abiertas'), titulo: `${fmt.plural(K.urgentes_en_vista, 'crítica')} · ${fmt.plural(K.escaladas_en_vista, 'escalada')}` }
        : { etiqueta: 'Pospuestas', valor: K.pospuestas, alPulsar: () => irA?.('mias', '', 'pospuestas'), titulo: 'Vuelven solas en su fecha; mientras, no cuentan ni escalan' },
    ], { etiqueta: 'Cifras de alertas (filtran la lista)' });
    franja.dataset.contadores = JSON.stringify(K);
    void mias; void escaladasAMi;
    arriba.replaceChildren(franja);
  };
  pintarArriba();

  // ---- 2 · pestañas: lista · departamentos · resumen · reglas · comprobación ----
  const pts = [
    { id: 'lista', texto: 'Alertas', icono: 'campana', cuenta: cuenta(todas, D.alcance === 'mias' ? 'mias' : 'en_vista'), cuentaEstado: cuenta(todas, 'urgentes') ? 'rojo' : null },
    { id: 'deps', texto: 'Por departamento', icono: 'eq' },
    { id: 'resumen', texto: 'Resumen del día', icono: 'mail' },
    { id: 'reglas', texto: 'Reglas y plazos', icono: 'libro' },
  ];
  if (D.coherencia) pts.push({ id: 'comprobacion', texto: 'Comprobación', icono: 'check', cuenta: D.coherencia.filter(x => !x.ok).length, cuentaEstado: 'rojo' });
  let pest = null;
  const pintarPestana = (id, zona) => {
    if (id === 'lista') pintarLista(zona);
    else if (id === 'deps') pintarDepartamentos(zona, dep => { pest.elegir('lista'); S.elegirDep?.(dep); });
    else if (id === 'resumen') pintarResumen(zona);
    else if (id === 'reglas') pintarReglas(zona);
    else pintarComprobacion(zona);
  };
  pest = pestanas({ pestanas: pts, clave: `${ID}.pestana`, activa: 'lista', pintar: pintarPestana, etiqueta: 'Secciones de alertas' });
  const yo = ctx.persona.id;
  irA = (quien, dep, est) => {
    try { sessionStorage.setItem(`ro.chips.${ID}.estado.${yo}`, JSON.stringify([est])); sessionStorage.setItem(`ro.chips.${ID}.dep.${yo}`, JSON.stringify([dep])); sessionStorage.setItem(`ro.chips.${ID}.quien.${yo}`, JSON.stringify([quien])); } catch { /* sin almacenamiento */ }
    S.quien = quien;
    if (pest.activa() === 'lista') { const z = pest.querySelector('.pestana-panel'); z.replaceChildren(); pintarLista(z); } else pest.elegir('lista');
    pest.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  // Tras cada marca (una o en lote): cifras de arriba, chips y lista, con la misma definición.
  S.refrescar = () => { pintarArriba(); if (pest.activa() === 'lista') LISTA?.(); };
  const secPest = h('section', { class: 'panel' }, pest);
  cont.append(secPest);
  consejoCompacto(cont, secPest);   // el consejo de la IA, plegado y debajo de la lista
  // ---- 3 · avisos de horas (regla de Tomás, 2-oct): se ven, pero no cuentan como alerta, no vencen y no escalan ----
  const avisos = D.avisos || [];
  if (avisos.length) {
    const propios = avisos.filter(a => a.dueno_id === ctx.persona.id);
    const verAvisos = (propios.length ? [...propios, ...avisos.filter(a => a.dueno_id !== ctx.persona.id)] : avisos).slice(0, 6);
    cont.append(panel({ titulo: 'Avisos de horas', icono: 'clock', sub: `${fmt.plural(avisos.length, 'aviso', 'avisos')}. Las horas imputadas son solo aviso: sin plazo, sin rojo y sin escalado.` },
      listaLoPrimero(verAvisos.map(a => ({
        estado: 'gris', icono: 'clock', motivo: limpiaTexto(a.motivo),
        detalle: a.dueno_id === ctx.persona.id ? 'Aviso para ti · sin plazo ni escalado' : `Aviso · ${corto(ctx, a.dueno_id)}`,
        botones: [a.abrir?.[0] && a.dueno_id === ctx.persona.id ? h('a', { class: 'bt mini', href: a.abrir[0].url, target: '_blank', rel: 'noopener', on: { click: () => ctx.rastro({ accion: 'abrir', objeto: a.id, detalle: a.abrir[0].texto }) } }, icono('check', { clase: 's' }), a.abrir[0].texto) : null,
          a.dueno_id !== ctx.persona.id && ctx.veModulo('personas') ? h('a', { class: 'bt mini', href: '#/personas' }, icono('flecha', { clase: 's' }), 'Ver en Personas') : null].filter(Boolean),
      })), { subir: false }),
      avisos.length > verAvisos.length ? h('p', { class: 'fila sub' }, `…y ${fmt.num(avisos.length - verAvisos.length)} más en Personas › «Quién no imputa».`) : null));
  }
  cont.append(h('p', { class: 'fila sub', style: { flexWrap: 'nowrap', alignItems: 'flex-start' } }, icono('info', { clase: 's' }),
    'Las alertas no se calculan aquí: vienen de cada pantalla con su misma regla, así que las cifras son las mismas. Los botones dejan la marca en la app (con rastro); nada se escribe en Desk, GoHighLevel, Meta ni ClickUp.'));
}

export default {
  id: ID,
  titulo: 'Alertas del departamento',
  grupo: 'Hoy',
  puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', proyectos: 'todo', rrhh: 'todo', administracion: 'todo', tecnico_altas: 'todo', jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo', setters: null },
  render,
};
