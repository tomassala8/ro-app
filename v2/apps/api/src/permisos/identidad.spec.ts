import { createSign, generateKeyPairSync } from 'node:crypto';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Controller, Get, INestApplication, Req } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { olvidarClaves } from './access-jwt.js';
import { CrudoService } from './crudo.service.js';
import { Permiso, Publico } from './declarar.js';
import { galletas, IdentidadGuard, rutaLecturaVerComo585 } from './identidad.guard.js';
import type { VistaConContexto } from './motor-ro.js';

// Personas inventadas: nada de datos reales.
const crudo = {
  personas: [
    { id: 'p_dir', alias: 'Dir', puestos: ['direccion'], estado: 'activo', correo: 'dir@ejemplo.test' },
    { id: 'p_acc', alias: 'Acc', puestos: ['account'], estado: 'activo', correo: 'acc@ejemplo.test' },
    { id: 'p_baja', alias: 'Baja', puestos: ['account'], estado: 'baja' },
    { id: 'p_doble', puestos: ['seo'], estado: 'activo' },
    { id: 'p_doble', puestos: ['seo'], estado: 'activo' },
  ],
  clientes: [],
  asignaciones: [],
  alarmas: [],
  logos: {},
  meta: {},
};
const crudoFalso = { actual: async () => crudo, correosEntrada: async () => ({ p_acc: 'entrada@ejemplo.test' }) };

@Controller()
class Prueba {
  @Permiso({ soloIdentidad: 'prueba', sinRecorte: 'prueba' }) @Get('api/quien') quien(@Req() req: { vista: VistaConContexto }) {
    return { real: req.vista.real.id, como: req.vista.como?.id ?? null };
  }
  @Publico('prueba') @Get('vivo') vivo() {
    return { ok: true };
  }
}

async function montar() {
  const mod = await Test.createTestingModule({
    controllers: [Prueba],
    providers: [{ provide: CrudoService, useValue: crudoFalso }, { provide: APP_GUARD, useClass: IdentidadGuard }],
  }).compile();
  const app = mod.createNestApplication();
  await app.init();
  return app;
}

describe('identidad (servir.py › host_ok y _quien)', () => {
  let app: INestApplication;
  const antes = { ...process.env };
  beforeEach(async () => {
    delete process.env.RO_IDENTIDAD;
    app = await montar();
  });
  afterEach(async () => {
    process.env = { ...antes };
    await app?.close();
  });

  it('/vivo no pide identidad', async () => {
    await request(app.getHttpServer()).get('/vivo').expect(200);
  });

  it('sin identidad, 401 con el texto de servir.py', async () => {
    const r = await request(app.getHttpServer()).get('/api/quien').expect(401);
    expect(r.body.message).toMatch(/^Sin identificar\./);
  });

  it('un Host ajeno da 403 antes de mirar quién es (DNS rebinding)', async () => {
    const r = await request(app.getHttpServer()).get('/api/quien').set('Host', 'evil.test').set('X-RO-Yo', 'p_dir').expect(403);
    expect(r.body.message).toBe('Host no permitido.');
  });

  it('la persona sale de X-RO-Yo, de ?yo= o de la galleta ro_yo', async () => {
    const s = app.getHttpServer();
    expect((await request(s).get('/api/quien').set('X-RO-Yo', 'p_acc')).body).toEqual({ real: 'p_acc', como: null });
    expect((await request(s).get('/api/quien?yo=p_acc')).body).toEqual({ real: 'p_acc', como: null });
    expect((await request(s).get('/api/quien').set('Cookie', 'ro_yo=p_acc')).body).toEqual({ real: 'p_acc', como: null });
  });

  it('una persona que no existe, de baja o repetida no entra', async () => {
    const s = app.getHttpServer();
    for (const yo of ['nadie', 'p_baja', 'p_doble']) {
      const r = await request(s).get('/api/quien').set('X-RO-Yo', yo).expect(403);
      expect(r.body.message).toBe('No existe esa persona.');
    }
  });

  it('«ver como» solo para dirección y a una persona activa e inequívoca', async () => {
    const s = app.getHttpServer();
    expect((await request(s).get('/api/quien').set('X-RO-Yo', 'p_dir').set('X-RO-Como', 'p_acc')).body).toEqual({ real: 'p_dir', como: 'p_acc' });
    const acc = await request(s).get('/api/quien').set('X-RO-Yo', 'p_acc').set('X-RO-Como', 'p_dir').expect(403);
    expect(acc.body.message).toBe('«Ver como» es solo para Mili y Tomás.');
    for (const como of ['p_baja', 'p_doble', 'nadie']) {
      const r = await request(s).get('/api/quien').set('X-RO-Yo', 'p_dir').set('X-RO-Como', como).expect(403);
      expect(r.body.message).toBe('La persona de esta vista no está activa o su identidad no es inequívoca.');
    }
    // Verse a sí mismo no es «ver como».
    expect((await request(s).get('/api/quien').set('X-RO-Yo', 'p_dir').set('X-RO-Como', 'p_dir')).body).toEqual({ real: 'p_dir', como: null });
  });

  it('la galleta ro_como solo cuenta si la identidad también vino por galleta', async () => {
    const s = app.getHttpServer();
    expect((await request(s).get('/api/quien').set('Cookie', 'ro_yo=p_dir; ro_como=p_acc')).body).toEqual({ real: 'p_dir', como: 'p_acc' });
    expect((await request(s).get('/api/quien').set('X-RO-Yo', 'p_dir').set('Cookie', 'ro_como=p_acc')).body).toEqual({ real: 'p_dir', como: null });
  });

  describe('RO_IDENTIDAD=access', () => {
    const { privateKey, publicKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
    const dir = mkdtempSync(join(tmpdir(), 'ro-access-'));
    const certs = join(dir, 'certs.json');
    writeFileSync(certs, JSON.stringify({ keys: [{ ...publicKey.export({ format: 'jwk' }), kid: 'k1' }] }));
    const sello = (carga: Record<string, unknown>, kid = 'k1') => {
      const b = (o: object) => Buffer.from(JSON.stringify(o)).toString('base64url');
      const cuerpo = `${b({ alg: 'RS256', kid })}.${b(carga)}`;
      return `${cuerpo}.${createSign('RSA-SHA256').update(cuerpo).sign(privateKey).toString('base64url')}`;
    };
    const ahora = () => Math.floor(Date.now() / 1000);
    const bueno = (email: string) => ({ aud: ['aud-prueba'], iss: 'https://equipo-prueba.cloudflareaccess.com', exp: ahora() + 600, email });

    beforeEach(() => {
      Object.assign(process.env, { RO_IDENTIDAD: 'access', RO_CF_AUD: 'aud-prueba', RO_CF_EQUIPO: 'equipo-prueba', RO_CF_CERTS_FICHERO: certs });
      olvidarClaves();
    });

    it('X-RO-Yo y ?yo= no valen: sin sello no entra nadie', async () => {
      const r = await request(app.getHttpServer()).get('/api/quien?yo=p_dir').set('X-RO-Yo', 'p_dir').expect(403);
      expect(r.body.message).toBe('Falta el sello de Cloudflare Access: entra por la dirección de la app.');
    });

    it('con un sello bueno, la persona sale del correo (primero la lista de entrada)', async () => {
      const s = app.getHttpServer();
      expect((await request(s).get('/api/quien').set('Cf-Access-Jwt-Assertion', sello(bueno('DIR@ejemplo.test')))).body).toEqual({ real: 'p_dir', como: null });
      expect((await request(s).get('/api/quien').set('Cookie', `CF_Authorization=${sello(bueno('entrada@ejemplo.test'))}`)).body).toEqual({ real: 'p_acc', como: null });
      const r = await request(s).get('/api/quien').set('Cf-Access-Jwt-Assertion', sello(bueno('otro@ejemplo.test'))).expect(403);
      expect(r.body.message).toBe('Tu correo no está en la tabla de personas. Pídeselo a Mili o a Tomás.');
    });

    it('un sello caducado, de otra aplicación, de otra clave o tocado no entra', async () => {
      const s = app.getHttpServer();
      const casos: [string, string][] = [
        [sello({ ...bueno('dir@ejemplo.test'), exp: ahora() - 3600 }), 'El sello de Access ha caducado: vuelve a entrar.'],
        [sello({ ...bueno('dir@ejemplo.test'), aud: ['otra'] }), 'El sello de Access es de otra aplicación.'],
        [sello({ ...bueno('dir@ejemplo.test'), iss: 'https://otro.cloudflareaccess.com' }), 'El sello de Access es de otro equipo de Cloudflare.'],
        [sello(bueno('dir@ejemplo.test'), 'k2'), 'Sello de Access firmado con una clave desconocida.'],
        [sello(bueno('dir@ejemplo.test')).replace(/\.[^.]+$/, '.AAAA'), 'La firma del sello de Access no es válida.'],
        ['basura', 'Sello de Access mal formado.'],
      ];
      for (const [t, texto] of casos) {
        const r = await request(s).get('/api/quien').set('Cf-Access-Jwt-Assertion', t).expect(403);
        expect(r.body.message).toBe(texto);
      }
    });
  });
});

describe('piezas de la identidad', () => {
  it('rutaLecturaVerComo585 agrupa por familia pública', () => {
    expect(rutaLecturaVerComo585('/api/sesion?x=1')).toBe('/api/sesion');
    expect(rutaLecturaVerComo585('/api/cliente/abc/def')).toBe('/api/cliente');
    expect(rutaLecturaVerComo585('/api/inventada')).toBe('/api/otra');
    expect(rutaLecturaVerComo585('/otra/cosa')).toBe('/api/otra');
  });

  it('galletas descodifica como app.js las escribe', () => {
    expect(galletas('ro_yo=p%C3%B1; otra=1')).toEqual({ ro_yo: 'pñ', otra: '1' });
    expect(galletas(undefined)).toEqual({});
  });
});
