import { ambitoDe, clienteVisible } from '../rastro/rastro-lectura.service.js';
import { puestosDe, type Contexto, type Crudo, type Persona } from '@ro/permisos';

type Identidad = { id?: unknown; puestos?: unknown };

/** servir.py › puede_contestar. Mira los puestos de esa persona, no la intersección de «ver como». */
export function puedeContestar(persona: { puestos?: readonly string[] } | null | undefined, tipo: string): boolean {
  const pu = new Set(persona?.puestos ?? []);
  if (tipo === 'para_coti') return pu.has('proyectos') || pu.has('direccion');
  return pu.has('direccion');
}

export interface FilaFiltro {
  tipo?: unknown;
  quien?: unknown;
}

/**
 * servir.py › decisiones_para, el filtro final. `puestosDe` aplica la intersección si hay «ver como»
 * (la llamada va dentro de conVista, como mirando_como).
 */
export function filtroDecisiones<T extends FilaFiltro>(persona: Persona, lista: T[]): T[] {
  const pu = puestosDe(persona);
  if (pu.has('direccion') || pu.has('operaciones')) return lista;
  if (pu.has('proyectos')) return lista.filter((d) => d.tipo === 'para_coti' || d.quien === persona.id);
  return lista.filter((d) => d.quien === persona.id);
}

export interface AmbitoCargado {
  crudo: Crudo;
  firma: string;
}

/**
 * servir.py › autoridad_decision607. La firma es la marca del crudo de F5.2 (el mismo papel que el json
 * de ambito en Python). Vacío de clientes: all([]) es verdad.
 */
export async function autoridadDecision607(
  cargar: () => Promise<AmbitoCargado>,
  real: Identidad,
  clientes: string[],
): Promise<string | null> {
  const primero = await cargar();
  const inicial = ambitoDe(primero.crudo, real, real);
  if (!inicial) return null;
  if (!clientes.every((cid) => clienteVisible(cid, primero.crudo, inicial.ps, inicial.cps))) return null;
  const segundo = await cargar();
  const final = ambitoDe(segundo.crudo, real, real);
  return final && segundo.firma === primero.firma ? primero.firma : null;
}

export type { Contexto };
