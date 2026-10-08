import {
  CLAVES_LEAD,
  importesAQuitar,
  sinImportes,
  ver,
  type Contexto,
  type Persona,
  type QuitaClave,
} from '@ro/permisos';
import { jsonComoPython } from '@ro/compat';
import { quitarPara, recortarDoc } from '../rastro/rastro-lectura.service.js';

type Fila = Record<string, unknown>;

/** Igualdad de Python (`==`): el orden de las listas cuenta; el de las claves, no. True == 1. */
export function igualProfunda(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  const num = (x: unknown) => typeof x === 'number' || typeof x === 'boolean';
  if (num(a) && num(b)) return Number(a) === Number(b);
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((x, i) => igualProfunda(x, b[i]));
  }
  if (esObj(a) && esObj(b)) {
    const ka = Object.keys(a);
    if (ka.length !== Object.keys(b).length) return false;
    return ka.every((k) => Object.prototype.hasOwnProperty.call(b, k) && igualProfunda(a[k], b[k]));
  }
  return false;
}

function esObj(x: unknown): x is Fila {
  return !!x && typeof x === 'object' && !Array.isArray(x);
}

function cidDe(v: unknown): string | undefined {
  return typeof v === 'string' && v ? v : undefined;
}

/**
 * servir.py › recorte_importes_lectura588. `vista_previa` solo se reescribe si el recorte cambió el valor
 * (`limpio != valor`); si no, se deja el texto guardado tal cual.
 */
export function recorteImportesLectura588(filas: Fila[], personas: Persona[], contextos: Contexto[]): Fila[] {
  const salida: Fila[] = [];
  for (const original of filas) {
    let fila: Fila = { ...original };
    const cid = cidDe(fila.cliente_id);
    const permisos = (['cuota', 'inversion', 'cobros', 'dinero_empresa'] as const).map((tipo) =>
      personas.every((p, i) => ver(p, { tipo, cliente_id: cid }, contextos[i] ?? {}).ok === true),
    );
    const quitar = importesAQuitar(permisos[0] ?? false, permisos[1] ?? false, permisos[2] ?? false, permisos[3] ?? false);
    const patrones: QuitaClave[] = [];
    for (let i = 0; i < personas.length; i++) {
      const p = personas[i];
      const cp = contextos[i];
      if (!p || !cp) continue;
      for (const patron of quitarPara(p, cp, cid)) {
        if (patron !== CLAVES_LEAD && !patrones.includes(patron)) patrones.push(patron);
      }
    }
    fila = recortarDoc(fila, patrones) as Fila;
    if (quitar.length) {
      const vp = fila.vista_previa;
      delete fila.vista_previa;
      const tieneVp = Object.prototype.hasOwnProperty.call(original, 'vista_previa');
      fila = sinImportes(fila, quitar) as Fila;
      if (tieneVp) {
        if (typeof vp === 'string') {
          try {
            const valor = JSON.parse(vp) as unknown;
            const limpio = sinImportes(recortarDoc(valor, patrones), quitar);
            fila.vista_previa = igualProfunda(limpio, valor) ? vp : jsonComoPython(limpio, { ensureAscii: false });
          } catch {
            fila.vista_previa = sinImportes(vp, quitar);
          }
        } else {
          fila.vista_previa = sinImportes(recortarDoc(vp, patrones), quitar);
        }
      }
    }
    salida.push(fila);
  }
  return salida;
}
