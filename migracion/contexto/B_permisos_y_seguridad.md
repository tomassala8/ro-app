> Recogido en: `migracion/PENDIENTES_LOGICA.md` (L-02…L-17 y anexo de permisos) y `SUPERPROMPT_ASTRA_2026-10-04.md`. Es la auditoría de permisos que los originó (anexo B). La tabla puesto × módulo del §5 es la matriz **antes** de los cambios del 4-oct (ver `ACCESOS_POR_PUESTO_PARA_CONFIRMAR.md`).
> **Copia saneada para Cursor (4-oct-2026).** Fuente: `/mnt/project-files/feedback_herramienta/anexos/`. Personas de prueba por su puesto; ejemplos de sueldo quitados.

# B · Permisos y seguridad de la app de RO (ro-app, rama main)

Revisión del 4-oct-2026. Copia revisada: `scratchpad/app_b`. No se ha tocado esa copia.

**Cómo se ha probado:**
- Lectura del código.
- Una prueba de paridad propia entre Python y JS.
- Una copia aparte (`scratchpad/b_pruebas/app`) con datos inventados mínimos: 9 personas y 4 clientes.
- `servir.py` arrancado en local, en el puerto 8791, con base de pruebas `RO_DB`.

Lo que no se ha podido probar va marcado **«sin confirmar»**.

Gravedades: **P0** expone datos o permite suplantar · **P1** fallo de permisos o funcional · **P2** incoherencia · **P3** pulido.

---

## Resumen de hallazgos

| # | Gravedad | Título | Estado |
|---|---|---|---|
| 1 | P0 | «Ver como» deja leer el rastro y las acciones personales de cualquiera (también de dirección), sin dejar rastro | Probado |
| 2 | P1 | La puerta de secretos solo mira `data/` al cargar: un fichero que cambia después se sirve sin escanear | Probado |
| 3 | P1 | El recorte de dinero por nombre de clave deja pasar `importe`, `precio_*`, `facturacion`, `mrr`, `fee`, `tarifa`, `presupuesto` (número), `Cuota`, `Gasto`, `CPL`… | Probado con datos inventados |
| 4 | P1 | Un fichero de módulo con `cliente_id` en la raíz (no dentro de una lista) llega entero a quien no lleva ese cliente | Probado con datos inventados. Los generadores actuales cumplen el contrato |
| 5 | P1 | Las capturas de «Algo va mal» de dirección (Panel de dirección, Finanzas) las ve operaciones | Probado |
| 6 | P1 | Un setter dado de alta desde Ajustes no ve nada suyo: la regla depende de ids `setter_<clave>` y de «<setter_1>»/«<setter_2>» escritos a mano | Leído en el código, sin datos reales |
| 7 | P1 | En Postgres (Render) el rastro y varios disparadores no funcionan: `BEGIN IMMEDIATE`, disparadores con `WHEN`, `INSERT OR REPLACE` | Sin confirmar: no hay Postgres aquí |
| 8 | P2 | `HEAD` se salta todo: host, identidad y Access. Da tamaño y fecha de cualquier fichero (`local.db`, `_privado/`) | Probado |
| 9 | P2 | El rastro «imborrable» se reescribe con `INSERT OR REPLACE` sin que salten los disparadores | Probado. La cadena de huellas lo detecta |
| 10 | P2 | Las lecturas en «ver como» fuera de `/api/modulo`, `/api/cliente` y `/api/buscar` no dejan rastro | Probado |
| 11 | P2 | `/api/acciones`: `objeto` libre sin cliente, tickets que el servidor no conoce y `decision_nueva` sin validar | Probado |
| 12 | P2 | `/api/ajustes/asignacion` no valida silla del puesto, persona activa ni fechas | Leído en el código |
| 13 | P2 | Hay dos caminos para dar de baja y no hacen lo mismo (`/api/ajustes/persona` frente a `/api/altas/baja`) | Leído en el código |
| 14 | P2 | `/api/cliente/<id>` no mira el módulo: sirve la ficha a quien no ve «Ficha» (outreach) o la ve en «resumen» (redes, producción) | Leído en el código |
| 15 | P2 | operaciones puede dar jefaturas, `proyectos` o `tecnico_altas` (todos los clientes) sin dirección | Leído en el código. Decisión de dirección |
| 16 | P2 | Importes en texto: un «gasto 300 €» cerca de la palabra «Cuota» se cuenta como cuota y no se tapa a quien no ve la inversión | Probado |
| 17 | P2 | Incoherencias de matriz: proyectos y rentabilidad; técnico de altas sin silla («suyo» vacío); jefa de SEO con toda la Bandeja | Leído en el código |
| 18 | P2 | Modo local: la identidad no tiene firma. Si alguien lo expone con un túnel que reescriba `Host`, entra cualquiera con `?yo=dir` | Sin confirmar: depende de cómo se exponga |
| 19 | P3 | Pulido: textos que no dicen la verdad, `hoy` en UTC en JS, DNI e IBAN fuera del escáner, comodines de `fnmatch`, GET que escribe… | Varios |

**Resultados limpios:**
- Paridad Python ↔ JS: **38.812 casos sin ninguna diferencia**.
- Inyección SQL: no hay.
- Path traversal en `/api/modulo` y `/api/ver_dato`: no hay.
- XSS: no hay por `innerHTML` con datos.
- Escrituras en «ver como»: bloqueadas en todas las rutas POST. No hay PUT ni DELETE.
- Suplantación en modo servidor: no se puede. Solo vale el JWT firmado de Access.

---

## 1. Paridad `permisos.py` ↔ `permisos.js`

**Prueba:** `scratchpad/b_pruebas/gen.py`, `py.py` y `js.mjs`.

Se generaron:
- 62 personas con 1-3 puestos al azar, incluido uno sin puestos y uno con un puesto que no existe.
- ~180 asignaciones con estos casos límite:
  - `desde` y `hasta` en ayer, hoy, mañana, vacío y `None`;
  - suplencias sin `hasta`, vencidas y con `hasta` = hoy;
  - silla `None`;
  - `suplencia` puesta como `0`, `1` o `None`.
- 39 tipos × 4 clientes × 4 personas objetivo.

Se compararon `carteraPorSilla`, `ambito` y `ver()` (ok, nivel y desenmascarable): **38.812 resultados idénticos**.

Los casos límite se comportan igual en los dos:
- `hasta` = hoy está vigente.
- Una suplencia sin `hasta` no da cartera.
- Una suplencia vencida no da cartera.
- Con varios puestos manda el mejor.
- Una persona de baja conserva su cartera en `permisos.*`. No entra porque `servir.py` la para por `estado`.

Diferencias que sí existen (ninguna afecta al servidor):

### 1.1 «Ver como» = mínimo de las dos personas, solo en Python — P3
- **Dónde:** `permisos.py:173-224`. `permisos.js` no lo tiene.
- **Por qué:** en el navegador, `ctx.ver()` en «ver como» puede enseñar botones que el servidor después niega. No expone nada, porque el servidor recorta.
- **Arreglo:** documentarlo en `permisos.js`, o pasar `soloLectura` y el real a `ver()` del cliente.

### 1.2 `hoy` distinto — P3
- **Dónde:** `permisos.js:20`. `hoyISO()` usa UTC (`toISOString`). `permisos.py` usa Madrid (`hoy_iso`).
- **Por qué:** entre las 00:00 y las 02:00 de Madrid, JS cree que es ayer. Solo afecta al modo estático (`datos.js recortar`), porque con servidor la cartera llega hecha.
- **Arreglo:** usar `fechas.hoy()` de Madrid en `permisos.js`.

### 1.3 `recortar()` de `datos.js` no hace lo que hace `permisos.recortar` — P3
- **Dónde:** `datos.js:70-120`.
- **Por qué:** no quita importes de los textos de detalle y no pasa `enlace_seguro` a las alarmas. Solo cuenta en modo estático, pero ese modo sirve `data/` entero al navegador (ver 19.6).

### 1.4 `nivelModulo` en JS revienta si `persona.puestos` no existe — P3
- **Dónde:** `permisos.js:28`. Python lo tolera.

### 1.5 La docstring cita una ruta que no existe — P3
- **Dónde:** `permisos.py:7-9`.
- **Por qué:** menciona `/api/prueba_paridad`, y esa ruta no está en `servir.py`. La paridad real está en `pruebas_e0.py` y en la prueba de arriba.
- **Arreglo:** corregir el texto.

---

## 2. Recortes en `servir.py`

### Hallazgo 3 · P1 · El recorte de dinero por clave deja pasar dinero con otros nombres

**Dónde:**
- `servir.py:756` (`CLAVES_CUOTA`), `:770` (`CLAVES_COBROS`), `:771` (`CLAVES_INVERSION`) y `:772` (`CLAVES_LEAD`).
- Se aplican en `recortar_modulo` (`servir.py:921-1018`).

**Por qué:**
- Las expresiones van ancladas (`^…$`) y distinguen mayúsculas.
- Pasan intactas: `importe`, `precio_mes`, `facturacion`, `mrr`, `fee`, `tarifa`, `presupuesto` (si es un número), `importe_publicidad`, `Cuota`, `Gasto` y `CPL`.
- Con `CLAVES_LEAD` igual: solo cae `telefono` exacto. Pasan `email`, `movil`, `whatsapp`, `telefono_contacto`, `tel_m`, `nombre_m`, `dni` e `iban`. Hoy los frena la puerta de secretos, que no mira DNI ni IBAN y no se aplica a ficheros nuevos (hallazgo 2).

**Prueba:** `recortar_modulo` con una jefa de SEO inventada (`jefa_seo`), que ve el detalle pero ni cuota ni inversión. Fila de `c0` con todas esas claves. Resultado:
`{"Cuota": 999, "importe": 1000, "precio_mes": 300, "facturacion": 3000, "mrr": 1000, "fee": 500, "tarifa": 31, "presupuesto": 800, "Gasto": 7, "CPL": 11, "importe_publicidad": 50}`.
Sí se quitan `cuota`, `gasto_meta`, `spend`, `inversion_ads`, `cpl`, `coste_lead` y los importes del texto.

**Con datos reales:** sin confirmar. Los generadores actuales usan casi siempre nombres reconocidos. Sí aparecen:
- `importe`, `facturado_*` y `presupuesto` en `fuentes_dinero/` (ficheros de Finanzas y Dinero por cliente);
- `facturado_mes` en `decisiones/direccion`, que llega a operaciones, y operaciones no ve cobros según `tipos.cobros`.

**Arreglo:**
1. Expresiones sin distinguir mayúsculas y por palabra:
   `(?i)(^|_)(cuota|importe|precio|factur|mrr|fee|tarifa|ingres|presupuesto|budget|gasto|coste|cpl|spend|inversion|eur)(_|$)`.
2. Por defecto, quitar cualquier número cuya clave contenga `eur` o `importe`.
3. Lista de permitidas, no de prohibidas: cada fichero de `datos_de_modulo` declara qué claves de dinero lleva y de qué tipo (cuota, cobros o inversión), y lo demás numérico con forma de dinero se quita.
4. Para leads: `(?i)(tel|movil|m[oó]vil|phone|whatsapp|correo|email|mail|dni|nif|iban)`.

### Hallazgo 4 · P1 · `cliente_id` en la raíz del fichero no filtra

**Dónde:** `servir.py:941` (`fila_ok`, solo para elementos de listas) y `servir.py:1003` (`out = paso(obj)`). En la raíz, `cliente_id` solo decide qué dinero se quita; no decide si el fichero llega.

**Por qué:** `paneles/<herr>/*` e `informe/c_*/*` son ficheros por cliente. Si uno trae `{"cliente_id": "c2", …}` arriba en lugar de `{"filas": [{cliente_id…}]}`, llega entero (sin dinero) a cualquiera que vea el módulo.

**Prueba:** La persona account lleva c0 y c1. `GET /api/modulo/paneles/meta/c2?yo=account1` devolvió `{"cliente_id":"c2","campanas":[{"nombre":"Camp secreta c2","leads":40}],…}`. Lo mismo pasó con `informe/c_2026-09/c2` («Informe privado de c2»). En cambio, `/api/cliente/c2` da 403.

**Con datos reales:** `generar_paneles.py` y `partir_informe.py` escriben `{"filas":[…]}`, así que hoy no hay fuga. La protección depende de que cada generador respete el contrato.

**Arreglo:** en `recortar_modulo`, si `obj` es un dict con `cliente_id` y `fila_ok(obj)` es falso, devolver 403 o `recorte_vacio`. Además, para los patrones por cliente (`paneles/*/<cid>`, `informe/c_*/<cid>`), comprobar en `puerta_modulo` que el último trozo de la ruta es un cliente que ve.

### Hallazgo 2 · P1 · La puerta de secretos no mira los ficheros que cambian después de cargar

**Dónde:**
- `servir.py:610`: `E.bloqueados = ESC.escanear(DATA)` solo se calcula en `Estado.cargar()`.
- `leer_json_bueno` (`servir.py:1215`) lee el fichero en cada petición.
- `recargar_si_cambian` (`servir.py:1175`) solo vigila reglas y módulos.

**Por qué:**
- Los timers locales (`despliegue/servidor/*.timer`) y los pasos de una recarga escriben en `data/`. Hasta el siguiente `E.cargar()` (al final de una recarga de la app, o al reiniciar), lo nuevo se sirve sin escanear.
- Un correo o teléfono de lead colado por un generador llega a quien vea el módulo.
- Las claves de lead del recorte son pocas (hallazgo 3), así que la puerta es la barrera principal.

**Prueba:** se creó `data/en_rojo/atajos.json` con el servidor ya arrancado, con email, móvil, WhatsApp, teléfono, salario y sueldo. `GET /api/modulo/en_rojo/atajos?yo=admin1` lo devolvió entero. El escáner (`ESC.escanear`) lo marca: 6 hallazgos (correo, 3 teléfonos y 2 sueldos).

**Arreglo:** en `leer_json_bueno`, cuando cambie `(mtime, size)`, escanear ese fichero (`ESC.escanear_fichero` o equivalente). Si da hallazgos, meterlo en `E.bloqueados` y responder 503. Así, la puerta va con el dato y no con la carga.

### Rutas `/api/*` que sacan datos sin pasar por `recortar_modulo`

Revisadas una a una (`servir.py:2190-2486` y los enganches de `ia.py`, `avisos.py`, `altas_personas.py`, `envios.py`, `sincronia.py`, `vigia.py` y `servidor_gbp.py`). Casi todas se recortan con su propia regla. Las que no:

#### 2.a · `/api/rastro` y `/api/acciones` sin `?modulo=` — P0 en «ver como»
Ver hallazgo 1.

#### 2.b · `/api/acciones?modulo=X`: `texto` y `vista_previa` sin recortar — P2
- **Dónde:** `servir.py:2291-2319`.
- **Por qué:** solo se recortan los tipos de `acciones_vista_previa_recortada` (2 tipos). El texto que escribe un account («te recuerdo la cuota de 1.470 €») lo leen todos los que ven ese módulo y ese cliente: jefa de SEO, técnico de altas…
- **Arreglo:** pasar `texto` y `vista_previa` por `P.sin_importes(…, quitar_para(persona, cp, cid))` y por `recortar_doc`, igual que la ficha.

#### 2.c · `/api/opiniones/captura` — P1
Ver hallazgo 5.

#### 2.d · `/api/decisiones` — P3
- **Dónde:** `servir.py:1736-1773`.
- **Por qué:** Dirección y operaciones reciben `problema` y `recomendacion` sin quitar dinero de empresa. Operaciones no ve `dinero_empresa`.
- **Arreglo:** aplicar `textos_sin_importes_salvo: dinero_empresa`, como en `decisiones/firmadas`.

**Claves anidadas y listas de listas: bien.** `paso()` recorre a cualquier profundidad. En la prueba, `[[{"cliente_id":"c2"}]]` llegó a la persona account como `[[]]`. Las filas que llevan el cliente en otra clave (`cli`, `cliente`, `cid_otro`) no se filtran por cliente. En Producción y Reuniones es a propósito: la fila se filtra por `persona_id`.

---

## 3. «Ver como»

**Escrituras: bien bloqueadas.**
- `servir.py:2513-2515` corta todo POST salvo `/api/ver_dato`.
- Los enganches que entran antes que ese corte comprueban `real != persona` por su cuenta: `avisos.py:933`, `envios.py:1001`, `sincronia.py:1311`, `avisos_programados.py:939`, `altas_personas.py:806` y `:643`, `vigia.py`, `fuentes_modular/acceso.py`, `servidor_gbp.py:160` (`responder`), `ia_gasto.puede_ver`, y en `ia.py`, `valorar`, `borrador` y `copiloto` sin generar.
- `/api/gbp/borrador` en «ver como» solo usa reglas y deja rastro.
- No hay `do_PUT` ni `do_DELETE`: devuelven 501.
- **Excepción menor (P3):** `GET /api/sincronia` escribe (`sincronizar(con)` y `commit`, `sincronia.py:1264`) también en «ver como». Es un sincronizado interno y no se atribuye a nadie.

### Hallazgo 1 · P0 · «Ver como» da más de lo que tiene la persona real

**Dónde:**
- `servir.py:2280-2290` (`/api/rastro`)
- `servir.py:2304-2305` (`/api/acciones` sin `?modulo=`)

**Por qué:**
- Sin `rastro_todo`, la consulta es `WHERE quien=persona OR como=persona` para la persona **vista**.
- El tipo `rastro_todo` sí pasa por el mínimo de las dos personas. Esta lista personal no.
- Operaciones viendo como dirección recibe las 500 últimas filas del rastro de dirección y sus 200 acciones (`texto` y `vista_previa` enteros). Ahí hay decisiones, cambios de Ajustes, «ver datos» de sueldos (a quién y cuándo), acciones de Finanzas con importes, topes de IA…
- Lo mismo con cualquier persona con un puesto que operaciones no tiene: finanzas de dirección, RRHH, administración.
- Además, esa lectura **no deja rastro**: `apuntar_lectura_ver_como` (`servir.py:2185`) solo se llama para `/api/modulo/`, `/api/cliente/` y `/api/buscar`.

**Prueba:**
1. `POST /api/decisiones?yo=dir` con el título «Subir sueldo a <persona> <importe inventado>», y `POST /api/rastro?yo=dir` con la nota «privado de dirección».
2. `GET /api/rastro?yo=ops` → `[]`.
3. `GET /api/rastro?yo=ops&como=dir` → las dos filas de dirección con sus `datos`.
4. Después, `GET /api/rastro?yo=dir` no muestra ninguna fila con `como` que delate la lectura.

**Arreglo:**
- En «ver como», `/api/rastro` y `/api/acciones` (sin módulo) devuelven solo `WHERE como=persona AND quien=real`: lo que el real hizo como esa persona. Otra opción es 403.
- Si se quiere enseñar la lista de la vista, filtrarla por lo que vería el real: sin colecciones `sueldos`, `leads`, `contactos`, `decisiones` ni `finanzas`.
- Añadir `/api/rastro`, `/api/acciones`, `/api/decisiones`, `/api/ajustes`, `/api/altas`, `/api/perfil`, `/api/opiniones` e `/api/ia/` a `apuntar_lectura_ver_como` (o apuntar toda petición en «ver como»).

**Lo demás no da más que lo que tiene el real:**
- `ver()` y `nivel_modulo()` calculan el mínimo.
- `puestos_de()` da la intersección.
- `puerta_modulo` exige que el real también tenga el puesto (`puestos_ok`), `solo_real` y `solo_propio` con el real.
- `nombres_para_su_dueno` no se aplica en «ver como».
- `ver_dato` usa el mínimo y deja rastro con `como`.

---

## 4. Identidad: `?yo=`, cabecera de Access y galleta

**Modo servidor (`RO_MODO=servidor`): bien.**
- `_quien` (`servir.py:1998-2002`) solo cree el JWT de Access, con firma RS256, audiencia, emisor, `exp` y `nbf` comprobados (`despliegue/acceso_cf.py`).
- `?yo=`, `X-RO-Yo` y la galleta `ro_yo` no valen.
- No arranca sin `RO_CF_EQUIPO` y `RO_CF_AUD`.
- Sin `RO_MODO`, `servir.py` escucha solo en 127.0.0.1 y sale si hay `PORT` o `--bind` a otra dirección (`servir.py:3105-3110`). Si se despliega sin la variable, falla cerrado.
- `render.yaml` y `docker-compose.yml` ponen `RO_MODO=servidor`.

**Modo local:**
- **Cualquiera que llegue a 127.0.0.1 es quien diga.** `?yo=`, `X-RO-Yo`, la galleta y `Cf-Access-Authenticated-User-Email` (`servir.py:2003`) se aceptan sin firma. Es lo previsto.
- La barrera es `host_ok()` (`servir.py:2042`): `Host` tiene que ser `127.0.0.1:<puerto>` o `localhost:<puerto>`. Frena el «DNS rebinding».
- Los POST exigen `X-RO-App` y JSON. No se responde a OPTIONS, así que otra web no puede escribir.

### Hallazgo 18 · P2 · Sin confirmar · Exponer el modo local abre la suplantación
- **Por qué:** si alguien expone el puerto local con un túnel que reescriba `Host` (`ngrok --host-header=rewrite`, `cloudflared --http-host-header localhost:8770`, un proxy inverso), `host_ok` pasa. Entonces cualquiera entra con `?yo=dir`, o con `Cf-Access-Authenticated-User-Email: persona@ejemplo.test`, que en local no se comprueba.
- **Arreglo:** en modo local:
  - rechazar cualquier petición con `X-Forwarded-For`, `Forwarded`, `Cf-Connecting-Ip`, `Cf-Ray` o `X-Real-Ip`;
  - no leer nunca `Cf-Access-Authenticated-User-Email` (hoy no aporta nada en local y es una puerta);
  - comprobar `self.client_address[0] in ('127.0.0.1', '::1')`.

### 4.b · La docstring dice lo contrario de lo que hace el código — P3
- **Dónde:** `servir.py:6-7` dice «Sin nada: Dirección (solo prototipo)».
- **Por qué:** desde la ronda 6, sin identidad la respuesta es 401.
- **Arreglo:** corregir el texto, que confunde a quien despliega.

### 4.c · operaciones puede cambiar el correo de una persona sin pasar por dirección — P2
- **Dónde:** `servir.py:2871`, `/api/ajustes/persona` con `correo`.
- **Por qué:**
  - En modo servidor, `por_correo` usa ese correo como identidad si no está en `correos_entrada.json`.
  - Esta ruta no crea la tarea de Access para dirección. `/api/altas/cambio` sí la crea.
  - La unicidad no mira `correos_entrada.json` (`correo_libre` de altas sí lo mira).
- **Arreglo:** que esta ruta no acepte `correo`, o que use `correo_libre` y `nueva_tarea(access_anadir)` como altas.

---

## 5. Coherencia por puesto

### Tabla puesto × módulo

Es la matriz que aplica el servidor: `P.cargar_modulos()`, es decir, `indice.js` más el `puestos_que_lo_ven` de cada fichero más `modulos_sin_puesto`. Es la misma que recibe el menú (`modulos_puestos` en `/api/sesion`).

Leyenda: ● todo · ◐ suyo · ○ resumen · · no lo ve.

| módulo | dir | fin | adm | ops | pro | rrh | acc | trf | jpu | ghl | jcr | tec | jse | seo | fgo | web | red | prd | set | vro | out |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mi-dia | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | · | ● | ● |
| en-rojo | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | · | ● | ● |
| bandeja | ● | ● | · | ● | ● | · | ◐ | ◐ | ● | ◐ | ● | ◐ | ● | · | · | · | · | · | · | · | · |
| agenda | ● | ◐ | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| chat-equipo | ● | ◐ | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| asistente-ia | ● | · | · | ● | ● | · | ◐ | · | ● | · | ● | · | ● | · | · | · | · | · | · | · | · |
| alertas | ● | ◐ | ● | ● | ● | ● | ◐ | ◐ | ● | ◐ | ● | ● | ● | ◐ | ◐ | ◐ | ◐ | ◐ | · | ◐ | ◐ |
| ficha | ● | ● | ○ | ● | ● | · | ◐ | ◐ | ● | ◐ | ● | ● | ● | ◐ | ◐ | ◐ | ○ | ○ | · | · | · |
| informe-cliente | ● | ● | · | ● | ● | · | ◐ | ◐ | ● | · | ● | · | ● | ◐ | ◐ | · | · | · | · | · | ◐ |
| paneles | ● | ● | · | ● | ● | · | ◐ | ◐ | ● | ◐ | ● | ● | ● | ◐ | ◐ | ◐ | ◐ | · | · | · | · |
| clientes-nuevos | ● | ● | ○ | ● | ● | · | ◐ | ◐ | ● | ◐ | ● | ● | ○ | · | · | · | · | · | · | · | · |
| informes-mensuales | ● | ● | · | ● | ● | · | ◐ | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| incidencias | ● | ◐ | ◐ | ● | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| captacion | ● | ● | · | ● | ● | · | ◐ | ◐ | ● | ○ | ○ | ○ | · | · | · | · | · | ○ | · | · | · |
| salud-crm | ● | ● | · | ● | ● | · | ◐ | ○ | ○ | ◐ | ● | ● | · | · | · | · | · | · | · | · | · |
| seo-web | ● | ● | · | ● | ● | · | ◐ | ◐ | ○ | · | · | ○ | ● | ◐ | ◐ | ◐ | · | · | · | · | · |
| redes | ● | ● | · | ● | ● | · | ◐ | · | · | · | · | · | ○ | · | · | · | ◐ | ○ | · | · | · |
| produccion | ● | ◐ | · | ● | ● | ○ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | · | ◐ | ◐ |
| horas | ● | ◐ | ◐ | ● | ◐ | ● | ◐ | ◐ | ● | ◐ | ● | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| reuniones | ● | ◐ | · | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| personas | ● | ◐ | ◐ | ● | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| setters | ● | · | · | ○ | · | · | · | · | · | · | ○ | · | · | · | · | · | · | · | ◐ | ● | · |
| ventas-ro | ● | · | · | ○ | ○ | · | · | · | · | · | ○ | · | · | · | · | · | · | · | · | ● | ○ |
| prospeccion | ● | · | · | ○ | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | · | · | ◐ |
| dinero-cliente | ● | ● | ● | ● | ● | · | ◐ | ○ | ○ | · | · | · | · | · | · | · | · | · | · | · | · |
| finanzas | ● | ● | ● | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| panel-direccion | ● | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| decisiones | ● | ◐ | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| ajustes | ● | · | · | ● | · | ○ | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| indicadores | ● | · | · | ● | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| componentes | ● | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| primera-semana | ● | ◐ | ◐ | ● | ● | ● | ◐ | ◐ | ● | ◐ | ● | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| mi-perfil | ● | ◐ | ◐ | ● | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| conexiones | ● | · | · | ● | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | · | · |
| envios | ● | · | · | ● | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | · | · |
| avisos-automaticos | ● | ◐ | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| gasto-ia | ● | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |

Abreviaturas: dir dirección · fin finanzas de dirección · adm administración · ops operaciones · pro proyectos · rrh RRHH · acc account · trf trafficker · jpu jefa de publicidad · ghl especialista GHL · jcr jefa de CRM · tec técnico de altas · jse jefa de SEO · seo SEO · fgo ficha de Google · web web · red redes · prd producción · set setters · vro ventas de RO · out outreach.

Ámbito de clientes con detalle:
- **todos:** dirección, finanzas, administración, operaciones, proyectos y técnico de altas.
- **disciplina** (que en la práctica es todos): las tres jefas.
- **cartera:** account, trafficker, GHL, SEO y ficha de Google.
- **tareas:** web, redes y producción.
- **ninguno:** RRHH, setters, ventas de RO y outreach.

### Menú frente a datos del servidor

Se cruzaron los ficheros que pide cada módulo (búsqueda de `datosModulo` y `api('modulo/…')`) con `datos_de_modulo`. También todas las fuentes de `data/mi_dia/config.json`.

- **Mi día:** sin huecos. La pantalla comprueba `veModulo` antes de pedir y casa con el servidor.
- **No hay módulos «hecho» sin entrada en `datos_de_modulo`.**
- Los cruces que dan 403 los evita el propio cliente, que primero pregunta `veModulo`, el puesto o atrapa el error:
  - `incidencias` → `bandeja/bandeja` solo si ve Bandeja;
  - `personas` → `captacion/captacion` solo si ve Captación, y `personas_m20/contratacion` solo si ve Ajustes;
  - `conexiones` → `ajustes/conexiones` solo si ve Ajustes;
  - `paneles` → cada herramienta excluida por `excluir_puestos`;
  - `decisiones/direccion` solo para dirección y operaciones.

**Pantallas que quedan vacías o a medias:**

- **5.1 · P3 · operaciones pierde la comparación con la empresa en Dinero del cliente.**
  - **Dónde:** `dinero_cliente.js:130` pide `finanzas/finanzas` con `todo && veCuota`.
  - **Por qué:** para operaciones esa condición se cumple, pero `finanzas/finanzas` es solo de dir, fin y adm, así que da 403 sin aviso.
  - **Arreglo:** pedirlo solo si `ctx.veModulo('finanzas')`.
- **5.2 · P2 · Proyectos ve Dinero del cliente sin dinero.**
  - **Por qué:**
    - proyectos ve Dinero del cliente con nivel «todo», pero `tipos.cuota` no incluye `proyectos`: las cuotas se recortan y la pantalla sale casi sin cifras.
    - `datos_de_modulo["dinero_cliente/rentabilidad"]` y `cohortes` sí dan el fichero a proyectos (`reglas_permisos.json:969`), pero `tipos.rentabilidad_cliente` lo excluye. Le llega el fichero sin `tarifa_hora`, `margen*` ni `rentabilidad*`.
    - `/api/indicadores` (`servir.py:2248`) trata a proyectos como si viera la cuota.
  - **Arreglo:** que dirección decida si proyectos ve cuota y rentabilidad, y alinear `tipos`, `datos_de_modulo` e indicadores.
- **5.3 · P2 · El técnico de altas tiene la Bandeja siempre vacía.**
  - **Dónde:** `reglas_permisos.json → sillas_de_puesto` no tiene `tecnico_altas`.
  - **Por qué:** su Bandeja es ◐ «suyo». Sin silla, su cartera solo sale de asignaciones sueltas, y «suyo» filtra por cartera (`servir.py:948`).
  - **Arreglo:** darle «todo» en Bandeja (su ámbito ya es «todos»), o una silla `altas` con las altas en curso.
- **5.4 · P1 · Hueco: un setter nuevo no funciona** (hallazgo 6).

**Accesos que conviene que dirección confirme (P2, decisión):**
- **Jefa de SEO:** Bandeja ● «todo». Ve todos los correos de clientes de todos los clientes (ámbito disciplina = todos), aunque su trabajo es SEO y web.
- **Producción:** Captación ○ «resumen». `captacion/captacion` no tiene `resumen` ni `solo_todo_sin_cliente`, así que le llegan las filas sin cliente (por ejemplo `carteras_publicidad`) y el detalle de sus clientes, sin dinero. Justificado por D-82 (rendimiento de piezas); lo razonable es proyectar con `resumen`.
- **Administración:** Alertas ● «todo». Solo lee `alertas/p_<id>`, que es suyo, así que «todo» no le da nada.
- **Setters:**
  - ven Incidencias, Reuniones, Horas, Personas y Decisiones en ◐. No hay fuga, porque se filtra por `persona_id` y `setter`.
  - **No** ven datos de otros setters: `fila_ok` filtra por `setter` (`servir.py:955`) y `ver_dato` exige `dueno_setter`.
- **Producción y cuotas:** no las ve. `cuota` es solo de dir, fin, ops, adm y el account de su cartera, y las horas pautadas se quitan con `sin_cuota`.
- **Administración y publicidad:** no la ve. `inversion` no incluye administración y la ficha va con `ficha_solo_contrato`.
- **Coherencia indice.js ↔ ficheros — P3:** `envios` dice `'*': 'suyo'` en `indice.js`, pero el fichero manda «solo dir, ops y tec». Manda el fichero, así que no hay fallo. El índice confunde a quien lo lee.

### Hallazgo 6 · P1 · Un setter dado de alta desde Ajustes no ve nada suyo

**Dónde:**
- `servir.py:932` y `:1121`: `mi_setter = persona["id"].replace("setter_", "") if startswith("setter_")`.
- `servir.py:1133`: `fila.get("setter") in ("<setter_1>", "<setter_2>")`.
- `fuentes_ventas/generar_ventas_ro.py:43`: setters escritos a mano.
- `altas_personas.py:857`: el id nuevo es `slug(nombre)`, sin el prefijo `setter_`.

**Por qué:**
- Una setter nueva («Nueva», id `nueva`) recibe `mi_setter=None`, y `fila_ok` quita todas las filas con `setter`. Su pantalla «Setters» sale vacía.
- `ver_dato` sobre `ventas_ro/_privado/setter_nueva` falla, porque `nombre_alm != persona["id"]`.
- Dirección y ventas de RO tampoco verían en claro los leads de la setter nueva (lista fija de dos setters).

**Estado:** sin confirmar con datos reales. La regla es determinista en el código.

**Arreglo:**
- Guardar en la persona un campo `clave_setter` (lo pone el alta) y usarlo en `fila_ok`, `nombres_para_su_dueno` y `dueno_setter`.
- En `generar_ventas_ro.py`, sacar `SETTERS` de `personas.json` (puesto `setters`).
- O bien, que altas cree el id `setter_<slug>` cuando el puesto es `setters`.

---

## 6. Acciones, decisiones, ajustes, altas y bajas

**Lo que está bien validado en el servidor (`servir.py:2548-2666`):**
- La acción va a nombre de un módulo que la persona ve.
- Lista blanca de tipos y herramientas.
- `acciones_solo_puestos` con la persona real: un account no encola bajas, cobros ni accesos. Probado: `aviso_impago_account` da 403 a la persona account.
- `decidir` solo lo hace el destinatario.
- Piezas: no puede revisarlas su autor.
- El cliente de Desk, WhatsApp y GHL lo pone el servidor.
- `responder` solo con un cliente que lleva.
- Lo que tiene efecto fuera exige un cliente que lleva.
- Las tareas de ClickUp solo cambian si son propias o del equipo.
- Con `cliente_id`, comprueba `cliente_detalle`. Probado: la persona account sobre `c2` da 403.

### Hallazgo 11 · P2 · Huecos en `/api/acciones`

1. **`objeto` libre sin `cliente_id`.** `POST /api/acciones?yo=account1 {"modulo":"ficha","herramienta":"app","tipo":"traspaso","objeto":"c2"}` → 200. La acción habla de un cliente ajeno y nadie lo comprueba.
   - **Arreglo:** para `herramienta: app` con tipos de cliente (`traspaso`, `nota`, `escalar`, `asignar`…), exigir `cliente_id` o deducirlo de `objeto` cuando `objeto` es un id de cliente.
2. **Tickets que el servidor no conoce.** `herr=desk` con un ticket desconocido y un tipo distinto de `responder` → 200 sin cliente. Probado: una persona de producción encoló `escalar` sobre el ticket 123.
   - **Por qué:** hoy es simulado. Con W1, cualquiera actuaría sobre tickets que el servidor no sabe ubicar.
   - **Arreglo:** que «cerrado si no se sabe» valga para todos los tipos de Desk, WhatsApp y GHL, no solo para `responder`.
3. **`decision_nueva` por la cola de acciones** (está en `acciones_permitidas["*"]`). Se salta las exigencias de `post_decision`: título, problema, recomendación y cliente que lleva. Aparece en `/api/decisiones` como «Subida desde la app (simulado)». Probado con la persona account.
   - **Arreglo:** quitar `decision_nueva` de `*`, o validarla igual que `post_decision`.

**Decisiones (`post_decision`, `servir.py:2820`):** bien.
- Contestar: solo el destinatario, una vez, y lo frena también un disparador.
- `cliente_id` comprobado.

### Ajustes y altas

**Bien:**
- `puestos_solo_tomas` se aplica en `/api/ajustes/persona` (`servir.py:2886-2898`) y en altas (`puede_tocar` y `mando()`, `altas_personas.py:485-503`).
- Nadie cambia sus propios puestos.
- A una persona con un puesto de mando solo la cambia dirección.
- Las altas validan las sillas contra el puesto (`validar_cartera`).
- `/api/altas/departamento` y las tareas de Access son solo de dirección.
- `es_tomas` = puesto `direccion`. Cualquier persona con dirección lo es, así que conviene que «dirección» siga siendo solo dirección.

#### Hallazgo 12 · P2 · `/api/ajustes/asignacion` valida menos que altas
- **Dónde:** `servir.py:2920-2939`.
- **Por qué:**
  - No comprueba que la silla sea del puesto de la persona. `/api/altas/repartir` sí lo hace.
  - No comprueba que la persona esté activa.
  - No valida el formato de `desde` ni de `hasta`. Las fechas se comparan como texto, así que `"31/12/2026"` deja una suplencia vigente para siempre.
  - `suplencia` se convierte con `bool()`, así que `"false"` cuenta como verdadero.
  - Una suplencia en cualquier silla da cartera aunque el puesto no tenga esa silla (`permisos.py:72`).
  - Una persona sin sillas (setters, RRHH, ventas) cuenta todas sus asignaciones.
- **Arreglo:** las mismas validaciones que `altas/repartir` y `validar_cartera`; fechas con `fecha_valida`; tope de duración para las suplencias.

#### Hallazgo 13 · P2 · Dos bajas distintas
- **Dónde:** `/api/ajustes/persona` con `estado: baja` (`servir.py:2877`).
- **Por qué:** no cierra asignaciones, no crea la tarea de quitar Access y no propone reparto. `/api/altas/baja` hace las tres cosas. Con la primera, el cliente sigue con «responsable» de baja y su cartera abierta. Operaciones también puede reactivar (`estado: activo`) a alguien de baja sin que dirección sepa que hay que volver a darle Access.
- **Arreglo:** que `/api/ajustes/persona` no acepte `estado`, y que toda baja o reactivación vaya por altas.

#### Hallazgo 15 · P2 · Decisión de dirección · operaciones da accesos amplios sin dirección
- **Por qué:** Operaciones puede dar a cualquiera que no sea de mando `jefa_publicidad`, `jefa_seo` o `jefa_crm` (detalle de todos los clientes; la de publicidad, con la inversión de todos), `proyectos` o `tecnico_altas` (ámbito «todos»). Esos puestos no están en `puestos_solo_tomas`.
- **Arreglo:** si dirección quiere controlarlo, añadirlos a `puestos_solo_tomas`.

---

## 7. Rastro

**Bien:**
- Disparadores BEFORE UPDATE y BEFORE DELETE en `registro`, `historial`, `registro_huellas`, `rastro_cortes`, `rastro_incidencias`, `acciones` (solo cambia el estado), `decisiones` (una sola respuesta), `opiniones`, `envios`, `sinc_*`, `canal_mensajes`, `avisos_prog_*`, `ia_gasto` e `ia_topes` (comprobado con `sqlite_master`).
- Cadena de huellas SHA-256 y anclas diarias fuera de la base.
- `ver_dato` deja rastro siempre, también cuando no hay dato o se deniega, y no guarda el valor.
- «Ver datos» de sueldos va a la colección `sueldos`.
- `/api/sesion` en «ver como» apunta `ver_como`.

### Hallazgo 9 · P2 · `INSERT OR REPLACE` se salta los disparadores
- **Por qué:** en SQLite, REPLACE borra la fila sin disparar DELETE si `recursive_triggers` está apagado (el valor por defecto).
- **Prueba:** sobre la base de pruebas, `INSERT OR REPLACE INTO registro (id, …) VALUES (1, 'nadie', 'borrado', …)` reescribió la fila 1. La comprobación (`/api/rastro/verificar`) lo detecta: `ok: false, primera_fila_rota: 1`.
- **Lo que queda abierto:** con el mismo truco sobre `registro_huellas`, más una fila «corte» en `rastro_incidencias` (los INSERT se permiten), la cadena se puede blanquear. Solo quedan las anclas diarias, que viven en el mismo disco (`despliegue/estado/`).
- **Arreglo:**
  - `PRAGMA recursive_triggers = ON` en `conectar()`;
  - disparador `BEFORE INSERT ON registro WHEN NEW.id <= (SELECT max(id) FROM registro)` que aborte, y lo mismo para `registro_huellas`;
  - que los cortes de `rastro_incidencias` solo los acepte la línea de órdenes y con ancla;
  - copiar las anclas a un sitio que no sea el Mac (R2 o correo).

### Hallazgo 7 · P1 · Sin confirmar: no hay Postgres aquí · En Postgres (Render) no funcionan el rastro ni varios disparadores
- **Dónde y por qué:**
  - `despliegue/base.py:43` solo traduce los disparadores de una línea sin `WHEN`. `decisiones_una_respuesta`, `acciones_solo_estado` y `opiniones_solo_estado` (más `altas_tareas_solo_estado`) llegan a Postgres con sintaxis de SQLite: `CREATE TRIGGER IF NOT EXISTS … WHEN … BEGIN SELECT RAISE…`. Lo comprobado con `base.esquema_postgres()` es que esas líneas salen sin traducir. Que Postgres las rechace y `iniciar_base()` (`servir.py:298`) falle al arrancar es lo esperable, pero no se ha probado.
  - `_registrar` (`servir.py:381`) hace `BEGIN IMMEDIATE` y `COMMIT` a mano. `traducir()` no los convierte, y en Postgres «BEGIN IMMEDIATE» es un error de sintaxis, así que **todo `registrar()` fallaría**.
  - `INSERT OR REPLACE INTO preferencias` tampoco se traduce: solo se traduce `OR IGNORE`.
  - En Postgres, `TRUNCATE` se salta los disparadores FOR EACH ROW.
- **Arreglo:**
  - traducir los disparadores con `WHEN` a funciones plpgsql;
  - en Postgres, `registrar` con `SELECT … FOR UPDATE` o `pg_advisory_xact_lock`;
  - `ON CONFLICT DO UPDATE` para preferencias;
  - `REVOKE TRUNCATE, DELETE, UPDATE ON registro, historial, registro_huellas FROM <rol de la app>`;
  - una prueba de humo contra Postgres antes de C5.

### Hallazgo 10 · P2 · No todo lo sensible deja rastro
- **Por qué:** en «ver como» solo dejan rastro `/api/modulo/*`, `/api/cliente/*`, `/api/buscar`, `/api/sesion` y `/api/canales/canal|buscar`. **No** lo dejan `/api/rastro`, `/api/acciones`, `/api/decisiones`, `/api/ajustes`, `/api/altas`, `/api/ia/*`, `/api/perfil`, `/api/opiniones`, `/api/envios`, `/api/sincronia` ni `/api/avisos_programados`. Probado con `/api/rastro` (hallazgo 1).
- **Arreglo:** en `api_get` (`servir.py:2184`), apuntar **toda** ruta en «ver como», agrupada por minuto como ya se hace.

---

## 8. Errores típicos

- **Inyección SQL:** no hay. Todo va con parámetros `?`. Las f-strings solo componen nombres de tabla fijos o listas de `?` (`servir.py:2482`, `avisos.py:510`, `altas_personas.py:573`, `envios.py:307`, `ia_gasto.py:150`).
- **Path traversal:**
  - `/api/modulo/<rel>` solo admite `[\w\-/]+`, sin puntos. Pasa por `resolve()` más `startswith(DATA)`, y se niegan `_privado`, núcleo y `clientes/`.
  - `//etc/passwd` se resuelve fuera de `DATA` y da 403.
  - `ver_dato` hace lo mismo y exige `_privado`.
  - Estáticos: lista blanca y `..` prohibido.
  - **P3:** los patrones de `almacenes_privados` usan `fnmatch`, cuyo `*` también cruza `/`. `agenda/_privado/x/account1` encaja con `agenda/_privado/*`, y el dueño se saca del último trozo. Solo sería un problema si hubiera subcarpetas. Usar `fnmatch` por partes o `[^/]*`.
- **XSS:** no hay `innerHTML` con datos.
  - `componentes.js:163` y `:185` solo usan cadenas fijas de iconos.
  - `h()` usa `textContent`, filtra `on*` y comprueba las direcciones con `urlSegura`.
  - El chat pinta con nodos.
  - **P3:** `panel_direccion.js:108` pasa el HTML del panel por `DOMParser` y un saneado casero que no cubre `href="java&#9;script:"` ni `data:`. Lo frena la CSP (`script-src 'self'`, sin `unsafe-inline`), y el fichero es solo de dirección. Si se quiere más, usar un saneado con lista blanca de etiquetas y atributos.

### Hallazgo 8 · P2 · `HEAD` se salta toda la seguridad
- **Dónde:** `Manejador` no redefine `do_HEAD` (`servir.py:1870`), así que entra `SimpleHTTPRequestHandler.do_HEAD` sobre `AQUI`.
- **Prueba:**
  - `curl -I http://127.0.0.1:8791/data/_privado/secreto.json` → 200, `Content-Length: 33`, `Last-Modified`.
  - Con `-H "Host: evil.com"`, `/servir.py` → 200: se salta `host_ok`.
- **Por qué:** en modo servidor también se salta Access. No hay cuerpo, pero se sabe si un fichero existe, cuánto pesa y cuándo cambió: `local.db`, `data/sueldos/_privado/sueldos.json`, `correos_entrada.json`…
- **Arreglo:** `def do_HEAD(self): return self.responder(405, {"error": "Método no permitido."})`. Otra opción es hacer el GET sin cuerpo.

### Hallazgo 5 · P1 · Las capturas de «Algo va mal» cruzan permisos
- **Dónde:** `servir.py:2387-2399` y `:2772`.
- **Por qué:** `RUTA_SENSIBLE` (`servir.py:1447`) solo frena sueldos y nóminas. Una captura de dirección en `#/panel-direccion` o `#/finanzas` (caja, beneficio, dinero de empresa) la ve operaciones, porque `opiniones_ver` es de dirección y operaciones.
- **Prueba:** `POST /api/opinion?yo=dir` con ruta `#/panel-direccion` y captura. Después, `GET /api/opiniones/captura?id=1&yo=ops` devuelve la imagen.
- **Arreglo:** guardar con cada opinión los módulos que veía quien la manda. Servir la captura solo a quien vea también esos módulos (`ve_alguno`). Ampliar `RUTA_SENSIBLE` a `panel-direccion`, `finanzas`, `gasto-ia` y `dinero-cliente`.

### Hallazgo 16 · P2 · Importes mal clasificados en los textos
- **Dónde:** `permisos.py:374` (`tipo_importe`).
- **Por qué:** mira 40 caracteres antes. En «Cuota 1.470 €/mes y gasto 300 €», los 300 € se clasifican como cuota porque «Cuota» y «/mes» están cerca.
- **Prueba:** Administración (administración, que ve la cuota y no la inversión) recibió el texto intacto con «gasto 300 €».
- **Arreglo:** dar prioridad a la palabra más cercana. Si entre la palabra clave y el importe hay otro importe o «y gasto», manda la última.

### Hallazgo 14 · P2 · `/api/cliente/<id>` no mira el módulo
- **Dónde:** `servir.py:2212`.
- **Por qué:** solo comprueba `cliente_detalle`.
  - Outreach no ve «Ficha», pero recibe la ficha entera (sin dinero) de los clientes de su cartera de outreach.
  - Redes y producción ven «Ficha» en ○ «resumen», pero reciben la ficha completa.
- **Arreglo:** exigir `ve_alguno(persona, ["ficha", "bandeja", "captacion", "asistente-ia"])`, y con nivel «resumen» proyectar solo la cabecera.

### 19 · P3 · Pulido
1. `LEEME.md` (tabla de Permisos) dice que `sueldo` es «Nunca, para nadie». La regla vigente (2-oct) lo permite a dirección y RRHH, desenmascarable y con rastro. Corregir el LEEME.
2. El escáner (`escaner_secretos.py`) no busca DNI, NIE ni IBAN. Hoy ningún generador los saca, así que es endurecimiento: añadir patrones `\b\d{8}[A-Z]\b`, `\b[XYZ]\d{7}[A-Z]\b` y `\bES\d{22}\b`.
3. `GET /api/sincronia` escribe en la base (`sincronia.py:1264`). Pasarlo al hilo de fondo.
4. `pruebas_seguridad.py` no cubre: el hallazgo 1 (`/api/rastro` y `/api/acciones` en «ver como»), HEAD, ficheros nuevos sin escanear, `cliente_id` en la raíz ni capturas de opiniones. Añadirlos.
5. `peticion_propia` da por buena una petición sin `Sec-Fetch-Site`. Vale para el navegador, pero un `curl` con la galleta de Access pasa. Es aceptable detrás de Access.
6. El modo estático (`python3 -m http.server`, usado en la comprobación de la ola 0) sirve `data/` entero sin recorte: con datos reales, nunca fuera del Mac de dirección. Ponerlo en el LEEME como regla.

---

## Pruebas y artefactos (scratchpad)

- `b_pruebas/gen.py`, `py.py`, `js.mjs`: paridad Python ↔ JS (38.812 casos, 0 diferencias).
- `b_pruebas/app/`: copia con datos inventados.
  - Personas: `dir`, `ops`, `account1`, `trafficker1`, `produccion1`, `setter_a`, `admin1`, `rrhh1` y `baja1`.
  - Clientes: c0 a c3.
  - Ficheros añadidos con el servidor en marcha: `data/en_rojo/atajos.json`, `data/paneles/meta/c2.json` y `data/informe/c_2026-09/c2.json`.
- `b_pruebas/prueba.db`: base de la prueba. Ahí está la fila 1 del rastro reescrita a propósito (hallazgo 9).
- El servidor de pruebas (puerto 8791) ya está parado. La copia `app_b` no se ha modificado.
