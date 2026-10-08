import { type Contexto, type Persona } from '@ro/permisos';
import { quitaIndicadores, recortaCatalogo } from './importes-indicadores.js';
import type { VistaConContexto } from './motor-ro.js';

function persona(id: string, puestos: string[]): Persona {
  return { id, nombre: id, estado: 'activo', activo: true, puestos };
}

const dir = persona('p_dir', ['direccion']);
const acc = persona('p_acc', ['account']);
const cp = {
  cartera_ids: new Set(['cli-prueba']),
  cartera_por_silla: {},
  personas: [dir, acc],
  clientes_por_id: {},
} as Contexto;

const vista = (p: Persona): VistaConContexto => ({ real: p, cp });

describe('importes de indicadores', () => {
  it('dirección ve el catálogo entero y no se le quitan cuota ni inversión', () => {
    expect(recortaCatalogo(vista(dir))).toBe(false);
    const quita = quitaIndicadores(vista(dir));
    expect(quita).not.toContain('cuota');
    expect(quita).not.toContain('inversion');
  });

  it('un account recibe solo los de su puesto y se le tapan importes', () => {
    expect(recortaCatalogo(vista(acc))).toBe(true);
    const quita = quitaIndicadores(vista(acc));
    expect(quita.length).toBeGreaterThan(0);
    expect(quita).not.toContain('cobros');
    expect(quita).not.toContain('dinero_empresa');
  });
});
