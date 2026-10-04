import { Controller, Get, INestApplication, Post } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { Permiso, Publico } from './declarar.js';
import { MOTOR_PERMISOS, type MotorPermisos } from './motor.js';
import { PermisosModule } from './permisos.module.js';

@Controller()
class Prueba {
  @Get('sin-declarar') sinDeclarar() {
    return { secreto: 1 };
  }
  @Publico('prueba') @Get('publica') publica() {
    return { ok: true };
  }
  @Permiso({ modulo: 'crm', recortar: true }) @Get('crm') crm() {
    return { visible: 1, importe: 99 };
  }
  @Permiso({ modulo: 'crm', escritura: true }) @Post('crm') guardar() {
    return { ok: true };
  }
}

const motor: MotorPermisos = {
  entrar: (vista, d) => (vista?.real.puestos.includes('direccion') && d.modulo === 'crm' ? { ok: true } : { ok: false, status: 403, mensaje: 'Sin permiso.' }),
  recortar: (_v, _d, cuerpo) => ({ ...(cuerpo as object), importe: undefined }),
};

async function montar(vista?: object) {
  const mod = await Test.createTestingModule({ imports: [PermisosModule], controllers: [Prueba] })
    .overrideProvider(MOTOR_PERMISOS)
    .useValue(motor)
    .compile();
  const app = mod.createNestApplication();
  app.use((req: { vista?: object }, _res: unknown, next: () => void) => ((req.vista = vista), next()));
  await app.init();
  return app;
}

describe('permisos en un solo sitio', () => {
  let app: INestApplication;
  afterEach(() => app?.close());

  it('una ruta sin declarar se deniega', async () => {
    app = await montar({ real: { id: 'a', puestos: ['direccion'] } });
    await request(app.getHttpServer()).get('/sin-declarar').expect(403);
  });

  it('una ruta pública responde a cualquiera', async () => {
    app = await montar();
    await request(app.getHttpServer()).get('/publica').expect(200);
  });

  it('el motor decide quién entra y la respuesta sale recortada', async () => {
    app = await montar({ real: { id: 'a', puestos: ['direccion'] } });
    await request(app.getHttpServer()).get('/crm').expect(200).expect({ visible: 1 });
    await app.close();
    app = await montar({ real: { id: 'b', puestos: ['seo'] } });
    await request(app.getHttpServer()).get('/crm').expect(403);
  });

  it('«ver como» no puede escribir', async () => {
    app = await montar({ real: { id: 'a', puestos: ['direccion'] }, como: { id: 'b', puestos: ['seo'] } });
    await request(app.getHttpServer()).post('/crm').expect(403);
  });

  it('sin motor portado, toda ruta con permiso se deniega', async () => {
    const mod = await Test.createTestingModule({ imports: [PermisosModule], controllers: [Prueba] }).compile();
    app = mod.createNestApplication();
    await app.init();
    await request(app.getHttpServer()).get('/crm').expect(403);
  });
});
