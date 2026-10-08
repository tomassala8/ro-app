import { Body, Controller, Get, HttpCode, Post, Req } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { PreferenciasService } from './preferencias.service.js';

/**
 * GET y POST /api/preferencias. Identidad sin módulo: la lista ya sale filtrada.
 * «Ver como» en el POST lo corta la guarda (escritura).
 */
@Controller('preferencias')
export class PreferenciasController {
  constructor(private readonly preferencias: PreferenciasService) {}

  @Permiso({
    soloIdentidad: 'toda persona activa lee sus clientes fijados',
    sinRecorte: 'la lista ya se filtra con recortar(persona).clientes[].detalle como servir.py:3021-3024',
  })
  @Get()
  leer(@Req() req: { vista: VistaConContexto }) {
    return this.preferencias.leer(req.vista);
  }

  @Permiso({
    soloIdentidad: 'toda persona activa guarda sus clientes fijados; «ver como» no escribe',
    sinRecorte: 'la respuesta es ok y la lista, sin datos de clientes',
  })
  @Post()
  @HttpCode(200)
  guardar(@Req() req: { vista: VistaConContexto }, @Body() body: unknown) {
    return this.preferencias.guardar(req.vista, body);
  }
}
