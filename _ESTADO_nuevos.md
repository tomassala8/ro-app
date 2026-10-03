# M12 · Clientes nuevos, de la firma al día 90 · estado (2-oct-2026)

**Ruta:** `#/clientes-nuevos` (lista) y `#/clientes-nuevos/<cliente>` (línea de tiempo del alta).
**Ficheros:** `modulos/nuevos.js`, `fuentes_nuevos/generar_nuevos.py` (+ `_crudo/`), `data/nuevos/nuevos.json`, `capturas/nuevos/`.
**Comunes tocados (edición localizada):** `modulos/indice.js` (entrada M12 → hecho), `reglas_permisos.json` (`datos_de_modulo["nuevos/nuevos"] = ["clientes-nuevos"]`), `LEEME.md` (línea M12), `../dudas_pintura.md`.

## Qué hace
- **Cifras** (recalculadas con las altas que recibe cada persona): altas encendidas en plazo (D-28), fuera de plazo, sin tareas a las 48 h, tareas vencidas, bloqueadas/no avanzan, arranques de la semana (tope 5), conexiones caídas de las 66 subcuentas.
- **Lo primero hoy** (máx. 7, una por alta y motivo) con «Escalar» a la cola simulada.
- **Altas en curso**: día X de 90 con marcas del día 10 y 12, cohete en el día de encendido, barra de % de tareas (hechas/vencidas/bloqueadas), hito siguiente con dueño, chips de filtro que se quedan.
- **Detalle**: cabecera (dueño Agus hasta el día 90, vigilante Mili, account, trafficker, CRM), 8 hitos (firma → accesos → taller → encendido → primer lead → reunión de resultados → día 30 garantía → día 90) con prueba, alertas, accesos (dado/falta/quién/desde, nunca la clave), casillas técnicas, línea de tiempo en 13 semanas (fecha real o propuesta D+N con borde discontinuo; «sin plazo» en gris), gasto/leads diarios de Meta, garantía, objetivo del alta (D-03, a la cola local) y fechas D+N del alta.
- **Pestañas**: accesos · casillas técnicas · conexiones caídas · talleres · bloqueos de Meta · garantía · contratos que vienen (Asecon 22-oct, Tax & Advise, Asefilco: no son clientes hasta firmar) · fechas automáticas (D+N, «se aplicará cuando haya escritura», W7).
- Alertas del punto 6 de Mili: tarea vencida · tarea que no avanza en su semana (en planning semanal/diario/en curso sin moverse 7 días, o con fecha de una semana pasada) · alta sin lista a las 48 h de la firma · bloqueo > 5 días (tiempo en estado de ClickUp) sin escalar.

## Datos (todo lectura, 2-oct 15:20-15:45)
Sign (`zh.py`, 23 sobres; el alta del contrato, el encargo art. 28 y la garantía salen del PDF) · ClickUp (`cu.py`, 12 listas «Onboarding —», 624 tareas) · Meta (`mt.py`, 74 cuentas; 5 altas con cuenta visible) · GHL (`app.py`, 66 subcuentas: calendarios, usuarios, WhatsApp 7 días, citas desde el alta) · DNS público (`dig`) · capa E1/E0 (web, emparejamientos, account, reuniones). Regenerar: `python3 fuentes_nuevos/generar_nuevos.py [--en-vivo]`.

## Lo que dicen los datos hoy
- 17 altas en ventana; **1 de 8** que llegan al día 12 encendida en plazo (Emex, día 9). Laver (día 14) y Deudout (día 16) encendidas tarde; Garmande, Lobo, Gestió Plural, Abner y CIB, pasado el día 12 sin encender.
- **Las 7 altas de octubre (Conficonsulting, IMFOR, Impulsa, Marlex, Think Value, TST, Billeo) no tienen ni carpeta ni tareas en ClickUp**; 5 ya pasan de 48 h desde la firma. IMFOR, Marlex y Think Value tampoco tienen subcuenta de GHL.
- RO no ve la cuenta de Meta de 12 de las 17 altas.
- 440 de 624 tareas de onboarding sin fecha límite: por eso la propuesta D+N.
- Solo Emex firmó la garantía de 2 reuniones en 30 días (ventana 18-sep → 18-oct).
- 3 subcuentas con calendario sin usuario (FBC, Gestymas, March de Luque); WhatsApp de RO 3 fallidos de 30 en 7 días.

## Cifras contrastadas con su fuente
1. Think Value: firma 1-oct 11:17 y alta 1-oct («Los servicios comienzan el 1 de octubre de 2026», PDF del sobre 52186000000213055 en Zoho Sign).
2. Emex: primer gasto en Meta el 18-sep (27,61 €, cuenta act_125546504832976) → encendido día 9 desde el alta del 9-sep.
3. Abner: 2 de 56 tareas completadas en «Onboarding — [Abner]» (lista 1200220000005767), consulta directa a ClickUp.

## Pruebas («hecho», sección 6)
- Consola sin errores propios con `?yo=tomas, mili, lucia, valeria, yessica, constanza, setter_ana` (y `agustina`). Solo sale el 404 de `modulos/informe.js` (módulo de otro agente aún sin fichero).
- Recorte en la respuesta de red (`/api/modulo/nuevos/nuevos`): Tomás, Mili, Valeria, Yessica, Constanza y Agus reciben 17 altas; **Lucía 0** (no lleva ninguna alta: estado vacío «Ninguno de tus clientes está en alta»); **setter_ana 403**. `gasto_*` desaparece para Yessica y Agus (no ven inversión).
- Capturas 1440 y 390 en `capturas/nuevos/` (las de 390 por iframe de 390 px reales; sin desplazamiento horizontal, `scrollWidth = 390`).
- `escaner_secretos.py`: limpio; el generador pasa el escáner antes de escribir y sanea correos y teléfonos de nombres de tareas.

## Falta / dudas
- W7: escribir las fechas D+N en ClickUp y crear la lista de onboarding al firmar (hoy solo cola simulada).
- Dominio verificado en Meta y calidad del píxel: piden leer el Business Manager del cliente (todavía no).
- Web y ficha de Google: sin registro en ninguna herramienta → «sin registro», se marcan a mano.
- Talleres agendados después del 1-oct no salen (ver `dudas_pintura.md`).
- Sesión de revisión con Coti, Mili y Agus (R15): pendiente.

## Ronda 2 (2-oct tarde) · estado del equipo de arranque
- **Fuente:** `fuentes_nuevos/estado_altas_manual_2026-10-02.json` (12 altas, tabla de Coti, Vale y Agus pegada por Tomás). Autor «equipo de arranque (Coti, Vale, Agus)», fecha 2-oct.
- **Hitos nuevos:** «Taller de oferta» (con fecha o «sin agendar», cruzado con el calendario de RO) y «Configuración básica» (declarada por el equipo; si no, la tarea «Reunión – Configuraciones Básicas» de ClickUp). Son 9 hitos en total.
- **Panel «Estado del equipo de arranque»** en cada alta: estado y próximo paso como texto del equipo, con autor y fecha, y al lado el cruce «el equipo dice / la app ve». También hay una pestaña «Equipo frente a la app» con las 12 altas y la columna «Configuración sin agendar».
- **Diferencias detectadas:**
  - Impulsa: «accesos completados», pero la app ve pendientes Meta, Analytics y otros.
  - Las 7 altas de octubre no tienen carpeta en ClickUp.
  - IMFOR, Marlex y Think Value no tienen subcuenta en GHL.
  - Conficonsulting, TST, Billeo e IMFOR: «accesos pedidos», pero sin tareas de accesos en ClickUp.
  - Gestió Plural y CIB: «subcuenta creada», y coincide con GHL.
  - Gestió Plural: «taller hecho 17-sep», pero no aparece en el calendario de RO.
- **CIB está marcado urgente:** sale arriba en la lista y es lo primero de «Lo primero hoy». Gestió Plural y CIB tienen la alerta «Configuración sin agendar y cliente sin responder» en «Lo primero hoy», y su alarma de día 12 lleva la causa declarada.
- **Formulario «Actualizar el estado del equipo»** en cada alta. Lo ven Coti, Agus, Vale, Mili y Tomás; en «ver como» no deja escribir. Guarda en la cola simulada (`acciones`, tipo `estado_alta`) con rastro.
  - La pantalla lo enseña al instante.
  - El generador lo recoge de `local.db` con su autor y la hora de Madrid. Si se guarda sin cambios, se mantiene el autor que había; si se vuelve al texto de la tabla, vuelve también su autor.
- **Prueba de punta a punta:** como Agus, guardé en Gestió Plural (acción n.º 14 con rastro, «Agus · 16:48»). Después lo deshice con la acción n.º 15, que devuelve el texto de la tabla. Las acciones no se borran.
- **Consola:** sin errores con tomas, mili, lucia, valeria, yessica, constanza y setter_ana. Lucía recibe 0 altas y la setter, 403. El escáner sale limpio.
- **Capturas:** `capturas/nuevos/r2_*` (1440 y 390).
- **Compatible con `ctx.verdad`:** el módulo no depende de él.

## Ronda 3 (2-oct noche) · arreglos de las auditorías

| Fallo de la auditoría | Qué se ha hecho |
|---|---|
| Cifras E-02: los leads se contaban dos veces (`lead` + `lead_grouped`; Emex 6 frente a 3 el 1-oct) | **Arreglado.** `leads_de()` usa la misma regla que Captación. Ahora Emex tiene 3 leads el 1-oct y 4 desde el alta, igual que Meta |
| Cifras E-19: el encendido contaba cualquier céntimo (Laver salía encendida el día 14 con 0,24 €) | **Arreglado.** El encendido es el primer día con 5 € o más, seguido de otros 2 días con gasto. Laver pasa al día 18 y sigue «tarde» |
| Calidad B-03 y experiencia: Emex salía «sin account» aquí y con account en En rojo | **Arreglado.** El account y el «sin account» salen de la verdad única, en el generador y en el módulo (`aplicarVerdad`). Emex sale «sin account · para confirmar» en todas las pantallas. Garmande ahora sale con Candela |
| Fuera de plazo con criterios distintos en cada pantalla | **Arreglado.** El estado de encendido sale de `verdad.encendido.estado`. El día de encendido lo sigue poniendo este módulo, porque es la fuente que lee la verdad |
| Calidad I-09: 17 frente a 16 nuevos | **No aplica aquí.** La verdad ya cuenta 17 a partir de esta lista; el 16 era de En rojo |
| «Lo primero hoy»: CIB y Gestió Plural salían dos veces | **Arreglado.** Una línea por cliente: la alerta más grave como titular y «También: …» con el resto. Escalar va por cliente |
| Arquitectura, parte C: faltaba el atajo a la subcuenta de GHL | **Arreglado.** «Abrir en GHL» (`app.gohighlevel.com/v2/location/{id}/dashboard`) en «Lo primero hoy», en la cabecera del alta, en el acceso al CRM y en la tabla de conexiones. Ya estaban ClickUp y Meta |
| Códigos de obra en pantalla (D-28, D-30, D-03, D-48, W1, W7, exigencia 32, regla del 9-sep, emoji del cohete, ⚠️) | **Arreglado.** Textos reescritos en lenguaje llano y el emoji cambiado por el icono del sistema. `tile`, `panel` y `avisoParcial` pasan además por `limpiaTexto` |
| «calendario(s)» y fechas en formato máquina en las alertas | **Arreglado.** Singular y plural bien escritos y fechas como «28 sept» |
| Alias «Vale» y «Jessi» | **Arreglado.** Ahora pone «Valeria» y «Yessica», como en `personas.json`; account, trafficker y CRM se pintan con `ctx.nombre()` |
| Pestañas cortadas a 1440 | **Arreglado.** Nombres cortos: Equipo · Accesos · Casillas · Conexiones · Talleres · Meta · Garantía · Por firmar · Fechas |
| Ventanas: WhatsApp contaba 7×24 h móviles | **Arreglado.** Son 7 días naturales cerrados, sin hoy, en hora de Madrid. GHL releído en vivo |
| Verdes falsos sin dato | **Arreglado.** «Tareas vencidas» y «Bloqueadas» salen en gris si no hay tareas |
| Zona horaria de Meta | **No aplica.** Los días de los informes de Meta ya vienen en la zona de cada cuenta (todas en Europa/Madrid). Las horas del formulario se pasan de la hora del servidor (UTC) a la de Madrid |
| Seguridad (27) | **No aplica.** El módulo no aparece en esa auditoría. El escáner sale limpio |

**Pruebas:**
- `pruebas_e0.py`: todo bien.
- `pruebas_coherencia.py`: `clientes-nuevos` está en ADOPTADOS y pasa. El único error que queda es de Agenda, que es de otro módulo.
- Consola sin errores con las 7 personas.
- Capturas en `capturas/nuevos/r3_*`.

## N6 · diseño 10/10 (2-oct)
**Qué cambié (solo `modulos/nuevos.js`, sin tocar datos ni permisos):**
- Fuera la hoja inyectada (`ESTILO` / `estilos()`, ~120 reglas `.m12-*`). Todo con clases comunes (`tile`, `panel`, `cuerpo`, `fila`, `ico-c`, `chip`, `densa`, `tabla-scroll`, `lista-i`, `detalle-cab`, `meta-linea`, `campo`, `menu-flot`) y `style` inline solo con tokens (`--t-*`, `--s-*`, `--r-*`, `--borde*`, colores de estado). `pruebas_diseno.py`: nuevos.js en «Limpios».
- Orden de la guía 3.6: «Lo primero hoy» arriba (4 visibles + «Ver todas (7)»; un botón principal, «Escalar» y un «Abrir en…» con ClickUp/GHL), luego 4 tarjetas sin huérfanas (en plazo, fuera de plazo, sin tareas a las 48 h, configuración sin agendar); las otras 4 (vencidas, bloqueadas, arranques de la semana, conexiones) pasan al panel semanal, encima de las pestañas.
- Filas de altas = `.tile` pulsable (borde, sombra y realce comunes) con 5 columnas que se pliegan solas (5 → 3 → 1); nombre del cliente que se parte en vez de desbordar, chips con «…» y burbuja; pista del día 30 y barra de tareas con style inline (left en %, `var(--good/--bad/--ink)`); 6 visibles + «Ver todas las altas (17)».
- Leyenda de la pista y de la barra a 12 px, con muestras de color, en el pie del panel. Nada por debajo de 12 px salvo cabeceras de tabla (11/700 mayúsculas, comunes).
- Línea de fuentes → un solo chip «Datos al día» que despliega las 5 frescuras. «Cómo se cuenta» y todas las notas de las pestañas, plegadas al pie (`<details>` de 32 px).
- Tablas: nombre del alta en tinta 13/600 y fila entera pulsable (tablaApilable `alPulsar`), no enlaces azules de 20 px; matrices de accesos y casillas con la tabla común `.densa` y puntos `.ico-c s`. Tablas largas recortadas (equipo 6, conexiones 8, fechas 5/8) con «Ver todas».
- Detalle: «Qué pide atención» arriba; sin migas (botón «Clientes nuevos» + selector); hitos en rejilla 9 → 6+3 → 3×3 con el siguiente resaltado; casillas 4 + «Ver todas»; semanas 3 + «Ver todas las semanas», 4 tareas por semana + «Ver las de esta semana». Gráfico de 13 semanas y de gasto/leads de Meta con `grafico()` (motor único). Formulario del equipo sin `<select>`: chips + `campoTexto()`; objetivo del alta con `campoTexto` numérico.
- Sin «—» sueltos (sin dato → texto), sin códigos ni nombres de fichero en pantalla.

**n6_revisar (7 personas × 1440/1024/390):** antes 9 de 12 pantallas con fallos (16 textos de 11 px, 11-12 objetivos de 20 px, 30 desbordes a 390); después 0 errores de consola, 0 textos < 12 px, 0 clics < 24 px, sin scroll horizontal; solo queda 1 «desborde» a 390 que es el `<thead>` oculto de tablaApilable (común). Detalle (emex, garmande, think-value) igual. Alto de página: lista 5.990 → 3.230 px a 1440 y **15.291 → 6.760 px en el móvil**; detalle Emex 8.473 → 4.951 (1440) y 15.537 → ~8.150 (390). Capturas en `capturas/_n6/nuevos/` (y `detalle_*`).
**Pruebas:** pruebas_diseno (limpio), pruebas_e0, pruebas_seguridad, pruebas_coherencia y escaner_secretos en verde.

**Queda / peticiones a E0** (en `../dudas_pintura.md`, D-P-N6-nuevos): `menuMas()` pinta «null» al cerrarse (por eso uso un `<details>` propio); `.dos` no pasa a una columna a 390 px (uso rejilla inline); `.bt.mini` y los chips de `chipsFiltro` miden ~28 px (bajo 32); la «ⓘ» de `tile` va en su propia línea; la barra de pestañas se corta a 1440 («Por firmar» con desplazamiento) — todo común.
**Nota que me pongo:** 6,0 → **8,5/10**. No llega a 9-10 por lo común de arriba (ⓘ en línea propia, botones mini de 28 px, pestañas que no caben) y porque el detalle sigue siendo largo en el móvil (~8.000 px: es una ficha de 90 días con 60 tareas).

## R12 · arreglos tras la auditoría final (carril E, 2-oct noche)
- **B-C02 «activa» en altas sin encender (Garmande, Lobo) → arreglado en mis datos y pantalla.** `meta.estado_cuenta` («cuenta activa») y `campana` ({encendida, texto: «campaña sin encender» / «encendida el día N»}) en el generador; la pantalla saca la campaña de la verdad única (`encendido`) y enseña los dos chips por separado. Mi día (otro carril) ya escribe «cuenta publicitaria activa · campaña …». Comprobado en `pruebas_coherencia.py`.

## V2-C1 (3-oct)
- **B-M5 · arreglado:** «Siguiente paso: encender la campaña» (verbo; nunca «Siguiente: Encendido»). Línea «Cómo cuadran las cifras: 17 altas… 8 ya pasaron su día 12: 1 se encendió en plazo y 7 están fuera de plazo… las otras 9 aún están dentro de su plazo. 16 de las 17 tienen algo pendiente». «Lo primero hoy»: «16 de las 17 altas tienen algo pendiente… (las 7 primeras)».
- **A-M4 13 % frente a 12 % · arreglado:** el generador redondea como la pantalla (1 de 8 = 13 %).
- **B-B4 · arreglado:** «28925 FBC EUROCONSULTING» → «FBC Euroconsulting».
