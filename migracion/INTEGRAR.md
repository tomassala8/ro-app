# Funciones nuevas del 4-oct: cómo entran en la app nueva

Una ficha por función. Para Cursor (esta noche y los días siguientes) y para quien siga después.
Regla de la noche: **ninguna función nueva se reescribe esta noche.** Viajan como están (Python + JS de hoy) por el
proxy de Nest y el puente de Next, y las puertas las cubren. Lo de «Al mudarla» es para cuando su grupo pase a Nest/React.

Cómo llega cada pieza al Mac:
- Lo de los PR #2, #3 y #4 → F1.3, paso 3b (`RAMAS_A_JUNTAR.txt`).
- Lo de la rama del plan fuera de `migracion/` y `v2/` (fuentes/, fuentes_contexto/, schema_v2.sql, reglas_permisos.json,
  config.py, despliegue/) → `migracion/juntar_plan.sh`, que lanza `noche.sh` al empezar (F1.3, paso 3c).

Para cada función, al mudarla a Nest/React: mismo contrato (respuesta idéntica), `@Permiso` declarado, recorte por cartera
dentro de la consulta, pruebas Python de hoy en `baterias.sh` y su pantalla con fotos ≤ 0,5 %.

---

## 1. Cerebros de área y «Qué hago si…» (PR #2)

- **Qué es:** 13 cerebros (`fuentes_consejos/cerebros/<area>.json`, ~480 fichas de situación) que dicen qué hacer ante una
  alerta, un consejo o un problema escrito con palabras. Se buscan **sin IA** (`buscar.py`); con clave, la IA solo adapta la ficha.
- **Hoy:** `ia.py` lo carga como `CB` (si falla, todo sigue igual sin fichas). Pantallas: «Qué hago si…» en Mi día y en el
  Asistente (`ia_componentes.js › panelCerebro`, `fichaCompleta`), ficha corta en cada consejo de «Qué haría yo hoy aquí».
- **Contrato:**
  - `GET /api/ia/cerebro?q=<texto>` → lista de fichas; `?id=<ficha>` → una ficha. Sin IA, sin coste.
  - `POST /api/ia/cerebro {id, cliente, pregunta}` → la ficha adaptada por la IA (con clave; **nunca en «ver como»**).
  - `GET /api/ia/consejo` → cada consejo lleva `ficha` (corta).
- **Permisos:** `direccion` y `personas_admin` solo salen a sus puestos y a dirección: la ruta pasa SIEMPRE el puesto de
  quien pregunta (`buscar(..., puesto=)`). En «ver como», el puesto de la persona vista.
- **Datos:** ficheros JSON versionados en el repo (no van a la base). El índice se rehace con `construir_indice.py`.
- **Esta noche:** por el proxy. `contrato.py` ya graba `GET /api/ia/cerebro?q=…` e `?id=rb_sano_mantener` para cada
  persona (cada puesto ve sus cerebros). El POST queda fuera del contrato (gasta IA); su caso «denegado en ver como» sí entra en F1.5.
- **Pruebas:** `python3 fuentes_consejos/cerebros/probar_cerebros.py` y `probar_en_app.py` (sin servidor) → `baterias.sh`.
- **Al mudarla:** un `CerebrosModule` en Nest que lea los JSON una vez al arrancar (con caché por versión) y porte
  `buscar.py` (normalización sin tildes, puntuación y orden **idénticos**: ver «Búsqueda» en la guía de traducción). El
  POST se queda en el legado (IA y su control de gasto `ia_gasto.py` siguen en Python, PLAN §8).
- **Falta:** nada para la noche.

## 2. Diagnósticos de calidad (PR #3)

- **Qué es:** `fuentes_diagnosticos/diagnosticos.py` mira **qué** llega (no cuánto): leads no calificados, el despacho no
  atiende, los leads no avanzan, leads baratos pero malos, SEO… y un **veredicto del embudo** (leads malos · no atiende ·
  contacta pero no agenda · no vienen · sano). Cada uno apunta a su ficha del cerebro `calidad`.
- **Hoy:** `generar_diagnosticos.py` escribe `data/diagnosticos/diagnosticos.json` (solo lectura, 0 llamadas) desde
  `ghl_vivo.json`, `crm.json`, `captacion.json` y `gsc.json`. Lo usan el riesgo de baja (causa probable) y el cerebro.
- **Contrato:** no tiene ruta propia ni pantalla. El fichero **no está dado de alta** en `reglas_permisos.json`
  (`datos_de_modulo`), así que hoy ninguna pantalla lo pide. No lo des de alta esta noche (sería una función nueva).
- **Datos:** un JSON por versión, como el resto de `data/` (`publicacion.py`). No necesita tabla propia.
  «diagnostico» y «veredicto_embudo» son campos de ese JSON, no tablas.
- **Tubería:** comprueba que `despliegue/pasos.json` tiene un paso que lo lance **antes** de `riesgo_baja` (el riesgo lee el
  veredicto). Si no está, apúntalo en NOTAS_NOCHE.md (no lo añadas esta noche: cambia la tubería).
- **Pruebas:** `python3 fuentes_diagnosticos/probar_diagnosticos.py` (ficheros inventados) → `baterias.sh`.
- **Al mudarla:** se queda en Python (es un lector de la tubería). La pantalla, cuando se decida, va en la ficha del cliente
  y en CRM, con «sin dato» cuando hay poca muestra (nunca 0).
- **Falta:** decidir dónde se enseña (pregunta a Tomás) y los diagnósticos 🟡/⚪ del `CATALOGO.md`.

## 3. Semáforo en tres ejes y riesgo de baja (PR #4)

- **Qué es:** `fuentes_riesgo/riesgo_baja.py` calcula Resultados, Relación (silencio, asistencia, calidez) y Quejas en
  verde/ámbar/rojo/gris, los combina en un patrón y un nivel (bajo · vigilar · alto · crítico) y apunta a su ficha del
  cerebro `riesgo_baja`. Umbrales firmados por Tomás el 4-oct (`FIRMADO = True`).
- **Hoy:** escribe `data/riesgo/riesgo_baja.json`; dado de alta en `reglas_permisos.json` (`riesgo/riesgo_baja`: ficha,
  Mi día, En rojo; no administración); paso `riesgo_baja` en `despliegue/pasos.json`. Pantalla: fila «Riesgo de baja» en la
  ficha (`ficha.js › filaRiesgo`) y dos campos nuevos en el semáforo del lunes (`vista_previa.queja`, `vista_previa.tono`,
  misma acción `semaforo_semanal`). El copiloto lo recibe (`ia.cliente_para_borrador › riesgo_baja`).
- **Contrato:** `GET /api/modulo/riesgo/riesgo_baja` (recortado por cartera: cada fila lleva `cliente_id`; la cartera del
  account, `persona_id`). La acción `semaforo_semanal` con `queja` y `tono` entra en los casos de escritura de F1.5.
- **Datos:** un JSON por versión. La calidez y la queja viajan dentro de la acción (rastro), no en tabla propia.
- **Pruebas:** `python3 fuentes_riesgo/probar_riesgo.py` → `baterias.sh`. Fotos: la ficha del cliente con y sin riesgo.
- **Al mudarla:** la ruta de datos entra con F5.3 (`/api/modulo/**`) sin nada especial. En React (F6.4, «Ficha del
  cliente»): `filaRiesgo` tal cual (chips por eje con `title` = motivos, «Qué significa y qué hago» abre la ficha del
  cerebro). Administración no la pide (`perfil(ctx) !== 'admin'`): igual en React.
- **Falta (fuera de la noche):** `desk.ult_correo_entrante` (Zoho Desk, tickets cerrados) para que la Relación salga con
  confianza alta; la calidez propuesta desde las actas de Fathom; canceladas de Bookings.

## 4. Contexto del cliente (fichas breves)

- **Qué es:** un resumen de cada cliente (a qué se dedica, qué quiere, qué nos ha dicho, qué le gusta y qué no, cómo
  trabajar con él, situación actual y lo que aún no sabemos) para que el account lo tenga a mano en la ficha.
- **Ya hecho (4-oct, rama del plan):**
  - `fuentes_contexto/generar_contexto.py`: lee las fichas de un sitio PRIVADO (`RO_CONTEXTO_CLIENTES`, o
    `fuentes_contexto/_privado/contexto_clientes/fichas_clientes.json`) y escribe `data/contexto/contexto_clientes.json`,
    una fila por `cliente_id` de la app.
  - Privacidad: quita las personas del cliente (`quien_esta_detras`), el account, nombre y fuentes; en las citas, el nombre
    pasa a su papel; correos y teléfonos se borran. Nunca escribe vacío ni pisa un fichero bueno con uno mucho más pequeño.
  - Dado de alta en `reglas_permisos.json` (`contexto/contexto_clientes`: solo la ficha; administración no). Cada uno ve
    solo sus clientes (recorte por `cliente_id`).
  - `fuentes_contexto/probar_contexto.py`: 21 casos con clientes inventados, en verde. Va a `baterias.sh`.
- **Los datos reales:** las fichas NO van al repo. Tomás (o Astra) copia `fichas_clientes.json` a
  `fuentes_contexto/_privado/contexto_clientes/` en el Mac (ignorado por git). Comprobado en seco con el fichero real:
  67 clientes válidos.
- **Esta noche:** nada. Sin el fichero privado no escribe; si está, el contrato graba `/api/modulo/contexto/contexto_clientes`
  como cualquier otro dato.
- **Falta:**
  1. Pantalla (mañana, primero en `ficha.js`; en React con F6.4 «Ficha del cliente»): bloque de solo lectura «Contexto del
     cliente» que lee `contexto/contexto_clientes`, coge la fila del cliente y enseña «Actualizado el …», la frase, las
     listas y las citas; `huecos` en gris como «Nos falta saber…». Sin fila, no sale.
  2. El paso en `despliegue/pasos.json` (poco frecuente: las fichas cambian a mano).
  3. La hoja `contexto_clientes_2026-10-04.xlsx` trae más campos (zona objetivo, servicios prioritarios, propuesta de valor,
     competidores, palabras clave, tono y vetos, objetivos de leads y citas, ticket medio…). No se usan: importes, decisor
     e interlocutor piden antes una decisión de Tomás sobre quién los ve.
- **Al mudarla:** la ruta de datos entra con F5.3 sin nada especial. Si un día se edita desde la app, pasa a tabla propia.

## 5. Copia propia de las APIs: nunca ceros (N-01 a N-12)

- **Qué es:** la regla de Tomás del 4-oct (PLAN §2.5): lo que manda una API se guarda en NUESTRA base antes de usarlo;
  si la API falla, se enseña lo último bueno con su hora y «Sin datos en tiempo real», nunca un 0 ni un vacío.
- **Ya hecho (4-oct, rama del plan):**
  - Tabla `fuente_lectura` + índice + vista `fuente_ultimo_bueno` en `schema_v2.sql` (la crean servir.py, `crear_base_pg.py`
    y el propio módulo). En F2.2 es una tabla nueva: `rehacer_base.sh` la lleva a Prisma.
  - `fuentes/lectura.py`:
    - `leer(fuente, recurso, funcion, sospechoso=None) -> Lectura(datos, estado, desde, error)`, con `estado` = ok · viejo · sin_dato.
    - Cuenta como fallo: excepción, vacío, `{"_error": …}` (el de Search Console, N-02), «todo a 0» cuando lo último bueno
      no lo era, y lo que diga `sospechoso`.
    - Guarda cada lectura (también los errores) y se queda con las 30 últimas buenas por recurso. `podar()` borra los
      errores de más de 30 días.
    - `marcar(lectura)` añade `_viejo`/`_desde` a un diccionario.
  - `fuentes/probar_lectura.py`: 28 casos en SQLite y 26 en Postgres (`--pg`), en verde. Va a `baterias.sh`.
- **Falta (F5.10, en este orden):**
  1. N-01: que cada lector pase su llamada por `leer()`. Empieza por el `con_cache` de Holded (`fuentes_dinero/`), que es lo
     mismo en pequeño.
  2. N-02 a N-06: SEO, Redes, CRM por subcuenta (total «parcial», nunca la suma con un 0), Hostinger y Paneles. Cada uno
     con su prueba «API falsa caída → último bueno + aviso, ningún 0» en `despliegue/pruebas_noche.py --solo-solidez`.
  3. N-07 a N-09 en la tubería: copiar y restaurar cachés; no publicar si no se bajó la versión anterior o la nueva es
     mucho más pequeña; claves mínimas y recuento por paso.
  4. N-10 a N-12 en pantalla: «—» en vez de 0, el aviso común «Sin datos en tiempo real: lo último es de las HH:MM»
     (`desde` está en UTC: a Madrid con `ahora_madrid`/`RO_RELOJ` al pintar) y el sello del menú desde la tubería.
- **Al mudarla:** se queda en Python (los lectores viven en `ro-legado`). Nest solo lee la vista `fuente_ultimo_bueno`
  si una pantalla necesita «de cuándo es este dato».

## 6. Servidor MCP de la app (Tomás, 4-oct)

- **Qué es:** en lugar de una API pública, cada miembro conecta la app a **su** Claude. Diseño completo en `PLAN_MAESTRO.md` §2.14.
- **Esta noche:** nada. No se empieza hasta que las rutas de lectura estén en Nest: las herramientas llaman a esos servicios.
- **Contrato:** `POST /mcp` (MCP por HTTP), `GET /.well-known/oauth-authorization-server` y `oauth-protected-resource`,
  `/mcp/autorizar` (detrás de Access), `/mcp/token`, `/mcp/registro`. Tabla nueva `mcp_token` (solo la huella del token).
- **Permisos:** la misma guarda de Nest. La persona sale del token, nunca de una cabecera. En cada llamada, motor de
  permisos de la persona ∩ alcances del token. Sin «ver como». Solo lectura por defecto.
- **Pruebas:** las del final de §2.14, como e2e de Nest, más los vectores de permisos pasados por las herramientas.
- **Falta decidir (Tomás):** qué herramientas de escritura hay al principio y cuánto dura un token (propuesta: 30 días).

