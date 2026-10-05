import { AsyncLocalStorage } from 'node:async_hooks';
import type { Contexto, Crudo, Persona } from './tipos.js';

/** «Ver como» por contexto de ejecución: una petición no contamina a otra. */
const VISTA = new AsyncLocalStorage<{ real: Persona; cp: Contexto }>();

type HacerContexto = (real: Persona, crudo: Crudo) => Contexto;
let hacerContexto: HacerContexto | null = null;

/** Lo registra ver.ts al cargar, para no importar en círculo. */
export function registrarContexto(fn: HacerContexto): void {
  hacerContexto = fn;
}

export function vistaActiva(): { real: Persona; cp: Contexto } | undefined {
  return VISTA.getStore();
}

export function conVista<T>(vista: { real: Persona; cp: Contexto }, fn: () => T): T {
  return VISTA.run(vista, fn);
}

export function mirandoComo<T>(real: Persona, crudo: Crudo, fn: () => T): T {
  if (!hacerContexto) throw new Error('contexto no registrado');
  return VISTA.run({ real, cp: hacerContexto(real, crudo) }, fn);
}

export function puestosDe(persona: Persona): Set<string> {
  const propios = new Set(persona.puestos ?? []);
  const activo = vistaActiva();
  if (activo && activo.real.id !== persona.id) {
    const delReal = new Set(activo.real.puestos ?? []);
    return new Set([...propios].filter((p) => delReal.has(p)));
  }
  return propios;
}
