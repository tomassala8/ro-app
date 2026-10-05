import { ambito, carteraPorSilla, cumple, sillasDe } from './cartera.js';
import { reglas, SERVICIOS_JEFATURA, SERVICIOS_SILLA } from './reglas.js';
import type { Cliente, Contexto, ContextoParcial, Crudo, Dato, Persona, Respuesta } from './tipos.js';
import { registrarContexto, vistaActiva } from './vista.js';

const ORDEN_NIVEL: Record<string, number> = { no: 0, enmascarado: 1, resumen: 2, completo: 3 };

export function soloSuCartera(persona: Persona): boolean {
  if (ambito(persona) === 'todos') return false;
  const puestos = new Set(persona.puestos ?? []);
  const deReglas = new Set(reglas().solo_su_cartera?.puestos ?? []);
  const jefatura = new Set(Object.keys(SERVICIOS_JEFATURA));
  const conSilla = new Set<string>();
  for (const p of puestos) {
    const sillas = sillasDe({ puestos: [p] });
    for (const s of sillas) {
      if (s in SERVICIOS_SILLA) {
        conSilla.add(p);
        break;
      }
    }
  }
  for (const p of puestos) {
    if (deReglas.has(p) || jefatura.has(p) || conSilla.has(p)) return true;
  }
  return false;
}

export function contexto(persona: Persona, crudo: Crudo): Contexto {
  const clientes = crudo.clientes ?? [];
  const porSilla = carteraPorSilla(persona, crudo.asignaciones, undefined, clientes);
  const ids = new Set<string>();
  for (const s of Object.values(porSilla)) for (const id of s) ids.add(id);
  const clientesPorId: Record<string, Cliente> = {};
  for (const c of clientes) clientesPorId[c.id] = c;
  return {
    cartera_ids: ids,
    cartera_por_silla: porSilla,
    personas: crudo.personas,
    clientes_por_id: clientesPorId,
  };
}

registrarContexto(contexto);

export function verSinVista(persona: Persona, dato: Dato, cp: ContextoParcial = {}): Respuesta {
  const carteraIds = cp.cartera_ids ?? new Set<string>();
  if (dato.cliente_id && soloSuCartera(persona) && !carteraIds.has(dato.cliente_id)) {
    return { ok: false, nivel: 'no', motivo: 'Este cliente no está en tu cartera ni en tu servicio contratado.' };
  }
  const tipos = reglas().tipos;
  const regla = dato.tipo ? tipos[dato.tipo] : undefined;
  if (!regla) {
    return { ok: false, nivel: 'no', motivo: `Tipo de dato desconocido: ${dato.tipo}. Por defecto, no se enseña.` };
  }
  if (regla.nunca) return { ok: false, nivel: 'no', motivo: regla.nunca };
  for (const caso of regla.si ?? []) {
    if (!cumple(caso, persona, dato, cp)) continue;
    const r: Respuesta = { ok: true, nivel: caso.nivel ?? 'completo', motivo: caso.motivo ?? '' };
    if (caso.desenmascarable) r.desenmascarable = true;
    return r;
  }
  return { ok: false, nivel: 'no', motivo: regla.no || 'No visible para tu puesto.' };
}

export function ver(persona: Persona, dato: Dato, cp?: ContextoParcial): Respuesta {
  const r = verSinVista(persona, dato, cp ?? {});
  const activo = vistaActiva();
  if (activo && activo.real.id !== persona.id && r.ok) {
    const r2 = verSinVista(activo.real, dato, activo.cp);
    if (!r2.ok) {
      return {
        ok: false,
        nivel: 'no',
        motivo: `En «ver como» solo se ve lo que ven las dos personas. ${r2.motivo ?? ''}`,
      };
    }
    const out: Respuesta = (ORDEN_NIVEL[r2.nivel] ?? 0) < (ORDEN_NIVEL[r.nivel] ?? 0) ? { ...r, nivel: r2.nivel } : { ...r };
    if (!r2.desenmascarable) delete out.desenmascarable;
    return out;
  }
  return r;
}
