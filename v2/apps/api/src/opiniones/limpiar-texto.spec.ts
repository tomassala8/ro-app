import { limpiarTexto } from './limpiar-texto.js';

const TAPADA = '\u2022\u2022\u2022\u2022 (tapada)';

describe('limpiarTexto', () => {
  it('tapa claves, correos y teléfonos como tapado.py', () => {
    expect(limpiarTexto('hola equipo')).toBe('hola equipo');
    expect(limpiarTexto('la contraseña es Secreta1')).toBe(`la contraseña es ${TAPADA}`);
    expect(limpiarTexto('la clave es que hay que esperar')).toBe('la clave es que hay que esperar');
    expect(limpiarTexto('password: hunter2')).toBe(`password: ${TAPADA}`);
    expect(limpiarTexto('Usuario: ana · Contraseña: Abcd1234!')).toBe(`Usuario: ${TAPADA} · Contraseña: ${TAPADA}`);
    expect(limpiarTexto('escribe a ana@ejemplo.test por favor')).toBe('escribe a [correo] por favor');
    expect(limpiarTexto('el teléfono es 612 345 678')).toBe('el teléfono es [teléfono]');
    expect(limpiarTexto('llama al +34 612345678')).toBe('llama al [teléfono]');
    expect(limpiarTexto('https://panel.test/a?token=abc123&x=1')).toBe('https://panel.test/a?token=\u2026&x=1');
    expect(limpiarTexto('password=secreto')).toBe(`password=${TAPADA}`);
    expect(limpiarTexto('')).toBe('');
    expect(limpiarTexto('ñandú')).toBe('ñandú');
    expect(limpiarTexto('la contraseña de su WordPress es Concilia2026!')).toBe(
      `la contraseña de su WordPress es ${TAPADA}`,
    );
    expect(limpiarTexto('  espacios   raros  ')).toBe('espacios   raros');
  });
});
