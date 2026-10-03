# _ESTADO_ia · N3 · IA dentro de la app (2-oct-2026, noche)

## Qué hay
| Pieza | Fichero | Qué hace |
|---|---|---|
| Servicio común | `ia.py` (enganchado en `servir.py` con UNA edición antes de `main()`: `import ia; IA.enganchar(Manejador, …)`; sin el fichero, nada cambia) | Rutas `/api/ia/estado`, `/api/ia/lista`, `POST /api/ia/borrador {ticket, nuevo}`, `POST /api/ia/copiloto {cliente_id, nuevo}`. El navegador solo manda ids. El contexto se arma en el servidor con lo que ESA persona ve (P.ver `responder_cliente` para borradores, `cliente_detalle` para copiloto; `recortar_ficha`; cuota fuera si no la ve). Fuera sueldos, contraseñas (también «usuario: / contraseña:» dentro de los hilos), correos y teléfonos. Nunca envía nada. Rastro: `ia_borrador`, `ia_copiloto`, `ia_denegado` (solo servidor) e `ia_usar`, `ia_descartar` (navegador). Tope 40 generaciones/hora/persona. En «ver como», solo lo ya generado |
| Proveedor | `ia.py → llamar()` | Anthropic, `claude-opus-5` (`RO_IA_MODELO` lo cambia), SDK oficial `anthropic`, pensamiento adaptativo, salida JSON con esquema, `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) ante rechazos, errores con motivo legible. Clave: `ANTHROPIC_API_KEY` o llavero `anthropic_api_key` (nunca se imprime). **Hoy no hay clave ni paquete:** responde «IA sin conectar» y sirve lo precalculado |
| Instrucciones | `ia.py → SISTEMA_BORRADOR`, `SISTEMA_COPILOTO` | Destiladas de `redacta-mail-ro` (+ `voz-mail-tomas` si firma Tomás) y de `consejero-account-ro`, `diagnostico-embudo-despacho` y leyes de `criterio-tomas-ro` (solo como referencia) |
| Componentes | `modulos/ia_componentes.js` | `botonIA(ctx, { ticket, destino })`, `panelCopiloto(ctx, clienteId)`, `bloqueCopiloto(ctx)`, `iaDe(ctx)` (= lo que sería `ctx.ia`: `borrador(ticketId)`, `copiloto(id)`, `lista()`, `estado()`) |
| Pantalla | `modulos/asistente_ia.js` (`#/asistente-ia`, grupo Hoy) | «Qué haría hoy» (lista de clientes con color + diagnóstico de 3 líneas + 3 acciones con porqué, dato, quién, cuándo y «Ver la prueba») y «Borradores de correo» (quejas arriba). Dirección, operaciones, proyectos, jefas (todo) y account (lo suyo) |
| Hilos de Desk | `fuentes_ia/extraer_hilos.py` → `data/ia/_privado/hilos.json` | 40 correos más urgentes (quejas, rojo, horas; los de Lucía todos) con su hilo, solo lectura con `zh.py`, limpios |
| Precalculados | `fuentes_ia/precalcular.py` → `data/ia/_privado/{borradores,copiloto}.json` | `--volcar` el contexto exacto que usaría el servicio (como lo vería el account), `--cargar` lo redactado y validado, `--vivo` lo rehace todo con clave |
| Pruebas | `fuentes_ia/probar_ia.py` (23/23), `fuentes_ia/capturar_ia.py` (capturas + consola) | |

## Hecho hoy (precalculado, «Generado el 2-oct … Revisar antes de usar»)
- **40 borradores** de los correos más urgentes (8 quejas incluidas), firmados por el account del cliente; cada uno con «qué pedía el cliente y cómo queda» y los huecos a completar (125 en total, entre corchetes).
- **22 copilotos**: los 11 críticos + los 12 de Lucía (GAC en los dos). 15 rojo, 6 ámbar, 1 verde.
- Lo generé con Claude (subagentes con exactamente el contexto e instrucciones de `ia.py`).

## Comprobado
- `probar_ia.py` contra `servir.py` (copia de la base): Tomás ve 40 + 22; **Lucía 17 borradores y 12 copilotos, todos de su cartera; 403 en Musashi y en cualquier ticket ajeno**; Camilo, Sofía y Ana setter, 403; «ver como» sirve lo hecho y no genera; POST sin cabecera de la app, 403; el navegador no puede fingir `ia_borrador`; rastro con `ia_borrador`, `ia_denegado` y lo leído en «ver como»; ninguna respuesta lleva correos, teléfonos ni claves. Modo en vivo probado con un proveedor simulado (genera, guarda en `vivo_*.json`, enlaza la prueba).
- `capturar_ia.py`: tomas, mili, lucia, valeria, yessica, constanza y setter_ana a 1440 y 390 px: **0 errores de consola, sin desplazamiento horizontal**; setter_ana ve «no es de tu puesto». Componente con caja de respuesta: «Sugerir respuesta» → «Usar» rellena la caja. Capturas en `capturas/asistente_ia/`.
- `pruebas_seguridad.py`: TODO BIEN tras la edición de `servir.py`. `escaner_secretos.py`: limpio.

## Encontrado y arreglado
- **El hilo RO-4848 (Prodegest) traía usuario y contraseña FTP en claro** (los mandamos nosotros en junio). Se quitan ya en la extracción y otra vez en `ia.py`; el borrador recomienda cambiarla. **Que web (Macarena) cambie esa contraseña.**

## Para los dueños de Bandeja, Ficha y Mi día (una línea cada uno; no he tocado sus ficheros)
```js
import { botonIA, panelCopiloto, bloqueCopiloto } from './ia_componentes.js';
// Bandeja (bandeja.js, modo «responder», justo después de crear  const ta = h('textarea', { id: 'bdj-texto', … })):
botonIA(ctx, { ticket: x.numero, destino: ta })            // ponerlo encima de la etiqueta de la caja
// Ficha › Comunicación (por correo de la lista, o uno arriba con el más antiguo): sin destino → «Copiar» + «Contestar en la Bandeja»
botonIA(ctx, { ticket: x.numero })
// Ficha › Resumen:
z.append(panelCopiloto(ctx, F.c.id))
// Mi día del account (bloque):
bloqueCopiloto(ctx, { max: 5 })
```
Solo con `F.ve.responder` / `ctx.ver({ tipo: 'responder_cliente', … }).ok` para el botón: el servidor lo vuelve a comprobar igual.

## Lo que espera a Tomás
1. Clave de la API de Anthropic en el llavero (`security add-generic-password -s anthropic_api_key -w`) o en `ANTHROPIC_API_KEY`, y `pip install anthropic` donde corra el servidor. Con eso, «Otra versión» y cualquier cliente o ticket se generan al momento (`precalcular.py --vivo` rehace los 62).
2. Icono `asistente-ia: 'spark'` en `ICONO_MODULO` (E0, D-P-IA1).
3. Revisar los «tickets raros» que ya están contestados o no piden respuesta (RO-2734, RO-4848, RO-6625, RO-6753, RO-7187, RO-7725, RO-8000…): mejor cerrarlos en Desk que contestarlos.

## N6 · Diseño 10/10 · Asistente IA (`modulos/asistente_ia.js`, 2-oct noche) · nota que me pongo: **8,5 / 10**
- Sin hoja propia (fuera `asi-estilos`): lista de clientes y de correos con filas-botón en línea (tokens; la elegida en azul suave con filete), dos columnas que se apilan solas, carga con `esqueleto()`, «Ver propuestas / Ver borradores» en vez de «Ver», fecha «2 oct, 18:00».
- `pruebas_diseno.py` limpio en `asistente_ia.js`; 7 personas × 3 anchos sin errores. Capturas en `capturas/_n6/asistente_ia/`.
- Por qué no 10: `ia_componentes.js` (no es mío) sigue inyectando su hoja; la lista de 22 clientes no tiene buscador.

## N12 · IA en cada área (2-oct, 22:20) · «Qué haría yo hoy aquí» + «Qué hacer» ante errores
**Encargo de Tomás:** «que tenga detrás la IA pensando para recomendar en cada área y cada paso para que todo funcione perfecto, sugerencias cuando hay errores».

| Pieza | Fichero | Qué hace |
|---|---|---|
| Motor de reglas | `fuentes_consejos/motor_consejos.py` | Candidatos por persona: alertas N4 (31 tipos con su «qué hacer» en imperativo, cifra, umbral del catálogo, dueño, plazo, enlace a la prueba y «Lo tengo»), verdad única (bloqueo callado, fuga Meta → GoHighLevel), fuentes viejas o caídas por pantalla, conexiones de Ajustes y setters (solo sus recuentos). Agrupa por tipo («lo mismo en N clientes más») y corta a 3 |
| Precalculado | `fuentes_consejos/generar_consejos.py` → `data/consejos/p_<id>.json` | Las 32 personas activas, ~2 s. Paso para la tubería de C5 (apuntado en `../dudas_pintura.md`) |
| Servicio | `ia.py` → `GET /api/ia/consejo?pantalla=&cliente=` y `POST /api/ia/consejo` | Datos leídos con `leer_como()` por la MISMA puerta que `/api/modulo/*` (recorte de servir.py; sin denegados de ruido). Al servir, cada consejo se vuelve a filtrar: pantalla y módulo que ve, cliente que puede abrir, nada personal en «ver como», importes y cobros recortados, `limpiar()` (correos, teléfonos, credenciales), enlaces seguros. Sin clave: reglas. Con clave: POST, la IA (modelo vigente, `effort: low`, salida con esquema) solo reordena y redacta los MISMOS candidatos; un «ref» inventado o una cifra que no estaba se descartan; caché 3 h; tope 40/h por persona; rastro `ia_consejo`. Nunca en «ver como». **No hizo falta tocar `servir.py`**: el gancho de N3 ya atiende `/api/ia/*` |
| Pintura | `modulos/ia_componentes.js` (`bloqueConsejo`, `queHacerPara`, `enriquecerErrores`) + `carcasa.js` | Bloque «Qué haría yo hoy aquí» arriba de cada pantalla con consejos (1-3: qué, porqué, cifra · umbral, quién, cuándo, «Ver fuente ↗», «Ir», «Lo tengo» a la cola simulada de Alertas). Plegable (en el móvil, plegado de entrada; se recuerda). Si no hay nada útil, no se pinta. Sin hoja propia: clases `ia-*` de estilos.css |
| «Qué hacer» | `enriquecerErrores` + `vacioLinea(texto, { que_hacer })` (componentes.js, compatible) | A `vacioLinea`, `vacio`, `estadoVacio` y `tile`/`fichaIndicador` «Sin dato» que nombran una fuente caída, rota, vieja o sin conectar: «Meta caído desde las 21:05 · lo revisa Agus · mientras, cifras de las 18:05». Nunca si la fuente está bien ni en lo previsto («Todavía no», «Se mide desde») |

**Pruebas (servidor en 127.0.0.1:8990 con copia de local.db):** `probar_ia.py` 45/45 (465 consejos a 32 personas sin fugas, sin sueldos ni credenciales, account sin clientes ajenos, setter sin datos del otro setter ni leads, «ver como» sin lo personal, POST sin cabecera 403, `ia_consejo` no se puede fingir desde el navegador, IA simulada que reordena y descarta lo inventado, Meta caído); `pruebas_e0.py`, `pruebas_seguridad.py`: TODO BIEN; `pruebas_coherencia.py`: 0 errores; `escaner_secretos.py --proyecto`: limpio; `pruebas_diseno.py --estricto`: limpio. Navegador (`fuentes_consejos/capturar_consejos.py`): 8 personas × 2 pantallas × 1440/390, bloque arriba en las 30, 0 errores de consola, sin desplazamiento horizontal; capturas `.jpg` en `capturas/_n12/`.

**Pendiente de otros:** E0 añada `"ia_consejo"` a `rastro_solo_servidor` y el `que_hacer` de `vacioLinea` al LEEME; C5 meta el paso en la tubería y, si quiere, `data/conexiones/salud.json` (formato en dudas_pintura). Mi nota: **9 / 10** (falta probarlo con la clave real de Anthropic).

## V2-B · IA y consejos (3-oct-2026, madrugada) · «Qué haría yo hoy aquí» = lo que un buen jefe le diría a ESA persona en ESA pantalla
Ficheros: `fuentes_consejos/motor_consejos.py`, `fuentes_consejos/generar_consejos.py` (sin cambios de lógica), `fuentes_consejos/capturar_consejos.py`, `ia.py`, `modulos/ia_componentes.js`, `modulos/asistente_ia.js`, `ayudas.js` (solo «Contestar el correo más antiguo»), `fuentes_ia/probar_ia.py`, sección V2-B de `pruebas_coherencia.py`.

**Cómo decide ahora**
- **Filtro duro por dueño** (`ia.para_quien`): cada candidato lleva `dueno`. Si no es quien lee, no sale. Excepción: jefas (operaciones; jefa de publicidad → traffickers; jefa de CRM → especialistas GHL y outreach; jefe de SEO → SEO, ficha de Google y web) ven lo de su equipo como «Pide a X: …» con botón **«Avisar a X»** (acción `avisar`, cola simulada con rastro) y siempre detrás de lo suyo. **Dirección no recibe tareas de nadie** (ni de Mili ni de Sofía): solo lo suyo y lo que le escalan.
- **Prioridad por puesto** (`ia.PRIORIDAD`): account → crítico de la verdad única y correos > 48 h; técnico de altas → altas fuera de plazo; Tomás → decisiones con reloj (ahora también en Mi día), impagos de más de 60 días que decide él («Decide qué hacer con el impago de…», nunca «reclama»), luego ventas; Coti → «Da tu «Visto» al plan de X» (críticos de la verdad sin su visto en el rastro de 14 días); producción → devuelta, vencida más antigua, para hoy; ventas_ro → contrato sin firmar ≥ 3 días, reunión pasada sin resultado, propuesta sin abrir ≥ 72 h; outreach → respuestas por clasificar (la más antigua primero) y positivas sin dueño > 4 h. **Las horas nunca abren** (orden 20) y la cola de ClickUp de quien no es de producción va detrás de lo de su puesto.
- **Fuera el ruido**: «Ojo con las cifras de N fuentes» ya no ocupa un consejo; va a una chapa del sello («2 fuentes con retraso», detalle al pasar por encima; `r.retrasos`). Solo si una fuente CAÍDA/ROTA afecta al consejo, va dentro («Dato en duda: …»); con SE Ranking roto el consejo de SEO pasa a «Comprueba en Google las palabras de X antes de tocar nada».
- **Nada absurdo**: no se propone archivar la subcuenta de un alta de menos de 90 días (Garmande); «está en crítico» solo si la verdad única lo dice; el color del copiloto ES la gravedad de la verdad (`ia.color_verdad`: crítico/atención/bien; el de la IA queda en `color_ia`).
- **Producción, Prospección y Ventas de RO** con reglas propias (`de_produccion`, `de_outreach`, `de_ventas`, `de_visto`). Outreach y «Visto» se calculan al servir (dependen de la cola y del rastro).

**Hallazgos de mis ficheros**
| Hallazgo | Estado |
|---|---|
| 40_A A1 · copiloto marca «Rojo» clientes en atención | **Arreglado**: color = gravedad de la verdad; etiquetas «Crítico/Atención/Bien» en copiloto, lista y Asistente IA |
| 40_A A2 / 40_B M4 · horas como consejo n.º 1 (Lucía, Candela, Agus) | **Arreglado**: Lucía «Llama hoy a GAC: está en crítico», Candela «…Lobo…», Agus «Enciende la campaña de Laver…» |
| 40_A A3 · Coti con trabajo de Kimberlyn/Belén; Tomás con tareas de Mili/Sofía | **Arreglado**: Coti «Da tu «Visto»…»; Tomás «Contesta la decisión con reloj…», «Decide qué hacer con el impago…», ventas |
| 40_A M10 / 40_C 24 · dos bloques «Qué haría hoy» | **Arreglado**: el del copiloto solo al account y se llama «Tus clientes por gravedad · lo que propone la IA» |
| 40_A M11 · ⌘K abre otro correo que Mi día | **Arreglado**: misma regla que Bandeja/«Lo mío» (sin automáticos ni boletines, sin viejos, sin lo despachado; el de más horas). GAC → RO-6627 en los tres |
| 40_A M15 / M16 · consejo de frescura como único consejo (Coti en GAC, Sofía en la ficha) | **Arreglado** (va al sello). El botón «Visto» en la cabecera es de `en_rojo.js` |
| 40_A B2 · plazos con minuto raro y en fin de semana | **Arreglado**: «Hoy, antes de las 17:00», «El lunes 5», «vencía el vie 2» |
| 40_A B4 · «Lucía no imputó…» en su tarjeta | **Arreglado**: «No imputaste…» |
| 40_A B6 · «4 personas más: AyG Asesores…» | **Arreglado**: sustantivo por tipo (decisiones, clientes, piezas, contratos…) |
| 40_A B12 / 40_C 30 · sello sin día | **Arreglado**: «Reglas · datos del vie 2, 23:14» |
| 40_B M1 · aviso de fuentes en cada pantalla | **Arreglado** |
| 40_B M8 · consejo de SEO sobre SE Ranking en duda | **Arreglado** en el consejo; la cifra en gris es de `seo.js` |
| 40_B M9 · archivar subcuenta de Garmande | **Arreglado** |
| 40_B B1 / 40_C 22 · «Palabras clave clave» | **Arreglado** en el consejo (quita la palabra repetida); el nombre del catálogo es de `generar_catalogo.py` (dudas) |
| 40_B B2 · plurales en consejos | **Arreglado** en el motor («1 cita sin estado»); «(1 contactos)» viene del motivo de `generar_alertas.py` (dudas) |
| 40_C 4 · «null» del copiloto (Fitec, Concilia) | **Arreglado**: `replaceChildren(...filter(Boolean))` + `_sin_nulos` en el servidor |
| 40_C 5 / 15 · sin consejo en Producción, Prospección y Ventas de RO; consejos de otros | **Arreglado** (reglas propias + filtro por dueño) |
| 40_C 7 · el consejo no cambia con la pestaña de puesto de Jerónimo | **No aplica a mis ficheros**: la carcasa no manda el puesto elegido (dudas para E0/Mi día) |
| 40_C 11 · setter: «el más antiguo primero» y sin «Ir» | **Arreglado**: «el más nuevo primero» (como la lista) y «Ir a «Llamar ya»» / «Ir a «Confirmar»» que abren la pestaña |
| 39b · `RO-####` en texto plano en el asistente | **Arreglado**: diagnóstico, acciones, escalar, huecos y «qué pedía el cliente» con `conTickets` (en el copiloto, tamaño de botón) |
| 39b · «Contexto: 1 mensajes» | **Arreglado** |
| V2-C1 (b) · «Google Ads sin conectar · lo conecta Agus» | **Arreglado**: misma regla que `duenoConexion` (`motor_consejos.DUENOS_CONEXION`): «lo hace Tomás: pegar la clave de…; después Agus comprueba que llegan los datos» en el sello, «Qué hacer» y Ajustes; con prueba en `probar_ia.py` |

**Pruebas (servidor 127.0.0.1:9135 con copia de local.db):** `probar_ia.py` **91/91** (46 nuevas V2: primer consejo de Mi día de su puesto y dueño en las 10 personas, Tomás sin tareas de Mili/Sofía, «Pide a…» con «Avisar», sin ruido de fuentes, nada absurdo, Producción/Prospección/Ventas, setters, copiloto sin «null» y con la vara de la verdad). `pruebas_coherencia.py`: 0 errores (sección V2-B: «crítico» = verdad, subcuentas de altas, color del copiloto, ⌘K = Bandeja/Mi día). `pruebas_seguridad.py`: TODO BIEN. `escaner_secretos.py --proyecto`: limpio (renombrado `pestana.clave` → `pestana.sesion`). `pruebas_diseno.py --estricto`: 46/46 limpios. `pruebas_e0.py`: solo fallan las 2 de la setter y la verdad única (403 por el cambio de permisos de R16, no de este carril). Navegador (`capturar_consejos.py`): 13 personas × 25 pantallas × 1440/1024/390 = 77 cargas, 0 desbordes, 0 «null/undefined/NaN», 0 errores de consola (última pasada, 01:40); capturas `.jpg` en `capturas/_v2b/`.

**Nota que pondría ahora a la dimensión IA por puesto:** account 8,5 · técnico de altas 8,5 · dirección 8,5 · proyectos 8 · jefas (publicidad, CRM, SEO) 8 · producción 8 · ventas de RO 8,5 · outreach 8 · setters 8,5. Lo que falta para el 9,5: la clave de Anthropic (redacción en vivo), que la carcasa mande la pestaña de puesto y que Mi día no repita en «Lo mío» lo que ya dice el consejo.
