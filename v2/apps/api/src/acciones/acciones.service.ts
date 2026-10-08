import { HttpException, Injectable } from '@nestjs/common';
import { Prisma } from '@ro/db';
import { ver } from '@ro/permisos';
import { CrudoService } from '../permisos/crudo.service.js';
import { recorteImportesLectura588 } from '../permisos/recorte-importes-588.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { ambitoDe, filaVisible, quitarPara, recortarVistas, veAlguno } from '../rastro/rastro-lectura.service.js';

type Fila = Record<string, unknown>;

const PANTALLA_AJENA = 'Esa pantalla no es de tu puesto' + '.';

function filaSql(r: Fila): Fila {
  const o: Fila = {};
  for (const [k, v] of Object.entries(r)) o[k] = typeof v === 'bigint' ? Number(v) : v;
  return o;
}

/** GET /api/acciones. El mismo orden que servir.py › la rama GET. */
@Injectable()
export class AccionesService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly crudoSvc: CrudoService,
  ) {}

  async listar(vista: VistaConContexto, mod: string | undefined): Promise<{ modulo: string | null; acciones: Fila[] }> {
    const real = vista.real;
    const personaReq = vista.como ?? vista.real;
    // La lista personal no es una cola de módulo: «ver como» sin ?modulo= sale vacía antes del ámbito.
    if (!mod && real.id !== personaReq.id) return { modulo: null, acciones: [] };

    const primero = await this.cargar();
    const ambito = ambitoDe(primero.crudo, real, personaReq);
    if (!ambito) throw new HttpException('El ámbito actual de las acciones no está disponible.', 403);
    const { ps, cps } = ambito;
    const persona = ps[1];
    const cp = cps[1];
    if (!persona || !cp) throw new HttpException('El ámbito actual de las acciones no está disponible.', 403);
    if (mod && !ps.every((p) => veAlguno(p, [mod]))) {
      throw new HttpException(PANTALLA_AJENA, 403);
    }

    let filas: Fila[];
    if (mod) {
      // La segunda comprobación no añade casos: si pasó la de las dos personas, esta también.
      if (!veAlguno(persona, [mod])) throw new HttpException(PANTALLA_AJENA, 403);
      filas = (
        await this.prisma.db.$queryRaw<Fila[]>`
          SELECT * FROM acciones WHERE modulo = ${mod} ORDER BY id DESC LIMIT 500`
      ).map(filaSql);
      const nivel = veAlguno(persona, [mod]);
      filas = filas.filter((r) => {
        const cid = r.cliente_id;
        if (cid) return ver(persona, { tipo: 'cliente_detalle', cliente_id: String(cid) }, cp).ok === true;
        return nivel === 'todo' || r.quien === persona.id;
      });
    } else {
      filas = (
        await this.prisma.db.$queryRaw<Fila[]>`
          SELECT * FROM acciones WHERE quien = ${persona.id} ORDER BY id DESC LIMIT 500`
      ).map(filaSql);
    }
    filas = filas.filter((r) => filaVisible(r, primero.crudo, ps, cps, persona.id));
    await this.ponerEnvios(filas);
    filas = recortarVistas(filas, (cid) => quitarPara(persona, cp, cid));
    filas = recorteImportesLectura588(filas, ps, cps);

    const segundo = await this.cargar();
    const final = ambitoDe(segundo.crudo, real, personaReq);
    if (!final || segundo.sello !== primero.sello) {
      throw new HttpException('El ámbito de las acciones cambió durante la lectura.', 403);
    }
    return { modulo: mod ?? null, acciones: filas };
  }

  /** El último paso de envío de cada acción, en una consulta (el mismo resultado que una por fila). */
  private async ponerEnvios(filas: Fila[]): Promise<void> {
    if (!filas.length) return;
    const existe = await this.prisma.db.$queryRaw<{ t: string | null }[]>`SELECT to_regclass('envio_pasos')::text AS t`;
    if (!existe[0]?.t) return;
    const ids = filas.map((r) => Number(r.id)).filter((n) => Number.isFinite(n));
    if (!ids.length) return;
    const pasos = await this.prisma.db.$queryRaw<{ accion_id: number | bigint; estado: string; hora: string }[]>`
      SELECT DISTINCT ON (e.accion_id) e.accion_id, p.estado, p.hora
      FROM envios e
      JOIN envio_pasos p ON p.envio_id = e.id
      WHERE e.accion_id IN (${Prisma.join(ids)})
      ORDER BY e.accion_id, p.id DESC`;
    const porId = new Map<number, { estado: string; hora: string }>();
    for (const p of pasos) porId.set(Number(p.accion_id), { estado: p.estado, hora: p.hora });
    for (const r of filas) {
      const envio = porId.get(Number(r.id));
      if (!envio) continue;
      r.envio_estado = envio.estado;
      r.envio_fecha = envio.hora;
    }
  }

  private async cargar(): Promise<{ crudo: Awaited<ReturnType<CrudoService['actual']>>; sello: string }> {
    return { crudo: await this.crudoSvc.actual(), sello: await this.crudoSvc.sello() };
  }
}
