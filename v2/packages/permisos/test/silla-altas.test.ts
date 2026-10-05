import { describe, expect, it } from 'vitest';
import { cartera, carteraPorSilla } from '../src/index.js';
import type { Persona } from '../src/tipos.js';

// L-25 (Tomás, 4-oct): «altas» es una silla virtual. Igual que permisos.py › cartera_por_silla.
const clientes = [
  { id: 'c1', nombre: 'Uno', nuevo: true },
  { id: 'c2', nombre: 'Dos', nuevo: false },
  { id: 'c3', nombre: 'Tres', nuevo: true },
  { id: 'c4', nombre: 'Cuatro' },
];
const altas: Persona = { id: 'p_altas', nombre: 'A', puestos: ['tecnico_altas'] };

describe('silla virtual «altas»', () => {
  it('el técnico de altas lleva los clientes nuevos y ninguno más', () => {
    const por = carteraPorSilla(altas, [], '2026-10-05', clientes);
    expect([...(por['altas'] ?? [])].sort()).toEqual(['c1', 'c3']);
    expect([...cartera(altas, [], '2026-10-05', clientes)].sort()).toEqual(['c1', 'c3']);
  });

  it('sin catálogo de clientes no hay silla altas (como en Python)', () => {
    expect(carteraPorSilla(altas, [], '2026-10-05')['altas']).toBeUndefined();
  });

  it('sin clientes nuevos no se crea la silla', () => {
    const por = carteraPorSilla(altas, [], '2026-10-05', [{ id: 'c2', nuevo: false }]);
    expect(por['altas']).toBeUndefined();
  });

  it('otros puestos no la reciben', () => {
    const cuenta: Persona = { id: 'p_acc', nombre: 'B', puestos: ['account'] };
    expect(carteraPorSilla(cuenta, [], '2026-10-05', clientes)['altas']).toBeUndefined();
    const dir: Persona = { id: 'p_dir', nombre: 'D', puestos: ['direccion'] };
    expect(carteraPorSilla(dir, [], '2026-10-05', clientes)['altas']).toBeUndefined();
  });
});
