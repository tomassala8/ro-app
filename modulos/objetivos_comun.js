// modulos/objetivos_comun.js · A4 (2-oct) · la lectura ÚNICA del objetivo del cliente y del semáforo del lunes en el navegador.
//
// Dónde vive el dato: la tabla «acciones» de la base de la app (modo simulación, con rastro). Tipos:
//   · «objetivo_alta»    → objetivo del cliente (el mismo tipo que ya guardaba Clientes nuevos; la ficha escribe el mismo).
//   · «semaforo_semanal» → semáforo del lunes (verde | ambar | rojo) + una línea de nota.
// Cómo se lee (siempre recortado por el servidor: coste_* e inversion_* solo a quien ve la inversión del cliente):
//   1. data/objetivos/objetivos.json (fuentes_objetivos/objetivos.py, en cada vuelta de la tubería): lo guardado hasta entonces;
//   2. /api/acciones?modulo=ficha y ?modulo=clientes-nuevos (en vivo): lo guardado después.
// La regla (reducir) es la MISMA que fuentes_objetivos/objetivos.py, que es la que usan Captación y Mi día (captacion.json).
// Nadie más filtra «objetivo_alta» por su cuenta: pruebas_coherencia.py lo comprueba.

import { REGLAS } from '../permisos.js';

export const TIPO_OBJETIVO = 'objetivo_alta';
export const TIPO_SEMAFORO = 'semaforo_semanal';
export const CAMPOS = ['leads_mes', 'coste_lead', 'coste_cita', 'ventas_mes', 'citas_mes', 'inversion_mes'];
const ALIAS = { presupuesto: 'inversion_mes' };
const PRINCIPALES = ['leads_mes', 'coste_lead', 'coste_cita', 'ventas_mes'];
export const COLORES = ['verde', 'ambar', 'rojo'];
const MODULOS = ['ficha', 'clientes-nuevos'];
const SEMANAS_HISTORIAL = 12;
/** Importe escrito en un texto (misma regla que objetivos.py): la nota del semáforo va sin importes. */
export const RE_IMPORTE = /\d[\d.,]*\s*(?:€|euros?|EUR\b)|€\s*\d[\d.,]*/g;

const DIAS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
/** «creada» de la base es UTC sin zona → hora de Madrid y lunes de esa semana. */
export function horaMadrid(creada) {
  const d = new Date(`${String(creada || '').replace(' ', 'T').slice(0, 19)}Z`);
  if (Number.isNaN(d.getTime())) return null;
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23', weekday: 'short' }).formatToParts(d).map(x => [x.type, x.value]));
  const fecha = `${p.year}-${p.month}-${p.day}`;
  const lunes = new Date(`${fecha}T12:00:00Z`);
  lunes.setUTCDate(lunes.getUTCDate() - Math.max(0, DIAS.indexOf(p.weekday)));
  return { cuando: `${fecha} ${p.hour}:${p.minute}`, semana: lunes.toISOString().slice(0, 10) };
}
/** Lunes de hoy (hora de Madrid). */
export const lunesDeHoy = () => horaMadrid(new Date().toISOString().slice(0, 19).replace('T', ' '))?.semana || null;

function num(v) {
  if (v === null || v === undefined || v === '') return null;
  const x = Number(v);
  if (!Number.isFinite(x) || x < 0 || x > 1e7) return null;
  return Number.isInteger(x) ? x : Math.round(x * 100) / 100;
}

/** Fila de «acciones» (de /api/acciones) → fila común (la misma forma que las de objetivos.json). */
export function normalizar(a) {
  let vp = a.vista_previa;
  if (typeof vp === 'string') { try { vp = JSON.parse(vp); } catch { vp = {}; } }
  if (!vp || typeof vp !== 'object') vp = {};
  const h = horaMadrid(a.creada);
  const out = { id: a.id, tipo: a.tipo, cliente_id: a.cliente_id, quien: a.quien, modulo: a.modulo, cuando: h?.cuando || null, semana: h?.semana || null };
  if (a.tipo === TIPO_OBJETIVO) {
    out.campos = {};
    for (const [k0, v] of Object.entries(vp)) { const k = ALIAS[k0] || k0; if (CAMPOS.includes(k)) out.campos[k] = num(v); }
  } else {
    const color = String(vp.color || '').trim().toLowerCase().replace('á', 'a');
    out.color = COLORES.includes(color) ? color : null;
    out.nota = String(vp.nota || '').replace(RE_IMPORTE, '').replace(/\s{2,}/g, ' ').trim().replace(/\n/g, ' ').slice(0, 200);
  }
  return out;
}

/** Filas comunes → Map(cliente_id → { objetivo, historial_objetivo, semaforo, semanas }). Igual que reducir() de objetivos.py. */
export function reducir(filas) {
  const out = new Map();
  for (const f of [...filas].sort((a, b) => a.id - b.id)) {
    if (!out.has(f.cliente_id)) out.set(f.cliente_id, { cliente_id: f.cliente_id, objetivo: null, historial_objetivo: [], semaforo: null, semanas: [] });
    const c = out.get(f.cliente_id);
    if (f.tipo === TIPO_OBJETIVO) {
      const prev = Object.fromEntries(Object.entries(c.objetivo || {}).filter(([k]) => CAMPOS.includes(k)));
      const nuevo = { ...prev, ...(f.campos || {}) };
      c.objetivo = { ...Object.fromEntries(CAMPOS.map(k => [k, nuevo[k] ?? null])), cargado: PRINCIPALES.some(k => nuevo[k] !== null && nuevo[k] !== undefined),
        quien: f.quien, cuando: f.cuando, desde: f.modulo, accion_id: f.id };
      c.historial_objetivo.unshift({ accion_id: f.id, quien: f.quien, cuando: f.cuando, desde: f.modulo, campos: f.campos || {} });
    } else if (f.color) {
      const s = { color: f.color, nota: f.nota || '', quien: f.quien, cuando: f.cuando, semana: f.semana, accion_id: f.id };
      c.semaforo = s;
      c.semanas = [s, ...c.semanas.filter(x => x.semana !== s.semana)];
    }
  }
  for (const c of out.values()) {
    c.historial_objetivo = c.historial_objetivo.slice(0, 10);
    c.semanas = c.semanas.sort((a, b) => String(b.semana || '').localeCompare(String(a.semana || ''))).slice(0, SEMANAS_HISTORIAL);
  }
  return out;
}

/** R15a: ¿le da el servidor «objetivos/objetivos» a esta persona? Misma regla que servir.py (reglas_permisos.json →
 *  datos_de_modulo): ver alguna de sus pantallas y no tener SOLO puestos excluidos (Sofía, administración). Así no se pide
 *  para recibir un 403 (el servidor sigue siendo quien decide). */
export function veObjetivos(ctx) {
  const conf = REGLAS.datos_de_modulo?.['objetivos/objetivos'];
  if (!conf) return true;
  const mods = Array.isArray(conf) ? conf : conf.modulos || MODULOS;
  if (ctx.veModulo && !mods.some(m => ctx.veModulo(m))) return false;
  const ex = Array.isArray(conf) ? [] : conf.excluir_puestos || [];
  const pu = ctx.persona?.puestos || [];
  return !(ex.length && pu.length && pu.every(p => ex.includes(p)));
}

/** Todo lo que la persona puede ver: el fichero de la última vuelta + lo guardado después (en vivo). */
export async function cargarObjetivos(ctx) {
  const filas = new Map();
  if (!veObjetivos(ctx)) return reducir([]);   // R15a: Sofía no ve objetivos → ni se piden (antes, 403 en su consola)
  try {
    const d = await ctx.datosModulo('objetivos/objetivos');
    for (const c of d?.clientes || []) for (const f of c.filas || []) filas.set(f.id, f);
  } catch { /* sin el fichero: solo lo de en vivo */ }
  if (ctx.servidor) {
    await Promise.all(MODULOS.filter(m => !ctx.veModulo || ctx.veModulo(m)).map(async m => {
      try {
        const r = await ctx.api(`acciones?modulo=${m}`);
        for (const a of r?.acciones || []) if ((a.tipo === TIPO_OBJETIVO || a.tipo === TIPO_SEMAFORO) && a.cliente_id && !filas.has(a.id)) filas.set(a.id, normalizar(a));
      } catch { /* esa pantalla no es suya */ }
    }));
  }
  return reducir([...filas.values()]);
}

/** ¿Puede cargar el objetivo y el semáforo de este cliente? (su account, operaciones y dirección; nunca en «ver como»). */
export const puedeEditar = (ctx, clienteId, que = 'semaforo') => !ctx.soloLectura && ctx.ver({ tipo: que === 'objetivo' ? 'editar_objetivo_alta' : 'editar_objetivo_cliente',
  cliente_id: clienteId, cliente_nuevo: !!(ctx.verdad?.(clienteId)?.nuevo ?? ctx.clientes?.find(c => c.id === clienteId)?.nuevo) }).ok;
