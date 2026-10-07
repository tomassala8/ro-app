import { existsSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { inflateSync } from 'node:zlib';
import { Injectable, Logger } from '@nestjs/common';
import { hoyIso, type Alarma, type Asignacion, type Cliente, type Crudo, type Persona } from '@ro/permisos';
import { PrismaService } from '../prisma/prisma.service.js';

/** E.crudo de servir.py: los datos base de la versión vigente de `data` más lo cambiado en Ajustes. */
export interface CrudoRo extends Crudo {
  para_confirmar: unknown[];
}

/** Lo que guarda la caché: el crudo y lo que la identidad necesita de la misma versión. */
interface Cargado {
  marca: string;
  version: number;
  crudo: CrudoRo;
  correosEntrada: Record<string, string>;
}

/** Raíz del repositorio (como reglas_permisos.json y modulos/ en @ro/permisos). */
const RAIZ = fileURLToPath(new URL('../../../../../', import.meta.url));

/** servir.py › NUCLEO, en el mismo orden. */
const NUCLEO = ['personas', 'asignaciones', 'clientes', 'alarmas', 'logos', 'meta'] as const;
/** fuentes_verdad/clientes_activos.py */
const BAJAS_CONFIRMADAS = new Set(['medalba']);
const TIPOS_ACTIVOS = new Set(['activo', 'recurrente', 'proyecto', 'firmado_sin_ficha']);

/** despliegue/publicacion.py › _bajo(R["APP"], "APP", "data"): las rutas del espacio `data` llevan este prefijo. */
const PREFIJO = 'APP/data/';
/** Versión «0»: sin `data` publicada en la base, se lee servir.py › DATA (AQUI / "data"). */
const EN_DISCO = 0;
const DATA_DISCO = join(RAIZ, 'data');
const FICHEROS_DISCO = [...NUCLEO.map((n) => `${n}.json`), 'para_confirmar.json', 'ids_clientes.json', 'verdad/estado_clientes.json', '_privado/correos_entrada.json'];
const mtime = (f: string) => {
  try {
    return String(statSync(f).mtimeMs);
  } catch {
    return '-';
  }
};

type Obj = Record<string, unknown>;
const esObj = (x: unknown): x is Obj => typeof x === 'object' && x !== null && !Array.isArray(x);

@Injectable()
export class CrudoService {
  private readonly registro = new Logger('CrudoService');
  private cargado?: Cargado;
  private enCurso?: { marca: string; promesa: Promise<Cargado> };
  private avisadoPara = -1;
  private avisadoDisco = false;

  constructor(private readonly prisma: PrismaService) {}

  /** servir.py › E.crudo, recargado si cambian la versión de `data`, Ajustes (historial, decisiones) o el día. */
  async actual(): Promise<CrudoRo> {
    return (await this.vigente()).crudo;
  }

  /** Marca del crudo (versión, disco, historial, decisiones y día). Sirve para ver si cambió a mitad de una lectura. */
  async sello(): Promise<string> {
    return (await this.marca()).marca;
  }

  /** data/_privado/correos_entrada.json › correos de la misma versión. Solo para la identidad: nunca sale en una respuesta. */
  async correosEntrada(): Promise<Record<string, string>> {
    return (await this.vigente()).correosEntrada;
  }

  /**
   * Un fichero JSON de la versión vigente de `data` (ruta relativa a data/: «personas.json»). undefined si no está.
   * Versión EN_DISCO: la base no tiene `data` publicada (las bases de prueba de base-limpia) y se lee, sin escribir
   * nunca, la misma carpeta que servir.py › DATA.
   */
  async fichero(ruta: string, version?: number): Promise<unknown> {
    const v = version ?? (await this.marca()).version;
    if (v === EN_DISCO) {
      const f = join(DATA_DISCO, ruta);
      return existsSync(f) ? JSON.parse(readFileSync(f, 'utf8')) : undefined;
    }
    const filas = await this.prisma.db.$queryRaw<{ contenido: Uint8Array }[]>`
      SELECT b.contenido FROM datos_fichero f JOIN datos_blob b ON b.sha = f.sha
      WHERE f.version = ${v} AND f.ruta = ${PREFIJO + ruta}`;
    const fila = filas[0];
    if (!fila) return undefined;
    return JSON.parse(inflateSync(Buffer.from(fila.contenido)).toString('utf8'));
  }

  private async marca(): Promise<{ version: number; marca: string }> {
    const [m] = await this.prisma.db.$queryRaw<{ v: number | null; h: string | null; d: string | null }[]>`
      SELECT (SELECT id FROM datos_version WHERE estado = 'vigente' AND espacio = 'data' ORDER BY id DESC LIMIT 1)::int AS v,
             (SELECT max(n) FROM historial)::text AS h,
             (SELECT max(id) FROM decisiones)::text AS d`;
    const version = m?.v ?? EN_DISCO;
    if (version === EN_DISCO && this.avisadoDisco !== true) {
      this.registro.warn(`La base no tiene data publicada: el crudo se lee de ${DATA_DISCO} (solo lectura), como servir.py.`);
      this.avisadoDisco = true;
    }
    // En disco, como servir.py › recargar_si_cambian: la hora de modificación de cada fichero.
    const disco = version === EN_DISCO ? FICHEROS_DISCO.map((f) => mtime(join(DATA_DISCO, f))).join(',') : '';
    // El día entra en la marca: el responsable de cada cliente sale de las asignaciones vigentes hoy.
    return { version, marca: [version, disco, m?.h, m?.d, hoyIso()].join('|') };
  }

  private async vigente(): Promise<Cargado> {
    const { version, marca } = await this.marca();
    if (this.cargado?.marca === marca) return this.cargado;
    if (this.enCurso?.marca === marca) return this.enCurso.promesa;
    const promesa = this.cargar(version, marca);
    this.enCurso = { marca, promesa };
    try {
      this.cargado = await promesa;
      return this.cargado;
    } finally {
      if (this.enCurso?.promesa === promesa) this.enCurso = undefined;
    }
  }

  /** servir.py › Estado.cargar(), en el mismo orden (sin la puerta de secretos: la sigue haciendo el legado). */
  private async cargar(version: number, marca: string): Promise<Cargado> {
    const crudo: Obj = {};
    for (const n of NUCLEO) {
      const v = await this.fichero(`${n}.json`, version);
      if (v === undefined) throw new Error(`Falta data/${n}.json en la versión ${version}.`);
      crudo[n] = v;
    }
    crudo.para_confirmar = (await this.fichero('para_confirmar.json', version)) ?? [];
    const ids = (await this.fichero('ids_clientes.json', version)) as Obj | undefined;
    const idApp = (esObj(ids) && esObj(ids.portal_a_app) ? ids.portal_a_app : {}) as Obj;
    const estadoClientes = ((await this.fichero('verdad/estado_clientes.json', version)) ?? null) as Obj | null;
    const c = crudo as unknown as CrudoRo;
    aplicarServicios(c.clientes, estadoClientes ?? {});
    await this.aplicarAjustes(c, version, idApp);
    limpiarNucleo(c, estadoClientes);
    quitarCorreosRepetidos(c.personas);
    const privados = (await this.fichero('_privado/correos_entrada.json', version)) as Obj | undefined;
    const correos = esObj(privados) && esObj(privados.correos) ? (privados.correos as Record<string, string>) : {};
    return { marca, version, crudo: c, correosEntrada: correos };
  }

  /** servir.py › Estado.aplicar_ajustes: reaplica, en orden, lo cambiado en Ajustes (historial y decisiones). */
  private async aplicarAjustes(crudo: CrudoRo, version: number, _idApp: Obj): Promise<void> {
    const filas = await this.prisma.db.$queryRaw<{ coleccion: string; operacion: string; id: string; datos: string | null }[]>`
      SELECT coleccion, operacion, id, datos FROM historial WHERE coleccion IN ('personas', 'asignaciones') ORDER BY n`;
    const decis = await this.prisma.db.$queryRaw<{ id: number; anula_a: number | null; respuesta: string | null }[]>`
      SELECT id::int AS id, anula_a::int AS anula_a, respuesta FROM decisiones WHERE tipo = 'para_confirmar' ORDER BY id`;
    const porPersona = new Map<string, Persona>();
    for (const p of crudo.personas) porPersona.set(p.id, p);
    for (const h of filas) {
      const d = JSON.parse(h.datos || '{}') as Obj;
      if (h.coleccion === 'personas' && h.operacion === 'cambiar' && porPersona.has(h.id)) {
        Object.assign(porPersona.get(h.id)!, d);
      } else if (h.coleccion === 'asignaciones' && h.operacion === 'crear') {
        crudo.asignaciones.push(d as unknown as Asignacion);
      } else if (h.coleccion === 'asignaciones' && (h.operacion === 'cerrar' || h.operacion === 'confirmar')) {
        for (const a of crudo.asignaciones as (Asignacion & Obj)[]) {
          if (a.cliente_id === d.cliente_id && a.silla === d.silla && a.persona_id === d.persona_id && !a.hasta) {
            if (h.operacion === 'cerrar') a.hasta = d.hasta as string;
            else a.confianza = 'confirmada';
          }
        }
      }
    }
    // F5.1: las respuestas a «para confirmar» las aplica altas_personas.py (aplicar_respuestas), que no se porta esta
    // noche. Si hay alguna, se dice en el registro: el crudo de Nest no las lleva y la sesión saldría distinta.
    const anuladas = new Set(decis.map((r) => r.anula_a).filter((x) => x));
    const pendientes = decis.filter((r) => !anuladas.has(r.id) && !r.anula_a && r.respuesta).length;
    if (pendientes && this.avisadoPara !== version) {
      this.avisadoPara = version;
      this.registro.warn(`F5.1: decisiones para_confirmar sin aplicar: ${pendientes}`);
    }
    const fechaHoy = hoyIso();
    for (const c of crudo.clientes) {
      const acc = (crudo.asignaciones as (Asignacion & Obj)[]).filter(
        (a) =>
          a.cliente_id === c.id &&
          a.silla === 'account' &&
          (a.principal ?? true) &&
          !a.suplencia &&
          (!a.desde || a.desde <= fechaHoy) &&
          (!a.hasta || a.hasta >= fechaHoy),
      );
      const ultima = acc[acc.length - 1];
      if (ultima) {
        c.responsable_id = ultima.persona_id;
        c.sin_account = null;
      }
    }
  }
}

/** Ruta del catálogo de servicios confirmados (fuentes_verdad/servicios_confirmados.json, fuera de git y de data/). */
function rutaServicios(): string {
  return process.env.RO_SERVICIOS_CONFIRMADOS ?? `${RAIZ}fuentes_verdad/servicios_confirmados.json`;
}

/** fuentes_verdad/servicios_confirmados.py › aplicar. Sin el fichero, los clientes salen como en data/clientes.json. */
export function aplicarServicios(clientes: Cliente[], estado: Obj, fuente = rutaServicios()): Cliente[] {
  if (!existsSync(fuente)) return clientes;
  const evidencia = JSON.parse(readFileSync(fuente, 'utf8')) as { clientes?: Obj[] };
  const bajas = new Set<unknown>([
    ...((estado.bajas_ids as unknown[]) ?? []),
    ...((estado.bajas as Obj[]) ?? []).map((x) => x.cliente_id),
  ]);
  const porId = new Map<unknown, Obj>();
  for (const x of evidencia.clientes ?? []) porId.set(x.cliente_id, x);
  for (const cliente of clientes) {
    const cid = cliente.id;
    const fila = porId.get(cid);
    if (!fila || bajas.has(cid)) continue;
    if (cliente.servicios === undefined || cliente.servicios === null) cliente.servicios = {};
    const servicios = cliente.servicios as Record<string, string>;
    for (const [nombre, valor] of Object.entries((fila.servicios as Obj) ?? {})) {
      if (valor !== 'sí') continue;
      servicios[nombre] = valor;
      servicios[`${nombre}_fuente`] = `${textoPy(fila.fuente)} · fila ${textoPy(fila.fila)} · ${textoPy(fila.leida)}`;
    }
  }
  return clientes;
}

/** str() de Python para lo que trae el catálogo (textos y enteros; None si falta). */
function textoPy(x: unknown): string {
  if (x === null || x === undefined) return 'None';
  if (typeof x === 'boolean') return x ? 'True' : 'False';
  return String(x);
}

/** fuentes_verdad/clientes_activos.py › estado()["_activos"]. Sin el fichero, ningún cliente es activo. */
export function activosDe(estado: Obj | null): Set<string> {
  if (!estado) return new Set();
  const ids = new Set<unknown>([...((estado.bajas_ids as unknown[]) ?? []), ...BAJAS_CONFIRMADAS]);
  const out = new Set<string>();
  for (const a of (estado.activos as Obj[]) ?? []) {
    if (a.id && TIPOS_ACTIVOS.has(a.tipo as string) && !ids.has(a.id)) out.add(a.id as string);
  }
  return out;
}

/** fuentes_verdad/clientes_activos.py › limpiar_nucleo: clientes de baja fuera de los datos base. */
export function limpiarNucleo(crudo: CrudoRo, estado: Obj | null): string[] {
  const activos = activosDe(estado);
  const esActivo = (cid: unknown) => typeof cid === 'string' && activos.has(cid);
  const ids = new Set(crudo.clientes.filter((c) => !esActivo(c.id)).map((c) => c.id));
  const fuera = [...ids].sort();
  crudo.clientes = crudo.clientes.filter((c) => esActivo(c.id));
  for (const c of crudo.clientes) c.activo_confirmado = true;
  if (Array.isArray(crudo.asignaciones)) crudo.asignaciones = crudo.asignaciones.filter((a) => esActivo(a.cliente_id));
  if (Array.isArray(crudo.alarmas)) crudo.alarmas = crudo.alarmas.filter((a: Alarma) => !a.cliente_id || esActivo(a.cliente_id));
  if (esObj(crudo.logos)) crudo.logos = Object.fromEntries(Object.entries(crudo.logos).filter(([k]) => !ids.has(k)));
  return fuera;
}

/** servir.py › Estado.sembrar_tablas (solo la parte que cambia el crudo): un correo repetido se ignora en la segunda persona. */
export function quitarCorreosRepetidos(personas: Persona[]): void {
  const vistos = new Set<string>();
  const limpio = (x: unknown) => (typeof x === 'string' ? x : '').trim().toLowerCase();
  for (const p of personas) {
    for (const bruto of [p.correo, ...((p.otros_correos as unknown[]) ?? [])]) {
      const c = limpio(bruto);
      if (!c) continue;
      if (vistos.has(c)) {
        if (limpio(p.correo) === c) p.correo = null;
        p.otros_correos = ((p.otros_correos as string[]) ?? []).filter((x) => x.trim().toLowerCase() !== c);
      }
      vistos.add(c);
    }
  }
}
