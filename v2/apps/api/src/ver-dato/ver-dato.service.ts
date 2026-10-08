import { HttpException, Injectable } from '@nestjs/common';
import { conVista, contexto, reglas, ver, type Persona } from '@ro/permisos';
import { CrudoService } from '../permisos/crudo.service.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { clienteDelDato, configAlmacen, duenoOk, veAlgunoConVista, type AlmacenConf } from '../permisos/ver-dato-reglas.js';
import { RastroService } from '../rastro/rastro.service.js';

type Fila = Record<string, unknown>;

function esFila(x: unknown): x is Fila {
  return !!x && typeof x === 'object' && !Array.isArray(x);
}

function comoPersona(p: { id: string; nombre?: unknown; puestos?: string[]; alias?: unknown }): Persona {
  return { ...(p as Persona), nombre: typeof p.nombre === 'string' ? p.nombre : '', puestos: p.puestos ?? [] };
}

function aliasDe(p: { id: string; alias?: unknown }): string {
  return typeof p.alias === 'string' && p.alias ? p.alias : p.id;
}

function conLaVista<T>(vista: VistaConContexto, fn: () => T): T {
  if (vista.como && vista.cpReal) return conVista({ real: comoPersona(vista.real), cp: vista.cpReal }, fn);
  return fn();
}

const COLECCION: Record<string, string> = {
  contactos_cliente: 'contactos',
  chat_cliente: 'chat',
  mensaje_cliente: 'whatsapp',
  sueldos: 'sueldos',
};

@Injectable()
export class VerDatoService {
  constructor(
    private readonly crudoSvc: CrudoService,
    private readonly rastro: RastroService,
  ) {}

  /** POST /api/ver_dato. «Ver como» puede: es la única lectura por POST. */
  async ver(vista: VistaConContexto, body: unknown): Promise<Fila> {
    const b = esFila(body) ? body : {};
    const almacen = typeof b.almacen === 'string' ? b.almacen : '';
    const ref = String(b.ref ?? '');
    const campo = typeof b.campo === 'string' ? b.campo : '';
    if (!/^[\w\-/]+$/.test(almacen) || !almacen.split('/').includes('_privado')) {
      throw new HttpException('Almacén no válido (debe ser una carpeta _privado/ de data/).', 400);
    }
    const conf = configAlmacen(almacen);
    if (!conf) {
      throw new HttpException('Ese almacén no está en reglas_permisos.json (almacenes_privados): no se abre.', 403);
    }
    const crudo = await this.crudoSvc.actual();
    const real = comoPersona(vista.real);
    const persona = comoPersona(vista.como ?? vista.real);
    const soloLectura = !!vista.como;
    const coleccion = COLECCION[conf.tipo] ?? 'leads';
    const como = soloLectura ? persona.id : null;
    const extra: Fila = {};
    if (soloLectura) extra.detalle = `visto como ${aliasDe(persona)} por ${aliasDe(real)}`;
    const clienteReal = await clienteDelDato(conf, ref, almacen, crudo.clientes, (ruta) => this.crudoSvc.fichero(ruta));
    const clientesDato = clienteReal ? crudo.clientes.filter((c) => c.id === clienteReal) : [];
    const cpReal = contexto(real, crudo);
    const cpPersona = contexto(persona, crudo);
    const clienteOk = conLaVista(vista, () => this.clienteOk(conf, clienteReal, clientesDato, real, persona, cpReal, cpPersona));
    if (!clienteOk) {
      await this.rastro.registrarAgrupado(
        real.id,
        coleccion,
        'ver_dato_denegado',
        `${almacen}#${ref}`,
        { campo, motivo: 'dato sin cliente', ...extra },
        null,
        como,
      );
      throw new HttpException('Ese dato no pertenece a un cliente activo que puedas consultar.', 403);
    }
    const dueno = conf.dueno === 'fichero' ? (almacen.split('/').at(-1) ?? null) : null;
    const nombreAlm = almacen.split('/').at(-1) ?? '';
    const visto = conLaVista(vista, () => {
      const v = ver(persona, { tipo: conf.tipo, cliente_id: clienteReal ?? undefined, persona_id: dueno ?? undefined }, cpPersona);
      return {
        desenmascarable: v.desenmascarable === true,
        duenoBien: duenoOk(persona, conf, nombreAlm),
        moduloOk: veAlgunoConVista(persona, conf.modulos ?? []),
      };
    });
    if (!visto.desenmascarable || !visto.duenoBien || !visto.moduloOk) {
      await this.rastro.registrarAgrupado(
        real.id,
        coleccion,
        'ver_dato_denegado',
        `${almacen}#${ref}`,
        { campo, cliente_id: clienteReal, ...extra },
        null,
        como,
      );
      const no = (reglas() as { tipos: Record<string, { no?: string }> }).tipos[conf.tipo]?.no;
      throw new HttpException(no || 'Estos datos solo los ve quien los trabaja.', 403);
    }
    const doc = await this.crudoSvc.fichero(`${almacen}.json`);
    if (doc === undefined) throw new HttpException('No existe ese almacén.', 404);
    const valor = buscar(doc, ref, campo);
    if (valor === undefined || valor === null) {
      const rid = await this.rastro.registrar(null, {
        quien: real.id,
        coleccion,
        accion: 'ver_dato',
        clave: `${almacen}#${ref}`,
        datos: { campo, sin_dato: true, ...extra },
        como,
      });
      return { ok: true, valor: null, sin_dato: true, texto: 'sin dato', rastro: rid };
    }
    const rid = await this.rastro.registrar(null, {
      quien: real.id,
      coleccion,
      accion: 'ver_dato',
      clave: `${almacen}#${ref}`,
      datos: { campo, cliente_id: clienteReal, ...extra },
      como,
    });
    return { ok: true, valor, rastro: rid };
  }

  private clienteOk(
    conf: AlmacenConf,
    clienteReal: string | null,
    clientesDato: { id: string }[],
    real: Persona,
    persona: Persona,
    cpReal: ReturnType<typeof contexto>,
    cpPersona: ReturnType<typeof contexto>,
  ): boolean {
    if (!conf.cliente) return true;
    if (clientesDato.length !== 1 || !clienteReal) return false;
    const dato = { tipo: 'cliente_detalle', cliente_id: clienteReal };
    return ver(real, dato, cpReal).ok === true && ver(persona, dato, cpPersona).ok === true;
  }
}

/** servir.py:3465-3468. undefined si no hay fila; null si el campo falta o vale null. */
function buscar(doc: unknown, ref: string, campo: string): unknown {
  const colecciones = esFila(doc) ? Object.values(doc) : [];
  for (const coleccion of colecciones) {
    if (!esFila(coleccion) || !Object.hasOwn(coleccion, ref)) continue;
    const fila = coleccion[ref];
    if (!esFila(fila)) continue;
    return Object.hasOwn(fila, campo) ? fila[campo] : null;
  }
  return undefined;
}
