import { conVista, importesAQuitar, puestosDe, sinImportes, ver, type Contexto, type Persona } from '@ro/permisos';
import type { VistaConContexto } from './motor-ro.js';

/**
 * servir.py › GET /api/indicadores (2822-2843).
 * L-25: ya no hay dos conjuntos de puestos escritos en la ruta. Cuota e inversión salen de ver()
 * (el mínimo de las dos personas en «ver como»). La inversión del trafficker es por cliente de su cartera.
 */

const RECORTADO = 'Solo los indicadores de tus puestos.';

type Fila = Record<string, unknown>;
const esFila = (x: unknown): x is Fila => !!x && typeof x === 'object' && !Array.isArray(x);

function comoPersona(p: { id: string; nombre?: unknown; puestos?: string[] }): Persona {
  return { ...(p as Persona), nombre: typeof p.nombre === 'string' ? p.nombre : '', puestos: p.puestos ?? [] };
}

/** Catálogo mal formado: Python lanza KeyError y do_GET responde 500. */
export class CatalogoRoto extends Error {}

function dentro<T>(vista: VistaConContexto, fn: (persona: Persona, cp: Contexto) => T): T {
  const persona = comoPersona(vista.como ?? vista.real);
  const cp = vista.cp;
  if (!cp) throw new CatalogoRoto('sin contexto');
  const aplicar = () => fn(persona, cp);
  if (vista.como && vista.cpReal) return conVista({ real: comoPersona(vista.real), cp: vista.cpReal }, aplicar);
  return aplicar();
}

/** True si el catálogo se queda solo con los indicadores de sus puestos. */
export function recortaCatalogo(vista: VistaConContexto): boolean {
  return dentro(vista, (persona, cp) => !ver(persona, { tipo: 'catalogo_indicadores' }, cp).ok);
}

/**
 * Claves de importe a tapar. Dos argumentos: cobros y dinero_empresa quedan undefined
 * (None no es False: importes_a_quitar no los quita).
 */
export function quitaIndicadores(vista: VistaConContexto): string[] {
  return dentro(vista, (persona, cp) => {
    const veCuota = ver(persona, { tipo: 'cuota' }, cp).ok;
    const cartera = cp.cartera_ids ?? new Set<string>();
    const veInv =
      ver(persona, { tipo: 'inversion' }, cp).ok ||
      [...cartera].some((cid) => ver(persona, { tipo: 'inversion', cliente_id: cid }, cp).ok);
    return importesAQuitar(veCuota, veInv);
  });
}

/** Recorte del catálogo. Mutar `cat` (el servicio pasa una copia). */
export function recortarIndicadores(vista: VistaConContexto, cat: unknown): unknown {
  if (!esFila(cat)) throw new CatalogoRoto('el catálogo no es un objeto');
  return dentro(vista, (persona, cp) => {
    if (!ver(persona, { tipo: 'catalogo_indicadores' }, cp).ok) {
      const mios = puestosDe(persona);
      const lista = cat.indicadores;
      if (!Array.isArray(lista)) throw new CatalogoRoto('sin lista');
      const filtrada: unknown[] = [];
      for (const i of lista) {
        if (!esFila(i) || !('puesto' in i)) throw new CatalogoRoto('indicador sin puesto');
        if (typeof i.puesto === 'string' && mios.has(i.puesto)) filtrada.push(i);
      }
      cat.indicadores = filtrada;
      if (!esFila(cat._meta)) throw new CatalogoRoto('sin _meta');
      cat._meta.recortado = RECORTADO;
    }
    const quita = quitaIndicadores(vista);
    return quita.length ? sinImportes(cat, quita) : cat;
  });
}
