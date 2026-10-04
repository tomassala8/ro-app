import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  // Mismas rutas que servir.py: todo bajo /api, salvo /vivo.
  app.setGlobalPrefix('api', { exclude: ['vivo'] });
  // Solo 127.0.0.1 en local (regla de 2-oct: nunca a la wifi). En la nube, HOST=0.0.0.0 dentro del contenedor.
  await app.listen(Number(process.env.PORT ?? 4000), process.env.HOST ?? '127.0.0.1');
}
await bootstrap();
