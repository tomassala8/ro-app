# E6 · Setters, ventas de RO y outreach · _ESTADO

**2-oct-2026, 15:10.** Construido sobre la base `30_APP_PROTOTIPO/` y el servidor `servir.py` de E0. **Nada escrito en GHL, Zadarma, Snov ni ninguna otra herramienta.** Todos los botones dejan una acción «simulada» (tabla `acciones` de `local.db` con `servir.py`; copia en el navegador sin servidor).

## Qué hay

| Pieza | Fichero | Qué hace |
|---|---|---|
| Mi día del setter | `modulos/setters.js` (`#/setters`) | Abre con **tu siguiente llamada** (Llamar · WhatsApp · Ver completo · GHL) y siete bloques: llamar ya · segundas que vencen en 48 h · citas por confirmar (hoy y siguiente día laborable) · citas pasadas sin resultado · marcador · llamadas perdidas o sin ficha · informe de fin de día. Móvil a 390 px primero, botones de 44 px. Tomás ve «Los dos / Ana / Javier»; Jessi y operaciones, solo recuentos. |
| Ventas de RO | `modulos/ventas_ro.js` (`#/ventas-ro`) | Cierre sobre celebradas (D-63), firmados a ritmo, asistencia (D-62), coste por cliente (D-13) y por cita (D1 ⚠️), reuniones de hoy, propuestas sin abrir a 72 h y sin respuesta a 7 días, contratos sin firmar, embudo septiembre/octubre con ritmo, circuito, huecos de 45 min frente a citas necesarias, bajas en 90 días. En «resumen» (operaciones, proyectos, Jessi, outreach): recuentos sin euros ni nombres. |
| Prospección y outreach | `modulos/outreach.js` (`#/prospeccion`) | Dos pestañas (D-69): **campañas de clientes** primero y **campañas de RO**. Respuestas de Snov.io de 30 días con «Asignar a…» y «Clasificar» · campañas y salud del envío · resultados por cliente (cifras del panel v7 de Mili) · **hoja semanal declarada** (D-71) con su propio sello. |
| Piezas comunes de E6 | `modulos/_ventas_comun.js` | Lectura por `ctx.datosModulo`, «Ver completo» por `ctx.verDato`, acciones por `ctx.accion`, iconos SVG locales, llamar (`sip:`) y WhatsApp (`wa.me`) con un clic, pestañas y campos de formulario. |
| Generador | `fuentes_ventas/generar_ventas_ro.py` | Solo lectura: GHL de RO (`GHL_PIT_NEW`, mismas funciones y exclusiones que `repartir_setters.py`), Zadarma (1 consulta), Snov.io, `dataset_ro.json` del panel v29 y `outreach_clientes.json`. Puerta de secretos propia **antes** de escribir. `--sin-zadarma`, `--sin-snov`. |
| Datos | `data/ventas_ro/{setters,ventas_ro,outreach,meta}.json` | Leads **enmascarados** (`M··· L···`, `··· ··· 807`). |
| Almacenes privados | `data/ventas_ro/_privado/` (`.gitignore` = `*`) | Nombre, despacho y teléfono (o correo) **solo** para «Ver completo». `servir.py` no los sirve nunca en bloque; `/api/ver_dato` los da campo a campo y deja rastro. **Nunca a GitHub ni a publicar.** |
| Índice | `modulos/indice.js` | Solo mis entradas: `setters` (nueva, M16a), `ventas-ro` (M16) y `prospeccion` (M17) a «hecho». |

**Para regenerar:** `cd 30_APP_PROTOTIPO && python3 fuentes_ventas/generar_ventas_ro.py` (≈1 min). **Para probar:** `python3 servir.py` y `?yo=setter_ana`, `?yo=tomas`, `?yo=eulimar`.

## Datos de hoy (2-oct, 14:54)

- **56 leads repartidos (28 Ana / 28 Javier, reparto simulado)**: 44 para «llamar ya» (sin ningún intento) y 12 con cita de 45 min. Excluidos 16: 5 segundas reuniones, 4 del curso, 3 con tarjeta en Propuesta/Seguimiento, 2 fichas de prueba, 1 «No encaja», 1 «no quiere crecer».
- **5 citas por confirmar** (lunes 5), **2 citas pasadas sin resultado** (hoy 11:00 y 12:00), **9 llamadas perdidas o sin ficha** en 48 h (solo Tomás las ve todas; cada setter, las de su extensión).
- **Ventas:** 3 reuniones hoy, 11 propuestas abiertas, 4 contratos enviados, 12 huecos libres de 45 min en 14 días (7, 8 y 9-oct) con 19 citas ya reservadas.
- **Outreach:** 17 campañas activas en Snov.io, **ninguna de RO**; 97 respuestas en 30 días, todas de campañas de clientes (Proincentiva Promotores 35, Greconsult Latam 16…).

## Pruebas de aceptación

| Prueba | Resultado |
|---|---|
| «Llamar ya» = leads sin intento | ✓ **0 de 44** tienen una nota «LLAMADA ZADARMA» en GHL posterior a su entrada en la lista (23 notas son anteriores: llamadas de Tomás antes de la cita). Intento = llamada saliente de Zadarma a su número desde que entró (no-show, alta o «sin hueco»). Las horas de Zadarma vienen en hora de Madrid (comprobado en el panel, 21-sep). |
| Un setter no recibe nada de los clientes de la agencia | ✓ en mis datos: respuesta de red de Javier → 28 leads, todos suyos; `ventas_ro` llega sin filas de prospectos ni euros; `_privado/setter_ana.json` → 403; `/api/ver_dato` sobre el almacén de Ana → 403. **✗ fuera de E6:** `/api/sesion` le manda 68 clientes y 120 alarmas («En rojo», D-90) y `/api/modulo/ventas_ro/outreach` le llega si lo pide a mano (ver «Para E0»). |
| Se usa con una mano a 390 px | ✓ sin desplazamiento horizontal (390 de ancho), siguiente llamada arriba, botones de 44 px, tablas apiladas. Capturas: no se pudieron sacar (el panel del navegador estaba oculto); comprobado por DOM y red. |
| El embudo de RO cuadra con el panel v29 en septiembre | ✓ **exacto**, ejecutando `calc()` del propio panel: 9.559,20 € · 769 contactos · 165 citas · 103 celebradas · 38 propuestas · 18 acuerdos · 13 firmados · 7 cobrados. |
| «Ver como» de 3 puestos (red, no pantalla) | ✓ Ana (setter): sus 28, Llamar/Ver completo activos, el resultado se guarda como acción simulada y «ver_lead» queda en el rastro (3 entradas: nombre, despacho, teléfono). ✓ Tomás «como Ana»: solo lectura, sin Llamar ni Ver completo, «Guardar» desactivado. ✓ Eulimar (outreach): 0 leads de setters, 97 respuestas enmascaradas, asignar y clasificar funcionan (96 sin dueño tras asignar una), Ventas de RO en resumen. ✓ Jessi: setters en recuento, sin filas. |

## Indicadores que pinta y con qué sello

- **Setter:** reuniones celebradas al mes (todavía no) · leads para llamar ya (a medias) · conversaciones > 60 s (a medias: extensiones por confirmar) · citas agendadas hoy (a medias) · intentos por lead D-65 (a medias) · citas pasadas sin resultado D-66 (se mide hoy).
- **Closer:** cierre sobre celebradas D-63 (a medias: 8 sin marcar en septiembre; 13 % → rojo) · firmados a ritmo (gris hasta el día 6: con 1 día da 344 %) · asistencia D-62 (73 %, ámbar) · coste por cliente D-13 (735 € en septiembre, ámbar) · coste por cita (58 €, propuesta D1 ⚠️) · huecos frente a citas necesarias (propuesta ⚠️) · bajas en 90 días (a medias: 1 coincidencia por nombre, Uhy Fay, a revisar: parece un cliente antiguo).
- **Outreach:** reuniones por 1.000 (todavía no) · respuestas sin dueño (a medias: solo Snov) · positivas fuera de GHL (a medias) · tasa de respuesta D-70 (todavía no) · rebotes y spam (todavía no).

## Lo que hace falta el lunes 5 para que los setters lo usen de verdad

1. **Permiso de escritura en GHL (W3 / D-04):** renovar `GHL_PIT_WRITE` de la subcuenta de RO y añadir a la app de agencia `conversations.write`, `conversations/message.write`, `contacts.write`, `opportunities.write`, `calendars/events.write`, `locations/tags.write`. Sin él, «Apuntar resultado», «Mover tarjeta» y «Agendar» se quedan en simulación y el setter lo repite a mano en GHL.
2. **Correos de RO de Ana y Javier** (`…@rankingonline.com`): son su llave de entrada (Cloudflare Access, W1) y el campo `correo` de `personas.json`. Hoy están como `setter_ana` / `setter_javier`, «por incorporar», sin correo de RO. Mientras no haya W1, la app solo se abre en el Mac de Tomás.
3. **Usuarios de GHL y etiquetas `setter:ana` / `setter:javier`** (con el sí de Tomás: crear usuario manda invitación): `crear_usuarios_setters.py --ejecutar` y `repartir_setters.py --ejecutar`. En cuanto estén, el reparto de la app deja de ser simulado y el marcador cuenta las citas de cada uno.
4. **Extensiones de Zadarma de cada setter** confirmadas (puse 107 Ana y 110 Javier por la memoria del 1-oct; están en `SETTERS` del generador). Sin ellas el marcador sale a cero.
5. **Que `sip:` abra Zadarma en su móvil** (la app de Zadarma tiene que estar instalada y registrada con su extensión) y **qué WhatsApp usan** con `wa.me`: el del móvil del setter, no el número de WhatsApp de RO en GHL. Si Tomás quiere que salga del número de RO, hace falta W3.
6. **Regenerar los datos cada mañana y a mediodía** (`generar_ventas_ro.py`), igual que el reparto: hoy no hay tarea programada para esto.

## Para E0 (propuestas, no tocado)

1. **`/api/modulo/<carpeta>/<fichero>` no mira qué módulos ve cada puesto:** un setter que lo pida a mano recibe `outreach.json` (respuestas enmascaradas de campañas de clientes). Propuesta: mapear `ventas_ro/setters` → módulo `setters`, `ventas_ro/ventas_ro` → `ventas-ro`, `ventas_ro/outreach` → `prospeccion` y negar con `nivelModulo`. Mientras, las filas de prospectos de `ventas_ro.json` llevan `setter: "_closer"` para que tu filtro solo las mande a dirección, ventas, Jessi y operaciones.
2. **Setters y «En rojo»:** `/api/sesion` les manda 68 clientes y 120 alarmas y su menú abre en «En rojo». La ficha G3 dice «clientes: ninguno»; D-90 dice «En rojo lo ven todos». Que Tomás decida; si gana la ficha, `en-rojo` con `setters: null` y su inicio en `#/setters`.
3. **`ver('lead')` no deja desenmascarar a outreach** (ni a `ventas_ro` sin dirección): la ficha G3 dice «completos los prospectos de sus campañas». Propuesta: `outreach` desenmascarable sobre `ventas_ro/_privado/outreach_respuestas`.
4. **Acciones compartidas:** `/api/rastro` solo devuelve las acciones de cada persona, así que el «dueño» que pone Eulimar no lo ve Fátima. Hace falta leer las acciones de un módulo (`/api/acciones?modulo=prospeccion`) para quien ve ese módulo.
5. **`sessionStorage` de «ver como» sobrevive al cambiar de `?yo=`:** tras ver como Ana, entrar como Javier da 403 en `/api/sesion` hasta borrar el almacenamiento.
6. Ola 0: cuando publique `icono()`, `pestanas()` y `botonesContacto()`, cambio los míos locales (`_ventas_comun.js`) por los comunes. Botón grande de 44 px: propongo `.bt.grande`.

## Dudas para Tomás

1. ¿Quién dirige a los setters en el día a día? (ficha G3 §7, pregunta 2). Hoy Jessi ve recuentos; si es ella, pasa a «todo».
2. ¿WhatsApp de los setters desde su móvil (wa.me) o desde el número de RO en GHL (necesita W3)?
3. ¿Objetivo de octubre = 18 firmados? Es el de la ficha del closer; el ritmo y los huecos se calculan con él.
4. RO no tiene ninguna campaña de outreach activa en Snov.io: ¿la pestaña «Campañas de RO» es para Linked Helper/Explee (solo hoja semanal) o se quita?

## Lo que se podría apagar

- El reparto en hoja y las listas de `25_GHL_PRUEBA_SETTERS/informes/` como lista de trabajo del setter (la app la saca sola cada vez).
- El panel de resultados v29 como sitio donde Tomás mira el embudo del día (queda para el detalle por anuncio).
- El recuento a mano de «respuestas sin dueño» (las 71 de Explee del 1-oct) en cuanto Explee mande sus respuestas a un buzón que lea la app.

## Falta (siguiente vuelta)

- Sesión de revisión con **Coti, Mili y Agus** (regla 15): sin hacer.
- Ficha del setter antes de cada reunión (cinco filtros, notas, grabación) en «Reuniones de hoy».
- Zoho Sign en «Contratos» (hoy, columna de GHL) y Explee/Linked Helper (sin API).
- Capturas de pantalla de los 3 puestos.

---

# Ronda de arreglos (2-oct noche)

Setters, Ventas de RO y Prospección rehechos con el sistema visual de la ola 0 (`tile`/`tiles`, `pestanas`, `chipsFiltro`, `vacio`, `tablaApilable`, `embudoBarras`, `barraProgreso`, `botonesContacto`, `icono`). Mis iconos y pestañas locales han desaparecido de `_ventas_comun.js`.

## Fallo de la auditoría → qué se ha hecho

| Fallo (auditoría) | Estado |
|---|---|
| B-01 / F-02 · Ventas: «Propuestas» y «Contratos» aplastadas | **Arreglado.** Ya no van en dos columnas: cada panel ocupa todo el ancho dentro de la pestaña «Hoy». Cada fila lleva dos botones (GHL y Fathom) y un «⋯ Más» con Ver datos, Oportunidades, Recordarme mañana y Mover tarjeta |
| I-07 · «344 % a ritmo» el día 2 | **Arreglado.** El ritmo solo se calcula con 5 o más días laborables cerrados. Antes, la tarjeta dice: «El ritmo se calcula desde el quinto día laborable (van 1)» |
| Texto 24 · «Cierre octubre — 2 de 0» | **Arreglado.** Sin reuniones celebradas, la tarjeta sale en gris: «Todavía sin reuniones celebradas este mes» |
| I-05 · Setters y Ventas fuera del sistema visual | **Arreglado.** Tarjetas con icono, pestañas comunes con contador, chips comunes, sin «→» |
| I-06 · Llamar y WhatsApp en un lead sin teléfono | **Arreglado.** Si no dejó teléfono pero hay correo, sale «Escribir por correo»; si no hay ninguno de los dos, «míralo en GHL». Esos leads van al final de la lista y la tarjeta «tu siguiente llamada» solo elige leads con teléfono |
| F-10 · Nombres enmascarados para quien llama | **Adaptado.** El servidor (E0) manda nombre y despacho completos a su dueño, y el módulo los enseña. Teléfono y correo salen al pulsar «Llamar», «WhatsApp» o «Ver datos», siempre por `ctx.verDato`, con rastro |
| Datos de leads siempre por ver_dato | **Hecho.** Ningún fichero `_privado/` se lee directamente |
| Extensiones 107 y 110 (desconectadas o de Lourdes) | **Hecho.** `ext = None` y «por confirmar» en el generador. Las llamadas del marcador salen «sin dato» en gris, nunca a cero |
| Textos 26, 27, 28, 29 y 66 · «Cole:», «/reuniones/», «ficha G3 §9», códigos, «Yessica» escrito a mano | **Arreglado.** Lenguaje llano en el generador y en los módulos («Rellenó el formulario de la web y no reservó»). Los nombres de personas salen de `ctx.nombre()`; `limpiaTexto` se aplica a todo |
| P-06 · «Yessica»/«Jessi» | **Arreglado en mis módulos.** Ya no hay nombres escritos a mano: el que sale es el de `personas.json` («Yessica», regla de E0) |
| F (29) · Yessica reparte 97 respuestas una a una con 17 desplegables | **Arreglado.** Se marcan varias con casillas (o «Elegir todas»), se elige a quién y qué clase con chips, y «Aplicar a las elegidas» de una vez. Hay filtros con contador (Sin dueño, Positivas, Todas, y por campaña). La lista enseña 15 respuestas y «Ver 15 más»; el contador de la pestaña ahora cuenta las respuestas sin dueño |
| Atajos (parte C del 26) · Setters | **Hecho.** GHL (contacto), GHL oportunidades (lista; no hay formato para abrir una oportunidad concreta), Zadarma (estadísticas), calendario y conversaciones de GHL |
| Atajos · Ventas | **Hecho.** GHL, **Fathom** (última grabación del contacto, cruzada desde el panel: 14 de 18 propuestas y contratos la tienen; si falta, el botón sale en gris con el motivo), oportunidades y calendario |
| Atajos · Prospección | **Hecho.** GHL (búsqueda por correo en la subcuenta de RO: hoy 0 de 97 están, y el botón gris lo explica) y **LinkedIn** (54 de 97, el perfil se abre por `verDato`), además de ClickUp y Snov.io |
| Auditoría 27 · outreach en «resumen» de Ventas recibe el tablero entero | **Arreglado.** En mi entrada de `reglas_permisos.json` añado `resumen` y `filas_lead`: quien ve Ventas en resumen recibe solo el embudo, el circuito y los recuentos. Lo mismo para Setters (Yessica y operaciones reciben recuentos, sin filas de leads) |
| Lista blanca de acciones | **Hecho.** Tipos nuevos dados de alta por módulo en `acciones_permitidas`; las herramientas, de la lista (ghl, zadarma, whatsapp, app) |
| Verdad única | **No aplica casi nada:** estos módulos tratan prospectos de RO, no clientes. Lo único de clientes (resultados por cliente en Prospección) toma el nombre de `ctx.verdadComun()`. No entro en ADOPTADOS porque `pruebas_coherencia.py` no tiene ninguna comprobación de estos módulos |
| P-12 · el setter aterriza en «En rojo» y tiene dos «Mi día» | **Pendiente de E0** (app.js y carcasa, ficheros comunes) |

## Pruebas

- `pruebas_e0.py`: **TODO BIEN** (servidor propio en 127.0.0.1, ya cerrado).
- `pruebas_coherencia.py`: un error, **de Agenda**, no mío. Mis módulos no tienen comprobaciones ahí.
- Recorrido con Playwright de **7 personas** (Tomás, Ana, Javier, Yessica, Eulimar, Mili y Coti) por las 3 pantallas, a 390 y 1440 px: **0 errores de consola** y ningún desbordamiento horizontal. Capturas en `capturas/{setters,ventas_ro,prospeccion}/r3_<persona>_<ancho>.png`.
- Ana a 390 px: la pantalla abre con «tu siguiente llamada» (nombre completo, Llamar, WhatsApp y GHL); sus 22 leads salen con nombre y 0 enmascarados.

## Lo que queda pendiente

- Confirmar las extensiones de Zadarma de Ana y Javier.
- Permiso de escritura en GHL (agendar, mover tarjeta, nota).
- La ruta de inicio por puesto, que es de E0.

## N6 · diseño 10/10 (2-oct, noche) · Mi día del setter y Prospección
Solo presentación (datos, permisos, cola simulada y botones igual). `setters.js` y `outreach.js`, limpios en `pruebas_diseno.py`.

**Mi día del setter (`setters.js`).**
- Pantalla de móvil:
  - Las 6 tarjetas van 2 + 2 + 2 en el móvil y 3 + 3 en el ordenador, con su propia rejilla. Nada de carrusel cortado ni tarjeta suelta.
  - En «Tu siguiente llamada», los botones de Llamar y WhatsApp tienen 48 px y van a todo el ancho en el móvil.
- El nombre del lead sale en `--t-h1`; fuera el `fontSize: 18px`.
- Fuera el número de las llamadas perdidas en Geist Mono a 11,7 px.
- Las tarjetas sin dato ya no pintan «—» de 24 px: ponen «Sin dato» o «Se mide desde el lunes 5» en letra de metadatos.
- La nota del día (1-10) va con chips en vez de desplegable.
- Los últimos informes salen como lista con icono y fecha «2 oct, 17:12».
- «Lo que falta para que funcione del todo» va plegado al final.
- «Ninguna llamada perdida» es un vacío en línea.
- Todos los espaciados usan tokens.

**Prospección (`outreach.js`).**
- Arreglado el «null» que se pintaba bajo «Aplicar a las elegidas»: venía de `replaceChildren(null, …)`.
- Las dos tarjetas «todavía no se mide» pasan a una línea bajo las 3 tarjetas medidas, que ya no dejan huérfana.
- Fuera los dos `<select>` de la hoja semanal: campaña y canal van con chips.
- Paneles con relleno común; «Ver 15 más» centrado; la casilla «Elegir todas» con 40 px de área.
- Las últimas filas declaradas salen como lista con icono.

**Comprobado:** 7 personas × 1440/1024/390. No hay errores de consola, scroll horizontal, texto < 12 px ni «null». Capturas en `capturas/_n6/setters/` y `capturas/_n6/outreach/`.

**Queda (de lo común):**
- `masAcciones` de `_ventas_comun.js` tiene una caja oculta que mide de más.
- La cabecera oculta de la tabla apilable a 390.
- El chip «Con…» de la 4.ª pestaña queda cortado a 390, porque `pestanas` desplaza en horizontal.

**Nota:**

| Pantalla | Antes | Después |
|---|---|---|
| Mi día del setter | 5,0 | 8,8 |
| Prospección | 5,0 | 8,7 |

## N6 · Diseño 10/10 (2-oct, noche) · Ventas de RO **8,5 / 10** (auditoría 30: 5,0)
- `ventas_ro.js`: coste por cliente con `colorCifra('coste_cliente')` (735 € en ámbar, el mismo color que en el Panel de dirección); 6 tarjetas → 3 + 3 (rejilla común); nueva pestaña «De qué anuncio» con los bloques 8 y 9 de `dinero_m16_anuncios.js`, que se habían quedado sin llamar. Sin estilos en línea.
- `_ventas_comun.js`: `campo()` pasa a la clase común `.campo` (antes estilos en línea de 15 px y relleno de 9/10 px); `masAcciones()`, `vistaPrevia()` y `contactoLead()` sin estilos en línea (los botones de 44 px en el móvil ya los da estilos.css). La firma de las funciones no cambia (la usan setters.js y outreach.js).
- Tomás, Mili y Coti a 1440, 1024 y 390: sin scroll, 0 textos < 12 px, 0 errores. Capturas en `capturas/_n6/ventas_ro/`.

## R12 · arreglos tras la auditoría final (2-oct, noche) · carril ventas y dinero
- **C-A1 · arreglado.** «Mi día del setter» en la vista «Los dos»: cada lead abre el almacén de SU setter (`almacenDe(l)` en setters.js); `puedeAbrir()` de `_ventas_comun.js` sigue la regla del servidor (la setter, dirección o ventas de RO) y nunca acepta `setter_null`. Probado como Tomás: WhatsApp → `/api/ver_dato` 200 sobre `setter_ana`, con rastro.
- **C-A4 · arreglado.** La causa: la recarga ligera corre el generador con `--sin-snov` y dejaba `snov: null` → «0 campañas, 0 respuestas». Ahora conserva la última lectura buena (con su hora; fuente «viejo» si es de otro día) y la pantalla dice «sin dato» y por qué si nunca se ha leído. Leído hoy: 25 campañas (17 activas), 97 respuestas de 30 días para repartir y clasificar.
- **C medio «0 celebradas» · arreglado.** Las reuniones de hoy ya pasadas cuentan con la etapa de GHL en vivo (Propuesta/Contrato/Cliente = celebrada; «No se presentó» = ausencia); la foto del panel es de la madrugada. Octubre: 1 celebrada (Clara), 1 ausencia, sin doble cuenta si el panel ya las marcó. En «Hoy», cada reunión pasada lleva su chip.
- **A-A2 · arreglado en Ventas de RO.** Serie diaria (`ventas_ro.json → dias`, mismas reglas que el panel; septiembre sumando días = 13 de 103, 9.559 €, exacto) → periodo común: 7 días, 30 días, este mes, mes anterior, trimestre, año y a medida, con comparación. No cambian (dicho en pantalla): «Hoy», la agenda de 45 min y las bajas tempranas. El cierre no da % con menos de 5 celebradas.
- Pruebas: `pruebas_coherencia.py` sección «R12 · VENTAS Y DINERO» (ventas-ro, setters y prospección pasan a ADOPTADOS). Capturas en `capturas/_r12_ventas/`.
