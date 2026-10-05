import { hoyIso, puesto, reglas, SERVICIOS_JEFATURA, SERVICIOS_SILLA, servicioContratado } from './reglas.js';
import type { Ambito, Asignacion, Caso, Cliente, ContextoParcial, Dato, Persona } from './tipos.js';

export function sillasDe(persona: { puestos?: string[] }): Set<string> {
  const mapa = reglas().sillas_de_puesto ?? {};
  const out = new Set<string>();
  for (const p of persona.puestos ?? []) for (const s of mapa[p] ?? []) out.add(s);
  return out;
}

export function vigente(a: { desde?: string | null; hasta?: string | null }, hoy: string): boolean {
  if (a.desde && a.desde > hoy) return false;
  if (a.hasta && a.hasta < hoy) return false;
  return true;
}

export function carteraPorSilla(
  persona: Persona,
  asignaciones: Asignacion[],
  hoy?: string,
  clientes?: Cliente[],
): Record<string, Set<string>> {
  const dia = hoy || hoyIso();
  const sillas = sillasDe(persona);
  const out: Record<string, Set<string>> = {};
  for (const a of asignaciones) {
    if (a.persona_id !== persona.id || !vigente(a, dia)) continue;
    if (a.suplencia && !a.hasta) continue;
    if (a.silla && sillas.size && !sillas.has(a.silla) && !a.suplencia) continue;
    const clave = a.silla || 'sin_silla';
    (out[clave] ??= new Set()).add(a.cliente_id);
  }
  const equipo = reglas().sillas_de_equipo ?? [];
  for (const silla of equipo) {
    if (!sillas.has(silla)) continue;
    const todos = new Set<string>();
    for (const a of asignaciones) {
      if (a.silla === silla && vigente(a, dia) && !(a.suplencia && !a.hasta)) todos.add(a.cliente_id);
    }
    if (todos.size) {
      const dest = (out[silla] ??= new Set<string>());
      for (const id of todos) dest.add(id);
    }
  }
  // L-25 (Tomás, 4-oct): «altas» es una silla virtual: los clientes con alta firmada en los últimos 90 días (verdad «nuevo»).
  if (sillas.has('altas') && clientes !== undefined) {
    const nuevos = clientes.filter((c) => Boolean(c.nuevo)).map((c) => c.id);
    if (nuevos.length) {
      const dest = (out['altas'] ??= new Set<string>());
      for (const id of nuevos) dest.add(id);
    }
  }
  if (clientes !== undefined) {
    const porId: Record<string, Cliente> = {};
    for (const c of clientes) porId[c.id] = c;
    for (const [silla, ids] of Object.entries(out)) {
      const claves = SERVICIOS_SILLA[silla];
      if (!claves) continue;
      out[silla] = new Set([...ids].filter((cid) => porId[cid] !== undefined && servicioContratado(porId[cid], claves)));
    }
    for (const silla of equipo) {
      const claves = SERVICIOS_SILLA[silla];
      if (sillas.has(silla) && claves) {
        out[silla] = new Set(clientes.filter((c) => servicioContratado(c, claves)).map((c) => c.id));
      }
    }
    const puestos = new Set(persona.puestos ?? []);
    for (const [puestoId, claves] of Object.entries(SERVICIOS_JEFATURA)) {
      if (puestos.has(puestoId)) {
        out[`servicio_${puestoId}`] = new Set(clientes.filter((c) => servicioContratado(c, claves)).map((c) => c.id));
      }
    }
  }
  return out;
}

export function cartera(persona: Persona, asignaciones: Asignacion[], hoy?: string, clientes?: Cliente[]): Set<string> {
  const ids = new Set<string>();
  for (const s of Object.values(carteraPorSilla(persona, asignaciones, hoy, clientes))) for (const id of s) ids.add(id);
  return ids;
}

export function ambito(persona: Persona): Ambito {
  const orden = reglas().orden_ambitos;
  let mejor = 'ninguno';
  for (const p of persona.puestos ?? []) {
    const a = puesto(p)?.ambito ?? 'ninguno';
    if (orden.indexOf(a) > orden.indexOf(mejor)) mejor = a;
  }
  return mejor as Ambito;
}

export function esJefe(persona: Persona, objetivo?: Persona | null): boolean {
  if (!objetivo) return false;
  if (objetivo.jefe === persona.id) return true;
  const mapa = reglas().jefe_de_puesto ?? {};
  const subordinados = new Set<string>();
  for (const p of persona.puestos ?? []) for (const s of mapa[p] ?? []) subordinados.add(s);
  return (objetivo.puestos ?? []).some((p) => subordinados.has(p));
}

export function cumple(caso: Caso, persona: Persona, dato: Dato, cp: ContextoParcial): boolean {
  const puestos = persona.puestos ?? [];
  if ('identidades' in caso && !(caso.identidades ?? []).includes(persona.id)) return false;
  if ('puestos' in caso && !puestos.some((p) => (caso.puestos ?? []).includes(p))) return false;
  if ('ambito' in caso && !(caso.ambito ?? []).includes(ambito(persona))) return false;
  if (caso.cartera) {
    const cid = dato.cliente_id;
    if (!cid) return false;
    if (caso.cartera === true) {
      if (!(cp.cartera_ids ?? new Set()).has(cid)) return false;
    } else if (typeof caso.cartera === 'string') {
      const por = cp.cartera_por_silla;
      const conjunto = por !== undefined ? (por[caso.cartera] ?? new Set<string>()) : (cp.cartera_ids ?? new Set<string>());
      if (!conjunto.has(cid)) return false;
    }
  }
  if (caso.sin_cliente && dato.cliente_id) return false;
  if (caso.propio && dato.persona_id !== persona.id) return false;
  if (caso.jefe) {
    const obj = (cp.personas ?? []).find((p) => p.id === dato.persona_id) ?? null;
    if (!esJefe(persona, obj)) return false;
  }
  if (caso.participante) {
    const partes = Array.isArray(dato.participantes) ? dato.participantes : [];
    if (!partes.includes(persona.id)) return false;
  }
  if (caso.cliente_nuevo && !dato.cliente_nuevo) return false;
  return true;
}
