import type { Crudo, Persona } from '@ro/permisos';
import { entradaDatosModulo, puertaModulo } from './puerta-modulo.js';

function persona(id: string, puestos: string[]): Persona {
  return { id, nombre: id, estado: 'activo', activo: true, puestos };
}

const dir = persona('p_dir', ['direccion']);
const acc = persona('p_acc', ['account']);
const ops = persona('p_ops', ['operaciones']);
const set = persona('p_set', ['setters']);
const crudo = { personas: [dir, acc, ops, set], clientes: [], asignaciones: [] } as Crudo;

describe('puerta del módulo', () => {
  it('el patrón casa un segmento y no dos', () => {
    expect(entradaDatosModulo('chat_equipo/p_x')).toBeTruthy();
    expect(entradaDatosModulo('chat_equipo/p_x/y')).toBeNull();
  });

  it('un fichero privado no se sirve', async () => {
    const r = await puertaModulo({ real: dir, como: dir }, 'alertas/_privado/x', crudo, { apuntar: false });
    expect(r.error).toEqual({ codigo: 403, texto: 'Ese fichero no se sirve por aquí.' });
  });

  it('en «ver como», un fichero solo_propio es siempre 403', async () => {
    const r = await puertaModulo({ real: dir, como: acc }, 'chat_equipo/p_acc', crudo, { apuntar: false });
    expect(r.error?.texto).toBe('Ese fichero es de otra persona.');
  });

  it('vacio_para_puestos devuelve nivel vacio si los puestos caben en la lista', async () => {
    const r = await puertaModulo({ real: set, como: set }, 'verdad/clientes', crudo, { apuntar: false });
    expect(r.error).toBeUndefined();
    expect(r.nivel).toBe('vacio');
  });

  it('en «ver como», un fichero por puestos exige la intersección', async () => {
    const sola = await puertaModulo({ real: dir, como: dir }, 'personas_m20/contratacion', crudo, { apuntar: false });
    expect(sola.nivel).toBe('todo');
    const ambas = await puertaModulo({ real: dir, como: ops }, 'personas_m20/contratacion', crudo, { apuntar: false });
    expect(ambas.nivel).toBe('todo');
    const corta = await puertaModulo({ real: dir, como: acc }, 'personas_m20/contratacion', crudo, { apuntar: false });
    expect(corta.error?.texto).toBe('Estos datos son de una pantalla que no es de tu puesto.');
  });
});
