import { Controller, Get, Req, Res } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { IndicadoresService } from './indicadores.service.js';

type Respuesta = {
  status(c: number): Respuesta;
  setHeader(k: string, v: string): Respuesta;
  json(c: unknown): void;
  end(): void;
};

/**
 * GET /api/indicadores. Identidad sin módulo: el recorte es por puestos y por importes, como servir.py:2828-2839.
 */
@Controller('indicadores')
export class IndicadoresController {
  constructor(private readonly indicadores: IndicadoresService) {}

  @Permiso({
    soloIdentidad: 'toda persona activa pide el catálogo; el recorte es por sus puestos',
    sinRecorte: 'recorte por puestos y sinImportes como servir.py:2749-2759',
  })
  @Get()
  leer(
    @Req() req: { vista: VistaConContexto; headers: Record<string, string | string[] | undefined> },
    @Res() res: Respuesta,
  ): void {
    const pedido = req.headers['if-none-match'];
    const ifNone = Array.isArray(pedido) ? pedido[0] : pedido;
    const out = this.indicadores.catalogo(req.vista, ifNone);
    res.setHeader('ETag', out.etag);
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Vary', 'Accept-Encoding, Cookie, X-RO-Yo, X-RO-Como');
    if (out.codigo === 304) {
      res.status(304).end();
      return;
    }
    res.status(200).json(out.cuerpo);
  }
}
