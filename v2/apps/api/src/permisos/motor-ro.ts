import { Injectable } from '@nestjs/common';
import {
  ambito,
  conVista,
  importesAQuitar,
  nivelModulo,
  sinImportes,
  soloFilasDe,
  soloSuCartera,
  puestosDe,
  ver,
  type Contexto,
  type Persona,
} from '@ro/permisos';
import type { DeclaracionPermiso } from './declarar.js';
import type { Decision, MotorPermisos, Vista } from './motor.js';
import { modulosActuales } from './recarga.js';

const SIN_IDENTIFICAR = 'Sin identificar. En el prototipo, elige quién eres; en el servidor, entra por Cloudflare Access.';
const PANTALLA_AJENA = 'Estos datos son de una pantalla que no es de tu puesto.';

/** Lo usa la guarda (permisos.guard.ts). Queda exportada para F5.1 y no se repite aquí. */
export const VER_COMO_SOLO_LECTURA = 'Estás en «ver como»: es solo lectura. No se escribe nada.';

/** Contexto de permisos que la guarda de identidad (F5.1) deja en req.vista. */
export interface VistaConContexto extends Vista {
  cp?: Contexto;
  cpReal?: Contexto;
}

function comoPersona(p: Vista['real']): Persona {
  return { nombre: '', ...p, puestos: p.puestos ?? [] };
}

@Injectable()
export class MotorRo implements MotorPermisos {
  entrar(vista: VistaConContexto | undefined, d: DeclaracionPermiso): Decision {
    if (!vista) return { ok: false, status: 401, mensaje: SIN_IDENTIFICAR };
    const persona = comoPersona(vista.como ?? vista.real);
    const decide = (): Decision => {
      if (d.soloIdentidad) return { ok: true };
      if (d.modulo !== undefined) {
        const mapa = modulosActuales()[d.modulo];
        if (!mapa || !nivelModulo(persona, mapa)) return { ok: false, status: 403, mensaje: PANTALLA_AJENA };
        return { ok: true };
      }
      if (d.tipo !== undefined || d.oPuesto) {
        let ok = false;
        let motivo = d.mensaje ?? 'No visible para tu puesto.';
        if (d.tipo !== undefined) {
          const r = ver(persona, { tipo: d.tipo }, vista.cp ?? {});
          if (r.ok) ok = true;
          else if (!d.mensaje) motivo = r.motivo || 'No visible para tu puesto.';
        }
        // En «ver como», puestosDe es la intersección de las dos personas.
        if (!ok && d.oPuesto && puestosDe(persona).has(d.oPuesto)) ok = true;
        return ok ? { ok: true } : { ok: false, status: 403, mensaje: motivo };
      }
      return { ok: false, status: 403, mensaje: 'Sin permiso.' };
    };
    const real = comoPersona(vista.real);
    return vista.como && vista.cpReal ? conVista({ real, cp: vista.cpReal }, decide) : decide();
  }

  recortar(vista: VistaConContexto | undefined, _d: DeclaracionPermiso, cuerpo: unknown): unknown {
    if (!vista?.cp) throw new Error('Vista sin contexto de permisos: la guarda de identidad (F5.1) tiene que ponerlo.');
    const persona = comoPersona(vista.como ?? vista.real);
    const cp = vista.cp;
    const aplicar = (): unknown => {
      let salida = soloSuCartera(persona) ? soloFilasDe(cuerpo, cp.cartera_ids) : cuerpo;
      const ve = (tipo: string) => ver(persona, { tipo }, cp).ok;
      const quita = importesAQuitar(ve('cuota'), ve('inversion'), ve('cobros'), ve('dinero_empresa'));
      if (quita.length) salida = sinImportes(salida, quita);
      return salida;
    };
    const real = comoPersona(vista.real);
    return vista.como && vista.cpReal ? conVista({ real, cp: vista.cpReal }, aplicar) : aplicar();
  }
}

export { ambito };
