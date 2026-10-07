import type { Contexto, Persona } from '@ro/permisos';
import { CLAVES_INVERSION, DINERO_INVERSION_VALOR } from '@ro/permisos';
import { filaVisible, recortarDoc, recortarVistas } from './rastro-lectura.service.js';

const cp = { cartera_ids: new Set<string>(), cartera_por_silla: {}, personas: [], clientes_por_id: {} } as Contexto;

function persona(id: string, puestos: string[]): Persona {
  return { id, nombre: id, puestos, estado: 'activo' };
}

describe('lectura del rastro', () => {
  const dir = persona('dir', ['direccion']);
  const acc = persona('acc', ['account']);
  const crudo = {
    personas: [dir, acc],
    clientes: [{ id: 'c1', estado: 'activo', activo: true }],
    asignaciones: [],
    alarmas: [],
    meta: {},
  };

  it('sin cliente, la fila propia se ve y la ajena solo si el módulo es de nivel todo', () => {
    const propia = { modulo: 'operaciones', cliente_id: null, quien: 'acc' };
    expect(filaVisible(propia, crudo, [acc], [cp], 'acc')).toBe(true);
    const ajena = { modulo: 'operaciones', cliente_id: null, quien: 'dir' };
    const veTodo = filaVisible(ajena, crudo, [dir], [cp], 'dir');
    const noTodo = filaVisible(ajena, crudo, [acc], [cp], 'acc');
    expect(veTodo).toBe(true);
    expect(noTodo).toBe(false);
  });

  it('un cliente que no está en el crudo no se ve', () => {
    const fila = { modulo: 'mi-dia', cliente_id: 'ajeno', quien: 'dir' };
    expect(filaVisible(fila, crudo, [dir], [cp], 'dir')).toBe(false);
  });

  it('recortarVistas quita coste_total de la vista previa a quien no ve inversión', () => {
    const filas = [
      {
        tipo: 'objetivo_alta',
        cliente_id: null,
        vista_previa: '{"nombre": "pieza", "coste_total": 12}',
      },
    ];
    const out = recortarVistas(filas, () => [CLAVES_INVERSION, DINERO_INVERSION_VALOR]);
    expect(out[0]?.vista_previa).toBe('{"nombre": "pieza"}');
    expect(recortarDoc({ coste_total: 12, nombre: 'pieza' }, [CLAVES_INVERSION])).toEqual({ nombre: 'pieza' });
  });
});
