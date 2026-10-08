import { Module } from '@nestjs/common';
import { RastroModule } from '../rastro/rastro.module.js';
import { AjustesController } from './ajustes.controller.js';
import { AjustesService } from './ajustes.service.js';

/** Ajustes: personas, asignaciones y «para confirmar». */
@Module({
  imports: [RastroModule],
  controllers: [AjustesController],
  providers: [AjustesService],
})
export class AjustesModule {}
