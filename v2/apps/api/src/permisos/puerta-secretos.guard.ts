import { CanActivate, ExecutionContext, HttpException, Injectable } from '@nestjs/common';
import { tokenDe } from './access-jwt.js';
import { declaracionDe } from './declarar.js';
import { SIN_IDENTIDAD } from './identidad.guard.js';
import type { VistaConContexto } from './motor-ro.js';
import { PuertaSecretosService } from './puerta-secretos.service.js';

interface Peticion {
  headers: Record<string, string | string[] | undefined>;
  originalUrl?: string;
  url?: string;
  vista?: VistaConContexto;
}

/**
 * Guarda global entre la de identidad y la de permisos (el orden de servir.py: _quien → puerta de secretos →
 * permisos). Con la puerta cerrada, o sin poder saberlo, la ruta no se sirve.
 */
@Injectable()
export class PuertaSecretosGuard implements CanActivate {
  constructor(private readonly puerta: PuertaSecretosService) {}

  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    const req = ctx.switchToHttp().getRequest<Peticion>();
    const ruta = (req.originalUrl ?? req.url ?? '').split('?')[0] ?? '';
    const { publico } = declaracionDe(ctx.getHandler(), ctx.getClass());
    if (publico && SIN_IDENTIDAD.includes(ruta)) return true;
    const e = await this.puerta.estado(this.identidad(req));
    if (!e.abierta) throw new HttpException(e.error, e.status);
    return true;
  }

  private identidad(req: Peticion): Record<string, string> {
    if (process.env.RO_IDENTIDAD === 'access') {
      const token = tokenDe(req.headers as never);
      return token ? { 'cf-access-jwt-assertion': token } : {};
    }
    const id = req.vista?.real?.id;
    return typeof id === 'string' ? { 'x-ro-yo': id } : {};
  }
}
