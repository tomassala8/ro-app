import { errorDe, leerVec, pedir, personasPorPuesto, vectoresListos } from './_ayuda.js';

interface Persona {
  id: string;
  estado?: string;
  puestos?: string[];
}

const crudo = () => leerVec('crudo.json') as { personas: Persona[] };

function quitarReloj(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(quitarReloj);
  if (v && typeof v === 'object') {
    const o: Record<string, unknown> = {};
    for (const [k, x] of Object.entries(v)) {
      if (k === 'hora' || k === 'generado') continue;
      o[k] = quitarReloj(x);
    }
    return o;
  }
  return v;
}

async function legado(ruta: string, yo?: string, como?: string): Promise<{ status: number; json: unknown }> {
  const headers: Record<string, string> = { Accept: 'application/json', 'X-RO-App': '1' };
  if (yo) headers['X-RO-Yo'] = yo;
  if (como) headers['X-RO-Como'] = como;
  const r = await fetch(`http://127.0.0.1:8771${ruta}${como ? `?como=${como}` : ''}`, { headers });
  return { status: r.status, json: await r.json() };
}

/** El primero de un puesto puede llevar también dirección (y entonces sí ve respuestas_mili). */
function una(puesto: string, sin: string[]): string | undefined {
  return crudo().personas.find((p) => {
    const pu = p.puestos ?? [];
    return p.estado === 'activo' && pu.includes(puesto) && sin.every((s) => !pu.includes(s));
  })?.id;
}

describe.skipIf(!vectoresListos())('decisiones y opiniones en Nest', () => {
  it('las lecturas coinciden con el legado y un account no ve respuestas_mili', async () => {
    const mapa = personasPorPuesto(crudo());
    const dir = mapa.direccion;
    const acc = una('account', ['direccion', 'operaciones']);
    const set = una('setters', ['direccion', 'operaciones']);
    expect(dir && acc && set).toBeTruthy();

    const mili = await pedir('GET', '/api/respuestas_mili', { yo: acc });
    expect(mili.status).toBe(403);
    expect(errorDe(mili.json)).toBe('Solo Mili y Tomás.');

    for (const yo of [dir, acc, set]) {
      for (const ruta of ['/api/decisiones', '/api/opiniones', '/api/respuestas_mili'] as const) {
        if (ruta === '/api/respuestas_mili' && yo !== dir) continue;
        const a = await pedir('GET', ruta, { yo });
        const b = await legado(ruta, yo);
        expect(a.status).toBe(b.status);
        expect(quitarReloj(a.json)).toEqual(quitarReloj(b.json));
      }
    }

    const deDir = await pedir('GET', '/api/decisiones', { yo: dir });
    const deAcc = await pedir('GET', '/api/decisiones', { yo: acc });
    const nDir = (deDir.json as { decisiones?: unknown[] }).decisiones?.length ?? 0;
    const nAcc = (deAcc.json as { decisiones?: unknown[] }).decisiones?.length ?? 0;
    expect(deDir.status).toBe(200);
    expect(nAcc).toBeLessThanOrEqual(nDir);

    const op = await pedir('GET', '/api/opiniones', { yo: acc });
    expect((op.json as { todas?: boolean }).todas).toBe(false);
  });

  it('los POST mal formados dan el texto de servir.py y «ver como» no escribe', async () => {
    const mapa = personasPorPuesto(crudo());
    const dir = mapa.direccion;
    const acc = una('account', ['direccion', 'operaciones']);
    expect(acc).toBeTruthy();
    const sin = await pedir('POST', '/api/decisiones', {
      yo: dir,
      cuerpo: { operacion: 'nueva', tipo: 'para_tomas', titulo: 't', problema: 'p' },
    });
    expect(sin.status).toBe(400);
    expect(errorDe(sin.json)).toBe('Falta tu recomendación (exigencia 48: sin recomendación no se sube).');

    const id = await pedir('POST', '/api/decisiones', { yo: dir, cuerpo: { operacion: 'responder', id: 'x' } });
    expect(id.status).toBe(400);
    expect(errorDe(id.json)).toBe('Solo se contestan aquí las decisiones de la tabla (id «db-…»).');

    const tipo = await pedir('POST', '/api/opinion', { yo: acc, cuerpo: { tipo: 'otro', texto: 'hola equipo' } });
    expect(tipo.status).toBe(400);
    expect(errorDe(tipo.json)).toBe('Falta qué ha pasado (o el tipo no es «fallo» o «idea»).');

    const como = await pedir('POST', '/api/decisiones', {
      yo: dir,
      como: acc,
      cuerpo: { operacion: 'nueva', titulo: 't', problema: 'p', recomendacion: 'r' },
    });
    expect(como.status).toBe(403);
    expect(errorDe(como.json)).toBe('Estás en «ver como»: es solo lectura. No se escribe nada.');

    const est = await pedir('POST', '/api/opiniones/estado', { yo: dir, cuerpo: { id: 1, estado: 'x' } });
    expect(est.status).toBe(400);
    expect(errorDe(est.json)).toBe('Estado no válido.');
  });
});
