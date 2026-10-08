import { Body, Controller, Get, HttpCode, Post, Req } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { DecisionesService } from './decisiones.service.js';

/** GET y POST /api/decisiones. Identidad sin módulo: el recorte va dentro. */
@Controller('decisiones')
export class DecisionesController {
  constructor(private readonly decisiones: DecisionesService) {}

  @Permiso({
    soloIdentidad: 'toda persona activa lee las decisiones de su ámbito',
    sinRecorte: 'recorte por fila con recorteImportesLectura588 y filtroDecisiones como servir.py:2893-2894',
  })
  @Get()
  listar(@Req() req: { vista: VistaConContexto }) {
    return this.decisiones.listar(req.vista);
  }

  @Permiso({
    soloIdentidad: 'toda persona activa puede subir o contestar; «ver como» no escribe',
    sinRecorte: 'la respuesta es ok e id, sin datos de clientes',
  })
  @Post()
  @HttpCode(200)
  escribir(@Req() req: { vista: VistaConContexto }, @Body() body: unknown) {
    return this.decisiones.escribir(req.vista, body);
  }
}
