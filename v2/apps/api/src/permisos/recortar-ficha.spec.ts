import { ver, type Contexto, type Crudo, type Persona } from '@ro/permisos';
import { puertaCliente581 } from './puerta-cliente.js';
import { recortarFicha } from './recortar-ficha.js';

function persona(id: string, puestos: string[]): Persona {
  return { id, nombre: id, estado: 'activo', activo: true, puestos };
}

const dir = persona('p_dir', ['direccion']);
const acc = persona('p_acc', ['account']);
const set = persona('p_set', ['setters']);
const cid = 'cli-prueba';

const cp = {
  cartera_ids: new Set([cid]),
  cartera_por_silla: {},
  personas: [dir, acc, set],
  clientes_por_id: {},
} as Contexto;

const doc = {
  cuota: 100,
  coste_total: 50,
  tarifa_hora: 40,
  telefono: '600000000',
  url: 'https://ejemplo.test/ficha',
  fuentes: {
    libro: { meses: { ene: 1 }, nota: 'sin cifra' },
    cartera: { nombre: 'Cabecera' },
  },
};

describe('recortar ficha', () => {
  it('dirección conserva la cuota y la tarifa, y el teléfono no viaja (clave de lead)', () => {
    const out = recortarFicha(dir, cp, cid, doc) as Record<string, unknown>;
    expect(ver(dir, { tipo: 'cuota', cliente_id: cid }, cp).ok).toBe(true);
    expect(out.cuota).toBe(100);
    expect(out.tarifa_hora).toBe(40);
    expect(out.telefono).toBeUndefined();
    expect(out.url).toBe('https://ejemplo.test/ficha');
  });

  it('el account del cliente no recibe rentabilidad (tarifa_hora) si ver() se la niega', () => {
    const ve = ver(acc, { tipo: 'dinero_empresa', cliente_id: cid }, cp).ok;
    const out = recortarFicha(acc, cp, cid, doc) as Record<string, unknown>;
    expect(ve).toBe(false);
    expect(out.tarifa_hora).toBeUndefined();
    expect(out.telefono).toBeUndefined();
  });

  it('el setter no llega a recortar: la puerta ya es 403', () => {
    const crudo = {
      personas: [set],
      clientes: [{ id: cid, nombre: 'Cli', estado: 'activo', activo: true }],
      asignaciones: [],
      alarmas: [],
      logos: {},
      meta: {},
    } as Crudo;
    expect(puertaCliente581({ real: set }, crudo, cid, 'sello')).toBeNull();
  });
});
