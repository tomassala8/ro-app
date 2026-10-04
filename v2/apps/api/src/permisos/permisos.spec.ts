import { Controller, Get, INestApplication, Post } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { Permiso, Publico } from './declarar.js';
import { MOTOR_PERMISOS, RASTRO_VER_COMO, type MotorPermisos, type RastroVerComo } from './motor.js';
import { PermisosModule } from './permisos.module.js';

@Controller()
class Prueba {
  @Get('sin-declarar') sinDeclarar() {
    return { secreto: 1 };
  }
  @Publico('prueba') @Get('publica') publica() {
    return { ok: true };
  }
  @Permiso({ modulo: 'crm' }) @Get('crm') crm() {
    return { visible: 1, importe: 99 };
  }
  @Permiso({ modulo: 'crm', sinRecorte: 'binario' }) @Get('crm/foto') foto() {
    return { visible: 1, importe: 99 };
  }
  @Permiso({ modulo: 'crm' }) @Post('crm') guardar() {
    return { ok: true };
  }
  @Permiso({ modulo: 'crm', lecturaPorPost: 'solo lee' }) @Post('crm/ver') verPorPost() {
    return { ok: true };
  }
}

const DIR = { id: 'a', puestos: ['direccion'] };
const SEO = { id: 'b', puestos: ['seo'] };
const motor: MotorPermisos = {
  entrar: (vista, d) => (vista?.real.puestos.includes('direccion') && d.modulo === 'crm' ? { ok: true } : { ok: false, status: 403, mensaje: 'Sin permiso.' }),
  recortar: (_v, _d, cuerpo) => ({ ...(cuerpo as object), importe: undefined }),
};

async function montar(vista?: object, rastro?: RastroVerComo | null) {
  let mod = Test.createTestingModule({ imports: [PermisosModule], controllers: [Prueba] }).overrideProvider(MOTOR_PERMISOS).useValue(motor);
  if (rastro !== null) mod = mod.overrideProvider(RASTRO_VER_COMO).useValue(rastro ?? { apuntar: () => undefined });
  const app = (await mod.compile()).createNestApplication();
  app.use((req: { vista?: object }, _res: unknown, next: () => void) => ((req.vista = vista), next()));
  await app.init();
  return app;
}

describe('permisos en un solo sitio', () => {
  let app: INestApplication;
  afterEach(() => app?.close());

  it('una ruta sin declarar se deniega', async () => {
    app = await montar({ real: DIR });
    await request(app.getHttpServer()).get('/sin-declarar').expect(403);
  });

  it('una ruta pública responde a cualquiera', async () => {
    app = await montar();
    await request(app.getHttpServer()).get('/publica').expect(200);
  });

  it('el motor decide quién entra', async () => {
    app = await montar({ real: SEO });
    await request(app.getHttpServer()).get('/crm').expect(403);
  });

  it('toda respuesta sale recortada por defecto; solo `sinRecorte` (con motivo) la deja entera', async () => {
    app = await montar({ real: DIR });
    await request(app.getHttpServer()).get('/crm').expect(200).expect({ visible: 1 });
    await request(app.getHttpServer()).get('/crm/foto').expect(200).expect({ visible: 1, importe: 99 });
  });

  it('«ver como» no puede escribir aunque la ruta no diga nada; solo `lecturaPorPost` pasa', async () => {
    app = await montar({ real: DIR, como: SEO });
    await request(app.getHttpServer()).post('/crm').expect(403);
    await request(app.getHttpServer()).post('/crm/ver').expect(201);
  });

  it('toda petición en «ver como» deja rastro, y sin rastro no hay «ver como»', async () => {
    const apuntadas: string[] = [];
    app = await montar({ real: DIR, como: SEO }, { apuntar: (_v, m, r) => void apuntadas.push(`${m} ${r}`) });
    await request(app.getHttpServer()).get('/crm').expect(200);
    expect(apuntadas).toEqual(['GET /crm']);
    await app.close();
    app = await montar({ real: DIR, como: SEO }, null);   // el de por defecto: aún sin portar
    await request(app.getHttpServer()).get('/crm').expect(503);
    await app.close();
    app = await montar({ real: DIR }, null);              // sin «ver como» no hace falta
    await request(app.getHttpServer()).get('/crm').expect(200);
  });

  it('sin motor portado, toda ruta con permiso se deniega', async () => {
    const mod = await Test.createTestingModule({ imports: [PermisosModule], controllers: [Prueba] }).compile();
    app = mod.createNestApplication();
    await app.init();
    await request(app.getHttpServer()).get('/crm').expect(403);
  });
});
