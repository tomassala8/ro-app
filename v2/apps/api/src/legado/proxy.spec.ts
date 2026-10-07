import { createServer, request as pedir } from 'node:http';
import type { AddressInfo } from 'node:net';
import express from 'express';
import request from 'supertest';
import { hostLocal, proxyLegado, sinIdentidadLocal } from './proxy.js';
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
  it('en la nube (access) quita X-RO-Yo, ?yo=, la galleta ro_yo y el correo de Access; lo demás queda igual', () => {
    const r = sinIdentidadLocal('/api/clientes?yo=tomas&x=1', {
      'x-ro-yo': 'tomas',
      'cf-access-authenticated-user-email': 'falso@example.com',
      cookie: 'a=1; ro_yo=tomas; b=2',
      'cf-access-jwt-assertion': 'j',
    });
    expect(r.path).toBe('/api/clientes?x=1');
    expect(r.headers['x-ro-yo']).toBeUndefined();
    expect(r.headers['cf-access-authenticated-user-email']).toBeUndefined();
    expect(r.headers.cookie).toBe('a=1; b=2');
    expect(r.headers['cf-access-jwt-assertion']).toBe('j');
    expect(sinIdentidadLocal('/x', { cookie: 'ro_yo=tomas' }).headers.cookie).toBeUndefined();
  });

  it('lo que Nest atiende no pasa al legado', () => {
    expect(atiendeNest('GET', '/vivo')).toBe(true);
    expect(atiendeNest('GET', '/api/sesion')).toBe(false);
    expect(atiendeNest('GET', '/api/clientes')).toBe(false);
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
    const r = await request(app).get('/api/clientes').set('Host', 'malo.example:3000');
    expect(r.status).toBe(403);
    expect(r.body).toEqual({ error: 'Host no permitido.' });
  });

  it('detrás del rewrite de Next (Host 127.0.0.1:4000), mira también X-Forwarded-Host', async () => {
    const app = express();
    app.use(proxyLegado('http://127.0.0.1:9'));
    const r = await request(app).get('/api/clientes').set('Host', '127.0.0.1:4000').set('X-Forwarded-Host', 'malo.example:3000');
    expect(r.status).toBe(403);
    expect(hostLocal({ host: '127.0.0.1:4000', 'x-forwarded-host': 'localhost:3000' })).toBe(true);
    expect(hostLocal({ host: '127.0.0.1:4000', 'x-forwarded-host': 'localhost:3000, malo.example' })).toBe(false);
  });

  it('si el cliente se va antes de tiempo, se corta también la petición al legado', async () => {
    let cerrada!: () => void;
    const corte = new Promise<void>((ok) => (cerrada = ok));
    const lento = createServer((req) => req.socket.on('close', () => cerrada()));
    await new Promise<void>((ok) => lento.listen(0, '127.0.0.1', () => ok()));
    const app = express();
    app.use(proxyLegado(`http://127.0.0.1:${(lento.address() as AddressInfo).port}`));
    const srv = app.listen(0, '127.0.0.1');
    await new Promise<void>((ok) => srv.once('listening', () => ok()));
    const cliente = pedir({ port: (srv.address() as AddressInfo).port, host: '127.0.0.1', path: '/api/clientes' });
    cliente.on('error', () => undefined);
    cliente.end();
    setTimeout(() => cliente.destroy(), 100);
    await corte;   // sin el corte, servir.py seguiría con la conexión abierta hasta los 60 s
    srv.close();
    lento.close();
  });

  it('si el legado no responde, 502 con un mensaje claro', async () => {
    const app = express();
    app.use(proxyLegado('http://127.0.0.1:9'));
    const r = await request(app).get('/api/clientes').set('Host', '127.0.0.1:3000');
    expect(r.status).toBe(502);
  });

  it('cuerpo por encima del tope (como servir.py) → 413, sin molestar al legado', async () => {
    const legado = await legadoFalso();
    const app = express();
    app.use(proxyLegado(legado.url, { cuerpoMax: 10 }));
    const r = await request(app).post('/api/rastro').set('Host', '127.0.0.1:3000').set('Content-Type', 'application/json').send('{"mucho":"texto de más"}');
    expect(r.status).toBe(413);
    expect(r.body).toEqual({ error: 'Petición demasiado grande.' });
    legado.cerrar();
  });

  it('si el legado tarda demasiado, 504 con mensaje en vez de dejar la pestaña cargando', async () => {
    const lento = createServer(() => {});
    await new Promise<void>((ok) => lento.listen(0, '127.0.0.1', () => ok()));
    const app = express();
    app.use(proxyLegado(`http://127.0.0.1:${(lento.address() as AddressInfo).port}`, { esperaMs: 200 }));
    const r = await request(app).get('/api/clientes').set('Host', '127.0.0.1:3000');
    expect(r.status).toBe(504);
    lento.closeAllConnections();
    lento.close();
  });

  it('HEAD y OPTIONS no llegan al legado (se saltarían identidad y permisos): 405', async () => {
    const legado = await legadoFalso();
    const app = express();
    app.use(proxyLegado(legado.url));
    expect((await request(app).head('/data/_privado/x.json').set('Host', '127.0.0.1:3000')).status).toBe(405);
    expect((await request(app).options('/api/clientes').set('Host', '127.0.0.1:3000')).status).toBe(405);
    legado.cerrar();
  });
});
