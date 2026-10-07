import { reglas, type Contexto, type Crudo, type Persona } from '@ro/permisos';
import type { VistaConContexto } from './motor-ro.js';
import { ambitoDe, clienteVisible, veAlguno } from '../rastro/rastro-lectura.service.js';

/** servir.py › NUCLEO, más los que la puerta añade a mano. */
const NO_SE_SIRVE = new Set(['personas', 'asignaciones', 'clientes', 'alarmas', 'logos', 'meta', 'para_confirmar', 'ids_clientes']);
const RANGO: Record<string, number> = { resumen: 1, suyo: 2, todo: 3 };

export interface ResultadoPuerta {
  error?: { codigo: number; texto: string };
  conf?: Record<string, unknown>;
  nivel?: string | null;
  firma581?: string;
  niveles581?: (string | null)[];
  marca581?: string | null;
}

type Anotador = {
  registrarAgrupado: (
    quien: string,
    coleccion: string,
    accion: string,
    clave: string | null,
    datos: Record<string, unknown> | null,
    motivo: string | null,
    como: string | null,
  ) => Promise<unknown>;
};

function datosDeModulo(): Record<string, unknown> {
  return ((reglas() as unknown as { datos_de_modulo?: Record<string, unknown> }).datos_de_modulo) ?? {};
}

function casa(trozo: string, patron: string): boolean {
  const re = new RegExp(`^${patron.replace(/[.+^${}()|[\]\\]/g, '\\$&').replaceAll('*', '[^/]*').replaceAll('?', '[^/]')}$`);
  return re.test(trozo);
}

/** servir.py › entrada_datos_modulo. */
export function entradaDatosModulo(rel: string): unknown {
  if (rel.split('/').some((s) => s === '' || s === '.' || s === '..')) return null;
  const dm = datosDeModulo();
  if (Object.prototype.hasOwnProperty.call(dm, rel)) return dm[rel];
  const segmentos = rel.split('/');
  for (const [k, v] of Object.entries(dm)) {
    if (!k.includes('*')) continue;
    const partes = k.split('/');
    if (partes.length === segmentos.length && partes.every((patron, i) => casa(segmentos[i] ?? '', patron))) return v;
  }
  return null;
}

/** panel_direccion_privado_249 › permitido. Solo se usa si alguien pide ese prefijo. */
function panelPermitido(real: { id?: string }, vista: { id?: string }, personas: Persona[]): boolean {
  if (real.id !== 'tomas' || vista.id !== 'tomas') return false;
  const candidatos = personas.filter((p) => p?.id === 'tomas');
  if (candidatos.length !== 1) return false;
  const canonica = candidatos[0]!;
  return canonica.estado === 'activo' && canonica.activo !== false && (canonica.puestos ?? []).includes('direccion');
}

function comoConf(entrada: unknown): Record<string, unknown> {
  return entrada && typeof entrada === 'object' && !Array.isArray(entrada) ? (entrada as Record<string, unknown>) : { modulos: entrada };
}

function lista(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [];
}

/**
 * servir.py › puerta_modulo. La decisión por puesto vive aquí, dentro de src/permisos.
 */
export async function puertaModulo(
  vista: VistaConContexto,
  rel: string,
  crudo: Crudo,
  opts: { rastro?: Anotador; apuntar?: boolean; sello?: string | null } = {},
): Promise<ResultadoPuerta> {
  const real = vista.real;
  const persona = vista.como ?? vista.real;
  const ambito = ambitoDe(crudo, real, persona);
  if (!ambito) return { error: { codigo: 403, texto: 'El ámbito actual de estos datos no está disponible.' } };
  if (rel.split('/')[0] === 'panel_direccion' && !panelPermitido(real, persona, crudo.personas ?? [])) {
    return { error: { codigo: 403, texto: 'El panel de dirección está reservado a Tomás, sin «ver como».' } };
  }
  const soloLectura = persona.id !== real.id;
  if (rel.includes('_privado') || rel.split('/')[0] && NO_SE_SIRVE.has(rel.split('/')[0]!)) {
    return { error: { codigo: 403, texto: 'Ese fichero no se sirve por aquí.' } };
  }
  const entrada = entradaDatosModulo(rel);
  const conf = comoConf(entrada);
  const modulos = lista(conf.modulos);
  const puestosOk = Array.isArray(conf.puestos) ? lista(conf.puestos) : null;
  if (!entrada || !(modulos.length || puestosOk?.length)) {
    return { error: { codigo: 403, texto: `data/${rel}.json no está asignado a ningún módulo en reglas_permisos.json (datos_de_modulo): no se sirve.` } };
  }
  const ultimo = rel.split('/').at(-1);
  if (conf.solo_propio && (ultimo !== `p_${persona.id}` || ultimo !== `p_${real.id}`)) {
    if (opts.apuntar !== false && opts.rastro) {
      await opts.rastro.registrarAgrupado(real.id, 'modulo', 'denegado', rel, { motivo: 'fichero de otra persona' }, null, soloLectura ? persona.id : null);
    }
    return { error: { codigo: 403, texto: 'Ese fichero es de otra persona.' } };
  }
  let niveles581: (string | null)[];
  let nivel: string | null;
  if (puestosOk && puestosOk.length) {
    niveles581 = ambito.ps.map((p) => (lista(p.puestos).some((x) => puestosOk.includes(x)) ? 'todo' : null));
    nivel = niveles581.every(Boolean) ? 'todo' : null;
    if (conf.solo_real && !lista(real.puestos).some((x) => puestosOk.includes(x))) nivel = null;
  } else {
    niveles581 = ambito.ps.map((p) => veAlguno(p, modulos));
    nivel = niveles581.every(Boolean) ? niveles581.reduce((a, b) => ((RANGO[a!] ?? 0) <= (RANGO[b!] ?? 0) ? a : b)) : null;
  }
  const excluir = lista(conf.excluir_puestos);
  if (excluir.length && ambito.ps.some((p) => lista(p.puestos).every((x) => excluir.includes(x)))) nivel = null;
  const vacio = lista((conf.vacio_para_puestos as { puestos?: unknown } | undefined)?.puestos);
  if (!nivel && vacio.length && lista(persona.puestos).length && lista(persona.puestos).every((x) => vacio.includes(x))) {
    return { conf, nivel: 'vacio', firma581: opts.sello ?? '', niveles581, marca581: opts.sello ?? null };
  }
  if (!nivel) {
    if (opts.apuntar !== false && opts.rastro) {
      await opts.rastro.registrarAgrupado(real.id, 'modulo', 'denegado', rel, { modulos }, null, soloLectura ? persona.id : null);
    }
    return { error: { codigo: 403, texto: 'Estos datos son de una pantalla que no es de tu puesto.' } };
  }
  const cid = clienteDeUrl(rel);
  if (cid !== null && !clienteDeDatos(cid, crudo, ambito.ps, ambito.cps, niveles581)) {
    return { error: { codigo: 403, texto: 'El cliente de estos datos no está autorizado.' } };
  }
  return { conf, nivel, firma581: opts.sello ?? '', niveles581, marca581: opts.sello ?? null };
}

function clienteDeUrl(rel: string): string | null {
  const partes = rel.split('/');
  if (partes.length === 2 && partes[0] === 'clientes') return partes[1] ?? null;
  if (partes.length === 3 && ((partes[0] === 'paneles' && ['ga4', 'gsc', 'meta', 'ghl', 'mc'].includes(partes[1] ?? '')) || (partes[0] === 'informe' && (partes[1] ?? '').startsWith('c_')))) {
    return partes[2] ?? null;
  }
  return null;
}

function clienteDeDatos(cid: string, crudo: Crudo, ps: Persona[], cps: Contexto[], niveles: (string | null)[]): boolean {
  if (!clienteVisible(cid, crudo, ps, cps)) return false;
  return niveles.every((nivel, i) => nivel !== 'suyo' || (cps[i]?.cartera_ids ?? new Set()).has(cid));
}
