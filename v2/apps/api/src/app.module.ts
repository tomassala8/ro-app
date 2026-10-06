import { Module, type OnApplicationBootstrap } from '@nestjs/common';
import { HttpAdapterHost } from '@nestjs/core';
import { IdentidadModule } from './permisos/identidad.module.js';
import { PermisosModule } from './permisos/permisos.module.js';
import { PrismaModule } from './prisma/prisma.module.js';
import { RastroModule } from './rastro/rastro.module.js';
import { SaludController } from './salud/salud.controller.js';
import { SesionModule } from './sesion/sesion.module.js';

// Un módulo de Nest por dominio (ver migracion/PLAN_MAESTRO.md › «Backend»): identidad, permisos, sesion, datos,
// clientes, rastro, acciones, decisiones, ajustes, avisos, perfil, opiniones, recarga, buscar, indicadores…
// IdentidadModule va antes que PermisosModule: su guarda tiene que correr primero.
@Module({
  imports: [PrismaModule, RastroModule, IdentidadModule, PermisosModule, SesionModule],
  controllers: [SaludController],
})
export class AppModule implements OnApplicationBootstrap {
  constructor(private readonly http: HttpAdapterHost) {}

  // servir.py no manda ETag en las respuestas de /api (ni contesta 304): Express lo pone por defecto.
  onApplicationBootstrap() {
    const app = this.http.httpAdapter?.getInstance?.() as { set?(k: string, v: unknown): void } | undefined;
    app?.set?.('etag', false);
  }
}
