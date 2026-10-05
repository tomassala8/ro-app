import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { App } from 'supertest/types.js';
import { AppModule } from './../src/app.module.js';

describe('Salud (e2e)', () => {
  let app: INestApplication<App>;

  beforeEach(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({ imports: [AppModule] }).compile();
    app = moduleFixture.createNestApplication();
    app.setGlobalPrefix('api', { exclude: ['vivo'] });
    await app.init();
  });

  it('/vivo responde sin datos', () => {
    return request(app.getHttpServer()).get('/vivo').expect(200).expect({ ok: true });
  });

  afterEach(async () => {
    await app.close();
  });
});
