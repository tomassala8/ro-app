import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { Contexto, Persona } from '@ro/permisos';
import { MotorRo } from './motor-ro.js';

const reglas = JSON.parse(readFileSync(new URL('../../../../../reglas_permisos.json', import.meta.url), 'utf8')) as {
  tipos: { sueldo: { no?: string } };
};

const account: Persona = { id: 'p1', nombre: 'P', puestos: ['account'] };
const direccion: Persona = { id: 'dir', nombre: 'D', puestos: ['direccion'] };
const cp = {
  cartera_ids: new Set(['c1']),
  cartera_por_silla: {},
  personas: [],
  clientes_por_id: {},
} as Contexto;

describe('MotorRo', () => {
  const motor = new MotorRo();

  it('sin vista no identifica', () => {
    expect(motor.entrar(undefined, { modulo: 'crm' })).toEqual({
      ok: false,
      status: 401,
      mensaje: 'Sin identificar. En el prototipo, elige quién eres; en el servidor, entra por Cloudflare Access.',
    });
  });

  it('un account no entra en ajustes y sí en mi-dia', () => {
    const vista = { real: account, cp };
    expect(motor.entrar(vista, { modulo: 'ajustes' })).toEqual({
      ok: false,
      status: 403,
      mensaje: 'Estos datos son de una pantalla que no es de tu puesto.',
    });
    expect(motor.entrar(vista, { modulo: 'mi-dia' })).toEqual({ ok: true });
  });

  it('soloIdentidad deja entrar a cualquier persona identificada, pero no sin identidad', () => {
    expect(motor.entrar({ real: account, cp }, { soloIdentidad: 'sesión' })).toEqual({ ok: true });
    expect(motor.entrar(undefined, { soloIdentidad: 'sesión' })).toMatchObject({ ok: false, status: 401 });
  });

  it('el mensaje de la declaración sustituye al motivo de la matriz', () => {
    const r = motor.entrar({ real: account, cp }, { tipo: 'sueldo', mensaje: 'Solo dirección.' });
    expect(r).toEqual({ ok: false, status: 403, mensaje: 'Solo dirección.' });
  });

  it('un account no ve sueldos, con el motivo de la matriz', () => {
    const r = motor.entrar({ real: account, cp }, { tipo: 'sueldo' });
    expect(r.ok).toBe(false);
    expect(r.status).toBe(403);
    expect(r.mensaje).toBe(reglas.tipos.sueldo.no);
  });

  it('recortar sin contexto lanza', () => {
    expect(() => motor.recortar({ real: account }, { modulo: 'mi-dia' }, { nota: 'x' })).toThrow(/Vista sin contexto/);
  });

  it('recortar deja solo la cartera y quita el importe', () => {
    const salida = motor.recortar({ real: account, cp }, { modulo: 'mi-dia' }, {
      filas: [
        { cliente_id: 'c1', x: 1 },
        { cliente_id: 'c2', x: 2 },
      ],
      nota: 'Cuota 300 € al mes',
    });
    expect(salida).toEqual({ filas: [{ cliente_id: 'c1', x: 1 }], nota: 'Cuota' });
  });

  it('ver como usa el mínimo: un account no abre el panel de dirección', () => {
    const r = motor.entrar(
      { real: direccion, como: account, cp, cpReal: cp },
      { modulo: 'panel-direccion' },
    );
    expect(r).toEqual({
      ok: false,
      status: 403,
      mensaje: 'Estos datos son de una pantalla que no es de tu puesto.',
    });
  });
});
