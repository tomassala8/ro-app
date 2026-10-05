import { Module } from '@nestjs/common';
import { PermisosModule } from './permisos/permisos.module.js';
import { PrismaModule } from './prisma/prisma.module.js';
import { SaludController } from './salud/salud.controller.js';

// Un módulo de Nest por dominio (ver migracion/PLAN_MAESTRO.md › «Backend»): identidad, permisos, sesion, datos,
// clientes, rastro, acciones, decisiones, ajustes, avisos, perfil, opiniones, recarga, buscar, indicadores…
@Module({
  imports: [PrismaModule, PermisosModule],
  controllers: [SaludController],
})
export class AppModule {}
