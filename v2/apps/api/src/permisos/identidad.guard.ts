import { CanActivate, ExecutionContext, HttpException, Injectable } from '@nestjs/common';
import { contexto, ver, type Persona } from '@ro/permisos';
import { hostLocal } from '../legado/proxy.js';
import { correoValidado } from './access-jwt.js';
import { CrudoService, type CrudoRo } from './crudo.service.js';
import { declaracionDe } from './declarar.js';
import type { VistaConContexto } from './motor-ro.js';
import { recargarSiCambian } from './recarga.js';

/** Rutas sin identidad (hoy, /vivo no tiene). Un @Publico fuera de esta lista salta el permiso, no la identidad. */
export const SIN_IDENTIDAD = ['/vivo'];

const SIN_IDENTIFICAR = 'Sin identificar. En el prototipo, elige quién eres; en el servidor, entra por Cloudflare Access.';
const PEERS_LOCALES = new Set(['127.0.0.1', '::1', '::ffff:127.0.0.1']);

/** servir.py › ruta_lectura_ver_como585: la familia pública de la ruta, sin segmentos dinámicos ni consulta. */
const FAMILIAS = new Set([
  'sesion', 'modulo', 'cliente', 'buscar', 'decisiones', 'ajustes', 'acciones', 'rastro',
  'ia', 'avisos', 'envios', 'sincronia', 'canales', 'cerebro', 'metodo', 'mi_trabajo',
  'tareas', 'uso', 'operaciones', 'crm', 'agenda', 'recarga', 'opiniones',
]);

export function rutaLecturaVerComo585(ruta: string): string {
  const sinConsulta = String(ruta).split('?', 1)[0] ?? '';
  // str.split("/", 3) de Python: como mucho 4 trozos, el último con el resto.
  const trozos = sinConsulta.split('/');
  const segmentos = trozos.length > 4 ? [...trozos.slice(0, 3), trozos.slice(3).join('/')] : trozos;
  const familia = segmentos.length >= 3 && segmentos[0] === '' && segmentos[1] === 'api' ? (segmentos[2] ?? '') : '';
  return `/api/${FAMILIAS.has(familia) ? familia : 'otra'}`;
}

/** servir.py › galletas: la identidad del prototipo en cookie (la pone app.js con encodeURIComponent). */
export function galletas(cookie: string | undefined): Record<string, string> {
  const out: Record<string, string> = {};
  for (const trozo of (cookie ?? '').split(';')) {
    const i = trozo.indexOf('=');
    if (i < 0) continue;
    const k = trozo.slice(0, i).trim();
    const v = trozo.slice(i + 1);
    try {
      out[k] = decodeURIComponent(v);
    } catch {
      out[k] = v;
    }
  }
  return out;
}

/** parse_qs de Python + `(q.get(x) or [None])[0]`: el primer valor no vacío, o undefined. */
function primero(valor: unknown): string | undefined {
  const lista = Array.isArray(valor) ? valor : [valor];
  const v = lista.find((x) => typeof x === 'string' && x !== '');
  return typeof v === 'string' ? v : undefined;
}

function cabecera(req: Peticion, nombre: string): string | undefined {
  const v = req.headers[nombre];
  return (Array.isArray(v) ? v[0] : v) || undefined;
}

/** servir.py › _quien › canonica: la ÚNICA persona con ese id, activa. */
function canonica(crudo: CrudoRo, pid: unknown): Persona | null {
  if (typeof pid !== 'string' || !pid || !Array.isArray(crudo.personas)) return null;
  const candidatas = crudo.personas.filter((p) => p && typeof p === 'object' && p.id === pid);
  if (candidatas.length !== 1) return null;
  const actual = candidatas[0]!;
  return actual.estado === 'activo' && actual.activo !== false ? actual : null;
}

/** servir.py › Estado.por_correo: primero la lista de correos de entrada; si coincide con más de una persona, nadie. */
function porCorreo(crudo: CrudoRo, privados: Record<string, string>, bruto: string): Persona | null {
  const correo = (bruto ?? '').trim().toLowerCase();
  const limpio = (x: unknown) => (typeof x === 'string' ? x : '').trim().toLowerCase();
  const entrada = crudo.personas.filter((p) => correo && limpio(privados[p.id]) === correo);
  if (entrada.length) return entrada.length === 1 ? entrada[0]! : null;
  const hits = crudo.personas.filter(
    (p) => limpio(p.correo) === correo || ((p.otros_correos as string[] | undefined) ?? []).map(limpio).includes(correo),
  );
  return hits.length === 1 ? hits[0]! : null;
}

interface Peticion {
  headers: Record<string, string | string[] | undefined>;
  query?: Record<string, unknown>;
  socket?: { remoteAddress?: string };
  originalUrl?: string;
  url?: string;
  vista?: VistaConContexto & { rutaFamilia?: string };
}

const no = (status: number, texto: string) => new HttpException(texto, status);

/**
 * Guarda global de identidad (servir.py › host_ok + _quien). Corre ANTES que PermisosGuard y deja en req.vista quién
 * es la persona real, a quién mira en «ver como» y el contexto de permisos de las dos. Mismos códigos y textos.
 * RO_IDENTIDAD=local: X-RO-Yo, ?yo= o la galleta ro_yo, solo desde 127.0.0.1. RO_IDENTIDAD=access: solo el sello
 * firmado de Cloudflare Access (X-RO-Yo, ?yo=, ro_yo y X-Forwarded-* no valen).
 * Lo que no hace (duda 29): la puerta de secretos (503 si el escáner encuentra algo en el núcleo) la sigue haciendo
 * servir.py, que es quien escanea data/; Nest no escanea.
 */
@Injectable()
export class IdentidadGuard implements CanActivate {
  constructor(private readonly crudo: CrudoService) {}

  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    const req = ctx.switchToHttp().getRequest<Peticion>();
    const ruta = (req.originalUrl ?? req.url ?? '').split('?')[0] ?? '';
    const { publico } = declaracionDe(ctx.getHandler(), ctx.getClass());
    if (publico && SIN_IDENTIDAD.includes(ruta)) return true;
    req.vista = await this.vista(req, ruta);
    return true;
  }

  private async vista(req: Peticion, ruta: string): Promise<VistaConContexto & { rutaFamilia?: string }> {
    const access = process.env.RO_IDENTIDAD === 'access';
    const local = PEERS_LOCALES.has(req.socket?.remoteAddress ?? '');
    // servir.py › host_ok va antes que _quien (contra «DNS rebinding»): fuera de 127.0.0.1 o con un Host ajeno, este
    // texto. Detrás de Next el Host original llega en X-Forwarded-Host.
    if (!access && (!local || !hostLocal(req.headers))) throw no(403, 'Host no permitido.');
    recargarSiCambian();
    const crudo = await this.crudo.actual();
    const q = req.query ?? {};
    let correo: string | null = null;
    let real: Persona | null;
    if (access) {
      const r = await correoValidado(req.headers);
      if ('motivo' in r) throw no(403, r.motivo);
      correo = r.correo;
      real = porCorreo(crudo, await this.crudo.correosEntrada(), correo);
      if (!real) throw no(403, 'Tu correo no está en la tabla de personas. Pídeselo a Mili o a Tomás.');
    } else {
      const yo = cabecera(req, 'x-ro-yo') || primero(q.yo) || galletas(cabecera(req, 'cookie')).ro_yo;
      if (!yo) throw no(401, SIN_IDENTIFICAR);
      real = canonica(crudo, yo);
      if (!real) throw no(403, 'No existe esa persona.');
    }
    real = canonica(crudo, real.id);
    if (!real) throw no(403, 'Esta persona no está activa: Mili la activa en Ajustes › Personas.');
    let como: string | undefined = cabecera(req, 'x-ro-como') || primero(q.como);
    // La galleta de «ver como» solo cuenta si la identidad también vino por galleta.
    if (como === undefined && !correo && !cabecera(req, 'x-ro-yo') && !primero(q.yo)) {
      como = galletas(cabecera(req, 'cookie')).ro_como || undefined;
    }
    const cpReal = contexto(real, crudo);
    if (como && como !== real.id) {
      const vista = canonica(crudo, como);
      if (!vista) throw no(403, 'La persona de esta vista no está activa o su identidad no es inequívoca.');
      if (!ver(real, { tipo: 'ver_como' }, cpReal).ok) throw no(403, '«Ver como» es solo para Mili y Tomás.');
      return { real, como: vista, cp: contexto(vista, crudo), cpReal, rutaFamilia: rutaLecturaVerComo585(ruta) };
    }
    return { real, cp: cpReal, cpReal };
  }
}
