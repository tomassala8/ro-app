import { Module } from '@nestjs/common';
import { RastroModule } from '../rastro/rastro.module.js';
import { DatosController } from './datos.controller.js';
import { DatosService } from './datos.service.js';

/** GET /api/modulo/<rel> para la lista cerrada MODULOS_EN_NEST. */
@Module({ imports: [RastroModule], controllers: [DatosController], providers: [DatosService] })
export class DatosModule {}
