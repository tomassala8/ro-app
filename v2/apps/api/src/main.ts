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
  // El mismo tope que servir.py y el proxy (200 KB): una ruta no acepta más por haberse mudado a Nest.
  app.use(leerJson(Number(process.env.RO_CUERPO_MAX ?? 200_000)), urlencoded({ extended: false, limit: 200_000 }));
  // Como servir.py: las respuestas de /api son de una persona concreta, ni el navegador ni nadie en medio las guarda.
  // Una ruta que necesite otra cosa (ETag de un fichero) la pone ella y manda sobre esta.
  app.use('/api', (_req: unknown, res: { setHeader(n: string, v: string): void }, next: () => void) => {
    res.setHeader('Cache-Control', 'no-store');
    next();
  });
  // Al parar (despliegue, reinicio) termina lo que está en marcha y cierra las conexiones a Postgres.
  app.enableShutdownHooks();
  // Mismas rutas que servir.py: todo bajo /api, salvo /vivo.
  app.setGlobalPrefix('api', { exclude: ['vivo'] });
  // Solo 127.0.0.1 en local (regla de 2-oct: nunca a la wifi). En la nube, HOST=0.0.0.0 dentro del contenedor.
  await app.listen(Number(process.env.PORT ?? 4000), process.env.HOST ?? '127.0.0.1');
}
await bootstrap();
