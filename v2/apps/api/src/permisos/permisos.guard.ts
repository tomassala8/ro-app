import { CanActivate, ExecutionContext, ForbiddenException, HttpException, Inject, Injectable } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { CLAVE_PERMISO, CLAVE_PUBLICO, type DeclaracionPermiso } from './declarar.js';
import { MOTOR_PERMISOS, RASTRO_VER_COMO, type MotorPermisos, type RastroVerComo, type Vista } from './motor.js';

/** Guarda global: toda ruta de Nest pasa por aquí. Sin declaración, 403. */
@Injectable()
export class PermisosGuard implements CanActivate {
  constructor(
    private readonly reflector: Reflector,
    @Inject(MOTOR_PERMISOS) private readonly motor: MotorPermisos,
    @Inject(RASTRO_VER_COMO) private readonly rastro: RastroVerComo,
  ) {}

  async canActivate(contexto: ExecutionContext): Promise<boolean> {
    const objetivos = [contexto.getHandler(), contexto.getClass()];
    if (this.reflector.getAllAndOverride<string>(CLAVE_PUBLICO, objetivos)) return true;
    const declaracion = this.reflector.getAllAndOverride<DeclaracionPermiso>(CLAVE_PERMISO, objetivos);
    if (!declaracion) throw new ForbiddenException('Ruta sin permiso declarado.');
    const req = contexto.switchToHttp().getRequest<{ vista?: Vista; method?: string; originalUrl?: string; url?: string }>();
    const metodo = (req.method ?? 'GET').toUpperCase();
    const escribe = metodo !== 'GET' && !declaracion.lecturaPorPost;
    if (escribe && req.vista?.como) throw new ForbiddenException('Estás en «ver como»: es solo lectura. No se escribe nada.'); // texto de servir.py
    const decision = this.motor.entrar(req.vista, declaracion);
    if (!decision.ok) throw new HttpException(decision.mensaje ?? 'Sin permiso.', decision.status ?? 403);
    if (req.vista?.como) {
      try {
        await this.rastro.apuntar(req.vista, metodo, req.originalUrl ?? req.url ?? '');
      } catch {
        throw new HttpException('No se puede apuntar en el rastro: «ver como» no está disponible.', 503);
      }
    }
    return true;
  }
}
