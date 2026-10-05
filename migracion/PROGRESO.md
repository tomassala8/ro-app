# Cuaderno de la noche · migración 4→5-oct-2026

ESTADO: EN CURSO

Leyenda: ⬜ pendiente · 🔄 en curso · ✅ hecho (puerta verde) · ⚠ plan B aplicado (ver motivo).
Cada paso: su sección en `migracion/PLAN_NOCHE.md` (el plan de la noche, escrito y revisado antes) y el detalle en `migracion/PROMPTS_CURSOR.md` (mismo código). Hasta 3 intentos con enfoques distintos; luego, su plan B.
Formato al cerrar: `✅ F1.2 · 23:14 · <resultado en una línea> · puerta: ~/RO_MIGRACION/puertas/f1.md`
Mientras dura: `🔄 F2.4 · 01:10 · intento 2/3 · <qué estás probando>` (el número de intento va en la línea del paso: si te relanzan, sigues por ahí). En F5.10, con el fallo en curso: `🔄 F5.10 · 01:10 · L-03 · intento 2/3 · <qué>`.
Al retomar, arranca solo lo de fases cerradas: `viejo` tras F1.4, `legado` tras F2.3, `api` y `web` tras F3.1. Nunca un `servicios.sh arrancar` a secas antes de F2.3: crearía tablas en `ro_app` vacía.

Fin de la noche: 2026-10-08 02:01 (`RO_FIN_NOCHE`)

Cortes del reloj (se miran con `date` al empezar CADA vuelta, no solo al principio):
- F5.10: hasta **2 h 30** antes del fin (L-01 y L-21, luego los de seguridad, van primero; no tienen prórroga). Lo que quede → `pendiente: sin tiempo` y al informe.
- F5.11: hasta **2 h** antes del fin.
- F5.1–F5.9: hasta **1 h 30** antes del fin. Lo que quede → ⚠ «sin tiempo» (sus rutas siguen por el proxy, que funciona).
- Fase 6: hasta **1 h** antes del fin.
- Fase 7: la última hora, pase lo que pase.

## En curso

Siguiente: F1.7 (reabierto a las 06:47 por el mismo error). F1.6 cerrado otra vez a las 08:20.

Fotos (decisión Tomás 5-oct 06:12), lista en `~/RO_MIGRACION/capturas/personas_fotos.txt`. Una persona por (puestos, ámbito, módulos, ver como, permisos, clientes). 25 de 32.
- candela, carla, casiana, dana, facundo, lucia, natalia: account, cada uno su cartera (8, 10, 7, 5, 6, 12, 9 clientes).
- gustavo (especialista_ghl, 13 clientes) y miguel_vargas (especialista_ghl, 0): carteras distintas.
- alejandro_montalvo por producción (camilo, emanuel, manuel: mismo rol, ámbito, módulos y clientes).
- anderson por redes+producción (belen, kimberlyn).
- setter_ana por setters (setter_javier).
- carlos_viur por web (macarena).
- Únicos: sofia (administración), tomas (dirección), yessica (jefa crm), valeria (jefa publicidad), jeronimo (jefa seo), mili (operaciones), eulimar (outreach), constanza (proyectos+account), lara (redes+outreach), cecilia (rrhh), agustina (técnico altas), lina (trafficker).

## Fase 1 · Referencia

- ✅ F1.1 · 02:03 · inventario 42 pantallas, 37 rutas (22 GET, 15 POST), 125 enchufes, 66 tablas, 21 puestos, 41 tipos, 107 componentes; 0 altas/bajas de pantallas, rutas, tablas y componentes; commit a97b648. Puerta f1 en F1.7. Plan B: si `--comparar` falla, inventario sin comparar y apuntarlo.
- ✅ F1.2 · 02:05 · escáner salida 1, 38 ficheros, 0 en v2/; commit 5d007f1 (solo CARPETAS_FUERA). Plan B: dejarlo como estaba y apuntar los falsos positivos.
- ✅ F1.3 · 02:12 · instantánea `006bc44` (1056 ficheros); privados `595fa97` (64 fuera, siguen en el disco); plan juntado `f8bb955` + `8dc3667`; merge `b542cae` (árbol intacto); inventario `e4b0e08`; copias ok; `ref/` 306M. Puerta f1 en F1.7. Plan B: si el escáner marca algo, NO se commitea ese fichero; se apunta y se sigue.
- ⬜ F1.3 Instantánea del código del Mac en la rama `migracion/v2` (tras el escáner; el código hasta el corte 675 de la entrega ya está en la rama: solo lo cambiado en el Mac después, fichero a fichero; los privados que la entrega sacó de git no se vuelven a añadir nunca), las ramas de `migracion/RAMAS_A_JUNTAR.txt` juntadas (PR #2, #3 y #4 del 4-oct), copia de la base y copia congelada de la app de hoy en `~/RO_MIGRACION/ref`. Plan B: si el escáner marca algo, NO se commitea ese fichero; se apunta y se sigue.
- ✅ F1.4 · 08:11 · 2100 png (25 personas × 42 pantallas × 2 tamaños), 0 errores, 0 fotos < 15 KB, mediana 802 ms; 31 claves ≥ 15 s pintadas · puerta: ~/RO_MIGRACION/puertas/f1.md
- ✅ F1.5 · 06:18 · 45 casos, 14 rutas, ensayo rc=0 contra la copia en 8780 · comprobado otra vez 08:19 (reabierto 06:47 por error de la maquinaria, nota de Claude para F2.2: no se rehace; la puerta f1 de 08:05 ya repitió los 45 casos). Plan B: ninguno; es imprescindible.
- ✅ F1.6 · 06:31 · 169 verdes, 38 heredadas, pasada 2 rc=0 · comprobado otra vez 08:20 (reabierto 06:47 por error de la maquinaria, nota de Claude para F2.2: no se rehace; la puerta f1 de las 08:05 acabó a las 08:10 en Verdes: 169 · heredadas en rojo: 38 · ROJAS: 0). Plan B: las que fallan ya contra la app de hoy se apuntan y se quedan fuera (no se arreglan esta noche).
- 🔄 F1.7 · 06:39 · puerta f1 VERDE (9/9) · puerta: ~/RO_MIGRACION/puertas/f1.md. Push de la rama. Plan B: ninguno; repetir lo que falte. · 06:47 · intento 2/3 · revisión: rehacer con migracion/PLAN_VUELTA.md

## Fase 2 · Base Postgres y la app de hoy sobre ella

- 🔄 F2.1 · 06:42 · intento 1 · `avisos` de la tubería → `tuberia_avisos` en `despliegue/estado.py`; prueba temporal count 1; solidez 69/95, igual que F1.6. Plan B: dejarla y copiar solo `local.db` (la tubería empieza vacía en Postgres); apuntarlo. · 06:47 · intento 2/3 · revisión: rehacer con migracion/PLAN_VUELTA.md
- ⬜ F2.2 Si el inventario trae tablas o columnas nuevas: `rehacer_base.sh` y revisar el diff de `schema.prisma`. Plan B: ninguno; sin esto se pierden columnas.
- ⬜ F2.3 Postgres arriba, `pnpm db:deploy`, copia «cuadrada» de `local.db.antes` (y `tuberia.db.antes`), `publicacion.py publicar data`.
- ⬜ F2.4 Legado (servir.py sobre Postgres) arrancado y `bash migracion/puerta.sh f2` en VERDE, arreglando `despliegue/base.py` lo que haga falta (commits propios, cada uno con su prueba). Plan B: rutas que no cuadran tras 3 intentos → `~/RO_MIGRACION/excepciones.txt` con el motivo; apuntadas como bloqueo para el piloto.

## Fase 3 · La app nueva entera (por el proxy)

- ⬜ F3.1 `servicios.sh arrancar` (api y web) y `bash migracion/puerta.sh f3` en VERDE. Push. Plan B: arreglar fontanería del proxy; si no, apuntar y seguir con la fase 4. **Si F3.1 queda ⚠: F5.1–F5.9 y F6.x → ⚠ sin intentarlo; F5.10 se cierra con su prueba + `puerta.sh f2`.**

## Fase 4 · Motor de permisos en TypeScript

- ⬜ F4.1 `permisos.py` → `v2/packages/permisos` función a función, con «ver como» explícito, y enchufarlo como el motor de `v2/apps/api/src/permisos/` (sustituye a `MotorSinPortar`). `bash migracion/puerta.sh f4` al 100 %. Máximo 90 minutos. Plan B: apuntar los vectores que fallan y saltar los grupos de rutas (⚠ en F5.1–F5.9). F5.10 (arreglando solo en el legado: `servir.py`, `permisos.py`, `reglas_permisos.json`) y F5.11 siguen.
- ⬜ F4.2 Pruebas de permisos que impiden volver atrás (anexo de `PENDIENTES_LOGICA.md`, punto 8), en `test/*.e2e-spec.ts` (las lanza `puerta.sh` f3/f5/f6/f7). Si F4.1 queda ⚠, F4.2 se hace igual: lo que necesite el motor en TypeScript va a `it.todo('F4.1 ⚠')`. Se cierra con `bash migracion/puerta.sh f3` en VERDE. Plan B: `it.todo` con su motivo.

## Fase 5 · Rutas a Nest (un grupo cada vez; cada uno: módulo + RUTAS_EN_NEST + puerta f5)

Primero los fallos y los escalados (Tomás, 4-oct: los fallos se arreglan sí o sí; mudar rutas a Nest no cambia nada de lo que ve el equipo). Las rutas que no están en ningún grupo de F5.1–F5.9 (muchas rutas nuevas de enchufes de la entrega) se quedan por el proxy: está bien así, para el equipo no cambia nada. Los «Pendientes de producto de la entrega» de `PENDIENTES_LOGICA.md` no se construyen esta noche: van al informe. Mientras tanto todas las rutas siguen por el proxy, así que en F5.10 se arregla en `servir.py` (y en los dos motores si es de permisos).
- ⬜ F5.10 Fallos pendientes (L-01…L-49 del hilo de feedback y N-01…N-23; L-16 ya cerrado por la entrega; L-01 y L-21 primero; D1–D8 ya contestadas, lo «pendiente» no se toca) (N-01 a N-12 son la copia propia de las APIs y «nunca ceros»: `PLAN_MAESTRO.md` §2.5) de `migracion/PENDIENTES_LOGICA.md` (o de `~/RO_MIGRACION/PENDIENTES_LOGICA.md` si existe), de seguridad a presentación: cada uno con su prueba, su commit «<id> · …» (L-n o N-n) y su estado en la lista. Por fallo: su prueba + `puerta.sh f5 --rapido`; la puerta completa, una vez al acabar cada bloque (seguridad, datos, funcional, presentación). Las pruebas nuevas o cambiadas van en ficheros NUEVOS (`migracion/pruebas_L-<n>.py`, `despliegue/pruebas_solidez_N-<n>.py`); nunca se tocan los `pruebas_*.py` ni `pruebas_noche.py` que ya existen (juzgan). Intentos: hasta 3 **por fallo**, no por paso, contados en «Intentos y notas» («F5.10 · L-07 · intento 2 · …»); la línea del paso dice qué fallo llevas. Reloj: hasta 2 h 30 antes del fin. Plan B por fallo: se queda como estaba, con la prueba marcada pendiente, y va al informe (seguridad = bloqueo para el piloto).
- ⬜ F5.11 Ensayo de escalados sobre Postgres (`migracion/escalados.py`, `PLAN_MAESTRO.md` §2.9): alerta y aviso automático vencidos → «sube a X» a la persona correcta, una vez. Se cierra con `python3 migracion/escalados.py` saliendo con 0. Plan B: apuntar qué no escala como bloqueo para el piloto.

Después, las rutas a Nest:
- ⬜ F5.1 identidad (guarda global) + escritor del rastro de «ver como» (`RASTRO_VER_COMO`) + sesion. **Si F5.1 queda ⚠, F5.2–F5.9 → ⚠ sin intentarlo** (sin identidad ni rastro, toda ruta de Nest falla) y a la fase 6.
- ⬜ F5.2 rastro (lectura, escritura y verificar)
- ⬜ F5.3 datos (`/api/modulo/**`)
- ⬜ F5.4 clientes y logos
- ⬜ F5.5 buscar, contadores e indicadores
- ⬜ F5.6 perfil y preferencias
- ⬜ F5.7 decisiones y opiniones
- ⬜ F5.8 ajustes y ver_dato
- ⬜ F5.9 acciones, avisos y canales
Detalle de los nueve: sección «F5.x» de `PROMPTS_CURSOR.md`.
Plan B de cada grupo: quitar sus rutas de `RUTAS_EN_NEST` (vuelven al proxy), guardar el módulo en la rama `intento/<grupo>` (cómo, en «F5.x»; también si ya hiciste commit), ⚠ y siguiente grupo.
Reloj: ver «Cortes del reloj» arriba (grupos hasta 1 h 30 antes del fin).

## Fase 6 · Front en React + shadcn

- ⬜ F6.1 shadcn init con versión fijada (sin tocar el tema ni el CSS sin preflight; tokens nuevos a `ro-tema.css`), `src/lib/ctx.ts` (43 campos; la cuenta que manda está en `migracion/inventario/RESUMEN.md`) y `PantallaPuente`.
- ⬜ F6.2 Carcasa en React en `src/app/carcasa/`, con el puente para las 42 pantallas (cuenta en `migracion/inventario/RESUMEN.md`; manda esa); con `RO_CARCASA=1` «/» la enseña sin cambiar la dirección (sin la variable, «/» sigue siendo el front de hoy); fotos con la variable iguales que las de hoy.
- ⬜ F6.3 La carcasa encendida por defecto y `bash migracion/puerta.sh f6` en VERDE. Plan B: la carcasa se queda apagada (solo con `RO_CARCASA=1`) y «/» sigue siendo el front de hoy.
- ⬜ F6.4 Pantallas en React, una cada vez, de menos a más riesgo (lista en PROMPTS_CURSOR.md). Plan B por pantalla: se queda con el puente.
Reloj: hasta 1 h antes del fin; lo que quede → ⚠ «sin tiempo» y a la fase 7.

## Fase 7 · Cierre (la última hora, pase lo que pase)

- ⬜ F7.1 `bash migracion/servicios.sh parar web api` y `docker compose --profile completo up --build`: que los contenedores arranquen y respondan (la web del contenedor, en 127.0.0.1:3100: `/vivo`, `/api/elegir`). Después, `docker compose --profile completo stop api web`: la puerta f7 se pasa siempre contra los servicios locales (los vuelve a arrancar ella). Además, el paquete de fuentes privadas preparado solo en local con `despliegue/empaquetado.py` en `~/RO_MIGRACION/paquete/` (N-23; nunca a git; subirlo es de Tomás y es bloqueo para el piloto). Plan B: apuntar qué falla en el contenedor (p. ej. `RO_LEGADO_URL`, «Host no permitido») como bloqueo para el piloto.
- ⬜ F7.2 `v2/render.yaml` (ro-web, ro-api, ro-legado una sola copia con los bucles y el vigía; `ro-base` es el grupo de entorno con la `DATABASE_URL` de Supabase, Session pooler 5432, no una base de Render), sin llaves, con el grupo `ro-llaves` completo (se ejecuta `python3 migracion/llaves_nube.py`, nunca se edita, y sale con 0), sin `RO_AVISOS_SIN_BUCLE` y con el cron de copias cada hora (§2.10). Plan B: ninguno; es solo escribir.
- ⬜ F7.3 `migracion/INFORME_NOCHE.md` para Tomás (con el estado de cada fallo de `PENDIENTES_LOGICA.md`) y `bash migracion/puerta.sh f7` (incluye el ensayo de restauración).
- ⬜ F7.4 Commit, `git push origin migracion/v2` y `ESTADO: TERMINADO`.

## Intentos y notas

- F1.4 · intento 1 · 8770 responde 200; contrato (64 entradas, 63 carpetas) y vectores (32) ya estaban y cumplen el «sale bien» de los pasos 2 y 3; cerebro 200 en dirección; riesgo 404 en dirección (setters 403: la ruta existe; no es «todo 404»; no se arregla aquí). Fotos: `capturar.mjs` espera `networkidle` (45 s) y, si salta el plazo, el `catch` no guarda la png. Tres `POST /api/uso` con `keepalive: true` (`app.js`) se quedan en vuelo aunque el servidor ya respondió 200: `networkidle` no llega nunca. A los ~6 min, 0 png. No se tocó el repo (F1.4 solo permite L-01). `excepciones_solidez.txt` escrito (N-13). 8770 sigue en una sesión larga (el `nohup` de `servicios.sh` muere al cerrar la orden). El Intento 2 del plan (puerto ocupado / módulo que falta) no cubre este fallo.
- F1.4 · intento 2 · 04:01 una persona: 84 png en 2 min 14 s (mediana 0,7 s, ninguna a 45 s). 04:05–04:44 pasada completa: 2688 png en 38 min 54 s, 0 errores, mediana 93 ms. 14 png < 15 KB; reintento de mi-trabajo, produccion y operaciones dejó 7 móviles en carga (el texto no es «Cargando…»). Ese reintento reescribió `_tiempos.json`; segunda pasada 04:50–05:26 (36 min 21 s) repuso 2688 tiempos y 0 errores. Repo: `capturar.mjs` `waitUntil: 'load'`.
- F1.4 · intento 2 (plan de guardia, 05:31) · hipótesis: la espera exacta `Cargando…` no ve «Cargando tus tareas…» / «Leyendo las fuentes autorizadas…»; un regex en la línea 66 retiene esas pantallas. Resultado: no. `node --check` sin salida. 8770 estaba parado; `arrancar viejo` → curl 200 (sesión larga, pid del shell de arranque). Prueba `--personas tomas --pantallas mi-trabajo,produccion,operaciones`: `6 fotos … 0 errores` en 19 s. Móvil: 11382, 12232 y 13866 bytes, las tres con el texto de carga todavía. Escritorio: mi-trabajo 313188 bytes y pintada (11641 ms); produccion 71660 (111 ms) y operaciones 72460 (1085 ms), las dos con el texto de carga. Tiempos: escritorio/mi-trabajo 11641; el resto entre 111 y 1085 ms (la espera no llegó a 15 s). APIs (curl, solo código y segundos): modulo/mi_trabajo/mi_trabajo 200 0,022 s; api/mi_trabajo 200 0,408 s; modulo/produccion/produccion 200 0,014 s; produccion/transiciones 200 0,370 s; las de operaciones del día, 200 y ~0,014 s. Sonda aparte en móvil, misma hora fija: al acabar `load` el regex ya coincide (texto corto); a los 2 s ya no coincide y el texto crece. La condición `!regex` se cumple cuando el texto aún no está, la espera sale y la foto (400 ms después) pilla el cascarón. No se regrabó `capturas/viejo`. `capturar.mjs` línea 66 cambiada, sin commit. PLAN_VUELTA.md → GASTADO.
- F1.4 · intento 3 · 06:09 · la condición de presencia tampoco retiene: móvil mi-trabajo 121751 B / 1953 ms (pintada), produccion 139766 B / 2212 ms (pintada), operaciones 13954 B / 204 ms (sigue «Leyendo las fuentes autorizadas…»). Escritorio operaciones 72458 B / 130 ms, el mismo texto: `#main` ya tiene «Cambiar apartado» y la espera da por pintada la pantalla. No se regrabó `capturas/viejo` (2688 png, 7 < 15 KB). Plan B.
- F1.5 · intento 1 · 06:18 · 45 casos, 14 rutas, «sin caso: ninguno», ensayo rc=0. El primer id de account coincide con dirección: los casos «ver como» usan el primer account que no es dirección (si no, `/api/recarga` con cuerpo vacío se ejecutaría). El 200 de `/api/acciones` lleva módulo `agenda` (`app` no es un módulo; `mi-trabajo` rechaza el tipo `nota`). El caso sin `objeto` sale 403 (la referencia se mira antes), y la ruta igual tiene 4xx. 8780 parado; 8770 vivo.
- F1.6 · intento 1 · 06:31 · pasada 1: 169 verdes, 38 rojas, 5 min 9 s. Ninguna es de entorno. Pasada 2 con `baterias_heredadas.txt`: rc=0, ROJAS 0, 38 heredadas. `seguridad_aisladas` ✔. `solidez_tuberia` heredada (69/95). `.cjs` con ruta local: 18, no 21.
- F1.7 · intento 1 · 06:39 · puerta f1 VERDE. Salida: ✔ copia de seguridad (local.db.antes); ✔ contrato de la app de hoy grabado; ✔ vectores de permisos grabados; ✔ fotos de la app de hoy; ✔ casos de escritura cubren todos los POST; ✔ escrituras de referencia (SQLite); ✔ notas de la noche; ✔ baterías verdes contra la app de hoy; ✔ velocidad de la app de hoy medida; VERDE · puerta f1.
- F2.1 · intento 1 · 06:42 · 6 apariciones a `tuberia_avisos`, `py_compile` limpio, base temporal sqlite con count 1 y sin tabla `avisos`. Solidez rc=1, 69 de 95, el mismo `KeyError: 'valor'` que F1.6.
- F1.4 · intento 3 (revisión 06:44) · hipótesis: texto estable 600 ms. `Date.now()` no avanza con el reloj fijo: la prueba de 18 fotos se fue a 15 s. Con 6 sondeos de 100 ms: 18 fotos, 0 errores, ninguna < 15 KB, máximo 4053 ms, operaciones y producción pintadas. Pasada 07:01–08:03: 2100 png, 0 errores, mediana 802 ms. Puerta f1 VERDE 08:11 (9/9). La de 2688 está en `viejo_espera_vieja`.
- F1.5 · intento 2 · 08:19 · reabierto a las 06:47 por la nota genérica de Claude (notas_revisor/F1.5.md, solo habla de setsid); su nota para F2.2 dice que fue un error de la maquinaria y que no se rehaga. Comprobado: 45 casos, 14 rutas, «sin caso: ninguno»; la puerta f1 de 08:05 ejecutó los 45 casos (✔) y salió VERDE 9/9. Nada regrabado.
- F1.6 · intento 2 · 08:20 · reabierto a las 06:47 por el mismo error. Comprobado: el log de la puerta f1 (08:05, acabado 08:10) termina en «Verdes: 169 · heredadas en rojo: 38 · ROJAS: 0». Nada rehecho.
