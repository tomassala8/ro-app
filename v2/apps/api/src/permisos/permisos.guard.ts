import { CanActivate, ExecutionContext, ForbiddenException, HttpException, Inject, Injectable } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { CLAVE_PERMISO, CLAVE_PUBLICO, type DeclaracionPermiso } from './declarar.js';
import { MOTOR_PERMISOS, type MotorPermisos, type Vista } from './motor.js';

/** Guarda global: toda ruta de Nest pasa por aquí. Sin declaración, 403. */
@Injectable()
export class PermisosGuard implements CanActivate {
  constructor(
    private readonly reflector: Reflector,
    @Inject(MOTOR_PERMISOS) private readonly motor: MotorPermisos,
  ) {}

  canActivate(contexto: ExecutionContext): boolean {
    const objetivos = [contexto.getHandler(), contexto.getClass()];
    if (this.reflector.getAllAndOverride<string>(CLAVE_PUBLICO, objetivos)) return true;
    const declaracion = this.reflector.getAllAndOverride<DeclaracionPermiso>(CLAVE_PERMISO, objetivos);
    if (!declaracion) throw new ForbiddenException('Ruta sin permiso declarado.');
    const req = contexto.switchToHttp().getRequest<{ vista?: Vista }>();
    if (declaracion.escritura && req.vista?.como) throw new ForbiddenException('«Ver como» es solo de lectura.');
    const decision = this.motor.entrar(req.vista, declaracion);
    if (!decision.ok) throw new HttpException(decision.mensaje ?? 'Sin permiso.', decision.status ?? 403);
    return true;
  }
}
