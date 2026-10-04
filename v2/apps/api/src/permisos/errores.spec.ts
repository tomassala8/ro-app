import { Body, Controller, INestApplication, NotFoundException, Post } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { ErroresFilter, leerJson } from './errores.filter.js';

@Controller()
class Prueba {
  @Post('eco') eco(@Body() b: unknown) {
    return b;
  }
  @Post('repetido') repetido() {
    throw Object.assign(new Error('Unique constraint failed on the fields: (`correo`) SELECT …'), { code: 'P2002' });
  }
  @Post('no-esta') noEsta() {
    throw new NotFoundException('No existe esa decisión.');
  }
}

describe('errores con la forma de servir.py', () => {
  let app: INestApplication;
  beforeAll(async () => {
    app = (await Test.createTestingModule({ controllers: [Prueba] }).compile()).createNestApplication({ bodyParser: false });
    app.use(leerJson());
    app.useGlobalFilters(new ErroresFilter());
    await app.init();
  });
  afterAll(() => app.close());

  it('JSON roto → 400 en castellano, sin el texto del analizador', async () => {
    await request(app.getHttpServer()).post('/eco').set('content-type', 'application/json').send('{roto').expect(400).expect({ error: 'JSON no válido.' });
  });
  it('cuerpo demasiado grande → 413', async () => {
    await request(app.getHttpServer()).post('/eco').send({ a: 'x'.repeat(3_000_000) }).expect(413).expect({ error: 'Petición demasiado grande.' });
  });
  it('un choque de Prisma es un 409 sin SQL', async () => {
    await request(app.getHttpServer()).post('/repetido').expect(409).expect({ error: 'Ya existe.' });
  });
  it('los HttpException conservan su código y su texto', async () => {
    await request(app.getHttpServer()).post('/no-esta').expect(404).expect({ error: 'No existe esa decisión.' });
  });
});
