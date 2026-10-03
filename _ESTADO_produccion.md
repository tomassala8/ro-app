# _ESTADO · M10 Producción (E7) · 2-oct-2026

## Hecho
- `modulos/produccion.js` (+ `produccion_comun.js`, compartido con M11) · alta en `indice.js` (estado hecho) y `reglas_permisos.json → datos_de_modulo["produccion/produccion"]`.
- Datos: `fuentes_produccion/extraer_clickup.py` (ClickUp con la **llave propia** vía `cu.py`; 15.913 tareas abiertas o tocadas desde el 1-jun con historial de estados; 18.395 registros de tiempo desde el 1-abr; ~440 llamadas; nunca el conector) → `generar_produccion.py` → `data/produccion/produccion.json`. Reutiliza `tareas_flujo.json` y `planificacion.json` del panel y `fuentes_captacion/anuncios.json` (M6). No toca los ficheros del panel.
- Pestañas (orden por puesto): **Mi cola / Colas** (vencidas · hoy · semana · bloqueadas · esperando revisión · más adelante, por fecha y prioridad; tiles de devueltas, en fecha 30 d y a la primera; botones «A revisión» y «Avisar» simulados), **Revisiones 48 h** (del account, técnica y bloqueos del cliente; chips de antigüedad; «solo mis clientes» para accounts), **Por proyecto** (rev. >48 h, bloqueadas, no planificado ≥5 D-24, sin tareas del mes, vencidas, horas), **Carga del equipo** (solo quien puede comparar · D-83; cartera frente a 12/16 D-07; alfabético, sin ordenar por rendimiento; no planificado ≥3 por persona D-24), **Piezas en Meta** (índice frente a la media de la cuenta, sin euros · D-82; aviso «parcial: no consta quién hizo cada pieza» con la propuesta de iniciales D-43). Indicadores del catálogo con «¿Qué es?» y Fase 2 al pie.
- Recorte en servidor (probado por la API con `X-RO-Yo`): Lucía, su cola + 12 proyectos y 93 revisiones de su cartera; Camilo, solo su cola, 0 proyectos, 0 anuncios; Valeria, 6 colas (su gente) y todos los proyectos; Yessica 5 y Constanza 8 colas; Cecilia, colas de todos y 0 proyectos/revisiones/anuncios; setter_ana, 403. Sin claves de dinero en lo servido.

## Cifras contrastadas
1. GAC: 9 tareas en revisión del account, 4 de más de 48 h = `tareas_flujo.json` del panel (cu.py, 09:28). Revisión técnica 4 frente a 3 a las 09:28 (cambió durante el día).
2. Horas de GAC en octubre 7,5 h = ficha de E1 (`data/clientes/gac.json → horas.horas_mes`).
3. Horas de Camilo en septiembre 182,2 h = `por_persona_mes` de `_crudo/clickup/horas.json` (extracción independiente de cu.py). Igual Lina 104,6, Jerónimo 145,1, Gustavo 177,4.

## Pruebas
`fuentes_produccion/probar_equipo.py 8786` (Chrome sin cabeza): tomas, mili, lucia, valeria, yessica, constanza, setter_ana, camilo, cecilia a 1440 y 390 px y todas las pestañas: **0 errores de consola propios, 0 desbordes**. Capturas en `capturas/produccion/`. `escaner_secretos.py`: verde para este fichero (se limpian correos y teléfonos de los nombres de tarea).

## Falta / dudas (en `dudas_pintura.md`, D-P-E7)
- Rondas exactas: estado «corrección» (W7). Autor de las piezas: iniciales en los anuncios. Mover y comentar en ClickUp: W1 (hoy, cola simulada).
- Gates pendientes y ficha de marca del cliente junto a la tarea (bloques 5 y 6 del «Mi día» de producción): no hay fuente todavía.
- Revisión con Coti, Mili y Agus (R15): pendiente.
- Regenerar: `cd fuentes_produccion && python3 extraer_clickup.py && python3 generar_produccion.py && python3 ../fuentes_horas/generar_horas.py` (~25 min la extracción de tareas).

## Ronda de arreglos (2-oct noche) · fallo de la auditoría → qué se ha hecho
| Fallo | Origen | Estado |
|---|---|---|
| Página de 27.000 px y 1,4 MB, 460 filas sin paginar (nota 6,0) | 22 · I-08 | **Arreglado**: cola con 50 filas y «Ver 50 más»; las tablas de revisiones y proyectos usan la paginación común (50). JSON de 1,56 MB a 0,91 MB (sin URL repetida, sin campos sobrantes, compacto). Tomás: 4.000 px; Camilo: 1.650 px |
| Arriba salen tareas de 191 días | 22 · I-08 / 29 | **Arreglado**: revisiones abren en «Hasta 30 días»; las de más de 30 días van al chip «olvidadas». En la cola, las vencidas hace más de 30 días van a un grupo «Olvidadas» al final |
| «Bloqueos» 88 frente a 7 de En rojo | 22 · I-09 | **Arreglado**: misma regla que la verdad única («tareas en bloqueado»; «callado» si la más antigua pasa de 5 días, leído de `ctx.verdad`). `pruebas_coherencia.py`: producción en ADOPTADOS y en verde. El 7 de En rojo es otra regla (alarma de más de 2 días): nombre distinto |
| Account del proyecto de otra fuente | 28 / ronda 5 | **Arreglado**: account de la verdad única (`ctx.verdad(id).account`; el generador lee `data/verdad/clientes.json`) |
| Lucía abre en «Mi cola» y no en «Revisiones 48 h» | 29 | **Arreglado**: un account sin gente a cargo abre en Revisiones 48 h |
| «Ir» de Mi día no lleva a la tarea | 29 · F-03 | **Arreglado en Producción**: `#/produccion/<id de tarea>` abre la cola de su dueño en el grupo de la tarea y la señala. Falta que Mi día (`mi_dia_bloques.js`, no es mío) enlace a esa ruta |
| Emojis en los títulos de ClickUp | 29 · P-e | **Arreglado**: se quitan al generar; 🔴/🚨/‼ suben la tarea a urgente |
| Códigos internos en pantalla (D-xx, W1, ⭐, ficheros) | 29 / regla de textos | **Arreglado**: textos reescritos en llano |
| Atajo «Abrir en ClickUp» | 26 parte C | **Hecho** en cada tarea (cola, revisiones) y prueba de cada pieza |
| Ventanas: 30 días con el día en curso | regla 5 | **Arreglado**: 30 días naturales cerrados (hasta ayer) |
| Nombres en crudo | regla 2 | **Arreglado**: `ctx.nombre(id)` |
| Camilo tiene «Ficha del cliente» en el menú sin poder abrirla | 22 | **No aplica a este módulo** (entrada `ficha` de indice.js, de su dueño) |
| Contraste de contadores y altura de cabeceras ordenables | 29 | **No aplica**: estilos comunes (E0) |
| gzip en el servidor | 22 · I-08 | **No aplica**: servir.py (E0) |

Pruebas: `fuentes_produccion/probar_equipo.py 8786` (9 personas × 1440 y 390 × todas las pestañas: 0 errores, 0 desbordes), `pruebas_e0.py` y `pruebas_coherencia.py` (producción en verde; el error que queda es de Agenda). Capturas nuevas `capturas/produccion/r3_*`.

## Ronda 4 · guía de diseño (auditoría 30) y encargos del coordinador · 2-oct noche
- Fuera las hojas de estilos propias (`seo-estilos`, `cap-estilos`, `eq-estilos`): clases comunes (fila, pila, sub, chip, lista-i, rejilla, titulo-seccion) y estilo en línea solo con tokens (`var(--s-*, valor)`), nada por debajo de 12 px, cifras con punto de miles. Estado de fila = punto + texto en tinta. Línea de fuentes → un chip «Datos al día» que se despliega.
- Gráficos: `barras()` de `produccion_comun.js` usa ya el motor común `grafico()` de componentes.js; barras de progreso, embudo y ventanas, los comunes.
- SEO/web: pestaña Webs con columnas de Modular DS (Copia · Actualizaciones · Seguridad · Fuera de RO, con «bloqueada solo para RO»); hoy «Modular sin conectar» con el paso de Tomás (clave de solo lectura + pegar.sh). Camino conectado probado con datos simulados en el navegador.
- Horas: zona horaria de cada persona desde personas.json (Valeria hora de Venezuela, Sofía hora de España) en cabecera, listas, tabla y ficha.
- Producción: Camilo con la etiqueta «transversal» (copy, responde ante Mili), «sin cartera propia».
- Captación: Kiosko (tienda online) fuera de los leads de la casa (143 en vez de 1.562) y del techo de 35 € (4 de 8 en vez de 5 de 9), con nota en su tarjeta.
- Pruebas: 7 personas × 1440/390 × 7 rutas con todas las pestañas: 0 errores, 0 desbordes, 0 textos < 12 px · coherencia 0 errores · escáner limpio · pruebas_e0: 1 fallo ajeno (/api/cliente de Gustavo, «serie»).

## N6 · diseño 10/10 (2-oct, noche)
- **Rojo con cuentagotas** (`cuentagotas()` en produccion_comun.js): en Revisiones, Proyectos (bloqueadas), Cola (vencidas) y Carga del equipo (vencidas y «en fecha»), el rojo queda para el tercio peor; el resto, ámbar. Estado = punto de 8 px + texto en tinta (fuera el texto rojo/ámbar de «Vencida hace…»; «Bloqueada» en ámbar).
- Títulos de tarea en tinta 600 y fila entera clicable (ya venía; comprobado). Etiquetas de tarjeta de una línea: «Técnica > 48 h», «Bloqueadas (cliente)», «Revisión > 48 h», «No planificado», «Por encima del tope», «Con tareas vencidas»…; contextos cortos sin «ⓘ» suelta.
- Buscador de las tablas a 280 px (`ancharBuscador()`); en el móvil, todo el ancho.
- Cola: 8 tarjetas → 4 (Vencidas · Para hoy · Bloqueadas · En fecha 30 días con «a la primera» y devueltas en el contexto); 20 filas y «Ver más» (10 en el móvil); fuera el hueco vacío arriba en las colas de una sola persona y el chip «Transversal» repetido.
- Tablas a 15 filas (8 en el móvil); vacíos dentro de bloque con `vacioLinea()`.
- Periodo: **no usa `usa_periodo`**. Es la foto de ClickUp de ahora y los porcentajes son de los últimos 30 días (ventana fija); lo dice una línea bajo «Datos al día».
- Medidas: Tomás 390 px de 12.464 → 5.089 px (Revisiones), 3.624 al abrir; Camilo 11.540 → 3.576; Lucía 11.468 → 4.273. 7 personas × 1440/1024/390: 0 errores, 0 scroll horizontal, 0 textos < 12 px, 0 «null». Capturas en `capturas/_n6/produccion/` (antes en `capturas/_n6/_antes/produccion/`).
- Nota contra la auditoría 30: **5,5 → 8,5**. Falta para el 9-10: la cola en el móvil sigue siendo una lista de tarjetas altas (botones en su propia fila) y las tarjetas en el móvil son el carrusel común, que corta la segunda.
- **N6 · segunda pasada:** cola en el móvil con filas compactas de 2 líneas (título-enlace a ClickUp + su acción; línea meta con punto y plazo · cliente · estado) y 15 a la vista. Camilo 390 px: 3.161 px; Tomás (Colas): 2.969. n6_cap 42 pantallas, 0 con problemas; pruebas_diseno limpio. **Nota: 9,0.**

## R12 · arreglos tras la auditoría final (carril E, 2-oct noche)
- **C · M5 «tres cifras de mi cola» → arreglado.** Una definición: «tu cola ahora» = vencidas + para hoy + esta semana + bloqueadas (`GRUPOS_AHORA`, en `produccion_comun.js` y en `definiciones.cola_ahora` del generador; Mi día usa la misma lista). `personas[].vencidas` = solo el grupo «vencida» (antes contaba cualquier fecha pasada, también lo que espera revisión: 63 → 3 en Camilo); nuevos `cola_ahora` y `fecha_pasada_todas`. En Producción el chip por defecto es «Ahora 16» con la frase «la misma cifra que en Mi día» y lo demás aparte («Todo 126»). La pestaña «Mi cola» cuenta 3 vencidas, como Mi día. «Tareas vencidas» por proyecto pasa a «Con fecha pasada» (otra base, dicha).
- **Botones < 32 px en móvil → arreglado:** el título de cada tarea mide 32 px de alto a 390.
- **Seguridad (barrido) → arreglado:** los títulos de tarea pasan por `permisos.sin_importes` en el generador (`limpiar_tarea`): «localizar factura junio 2026 (344,85 €)» → sin la cifra y sin «[importe]».
- **Cliente de cada tarea (pedido de Mi día) → hecho:** `cola[].cliente` lleva el nombre de la verdad única cuando hay `cli`.
- **A2 periodo → no aplica:** ClickUp es una foto de ahora; ya lo dice una línea llana arriba.
- Comprobado en `pruebas_coherencia.py` (sección carril E).

## R14 · dos arreglos de 43_IDEAS_MEJORA (F5 y B2) · 2-oct noche
- **Un solo sello de frescura (F5).** `lineaFuentes()` (produccion_comun.js) ya no dice «Datos al día» si no lo está: cada fuente lleva su hora real y su límite de horas (el mismo de `data/fuentes.json` que usan los consejos y la cabecera); cerrado dice «Colas 15:29 · Revisiones y proyectos 09:16 · Horas 15:52 · Anuncios de Meta 17:32» y, si alguna pasa su límite, «N fuentes con retraso» con cuánto hace y quién la pone al día (Mili, «Actualizar ahora»). El generador escribe `nombre` y `limite_h` en `fuentes` (el JS tiene los mismos por defecto). La línea «Foto de ClickUp…» y la hora de preparación van dentro del sello. Horas usa el mismo sello con sus límites. El consejo «Ojo con las cifras de Tareas de ClickUp» ya no sale en Producción (`motor_consejos.FUENTES_DE_PANTALLA` sin `produccion`; consejos regenerados): lo dice el sello.
- **Pestaña «Por revisar» (B2, en simulación).** Junta las piezas que esperan revisión (grupo «Esperando revisión» de las colas + revisiones del flujo por cliente, sin repetir), agrupadas por cliente o por quién revisa, las más antiguas arriba, 5 por grupo con «Ver más»; las de más de 30 días aparte («olvidadas»). Chips: Me toca revisar · Mis piezas · Toda la revisión interna · Esperando al cliente. «Aprobar» (confirmación) y «Pedir cambios» (con qué cambiar, obligatorio) → `ctx.accion` tipos `pieza_aprobar` / `pieza_pedir_cambios` en la cola «acciones» en SIMULACIÓN, con rastro; texto llano «Se aplicará en ClickUp cuando Tomás lo active». Las ya apuntadas (de `/api/acciones?modulo=produccion`) salen sin botones con quién las decidió.
- **Reglas:** `reglas_permisos.json` → `acciones_permitidas.produccion` y `revision_piezas` (quién revisa cada estado; `siempre` = dirección y operaciones; nadie se aprueba a sí mismo; lo que espera al cliente no se aprueba). `servir.py` (`pieza_en_revision`, `puede_revisar_pieza`) lo comprueba al recibir la acción y saca la pieza y su cliente de produccion.json, nunca del navegador.
- **Pruebas:** `pruebas_seguridad.py` casos «R14» (12); N15 ya no cuenta las acciones de pieza como mensajes a ClickUp. Navegador (127.0.0.1:9055, copia de local.db): camilo, manuel, mili, constanza, lucia, tomas, cecilia × 1440/390: 0 errores, 0 desbordes, sin «Ojo con las cifras»; Mili pide cambios (vacío avisa) y aprueba. Capturas en `capturas/_produccion_r14/`.
- **Decide Tomás (B2):** escribir en ClickUp y quién aprueba qué (hoy: account del cliente, jefa del área en la técnica, Mili y Tomás en todas). El estado al que pasaría cada pieza (`revision_piezas.por_estado.*.a`) es propuesta.

## V2 · carril V2-C2 (3-oct)
- **B-11 / C-6 «Para hoy» con vencidas → arreglado.** `produccion_comun.js › alDia(D, hoy)`: reagrupa con el hoy real y la regla del generador, y recalcula las cifras de cada persona; «Para hoy» cuenta las filas (sin vencidas) y aviso «Las tareas son de ClickUp del vie 2…». Contador del menú: pedido a R16/E0.
- **R16 / B-A1 revisión técnica por área → arreglado.** `areas_tecnica`: Jerónimo pasa de 97 a 33 piezas «Me toca»; sin «Aprobar / Pedir cambios» en piezas de otra área; el revisor dice el área («Revisión técnica · Jefe de SEO»).
- **A-A5 revisiones de Lucía → arreglado.** `revisionesDelAccount()` (la regla de Mi día): pestaña y tarjeta «Tus revisiones > 48 h · 42 de 67»; la otra se llama «Toda la revisión interna > 48 h».
- **C-17** «Bloqueadas» dice cuántas esperan al cliente y cuántas son internas · «A la primera en 30 días: 100 % de 33 · 1 devuelta en la cola ahora» · jerga fuera (plan de la semana, plan del mes, próxima tanda, pendiente sin fecha). «Gates/skills» vienen en el nombre de la tarea de ClickUp: no aplica.
- **C-26** pestañas en una fila con «Más (n)» · **C-27** Camilo en segunda persona («Escribes para varias áreas…»).
- **Barrido v1 #8** título de tarea con zona de toque de 32 px.
- **C-5** «Qué haría» sin reglas de producción: de `ia.py` (dudas V2).
