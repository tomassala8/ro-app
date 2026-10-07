import type { Crudo, Persona } from '@ro/permisos';
import { entradaDatosModulo, puertaModulo } from './puerta-modulo.js';

function persona(id: string, puestos: string[]): Persona {
  return { id, nombre: id, estado: 'activo', activo: true, puestos };
}

const dir = persona('p_dir', ['direccion']);
const acc = persona('p_acc', ['account']);
const crudo = { personas: [dir, acc], clientes: [], asignaciones: [] } as Crudo;

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
});
