import { nivelModulo, puestosDe, reglas, type Persona } from '@ro/permisos';
import { modulosActuales } from './recarga.js';

export interface AlmacenConf {
  tipo: string;
  modulos?: string[];
  dueno?: string;
  dueno_setter?: boolean;
  cliente?: unknown;
}

type Fila = Record<string, unknown>;

function esFila(x: unknown): x is Fila {
  return !!x && typeof x === 'object' && !Array.isArray(x);
}

/** fnmatch.fnmatchcase de un solo segmento (los patrones de almacenes usan * y texto). */
function fnmatchcase(nombre: string, patron: string): boolean {
  let re = '';
  for (const c of patron) {
    if (c === '*') re += '.*';
    else if (c === '?') re += '.';
    else re += c.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp(`^${re}$`).test(nombre);
}

/** servir.py › config_almacen. null si el almacén no está declarado. */
export function configAlmacen(almacen: unknown): AlmacenConf | null {
  if (typeof almacen !== 'string' || almacen.split('/').some((s) => s === '' || s === '.' || s === '..')) return null;
  const segmentos = almacen.split('/');
  const mapa = (reglas() as { almacenes_privados?: Record<string, AlmacenConf> }).almacenes_privados ?? {};
  for (const [patron, conf] of Object.entries(mapa)) {
    const partes = patron.split('/');
    if (partes.length === segmentos.length && partes.every((p, i) => fnmatchcase(segmentos[i] ?? '', p))) return conf;
  }
  return null;
}

/** L-09: clave_setter, o el id `setter_<clave>` hasta la primera recarga. */
export function claveSetterDe(persona: { id?: unknown; clave_setter?: unknown }): string | null {
  const directa = persona.clave_setter;
  if (typeof directa === 'string' && directa) return directa;
  const id = typeof persona.id === 'string' ? persona.id : '';
  return id.startsWith('setter_') ? id.slice('setter_'.length) : null;
}

/**
 * servir.py:3454-3455. Hay que llamarla dentro de conVista: puestosDe aplica la intersección.
 * Sin dueno_setter, cualquiera (el tipo y el módulo deciden después).
 */
export function duenoOk(persona: Persona, conf: { dueno_setter?: boolean }, nombreAlm: string): boolean {
  if (!conf.dueno_setter) return true;
  const clave = claveSetterDe(persona);
  if (clave && nombreAlm === `setter_${clave}`) return true;
  const puestos = puestosDe(persona);
  return puestos.has('direccion') || puestos.has('ventas_ro');
}

/** servir.py › ve_alguno, con el mínimo de «ver como» (nivelModulo mira la vista activa). */
export function veAlgunoConVista(persona: Persona, mods: string[]): boolean {
  const mapas = modulosActuales();
  const niveles = mods.map((m) => nivelModulo(persona, mapas[m] ?? {})).filter((n) => !!n);
  return niveles.length > 0;
}

function clienteEnCrudo(clientes: { id: string }[], cid: unknown): boolean {
  return typeof cid === 'string' && clientes.some((c) => c.id === cid);
}

/**
 * servir.py › cliente_del_dato. `leer` es CrudoService.fichero (ruta relativa a data/, con .json).
 * es_activo queda fuera: aquí solo se reconoce el id si está en el crudo.
 */
export async function clienteDelDato(
  conf: AlmacenConf,
  ref: string,
  almacen: string | undefined,
  clientes: { id: string }[],
  leer: (ruta: string) => Promise<unknown>,
): Promise<string | null> {
  const c = conf.cliente;
  if (!c) return null;
  if (c === 'ref') return clienteEnCrudo(clientes, ref) ? ref : null;
  if (esFila(c) && c.campo) {
    let doc: unknown = {};
    if (almacen && !almacen.split('/').some((s) => s === '' || s === '.' || s === '..')) {
      try {
        doc = (await leer(`${almacen}.json`)) ?? {};
      } catch {
        return null;
      }
    }
    const colecciones = esFila(doc) ? Object.values(doc) : [];
    for (const coleccion of colecciones) {
      if (!esFila(coleccion)) continue;
      const fila = coleccion[ref];
      if (!esFila(fila)) continue;
      const cid = fila[String(c.campo)];
      return clienteEnCrudo(clientes, cid) ? (cid as string) : null;
    }
    return null;
  }
  if (!esFila(c) || typeof c.desde !== 'string') return null;
  let d: unknown;
  try {
    d = await leer(`${c.desde}.json`);
  } catch {
    return null;
  }
  if (!esFila(d)) return null;
  const listas = Array.isArray(c.listas) ? c.listas : [];
  const clave = typeof c.clave === 'string' ? c.clave : 'ref';
  for (const lista of listas) {
    if (typeof lista !== 'string') continue;
    const filas = d[lista];
    for (const fila of Array.isArray(filas) ? filas : []) {
      if (esFila(fila) && String(fila[clave] ?? '') === ref) {
        const cid = fila.cliente_id;
        return typeof cid === 'string' ? cid : null;
      }
    }
  }
  return null;
}
