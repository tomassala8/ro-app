import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  CLAVES_COBROS_SRC,
  CLAVES_CUOTA_SRC,
  CLAVES_DINERO_CAPTACION_SRC,
  CLAVES_INVERSION_SRC,
  CLAVES_LEAD_SRC,
  DINERO_EMPRESA_SRC,
} from '../src/importes.js';

const servir = readFileSync(fileURLToPath(new URL('../../../../servir.py', import.meta.url)), 'utf8');

function patron(nombre: string): string {
  const m = servir.match(new RegExp(`${nombre} = re\\.compile\\(r"([^"]*)"`));
  if (!m?.[1]) throw new Error(`no está ${nombre} en servir.py`);
  return m[1];
}

describe('claves de recortar_doc iguales a servir.py', () => {
  it('los patrones nombrados', () => {
    expect(CLAVES_CUOTA_SRC).toBe(patron('CLAVES_CUOTA'));
    expect(CLAVES_COBROS_SRC).toBe(patron('CLAVES_COBROS'));
    expect(CLAVES_INVERSION_SRC).toBe(patron('CLAVES_INVERSION'));
    expect(CLAVES_LEAD_SRC).toBe(patron('CLAVES_LEAD'));
    expect(CLAVES_DINERO_CAPTACION_SRC).toBe(patron('CLAVES_DINERO_CAPTACION'));
  });

  it('la expresión de dinero_empresa', () => {
    const m = servir.match(/if not v\("dinero_empresa"\):\s+q\.append\(re\.compile\(r"([^"]+)"/);
    expect(m?.[1]).toBe(DINERO_EMPRESA_SRC);
  });
});
