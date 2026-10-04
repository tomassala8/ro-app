/** Variables que la API necesita, comprobadas al arrancar. Si algo falta o es peligroso, no arranca (sale con 1 y dice
 *  qué): un despliegue en rojo se ve y se arregla; una API abierta a todos o con el reloj de la noche, no. */
export function comprobarEntorno(env: NodeJS.ProcessEnv = process.env): void {
  const fallos: string[] = [];
  // Producción = la nube de verdad (RO_ENTORNO=produccion, grupo ro-comun de render.yaml). NODE_ENV no vale: la imagen
  // lo lleva siempre a «production», también cuando se prueba en el Mac con docker compose.
  const nube = env.RO_ENTORNO === 'produccion';
  if (!/^postgres(ql)?:\/\//.test(env.DATABASE_URL ?? '')) fallos.push('DATABASE_URL tiene que ser una URL de Postgres.');
  if (!['local', 'access'].includes(env.RO_IDENTIDAD ?? '')) fallos.push('RO_IDENTIDAD tiene que ser «local» o «access».');
  // «local» deja elegir quién eres con ?yo= o una cabecera: en la nube, cualquiera sería Tomás.
  if (nube && env.RO_IDENTIDAD === 'local') fallos.push('RO_IDENTIDAD=local no se permite en producción: tiene que ser «access».');
  // El reloj fijo es de la noche de la migración: en producción, «hoy» sería siempre el 5-oct.
  if (nube && env.RO_RELOJ) fallos.push('RO_RELOJ no puede estar puesto en producción.');
  if (env.RO_RELOJ && Number.isNaN(Date.parse(env.RO_RELOJ))) fallos.push(`RO_RELOJ no es una fecha: «${env.RO_RELOJ}».`);
  if (env.PORT && !/^\d{2,5}$/.test(env.PORT)) fallos.push('PORT tiene que ser un número.');
  if (env.HOST && !['127.0.0.1', '0.0.0.0'].includes(env.HOST)) fallos.push('HOST: 127.0.0.1 en el Mac; 0.0.0.0 solo dentro de un contenedor.');
  // 0.0.0.0 con identidad «local» = cualquiera de la red elige quién es. Solo dentro de un contenedor (docker compose
  // pone RO_EN_CONTENEDOR=1 y publica el puerto en 127.0.0.1); en el Mac, 127.0.0.1.
  if (env.HOST === '0.0.0.0' && env.RO_IDENTIDAD !== 'access' && env.RO_EN_CONTENEDOR !== '1')
    fallos.push('HOST=0.0.0.0 con RO_IDENTIDAD=local solo dentro de un contenedor (RO_EN_CONTENEDOR=1): usa 127.0.0.1.');
  if (env.RO_LEGADO_URL && !/^https?:\/\/[^/]+/.test(env.RO_LEGADO_URL)) fallos.push('RO_LEGADO_URL no es una URL.');
  if (nube && !env.RO_LEGADO_URL) fallos.push('RO_LEGADO_URL hace falta en producción (el servicio privado del legado).');
  if (fallos.length) {
    console.error(`La API no arranca:\n- ${fallos.join('\n- ')}`);
    process.exit(1);
  }
}
