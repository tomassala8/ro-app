import { Injectable } from '@nestjs/common';
import type { DeclaracionPermiso } from './declarar.js';

/** Quién pregunta: la persona real y, si está en «ver como», la persona que mira. La pone la guarda de identidad (F5.1). */
export interface Vista {
  real: { id: string; puestos: string[]; [clave: string]: unknown };
  como?: { id: string; puestos: string[]; [clave: string]: unknown };
}

export interface Decision {
  ok: boolean;
  /** Código y mensaje iguales que los de servir.py para el mismo caso. */
  status?: number;
  mensaje?: string;
}

/** El único sitio que decide. La fase 4 lo implementa con @ro/permisos (ver, nivelModulo, recortar…). */
export interface MotorPermisos {
  entrar(vista: Vista | undefined, declaracion: DeclaracionPermiso): Decision;
  recortar(vista: Vista | undefined, declaracion: DeclaracionPermiso, cuerpo: unknown): unknown;
}

export const MOTOR_PERMISOS = Symbol('MOTOR_PERMISOS');

/** Mientras el motor no esté portado (fase 4), toda ruta con permiso se deniega: nada se abre por accidente. */
@Injectable()
export class MotorSinPortar implements MotorPermisos {
  entrar(): Decision {
    return { ok: false, status: 403, mensaje: 'Sin permiso.' };
  }

  recortar(): unknown {
    throw new Error('El recorte de permisos aún no está portado (fase 4).');
  }
}
