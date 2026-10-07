import type { NextFunction, Request, Response } from 'express';
import { PeticionMiddleware } from './peticion.middleware.js';

function llamada(parcial: Partial<Request> & { method: string; headers?: Record<string, string> }) {
  const res = {
    codigo: 0,
    cuerpo: undefined as unknown,
    cabeceras: {} as Record<string, string>,
    acabo: false,
    status(c: number) {
      this.codigo = c;
      return this;
    },
    setHeader(k: string, v: string) {
      this.cabeceras[k] = v;
      return this;
    },
    json(b: unknown) {
      this.cuerpo = b;
      this.acabo = true;
      return this;
    },
    end() {
      this.acabo = true;
      return this;
    },
  };
  let siguio = false;
  const next: NextFunction = () => {
    siguio = true;
  };
  new PeticionMiddleware().use(
    { headers: {}, ...parcial } as Request,
    res as unknown as Response,
    next,
  );
  return { res, siguio };
}

const local = { host: '127.0.0.1:4000' };

describe('PeticionMiddleware', () => {
  const antes = { PORT: process.env.PORT, ORIGEN: process.env.RO_ORIGEN_APP, ID: process.env.RO_IDENTIDAD };
  beforeAll(() => {
    process.env.PORT = '4000';
    process.env.RO_ORIGEN_APP = 'http://127.0.0.1:3000,http://localhost:3000';
    delete process.env.RO_IDENTIDAD;
  });
  afterAll(() => {
    process.env.PORT = antes.PORT;
    process.env.RO_ORIGEN_APP = antes.ORIGEN;
    if (antes.ID === undefined) delete process.env.RO_IDENTIDAD;
    else process.env.RO_IDENTIDAD = antes.ID;
  });

  it('rechaza un Host que no es local', () => {
    const { res, siguio } = llamada({ method: 'GET', headers: { host: 'evil.example' } });
    expect(siguio).toBe(false);
    expect(res.codigo).toBe(403);
    expect(res.cuerpo).toEqual({ error: 'Host no permitido.' });
  });

  it('HEAD y OPTIONS dan 405; solo OPTIONS lleva cuerpo', () => {
    const head = llamada({ method: 'HEAD', headers: local });
    expect(head.res.codigo).toBe(405);
    expect(head.res.cabeceras.Allow).toBe('GET, POST');
    expect(head.res.cuerpo).toBeUndefined();
    const opt = llamada({ method: 'OPTIONS', headers: local });
    expect(opt.res.codigo).toBe(405);
    expect(opt.res.cuerpo).toEqual({ error: 'Método no permitido.' });
  });

  it('un POST sin la cabecera de la app, sin JSON, con otro origen o desde otra web', () => {
    const base = { method: 'POST' as const, headers: { ...local } };
    expect(llamada(base).res.cuerpo).toEqual({ error: 'Falta la cabecera de la app (X-RO-App).' });
    expect(llamada({ ...base, headers: { ...local, 'x-ro-app': '1', 'content-type': 'text/plain' } }).res.cuerpo).toEqual({
      error: 'Solo se acepta JSON.',
    });
    expect(
      llamada({
        ...base,
        headers: { ...local, 'x-ro-app': '1', 'content-type': 'application/json', origin: 'https://otra.example' },
      }).res.cuerpo,
    ).toEqual({ error: 'Origen no permitido.' });
    expect(
      llamada({
        ...base,
        headers: {
          ...local,
          'x-ro-app': '1',
          'content-type': 'application/json',
          origin: 'http://127.0.0.1:3000',
          'sec-fetch-site': 'cross-site',
        },
      }).res.cuerpo,
    ).toEqual({ error: 'Petición desde otra web.' });
  });

  it('deja pasar un GET local y un POST propio', () => {
    expect(llamada({ method: 'GET', headers: local }).siguio).toBe(true);
    const post = llamada({
      method: 'POST',
      headers: {
        ...local,
        'x-ro-app': '1',
        'content-type': 'application/json; charset=utf-8',
        origin: 'http://127.0.0.1:3000',
        'sec-fetch-site': 'same-origin',
      },
    });
    expect(post.siguio).toBe(true);
    expect(post.res.acabo).toBe(false);
  });
});
