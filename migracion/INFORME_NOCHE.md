# Informe de la noche · migración 4→5-oct-2026

Escrito: 9-oct-2026 02:38. Rama: migracion/v2 (169 commits desde el 4-oct 20:00; 25 llevan «F5.10»). Fin de la noche: 2026-10-09 08:00.

## 1. En cinco líneas

- Qué funciona: la app nueva en local (Next 3000 → Nest 4000 → legado 8771 sobre Postgres) pasa contrato y escrituras en la puerta f7 del 9-oct 02:37, igual que en la f5 del 8-oct. La puerta f7 sale ROJA: restauración, fotos, baterías, «30 personas» y la CSP de «/». Contrato, escrituras, velocidad y caídas quedan en verde. La puerta f5 del 8-oct sale ROJA por los mismos jueces de fotos, baterías, «30 personas» y CSP (N-28 y N-30). La puerta f3 del 5-oct 10:48 sale ROJA por fotos y «30 personas». No hay informe de puerta f6.
- Mudado a Nest: `/vivo`, `/api/sesion`, rastro (GET, POST y verificar), los ficheros de `MODULOS_EN_NEST` (74 en F5.3; 26 siguen por el proxy), `GET /api/cliente/:id`, `GET /logos`, `GET /api/indicadores`, GET y POST `/api/preferencias`, respuestas, decisiones, opiniones, ajustes, `POST /api/ver_dato`, `GET /api/acciones`, `GET /api/avisos` y `POST /api/avisos/visto`.
- Mudado a React: nada. F6.1–F6.4 quedaron fuera de alcance (Tomás, 6-oct 19:02). `RO_CARCASA` apagado. «/» sigue siendo el front de hoy.
- Sigue por el proxy: `POST /api/acciones`, canales, buscar, índice, contadores, perfil, y los 26 ficheros de módulo que F5.3 dejó fuera. El front entero va por el puente.
- Fallos de `PENDIENTES_LOGICA.md`: 50 arreglados y 21 que ya estaban, de 79. Pendientes: 4 (L-10, L-31, N-18, N-23). De seguridad sin cerrar: L-10 (parcial). Conocidos o medidos, no son arreglo de código: N-26, N-27, N-28, N-30.

## 2. Puertas

| Puerta | Resultado | Informe | Qué falló (si falló) |
|---|---|---|---|
| f1 | VERDE | ~/RO_MIGRACION/puertas/f1.md | 5-oct 08:05. 9 de 9. |
| f2 | VERDE | ~/RO_MIGRACION/puertas/f2.md | 7-oct 05:04. Base, versión, contrato, escrituras y velocidad. |
| f4 | VERDE | ~/RO_MIGRACION/puertas/f4.md | 6-oct 10:28. Permisos en TypeScript, 100 % de los vectores. |
| f3 | ROJO | ~/RO_MIGRACION/puertas/f3.md | 5-oct 10:48. Compila, e2e, contrato, escrituras, baterías, velocidad, seguridad y caídas en verde. Fotos: 2004/2100 bajo el 0,5 %. «30 personas» en rojo. |
| f5 | ROJO | ~/RO_MIGRACION/puertas/f5.md | 8-oct 21:07. Compila, e2e, contrato, escrituras, velocidad y caídas en verde. Fotos 1984/2100 (N-28). Baterías en rojo (N-13, `seguridad_aisladas`, 562). «30 personas» en rojo (N-28). Seguridad: solo la CSP de «/» (N-30). |
| f6 | no medido | no hay `puertas/f6.md` | F6.1–F6.4 ⚠ fuera de alcance. No se lanzó la puerta. |
| f7 | ROJO | ~/RO_MIGRACION/puertas/f7.md | 9-oct 01:00–02:37. 10 ✔: informe, render.yaml, escalados, compila, reinicio, e2e, contrato, escrituras, velocidad y caídas. 5 ✘: restauración (`/api/salud`, forma de `foto`); fotos 1984/2100 y 0 errores de página (N-28); baterías 223 verdes, 38 heredadas, rojas N-13, `seguridad_aisladas` y 562; «30 personas» (`ConnectionResetError` al medir la referencia 8770, antes de la app nueva, N-28); seguridad solo la CSP de «/» (N-30). |

## 3. Bloqueos para el piloto (Astra)

- Permisos con datos reales: la puerta f4 está VERDE (100 % de los vectores, 6-oct 10:28). El contrato de la f5 (8-oct) incluye «ver como» y sale en verde.
- Restauración: ROJA (9-oct 01:04, `restauracion()` de la puerta f7). El volcado de `ro_app` se restauró en `ro_restaurada` y `servir.py` en 8782 respondió. El contrato contra la referencia: 10203 respuestas iguales, 1 distinta, 2810 en excepciones conocidas. La distinta es `/api/salud` para dirección: el objeto `foto` no tiene las mismas claves (referencia: `fecha` y `nota`; restaurada: `fecha`, `comparado_con` y `ficheros`). `/api/salud` está en `SOLO_FORMA`, así que se compara la forma, y `foto` no entra en `VOLATILES`. La puerta no da la copia por comprobada. Bloqueo para el piloto.
- Fuentes privadas: paquete N-23 preparado en `~/RO_MIGRACION/paquete/20261008-2306` (1964 ficheros; plan 837; privado 1126; `funciones_fuentes` 6). `listo_para_desplegar` false (`hidratacion_privada_no_implementada`, `restauracion_destino_no_verificada`). Subirlo es de Tomás. `indicadores.json` no está en la imagen de la API. Duda 18: el Dockerfile de la API no copia `modulos/`.
- Funciones críticas: `POST /api/acciones` y los canales siguen por el proxy (enchufes y triaje). El triaje responde 503 en Postgres a propósito (Duda 13). Varias rutas de operaciones, tareas, uso y transiciones siguen en 503 con `DATABASE_URL` (familia de F2.4; no es un fallo de traducción).
- Contenedores (F7.1, 8-oct 23:06, plan B): las imágenes api y web construyen (pnpm 10.28.0 y `Dockerfile.dockerignore`; contexto 4,61 MB y 9,13 MB). La API no se queda en pie: `ERR_MODULE_NOT_FOUND` de `/app/node_modules/@ro/permisos/dist/index.js` (`pnpm deploy` no empaqueta `dist/`, está en `.gitignore`). En 3100, `/vivo`, `/api/elegir`, `/api/sesion` y `/` dieron 500. No se llegó a «Host no permitido». `reglas_permisos.json` está en `/reglas_permisos.json`, no en `/app/`. Los servicios locales volvieron: 4 en verde y `/vivo` de 3000 en 200. Bloqueo del piloto: sí, el arranque de la API en Docker.
- Excepciones conocidas: 132 líneas en `~/RO_MIGRACION/excepciones.txt`. Por id: L-25 (99), L-38 (13), sin id (7), N-12 (2), L-32 (1), L-33 (1), N-11 (1), L-22 (1), L-26 (1), L-39 (1), L-41 (1), L-43 (1), L-44 (1), L-45 (1), N-26 (1).
- Fallos de seguridad de `PENDIENTES_LOGICA.md` sin arreglar: L-10 (plan B parcial: el recorte de «resumen» y unos tests que juzgan). El resto de seguridad de la lista está en «ya estaba» o «arreglado».

### Fallos de PENDIENTES_LOGICA.md

| Id | Gravedad | Estado |
|---|---|---|
| L-01 | funcional | ya estaba (el Mac ya no asigna `hoy` dentro de `aplicar_ajustes`; prueba `migracion/pruebas_L-01.py`, 5-oct) |
| L-02 | seguridad | ya estaba (el Mac ya devuelve el rastro `quien=<real> AND como=<vista>` y `acciones: []` en «ver como», sin 403; prueba `migracion/prueba… |
| L-03 | seguridad | ya estaba (el Mac escanea cada fichero cuando cambia su marca y responde 503 con el texto de la puerta de secretos; prueba `migracion/pru… |
| L-04 | seguridad | arreglado en v2 (+ `mrr`, `precio*`, `tarifa` en cuota y `email` en lead; IBAN en el escáner; `presupuesto` y DNI no, ver NOTAS; prueba `… |
| L-05 | seguridad | ya estaba (`puerta_modulo` y `config_almacen` ya casan por segmentos y el account recibe 403 con un cliente ajeno; prueba `migracion/prue… |
| L-06 | seguridad | ya estaba (`capturas_opiniones_565.permiso` exige que real y vista sean la autora y vean la pantalla; prueba `migracion/pruebas_L-06.py`,… |
| L-07 | seguridad | ya estaba (`do_HEAD` responde 405 sin cuerpo y OPTIONS no da 200, en 8771 y en 3000; prueba `migracion/pruebas_L-07.py`, 5-oct) |
| L-08 | seguridad | ya estaba (todo GET en «ver como» pasa por `apuntar_lectura_ver_como`, agrupado por familia y minuto, y `GET /api/sincronia` ya no escrib… |
| L-09 | funcional | arreglado (6-oct 10:59, 1ef2c0f; `migracion/pruebas_L-09.py`) |
| L-10 | seguridad | pendiente (plan B, parcial): ya estaba que outreach (sola) y producción (sola) reciben 403 y que un account recibe 403 con un cliente aje… |
| L-11 | seguridad | ya estaba (el Mac ya da 403 a una acción sobre un cliente ajeno por `objeto` o por `cliente_id`, 400 a `decision_nueva` en `*` y a un tic… |
| L-12 | seguridad | ya estaba (los textos de acciones se recortan por quien mira y las decisiones solo las ve quien tiene nivel; `sin_importes` clasifica cad… |
| L-13 | seguridad | ya estaba (`ajustes_validacion_579`, el 400 de bajas/correo en `/api/ajustes/persona` y `validar_persona` de `build_data.py` ya validan; … |
| L-14 | seguridad | arreglado en v2 (migración `20261005173000_l14_revoke_rastro`: REVOKE UPDATE/DELETE/TRUNCATE sobre rastro, historial y huellas al rol «ro… |
| L-15 | seguridad | ya estaba (`ia_real_559.autorizada()` exige `RO_IA_REAL=si` e interruptor firmado por Tomás, y `ia.py` e `ia_gasto.py` lo consultan; prue… |
| L-16 | seguridad | arreglado hoy (9a02a06) |
| L-17 | seguridad | ya estaba (código) · pendiente: la prueba N9 de `pruebas_seguridad.py` la cambia Tomás de día (fichero que juzga); prueba nueva `migracio… |
| L-18 | datos | arreglado en parte (5-oct): Mi día y «Lo mío» (`mi_dia.js`, `mi_dia_bloques.js`) leen ahora en Madrid; barrido de 9 pantallas × 2 persona… |
| L-19 | datos | arreglado (c34b9a9, 5-oct; `migracion/pruebas_L-19.py`) |
| L-20 | datos | arreglado en parte (35a0dd9, 5-oct; `migracion/pruebas_L-20.py`; rótulos de dato con periodo propio pendientes, NOTAS «L-20») |
| L-21 | funcional | ya estaba (el Mac ya atrapa cada vuelta con `try/except` y sigue; prueba `migracion/pruebas_L-21.py`, 5-oct) |
| L-22 | datos | arreglado (34b53d9, 5-oct; `migracion/pruebas_L-22.py`) |
| L-23 | funcional | ya estaba (6-oct): `pruebas_L-23.py` |
| L-24 | presentación | arreglado (6-oct 04:05; `migracion/pruebas_L-24.py` o la batería de `_entrada_error_562`) |
| L-25 | funcional | arreglado en parte (6-oct): D1–D4 y silla `altas`; falta `dinero_empresa` para administración (toca jueces, NOTAS «L-25») |
| L-26 | funcional | arreglado (6-oct): `pruebas_L-26.py` |
| L-27 | funcional | arreglado en parte (6-oct): rutas por `config.py` (`pruebas_L-27.py`); el llavero y `pasos.json` van en N-14 |
| L-28 | funcional | arreglado en parte (6-oct 10:15; `migracion/pruebas_L-28.py`); pendiente: toca un fichero que juzga (`pruebas_seguridad.py` M3, `pruebas_… |
| L-29 | funcional | arreglado (6-oct): `pruebas_L-29.py` |
| L-30 | datos | ya estaba (5-oct; `migracion/pruebas_L-30.py`) |
| L-31 | datos | pendiente: el dato no llega esta noche, sin prueba demostrable (NOTAS «L-31») |
| L-32 | datos | arreglado en parte (bd98c7c, 5-oct: ficha y selector; Mi día e incidencias usan campos propios, pendiente) |
| L-33 | datos | arreglado (a77fdbc, 5-oct; `migracion/pruebas_L-33.py`) |
| L-34 | datos | arreglado (adc34ac, 5-oct; `migracion/pruebas_L-34.py`) |
| L-35 | funcional | ya estaba (6-oct 02:42; `migracion/pruebas_L-35.py`) |
| L-36 | funcional | ya estaba (6-oct 02:50; `migracion/pruebas_L-36.py`) |
| L-37 | presentación | arreglado (6-oct 04:12; `migracion/pruebas_L-37.py`) |
| L-38 | presentación | arreglado (6-oct 05:07; `migracion/pruebas_L-38.py`) |
| L-39 | presentación | arreglado (6-oct 05:52; `migracion/pruebas_L-39.py`) |
| L-40 | presentación | arreglado (6-oct 06:30; `migracion/pruebas_L-40.py`) |
| L-41 | presentación | arreglado (6-oct 07:25; `migracion/pruebas_L-41.py`) |
| L-42 | presentación | ya estaba (6-oct 07:35; `migracion/pruebas_L-42.py`) |
| L-43 | presentación | arreglado (6-oct 07:55; `migracion/pruebas_L-43.py`) |
| L-44 | presentación | arreglado (6-oct 08:10; `migracion/pruebas_L-44.py`) |
| L-45 | presentación | arreglado (6-oct 08:25; `migracion/pruebas_L-45.py`) |
| L-46 | presentación | arreglado (6-oct 09:15; `migracion/pruebas_L-46.py`) |
| L-47 | presentación | ya estaba en parte (6-oct 09:30; `migracion/pruebas_L-47.py`; tarjetas a 0 que son `button` de filtro, NOTAS) |
| L-48 | presentación | arreglado (6-oct 09:50; `migracion/pruebas_L-48.py`) |
| L-49 | funcional | ya estaba: prueba hecha (6-oct 03:02; `migracion/pruebas_L-49.py`) |
| L-50 | seguridad | ya estaba (lo arregló L-25, `2ce5d37`: los importes a quitar salen de `P.ver(...)`, el mínimo de las dos personas, y no de `P.puestos_de`… |
| N-01 | datos | arreglado en v2 (5-oct; `despliegue/pruebas_solidez_N-01.py`) |
| N-02 | datos | arreglado en v2 (5-oct; `despliegue/pruebas_solidez_N-02.py`) |
| N-03 | datos | arreglado en v2 (5-oct; `despliegue/pruebas_solidez_N-03.py`) |
| N-04 | datos | arreglado en parte (5-oct; `despliegue/pruebas_solidez_N-04.py`; falta la prueba de DOM, NOTAS «N-04») |
| N-05 | datos | arreglado en v2 (5-oct; `despliegue/pruebas_solidez_N-05.py`) |
| N-06 | datos | arreglado en v2 (5-oct; `despliegue/pruebas_solidez_N-06.py`) |
| N-07 | datos | arreglado (5-oct; `despliegue/pruebas_solidez_N-07.py`) |
| N-08 | datos | arreglado (5-oct; `despliegue/pruebas_solidez_N-08.py`) |
| N-09 | datos | arreglado (5-oct; `despliegue/pruebas_solidez_N-09.py`) |
| N-10 | datos | arreglado en v2 (5-oct; NOTAS «N-10») |
| N-11 | datos | arreglado en v2 (5-oct; `migracion/pruebas_N-11.mjs`) |
| N-12 | funcional | arreglado en v2 (cc05c11, 5-oct; `migracion/pruebas_N-12.py`) |
| N-13 | funcional | arreglado (6-oct 03:14; `despliegue/pruebas_solidez_N-13.py`) |
| N-14 | funcional | arreglado (6-oct 03:23; `despliegue/pruebas_solidez_N-14.py`) |
| N-15 | funcional | arreglado (6-oct 03:29; casi todo ya estaba por L-27) |
| N-16 | funcional | arreglado (6-oct 03:36; `despliegue/render.yaml`) |
| N-17 | datos | arreglado (5-oct; `despliegue/pruebas_solidez_N-17.py`) |
| N-18 | funcional | pendiente: no se añade el cron `ro-vigia` (el disco de un cron de Render arranca de cero; NOTAS) |
| N-19 | funcional | arreglado (6-oct 03:46) |
| N-20 | funcional (inferido) | arreglado (6-oct 03:58; tabla `interruptor`) |
| N-21 | datos | arreglado hoy (4-oct: esquemas de uno en uno con candado 7263 y una sola vez por proceso; 0 errores en 3 pasadas) |
| N-22 | datos | arreglado hoy (4-oct, sin construir la imagen: aquí no hay Docker) |
| N-23 | datos | pendiente: se prepara en F7.1 (paquete en `~/RO_MIGRACION/paquete`); subirlo es de Tomás: bloqueo para el piloto |
| N-24 | datos | arreglado en v2 (c84da79, 510de10 y el lote de prioridades; puerta f2 VERDE 5-oct; las 6 rutas Operaciones ya no están en `excepciones*.t… |
| N-25 | seguridad | arreglado en v2 (7af9812; e2e 7 pasadas + 2 todo, 0 ficheros nuevos en `data/`) |
| N-26 | datos | conocido (no es un cambio de código; Tomás, 6-oct) |
| N-27 | rendimiento | medido (7-oct 05:04–05:10, vuelta de las 03:02): puerta f2 VERDE (base, versión vigente, contrato, escrituras y velocidad). La referencia… |
| N-28 | presentación | conocido |
| N-30 | pruebas | conocido |

### Fichas de `migracion/INTEGRAR.md`

| Ficha | Estado | Dónde (paso · commit) |
|---|---|---|
| §1 Cerebros (PR #2) | por el proxy | no hay ficha `cerebro` en `MODULOS_EN_NEST` |
| §2 Diagnósticos (PR #3) | por el proxy | no hay ficha de diagnóstico en `MODULOS_EN_NEST` |
| §3 Semáforo / riesgo de baja (PR #4) | riesgo de baja en Nest; el semáforo no aparece con ese nombre | F5.3 · ficha `riesgo/riesgo_baja` |
| §4 Contexto del cliente | en Nest | F5.3 · ficha `contexto/contexto_clientes` |
| §5 Copia propia de las APIs (N-01…N-12) | 12 arreglados, 0 ya estaban, 0 pendientes, de 12 | F5.10 |
| §6 Servidor MCP | pendiente | no hay paso cerrado (Duda 6) |

## 4. Revisiones

Hay `~/RO_MIGRACION/revisiones/PARA_EL_INFORME.md`. Resume, sin copiar el fichero entero:

- F1.4 a F1.7, F2.1 a F2.3: comprobados contra su «hecho cuando». Puerta f1 VERDE. F2.3 con el esquema al día y la publicación vigente.
- F5.11: `escalados.py` rc=0, 26/26, el 6-oct por la noche.
- F5.2, F5.3, F5.4, F5.5, F5.8 y F5.9: cotejados con `servir.py`. Las puertas rápidas de F5.6–F5.8 y la completa de F5.9 dejan los rojos en N-28 y N-30.

## 5. Preguntas para Tomás

1. N-18. El vigía no cabe en un cron: el disco se pierde y `episodios.json` no sobrevive. ¿Estado en la base, o un bucle dentro de `ro-legado`?
2. Duda 35 (a). `RO_API_URL` va como valor `http://ro-api:4000` porque el `next build` lo lee. Confirmar en la vista previa del Blueprint que Render inyecta las variables en el build.
3. Duda 35 (b). El `preDeployCommand` de `ro-api` llama a `pnpm --filter @ro/db migrate:deploy`, y la imagen no trae el CLI de prisma (es dependencia de desarrollo y `pnpm deploy --prod` no lo copia). ¿Se mete el CLI en el Dockerfile de día?
4. Duda 35 (c). `RO_LEGADO_URL` lleva esquema (`http://ro-legado:10000`). `fromService` hostport no vale (`entorno.ts`).
5. Duda 18. La imagen de la API no copia `modulos/` ni el `dist/` de `@ro/permisos` tras el deploy. Sin eso el contenedor no arranca. ¿Se corrige el Dockerfile de día?
6. N-23. El paquete de fuentes privadas está en el Mac. Subirlo y montarlo en `ro-legado` es tuyo. Hasta entonces el legado en la nube arranca sin ellas.
7. L-10. El plan B dejó un recorte de «resumen» a medias y tests que juzgan en rojo a propósito. Hay que actualizar esos tests de día o cerrar el recorte.
8. L-04. Dos tests viejos quieren que una clave `email` suelta de un contacto pase. La regla de esta noche la quita. ¿Se actualizan los tests o el contacto de un negocio sí pasa?
9. N-24 y F2.4. Unos tests y unas rutas siguen en 503 porque hay `DATABASE_URL` (operaciones, tareas, uso, transiciones). ¿Se levantan esas guardas ahora que la app va a Postgres, o siguen 503 también en la nube?
10. L-31. El dato no llegó esta noche. Sigue pendiente, sin prueba demostrable.
11. L-47. Las tarjetas a 0 que filtran siguen pulsables. No se desactivaron (cambiaría la pantalla). ¿Las quieres apagadas cuando valen 0?
12. Duda 29. La puerta de secretos de Nest pregunta al legado en cada petición. ¿Te vale, o se porta el escáner?
13. Duda 32 y Duda 33. La CSP de «/» y dos baterías (`seguridad_aisladas`, 562) comparan jueces que no pueden salir verdes esta noche. Ninguna puerta f5 queda VERDE por eso. Lo cambias tú de día.
14. Duda 34. El perfil sigue en el proxy: Node y Python no traen la misma lista de zonas horarias.
15. F6. Las pantallas en React no se hicieron (6-oct 19:02). «/» sigue con el front de hoy.
16. Los dos blueprints pueden convivir: `despliegue/render.yaml` (ro-app) y `v2/render.yaml` (ro-web, ro-api, ro-legado). Al crear el de la app nueva hay que indicar la ruta `v2/render.yaml`.
17. D1 (administración y beneficio del equipo; ámbito del trafficker) sigue sin decidir. No se tocó.
18. Duda 35 (g). `ro-legado` y los cuatro crons usan `despliegue/Dockerfile`, que copia `app/` y `herramientas/` (solo existen en el paquete de `preparar_contexto.sh`). `ro-web` y `ro-api` necesitan `v2/` y `reglas_permisos.json` en la raíz. Un mismo repo no cumple las dos cosas. Hoy, con la raíz como contexto, esos 5 servicios no construyen. Tú decides el repo de despliegue antes de crear el Blueprint.

## 6. Pasos de la mañana, exactos

1. `bash ~/RO_MIGRACION/comprobar_manana.sh` (huellas de los jueces, excepciones, servicios de cero, puertas f2, f4, f3 y f7).
2. Leer `migracion/PROGRESO.md` y este informe. Los ⚠ de esta noche: F2.4 (rutas 503 con `DATABASE_URL`), F5.1 (parcial), F5.10 (4 pendientes), F6.1–F6.4 (fuera de alcance), F7.1 (la API de Docker no arranca), F7.3 (puerta f7 ROJA).
3. Decidir las dudas 18, 29, 32, 33, 34 y 35 (incluida la g), y N-18, N-23, N-24, L-10, L-31, L-47. Bloquean el piloto: el arranque de la API en Docker (dist de `@ro/permisos` y `modulos/`), el paquete N-23 sin subir, el vigía sin sitio en la nube, que la tubería no construye con la raíz del repo como contexto (Duda 35 g), y que la copia restaurada no quedó comprobada (`/api/salud`, forma de `foto`).
4. Despliegue, cuando toque (no esta noche): T1b de Supabase (Frankfurt, Data API apagada, SSL, restricciones de red a las IP de Render, Session pooler 5432, certificado en `RO_PG_CA`). Decidir el repo de despliegue antes del Blueprint (Duda 35 g: o `preparar_contexto.sh` copia también `v2/` y ajusta rutas, o dos blueprints). Blueprint con la ruta `v2/render.yaml`. Confirmar `RO_API_URL` en el build (Duda 35 a). Subir el paquete `~/RO_MIGRACION/paquete/20261008-2306` al destino de `ro-legado`. No desplegar `ro-api` hasta que la imagen arranque (Duda 35 b y Duda 18). No crear los crons ni `ro-legado` hasta que el contexto de Docker exista: hoy no construyen.
5. De día, en este orden: (1) Dockerfile de la API, para que `dist/` de los paquetes y `modulos/` entren y `prisma migrate deploy` pueda correr; (2) jueces de CSP, `seguridad_aisladas` y 562; (3) L-10 y las guardas `DATABASE_URL` de F2.4; (4) N-18 con estado que sobreviva al cron; (5) hidratar el paquete N-23 en el destino.
