import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Injectable } from '@nestjs/common';
import { cortar, huellaRastro } from '@ro/compat';
import { PrismaService } from '../prisma/prisma.service.js';

/** Misma raíz que CrudoService y cargarModulos (el repositorio, no v2/). */
const RAIZ = fileURLToPath(new URL('../../../../../', import.meta.url));

type Fila = {
  id: bigint | number | string;
  creada: string;
  quien: string;
  como: string | null;
  coleccion: string;
  accion: string | null;
  clave: string | null;
  datos: string | null;
  motivo: string | null;
  anula_a: bigint | number | string | null;
  origen: string;
  huella_previa: string | null;
  huella_guardada: string;
};

function num(v: bigint | number | string | null | undefined): number | null {
  if (v == null || v === '') return null;
  return Number(v);
}

function vacio(v: string | null | undefined): string | null {
  return v || null;
}

export interface Cadena {
  ok: boolean;
  primera_fila_rota: number | null;
  filas_encadenadas: number;
  tras_anotacion?: { desde: number | null; ok: boolean; primera_fila_rota: number | null; filas: number };
  anclas?: { ok: boolean; comprobadas: number; malas: Record<string, unknown>[] };
}

/** servir.py › verificar_rastro, fila_tras_anotacion, cortes_anotados y comprobar_anclas. Solo lee. */
@Injectable()
export class VerificarService {
  constructor(private readonly prisma: PrismaService) {}

  private anclasRuta(): string {
    return process.env.RO_ANCLAS ?? join(RAIZ, 'despliegue', 'estado', 'anclas_rastro.jsonl');
  }

  /** `desde` es el query (undefined, «anotado» o dígitos). Undefined añade la segunda pasada y las anclas. */
  async verificar(desde: string | undefined): Promise<Cadena> {
    const primera = await this.cadena(desde === 'anotado' ? await this.filaTrasAnotacion() : num(desde));
    const res: Cadena = {
      ok: primera.ok,
      primera_fila_rota: primera.primera_fila_rota,
      filas_encadenadas: primera.filas,
    };
    if (desde === undefined) {
      const tras = await this.filaTrasAnotacion();
      const segunda = await this.cadena(tras);
      res.tras_anotacion = {
        desde: tras,
        ok: segunda.ok,
        primera_fila_rota: segunda.primera_fila_rota,
        filas: segunda.filas,
      };
      res.anclas = await this.comprobarAnclas();
    }
    return res;
  }

  private async filaTrasAnotacion(): Promise<number | null> {
    let ult: number | null = null;
    try {
      const [m] = await this.prisma.db.$queryRaw<{ m: bigint | number | null }[]>`SELECT max(hasta) AS m FROM rastro_incidencias`;
      ult = num(m?.m);
    } catch {
      ult = null;
    }
    const [c] = await this.prisma.db.$queryRaw<{ m: bigint | number | null }[]>`SELECT coalesce(max(id), 0) AS m FROM rastro_cortes`;
    const tope = Math.max(ult || 0, Number(c?.m ?? 0) || 0);
    return tope ? tope + 1 : null;
  }

  private async cortes(): Promise<Set<number>> {
    const ids = await this.prisma.db.$queryRaw<{ id: bigint | number }[]>`SELECT id FROM rastro_cortes`;
    const set = new Set(ids.map((r) => Number(r.id)));
    try {
      const rangos = await this.prisma.db.$queryRaw<{ desde: bigint | number; hasta: bigint | number }[]>`
        SELECT desde, hasta FROM rastro_incidencias WHERE tipo = 'corte'`;
      for (const r of rangos) {
        for (let i = Number(r.desde); i <= Number(r.hasta); i++) set.add(i);
      }
    } catch {
      /* la tabla puede no existir: igual que servir.py */
    }
    return set;
  }

  private async cadena(desde: number | null): Promise<{ ok: boolean; primera_fila_rota: number | null; filas: number }> {
    const inicio = desde || 0;
    const filas = await this.prisma.db.$queryRaw<Fila[]>`
      SELECT r.*, h.huella AS huella_guardada FROM registro r
      JOIN registro_huellas h ON h.id = r.id
      WHERE r.id >= ${inicio} ORDER BY r.id`;
    const cortes = await this.cortes();
    let previa: string | null = desde && filas.length ? vacio(filas[0]?.huella_previa) : null;
    for (const r of filas) {
      const id = Number(r.id);
      const guardadaPrevia = vacio(r.huella_previa);
      if (guardadaPrevia !== previa && !cortes.has(id)) return { ok: false, primera_fila_rota: id, filas: filas.length };
      if (cortes.has(id) && guardadaPrevia !== previa) previa = guardadaPrevia;
      const h = huellaRastro(previa, [
        id,
        r.creada,
        r.quien,
        r.como,
        r.coleccion,
        r.accion,
        r.clave,
        r.datos,
        r.motivo,
        num(r.anula_a),
        r.origen,
      ]);
      if (h !== r.huella_guardada) return { ok: false, primera_fila_rota: id, filas: filas.length };
      previa = h;
    }
    return { ok: true, primera_fila_rota: null, filas: filas.length };
  }

  private async comprobarAnclas(): Promise<{ ok: boolean; comprobadas: number; malas: Record<string, unknown>[] }> {
    const ruta = this.anclasRuta();
    if (!existsSync(ruta)) return { ok: true, comprobadas: 0, malas: [] };
    const malas: Record<string, unknown>[] = [];
    let n = 0;
    for (const linea of readFileSync(ruta, 'utf8').split('\n')) {
      if (!linea.trim()) continue;
      let a: Record<string, unknown>;
      try {
        a = JSON.parse(linea) as Record<string, unknown>;
      } catch {
        malas.push({ linea: cortar(linea, 80), motivo: 'línea rota en el fichero de anclas' });
        continue;
      }
      n += 1;
      if (!a.filas) continue;
      const filas = await this.filasDelAncla(a);
      if (filas.length !== Number(a.filas) || shaHuellas(filas) !== a.sha_dia) {
        malas.push({ dia: a.dia, hecha: a.hecha, filas_ancla: a.filas, filas_hoy: filas.length });
      }
    }
    return { ok: malas.length === 0, comprobadas: n, malas };
  }

  private async filasDelAncla(a: Record<string, unknown>): Promise<{ huella: string }[]> {
    const modo = a.modo;
    const primera = a.primera;
    if ((modo === 'ids' || modo === 'dia_madrid') && primera) {
      return this.prisma.db.$queryRaw<{ huella: string }[]>`
        SELECT h.huella FROM registro r JOIN registro_huellas h ON h.id = r.id
        WHERE r.id >= ${Number(primera)} AND r.id <= ${Number(a.ultima)} ORDER BY r.id`;
    }
    return this.prisma.db.$queryRaw<{ huella: string }[]>`
      SELECT h.huella FROM registro r JOIN registro_huellas h ON h.id = r.id
      WHERE substr(r.creada, 1, 10) = ${String(a.dia ?? '')} AND r.id <= ${Number(a.ultima)} ORDER BY r.id`;
  }
}

function shaHuellas(filas: { huella: string }[]): string {
  return createHash('sha256').update(filas.map((f) => f.huella).join(''), 'utf8').digest('hex');
}
