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
  const r = await fetch(`http://127.0.0.1:8771/api/indicadores${como ? `?como=${como}` : ''}`, { headers });
  return { status: r.status, json: await r.json() };
}

describe.skipIf(!vectoresListos())('indicadores en Nest', () => {
  it('dirección, account, setter y «ver como» coinciden con el legado; sin identidad, 401', async () => {
    const mapa = personasPorPuesto(crudo());
    const dir = mapa.direccion;
    const acc = mapa.account;
    const set = mapa.setters;
    expect(dir && acc && set).toBeTruthy();

    const deDir = await pedir('GET', '/api/indicadores', { yo: dir });
    const vieja = await legado(dir);
    expect(deDir.status).toBe(200);
    expect(deDir.json).toEqual(vieja.json);
    expect((deDir.json as { _meta?: { recortado?: string } })._meta?.recortado).toBeUndefined();

    const deAcc = await pedir('GET', '/api/indicadores', { yo: acc });
    expect(deAcc.json).toEqual((await legado(acc)).json);

    const deSet = await pedir('GET', '/api/indicadores', { yo: set });
    const viejaSet = await legado(set);
    expect(deSet.json).toEqual(viejaSet.json);
    expect((deSet.json as { _meta?: { recortado?: string } })._meta?.recortado).toBe(
      (viejaSet.json as { _meta?: { recortado?: string } })._meta?.recortado,
    );

    const como = await pedir('GET', '/api/indicadores', { yo: dir, como: acc });
    expect(como.json).toEqual((await legado(dir, acc)).json);

    const anon = await pedir('GET', '/api/indicadores');
    expect(anon.status).toBe(401);
    expect(errorDe(anon.json)).toBe(
      'Sin identificar. En el prototipo, elige quién eres; en el servidor, entra por Cloudflare Access.',
    );
  });
});
