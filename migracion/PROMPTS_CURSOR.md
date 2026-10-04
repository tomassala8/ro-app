# Prompts para Cursor · noche del 4 al 5 de octubre de 2026

Un chat de agente **nuevo** por fase. Pega el bloque tal cual. Cursor ya carga solo `AGENTS.md` y `.cursor/rules/`.
Modelo: **Claude Fable 5.1** (o **Claude Opus 5.5**), razonamiento alto, contexto grande. Ver `PLAN_MAESTRO.md` §6.

Antes de la fase 1, en la terminal de Cursor, desde la carpeta de la app:

```bash
bash migracion/preparar_noche.sh --instalar     # tiene que decir LISTO
git switch -c migracion/v2
python3 servir.py --bind 127.0.0.1 --puerto 8770   # en otra pestaña; déjalo en marcha
```

---

## Fase 1 · Inventario y referencia

```
Lee migracion/PLAN_MAESTRO.md entero. Vas a ejecutar la FASE 1. No escribas código de la app todavía.

1. Ejecuta `python3 migracion/inventario.py --comparar` y lee migracion/inventario/CAMBIOS.md y RESUMEN.md.
   Resume en migracion/NOTAS_NOCHE.md (créalo) qué pantallas, rutas, tablas, reglas de permisos y componentes son
   nuevos o han cambiado desde el 3-oct, y qué implica cada uno para las fases 2 a 6.
2. `mkdir -p ~/RO_MIGRACION && cp local.db ~/RO_MIGRACION/local.db.antes && git tag -f antes-de-migrar`
   (y si existe despliegue/estado/tuberia.db, cópiala también a ~/RO_MIGRACION/tuberia.db.antes).
3. Con servir.py en 127.0.0.1:8770:
   - `python3 migracion/contrato.py grabar --base http://127.0.0.1:8770 --salida ~/RO_MIGRACION/contrato/viejo --ver-como`
   - `python3 migracion/vectores_permisos.py --salida ~/RO_MIGRACION/vectores`
   - `cd v2/tools/capturas && node capturar.mjs --base http://127.0.0.1:8770 --modo viejo --salida ~/RO_MIGRACION/capturas/viejo`
4. Abre 5 fotos al azar de ~/RO_MIGRACION/capturas/viejo y comprueba que enseñan la pantalla con datos (no «Cargando…»).
   Si alguna sale vacía, arregla la espera en capturar.mjs y repite.
5. En escaner_secretos.py añade ".next", "dist", "generated" y "legacy" a CARPETAS_FUERA (PLAN_MAESTRO §7.6).
   Pasa `python3 escaner_secretos.py --proyecto` y commit aparte: «Escáner: no recorrer lo que genera v2».
6. Commit: «Migración · fase 1: inventario al día y notas de la noche» (solo migracion/inventario y NOTAS_NOCHE.md;
   nada de ~/RO_MIGRACION, que tiene datos reales).

Puerta: las tres grabaciones existen, las fotos tienen contenido y NOTAS_NOCHE.md lista los cambios del día.
Al acabar, escribe en NOTAS_NOCHE.md el resultado de la puerta y para.
```

## Fase 2 · Base de datos

```
Lee migracion/PLAN_MAESTRO.md (§2.3, §4 fase 2 y §7) y migracion/NOTAS_NOCHE.md. Ejecuta la FASE 2.

1. Arreglo §7.1: en despliegue/estado.py renombra la tabla «avisos» de la tubería a «tuberia_avisos» (todas sus
   consultas). Comprueba con `grep -n "avisos" despliegue/estado.py` que no queda ninguna de la tubería con el nombre
   viejo y que no tocas la «avisos» de servir.py. Commit propio.
2. `python3 migracion/inventario.py` y `bash v2/packages/db/scripts/rehacer_base.sh`
   (ADMIN_URL por defecto: la del docker-compose). Revisa el diff de schema.prisma: cada modelo nuevo o
   columna nueva tiene que estar en NOTAS_NOCHE.md. Si algo no cuadra, para y explícalo.
3. En v2/: `pnpm db:up && pnpm db:deploy`.
4. `DATABASE_URL="postgresql://127.0.0.1:5432/ro_app?user=ro&password=ro" python3 migracion/copiar_sqlite_a_pg.py --sqlite ~/RO_MIGRACION/local.db.antes`
   y, si existe, `… --sqlite ~/RO_MIGRACION/tuberia.db.antes --renombrar avisos=tuberia_avisos`.
5. `DATABASE_URL="postgresql://127.0.0.1:5432/ro_app?user=ro&password=ro" python3 despliegue/publicacion.py publicar data` y
   `… publicacion.py versiones` (tiene que haber una versión vigente de «data»).
6. Commit: «Migración · fase 2: base Postgres con Prisma».

Puerta: la copia dice «cuadrada», `pnpm --filter @ro/db exec prisma migrate status` está al día y hay versión vigente
de data. Apunta el resultado en NOTAS_NOCHE.md y para.
```

## Fase 3 · Motor de permisos

```
Lee migracion/PLAN_MAESTRO.md (§2.2 y fase 3), permisos.py, permisos.js, reglas_permisos.json y
v2/packages/permisos/src/index.ts. Ejecuta la FASE 3.

Traduce permisos.py a TypeScript en v2/packages/permisos/src, función a función y con los mismos nombres en
camelCase (carteraPorSilla, cartera, ambito, ver, contexto, recortar, nivelModulo, sinImportes, importesAQuitar,
enlaceSeguro, mirandoComo…). Reglas:
- La matriz se lee de reglas_permisos.json. No copies reglas al código.
- «Ver como»: en Python es un hilo (_HILO). Aquí, pásalo explícito (un objeto «vista» con real y su contexto),
  nunca un global: la API atiende peticiones a la vez.
- Fechas: «hoy» es el día en Europe/Madrid, como ahora_madrid()/hoy_iso().
- cargar_modulos() lee modulos/indice.js con expresiones regulares: mantén el mismo resultado (los vectores traen
  modulos.json para comparar).
Completa test/paridad.test.ts para comparar, con los vectores de ~/RO_MIGRACION/vectores: ver y ver_como de cada
pregunta, nivel de cada módulo, cartera, ámbito y el recorte de cada persona (recortes/<id>.json). Cualquier
diferencia es un fallo.

Puerta: `RO_VECTORES=~/RO_MIGRACION/vectores pnpm --filter @ro/permisos test` con el 100 % en verde.
No sigas a la fase 4 sin esto. Commit «Migración · fase 3: motor de permisos en TypeScript con paridad 100 %».
```

## Fase 4 · API en Nest

```
Lee migracion/PLAN_MAESTRO.md (§2.2 entero y fase 4), migracion/inventario/rutas_api.json, enchufes.json y
rutas_front.json, y servir.py. Ejecuta la FASE 4 en v2/apps/api.

Crea un módulo de Nest por fila de la tabla §2.2, en este orden: identidad (guarda global) → sesion → datos →
clientes → rastro → acciones → el resto de lectura → el resto de escritura → los enchufes (ia, avisos, envíos,
sincronía, altas, gbp, modular, vigía). Para cada ruta, abre su código en Python y reprodúcelo exactamente:
mismos códigos, mismos mensajes de error, mismas claves JSON, mismo recorte, mismo rastro. Usa @ro/permisos para
todo lo que sea permiso y PrismaService para la base (SQL crudo con $queryRaw solo si Prisma no llega).
Los bucles en hilo de los enchufes NO van a la API (§2.2, último punto).
Datos de módulos: léelos de datos_version/datos_fichero/datos_blob (espacio «data», versión vigente, zlib), con
caché en memoria por versión y comprobación cada minuto, como hace hoy la web en Render.

Ve comprobando por partes: arranca la API (pnpm --filter @ro/api dev) y la web (pnpm --filter @ro/web dev, puerto
3000), graba el contrato nuevo y compara:
  python3 migracion/contrato.py grabar --base http://127.0.0.1:3000 --salida ~/RO_MIGRACION/contrato/nuevo --ver-como
  python3 migracion/contrato.py comparar ~/RO_MIGRACION/contrato/viejo ~/RO_MIGRACION/contrato/nuevo
Antes de cada grabación, restaura la base nueva desde ~/RO_MIGRACION/local.db.antes (copiar_sqlite_a_pg.py --vaciar)
para que las dos partan del mismo estado.

Puerta: comparar → 0 diferencias; `python3 pruebas_e0.py --puerto 3000` verde; pruebas_seguridad.py verde contra
la API nueva (adáptala para que arranque v2 en vez de servir.py con una variable de entorno, sin quitar ninguna
comprobación). Commit por módulo. Apunta en NOTAS_NOCHE.md cada diferencia que hayas tenido que resolver.
```

## Fase 5 · Carcasa, ctx y puente

```
Lee migracion/PLAN_MAESTRO.md (§2.4 y fase 5), index.html, app.js, carcasa.js, ayudas.js, datos.js y
componentes.js. Lee también v2/apps/web/AGENTS.md: esta versión de Next tiene cambios; consulta
node_modules/next/dist/docs/ antes de escribir rutas o layouts. Ejecuta la FASE 5 en v2/apps/web.

1. `pnpm dlx shadcn@latest init` (sin tocar src/styles/ro-tema.css ni el globals.css sin preflight; si el init los
   cambia, déjalos como estaban) y añade las piezas que use la carcasa (sidebar, command, dropdown-menu, dialog,
   sheet, tooltip).
2. src/lib/ctx.ts: crearCtx de app.js en TypeScript, los 40 campos (lista en migracion/inventario/ctx.json), con el
   mismo comportamiento (memoria con ETag de datosModulo, X-RO-App en POST, fechas de Madrid…).
3. La carcasa en React con LAS MISMAS clases de estilos.css y el mismo DOM que pinta hoy app.js + carcasa.js: menú por
   puesto (sesion.modulos_puestos), cabecera, buscador ⌘K y «/», «ver como» (solo lectura), menú móvil, «¿Quién eres?»
   en local. Identidad local con ?yo= y galleta ro_yo, como hoy.
4. Rutas: /[pantalla]/[[...params]]. /#/x redirige a /x.
5. <PantallaPuente fichero="…"/>: importa /legacy/modulos/<fichero> en el navegador y llama a render(contenedor, ctx).
   Úsalo para las 37 pantallas.
6. Fotos: node v2/tools/capturas/capturar.mjs --base http://127.0.0.1:3000 --modo nuevo --salida ~/RO_MIGRACION/capturas/nuevo
   y node v2/tools/capturas/comparar.mjs ~/RO_MIGRACION/capturas/viejo ~/RO_MIGRACION/capturas/nuevo
   Mira las imágenes de _diferencias/ de las peores y corrige hasta que todas queden ≤ 0,5 %.

Puerta: todas las pantallas ≤ 0,5 %, _errores.json vacío, contrato sigue en 0 diferencias. Commit
«Migración · fase 5: carcasa en React y todas las pantallas por el puente». Apunta el resultado en NOTAS_NOCHE.md.
```

## Fase 6 · Pantallas en React + shadcn (repetir hasta que se acabe la noche)

```
Lee migracion/PLAN_MAESTRO.md (§2.4 y fase 6) y migracion/NOTAS_NOCHE.md. Ejecuta la FASE 6.

Primero, si no existe: v2/apps/web/src/components/ro/ con los componentes de componentes.js en React (mismas
clases, mismo DOM, mismos textos; usa shadcn solo donde la pieza sea equivalente: diálogo, menú, pestañas, ⌘K,
tooltip). Luego, una pantalla cada vez, en el orden del plan:
1. Rehaz la pantalla en React a partir de su módulo en modulos/.
2. Fotos solo de esa pantalla (--pantallas <id>) para todas las personas y los dos tamaños, y compara.
3. Si queda ≤ 0,5 % y el contrato y las pruebas siguen verdes: sustituye al puente y commit
   «Migración · pantalla <id> en React». Si tras dos intentos no queda igual: deja el puente, apunta por qué en
   NOTAS_NOCHE.md y pasa a la siguiente.
Nunca dejes una pantalla a medias sustituyendo al puente.
```

## Fase 7 · Listo para la nube

```
Lee migracion/PLAN_MAESTRO.md (fase 7 y §7), despliegue/DESPLIEGUE.md, despliegue/render.yaml y
v2/docker-compose.yml. Ejecuta la FASE 7.

1. `cd v2 && docker compose --profile completo up --build -d`. Repite contrato y fotos contra http://127.0.0.1:3000.
2. Prepara el worker: la imagen de despliegue/Dockerfile con DATABASE_URL de la base nueva; comprueba en local una
   vuelta «ligera» de la tubería (`docker compose run`) que publica una versión nueva de data y que la API la sirve.
3. Escribe v2/render.yaml a partir de despliegue/render.yaml: ro-web, ro-api, ro-worker (las tareas ligera/completa/
   noche y los bucles), ro-base. Sin llaves en el fichero. Cloudflare Access delante como en DESPLIEGUE.md.
4. Escribe migracion/INFORME_NOCHE.md para Tomás, en castellano y frases cortas: puertas pasadas, pantallas en React
   y pantallas en el puente (con el motivo), diferencias que quedan, y los pasos exactos de la mañana.
5. Commit, `git push -u origin migracion/v2` y abre el PR a main.

Puerta: todo verde contra los contenedores e INFORME_NOCHE.md escrito.
```
