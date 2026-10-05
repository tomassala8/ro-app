// permisos.js · las tres llaves del 00: PUESTO (qué pantallas) × CARTERA (qué clientes) × SENSIBILIDAD (qué datos).
//
// v2 (E0, 2-oct): las reglas ya no están escritas aquí, sino en reglas_permisos.json, que leen a la vez
// este fichero (navegador y, con W1, el Worker de Cloudflare) y permisos.py (servir.py). Este fichero
// solo INTERPRETA la matriz. La API pública no cambia: PUESTOS, PUESTO, nivelModulo, cartera, ambito,
// ver, enmascarar. Nuevo: REGLAS y carteraPorSilla.
//
// ⚠️ Con servir.py los datos ya llegan recortados del servidor; ver() en el navegador solo decide
// qué pintar. Esconder en pantalla no protege nada: lo que protege es que el servidor no lo mande.

import REGLAS from './reglas_permisos.json' with { type: 'json' };

export { REGLAS };

/** Los 21 puestos del 00 §1. ambito = qué clientes ve con detalle. */
export const PUESTOS = REGLAS.puestos;
export const PUESTO = Object.fromEntries(PUESTOS.map(p => [p.id, p]));

const tiene = (persona, ids) => (persona.puestos || []).some(p => ids.includes(p));
const hoyISO = () => new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());

/** Niveles de ver un módulo: 'todo' (●), 'suyo' (◐), 'resumen' (○). El más alto de sus puestos. */
const RANGO = { resumen: 1, suyo: 2, todo: 3 };
export function nivelModulo(persona, modulo) {
  const mapa = modulo.puestos_que_lo_ven || {};
  const fuera = (REGLAS.modulos_sin_puesto || {})[modulo.id] || [];   // R16c: la regla manda (setters fuera de «En rojo»)
  let mejor = null;
  for (const p of persona.puestos) {
    if (fuera.includes(p)) continue;
    // Una clave propia del puesto manda sobre '*'; null = excluido aunque haya '*'.
    const n = p in mapa ? mapa[p] : mapa['*'];
    if (n && (!mejor || RANGO[n] > RANGO[mejor])) mejor = n;
  }
  return mejor;
}

/** Sillas de la tabla asignaciones que dan cartera a la persona. */
function sillasDe(persona) {
  return new Set(persona.puestos.flatMap(p => REGLAS.sillas_de_puesto[p] || []));
}

function vigente(a, hoy) {
  if (a.desde && a.desde > hoy) return false;
  if (a.hasta && a.hasta < hoy) return false;
  return true;
}

/**
 * carteraPorSilla(persona, asignaciones) → { account: Set, trafficker: Set, … }
 * Asignaciones vigentes de la persona en las sillas de sus puestos, más suplencias vigentes
 * (una suplencia es una asignación con suplencia: true y fecha «hasta» obligatoria; caduca sola).
 * Si la persona no tiene ninguna silla (dirección, operaciones…), cuenta todas sus filas.
 */
// Contratos explícitos. Silla/Metricool no confirman una venta; desconocido queda fuera.
const SERVICIOS_SILLA = {
  seo: ['seo'], trafficker: ['publicidad'], crm: ['crm_ghl'], ghl: ['crm_ghl'],
  web: ['web', 'mantenimiento'], redes: ['redes', 'social_media'], outreach: ['outreach'],
};
const SERVICIOS_JEFATURA = {
  jefa_seo: ['seo'], jefa_publicidad: ['publicidad'], jefa_crm: ['crm_ghl', 'outreach'],
};
export function servicioContratado(cliente, claves) {
  return claves.some(k => cliente.servicios?.[k] === 'sí');
}

export function carteraPorSilla(persona, asignaciones, hoy = hoyISO(), clientes = null) {
  const sillas = sillasDe(persona);
  const out = {};
  for (const a of asignaciones) {
    if (a.persona_id !== persona.id || !vigente(a, hoy)) continue;
    if (a.suplencia && !a.hasta) continue;               // sin fecha de fin no hay suplencia
    if (a.silla && sillas.size && !sillas.has(a.silla) && !a.suplencia) continue;
    (out[a.silla || 'sin_silla'] ||= new Set()).add(a.cliente_id);
  }
  // Tomás 3-oct («sillas_de_equipo»): web y redes son equipos transversales: con la silla por su puesto, sus clientes
  // de esa silla son todos los que la tienen asignada a alguien (el servicio activo). Igual que permisos.py.
  for (const silla of REGLAS.sillas_de_equipo || []) {
    if (!sillas.has(silla)) continue;
    for (const a of asignaciones) {
      if (a.silla !== silla || !vigente(a, hoy) || (a.suplencia && !a.hasta)) continue;
      (out[silla] ||= new Set()).add(a.cliente_id);
    }
  }
  if (clientes !== null) {
    const porId = Object.fromEntries(clientes.map(c => [c.id, c]));
    for (const [silla, ids] of Object.entries(out)) {
      const claves = SERVICIOS_SILLA[silla];
      if (claves) out[silla] = new Set([...ids].filter(cid => porId[cid] && servicioContratado(porId[cid], claves)));
    }
    for (const silla of REGLAS.sillas_de_equipo || []) {
      if (sillas.has(silla) && SERVICIOS_SILLA[silla]) out[silla] = new Set(clientes.filter(c => servicioContratado(c, SERVICIOS_SILLA[silla])).map(c => c.id));
    }
    for (const [puesto, claves] of Object.entries(SERVICIOS_JEFATURA)) {
      if (persona.puestos.includes(puesto)) out['servicio_' + puesto] = new Set(clientes.filter(c => servicioContratado(c, claves)).map(c => c.id));
    }
  }
  return out;
}

/** Cartera de una persona en una fecha: todos los clientes de carteraPorSilla juntos. */
export function cartera(persona, asignaciones, hoy = hoyISO(), clientes = null) {
  const ids = new Set();
  for (const s of Object.values(carteraPorSilla(persona, asignaciones, hoy, clientes))) for (const c of s) ids.add(c);
  return ids;
}

/** Ámbito de clientes más amplio de la persona. */
export function ambito(persona) {
  const orden = REGLAS.orden_ambitos;
  return persona.puestos.map(p => PUESTO[p]?.ambito || 'ninguno')
    .reduce((a, b) => (orden.indexOf(b) > orden.indexOf(a) ? b : a), 'ninguno');
}

/** Tomás 3-oct: ¿solo recibe los clientes de su cartera, en todas partes? (accounts sin ámbito mayor). Igual que permisos.py. */
export function soloSuCartera(persona) {
  if (ambito(persona) === 'todos') return false;
  return tiene(persona, REGLAS.solo_su_cartera?.puestos || [])
    || tiene(persona, Object.keys(SERVICIOS_JEFATURA))
    || [...sillasDe(persona)].some(s => s in SERVICIOS_SILLA);
}

/** ¿Es `persona` jefa de la persona `objetivo`? Por el campo jefe o por la disciplina. */
function esJefe(persona, objetivo) {
  if (!objetivo) return false;
  if (objetivo.jefe === persona.id) return true;
  const subordinados = persona.puestos.flatMap(p => REGLAS.jefe_de_puesto[p] || []);
  return (objetivo.puestos || []).some(p => subordinados.includes(p));
}

function cumple(caso, persona, dato, cp) {
  if (caso.identidades && !caso.identidades.includes(persona.id)) return false;
  if (caso.puestos && !tiene(persona, caso.puestos)) return false;
  if (caso.ambito && !caso.ambito.includes(ambito(persona))) return false;
  if (caso.cartera) {
    if (!dato.cliente_id) return false;
    if (caso.cartera === true) { if (!cp.carteraIds?.has(dato.cliente_id)) return false; }
    else {
      const set = cp.carteraPorSilla ? cp.carteraPorSilla[caso.cartera] : cp.carteraIds;
      if (!set?.has(dato.cliente_id)) return false;
    }
  }
  if (caso.sin_cliente && dato.cliente_id) return false;
  if (caso.propio && dato.persona_id !== persona.id) return false;
  if (caso.jefe && !esJefe(persona, (cp.personas || []).find(p => p.id === dato.persona_id))) return false;
  if (caso.participante && !(dato.participantes || []).includes(persona.id)) return false;
  if (caso.cliente_nuevo && !dato.cliente_nuevo) return false;   // A4: solo clientes en alta
  return true;
}

/**
 * ver(persona, dato, ctxPermisos) → { ok, nivel, motivo, desenmascarable? }
 *   nivel: 'completo' | 'enmascarado' | 'resumen' | 'no'
 * dato = { tipo, cliente_id?, persona_id?, participantes? }
 * ctxPermisos = { carteraIds: Set, carteraPorSilla?: {silla: Set}, personas }
 * Tipos: los de reglas_permisos.json → tipos (sueldo, contrasena, cliente_lista, cliente_detalle, cuota,
 * inversion, rentabilidad_cliente, cobros, caja, dinero_empresa, lead, horas_persona, notas_persona,
 * alarma_persona, horas_cliente, comparar_personas, rendimiento_pieza, grabacion, responder_cliente,
 * ver_como, ajustes_editar, catalogo_indicadores, rastro_todo). Desconocido = no.
 */
export function ver(persona, dato, cp = {}) {
  if (dato.cliente_id && soloSuCartera(persona) && !cp.carteraIds?.has(dato.cliente_id)) {
    return { ok: false, nivel: 'no', motivo: 'Este cliente no está en tu cartera ni en tu servicio contratado.' };
  }
  const regla = REGLAS.tipos[dato.tipo];
  if (!regla) return { ok: false, nivel: 'no', motivo: `Tipo de dato desconocido: ${dato.tipo}. Por defecto, no se enseña.` };
  if (regla.nunca) return { ok: false, nivel: 'no', motivo: regla.nunca };
  for (const caso of regla.si || []) {
    if (!cumple(caso, persona, dato, cp)) continue;
    const r = { ok: true, nivel: caso.nivel || 'completo', motivo: caso.motivo || '' };
    if (caso.desenmascarable) r.desenmascarable = true;
    return r;
  }
  return { ok: false, nivel: 'no', motivo: regla.no || 'No visible para tu puesto.' };
}

/** Enmascara un nombre, teléfono o correo de lead: «María López» → «M··· L···». */
export function enmascarar(texto = '') {
  if (texto.includes('@')) { const [u, d] = texto.split('@'); return `${u[0] || ''}···@${d}`; }
  if (/\d{6,}/.test(texto.replace(/\D/g, ''))) return texto.replace(/\d(?=(?:\D*\d){3})/g, '·');
  return texto.split(/\s+/).map(p => (p ? p[0] + '···' : p)).join(' ');
}

/** Fechas y salud de fuentes para la carcasa; sin contadores ni historia de otros clientes. */
export function metaDeCartera(meta) {
  const out = Object.fromEntries(['generado', 'construido'].filter(k => k in meta).map(k => [k, meta[k]]));
  if (Array.isArray(meta.fuentes)) out.fuentes = meta.fuentes.filter(f => f && typeof f === 'object' && !Array.isArray(f))
    .map(f => Object.fromEntries(['fuente', 'estado', 'generado', 'fecha', 'actualizado'].filter(k => k in f).map(k => [k, f[k]])));
  return out;
}
