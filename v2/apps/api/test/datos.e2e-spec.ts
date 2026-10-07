import { BASE, errorDe, leerVec, pedir, personasPorPuesto, vectoresListos } from './_ayuda.js';

interface Persona {
  id: string;
  estado?: string;
  puestos?: string[];
}

const crudo = () => leerVec('crudo.json') as { personas: Persona[] };
const puestos = () => personasPorPuesto(crudo());

function iguales(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) <= 1e-9;
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((x, i) => iguales(x, b[i]));
  if (a && b && typeof a === 'object' && typeof b === 'object') {
    const ka = Object.keys(a as object);
    const kb = Object.keys(b as object);
    if (ka.length !== kb.length) return false;
    return ka.every((k) => iguales((a as Record<string, unknown>)[k], (b as Record<string, unknown>)[k]));
  }
  return false;
}

async function legado(ruta: string, yo: string): Promise<unknown> {
  const r = await fetch(`http://127.0.0.1:8771${ruta}`, {
    headers: { Accept: 'application/json', 'X-RO-Yo': yo, 'X-RO-App': '1' },
  });
  return r.json();
}

describe.skipIf(!vectoresListos())('modulo en Nest', () => {
  const rel = '/api/modulo/decisiones/reloj';

  it('tres puestos ven el mismo fichero que el legado', async () => {
    const mapa = puestos();
    const ids = [mapa.direccion, mapa.account, mapa.setters].filter(Boolean);
    expect(ids.length).toBe(3);
    for (const yo of ids) {
      const nuevo = await pedir('GET', rel, { yo });
      expect(nuevo.status).toBe(200);
      const viejo = await legado(rel, yo);
      expect(iguales(nuevo.json, viejo)).toBe(true);
    }
  });

  it('el setter no abre finanzas y el texto es el de la puerta', async () => {
    const yo = puestos().setters;
    expect(yo).toBeTruthy();
    const r = await pedir('GET', '/api/modulo/finanzas/impagos', { yo });
    expect(r.status).toBe(403);
    expect(errorDe(r.json)).toBe('Estos datos son de una pantalla que no es de tu puesto.');
  });

  it('un fichero privado no se sirve', async () => {
    const r = await pedir('GET', '/api/modulo/alertas/_privado/x', { yo: 'tomas' });
    expect(r.status).toBe(403);
    expect(errorDe(r.json)).toBe('Ese fichero no se sirve por aquí.');
  });

  it('una ruta que no es un fichero responde 404', async () => {
    const r = await pedir('GET', '/api/modulo/a.b', { yo: 'tomas' });
    expect(r.status).toBe(404);
    expect(errorDe(r.json)).toBe('No existe esa ruta de la API.');
  });

  it('If-None-Match con el ETag devuelto responde 304', async () => {
    const primero = await fetch(`${BASE}${rel}`, { headers: { Accept: 'application/json', 'X-RO-Yo': 'tomas', 'X-RO-App': '1' } });
    expect(primero.status).toBe(200);
    const etag = primero.headers.get('etag');
    expect(etag).toBeTruthy();
    await primero.arrayBuffer();
    const segundo = await fetch(`${BASE}${rel}`, {
      headers: { Accept: 'application/json', 'X-RO-Yo': 'tomas', 'X-RO-App': '1', 'If-None-Match': etag ?? '' },
    });
    expect(segundo.status).toBe(304);
    expect(await segundo.text()).toBe('');
  });
});
