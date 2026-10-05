import { ambito } from './cartera.js';
import { enlaceSeguro, importesAQuitar, sinImportes } from './importes.js';
import type { Alarma, Asignacion, Cliente, Crudo, Persona, Sesion } from './tipos.js';
import { contexto, soloSuCartera, ver } from './ver.js';

const COMUNES = ['id', 'nombre', 'responsable_id', 'responsable_texto', 'salud', 'salud_fuente', 'semaforo', 'nuevo', 'sin_account', 'tipo_negocio', 'activo_confirmado'] as const;
const DETALLE = ['web', 'descripcion', 'descripcion_completa', 'alta', 'tickets_abiertos', 'pend_horas', 'dias_sin_reunion', 'ult_reunion', 'prox_reunion', 'informe_anterior', 'revision48', 'enlace_clickup', 'equipo', 'servicios'] as const;
const PERSONA_PUBLICA = ['id', 'nombre', 'alias', 'puestos', 'prueba', 'estado', 'activo', 'jefe', 'zona', 'rol', 'pais', 'fecha_ingreso', 'cumple_dia_mes', 'etiquetas'] as const;

export function directorio(personas: Persona[]): Record<string, unknown>[] {
  return personas.map((p) => {
    const fila: Record<string, unknown> = {};
    for (const k of PERSONA_PUBLICA) fila[k] = p[k] ?? null;
    return fila;
  });
}

function ordenarIds(ids: Iterable<string>): string[] {
  return [...ids].sort();
}

export function metaDeCartera(meta: Record<string, unknown> | null | undefined): Record<string, unknown> {
  const m = meta ?? {};
  const out: Record<string, unknown> = {};
  for (const k of ['generado', 'construido'] as const) if (k in m) out[k] = m[k];
  if (Array.isArray(m.fuentes)) {
    out.fuentes = m.fuentes
      .filter((f): f is Record<string, unknown> => typeof f === 'object' && f !== null && !Array.isArray(f))
      .map((f) => {
        const fila: Record<string, unknown> = {};
        for (const k of ['fuente', 'estado', 'generado', 'fecha', 'actualizado'] as const) if (k in f) fila[k] = f[k];
        return fila;
      });
  }
  return out;
}

export function soloFilasDe(o: unknown, ids: Set<string>): unknown {
  if (Array.isArray(o)) {
    return o.filter((x) => !filaAjena(x, ids)).map((x) => soloFilasDe(x, ids));
  }
  if (o && typeof o === 'object') {
    return Object.fromEntries(Object.entries(o).map(([k, v]) => [k, soloFilasDe(v, ids)]));
  }
  return o;
}

function filaAjena(x: unknown, ids: Set<string>): boolean {
  if (!x || typeof x !== 'object' || Array.isArray(x)) return false;
  const cid = (x as Record<string, unknown>).cliente_id;
  if (!cid || (typeof cid === 'object' && Object.keys(cid).length === 0)) return false;
  return !(typeof cid === 'string' && ids.has(cid));
}

function quitaDe(persona: Persona, clienteId: string | undefined, cp: ReturnType<typeof contexto>): string[] {
  const ve = (tipo: string) => ver(persona, { tipo, cliente_id: clienteId }, cp).ok;
  return importesAQuitar(ve('cuota'), ve('inversion'), ve('cobros'), ve('dinero_empresa'));
}

export function recortar(persona: Persona, crudo: Crudo): Sesion {
  const cp = contexto(persona, crudo);
  const nombre: Record<string, string> = {};
  for (const p of crudo.personas) nombre[p.id] = p.alias || p.nombre;
  const clientes: Record<string, unknown>[] = [];
  const soloMios = soloSuCartera(persona);
  for (const c of crudo.clientes) {
    if (soloMios && !cp.cartera_ids.has(c.id)) continue;
    const out: Record<string, unknown> = {};
    for (const k of COMUNES) out[k] = c[k] ?? null;
    out.logo = crudo.logos?.[c.id] ?? null;
    out.responsable = c.responsable_id ? (nombre[c.responsable_id] ?? null) : c.responsable_texto || 'sin responsable';
    out.enCartera = cp.cartera_ids.has(c.id);
    out.detalle = ver(persona, { tipo: 'cliente_detalle', cliente_id: c.id }, cp).ok;
    if (out.detalle) {
      const quita = quitaDe(persona, c.id, cp);
      for (const k of DETALLE) out[k] = sinImportes(c[k] ?? null, quita);
    }
    if (ver(persona, { tipo: 'cuota', cliente_id: c.id }, cp).ok) {
      out.cuota = c.cuota ?? null;
      out.cuota_fuente = c.cuota_fuente ?? null;
    }
    if (ver(persona, { tipo: 'inversion', cliente_id: c.id }, cp).ok) {
      out.publicidad_30d = c.publicidad_30d ?? null;
    }
    clientes.push(out);
  }
  const porId: Record<string, Record<string, unknown>> = {};
  for (const c of clientes) if (typeof c.id === 'string') porId[c.id] = c;

  const alarmas: Record<string, unknown>[] = [];
  for (const a of crudo.alarmas ?? []) alarmas.push(...filaAlarma(a, persona, cp, soloMios, nombre, porId));

  const mias = crudo.asignaciones.filter(
    (a) => a.persona_id === persona.id && (!soloMios || cp.cartera_ids.has(a.cliente_id)),
  );
  const porSilla: Record<string, string[]> = {};
  for (const [k, s] of Object.entries(cp.cartera_por_silla)) porSilla[k] = ordenarIds(s);
  return {
    clientes,
    alarmas,
    carteraIds: ordenarIds(cp.cartera_ids),
    carteraPorSilla: porSilla,
    ambito: ambito(persona),
    soloSuCartera: soloMios,
    personas: directorio(crudo.personas),
    asignaciones: mias,
    meta: soloMios ? metaDeCartera(crudo.meta) : crudo.meta,
  };
}

function filaAlarma(
  a: Alarma,
  persona: Persona,
  cp: ReturnType<typeof contexto>,
  soloMios: boolean,
  nombre: Record<string, string>,
  porId: Record<string, Record<string, unknown>>,
): Record<string, unknown>[] {
  const resp = a.responsable_id ? (nombre[a.responsable_id] ?? null) : a.responsable_texto || 'sin responsable';
  if (a.ambito === 'cliente') {
    const cid = typeof a.cliente_id === 'string' ? a.cliente_id : '';
    if (soloMios && !cp.cartera_ids.has(cid)) return [];
    const fila: Record<string, unknown> = {};
    for (const k of ['id', 'cliente_id', 'cliente', 'gravedad', 'tipo', 'desde', 'responsable_id'] as const) fila[k] = a[k] ?? null;
    fila.ambito = 'cliente';
    fila.responsable = resp;
    const detalle = Boolean(porId[cid]?.detalle);
    if (detalle && ver(persona, { tipo: 'alarma_detalle', cliente_id: cid || undefined }, cp).ok) {
      const quita = quitaDe(persona, cid || undefined, cp);
      fila.texto = sinImportes(a.texto ?? null, quita);
      fila.accion = sinImportes(a.accion ?? null, quita);
      fila.enlace = enlaceSeguro(a.enlace ?? null);
    }
    return [fila];
  }
  const ok = a.responsable_id
    ? ver(persona, { tipo: 'alarma_persona', persona_id: a.responsable_id }, cp).ok
    : (persona.puestos ?? []).some((p) => p === 'direccion' || p === 'operaciones');
  if (!ok) return [];
  return [{ ...a, responsable: resp }];
}

export type { Asignacion, Cliente };
