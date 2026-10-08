import { Body, Controller, Get, HttpCode, Post, Req } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { AvisosService } from './avisos.service.js';

/** Avisos de la app. El motor da el «no» de recargar. Los canales siguen en el proxy. */
@Controller('avisos')
export class AvisosController {
  constructor(private readonly avisos: AvisosService) {}

  @Permiso({
    tipo: 'recargar',
    sinRecorte: 'avisos de la app: sin clientes ni importes; filas enteras como servir.py:2884',
  })
  @Get()
  listar() {
    return this.avisos.listar();
  }

  @Permiso({
    tipo: 'recargar',
    sinRecorte: 'la respuesta es ok, sin datos de clientes',
  })
  @Post('visto')
  @HttpCode(200)
  visto(@Req() req: { vista: VistaConContexto }, @Body() body: unknown) {
    return this.avisos.visto(req.vista, body);
  }
}
