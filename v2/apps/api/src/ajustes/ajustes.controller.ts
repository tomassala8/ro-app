import { Body, Controller, Get, HttpCode, Param, Post, Req } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { AjustesService } from './ajustes.service.js';

/** GET /api/ajustes y POST /api/ajustes/<persona|asignacion|confirmar>. */
@Controller('ajustes')
export class AjustesController {
  constructor(private readonly ajustes: AjustesService) {}

  @Permiso({
    tipo: 'ajustes_editar',
    oPuesto: 'rrhh',
    mensaje: 'Ajustes es de Mili y Tomás (RRHH, en resumen).',
    sinRecorte: 'recorte por nivel_ok con PERSONA_PUBLICA como servir.py:2850',
  })
  @Get()
  leer(@Req() req: { vista: VistaConContexto }) {
    return this.ajustes.leer(req.vista);
  }

  @Permiso({
    tipo: 'ajustes_editar',
    sinRecorte: 'la respuesta es ok, sin datos de clientes',
  })
  @Post('*resto')
  @HttpCode(200)
  escribir(@Param('resto') resto: string | string[], @Req() req: { vista: VistaConContexto }, @Body() body: unknown) {
    const sub = Array.isArray(resto) ? resto.join('/') : String(resto ?? '');
    return this.ajustes.escribir(req.vista, sub, body);
  }
}
