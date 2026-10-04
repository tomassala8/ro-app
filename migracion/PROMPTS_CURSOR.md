# Detalle de cada paso · noche del 4 al 5 de octubre de 2026

**El prompt que se pega (o que lanza `noche.sh`) es `migracion/PROMPT_NOCHE.md`.** Este fichero es el detalle de cada paso de `migracion/PROGRESO.md`: el agente lee la sección del paso que le toca.

Convenciones para todos los pasos:
- `FUERA` = `~/RO_MIGRACION` (datos reales; nunca al repo). Puertos: 8770 app de hoy sobre copia SQLite · 8771 legado (app de hoy sobre Postgres `ro_app`) · 4000 Nest · 3000 Next · 5432 Postgres.
- Arrancar y parar: `bash migracion/servicios.sh arrancar|parar|estado [viejo|legado|api|web|todo]`.
- Cerrar: `bash migracion/puerta.sh <fase>` en VERDE (el informe queda en `FUERA/puertas/<fase>.md`). `--rapido` sirve para iterar, no para cerrar.
- Commits pequeños, mensaje que empieza por el código del paso: «F2.4 · base.py: …».

---

## F1.1 · Inventario y notas

```bash
python3 migracion/inventario.py --comparar
```
Lee `migracion/inventario/CAMBIOS.md` y `RESUMEN.md`. Crea `migracion/NOTAS_NOCHE.md` con: qué pantallas, rutas (también de enchufes), tablas, columnas, reglas de permisos y componentes son nuevos o cambian respecto a lo que hay en GitHub, y qué implica cada uno para las fases 2 a 6. Lee también `migracion/NOTA_ASTRA.md`: sus «mejoras locales recientes» tienen que aparecer en el inventario; si alguna no aparece, apúntalo. Añade al final las secciones «Preguntas para Tomás» y «Bloqueos para el piloto» (vacías).

## F1.2 · Escáner de secretos

En `escaner_secretos.py`, añade `".next"`, `"dist"`, `"generated"` y `"legacy"` a `CARPETAS_FUERA`. Pasa `python3 escaner_secretos.py --proyecto`: lo que quede marcado fuera de esas carpetas se apunta en NOTAS_NOCHE.md (hay un falso positivo conocido en `pruebas_seguridad.py`). Commit propio: «F1.2 · escáner: no recorrer lo que genera v2».

## F1.3 · Instantánea del código y copia de la base

1. `git status --short`: lista lo que hay sin commit (el Mac va por delante de GitHub). Nunca entra: `data/`, `*.db`, `_privado/`, `_cache/`, `_crudo/`, `.env*`, capturas, nada con datos de personas o clientes, binarios pesados. Si `git status` enseña alguno, añádelo a `.gitignore` (commit propio) en vez de commitearlo.
2. `python3 escaner_secretos.py --proyecto` en verde para lo que vas a añadir. Lo que marque, fuera del commit y apuntado.
3. Commit «F1.3 · instantánea del código del Mac al empezar la migración» en la rama `migracion/v2` (nunca en `main`).
4. `mkdir -p ~/RO_MIGRACION && cp local.db ~/RO_MIGRACION/local.db.antes && git tag -f antes-de-migrar`. Si existe `despliegue/estado/tuberia.db`, cópiala a `~/RO_MIGRACION/tuberia.db.antes`.

## F1.4 · Referencia: contrato, vectores y fotos

```bash
bash migracion/servicios.sh arrancar viejo           # 8770, sobre ~/RO_MIGRACION/viejo.db (copia)
python3 migracion/contrato.py grabar --base http://127.0.0.1:8770 --salida ~/RO_MIGRACION/contrato/viejo --ver-como
python3 migracion/vectores_permisos.py --salida ~/RO_MIGRACION/vectores
cd v2/tools/capturas && node capturar.mjs --base http://127.0.0.1:8770 --modo viejo --salida ~/RO_MIGRACION/capturas/viejo
```
Abre 5 fotos al azar: tienen que enseñar la pantalla con datos, no «Cargando…». Si alguna sale vacía, arregla la espera en `capturar.mjs` y repite. Mira `_errores.json`: los errores que ya tiene la app de hoy se apuntan (no se arreglan esta noche) y no cuentan contra la nueva. `_tiempos.json` guarda cuánto tarda cada pantalla (lo usa la puerta de velocidad).
Todo esto va con el reloj fijo (`RO_RELOJ`, lo ponen `servicios.sh`, `puerta.sh` y `noche.sh`): no lo quites, o lo grabado antes de medianoche no se parecerá a lo de después.
Crea `~/RO_MIGRACION/excepciones_solidez.txt` con una línea por fallo heredado que ya conoces: `JSON roto  # N-13 servir.py da 500 con un JSON mal formado`.

## F1.5 · Casos de escritura

Escribe `~/RO_MIGRACION/casos_escritura.json` (fuera del repo: lleva ids reales). Formato: lista de `{"persona", "ruta", "cuerpo", "como"?, "nota"}`, en orden. Para **cada POST de servir.py** (lista en `migracion/inventario/rutas_api.json`) al menos: un caso que funcione (200) con una persona que puede, y uno que se deniegue (403/400) con una que no o con un cuerpo malo. Mira el código de cada ruta para construir cuerpos válidos. Incluye casos de «ver como» (deben denegarse: es solo lectura) y de cliente fuera de cartera. **Nunca** casos de rutas que hablan con fuera (`/api/recarga` que lance la tubería, envíos, sincronía, IA, GBP, Modular): esas se quedan en el legado esta noche. Comprueba con `bash migracion/puerta.sh f1` (paso «casos cubren todos los POST»).

## F1.6 · baterias.sh

Crea `migracion/baterias.sh <puerto>`: lanza contra ese puerto **todas** las baterías que pueden apuntar a un servidor ya arrancado (`pruebas_e0.py --puerto`, y las de `migracion/inventario/pruebas.json` que admitan puerto o URL, incluidas las focalizadas de Astra: triaje, método e histórico, reuniones, campañas, cabeceras, si existen en el Mac). Las que arrancan su propio servidor o necesitan proveedores, no; la excepción es `python3 despliegue/pruebas_noche.py --solo-solidez --sin-red --sin-avisos` (último dato bueno de las fuentes, sin red): inclúyela, y si algún caso ya falla contra la app de hoy, apúntalo y haz que `baterias.sh` solo falle con los casos que hoy pasan. Sale 1 si alguna falla. Pásalo contra 8770: lo que ya falla contra la app de hoy se apunta y se quita de la lista (no se arregla esta noche). Commit.

## F1.7 · Puerta 1

`bash migracion/puerta.sh f1` → VERDE. `git push -u origin migracion/v2`.

---

## F2.1 · `avisos` → `tuberia_avisos`

En `despliegue/estado.py`, renombra la tabla de la tubería (y todas sus consultas). `grep -n "avisos" despliegue/estado.py` no debe dejar ninguna de la tubería con el nombre viejo; no toques la `avisos` de `schema_v2.sql`/`servir.py`. Lanza las pruebas de la tubería que toquen `estado.py`. Commit propio.

## F2.2 · Esquema al día

Si `CAMBIOS.md` trae tablas o columnas nuevas (o si dudas): `bash v2/packages/db/scripts/rehacer_base.sh`. Revisa el diff de `schema.prisma` y de `0_base/migration.sql`: cada modelo o columna nueva tiene que estar en NOTAS_NOCHE.md. `crear_base_pg.py` tiene que terminar sin ✘ (salvo el aviso de `avisos` si F2.1 fue ⚠). Commit.

## F2.3 · Postgres con los datos

```bash
cd v2 && pnpm db:up && pnpm db:deploy && cd ..
DATABASE_URL="postgresql://127.0.0.1:5432/ro_app?user=ro&password=ro" python3 migracion/copiar_sqlite_a_pg.py --sqlite ~/RO_MIGRACION/local.db.antes
# si existe:  … --sqlite ~/RO_MIGRACION/tuberia.db.antes --renombrar avisos=tuberia_avisos
DATABASE_URL="postgresql://127.0.0.1:5432/ro_app?user=ro&password=ro" python3 despliegue/publicacion.py publicar data
```
La copia tiene que decir «cuadrada» (si dice que una columna no se copia, vuelve a F2.2). Para repetir desde cero: `--vaciar` (pide «sí»; en esta base de pruebas, contesta tú).

## F2.4 · La app de hoy sobre Postgres

```bash
bash migracion/servicios.sh arrancar legado
bash migracion/puerta.sh f2
```
Cada diferencia es un fallo de traducción SQLite → Postgres en `despliegue/base.py` (mira `~/RO_MIGRACION/logs/legado.log` y `esc_legado.log`: el error de psycopg dice qué SQL falla). Arréglalo en `base.py` de forma general (traducción), nunca tocando la consulta en `servir.py`, y añade el caso a `python3 despliegue/base.py --probar` si se puede. Ya se arreglaron el 4-oct: disparadores con WHEN, BEGIN IMMEDIATE, INSERT OR REPLACE, datetime con modificador, sqlite_master, lastrowid y rowcount. Candidatos típicos que quedan: `IFNULL`, `GROUP_CONCAT`, `strftime`, `LIKE` sin distinguir mayúsculas, comparaciones de texto con números, `ORDER BY` de NULL. Plan B: `~/RO_MIGRACION/excepciones.txt` (una ruta por línea, `# motivo`). El triaje (503 a propósito en Postgres, nota de Astra) va ahí desde el principio.

---

## F3.1 · La app nueva entera

```bash
bash migracion/servicios.sh arrancar        # viejo, legado, api, web
bash migracion/puerta.sh f3
```
Ensayado el 4-oct: sale igual a la primera. Si algo difiere es fontanería: cabeceras (`src/legado/proxy.ts`), reescrituras (`v2/apps/web/next.config.ts`), compresión, `Host`/`Origin` (`RO_ORIGEN_APP`). Push.

---

## F4.1 · Motor de permisos

Lee `permisos.py`, `permisos.js`, `reglas_permisos.json` y `v2/packages/permisos/src/index.ts`. Traduce `permisos.py` a TypeScript función a función, con los mismos nombres en camelCase (carteraPorSilla, cartera, ambito, ver, contexto, recortar, nivelModulo, sinImportes, importesAQuitar, enlaceSeguro, mirandoComo…):
- La matriz se lee de `reglas_permisos.json`. No copies reglas al código.
- «Ver como» en Python es un hilo (`_HILO`); aquí, un objeto «vista» explícito (real + su contexto), nunca un global.
- «Hoy» es el día en Europe/Madrid, y respeta `RO_RELOJ` igual que `permisos.py` (`ahora_madrid`): toda la noche va con el reloj fijo.
- `cargar_modulos()` lee `modulos/indice.js` con expresiones regulares: mismo resultado (los vectores traen `modulos.json`).
Completa `test/paridad.test.ts`: ver y ver_como de cada pregunta, nivel de cada módulo, cartera, ámbito y recorte de cada persona. `bash migracion/puerta.sh f4` al 100 %.
Después, enchúfalo en la API: en `v2/apps/api/src/permisos/` crea `MotorRo implements MotorPermisos` (entrar = nivel del módulo o `ver()` del tipo, con los mismos códigos y mensajes que `servir.py`; recortar = `recortar()`) y ponlo en `permisos.module.ts` en lugar de `MotorSinPortar`. No toques la guarda, el recorte ni `rutas-declaradas.spec.ts`. Commit.

---

## F4.2 · Pruebas de permisos que impiden volver atrás

Anexo de `migracion/PENDIENTES_LOGICA.md`, punto 8. En `v2/apps/api/test/permisos-regresion.e2e-spec.ts`, con el motor portado y los vectores (`RO_VECTORES`):
- toda ruta de escritura de Nest da 403 en «ver como», salvo la lista de `lecturaPorPost` (la prueba la imprime y la compara con una lista fija);
- ninguna respuesta en «ver como» trae algo que la persona real no vería (compara las dos respuestas);
- para cada puesto, ninguna respuesta lleva claves de dinero o de leads que su tipo no permite (las cuatro expresiones de L-04, iguales que en `permisos.py`);
- un account no recibe nada de un cliente ajeno por ninguna ruta (raíz, ruta o fila);
- `HEAD`/`OPTIONS` a una ruta de datos por el puerto de Next → 405 (ya cubierto en el proxy: compruébalo de punta a punta).
Mientras las rutas sigan en el proxy, estas pruebas van contra la app nueva entera (puerto 3000), así que también vigilan a `servir.py`: lo que falle por un L-xx abierto se marca `it.todo('L-xx …')` y se activa al arreglarlo en F5.10. Súmala a `puerta.sh f4`. Plan B: lo que no salga, `it.todo` con su motivo y al informe.

## F5.x · Un grupo de rutas a Nest

Para el grupo del paso (tabla §2.2 del plan):
1. Lee el código Python de cada ruta del grupo (servir.py y el enchufe que toque) y reprodúcelo en un módulo de Nest: mismos códigos, mensajes, claves JSON, recorte (con `@ro/permisos`), rastro y cabeceras. Base con `PrismaService` (SQL crudo con `$queryRaw` solo si Prisma no llega). Datos de módulos: de `datos_version`/`datos_fichero`/`datos_blob` (espacio «data», versión vigente, zlib), con caché por versión.
   **Permisos:** cada método lleva `@Permiso({ modulo | tipo })` (o `@Publico('motivo')` si no tiene datos). Todo sale recortado y todo POST es escritura por defecto; `sinRecorte` y `lecturaPorPost` solo con motivo y solo donde `servir.py` hace lo mismo hoy. F5.6 implementa `RASTRO_VER_COMO` (rastro de «ver como» agrupado por minuto, L-08) en lugar de `RastroVerComoSinPortar`: hasta entonces, «ver como» a una ruta de Nest da 503, y por eso F5.6 va antes que cualquier grupo que tenga pantallas en «ver como» (si no da tiempo, esas rutas se quedan en el proxy). Prohibido comprobar puestos, personas o carteras a mano en el controlador o el servicio: si la declaración no llega, se amplía el motor en `src/permisos/` (y su prueba), no la ruta. `rutas-declaradas.spec.ts` lo vigila y no se relaja.
2. Añade sus rutas a `v2/apps/api/src/legado/rutas-en-nest.ts`.
3. `bash migracion/puerta.sh f5 --rapido` para iterar; `bash migracion/puerta.sh f5` para cerrar.
4. VERDE → commit «F5.x · <grupo> en Nest». ROJO tras 3 intentos → quita sus rutas de la lista, `git switch -c intento/<grupo>` con el módulo, vuelve a `migracion/v2`, ⚠ y siguiente.
F5.1 (identidad) es la guarda global de las rutas de Nest: `RO_IDENTIDAD=local|access` como `despliegue/acceso_cf.py`; las rutas que siguen en el proxy las sigue comprobando servir.py.

## F5.10 · Fallos pendientes de lógica

Lista: `migracion/PENDIENTES_LOGICA.md` **juntada** con `~/RO_MIGRACION/PENDIENTES_LOGICA.md` si existe (por id; para un id en las dos manda la columna Estado del Mac, que es la que actualiza Astra; las filas de una sola se suman). Escribe el resultado en `migracion/PENDIENTES_LOGICA.md` y trabaja sobre ese. Regla de Tomás: lo que no quedó arreglado en la app de hoy se arregla aquí sí o sí. Orden: **L-01 y L-21 primero** (tumban el servidor), luego seguridad → datos → funcional → presentación. Los `decide Tomás (Dn)` no se tocan (van al informe con su recomendación). Los `arreglado hoy` / `ya estaba`: solo comprobar que su prueba pasa en la app nueva. Para cada fallo `abierto`:
1. Escribe primero la prueba que lo demuestra y comprueba que FALLA (Vitest en `v2/` si la ruta está en Nest; Python en `migracion/` o junto a la batería que toque si sigue en `servir.py`).
2. Arréglalo donde viva esa noche: el módulo de Nest si la ruta ya se mudó; `servir.py` (o su enchufe) si sigue por el proxy; si es de permisos, en `reglas_permisos.json` (lo leen los dos motores) o en los dos motores a la vez (`permisos.py` y `@ro/permisos`), y vuelve a sacar los vectores con `vectores_permisos.py` para que la paridad siga al 100 %.
3. La prueba pasa. Las rutas cuya respuesta cambia a propósito van a `~/RO_MIGRACION/excepciones.txt` con `# L-n <motivo>`.
4. `bash migracion/puerta.sh f5` en VERDE → commit «L-n · <qué>» y estado `arreglado en v2 (<commit>)` en la lista.
Tras 3 intentos sin salir: deshaz el arreglo, deja la prueba marcada como pendiente (`it.todo`/`skip` con «L-n»; nunca borrada), estado `pendiente: <motivo>` y siguiente. Los de **seguridad** se hacen aunque el reloj diga «sin tiempo», antes de la fase 7.
Para N-01 a N-12 (fuentes), sigue `PLAN_MAESTRO.md` §2.5: primero N-01 (tabla `fuente_lectura` en `v2/packages/db` con su migración, y `fuentes/lectura.py › leer()` con su prueba), y luego cada lector pasa por `leer()` con una prueba de «API falsa caída → último dato bueno + aviso, ningún 0» añadida a `despliegue/pruebas_noche.py --solo-solidez`. Para N-10, escribe `migracion/nunca_ceros.mjs` (cuenta `?? 0` y `|| 0` sobre cifras pintadas en `modulos/` y `v2/apps/web/src`; guarda la cifra de partida en `~/RO_MIGRACION/nunca_ceros.txt` y falla si sube) y súmalo a `baterias.sh`. Ningún lector se prueba contra la API de verdad: siempre con una falsa en 127.0.0.1 o un módulo de mentira.
Cuando arregles N-13, quita su línea de `~/RO_MIGRACION/excepciones_solidez.txt`.
Los fallos `arreglado hoy`: comprueba que su prueba pasa también en la app nueva (`--pantallas` o la ruta); si no, trátalo como abierto.

## F5.11 · Escalados sobre Postgres

Escribe `migracion/escalados.py` y súmalo a la puerta 7:
1. Base limpia `ro_esc` (`contrato_escritura.py base-limpia ro_esc`).
2. Legado aparte en 127.0.0.1:8783 sobre ella, con los bucles ENCENDIDOS (sin `RO_AVISOS_SIN_BUCLE`) y TODAS las salidas apagadas (sin `RO_ENVIOS_REALES` ni `RO_CLICKUP_REAL`).
3. Un `RO_RELOJ` más tarde que el plazo de una alerta y de una regla de aviso automático (créalas como lo hacen `pruebas_seguridad.py › alertas_a8` y `avisos_automaticos`).
4. Comprueba por la API (`/api/canales/campana` de cada persona) que el «sube a X» llega a la persona que toca según `cadena_escalado` y `avisos_programados.escalar()`, **una sola vez** aunque pasen dos vueltas del bucle, y que lo marcado «Lo tengo» no escala.
5. Lo paras. Nunca contra `ro_app`.

Si algo no escala sobre Postgres y en SQLite sí, es un fallo de `despliegue/base.py`: arréglalo con su prueba. Plan B: apuntarlo como bloqueo para el piloto.

---

## F6.1 · shadcn, ctx y puente

Lee `v2/apps/web/AGENTS.md` (esta versión de Next tiene cambios: consulta `node_modules/next/dist/docs/` antes de escribir rutas o layouts).
1. `pnpm dlx shadcn@latest init` en `v2/apps/web` sin tocar `src/styles/ro-tema.css` ni el `globals.css` sin preflight (si el init los cambia, devuélvelos como estaban). Añade sidebar, command, dropdown-menu, dialog, sheet, tooltip.
2. `src/lib/ctx.ts`: `crearCtx` de `app.js` en TypeScript, los 40 campos (`migracion/inventario/ctx.json`), mismo comportamiento.
3. `PantallaPuente`: importa `/legacy/modulos/<fichero>` en el navegador y llama a `render(contenedor, ctx)`.

## F6.2 · Carcasa en React en /carcasa

La carcasa con LAS MISMAS clases de `estilos.css` y el mismo DOM que pintan hoy `app.js` + `carcasa.js`: menú por puesto, cabecera, ⌘K y «/», «ver como» (solo lectura), menú móvil, «¿Quién eres?» en local. Mismas direcciones `#/pantalla`. Las 37 pantallas por el puente. Compara sus fotos con las de «/» (`capturar.mjs --base http://127.0.0.1:3000` sobre `/carcasa`, o temporalmente con la carcasa en «/» detrás de una variable) hasta ≤ 0,5 %.

## F6.3 · Carcasa a «/»

Mueve la carcasa a `src/app/page.tsx` (ya no cae al front de hoy). `bash migracion/puerta.sh f6` en VERDE → commit. Si no: vuelve a `/carcasa` (⚠) y «/» sigue siendo el front de hoy.

## F6.4 · Pantallas en React

Primero, si no existe, `src/components/ro/` (componentes.js en React, mismas clases, mismo DOM; shadcn solo donde la pieza sea equivalente). Luego, una pantalla cada vez, en este orden: Mi perfil, Catálogo de indicadores, Decisiones y rastro, En rojo, Agenda, Reuniones, Horas, Producción, CRM, SEO, Web, Redes, Paid, Mi día, Ficha del cliente, Captación, Bandeja, Panel de dirección, Finanzas. Para cada una: rehacer → fotos solo de esa pantalla (`--pantallas <id>`, todas las personas y los dos tamaños) → ≤ 0,5 % y contrato y baterías verdes → sustituye al puente y commit. Si no, se queda el puente (⚠ esa pantalla) y siguiente. Respeta las reglas de presentación de la nota de Astra (desconocido ≠ cero, siglas con `title`, colores solo con evidencia): no se cambian, se copian.

---

## F7.1 · Contenedores

`cd v2 && docker compose --profile completo up --build -d` y `bash migracion/puerta.sh f3` contra ellos (los mismos puertos). Si el contenedor de la API no llega al legado, el legado es el `servir.py` del Mac en 8771 (`RO_LEGADO_URL=http://host.docker.internal:8771`).

## F7.2 · render.yaml

`v2/render.yaml` a partir de `despliegue/render.yaml` (y `PLAN_MAESTRO.md` §2.7–2.9): `ro-web` (Next), `ro-api` (Nest, `RO_LEGADO_URL` al servicio privado del legado), `ro-legado` (la imagen de `despliegue/Dockerfile`, **una sola copia**, con la tubería y los bucles), `ro-base` (Postgres). Sin llaves. Cloudflare Access delante, como en `despliegue/DESPLIEGUE.md`. El grupo `ro-llaves` completo (comprueba con `python3 migracion/llaves_nube.py`: nada «FALTA en render.yaml») y solo en `ro-legado`. Sin `RO_AVISOS_SIN_BUCLE` (los escalados necesitan los bucles). El vigía, como cron o dentro del legado (N-18). ClickUp real apagado. **Nunca ejecutes `llaves_nube.py --exportar`**: es de Tomás.

## F7.3 · Informe y puerta 7

`migracion/INFORME_NOCHE.md`, para Tomás, en castellano y frases cortas:
1. Resumen en 5 líneas: qué funciona en la app nueva, qué se ha mudado a Nest y a React, qué sigue por el proxy o el puente.
2. Puertas: cada una con VERDE/ROJO y su informe.
3. Bloqueos para el piloto (Astra): permisos con datos reales, restauración, fuentes, funciones críticas; excepciones conocidas; fallos de seguridad de `PENDIENTES_LOGICA.md` sin arreglar.
   Y una tabla con cada fallo de `PENDIENTES_LOGICA.md`: arreglado (dónde y commit) o pendiente (por qué).
4. Preguntas para Tomás.
5. Pasos de la mañana, exactos.
Después, `bash migracion/puerta.sh f7`.

## F7.4 · Cierre

Commit, `git push origin migracion/v2`, `ESTADO: TERMINADO` en PROGRESO.md, commit y push.
