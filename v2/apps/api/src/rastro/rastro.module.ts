import { Module } from '@nestjs/common';
import { RastroController } from './rastro.controller.js';
import { RastroLecturaService } from './rastro-lectura.service.js';
import { RastroService } from './rastro.service.js';
import { VerificarService } from './verificar.service.js';

/** El rastro imborrable (tabla registro + registro_huellas) y sus tres rutas. */
@Module({
  controllers: [RastroController],
  providers: [RastroService, VerificarService, RastroLecturaService],
  exports: [RastroService],
})
export class RastroModule {}
