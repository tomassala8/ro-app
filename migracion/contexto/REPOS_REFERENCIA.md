> Recogido en: `migracion/PLAN_MAESTRO.md` §2.11 (lo de «esta noche» ya está hecho en la rama; lo de la fase 5 y después, resumido allí).
> **Copia saneada para Cursor (4-oct-2026).** Fuente: `/mnt/project-files/referencias_stack/`.

# Repos de referencia del stack (NestJS + Prisma + Postgres + Next)

**4-oct-2026.** Estudio de herramientas públicas ya construidas con nuestro stack, para copiar cómo ordenan la base, el backend y los permisos. Todo está contrastado con el esqueleto de `v2/` del PR #1 de ro-app (rama `claude/project-thread-rjes21`) y con `migracion/PLAN_MAESTRO.md` (versión 2). Este documento **no cambia el plan**: el dueño del plan decide qué entra.

## Qué repos y por qué

| Repo | Stack | Para qué sirve mirarlo |
|---|---|---|
| **teableio/teable** | Nest + Prisma + Next, pnpm | El más parecido a nosotros. Contrato zod compartido front/back, guardas globales, transacciones con CLS, `migrate deploy` al arrancar, e2e con Postgres real. |
| **calcom/cal.com** (`apps/api/v2`) | Nest + Prisma (front Next) | Roles por organización/equipo, filtro de errores de Prisma, formato de respuesta, logs con request-id, cómo migraron de roles fijos a permisos en tabla sin romper nada. |
| **ghostfolio/ghostfolio** | Nest + Prisma 7 + Bull | Producción real con Prisma 7 y `PrismaPg` (como nosotros). Dockerfile, entrypoint, salud, matriz rol→permisos compartida con el front, guarda que bloquea escrituras al suplantar. |
| **hoppscotch** (`packages/hoppscotch-backend`) | Nest + Prisma | Modelo de roles simple por equipo y bloqueo `FOR UPDATE` en listas ordenables. También como ejemplo de lo que **no** hacer (guardas por ruta). |
| **documenso/documenso** | Prisma + zod (ya no Next: pasó a React Router 7) | Permisos dentro del `WHERE` (contra IDOR), auditoría en la misma transacción, errores con código estable, cola de trabajos en Postgres, sesión por cookie. |
| **twentyhq/twenty** | Nest + TypeORM | Solo de pasada (lo revisa el hilo de la migración). Config validada y cola con driver «sync» para pruebas. El resto es sobre-ingeniería para 30 personas. |
| brocoders/nestjs-boilerplate, notiz-dev/nestjs-prisma-starter | plantillas Nest | Config validada por áreas; filtro `PrismaClientExceptionFilter`. notiz-dev está desfasado (Prisma 5, 2023). |

## Lo que v2 ya hace bien (coincide con los repos maduros)

- **Guarda global que deniega lo no declarado** (`v2/apps/api/src/permisos/permisos.module.ts`, `APP_GUARD`). Es el patrón de Teable (`global.module.ts`). Hoppscotch pone guardas ruta a ruta y basta olvidar una para dejar algo abierto. Nosotros además tenemos `rutas-declaradas.spec.ts`, que ninguno de los seis tiene.
- **Bloquear escrituras en «ver como»**: Ghostfolio lo hace igual (`ImpersonationWriteGuard` global).
- **Un solo cliente de Prisma con `PrismaPg`** (`packages/db/src/index.ts`): igual que Ghostfolio y cal.com.
- **Matriz de permisos en un paquete compartido** (`@ro/permisos`): Teable (`packages/core/src/auth/role/constant.ts`) y Ghostfolio (`libs/common/src/lib/permissions.ts`) hacen lo mismo, y el front usa la misma matriz para ocultar botones.
- **Dockerfile multi-etapa con HEALTHCHECK a `/vivo`**: correcto.

## Recomendaciones para ESTA NOCHE (orden de prioridad)

Todas son pequeñas, no tocan el contrato que ve el equipo y ayudan a pasar las puertas `caidas.sh` y `seguridad_http.py`.

1. **Un filtro global de errores (`@Catch()` sin argumentos) con la forma `{"error": …}` de servir.py.** Hoy `main.ts` no tiene ninguno, así que un fallo inesperado en una ruta de Nest sale con el formato por defecto de Nest. Teable (`src/filter/global-exception.filter.ts`) y cal.com (`bootstrap.ts`) lo registran siempre. Debe:
   - traducir los errores de Prisma: P2002 → 409, P2025 → 404, P2003 → 400 (cal.com `filters/prisma-exception.filter.ts`);
   - responder 400 al JSON roto en vez de 500 (es N-13 de `PENDIENTES_LOGICA.md`);
   - no sacar nunca la pila ni el SQL al navegador; sí al log;
   - no apuntar como error los 400/401/403/404 (Teable), para no llenar el log de ruido.
2. **`app.enableShutdownHooks()` en `main.ts`.** Sin él, `onModuleDestroy` de `PrismaService` no se ejecuta al reiniciar el contenedor y quedan conexiones colgadas en Postgres. Lo hacen todas las plantillas.
3. **Validar las variables de entorno al arrancar y no arrancar si falta algo.** Teable (Joi, `env.validation.schema.ts`), Ghostfolio (`envalid`), brocoders (`validate-config.ts`). Para nosotros, con zod en un `config.ts`: `DATABASE_URL`, `RO_IDENTIDAD` (en la nube solo `access`), `RO_RELOJ`, `PORT`, `HOST`, la URL del legado. Así un `RO_IDENTIDAD=local` olvidado en la nube no arranca, en vez de abrir la puerta.
4. **Tamaño del pool de conexiones explícito.** `PrismaPg` abre hasta 10 por defecto, y en la nube también tira de Postgres `servir.py`. cal.com fija el pool por configuración (`modules/prisma/prisma.module.ts`). Poner `max` en `crearPrisma` y sumar con el legado por debajo del límite del plan de Postgres contratado.
5. **Migraciones: `prisma migrate deploy` antes de arrancar y abortar si falla.** Teable (`scripts/start.sh`) y Ghostfolio (`docker/entrypoint.sh`). Nuestro Dockerfile dice «se aplican aparte»: vale, pero que sea un paso que pare el despliegue si falla. Nunca `migrate dev` en la nube. Si el proveedor pone un pooler delante, migrar con `DIRECT_URL` (Ghostfolio `.config/prisma.ts`). El seed, idempotente (`createMany({ skipDuplicates: true })`), nunca `deleteMany`.
6. **Contenedor sin root.** Añadir `USER node` en la etapa final del Dockerfile (Ghostfolio). Es una línea.
7. **Logs con request-id y cabeceras sensibles tapadas.** `nestjs-pino` con `genReqId` (Teable `src/logger/logger.module.ts`); cal.com filtra cabeceras antes de loguear. Tapar `cookie`, `cf-access-jwt-assertion` y `x-ro-yo`. Ayuda mucho a leer qué falló de madrugada.

## Recomendaciones para las rutas que se mudan a Nest (fase 5)

8. **Un contrato por ruta en zod, compartido front/back.** Es lo que más estabilidad da en Teable (`packages/openapi/src/<dominio>/<acción>.ts`): en un archivo, el esquema de entrada, el de salida, la ruta y la función del cliente. El back valida con un `ZodValidationPipe` y el front importa los mismos tipos. Para nosotros, además, **validar la salida** con el esquema garantiza el contrato (`snake_case`, fechas en texto) que comprueba la puerta. Documenso hace lo mismo con `.output(schema)`.
9. **Transacción y usuario actual por contexto (`nestjs-cls`).** Teable (`packages/db-main-prisma/src/prisma.service.ts`): `$tx()` reutiliza la transacción abierta y los servicios leen el usuario con `cls.get('user.id')`. Encaja con el escritor único del rastro de F5.1: abrir la transacción, tomar `pg_advisory_xact_lock` y escribir rastro y cambio juntos, sin pasar `tx` de función en función.
10. **El permiso también dentro del `WHERE`.** Documenso (`buildTeamWhereQuery`) busca el recurso ya filtrado por lo que la persona puede ver; si no sale, 404. Es la defensa contra pedir `/api/cliente/:id` de otra cartera cambiando el número. Complementa la guarda, no la sustituye.
11. **Listas con orden manual**: `SELECT … FOR UPDATE` y un índice único sobre la posición (Hoppscotch `team-collection.service.ts`). Solo si alguna pantalla reordena.

## Para después de la noche (§8 del plan)

12. **Permisos en tabla sin big bang.** cal.com añadió `Role` + `RolePermission {resource, action}` con permisos `recurso.accion` y una marca en la petición: si el sistema nuevo autoriza, el viejo no se consulta. Así convivieron los dos. Es el camino para pasar `reglas_permisos.json` a tablas con pantalla en Ajustes.
13. **Cola de trabajos en Postgres, no en Redis.** Para 30 personas, `pg-boss` o el patrón de Documenso (`BackgroundJob`, ids deterministas para no duplicar) evitan montar Redis. El cron solo encola, no trabaja (Ghostfolio `cron.service.ts`). Driver «sync» para pruebas (Twenty). Para la tubería y los bucles que hoy viven en Python.
14. **Auditoría en la misma transacción que el cambio**, con el id del objeto como texto, sin clave foránea, para que sobreviva al borrado (cal.com `BookingAudit`, Documenso `DocumentAuditLog`).
15. **Tipos de verdad**: `Decimal` para dinero, nunca `Float` (Ghostfolio lo hace mal); `timestamptz`; campos base `created_at/created_by/updated_at/updated_by` con `@map` a snake_case (Teable).
16. **Borrado lógico, si se usa, con una extensión de Prisma.** Teable tiene 463 filtros `deletedTime: null` a mano; es justo el error que se olvida.
17. **Pruebas e2e contra Postgres real, una base por proceso** (Teable `E2E_WORKER_DB`, `TZ=UTC`). Encaja con «las puertas en cada PR».
18. **Salud en dos rutas**: `/vivo` (proceso vivo) y otra de «listo» que pruebe Postgres y el legado (`@nestjs/terminus`, Teable y Hoppscotch).

## Qué NO copiar

- **Esquema por cliente o base de datos por espacio** (Twenty, Teable): para un único equipo es complejidad pura.
- **GraphQL** (Twenty, Hoppscotch): REST con contrato zod es más simple y es lo que ya habla el front.
- **Réplicas lectura/escritura y versionado por fecha en cabecera** (cal.com): pensados para una API pública.
- **Caché de permisos en Redis** (cal.com `roles.guard.ts`): al cambiar a alguien de puesto, sigue viendo lo de antes hasta que caduca.
- **JWT en `localStorage`** (Ghostfolio): expuesto a XSS. Seguimos con Cloudflare Access; si algún día hay sesión propia, cookie `httpOnly` con token guardado como hash y revocable (Documenso `session.ts`).
- **Limitador de peticiones que falla abierto** (Ghostfolio) y **CORS `*`** (cal.com).
- **Escribir en la base en cada petición desde la autenticación** (Ghostfolio hace un `upsert` en `jwt.strategy.ts`).
- **`Either` de fp-ts por todo el código** (Hoppscotch): ceremonia que no compensa.
- **Configuración guardada en la base sin validar** (Hoppscotch `InfraConfig`).

## Fuentes

Clonados el 4-oct-2026 (`--depth 1`). cal.com en el commit 54343aa del 20-sep-2026: ya publica la edición comunitaria («Cal.diy») y el PBAC quedó como esquema y migraciones, sin el motor. Las rutas citadas son relativas a cada repositorio.
