import { Injectable } from '@nestjs/common';
import { huellaRastro, jsonComoPython } from '@ro/compat';
import type { Prisma } from '@ro/db';
import { PrismaService } from '../prisma/prisma.service.js';

/** Una fila del rastro: los mismos campos que servir.py › registrar(quien, coleccion, accion, clave, datos, motivo, como, anula_a, origen). */
export interface FilaRastro {
  quien: string;
  coleccion: string;
  accion?: string | null;
  clave?: string | null;
  datos?: unknown;
  motivo?: string | null;
  como?: string | null;
  anula_a?: number | null;
  origen?: string;
}

/** El candado del rastro entre procesos: el mismo número que despliegue/base.py (BEGIN IMMEDIATE en Postgres). */
const CANDADO_RASTRO = 7262;

@Injectable()
export class RastroService {
  constructor(private readonly prisma: PrismaService) {}

  /**
   * servir.py › _registrar: rastro imborrable y ENCADENADO. Nest y el legado escriben a la vez: el candado va dentro
   * de la misma transacción que el INSERT, y `creada` la pone la base y se lee de vuelta (esa es la que entra en la
   * huella). Con `tx`, la fila va en la transacción de quien llama (escritura y rastro juntos); sin ella, abre una.
   */
  async registrar(tx: Prisma.TransactionClient | null, f: FilaRastro): Promise<number> {
    if (tx) return this.escribir(tx, f);
    return this.prisma.db.$transaction((t) => this.escribir(t, f), { maxWait: 10_000, timeout: 10_000 });
  }

  private async escribir(t: Prisma.TransactionClient, f: FilaRastro): Promise<number> {
    await t.$executeRaw`SELECT pg_advisory_xact_lock(${CANDADO_RASTRO})`;
    const previa = (await t.$queryRaw<{ huella: string }[]>`SELECT huella FROM registro_huellas ORDER BY id DESC LIMIT 1`)[0]?.huella ?? null;
    // json.dumps(datos, ensure_ascii=False): separadores por defecto y sin ordenar.
    const texto = f.datos === undefined || f.datos === null ? null : jsonComoPython(f.datos, { ensureAscii: false });
    const como = f.como ?? null;
    const accion = f.accion ?? null;
    const clave = f.clave ?? null;
    const motivo = f.motivo ?? null;
    const anula = f.anula_a ?? null;
    const origen = f.origen ?? 'app';
    const fila = await t.registro.create({
      data: { quien: f.quien, como, coleccion: f.coleccion, accion, clave, datos: texto, motivo, anula_a: anula, origen, huella_previa: previa },
      select: { id: true, creada: true },
    });
    const id = Number(fila.id);
    const h = huellaRastro(previa, [id, fila.creada, f.quien, como, f.coleccion, accion, clave, texto, motivo, anula, origen]);
    await t.registro_huellas.create({ data: { id, huella: h } });
    return id;
  }
}
