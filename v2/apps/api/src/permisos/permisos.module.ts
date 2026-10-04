import { Global, Module } from '@nestjs/common';
import { APP_GUARD, APP_INTERCEPTOR } from '@nestjs/core';
import { MOTOR_PERMISOS, MotorSinPortar } from './motor.js';
import { PermisosGuard } from './permisos.guard.js';
import { RecortarInterceptor } from './recortar.interceptor.js';

/** Permisos en un solo sitio: la guarda y el recorte globales, y el motor que deciden (fase 4: @ro/permisos). */
@Global()
@Module({
  providers: [
    { provide: MOTOR_PERMISOS, useClass: MotorSinPortar },
    { provide: APP_GUARD, useClass: PermisosGuard },
    { provide: APP_INTERCEPTOR, useClass: RecortarInterceptor },
  ],
  exports: [MOTOR_PERMISOS],
})
export class PermisosModule {}
