import { Module } from '@nestjs/common';
import { RastroModule } from '../rastro/rastro.module.js';
import { AvisosController } from './avisos.controller.js';
import { AvisosService } from './avisos.service.js';

/** Avisos de la app (tabla avisos). El bucle y ClickUp se quedan en el legado. */
@Module({
  imports: [RastroModule],
  controllers: [AvisosController],
  providers: [AvisosService],
})
export class AvisosModule {}
