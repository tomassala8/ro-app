# Plan maestro · la app de RO a Next + Nest + Postgres

**4-oct-2026.** Para ejecutar con Cursor la noche del 4 al 5 de octubre. Objetivo: que el 5 por la mañana la app se pueda desplegar en la nube con **la misma cara, las mismas funciones y los mismos permisos**, sobre una base que escale.

Stack de destino: **Next.js 16** (web) · **NestJS 12** (API) · **PostgreSQL 16 + Prisma 7** (base) · **shadcn/ui + Tailwind 4** (interfaz). Monorepo con **pnpm** en `v2/`.

---

## 0. Las cinco reglas que mandan sobre todo lo demás

1. **Nada cambia para quien usa la app.** Mismas pantallas, mismos textos, mismos colores, mismas rutas de API, mismas respuestas, mismos 403. Si algo se ve o responde distinto, es un fallo, no una mejora.
2. **Se demuestra, no se supone.** Cada fase acaba en una **puerta** con una orden que sale en verde. Sin verde no se pasa de fase.
3. **La mañana nunca se rompe.** Toda pantalla tiene una red: si su versión en React no queda idéntica, se queda con su código de hoy dentro de la carcasa nueva («puente»). Así el 100 % de las funciones está disponible aunque no dé tiempo a rehacerlo todo.
4. **Los datos reales no salen del Mac.** Grabaciones, vectores y fotos van a `~/RO_MIGRACION/`, nunca al repositorio ni a un chat.
5. **Lo de hoy no se toca.** La app vieja (raíz del repo) sigue funcionando igual hasta que Tomás diga. Todo lo nuevo vive en `v2/` y en `migracion/`. Única excepción: los arreglos de la sección 7, y cada uno en su commit.

---

## 1. Qué hay hoy (inventario a 3-oct)

Lo genera `python3 migracion/inventario.py` en `migracion/inventario/` (ver `RESUMEN.md`). Cifras de la versión del 3-oct:

| Pieza | Hoy | Cuánto |
|---|---|---|
| Pantallas | `modulos/*.js` (JS sin framework, `render(contenedor, ctx)`) | 37 en el menú, 61 ficheros, ~36.000 líneas de front |
| Carcasa | `index.html`, `app.js`, `carcasa.js`, `ayudas.js` (⌘K) | menú por puesto, «ver como», buscador |
| Sistema de diseño | `estilos.css` (tokens) + `componentes.js` | 107 componentes |
| Servidor | `servir.py` (Python, sin framework) | 37 rutas propias + 62 de 11 ficheros «enchufados» (ia, avisos, envíos, sincronía, vigía, altas, GBP, Modular…) |
| Permisos | `reglas_permisos.json` + `permisos.py` (servidor) + `permisos.js` (navegador) | 21 puestos, 39 tipos de dato, 92 ficheros de datos con permiso, 9 almacenes privados, 133 acciones |
| Base | SQLite `local.db` (en la nube, Postgres vía `despliegue/base.py`) | 40 tablas, rastro imborrable con disparadores y huellas encadenadas |
| Datos | `fuentes_*/generar_*.py` → `data/*.json` (la «tubería») | 50 pasos, 86 generadores, 27 lectores en `~/RO_HERRAMIENTAS` (fuera del repo) |
| Pruebas | `pruebas_*.py`, `despliegue/pruebas_noche.py` | 16 baterías |

**La app está viva y cambia hoy.** Por eso la fase 1 rehace el inventario y saca la lista de lo que ha cambiado (`--comparar`) antes de migrar nada.

---

## 2. La arquitectura nueva

```
v2/
├── apps/web          Next 16 (App Router) + Tailwind 4 + shadcn. La carcasa y las pantallas en React.
│   ├── src/app/[pantalla]/…    una ruta por pantalla (/mi-dia, /en-rojo…); #/mi-dia redirige a /mi-dia
│   ├── src/lib/ctx.ts          el MISMO ctx que hoy (40 campos), en TypeScript
│   ├── src/components/ro/      componentes.js rehechos en React (mismas clases y tokens)
│   ├── src/components/ui/      shadcn (con el tema de RO: src/styles/ro-tema.css)
│   └── public/legacy/          copia automática del front de hoy (el puente). No se edita.
├── apps/api          Nest 12. Un módulo por dominio. MISMAS rutas y respuestas que servir.py.
├── packages/db       Prisma 7: schema.prisma (40 modelos) + migraciones. Sacado de la base real, no escrito a mano.
├── packages/permisos El motor de permisos en TypeScript. Lo usan la API y la web. La matriz sigue en reglas_permisos.json.
├── tools/capturas    Fotos de cada pantalla (vieja y nueva) y comparación píxel a píxel.
└── docker-compose.yml  Postgres local (y, con --profile completo, api + web como en la nube).
```

**Cómo viaja una petición:** navegador → Next (`/api/*` reescrito) → Nest → Postgres. El navegador solo ve una dirección, como hoy.

**Los datos de los módulos** (`data/*.json`) siguen saliendo de la tubería en Python. Ya hoy `despliegue/publicacion.py` los publica en Postgres por versiones (`datos_version`, `datos_fichero`, `datos_blob` con zlib). Nest los lee de ahí, los recorta por persona con `@ro/permisos` y los sirve en `/api/modulo/<carpeta>/<fichero>`. **La tubería no se reescribe esta noche** (ver 2.1).

### 2.1 Una decisión tomada por defecto: la tubería se queda en Python esta noche

Los 86 generadores y 27 lectores hablan con ClickUp, GoHighLevel (con una llave que rota en cada uso), Meta, Zoho, Holded, Google… Reescribirlos en una noche arriesga romper integraciones reales, y no cambian nada de lo que se ve. Así que:

- **Web, API, base, accesos y permisos:** al stack nuevo esta noche (100 %).
- **Tubería, avisos, envíos, sincronía y vigía (lo que corre en segundo plano):** siguen en Python, en un contenedor «worker» aparte, contra la **misma** Postgres. Se pasan a Nest después, uno a uno, con la misma red de pruebas.

### 2.2 Backend: módulos de Nest

Cada módulo es dueño de sus rutas, su servicio y sus tablas. Nadie lee tablas de otro módulo: pide al servicio.

| Módulo Nest | Rutas (idénticas a hoy) | Viene de |
|---|---|---|
| `identidad` (guarda global) | todas | `servir.py › _quien`, `despliegue/acceso_cf.py` |
| `permisos` | — (servicio) | `@ro/permisos` |
| `sesion` | `GET /api/sesion`, `GET /api/elegir` | `servir.py` |
| `datos` | `GET /api/modulo/**`, `GET /data/<carpeta>/<fichero>.json` | `servir.py`, `despliegue/publicacion.py` |
| `clientes` | `GET /api/cliente/:id`, `GET /logos/:id` | `servir.py` |
| `buscar` | `GET /api/buscar`, `/api/buscar/indice`, `/api/contadores` | `servir.py` |
| `indicadores` | `GET /api/indicadores` | `servir.py` |
| `rastro` | `GET/POST /api/rastro`, `GET /api/rastro/verificar` | `servir.py` (+ `registro_huellas`) |
| `acciones` | `GET/POST /api/acciones` | `servir.py`, `envios.py`, `sincronia.py`, `fuentes_alertas/guardia_alertas.py` |
| `ver-dato` | `POST /api/ver_dato` | `servir.py` |
| `decisiones` | `GET/POST /api/decisiones`, `GET /api/respuestas_mili` | `servir.py` |
| `ajustes` | `GET /api/ajustes`, `POST /api/ajustes/*` | `servir.py` |
| `altas` | `/api/altas/*` | `altas_personas.py` |
| `avisos` | `GET /api/avisos`, `POST /api/avisos/visto`, `/api/canales/*`, `/api/avisos_programados/*` | `servir.py`, `avisos.py`, `avisos_programados.py` |
| `perfil` | `GET /api/perfil`, `POST /api/perfil/zona`, `GET/POST /api/preferencias` | `servir.py` |
| `opiniones` | `GET /api/opiniones`, `/captura`, `POST /api/opinion`, `/api/opiniones/estado` | `servir.py` |
| `recarga` | `GET/POST /api/recarga` | `servir.py` (lanza la tubería: en la nube, encola para el worker) |
| `envios`, `sincronia` | `/api/envios/*`, `/api/sincronia/*` | `envios.py`, `sincronia.py` |
| `ia` | `/api/ia/*` | `ia.py`, `ia_gasto.py` |
| `gbp`, `modular`, `vigia` | `/api/gbp/*`, `/api/modular/acceso`, `/api/vigia/*` | `fuentes_gbp/servidor_gbp.py`, `fuentes_modular/acceso.py`, `despliegue/vigia.py` |
| `salud` | `GET /vivo`, `GET /api/salud` | `servir.py` |

Reglas del backend:
- **Mismo contrato.** Mismo método, ruta, códigos (200/401/403/404/503), cabeceras que importan (`ETag`, `Cache-Control`, `X-RO-App` obligatoria en POST) y el **mismo JSON**, con las mismas claves en `snake_case`. Las fechas salen como hoy (texto `AAAA-MM-DD HH:MM:SS` en UTC).
- **Identidad.** `RO_IDENTIDAD=local`: `X-RO-Yo` / `?yo=` / galleta `ro_yo`, solo escuchando en 127.0.0.1. `RO_IDENTIDAD=access`: solo el sello firmado de Cloudflare Access (`Cf-Access-Jwt-Assertion`, comprobado contra las llaves del equipo `RO_CF_EQUIPO` y la audiencia `RO_CF_AUD`), como `despliegue/acceso_cf.py`. Solo entra quien está `activo`.
- **«Ver como»:** solo lectura, mínimo de las dos personas, y lo leído queda en el rastro (como `apuntar_lectura_ver_como`).
- **Rastro imborrable:** lo hace la base (disparadores ya incluidos en la migración `0_base`) y la cadena de huellas (`registro_huellas`) se calcula igual que hoy.
- **Puerta de secretos:** si `escaner_secretos.py` marca algo en los datos comunes, la API responde 503, como hoy.
- **Validación** con DTOs (`class-validator`) de lo que hoy valida `servir.py`, sin aceptar más ni menos.
- **Bucles en segundo plano:** nada de hilos dentro de la API (en la nube puede haber varias copias y se duplicarían). Los cinco bucles de hoy (avisos, avisos programados, envíos, sincronía, vigía) corren en el worker.

### 2.3 Base de datos

- `packages/db/prisma/schema.prisma` **no se escribe a mano**: sale de crear en Postgres las tablas que usa hoy la app (`migracion/crear_base_pg.py`) y leerlas con `prisma db pull`. Lo hace `v2/packages/db/scripts/rehacer_base.sh`. Así no se escapa ninguna columna.
- La migración `0_base` incluye lo que Prisma no sabe expresar: `CHECK`, la vista `v_cartera_hoy` y los disparadores (rastro, historial, acciones, recargas imborrables; «de una acción solo avanza el estado»; «una decisión se contesta una vez»…). Comprobado el 4-oct en un Postgres 16 real: 95 sentencias sin error y `prisma migrate diff` vacío.
- Esta noche los tipos se quedan **como hoy** (fechas en texto, enteros 0/1) porque el worker en Python escribe en las mismas tablas. Pasar a `timestamptz`, `boolean` y `jsonb` es una migración posterior, cuando el worker esté en Nest.
- Los datos se copian de `local.db` con `migracion/copiar_sqlite_a_pg.py` (cuadra filas tabla a tabla) y los ficheros de `data/` con `DATABASE_URL=… python3 despliegue/publicacion.py publicar data`.

### 2.4 Frontend

- **Carcasa en React + shadcn** (menú lateral marino, cabecera, buscador ⌘K, «ver como», menú móvil) con **las mismas clases de `estilos.css`**, que se sigue cargando tal cual (`/legacy/estilos.css`). Tailwind entra sin «preflight» para no cambiar la base. El tema de shadcn apunta a los tokens de RO (`src/styles/ro-tema.css`).
- **`ctx` en TypeScript** (`src/lib/ctx.ts`): los 40 campos de `crearCtx` de `app.js`, con el mismo comportamiento (memoria por persona con ETag en `datosModulo`, fechas de Madrid, `api()` con `X-RO-App: 1`, `accion()`, `verDato()`, `rastro()`…). Es lo que reciben tanto las pantallas React (por contexto) como las del puente.
- **El puente** (`<PantallaPuente fichero="mi_dia.js" />`): importa en el navegador el módulo de hoy desde `/legacy/modulos/` y llama a `render(contenedor, ctx)`. Con esto, la mañana del 5 todas las pantallas funcionan aunque no se haya rehecho ninguna.
- **Pantallas en React:** se rehacen una a una con componentes de `src/components/ro/` (que son `componentes.js` en React, mismas clases) y piezas de shadcn donde encajen (diálogos, menús, pestañas, tablas, ⌘K). Una pantalla rehecha **solo** sustituye al puente si sus fotos salen iguales (≤ 0,5 % de píxeles distintos) para todas las personas, en escritorio y móvil, y sus pruebas siguen verdes.
- Rutas: `/mi-dia`, `/en-rojo/gac`… (lo de después del id son los `params` de hoy). `/#/x` redirige a `/x` para que no se rompa ningún enlace guardado.
- Sin Google Fonts (regla de la ronda 14): Montserrat y Geist Mono se sirven desde la app. Claro siempre, nunca modo oscuro.

---

## 3. Las redes de seguridad (ya hechas y probadas el 4-oct)

| Herramienta | Qué demuestra | Orden |
|---|---|---|
| `migracion/inventario.py` | que no se olvida ninguna pantalla, ruta, tabla, regla o componente, y qué ha cambiado hoy | `python3 migracion/inventario.py --comparar` |
| `migracion/contrato.py` | que la API nueva responde **lo mismo** que la vieja a cada persona en cada ruta (incluidos los 403 y «ver como») | `grabar` en las dos y `comparar` |
| `migracion/vectores_permisos.py` | que el motor de permisos nuevo da **las mismas** respuestas que `permisos.py` a cada pregunta | genera vectores; `RO_VECTORES=… pnpm --filter @ro/permisos test` |
| `v2/tools/capturas` | que cada pantalla se **ve igual**, píxel a píxel, por persona, en escritorio y móvil | `capturar.mjs` en las dos y `comparar.mjs` |
| Baterías de hoy (`pruebas_e0.py`, `pruebas_seguridad.py`, `pruebas_coherencia.py`…) | que la seguridad y la coherencia siguen | se lanzan contra la app nueva (`--puerto 3000`) |
| `migracion/crear_base_pg.py` + `rehacer_base.sh` | que la base nueva tiene todas las tablas y protecciones | ver 2.3 |
| `migracion/copiar_sqlite_a_pg.py` | que no se pierde ni una fila al pasar a Postgres | cuadra filas tabla a tabla |

Ensayo del 4-oct (en la nube de Claude, con datos inventados): grabar dos veces la misma app da 0 diferencias de contrato y 0,00 % de píxeles distintos. Es decir: lo que marquen esta noche es una diferencia de verdad, no ruido.

---

## 4. Las fases de la noche

Cada fase: qué se hace, quién, y la **puerta** (la orden que tiene que salir en verde). Las órdenes, completas, en `migracion/PROMPTS_CURSOR.md`.

### Fase 0 · Por la tarde (Tomás) · Dejar el Mac listo
1. Terminar lo de hoy y hacer commit y push en `main`.
2. `bash migracion/preparar_noche.sh --instalar` hasta que diga **LISTO**.
3. Abrir la carpeta de la app en Cursor y elegir el modelo (sección 6).
4. `git switch -c migracion/v2` y pegar el prompt de la fase 1.

**Puerta:** `preparar_noche.sh` dice LISTO.

### Fase 1 · Inventario y referencia (Cursor)
1. `python3 migracion/inventario.py --comparar` → `migracion/inventario/CAMBIOS.md`. Todo lo nuevo de hoy entra en el plan (pantallas, rutas, tablas, reglas).
2. Copia de seguridad: `cp local.db ~/RO_MIGRACION/local.db.antes` y etiqueta `git tag antes-de-migrar`.
3. Con `servir.py` en 8770: `contrato.py grabar --ver-como` (→ `~/RO_MIGRACION/contrato/viejo`), `vectores_permisos.py`, y `capturar.mjs --modo viejo`.

**Puerta:** existen las tres grabaciones y `CAMBIOS.md` está revisado.

### Fase 2 · Base de datos
1. Si `CAMBIOS.md` trae tablas nuevas o cambiadas: `bash v2/packages/db/scripts/rehacer_base.sh`.
2. `pnpm db:up && pnpm db:deploy` (en `v2/`).
3. `copiar_sqlite_a_pg.py --sqlite ~/RO_MIGRACION/local.db.antes` y la base del estado de la tubería.
4. `DATABASE_URL=… python3 despliegue/publicacion.py publicar data`.

**Puerta:** la copia sale «cuadrada», `pnpm --filter @ro/db exec prisma migrate status` dice que está al día y `publicacion.py versiones` enseña una versión vigente de `data`.

### Fase 3 · Motor de permisos (`@ro/permisos`)
Traducir `permisos.py` función a función (mismos nombres), con «ver como» incluido, `recortar`, `nivel_modulo`, `sin_importes`…

**Puerta:** `RO_VECTORES=~/RO_MIGRACION/vectores pnpm --filter @ro/permisos test` con **100 %** de coincidencias (cada persona, tipo, cliente y persona objetivo; y los recortes).

### Fase 4 · API (Nest)
Módulos de la tabla 2.2, en este orden: identidad → sesion → datos → clientes → rastro → acciones → resto de lectura → resto de escritura → enchufes.

**Puerta:**
- `contrato.py grabar --base http://127.0.0.1:3000 … nuevo` + `comparar viejo nuevo` → **0 diferencias**.
- `python3 pruebas_e0.py --puerto 3000` verde.
- `pruebas_seguridad.py` contra la API nueva verde (adaptarla para que arranque `v2` en vez de `servir.py`, sin quitar ni una comprobación).

### Fase 5 · Carcasa, ctx y puente
Carcasa React + shadcn, `ctx.ts`, `PantallaPuente` para las 37 pantallas.

**Puerta:** `capturar.mjs --modo nuevo` + `comparar.mjs` con todas las pantallas ≤ 0,5 % y sin errores de página. **En este punto la app nueva ya está completa** y se puede desplegar.

### Fase 6 · Pantallas en React + shadcn (todo el tiempo que quede)
Orden: piezas comunes (`componentes.js` → `src/components/ro/`), luego pantallas de menos a más riesgo: Mi perfil, Catálogo de indicadores, Decisiones y rastro, En rojo, Agenda… y al final Mi día, Ficha del cliente, Captación, Bandeja, Panel de dirección y Finanzas.

**Puerta, por pantalla:** fotos ≤ 0,5 % para todas las personas y tamaños + contrato y pruebas verdes. Si no, se deja en el puente y se apunta en el informe. Una pantalla a medias **nunca** sustituye al puente.

### Fase 7 · Listo para la nube
1. `docker compose --profile completo up --build` en el Mac y repetir contrato y fotos contra esa versión.
2. Worker: la imagen de hoy (`despliegue/Dockerfile`) con `DATABASE_URL` de la base nueva, para la tubería y los cinco bucles.
3. Blueprint de la nube (`v2/render.yaml`, a partir de `despliegue/render.yaml`): `ro-web` (Next), `ro-api` (Nest), `ro-worker` (Python), `ro-base` (Postgres). Cloudflare Access delante, igual que en `despliegue/DESPLIEGUE.md`.
4. Escribir `migracion/INFORME_NOCHE.md`: qué puertas pasaron, qué pantallas quedaron en el puente y por qué, y los pasos de la mañana.

**Puerta:** todo lo anterior en verde contra los contenedores y el informe escrito. Commit y push de la rama `migracion/v2`, y PR a `main` para que lo revise Tomás.

### La mañana del 5 (Tomás)
Leer `INFORME_NOCHE.md`, revisar el PR y seguir `despliegue/DESPLIEGUE.md` con los servicios nuevos. Hasta el «sí» de Tomás, la app vieja sigue siendo la buena.

---

## 5. Si algo se tuerce

| Si… | Entonces |
|---|---|
| El motor de permisos no llega al 100 % | No se sigue con la API. Es la pieza que no admite «casi». |
| Una ruta del contrato no cuadra y no se ve por qué | Se deja en el informe con la diferencia exacta y se sigue con las demás. La puerta de la fase 4 no se da por pasada. |
| Una pantalla en React no queda igual | Se queda en el puente. No se insiste más de dos vueltas. |
| No da tiempo a la fase 6 | No pasa nada: tras la fase 5 la app nueva ya tiene todo. La fase 6 sigue otro día. |
| Algo rompe la app vieja | `git switch main` y `cp ~/RO_MIGRACION/local.db.antes local.db`. |

---

## 6. Con qué modelo de Cursor

**Recomendado: Claude Fable 5.1**, si tu Cursor lo ofrece. Es el más capaz de Anthropic para trabajos largos y autónomos de programación, que es justo esto: muchas horas, mucho código y puertas que exigen exactitud. Úsalo con la ventana de contexto grande (modo «Max») y razonamiento alto.

**Alternativa: Claude Opus 5.5.** Muy fuerte y más barato. Buena opción si Fable 5.1 no aparece o si el gasto preocupa.

No uses modelos «rápidos» ni el modo automático para las fases 3 y 4: ahí un detalle mal traducido abre un agujero de permisos.

No he podido comprobar desde aquí qué modelos tiene tu Cursor. Si no ves ninguno de los dos, elige el Claude más reciente de la lista.

Cómo trabajar con él:
- Un chat de agente por fase, empezando con el prompt de `PROMPTS_CURSOR.md`. Al acabar una fase, un chat nuevo: el contexto limpio trabaja mejor.
- Las reglas de `.cursor/rules/` se cargan solas. `AGENTS.md` (raíz) le da el mapa.
- Deja que ejecute las órdenes (terminal) sin pedir permiso para cada una, salvo `git push`.

---

## 7. Cosas encontradas al preparar el plan (4-oct)

1. **La tabla `avisos` está dos veces con columnas distintas:** `schema_v2.sql` (avisos a Tomás) y `despliegue/estado.py` (avisos de la tubería). En local viven en ficheros distintos; en una sola Postgres chocan. Arreglo propuesto: renombrar la de la tubería a `tuberia_avisos` en `despliegue/estado.py`.
2. **`despliegue/base.py` no traduce 4 disparadores con condición** (`acciones_solo_estado`, `decisiones_una_respuesta`, `opiniones_solo_estado`, `altas_tareas_solo_estado`). En la Postgres de Render, esas protecciones faltarían. La base nueva ya las trae (migración `0_base`); conviene arreglar también `base.py` por si la app vieja se despliega antes.
3. **Cinco ficheros arrancan un bucle propio dentro del servidor** (avisos, avisos programados, envíos, sincronía, vigía). Con más de una copia del servidor en la nube se duplicarían. En la arquitectura nueva van al worker.
4. **Las rutas están repartidas en 12 ficheros** (`servir.py` y 11 «enchufes»). El inventario ya los recoge todos.
5. **La tubería depende de `~/RO_HERRAMIENTAS`** (27 lectores fuera del repo). El worker los necesita en su imagen, como ya hace `despliegue/preparar_contexto.sh`.
6. **El escáner de secretos (`escaner_secretos.py --proyecto`) recorre también lo que genera v2** (`.next`, `dist`, `src/generated`, `public/legacy`) y da falsos positivos. Arreglo: añadir esas carpetas a `CARPETAS_FUERA`, en su propio commit (fase 1).

---

## 8. Después de la noche (para que escale)

- Pasar la matriz de permisos de `reglas_permisos.json` a tablas (`puestos`, `reglas`, `permisos_por_puesto`) con pantalla de edición en Ajustes y su propio rastro. El motor ya estará en un solo sitio (`@ro/permisos`), así que es cambiar de dónde lee.
- Tipos de verdad en la base (`timestamptz`, `boolean`, `jsonb`) cuando el worker deje de escribir en texto.
- Pasar la tubería y los bucles a Nest (`@nestjs/schedule` y una cola), uno a uno, con el contrato como red.
- Pruebas de extremo a extremo con Playwright por puesto, en cada PR.
