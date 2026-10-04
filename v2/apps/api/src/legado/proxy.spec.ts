import { createServer } from 'node:http';
import type { AddressInfo } from 'node:net';
import express from 'express';
import request from 'supertest';
import { proxyLegado } from './proxy.js';
import { atiendeNest } from './rutas-en-nest.js';

// Un «servir.py» de mentira que devuelve lo que recibe: así se ve que el proxy no cambia nada.
function legadoFalso() {
  const srv = createServer((req, res) => {
    let cuerpo = '';
    req.on('data', (t) => (cuerpo += t));
    req.on('end', () => {
      res.writeHead(req.url?.startsWith('/api/prohibido') ? 403 : 200, { 'Content-Type': 'application/json', ETag: '"x1"' });
      res.end(JSON.stringify({ metodo: req.method, url: req.url, host: req.headers.host, yo: req.headers['x-ro-yo'] ?? null, cuerpo }));
    });
  });
  return new Promise<{ url: string; cerrar: () => void }>((ok) =>
    srv.listen(0, '127.0.0.1', () => ok({ url: `http://127.0.0.1:${(srv.address() as AddressInfo).port}`, cerrar: () => srv.close() })),
  );
}

describe('proxy de legado', () => {
  it('lo que Nest atiende no pasa al legado', () => {
    expect(atiendeNest('GET', '/vivo')).toBe(true);
    expect(atiendeNest('GET', '/api/sesion')).toBe(false);
  });

  it('pasa método, ruta, consulta, cabeceras, cuerpo, código y cabeceras de vuelta sin tocarlos', async () => {
    const legado = await legadoFalso();
    const app = express();
    app.use(proxyLegado(legado.url));
    const r = await request(app)
      .post('/api/rastro?x=1')
      .set('Host', '127.0.0.1:3000')
      .set('X-RO-Yo', 'mili')
      .set('Content-Type', 'application/json')
      .send('{"accion":"evento"}');
    expect(r.status).toBe(200);
    expect(r.headers.etag).toBe('"x1"');
    expect(r.body).toEqual({ metodo: 'POST', url: '/api/rastro?x=1', host: new URL(legado.url).host, yo: 'mili', cuerpo: '{"accion":"evento"}' });
    const p = await request(app).get('/api/prohibido').set('Host', 'localhost:3000');
    expect(p.status).toBe(403);
    legado.cerrar();
  });

  it('en local, rechaza un Host que no es 127.0.0.1 ni localhost (DNS rebinding), como servir.py', async () => {
    const app = express();
    app.use(proxyLegado('http://127.0.0.1:9'));
    const r = await request(app).get('/api/sesion').set('Host', 'malo.example:3000');
    expect(r.status).toBe(403);
    expect(r.body).toEqual({ error: 'Host no permitido.' });
  });

  it('si el legado no responde, 502 con un mensaje claro', async () => {
    const app = express();
    app.use(proxyLegado('http://127.0.0.1:9'));
    const r = await request(app).get('/api/sesion').set('Host', '127.0.0.1:3000');
    expect(r.status).toBe(502);
  });
});
