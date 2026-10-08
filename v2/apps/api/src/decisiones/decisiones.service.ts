import { HttpException, Injectable } from '@nestjs/common';
import { cortar, horaMadrid, jsonComoPython, ordenarComoPython } from '@ro/compat';
import { conVista, type Persona } from '@ro/permisos';
import { CrudoService } from '../permisos/crudo.service.js';
import { autoridadDecision607, filtroDecisiones, puedeContestar } from '../permisos/ambito-decision.js';
import { recorteImportesLectura588 } from '../permisos/recorte-importes-588.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { ambitoDe } from '../rastro/rastro-lectura.service.js';
import { RastroService } from '../rastro/rastro.service.js';
import { armarDecisiones } from './armar.js';

const TIPOS = new Set(['para_tomas', 'para_coti', 'escalada']);
type Fila = Record<string, unknown>;

function esObj(x: unknown): x is Fila {
  return !!x && typeof x === 'object' && !Array.isArray(x);
}

function comoPersona(p: { id: string; nombre?: unknown; puestos?: string[]; alias?: unknown }): Persona {
  return { ...(p as Persona), nombre: typeof p.nombre === 'string' ? p.nombre : '', puestos: p.puestos ?? [] };
}

function num(v: unknown): number | null {
  if (typeof v === 'bigint') return Number(v);
  if (typeof v === 'number') return v;
  return null;
}

function filaSql(r: Fila): Fila {
  const o: Fila = {};
  for (const [k, v] of Object.entries(r)) o[k] = typeof v === 'bigint' ? Number(v) : v;
  return o;
}

@Injectable()
export class DecisionesService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly crudoSvc: CrudoService,
    private readonly rastro: RastroService,
  ) {}

  private async cargarAmbito() {
    const crudo = await this.crudoSvc.actual();
    const firma = await this.crudoSvc.sello();
    return { crudo, firma };
  }

  /** GET /api/respuestas_mili. El permiso lo declara el controlador. */
  async respuestasMili(): Promise<{ _meta: { generado: string; origen: string; uso: string }; respuestas: unknown[] }> {
    const filas = (
      await this.prisma.db.$queryRaw<Fila[]>`
        SELECT id, anula_a, respuesta FROM decisiones WHERE tipo = 'para_confirmar' ORDER BY id`
    ).map(filaSql);
    const anuladas = new Set(filas.map((r) => num(r.anula_a)).filter((n) => n));
    const resp: unknown[] = [];
    for (const r of filas) {
      const id = num(r.id);
      if (id != null && !anuladas.has(id) && !num(r.anula_a) && r.respuesta) {
        const x = JSON.parse(String(r.respuesta)) as unknown;
        if (Array.isArray(x)) resp.push(...x);
        else resp.push(x);
      }
    }
    return {
      _meta: {
        generado: horaMadrid(new Date(), ''),
        origen: 'Ajustes › Para confirmar (local.db)',
        uso: 'Guárdalo como 20_FASE0_DATOS/respuestas_mili.json y lanza build_data.py',
      },
      respuestas: resp,
    };
  }

  /** GET /api/decisiones. */
  async listar(vista: VistaConContexto): Promise<{ decisiones: Fila[]; hora: string }> {
    const real = vista.real;
    const persona = vista.como ?? vista.real;
    const primero = await this.cargarAmbito();
    const ambito = ambitoDe(primero.crudo, real, persona);
    if (!ambito) throw new HttpException('El ámbito actual de las decisiones no está disponible.', 403);
    const vistaPersona = ambito.ps[1];
    if (!vistaPersona) throw new HttpException('El ámbito actual de las decisiones no está disponible.', 403);
    const tabla = (
      await this.prisma.db.$queryRaw<Fila[]>`
        SELECT id, creada, quien, tipo, clave, problema, recomendacion, respuesta, respondida, respondida_por, anula_a, titulo, cliente_id, datos
        FROM decisiones WHERE tipo <> 'para_confirmar' AND anula_a IS NULL ORDER BY id`
    ).map(filaSql);
    const acc = (
      await this.prisma.db.$queryRaw<Fila[]>`
        SELECT id, creada, quien, tipo, cliente_id, texto, vista_previa
        FROM acciones WHERE tipo IN ('decision_nueva', 'decidir') ORDER BY id`
    ).map(filaSql);
    const crudo = primero.crudo;
    const personas = new Map((crudo.personas ?? []).map((p) => [p.id, p]));
    let lista = armarDecisiones(tabla, acc, (id) => personas.get(id) ?? null);
    const filtrar = () => filtroDecisiones(vistaPersona, lista);
    lista =
      vista.como && vista.cpReal
        ? conVista({ real: comoPersona(real), cp: vista.cpReal }, filtrar)
        : filtrar();
    const recortada = recorteImportesLectura588(lista, ambito.ps, ambito.cps);
    const segundo = await this.cargarAmbito();
    const final = ambitoDe(segundo.crudo, real, persona);
    if (!final || segundo.firma !== primero.firma) {
      throw new HttpException('El ámbito de las decisiones cambió durante la lectura.', 403);
    }
    return { decisiones: recortada, hora: horaMadrid(new Date(), '') };
  }

  /** POST /api/decisiones. «Ver como» no llega: lo corta la guarda. */
  async escribir(vista: VistaConContexto, body: unknown): Promise<{ ok: true; id?: string }> {
    if (!esObj(body)) throw new HttpException('La decisión debe ser un objeto.', 400);
    const op = body.operacion || 'nueva';
    if (op === 'nueva') return this.nueva(vista, body);
    if (op === 'responder') return this.responder(vista, body);
    throw new HttpException('Operación no válida (nueva o responder).', 400);
  }

  private async nueva(vista: VistaConContexto, b: Fila): Promise<{ ok: true; id: string }> {
    const tipo = b.tipo || 'para_tomas';
    if (typeof tipo !== 'string' || !TIPOS.has(tipo)) {
      throw new HttpException('Tipo no válido (para_tomas, para_coti o escalada).', 400);
    }
    if (!['titulo', 'problema'].every((k) => typeof b[k] === 'string' && (b[k] as string).trim())) {
      throw new HttpException('Falta qué hay que decidir o el problema.', 400);
    }
    if (typeof b.recomendacion !== 'string' || !b.recomendacion.trim()) {
      throw new HttpException('Falta tu recomendación (exigencia 48: sin recomendación no se sube).', 400);
    }
    const cid = b.cliente_id;
    if (cid != null && (typeof cid !== 'string' || !cid)) throw new HttpException('Cliente no válido.', 400);
    const otros = b.clientes;
    if (
      otros != null &&
      (!Array.isArray(otros) || !otros.every((x) => typeof x === 'string' && x) || new Set(otros).size !== otros.length)
    ) {
      throw new HttpException('La lista de clientes debe contener identidades únicas.', 400);
    }
    const clientes = ordenarComoPython([
      ...new Set([...(typeof cid === 'string' ? [cid] : []), ...((otros as string[] | null) ?? [])]),
    ]);
    const real = vista.real;
    const firma = await autoridadDecision607(() => this.cargarAmbito(), real, clientes);
    if (firma == null) throw new HttpException('No puedes subir una decisión con ese ámbito actual.', 403);
    if (b.prueba && !String(b.prueba).startsWith('https://') && !String(b.prueba).startsWith('#/')) {
      throw new HttpException('La prueba tiene que ser un enlace https:// o una pantalla de la app (#/…).', 400);
    }
    const extra: Fila = {};
    for (const k of ['opciones', 'fecha', 'prueba', 'clientes'] as const) {
      if (b[k] != null) extra[k] = b[k];
    }
    if (otros != null) extra.clientes = [...(otros as unknown[])];
    const titulo = cortar((b.titulo as string).trim(), 200);
    const problema = (b.problema as string).trim();
    const recomendacion = b.recomendacion.trim();
    const clave = b.clave == null ? null : typeof b.clave === 'string' ? b.clave : String(b.clave);
    const datos = jsonComoPython(extra, { ensureAscii: false });
    const did = await this.prisma.db.$transaction(async (t) => {
      const otra = await autoridadDecision607(() => this.cargarAmbito(), real, clientes);
      if (otra !== firma) throw new HttpException('El ámbito de la decisión ha cambiado; no se ha guardado.', 403);
      const filas = await t.$queryRaw<{ id: bigint }[]>`
        INSERT INTO decisiones (quien, tipo, clave, titulo, problema, recomendacion, cliente_id, datos)
        VALUES (${real.id}, ${tipo}, ${clave}, ${titulo}, ${problema}, ${recomendacion}, ${typeof cid === 'string' ? cid : null}, ${datos})
        RETURNING id`;
      const id = Number(filas[0]?.id);
      await this.rastro.registrar(t, {
        quien: real.id,
        coleccion: 'decisiones',
        accion: 'decision_nueva',
        clave: `db-${id}`,
        datos: { tipo, titulo: cortar(b.titulo as string, 120) },
      });
      return id;
    });
    return { ok: true, id: `db-${did}` };
  }

  private async responder(vista: VistaConContexto, b: Fila): Promise<{ ok: true }> {
    const crudo = String(b.id ?? '');
    const m = /^db-([0-9]+)$/.exec(crudo);
    if (!m) throw new HttpException('Solo se contestan aquí las decisiones de la tabla (id «db-…»).', 400);
    const real = vista.real;
    await this.prisma.db.$transaction(async (t) => {
      const filas = await t.$queryRaw<Fila[]>`
        SELECT id, tipo, respondida FROM decisiones WHERE id = ${Number(m[1])} LIMIT 1`;
      const fila = filas[0] ? filaSql(filas[0]) : null;
      if (!fila || typeof fila.tipo !== 'string' || !TIPOS.has(fila.tipo)) {
        throw new HttpException('No existe esa decisión.', 404);
      }
      if (!puedeContestar(real, fila.tipo)) {
        throw new HttpException('Esta decisión la contesta su destinatario (Tomás o Coti).', 403);
      }
      if (fila.respondida) throw new HttpException('Ya está contestada. Para cambiarla, sube una decisión nueva.', 409);
      const resp = { decision: b.decision ?? null, motivo: b.motivo ?? null, delegada_en: b.delegada_en ?? null };
      const motivo = typeof resp.motivo === 'string' ? resp.motivo : '';
      if (resp.decision !== 'Aprobar la recomendación' && !motivo.trim()) {
        throw new HttpException('Rechazar o delegar necesita un motivo.', 400);
      }
      const texto = jsonComoPython(resp, { ensureAscii: false });
      await t.$executeRaw`
        UPDATE decisiones
        SET respuesta = ${texto},
            respondida = to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS'),
            respondida_por = ${real.id}
        WHERE id = ${Number(fila.id)}`;
      await this.rastro.registrar(t, {
        quien: real.id,
        coleccion: 'decisiones',
        accion: 'decidir',
        clave: crudo,
        datos: resp,
      });
    });
    return { ok: true };
  }
}
