import { HttpException, Injectable } from '@nestjs/common';
import { ahoraBaseUtc, jsonComoPython } from '@ro/compat';
import type { Prisma } from '@ro/db';
import { mirandoComo, recortar, ver, type Persona } from '@ro/permisos';
import { CrudoService } from '../permisos/crudo.service.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { RastroService } from '../rastro/rastro.service.js';

/** servir.py › TOPE_FIJADOS. */
const TOPE = 30;
/** re.fullmatch(r"[\w\-]{1,80}", x): \w de Python es letra, número o _. */
const ID_OK = /^[\p{L}\p{N}_-]{1,80}$/u;
const INTERNO = 'Error interno (el detalle queda en el registro del servidor).';

function personaDe(p: { id: string; nombre?: unknown; puestos?: string[] }): Persona {
  return { ...(p as Persona), nombre: typeof p.nombre === 'string' ? p.nombre : '', puestos: p.puestos ?? [] };
}

function parsear(valor: string): unknown {
  try {
    return JSON.parse(valor);
  } catch {
    return null;
  }
}

@Injectable()
export class PreferenciasService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly crudoSvc: CrudoService,
    private readonly rastro: RastroService,
  ) {}

  private async leido(db: Prisma.TransactionClient | PrismaService['db'], pid: string): Promise<unknown> {
    const fila = await db.preferencias.findUnique({
      where: { persona_clave: { persona: pid, clave: 'fijados' } },
      select: { valor: true },
    });
    return fila ? parsear(fila.valor) : null;
  }

  /** GET /api/preferencias. La lista es de la persona vista. */
  async leer(vista: VistaConContexto): Promise<{ fijados: string[] | null; tope: number }> {
    const persona = personaDe(vista.como ?? vista.real);
    const real = personaDe(vista.real);
    const fij = await this.leido(this.prisma.db, persona.id);
    if (fij === null) return { fijados: null, tope: TOPE };
    if (!Array.isArray(fij)) throw new HttpException(INTERNO, 500);
    const vis = new Set<string>();
    if (fij.length) {
      const crudo = await this.crudoSvc.actual();
      const llenar = () => {
        for (const c of recortar(persona, crudo).clientes) {
          if (c.detalle === true && typeof c.id === 'string') vis.add(c.id);
        }
      };
      if (vista.como) mirandoComo(real, crudo, llenar);
      else llenar();
    }
    const fijados: string[] = [];
    for (const c of fij) {
      if (typeof c === 'string' && vis.has(c)) fijados.push(c);
    }
    return { fijados, tope: TOPE };
  }

  /** POST /api/preferencias. «Ver como» lo corta la guarda antes de llegar aquí. */
  async guardar(vista: VistaConContexto, body: unknown): Promise<{ ok: true; fijados: string[] }> {
    const b = body && typeof body === 'object' && !Array.isArray(body) ? (body as Record<string, unknown>) : {};
    const cruda = b.fijados;
    if (
      !Array.isArray(cruda) ||
      cruda.length > TOPE ||
      !cruda.every((x) => typeof x === 'string' && ID_OK.test(x))
    ) {
      throw new HttpException(`«fijados» es una lista de hasta ${TOPE} clientes.`, 400);
    }
    const lista = [...new Set(cruda)];
    const persona = personaDe(vista.como ?? vista.real);
    const real = personaDe(vista.real);
    if (!vista.cp) throw new HttpException(INTERNO, 500);
    const malos = lista.filter((c) => !ver(persona, { tipo: 'cliente_detalle', cliente_id: c }, vista.cp).ok);
    if (malos.length) {
      await this.rastro.registrarAgrupado(
        real.id,
        'preferencias',
        'denegado',
        malos.join(',').slice(0, 80),
        { motivo: 'fijar un cliente que no abre' },
        null,
        null,
      );
      throw new HttpException('Solo puedes fijar clientes que abres.', 403);
    }
    const valor = jsonComoPython(lista, { ensureAscii: true });
    const cambiado = ahoraBaseUtc();
    await this.prisma.db.$transaction(async (t) => {
      const antesRaw = await this.leido(t, real.id);
      const antes = Array.isArray(antesRaw) ? antesRaw : [];
      await t.preferencias.upsert({
        where: { persona_clave: { persona: real.id, clave: 'fijados' } },
        create: { persona: real.id, clave: 'fijados', valor, cambiado },
        update: { valor, cambiado },
      });
      for (const c of lista) {
        if (!antes.includes(c)) {
          await this.rastro.registrar(t, { quien: real.id, coleccion: 'preferencias', accion: 'cliente_fijado', clave: c });
        }
      }
      for (const c of antes) {
        if (typeof c === 'string' && !lista.includes(c)) {
          await this.rastro.registrar(t, { quien: real.id, coleccion: 'preferencias', accion: 'cliente_desfijado', clave: c });
        }
      }
    });
    return { ok: true, fijados: lista };
  }
}
