import { CallHandler, ExecutionContext, Inject, Injectable, NestInterceptor } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { map, type Observable } from 'rxjs';
import { CLAVE_PERMISO, type DeclaracionPermiso } from './declarar.js';
import { MOTOR_PERMISOS, type MotorPermisos, type Vista } from './motor.js';

/** Recorte global: si la ruta declara `recortar: true`, la respuesta sale por el motor. Nadie recorta a mano. */
@Injectable()
export class RecortarInterceptor implements NestInterceptor {
  constructor(
    private readonly reflector: Reflector,
    @Inject(MOTOR_PERMISOS) private readonly motor: MotorPermisos,
  ) {}

  intercept(contexto: ExecutionContext, siguiente: CallHandler): Observable<unknown> {
    const declaracion = this.reflector.getAllAndOverride<DeclaracionPermiso>(CLAVE_PERMISO, [
      contexto.getHandler(),
      contexto.getClass(),
    ]);
    if (!declaracion?.recortar) return siguiente.handle();
    const req = contexto.switchToHttp().getRequest<{ vista?: Vista }>();
    return siguiente.handle().pipe(map((cuerpo) => this.motor.recortar(req.vista, declaracion, cuerpo)));
  }
}
