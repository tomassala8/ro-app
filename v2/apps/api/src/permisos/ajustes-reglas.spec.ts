import { describe, expect, it } from 'vitest';
import { errorPuestos, reglasCambioPersona, validarAsignacion579, validarLista572 } from './ajustes-reglas.js';
import { configAlmacen, duenoOk } from './ver-dato-reglas.js';
import type { Persona } from '@ro/permisos';

describe('reglas de ajustes y ver_dato', () => {
  it('imprime los puestos malos como Python', () => {
    expect(errorPuestos(['no_existe'])).toBe("Puestos no válidos: ['no_existe']");
    expect(errorPuestos([])).toBe('Puestos no válidos: ninguno');
    expect(errorPuestos(['account'])).toBeNull();
  });

  it('nadie cambia sus propios puestos', () => {
    const p = { id: 'tomas', puestos: ['direccion'] };
    const r = reglasCambioPersona({ id: 'tomas', puestos: ['direccion'] }, p, { puestos: ['account'] });
    expect(r).toEqual([403, 'Nadie cambia sus propios puestos: pídeselo a Tomás.']);
  });

  it('una asignación sin operación no vale', () => {
    expect(validarAsignacion579({ clientes: [], personas: [], asignaciones: [], alarmas: [], meta: {} }, { operacion: 'borrar' }, '2026-10-08')).toBeNull();
  });

  it('una confirmación vacía no vale', () => {
    expect(validarLista572({}, { clientes: [], personas: [], asignaciones: [], alarmas: [], meta: {}, para_confirmar: [] })).toBe(false);
  });

  it('configAlmacen casa setter_* y rechaza ..', () => {
    expect(configAlmacen('ventas_ro/_privado/setter_ana')?.dueno_setter).toBe(true);
    expect(configAlmacen('agenda/_privado/tomas')?.dueno).toBe('fichero');
    expect(configAlmacen('leads')).toBeNull();
    expect(configAlmacen('a/../_privado/x')).toBeNull();
  });

  it('dueño_ok: sin dueno_setter pasa; con él, solo su fichero o dirección', () => {
    const setter: Persona = { id: 'setter_ana', nombre: 'A', puestos: ['setters'] };
    const account: Persona = { id: 'acc', nombre: 'C', puestos: ['account'] };
    expect(duenoOk(account, {}, 'cualquiera')).toBe(true);
    expect(duenoOk(setter, { dueno_setter: true }, 'setter_ana')).toBe(true);
    expect(duenoOk(account, { dueno_setter: true }, 'setter_ana')).toBe(false);
  });
});
