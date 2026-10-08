import { Module } from '@nestjs/common';
import { RastroModule } from '../rastro/rastro.module.js';
import { DecisionesController } from './decisiones.controller.js';
import { DecisionesService } from './decisiones.service.js';
import { RespuestasMiliController } from './respuestas-mili.controller.js';

/** Decisiones en vivo y el volcado de respuestas para confirmar. */
@Module({
  imports: [RastroModule],
  controllers: [DecisionesController, RespuestasMiliController],
  providers: [DecisionesService],
})
export class DecisionesModule {}
