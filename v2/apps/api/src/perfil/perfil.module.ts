import { Module } from '@nestjs/common';
import { RastroModule } from '../rastro/rastro.module.js';
import { PreferenciasController } from './preferencias.controller.js';
import { PreferenciasService } from './preferencias.service.js';

/** Preferencias. El perfil se queda en el proxy: la lista de zonas de Node no es la de Python. */
@Module({
  imports: [RastroModule],
  controllers: [PreferenciasController],
  providers: [PreferenciasService],
})
export class PerfilModule {}
