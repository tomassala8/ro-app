> Recogido en: `migracion/PENDIENTES_LOGICA.md` (filas L-01…L-49, decisiones D1–D8 y «Cambios de matriz»). Aquí está el **detalle** de cada arreglo (líneas, expresiones de L-04, trampas que rompen la app). Era el encargo a Astra del 4-oct: para Cursor es referencia, no órdenes. Si choca con `PENDIENTES_LOGICA.md` o `PROMPTS_CURSOR.md`, mandan esos (por ejemplo: esta noche no se toca ningún `pruebas_*.py` que ya exista; las pruebas nuevas van en `migracion/pruebas_L-<n>.py`).
> **Copia saneada para Cursor (4-oct-2026).** Fuente: `/mnt/project-files/feedback_herramienta/`. Personas cambiadas por su puesto; ids de prueba y de cliente, por ids neutros.

# Súper prompt para Astra · auditoría total de la app de RO (4-oct-2026)

> **Cómo usarlo:** Dirección copia desde la línea «---» de abajo hasta el final y lo pega en la sesión de Astra. Junto con él, deja en el Mac el otro fichero de esta carpeta **con el nombre `~/RO_MIGRACION/PENDIENTES_LOGICA.md`** (todo sale `abierto`). Así Cursor tiene las 49 filas esta noche aunque Astra no llegue a las 19:00. Astra lo usa para las pruebas de cada punto y solo le cambia la columna Estado.
>
> Versión 3: revisada tres veces contra el código y contra el plan de migración de esta noche. Se quitaron los arreglos que habrían roto la app, las pruebas o la migración.

---

Astra, te paso la auditoría completa de la app de RO. Se ha hecho hoy, 4-oct-2026, sobre el código de GitHub (`ro-app`, rama `main`, commit `4f46378`, versión del 3-oct), con **datos inventados**:
- 10 puestos recorridos en navegador, 420 pantallas a 1366 y 390 px;
- 38.812 casos de paridad de permisos Python ↔ JS, sin ninguna diferencia;
- todas las rutas de `servir.py` y los 61 módulos leídos uno a uno.

Lo grave se ha vuelto a comprobar en el código. Quiero que lo corrijas hoy, con este método y en este orden.

## 0. Reglas de trabajo (léelas antes de tocar nada)

1. **Tu copia va por delante de GitHub.** Los números de línea son de `main@4f46378`. Antes de cada punto, comprueba si sigue pasando en tu copia. Si ya está arreglado, márcalo `ya estaba` y sigue. Si el código se ha movido, búscalo por el nombre de la función o por el texto citado.
2. **Un punto, un ciclo:** reproducir → arreglar → prueba que falla antes y pasa después → commit con el id en el mensaje (`L-05: …`). Si un punto no trae «Prueba», usa la columna «Cómo se comprueba» de su fila en `~/RO_MIGRACION/PENDIENTES_LOGICA.md`.
3. **No rompas lo que funciona.** Al cerrar cada bloque pasa: `python3 escaner_secretos.py --proyecto`, `python3 pruebas_seguridad.py`, `python3 pruebas_coherencia.py`, `python3 pruebas_diseno.py --estricto` y `python3 pruebas_e0.py`. Cada arreglo de seguridad suma un caso a `pruebas_seguridad.py`. Nunca relajes una comprobación para que pase; si un cambio de contrato es a propósito, cambia la prueba y di por qué en el commit.
4. **Nada sale fuera.** Envíos, ClickUp, IA, Ficha de Google y Modular siguen apagados. Hasta cerrar L-15, trabaja con `unset ANTHROPIC_API_KEY` en tu terminal. No despliegues nada.
5. **Nada de datos reales** en el repo, en pruebas, en capturas ni en mensajes de commit.
6. **No toques `migracion/` ni `v2/`.** Son del plan de esta noche. Haz commit solo de lo tuyo: `git add <ficheros>`, nunca `git add -A` ni `git commit -a`. Si `git status` enseña `migracion/` o `v2/` preparados, déjalos fuera con `git restore --staged migracion v2`.
7. **Las decisiones de la sección 6 no las tomas tú.** Deja el código listo para las dos opciones si es barato y apunta `decide dirección (Dn)`.
8. **Corte a las 19:00 (Madrid).** A esa hora, commit y tabla del punto 7, aunque falten puntos. Esta noche Cursor migra la app a Next + Nest + Postgres partiendo de tu copia, y lo que no cierres lo arregla él **sí o sí** (regla de dirección).
9. **Orden mínimo del día:** §0b → L-01, L-02 → L-07, L-06, L-03, L-05, L-08, L-10, L-11, L-12, L-13, L-14, L-15, L-04 → cambios de matriz de la sección 6 → L-16, L-21, L-24, L-09, L-17. Después, lo que dé tiempo. L-18, L-19, L-20, L-27, L-34 y L-38 a L-49 son los que mejor puede hacer Cursor si no llegas.
10. Si un punto te parece mal planteado, dilo con la prueba en vez de forzarlo.

Gravedad: **P0** rompe o expone datos · **P1** fallo de permisos o funcional · **P2** coherencia o usabilidad · **P3** pulido.

---

## 0b. Antes de nada (30 min): que las baterías digan la verdad

Sin esto no se puede cumplir la regla 3: hoy dos baterías fallan solas con el repo limpio.

### L-28 · Las baterías de prueba fallan por sí mismas
- **`escaner_secretos.py --proyecto`** sale en rojo con el repo limpio: toma `-iTCP@127.0.0.1` de `pruebas_seguridad.py:48` por un correo. **Arreglo:** que el patrón de correo no case con `@127.0.0.1`, o añadir esa línea a `escaner_permitidos.json`.
- **`pruebas_seguridad.py`, bloque M3 (282-290):** abre conexiones sqlite en línea sin cerrarlas. Si el `DELETE` no dispara el disparador (tabla vacía), deja una escritura abierta y la base bloqueada, y todo lo que escribe después da 500. Además, `except sqlite3.DatabaseError` toma «database is locked» por un bloqueo correcto. **Arreglo:** `with closing(sqlite3.connect(...)) as c:` y comprobar el mensaje del disparador, no solo el tipo de error.
- **`pruebas_e0.py:94`** revienta con `KeyError` si falta una de las personas fijas que usa (usa cuatro ids fijos sin comprobar). **Arreglo:** marcar ✗ con el motivo y seguir.
- **Prueba:** las tres baterías en verde (o con ✗ explicados) sobre tu copia limpia.

### L-29 · `generar_alertas.py` reescribe un fichero que está en git
- `fuentes_alertas/estado_alertas.json` cambia en cada recarga (5.388 líneas tras una pasada) y acabaría en tus commits. **Arreglo:** moverlo a `data/` (o a la base) y sacarlo del repo con `git rm --cached`. **Prueba:** `git status` limpio tras una recarga.

---

## 1. P0 · Lo primero

### L-01 · Contestar un «Para confirmar» tumba el servidor y luego impide arrancarlo
- **Dónde:** `servir.py`, `Estado.aplicar_ajustes` (líneas 687 y 692).
- **Qué pasa:** en la 687 se llama a `hoy()` (la función del módulo) y en la 692 la misma función hace `hoy = P.hoy_iso()`. Python trata `hoy` como local en toda la función y la 687 lanza `UnboundLocalError`. Solo corre cuando hay respuestas `para_confirmar` guardadas.
  1. Operaciones contesta en Ajustes › Para confirmar → `POST /api/ajustes/confirmar` guarda en `local.db` y llama a `E.recargar_personas()` → 500.
  2. En el siguiente arranque, `main()` llama a `E.cargar()` sin `try` (línea 3121) → **el servidor no arranca**. «Actualizar ahora» acaba igual.
- **Arreglo:** `dia_hoy = hoy()` una vez al principio de la función y usarla en las dos líneas.
- **Prueba:** caso nuevo que conteste un «Para confirmar», recargue y vuelva a arrancar. Y `pipx run ruff check --select F821,F823 .` limpio.

### L-02 · «Ver como» deja leer el rastro y las acciones personales de cualquiera, incluido dirección, sin dejar rastro
- **Dónde:** `servir.py` 2280-2290 (`/api/rastro`) y 2304-2305 (`/api/acciones` sin `?modulo=`).
- **Qué pasa:** sin `rastro_todo`, la consulta filtra por la persona **vista** (`WHERE quien=? OR como=?`). Operaciones viendo como dirección recibe sus 500 últimas filas de rastro y sus 200 acciones con `texto` y `vista_previa` enteros: decisiones, cambios de Ajustes, a quién le miró el sueldo, acciones de Finanzas con importes. Igual con cualquier puesto que operaciones no tiene (finanzas, RRHH, administración). Y la lectura no se apunta.
- **Reproducir:** `POST /api/decisiones?yo=dir` con un título; `GET /api/rastro?yo=ops` → vacío; `GET /api/rastro?yo=ops&como=dir` → salen las filas de dirección.
- **Arreglo (sin 403: la ficha, Decisiones, Mi día y Primera semana leen estas rutas dentro de un `Promise.all`, y un 403 les rompería la pestaña entera):**
  - en «ver como», `/api/rastro` responde 200 con `registro` = filas `WHERE quien=<real> AND como=<vista>` y `acciones: []`;
  - `/api/acciones` sin `?modulo=` responde 200 con `acciones: []` (la tabla `acciones` no tiene columna `como`, y en «ver como» no se puede escribir).
- **Prueba:** lo de «Reproducir» → 200 y ninguna fila de dirección.

---

## 2. P1 · Seguridad y permisos

### L-07 · `HEAD` se salta host, identidad y Access
- **Dónde:** `Manejador` (`servir.py:1870`) no redefine `do_HEAD`, así que entra el de `SimpleHTTPRequestHandler`.
- **Qué pasa:** `curl -I http://127.0.0.1:<p>/data/_privado/secreto.json` → 200 con tamaño y fecha; con `-H "Host: evil.com"` sobre `/servir.py` → 200. Dice si existe, cuánto pesa y cuándo cambió `local.db`, `sueldos.json` o `correos_entrada.json`.
- **Arreglo:** `def do_HEAD(self): return self.responder(405, {"error": "Método no permitido."})`.
- **Prueba:** `curl -I` a cualquier ruta → 405.

### L-06 · Las capturas de «Algo va mal» de dirección las ve operaciones
- **Dónde:** `servir.py` 2387-2399 y 2772; `RUTA_SENSIBLE` (1447) solo frena sueldos y nóminas.
- **Qué pasa:** `POST /api/opinion?yo=dir` desde `#/panel-direccion` con captura → `GET /api/opiniones/captura?id=1&yo=ops` devuelve la imagen (caja, beneficio).
- **Arreglo (sin cambiar el esquema de `opiniones`, que la migración copia tal cual):** sacar el módulo de la `ruta` que ya se guarda con cada opinión y servir la captura solo si la persona real **y** la vista ven ese módulo. No amplíes `RUTA_SENSIBLE`: tiraría la captura también para dirección.
- **Prueba:** la de arriba → 403 para operaciones.

### L-03 · La puerta de secretos solo mira `data/` al arrancar
- **Dónde:** `servir.py:610` (`E.bloqueados = ESC.escanear(DATA)`, solo en `Estado.cargar()`); `leer_json_bueno` (1215) lee el fichero en cada petición.
- **Qué pasa:** un fichero que un generador escribe con el servidor en marcha se sirve sin escanear hasta la siguiente carga entera. Probado: se creó `data/en_rojo/atajos.json` con correo, móvil, WhatsApp, teléfono y sueldo, y `GET /api/modulo/en_rojo/atajos?yo=admin1` lo devolvió entero.
- **Arreglo:** en `leer_json_bueno`, cuando cambie `(mtime, size)`, pasar `escaner_secretos.escanear_fichero()` con los mismos `permitidos` y `correos_ro_ok` que usa `escanear()`. Si hay hallazgos, meterlo en `E.bloqueados` con la clave `data/<rel>.json` y responder 503; y sacarlo de `E.bloqueados` cuando el fichero vuelva a salir limpio (si no, queda en 503 hasta reiniciar).
- **Prueba:** escribir un fichero con un correo de lead con el servidor arrancado → 503.

### L-05 · Un fichero de módulo con `cliente_id` en la raíz llega entero a quien no lleva ese cliente
- **Dónde:** `servir.py:941` (`fila_ok`, solo para elementos de listas) y 1003 (`out = paso(obj)`); `puerta_modulo` (1250).
- **Qué pasa:** probado con datos inventados: una persona account (de c0 y c1) pidió `GET /api/modulo/paneles/meta/c2` y recibió `{"cliente_id":"c2","campanas":[…]}`. Igual con `informe/c_2026-09/c2`. Hoy no hay fuga porque los generadores escriben `{"filas":[…]}`, pero la protección depende de que nadie cambie un generador.
- **Arreglo:**
  - si `obj` es un dict con `cliente_id` en la raíz, comprobar **solo el cliente** (`cliente_detalle` y, con nivel «suyo», la cartera), no `fila_ok` entero: `fila_ok` también mira `persona_id`, `miembros` y `setter` y daría 403 a ficheros por persona;
  - en `puerta_modulo`, para las rutas por cliente (`paneles/*/<cid>`, `informe/c_*/<cid>`): 403 solo si el último trozo es un id de cliente que existe y la persona no ve;
  - de paso: los patrones de `almacenes_privados` y `entrada_datos_modulo` (1246) usan `fnmatch`, cuyo `*` también cruza `/`. Usar `[^/]*` o comparar por trozos.
- **Prueba:** account pide `paneles/meta/<cliente ajeno>` → 403.

### L-08 · En «ver como» casi ninguna lectura deja rastro
- **Dónde:** `apuntar_lectura_ver_como` (`servir.py:1716`); solo se llama (2185) para `/api/modulo/`, `/api/cliente/` y `/api/buscar`.
- **Qué pasa:** no dejan rastro `/api/rastro`, `/api/acciones`, `/api/decisiones`, `/api/ajustes`, `/api/altas`, `/api/ia/*`, `/api/perfil`, `/api/opiniones`, `/api/envios`, `/api/sincronia` ni `/api/avisos_programados`. Además, `GET /api/sincronia` escribe en la base (`sincronia.py:1264`), también en «ver como».
- **Arreglo:** en `api_get`, apuntar toda petición hecha en «ver como», agrupada por minuto como ya se hace. Quitar `sincronizar(con)` de `_get` (`sincronia.py` 1264-1269): ya lo hacen `_tras_accion` (1375) después de cada acción y la tubería (`despliegue/reconciliar_clickup.py:54`).
- **Prueba:** leer `/api/decisiones` en «ver como» → fila nueva en `registro`.

### L-10 · `/api/cliente/<id>` no mira el módulo ni el nivel
- **Dónde:** `servir.py:2212` (solo comprueba `cliente_detalle`).
- **Qué pasa:** outreach no ve «Ficha» pero recibe la ficha entera (sin dinero) de su cartera. Redes y producción ven «Ficha» en «resumen» y reciben la ficha completa.
- **Arreglo:** exigir `ve_alguno(persona, ["ficha", "bandeja", "captacion", "asistente-ia"])`. Si el nivel más alto de la persona entre esos cuatro módulos es «resumen», devolver solo la cabecera, **salvo los puestos de `ficha_solo_contrato` (administración)**, que siguen con su recorte actual (cabecera, cuota, contrato y accesos: `servir.py` 872-877, probado en `pruebas_e0.py` 123 y 168).
- **Prueba:** outreach pide `/api/cliente/<su cliente>` → 403; producción → solo cabecera; administración → igual que hoy.

### L-11 · Huecos de validación en `/api/acciones`
1. **`objeto` libre sin `cliente_id`:** `POST /api/acciones?yo=account1 {"modulo":"ficha","herramienta":"app","tipo":"traspaso","objeto":"c2"}` → 200 sobre un cliente ajeno. **Arreglo:** solo con `herramienta: "app"`, en los tipos de cliente (`traspaso`, `nota`, `escalar`…) exigir `cliente_id`, o deducirlo de `objeto` cuando sea un id de cliente, y comprobar `cliente_detalle`. En Desk, WhatsApp, GHL y ClickUp el cliente lo pone el servidor (`servir.py` 2597-2601 y 2640): no lo exijas ahí, que la Bandeja manda `cliente_id: null` al triar (`bandeja.js:1277`).
2. **Tickets que el servidor no conoce:** alguien de producción encoló `escalar` sobre el ticket 123 de Desk. **Arreglo:** «si no sé de qué cliente es, no» para todos los tipos de Desk, WhatsApp y GHL, no solo para `responder`.
3. **`decision_nueva`** está en `acciones_permitidas["*"]` y se salta las exigencias de `post_decision` (título, problema, recomendación, cliente). Hoy ninguna pantalla la manda por esta vía (compruébalo con `grep -rn decision_nueva modulos/`). **Arreglo:** quitarla de `*`, o validarla igual que `post_decision`.
- **Prueba:** el `POST` del punto 1 → 403.

### L-12 · Textos con importes que llegan a quien no debe
- **`/api/acciones?modulo=X`** (`servir.py` 2291-2319): `texto` y `vista_previa` solo se recortan en 2 tipos. «Te recuerdo la cuota de 1.470 €» lo lee todo el que ve ese módulo y ese cliente. **Arreglo:** pasarlos por `P.sin_importes(…, quitar_para(persona, cp, cid))`, como la ficha.
- **`/api/decisiones`** (1736-1773): operaciones recibe `problema` y `recomendacion` con dinero de empresa. **Arreglo:** `textos_sin_importes_salvo: dinero_empresa`, como en `decisiones/firmadas`.
- **`permisos.py:374` (`tipo_importe`):** en «Cuota 1.470 €/mes y gasto 300 €», los 300 € se cuentan como cuota y administración (ve cuota, no inversión) los recibe. **Arreglo:** manda la palabra clave más cercana al importe.
- **Prueba:** ese texto leído por administración → ve la cuota y no los 300 €.

### L-13 · Ajustes valida menos que Altas, y «Para confirmar» no valida nada
1. **`/api/ajustes/asignacion`** (2920-2939): no comprueba que la silla sea del puesto, que la persona esté activa ni el formato de fechas (`"31/12/2026"` deja una suplencia vigente para siempre, porque se comparan como texto); `bool("false")` es verdadero. Además, una suplencia en cualquier silla da cartera aunque el puesto no tenga esa silla (`permisos.py:72`), y una persona sin sillas cuenta todas sus asignaciones. **Arreglo:** las mismas validaciones que `altas/repartir` y `validar_cartera`, `fecha_valida` y un tope de duración para las suplencias.
2. **Bajas y reactivaciones por `/api/ajustes/persona`** (2877): no cierran asignaciones, no crean la tarea de Access ni proponen reparto; `/api/altas/baja` sí. **Arreglo (sin romper «Guardar»: `ajustes.js:255` manda siempre `estado`):** rechazar con 400 solo el paso **a** `baja` o **desde** `baja`, con «Las bajas y las reactivaciones se hacen en Altas y bajas». Ese 400 va **después** de todos los 403 de permisos (puestos solo de dirección, dirección, mando, 2888-2900), justo antes de escribir: `pruebas_seguridad.py` 539-542 espera 403 cuando operaciones intenta dar de baja a alguien con mando. Un `estado` igual al actual, o el paso entre `activo`, `dudoso` y `por_incorporar`, se sigue aceptando. En `ajustes.js`, quitar la opción «baja» del selector y poner un enlace a Altas; cambiar el texto de `personas.js:555`, que manda a hacer la baja en Ajustes.
3. **Cambio de correo por `/api/ajustes/persona`** (2903): sin pasar por dirección ni crear la tarea de Access, y en modo servidor ese correo es identidad. **Arreglo:** que use `correo_libre` y `nueva_tarea(access_anadir)` como Altas, o que no acepte `correo`. En los dos casos, el duplicado sigue dando 409 (`pruebas_seguridad.py:266`).
4. **Nuevo · «Para confirmar» puede dar cualquier puesto, también dirección** (leído en el código, sin probar): `/api/ajustes/confirmar` (2941-2958) solo valida el `tipo`; con `tipo: persona`, `aplicar_respuestas` (`build_data.py` 398-417) hace `p.update(cambios)` sin comprobar nada: ni `puestos_solo_tomas`, ni «nadie cambia sus propios puestos», ni que la duda exista. **Arreglo:** con `tipo: persona`, aceptar solo `cambios.estado` entre `activo` y `dudoso`, y solo para una duda que exista en `para_confirmar` con ese `persona_id`. `puestos`, `correo`, `jefe` y `baja` → 400 («eso se cambia en Ajustes o en Altas»). Y quita `baja` de las opciones de ese selector (`ajustes.js:382`).
- **Prueba:** asignación con `hasta: "31/12/2026"` → 400; `estado: baja` por Ajustes → 400 y «Guardar» normal → 200; `cambios: {puestos: ["direccion"]}` por «Para confirmar» como operaciones → 400.

### L-14 · El rastro «imborrable» se puede reescribir con `INSERT OR REPLACE`
- **Qué pasa:** en SQLite, REPLACE borra la fila sin disparar el DELETE si `recursive_triggers` está apagado (por defecto). Probado: se reescribió la fila 1 de `registro`. La cadena de huellas lo detecta, pero con el mismo truco sobre `registro_huellas` más una fila «corte» en `rastro_incidencias` se blanquea.
- **Arreglo:**
  - `PRAGMA recursive_triggers = ON` en `conectar()` (`servir.py:288`);
  - disparador que aborte reinsertar un id existente en `registro` y `registro_huellas`, escrito exactamente con esta forma para que lo traduzcan a Postgres `base.py` y `crear_base_pg.py` de la rama de esta noche: `CREATE TRIGGER IF NOT EXISTS <nombre> BEFORE INSERT ON <tabla> WHEN NEW.id <= (SELECT max(id) FROM <tabla>) BEGIN SELECT RAISE(ABORT, '<mensaje>'); END;`. No lo pruebes en Postgres hoy ni toques `despliegue/base.py`: el de `main` no traduce `WHEN` y la rama ya lo cambió;
  - que ninguna ruta de la API inserte filas de corte en `rastro_incidencias`: hoy ya es así (solo `--anotar-incidencia`, `servir.py:3084`), compruébalo y sigue.
  - Copiar las anclas diarias fuera del Mac sale de casa: no hoy (decide dirección, D8).
- **Prueba:** `INSERT OR REPLACE` sobre una fila existente de `registro` → error.

### L-16 · Datos reales de dinero y clientes en el repositorio
- **Dónde (`git ls-files`):** `fuentes_dinero/cuotas.json` (cuota de 67 clientes), `fuentes_dinero/impagos_estado.json`, `fuentes_incidencias/rastro_operaciones.json`, `fuentes_bandeja/_cache_cuentas_desk.json`, `fuentes_captacion/anuncios.json`, `fuentes/_muestras/google_ads_septiembre_muestra_2026-10-02.json`, `fuentes/_muestras/seranking_proyectos_2026-10-02.json` y los 10 `fuentes_paneles/_log_*.txt` (ids de los 68 clientes y sus herramientas).
- **Qué pasa:** el LEEME dice «solo código». La cuota es justo lo que la app esconde a casi todos los puestos. El 3-oct ya se recomendó sacar los dos de dinero.
- **Arreglo hoy:** `git rm --cached` de esos ficheros (siguen en tu disco) y sus patrones al `.gitignore`: `fuentes_dinero/*.json`, `**/_log_*.txt`, `**/_cache_*.json`, `fuentes/_muestras/`, `fuentes_incidencias/rastro_operaciones.json`, `fuentes_captacion/anuncios.json`. Comprueba antes que los generadores los siguen encontrando en disco. Quitarlos del historial: no hoy (D6).
- **Prueba:** `git ls-files` no los lista y la app arranca igual.

### L-15 · La IA pasa a real en cuanto hay una clave
- **Dónde:** `ia.py` 65-76 (`clave()` lee `ANTHROPIC_API_KEY` del entorno o del llavero) e `ia_gasto.py:63` (`"activa": True`).
- **Qué pasa:** envíos pide fichero firmado + `RO_ENVIOS_REALES=si`; ClickUp, fichero + `RO_CLICKUP_REAL=si` + llave de servicio. La IA arranca en real con solo tener la clave en el entorno (habitual en el shell de quien programa con Claude) o en el llavero del Mac. Los topes limitan el daño, pero «gasto 0 €» depende de que nadie la tenga a mano.
- **Arreglo (hazlo hoy, es más prudente que lo actual):** la IA solo va en real con `RO_IA_REAL=si` **y** `data/ia/interruptor.json` con `activado_por: "<id de dirección>"`, venga la clave de donde venga. Sigue leyendo los mismos nombres de clave (Render usa `ANTHROPIC_API_KEY`; renombrarla lo decide dirección, D7).
- **Prueba:** con la clave puesta y sin interruptor → la IA responde «sin conectar» y el gasto sigue en 0.

### L-09 · Un setter dado de alta desde Ajustes no ve nada suyo
- **Dónde:** `servir.py:932` y 1121 (`mi_setter` solo si el id empieza por `setter_`), 1133 (`fila.get("setter") in ("<setter_1>", "<setter_2>")`), `fuentes_ventas/generar_ventas_ro.py:43` (setters a mano) y `altas_personas.py:857` (el id nuevo es `slug(nombre)`, sin prefijo).
- **Qué pasa:** una setter nueva («Nueva», id `nueva`) recibe `mi_setter=None`, su pantalla Setters sale vacía y `ver_dato` sobre `ventas_ro/_privado/setter_nueva` falla. Dirección y ventas tampoco verían sus leads en claro.
- **Arreglo:** un campo `clave_setter` en la persona, que pone el alta, usado en `fila_ok`, `nombres_para_su_dueno` y la regla `dueno_setter` de `ver_dato` (`servir.py:2689`). **Rellénalo antes en las dos setters actuales** (`<setter_1>` y `<setter_2>`), o deja el prefijo `setter_` como respaldo: si no, pierden sus filas. En 1133, `in ("<setter_1>", "<setter_2>")` pasa a «cualquier setter que no sea `_closer`». En `generar_ventas_ro.py`, la lista sale de `personas.json` (puesto `setters`). Fuera los nombres fijos.
- **Prueba:** alta de una setter inventada → ve sus filas y su almacén privado.

### L-04 · El recorte de dinero y de datos de leads por nombre de clave deja pasar campos
- **Dónde:** `servir.py` 756 (`CLAVES_CUOTA`), 770 (`CLAVES_COBROS`), 771 (`CLAVES_INVERSION`), 772 (`CLAVES_LEAD`); se aplican en `recortar_modulo` (921).
- **Qué pasa:** las expresiones van ancladas (`^…$`) y distinguen mayúsculas. Con una jefa de SEO inventada (ve el detalle, no la cuota ni la inversión) pasaron `Cuota`, `importe`, `precio_mes`, `facturacion`, `mrr`, `fee`, `tarifa`, `presupuesto`, `Gasto`, `CPL` e `importe_publicidad`. En leads solo caen cinco nombres exactos (`nombre_lead`, `telefono`, `tel`, `correo_lead`, `email_lead`): pasan `email`, `movil`, `whatsapp`, `telefono_contacto`, `dni` e `iban`. En los datos de hoy ya hay `importe`, `facturado_*` y `presupuesto` (Finanzas, Dinero por cliente) y `facturado_mes` en `decisiones/direccion`, que llega a operaciones.
- **Arreglo** (expresiones comprobadas en Python; sin distinguir mayúsculas y por tramos separados por `_`):
  ```
  CLAVES_CUOTA     = (?i)(^|_)((cuota|importe|precio|tarifa|ingres)[a-z]*|fee|fees|mrr|eur)(_|$)
  CLAVES_COBROS    = (?i)(^|_)((factur|cobr|impag)[a-z]*|pendiente_cobro)(_|$)
  CLAVES_INVERSION = (?i)(^|_)((gasto|coste|inversion|presupuesto|publicidad)[a-z]*|cpl|cpa|spend|budget)(_|$)
  CLAVES_LEAD      = (?i)(^|_)(nombre_lead|tel|telefono|movil|m[oó]vil|phone|whatsapp|correo|email|e_mail|mail|dni|nif|nie|iban)(_|$)
  ```
  - Una clave que encaje en dos familias (p. ej. `importe_publicidad`) se quita salvo que la persona vea las dos.
  - Mantén las claves derivadas de la cuota que ya existen (`CLAVES_DERIVADAS_CUOTA`).
  - **Antes de cerrar**, compara `/api/sesion` y 3 ficheros de módulo para un account, un trafficker, administración y operaciones, antes y después. Ninguna cifra que hoy se ve con derecho puede desaparecer (p. ej. la cuota que ve un account de su cartera).
  - DNI, NIE e IBAN también al escáner (`\b\d{8}[A-Z]\b`, `\b[XYZ]\d{7}[A-Z]\b`, `\bES\d{22}\b`), **pero** pásalo antes sobre tu `data/` real: si casa con algo que no es un DNI o IBAN de verdad (referencias de factura o de pedido), ajusta el patrón (letra de control válida) o añádelo a `escaner_permitidos.json`. Si casa en un fichero del núcleo, **toda la API da 503**: nunca lo dejes así.
- **Prueba:** una fila con `Cuota`, `importe`, `facturado_mes`, `cobrado`, `Gasto`, `CPL`, `email`, `movil`, `nombre_lead` y `hotel` para una persona sin cuota ni inversión → queda solo `hotel`.

---

## 3. P1 · Fechas, datos y funcionamiento

### L-21 · El hilo de recargas puede morir en silencio y dejar «Actualizar ahora» colgado
- **Dónde:** `servir.py` 1793-1829 (`trabajador_recargas`). Solo `subprocess.run` va en `try`; `json.loads(RECARGA_CFG…)`, los `UPDATE`, `registrar()` y `calcular_avisos()` no.
- **Qué pasa:** una excepción mata el hilo (`daemon`, nadie lo relanza). Ya hay un `UPDATE … con_fallos` al arrancar (`main`, 3123-3124), pero hasta reiniciar no se atiende ninguna recarga más.
- **Arreglo:** el cuerpo de cada vuelta en `try/except` con la traza; en el `except`, la fila a `con_fallos` y el hilo sigue.
- **Prueba:** forzar una excepción en una vuelta → la siguiente recarga se atiende.

### L-24 · Una persona de baja o desconocida ve «Cargando…» y una orden de terminal
- **Dónde:** `app.js:82`.
- **Qué pasa:** con `?yo=<baja>` o `?yo=<no existe>`: título «Cargando…» para siempre y «Qué hacer: Arranca python3 servir.py… en la carpeta 30_APP_PROTOTIPO».
- **Arreglo:** `app.js:82` pinta lo mismo para 403, 500 y 503; sepáralos. Con 403: «No tienes acceso. Pídeselo a operaciones». Con 500, 503 o sin servidor: «La app no responde. Avisa a operaciones». Nada de texto técnico; la orden de terminal, solo si el host es `127.0.0.1` o `localhost`.

### L-18 · Las horas de Madrid se leen con la zona del navegador
- **Qué pasa:** los datos traen «2026-10-02 23:14» en hora de Madrid, pero no hay una función común que lo pase a instante, así que cada módulo hace `new Date(s.replace(' ', 'T'))` en la zona del navegador. Para un account en Buenos Aires todo vence 5 h tarde; para alguien de dirección en Asia, las antigüedades salen 5-6 h largas o negativas.
- **Dónde decide (no solo pinta):**
  - `alertas.js` 68 (`aFecha`), 116-139 (`venceDe`, `nivelEscalado`), 183-189 (`fechaVuelta`: «posponer a mañana a las 9» a las 9 locales);
  - `mi_dia_bloques.js` 38-39 (`fecha`, `edadH`), 1674 (`reuPasada`), 2097-2151 («Lo mío»); `mi_dia.js:747`;
  - `bandeja.js` 77-80 (`edadH`, la regla de 48 h);
  - `incidencias.js` 93-99 y 169-177 (`fechaLocal`, relojes de 48 h y 24 h), 991, 1031, 1089-1090;
  - `produccion_comun.js` 150-159 (`vence()`) y 181;
  - `agenda.js` 100, 156, 160, 181, 188-189, 471-472 (línea de «ahora»);
  - `_ventas_comun.js` 33 y 50, `captacion.js:238`, `dinero_comun.js:88`, `nuevos.js:57`, `outreach.js:175`, `setters.js:291`, `decisiones.js:172`.
- **Arreglo:** añadir a `fechasDe()` (`componentes.js:1437`) `instante(t)` (lee el texto sin zona como Europe/Madrid), `horasDesde(t)` y `horasHasta(t)`, y cambiar por ellos los ayudantes locales de esos módulos. «Mañana a las 9» = `${fechas.manana()} 09:00`.
- **Prueba:** `despliegue/barrido_total.py` con `TZ=America/Argentina/Buenos_Aires` y con `Asia/Makassar`: mismas vencidas y mismo «Lo mío» que con Madrid.

### L-19 · «Hoy», el mes y el trimestre con `new Date()` local o UTC
- **Dónde:** `reuniones.js` 66, 138, 155, 287 (mes en UTC: el día 1 de 00:00 a 02:00 el «mes en curso» es el anterior); `personas.js` 120, 122, 124, 163; `ventas_ro.js` 73-76; `ficha.js:928` (además divide siempre entre 30); `ficha_equipo.js:200`; `mi_dia_bloques.js` 234, 1707, 1719, 1998; `chat_equipo.js` 78 y 92; `ia_componentes.js:390`; `finanzas.js:34`; `objetivos_comun.js:38`; `en_rojo.js` 264 y 371; `ficha.js:161`; `permisos.js:20` (`hoyISO` en UTC).
- **Arreglo:** `ctx.hoy`, `ctx.fechas.*` y `sumarDias(ctx.hoy, n)`; en `permisos.js`, `fechas.hoy()`. Añadir a `pruebas_coherencia.py` una regla que falle con `new Date().toISOString().slice(` y con `getDate()`/`getMonth()` en `modulos/` y en los `.js` de la raíz.

### L-20 · Meses escritos a mano: desde el 1-nov las pantallas dirán «septiembre» con datos de octubre
- **Textos:** «septiembre» unas 100 veces: `captacion.js` (p. ej. 638 «Inversión gestionada · septiembre»), `ficha.js` (807, 820, 1088), `dinero_cliente.js` (103, 160, 262, 318), `informe.js`, `ventas_ro.js`, `finanzas.js`, `mi_dia_bloques.js`.
- **Lógica:** `informe.js` 727, 1113, 1117 (la paridad con Looker compara siempre con `'2026-09'`); `ventas_ro.js` 76 y 82; `dinero_cliente.js` 143-144 y 372; `finanzas.js` 471, 483, 528, 870 (el desplegable de coste del equipo solo ofrece sep y oct); `panel_direccion.js` 791-793, 1085, 1097, 1143 y `generar_panel_direccion.py:101` (`PERIODOS = ("sep","oct","todo","d14","d7")`); `informe.js` 975-978 (fechas por cliente a mano).
- **Python:** `fuentes/comun.py:139` y `fuentes_informes/generar_informes.py:58` con `anio=2026` por defecto: en enero de 2027 las fuentes saldrán con un año de retraso y como viejas.
- **Arreglo:** etiquetas con `nombreMes(D._meta.mes_anterior)` o `mesMas(ctx.hoy.slice(0,7), -1)`; periodos del panel generados desde hoy; el año, el del reloj de Madrid.
- **Prueba:** con el reloj en 2026-11-03, no aparece «septiembre» ni `2026-09` como mes en curso.

### L-22 · `servir.ahora()` sin zona, pero etiquetada como Madrid
- **Dónde:** `servir.py` 238-239 (`datetime.now().isoformat()`), usada en el ancla del rastro, sesión, decisiones, acciones y Para confirmar; `ia.py` con 13 `datetime.now()` (p. ej. el «hoy» que se manda a la IA); unas 100 más en `fuentes_*` y `despliegue/`.
- **Arreglo:** `datetime.now(MADRID)` en `ahora()`, `P.hoy_iso()` en `ia.py`, y que `despliegue/entrada.sh` pare si `TZ` no es Europe/Madrid.

### L-23 · «Avisar al equipo» sale desactivado aunque el cliente tiene equipo
- **Dónde:** `modulos/ficha_equipo.js` 53-70 (`equipoAvisable`): solo mira `F.verdad.equipo`, que el servidor recorta para un account, y nunca `F.c.equipo`.
- **Arreglo:** usar `cliente.equipo` como respaldo. Dudoso: con tus fichas reales puede que no pase; compruébalo.

### L-25 · Pantallas que quedan vacías por un desajuste de permisos
- **Técnico de altas:** Bandeja «suyo» siempre vacía, porque `sillas_de_puesto` no tiene `tecnico_altas`. **Arreglo:** una silla `altas` con los clientes en alta (no amplía lo que ve fuera de sus altas). Darle «todo» sería ampliar permisos: eso lo decide dirección.
- **Operaciones en Dinero por cliente** (`dinero_cliente.js:130`): pide `finanzas/finanzas` y recibe 403 sin aviso. **Arreglo:** pedirlo solo si `ctx.veModulo('finanzas')`.
- **Proyectos:** ve Dinero por cliente en «todo» pero sin cuotas ni rentabilidad, y `/api/indicadores` (2248) la trata como si viera la cuota. Ya decidido (D1): proyectos ve la cuota por cliente. Aplícalo con el resto de cambios de matriz de la sección 6.

### L-26 · Lecturas que se saltan `ctx`, y otros caminos propios
- `ficha.js` 207-209 (`cargarPrivado` reimplementa `ctx.verDato` copiando las cabeceras de identidad), `panel_direccion.js:937` (`fetch('reglas_permisos.json')`), `dinero_comun.js:108` (rama muerta), `ficha.js` 183-184 (respaldo estático).
- `_ventas_comun.js` 80-91: guarda acciones en `localStorage` sin el campo `modulo`, luego filtra por `modulo` (nunca salen) y lee todo `ctx.api('rastro')` en vez de `acciones?modulo=<id>`.
- `panel_direccion.js:108`: saneado casero del HTML del panel que no cubre `href="java&#9;script:"` ni `data:` (lo frena la CSP y es solo de dirección).
- **Arreglo:** `ctx.verDato()`, `ctx.ver({ tipo: 'sueldo_coste' })` y `acciones?modulo=`; borrar la rama muerta; saneado con lista blanca de etiquetas y atributos.

### L-27 · Rutas y llavero del Mac en lo que corre la tubería (bloquea el despliegue)
- 25 ficheros Python se saltan `config.py` con `Path.home()` o `~/…`. 13 pasos de `despliegue/pasos.json` ejecutan scripts que llevan dentro rutas a `~/Downloads` o `~/RO_HERRAMIENTAS` (agenda, chat_equipo, dinero, ficha, gbp, hostinger, informe, lector_hoja_informes, mi_dia, modular, panel_direccion, paneles, sueldos). `build_data.py` lee `~/Downloads/PANEL_OPERACIONES_2026-10-01/…`. 13 llamadas a `security find-generic-password` en 10 ficheros. `fuentes_consejos/conocimiento/reglas_minadas.json` lleva 103 rutas `/Users/<usuario>/…`.
- **Arreglo:** todo por `config.CRUDOS`, `config.HERRAMIENTAS` y `config.secreto()`, y un `grep` en `despliegue/pruebas_noche.py` que falle con `Path.home()` o `~/` fuera de `config.py`.

---

## 4. P2 · Coherencia entre pantallas

### L-30 · Dos cifras de «clientes bien» en el mismo Mi día
- `mi_dia_bloques.js:856` cuenta a los críticos con salud ≥ 60; `:1878` no. Con un cliente crítico de salud 62, un bloque dice «11 con salud ≥ 60» y el otro «10 de 12». **Arreglo:** una sola `estaBien(v)` en los dos sitios.

### L-31 · «Sin imputar» definido de tres formas
- `verdad/equipo.json → no_imputan_ayer` (tile de Personas y Mi día), `personas.js:290` (filtro con `!p.horas.ayer`), `horas.js:299` (< 15 min) y `mi_dia_bloques.js:1584` (`p.ayer`, y además «día(s)»). **Arreglo:** una definición en la verdad única, con el umbral de 15 min, y todos leen esa.

### L-32 · La ficha cae en el account de la Cartera cuando la verdad no tiene
- `ficha.js` 287 y 745, `incidencias.js:641`, `mi_dia_bloques.js:515`. El LEEME lo prohíbe («nunca el de la Cartera ni el del CRM»). **Arreglo:** si `verdad.account` es `null`, pintar `verdad.sin_account`.

### L-33 · «Días sin reunión» en la ficha frente a «sin reunión el mes pasado» en el resto
- `ficha.js:814` usa 30/35 días; En rojo, Mi día y Reuniones usan `verdad.sin_reunion_mes_pasado`. El mismo cliente sale verde en la ficha y «sin reunión» en En rojo. **Arreglo:** la ficha enseña las dos cosas con el color de la verdad.

### L-34 · Umbrales repetidos a mano
- 31,47 €/h: 10 veces en `dinero_cliente.js` + `indice.js:123`. 128 h: unas 13 (`personas.js`, `reuniones.js`, `horas.js`, `ajustes.js`, `mi_dia_bloques.js`, `indice.js`). Topes 12/16: `personas.js:26` y `mi_dia_bloques.js:743`. Salud 60/40: `componentes.js:379`, `ficha.js:456`, `en_rojo.js:353`, `mi_dia_bloques.js` 856 y 1878.
- **Arreglo:** `modulos/_reglas.js` con `TARIFA_HORA`, `HORAS_MES`, `TOPE_SILLA` y `SALUD_UMBRAL`, y `pruebas_coherencia.py` falla si reaparece un literal.

### L-35 · Alertas no tiene «Deshacer», aunque el LEEME dice que sí
- `alertas.js` no importa `_deshacer.js`; `marcar()` (193-203) y `lote()` (212-224) escriben al momento. Un «Resuelta» en lote no se puede deshacer. **Arreglo:** `conDeshacer({ optimista, hacer, revertir })`, como «Lo mío».

### L-36 · «Reabrir» en Gasto de IA no maneja errores
- `gasto_ia.js:183`: `click: async` sin `try/catch` y sin mirar `ctx.soloLectura`. **Arreglo:** `try/catch` con `avisoFlotante` y `aria-disabled` en «ver como».

### L-37 · Contadores distintos en la misma cabecera
- La campana de dirección (`carcasa.js`, `/api/canales/campana`) marca 12 y «Alertas» marca 13 en la misma pantalla. **Arreglo:** el mismo número, o etiquetas que digan que son cosas distintas.

---

## 5. P2-P3 · Usabilidad y presentación

### L-17 · Modo local: la identidad no tiene firma (P2, sin confirmar)
- **Qué pasa:** si alguien expone el puerto local con un túnel que reescriba `Host` (ngrok, cloudflared, un proxy), `host_ok` (`servir.py:2042`) pasa y entra cualquiera con `?yo=dir` o con la cabecera `Cf-Access-Authenticated-User-Email`, que en local no se comprueba. El modo servidor está bien: solo vale el JWT de Access.
- **Arreglo de hoy, solo esto:** en modo local, no leer `Cf-Access-Authenticated-User-Email` y exigir `self.client_address[0] in ('127.0.0.1', '::1')`. Cambia la prueba N9 de `pruebas_seguridad.py` (~675) para que espere 401 con esa cabecera: es un cambio de contrato a propósito, dilo en el commit.
- **No rechaces `X-Forwarded-*`:** esta noche Next y Nest las ponen al pasar las peticiones a `servir.py`, y todo daría 403.
- **Lo que queda abierto:** el servidor local solo escucha en 127.0.0.1 (3115-3116) y un túnel que corra en el mismo Mac entra desde 127.0.0.1, así que el `?yo=` tras un túnel sigue abierto. Dilo en el commit y deja L-17 `abierto` para Cursor.

### L-38 · Códigos internos a la vista de todo el equipo
- Subtítulos: el campo `resumen` de `modulos/indice.js` se pinta tal cual en `app.js:604`, sin `limpiaTexto`. Ejemplos: Bandeja (`indice.js:28`) «simulado hasta W1… WhatsApp en W6»; Chat (36) W1; Informes mensuales (68) «(D-09)… W5»; Horas (98) «(D-27)»; Reuniones (102) «hasta W4… (D-06)»; Indicadores (142) «E0». Además, los de Paneles, Incidencias y Bandeja ocupan 2-3 líneas.
- «Fase 2 · N indicadores que todavía no se pueden medir» al pie de Mi día y de Bandeja, para todos los puestos.
- Decisiones: el subtítulo dice «las 101 firmadas» fijo mientras la tarjeta dice «Firmadas —».
- **Arreglo:** `resumen` en llano y corto, pasado por `limpiaTexto`; «Fase 2» solo para dirección; el número, del dato.
- **Cuidado:** `permisos.py` lee `indice.js` con expresiones regulares. Toca solo el texto de `resumen`, nunca `puestos_que_lo_ven`, y compara `modulos_puestos` de `/api/sesion` para 5 puestos antes y después: debe salir idéntico.

### L-39 · Vacíos con frases rotas
- `limpiaTexto` (`componentes.js:2102`; la 2106 borra el nombre del fichero) deja la frase coja: SEO (`seo.js:745`) y Redes (`redes.js:403`) dicen «No existe. Se generan con.». Bandeja, Informe, Paneles, Informes mensuales, Incidencias, Captación, CRM, Producción, Horas, Reuniones, Dinero por cliente y Finanzas muestran solo «No existe» (el 404 del servidor).
- **Arreglo:** un vacío común: «Todavía no hay datos de <pantalla> de hoy. Lo arregla <quién>». Nunca el mensaje crudo.

### L-40 · Menús demasiado largos
- Medido: Dirección 35 entradas, operaciones 31, account 24 (+4 de sus clientes = 28; en móvil, 1.325 px de alto), trafficker 21, jefe de SEO 20, GHL 18, producción 15, administración 14, RRHH 13, setter 9.
- Pantallas que no parecen del puesto: un account ve Producción, Horas, Personas, SEO, Redes y Captación; producción ve Captación e Incidencias; RRHH ve En rojo y Producción.
- **Propuesta (decide dirección, D5):** 8-12 entradas fijas por puesto con lo suyo del día; el resto en un grupo «Más» plegado y en ⌘K. Es solo orden y agrupación del menú, no permisos. Si lo preparas, vale el mismo cuidado de L-38 con `indice.js`.

### L-41 · «Lo mío» de dirección repite cada llave que falta, con texto duplicado y una orden de terminal
- `mi_dia.js` 575-577 y las alertas de `generar_alertas`: «ClickUp (llave propia) · Falta la llave: Falta la llave», con el porqué «una fuente no ha llegado a tiempo» (no es eso), otra fila igual más abajo y `security add-generic-password …` a la vista. Igual con Zoho CRM y Desk.
- **Arreglo:** una fila por conexión caída, motivo correcto, y la orden plegada en «Cómo se arregla».

### L-42 · Asistente IA con textos fijos que contradicen el dato
- `asistente_ia.js` 70 y 145: «borradores para los 40 correos más urgentes» y «precalculados del 2-oct» con «Borradores listos 0». **Arreglo:** número y fecha del dato.

### L-43 · «Dinero por cliente» para quien no ve la cuota
- Un trafficker lo tiene en el menú con el subtítulo «Cuota, horas frente a cuota (31,47 €/h) y rentabilidad» (`indice.js:121`), y no verá ninguna de las tres. **Arreglo:** para quien no ve cuota, título «Horas por cliente» y subtítulo acorde.

### L-44 · El vacío de la Agenda desborda en móvil
- A 390 px la página mide 419 de ancho: dentro de `.vacio-g`, el botón «Recargar» mide 40 px y su texto pide 97. Los vacíos de tres columnas parten el título palabra a palabra (p. ej. «Mi día del setter»). **Arreglo:** el vacío se apila por debajo de 640 px.

### L-45 · Etiquetas incoherentes
- «Jefa de publicidad», «Jefa de CRM y outreach» frente a «Jefe de SEO».
- Decisiones: el filtro «Para <persona de proyectos> · 24 h» (`decisiones.js` 56 y 189) lo ve cualquiera, también un account.
- «Ver como»: las personas con dos puestos salen dos veces en el desplegable (una por puesto, mismo valor).
- **Arreglo:** nombres de puesto coherentes; ese filtro solo a quien le toque; una línea por persona con sus puestos al lado.

### L-46 · Elementos pulsables que no son botón
- `horas.js` 208-213 (`<li tabindex=0>` sin `role` ni Espacio) y `chat_equipo.js` 851-855 (`div role=button` sin Espacio). **Arreglo:** `<button>` dentro, o la fila pulsable común.

### L-47 · Pulido de ⌘K y tarjetas
- Esc necesita dos pulsaciones con texto escrito (`ayudas.js:401`) aunque el pie dice «Esc cerrar»; Ctrl+K con la paleta abierta la cierra. Buscar el id de un cliente («cli-a») no lo encuentra. Tarjetas a 0 que se pueden pulsar y no hacen nada («Crítico 0 de 10» en En rojo, «Simulados 0» en Envíos). `catalogo.js:209` pinta «undefined ·» si a `meta.fuentes` le falta `fuente` o `edad_h`.
- **Arreglo:** un Esc cierra; buscar también por id y alias; tarjetas a 0 desactivadas; tolerar el campo vacío.

### L-48 · Documentación que no cuadra con el código
- LEEME: M16 y M17 salen «previsto» pero están hechos (`indice.js` 113 y 116); cita `modulos/paneles_periodo.js`, que no existe; dice que Alertas usa `_deshacer.js` (no, L-35); la tabla de permisos dice que `sueldo` es «nunca, para nadie» y la regla vigente lo permite a dirección y RRHH con rastro. Añadir que el modo estático (`python3 -m http.server`) sirve `data/` entera sin recorte y no se usa nunca con datos reales fuera del Mac.
- `servir.py` 6-7: la docstring dice «Sin nada: Dirección», pero sin identidad responde 401. `permisos.py` 7-9 cita `/api/prueba_paridad`, que no existe.
- `_ESTADO_panel_direccion.md` y `_ESTADO_alertas.md` piden cosas ya hechas. En `indice.js`, `envios` dice `'*': 'suyo'` y el fichero manda «solo dirección, operaciones y técnico».
- **Arreglo:** una pasada de cierre sobre esas líneas.

### L-49 · Deuda: no agrandarla hoy
- Ficheros enormes: `mi_dia_bloques.js` 203 KB, `componentes.js` 191 KB, `servir.py` 189 KB, `ficha.js` 140 KB. `servir.py` engancha las rutas de `avisos`, `envios`, `sincronia` e `ia` reescribiendo `_api_get` y `api_post` en cadena: el orden de importación decide qué ruta gana.
- Sin uso: `modulos/rastro.js` (nadie lo importa) y `modulos/panel_direccion_estilo.js` («YA NO SE USA»).
- Plurales a mano: `mi_dia_bloques.js:1584` y `produccion_comun.js:155`. Medidas en línea en `gasto_ia.js` 93 y 105. Caché fija `ro-pagina-v1` en `sw.js`. Argumento mutable en `generar_agenda.py:191`.
- Paridad del navegador: `permisos.js` no hace «ver como» = mínimo de las dos personas; `datos.js` `recortar()` no quita importes de los textos; `nivelModulo` revienta si la persona no trae `puestos` (`permisos.js:28`). Solo afectan al modo estático, pero conviene dejarlos iguales al servidor.
- **Hoy:** borra lo que no se usa y arregla los plurales. Partir ficheros y ordenar rutas lo hace la migración.

---

## 6. Decisiones de dirección (no las tomes tú)

dirección ya contestó (columna de la derecha). D5 es L-40. D6: no reescribas el historial. Lo que dice «pendiente», no lo toques.

**Cambios de matriz decididos por dirección (4-oct, 09:42 y 09:45)**. Todos van en `reglas_permisos.json` y en `modulos/indice.js`, con un caso por línea en `pruebas_seguridad.py`. Compara `modulos_puestos` y `/api/sesion` de los puestos afectados antes y después.
- `tipos.cuota.si`: añadir `proyectos`.
- `tipos.rentabilidad_cliente.si`: añadir `proyectos` (el beneficio por cliente aún no existe; queda listo).
- `tipos.inversion.si`: añadir `proyectos`; `trafficker` pasa a todos los clientes (quitar `cartera: "trafficker"`).
- `tipos.dinero_empresa.si`: añadir `administracion`, que ve también los totales de la agencia. `caja` y `cobros` se quedan como están (dirección, finanzas de dirección y administración). Finanzas de dirección no se asigna a nadie más que a dirección; ya está en `puestos_solo_tomas`.
- `puestos_solo_tomas`: añadir `proyectos`, `tecnico_altas`, `jefa_publicidad`, `jefa_crm` y `jefa_seo` (D2).
- `indice.js`, Captación: `produccion` no la ve (D4); `trafficker` pasa a `todo`.
- `indice.js`, Bandeja: `jefa_seo` solo ve las quejas de SEO y web (D3). Si la Bandeja no sabe clasificar por tema, quítasela (`null`) y que las quejas le lleguen por En rojo e Incidencias; no la dejes en `todo`.
- Técnico de altas: la silla `altas` de L-25.
- Toca solo esos valores de `indice.js`, nunca el formato: `permisos.py` lo lee con expresiones regulares.

| Id | Pregunta | Recomendación | Respuesta de dirección (4-oct) |
|---|---|---|---|
| D1 | ¿Proyectos ve la cuota y la rentabilidad por cliente? Hoy ve la pantalla «todo» pero sin cifras | Que la vea, o quitarle la pantalla; la pantalla vacía no vale | Sí: proyectos ve la cuota y la inversión de cada cliente y, cuando exista, el beneficio por cliente. El dinero de la agencia lo ven dirección y administración |
| D2 | ¿operaciones puede dar jefaturas, `proyectos` o `tecnico_altas` (acceso a todos los clientes) sin dirección? Hoy sí | Añadirlos a `puestos_solo_tomas` | Sí: los da solo dirección |
| D3 | ¿La jefa de SEO ve todos los correos de clientes en Bandeja? Hoy «todo» | Bajarla a «suyo» o a solo SEO y web | Ni Bandeja entera ni nada: solo las quejas de clientes por SEO o web. Si no se pueden clasificar, por En rojo e Incidencias |
| D4 | ¿Producción ve Captación? Hoy le llegan filas sin cliente y el detalle de sus clientes (sin dinero) | Proyectar con «resumen» | Producción creativa no ve Captación. Los traffickers ven la Captación de todos los clientes |
| D5 | Menús: ¿8-12 entradas por puesto y el resto en «Más»? | Sí | Sí, a criterio de Claude |
| D6 | ¿Quitar `cuotas.json`, `impagos_estado.json` y los logs también del historial de GitHub? Obliga a reescribir todas las ramas y forzar la subida | Sí, pero mañana, después de la noche y sobre todas las ramas a la vez. Hoy basta con L-16 | No reescribir el historial; basta con L-16 (los ficheros siguen en disco y la app funciona igual) |
| D7 | ¿Renombrar la clave de la IA a `RO_ANTHROPIC_API_KEY`? Hay que cambiarla también en Render | Sí, junto con el despliegue | Sí, el día del despliegue |
| D8 | ¿Copiar las anclas diarias del rastro fuera del Mac (R2 o correo)? | Sí, cuando se active la copia en R2 | Sí, cuando se active la copia en R2 |

---

## 7. A las 19:00: el estado, para Cursor

Actualiza la tabla **solo** en `~/RO_MIGRACION/PENDIENTES_LOGICA.md`, fuera de git: Cursor la lee primero (paso F5.10) y manda sobre la del repo. No edites `migracion/`.

- Dirección ya lo dejó ahí con la cabecera y las 49 filas, todas `abierto`. **Solo cambias la columna Estado:** `arreglado hoy (<commit>)`, `ya estaba`, `abierto` o `decide dirección (Dn)`.
- Sin datos reales: «persona con puesto X», «cliente de prueba».
- Lo que encuentres tú y no esté, añádelo como L-50 en adelante.

Y responde a dirección con un resumen corto: cuántos puntos cerrados, cuáles quedan abiertos y por qué, y qué baterías pasan.
