import { createHash } from 'node:crypto';
import type { IncomingHttpHeaders } from 'node:http';
import { Controller, Get, Param, Query, Req, Res } from '@nestjs/common';
import { correoValidado } from '../permisos/access-jwt.js';
import { CrudoService } from '../permisos/crudo.service.js';
import { Publico } from '../permisos/declarar.js';

/** servir.py › INMUTABLE. Siempre private: nunca public. */
const INMUTABLE = 'private, max-age=31536000, immutable';
const FICHERO = /^([\w-]+)\.(jpg|png|webp|gif)$/;
const DATA_URI = /^data:(image\/(?:jpeg|png|webp|gif));base64,(.+)$/s;

type Guardado = { marca: string; datos: Buffer; tipo: string; huella: string };
/** servir.py › _SERVIDOS[("logo", cid)] = (sha256(uri), (bytes, tipo, huella)). */
const cache = new Map<string, Guardado>();

type Respuesta = {
  status(c: number): Respuesta;
  setHeader(k: string, v: string | number): Respuesta;
  json(c: unknown): void;
  end(c?: unknown): void;
};

function logoDe(cid: string, uri: unknown): { datos: Buffer; tipo: string; huella: string } | null {
  if (typeof uri !== 'string') return null;
  const m = DATA_URI.exec(uri);
  if (!m) return null;
  const marca = createHash('sha256').update(uri).digest('hex');
  const previo = cache.get(cid);
  if (previo && previo.marca === marca) return previo;
  const datos = Buffer.from(m[2] ?? '', 'base64');
  const guardado: Guardado = {
    marca,
    datos,
    tipo: m[1] ?? 'application/octet-stream',
    huella: createHash('sha1').update(datos).digest('hex').slice(0, 12),
  };
  cache.set(cid, guardado);
  return guardado;
}

/**
 * GET /logos/<cid>.<ext> fuera del prefijo /api (servir.py › servir_logo).
 * Sin identidad en local. Con RO_IDENTIDAD=access, el sello, como do_GET para lo que no es /api/.
 */
@Controller('logos')
export class LogosController {
  constructor(private readonly crudo: CrudoService) {}

  @Publico('logo común de un cliente activo: servir.py lo sirve sin identidad (:2641); ningún dato más que la imagen')
  @Get(':fichero')
  async logo(
    @Param('fichero') fichero: string,
    @Query('v') v: string | string[] | undefined,
    @Req() req: { headers: IncomingHttpHeaders },
    @Res() res: Respuesta,
  ): Promise<void> {
    // servir.py:2559 — solo en modo access, y el texto es el de la carcasa, no el de /api/.
    if (process.env.RO_IDENTIDAD === 'access') {
      const sello = await correoValidado(req.headers);
      if (!('correo' in sello)) {
        res.status(403).json({ error: 'Entra por la dirección de la app (Cloudflare Access).' });
        return;
      }
    }
    const m = FICHERO.exec(fichero);
    if (!m) {
      res.status(403).json({ error: 'No se sirve como fichero. Los datos salen recortados de /api/.' });
      return;
    }
    const cid = m[1] ?? '';
    const crudo = await this.crudo.actual();
    const lg = logoDe(cid, crudo.logos?.[cid]);
    if (!lg) {
      res.status(404).json({ error: 'Sin logo.' });
      return;
    }
    const etag = `"${lg.huella}"`;
    const pedido = Array.isArray(v) ? v[0] : v;
    const cacheControl = pedido === lg.huella ? INMUTABLE : 'no-cache';
    const inm = req.headers['if-none-match'];
    const ifNone = (Array.isArray(inm) ? inm[0] : inm ?? '').trim();
    if (ifNone === etag) {
      res.status(304).setHeader('ETag', etag).setHeader('Cache-Control', cacheControl).end();
      return;
    }
    res
      .status(200)
      .setHeader('Content-Type', lg.tipo)
      .setHeader('ETag', etag)
      .setHeader('Cache-Control', cacheControl)
      .setHeader('Content-Length', String(lg.datos.length))
      .end(lg.datos);
  }
}
