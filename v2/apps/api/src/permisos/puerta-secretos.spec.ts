import { createServer, type IncomingHttpHeaders } from 'node:http';
import type { AddressInfo } from 'node:net';
import { PuertaSecretosService, RUTA_SONDEO, SIN_LEGADO } from './puerta-secretos.service.js';

// Un «servir.py» de mentira que contesta siempre lo mismo y apunta lo que recibe.
function legadoFalso(status: number, cuerpo: unknown) {
  const recibidas: { url?: string; headers: IncomingHttpHeaders }[] = [];
  const srv = createServer((req, res) => {
    recibidas.push({ url: req.url, headers: req.headers });
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(cuerpo));
  });
  return new Promise<{ url: string; recibidas: typeof recibidas; cerrar: () => Promise<void> }>((ok) =>
    srv.listen(0, '127.0.0.1', () =>
      ok({
        url: `http://127.0.0.1:${(srv.address() as AddressInfo).port}`,
        recibidas,
        cerrar: () => new Promise<void>((fin) => srv.close(() => fin())),
      }),
    ),
  );
}

describe('puerta de secretos (pregunta a servir.py)', () => {
  const antes = process.env.RO_LEGADO_URL;
  afterEach(() => {
    if (antes === undefined) delete process.env.RO_LEGADO_URL;
    else process.env.RO_LEGADO_URL = antes;
  });

  it('404 del legado: la petición pasó la puerta, abierta; con X-RO-Yo y sin X-RO-Como', async () => {
    const f = await legadoFalso(404, { error: 'No existe esa ruta de la API.' });
    process.env.RO_LEGADO_URL = f.url;
    expect(await new PuertaSecretosService().estado({ 'x-ro-yo': 'p1' })).toEqual({ abierta: true });
    expect(f.recibidas).toHaveLength(1);
    expect(f.recibidas[0]!.url).toBe(RUTA_SONDEO);
    expect(f.recibidas[0]!.headers['x-ro-yo']).toBe('p1');
    expect(f.recibidas[0]!.headers['x-ro-como']).toBeUndefined();
    await f.cerrar();
  });

  it('503 del legado: cerrada, con el texto del legado tal cual', async () => {
    const f = await legadoFalso(503, { error: 'X' });
    process.env.RO_LEGADO_URL = f.url;
    expect(await new PuertaSecretosService().estado({ 'x-ro-yo': 'p1' })).toEqual({ abierta: false, status: 503, error: 'X' });
    await f.cerrar();
  });

  it('otro código (200, 401, 500): no se sabe, cerrada con 502', async () => {
    for (const status of [200, 401, 500]) {
      const f = await legadoFalso(status, { error: 'otra cosa' });
      process.env.RO_LEGADO_URL = f.url;
      expect(await new PuertaSecretosService().estado({ 'x-ro-yo': 'p1' })).toEqual({ abierta: false, status: 502, error: SIN_LEGADO });
      await f.cerrar();
    }
  });

  it('legado caído: cerrada con 502 y el texto del proxy', async () => {
    const f = await legadoFalso(404, {});
    await f.cerrar();
    process.env.RO_LEGADO_URL = f.url;
    expect(await new PuertaSecretosService().estado({ 'x-ro-yo': 'p1' })).toEqual({ abierta: false, status: 502, error: SIN_LEGADO });
  });

  it('sin RO_LEGADO_URL: cerrada con 502', async () => {
    delete process.env.RO_LEGADO_URL;
    expect(await new PuertaSecretosService().estado({ 'x-ro-yo': 'p1' })).toEqual({ abierta: false, status: 502, error: SIN_LEGADO });
  });
});
