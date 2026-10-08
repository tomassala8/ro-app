import { nivelModulo, ver, type Contexto, type Crudo, type Persona } from '@ro/permisos';
import { ambitoDe, clienteVisible } from '../rastro/rastro-lectura.service.js';
import { modulosActuales } from './recarga.js';

type Fila = { ruta?: unknown; quien?: unknown };

/** panel_direccion_privado_249.permitido. El id literal va aquí, en permisos. */
export function permitidoPanel249(
  real: { id?: unknown; puestos?: unknown } | null,
  vista: { id?: unknown; puestos?: unknown } | null,
  personas: unknown,
): boolean {
  if (!real || !vista || typeof real !== 'object' || typeof vista !== 'object') return false;
  if (real.id !== 'tomas' || vista.id !== 'tomas') return false;
  if (!Array.isArray(personas)) return false;
  const candidatos = personas.filter((p) => p && typeof p === 'object' && (p as { id?: unknown }).id === 'tomas');
  if (candidatos.length !== 1) return false;
  const c = candidatos[0] as { estado?: unknown; activo?: unknown; puestos?: unknown };
  const puestos = Array.isArray(c.puestos) ? c.puestos : [];
  return c.estado === 'activo' && c.activo !== false && puestos.includes('direccion');
}

/**
 * capturas_opiniones_565.permiso. Devuelve «modulo\\0firma» o null.
 * Hay que llamarla con «ver como» ya puesto (conVista), porque nivelModulo mira la vista activa.
 */
export function permisoCaptura565(
  crudo: Crudo,
  firma: string,
  real: { id?: unknown; puestos?: unknown },
  persona: { id?: unknown; puestos?: unknown },
  fila: Fila,
): string | null {
  try {
    const actual = ambitoDe(crudo, real, persona);
    if (!actual) return null;
    const { ps, cps } = actual;
    const ruta = fila.ruta;
    if (typeof ruta !== 'string' || Array.from(ruta).length > 200 || !/^#\/[-\p{L}\p{N}_/.%?=&]*$/u.test(ruta)) return null;
    const mid = ruta.slice(2).split('?')[0]?.split('/')[0] ?? '';
    if (!/^[\p{L}\p{N}_-]+$/u.test(mid)) return null;
    const modulos = modulosActuales();
    if (!Object.prototype.hasOwnProperty.call(modulos, mid)) return null;
    const mapa = modulos[mid];
    if (!mapa || typeof mapa !== 'object') return null;
    if (!ps.every((p) => ['suyo', 'todo'].includes(nivelModulo(p, mapa) ?? ''))) return null;
    if (mid === 'panel-direccion' && !permitidoPanel249(ps[0] ?? null, ps[1] ?? null, crudo.personas)) return null;
    const todas = ps.every((p, i) => ver(p, { tipo: 'opiniones_ver' }, cps[i] ?? {}).ok === true);
    if (!todas && fila.quien !== ps[1]?.id) return null;
    if (ps.some((p) => p.id !== fila.quien)) return null;
    if (mid === 'ficha') {
      const partes = (ruta.slice(2).split('?')[0] ?? '').split('/');
      const cid = partes[1];
      if (!cid || !clienteVisible(cid, crudo, ps, cps)) return null;
    }
    return `${mid}\0${firma}`;
  } catch {
    return null;
  }
}

export type { Contexto, Persona };
