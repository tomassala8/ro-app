import { Global, Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { CrudoService } from './crudo.service.js';
import { IdentidadGuard } from './identidad.guard.js';

/**
 * Quién es (servir.py › host_ok y _quien): deja `req.vista` para la guarda de permisos. AppModule lo importa ANTES
 * que PermisosModule: las guardas globales corren en el orden en que se registran (lo comprueba identidad.e2e-spec).
 */
@Global()
@Module({
  providers: [CrudoService, { provide: APP_GUARD, useClass: IdentidadGuard }],
  exports: [CrudoService],
})
export class IdentidadModule {}
