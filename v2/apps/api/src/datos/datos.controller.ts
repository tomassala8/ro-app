import { Controller, Get, HttpException, Param, Req, Res } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { DatosService } from './datos.service.js';

type Respuesta = {
  status(c: number): Respuesta;
  setHeader(k: string, v: string): void;
  json(c: unknown): void;
  end(): void;
};

/**
 * GET /api/modulo/<rel>. La puerta del fichero decide el módulo; aquí solo hace falta estar identificado.
 * El recorte es el de servir.py (recortarModulo + quitarBajas), no el del interceptor.
 */
@Controller('modulo')
export class DatosController {
  constructor(private readonly datos: DatosService) {}

  @Permiso({
    soloIdentidad: 'toda persona activa pide un fichero; la puerta del módulo decide si es de su puesto',
    sinRecorte: 'el recorte lo hace recortarModulo + quitarBajas línea a línea como servir.py:3020',
  })
  @Get('*rel')
  async leer(
    @Param('rel') p: string | string[],
    @Req() req: { vista: VistaConContexto; headers: Record<string, string | string[] | undefined> },
    @Res() res: Respuesta,
  ): Promise<void> {
    const rel = Array.isArray(p) ? p.join('/') : String(p ?? '');
    const pedido = req.headers['if-none-match'];
    const ifNone = Array.isArray(pedido) ? pedido[0] : pedido;
    try {
      const out = await this.datos.leer(req.vista, rel, ifNone);
      if (out.etag) res.setHeader('ETag', out.etag);
      if (out.codigo === 304) {
        res.status(304).end();
        return;
      }
      res.status(200).json(out.cuerpo);
    } catch (e) {
      if (e instanceof HttpException) {
        const cuerpo = e.getResponse();
        const texto = typeof cuerpo === 'string' ? cuerpo : e.message;
        res.status(e.getStatus()).json({ error: texto });
        return;
      }
      throw e;
    }
  }
}
