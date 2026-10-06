import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { AppModule } from '../src/app.module.js';

// AppModule entero en el proceso, sobre la base que diga DATABASE_URL (solo lee: aquí nadie entra en «ver como»).
describe.skipIf(!process.env.DATABASE_URL)('identidad antes que permisos (AppModule)', () => {
  let app: INestApplication;
  beforeAll(async () => {
    const mod = await Test.createTestingModule({ imports: [AppModule] }).compile();
    app = mod.createNestApplication();
    app.setGlobalPrefix('api', { exclude: ['vivo'] });
    await app.init();
  });
  afterAll(() => app?.close());

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
});
