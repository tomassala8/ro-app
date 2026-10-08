import { errorDe, pedir, personasPorPuesto, vectoresListos, leerVec } from './_ayuda.js';

interface Persona {
  id: string;
  estado?: string;
  puestos?: string[];
}

const crudo = () => leerVec('crudo.json') as { personas: Persona[] };

function una(puesto: string, sin: string[]): string | undefined {
  return crudo().personas.find((p) => {
    const pu = p.puestos ?? [];
    return p.estado === 'activo' && pu.includes(puesto) && sin.every((s) => !pu.includes(s));
  })?.id;
}

describe.skipIf(!vectoresListos())('acciones y avisos en Nest', () => {
  it('GET /api/acciones sin módulo, el setter no abre ajustes y «ver como» sale vacío', async () => {
    const mapa = personasPorPuesto(crudo());
    const dir = mapa.direccion;
    const acc = una('account', ['direccion', 'operaciones']);
    const set = una('setters', ['direccion', 'operaciones']);
    expect(dir && acc && set).toBeTruthy();

    for (const yo of [dir, acc, set]) {
      const r = await pedir('GET', '/api/acciones', { yo });
      expect(r.status).toBe(200);
      expect((r.json as { modulo?: unknown }).modulo).toBeNull();
      expect(Array.isArray((r.json as { acciones?: unknown }).acciones)).toBe(true);
    }

    const ajeno = await pedir('GET', '/api/acciones?modulo=ajustes', { yo: set });
    expect(ajeno.status).toBe(403);
    expect(errorDe(ajeno.json)).toBe('Esa pantalla no es de tu puesto.');

    const como = await pedir('GET', '/api/acciones', { yo: dir, como: acc });
    expect(como.status).toBe(200);
    expect(como.json).toEqual({ modulo: null, acciones: [] });
  });

  it('un account no ve avisos, «ver como» no marca visto y el POST de acciones sigue en el legado', async () => {
    const mapa = personasPorPuesto(crudo());
    const dir = mapa.direccion;
    const acc = una('account', ['direccion', 'operaciones']);
    expect(dir && acc).toBeTruthy();

    const avisos = await pedir('GET', '/api/avisos', { yo: acc });
    expect(avisos.status).toBe(403);
    expect(errorDe(avisos.json)).toBe('«Actualizar ahora» y los avisos de fuentes son de Mili y Tomás.');

    const visto = await pedir('POST', '/api/avisos/visto', { yo: dir, como: acc, cuerpo: { id: 1 } });
    expect(visto.status).toBe(403);
    expect(errorDe(visto.json)).toBe('Estás en «ver como»: es solo lectura. No se escribe nada.');

    const accion = await pedir('POST', '/api/acciones', { yo: dir, cuerpo: {} });
    expect(accion.status).toBe(400);
    expect(errorDe(accion.json)).toBe('Falta el módulo de la acción (o no existe).');
  });
});
