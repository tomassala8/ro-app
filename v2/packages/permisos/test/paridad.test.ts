// Paridad con permisos.py: mismas respuestas para las mismas preguntas.
// Vectores: python3 migracion/vectores_permisos.py (en el Mac, con data/) → RO_VECTORES=~/RO_MIGRACION/vectores pnpm test
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { cargarReglas } from '../src/index.js';

const dir = process.env.RO_VECTORES?.replace(/^~/, process.env.HOME ?? '');
const hay = !!dir && existsSync(join(dir, 'permisos.json'));

describe('reglas', () => {
  it('reglas_permisos.json se lee y tiene los puestos', () => {
    const r = cargarReglas();
    expect(r.puestos.length).toBeGreaterThan(0);
  });
});

describe.skipIf(!hay)('paridad con permisos.py', () => {
  it('hay vectores para cada persona activa', () => {
    const v = JSON.parse(readFileSync(join(dir!, 'permisos.json'), 'utf8'));
    expect(Object.keys(v.por_persona).length).toBeGreaterThan(0);
    // Fase 2: por cada persona y pregunta «tipo|cliente|persona», ver() del motor nuevo === v.por_persona[p].ver[clave]
    // (y lo mismo con ver_como, nivel_modulo, cartera_por_silla y recortar frente a recortes/<persona>.json).
  });
});
