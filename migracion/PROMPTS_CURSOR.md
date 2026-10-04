# Detalle de cada paso · noche del 4 al 5 de octubre de 2026

**El prompt que se pega (o que lanza `noche.sh`) es `migracion/PROMPT_NOCHE.md`.** Este fichero es el detalle de cada paso de `migracion/PROGRESO.md`: el agente lee la sección del paso que le toca. Si existe `migracion/PLAN_NOCHE.md` (el plan de la noche, escrito y revisado antes), lee primero su sección del paso y síguela; esto es el detalle de fondo.

Convenciones para todos los pasos:
- `FUERA` = `~/RO_MIGRACION` (datos reales; nunca al repo). Puertos: 8770 app de hoy sobre copia SQLite · 8771 legado (app de hoy sobre Postgres `ro_app`) · 4000 Nest · 3000 Next · 5432 Postgres.
- Arrancar y parar: `bash migracion/servicios.sh arrancar|parar|reiniciar|estado [viejo|legado|api|web|todo]`. La puerta reinicia sola legado, Nest y Next antes de comparar; para probar a mano tras tocar código, `reiniciar` (con `arrancar`, un servicio vivo se queda con el código de antes). Al retomar una vuelta, arranca solo lo de fases cerradas: `viejo` tras F1.4, `legado` tras F2.3, `api` y `web` tras F3.1 (un `arrancar` a secas antes de F2.3 crea tablas en `ro_app` vacía).
- Diferencias aceptadas: `~/RO_MIGRACION/excepciones.txt`, SOLO con un id L-/N- de `PENDIENTES_LOGICA.md` o con el plan B de F2.4. Si un fichero que juzga parece estar mal, no va aquí: va a «Preguntas para Tomás» de NOTAS_NOCHE.md. Una por línea, con motivo obligatorio: `/api/ruta  # L-n …`, `/api/modulo/seo/*  # …` (prefijo), `tabla:avisos  # …`, `foto:crm  # …`. La leen el contrato, la escritura y las fotos.
- Cerrar: `bash migracion/puerta.sh <fase>` en VERDE (el informe queda en `FUERA/puertas/<fase>.md`). `--rapido` sirve para iterar, no para cerrar.
- Commits pequeños, mensaje que empieza por el código del paso: «F2.4 · base.py: …».
- **Antes de traducir una sola línea de Python o del JS de hoy (F4, F5, F6), lee la «Guía de traducción» del final de este fichero.**

---

## F1.1 · Inventario y notas

```bash
python3 migracion/inventario.py --comparar
```
Lee `migracion/inventario/CAMBIOS.md` y `RESUMEN.md`. Crea `migracion/NOTAS_NOCHE.md` con: qué pantallas, rutas (también de enchufes), tablas, columnas, reglas de permisos y componentes son nuevos o cambian respecto a lo que hay en GitHub, y qué implica cada uno para las fases 2 a 6. Lee también `migracion/NOTA_ASTRA.md`: sus «mejoras locales recientes» tienen que aparecer en el inventario; si alguna no aparece, apúntalo. Añade al final las secciones «Preguntas para Tomás» y «Bloqueos para el piloto» (vacías).
Cambios de forma en `data/` que llegan del 4-oct (si el Mac ya los tiene): `data/agenda/agenda.json` trae una lista nueva `canceladas` y la agenda mira 30 días atrás (la lee `riesgo_baja.py`). Esta noche los ficheros de `data/` viajan enteros como blobs (`datos_fichero`): no se tipan ni se recortan claves; si alguna pieza nueva los lee, se conserva tal cual.

## F1.2 · Escáner de secretos

En `escaner_secretos.py`, añade `".next"`, `"dist"`, `"generated"` y `"legacy"` a `CARPETAS_FUERA`. Pasa `python3 escaner_secretos.py --proyecto`: lo que quede marcado fuera de esas carpetas se apunta en NOTAS_NOCHE.md (hay un falso positivo conocido en `pruebas_seguridad.py`). Commit propio: «F1.2 · escáner: no recorrer lo que genera v2».

## F1.3 · Instantánea del código y copia de la base

Antes, el contexto (4-oct): el código del Mac hasta el corte 650 de la entrega (`codex/ro-entrega-cursor-2026-10-04`) **ya está en esta rama**, juntado con los PR #2, #3 y #4 y con los choques resueltos. El Mac no cambia de rama: `preparar_noche.sh` trajo de aquí solo `migracion/`, `v2/`, `.cursor/` y `AGENTS.md`, y `juntar_plan.sh` (3c) trae lo demás fichero a fichero (mezcla a tres contra `main`; donde el Mac sigue en el corte 650 no hace nada, y lo que Astra cambió después se respeta). Por eso esta instantánea solo recoge **lo que cambió en el Mac después del corte 650**, con la misma regla de siempre: fichero a fichero, nunca `git add -A`.
**Ficheros privados que la entrega sacó de git** (los `_ESTADO_*.md`, `fuentes_consejos/conocimiento/*.json`, `indicadores.json`, `escaner_permitidos.json`, cachés y logs de `fuentes_*/`…; lista exacta: `git diff --name-status main origin/codex/ro-entrega-cursor-2026-10-04 | grep ^D`): se quedan en el Mac, ya están en `.gitignore` y **nunca se vuelven a añadir**, aunque `git status` los enseñe o un paso parezca necesitarlos. Si alguno sale en `git status`, se apunta en NOTAS_NOCHE.md; no se commitea ni se fuerza con `git add -f`.

1. `git status --short`: lista lo que hay sin commit (el Mac va por delante de GitHub). Nunca entra: `data/`, `*.db`, `_privado/`, `_cache/`, `_crudo/`, `.env*`, capturas, nada con datos de personas o clientes, binarios pesados, ni los ficheros privados que la entrega sacó de git (arriba). Si `git status` enseña alguno, añádelo a `.gitignore` (commit propio) en vez de commitearlo.
2. `python3 escaner_secretos.py --proyecto` en verde para lo que vas a añadir. Lo que marque, fuera del commit y apuntado.
3. Commit «F1.3 · instantánea del código del Mac al empezar la migración» en la rama `migracion/v2` (nunca en `main`). Nunca `git add -A` ni `git add .`: `git add` fichero a fichero, solo la lista revisada (el código que salga en el punto 1 y haya cambiado en el Mac después del corte 650, cada uno mirado; la tabla «Mejoras locales recientes» de `migracion/NOTA_ASTRA.md` ya entró con la entrega: solo se comprueba que está). Escribe esa lista en NOTAS_NOCHE.md; lo que no entra, apuntado.
3b. Junta el trabajo del 4-oct que aún está en PR: para cada rama de `migracion/RAMAS_A_JUNTAR.txt`, en orden, `git fetch origin <rama>` y, si `git merge-base --is-ancestor origin/<rama> HEAD` falla, `git merge --no-edit origin/<rama>`. Si choca: en los ficheros en conflicto, une las dos versiones si son listas o fichas que se suman (p. ej. los cerebros de `fuentes_consejos/cerebros/`: van las fichas de las dos), y si no, `git checkout --ours` del fichero; pasa su `probar_*.py` y apunta en NOTAS_NOCHE.md («Preguntas para Tomás») qué fichero y qué versión quedó. Nunca `--force`, nunca a `main`. Después, `python3 migracion/inventario.py --comparar` otra vez y añade a NOTAS_NOCHE.md lo nuevo (pantallas, rutas, ficheros de `data/`).
3c. `noche.sh` ya ha juntado lo que el plan cambia fuera de `migracion/` y `v2/` (`migracion/juntar_plan.sh`: config.py, despliegue/, fuentes/…). Vuelve a pasarlo (no hace nada si ya está) y, si existe `~/RO_MIGRACION/choques_plan.txt`, resuelve cada fichero a mano: lo de Astra se queda y se añade lo de la rama que falte (`git diff <base> origin/claude/project-thread-rjes21 -- <fichero>`). Commit «F1.3 · plan juntado». Plan B: se queda el del Mac y se apunta en NOTAS_NOCHE.md qué falta.
4. `mkdir -p ~/RO_MIGRACION && cp local.db ~/RO_MIGRACION/local.db.antes && git tag -f antes-de-migrar`. Si existe `despliegue/estado/tuberia.db`, cópiala a `~/RO_MIGRACION/tuberia.db.antes`.
5. Copia congelada de la app de hoy (la referencia 8770/8780 se sirve desde ahí, así los arreglos de F5.10 no la cambian): `rsync -a --delete --exclude .git --exclude v2 --exclude node_modules --exclude capturas --exclude historia ./ ~/RO_MIGRACION/ref/`. Comprueba `ls ~/RO_MIGRACION/ref/servir.py`.

## F1.4 · Referencia: contrato, vectores y fotos

```bash
bash migracion/servicios.sh arrancar viejo           # 8770, sobre ~/RO_MIGRACION/viejo.db (copia)
python3 migracion/contrato.py grabar --base http://127.0.0.1:8770 --salida ~/RO_MIGRACION/contrato/viejo --ver-como
python3 migracion/vectores_permisos.py --salida ~/RO_MIGRACION/vectores
cd v2/tools/capturas && node capturar.mjs --base http://127.0.0.1:8770 --modo viejo --salida ~/RO_MIGRACION/capturas/viejo
```
Si 8770 no arranca y `~/RO_MIGRACION/logs/viejo.log` dice `UnboundLocalError` (es L-01: una respuesta de «Para confirmar» en la base tumba `servir.py`), arregla L-01 primero en `servir.py` y en `~/RO_MIGRACION/ref/servir.py` (mismo cambio, con su prueba y su commit «L-01 · …»), márcalo en la lista y sigue.
Abre 5 fotos al azar: tienen que enseñar la pantalla con datos, no «Cargando…». Si alguna sale vacía, arregla la espera en `capturar.mjs` y repite. Mira `_errores.json`: los errores que ya tiene la app de hoy se apuntan (no se arreglan esta noche) y no cuentan contra la nueva. `_tiempos.json` guarda cuánto tarda cada pantalla (lo usa la puerta de velocidad).
Todo esto va con el reloj fijo (`RO_RELOJ`, lo ponen `servicios.sh`, `puerta.sh` y `noche.sh`): no lo quites, o lo grabado antes de medianoche no se parecerá a lo de después.
Crea `~/RO_MIGRACION/excepciones_solidez.txt` con una línea por fallo heredado que ya conoces: `JSON roto  # N-13 servir.py da 500 con un JSON mal formado`.

Funciones del 4-oct (`migracion/INTEGRAR.md`): el contrato ya graba `GET /api/ia/cerebro?q=…` e `?id=…` y el fichero del riesgo de baja (`datos_de_modulo`). Comprueba que salen en `~/RO_MIGRACION/contrato/viejo` con datos (no 404): si no, apúntalo en NOTAS_NOCHE.md.

## F1.5 · Casos de escritura

Escribe `~/RO_MIGRACION/casos_escritura.json` (fuera del repo: lleva ids reales). Formato: lista de `{"persona", "ruta", "cuerpo", "como"?, "nota"}`, en orden. Para **cada POST de servir.py** (lista en `migracion/inventario/rutas_api.json`) al menos: un caso que funcione (200) con una persona que puede, y uno que se deniegue (403/400) con una que no o con un cuerpo malo. Mira el código de cada ruta para construir cuerpos válidos. Incluye casos de «ver como» (deben denegarse: es solo lectura) y de cliente fuera de cartera. **Nunca** casos de rutas que hablan con fuera (`/api/recarga` que lance la tubería, envíos, sincronía, IA, GBP, Modular): esas se quedan en el legado esta noche. Para `/api/recarga` (y cualquier POST que lance algo fuera), **solo el caso denegado** (403/400): cuenta para «casos cubren todos los POST». Comprueba con `bash migracion/puerta.sh f1` (paso «casos cubren todos los POST»).

## F1.6 · baterias.sh

Crea `migracion/baterias.sh <puerto>`: lanza contra ese puerto **todas** las baterías que pueden apuntar a un servidor ya arrancado (`pruebas_e0.py --puerto`, y las de `migracion/inventario/pruebas.json` que admitan puerto o URL, incluidas las focalizadas de Astra: triaje, método e histórico, reuniones, campañas, cabeceras, si existen en el Mac). Las que arrancan su propio servidor o necesitan proveedores, no; la excepción es `python3 despliegue/pruebas_noche.py --solo-solidez --sin-red --sin-avisos` (último dato bueno de las fuentes, sin red): inclúyela, y si algún caso ya falla contra la app de hoy, apúntalo y haz que `baterias.sh` solo falle con los casos que hoy pasan. Sale 1 si alguna falla. Suma también las pruebas sin servidor de las funciones del 4-oct (ver `migracion/INTEGRAR.md`): `fuentes_consejos/cerebros/probar_cerebros.py`, `probar_en_app.py`, `fuentes_diagnosticos/probar_diagnosticos.py`, `fuentes_riesgo/probar_riesgo.py`, `fuentes_contexto/probar_contexto.py` y `fuentes/probar_lectura.py` (las que existan). Suma también lo de la entrega del 4-oct, que corre sobre el checkout (sin puerto ni datos):
- **El carril de seguridad aislado** (29 suites, solo fixtures y AST, sin servidor ni secretos): `python3 pruebas_seguridad.py --aisladas` (la lista exacta está en `ejecutar_aisladas_560` de `pruebas_seguridad.py`; la vigila `probar_baterias_seguras_560.py`). Sale distinto de 0 si una suite falla.
- **Las pruebas DOM** `pruebas_*.cjs` de la raíz: `node <fichero>.cjs` (sin dependencias; DOM simulado). Solo las portables: las que leen rutas absolutas del Mac (`/Users/…`) o un servidor (`127.0.0.1`, `localhost`) se quedan fuera y se apuntan. Se sabe que `pruebas_captacion_compacta_243.cjs` y `pruebas_matriz_paid_508.cjs` fallan en su versión original (`entrega/VERIFICACION_FINAL_UI_CURSOR.md`): fuera y apuntadas.
La entrega dice que las **baterías originales globales no están certificadas verdes**. Es lo esperado: pásalo contra 8770 y el checkout; lo que ya falla contra la app de hoy se apunta en NOTAS_NOCHE.md y se quita de la lista (el plan B de siempre; no se arregla esta noche ni se copian datos reales para que pase). Commit.

## F1.7 · Puerta 1

`bash migracion/puerta.sh f1` → VERDE. `git push -u origin migracion/v2`.

Con la puerta en verde, deja de solo lectura lo que es la referencia (nada de esto se vuelve a escribir esta noche):
```bash
chmod -R a-w ~/RO_MIGRACION/contrato/viejo ~/RO_MIGRACION/capturas/viejo ~/RO_MIGRACION/local.db.antes 2>/dev/null || true
find ~/RO_MIGRACION/ref \( -name '*.py' -o -name '*.js' -o -name '*.html' -o -name '*.sql' \) -exec chmod a-w {} +   # solo el código: la referencia sí escribe anclas y estado en su carpeta
```
(Los vectores de permisos NO: F5.10 los regenera. Ni la carpeta `ref` entera: servir.py escribe ahí sus anclas.) Si un paso posterior necesita escribir ahí, es que va mal: plan B, no `chmod`.

---

## F2.1 · `avisos` → `tuberia_avisos`

En `despliegue/estado.py`, renombra la tabla de la tubería (y todas sus consultas). `grep -n "avisos" despliegue/estado.py` no debe dejar ninguna de la tubería con el nombre viejo; no toques la `avisos` de `schema_v2.sql`/`servir.py`. Lanza las pruebas de la tubería que toquen `estado.py`. `despliegue/pruebas_noche.py` ya lee `tuberia_avisos` o `avisos`: no lo toques (juzga). Commit propio.

## F2.2 · Esquema al día

Tabla nueva que seguro trae: `fuente_lectura` (y su vista `fuente_ultimo_bueno`), de N-01 (`migracion/INTEGRAR.md` §5). Si `CAMBIOS.md` trae tablas o columnas nuevas (o si dudas): `bash v2/packages/db/scripts/rehacer_base.sh`. Revisa el diff de `schema.prisma` y de `0_base/migration.sql`: cada modelo o columna nueva tiene que estar en NOTAS_NOCHE.md. `crear_base_pg.py` tiene que terminar sin ✘ (salvo el aviso de `avisos` si F2.1 fue ⚠). Commit.

## F2.3 · Postgres con los datos

```bash
cd v2 && pnpm db:up && pnpm db:deploy && cd ..
DATABASE_URL="postgresql://127.0.0.1:5432/ro_app?user=ro&password=ro" python3 migracion/validar_sqlite.py --sqlite ~/RO_MIGRACION/local.db.antes --pg
DATABASE_URL="postgresql://127.0.0.1:5432/ro_app?user=ro&password=ro" python3 migracion/copiar_sqlite_a_pg.py --sqlite ~/RO_MIGRACION/local.db.antes
# si existe:  … --sqlite ~/RO_MIGRACION/tuberia.db.antes --renombrar avisos=tuberia_avisos
DATABASE_URL="postgresql://127.0.0.1:5432/ro_app?user=ro&password=ro" python3 despliegue/publicacion.py publicar data
```
`validar_sqlite.py` va ANTES de copiar: un ✘ (byte NUL, texto que no es UTF-8, valor que no cabe en el tipo de Postgres) hace fallar la copia a medias. Se arregla en otra copia (`~/RO_MIGRACION/local.db.limpia`, nunca en `local.db.antes` ni en `local.db`) con la orden exacta en NOTAS_NOCHE.md, y se copia desde esa. Cada ⚠ (tipos mezclados en una columna) se apunta en NOTAS_NOCHE.md: al portar las rutas que la leen, compara y ordena como hoy. La copia tiene que decir «cuadrada» (si dice que una columna no se copia, vuelve a F2.2). Para repetir desde cero, `--vaciar` (pide «sí» por teclado; en esta base de pruebas, contesta tú con una tubería):
```bash
echo sí | DATABASE_URL="postgresql://127.0.0.1:5432/ro_app?user=ro&password=ro" python3 migracion/copiar_sqlite_a_pg.py --sqlite ~/RO_MIGRACION/local.db.antes --vaciar
```
(con `local.db.limpia` en lugar de `local.db.antes` si la hiciste).

## F2.4 · La app de hoy sobre Postgres

```bash
bash migracion/servicios.sh arrancar legado
bash migracion/puerta.sh f2
```
Antes: `git diff origin/claude/project-thread-rjes21 -- despliegue/base.py`. Si sale algo, el Mac no tiene los arreglos del 4-oct. Júntalos con una mezcla a tres (nunca `git checkout` del fichero de la rama: pisaría lo de Astra):
```bash
mkdir -p ~/RO_MIGRACION/tmp
git show "$(git merge-base HEAD origin/claude/project-thread-rjes21)":despliegue/base.py > ~/RO_MIGRACION/tmp/base.comun.py
git show origin/claude/project-thread-rjes21:despliegue/base.py > ~/RO_MIGRACION/tmp/base.rama.py
git merge-file despliegue/base.py ~/RO_MIGRACION/tmp/base.comun.py ~/RO_MIGRACION/tmp/base.rama.py
```
Sale 0: `python3 despliegue/base.py --probar` y commit propio. Si choca (sale >0): `git checkout -- despliegue/base.py` (se queda el del Mac) y apúntalo en NOTAS_NOCHE.md, como en F1.3 3c.
Cada diferencia es un fallo de traducción SQLite → Postgres en `despliegue/base.py` (mira `~/RO_MIGRACION/logs/legado.log` y `esc_legado.log`: el error de psycopg dice qué SQL falla). Arréglalo en `base.py` de forma general (traducción), nunca tocando la consulta en `servir.py`, y añade el caso a `python3 despliegue/base.py --probar` si se puede. Ya se arreglaron el 4-oct: disparadores con WHEN, BEGIN IMMEDIATE, INSERT OR REPLACE, datetime con modificador, sqlite_master, lastrowid y rowcount. Candidatos típicos que quedan: `IFNULL`, `GROUP_CONCAT`, `strftime`, `LIKE` sin distinguir mayúsculas, comparaciones de texto con números, `ORDER BY` de NULL. Plan B: `~/RO_MIGRACION/excepciones.txt` (una ruta por línea, `# motivo`; ver «Diferencias aceptadas» arriba). El triaje (503 a propósito en Postgres, nota de Astra) va ahí desde el principio.

---

## F3.1 · La app nueva entera

```bash
bash migracion/servicios.sh arrancar        # viejo, legado, api, web
bash migracion/puerta.sh f3
```
Si F3.1 queda ⚠: F5.1–F5.9 y F6.x → ⚠ sin intentarlo; F5.10 se cierra con su prueba + `puerta.sh f2`. Ensayado el 4-oct: sale igual a la primera. Si algo difiere es fontanería: cabeceras (`src/legado/proxy.ts`), reescrituras (`v2/apps/web/next.config.ts`), compresión, `Host`/`Origin` (`RO_ORIGEN_APP`). Push.

---

## F4.1 · Motor de permisos

Lee `permisos.py`, `permisos.js`, `reglas_permisos.json`, `v2/packages/permisos/src/index.ts` y la cabecera de `v2/packages/permisos/test/paridad.test.ts` (las funciones y firmas que la puerta f4 exige; ese fichero juzga y no se toca). Traduce `permisos.py` a TypeScript función a función, con los mismos nombres en camelCase (carteraPorSilla, cartera, ambito, ver, contexto, recortar, nivelModulo, sinImportes, importesAQuitar, enlaceSeguro, mirandoComo…):
- La matriz se lee de `reglas_permisos.json`. No copies reglas al código.
- «Ver como» en Python es un hilo (`_HILO`); aquí, un objeto «vista» explícito (real + su contexto), nunca un global.
- «Hoy» es el día en Europe/Madrid, y respeta `RO_RELOJ` igual que `permisos.py` (`ahora_madrid`): toda la noche va con el reloj fijo.
- `cargar_modulos()` lee `modulos/indice.js` con expresiones regulares: mismo resultado (los vectores traen `modulos.json`).
No toques `test/paridad.test.ts` (juzga). Exporta desde `src/index.ts` las funciones que pide su cabecera (`ver`, `contexto`, `nivelModulo`, `carteraPorSilla`, `ambito`, `recortar`, `mirandoComo`) hasta que `puerta.sh f4` dé 100 %.
Después, enchúfalo en la API: en `v2/apps/api/src/permisos/` crea `MotorRo implements MotorPermisos` (entrar = nivel del módulo o `ver()` del tipo, con los mismos códigos y mensajes que `servir.py`; recortar = `recortar()`) y ponlo en `permisos.module.ts` en lugar de `MotorSinPortar`. No toques la lógica de la guarda, el recorte ni `rutas-declaradas.spec.ts`; los textos de error sí deben ser los de `servir.py` (el filtro `errores.filter.ts` ya les da la forma `{"error": …}`). Las pruebas de `permisos.spec.ts` ya meten su motor a mano: no deberían cambiar; si una cambia, que siga probando lo mismo. Commit.

---

## F4.2 · Pruebas de permisos que impiden volver atrás

Anexo de `migracion/PENDIENTES_LOGICA.md`, punto 8. En `v2/apps/api/test/permisos-regresion.e2e-spec.ts` (los `*.e2e-spec.ts` los lanza `puerta.sh` f3/f5/f6/f7 con `pnpm --filter @ro/api test:e2e`: así protegen toda la fase 5), con el motor portado y los vectores (`RO_VECTORES`):
- toda ruta de escritura de Nest da 403 en «ver como», salvo la lista de `lecturaPorPost` (la prueba la imprime y la compara con una lista fija);
- ninguna respuesta en «ver como» trae algo que la persona real no vería (compara las dos respuestas);
- para cada puesto, ninguna respuesta lleva claves de dinero o de leads que su tipo no permite (las cuatro expresiones de L-04, iguales que en `permisos.py`);
- un account no recibe nada de un cliente ajeno por ninguna ruta (raíz, ruta o fila);
- `HEAD`/`OPTIONS` a una ruta de datos por el puerto de Next → 405 (ya cubierto en el proxy: compruébalo de punta a punta).
Mientras las rutas sigan en el proxy, estas pruebas van contra la app nueva entera (puerto 3000), así que también vigilan a `servir.py`: lo que falle por un L-xx abierto se marca `it.todo('L-xx …')` y se activa al arreglarlo en F5.10. Plan B: lo que no salga, `it.todo` con su motivo y al informe.

## F5.x · Un grupo de rutas a Nest

Para el grupo del paso (tabla §2.2 del plan). Las rutas que no están en ningún grupo (la entrega trae 125 rutas de enchufes, cuenta en `migracion/inventario/RESUMEN.md`; manda esa) se quedan por el proxy: está bien así, para el equipo no cambia nada. Antes de empezar: si F3.1 quedó ⚠, F5.1–F5.9 → ⚠ sin intentarlo (ver PROGRESO.md).
1. Lee el código Python de cada ruta del grupo (servir.py y el enchufe que toque) y reprodúcelo en un módulo de Nest: mismos códigos, mensajes, claves JSON, recorte (con `@ro/permisos`), rastro y cabeceras. Base con `PrismaService` (SQL crudo con `$queryRaw` solo si Prisma no llega). Datos de módulos: de `datos_version`/`datos_fichero`/`datos_blob` (espacio «data», versión vigente, zlib), con caché por versión.
   **Permisos:** cada método lleva `@Permiso({ modulo | tipo })` (o `@Publico('motivo')` si no tiene datos). Todo sale recortado y todo POST es escritura por defecto; `sinRecorte` y `lecturaPorPost` solo con motivo y solo donde `servir.py` hace lo mismo hoy. F5.1 implementa `RASTRO_VER_COMO` (el escritor del rastro de «ver como», agrupado por minuto, L-08, con `huellaRastro` de `@ro/compat` y el candado 7262) en lugar de `RastroVerComoSinPortar`: hasta entonces, «ver como» a una ruta de Nest da 503 y la puerta (que graba en «ver como») sale ROJA. **Permiso dentro de la consulta:** el servicio recibe la vista como argumento obligatorio y filtra por su cartera en el `WHERE` (Prisma `where`), igual que lo que hoy recorta `servir.py`; si el recurso no es de la persona, 404 como si no existiera. La escritura y su línea de rastro, en la misma transacción. Errores con `HttpException` y el texto exacto de `servir.py` (el filtro global les da la forma). Al añadir rutas, `pnpm --filter @ro/api test -u` y revisa el diff de `src/permisos/rutas-permisos.txt` en el mismo commit. Prohibido comprobar puestos, personas o carteras a mano en el controlador o el servicio: si la declaración no llega, se amplía el motor en `src/permisos/` (y su prueba), no la ruta. `rutas-declaradas.spec.ts` lo vigila y no se relaja.
2. Añade sus rutas a `v2/apps/api/src/legado/rutas-en-nest.ts`.
3. `bash migracion/puerta.sh f5 --rapido` para iterar; `bash migracion/puerta.sh f5` para cerrar.
4. VERDE → commit «F5.x · <grupo> en Nest». ROJO tras 3 intentos → plan B, en este orden: (a) `git switch -C intento/<grupo>` (los cambios sin commit viajan contigo), `git add v2/ && git commit -m "intento <grupo>"` (solo `v2/`, nunca `PROGRESO.md`); (b) `git switch migracion/v2` (vuelve sin el módulo y con `rutas-en-nest.ts` como estaba; `PROGRESO.md` sigue con tus notas); (c) `git status` limpio salvo `PROGRESO.md`, `NOTAS_NOCHE.md`, `PENDIENTES_LOGICA.md` y `PLAN_VUELTA.md`; nunca `git clean` ni `git stash`; ⚠ y siguiente. Si ya hay commit del módulo en `migracion/v2` (lo hiciste por poco contexto, y viaja a `intento/<grupo>` con el paso (a)), el plan B quita a mano sus rutas de `rutas-en-nest.ts` en un commit «F5.x · <grupo> vuelve al proxy».
F5.1 (identidad) es la guarda global de las rutas de Nest: `RO_IDENTIDAD=local|access` como `despliegue/acceso_cf.py`. En `access`, la persona sale SOLO del JWT `Cf-Access-Jwt-Assertion` con su firma (claves del equipo), `aud` = `RO_CF_AUD`, emisor y caducidad comprobados, igual que `acceso_cf.py`; nunca de la cabecera del correo, ni de `X-RO-Yo`, `?yo=`, la galleta `ro_yo` o `X-Forwarded-*` (detrás de Next todo llega desde 127.0.0.1: la IP no prueba nada). Prueba e2e con curl: JWT falso, sin firma, con otro `aud` y caducado → 403; `X-RO-Yo: tomas` sin JWT → 403; las rutas que siguen en el proxy las sigue comprobando servir.py. Vive en `src/permisos/` (ahí sí se leen puestos; `rutas-declaradas.spec.ts` lo prohíbe fuera). **Rastro con dos escritores:** al terminar el escritor de «ver como», prueba de punta a punta (NO va en `test/*.e2e-spec.ts`: `puerta.sh` lanza todos los `*.e2e-spec.ts` contra `ro_app`; va en un fichero nuevo `migracion/pruebas_rastro_dos_escritores.sh`, que se niega a arrancar si `DATABASE_URL` no acaba en `/ro_esc` y al final para su legado y su Nest de 8784 y 4004; contra la base aparte `ro_esc`: `contrato_escritura.py base-limpia ro_esc`, con un legado y un Nest propios sobre ella en otros puertos, p. ej. 8784 y 4004; **nunca contra `ro_app`**) de 50 altas MEZCLADAS en el rastro a la vez (25 por Nest, 25 por el legado vía servir.py, en paralelo), y después `/api/rastro/verificar` → «ok» con cero huecos ni huellas rotas. Si falla, es el candado o la hora (ver la Guía de traducción): no sigas a F5.2 sin esto. Si F5.1 sale ⚠, F5.2–F5.9 van a ⚠ sin intentarlo.

## F5.10 · Fallos pendientes de lógica

Lista: `migracion/PENDIENTES_LOGICA.md` **juntada** con `~/RO_MIGRACION/PENDIENTES_LOGICA.md` si existe (por id; para un id en las dos manda la columna Estado del Mac, que es la que actualiza Astra; las filas de una sola se suman). Escribe el resultado en `migracion/PENDIENTES_LOGICA.md` y trabaja sobre ese. Regla de Tomás: lo que no quedó arreglado en la app de hoy se arregla aquí sí o sí. Orden: **L-01 y L-21 primero** (tumban el servidor), luego seguridad → datos → funcional → presentación. D1–D8 ya están contestadas (tabla «Decisiones de Tomás»): aplica su respuesta; lo que diga «pendiente» no se toca y va al informe. Los `arreglado hoy` / `ya estaba`: solo comprobar que su prueba pasa en la app nueva. Reloj: hasta 2 h 30 antes del fin (los de seguridad van primero en el orden). Va ANTES de mudar rutas (F5.1–F5.9): todas las rutas siguen por el proxy, así que se arregla en `servir.py`. Intentos: 3 **por fallo**, no para todo el paso, contados en «Intentos y notas» de PROGRESO.md («F5.10 · L-07 · intento 2 · …»).
**Los ficheros que juzgan no se tocan esta noche** (tienen huella y se restauran por la mañana): ni los `pruebas_*.py` que ya existen ni `despliegue/pruebas_noche.py`. Una prueba nueva o cambiada va en un fichero NUEVO: `migracion/pruebas_L-<n>.py` o `despliegue/pruebas_solidez_N-<n>.py`. Si un fallo solo se arregla cambiando uno que juzga (L-17, L-28), estado `pendiente: toca un fichero que juzga (lo cambia Tomás de día)`.
Para cada fallo `abierto`:
1. Escribe primero la prueba que lo demuestra y comprueba que FALLA (Vitest en `v2/` si la ruta está en Nest; si sigue en `servir.py` (esta noche, al ir antes de F5.1, todas siguen en servir.py), Python en su fichero nuevo `migracion/pruebas_L-<n>.py`).
2. Arréglalo donde viva esa noche: el módulo de Nest si la ruta ya se mudó; `servir.py` (o su enchufe) si sigue por el proxy; si es de permisos, en `reglas_permisos.json` (lo leen los dos motores) o en los dos motores a la vez (`permisos.py` y `@ro/permisos`), y vuelve a sacar los vectores con `vectores_permisos.py` para que la paridad siga al 100 %.
3. La prueba pasa. Lo que cambia a propósito va a `~/RO_MIGRACION/excepciones.txt` con `# <id> <motivo>`: rutas (exactas o prefijo con `*`), `tabla:<t>` y `foto:<pantalla>` (ver «Diferencias aceptadas» arriba). Las pruebas Python nuevas se suman a `migracion/baterias.sh`.
4. `bash migracion/puerta.sh f5 --rapido` (o `puerta.sh f2` si F3.1 quedó ⚠) en VERDE → commit «<id> · <qué>» (L-n o N-n) y estado `arreglado en v2 (<commit>)` en la lista. Al acabar cada bloque (seguridad, datos, funcional, presentación), `bash migracion/puerta.sh f5` completa una vez: si sale ROJO, el último arreglo del bloque que lo causa se deshace (plan B).
Tras 3 intentos sin salir con ese fallo: deshaz el arreglo, deja la prueba marcada como pendiente (`it.todo`/`skip` con «L-n»; nunca borrada), estado `pendiente: <motivo>` y siguiente fallo.
Para N-01 a N-12 (fuentes), sigue `PLAN_MAESTRO.md` §2.5: primero N-01: la tabla `fuente_lectura` ya entró en F2.2; aquí solo se conecta `fuentes/lectura.py › leer()` (empieza por el `con_cache` de Holded), con su prueba. Luego cada lector pasa por `leer()` con una prueba de «API falsa caída → último dato bueno + aviso, ningún 0» en su fichero nuevo `despliegue/pruebas_solidez_N-<n>.py` (súmalo a `baterias.sh`; `pruebas_noche.py` no se toca). Para N-10, escribe `migracion/nunca_ceros.mjs` (cuenta `?? 0` y `|| 0` sobre cifras pintadas en `modulos/` y `v2/apps/web/src`; guarda la cifra de partida en `~/RO_MIGRACION/nunca_ceros.txt` y falla si sube) y súmalo a `baterias.sh`. Ningún lector se prueba contra la API de verdad: siempre con una falsa en 127.0.0.1 o un módulo de mentira.
Cuando arregles N-13, quita su línea de `~/RO_MIGRACION/excepciones_solidez.txt`.
Los fallos `arreglado hoy`: comprueba que su prueba pasa también en la app nueva (`--pantallas` o la ruta); si no, trátalo como abierto.

## F5.11 · Escalados sobre Postgres

Escribe `migracion/escalados.py` (`puerta.sh f7` ya lo lanza si existe; no la toques):
1. Base limpia `ro_esc` (`contrato_escritura.py base-limpia ro_esc`).
2. Legado aparte en 127.0.0.1:8783 sobre ella, con los bucles ENCENDIDOS (sin `RO_AVISOS_SIN_BUCLE`) y TODAS las salidas apagadas (sin `RO_ENVIOS_REALES` ni `RO_CLICKUP_REAL`).
3. Un `RO_RELOJ` más tarde que el plazo de una alerta y de una regla de aviso automático (créalas como lo hacen `pruebas_seguridad.py › alertas_a8` y `avisos_automaticos`).
4. Comprueba por la API (`/api/canales/campana` de cada persona) que el «sube a X» llega a la persona que toca según `cadena_escalado` y `avisos_programados.escalar()`, **una sola vez** aunque pasen dos vueltas del bucle, y que lo marcado «Lo tengo» no escala.
5. Lo paras. Nunca contra `ro_app`.

Si algo no escala sobre Postgres y en SQLite sí, es un fallo de `despliegue/base.py`: arréglalo con su prueba. Plan B: apuntarlo como bloqueo para el piloto.

---

## F6.1 · shadcn, ctx y puente

Lee `v2/apps/web/AGENTS.md` (esta versión de Next tiene cambios: consulta `node_modules/next/dist/docs/` antes de escribir rutas o layouts). Y las reglas de oficio de React de `.cursor/rules/20-frontend-next.mdc` (guía completa en `v2/.agents/skills/vercel-react-best-practices/`).
1. `pnpm dlx shadcn@4.17.0 init -y` en `v2/apps/web`: lee `components.json` (ya está en el repo, estilo `base-nova`; si `init` pregunta si lo sobrescribe, quédate con el nuestro) (y `add -y …` con la misma versión: sin `-y` se queda esperando una respuesta; necesita red). Versión: `shadcn@4.17.0` (estilo `base-nova`), siempre la misma en `init` y en `add`. Nunca `@latest`. Los cambios que haga `add` en `package.json` y `pnpm-lock.yaml` (sus dependencias, con versión exacta) se aceptan y van en el mismo commit; nada más cambia de versión. `globals.css` no se reescribe: si el init lo cambia, devuélvelo como estaba (sin preflight) y lleva los tokens nuevos que necesite shadcn a `src/styles/ro-tema.css`, con los colores de RO. Añade sidebar, command, dropdown-menu, dialog, sheet, tooltip, tabs.
2. `src/lib/ctx.ts`: `crearCtx` de `app.js` en TypeScript, los 43 campos (cuenta en `migracion/inventario/RESUMEN.md`; manda esa; lista en `migracion/inventario/ctx.json`), mismo comportamiento.
3. `PantallaPuente`: importa `/legacy/modulos/<fichero>` en el navegador y llama a `render(contenedor, ctx)`. El import es en tiempo de ejecución, no de compilación: `import(/* webpackIgnore: true */ /* turbopackIgnore: true */ url)`; si no, Turbopack intenta empaquetar `/legacy` y falla el build (o mete una copia vieja). Los módulos de hoy se importan entre sí con rutas relativas (`import('./decisiones.js')`): por eso se cargan desde `/legacy/modulos/`, nunca copiados a otra carpeta.
4. CSS (Tailwind 4): `estilos.css` va sin capa y `globals.css` declara `@layer theme, base, components, utilities`. Lo que no está en una capa gana SIEMPRE a lo que está en una, sea cual sea la especificidad: si una utilidad de Tailwind «no hace nada», es que `estilos.css` toca esa propiedad; no lo arregles con `!important` ni sacando Tailwind de su capa, usa la clase de `estilos.css`. `box-sizing: border-box` ya lo pone `estilos.css` (`* {…}`), y es lo que shadcn espera sin preflight.

## F6.2 · Carcasa en React (detrás de una variable)

La carcasa vive en `src/app/carcasa/page.tsx`. Con `RO_CARCASA=1` en el build, `next.config.ts` reescribe «/» a la carcasa sin cambiar la dirección (ya está hecho); sin la variable, «/» sigue siendo el front de hoy. Así `capturar.mjs`, `/api/elegir` y los `fetch` relativos funcionan igual que hoy. No crees `src/app/page.tsx`: taparía el front de hoy. La carcasa con LAS MISMAS clases de `estilos.css` y el mismo DOM que pintan hoy `app.js` + `carcasa.js`: menú por puesto, cabecera, ⌘K y «/», «ver como» (solo lectura), menú móvil, «¿Quién eres?» en local. Mismas direcciones `#/pantalla`. Las 42 pantallas (cuenta en `migracion/inventario/RESUMEN.md`; manda esa) por el puente. Para compararla: `RO_CARCASA=1 bash migracion/puerta.sh f6 --rapido` (la puerta reinicia web sola y la variable entra en el `next build`), hasta ≤ 0,5 %. Al terminar, `bash migracion/servicios.sh reiniciar web` sin la variable.

## F6.3 · Carcasa por defecto

En `next.config.ts`, que la carcasa vaya encendida por defecto (`process.env.RO_CARCASA !== "0"`) y reinicia web. `bash migracion/puerta.sh f6` en VERDE → commit. Si no: vuelve a `=== "1"` (⚠) y «/» sigue siendo el front de hoy.

## F6.4 · Pantallas en React

Primero, si no existe, `src/components/ro/` (componentes.js en React, mismas clases, mismo DOM; shadcn solo donde la pieza sea equivalente). Luego, una pantalla cada vez, de menos a más riesgo, en este orden (id para `--pantallas`; son las 42 del menú, cuenta en `migracion/inventario/RESUMEN.md`; manda esa; si el inventario trae otra, va donde le toque por riesgo): `componentes` (Componentes), `primera-semana` (Tu primera semana), `mi-perfil` (Mi perfil), `indicadores` (Catálogo de indicadores), `uso-app` (Uso y mejoras), `gasto-ia` (Gasto de IA), `conexiones` (Salud del sistema), `avisos-automaticos` (Avisos automáticos), `envios` (Envíos), `decisiones` (Decisiones y rastro), `en-rojo` (En rojo), `alertas` (Alertas del departamento), `agenda` (Agenda), `reuniones` (Reuniones), `horas` (Horas y productividad), `personas` (Personas), `produccion` (Producción), `incidencias` (Incidencias), `clientes-nuevos` (Clientes nuevos), `informes-mensuales` (Informes mensuales), `salud-crm` (Salud del CRM), `seo-web` (SEO, ficha y webs), `redes` (Redes), `paneles` (Paneles de herramientas), `prospeccion` (Prospección y outreach), `setters` (Mi día del setter), `ventas-ro` (Ventas de RO), `chat-equipo` (Chat del equipo), `asistente-ia` (Asistente IA), `prioridades-cliente` (Prioridades por cliente), `mi-trabajo` (Mi trabajo), `mi-dia` (Mi día), `ficha` (Ficha del cliente), `informe-cliente` (Informe del cliente), `producto` (Dirección de producto), `operaciones` (Dirección de operaciones), `captacion` (Captación, donde vive Paid), `bandeja` (Bandeja), `dinero-cliente` (Dinero por cliente), `panel-direccion` (Panel de dirección), `finanzas` (Finanzas de la empresa), `ajustes` (Ajustes).
El orden es de menos a más riesgo y no se cambia. Prioridad de la entrega (Operaciones → Accounts → Paid): cuando dos pantallas empatan, va antes la de Operaciones, luego las de cartera de Accounts y luego Paid. Para cada una: rehacer → fotos solo de esa pantalla (`--pantallas <id>`, todas las personas y los dos tamaños) → ≤ 0,5 % y contrato y baterías verdes → sustituye al puente y commit. Si no, se queda el puente (⚠ esa pantalla) y siguiente. Respeta las reglas de presentación de la nota de Astra y de la entrega (desconocido ≠ cero ni verde, siglas con `title`, colores solo con evidencia, tablas compactas con el detalle plegado, fuegos ≠ clientes rojos): no se cambian, se copian. Los pendientes de UI de `entrega/VERIFICACION_FINAL_UI_CURSOR.md` no se arreglan en React esta noche: la pantalla se copia como está hoy.

---

## F7.1 · Contenedores

```bash
bash migracion/servicios.sh parar web api
cd v2 && docker compose --profile completo up --build -d && cd ..
```
Que los contenedores arranquen y respondan: la web del contenedor está en 127.0.0.1:3100 (`/vivo`, `/api/elegir`). La API del contenedor llega al legado del Mac en 8771 con `RO_LEGADO_URL` (ya en el compose). Después, `cd v2 && docker compose --profile completo stop api web`: la puerta f7 se pasa siempre contra los servicios locales (los vuelve a arrancar ella). Plan B: apuntar qué falla en el contenedor (p. ej. `RO_LEGADO_URL`, «Host no permitido») como bloqueo para el piloto.

**Paquete de fuentes privadas (N-23).** Los contenedores y Render necesitan las fuentes privadas que la entrega sacó del código (`despliegue/empaquetado.py`: `PRIVADOS_REQUERIDOS` y `PRIVADOS_OPCIONALES`). Nunca van a git ni a `v2/`. Esta noche solo se preparan en local:
```bash
P=~/RO_MIGRACION/paquete/$(date +%Y%m%d-%H%M)        # carpeta nueva: los dos destinos tienen que estar vacíos y fuera del repo
R=~/RO_MIGRACION/ref                                  # la copia congelada de F1.3: sin .git, v2 ni node_modules (desde «.» copiaría todo node_modules como «código»)
python3 despliegue/empaquetado.py plan "$R" > ~/RO_MIGRACION/paquete_plan.json   # qué entra como código
python3 despliegue/empaquetado.py codigo "$R" "$P/codigo"
python3 despliegue/empaquetado.py privado "$R" "$P/privado" --codigo-destino "$P/codigo"
```
Antes, `df -h ~` (la entrega vio el disco al 99 %): si quedan menos de 5 GB, no lo prepares; apúntalo como bloqueo y sigue. El código de `$P/codigo` es solo el destino que exige `privado`: la imagen de verdad la arma `despliegue/preparar_contexto.sh`.
Solo lee; escribe en `~/RO_MIGRACION/paquete/` (carpeta 700, ficheros 600, con `manifiesto_privado.json`). En el chat y en el informe, solo el resumen que imprime (número de ficheros y `funciones_fuentes`), nunca contenidos. Si `privado` dice «Faltan fuentes privadas obligatorias», se apunta cuáles faltan (sin valores) y sigue. Sale siempre `listo_para_desplegar: false` (la hidratación en destino aún no está hecha): es lo esperado. Va al informe como **bloqueo para el piloto**: Tomás sube el paquete al destino de la nube (aún no existe) y se ensaya su hidratación. Nunca `git add` de nada de `~/RO_MIGRACION/paquete/`.

## F7.2 · render.yaml

`v2/render.yaml` a partir de `despliegue/render.yaml` (y `PLAN_MAESTRO.md` §2.7–2.12): `ro-web` (Next, el ÚNICO servicio público), `ro-api` (Nest, **servicio privado** `type: pserv`, `RO_LEGADO_URL` al servicio privado del legado), `ro-legado` (**privado**) (la imagen de `despliegue/Dockerfile`, **una sola copia**, con la tubería y los bucles), la base en **Supabase** (no una base de Render: grupo `ro-base` con `DATABASE_URL` `sync: false`, Session pooler 5432, y `RO_PG_CA` para `ro-api`; ver `despliegue/render.yaml` y DESPLIEGUE.md T1b). Sin llaves. Cloudflare Access delante, como en `despliegue/DESPLIEGUE.md`. El grupo `ro-llaves` completo (comprueba con `python3 migracion/llaves_nube.py`: nada «FALTA en render.yaml») y solo en `ro-legado`. Sin `RO_AVISOS_SIN_BUCLE` (los escalados necesitan los bucles). El vigía, como cron o dentro del legado (N-18). ClickUp real apagado. En `ro-api`: `RO_ENTORNO=produccion`, `RO_IDENTIDAD=access`, sin `RO_RELOJ` (la API no arranca si no), y `preDeployCommand: pnpm --filter @ro/db migrate:deploy` (si falla, no se despliega). El cron `ro-copias` (cada hora, `despliegue/entrada.sh copias`, `RO_COPIAS_DIAS=7`, grupo con `RO_R2_*` y `RO_B2_*`), como en `despliegue/render.yaml` (§2.10). **Nunca ejecutes `llaves_nube.py --exportar`**: es de Tomás. `ro-legado` necesita también el paquete de fuentes privadas de F7.1 (N-23): apunta en `v2/render.yaml`, con un comentario, que se monta aparte (disco privado o secreto de fichero) y que no viene en la imagen; no inventes su destino.

## F7.3 · Informe y puerta 7

`migracion/INFORME_NOCHE.md`, para Tomás, en castellano y frases cortas:
1. Resumen en 5 líneas: qué funciona en la app nueva, qué se ha mudado a Nest y a React, qué sigue por el proxy o el puente.
2. Puertas: cada una con VERDE/ROJO y su informe.
3. Bloqueos para el piloto (Astra): permisos con datos reales, restauración, fuentes, funciones críticas; excepciones conocidas; fallos de seguridad de `PENDIENTES_LOGICA.md` sin arreglar.
   Y una tabla con cada fallo de `PENDIENTES_LOGICA.md`: arreglado (dónde y commit) o pendiente (por qué).
4. Revisiones: copia aquí `~/RO_MIGRACION/revisiones/PARA_EL_INFORME.md` si existe (pasos que la revisión aún ve mal o con algo pendiente).
5. Preguntas para Tomás.
6. Pasos de la mañana, exactos.
Después, `bash migracion/puerta.sh f7`.

## F7.4 · Cierre

Commit, `git push origin migracion/v2`, `ESTADO: TERMINADO` en PROGRESO.md, commit y push.

---

## Guía de traducción (Python → TypeScript, JS de hoy → React)

Una traducción que «funciona» pero redondea, ordena o cuenta distinto no da error: da una diferencia en la puerta a las 4 de la mañana y tres intentos perdidos. Estas son las trampas conocidas. Lo que se puede resolver con código ya está en **`@ro/compat`** (`v2/packages/compat`), probado contra Python de verdad (`pnpm --filter @ro/compat test`). **Úsalo; no lo reescribas.**

**Números**
- `round(x, n)` redondea al par: `round(2.5) = 2` y `round(0.125, 2) = 0.12`. → `redondear(x, n)`.
- `f"{x:.2f}"` y `f"{x:,.0f}"` → `formatoFijo(x, 2)` y `formatoFijo(x, 0, true)`. Nunca `toFixed` directo.
- `/` siempre da float. `//` y `%` redondean hacia abajo → `divEntera`, `modulo`. `int(x)` trunca → `Math.trunc`.
- En las respuestas, 12.0 y 12 valen lo mismo: el contrato los compara por valor. Dentro de una huella o de un texto, no: `flotante(12)` sale como «12.0».

**Textos**
- `texto[:140]` y `len(texto)` cuentan caracteres. JS cuenta unidades UTF-16 y parte los emojis. → `cortar`, `longitud`.
- `sorted()` ordena por punto de código. → `ordenarComoPython` (estable, con tuplas y `reverse` igual que Python). **Nunca `localeCompare`.**
- `.split()` sin argumento corta por grupos de espacios y quita los vacíos → `s.trim().split(/\s+/).filter(Boolean)`. `.strip()` → `.trim()`.
- Expresiones regulares: en Python `\w`, `\d` y `\b` entienden acentos y la ñ; en JS no.
  - Usa la bandera `u` y `[\p{L}\p{N}_]` donde Python ponía `\w`.
  - `re.match` solo mira el principio del texto.
  - En `re.sub`, el `\1` de Python es `$1` en JS.

**Verdad y ausencia**
- `[]`, `{}` y `""` son falsos en Python. En JS, `[]` y `{}` son verdaderos.
  - `if lista:` → `if (lista.length)`.
  - `x or y` con listas o diccionarios necesita la comprobación explícita.
- `d.get(k, defecto)` devuelve `None` si la clave existe con `None`. → `k in d ? d[k] : defecto`, no `d[k] ?? defecto`.
- `None` es `null`, nunca `undefined`: `JSON.stringify` borra las claves `undefined`, y el contrato dice «falta en la nueva».
- Comparar `None` con un número da `TypeError` en Python. Si el código de hoy no lo hace, el tuyo tampoco.

**Fechas y horas**
- La hora de negocio es la de Madrid y respeta `RO_RELOJ`: `horaMadrid()`, `hoyMadrid()`.
- Las horas de la base son texto UTC «AAAA-MM-DD HH:MM:SS»: `ahoraBaseUtc()`.
- Nunca `new Date().toISOString()` en una respuesta (milisegundos y «Z»). Nunca un `Date` en una respuesta.
- `weekday()` empieza el lunes en 0. `getDay()` empieza el domingo en 0.

**JSON, base y respuestas**
- Las claves salen tal cual, en `snake_case`. Ni camelCase ni claves nuevas.
- Prisma devuelve `BigInt` y `Decimal`: conviértelos antes de responder (`JSON.stringify` revienta con `BigInt`, y `Decimal` sale como texto `"12.50"` donde `servir.py` da el número `12.5`): rompe el contrato.
- 0/1 se quedan como números, no `true`/`false`.
- Las respuestas se comparan ya leídas, así que los espacios del JSON dan igual. **Las huellas no:**
  - el rastro encadena `sha256(previa + json.dumps(campos, ensure_ascii=False, sort_keys=True))` → `huellaRastro(previa, campos)`, idéntica byte a byte;
  - además, Nest y el legado escriben en la MISMA tabla a la vez, así que todo alta en el rastro va dentro de una transacción con el MISMO candado que `base.py`: `SELECT pg_advisory_xact_lock(7262)` como primera orden DENTRO de `prisma.$transaction(async (tx) => …)` (el de transacción, `xact`; nunca `pg_advisory_lock` de sesión, que con el pool se queda cogido en otra petición). Si no, dos escritores rompen la cadena.
  - Después de portar el rastro, `/api/rastro/verificar` tiene que seguir diciendo «ok» con filas escritas por los dos.
  - La huella lleva `[id, creada, quien, como, coleccion, accion, clave, datos, motivo, anula_a, origen]` (`_registrar` en `servir.py`). `creada` la pone la BASE (el `@default` de `schema.prisma`: texto UTC «AAAA-MM-DD HH:MM:SS», sin milisegundos): no la mandes desde JS ni con `now()`; insértala sin ella, léela de vuelta y mete en la huella ese mismo texto. `id` y `anula_a` vienen de Prisma como `BigInt`: a `Number` antes de la huella (si no, `json.dumps` y `JSON.stringify` no coinciden).
- Los mensajes de error y los códigos se copian tal cual, también el 500 genérico «Error interno (el detalle queda en el registro del servidor).».

**Búsqueda**
- `/api/buscar` no usa SQL: `buscar_en()` busca en memoria, sin tildes ni mayúsculas (`_sin_tilde`), todas las palabras, y ordena por «empieza por» / «palabra que empieza» / resto. Pórtalo igual. Nunca `LIKE`/`ILIKE` de Postgres: distingue tildes, `ILIKE` no es el `LIKE` de SQLite (que ya ignora mayúsculas en ASCII) y `%`/`_` del texto buscado serían comodines.

**Del JS de hoy a React (fase 6)**
- Mismo DOM y mismas clases (`estilos.css`); shadcn solo donde la pieza es equivalente.
- Si hoy se pinta HTML desde un texto, en React también, con el mismo saneado: nada nuevo sin sanear.
- «Hoy», mes y trimestre salen de `ctx` (`ctx.hoy`, `ctx.fechas`), nunca de `new Date()` en el navegador (L-19).
- Ningún `?? 0` / `|| 0` sobre una cifra que se pinta (§2.5 del plan).

**Si una diferencia no se explica con esta lista,** antes de cambiar el código nuevo léete el viejo línea a línea buscando la regla que falta, y añádela aquí («Guía de traducción», con la fecha) para la vuelta siguiente.

