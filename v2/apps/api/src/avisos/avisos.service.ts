import { Injectable } from '@nestjs/common';
import { ahoraBaseUtc } from '@ro/compat';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { RastroService } from '../rastro/rastro.service.js';

type Fila = Record<string, unknown>;

const NOTA = 'La notificación real (escritorio y móvil) llega con W1. En el prototipo se ven aquí.';

function filaSql(r: Fila): Fila {
  const o: Fila = {};
  for (const [k, v] of Object.entries(r)) o[k] = typeof v === 'bigint' ? Number(v) : v;
  return o;
}

function esObj(x: unknown): x is Fila {
  return !!x && typeof x === 'object' && !Array.isArray(x);
}

/** `int(b.get("id") or 0)`. Un texto que no es entero es el 500 de servir.py. */
function idEntero(v: unknown): number {
  if (v === undefined || v === null || v === '' || v === false) return 0;
  if (v === true) return 1;
  if (typeof v === 'number' && Number.isFinite(v)) return Math.trunc(v);
  if (typeof v === 'string' && /^[+-]?\d+$/.test(v.trim())) return parseInt(v.trim(), 10);
  throw new Error('id de aviso no entero');
}

/** GET y POST de los avisos de la app (tabla `avisos`, no la de la tubería). */
@Injectable()
export class AvisosService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly rastro: RastroService,
  ) {}

  async listar(): Promise<{ tope_dia: number; avisos: Fila[]; nota: string }> {
    const avisos = (
      await this.prisma.db.$queryRaw<Fila[]>`SELECT * FROM avisos ORDER BY id DESC LIMIT 100`
    ).map(filaSql);
    return { tope_dia: 3, avisos, nota: NOTA };
  }

  /** Siempre 200, haya fila o no. La clave del rastro es str(b.get("id")), no el entero del UPDATE. */
  async visto(vista: VistaConContexto, body: unknown): Promise<{ ok: true }> {
    const b = esObj(body) ? body : {};
    const clave = b.id === undefined || b.id === null ? 'None' : String(b.id);
    const id = idEntero('id' in b ? b.id : undefined);
    const real = vista.real;
    await this.prisma.db.$transaction(
      async (t) => {
        await t.$executeRaw`
          UPDATE avisos SET visto = ${ahoraBaseUtc()}, visto_por = ${real.id}
          WHERE id = ${id} AND visto IS NULL`;
        await this.rastro.registrar(t, {
          quien: real.id,
          coleccion: 'avisos',
          accion: 'aviso_visto',
          clave,
        });
      },
      { maxWait: 10_000, timeout: 10_000 },
    );
    return { ok: true };
  }
}
