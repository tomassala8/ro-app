import { NestFactory } from '@nestjs/core';
import { urlencoded } from 'express';
import { AppModule } from './app.module.js';
import { comprobarEntorno } from './entorno.js';
import { proxyLegado } from './legado/proxy.js';
import { leerJson } from './permisos/errores.filter.js';

async function bootstrap() {
  // Sin el entorno bien puesto, no se arranca: mejor un despliegue en rojo que una app abierta o con el reloj fijo.
  comprobarEntorno();
  // Sin lector de cuerpo global: el proxy de legado tiene que reenviar el cuerpo tal cual llega.
  const app = await NestFactory.create(AppModule, { bodyParser: false });
  // Primero el proxy (lo que Nest aún no atiende va a servir.py) y después el lector de JSON para las rutas de Nest.
  // Sin «X-Powered-By: Express»: servir.py no lo manda y no hay por qué anunciar el servidor.
  app.getHttpAdapter().getInstance().disable('x-powered-by');
  app.use(proxyLegado());
  app.use(leerJson('2mb'), urlencoded({ extended: false }));
  // Al parar (despliegue, reinicio) termina lo que está en marcha y cierra las conexiones a Postgres.
  app.enableShutdownHooks();
  // Mismas rutas que servir.py: todo bajo /api, salvo /vivo.
  app.setGlobalPrefix('api', { exclude: ['vivo'] });
  // Solo 127.0.0.1 en local (regla de 2-oct: nunca a la wifi). En la nube, HOST=0.0.0.0 dentro del contenedor.
  await app.listen(Number(process.env.PORT ?? 4000), process.env.HOST ?? '127.0.0.1');
}
await bootstrap();
