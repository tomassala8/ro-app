# M3 · Bandeja · estado (2-oct-2026, 15:40)

## Hecho
- `modulos/bandeja.js`: 5 indicadores arriba (correos > 48 h, 24-48 h, quejas, llamadas sin devolver, tickets sin agente para quien ve todo; WhatsApp para el account). Pestañas: **Correos y llamadas** (vistas en chips que se quedan: Para hoy · Quejas · > 48 h · 24-48 h · Llamadas · Automáticos y reenvíos · Más de 30 días · En cola; agrupar por account, día o cliente; chips de account para Mili, Coti, jefas y Tomás; buscador) · **Sin agente** (triaje seguro / dudoso / sin cliente, asignar al propuesto o cerrar) · **WhatsApp** (hueco W6 con los 7 pasos) · **De dónde sale** (reglas, departamentos de Desk y ruido descartado). Pie de fase 2.
- Detalle (a la derecha en escritorio, ruta `#/bandeja/<id>` en móvil): Contestar con plantillas y vista previa (de marketing@, asunto, firma de quien envía, nota interna «Enviado desde el panel por X»), Nota interna, Asignar, Cerrar, «No aplica» con motivo obligatorio; llamadas: «Ya la he devuelto», llamar con un clic marcado «espera W1». Todo va a `ctx.accion` (cola simulada); lo hecho pasa a «En cola». Quien no puede contestar (D-91) solo deja nota.
- Datos: `fuentes_bandeja/generar_bandeja.py` (en vivo Desk + Zadarma, plan B ficheros del panel; `--ficheros` sin llamadas; puerta de secretos antes de escribir) → `data/bandeja/bandeja.json`, dado de alta en `reglas_permisos.json → datos_de_modulo`. Reutiliza sin rehacer: criterio de pendiente y horas L-V de `hilos_clientes.json`, `_AUTO` y `_QUEJA` de `build.py`, `filtro_ruido.py`, lógica de llamadas perdidas de `build.py` 679-710, `triaje_desk.json`, `puente.json`.
- Permisos: `indice.js` → jefas pasan a «todo» (encargo: Mili, Coti, jefes y Tomás ven todo). Recorte en servidor comprobado por red: tomas/mili 736 correos + 3 llamadas + 264 sin agente; lucia 62 (solo los suyos, 0 sin cliente); valeria/yessica/constanza 410 (sin filas sin cliente); setter_ana 403.

## Pruebas (`fuentes_bandeja/probar_bandeja.py`, Chrome sin cabeza, servir.py :8783)
- tomas, mili, lucia, valeria, yessica, constanza y setter_ana a 1440 y 390 px: 0 errores de consola propios, 0 px de desborde. (El único 404 es `modulos/nuevos.js`, de otro agente en curso.) Detalle en móvil sin desborde. Acción simulada probada: Lucía contesta RO-7480 → fila `acciones` «simulada» y Mili la ve en «En cola».
- Capturas en `capturas/bandeja/`. `escaner_secretos.py`: limpio.

## Cifras contrastadas
1. **RO-7480 GAC «Seguimos casi sin leads»**: panel v27 165 h a las 07:00 → app 7 d 6 h (174 h) a las 15:2x: cuadra (+8 h laborables).
2. **Llamadas sin devolver**: 3 números (···028865 ×3, ···984555 ×9, ···203753 ×1), los mismos que `v7.perdidas` del panel, ahora leídos en vivo de Zadarma.
3. **Triaje sin agente**: 80 seguros · 30 dudosos · 154 sin cliente, frente a 80 · 30 · 155 de `triaje_desk.json` (uno cerrado desde las 06:56).
- Además: 2.568 tickets abiertos en «Marketing Clientes.»; 117 correos de cliente recientes frente a 125 del panel a las 07:00 (contestados o cerrados desde entonces).

## Falta / dudas (en `dudas_pintura.md`, D-P-BDJ)
- Solo 1 de 30 departamentos de Desk es legible con la llave de lectura (3 activos dan 403): permiso en Desk.
- `/api/acciones?modulo=` no recorta por cliente (E0).
- Hilo completo del correo: se abre en Desk; leerlo aquí llega con W1. Envío real (Desk), llamar con un clic (W1/W7) y WhatsApp (W6) con botón ya puesto.
- «Opinión del cliente sobre sus leads»: fase 2 (no hay campo).
- Revisión con Coti, Mili y Agus (R15): pendiente.

---

# Ronda de arreglos (2-oct noche) · fallo de la auditoría → qué se ha hecho

| Fallo (documento) | Estado |
|---|---|
| E-06 (28): no leía «Por resolver»; 71 tickets fuera (Laver RO-6626, Musashi RO-6843 y RO-6894) | **Arreglado.** El generador lee de Desk la lista de estados y coge todos los que no son de tipo cerrado (Abierto, En espera, Escalado, Por resolver, Por responder, En Seguimiento). Hoy: 42 «Por resolver», 25 «Por responder», 18 «En Seguimiento». RO-6626, RO-6843 y RO-6894 ya salen |
| E-21 (28): falsas quejas (Drive, calendario) | **Arreglado.** «Cancelado:», «Cancelada:», «Invitación:», «Elemento compartido», «Documento compartido», «ha compartido»… van a avisos automáticos antes de mirar si es queja |
| E-07 (28): ficha (07:00) frente a Bandeja; días naturales frente a laborables | **Arreglado en la Bandeja / preparado para la ficha.** Todo en laborables (`dias_laborables`, horas L-V). Nuevo `data/bandeja/por_cliente.json` con la misma regla (sin contestar, > 48 h, 24-48 h, quejas, más antiguo con enlace), dado de alta para Bandeja, Ficha y Mi día. **Falta que la ficha lo lea** (es fichero del dueño de la ficha; apuntado en dudas) |
| I-13 (22): perdida de hoy 12:08 (619…618) no aparecía | **No aplica:** se devolvió a los 25 s (Tomás, 12:08:35, contestada 3 min 17 s). Comprobado en Zadarma en vivo. Las de 0 s sí cuentan ahora |
| I-13 (22): «primera 16:21» de 669…753, cuando llamó a las 10:41 | **Arreglado.** Nueva regla: pendiente = entrantes sin contestar después del último contacto contestado; un intento nuestro sin respuesta (12:47) ya no la da por devuelta. Ahora: primera 10:41, 3 llamadas, 1 intento nuestro |
| 22: «Sin cliente identificado» arriba, «BOFU», «(D-29)» | **Arreglado.** «Correos sin cliente» va el último; textos sin códigos ni nombres de fichero (comprobado: 0 coincidencias en pantalla) |
| 26 parte C: Zadarma en la Bandeja y tickets de Desk en formato nuevo | **Arreglado.** Desk: `desk.zoho.eu/agent/rankingonline836/marketing-clientes-1/tickets/details/<id>` (también en el reparto y en el plan B). Llamadas: «Ver en Zadarma» (estadísticas; no hay enlace por llamada). GHL del número: no aplica (no se guarda el número completo) |
| F-03 / F-09 (29): «Ir» a la cosa; queja de Adade escondida; «Por día» al revés; 3 filas de chips | **Arreglado.** `#/bandeja/<id>` abre ese correo en la lista (cambia de vista sola si hace falta; probado con RO-6626); las quejas nunca van a «Más de un mes» (Adade RO-3940 sale el primero en la bandeja de Lucía); «Por día» del más antiguo al más nuevo; 4 vistas (Para hoy, Quejas, Llamadas, Todo) + «Más vistas…»; el account se elige en un desplegable |
| 29: letra < 12 px | **Arreglado** (0 textos por debajo de 12 px; logos de 22 px) |
| 29: reescrituras 10, 11, 13 y 14 | **Arregladas** («Correos sin responsable», «Es una queja: llama hoy…», «Prueba: este envío todavía no sale de verdad», subtítulo) |
| 29: sello «Se mide hoy» en todo | **Arreglado:** solo sale cuando no se mide del todo (quejas «a medias», WhatsApp «todavía no») |
| Regla 1: verdad única | **Adoptada.** Account de cada fila = `verdad.account` (en el generador y otra vez al pintar con `ctx.verdad`); nombres con `ctx.nombre`. `bandeja` en ADOPTADOS de `pruebas_coherencia.py` con 2 comprobaciones, en verde. `--solo-account` vuelve a sellar sin llamar a nadie |
| Regla 6: sin dato = gris | **Arreglado:** si falta Desk o Zadarma, el indicador sale «—» en gris, no 0 en verde |
| 27 M3 (rastro y acciones de cualquiera) | **No aplica aquí:** lo arregla E0 en `servir.py`/`schema_v2.sql`. Añadido `llamada_devuelta` a `acciones_permitidas.bandeja` |

**Pruebas (ronda 3):** `fuentes_bandeja/probar_bandeja.py` con las 7 personas a 1440 y 390 px: 0 errores, 0 desborde, ruta directa RO-6626 abierta. `pruebas_coherencia.py`: 0 errores (bandeja en verde). `pruebas_e0.py`: el único fallo es el escáner sobre `data/agenda/agenda.json` (de Agenda, no de la Bandeja). Capturas en `capturas/bandeja/r3_*`.

**Aviso de operación:** el generador en vivo tarda varios minutos (≈2.900 tickets abiertos y una consulta por cuenta nueva). Ahora guarda las cuentas en `fuentes_bandeja/_cache_cuentas_desk.json` y la segunda pasada es mucho más rápida. Si la recarga de E0 lo corta a los 300 s, sale el plan B (fichero del panel de las 07:00): a las 17:28 alguien lo lanzó así; la pasada en vivo de las 17:30 tardó 8 min. Recomendación a E0: subir el tiempo a 900 s en `recarga.json`.

# Ronda IA + diseño (2-oct, noche)
- **IA:** «Sugerir respuesta» (`botonIA(ctx, { ticket, destino })`) en cada correo, encima de la caja de respuesta. «Usar este borrador» solo rellena la caja; enviar sigue pidiendo «Sí, enviar» (cola simulada). Probado: la cola no cambia al usar el borrador (1 → 1).
- **«null»:** confirmado que ya no sale. Venía de `Element.append(null)` (bajo «Desk · hace… · Zadarma · hace…») y había otro en el detalle de cada correo que no es queja; arreglados y la prueba ahora lo busca.
- **Guía de diseño:** fuera la hoja propia (`bandeja-estilos`); filas con el patrón común «Lo primero» (`.primero`), controles en `.tabla-ctl`, campos `.campo`, «Más vistas ▾» con el `menuMas` común, `rejillaTarjetas`; códigos RO-xxxx sin Geist Mono; 0 textos < 12 px. Sin cifras por periodo: no usa `usa_periodo`.
- **Pruebas:** `fuentes_bandeja/probar_bandeja.py` (puesto al día: sofia en lugar de constanza, comprobación de «null», hoja propia, textos < 12 px y de la IA) → TODO BIEN con las 7 personas a 1440 y 390. `pruebas_coherencia.py`: bandeja en verde. Capturas `capturas/bandeja/r4_*`.

## V2-C1 (3-oct)
- **A-M11 boletines · arreglado:** `clasifica_asunto()` en el generador: boletines y circulares de marketing («¿Sabes…? Descúbrelo en esta guía», «Nota informativa», webinar, newsletter…) van a «Automáticos y reenvíos», con chip «Boletín: no cuenta»; no suben días ni gravedad. Un encargo sobre el boletín («Revisión de la newsletter mensual», «Pedido de aprobación - Newsletters») SÍ cuenta (antes iba como automático). Modo `--reclasificar` sin llamadas. Prueba en pruebas_coherencia (V2-C1).
- **A-M11 «el más antiguo» de ⌘K · no aplica aquí** (la acción es de `ayudas.js`); la Bandeja ya da el más antiguo sin boletines en `por_cliente.json`.
- **R16 · arreglado:** «Asignar» solo para dirección, operaciones y proyectos (detalle y reparto).

# V5 · Bandeja para TRABAJAR (3-oct)
Encargo de Tomás: «¿cómo puede ser que la parte de responder correos sea pequeñita y esté a la derecha?». Rehecha la pantalla de
`modulos/bandeja.js` (vistas secundarias, reglas y datos de antes, intactos).

**Cómo lo resuelven otros (fuentes abiertas):** tres zonas (lista · conversación con editor · ficha del cliente plegable) en Front
(help.front.com/en/articles/3889728), Zendesk Agent Workspace (support.zendesk.com/hc/en-us/articles/4408821259930), Missive
(missiveapp.com/docs/get-started/missive-interface) y Superhuman (help.superhuman.com/hc/en-us/articles/46005778939789); «enviar y
siguiente» / qué pasa tras enviar en Help Scout (docs.helpscout.com/article/69-respond-to-conversations) y Zendesk
(support.zendesk.com/hc/en-us/articles/4408829483930); «Enviar y archivar/snooze» en Front (help.front.com/en/articles/2431) y Missive
(missiveapp.com/docs/core-features/triage-and-assignment); atajos j/k/r/e/a en Front (help.front.com/en/articles/2189), Help Scout
(docs.helpscout.com/article/419-keyboard-shortcuts), Missive (missiveapp.com/docs/advanced-features/shortcuts) y Gmail
(support.google.com/mail/answer/6594); plantillas con «/» en Front (help.front.com/en/articles/2230) y huecos que avisan en Superhuman
(help.superhuman.com/hc/en-us/articles/46005686571149); estados «pendiente/esperando» que se reabren en Zendesk
(support.zendesk.com/hc/en-us/articles/8263915942938); móvil con pestañas Conversación/Detalles en Zendesk
(support.zendesk.com/hc/en-us/articles/4408825697434).

**Qué hay ahora**
- **Escritorio (contenido ≥ 1.000 px):** lista compacta a la izquierda (filtros Míos · Sin responder · Quejas · Esperando · Todos con
  contador; «Más» con automáticos, más de un mes, ya hechos y las vistas de reparto, WhatsApp y de dónde sale; orden Urgencia | Más
  antiguo; los sin cliente al final) · **centro**: cabecera (asunto, espera, queja, cliente, ticket ↗, account, estado de Desk, «3 de
  17 ‹ ›») + acciones de un clic (Despachado e · Esperando p · Asignar a (solo quien puede) · Tarea en ClickUp · Avisar a su account ·
  Más: No aplica con motivo, Cerrar, Abrir en Desk) + **hilo legible** (mensajes plegables, los dos últimos abiertos, «Desplegar
  todo», pies legales y citas quitados) + **editor siempre a la vista** con el borrador de la IA ya dentro · derecha: **contexto del
  cliente plegable** (gravedad y por qué, equipo, más correos suyos, impago si lo ve, campaña y leads 7 d, tareas en revisión y
  bloqueadas, reuniones, enlaces a ficha/Desk/canal/GHL). Abierto por defecto si el contenido mide ≥ 1.280 px; se recuerda.
- **1024:** lista + conversación; el contexto pasa a pestaña «Cliente»; acciones con icono. **390:** lista → conversación a pantalla
  completa (sin cambiar de pantalla: `history`), editor fijo abajo, pestaña «Cliente».
- **Editor (cerebro de respuestas, `/api/ia/borrador`):** «Calidad del borrador NN/100 · lista/revisar/rehacer» (la nota del servidor;
  los huecos se cuentan en vivo), tipo de correo, «Lo que falta» (faltas que llevan al hueco, `[completar: …]` como botones, casillas de
  huecos, recomendación interna, siguiente paso, datos citados, qué pedía el cliente), los `[…]` **resaltados en ámbar** dentro del
  texto y **Enviar bloqueado** mientras quede uno (selecciona el primero). Si el cerebro dice «no hace falta responder», el botón
  principal es **«Cerrar sin responder»** (⌘↵ hace el principal). Plantillas (menú y «/» al empezar una línea), adjuntos simulados
  (solo el nombre va a la cola), firma de quien envía, Responder | Nota interna, ampliar. Crece con el texto (quejas de 160 palabras,
  resultados de 200) dejando 160 px de hilo (96 px mientras escribes).
- **Procesar la bandeja:** «Enviar y siguiente» abre el siguiente; j/k, r, e, a, p, z (deshacer), ⌘↵; atajos a la vista (letras en los
  botones y pie de la lista). Lo que saca el correo (responder, despachado, esperando, no aplica, cerrar) usa **«Hecho · Deshacer»**
  de `modulos/_deshacer.js` (8 s, se encola al cambiar de pantalla); el «¿Seguro?» solo vuelve si los envíos reales están activados
  (`/api/envios → modo.reales`). Sin cliente no se contesta (el servidor daría 403): nota, asignar o despachado.
- **Envíos:** todo sigue en simulación y pasa por `envios.py`; el hilo enseña «Desde la app» con el estado de cada envío (simulado /
  pendiente / enviado / confirmado / fallido) y la hora local.
- **Datos nuevos:** `fuentes_bandeja/generar_hilos.py` → `data/bandeja/hilos.json` (40 hilos, 158 mensajes, sin correos ni teléfonos;
  recorte por `cliente_id`, sin cliente solo Operaciones y Dirección), dado de alta en `reglas_permisos.json → datos_de_modulo` y
  lanzado al final de `generar_bandeja.py`. Acciones nuevas `despachado` y `esperando_cliente` en `acciones_permitidas.bandeja`.
  Molde común: `plegarConsejo` de `_plegar_consejo.js` (el consejo en una línea, sin empujar la zona).

**Medición (`fuentes_bandeja/medir_bandeja.py`, Chrome sin cabeza, base copiada en cada pasada, primero la tarea A de todos)**

| 1440 × 900 | A · leer el más antiguo y dejar la respuesta lista | B · procesar 5 seguidos |
|---|---|---|
| lucia | 3 clics + 4 ruedas → **0 + 0** | 20 + 23 → **5 + 0** |
| candela | 3 + 4 → **0 + 0** | 16 + 16 → **5 + 0** |
| mili | 3 + 4 → **0 + 0** | 24 + 29 → **5 + 0** |
| tomas | 3 + 4 → **2 + 0** (Sin responder + Más antiguo) | 25 + 26 → **5 + 0** |
| yessica | 3 + 2 → **0 + 0** | 24 + 23 → **5 + 0** |

A 1024 × 768: antes A 3 clics + 2-3 ruedas, B 21-25 clics + 11-20 ruedas → después igual que a 1440 (A 0-2 + 0, B 5 + 0). Con
⌘↵ la B es 0 clics. A 390: 1 toque en la fila y el editor ya está abajo (probar_bandeja).

**Pruebas:** `probar_bandeja.py` (8 personas × 1440/1024/390 + flujo) TODO BIEN · `pruebas_e0.py --puerto 9230` TODO BIEN (diseño
estricto incluido) · `pruebas_seguridad.py` TODO BIEN · `pruebas_coherencia.py` sin errores (bandeja en verde) · `escaner_secretos.py
--proyecto` limpio · `import('./modulos/bandeja.js')` sin errores. Servidor solo en 127.0.0.1:9230 con copia de `local.db`.
Capturas `.jpg` en `capturas/_bandeja_v5/` (antes_*, cada persona a 1440/1024/390, hilo, tras enviar, vistas, móvil).

**Pendiente / dudas (D-P-BDJ-5):** Mi día da por hecho cualquier acción de la Bandeja; `envios.py` debería rechazar `[…]` en el
servidor; el hilo solo existe para 40 correos (el extractor de la IA tendría que bajar todos los pendientes).
