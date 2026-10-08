import { Module } from '@nestjs/common';
import { RastroModule } from '../rastro/rastro.module.js';
import { OpinionController, OpinionesController } from './opiniones.controller.js';
import { OpinionesService } from './opiniones.service.js';

/** «Algo va mal / Tengo una idea» y el aviso en el canal de dirección. */
@Module({
  imports: [RastroModule],
  controllers: [OpinionesController, OpinionController],
  providers: [OpinionesService],
})
export class OpinionesModule {}
