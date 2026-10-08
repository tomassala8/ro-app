import { Controller, Get } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import { DecisionesService } from './decisiones.service.js';

/** GET /api/respuestas_mili. Controlador aparte: nunca una ruta '../' dentro de DecisionesController. */
@Controller('respuestas_mili')
export class RespuestasMiliController {
  constructor(private readonly decisiones: DecisionesService) {}

  @Permiso({
    tipo: 'ajustes_editar',
    mensaje: 'Solo Mili y Tomás.',
    sinRecorte: 'respuestas de para_confirmar: sin clientes ni importes',
  })
  @Get()
  leer() {
    return this.decisiones.respuestasMili();
  }
}
