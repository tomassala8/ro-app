import { Module } from '@nestjs/common';
import { AccionesController } from './acciones.controller.js';
import { AccionesService } from './acciones.service.js';

/** Lectura de acciones. El POST se queda en servir.py. */
@Module({
  controllers: [AccionesController],
  providers: [AccionesService],
})
export class AccionesModule {}
