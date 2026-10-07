import { Injectable } from '@nestjs/common';
import { jsonComoPython } from '@ro/compat';
import { Prisma } from '@ro/db';
import {
  CLAVES_COBROS,
  CLAVES_CUOTA,
  CLAVES_DINERO_CAPTACION,
  CLAVES_INVERSION,
  CLAVES_LEAD,
  DINERO_CUOTA_VALOR,
  DINERO_EMPRESA,
  DINERO_INVERSION_VALOR,
  contexto,
  reglas,
  ver,
  type Contexto,
  type Crudo,
  type Persona,
  type QuitaClave,
} from '@ro/permisos';
import { CrudoService } from '../permisos/crudo.service.js';
import { modulosActuales } from '../permisos/recarga.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { PrismaService } from '../prisma/prisma.service.js';

const RANGO: Record<string, number> = { resumen: 1, suyo: 2, todo: 3 };
const LEAD_NOMBRES = new Set(['nombre', 'name', 'email', 'correo', 'phone']);
const LEAD_RAMAS = new Set(['leads', 'leads_detalle', 'contactos_lead']);
const SERIES = new Set(['serie', 'serie_ant', 'serie_anio']);
const META_SI = new Set(['campanas', 'conjuntos', 'gasto', 'cpl', 'actual', 'presupuesto']);
const META_NO = new Set(['clics', 'impresiones_web', 'usuarios']);

type Fila = Record<string, unknown>;

function nivelSinVista(persona: { puestos?: string[] }, mapa: Record<string, string | null> | undefined): string | null {
  if (!mapa) return null;
  let mejor: string | null = null;
  for (const p of persona.puestos ?? []) {
    const n = (p in mapa ? mapa[p] : mapa['*']) ?? null;
    if (n && (!mejor || (RANGO[n] ?? 0) > (RANGO[mejor] ?? 0))) mejor = n;
  }
  return mejor;
}

/** servir.py › ve_alguno, sin la vista global: el mínimo lo calculan las dos personas por separado. */
export function veAlguno(persona: { puestos?: string[] }, mods: string[]): string | null {
  const mapas = modulosActuales();
  const niveles = mods.map((m) => nivelSinVista(persona, mapas[m])).filter((n): n is string => !!n);
  if (!niveles.length) return null;
  return niveles.reduce((a, b) => ((RANGO[a] ?? 0) >= (RANGO[b] ?? 0) ? a : b));
}

export function moduloConocido(col: string): boolean {
  return Object.prototype.hasOwnProperty.call(modulosActuales(), col);
}

function idsDePuesto(): Set<string> {
  const lista = reglas().puestos;
  return new Set(lista.map((p) => p.id));
}

function canonica(crudo: Crudo, identidad: { id?: unknown; puestos?: unknown }): Persona | null {
  if (typeof identidad.id !== 'string' || !identidad.id) return null;
  const xs = (crudo.personas ?? []).filter((p) => p && p.id === identidad.id);
  const roles = identidad.puestos;
  const validos = idsDePuesto();
  if (
    xs.length !== 1 ||
    xs[0]?.estado !== 'activo' ||
    xs[0]?.activo === false ||
    !Array.isArray(roles) ||
    roles.length === 0 ||
    !roles.every((r) => typeof r === 'string' && validos.has(r)) ||
    new Set(roles).size !== roles.length ||
    [...(xs[0]?.puestos ?? [])].sort().join('\0') !== [...roles].sort().join('\0')
  ) {
    return null;
  }
  return xs[0] ?? null;
}

/** acciones_lectura_544 › ambito, sin la firma de Python: aquí la marca del crudo cumple el mismo papel. */
export function ambitoDe(crudo: Crudo, real: { id?: unknown; puestos?: unknown }, persona: { id?: unknown; puestos?: unknown }): { ps: Persona[]; cps: Contexto[] } | null {
  try {
    const ps = [canonica(crudo, real), canonica(crudo, persona)];
    if (ps.some((p) => !p)) return null;
    const buenos = ps as Persona[];
    return { ps: buenos, cps: buenos.map((p) => contexto(p, crudo)) };
  } catch {
    return null;
  }
}

export function clienteVisible(cid: unknown, crudo: Crudo, ps: Persona[], cps: Contexto[]): boolean {
  try {
    if (typeof cid !== 'string' || !cid) return false;
    const cs = (crudo.clientes ?? []).filter((c) => c && c.id === cid);
    const activos = new Set((crudo.clientes ?? []).map((c) => c.id));
    return (
      cs.length === 1 &&
      cs[0]?.activo !== false &&
      cs[0]?.estado !== 'baja' &&
      activos.has(cid) &&
      ps.every((p, i) => ver(p, { tipo: 'cliente_detalle', cliente_id: cid }, cps[i] ?? {}).ok === true)
    );
  } catch {
    return false;
  }
}

export function filaVisible(
  r: Fila,
  crudo: Crudo,
  ps: Persona[],
  cps: Contexto[],
  vistaId: string,
): boolean {
  try {
    const modulo = r.modulo;
    if (!modulo || !ps.every((p) => veAlguno(p, [String(modulo)]))) return false;
    if (r.cliente_id == null) {
      return r.quien === vistaId || ps.every((p) => veAlguno(p, [String(modulo)]) === 'todo');
    }
    return clienteVisible(r.cliente_id, crudo, ps, cps);
  } catch {
    return false;
  }
}

function serieDeMeta(bloque: Fila): boolean {
  const normal = new Map(Object.entries(bloque).map(([k, v]) => [k.toLowerCase(), v]));
  const ser = normal.get('serie');
  if (Array.isArray(ser) && ser.length && ser[0] && typeof ser[0] === 'object' && !Array.isArray(ser[0])) {
    const claves = new Set(Object.keys(ser[0] as object).map((k) => k.toLowerCase()));
    if (claves.has('meta')) return true;
  }
  const keys = new Set(normal.keys());
  const tiene = [...META_SI].some((k) => keys.has(k));
  const no = [...META_NO].some((k) => keys.has(k));
  return tiene && !no;
}

function serieSinGasto(serie: unknown): unknown {
  if (!Array.isArray(serie)) return serie;
  return serie.map((x) => {
    if (Array.isArray(x) && x.length >= 3 && typeof x[0] === 'string') return [x[0], null, ...x.slice(2)];
    if (x && typeof x === 'object' && !Array.isArray(x)) {
      const y: Fila = {};
      for (const [k, w] of Object.entries(x as Fila)) {
        if (!CLAVES_INVERSION.quita(k, w)) y[k] = w;
      }
      const metaKey = Object.keys(y).find((k) => k.toLowerCase() === 'meta');
      if (metaKey && Array.isArray(y[metaKey]) && (y[metaKey] as unknown[]).length) {
        const lista = y[metaKey] as unknown[];
        y[metaKey] = [null, ...lista.slice(1)];
      }
      return y;
    }
    return x;
  });
}

/** servir.py › recortar_doc. Conserva el orden de las claves. */
export function recortarDoc(obj: unknown, quitar: QuitaClave[], lead = false): unknown {
  if (Array.isArray(obj)) return obj.map((v) => recortarDoc(v, quitar, lead));
  if (obj && typeof obj === 'object') {
    const o = obj as Fila;
    const meta = quitar.includes(CLAVES_INVERSION) && serieDeMeta(o);
    const out: Fila = {};
    for (const [k, v] of Object.entries(o)) {
      if (quitar.some((rx) => rx.quita(k, v))) continue;
      if (lead && LEAD_NOMBRES.has(k.toLowerCase())) continue;
      const hijoLead = lead || LEAD_RAMAS.has(k.toLowerCase());
      const rec = recortarDoc(v, quitar, hijoLead);
      out[k] = meta && SERIES.has(k.toLowerCase()) ? serieSinGasto(rec) : rec;
    }
    return out;
  }
  return obj;
}

/** servir.py › quitar_para, con las mismas piezas que F4.1 dejó en @ro/permisos. */
export function quitarPara(persona: Persona, cp: Contexto, clienteId: unknown): QuitaClave[] {
  const cid = typeof clienteId === 'string' ? clienteId : undefined;
  const ve = (t: string) => ver(persona, { tipo: t, cliente_id: cid }, cp).ok;
  const q: QuitaClave[] = [CLAVES_LEAD];
  if (!ve('cuota')) q.push(CLAVES_CUOTA, DINERO_CUOTA_VALOR);
  if (!ve('cobros')) q.push(CLAVES_COBROS);
  if (!ve('inversion')) q.push(CLAVES_INVERSION, DINERO_INVERSION_VALOR);
  if (!ve('dinero_empresa')) q.push(DINERO_EMPRESA);
  return q;
}

/** acciones_lectura_544 › recortar_vistas. */
export function recortarVistas(filas: Fila[], quitar: (cid: unknown) => QuitaClave[]): Fila[] {
  const tipos = new Set(
    ((reglas() as { acciones_vista_previa_recortada?: string[] }).acciones_vista_previa_recortada ?? []),
  );
  return filas.map((r) => {
    const copia = { ...r };
    if (tipos.has(String(copia.tipo ?? '')) && copia.vista_previa) {
      let vp: unknown = null;
      try {
        vp = JSON.parse(String(copia.vista_previa));
      } catch {
        vp = null;
      }
      const q = quitar(copia.cliente_id);
      if (q.includes(CLAVES_INVERSION)) q.push(CLAVES_DINERO_CAPTACION);
      const rec = vp && typeof vp === 'object' && !Array.isArray(vp) ? recortarDoc(vp, q) : null;
      copia.vista_previa = jsonComoPython(rec, { ensureAscii: false });
    }
    return copia;
  });
}

function celda(k: string, v: unknown): unknown {
  if (typeof v === 'bigint') return Number(v);
  if ((k === 'id' || k === 'anula_a') && typeof v === 'string' && /^\d+$/.test(v)) return Number(v);
  return v;
}

function fila(r: Fila): Fila {
  const o: Fila = {};
  for (const [k, v] of Object.entries(r)) o[k] = celda(k, v);
  return o;
}

/** GET /api/rastro: el ámbito, las 500 filas y las acciones visibles. */
@Injectable()
export class RastroLecturaService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly crudo: CrudoService,
  ) {}

  async leer(vista: VistaConContexto): Promise<{ todo: boolean; registro: Fila[]; acciones: Fila[] }> {
    const crudo = await this.crudo.actual();
    const sello = await this.crudo.sello();
    const real = vista.real;
    const persona = vista.como ?? vista.real;
    const ambito = ambitoDe(crudo, real, persona);
    if (!ambito) throw new Error('AMBITO');
    const { ps, cps } = ambito;
    const auditorias = ps.map((p, i) => ver(p, { tipo: 'rastro_todo' }, cps[i] ?? {}).ok);
    const mirando = real.id !== persona.id;
    const todo = !mirando && auditorias.every(Boolean);
    const limitados = ps.filter((_, i) => !auditorias[i]).map((p) => p.id);
    const registro = mirando
      ? await this.prisma.db.$queryRaw<Fila[]>`
          SELECT * FROM registro WHERE quien = ${real.id} AND como = ${persona.id} ORDER BY id DESC LIMIT 500`
      : await this.filasRegistro(limitados);
    let acciones: Fila[] = [];
    if (!mirando) acciones = await this.filasAcciones(limitados);
    acciones = acciones.map(fila).filter((r) => filaVisible(r, crudo, ps, cps, persona.id));
    const vistaPersona = ps[1];
    const cpVista = cps[1];
    if (vistaPersona && cpVista) {
      acciones = recortarVistas(acciones, (cid) => quitarPara(vistaPersona, cpVista, cid));
    }
    if ((await this.crudo.sello()) !== sello) throw new Error('CAMBIO');
    return { todo, registro: registro.map(fila), acciones };
  }

  private async filasRegistro(limitados: string[]): Promise<Fila[]> {
    if (!limitados.length) {
      return this.prisma.db.$queryRaw<Fila[]>`SELECT * FROM registro ORDER BY id DESC LIMIT 500`;
    }
    const partes = limitados.map((id) => Prisma.sql`(quien = ${id} OR como = ${id})`);
    return this.prisma.db.$queryRaw<Fila[]>`SELECT * FROM registro WHERE ${Prisma.join(partes, ' AND ')} ORDER BY id DESC LIMIT 500`;
  }

  private async filasAcciones(limitados: string[]): Promise<Fila[]> {
    if (!limitados.length) {
      return this.prisma.db.$queryRaw<Fila[]>`SELECT * FROM acciones ORDER BY id DESC LIMIT 200`;
    }
    const partes = limitados.map((id) => Prisma.sql`quien = ${id}`);
    return this.prisma.db.$queryRaw<Fila[]>`SELECT * FROM acciones WHERE ${Prisma.join(partes, ' AND ')} ORDER BY id DESC LIMIT 200`;
  }
}
