# _ESTADO · M24 Chat del equipo + N15 Canales de avisos, grupos y alertas automáticas (2-oct-2026)

## N15 (2-oct, noche) · «que los canales de avisos, grupos y alertas automáticas de ClickUp también existan»

**Hecho.** Servidor `avisos.py` (enganchado a `servir.py` como `ia.py`/`altas_personas.py`, rutas **`/api/canales/*`**; `/api/avisos` sigue siendo lo de E0), pantalla `modulos/chat_equipo.js`, campana en `carcasa.js`, tapado común en `fuentes_chat_equipo/tapado.py` y partido del chat en `fuentes_chat_equipo/partir_chat.py`.

- **Avisos por departamento** (#avisos-web, -seo, -crm, -publicidad, -redes, -accounts, -altas, -administración, -rrhh, -dirección): cada alerta de N4 (`data/alertas/alertas.json`) se publica una vez con dueño, plazo, gravedad y **mención al dueño**; si pasa el plazo sin «Lo tengo», un aviso en su hilo menciona a quien sube. Eventos del sistema: cliente firmado (#avisos-altas y #general), alta de persona (#avisos-rrhh y bienvenida en #general), fuente caída (#avisos-dirección), informe enviado (#avisos-accounts, solo a quien abre el cliente), cumpleaños y aniversarios del día (#general). Web caída llega como alerta de N4.
- **«Lo tengo» / «Resuelta»** en la tarjeta escriben la **misma acción** que la pantalla de Alertas (`acciones`, módulo `alertas`, `alerta_lo_tengo` / `alerta_resuelta`): para el escalado, la ve Alertas y el generador la comprueba con el dato siguiente. Deja respuesta en el hilo y fila en el rastro.
- **Grupos de la app** donde se escribe: #general, uno por equipo (`equipo-<dep>`), uno por cliente (`cliente-<id>`, solo quien lo lleva y quien puede abrir el cliente; dirección y operaciones, todos) y grupos propios («Nuevo grupo»). Lo escrito queda en `canal_mensajes` (imborrable por disparadores) y **nunca sale a ClickUp ni fuera**. Hilos, @menciones con sugerencias, «Añadir persona», silenciar.
- **ClickUp = espejo de solo lectura**: sin caja de escribir; «Contestar en ClickUp». Auditoría de velocidad: `p_<id>.json` es ahora un **índice ligero** (Tomás 1 MB → 134 KB, 17 KB comprimido) y los mensajes de cada canal van en `data/chat_equipo/_privado/c_<canal>.json`, servidos por `/api/canales/clickup` de 50 en 50 («Cargar mensajes anteriores») y solo a quien es miembro según su propio índice.
- **Campana** en la cabecera (junto al avatar, mismas clases `yo-menu/yo-btn/yo-pop`): nuevas desde la última vez, menciones, avisos con tu nombre y **resumen diario** a la hora de cada persona en su zona (`personas.json → zona`, 08:30 por defecto; se cambia en «Tus avisos»). Se refresca cada minuto y al tocar algo en el chat.
- **Permisos**: canales de su departamento (puesto → departamento, más jefes y dueños fijos de `departamentos.json`) y los que le añaden; un aviso solo llega si esa alerta está en su `alertas/p_<id>.json`; lo de un cliente solo si puede abrirlo; importes fuera con `P.sin_importes` según cuota/inversión; contraseñas (`tapar()`), correos y teléfonos tapados **antes de guardar**; los sueldos no se pueden escribir (400). «Ver como»: canales y alertas que ven LAS DOS, nada se escribe (403) y el ClickUp de otro no se abre.
- **Tablas nuevas** (misma base, `CREATE IF NOT EXISTS` en `avisos.py`): `canal_mensajes`, `canal_miembros`, `canal_grupos` (sin borrar ni cambiar), `canal_leidos`, `canal_preferencias`, `canal_resumenes`, `canal_campana`. No había `estado.py`: las tablas las crea `avisos.py` al engancharse.

**Pruebas (servidor propio 127.0.0.1:9010 con copia de local.db):** 7 personas (tomas, mili, lucia, valeria, yessica, constanza, setter_ana) × 1440 y 390 sin errores de consola, sin desborde ni «undefined»; flujo de Lucía (Lo tengo, comentario con @Mili, mensaje con contraseña y teléfono → tapados, campana, espejo sin caja), Natalia ve «Te menciona», Tomás «como» Lucía sin escribir. `pruebas_seguridad.py` TODO BIEN, con 54 comprobaciones N15 (nadie lee canales ajenos, «ver como» no escribe por ninguna ruta, resumen a su hora con reloj fijado); `pruebas_e0.py` TODO BIEN (diseño estricto limpio); `pruebas_coherencia.py` 0 errores; `escaner_secretos.py --proyecto` limpio. Capturas en `capturas/_n15/` (26 .jpg). `despliegue/barrido_total.py --vuelta n15` (tomas, mili, lucia, lara, setter_ana): 0 fallos en chat-equipo y en la carcasa, 0 desbordes (la campana a 390 px desbordaba 11 px con «Actualizar»: arreglado).

**Para Tomás (pendiente de decidir):** escribir en ClickUp desde la app (hoy no: todo se queda en la app). Recarga: `generar_chat_equipo.py` ya parte solo; `generar_alertas.py` alimenta los avisos sin tocar nada más.

---


## Ronda 3 (2-oct noche) · fallos de las auditorías → qué se ha hecho

| Fallo (auditoría) | Estado |
|---|---|
| F-04 (29): decía «Todavía no estás en ningún canal… Lo arregla: Mili» cuando era un 403 | **Arreglado**: 404 (no hay fichero) = sin canales de verdad; cualquier otro error = «No puedo leer tus canales ahora mismo. Recarga en un minuto; si sigue, avisa a Tomás» con botón Recargar. Probado forzando un 403. |
| Lectura del fichero propio tras los permisos de E0 | **Comprobado**: `chat_equipo/p_*` con `solo_propio` + filtro por `miembros`: Lucía lee el suyo (32 canales), pedir el de otro → 403. |
| Escribir: tipos de acción fuera de la lista blanca | **Arreglado**: `acciones_permitidas["chat-equipo"] = ["chat_mensaje", "chat_respuesta"]`; el mensaje queda en cola (probado). |
| 26 parte C: atajos | **Arreglado**: «Abrir en ClickUp» por canal y, en cada mensaje, el enlace al mensaje exacto (`app.clickup.com/{equipo}/chat/r/{canal}/t/{mensaje}`). |
| Regla 2: emojis y códigos en pantalla | **Arreglado**: el clip de adjunto es un icono del sistema; textos sin «W1»; los emojis que escribe la gente se respetan (son su mensaje). |
| 70 (29): nombres | **Arreglado**: autores, miembros y directos con `ctx.nombre(id)` cuando la persona está en la app. |

**Pruebas:** 7 personas × 1440 y 390 sin errores de consola · capturas `capturas/chat_equipo/r3_*` (incluida la del 403: `r3_lucia_403_1440.png`).

---


**Hecho.** `modulos/chat_equipo.js` (ruta `#/chat-equipo/<canal>`, grupo «Hoy»), datos con `fuentes_chat_equipo/generar_chat_equipo.py` (llave propia de ClickUp `clickup_api_token`, API v3, solo GET; **nunca** el conector de Claude).

## Qué hace
- **Arriba:** te han mencionado · sin leer · tus canales · en cola (simulado). En móvil se ocultan para que la lista de canales sea lo primero.
- **Como ClickUp/Slack:** columna de canales (Canales · Grupos · Mensajes directos) con último mensaje, contador azul de no leídos y rojo «@n» de menciones; vistas Todo · Sin leer · Menciones; buscador en todos tus canales e hilos con el texto resaltado.
- **Conversación:** separadores por día, línea «Nuevos», menciones resaltadas (las tuyas en ámbar), enlaces y adjuntos clicables, hilos desplegables con sus respuestas, «Responder en hilo», caja de escribir (Intro envía). En directos, «Videollamada Zoom». «Abrir en ClickUp» en cada canal.
- **Escribir y responder:** `ctx.accion({ herramienta: 'clickup', tipo: 'chat_mensaje' | 'chat_respuesta' })` → cola con estado «simulada»; el mensaje sale en el canal con el chip «En cola · simulado». En «ver como», la caja está desactivada (y el servidor lo rechaza).
- **Panel «Cómo saldrán tus mensajes cuando la app se publique»:** OAuth por usuario explicado en 4 pasos.

## Datos
- 217 conversaciones en ClickUp → 105 de clientes (fuera: ya están en la pestaña Chat de la ficha, M4) · **38 canales internos** con actividad en 120 días · 23 dormidos · 43 directos y grupos de Tomás.
- Últimos 40 mensajes por canal, hasta 10 hilos por canal (25 respuestas cada uno). Correos, teléfonos y contraseñas de enlaces (`pwd=`) se quitan; emojis partidos de la API, saneados. 252 llamadas a la API por pasada (cupo 1.000/min).
- **Un fichero por persona** (`data/chat_equipo/p_<id>.json`, 32) con solo los canales de los que es miembro (lista de miembros de cada canal de la API). Los directos que da la API son los de Tomás (la llave es suya): solo en `p_tomas`.
- **No leído** = llegó después de tu última visita a ese canal en esta app (en el navegador; primera visita: lo de las últimas 48 h). El leído de ClickUp por persona no se puede leer con una sola llave: llega con OAuth.

## Cifras contrastadas a mano
1. **217 conversaciones** = listado directo `GET /v3/workspaces/90152357276/chat/channels` (166 canales, 47 directos, 4 grupos).
2. **Account Managers: 14 personas · Heads: 15** = `GET …/channels/{id}/members` de la sonda.
3. **Mención a Mili** «90 % de mis informes subidos al sheet…» con 1 respuesta («topp, mañana reviso todo») = mensaje y `replies` de Account Managers en la API.

## Permisos (probado contra el servidor)
- Lucía pidiendo `chat_equipo/p_tomas` → 0 canales (filas con `persona_id: tomas`, recorte de servir.py). Ana (setter): 0 canales, estado vacío con «Lo arregla: Mili».
- Cada persona solo pide su fichero. **Hueco conocido:** por la regla `horas_persona`, su jefe, operaciones, RRHH y dirección podrían pedir el fichero de otra persona por la API. Pedido a E0 (D-P-CHAT): filtrar filas por `miembros` (lista de ids) o una regla «solo la persona». En pantalla no se ve nunca el de otro salvo con «ver como» (Mili y Tomás, queda en el rastro).

## ¿ClickUp chat o una alternativa? Recomendación: **seguir con ClickUp**
- **A favor:** el equipo ya vive ahí (217 conversaciones, 38 canales internos activos, 46 clientes con canal), las tareas y los chats de clientes están en el mismo sitio, sin migración ni coste nuevo; la API v3 de chat permite leer canales, miembros, mensajes, hilos y menciones, y escribir mensajes y respuestas; tiene OAuth por usuario para que cada mensaje salga con su nombre.
- **En contra:** no da el «leído» por persona con una llave común; la API de chat es la v3 (más nueva, puede cambiar); hoy no hemos comprobado avisos al momento (webhooks) del chat: si no los hay, la app consultará cada minuto por persona.
- **Alternativas miradas:** Slack (mejor API y llamadas, pero pago por persona y migrar todo), Zoho Cliq (entra en el ecosistema Zoho de Desk/CRM/Bookings, misma llave OAuth, pero el equipo no lo usa) y Google Chat (sin Workspace de RO para todos). Ninguna compensa mover 217 conversaciones.
- **Llamadas:** «Videollamada Zoom» abre Zoom con tu cuenta; la llamada de un clic al cliente (Zadarma, «callback») va en la ficha y llega con la publicación.

## Para publicar (W1)
1. Registrar la app de RO en ClickUp (Settings › Apps › Create new app) con la dirección de vuelta de Cloudflare.
2. «Conectar mi ClickUp» la primera vez que alguien pulsa Enviar; la llave de cada uno como secreto del servidor.
3. Cambiar `encolar()` por `POST /api/v3/workspaces/{ws}/chat/channels/{id}/messages` (y `…/messages/{id}/replies`) con la llave de quien escribe; la cola simulada ya guarda canal, texto y quién.

## Pendiente / dudas (en `dudas_pintura.md`, D-P-CHAT)
- Filtro por `miembros` en servir.py (arriba). Icono `ICONO_MODULO['chat-equipo'] = 'chat'` (hoy sale el del grupo). Las 32 altas `chat_equipo/p_<id>` en `datos_de_modulo`: si entra una persona nueva hay que añadir la suya (o que E0 acepte un patrón `chat_equipo/p_*`).
- 10 miembros de ClickUp sin persona en la app (Alejandro Carugatti, Alejandro Toledo, Camila Videla, Carlos Pedraza «charly», Francisco Colmenarez, Gastón, Gianluigi Rondon, Mauricio Gonzalez y 2 bots): salen con su nombre en los miembros, sin agenda ni fichero.

## Capturas (`capturas/chat_equipo/`)
`<persona>_1440.png` y `<persona>_390.png` para tomas, mili, lucia, valeria, yessica, constanza y setter_ana · `lucia_canal_hilo_1440.png` (hilo abierto + mensaje en cola), `lucia_busqueda_1440.png` («informe», 11 resultados), `lucia_menciones_1440.png` (22). Consola sin errores; sin desplazamiento horizontal a 390 px.

## Regenerar
`python3 fuentes_chat_equipo/generar_chat_equipo.py` (≈ 4 min). Para desarrollo, `RO_CHAT_CACHE=<fichero>` guarda las respuestas y no repite llamadas.

## N6 · diseño 10/10 (2-oct)
**Qué cambié (solo presentación; datos, permisos, cola simulada, rastro, teclado y enlaces intactos):**
- Fuera la hoja inyectada (`ESTILO`/`estilos()`): todo con clases comunes (tiles, chips-f, bt, av, ico-c, panel, vacio-g) y estilos en línea con tokens (`--t-*`, `--s-*`, `--r-*`, `--borde`, `--sombra-1`, `--anillo`). Sale limpio en `pruebas_diseno.py`.
- Lo que hacía la hoja lo hace el módulo: `realce()` (fondo al pasar el ratón en canales y mensajes) y `ANCHO` con `matchMedia` (≤ 860 px se ve la lista o la conversación, ≤ 640 px sin tarjetas); se repinta al cambiar de ancho, con un solo oyente.
- Contadores y grupos de 10,5 px → 12 px (contadores) y 11 px eyebrow en mayúsculas 700 (grupos, días, «NUEVOS»); avances de último mensaje y horas a 12 px `--dim`.
- Área de clic: buscador 22 → 34 px; «N respuestas» 22 → 32 px; enlaces de los mensajes 16 → 32 px (relleno vertical en línea, sin mover las líneas); «Abrir en ClickUp» por mensaje y «Responder en un hilo» como iconos de 32 × 32 que aparecen al pasar el ratón (siempre en pantallas táctiles); `bt mini` de cabecera a 32 px.
- Vistas Todo / Sin leer / Menciones con `chipsFiltro` (contador rojo). Vacíos dentro de bloques con `vacioLinea`. Cifras con `fmt`.
- «Cómo saldrán tus mensajes…» plegado al pie (`<details class="panel">`); quitado el «—» de los datos si faltan.
- Arreglado en el móvil: la búsqueda y las menciones no se veían (la conversación estaba oculta sin canal); ahora salen con botón «volver».

**Revisión (n6_revisar, 7 personas × 1440/1024/390):** antes 21 pantallas con fallos (hasta 208 textos < 12 px y 8 clics < 24 px con Tomás); después 0 con fallos, 0 errores de consola, sin scroll horizontal. Capturas en `capturas/_n6/chat_equipo/`.

**Queda:** en el móvil la lista de canales es larga (como antes; 80 conversaciones de Tomás). Los emojis vienen de ClickUp y se respetan.
**Peticiones a E0:** ninguna obligatoria.
**Nota:** 7,5 → **9,3**/10 (falta un buscador de canales en la lista móvil y la burbuja de ayuda en los iconos ocultos).

## R16b (3-oct)
- «Añadir persona» solo con `puede_anadir === true` (y nunca en «ver como»); si el servidor contesta 403 al añadir, se refrescan los canales y el botón desaparece.
- Mensaje rechazado con 400 (sueldos): el motivo del servidor sale tal cual en una línea fija bajo la caja («No se ha enviado. Los sueldos no se escriben…», `role=alert`) y el texto se queda para corregirlo; la línea se borra al volver a escribir.
- `tapado.tapar()` tapa también «la contraseña de … es X» sin «:» (`RX_CLAVE_ES` + `parece_clave`, la misma que `servir.limpiar_texto`). `servir.py` sigue con su copia: **para el dueño de servir.py**, cambiar `RX_CLAVE_ES`/`_parece_clave` por `TAPADO.RX_CLAVE_ES`/`TAPADO.parece_clave` (con su copia como respaldo en el `except ImportError`); hoy aplicarla dos veces no cambia nada (`(?!••••)`). `--solo-tapar` sobre el espejo: 0 ficheros cambiados.

## Puesta al día 3-oct-2026
- **Avisos programados** (`avisos_programados.py`, 11 reglas) publican en los canales de avisos con **botones** en el mensaje (hasta 5, a una pantalla o a un enlace); `chat_equipo.js` los pinta y respeta los saltos de línea. Ver `_ESTADO_avisos.md`.
- **Puente de chat con ClickUp:** programado y apagado (`sincronia.py`). Ver `_ESTADO_sincronia.md`.
