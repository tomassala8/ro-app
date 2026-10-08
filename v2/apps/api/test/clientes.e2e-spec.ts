import { errorDe, leerVec, pedir, personasPorPuesto, vectoresListos } from './_ayuda.js';

interface Persona {
  id: string;
  estado?: string;
  puestos?: string[];
}

interface ClienteSesion {
  id: string;
  logo?: string;
}

const crudo = () => leerVec('crudo.json') as { personas: Persona[] };
const puestos = () => personasPorPuesto(crudo());

async function legado(ruta: string, yo?: string): Promise<{ status: number; json: unknown; etag: string | null; cache: string | null }> {
  const headers: Record<string, string> = { Accept: 'application/json', 'X-RO-App': '1' };
  if (yo) headers['X-RO-Yo'] = yo;
  const r = await fetch(`http://127.0.0.1:8771${ruta}`, { headers });
  const texto = await r.text();
  let json: unknown = null;
  if (texto) {
    try {
      json = JSON.parse(texto);
    } catch {
      json = texto;
    }
  }
  return {
    status: r.status,
    json,
    etag: r.headers.get('etag'),
    cache: r.headers.get('cache-control'),
  };
}

describe.skipIf(!vectoresListos())('cliente y logos en Nest', () => {
  it('dirección tiene fuentes, el account ajeno y el setter reciben el 403 de la puerta', async () => {
    const mapa = puestos();
    const dir = mapa.direccion;
    const acc = mapa.account;
    const set = mapa.setters;
    expect(dir && acc && set).toBeTruthy();
    const sesionDir = await pedir('GET', '/api/sesion', { yo: dir });
    const sesionAcc = await pedir('GET', '/api/sesion', { yo: acc });
    const deDir = ((sesionDir.json as { datos?: { clientes?: ClienteSesion[] } }).datos?.clientes ?? []);
    const deAcc = new Set(((sesionAcc.json as { datos?: { clientes?: ClienteSesion[] } }).datos?.clientes ?? []).map((c) => c.id));
    const propio = deDir.find((c) => deAcc.has(c.id))?.id;
    const ajeno = deDir.find((c) => !deAcc.has(c.id))?.id;
    expect(propio).toBeTruthy();
    const ficha = await pedir('GET', `/api/cliente/${propio}`, { yo: dir });
    const vieja = await legado(`/api/cliente/${propio}`, dir);
    expect(ficha.status).toBe(200);
    expect(vieja.status).toBe(200);
    expect(ficha.json).toEqual(vieja.json);
    const fuentes = (ficha.json as { fuentes?: unknown }).fuentes;
    expect(fuentes && typeof fuentes === 'object').toBe(true);

    const delAccount = await pedir('GET', `/api/cliente/${propio}`, { yo: acc });
    const viejaAcc = await legado(`/api/cliente/${propio}`, acc);
    expect(delAccount.status).toBe(viejaAcc.status);
    expect(delAccount.json).toEqual(viejaAcc.json);

    if (ajeno) {
      const no = await pedir('GET', `/api/cliente/${ajeno}`, { yo: acc });
      expect(no.status).toBe(403);
      expect(errorDe(no.json)).toBe('El cliente o el ámbito actual de Ficha no está autorizado.');
    }

    const setter = await pedir('GET', `/api/cliente/${propio}`, { yo: set });
    expect(setter.status).toBe(403);
    expect(errorDe(setter.json)).toBe('El cliente o el ámbito actual de Ficha no está autorizado.');

    const fantasma = await pedir('GET', '/api/cliente/no-existe-esta-ficha', { yo: dir });
    const viejaFantasma = await legado('/api/cliente/no-existe-esta-ficha', dir);
    expect(fantasma.status).toBe(403);
    expect(fantasma.status).toBe(viejaFantasma.status);
    expect(errorDe(fantasma.json)).toBe(errorDe(viejaFantasma.json));
  });

  it('un logo sin identidad y un .txt dan lo mismo que el legado', async () => {
    const mapa = puestos();
    const sesion = await pedir('GET', '/api/sesion', { yo: mapa.direccion });
    const clientes = (sesion.json as { datos?: { clientes?: ClienteSesion[] } }).datos?.clientes ?? [];
    const conLogo = clientes.find((c) => typeof c.logo === 'string' && c.logo.startsWith('logos/'));
    expect(conLogo?.logo).toBeTruthy();
    const ruta = `/${String(conLogo?.logo).split('?')[0]}`;
    const nuevo = await fetch(`http://127.0.0.1:3000${ruta}`);
    const viejo = await fetch(`http://127.0.0.1:8770${ruta}`);
    expect(nuevo.status).toBe(viejo.status);
    expect(nuevo.headers.get('etag')).toBe(viejo.headers.get('etag'));
    expect(nuevo.headers.get('cache-control')).toBe(viejo.headers.get('cache-control'));
    const huella = (nuevo.headers.get('etag') ?? '').replaceAll('"', '');
    if (huella) {
      const conV = await fetch(`http://127.0.0.1:3000${ruta}?v=${huella}`);
      expect(conV.headers.get('cache-control')).toBe('private, max-age=31536000, immutable');
    }
    const txt = ruta.replace(/\.(jpg|png|webp|gif)$/, '.txt');
    const malo = await fetch(`http://127.0.0.1:3000${txt}`);
    expect(malo.status).toBe(403);
    expect(errorDe(await malo.json())).toBe('No se sirve como fichero. Los datos salen recortados de /api/.');
  });
});
