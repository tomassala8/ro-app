import { Global, Module } from '@nestjs/common';
import { APP_FILTER, APP_GUARD, APP_INTERCEPTOR } from '@nestjs/core';
import { ErroresFilter } from './errores.filter.js';
import { MOTOR_PERMISOS, MotorSinPortar, RASTRO_VER_COMO, RastroVerComoSinPortar } from './motor.js';
import { PermisosGuard } from './permisos.guard.js';
import { RecortarInterceptor } from './recortar.interceptor.js';

/** Permisos en un solo sitio: la guarda y el recorte globales, y el motor que deciden (fase 4: @ro/permisos). */
@Global()
@Module({
  providers: [
    { provide: MOTOR_PERMISOS, useClass: MotorSinPortar },
    { provide: RASTRO_VER_COMO, useClass: RastroVerComoSinPortar },
    { provide: APP_GUARD, useClass: PermisosGuard },
    { provide: APP_INTERCEPTOR, useClass: RecortarInterceptor },
    { provide: APP_FILTER, useClass: ErroresFilter },
  ],
  exports: [MOTOR_PERMISOS, RASTRO_VER_COMO],
})
export class PermisosModule {}
