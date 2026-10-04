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

/** Apunta en el rastro cada petición hecha en «ver como» (quién real, a quién mira, método y ruta). F5.6 la implementa
 *  con el módulo de rastro (agrupada por minuto, como pide L-08). Hasta entonces las rutas van por servir.py. */
export interface RastroVerComo {
  apuntar(vista: Vista, metodo: string, ruta: string): void | Promise<void>;
}

export const RASTRO_VER_COMO = Symbol('RASTRO_VER_COMO');

@Injectable()
export class RastroVerComoSinPortar implements RastroVerComo {
  apuntar(): never {
    // Nada de «ver como» sin rastro: mientras no esté portado, la guarda no deja pasar ninguna petición en «ver como».
    throw new Error('El rastro de «ver como» aún no está portado (F5.6).');
  }
}

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
