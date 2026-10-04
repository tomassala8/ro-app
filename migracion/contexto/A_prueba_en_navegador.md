> Recogido en: `migracion/PENDIENTES_LOGICA.md` (L-xx) y `SUPERPROMPT_ASTRA_2026-10-04.md` de esta carpeta. Es el informe de la prueba en navegador que los originó (anexo A).
> **Copia saneada para Cursor (4-oct-2026).** Fuente: `/mnt/project-files/feedback_herramienta/anexos/`. Las personas de prueba se nombran por su puesto (`dir`, `ops`, `account1`…) y los clientes por ids neutros (`cli-a`, `cli-b`).

# A · Prueba en navegador de la app de RO (prototipo local)

Fecha: 4-oct-2026. Copia probada: `scratchpad/app_a` (repo `ro-app`, rama `main`).
Servidor: `python3 servir.py --bind 127.0.0.1 --puerto 8790`, con **datos inventados**.

## Cómo se probó

- **Datos inventados.** Script: `scratchpad/generar_datos_inventados.py`.
  - 19 personas inventadas, una o más por puesto, todas activas, y una de baja. (Aquí se nombran por su puesto: `dir`, `ops`, `account1`, `trafficker1`, `produccion1`, `admin1`, `rrhh1`, `setter_a`, `ghl1`, `jefe_seo1`, `seo1`…)
  - 10 clientes inventados (cli-a, cli-b, bufete-norte, clinica-sol…), 25 asignaciones y 8 alarmas.
  - Una bandeja mínima con 5 correos. Los correos de entrada van en `data/_privado/` con `@ejemplo.test`.
  - Además se lanzaron los generadores que funcionan sin fuentes reales: `generar_verdad`, `generar_atajos`, `generar_alertas`, `generar_mi_dia`, `generar_consejos`, `generar_conexiones`, `generar_whatsapp`, `generar_hostinger` y `generar_gbp`.
  - El resto de módulos se probó **sin datos**, para ver cómo se comporta el vacío.
- **Recorrido automático.** Script: `scratchpad/recorrido.js`. Resultados en `scratchpad/recorrido/resultados_*.json`.
  - 10 personas: `dir`, `ops`, `account1`, `trafficker1`, `produccion1`, `admin1` (administración), `rrhh1`, `setter_a`, `ghl1` y `jefe_seo1`.
  - Cada entrada del menú, a 1366 y a 390 px. Son 420 pantallas.
  - Además se probaron hasta 8 botones por pantalla a 1366.
- **Escenarios a mano.** Script: `scratchpad/escenarios.js`, salida en `recorrido/escenarios.txt`. Cubren ⌘K, «Ver como», ficha ajena, pantalla sin permiso, identidad de baja o inexistente y menú móvil.
- **Capturas** en `scratchpad/recorrido/capturas/`.

Leyenda de gravedad: **P0** rompe o expone datos · **P1** fallo funcional · **P2** usabilidad o coherencia · **P3** pulido.
Si un hallazgo pone «dudoso», puede deberse a los datos inventados.

---

## 1. Arranque y baterías

### 1.1 Arranque de `servir.py`
- **Con correos `@ejemplo.test` en `personas.json`:** arranca, pero la puerta de secretos bloquea `data/personas.json` y **toda la API responde 503**.
  - Mensaje: «⛔ Hay secretos en los datos comunes».
  - Es por diseño: `escaner_secretos.py:29-32,128` solo admite `@<dominio de la empresa>` en el campo `correo`.
  - Se arregló poniendo `correo: null` (el correo de entrada va en `_privado`).
- **Con eso:** arranca limpio, sin trazas. Log en `scratchpad/servidor.log`.

### 1.2 `pruebas_e0.py --puerto 8790` → 15 fallos, ninguno de código de permisos
- **Pasa todo el bloque de seguridad básica:**
  - 403 a cliente ajeno para account1, trafficker1 y setter_a.
  - `data/`, `local.db`, `*.py`, `indicadores.json` e `historia/` no se sirven.
  - «Ver como» negado a la persona account.
  - La persona de baja no entra.
  - Huella de la matriz: `0081a495…`.
- **Los 15 ✗ son 404 de ficheros de módulo que no existen sin datos reales:** `ventas_ro/setters`, `ventas_ro/outreach`, `captacion`, `whatsapp`, `informe de dirección`, `contratación`, `crm`, `dinero_cliente`, `verdad`. Todos **por falta de datos reales**.
- **Hallazgo de la batería (P3).** Es frágil con nombres fijos:
  - Usa cuatro ids de persona fijos sin comprobar que existen.
  - Sin una de ellas revienta con `KeyError: 'datos'` (`pruebas_e0.py:94`) en vez de marcar ✗.

### 1.3 `pruebas_diseno.py --estricto` → limpio
61 de 61 módulos limpios. Solo informa de 1 radio con número en `estilos.css` y 4 colores sueltos en `index.html`.

### 1.4 `escaner_secretos.py --proyecto` → **falla sobre el propio código (P2, real)**
- Sale con código 1 y este hallazgo: «✗ pruebas_seguridad.py: 1 hallazgo(s) · correo línea 48».
- Es un falso positivo: en `pruebas_seguridad.py:47` está `lsof … -iTCP@127.0.0.1:{puerto}` y el patrón `correo` (`escaner_secretos.py:41`) lo toma por un correo.
- Así, la puerta del proyecto está en rojo con el repo limpio. No depende de los datos.
- Esperado: el texto `-iTCP@127.0.0.1` no cuenta como correo, o la línea se añade a `escaner_permitidos.json`.

### 1.5 `pruebas_coherencia.py`
- **Sin la verdad única:** «✗ No existe data/verdad/clientes.json». Por falta de datos.
- **Tras generarla:** 5 errores y 5 avisos, todos de coherencia de mis datos inventados (clientes nuevos, «fuera de plazo», sin reunión, cartera de captación). **Dudosos**; no indican fallo de código.

### 1.6 `pruebas_seguridad.py` → interrumpida a los 15 min (47 ✓, 17 ✗). Fallo de la propia batería (P2)
- **A partir del bloque M3** (`pruebas_seguridad.py:282-290`), todas las peticiones que escriben en la base devuelven **500** o se quedan colgadas. Ejemplos: chat, `R9`, `R11 X1`.
- **Causa verificada.** M3 abre conexiones sqlite en línea (`sqlite3.connect(...).execute("DELETE FROM decisiones")`) y no las cierra:
  - Si la sentencia **no** dispara el disparador (por ejemplo, `decisiones` vacía), queda una transacción de escritura abierta y la base queda bloqueada.
  - Además, `except sqlite3.DatabaseError` toma un «database is locked» por un «→ bloqueado» correcto.
  - Reproducido en `scratchpad/rep/lock.db`: tras el `DELETE` sobre la tabla vacía, cualquier escritura da `database is locked`.
  - El proceso de la prueba tenía más de 25 descriptores abiertos a `prueba.db`.
- **El servidor principal (8790) responde bien a esas mismas rutas:**
  - `chat_equipo/p_account1` como ops → 403.
  - `/api/cliente/cli-a` como produccion1 → 403.
- **Conclusión:** los ✗ de R9, «Chat» y R11 X1 son de la batería, no de la app. Los demás ✗ del arranque son por nombres o datos reales que faltan: C3 (sueldos), C4 (Concilia), A1 (una persona fija) y A7 (correo de operaciones).
- **Lado servidor (P2, dudoso):** con la base bloqueada, un GET que debería dar 403 en el acto (`/api/modulo/chat_equipo/p_account1`) se queda colgado más de 10 s y acaba en 500. El motivo es que deja rastro en la base antes de contestar. Esperado: la denegación no depende de poder escribir.

---

## 2. Hallazgos en navegador

### P0 · rompe o expone datos
**No he encontrado ningún P0 en navegador.**
- **Recorte de dinero en el servidor:** correcto en `/api/sesion` para las 17 personas:
  - trafficker1, ghl1, jefe_seo1, produccion1, rrhh1 y setter: 0 cuotas.
  - admin1: cuotas sí, inversión no.
  - account1: solo las de sus 4 clientes.
- **En pantalla:** ninguno de los puestos sin dinero ve «€» salvo en el subtítulo genérico de «Dinero por cliente».
- **«Ver como»:** de verdad es solo lectura. `POST /api/acciones` da 403 con «Estás en «ver como»: es solo lectura», tanto con cabeceras como solo con la galleta.
- **Ficha ajena:** da 403 y la pantalla lo explica.
- **Ficheros estáticos:** no se sirven `fuentes_dinero/cuotas.json`, `recarga.json` ni `LEEME.md`.

### P1 · fallo funcional / datos sensibles

#### P1-1 · El repo lleva datos de dinero reales, aunque el LEEME dice que no
- **Dónde:** `git ls-files`:
  - `fuentes_dinero/cuotas.json`: 67 clientes con cuota mensual y fuente; 64 con cuota mayor que 0.
  - `fuentes_dinero/impagos_estado.json`: 3 facturas con estado, nota y siguiente paso.
  - `fuentes/_muestras/google_ads_septiembre_muestra_2026-10-02.json`.
  - `fuentes_captacion/anuncios.json`.
  - `fuentes_bandeja/_cache_cuentas_desk.json`: 32 cuentas de Desk.
  - `fuentes_incidencias/rastro_operaciones.json`.
- **Cómo verlo:** `git ls-files | grep json`.
- **Esperado:** el LEEME («Qué no se sube a GitHub») dice que el repo lleva «solo código, reglas y documentación». La cuota por cliente es justo el dato que la app esconde a casi todos los puestos.
- **Gravedad:** el repo es privado y el servidor no sirve esos ficheros, así que no es una fuga activa. Pero cualquiera con acceso al repo los lee. **No es de los datos inventados.**

#### P1-2 · Una persona de baja o inexistente ve un error técnico y la cabecera atascada en «Cargando…»
- **Dónde:** `app.js:82`.
- **Cómo reproducirlo:** abrir `/?yo=baja1` (baja) o `/?yo=noexiste`. Captura `capturas/esc_yo_baja.png`.
- **Qué sale:**
  - Título «Cargando…» para siempre y avatar «·».
  - «No hay datos · Esta persona no está activa…».
  - Y luego «Qué hacer: Arranca «python3 servir.py» (o ejecuta «python3 build_data.py») en la carpeta 30_APP_PROTOTIPO y recarga».
- **Esperado:** una pantalla de «No tienes acceso / pide a operaciones que te active», sin instrucciones de terminal.

#### P1-3 · «Avisar al equipo» sale desactivado aunque el cliente tiene equipo
- **Dónde:** `modulos/ficha_equipo.js:53-70` (`equipoAvisable`).
- **Cómo reproducirlo:** account1 → `#/ficha/bufete-norte`.
- **Qué pasa:** el botón dice «Este cliente no tiene equipo asignado por silla (lo mantiene operaciones)». Pero `/api/cliente/bufete-norte` trae `cliente.equipo` con trafficker (trafficker1), crm (ghl1) y seo (seo1).
- **Causa:** la función solo mira `F.verdad.equipo`, que el servidor recorta para un account, y la fuente `asignaciones` de la ficha E1. Nunca mira `F.c.equipo`.
- **Esperado:** usar `cliente.equipo` como respaldo.
- **Dudoso:** con las fichas E1 reales (`data/clientes/<id>.json`) puede que no pase.

### P2 · usabilidad y coherencia

#### P2-1 · Jerga interna en los subtítulos de cabecera, que ve todo el equipo
- **Dónde:** `modulos/indice.js` (campo `resumen`), pintado tal cual en `app.js:604` sin pasar por `limpiaTexto`. Se ve en el subtítulo bajo el título.
- **Ejemplos:**
  - Bandeja (`indice.js:28`): «…(simulado hasta W1)…; WhatsApp en W6».
  - Chat del equipo (`indice.js:36`): W1.
  - Informes mensuales (`indice.js:68`): «(D-09)… histórico de la hoja en W5».
  - Horas (`indice.js:98`): «(D-27)».
  - Reuniones (`indice.js:102`): «solo grabadas hasta W4… (D-06)».
  - Indicadores (`indice.js:142`): «E0».
- **También en el cuerpo:**
  - «Fase 2 · N indicadores que todavía no se pueden medir»: al pie de Mi día y de Bandeja, para todos los puestos.
  - «Decisiones y rastro»: el subtítulo dice «consulta las 101 firmadas», un número fijo, mientras las tarjetas dicen «Firmadas —».
- **Esperado:** subtítulos en llano y sin códigos.

#### P2-2 · Los vacíos y errores enseñan frases rotas o el mensaje crudo del servidor
- **Dónde:** `componentes.js:2106` (`limpiaTexto`) borra los nombres de fichero y deja la frase coja.
- **Ejemplos:**
  - SEO, ficha y webs (`modulos/seo.js:745`) y Redes (`modulos/redes.js:403`): «No existe. **Se generan con.**». Captura `capturas/v_dir_seo_vacio.png`.
  - Bandeja, Informe del cliente, Paneles, Informes mensuales, Incidencias, Captación, CRM, Producción, Horas, Reuniones, Dinero por cliente y Finanzas: el cuerpo es solo «**No existe**», que es el 404 del servidor recortado.
- **Cómo reproducirlo:** abrir esas pantallas sin datos de módulo, con cualquier persona.
- **Esperado:** «Todavía no hay datos de X de hoy» y quién lo arregla, sin restos de la frase técnica.
- **Por qué cuenta:** el vacío sale por falta de datos, pero el texto roto es de código.

#### P2-3 · Menús demasiado largos
**Medido a 1366, sin contar «Mis clientes»:**

| Persona | Entradas |
|---|---|
| dir | 35 |
| ops | 31 |
| account1 (account) | 24 |
| trafficker1 (trafficker) | 21 |
| jefe_seo1 | 20 |
| ghl1 | 18 |
| produccion1 | 15 |
| admin1 | 14 |
| rrhh1 | 13 |
| setter | 9 |

- **El 24 de la persona account con 4 clientes más** da 28 enlaces. En el móvil, el menú abierto mide 1325 px de alto (`capturas/esc_account_390_menu.png`).
- **Pantallas que no parecen del puesto:**
  - Un account ve «Producción», «Horas y productividad», «Personas», «SEO, ficha y webs», «Redes» y «Captación».
  - Producción (produccion1) ve «Captación» e «Incidencias».
  - RRHH (rrhh1) ve «En rojo» y «Producción».
- **Esperado:** 8-12 entradas por puesto, con lo demás en ⌘K o en un «Más».

#### P2-4 · «Lo mío» de dirección repite el mismo problema dos veces, con texto duplicado
- **Dónde:** `modulos/mi_dia.js:575-577` (avisos) y las alertas de `generar_alertas`. Texto de `/api/avisos`.
- **Qué sale:**
  - Arriba, «ClickUp (llave propia) · **Falta la llave: Falta la llave** · lo hace dirección…». Con el porqué «Una fuente de datos no ha llegado a tiempo», que no es la razón: es una llave que falta.
  - Más abajo, otra fila «ClickUp (llave propia): falta la llave».
  - Pasa igual con Zoho CRM y Zoho Desk.
  - En «Lo mío» sale el comando de terminal `security add-generic-password -U -a "$USER" -s clickup_api_token -w`.
- **Cómo reproducirlo:** dir → Mi día, en una máquina sin llaves. Captura `capturas/v_dir_midia_1366.png`.
- **Esperado:** una sola fila por conexión caída, sin repetir texto.
- **Dudoso en parte:** depende de no tener llaves, pero la duplicación y el «X: X» son de código.

#### P2-5 · Contadores distintos en la misma cabecera
- **Qué pasa:** la campana de dirección marca **12** y «Alertas del departamento» / «Alertas · 13» marca **13**, en la misma pantalla.
- **Esperado:** el mismo número, o etiquetas que dejen claro que son cosas distintas.
- **Dudoso.**

#### P2-6 · Asistente IA: textos fijos que contradicen el dato
- **Dónde:** `modulos/asistente_ia.js:70,145`.
- **Qué pasa:** dice «Hoy hay borradores para los 40 correos más urgentes de la Bandeja» y «Se ven los borradores precalculados del **2-oct**» mientras enseña «Borradores listos 0».
- **Esperado:** el número y la fecha salen del dato.

#### P2-7 · «La persona trafficker tiene «Dinero por cliente» en el menú»
- **Qué pasa:** su puesto no ve cuotas y el subtítulo dice «Cuota, horas frente a cuota (31,47 €/h) y rentabilidad».
- **Según el LEEME** (M18: «publicidad, horas sin euros») es intencionado. Pero el título y el subtítulo prometen algo que no verá.
- **Esperado:** otro nombre o subtítulo para quien no ve la cuota, por ejemplo «Horas por cliente».
- **Dudoso:** sin datos no pude ver el contenido.

#### P2-8 · El vacío de la agenda desborda a 390 px
- **Dónde:** pantalla Agenda, todas las personas.
- **Qué pasa:** la página mide 419 px de ancho con 390 de pantalla. Dentro del vacío (`.vacio-g`), el botón «Recargar» mide 40 px pero su texto pide 97 px.
- **Captura:** `capturas/agenda_390_desborde.png`.
- **Más vacíos apretados a 390:** las tres columnas del vacío (icono, título y «Lo arregla») se aprietan y el título se parte palabra a palabra. Ejemplo: setter → «Mi día del setter» (`capturas/v_setter_390.png`).
- **Esperado:** el vacío se apila en el móvil.
- **Origen:** el vacío solo sale sin datos, pero el desborde es de CSS.

#### P2-9 · Etiquetas incoherentes
- **Puestos:** «Jefa de publicidad» y «Jefa de CRM y outreach» frente a «**Jefe** de SEO».
- **Decisiones:** el filtro «Para <persona de proyectos> · 24 h» (`modulos/decisiones.js:56,189`) nombra a una persona concreta, lo vean quien lo vea, la persona account incluida.
- **«Ver como»:** La jefatura de SEO y proyectos salen **dos veces** en el desplegable, una por puesto y con el mismo valor (`capturas/esc_dir_vercomo_menu.png`).
- **Esperado:** nombres de puesto coherentes y una línea por persona en el desplegable.

### P3 · pulido

1. **⌘K y Escape.** El pie de la paleta dice «Esc cerrar», pero con texto escrito el primer Escape solo borra y hace falta un segundo (`ayudas.js:401`). Además, Ctrl+K es interruptor: con la paleta abierta, la cierra.
2. **⌘K no encuentra un cliente por su identificador.** Buscar «cli-a» no da nada; «Gestoría» sí (dirección).
3. **Tarjetas de «En rojo» con 0.** «Crítico · actúa hoy 0 de 10» se puede pulsar y no hace nada (account1, trafficker1, ghl1). Lo mismo «Simulados 0» en Envíos. Mejor desactivarlas o dar un mensaje.
4. **«Componentes» (dirección) pinta «undefined ·»** en la muestra de frescura (`modulos/catalogo.js:209`), porque `meta.fuentes` no trae `fuente`/`edad_h`. **Dudoso:** es la forma de mis datos inventados de `meta`. Aun así, el componente debería tolerar el campo vacío.
5. **Generadores que cambian un fichero del repo.** `fuentes_alertas/generar_alertas.py` reescribe `fuentes_alertas/estado_alertas.json`, que está en git: 5388 líneas de diferencia tras una pasada. Lo restauré con `git checkout`. Cada recarga ensucia el repo.
6. **Subtítulos que son párrafos.** Paneles, Incidencias y Bandeja tienen subtítulos de 2-3 líneas a 1366 px. A 390 px se cortan o empujan el contenido.

## 3. Lo que funciona bien (verificado)

- **Navegación:** no hay excepciones de página en ninguna de las 420 pantallas. Las únicas peticiones fallidas son 404 de datos de módulo que faltan. No hay 5xx en el servidor principal.
- **Textos:** ningún «NaN», «[object Object]», «null» ni plurales rotos, salvo el «undefined» del punto P3-4.
- **Tiempos:** todas las pantallas cargan en menos de 0,6 s. **Dudoso:** son datos mínimos y no sirve como medida de velocidad.
- **Ficha ajena:** «La ficha de este cliente no es de tu puesto… habla con <persona responsable>» y botón «Ir a En rojo».
- **Pantalla fuera de menú:** «Esta pantalla no es de tu puesto… pídeselo a operaciones o a dirección».
- **Cliente inexistente:** «No encuentro ese cliente».
- **⌘K:** como account1, buscar «Clínica» (cliente ajeno) da 0 resultados. «Bufete» da su cliente, correos y acciones, e Intro abre la ficha. «/» también abre el buscador.
- **«Ver como»:** banda clara («Viendo como la persona account · solo lectura · queda en el rastro»), «Enviar» desactivado en la Bandeja, aviso de solo lectura en Mi perfil y el servidor rechaza las escrituras.
- **Operaciones:** puede «ver como» a dirección, RRHH y administración. Las pruebas C3 indican que las lecturas `solo_real` (sueldos) siguen bloqueadas; no lo pude verificar en pantalla sin datos de sueldos.

## Ficheros

- Generador de datos: `scratchpad/generar_datos_inventados.py`.
- Recorrido: `scratchpad/recorrido.js`, `scratchpad/analizar.py`, `scratchpad/recorrido/resultados_*.json`.
- Escenarios: `scratchpad/escenarios.js`, `esc_paleta*.js`, `esc_baja.js`, `esc_agenda.js`, `capturas.js`.
- Registros:
  - `scratchpad/servidor.log`
  - `scratchpad/seguridad.log`
  - `scratchpad/coherencia.log` y `scratchpad/coherencia2.log`
  - `scratchpad/diseno.log`
  - `scratchpad/escaner.log`
- Capturas: `scratchpad/recorrido/capturas/`.
