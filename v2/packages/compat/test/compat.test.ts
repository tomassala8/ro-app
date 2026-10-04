// Cada función contra Python de verdad (python3 del Mac): mismos casos, misma salida.
import { spawnSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';
import {
  compararComoPython, cortar, divEntera, flotante, horaMadrid, huellaRastro, jsonComoPython, longitud, modulo,
  formatoFijo, ordenarComoPython, redondear, reprFloat,
} from '../src/index.js';

const hayPython = spawnSync('python3', ['-c', 'print(1)']).status === 0;
function python(codigo: string, entrada: unknown): any {
  const r = spawnSync('python3', ['-c', `import json,sys\nE=json.load(sys.stdin)\n${codigo}`], { input: JSON.stringify(entrada), encoding: 'utf8' });
  if (r.status !== 0) throw new Error(r.stderr);
  return JSON.parse(r.stdout);
}

const FLOATS = [0.1, 0.5, 1.5, 2.5, -2.5, 2.675, 0.125, 0.375, 1e-5, 1.5e-7, 123456.789, 1e16, 1.5e16, 1e15, 3.14159, -0.0001234,
  31.47, 99.995, 1234.5, 0.045, 1.005, 7.0000001, 2 ** 53, 5e-324, 1.7976931348623157e308];
const TEXTOS = ['hola', 'Ñandú «coma» ação', 'línea\nnueva\t"comillas"\\', 'emoji 👍🏽 y más', '\u0001ctrl', 'zeta', 'Zeta', 'árbol', '𝔘nicode', ''];

describe.skipIf(!hayPython)('igual que Python', () => {
  it('repr de float', () => {
    expect(FLOATS.map(reprFloat)).toEqual(python('print(json.dumps([repr(float(x)) for x in E]))', FLOATS));
  });

  it('round(x, n) con n de 0 a 4', () => {
    for (const n of [0, 1, 2, 3, 4]) {
      const casos = FLOATS.filter((x) => Math.abs(x) < 1e15);
      expect(casos.map((x) => redondear(x, n))).toEqual(python(`print(json.dumps([float(round(x, ${n})) for x in E]))`, casos));
    }
  });

  it('f"{x:.nf}" y f"{x:,.nf}"', () => {
    const casos = [...FLOATS.filter((x) => Math.abs(x) < 1e15), 0.25, 1234567.5, -1234.565, 0];
    for (const n of [0, 1, 2]) {
      expect(casos.map((x) => formatoFijo(x, n))).toEqual(python(`print(json.dumps([f"{x:.${n}f}" for x in E]))`, casos));
      expect(casos.map((x) => formatoFijo(x, n, true))).toEqual(python(`print(json.dumps([f"{x:,.${n}f}" for x in E]))`, casos));
    }
  });

  it('json.dumps con y sin ensure_ascii y sort_keys', () => {
    const v = { z: 1, a: [true, null, 'Ñ', flotante(12), 0.1, -3], 'ü': { b: TEXTOS }, A: 'x' };
    const py = { ...v, a: [true, null, 'Ñ', 12.0, 0.1, -3] };
    for (const [ea, sk] of [[true, false], [false, true], [true, true]] as const) {
      expect(jsonComoPython(v, { ensureAscii: ea, sortKeys: sk })).toBe(
        python(`E['a'][3] = float(E['a'][3])\nprint(json.dumps(json.dumps(E, ensure_ascii=${ea ? 'True' : 'False'}, sort_keys=${sk ? 'True' : 'False'})))`, py),
      );
    }
  });

  it('huella del rastro idéntica a servir.py › _huella', () => {
    const campos = [17, '2026-10-05 05:30:00', 'mili', null, 'decisiones', 'alta', 'd-3', '{"texto": "¿Sí? 👍"}', null, null, 'app'];
    const py = python(
      'import hashlib\nprint(json.dumps(hashlib.sha256((E[0] or "").encode() + json.dumps(E[1], ensure_ascii=False, sort_keys=True).encode()).hexdigest()))',
      ['abc123', campos],
    );
    expect(huellaRastro('abc123', campos)).toBe(py);
  });

  it('cortar y longitud por caracteres', () => {
    expect(TEXTOS.map((t) => [cortar(t, 7), longitud(t)])).toEqual(python('print(json.dumps([[t[:7], len(t)] for t in E]))', TEXTOS));
  });

  it('// y % con negativos', () => {
    const pares = [[7, 2], [-7, 2], [7, -2], [-7, -2], [0, 3]];
    expect(pares.map(([a, b]) => [divEntera(a, b), modulo(a, b)])).toEqual(python('print(json.dumps([[a // b, a % b] for a, b in E]))', pares));
  });

  it('sorted de textos y de tuplas', () => {
    expect([...TEXTOS].sort(compararComoPython)).toEqual(python('print(json.dumps(sorted(E)))', TEXTOS));
    const filas = [['b', 2], ['a', 3], ['b', 1], ['Á', 0]];
    expect(ordenarComoPython(filas, (f) => [f[0], f[1]])).toEqual(python('print(json.dumps(sorted(E)))', filas));
  });
});

describe('reloj', () => {
  it('RO_RELOJ fija la hora de Madrid', () => {
    expect(horaMadrid(new Date(), '2026-10-05T07:30')).toBe('2026-10-05T07:30:00');
  });
  it('sin RO_RELOJ, hora de Madrid (verano: UTC+2)', () => {
    expect(horaMadrid(new Date('2026-10-04T22:30:00Z'), '')).toBe('2026-10-05T00:30:00');
  });
});
