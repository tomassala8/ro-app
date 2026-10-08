import { errorDe, leerVec, pedir, personasPorPuesto, vectoresListos } from './_ayuda.js';

interface Persona {
  id: string;
  estado?: string;
  puestos?: string[];
}

const crudo = () => leerVec('crudo.json') as { personas: Persona[] };

async function legado(yo?: string, como?: string): Promise<{ status: number; json: unknown }> {
  const headers: Record<string, string> = { Accept: 'application/json', 'X-RO-App': '1' };
  if (yo) headers['X-RO-Yo'] = yo;
  if (como) headers['X-RO-Como'] = como;
  const r = await fetch(`http://127.0.0.1:8771/api/preferencias${como ? `?como=${como}` : ''}`, { headers });
  return { status: r.status, json: await r.json() };
}

describe.skipIf(!vectoresListos())('preferencias en Nest', () => {
  it('dirección, account, setter y «ver como» coinciden con el legado; sin identidad, 401', async () => {
    const mapa = personasPorPuesto(crudo());
    const dir = mapa.direccion;
    const acc = mapa.account;
    const set = mapa.setters;
    expect(dir && acc && set).toBeTruthy();

    const deDir = await pedir('GET', '/api/preferencias', { yo: dir });
    expect(deDir.status).toBe(200);
    expect(deDir.json).toEqual((await legado(dir)).json);
    expect((deDir.json as { tope?: number }).tope).toBe(30);

    expect((await pedir('GET', '/api/preferencias', { yo: acc })).json).toEqual((await legado(acc)).json);
    expect((await pedir('GET', '/api/preferencias', { yo: set })).json).toEqual((await legado(set)).json);
    expect((await pedir('GET', '/api/preferencias', { yo: dir, como: acc })).json).toEqual((await legado(dir, acc)).json);

    const anon = await pedir('GET', '/api/preferencias');
    expect(anon.status).toBe(401);
    expect(errorDe(anon.json)).toBe(
      'Sin identificar. En el prototipo, elige quién eres; en el servidor, entra por Cloudflare Access.',
    );
  });

  it('31 ids es 400, un cliente ajeno es 403 y «ver como» no escribe', async () => {
    const mapa = personasPorPuesto(crudo());
    const dir = mapa.direccion;
    const set = mapa.setters;
    const muchos = Array.from({ length: 31 }, (_, i) => `c${i}`);
    const malo = await pedir('POST', '/api/preferencias', { yo: dir, cuerpo: { fijados: muchos } });
    expect(malo.status).toBe(400);
    expect(errorDe(malo.json)).toBe('«fijados» es una lista de hasta 30 clientes.');

    const ajeno = await pedir('POST', '/api/preferencias', { yo: set, cuerpo: { fijados: ['cliente-que-no-abre'] } });
    expect(ajeno.status).toBe(403);
    expect(errorDe(ajeno.json)).toBe('Solo puedes fijar clientes que abres.');

    const como = await pedir('POST', '/api/preferencias', { yo: dir, como: set, cuerpo: { fijados: [] } });
    expect(como.status).toBe(403);
    expect(errorDe(como.json)).toBe('Estás en «ver como»: es solo lectura. No se escribe nada.');
  });
});
