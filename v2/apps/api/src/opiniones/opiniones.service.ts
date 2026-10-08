import { HttpException, Injectable } from '@nestjs/common';
import { Prisma } from '@ro/db';
import { cortar, horaMadrid, jsonComoPython, longitud } from '@ro/compat';
import { conVista, ver, type Persona } from '@ro/permisos';
import { permisoCaptura565 } from '../permisos/captura-opinion-565.js';
import { CrudoService } from '../permisos/crudo.service.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { RastroService } from '../rastro/rastro.service.js';
import { limpiarTexto, txt } from './limpiar-texto.js';
import { ahoraUtcTxt } from './reloj-avisos.js';

const TOPE_HORA = 20;
const MAX_CAPTURA = 190_000;
const RUTA_APP = /^#\/[\p{L}\p{N}_/%.?=&-]{0,200}$/u;
const RUTA_SENSIBLE = /sueld|n[oó]min|salari/i;
const CAPTURA_OK = /^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/;
const COLUMNAS = [
  'id',
  'creada',
  'quien',
  'tipo',
  'prioridad',
  'texto',
  'esperaba',
  'ruta',
  'pantalla',
  'ancho',
  'alto',
  'frescura',
  'captura',
  'estado',
  'estado_por',
  'estado_hora',
] as const;

type Fila = Record<string, unknown>;

function verdad(v: unknown): boolean {
  return !(v == null || v === false || v === 0 || v === '');
}

function cortarRuta(v: unknown): string {
  const base = !v ? '' : cortar(String(v), 200);
  if (base && !RUTA_APP.test(base)) return '';
  return base;
}

function esObj(x: unknown): x is Fila {
  return !!x && typeof x === 'object' && !Array.isArray(x);
}

function comoPersona(p: { id: string; nombre?: unknown; puestos?: string[] }): Persona {
  return { ...(p as Persona), nombre: typeof p.nombre === 'string' ? p.nombre : '', puestos: p.puestos ?? [] };
}

function celda(v: unknown): unknown {
  if (typeof v === 'bigint') return Number(v);
  return v ?? null;
}

/** int() de Python para un id de opinión: falta → 0; un texto que no es entero → 500. */
function idEntero(v: unknown): number {
  if (v === null || v === undefined || v === false || v === '') return 0;
  if (v === true) return 1;
  if (typeof v === 'number' && Number.isFinite(v)) return Math.trunc(v);
  if (typeof v === 'string' && /^-?[0-9]+$/.test(v.trim())) return Number(v.trim());
  throw new Error('id de opinión no entero');
}

function strPy(v: unknown): string {
  if (v === undefined || v === null) return 'None';
  if (v === true) return 'True';
  if (v === false) return 'False';
  return String(v);
}

/** servir.py › ent: entero entre 1 y 19999. bool es int en Python. */
function ent(v: unknown): number | null {
  const n = typeof v === 'boolean' ? (v ? 1 : 0) : typeof v === 'number' ? v : null;
  if (n === null || !Number.isFinite(n) || !(n > 0 && n < 20000)) return null;
  return Math.trunc(n);
}

@Injectable()
export class OpinionesService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly crudoSvc: CrudoService,
    private readonly rastro: RastroService,
  ) {}

  private todasDe(vista: VistaConContexto): boolean {
    const persona = comoPersona(vista.como ?? vista.real);
    const real = comoPersona(vista.real);
    return (
      ver(persona, { tipo: 'opiniones_ver' }, vista.cp ?? {}).ok === true &&
      ver(real, { tipo: 'opiniones_ver' }, vista.cpReal ?? vista.cp ?? {}).ok === true
    );
  }

  private aJson(r: Fila, alias: string, conCaptura = false): Fila {
    const d: Fila = {};
    for (const k of COLUMNAS) {
      if (k === 'captura') continue;
      const v = celda(r[k]);
      d[k] = v;
    }
    for (const k of ['texto', 'esperaba', 'frescura', 'pantalla'] as const) {
      if (d[k]) d[k] = limpiarTexto(d[k]);
    }
    d.tiene_captura = Boolean(r.captura);
    if (conCaptura) d.captura = r.captura ?? null;
    d.quien_alias = alias;
    return d;
  }

  private aliasDe(crudoPersonas: { id: string; alias?: string | null }[], quien: unknown): string {
    const p = crudoPersonas.find((x) => x.id === quien);
    return (p?.alias && String(p.alias)) || String(quien ?? '');
  }

  /** GET /api/opiniones. */
  async listar(vista: VistaConContexto): Promise<{ todas: boolean; opiniones: Fila[]; equipo: Record<string, { alguna: boolean; primera: string | null }> }> {
    const crudo = await this.crudoSvc.actual();
    const persona = comoPersona(vista.como ?? vista.real);
    const todas = this.todasDe(vista);
    const filas = (
      todas
        ? await this.prisma.db.$queryRaw<Fila[]>`
            SELECT id, creada, quien, tipo, prioridad, texto, esperaba, ruta, pantalla, ancho, alto, frescura, captura, estado, estado_por, estado_hora
            FROM opiniones ORDER BY id DESC LIMIT 300`
        : await this.prisma.db.$queryRaw<Fila[]>`
            SELECT id, creada, quien, tipo, prioridad, texto, esperaba, ruta, pantalla, ancho, alto, frescura, captura, estado, estado_por, estado_hora
            FROM opiniones WHERE quien = ${persona.id} ORDER BY id DESC LIMIT 300`
    ).map((r) => {
      const o: Fila = {};
      for (const [k, v] of Object.entries(r)) o[k] = celda(v);
      return o;
    });
    const suyos = (crudo.personas ?? []).filter((p) => p.jefe === persona.id && verdad(p.activo)).map((p) => p.id);
    const equipo: Record<string, { alguna: boolean; primera: string | null }> = {};
    const mins = new Map<string, string | null>();
    if (suyos.length) {
      const grupos = await this.prisma.db.$queryRaw<{ quien: string; m: string | null }[]>`
        SELECT quien, min(creada) AS m FROM opiniones WHERE quien IN (${Prisma.join(suyos)}) GROUP BY quien`;
      for (const g of grupos) mins.set(g.quien, g.m);
    }
    for (const pid of suyos) {
      const m = mins.get(pid) ?? null;
      const dia = m ? m.slice(0, 10) : '';
      equipo[pid] = { alguna: Boolean(m), primera: dia || null };
    }
    return {
      todas,
      opiniones: filas.map((r) => this.aJson(r, this.aliasDe(crudo.personas ?? [], r.quien))),
      equipo,
    };
  }

  /** GET /api/opiniones/captura?id= */
  async captura(vista: VistaConContexto, idRaw: unknown): Promise<Fila> {
    const persona = comoPersona(vista.como ?? vista.real);
    const todas = this.todasDe(vista);
    const oid = /^[0-9]+$/.test(String(idRaw ?? '0')) ? Number(idRaw) : 0;
    const filas = await this.prisma.db.$queryRaw<Fila[]>`
      SELECT id, creada, quien, tipo, prioridad, texto, esperaba, ruta, pantalla, ancho, alto, frescura, captura, estado, estado_por, estado_hora
      FROM opiniones WHERE id = ${oid} LIMIT 1`;
    const r = filas[0];
    if (!r || !(todas || r.quien === persona.id)) {
      throw new HttpException('Esa opinión no es tuya.', r ? 403 : 404);
    }
    const fila = Object.fromEntries(Object.entries(r).map(([k, v]) => [k, celda(v)]));
    const correr = (fn: () => string | null) =>
      vista.como && vista.cpReal ? conVista({ real: comoPersona(vista.real), cp: vista.cpReal }, fn) : fn();
    const uno = await this.crudoSvc.actual();
    const firma1 = await this.crudoSvc.sello();
    const a1 = correr(() => permisoCaptura565(uno, firma1, vista.real, persona, fila));
    if (a1 == null) throw new HttpException('La captura no está disponible en tu ámbito actual.', 403);
    const crudo = uno;
    const salida = this.aJson(fila, this.aliasDe(crudo.personas ?? [], fila.quien), true);
    const dos = await this.crudoSvc.actual();
    const firma2 = await this.crudoSvc.sello();
    const a2 = correr(() => permisoCaptura565(dos, firma2, vista.real, persona, fila));
    if (a2 !== a1) throw new HttpException('La captura no está disponible en tu ámbito actual.', 403);
    return salida;
  }

  /** POST /api/opinion. */
  async crear(vista: VistaConContexto, body: unknown): Promise<{ ok: true; id: number; avisado: boolean; hora: string }> {
    const b = esObj(body) ? body : {};
    const tipo = b.tipo;
    const prio = b.prioridad || 'gris';
    const texto = limpiarTexto(txt(b.texto, 2000), 2000);
    if ((tipo !== 'fallo' && tipo !== 'idea') || (prio !== 'rojo' && prio !== 'ambar' && prio !== 'gris') || longitud(texto) < 3) {
      throw new HttpException('Falta qué ha pasado (o el tipo no es «fallo» o «idea»).', 400);
    }
    const rutaApp = cortarRuta(b.ruta);
    let cap: unknown = b.captura;
    if (cap && RUTA_SENSIBLE.test(rutaApp || String(b.pantalla ?? ''))) cap = null;
    if (cap && (typeof cap !== 'string' || !CAPTURA_OK.test(cap) || cap.length > MAX_CAPTURA)) {
      throw new HttpException('La captura tiene que ser una imagen JPEG de menos de 190 KB.', 400);
    }
    const captura = typeof cap === 'string' && cap ? cap : null;
    const real = comoPersona(vista.real);
    const ancho = ent(b.ancho);
    const alto = ent(b.alto);
    const esperaba = limpiarTexto(txt(b.esperaba, 1000), 1000) || null;
    const pantalla = limpiarTexto(txt(b.pantalla, 80), 80) || null;
    const frescura = limpiarTexto(txt(b.frescura, 300), 300) || null;
    const pantallaAviso = limpiarTexto(txt(b.pantalla, 80), 80);
    const oid = await this.prisma.db.$transaction(async (t) => {
      const n = await t.$queryRaw<{ n: number }[]>`
        SELECT count(*)::int AS n FROM opiniones
        WHERE quien = ${real.id}
          AND creada >= to_char((now() AT TIME ZONE 'UTC') + interval '-1 hour', 'YYYY-MM-DD HH24:MI:SS')`;
      if ((n[0]?.n ?? 0) >= TOPE_HORA) {
        throw new HttpException('Muchos avisos en una hora: espera un poco o escribe a Mili.', 429);
      }
      const filas = await t.$queryRaw<{ id: bigint }[]>`
        INSERT INTO opiniones (quien, tipo, prioridad, texto, esperaba, ruta, pantalla, ancho, alto, frescura, captura)
        VALUES (${real.id}, ${tipo}, ${prio}, ${texto}, ${esperaba}, ${rutaApp || null}, ${pantalla}, ${ancho}, ${alto}, ${frescura}, ${captura})
        RETURNING id`;
      const id = Number(filas[0]?.id);
      await this.rastro.registrar(t, {
        quien: real.id,
        coleccion: 'opiniones',
        accion: 'opinion_enviada',
        clave: String(id),
        datos: { tipo, prioridad: prio, ruta: rutaApp, ancho, captura: Boolean(captura), largo: longitud(texto) },
      });
      return id;
    });
    const avisado = await this.avisar(real, oid, {
      tipo,
      prioridad: String(prio),
      texto,
      pantalla: pantallaAviso,
      ruta: rutaApp,
      ancho,
    });
    return { ok: true, id: oid, avisado, hora: horaMadrid(new Date(), '') };
  }

  /** POST /api/opiniones/estado. El permiso opiniones_ver lo declara el controlador. */
  async estado(vista: VistaConContexto, body: unknown): Promise<{ ok: true }> {
    const b = esObj(body) ? body : {};
    const est = b.estado;
    if (est !== 'vista' && est !== 'resuelta' && est !== 'nueva') throw new HttpException('Estado no válido.', 400);
    const id = idEntero(b.id);
    const real = vista.real;
    await this.prisma.db.$transaction(async (t) => {
      const filas = await t.$queryRaw<{ id: number }[]>`
        UPDATE opiniones
        SET estado = ${est}, estado_por = ${real.id},
            estado_hora = to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
        WHERE id = ${id}
        RETURNING id`;
      if (!filas.length) throw new HttpException('No existe esa opinión.', 404);
      await this.rastro.registrar(t, {
        quien: real.id,
        coleccion: 'opiniones',
        accion: `opinion_${est}`,
        clave: strPy(b.id),
      });
    });
    return { ok: true };
  }

  /** servir.py › avisar_opinion + avisos.publicar. Fuera de la transacción de la opinión: un fallo no la deshace. */
  private async avisar(
    real: Persona,
    oid: number,
    b: { tipo: string; prioridad: string; texto: string; pantalla: string; ruta: string; ancho: number | null },
  ): Promise<boolean> {
    try {
      const que = b.tipo === 'fallo' ? 'Algo va mal' : 'Idea';
      const prio = b.prioridad === 'rojo' ? ' · rojo' : b.prioridad === 'ambar' ? ' · ámbar' : '';
      const alias = (typeof real.alias === 'string' && real.alias) || real.id;
      const donde = b.pantalla || b.ruta || 'la app';
      const px = b.ancho == null ? '?' : String(b.ancho);
      const texto = `${que}${prio} · ${alias} en «${donde}» (${px} px): «${txt(limpiarTexto(b.texto), 220)}»`;
      const menciones = ['tomas', 'mili'].filter((x) => x !== real.id);
      return await this.publicar('avisos-direccion', 'evento', texto, `opinion:${oid}`, {
        quien: real.id,
        duenoId: 'tomas',
        menciones,
        ver: { puestos: ['direccion', 'operaciones'] },
        datos: { icono: b.tipo === 'fallo' ? 'alert' : 'spark', ir: '#/ajustes/opiniones' },
      });
    } catch {
      return false;
    }
  }

  /** avisos.publicar. None (clave repetida) → false. */
  private async publicar(
    canalId: string,
    tipo: string,
    texto: string,
    clave: string,
    o: { quien: string; duenoId: string; menciones: string[]; ver: { puestos: string[] }; datos: Fila },
  ): Promise<boolean> {
    const ya = await this.prisma.db.$queryRaw<{ ok: number }[]>`SELECT 1 AS ok FROM canal_mensajes WHERE clave = ${clave} LIMIT 1`;
    if (ya.length) return false;
    const filas = await this.prisma.db.$queryRaw<{ id: bigint }[]>`
      INSERT INTO canal_mensajes (canal_id, tipo, quien, texto, hilo_de, menciones, clave, alerta_id, cliente_id, dueno_id, vence, ver, datos, creado)
      VALUES (
        ${canalId}, ${tipo}, ${o.quien}, ${texto}, ${null}, ${jsonComoPython(o.menciones)}, ${clave}, ${null}, ${null},
        ${o.duenoId}, ${null}, ${jsonComoPython(o.ver)}, ${jsonComoPython(o.datos, { ensureAscii: false })}, ${ahoraUtcTxt()}
      )
      RETURNING id`;
    return Boolean(filas[0]?.id);
  }
}
