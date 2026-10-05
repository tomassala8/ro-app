import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { hoyMadrid } from '@ro/compat';
import type { Cliente, Reglas } from './tipos.js';

function rutaReglas(ruta?: URL): URL {
  if (ruta) return ruta;
  const env = process.env.RO_REGLAS_PERMISOS;
  if (env) return pathToFileURL(env);
  return new URL('../../../../reglas_permisos.json', import.meta.url);
}

/** Lee reglas_permisos.json (por defecto, el de la raíz del repositorio). */
export function cargarReglas(ruta?: URL): Reglas {
  return JSON.parse(readFileSync(rutaReglas(ruta), 'utf8')) as Reglas;
}

let REGLAS: Reglas = cargarReglas();

/** Siempre el objeto vigente: recargarReglas sustituye el anterior. */
export function reglas(): Reglas {
  return REGLAS;
}

export function recargarReglas(ruta?: URL): void {
  REGLAS = cargarReglas(ruta);
}

export function puesto(id: string): Reglas['puestos'][number] | undefined {
  return REGLAS.puestos.find((p) => p.id === id);
}

/** Fecha de negocio en Madrid (AAAA-MM-DD). RO_RELOJ la fija, igual que permisos.py. */
export const hoyIso = (): string => hoyMadrid();

export const SERVICIOS_SILLA: Record<string, readonly string[]> = {
  seo: ['seo'],
  trafficker: ['publicidad'],
  crm: ['crm_ghl'],
  ghl: ['crm_ghl'],
  web: ['web', 'mantenimiento'],
  redes: ['redes', 'social_media'],
  outreach: ['outreach'],
};

export const SERVICIOS_JEFATURA: Record<string, readonly string[]> = {
  jefa_seo: ['seo'],
  jefa_publicidad: ['publicidad'],
  jefa_crm: ['crm_ghl', 'outreach'],
};

export function servicioContratado(cliente: Cliente, claves: readonly string[]): boolean {
  const servicios = cliente.servicios ?? {};
  return claves.some((k) => servicios[k] === 'sí');
}
