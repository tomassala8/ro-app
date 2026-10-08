import { HttpException, Injectable } from '@nestjs/common';
import { jsonComoPython } from '@ro/compat';
import { PERSONA_PUBLICA, conVista, hoyIso, reglas, ver, type Persona } from '@ro/permisos';
import {
  actorActual572,
  errorPuestos,
  esDireccion,
  horaLocalSinZona,
  permiteEstados572,
  reglasCambioPersona,
  respuestaOVacio,
  validarAsignacion579,
  validarLista572,
} from '../permisos/ajustes-reglas.js';
import { CrudoService, type CrudoRo } from '../permisos/crudo.service.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { RastroService } from '../rastro/rastro.service.js';

const PERMITIDOS = new Set(['puestos', 'jefe', 'horas_mes', 'imputa_horas', 'estado', 'correo', 'nombre', 'alias']);
const ESTADOS = new Set(['activo', 'dudoso', 'por_incorporar', 'baja']);
type Fila = Record<string, unknown>;

function esFila(x: unknown): x is Fila {
  return !!x && typeof x === 'object' && !Array.isArray(x);
}

function comoPersona(p: { id: string; nombre?: unknown; puestos?: string[] }): Persona {
  return { ...(p as Persona), nombre: typeof p.nombre === 'string' ? p.nombre : '', puestos: p.puestos ?? [] };
}

function filaSql(r: Fila): Fila {
  const o: Fila = {};
  for (const [k, v] of Object.entries(r)) o[k] = typeof v === 'bigint' ? Number(v) : v;
  return o;
}

function conLaVista<T>(vista: VistaConContexto, fn: () => T): T {
  if (vista.como && vista.cpReal) return conVista({ real: comoPersona(vista.real), cp: vista.cpReal }, fn);
  return fn();
}

@Injectable()
export class AjustesService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly crudoSvc: CrudoService,
    private readonly rastro: RastroService,
  ) {}

  /** GET /api/ajustes. La guarda ya dejó pasar a quien edita o es RRHH. */
  async leer(vista: VistaConContexto): Promise<Fila> {
    const crudo = await this.crudoSvc.actual();
    const persona = comoPersona(vista.como ?? vista.real);
    const nivelOk = conLaVista(vista, () => ver(persona, { tipo: 'ajustes_editar' }, vista.cp ?? {}).ok);
    const personas = nivelOk
      ? crudo.personas
      : crudo.personas.map((p) => {
          const fila: Fila = {};
          for (const k of [...PERSONA_PUBLICA, 'horas_mes', 'imputa_horas']) fila[k] = p[k] ?? null;
          return fila;
        });
    const decis = (
      await this.prisma.db.$queryRaw<Fila[]>`
        SELECT id, creada, quien, tipo, clave, problema, recomendacion, respuesta, respondida, respondida_por, anula_a, titulo, cliente_id, datos
        FROM decisiones WHERE tipo = 'para_confirmar' ORDER BY id DESC`
    ).map(filaSql);
    const hist = (
      await this.prisma.db.$queryRaw<Fila[]>`
        SELECT n, ts, quien, coleccion, id, operacion, antes, datos FROM historial ORDER BY n DESC LIMIT 200`
    ).map(filaSql);
    const reg = reglas() as { sillas?: unknown; puestos_solo_tomas?: unknown };
    return {
      puedeEditar: nivelOk && !vista.como,
      personas,
      asignaciones: nivelOk ? crudo.asignaciones : [],
      para_confirmar: nivelOk ? crudo.para_confirmar : [],
      clientes: crudo.clientes.map((c) => ({
        id: c.id,
        nombre: c.nombre ?? null,
        sin_account: 'sin_account' in c && c.sin_account !== undefined ? c.sin_account : null,
        responsable_id: 'responsable_id' in c && c.responsable_id !== undefined ? c.responsable_id : null,
      })),
      decisiones: nivelOk ? decis : [],
      historial: nivelOk ? hist : [],
      sillas: reg.sillas,
      puestos: reglas().puestos,
      puestos_solo_tomas: reg.puestos_solo_tomas ?? [],
      realEsDireccion: esDireccion(vista.real),
    };
  }

  /** POST /api/ajustes/<sub>. La guarda ya exigió ajustes_editar. */
  async escribir(vista: VistaConContexto, sub: string, body: unknown): Promise<{ ok: true }> {
    if (sub === 'persona') return this.persona(vista, body);
    if (sub === 'asignacion') return this.asignacion(vista, body);
    if (sub === 'confirmar') return this.confirmar(vista, body);
    throw new HttpException('No existe esa ruta de Ajustes.', 404);
  }

  private async persona(vista: VistaConContexto, body: unknown): Promise<{ ok: true }> {
    if (!esFila(body)) throw new HttpException('No existe esa persona.', 404);
    const crudo = await this.crudoSvc.actual();
    const p = crudo.personas.find((x) => x.id === body.id);
    if (!p) throw new HttpException('No existe esa persona.', 404);
    const cambios: Fila = {};
    const src = body.cambios;
    if (esFila(src)) {
      for (const [k, v] of Object.entries(src)) if (PERMITIDOS.has(k)) cambios[k] = v;
    }
    if ('puestos' in cambios) {
      const mal = errorPuestos(cambios.puestos);
      if (mal) throw new HttpException(mal, 400);
    }
    if ('estado' in cambios) {
      if (typeof cambios.estado !== 'string' || !ESTADOS.has(cambios.estado)) throw new HttpException('Estado no válido.', 400);
      cambios.activo = cambios.estado === 'activo';
    }
    if (jsonComoPython(body).includes('sueldo')) {
      throw new HttpException('Los sueldos no se cambian desde Ajustes.', 400);
    }
    const real = vista.real;
    const fila = p as unknown as Fila;
    const regla = reglasCambioPersona(real, fila, cambios);
    if (regla) throw new HttpException(regla[1], regla[0]);
    if ('correo' in cambios) this.correo(crudo, fila, cambios);
    const antes: Fila = {};
    for (const k of Object.keys(cambios)) antes[k] = fila[k] === undefined ? null : fila[k];
    const antesTxt = jsonComoPython(antes, { ensureAscii: false });
    const datosTxt = jsonComoPython(cambios, { ensureAscii: false });
    await this.prisma.db.$transaction(async (t) => {
      await t.$executeRaw`
        INSERT INTO historial (quien, coleccion, id, operacion, antes, datos)
        VALUES (${real.id}, 'personas', ${p.id}, 'cambiar', ${antesTxt}, ${datosTxt})`;
      await this.rastro.registrar(t, {
        quien: real.id,
        coleccion: 'ajustes',
        accion: 'cambio_persona',
        clave: p.id,
        datos: { antes, despues: cambios },
      });
    });
    await this.resembrarAsignaciones();
    return { ok: true };
  }

  private correo(crudo: CrudoRo, p: Fila, cambios: Fila): void {
    if (cambios.correo !== null && typeof cambios.correo !== 'string') throw new HttpException('Correo no válido.', 400);
    const correo = String(cambios.correo ?? '').trim().toLowerCase();
    if (correo && !correo.endsWith('@rankingonline.com') && !correo.endsWith('@rankingonlinemarketing.com')) {
      throw new HttpException('El correo tiene que ser de RO.', 400);
    }
    if (correo) {
      const otros = crudo.personas.filter((x) => {
        if (x.id === p.id) return false;
        const propio = String(x.correo ?? '').toLowerCase();
        const mas = Array.isArray(x.otros_correos) ? x.otros_correos : [];
        return propio === correo || mas.some((c) => typeof c === 'string' && c.toLowerCase() === correo);
      });
      if (otros.length) throw new HttpException('Ese correo ya es de otra persona: tiene que ser único.', 409);
    }
    const actual = String(p.correo ?? '').trim().toLowerCase();
    if (correo !== actual) {
      throw new HttpException('El correo de entrada se gestiona desde Altas y bajas; aquí no cambia Access.', 400);
    }
    cambios.correo = p.correo === undefined ? null : p.correo;
  }

  private async asignacion(vista: VistaConContexto, body: unknown): Promise<{ ok: true }> {
    const crudo = await this.crudoSvc.actual();
    const hoy = hoyIso();
    const d = validarAsignacion579(crudo, body, hoy);
    if (!d) throw new HttpException('Asignación no válida: revisa persona activa, silla, fechas y suplencia.', 400);
    const op = esFila(body) ? body.operacion : null;
    if (op === 'crear') {
      const alias = typeof vista.real.alias === 'string' ? vista.real.alias : '';
      d.fuente = `Ajustes · ${alias} · ${horaLocalSinZona()}`;
      d.confianza = 'confirmada';
    }
    const real = vista.real;
    const datosTxt = jsonComoPython(d, { ensureAscii: false });
    const idHist = `${d.cliente_id}·${d.silla}·${d.persona_id}`;
    await this.prisma.db.$transaction(async (t) => {
      const otra = validarAsignacion579(await this.crudoSvc.actual(), body, hoy);
      if (!otra) throw new HttpException('La asignación ha cambiado de ámbito.', 403);
      await t.$executeRaw`
        INSERT INTO historial (quien, coleccion, id, operacion, datos)
        VALUES (${real.id}, 'asignaciones', ${idHist}, ${String(op)}, ${datosTxt})`;
      await this.rastro.registrar(t, {
        quien: real.id,
        coleccion: 'ajustes',
        accion: `asignacion_${String(op)}`,
        clave: String(d.cliente_id),
        datos: d,
      });
    });
    await this.resembrarAsignaciones();
    return { ok: true };
  }

  private async confirmar(vista: VistaConContexto, body: unknown): Promise<{ ok: true }> {
    if (!esFila(body)) throw new HttpException('Respuesta no válida para la duda actual.', 400);
    const resp = respuestaOVacio(body.respuesta);
    const lista = Array.isArray(resp) ? resp : [resp];
    const crudo = await this.crudoSvc.actual();
    const real = vista.real;
    if (!actorActual572(crudo, real)) throw new HttpException('No puedes confirmar en tu ámbito actual.', 403);
    if (!validarLista572(resp, crudo)) throw new HttpException('Respuesta no válida para la duda actual.', 400);
    if (!permiteEstados572(crudo, real, resp)) throw new HttpException('No puedes modificar el estado de esa persona.', 403);
    const primera = esFila(lista[0]) ? lista[0] : {};
    const duda = typeof primera.duda === 'string' ? primera.duda : null;
    const nota = 'nota' in primera ? (primera.nota ?? null) : null;
    const texto = jsonComoPython(resp, { ensureAscii: false });
    const respondida = horaLocalSinZona();
    await this.prisma.db.$transaction(async (t) => {
      const fresco = await this.crudoSvc.actual();
      if (!actorActual572(fresco, real) || !validarLista572(resp, fresco) || !permiteEstados572(fresco, real, resp)) {
        throw new HttpException('El ámbito de confirmación ha cambiado.', 403);
      }
      const previas = await t.$queryRaw<{ id: bigint }[]>`
        SELECT id FROM decisiones WHERE tipo = 'para_confirmar' AND clave = ${duda} AND anula_a IS NULL ORDER BY id DESC LIMIT 1`;
      if (!actorActual572(fresco, real) || !validarLista572(resp, fresco) || !permiteEstados572(fresco, real, resp)) {
        throw new HttpException('El ámbito de confirmación ha cambiado.', 403);
      }
      const previa = previas[0];
      if (previa) {
        await t.$executeRaw`
          INSERT INTO decisiones (quien, tipo, clave, problema, respuesta, anula_a)
          VALUES (${real.id}, 'para_confirmar', ${duda}, 'anulada por una respuesta nueva', NULL, ${Number(previa.id)})`;
      }
      await t.$executeRaw`
        INSERT INTO decisiones (quien, tipo, clave, respuesta, recomendacion, respondida, respondida_por)
        VALUES (${real.id}, 'para_confirmar', ${duda}, ${texto}, ${nota}, ${respondida}, ${real.id})`;
      await this.rastro.registrar(t, {
        quien: real.id,
        coleccion: 'ajustes',
        accion: 'para_confirmar',
        clave: duda,
        datos: resp,
      });
    });
    await this.resembrarAsignaciones();
    return { ok: true };
  }

  /**
   * servir.py › recargar_personas → sembrar_tablas, solo la tabla `asignaciones`.
   * Borra y vuelve a insertar sin id: el contrato de escritura compara el id, y un POST que
   * guarda (persona, asignación, confirmar) deja a SQLite una siembra por delante si Nest no lo hace.
   * El contenido se copia de la fila que ya había (el caso que falla no cambia asignaciones).
   */
  private async resembrarAsignaciones(): Promise<void> {
    await this.prisma.db.$transaction(async (t) => {
      const filas = await t.$queryRaw<Fila[]>`
        SELECT cliente_id, cliente_id_portal, persona_id, silla, principal, suplencia,
               titular_id, desde, hasta, fuente, confianza, duda
        FROM asignaciones ORDER BY id`;
      await t.$executeRaw`DELETE FROM asignaciones`;
      for (const a of filas) {
        const n = (v: unknown) => (typeof v === 'bigint' ? Number(v) : v);
        await t.$executeRaw`
          INSERT INTO asignaciones (
            cliente_id, cliente_id_portal, persona_id, silla, principal, suplencia,
            titular_id, desde, hasta, fuente, confianza, duda)
          VALUES (
            ${a.cliente_id ?? null}, ${a.cliente_id_portal ?? null}, ${a.persona_id ?? null}, ${a.silla ?? null},
            ${n(a.principal) ?? 1}, ${n(a.suplencia) ?? 0},
            ${a.titular_id ?? null}, ${a.desde ?? null}, ${a.hasta ?? null},
            ${a.fuente ?? null}, ${a.confianza ?? null}, ${a.duda ?? null})`;
      }
    });
  }
}
