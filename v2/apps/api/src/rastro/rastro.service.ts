import { Injectable } from '@nestjs/common';
import { horaMadrid, huellaRastro, jsonComoPython } from '@ro/compat';
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
/** servir.py › TOPE_RASTRO_MINUTO. Se lee al cargar el módulo, como el `int(os.environ…)` de Python. */
const TOPE_RASTRO_MINUTO = Number(process.env.RO_TOPE_RASTRO_MINUTO || 30);

@Injectable()
export class RastroService {
  /** Contadores en memoria de ESTE proceso (servir.py › _AGRUPADOS y _POR_MINUTO). No se comparten con el legado. */
  private readonly agrupados = new Map<string, number>();
  private readonly porMinuto = new Map<string, number>();

  constructor(private readonly prisma: PrismaService) {}

  /** Hora local de Madrid, sin RO_RELOJ: servir.py › ahora() en el minuto de agrupación. */
  private minutoLocal(): string {
    return horaMadrid(new Date(), '').slice(0, 16).replace('T', ' ');
  }

  /** servir.py › tope_rastro_navegador. False cuando este minuto ya lleva TOPE * 2 anotaciones del navegador. */
  topeNavegador(quien: string): boolean {
    const k = `${quien}\u0000nav\u0000${this.minutoLocal()}`;
    const n = this.porMinuto.get(k) ?? 0;
    this.porMinuto.set(k, n + 1);
    return n < TOPE_RASTRO_MINUTO * 2;
  }

  /** servir.py › registrar_agrupado. Una fila por persona, ruta y minuto; al pasarse, una sola «rastro_limitado». */
  async registrarAgrupado(
    quien: string,
    coleccion: string,
    accion: string,
    clave: string | null,
    datos: Record<string, unknown> | null,
    motivo: string | null,
    como: string | null,
  ): Promise<number | null> {
    const minuto = this.minutoLocal();
    const k = [quien, como ?? '', coleccion, accion, clave ?? '', minuto].join('\u0000');
    if (this.agrupados.size > 20000) {
      this.agrupados.clear();
      this.porMinuto.clear();
    }
    if (this.agrupados.has(k)) {
      this.agrupados.set(k, (this.agrupados.get(k) ?? 0) + 1);
      return null;
    }
    const mk = `${quien}\u0000${minuto}`;
    const n = this.porMinuto.get(mk) ?? 0;
    this.porMinuto.set(mk, n + 1);
    if (n > TOPE_RASTRO_MINUTO) return null;
    this.agrupados.set(k, 1);
    if (n === TOPE_RASTRO_MINUTO) {
      return this.registrar(null, {
        quien,
        coleccion: 'rastro',
        accion: 'rastro_limitado',
        clave: minuto,
        datos: { detalle: `Más de ${TOPE_RASTRO_MINUTO} denegados o lecturas en un minuto: el resto de ese minuto no deja fila.` },
        como,
      });
    }
    return this.registrar(null, {
      quien,
      coleccion,
      accion,
      clave,
      datos: { ...(datos ?? {}), agrupado: 'una fila por persona, ruta y minuto' },
      motivo,
      como,
    });
  }

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
