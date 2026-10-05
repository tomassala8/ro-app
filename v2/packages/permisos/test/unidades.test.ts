import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { cargarModulos, enmascarar, enlaceSeguro, importesAQuitar, nivelModulo, sinImportes } from '../src/index.js';
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
