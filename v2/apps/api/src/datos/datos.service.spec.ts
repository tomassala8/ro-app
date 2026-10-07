import { HttpException } from '@nestjs/common';
import type { Crudo } from '@ro/permisos';
import type { CrudoService } from '../permisos/crudo.service.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import type { RastroService } from '../rastro/rastro.service.js';
import { DatosService } from './datos.service.js';

const VACIO = 'El fichero de datos está vacío y no hay un dato anterior en el servidor.';

function persona(id: string, puestos: string[]) {
  return { id, nombre: id, estado: 'activo' as const, activo: true, puestos };
}

const dir = persona('p_dir', ['direccion']);

let sellos = 0;

function servicio(opts: { archivos: Record<string, unknown>; romperAlEstado?: boolean }) {
  const crudo = { personas: [dir], clientes: [], asignaciones: [] } as Crudo;
  const marca = `sello-${sellos++}`;
  const falso = {
    actual: async () => crudo,
    sello: async () => marca,
    fichero: async (ruta: string) => {
      if (ruta === 'verdad/estado_clientes.json') {
        if (opts.romperAlEstado) crudo.personas = [];
        return opts.archivos[ruta] ?? { activos: [], bajas_ids: [] };
      }
      return Object.prototype.hasOwnProperty.call(opts.archivos, ruta) ? opts.archivos[ruta] : undefined;
    },
  };
  const rastro = { registrarAgrupado: async () => ({}) };
  const vista = { real: dir, como: dir } as VistaConContexto;
  return { svc: new DatosService(falso as unknown as CrudoService, rastro as unknown as RastroService), vista };
}

async function fallo(p: Promise<unknown>): Promise<HttpException> {
  try {
    await p;
  } catch (e) {
    if (e instanceof HttpException) return e;
    throw e;
  }
  throw new Error('la llamada debía fallar');
}

describe('lectura de un módulo', () => {
  it('un rel con punto no es una ruta', async () => {
    const { svc, vista } = servicio({ archivos: {} });
    const e = await fallo(svc.leer(vista, 'a.b'));
    expect(e.getStatus()).toBe(404);
    expect(e.message).toBe('No existe esa ruta de la API.');
  });

  it('un fichero que no está responde 404', async () => {
    const { svc, vista } = servicio({ archivos: {} });
    const e = await fallo(svc.leer(vista, 'decisiones/reloj'));
    expect(e.getStatus()).toBe(404);
    expect(e.message).toBe('No existe data/decisiones/reloj.json');
  });

  it('un fichero vacío trae el último dato bueno', async () => {
    const { svc, vista } = servicio({ archivos: { 'decisiones/reloj.json': {} } });
    const r = await svc.leer(vista, 'decisiones/reloj');
    expect(r.codigo).toBe(200);
    expect(r.cuerpo).toMatchObject({ _ultimo_dato_bueno: { dato_de: null, motivo: VACIO } });
  });

  it('si el ámbito cambia en la segunda puerta, 403', async () => {
    const { svc, vista } = servicio({ archivos: { 'decisiones/reloj.json': { generado: 'x' } }, romperAlEstado: true });
    const e = await fallo(svc.leer(vista, 'decisiones/reloj'));
    expect(e.getStatus()).toBe(403);
    expect(e.message).toBe('El ámbito cambió durante la lectura.');
  });

  it('quitarBajas saca la fila de baja de verdad/clientes', async () => {
    const { svc, vista } = servicio({
      archivos: {
        'verdad/clientes.json': { generado: 'x', comun: [{ id: 'cli_ok' }, { id: 'cli_baja' }] },
        'verdad/estado_clientes.json': {
          activos: [{ id: 'cli_ok', tipo: 'activo', nombre: 'Ok' }],
          bajas_ids: ['cli_baja'],
        },
      },
    });
    const r = await svc.leer(vista, 'verdad/clientes');
    expect(r.codigo).toBe(200);
    const comun = (r.cuerpo as { comun: { id: string }[] }).comun;
    expect(comun.map((f) => f.id)).toEqual(['cli_ok']);
  });
});
