import { Global, Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { CrudoService } from './crudo.service.js';
import { IdentidadGuard } from './identidad.guard.js';
import { PuertaSecretosGuard } from './puerta-secretos.guard.js';
import { PuertaSecretosService } from './puerta-secretos.service.js';

/**
 * Quién es (servir.py › host_ok y _quien): deja `req.vista` para la guarda de permisos. Después, la puerta de
 * secretos (servir.py › _api_get). AppModule lo importa ANTES que PermisosModule: las guardas globales corren en el
 * orden en que se registran (lo comprueba identidad.e2e-spec).
 */
@Global()
@Module({
  providers: [
    CrudoService,
    PuertaSecretosService,
    { provide: APP_GUARD, useClass: IdentidadGuard },
    { provide: APP_GUARD, useClass: PuertaSecretosGuard },
  ],
  exports: [CrudoService, PuertaSecretosService],
})
export class IdentidadModule {}
