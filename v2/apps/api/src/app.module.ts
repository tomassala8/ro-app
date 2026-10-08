import {
  type MiddlewareConsumer,
  Module,
  type NestModule,
  type OnApplicationBootstrap,
  RequestMethod,
} from '@nestjs/common';
import { HttpAdapterHost } from '@nestjs/core';
import { cabecerasSeguridad } from './permisos/cabeceras.middleware.js';
import { PeticionMiddleware } from './permisos/peticion.middleware.js';
import { IdentidadModule } from './permisos/identidad.module.js';
import { PermisosModule } from './permisos/permisos.module.js';
import { PrismaModule } from './prisma/prisma.module.js';
import { ClientesModule } from './clientes/clientes.module.js';
import { IndicadoresModule } from './indicadores/indicadores.module.js';
import { PerfilModule } from './perfil/perfil.module.js';
import { DecisionesModule } from './decisiones/decisiones.module.js';
import { OpinionesModule } from './opiniones/opiniones.module.js';
import { DatosModule } from './datos/datos.module.js';
import { RastroModule } from './rastro/rastro.module.js';
import { SaludController } from './salud/salud.controller.js';
import { SesionModule } from './sesion/sesion.module.js';

// Un módulo de Nest por dominio (ver migracion/PLAN_MAESTRO.md › «Backend»): identidad, permisos, sesion, datos,
// clientes, rastro, acciones, decisiones, ajustes, avisos, perfil, opiniones, recarga, buscar, indicadores…
// IdentidadModule va antes que PermisosModule: su guarda tiene que correr primero.
@Module({
  imports: [PrismaModule, RastroModule, IdentidadModule, PermisosModule, SesionModule, DatosModule, ClientesModule, IndicadoresModule, PerfilModule, DecisionesModule, OpinionesModule],
  controllers: [SaludController],
})
export class AppModule implements NestModule, OnApplicationBootstrap {
  constructor(private readonly http: HttpAdapterHost) {}

  // Cabeceras de seguridad de servir.py en todas las rutas de Nest, también en los errores de las guardas.
  configure(consumer: MiddlewareConsumer) {
    const todas = { path: '{*splat}', method: RequestMethod.ALL };
    // Cabeceras primero: un 403 de la petición sale con las mismas cabeceras que servir.py.
    consumer.apply(cabecerasSeguridad).forRoutes(todas);
    // Host, HEAD/OPTIONS y la petición propia de los POST. Corre después del proxy (main.ts) y antes de las guardas.
    consumer.apply(PeticionMiddleware).forRoutes(todas);
  }

  // servir.py no manda ETag en las respuestas de /api (ni contesta 304): Express lo pone por defecto.
  onApplicationBootstrap() {
    const app = this.http.httpAdapter?.getInstance?.() as { set?(k: string, v: unknown): void } | undefined;
    app?.set?.('etag', false);
  }
}
