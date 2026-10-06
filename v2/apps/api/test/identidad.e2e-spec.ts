import { createServer, type Server } from 'node:http';
import type { AddressInfo } from 'node:net';
import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { AppModule } from '../src/app.module.js';

// servir.py › end_headers
const CABECERAS = {
  'content-security-policy':
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: https:; " +
    "connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  'x-frame-options': 'DENY',
  'x-content-type-options': 'nosniff',
  'referrer-policy': 'no-referrer',
  'permissions-policy': 'camera=(), microphone=(), geolocation=()',
};

function conCabeceras(headers: Record<string, unknown>) {
  for (const [k, v] of Object.entries(CABECERAS)) expect(headers[k], k).toBe(v);
}

// AppModule entero en el proceso, sobre la base que diga DATABASE_URL (solo lee: aquí nadie entra en «ver como»).
describe.skipIf(!process.env.DATABASE_URL)('identidad antes que permisos (AppModule)', () => {
  let app: INestApplication;
  // Un «servir.py» de mentira para la puerta de secretos: 404 (abierta) o 503 (cerrada), según `puertaCerrada`.
  let legado: Server;
  let puertaCerrada = false;
  const legadoAntes = process.env.RO_LEGADO_URL;
  beforeAll(async () => {
    legado = createServer((_req, res) => {
      res.writeHead(puertaCerrada ? 503 : 404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: puertaCerrada ? 'cerrada' : 'No existe esa ruta de la API.' }));
    });
    await new Promise<void>((ok) => legado.listen(0, '127.0.0.1', () => ok()));
    process.env.RO_LEGADO_URL = `http://127.0.0.1:${(legado.address() as AddressInfo).port}`;
    const mod = await Test.createTestingModule({ imports: [AppModule] }).compile();
    app = mod.createNestApplication();
    app.setGlobalPrefix('api', { exclude: ['vivo'] });
    await app.init();
  });
  afterAll(async () => {
    await app?.close();
    await new Promise<void>((ok) => legado.close(() => ok()));
    if (legadoAntes === undefined) delete process.env.RO_LEGADO_URL;
    else process.env.RO_LEGADO_URL = legadoAntes;
  });

  it('la guarda de identidad corre antes que la de permisos: con identidad, la sesión entra', async () => {
    const r = await request(app.getHttpServer()).get('/api/sesion').set('X-RO-Yo', 'tomas');
    expect(r.status).toBe(200);
    expect(r.body.real.id).toBe('tomas');
    expect(r.headers.etag).toBeUndefined();
  });

  it('sin identidad, 401 con el texto de servir.py', async () => {
    const r = await request(app.getHttpServer()).get('/api/sesion').expect(401);
    expect(r.body).toEqual({ error: 'Sin identificar. En el prototipo, elige quién eres; en el servidor, entra por Cloudflare Access.' });
  });

  it('un Host ajeno da 403 «Host no permitido.» aunque la identidad sea buena', async () => {
    const r = await request(app.getHttpServer()).get('/api/sesion').set('Host', 'evil.test').set('X-RO-Yo', 'tomas').expect(403);
    expect(r.body).toEqual({ error: 'Host no permitido.' });
  });

  it('/vivo sigue sin pedir identidad', async () => {
    await request(app.getHttpServer()).get('/vivo').expect(200).expect({ ok: true });
  });

  it('las cabeceras de seguridad de servir.py salen en el 200, en el 401 de la guarda y en /vivo', async () => {
    conCabeceras((await request(app.getHttpServer()).get('/api/sesion').set('X-RO-Yo', 'tomas').expect(200)).headers);
    conCabeceras((await request(app.getHttpServer()).get('/api/sesion').expect(401)).headers);
    conCabeceras((await request(app.getHttpServer()).get('/vivo').expect(200)).headers);
  });

  it('con la puerta de secretos cerrada en servir.py, 503 con su texto; /vivo sigue respondiendo', async () => {
    puertaCerrada = true;
    try {
      const r = await request(app.getHttpServer()).get('/api/sesion').set('X-RO-Yo', 'tomas').expect(503);
      expect(r.body).toEqual({ error: 'cerrada' });
      conCabeceras(r.headers);
      await request(app.getHttpServer()).get('/vivo').expect(200);
    } finally {
      puertaCerrada = false;
    }
  });
});
