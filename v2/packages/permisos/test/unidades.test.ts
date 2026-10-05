import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  cargarModulos,
  clasificarImporte580,
  enmascarar,
  enlaceSeguro,
  importesAQuitar,
  nivelModulo,
  sinImportes,
  soloFilasDe,
} from '../src/index.js';
import type { Persona } from '../src/tipos.js';

const account: Persona = { id: 'p1', nombre: 'P', puestos: ['account'] };

describe('unidades del motor', () => {
  it('enmascara correo, teléfono largo y palabras', () => {
    expect(enmascarar('ana@ejemplo.test')).toBe('a···@ejemplo.test');
    expect(enmascarar('tel 600111222')).toBe('tel ······222');
    expect(enmascarar('Hola mundo')).toBe('H··· m···');
  });

  it('enlaceSeguro deja rutas y https, y tira javascript', () => {
    expect(enlaceSeguro('javascript:alert(1)')).toBeNull();
    expect(enlaceSeguro('#/ficha')).toBe('#/ficha');
    expect(enlaceSeguro('  https://x.test ')).toBe('https://x.test');
    expect(enlaceSeguro('')).toBe('');
  });

  it('importesAQuitar trata None distinto de False', () => {
    expect(importesAQuitar(false, true, undefined, false)).toEqual(['cuota', 'dinero_empresa']);
  });

  it('sinImportes coincide con permisos.py en cuatro textos inventados', () => {
    const quitar = ['cuota', 'inversion'];
    expect(sinImportes('Gasto (142 €) en la campaña', quitar)).toBe('Gasto en la campaña');
    expect(sinImportes('Uno · 80 € al mes · otro texto', quitar)).toBe('Uno otro texto');
    expect(sinImportes('2 leads a 167 €/mes cada uno', quitar)).toBe('2 leads cada uno');
    expect(sinImportes('Techo de 40 € por lead', quitar)).toBe('Techo');
  });

  it('sinImportes no corta palabras con ñ o tilde ante un importe (\\b de Python)', () => {
    const quitar = ['cuota', 'inversion'];
    expect(sinImportes('Gasto de la campaña 300 €', quitar)).toBe('Gasto de la campaña');
    expect(sinImportes('Inversión en España 1.200 €', quitar)).toBe('Inversión en España');
    expect(sinImportes('Asesoría 300 € al mes', quitar)).toBe('Asesoría');
    expect(sinImportes('Día 50 €', quitar)).toBe('Día');
  });

  it('clasificarImporte580 lee «facturación» entera (\\w de Python)', () => {
    const t = 'Facturación mensual: 300 €';
    expect(clasificarImporte580(t, t.indexOf('300'), t.length)).toBe('cuota');
  });

  it('soloFilasDe quita filas con cliente_id ajeno aunque no sea texto', () => {
    const cuerpo = { f: [{ cliente_id: 5 }, { cliente_id: 'c1' }, { cliente_id: '' }, { x: 1 }] };
    expect(soloFilasDe(cuerpo, new Set(['c1']))).toEqual({ f: [{ cliente_id: 'c1' }, { cliente_id: '' }, { x: 1 }] });
  });

  it('un null explícito en el mapa no cae al comodín', () => {
    expect(nivelModulo(account, { account: null, '*': 'todo' })).toBeNull();
  });

  it('cargarModulos coincide con el vector', () => {
    const dir = process.env.RO_VECTORES?.replace(/^~/, process.env.HOME ?? '');
    if (!dir || !existsSync(join(dir, 'modulos.json'))) return;
    const esperado = JSON.parse(readFileSync(join(dir, 'modulos.json'), 'utf8'));
    expect(cargarModulos()).toEqual(esperado);
  });
});
