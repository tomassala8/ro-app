import { Module } from '@nestjs/common';
import { RastroModule } from '../rastro/rastro.module.js';
import { VerDatoController } from './ver-dato.controller.js';
import { VerDatoService } from './ver-dato.service.js';

/** «Ver datos» de un almacén privado: un valor y su rastro. */
@Module({
  imports: [RastroModule],
  controllers: [VerDatoController],
  providers: [VerDatoService],
})
export class VerDatoModule {}
