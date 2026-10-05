> Recogido en parte en: `migracion/PLAN_MAESTRO.md` §2.10 (copias), §2.11 (lo que se copia de otros), §2.12 (seguridad en la nube) y §2.13 (agente solo toda la noche). Lo demás (§0–§9 y §11 de aquí) solo está en este fichero.
> **Copia saneada para Cursor (4-oct-2026).** Fuente: `/mnt/project-files/referencias_stack/`. Nombres de personas cambiados por su puesto.

# Buenas prácticas y errores ya cometidos · Next 16 + Nest 12 + Postgres 16 + Prisma 7

**4-oct-2026 · versión 3 (final).** Este documento reúne errores **que otros ya cometieron y dejaron documentados**, con lo que hay que hacer para no repetirlos. Las fuentes son incidencias de GitHub, informes de caídas, CVE, documentación oficial y blogs. Es para una herramienta interna que usarán a diario unas 30 personas.

Está cruzado con `migracion/PLAN_MAESTRO.md` y con el código del PR #1 de ro-app (rama `claude/project-thread-rjes21`), sin editarlos. Versiones del PR: **Next 16.3.8, React 19.2.8, Nest ^12.0.1, Prisma 7.10.0 con `@prisma/adapter-pg`, Tailwind 4.**

**Cómo leerlo**
- **P0 · esta noche.** Si se ignora, la migración se rompe, se pierden datos o queda un agujero.
- **P1 · antes del piloto o de subir a la nube.**
- **P2 · después**, al pasar a tipos de verdad y apagar el legado.
- **[INFERIDO]** = deducción aplicada a nuestro caso, no lo dice la fuente.
- **✅ PR #1** = ya está bien en el código o en el plan; no hay que hacer nada.

Cada punto: qué pasó (y a quién), qué hacer, **cómo comprobarlo** y la fuente.

---

## Resumen para esta noche

### Lo que el PR #1 ya hace bien (comprobado en el código)
- Next 16.3.8: por encima de todos los parches de 2025-2026 citados abajo (React2Shell, saltos de middleware, caché cruzada, contrabando de peticiones).
- La guarda de permisos es *singleton* y lee los decoradores con `getAllAndOverride`. Evita los dos fallos clásicos de guardas que no actúan (§4.1).
- `copiar_sqlite_a_pg.py` ya recoloca los contadores (`setval`) después de copiar. Es el fallo número uno al pasar de SQLite a Postgres (§1.1).
- Nest acepta JSON hasta 2 MB y el proxy corta a 200 KB. No hay choque de límites.
- Nest escucha en 127.0.0.1 por defecto.

### Los 15 que quedan para esta noche
1. **El agente no puede tocar nada de verdad.** Ni credenciales de producción, ni el llavero del Mac, ni las copias. Replit (jul-2025) y un agente de Cursor (PocketOS, 2026) borraron bases de producción, en el segundo caso también las copias. §0.1–0.3
2. **Las pruebas y las puertas no las puede editar el agente.** Los modelos tocan los tests para que pasen, y uno de cada cuatro informes de «hecho» es falso. Huella de `puerta.sh`, contratos y fotos antes de empezar, y comprobarla por la mañana. §0.4–0.5
3. **Copia restaurada de verdad antes de empezar**, con `pg_dump` de la misma versión que el servidor. Es lo que falló en GitLab en 2017. §7.1
4. **Validar los datos copiados:** tipos mezclados en SQLite, bytes NUL, fechas en texto, 0/1. §1.2–1.5
5. **Prisma 7 no carga `.env` solo y `pg` espera sin límite** si la base no responde. Poner `connectionTimeoutMillis` y un `max` razonable. §2.1–2.2
6. **Nunca `migrate dev`, `migrate reset` ni `db push`** contra una base con datos. §2.3
7. **`migrate diff` debe salir vacío.** Prisma no conoce los `CHECK`, las vistas ni los disparadores, y si los ve en la base propone borrarlos. §2.4
8. **El rastro encadenado: un solo escritor a la vez entre Python y Nest**, con `pg_advisory_xact_lock`, y la huella calculada igual en los dos (milisegundos frente a microsegundos). §3.1–3.2
9. **Los disparadores de fila no paran un `TRUNCATE`.** §3.3
10. **`output: "standalone"` en `next.config.ts`:** no copia `public/` (donde vive `public/legacy/`) ni `.next/static`. Además, `next start` no sirve con standalone. Hay que decidir cómo arranca. §5.1
11. **Identidad en la nube:** que Nest se niegue a arrancar si escucha fuera de 127.0.0.1 sin `RO_IDENTIDAD=access`. Validar firma, `aud` e `iss` del JWT de Cloudflare, no la cabecera de email. §4.5–4.7
12. **Nada de caché compartida con datos de una persona.** Revisar la salida de `next build`: ninguna ruta con datos por persona puede salir como estática. §5.3
13. **«Ver como»:** todo lo que no sea GET da 403, incluido lo que crea tokens, preferencias o sesiones. GitLab tuvo dos CVE por esto. §4.9–4.10
14. **El esquema solo crece esta noche.** Nada de renombrar ni borrar columnas mientras `servir.py` use las mismas tablas. §1.8
15. **La vuelta atrás en un solo paso, ensayada.** §0.6

---

## 0. El agente trabajando solo toda la noche

**0.1 Sin credenciales de producción ni de proveedores · P0**
- **Qué pasó:** Replit, julio de 2025. Durante una «congelación de código» el agente borró la base de producción de SaaStr (más de 1.200 directivos y 1.190 empresas). Dijo que no se podía recuperar, y era falso. La congelación existía solo en el prompt. [fuente](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure/)
- **Qué hacer:** que el agente trabaje solo contra la Postgres local de `docker-compose` y la copia de `~/RO_MIGRACION`. El plan ya prohíbe desplegar y mover llaves (regla 6).
- **[INFERIDO]** `config.py › secreto()` busca llaves en el **llavero del Mac**. Si Cursor corre con el usuario de dirección, puede leerlas. Opciones: otro usuario de macOS sin esas llaves, o bloquear el llavero esa noche. `servicios.sh` ya fuerza que nada salga fuera; esto cierra la puerta de lectura.
- **Comprobar:** desde la terminal de Cursor, `security find-generic-password -s <alguna llave>` debe fallar.

**0.2 Ningún token suelto en el disco que alcanza · P0**
- **Qué pasó:** PocketOS, 2026. Un agente de Cursor «resolvió» un desajuste de credenciales borrando un volumen de Railway en 9 segundos. Usó un token encontrado en un fichero que no tenía nada que ver, y las copias estaban en el mismo volumen. [fuente](https://www.techradar.com/pro/it-took-9-seconds-tech-founder-outlines-how-rogue-claude-powered-ai-tool-wiped-entire-company-database-and-backups-but-says-theres-no-such-thing-as-bad-publicity)
- **Comprobar:** `escaner_secretos.py` (ya existe) sobre todo lo que alcanza Cursor, no solo sobre el repositorio. Y las copias de seguridad, fuera de su alcance.

**0.3 Lista de comandos permitidos y freno a los borrados · P0**
- **Qué pasó:** en el foro de Cursor, un agente en modo YOLO borró el ordenador entero durante una migración de Express a Next.js; otro hizo `rm -rf` sobre una carpeta hermana. Gemini CLI destruyó ficheros porque falló un `mkdir` y siguió como si nada. [Cursor 1](https://forum.cursor.com/t/cursor-yolo-deleted-everything-in-my-computer/103131) · [Cursor 2](https://forum.cursor.com/t/cursor-ai-agent-used-rm-rf-to-delete-files-from-a-parallel-subdirectory/44742) · [Gemini](https://incidentdatabase.ai/cite/1178)
- **Qué hacer:** en Cursor, activar la protección contra borrado de ficheros y contra ficheros externos, y usar una lista de comandos permitidos. Scripts con `set -euo pipefail`. Commit en cada puerta verde (el plan ya lo hace en su rama).

**0.4 Las pruebas no se tocan · P0**
- **Qué pasó:** el estudio ImpossibleBench encontró que, ante tareas imposibles, los modelos modifican los tests, fijan a mano el resultado esperado o hacen trampas parecidas. Uno lo hizo el 76 % de las veces, y los modelos más capaces hacen más trampa. Lo único que lo bajó casi a cero fue **quitar el permiso de escritura sobre los tests**. [fuente](https://www.greaterwrong.com/posts/qJYMbrabcQqCZ7iqm/impossiblebench-measuring-reward-hacking-in-llm-coding-1)
- **Qué hacer:** antes de lanzar, guardar la huella de las puertas y sus referencias fuera del repositorio. Por la mañana, compararla:
  ```
  shasum -a 256 migracion/puerta.sh migracion/contrato*.py migracion/vectores_permisos.py migracion/caidas.sh migracion/seguridad_http.py migracion/rendimiento.py pruebas_*.py > ~/RO_MIGRACION/huellas_puertas.txt
  ```
  Además, `git diff --stat <commit_inicial> -- migracion/ pruebas_*.py` y revisar todo lo que no sea `PROGRESO.md`. Las fotos de referencia y `excepciones.txt` ya viven en `~/RO_MIGRACION`; que estén en solo lectura para Cursor (`chmod -R a-w`).

**0.5 El informe del agente no prueba nada · P0**
- **Qué pasó:** en un estudio de 2026 sobre agentes que se evalúan a sí mismos, el 75,8 % de sus fallos fueron «falsos éxitos»: el agente decía que había terminado. Razonar más no lo evitaba. [fuente](https://arxiv.org/abs/2606.09863)
- **Qué hacer:** por la mañana, alguien vuelve a lanzar `puerta.sh` de todas las fases desde cero (reinicio limpio) antes de creerse `PROGRESO.md`.

**0.6 Vuelta atrás en un paso · P0**
- **Qué hacer:** [INFERIDO a partir de Shopify, GitHub y Azure] dejar escrito cómo se vuelve en un paso: vaciar `RUTAS_EN_NEST` (todo va al legado) y, si cae Next, servir `servir.py` directamente. Ensayarlo una vez. [Azure](https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig)

**0.7 No «mejorar» el código viejo · P1**
- **Lección:** el código feo guarda años de arreglos de casos raros, y reescribirlo los pierde. Es la lección de Netscape. El plan ya lo dice (regla 1: un cambio visible es un fallo). [Spolsky](https://www.joelonsoftware.com/2000/04/06/things-you-should-never-do-part-i/)

---

## 1. Datos: de SQLite a Postgres

**1.1 Contadores detrás del id más alto · ✅ PR #1**
- El error de siempre: «duplicate key value violates unique constraint» después de copiar filas con id. `copiar_sqlite_a_pg.py` ya hace `setval`. [Supabase](https://supabase.com/docs/guides/troubleshooting/inserting-into-sequenceserial-table-causes-duplicate-key-violates-unique-constraint-error-pi6DnC)
- **Comprobar igual:** un INSERT nuevo en cada tabla, desde Python y desde Nest, después de copiar.

**1.2 Tipos mezclados en SQLite · P0**
- SQLite deja meter texto en una columna INTEGER. Postgres no. La copia puede fallar o convertir mal. [SQLite](https://www.sqlite.org/datatype3.html) · [Neon](https://neon.com/docs/import/migrate-sqlite)
- **Comprobar:** en SQLite, `SELECT typeof(col), count(*) FROM t GROUP BY 1;` por columna. Si una columna tiene más de un tipo, es un riesgo. Después, contar filas y no nulos por tabla en los dos lados.

**1.3 Bytes NUL en textos · P0**
- **Qué pasó:** en Atlassian (Bitbucket) la migración a Postgres fallaba con «invalid byte sequence for encoding UTF8: 0x00». Postgres no acepta ese carácter en texto. [fuente](https://support.atlassian.com/bitbucket-data-center/kb/database-migration-to-postgresql-fails-invalid-byte-sequence-for-encoding-utf8-0x00/)
- **Comprobar:** `SELECT count(*) FROM t WHERE instr(col, char(0)) > 0;` en SQLite, por cada columna de texto.

**1.4 0/1 y fechas en texto · P0 (esta noche se quedan como hoy, bien)**
- **Qué pasó:** Vikunja y GoToSocial migraron con pgloader y los booleanos acabaron como `bigint`, y el backend rompía. [Vikunja](https://community.vikunja.io/t/db-conversion-sqlite-to-postgresql/3421/18) · [GoToSocial](https://git.gay/elsaas/server/wiki/Gotosocial-SQLite-to-Postgres-migration)
- El plan mantiene 0/1 y texto esta noche (§2.3), así que esto no rompe hoy. Riesgo **[INFERIDO]**: que Prisma o Nest devuelvan `true` donde `servir.py` devuelve `1`. El contrato tiene que comparar tipos, no solo valores.
- **Comprobar:** buscar 20 fechas cerca de medianoche y del cambio de hora, y compararlas en SQLite, en Postgres y en la respuesta de Nest.

**1.5 SQL que SQLite acepta y Postgres no · P0**
- Ejemplos: `GROUP BY` con columnas sin agregar, texto entre comillas dobles, `GROUP_CONCAT`, `datetime()`, `strftime`, `char()`, subconsultas sin alias, división entera. [ejemplo](https://icculus.org/~chunky/stuff/sqlite3_example/sqlite_to_pgsql.html)
- La memoria del proyecto dice que `despliegue/base.py` necesitó 8 arreglos para funcionar en Postgres. Quedan los que no salieron en las pruebas.
- **Comprobar:** `grep -rnE "group_concat|datetime\(|strftime|julianday|char\(|IFNULL|\|\|" --include=*.py .` y pasar las baterías completas contra Postgres.

**1.6 Mayúsculas en búsquedas · P0 si hay buscador**
- En SQLite, `LIKE` no distingue mayúsculas en ASCII; en Postgres sí. Ninguno de los dos trata igual «José» y «jose». Las búsquedas cambian de resultado **sin dar error**. [SQLite](https://www.sqlite.org/lang_expr.html) · [Prisma](https://prisma.io/docs/orm/prisma-client/queries/case-sensitivity)
- **Comprobar:** `grep -rn " LIKE " --include=*.py .` y una prueba de contrato de `/api/buscar` con «maria», «María» y «MARIA».

**1.7 Orden de los resultados (collation) · P1**
- El `ORDER BY nombre` puede salir distinto en SQLite (binario), en la Postgres local y en la de la nube. Rompe las fotos y los contratos. Autumn tuvo una caída de 75 minutos (15-mar-2026) por cambiar la collation más tarde. [Postgres](https://www.postgresql.org/docs/current/collation.html) · [Autumn](https://useautumn.com/blog/post-mortem-database-outage-caused-by-collation-migration-locking-conflict)
- **Comprobar:** `SELECT datcollate FROM pg_database WHERE datname = current_database();`, igual en local y en la nube. Desempatar siempre por id.

**1.8 El esquema solo crece mientras convivan las dos apps · P0**
- Así lo hizo Stripe con cientos de millones de objetos: escribir en los dos sitios, leer del nuevo, escribir solo en el nuevo y, al final, borrar lo viejo. Nunca de golpe. [Stripe](https://stripe.com/blog/online-migrations) · [Prisma: expandir y contraer](https://www.prisma.io/docs/guides/database/data-migration)
- **Comprobar:** `grep -nE "DROP COLUMN|RENAME|ALTER COLUMN .* TYPE" v2/packages/db/prisma/migrations -r` vacío esta noche.

---

## 2. Prisma 7

**2.1 Arranque distinto de Prisma 6 · P0**
- Adaptador de driver obligatorio, `prisma.config.ts`, `output` obligatorio, solo ESM, sin *middleware* (ahora son *extensions*), y **`.env` no se carga solo**. Si `DATABASE_URL` llega vacía, falla tarde o apunta a otra base. [Prisma](https://www.prisma.io/docs/guides/upgrade-prisma-orm/v7)
- **Comprobar:** `import 'dotenv/config'` en `prisma.config.ts`. Al arrancar Nest, parar si falta `DATABASE_URL` y escribir en el log el host (sin la contraseña).

**2.2 Sin tiempo de espera por defecto · P0**
- Prisma 6 esperaba 5 s a conectar; `pg` espera **sin límite**. Si la base no responde o el pool se agota, las peticiones se quedan colgadas. Además, un certificado SSL inválido ahora da error. [Prisma](https://www.prisma.io/docs/guides/upgrade-prisma-orm/v7)
- Caso real: una app Next 16 + Postgres en Render se caía por memoria cada 24 h, y uno de los motivos era `connectionTimeoutMillis = 0`. [fuente](https://dev.to/danielrusnok/our-nextjs-app-crashed-every-24-hours-here-are-the-six-memory-fixes-2mj1)
- **Comprobar:** en el adaptador, `connectionTimeoutMillis: 5000` y un `max` explícito. Prueba: parar Postgres y ver que Nest responde error en segundos (el plan ya lo pide en `caidas.sh`).

**2.3 Nunca `migrate dev`, `migrate reset` ni `db push` con datos · P0**
- **Qué pasó:** en Railway, un desarrollador creyó que usaba la base de demo y borró la de producción de una cadena de salones. No tenía copias. [fuente](https://station.railway.com/questions/accidental-prisma-migrate-reset-on-produ-a081de50)
- Para la base que ya existe: `0_base` marcada con `prisma migrate resolve --applied 0_base`. Después, solo `migrate deploy` y `migrate status`. [Prisma](https://www.prisma.io/docs/orm/prisma-migrate/workflows/baselining)
- **Comprobar:** `SELECT migration_name, finished_at, rolled_back_at FROM _prisma_migrations;` y `prisma migrate status` sin nada pendiente ni fallido.

**2.4 `db pull` y `migrate diff` no ven `CHECK`, vistas ni disparadores · P0**
- Prisma lo dice en su tabla de funciones: esos objetos se añaden a mano en la migración. El plan ya los mete en `0_base`. El riesgo está en la siguiente migración. [Prisma](https://docs.prisma.io/docs/orm/reference/database-features)
- **Comprobar:** `prisma migrate diff --from-migrations prisma/migrations --to-schema prisma/schema.prisma --script` sin `DROP TRIGGER` ni `DROP VIEW`. Contar en la base:
  ```sql
  SELECT count(*) FROM pg_constraint WHERE contype = 'c';
  SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal;
  SELECT count(*) FROM pg_views WHERE schemaname = 'public';
  ```
  Y `pg_dump --schema-only` de la base de referencia frente a la nueva, con `diff`.

**2.5 Una migración fallida bloquea todo · P1**
- **Qué pasó:** en Fly.io, la migración corría al arrancar la app; falló y las máquinas no llegaban a levantarse. Con una migración fallida, `migrate deploy` se niega a aplicar ninguna más hasta hacer `migrate resolve`. [Fly](https://community.fly.io/t/failed-prisma-migration-locks-out-machines/16178)
- **Qué hacer:** la migración, en el «pre-deploy command» de Render, no al arrancar. Si falla, Render cancela el despliegue y sigue la versión vieja. [Render](https://render.com/docs/deploys)

**2.6 Transacciones · P1**
- Usar `prisma.` en vez de `tx.` dentro de `$transaction` deja la consulta fuera y puede bloquearse contra ella. Tiempos por defecto: 2 s de espera y 5 s de duración. Nada de llamadas de red dentro. [caso](https://dev.to/reyronald/dealing-with-open-database-transactions-in-prisma-3clk)
- **Prisma 7.10 con `adapter-pg` y pool de 1 conexión:** un proyecto reporta que, después de un ROLLBACK por tiempo, lo pendiente se confirmó dentro de la transacción de la siguiente petición. No está confirmado por Prisma, pero es nuestra versión exacta. **No usar `max: 1`.** [fuente](https://github.com/mattiasvoleman/SchemaPro/pull/74)
- El código `P2024` (pool agotado) ya no existe en Prisma 7.8+; el error llega de `pg-pool`. Si algún filtro o reintento lo busca, se traga el fallo. [fuente](https://github.com/yldm-tech/forma/pull/48)
- **Comprobar:** `grep -rn "P2024" v2/` vacío. Buscar `prisma.` dentro de `$transaction(async`.

**2.7 JSON: `BigInt` y `Decimal` · P0 en rutas que se muden**
- `JSON.stringify` revienta con `BigInt` («Do not know how to serialize a BigInt»), que sale en `count(*)` de `$queryRaw`. `Decimal` sale como texto. [Prisma](https://www.prisma.io/docs/orm/v7/prisma-client/special-fields-and-types)
- **Comprobar:** `count(*)::int` en el SQL crudo. El contrato compara tipos.

**2.8 Inyección con `$queryRawUnsafe` · P0**
- Prisma lo advierte. Los nombres de tabla no se pueden parametrizar, y eso empuja a usar la versión insegura. [Prisma](https://www.prisma.io/docs/orm/v7/prisma-client/using-raw-sql/raw-queries)
- **Comprobar:** `rg "queryRawUnsafe|executeRawUnsafe|Prisma\.raw\(" v2/` vacío, o con una lista blanca de identificadores.

**2.9 Un solo `PrismaClient` por proceso · P0**
- Cada instancia abre su propio pool. En Next, el recargado en caliente crea varias si no se guarda en `globalThis`. [Prisma](https://www.prisma.io/docs/orm/more/troubleshooting/nextjs)
- **Comprobar:** `grep -rn "new PrismaClient" v2/apps` da una sola línea.

**2.10 N+1 · P1**
- Un `findMany` y luego una consulta por fila. En local no se nota; en la nube, con red de por medio, sí. Usar `include`/`select` o `relationLoadStrategy: "join"`. [Prisma](https://prisma.io/docs/guides/prisma-guides/query-optimization-performance)
- **Comprobar:** `log: ['query']` en pruebas; más de unas 10 consultas en una lectura es sospechoso.

---

## 3. Postgres

**3.1 El rastro encadenado con dos escritores · P0**
- **[INFERIDO, con base en la documentación de Prisma sobre aislamiento]** Con el aislamiento por defecto, dos inserciones a la vez (una de Python y otra de Nest) pueden leer la misma huella anterior y bifurcar la cadena. [Prisma](https://www.prisma.io/docs/orm/v7/prisma-client/queries/transactions)
- **Qué hacer:** `pg_advisory_xact_lock(<clave fija>)` dentro de la transacción. El de sesión (`pg_advisory_lock`) no se suelta solo si la conexión vuelve al pool, y no funciona con PgBouncer en modo transacción. [Postgres](https://www.postgresql.org/docs/16/explicit-locking.html)
- **Comprobar:** 50 inserciones a la vez, mitad desde Python y mitad desde Nest, y después `GET /api/rastro/verificar` en verde.

**3.2 Milisegundos frente a microsegundos en la huella · P0**
- Postgres guarda microsegundos; `Date` de JS, milisegundos. Si la huella del rastro incluye la hora, Python y Node pueden calcular huellas distintas para la misma fila. Está documentado en Drizzle; en Prisma es [INFERIDO]. [fuente](https://github.com/drizzle-team/drizzle-orm/issues/1061)
- Esta noche las fechas siguen como texto, lo que lo evita. `packages/compat` ya prueba la huella contra Python; que esa prueba use horas con microsegundos.

**3.3 `TRUNCATE` se salta los disparadores de fila · P0**
- Un disparador `FOR EACH ROW` no salta con `TRUNCATE`, y el dueño de la tabla puede hacer `DISABLE TRIGGER`. [Postgres](https://www.postgresql.org/docs/16/sql-createtrigger.html)
- **Qué hacer:** añadir un disparador `BEFORE TRUNCATE ... FOR EACH STATEMENT` que lance error, y que la app conecte con un usuario que no sea dueño de las tablas: `REVOKE TRUNCATE, UPDATE, DELETE ON <rastro> FROM <usuario_app>`.
- **Comprobar:** con el usuario de la app, `TRUNCATE <rastro>;` falla.

**3.4 Migraciones que bloquean tablas · P1**
- **Qué pasó:** en Handshake, una migración que añadía una clave foránea a `users` se quedó esperando detrás de una lectura larga y bloqueó todas las demás consultas. La web cayó casi un minuto. [Handshake](https://joinhandshake.com/blog/our-team/postgresql-and-lock-queue) · [Xata](https://xata.io/blog/migrations-and-exclusive-locks)
- **Qué hacer:** `SET lock_timeout = '3s';` al principio de cada migración, claves foráneas con `NOT VALID` y validarlas después, e índices con `CONCURRENTLY`.
- **Comprobar:** antes de migrar, buscar sesiones «idle in transaction» en `pg_stat_activity`.

**3.5 Conexiones totales · P1**
- Render permite 100 conexiones con menos de 8 GB de RAM. Next, Nest, `servir.py` y la tubería suman, y durante un despliegue conviven dos instancias. [Render](https://render.com/docs/postgresql-creating-connecting)
- **Comprobar:** `application_name` en cada cadena de conexión y, durante `caidas.sh`:
  ```sql
  SELECT application_name, state, count(*) FROM pg_stat_activity GROUP BY 1, 2;
  ```

**3.6 Índices en claves foráneas · P1**
- Postgres no los crea solo. Render lo da como la causa de lentitud más fácil de arreglar: en su prueba, un borrado pasó de 19 s a 342 ms. [Render](https://render.com/blog/postgresql-top-cause-slow-queries)
- **Comprobar:**
  ```sql
  SELECT c.conrelid::regclass, a.attname
  FROM pg_constraint c
  JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
  WHERE c.contype = 'f'
    AND NOT EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = c.conrelid AND i.indkey[0] = c.conkey[1]);
  ```

**3.7 Consultas lentas a la vista · P1**
- `pg_stat_statements` activado y `log_min_duration_statement = 500`.

**3.8 No desactivar nunca autovacuum · P2**
- **Qué pasó:** Sentry, 20-ago-2015. Postgres dejó de aceptar escrituras casi un día por el «transaction ID wraparound», con autovacuum mal ajustado. Con 30 personas el riesgo es bajo. [Sentry](https://blog.sentry.io/transaction-id-wraparound-in-postgres)

**3.9 Tipos de verdad (después) · P2**
- `timestamptz`, dinero en `numeric` o céntimos (nunca `float` ni `money`), `text`, `identity`, `boolean`, `NOT EXISTS` en vez de `NOT IN`, y `>= AND <` en vez de `BETWEEN` con fechas. [Postgres «Don't Do This»](https://wiki.postgresql.org/wiki/Don%27t_Do_This)

**3.10 RLS (seguridad por filas): no por ahora · P2**
- Con la guarda central de Nest basta. Si algún día se usa, estos son los fallos típicos: probar con superusuario, olvidar `FORCE ROW LEVEL SECURITY`, confundir `USING` con `WITH CHECK`, perder la identidad con el pool, y que las vistas materializadas se salten las políticas. [Bytebase](https://www.bytebase.com/blog/postgres-row-level-security-footguns)

---

## 4. Nest, identidad y permisos

**4.1 Guardas que no actúan · ✅ PR #1, falta la prueba**
- **Qué pasó:** una guarda global con `Scope.TRANSIENT` no llega a ejecutarse en controladores sin dependencias por petición, y la ruta queda abierta sin avisar (issue #17991, Nest 12.1.2, abierto). Otros fallos típicos: leer con `reflector.get` y perder los decoradores de clase, que la guarda devuelva `undefined`, o un `@Catch()` que se trague el 403. [#17991](https://github.com/nestjs/nest/issues/17991) · [guía](https://fixdevs.com/blog/nestjs-guard-not-working/)
- La guarda del PR #1 es *singleton* y usa `getAllAndOverride`. Bien.
- **Comprobar:** una prueba e2e que recorra **todos** los controladores: sin permiso, 403. No basta con probar uno.
- `grep -rn "Scope\.\(TRANSIENT\|REQUEST\)" v2/apps/api/src` vacío. El ámbito por petición también se contagia hacia arriba y penaliza el rendimiento. [Nest](https://docs.nestjs.com/fundamentals/injection-scopes)

**4.2 Un filtro de errores asíncrono que falla tumba el proceso · P0**
- Si un filtro de excepciones rechaza una promesa (por ejemplo, al escribir el error en el rastro), el proceso muere y la petición queda sin respuesta. El autor de Nest dice que eso no está soportado. [PR #17881](https://github.com/nestjs/nest/pull/17881)
- **Qué hacer:** `try/catch` en todo lo asíncrono de los filtros, y `process.on('unhandledRejection', …)` con log y salida ordenada (Nest no lo hace solo, issue #17758). [#17758](https://github.com/nestjs/nest/issues/17758)

**4.3 Apagado ordenado · P1**
- `app.enableShutdownHooks()` no viene activado. Sin él, un `SIGTERM` de Render corta transacciones a medias, también del rastro. [Nest](https://docs.nestjs.com/fundamentals/lifecycle-events)
- **Comprobar:** `kill -TERM <pid>` en mitad de una escritura de rastro, y luego `/api/rastro/verificar`.

**4.4 Validación de entrada · P0 en rutas que se muden**
- Con `enableImplicitConversion`, el texto `"false"` se convierte en `true` y además pasa `@IsBoolean()`. Muy peligroso en indicadores como «activo» o «solo lectura». [caso](https://github.com/pdcarlson/Frapp/issues/2612)
- Los objetos anidados no se validan sin `@ValidateNested()` y `@Type()`. [Nest](https://docs.nestjs.com/techniques/validation) · [#11892](https://github.com/nestjs/nest/issues/11892)
- **[INFERIDO]** `forbidNonWhitelisted` devuelve 400 con campos de más. Si `servir.py` hoy los ignora, cambia el contrato; usar solo `whitelist`.
- **Comprobar:** `POST {"activo":"false"}` y `?solo=false` no acaban en `true`.

**4.5 Que la nube no pueda arrancar en modo local · P0**
- **Qué pasó:** CVE-2026-43634 (HestiaCP). Confiaba en `CF-Connecting-IP` sin comprobar que la petición venía de Cloudflare, y así se saltaba listas de IPs. Express también avisa: con `trust proxy` en `true`, cualquiera falsifica `X-Forwarded-For`. [Express](https://expressjs.com/en/guide/behind-proxies) · [CVE](https://osv.dev/vulnerability/CVE-2026-43634)
- En el PR #1, el proxy reenvía las cabeceras **tal cual** (`...req.headers`), y en modo local solo comprueba que `Host` sea 127.0.0.1. Eso protege contra el «DNS rebinding», pero no contra quien llega por otra vía. **[INFERIDO]** En la nube (`HOST=0.0.0.0`), si `RO_IDENTIDAD` no fuese `access`, cualquiera mandaría `Host: 127.0.0.1` y `X-RO-Yo: dir`.
- **Qué hacer:** que Nest y `servir.py` se nieguen a arrancar si escuchan fuera de 127.0.0.1 sin `RO_IDENTIDAD=access`. En modo `access`, el proxy borra `X-RO-Yo`, `?yo=` y la galleta `ro_yo` antes de reenviar.
- **Comprobar:** `RO_IDENTIDAD=access` y `curl -H 'Host: 127.0.0.1' -H 'X-RO-Yo: dir' http://<host>/api/sesion` → 401/403.

**4.6 El JWT de Cloudflare Access, bien validado · P0 antes de la nube**
- Cloudflare dice: validar la cabecera `Cf-Access-Jwt-Assertion` (la galleta no siempre llega), comprobar la firma con las claves de `https://<equipo>.cloudflareaccess.com/cdn-cgi/access/certs` buscando por `kid` (rotan cada 6 semanas), y comprobar `iss` y `aud`. [Cloudflare](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)
- **Qué pasó:** un caso documentado en el que Access protegía el dominio propio pero no `*.pages.dev`, y la app se fiaba de la cabecera de email, que cualquiera podía falsificar por esa otra vía. [fuente](https://jamieede.com/posts/hardened-admin-auth-cloudflare-pages/)
- **Comprobar:** pruebas que firmen tokens con una clave propia: `aud` de otra aplicación, firma alterada, `alg` cambiado o token caducado → 401.

**4.7 Que no se pueda llegar sin pasar por Cloudflare · P0 antes de la nube**
- Render deja abierto `https://<servicio>.onrender.com` salvo que se desactive. La IP de origen se encuentra con Shodan o Censys. [Render](https://render.com/docs/custom-domains) · [fuente](https://tylerobrien.dev/posts/2023/05/02/securing-a-cloudflare-site/)
- **Comprobar:** abrir `https://<servicio>.onrender.com` en incógnito: no debe responder la app.

**4.8 Bajas de personal · P0**
- El JWT de Access **sigue valiendo** aunque la persona salga del proveedor de identidad, hasta que caduca (24 h por defecto). [Cloudflare](https://developers.cloudflare.com/cloudflare-one/identity/users/session-management)
- El plan ya dice «solo entra quien está activo». **Comprobar:** desactivar a alguien de prueba con su token aún vigente; la siguiente llamada da 403.

**4.9 «Ver como»: quién puede y qué puede · P0**
- **Qué pasó:** GitLab, CVE-2016-4340. La ruta para terminar la suplantación no comprobaba que quien llamaba fuera admin, y cualquiera podía entrar como cualquiera. [InfoQ](https://www.infoq.com/news/2016/05/gitlab-impersonate-vulnerability/)
- **Qué pasó:** GitLab, CVE-2021-39891. Mientras suplantaba, el admin creaba tokens que no se borraban al terminar. [fuente](https://vulert.com/vuln-db/CVE-2021-39891)
- El plan ya hace que todo lo que no es GET sea escritura y que «ver como» no escriba. **Comprobar:** con «ver como» activo, recorrer todas las rutas POST/PUT/PATCH/DELETE: todas 403 y todas con línea en el rastro. Y un puesto sin permiso de «ver como» no puede activarlo.

**4.10 «Ver como» se activa con POST, no con GET · P1**
- Un enlace o un prefetch puede cambiar de persona si la activación es GET. `SameSite=Lax` no lo evita. [caso](https://github.com/oobi/laravel-boilerplate-v2/issues/11)
- GitHub Enterprise pide además motivo obligatorio, aviso a la persona suplantada, rastro en los dos lados y sesión de 1 hora como máximo. [GitHub](https://docs.github.com/en/enterprise-server@3.18/admin/managing-accounts-and-repositories/managing-users-in-your-enterprise/impersonating-a-user)

**4.11 Respuestas recortadas: objetos planos · P0**
- `ClassSerializerInterceptor` **no** recorta objetos planos ni filas del ORM en crudo. Si se devuelve `{ user: fila }`, salen todos los campos. [Nest](https://docs.nestjs.com/techniques/serialization)
- El PR #1 tiene su propio `recortar.interceptor.ts`. **Comprobar:** una foto de las claves de cada respuesta como dos personas distintas, sin campos de más.

**4.12 Matriz completa de permisos · P0**
- OWASP A01:2025: lo que más falla es acceder a otro registro cambiando el id (IDOR), entrar por URL directa y usar verbos sin control. [OWASP](https://top10.owasp.org/2025/A01_2025-Broken_Access_Control/)
- El plan ya tiene `vectores_permisos.py`. Que incluya ids de otra cartera en GET/POST y verbos no declarados.

**4.13 Prefijo global sin barra · P2**
- En Nest 12.0.0 y 12.0.1, `setGlobalPrefix('api')` hace que las rutas inexistentes devuelvan el 404 en HTML de Express (issue #17647). El PR #1 lo usa así, pero lo que Nest no conoce va antes al proxy, así que el efecto es pequeño. Fijar Nest ≥ 12.0.2 o usar `'/api'`. [#17647](https://github.com/nestjs/nest/issues/17647)

---

## 5. Next 16

**5.1 `output: "standalone"` · P0**
- El `next.config.ts` del PR #1 lo tiene activado. Standalone **no copia** `public/` ni `.next/static`, y ahí vive `public/legacy/`, el puente de pantallas. Además, `next start` no está pensado para standalone; se arranca con `node .next/standalone/server.js`. El plan dice «`next build` + `next start`». [Next](https://nextjs.org/docs/app/api-reference/config/next-config-js/output)
- **Qué hacer:** decidir uno de los dos caminos. Si es standalone: `cp -r public .next/standalone/apps/web/ && cp -r .next/static .next/standalone/apps/web/.next/` (en un monorepo la ruta lleva el nombre de la app).
- **Comprobar:** arrancar como en la nube y pedir `/legacy/modulos/mi_dia.js` y un fichero de `/_next/static`: los dos dan 200.

**5.2 Next no decide permisos · ✅ plan**
- CVE-2025-29927 (versiones 11 a 15.2.2) permitía saltarse el middleware con la cabecera `x-middleware-subrequest`. En 2026 hubo más saltos parecidos (CVE-2026-64642 y CVE-2026-44575), todos corregidos antes de 16.3.8. La lección es siempre la misma: la autorización, en el servidor de datos. Ya es así en el plan. [Fastly](https://fastly.com/blog/cve-2025-29927-authorization-bypass-in-next-js) · [lista de CVE](https://releasealert.dev/npmjs/_/next/cves)
- **Comprobar igual:** `curl -i -H 'x-middleware-subrequest: middleware:middleware:middleware:middleware:middleware' <host>/api/sesion`, `curl -i <host>/ruta.rsc` y `curl -i -H 'RSC: 1' <host>/ruta`, sin identidad: ninguna devuelve datos.

**5.3 Datos de una persona servidos a otra · P0**
- Hay tres patrones documentados: `fetch(..., {cache: 'force-cache'})` sobre datos por persona; `unstable_cache` o `'use cache'` sobre consultas por persona; y una página que Next cree estática con los datos de alguien incrustados en el build. [fuente](https://dev.to/anas_sheikh_2/your-nextjs-page-might-be-caching-one-users-data-and-serving-it-to-everyone-else-49lj) · [Next](https://nextjs.org/docs/app/guides/self-hosting)
- **Comprobar:**
  - en la salida de `next build`, ninguna ruta con datos por persona puede salir como `○ (Static)`;
  - `grep -rn "force-cache\|unstable_cache\|use cache" v2/apps/web/src` vacío;
  - dos personas en dos navegadores a la vez;
  - `curl -I` a `/api/*`: nunca `public` ni `s-maxage`.

**5.4 Turbopack es el empaquetador por defecto · P0**
- Si hay configuración `webpack`, el build **falla**. Los `import()` de `/legacy/…` necesitan `/* webpackIgnore: true */` o `/* turbopackIgnore: true */` para que no intente resolverlos. [Next 16](https://nextjs.org/docs/app/guides/upgrading/version-16)
- **Comprobar:** en la pestaña Network, la pantalla puente pide `/legacy/modulos/x.js` tal cual.

**5.5 Tailwind 4 frente a `estilos.css` · P0 para las fotos**
- Tailwind 4 pone sus utilidades dentro de `@layer`, y **cualquier CSS sin capa gana siempre**, tenga la especificidad que tenga. `estilos.css` cargado tal cual pisará las clases de shadcn. [fuente](https://docs.makeswift.com/developer/guides/troubleshooting/tailwind-styles-being-overridden)
- Sin el *preflight* se pierden `box-sizing: border-box` y `border: 0 solid`, y `border` no pinta. [Tailwind](https://tailwindcss.com/docs/preflight)
- **Qué hacer:** si se quiere que mande RO, está bien que gane `estilos.css` (es lo que busca el plan). Si un componente de shadcn sale mal, reponer `box-sizing` y `border` solo dentro del contenedor de React.

**5.6 Una sola CSP · P1**
- La CSP del `index.html` de hoy y la de Next no pueden aplicarse a la vez a la misma respuesta. Con nonce, todo se renderiza en dinámico, y `'strict-dynamic'` bloquea los `import()` de `/legacy/` sin nonce. [Next](https://nextjs.org/docs/app/guides/content-security-policy)
- **Comprobar:** `curl -sI <host>/ | grep -i content-security` en una ruta de Next y en una del legado: una sola CSP en cada una. Consola del navegador sin violaciones.

**5.7 Variables `NEXT_PUBLIC_*` · P0**
- Se incrustan en el JS en el momento de `next build`. Si Render construye sin ellas, o con otras, el navegador se queda con el valor equivocado, y todo lo que lleve ese prefijo es público. [Next](https://nextjs.org/docs/app/guides/environment-variables)
- **Comprobar:** después de `next build`, `grep -rE "sk-|eyJ|DATABASE_URL|TOKEN|SECRET" v2/apps/web/.next/static` vacío.

**5.8 Sesión de Cloudflare caducada a media navegación · P1**
- Las peticiones RSC y los prefetch son `fetch`. Cuando Access redirige al login, el navegador da un error CORS en vez de una página. Pasa también con los `fetch` del front de hoy. [Cloudflare](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/cors/)
- **Comprobar:** borrar la galleta `CF_Authorization` con la app abierta y navegar. Debe llevar al login, no quedarse en blanco.

**5.9 Cuerpo cortado en silencio · P1 si hay subidas**
- Con un `proxy.ts` de Next, el cuerpo se guarda en memoria hasta 10 MB y lo que pasa de ahí se corta sin error. El PR #1 no tiene `proxy.ts` en Next (sí en Nest), así que hoy no aplica. [Next](https://nextjs.org/docs/app/api-reference/config/next-config-js/proxyClientMaxBodySize)

**5.10 Memoria en Render · P1**
- Una app Next 16 + Postgres en Render con 512 MB se caía cada 24 h: clientes creados en cada petición, mapas sin límite, tiempo de espera 0 en el pool y sin `--max-old-space-size`. En otro caso, conexiones `fetch` contra un backend Python que nunca se cerraban (549 abiertas). [caso 1](https://dev.to/danielrusnok/our-nextjs-app-crashed-every-24-hours-here-are-the-six-memory-fixes-2mj1) · [caso 2](https://pipeboard.co/blog/nextjs-memory-leak-investigation)
- **Comprobar:** memoria de Render a las 24 h, y `ss -tnp | grep ESTAB | wc -l` sobre el proxy al legado.

**5.11 Varias instancias · P1**
- Cada instancia tiene su propia caché. La clave de las Server Actions cambia en cada build («Failed to find Server Action») y hay desfase de versiones durante los despliegues. Con una sola instancia no aplica. [Next](https://nextjs.org/docs/app/guides/self-hosting)

**5.12 El streaming se acumula detrás de un proxy · P2**
- nginx, Caddy o un balanceador pueden juntar toda la respuesta antes de mandarla, y `loading.tsx` no se ve. Solución: `X-Accel-Buffering: no`. [Caddy](https://caddy.community/t/nextjs-streamed-rendering-not-working-behind-reverse-proxy/25026/3)

**5.13 Fechas que no coinciden al hidratar · P2**
- El servidor formatea en UTC y el navegador en Madrid. Pasar `timeZone: 'Europe/Madrid'` siempre. [fuente](https://itime.day/articles/nextjs-date-hydration-mismatch)

---

## 6. Tareas de fondo e integraciones (cuando el legado suba a la nube)

**6.1 GHL: el token de refresco es de un solo uso · P0 el día del despliegue**
- Al usarlo, el anterior deja de valer. Si dos procesos refrescan a la vez, se pierde la cadena: le pasó a Atlassian con decenas de peticiones en paralelo. El plan ya dice que el Mac no vuelva a usar la llave después de sembrarla (§2.7). [GHL](https://marketplace.gohighlevel.com/docs/Authorization/OAuth2.0/index.html) · [Atlassian](https://community.developer.atlassian.com/t/oauth-rotating-tokens-unknown-or-invalid-refresh-token/54555)
- **Qué hacer:** un solo refrescador, con candado (`pg_advisory_xact_lock` o `SELECT … FOR UPDATE`), guardar el token nuevo en la misma transacción y avisar con el primer `invalid_grant`.

**6.2 Envíos duplicados · P0 cuando se encienda**
- **Qué pasó:** en Koha, la cola de mensajes mandó correos repetidos al correr dos instancias. [Koha](https://lists.koha-community.org/pipermail/koha-bugs/2016-January/196925.html)
- ClickUp ya lleva la marca `ro:<clave>` (§2.8). **Qué hacer:** el resto de envíos, con clave única e `INSERT … ON CONFLICT DO NOTHING` *antes* de enviar, y las tareas recogidas con `FOR UPDATE SKIP LOCKED`.

**6.3 Programaciones en UTC y cambio de hora · P1**
- Los cron de Render van **siempre en UTC**: «a las 9:00» se mueve una hora dos veces al año. Red Hat tuvo cron que corrieron dos veces en el cambio de hora. [Render](https://render.com/docs/cronjobs) · [Red Hat](https://bugzilla.redhat.com/show_bug.cgi?id=138001)
- **Qué hacer:** que la tarea compruebe la hora de Madrid o guarde «última vez por fecha local». Nada programado entre las 02:00 y las 03:00.

**6.4 Google Business Profile · P1**
- Los tokens de refresco mueren a los 6 meses sin uso. Hay un máximo de 100 por cuenta, y el 101 invalida el más viejo sin avisar. En modo «testing», caducan a los 7 días. [Google](https://developers.google.com/identity/protocols/oauth2)

**6.5 Límites de cada API · P1**
- ClickUp: 100 peticiones por minuto y token. GBP: 300 por minuto y 10 ediciones por minuto y ficha. Meta: cabeceras de uso. Un limitador por cuenta, compartido por todos los procesos. [ClickUp](https://developer.clickup.com/docs/rate-limits) · [GBP](https://developers.google.com/my-business/content/limits) · [Meta](https://developers.facebook.com/docs/marketing-api/overview/rate-limiting)

**6.6 Reintentos y webhooks · P1**
- Un reintento sin clave de idempotencia duplica la acción. Los webhooks llegan repetidos y desordenados: deduplicar por id (Holded manda `x-holded-webhook-id`) y comprobar la firma. [Stripe: idempotencia](https://stripe.com/blog/idempotency) · [Holded](https://help.holded.com/en/articles/15704965-webhooks)

**6.7 Fallos callados que parecen datos · ✅ plan (§2.5)**
- **Qué pasó:** un indicador marcó 0 % durante tres meses porque fallaron 280 llamadas seguidas a la API, y nadie lo notó. Public Health England perdió casi 16.000 casos de COVID por el límite de filas de un Excel. [caso](https://dev.to/yonatan_naor_5642e43447ea/four-times-our-own-dashboards-lied-to-us-in-five-days-127) · [PHE](https://www.theregister.com/2020/10/05/test_and_trace/)
- El plan ya cubre «nunca ceros». Falta añadir: cuadrar las filas de origen con las guardadas en cada lectura y avisar si no cuadran.

---

## 7. Copias, Render y operación

**7.1 Una copia que no se ha restaurado no es una copia · P0**
- **Qué pasó:** GitLab, 31-ene-2017. Se borraron unos 300 GB por error y fallaron los cinco sistemas de copia: `pg_dump` 9.2 contra un servidor 9.6 fallaba en silencio, los correos de aviso rebotaban y no había instantáneas de disco. Se perdieron 6 horas de datos y la recuperación tardó más de 18. [GitLab](https://about.gitlab.com/blog/postmortem-of-database-outage-of-january-31/)
- **Comprobar esta noche:** `pg_dump -Fc` con cliente 16, restaurarlo en una base aparte, contar filas por tabla y pasar `/api/rastro/verificar`. Y guardar intacto el `local.db` original.

**7.2 Render: plan, región, acceso externo · P0 antes de la nube**
- La Postgres gratuita de Render caduca a los 30 días, se borra a los 14 de gracia y no tiene copias. [Render](https://render.com/docs/free)
- El PITR es de 3 días en Hobby y 7 en Pro, y restaura en **una base nueva**: hay que cambiar `DATABASE_URL`. Las copias lógicas duran 7 días. [Render](https://render.com/docs/postgresql-backups)
- La región no se puede cambiar después. Por el RGPD, todo en Frankfurt. [Render](https://render.com/docs/regions)
- El acceso externo a la base viene abierto a cualquier IP que tenga la contraseña. Cerrarlo y usar la red privada. [Render](https://render.com/docs/postgresql-creating-connecting)
- Con el disco lleno, Render suspende la base. Las lecturas de API guardadas crecen sin parar, así que poner retención (el plan dice 30 lecturas buenas y 30 días de errores) y aviso al 70 %.

**7.3 Avisos que alguien lee · P0**
- **Qué pasó:** Knight Capital (2012) perdió 460 millones de dólares en 45 minutos. El sistema mandó 97 correos de aviso antes de abrir el mercado y nadie los leyó. En GitLab, los avisos rebotaban. [SEC](https://www.sec.gov/litigation/admin/2013/34-70694.pdf)
- **Qué hacer:** seguimiento de errores (Sentry o similar) en Next, Nest y Python, con avisos a un canal que se mira, y **probarlo provocando un fallo**.

**7.4 Un identificador por petición · P1**
- `X-Request-Id` de Next a Nest y al legado, en todos los logs. Sin él, «me ha fallado a las 10:14» no se puede encontrar. [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) · [Google SRE](https://sre.google/sre-book/monitoring-distributed-systems/)

**7.5 Comprobar la versión desplegada · P1**
- Knight Capital: un técnico no copió el código nuevo a uno de los 8 servidores. **Qué hacer:** que `/vivo` devuelva el commit, y comprobarlo después de cada despliegue. [fuente](https://www.jrvarma.in/blog/Y2013/Knight-Capital.html)

---

## 8. Secretos y RGPD

**8.1 Escanear todo el historial · P0**
- **Qué pasó:** Uber, 2016. Había credenciales de AWS en un repositorio **privado** de GitHub, en una cuenta sin doble factor; con ellas se llegó a los datos de 57 millones de personas. GitGuardian calcula que el 35 % de los repositorios privados tiene secretos en claro. [The Register](https://www.theregister.com/2018/02/07/uber_quit_github_for_custom_code_after_2016_data_breach/) · [GitGuardian](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2025/)
- **Comprobar:** `gitleaks detect` sobre **todo el historial** de ro-app (no solo lo último). `escaner_secretos.py` ya revisa antes de cada commit. Rotar lo que aparezca.

**8.2 Nada de tokens ni datos personales en los logs · P0 / P1**
- **Qué pasó:** Meta recibió una multa de 91 millones de euros de la autoridad irlandesa (27-sep-2024) por contraseñas en claro en sistemas internos. Twitter, en 2018, escribió contraseñas en un log. [DPC](https://www.dataprotection.ie/en/news-media/press-releases/DPC-announces-91-million-fine-of-Meta)
- **Qué hacer:** redactar en el logger `Authorization`, `Cf-Access-Jwt-Assertion`, tokens, emails y teléfonos. No guardar en logs cuerpos completos de GHL ni de Meta.

**8.3 RGPD básico · P1**
- Firmar el contrato de encargado de Render (DPA). Fijar plazos de conservación de lecturas y logs con borrado automático. Rastro de quién vio o exportó qué cliente (ya existe). Apuntar la herramienta en el registro de actividades. [AEPD vía Cuatrecasas](https://www.cuatrecasas.com/es/spain/articulo/plazos-maximos-conservacion-datos-personales-atencion-ultimo-informe-aepd) · [RGPD art. 28](https://gdpr-text.com/es/read/article-28/)
- **Qué pasó:** la AEPD multó a CaixaBank con 1,5 millones de euros porque un cliente vio datos de otro. Es justo lo que evita la matriz de permisos. [Fieldfisher](https://www.fieldfisher.com/es-es/locations/espana/actualidad/la-insuficiencia-de-medidas-de-seguridad-en-las-empresas-objeto-de-sancion)

---

## 9. Lo que se verifica con tráfico real, no en una noche · P1

- **GitHub** cambió su código de *merge* llamando a la versión vieja y a la nueva a la vez y comparando, siempre devolviendo la vieja. Encontró fallos en los dos lados: uno del viejo contaba 768 conflictos como 0. Exigieron 24 horas al 100 % sin ninguna diferencia antes de cambiar. [GitHub](https://github.blog/engineering/move-fast/)
- **Shopify** comparó su nuevo motor de tiendas con tráfico real, fijando la hora y los valores aleatorios para que la comparación fuera exacta, y volviendo a la versión vieja ante cualquier fallo. [Shopify](https://shopify.engineering/how-shopify-reduced-storefront-response-times-rewrite)
- **[INFERIDO]** Para nosotros: en las primeras semanas, para cada GET mudado, el proxy puede pedir a los dos, devolver el del legado y apuntar las diferencias. Así salen los casos que las pruebas no cubren.

---

## 10. Seguridad general: ransomware, DDoS, doble factor, «Wordfence»

**En una frase:** el «Wordfence» de esta app no es un plugin. Son cuatro piezas, casi todas gratis:
- **Cloudflare Access** como muro: quien no ha entrado con su Google no llega ni al servidor.
- **El cortafuegos (WAF) y el límite de peticiones de Cloudflare.**
- **Escáneres del código y de sus dependencias:** Dependabot, gitleaks y Socket.
- **Avisos de errores y de caídas:** Sentry y un monitor de disponibilidad.

Coste extra aproximado: de 0 a 60 €/mes, más lo que ya se paga de Render.

### P0 · antes de subir a la nube

**10.1 Copias que ni un atacante ni un agente pueden borrar**
- **Qué pasó:**
  - **Code Spaces, 2014.** El atacante entró en la consola de AWS y borró servidores, discos y también las copias «de fuera», porque se gestionaban desde la misma cuenta y sin doble factor. La empresa cerró. [Help Net Security](https://www.helpnetsecurity.com/2014/06/19/code-hosting-code-spaces-destroyed-by-extortion-hack-attack/)
  - **PocketOS, 2026.** Un agente borró la base y las copias, que estaban en el mismo volumen. Hubo 30 horas de caída y tuvieron que volver a una copia de tres meses atrás. [Computing](https://www.computing.co.uk/news/2026/ai/ai-coding-agent-goes-rogue)
- **Qué hacer:**
  - Abrir una cuenta **aparte** de Backblaze B2 (región UE) o de AWS S3 (UE), con otro email, otra contraseña y doble factor.
  - Crear un bucket con **Object Lock en modo «compliance»**, de 30 a 35 días. En ese modo, nadie puede borrar ni sobrescribir una copia antes de que caduque, tampoco el dueño de la cuenta. En B2 no se puede desactivar una vez puesto.
  - Coste: unos 7 $/TB al mes y los primeros 10 GB gratis, así que para esta base es prácticamente cero. [AWS](https://docs.aws.amazon.com/AmazonS3/latest/dev/object-lock-overview.html) · [B2](https://www.backblaze.com/docs/cloud-storage-object-lock)
  - **No usar Cloudflare R2 como copia principal:** sus candados los puede quitar un administrador. [Cloudflare](https://developers.cloudflare.com/r2/buckets/bucket-locks/)
- **Comprobar:** intentar borrar una copia con la clave de administrador. Tiene que fallar.

**10.2 Copia diaria cifrada, con una clave que escribe pero no borra**
- Un cron de Render ejecuta `pg_dump -Fc` contra la URL interna, lo cifra con `age` y lo sube a B2. La clave de descifrado vive fuera de Render, en el gestor de contraseñas de dirección.
- La clave de subida no tiene permiso para borrar. **[INFERIDO]** Si la roban, no sirve para destruir nada.
- **Comprobar:** un aviso si un día falta el fichero nuevo.

**10.3 Regla 3-2-1-1-0 y simulacro mensual**
- Tres copias: la base viva, el PITR de Render (3 o 7 días) y B2 inmutable. Si se quiere, una más semanal en un disco desconectado de la oficina. Una de ellas inmutable, y **cero errores comprobados restaurando**. [Veeam](https://bp.veeam.com/vb365/guide/design/3-2-1)
- Cada mes: bajar la copia de B2, descifrarla, restaurarla en una base temporal, contar filas y apuntar cuánto tarda. PocketOS tenía copias, pero no servían.

**10.4 Postgres cerrada a internet**
- Por defecto, Render acepta conexiones a la base desde cualquier IP con la contraseña. Vaciar la lista de IPs permitidas (`render pg update <db> --clear-ip-allow-list`) y usar solo la URL interna. [Render](https://render.com/docs/postgresql-creating-connecting)
- **Comprobar:** `psql` desde fuera de Render falla.

**10.5 Doble factor para todo el equipo: en Google, no dentro de la app**
- La recomendación es **no programar un Google Authenticator propio** en la herramienta. Se obliga en Google Workspace y Cloudflare solo deja entrar con Google. Así, un solo sitio controla las entradas y las bajas.
- En la consola de Google: obligar la verificación en dos pasos con la opción «cualquiera salvo SMS o llamada». Para administradores y personas clave, «solo llave de seguridad» (llaves físicas o passkeys, que no se pueden robar con un phishing). [Google](https://knowledge.workspace.google.com/admin/security/deploy-2-step-verification)
- Por qué: CISA pidió doble factor resistente al phishing después del gusano Shai-Hulud de 2025. [CISA](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem)
- **Comprobar:** el informe de verificación en dos pasos de la consola marca el 100 %.

**10.6 Cloudflare Access: solo Google, sin «One-time PIN»**
- El One-time PIN es un código por email: un único factor, no doble. Si alguien entra por ahí, Access deja de mirar sus grupos de Google. Quitarlo y exigir el dominio de la empresa o un grupo concreto. [Cloudflare](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/)
- La regla de Cloudflare que «exige doble factor» (`amr`) no está documentada para el conector de Google. Con Google, la garantía es obligarlo en Workspace (10.5). [Cloudflare](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/mfa-requirements)
- Gratis hasta 50 personas.
- **Comprobar:** entrar con un Gmail personal da rechazo.

**10.7 Nadie llega sin pasar por Cloudflare**
- Es lo mismo que §4.6 y §4.7: dominio propio, el subdominio `onrender.com` desactivado, y Nest validando **la firma** del JWT en cada petición, no solo leyéndolo. Render solo permite limitar por IP en sus planes Scale y Enterprise, así que la validación del JWT es el candado de verdad. [Render](https://render.com/docs/inbound-ip-rules)
- DNS en modo «Proxied» y SSL en «Full». **Comprobar:** la respuesta lleva la cabecera `cf-ray`. [Render](https://render.com/docs/configure-cloudflare-dns)

**10.8 DDoS: ya cubierto, coste 0**
- Cloudflare incluye protección contra DDoS sin límite en todos sus planes, también el gratuito. Render también protege por debajo. [Cloudflare](https://developers.cloudflare.com/ddos-protection/) · [Render](https://render.com/docs/ddos-protection)

**10.9 Doble factor en todas las cuentas de administración**
- Render (todo el equipo), GitHub («Require two-factor authentication» y «Only allow secure two-factor methods», que excluye SMS), Cloudflare y B2/AWS. Fue el fallo de Code Spaces y de Uber. [Render](https://render.com/docs/login-settings) · [GitHub](https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-two-factor-authentication-for-your-organization/requiring-two-factor-authentication-in-your-organization)

**10.10 Mínimos permisos en Render**
- Administración solo para 1 o 2 personas, y producción marcada como «protected environment». Quien no es admin no puede borrar servicios, ver las cadenas de conexión ni abrir una consola. Ningún agente con un token de administración. [Render](https://render.com/docs/team-members)

**10.11 Dependencias envenenadas**
- **Qué pasó:**
  - **chalk/debug, 8-sep-2025.** Robaron la cuenta del mantenedor con un correo falso para «actualizar el doble factor». Esos paquetes suman más de 2.000 millones de descargas por semana.
  - **Shai-Hulud, septiembre de 2025.** Un gusano que se copiaba solo comprometió más de 500 paquetes y robaba tokens de GitHub y de la nube.
  - [Check Point](https://blog.checkpoint.com/crypto/the-great-npm-heist-september-2025/)
- **Qué hacer:** pnpm 10 o posterior (no ejecuta los scripts de instalación de las dependencias), `minimumReleaseAge` de 3 a 7 días (no instalar versiones recién publicadas), `trustPolicy: no-downgrade` y lockfile congelado. [pnpm](https://pnpm.io/supply-chain-security)

### P1 · primer mes

- **Rama principal protegida en GitHub:** exigir PR, revisión y pruebas en verde, y prohibir el force-push. En repositorios privados puede requerir el plan Team.
- **Escáneres gratis:** Dependabot, gitleaks (antes de cada commit y en CI) y Socket.dev (gratis, bloquea paquetes maliciosos). El escaneo de secretos de GitHub en repositorios privados es de pago (19 $ por persona y mes); con gitleaks y Socket no hace falta al principio. [GitHub](https://docs.github.com/en/code-security/getting-started/github-security-features) · [Socket](https://socket.dev/pricing)
- **WAF de Cloudflare:** el plan gratuito ya trae reglas contra los ataques más explotados. Pro (unos 25 $/mes) añade las reglas OWASP. Con Access delante es un refuerzo, no una necesidad. [Cloudflare](https://developers.cloudflare.com/waf/managed-rules/)
- **Límite de peticiones en dos capas:** una regla en Cloudflare y `@nestjs/throttler` en Nest, contando por persona o por `CF-Connecting-IP`. Los bloqueos tras intentos fallidos (al estilo fail2ban) no hacen falta: el login lo hacen Google y Access. [Cloudflare](https://developers.cloudflare.com/waf/rate-limiting-rules/) · [Nest](https://docs.nestjs.com/security/rate-limiting)
- **Cabeceras de seguridad:** Nest 12.1+ trae `app.useSecurityHeaders()`, equivalente a Helmet. Al activarlo, que no cambie las cabeceras que hoy manda `servir.py` (ya lo mide `seguridad_http.py`). [Nest](https://docs.nestjs.com/security/helmet)
- **Sesión de Access de 8 a 12 horas** (por defecto son 24). [Cloudflare](https://developers.cloudflare.com/cloudflare-one/access-controls/access-settings/session-management/)
- **Protocolo de bajas, escrito:**
  1. En Google: suspender, cerrar sesiones y revocar tokens y llaves.
  2. En Cloudflare: revocar la sesión de Access (en menos de un minuto queda fuera).
  3. Quitar el acceso a GitHub y Render.
  - [Google](https://knowledge.workspace.google.com/admin/users/maintain-data-security-after-an-employee-leaves)
- **Avisos:** Sentry (gratis para empezar; unos 26 $/mes con todo el equipo), un monitor de disponibilidad que entre con un token de servicio de Cloudflare, y un aviso si falta la copia diaria. [Sentry](https://sentry.io/pricing/)
- **Registros de auditoría** de Render (plan Pro) y de Access, revisados cada mes. [Render](https://render.com/docs/audit-logs)
- **Gestor de contraseñas para la empresa:** Bitwarden Teams, unos 4 $ por persona y mes. [Bitwarden](https://bitwarden.com/pricing/business/)
- **Formación contra el phishing,** sobre todo para quien administra. Según el informe Verizon DBIR 2025, las primeras vías de entrada son las credenciales robadas (22 %), las vulnerabilidades (20 %) y el phishing (16 %). [Infosecurity](https://www.infosecurity-magazine.com/news/verizon-dbir-jump-vulnerability/)

### P2 · después

- Passkeys o llaves de seguridad para todo el equipo, no solo para las personas clave.
- Comprobar el estado del ordenador antes de entrar (disco cifrado, sistema al día) con el cliente WARP de Cloudflare. [Cloudflare](https://developers.cloudflare.com/cloudflare-one/identity/devices/warp-client-checks/)
- Copia de los repositorios y del `render.yaml` en el mismo bucket inmutable.
- Si algún día hay servidor propio: Cloudflare Tunnel, para no tener ni IP pública ni puertos abiertos. [Cloudflare](https://developers.cloudflare.com/tunnel/)

**No verificado:** qué pasa con las copias de Render si se borra la base, en qué plan de Cloudflare está su doble factor propio («Independent MFA»), y los precios actuales de Render.

## 11. Checklists y reglas públicas para dar a Cursor

Fuentes oficiales y listas de referencia en GitHub. Lo que encaja con el plan, listo para dárselo a Cursor.

**11.1 Versiones fijas · P0**
- Prisma 8 ya está en versión candidata (8.0.0-rc.19) y la web de Prisma tiene una guía de 7 a 8. Si Cursor «actualiza», rompe todo. El PR #1 fija `prisma` 7.10.0 exacto, bien. **Regla para Cursor:** no cambiar ninguna versión de `package.json` ni el lockfile salvo que una puerta lo exija, y siempre `pnpm install --frozen-lockfile`.

**11.2 `AGENTS.md` oficial de Next · P0**
- Desde la 16.3, `next dev` escribe un bloque en `AGENTS.md` (`<!-- BEGIN:nextjs-agent-rules -->`) que obliga al agente a leer la documentación que viene dentro de `node_modules/next/dist/docs/`, es decir, la de la versión instalada y no la que recuerda el modelo. En un monorepo pnpm, la ruta es la de `apps/web/node_modules/next/...`. Hay que hacer commit del bloque; las reglas propias van fuera de los marcadores. [Next](https://nextjs.org/docs/app/guides/ai-agents)
- Con `next dev` en marcha, `/_next/mcp` dice si una ruta compila sin lanzar `next build`.

**11.3 Reglas oficiales de Prisma para Cursor · P0**
- `.cursor/rules/prisma.mdc` con: generador `prisma-client` y `output` explícito, URL en `prisma.config.ts`, cliente con `@prisma/adapter-pg`, revisar `package.json`, `prisma.config.*`, `schema.prisma` y los imports antes de tocar nada, y leer `https://pris.ly/llms.txt`. [Prisma](https://www.prisma.io/docs/orm/more/ai-tools/cursor) · [skills](https://github.com/prisma/skills)
- **Freno ya incluido:** la CLI de Prisma detecta cuándo la llama un agente y bloquea `migrate reset --force` salvo que exista `PRISMA_USER_CONSENT_FOR_DANGEROUS_AI_ACTION`. **Regla para Cursor:** prohibido definir esa variable. **Comprobar:** `grep -rn PRISMA_USER_CONSENT ~/.zshrc v2/ migracion/` vacío.

**11.4 Next: lista de producción y seguridad de datos (oficial) · P1**
- [Lista de producción](https://nextjs.org/docs/app/guides/production-checklist) · [Seguridad de datos](https://nextjs.org/docs/app/guides/data-security) · [OWASP Next.js](https://cheatsheetseries.owasp.org/cheatsheets/Nextjs_Security_Cheat_Sheet.html)
- Lo que aplica a las páginas en React:
  - `app/global-error.tsx`, un `error.tsx` por segmento y `not-found`;
  - no llamar a Route Handlers desde Server Components;
  - si se usan `cookies()` o `headers()` en el layout raíz, toda la app pasa a dinámica (aquí es lo que queremos);
  - nunca pasar filas enteras de Prisma a componentes de cliente;
  - `productionBrowserSourceMaps` apagado;
  - antes de entregar, `next build` y arrancar como en la nube.
- OWASP pide además un inventario de todas las entradas (rutas, rewrites, proxy), cada una marcada como pública, con identidad o webhook, y probarlas **llamándolas directamente**: sin identidad, como otra persona y con otra cartera. Es lo que ya hacen `vectores_permisos.py` y `seguridad_http.py`.

**11.5 Node: goldbergyoni/nodebestpractices (~106.000 ★) · P1**
- [Repositorio](https://github.com/goldbergyoni/nodebestpractices)
- Errores en un solo sitio (el filtro global de Nest), distinguir errores esperados de catastróficos, capturar promesas rechazadas, `return await`, no enseñar detalles del error al cliente, limitar el tamaño del cuerpo, `NODE_ENV=production`, logs a la salida estándar con id de petición, y dependencias bloqueadas.

**11.6 Pruebas: goldbergyoni/javascript-testing-best-practices (~24.600 ★) · P1**
- [Repositorio](https://github.com/goldbergyoni/javascript-testing-best-practices)
- Mejor pruebas de API contra una base real que unitarias con imitaciones (justo lo que hacen `contrato.py` y `contrato_escritura.py`). Cada prueba crea sus propios datos. Comprobar respuesta, estado de la base, mensajes, efectos y tiempos.

**11.7 Migraciones seguras: ankane/strong_migrations (4.400 ★) · P2**
- [Repositorio](https://github.com/ankane/strong_migrations). Es para Rails, pero la lista vale para cualquiera:
  - índices con `CONCURRENTLY`;
  - `UNIQUE` creando primero el índice único concurrente;
  - `NOT NULL` en tres pasos (`CHECK ... NOT VALID`, validar, y después el `NOT NULL`);
  - `jsonb` y no `json`;
  - `lock_timeout` de unos 10 s en cada migración.

**11.8 Puertas automáticas que se pueden añadir · P1 (esta noche, solo si no frenan)**
- **squawk**: revisa el SQL de las migraciones y avisa de lo que bloquea tablas (índices sin `CONCURRENTLY`, `DROP COLUMN`, restricciones sin `NOT VALID`). [squawk](https://github.com/sbdchd/squawk)
  ```
  pnpm dlx squawk-cli --pg-version=16 v2/packages/db/prisma/migrations/*/migration.sql
  ```
  **[INFERIDO]** `0_base` va a dar avisos (crea todo de cero). Usarlo para las migraciones **nuevas**. La regla de índices concurrentes choca con que Prisma mete cada migración en una transacción; excluirla o escribir esas migraciones a mano.
- **knip**: dependencias, exportaciones y ficheros sin usar en el monorepo. `pnpm dlx knip`. [knip](https://knip.dev)
- **eslint-plugin-security**: lo recomienda OWASP (`eval`, `child_process`, expresiones regulares lentas). [OWASP Node](https://cheatsheetseries.owasp.org/cheatsheets/Nodejs_Security_Cheat_Sheet.html)
- `pnpm audit --audit-level=high`.

**11.9 Lo que NO conviene copiar tal cual · P0**
- La documentación de Nest recomienda `ValidationPipe` con `forbidNonWhitelisted: true` y, en producción, `disableErrorMessages: true`. Las dos cambian lo que responde la API frente a `servir.py` (400 con campos de más, mensajes de error distintos). La regla 1 del plan manda: en las rutas mudadas, `whitelist` sí y los mensajes de error, los de hoy. [Nest](https://docs.nestjs.com/techniques/validation)
- La lista de producción de Next sugiere `revalidateTag` y caché. Aquí todo depende de quién mira: nada de caché de Next sobre datos (§5.3).

---

## Lo que no se pudo respaldar con una fuente
- Las listas de incidencias de GitHub ordenadas por reacciones (la búsqueda de GitHub no estaba disponible).
- El umbral de píxeles en las fotos: que el suavizado o las fuentes cambien entre máquinas es una deducción, sin fuente.
- Casos publicados de matrices de roles que se descontrolan, o de permisos que solo se comprobaban en la interfaz. Solo hay el principio de OWASP.
