import { Global, Module } from '@nestjs/common';
import { APP_FILTER, APP_GUARD, APP_INTERCEPTOR } from '@nestjs/core';
import { ErroresFilter } from './errores.filter.js';
import { MOTOR_PERMISOS, RASTRO_VER_COMO } from './motor.js';
import { MotorRo } from './motor-ro.js';
import { PermisosGuard } from './permisos.guard.js';
import { RastroVerComoRo } from './rastro-ver-como-ro.js';
import { RecortarInterceptor } from './recortar.interceptor.js';

/** Permisos en un solo sitio: la guarda y el recorte globales, y el motor que decide (@ro/permisos). */
@Global()
@Module({
  providers: [
    { provide: MOTOR_PERMISOS, useClass: MotorRo },
    { provide: RASTRO_VER_COMO, useClass: RastroVerComoRo },
    { provide: APP_GUARD, useClass: PermisosGuard },
    { provide: APP_INTERCEPTOR, useClass: RecortarInterceptor },
    { provide: APP_FILTER, useClass: ErroresFilter },
  ],
  exports: [MOTOR_PERMISOS, RASTRO_VER_COMO],
})
export class PermisosModule {}
