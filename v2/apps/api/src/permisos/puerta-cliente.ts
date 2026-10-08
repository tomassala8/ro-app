import { reglas, type Contexto, type Crudo, type Persona } from '@ro/permisos';
import type { VistaConContexto } from './motor-ro.js';
import { ambitoDe, clienteVisible, veAlguno } from '../rastro/rastro-lectura.service.js';

/** servir.py › puerta_cliente_581: módulos que abren la ficha. */
const MODULOS_FICHA = ['ficha', 'bandeja', 'captacion', 'asistente-ia'];
const RANGO: Record<string, number> = { resumen: 1, suyo: 2, todo: 3 };
/** Python `\w` admite letras; el guion va aparte, como el fullmatch de cliente_datos_581. */
const CID_OK = /^[\p{L}\p{N}_-]{1,100}$/u;

interface ReglasFicha {
  ficha_solo_contrato?: { puestos?: string[]; fuentes?: string[] };
}

function contrato(): { puestos: string[]; fuentes: string[] } {
  const extra = reglas() as ReglasFicha;
  return {
    puestos: extra.ficha_solo_contrato?.puestos ?? [],
    fuentes: extra.ficha_solo_contrato?.fuentes ?? [],
  };
}

/** servir.py › set(puestos) <= set(ficha_solo_contrato.puestos). */
export function puestosSonSoloContrato(puestos: readonly string[] | undefined): boolean {
  const deja = new Set(contrato().puestos);
  return (puestos ?? []).every((p) => deja.has(p));
}

export function fuentesSoloContrato(): string[] {
  return contrato().fuentes;
}

/**
 * servir.py › administracion581 (:2789). Alguna persona del ámbito (real y vista) solo tiene
 * los puestos de ficha_solo_contrato. Vive aquí: rutas-declaradas no deja mirar puestos fuera de permisos.
 */
export function administracion581(ps: readonly Persona[]): boolean {
  return ps.some((p) => puestosSonSoloContrato(p.puestos));
}

/** servir.py › cliente_datos_581. */
export function clienteDatos581(
  cid: unknown,
  crudo: Crudo,
  ps: Persona[],
  cps: Contexto[],
  niveles: (string | null)[],
): boolean {
  if (!ps.length || typeof cid !== 'string' || !CID_OK.test(cid) || !clienteVisible(cid, crudo, ps, cps)) return false;
  return niveles.every((nivel, i) => nivel !== 'suyo' || (cps[i]?.cartera_ids ?? new Set()).has(cid));
}

/** servir.py › cliente_url_581, solo el caso de la ficha (`clientes/<cid>`). */
export function clienteDeUrlFicha(rel: string): string | null {
  const partes = rel.split('/');
  if (partes.length === 2 && partes[0] === 'clientes') return partes[1] ?? null;
  return null;
}

/** servir.py › documento_raiz_581. */
export function documentoRaiz581(
  doc: unknown,
  rel: string,
  crudo: Crudo,
  ps: Persona[],
  cps: Contexto[],
  niveles: (string | null)[],
): boolean {
  const ids: unknown[] = [];
  const deUrl = clienteDeUrlFicha(rel);
  if (deUrl !== null) ids.push(deUrl);
  if (doc && typeof doc === 'object' && !Array.isArray(doc)) {
    const o = doc as Record<string, unknown>;
    for (const k of ['cliente_id', 'cid', 'cli']) {
      if (k in o && o[k] != null) ids.push(o[k]);
    }
  }
  if (!ids.length) return true;
  const primero = ids[0];
  if (!ids.every((id) => typeof id === 'string' && id === primero)) return false;
  return clienteDatos581(primero, crudo, ps, cps, niveles);
}

export interface PuertaCliente {
  cid: string;
  ambito: { ps: Persona[]; cps: Contexto[] };
  niveles: string[];
  nivel: string;
  /** Marca del crudo: el papel de ambito[2] de Python (la firma) en esta noche. */
  firma: string;
  /** Con fichero leído: la misma marca, el papel del id de versión. */
  marca?: string | null;
  conFichero?: boolean;
}

/**
 * servir.py › puerta_cliente_581. `cid` va en la firma porque la puerta de Python lo recibe
 * y sin él no se puede llamar a cliente_datos_581.
 */
export function puertaCliente581(vista: VistaConContexto, crudo: Crudo, cid: string, firma: string): PuertaCliente | null {
  const persona = vista.como ?? vista.real;
  const ambito = ambitoDe(crudo, vista.real, persona);
  if (!ambito) return null;
  const niveles = ambito.ps.map((p) => veAlguno(p, MODULOS_FICHA));
  if (niveles.some((n) => !n)) return null;
  const buenos = niveles as string[];
  if (!clienteDatos581(cid, crudo, ambito.ps, ambito.cps, buenos)) return null;
  const nivel = buenos.reduce((a, b) => ((RANGO[a] ?? 99) <= (RANGO[b] ?? 99) ? a : b));
  return { cid, ambito, niveles: buenos, nivel, firma };
}

/**
 * servir.py › cliente_vigente_581. Sin fichero, solo la firma. Con fichero, también la marca
 * (aquí el sello del crudo: no hay mtime de disco cuando el dato vive en la versión publicada).
 */
export function clienteVigente581(vista: VistaConContexto, crudo: Crudo, previo: PuertaCliente, firmaAhora: string): boolean {
  const final = puertaCliente581(vista, crudo, previo.cid, firmaAhora);
  if (!final || final.firma !== previo.firma) return false;
  if (previo.conFichero && firmaAhora !== (previo.marca ?? null)) return false;
  return true;
}
