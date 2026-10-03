# M1 · Mi día — estado (2-oct-2026)

## Hecho
- `modulos/mi_dia.js` (orquestador y pintura) + `modulos/mi_dia_bloques.js` (113 bloques y 19 cálculos de «el número que manda»). Ruta `#/mi-dia` (puesto principal) y `#/mi-dia/<puesto>`. Quien tiene varios puestos (Tomás, Coti, Valeria, Yessica, Agus, Jero…) cambia con chips.
- No recalcula nada: cada bloque lee el fichero que su módulo ya sirve recortado (`ctx.datosModulo`). Si la persona no ve ese módulo, no se pide (sin 403 de ruido) y el bloque lo dice; si el dato no existe, «Llega con <módulo>» y se pinta solo cuando exista.
- Arriba: saludo, **el número que manda** (catálogo de E0: nombre, umbral, sello, frescura, «¿Qué es?»; «Va a Fase 2» si el catálogo dice «todavía no», con el dato de apoyo si hay) y **Lo primero hoy** (máx. 3, lo más grave arriba, «Ir» + «Lo he pedido»).
- Petición 19: lo marcado «Pedido» (cola `acciones`, modulo `mi-dia`) que a las 48 h sigue saliendo en el dato vuelve arriba con «Toca escalarlo»; si ya no sale, se cuenta como resuelto con el dato del día.
- Petición 1: avisos de fuentes caídas (`/api/avisos`, tope 3 al día) entran en Lo primero de Tomás y Mili. Petición 8: cuota recurrente y «si firman los pendientes» en Captación de RO (Tomás). Petición 13/«cambios»: `data/mi_dia/cambios.json` (solo dirección), sin IA. Petición 20: mapa de control por persona (de `incidencias.control`) en el día de Mili. Ronda de Mili (`rol_mili.json`) con «Hecho» que queda en el rastro. «Mi día más visual»: tiles de todos los bloques arriba.
- Configuración por puesto: `data/mi_dia/config.json` (21 puestos × 7 bloques, en el orden de las fichas G1-G3; catálogo de bloques con título, icono, ruta, frecuencia y alcance). Se edita sin tocar código.
- Datos propios: `fuentes_mi_dia/generar_mi_dia.py` → `data/mi_dia/cambios.json` (`puestos: [direccion]`) y `ronda_mili.json` (`puestos: [operaciones, direccion]`), dados de alta en `reglas_permisos.json`.
- Alta en `modulos/indice.js` (estado hecho). Línea en el LEEME.

## Pruebas (`fuentes_mi_dia/capturar_mi_dia.py`, servir.py en 8786, Chrome sin cabeza)
- 21 puestos con «ver como» (persona real de cada uno; setters con setter_ana) a 1440 y 390 px: 7 bloques en todos, 0 rotos, 0 desbordes horizontales, 0 errores de consola de Mi día. Capturas en `capturas/mi_dia/<puesto>_<persona>_<ancho>.png` y resumen en `capturas/mi_dia/_prueba.json`.
- Entrada propia (`?yo=`) de tomas, mili, lucia, valeria, yessica, constanza y setter_ana: sin errores. Recorte comprobado en servidor: `mi_dia/cambios` da 403 a Lucía; la ronda solo llega a Mili y Tomás.
- `escaner_secretos.py`: limpio.

## Cifras contrastadas con su fuente
1. Lucía, número que manda: 10 de 12 clientes de su cartera con salud ≥ 60 (83 %) = `asignaciones.json` + `clientes.json`.
2. Sofía, conciliación: 529 movimientos sin conciliar = `finanzas.json → admin.caja.sin_conciliar_total` (Holded).
3. Tomás (ventas de RO), cierre sobre celebradas de septiembre: 13 de 103 (13 %) = `ventas_ro.json → meses.2026-09`.
4. Coti (jefa de SEO): 10 de 41 clientes de SEO en verde (24 %) = `seo.json → resumen`.

## Falta / dudas (detalle en `dudas_pintura.md`, D-P-MID)
- **Ruta de inicio**: pedida a E0 (`app.js`): `mi-dia` antes que `en-rojo`. Hoy se aterriza en En rojo.
- Nota de cumplimiento 0-100 del account: no existe fórmula; el bloque enseña regla a regla (control de M14) con sello «a medias».
- Bloques «pendientes» (no medibles hoy, explicados en pantalla con quién lo arregla): flujos con error y rebotes (W3), reseñas y fichas de Google (W7), fábrica de anuncios, gates, aprobaciones de Coti, rentabilidad por servicio, quincenales, paquete de validación, contenidos frente a plan, cosecha.
- «Lo que ha cambiado desde ayer» compara cliente a cliente desde mañana (hoy solo hay una foto diaria); hoy resume los datos de ayer de cada módulo. Conviene meter `generar_mi_dia.py` en `recarga.json`.
- Sofía no recibe el importe de Meta sin factura (recorte de `gasto*`): pedido a E0.

## Ronda de arreglos (2-oct noche) · fallo de la auditoría → qué se ha hecho
| Fallo (origen) | Estado |
|---|---|
| F-03 (29) · los «Ir» llevan al módulo y no a la cosa | **Arreglado.** Rutas profundas en todos los bloques: `#/bandeja/<ticket>`, `#/ficha/<cliente>/<pestaña>`, `#/clientes-nuevos/<cliente>`, `#/captacion/<cliente>` (y `~trafficker/<persona>`), `#/salud-crm/<subcuenta>`, `#/seo-web/<cliente>`, `#/redes/<cliente>`, `#/incidencias/<id>`, `#/produccion/<tarea>`, `#/decisiones/reloj`, `#/ajustes/avisos`. Las alarmas «Sin responder» abren el correo más viejo de ese cliente. Lucía, «contestar su correo más viejo»: Mi día (inicio) → «Ir» → correo abierto con «Contestar» = **2 clics** (probado en el navegador con Adade, RO-3940). Quedan a nivel de pantalla solo «meses de caja» (Finanzas no tiene detalle) y «persona en alerta» (Personas no tiene ruta por persona) |
| F-01 (29) · beneficio −7.349 € en Mi día y otro en Finanzas | **Arreglado.** Sale de `data/finanzas/direccion.json → direccion[0].numero` (el mismo campo que Finanzas): «Beneficio de agosto 3.860 €», y debajo «−3.428 € contando el gasto sin factura». Euros siempre con separador de miles |
| Cuota con etiqueta exacta | **Arreglado.** «Cuota firmada» (recurrente), «Cuota cobrada X de Y facturada»; nunca se suman |
| Móvil: «Lo primero hoy» antes que las cifras; tarjetas compactas | **Arreglado.** Lo primero va primero en el DOM (en escritorio sigue a la derecha); en ≤ 640 px se quita la tira de tiles, el motivo se corta a 2 líneas y cada bloque enseña 3 filas |
| Textos con códigos (D-xx, W3, «panel v27», «(M21)», «data/mi_dia/config.json») | **Arreglado.** `limpiaTexto()` en motivo, filas, vacíos, número que manda y Lo primero; frases reescritas donde quitar el código las rompía; la referencia técnica solo en «¿De dónde sale?» plegado para Dirección. La prueba busca códigos en pantalla: 0 |
| «Lo he pedido» no se entiende (P-b) | **Arreglado.** «Ya lo he pedido» oculta el elemento un día; si a las 48 h sigue en el dato, vuelve con «Toca escalarlo» |
| «Releer» y «Actualizar ahora» duplican (P-c) | **Arreglado.** Fuera «Releer» |
| Letra de 9,5 px y contraste del «CADA DÍA» | **Arreglado.** Mínimo 12 px (11 px solo en mayúsculas espaciadas) y gris oscuro |
| «Empezáis el lunes 5-oct» (P-g) | **Arreglado.** «Empezamos el lunes 5 de octubre» |
| Mi día como inicio (P-12) | Ya hecho por E0 (`app.js`); comprobado: las 7 personas aterrizan en `#/mi-dia` |
| Verdad única (ronda) | **Adoptada**: responsable (`verdad.account` + `ctx.nombre`), encendido (altas fuera de plazo y número que manda de Mili y Agus), sin reunión, bloqueo callado; «no imputaron ayer» de `verdad/equipo.json` en el día de Mili. `mi-dia` en ADOPTADOS de `pruebas_coherencia.py` con su comprobación (altas fuera de plazo de «cambios desde ayer» = verdad): pasa |
| «Abrir en …» por elemento (26 parte C) | **Arreglado.** Icono «Abrir en Desk / ClickUp / Meta / la web / Holded / GoHighLevel» en cada fila que tiene enlace de origen; el nombre se deduce del enlace |
| Sin dato = gris | **Arreglado.** Un bloque sin cifra ni filas sale gris «sin dato», nunca verde |
| `generar_mi_dia.py` en «Actualizar ahora» | **Hecho** (edición localizada en `recarga.json`, último paso) |
| Mili «qué account no imputó ayer» (29) | **Arreglado**: primera fila de «El equipo, día a día» |
| Seguridad (27): `mi_dia/cambios` con `?yo=mili&como=tomas` → 200 | No aplica a Mi día: es la regla común de «ver como» (E0, ronda 6) |
| Duplicados en Lo primero (correo y alarma del mismo cliente) | **Arreglado**: se agrupan |

Pruebas de esta ronda: `capturar_mi_dia.py` (21 puestos × 1440/390, capturas `capturas/mi_dia/r3_*`, 0 problemas, 0 códigos a la vista) · `pruebas_e0.py`: TODO BIEN · `pruebas_coherencia.py`: 0 errores y 0 avisos · escáner de secretos limpio · 7 personas sin errores de consola.

## Ronda 2-oct noche (19:00) · alertas, IA, celebraciones, correos, dinero y guía 30 (Mi día + Incidencias)
- **Mis alertas** (N4) en Mi día: bloque `mi_dia` de `data/alertas/p_<id>.json` (máx. 5) con «Lo tengo · Resuelta · No aplica» (motivo obligatorio). Las acciones van con `modulo: 'alertas'` y tipos `alerta_*`, así se ven igual en Alertas y paran el escalado. Sin alertas y sin pantalla de Alertas (setter): no se pinta.
- **Incidencias**: panel «Alertas de web y SEO» (las que la persona ve: suyas, su departamento si es jefe; Mili y Tomás todas), 10 visibles, mismos botones. Tabla de incidencias a 15 filas + «Ver más».
- **Copiloto de IA**: `bloqueCopiloto(ctx, { max: 5 })` para quien ve Asistente IA.
- **Cumpleaños y aniversarios**: `ctx.celebraciones({ dias: 14 })`, para todo el equipo; si no hay, no sale.
- **Correos sin contestar**: de `data/bandeja/por_cliente.json` (regla de la Bandeja, días laborables); la alarma «Sin responder» de las 07:00 ya no cuenta en Mi día. Las esperas se dicen en días laborables.
- **Dinero**: beneficio de agosto 3.859,87 €, enero-agosto 93.492 € (`direccion[0].anio.bai`), y las tres cifras de cuota de `finanzas.json → admin.cuota_tres` (67.291 / 70.781 / 70.581 €). Si el servidor quita `cuota_*`, no salen filas.
- **Arreglado**: «Ya lo he pedido» / «Ya lo he escalado» daban 400 (tipos `pedido`/`escalado` fuera de la lista): ahora `avisar`/`escalar` (se leen también los antiguos).
- **Guía 30**: fuera la hoja propia de Mi día (`mid-estilos`) y la tira de tarjetas repetida; saludo en la cabecera común; bloques como `panel` + `lista-i` + `chip`; número que manda con `fichaIndicador`; mapa de control con `table.densa`; pistas con `barra-prog`; «Ir» → «Abrir correo / tarea / cliente…». Queda solo `mid-maqueta` (rejillas). Incidencias: hoja reducida a maquetación (sin tamaños de letra, hex, sombras ni radios con número; nada < 12 px).
- **Pruebas** (servir.py en 127.0.0.1:8843 con copia de la base, cerrado): 7 personas × 1440/390 en Mi día e Incidencias sin errores de consola ni desplazamiento horizontal, 0 textos < 12 px; `capturar_mi_dia.py` (selectores actualizados): 40 de 42 bien, los 2 «malos» son setters (E0 les quitó Mi día: aterrizan en `#/setters`). `pruebas_coherencia.py` 0 errores; `pruebas_e0.py` 1 fallo ajeno (Gustavo abre accompany y le llega «serie»: recorte de cliente/ficha); escáner limpio.

## N6 · Diseño 10/10 (2-oct, noche) · nota que me pongo: **8,5 / 10** (auditoría 30: 6,0)
- Sin hoja propia: fuera `mid-maqueta`; las rejillas van en línea con tokens (`repeat(auto-fit, minmax(min(100%, 420px), 1fr))`) y, si quedan impares, el último panel ocupa la fila entera (sin huérfanas).
- «El número que manda» con `cifraPrincipal()` (32 px) y su color por la regla única: `colorCifra('beneficio')` (beneficio positivo = verde, también en «Finanzas de dirección» y la serie mensual). Coste por cliente y coste por lead, con `colorCifra('coste_cliente' | 'coste_lead')`. Euros con `fmt.eur` («3.859,87 €», «−3.428 €»).
- Cuota de la empresa: `ctx.cuotaEmpresa()` primero; el fichero de Finanzas solo de respaldo.
- Pie de cada bloque con `panel({ pie, verTodo })`; vacíos dentro de bloque con `vacioLinea()`; carga con `esqueleto()`; «Mis alertas» con los botones debajo del texto. Fuera «prueba: null» y «undefined · 14 subcuentas» (Mili, Yessica).
- Pruebas: `pruebas_diseno.py` limpio en `mi_dia.js` y `mi_dia_bloques.js`; 7 personas × 1.440/1.024/390 sin errores de consola, sin scroll horizontal y sin texto < 12 px. Capturas en `capturas/_n6/mi_dia/`.
- Por qué no 10: los «¿Qué es?» siguen siendo `summary` (la ⓘ de 32 px es común), y el móvil sigue siendo largo (todos los bloques del puesto).

## Ronda 12 (2-oct, noche) · arreglos tras la auditoría final · UNA SOLA VERDAD
| Hallazgo | Estado |
|---|---|
| A-C1 · salud del account con la fórmula vieja (GAC 35 frente a 62; Lobo y Garmande «sanos») | **Arreglado.** Número que manda, «Tus clientes» y semáforo de Coti leen `verdad.salud` y `verdad.gravedad` (lo mismo que la ficha). Lucía: 12 de 12 (100 %) y «GAC · crítico · salud 62»; Candela: Lobo y Garmande en crítico arriba, y el número lo dice («en crítico aunque la salud pase de 60»). «Tus clientes» pasa a lista legible (estado · salud · motivo de la verdad), sin las tarjetas de una letra por línea |
| A-A3 · el account no ve primero los resultados | **Arreglado.** `config.puestos.account.arriba = resultados_mios`: «Resultados de tus despachos» va en la primera fila (leads 7 días con comparación, leads de ayer, por cliente: leads, citas 7 d, coste por lead si lo ve y ventas marcadas; lo que está en rojo arriba; cuántos de su cartera no tienen Meta). La salud (número que manda) va después |
| A-A4 · contadores que se contradicen | **Arreglado.** Fuera el bloque de alarmas de las 07:00 del account (urgencias = las de Alertas, «Mis alertas»); «Lo primero hoy» ya no da un total propio («Las 3 más graves de hoy»). Bandeja = regla de la pantalla Bandeja (sin automáticos, viejos ni lo ya en cola): 13, igual que la Bandeja, con Desk y Zadarma por separado (hace 16 h / 15 h). «Tu cumplimiento» cuenta contesta, revisa y reuniones con las mismas funciones que Bandeja, Trabajo y Reuniones (13 de 21 · 42 de 67 · 2). El mapa de control de Incidencias sigue con su cálculo: apuntado en `dudas_pintura.md` (R12) |
| A-A5 · número que manda de Coti «—» | **Arreglado.** Un número sin cifra dice «Sin dato» y el porqué (1 alta con garantía firmada que aún no ha llegado al día 30; la cifra sale ese día). Vale para todos los puestos (Camilo tampoco ve «—») |
| B-C01 · Laver «día 31 sin encender» y «encendida tarde» | **Arreglado.** `arranqueV()` lee `verdad.encendido`: solo «sin encender» si `sin_encender_fuera_de_plazo` (Garmande, Lobo…); Laver sale «encendida tarde, el día 18». También en «Arranques en curso» y «Bloqueos de Meta»: «cuenta publicitaria activa · campaña sin encender» (B-C02) |
| B-A02 · «[importe]» en el urgente de Lina y Valeria | **Arreglado en Mi día** (el hueco viene del servidor: apuntado a E0 en `dudas_pintura.md`). La frase va sin cifra y la cifra aparte de lo que sí recibe: «Coste por lead (7 días), 2,5 veces el techo · 87,70 € por lead · techo 35 €». `L()` quita cualquier «[importe]» que quede; la acción guardada tampoco lo lleva |
| B-A04 · cartera de Lina con cuatro tamaños | **Arreglado en Mi día.** Por trafficker y Carga = asignaciones vigentes (`verdad.equipo.trafficker`, como Personas): Lina 21, Valeria 19, «Sin trafficker asignado» en vez de «persona sin ficha». Los bloques de la trafficker usan `ctx.carteraPorSilla.trafficker` («tu cartera: 21 cuentas») |
| B-A05 · número de SEO distinto de su pantalla | **Arreglado.** Misma base (medibles: 1 de 38), umbral «bien desde el 80 % · mal bajo el 60 %», color y sello «a medias» que «Clientes en verde» de SEO, ficha y webs |
| B-A06 · «top 5 −43» sin aviso | **Arreglado.** Top 5 con la base y la regla de su pantalla (sus clientes por asignación, rojo solo si cae más de 2) y el aviso de SE Ranking («dejó de ver N palabras de golpe… la caída puede no ser real»); «clics — %» → «clics: sin Search Console» |
| B-M06 · Agus con bloques de account | **Arreglado.** Un puesto de account sin clientes en esa silla no sale como día propio si hay otro puesto; las alarmas de persona de account (revisión del account, informes, semáforo, semanal) no entran en «Lo primero hoy» de quien ya no lleva clientes |
| C-M2 · Mi día de web con las 64 webs | **Arreglado.** Bloques de web con `alcance: mio` = webs de su cartera de web y SEO (asignaciones): Macarena 26; las caídas del resto de la casa, en una fila «Guardia». El «Mientras» del número también es sobre sus webs. Musashi: «spam en la portada, con campaña» |
| C-M4 · tareas con «—» en vez de cliente | **Arreglado.** Nombre del cliente desde `cli` (Concilia, Sol-4, ECIJA…); sin cliente, «sin cliente». Pedido a Producción que rellene `cola[].cliente` |
| C-A2 · número que manda de Redes sobre 4 de 25 | **Arreglado.** Sobre la cartera de redes de las asignaciones: «0 de 14 con calendario en Metricool» y dice que 11 de sus 25 no están en Metricool (con nombres); en «Huecos» también |
| Textos rotos | **Arreglado.** «llega con .» → «llega cuando se conecte WhatsApp Business, no antes del 16 de octubre»; «1 cosas» → «1 cosa»; «, )» y «días .» (Cecilia); «Pide a Lucia… / Revisa con Lucia…» desaparece con el bloque de las 07:00; «Jessi» → «Yessica» en la configuración; `L()` limpia la puntuación que deja quitar un código |

**Pruebas R12** (servir.py en 127.0.0.1:8940 con copia de local.db, cerrado): lucia, candela, constanza, agustina, lina, valeria, jeronimo (+ `mi-dia/seo`), macarena, lara, tomas y camilo a 1440 y 390: 0 errores de consola, 0 desbordes, 0 «null/undefined/NaN/[importe]». Capturas en `capturas/mi_dia/r12/`. `pruebas_e0.py` TODO BIEN (diseño estricto incluido) · `pruebas_coherencia.py` 0 errores (sección nueva «R12 · MI DÍA»: cada bloque lee la definición única + cartera por trafficker = asignaciones + SEO = base de medibles) · `pruebas_seguridad.py` TODO BIEN · `escaner_secretos.py --proyecto` limpio.

## Ronda 13 (2-oct, noche)
| Arreglo | Estado |
|---|---|
| «gasto medio — al mes» (finanzas de dirección) | **Arreglado** con el parche de R12: lee `caja.gasto_medio` (47.115 €/mes) y `gasto_medio_texto`; «Bien desde 2 meses»; en «Lo primero» «Por debajo de 2 meses, que es el mínimo». El bloque de administración dice también el gasto medio |
| «Lo primero hoy» con reuniones pasadas (Clara 08:00 a las 20:30) | **Arreglado.** `vro_hoy`: una reunión pasada (`pasada` o su hora + 45 min) no sube a «Lo primero»; en la lista va con su resultado (celebrada · no se presentó · «apunta si se celebró»). Número = reuniones por delante |
| Número que manda de outreach «Fase 2» | **Arreglado.** `out_por_clasificar`: respuestas de Snov.io de 30 días sin clasificar (97 de 97; 4 hoy, 93 > 24 h) y al lado las reuniones conseguidas (origen outreach en GHL: ninguna medida, y se dice). «Jessi» → «Yessica» en mis ficheros |
| Número del account (nota R13 de E0) | **Aplicado.** `resultados_cartera` + config con `account.resultados_de_su_cartera_frente_a_objetivo`; la salud, «Segundo indicador» (proxy). Lucía: 50 % (1 de 2), salud 100 % debajo. Si un puesto no nombra indicador, manda el `el_que_manda` del catálogo |

**Pruebas R13** (servir.py en 127.0.0.1:8977 con copia de local.db, cerrado): tomas (+ ventas_ro, finanzas_direccion), eulimar y lucia a 1440 y 390: 0 errores de consola, 0 desbordes, 0 «null/undefined/NaN/[importe]». Capturas en `capturas/mi_dia/r13/`. `pruebas_e0.py` TODO BIEN (diseño estricto) · `pruebas_coherencia.py` 0 errores · `pruebas_seguridad.py` TODO BIEN · `escaner_secretos.py --proyecto` limpio.

## Ronda de velocidad (2-oct noche, auditoría 37 causas 3-5) · Mi día, Personas e Informe
**Mi día en una tanda.** `fuentes_mi_dia/resumen_mi_dia.py` (lo llama `generar_mi_dia.py`, último paso de la tubería, cada hora) deja por persona `data/mi_dia/p_<id>.json` (su primer puesto) y `data/mi_dia/puestos/<puesto>/p_<id>.json`: la configuración y cada fichero que usan sus bloques, **recortado con las mismas funciones de servir.py** (`entrada_datos_modulo`, `ve_alguno`, `recortar_modulo`) y sin las claves y campos de fila que el código de Mi día no nombra. Alta en `reglas_permisos.json` (`mi_dia/p_*` y `mi_dia/puestos/*/p_*`, `solo_propio`): nadie lee el de otro, ni en «ver como»; el servidor lo vuelve a recortar al servirlo. Fuera del resumen (se piden a la vez): `ventas_ro/*` (abren nombres con rastro), alertas propias, acciones, avisos y la lista del copiloto (antes iba sola al final). En «ver como», sin servidor o con un resumen de más de 3 h, Mi día pide los ficheros sueltos como antes. 30 personas, 2,3 s.
**Personas:** las 5 lecturas a la vez (`Promise.all`). **Informe:** ver `_ESTADO_informe.md`.

Medido con Playwright (4G lenta de Chrome: 562 ms, 1,44 Mbps, CPU ×4; 390 px; mediana de 3; misma copia de datos y de servir.py/app.js antes y después, servidores en 127.0.0.1:9035/9036):

| Pantalla (al navegar dentro de la app) | Persona | Antes: contenido útil · peticiones · KB | Después | 
|---|---|---|---|
| Mi día | tomas | 2.729 ms (3.226 completo) · 16 · 179 KB | 1.976 ms · 7 · 116 KB (944 ms la 2.ª vez, con ventas_ro adelantado) |
| Mi día | lucia | 2.087 ms (2.577) · 13 · 77 KB | **973 ms** · 5 · 49 KB |
| Mi día | valeria | 1.769 ms (2.313) · 7 · 94 KB | 1.119 ms · 5 · 72 KB |
| Mi día (entrada a la app) | tomas / lucia / valeria | 14,3 / 13,3 / 12,9 s · 20 / 16 / 10 | 13,6 / 12,3 / 12,5 s · 11 / 8 / 8 (el resto es la carga de la carcasa, causas 1-2 y 7, de otro carril) |
| Personas | tomas / lucia / valeria | 3.017 / 2.386 / 2.386 ms · 4 / 3 / 3 tandas | **760 / 694 / 684 ms** · 1 tanda |
| Informe del cliente | tomas / lucia / valeria | 4.742 / 3.107 / 4.733 ms · 378 / 118 / 378 KB | **1.935 / 1.970 / 1.937 ms** · 21 / 23 / 27 KB |

**Las cifras no cambian:** el texto entero de la pantalla, antes y después, es idéntico en 26 Mi día (los 21 puestos con su persona real + chips de Tomás, Valeria, Yessica, Jerónimo, Constanza; incluidos tomas, lucia y valeria), 5 Personas y 36 Informes (adade-zaragoza, fusterguell, bit-24, aster, ahedo × 3 periodos y 4 personas, más paridad). «Ver como» (Tomás → Lucía): idéntico, y sigue por la vía antigua.
Pruebas: `pruebas_e0.py` TODO BIEN (diseño estricto incluido) · `pruebas_seguridad.py` 271 ✓ y 0 fallos (en una primera vuelta salió 1 fallo intermitente de N15 «cola de ClickUp», ajeno; repetida, limpia) · `pruebas_coherencia.py` 0 errores · `escaner_secretos.py --proyecto` limpio.
Riesgo que queda: si a alguien le quitan un puesto, su resumen trae los ficheros de ese puesto hasta la siguiente vuelta de la tubería (≤ 1 h; el servidor sí quita al momento los clientes y el dinero que ya no ve).

## A1 + A3 (43_IDEAS_MEJORA, 2-oct noche) · «Lo mío» arriba de Mi día
- **«Lo mío»**: UNA lista personal arriba del todo (junto al número que manda en escritorio; primera en el móvil) que funde «Lo primero hoy» y «Mis alertas». Junta: alertas «mías» (definición única de Alertas con la cola `acciones?modulo=alertas`, respetando `alerta_lote` y `alerta_posponer`), correos sin contestar de su cartera de account (regla de la Bandeja, uno por cliente), piezas que le toca revisar (regla de Producción › Por revisar, una fila por cliente), menciones del chat sin leer (`/api/canales/campana`), decisiones que esperan su sí (reloj) y lo urgente que suben los bloques. Sin duplicados (una alerta manda sobre otra fila del mismo objeto o tema) y por plazo: vencido · hoy · esta semana · sin fecha, y dentro, la gravedad. Cada fila: qué · de quién · por qué · plazo (un chip) y UN botón con el verbo que abre el objeto exacto; si es alerta, «Lo tengo» y «Posponer» (mañana / el lunes, mismos tipos que Alertas). 6 filas a la vista (4 en el móvil) y «Ver las otras N».
- El consejo de la IA de la carcasa va debajo de «Lo mío» y sin sus filas (si no queda ninguna, oculto). En el móvil: 7 piezas a la vista como mucho (Lo mío, número, consejo, 3 bloques y «Más de tu día» plegado). Cumpleaños y copiloto al final (la cola de Camilo sube).
- Núcleo puro `<lo-mio>` en `mi_dia_bloques.js` (copia literal de `<contar>` de alertas.js). `resumen_mi_dia.py` mete `LO_MIO_USA` (bandeja, producción, decisiones) solo cuando pueden traer algo y recortados si solo los usa «Lo mío» (Tomás 527 → 548 KB).
- R15a: tarjeta «Tu primera semana · N de 5» (altas de < 14 días; `primera_semana.js` se carga solo para ellas). Personas en alerta y carga → `#/personas/<id>`.
- Medida (`fuentes_mi_dia/medir_lo_mio.py`, capturas `capturas/mi_dia/a1/`): 1.ª fila de trabajo a 1440 de 663-719 px a 183-299 px; móvil, bloques a la vista de 11-13 a 5-6 (+ «Más de tu día»), Lucía 7.574 → 3.968 px. Número que manda: texto idéntico en las 7 personas × 2 anchos. Alertas de «Lo mío» = «Mías» de Alertas y piezas = «Por revisar» de Producción (lucia, mili, gustavo, camilo, jeronimo, tomas). setter_ana no tiene Mi día (aterriza en #/setters).

## V2 · carril V2-A (3-oct, madrugada) · UNA SOLA VARA en Mi día · revisiones 40_A, 40_B, 40_C y barrido v1
Servidor de pruebas: `servir.py --bind 127.0.0.1 --puerto 9130` con copia de `local.db` (cerrado al acabar). Resúmenes de Mi día regenerados (`resumen_mi_dia.py`) tras los cambios de Bandeja, Captación e Incidencias de los otros carriles.

| Hallazgo | Estado |
|---|---|
| B-A1 · la revisión técnica llega a las tres jefas (Valeria 70, Yessica 62, Jerónimo 97) | **Arreglado.** `revisorTecnica()` aplica `revision_piezas.areas_tecnica` igual que `servir.puede_revisar_pieza` (puesto del autor o su jefa directa); lo huérfano (sin área o la jefa es la autora) va a operaciones. Valeria 28, Yessica 49, Jerónimo 33. «Lo mío» enseña como mucho 2 filas de revisión y una tercera «Revisar N piezas más» → Producción: las alertas ya no quedan escondidas. `resumen_mi_dia.py` mete lo huérfano en el resumen de Mili |
| A-A1 · cuatro varas de «rojo» | **Arreglado.** «Clientes en crítico» (Mili: 10 de 68, no 40), «Críticos esperando tu Visto» (Coti: los 10 críticos, no Finexen/Greconsult), «Gravedad de toda la cartera» (10 crítico · 44 atención · 14 bien, no «94 % verde · 0 rojo»), «Fuegos de toda la casa: clientes en crítico» (4 = `criticos_casa` de Captación) y la alarma de Meta con el cliente en atención como «publicidad urgente» en ámbar. El copiloto ya no está a la vista: solo al account y dentro de «Más de tu día» (V2-B le puso la vara de la verdad) |
| A-A4 · número del account en verde con 7 de 8 sin campaña | **Arreglado.** Denominador = toda su cartera de account: Lucía 8 % (1 de 12), Candela 13 % (1 de 8), con los que no tienen campaña nombrados. Segundo indicador: un crítico nunca cuenta como bien y con críticos no sale verde (Lucía 92 %, 11 de 12, ámbar), con su chip de color |
| A-A5 · revisiones de Lucía 64/63/54/42 | **Arreglado en Mi día**: dos cosas distintas con dos nombres. «Lo mío»: «64 piezas esperan tu visto bueno (últimos 30 días, como Producción › Por revisar)». «Trabajo», «Tu cumplimiento», el mapa de Mili e Incidencias: «42 de tus 67 revisiones del account llevan más de 48 h» con `revisionesDelAccount()` de `produccion_comun.js` (la misma de Producción y del generador). Las otras cifras de Producción (63, 54 de 84) son de su dueño |
| A-M4 · Mili: 13 % frente a 12 %, Lucía 14 frente a 13, «no imputaron ayer (1-oct)» un sábado | **Arreglado.** «Para Tomás» Nº 1 = `NUMERO.altas_en_plazo` (13 %); «Clientes esperando» con la regla de la pantalla Bandeja (`bandejaComoPantalla` + la cola de la Bandeja de todos: `acciones?modulo=bandeja`): Lucía 12 = su Bandeja; el mapa de control de Mi día e Incidencias, igual (`controlPersona`). «No imputaron el jue 1-oct (último dato; el vie 2-oct todavía no ha llegado)» con `fechas.ultimoLaborable()` |
| A-M5 · Cecilia 0 de 11 / 10 / 10; 3 por encima con 8 nombres; dos horas de ClickUp | **Arreglado.** Misma definición que Personas (`planDe`: apunte de tipo plan): «0 de 10 en alerta sin plan · 11 en alerta: 10 sin plan todavía y 1 con plan». Carga: solo los 3 que pasan, con su cifra («21 de 16 como trafficker»); los que están cerca, en una línea (explica por qué Contratación no pide accounts). «Registros por revisar» e «imputa ayer» con la hora del fichero de Horas |
| A-M6 · «administracion ·», «rrhh ·» | **Arreglado.** Fuera el id del departamento en «Lo mío» |
| A-M12 · «Abrir Personas» de la alerta de RRHH | **Arreglado.** `#/personas/<id>?plan=1` («Anotar el plan») en la alerta y en el bloque; alerta y fila del bloque, en una |
| A-M13 · Sofía: IP Forense dos veces, «Día 2 · hoy» un día 3, «alta 1-oct» | **Arreglado.** La fila de impagos abre `#/finanzas/cobros/<factura>` como su alerta: una sola fila. Calendario con el «hoy» de verdad («pendiente desde el vie 2-oct», en rojo si nadie lo marcó). «firmado el 1-oct · día 0: 1-oct» |
| A-A6 · «Nada pendiente de Meta» con el importe tapado | **Arreglado.** «Hay facturas de Meta de septiembre por contabilizar… No ves el importe por tu puesto (lo ve dirección): pídeselo a Tomás.» Fuera «FIN §6», «regla «inversion»» y «Pendiente de E0» |
| A-M1 · beneficio con céntimos y en verde a 26.000 € del norte | **Arreglado.** «3.860 €» sin céntimos, color por la trayectoria (plan del mes con el gasto sin factura: −3.428 € → rojo), «Con el gasto sin factura: −3.428 €. A 26.140 € del norte»; el resto, en «¿Qué es? › Detalle» |
| A-M7 · «(403)… --en-vivo seranking» en Mi día de Tomás | **Arreglado en Mi día** (`textoLlano`: «Posiciones en SE Ranking: no responde.»). El texto nace en `avisos.py` (R16): apuntado |
| A-M9 · 1024: número a 950-1.300 px; 10-11 bloques | **Arreglado.** Entre 641 y 1.180 px el número va arriba (89-145 px a 1024 en las 13 personas); «Lo mío» con 3 filas. Como mucho 7 piezas a la vista en todos los anchos (Lo mío + número + consejo + 4 bloques; 3 en el móvil): el resto, los cumpleaños y el copiloto, en «Más de tu día» (`config.comun.max_bloques_vista`) |
| A-M10 · tres listas de «qué hacer» | **Arreglado.** Fuera el copiloto de la vista; el consejo no repite lo que ya está en «Lo mío» |
| A-M14 · Coti: Kiosko (tienda online) en nichos; «Alarmas del panel ·» sin hora | **Arreglado.** Tienda online fuera de la suma (dicho en una línea); frase del coste según lo que ve; hora de la fuente en «Lo de tus clientes» |
| A-B3 · «(propuesta sin firmar…)» en el umbral | **Arreglado.** El matiz entre paréntesis va a «¿Qué es?» |
| A-B5 · «478 h», «439 h» | **Arreglado** en Mi día e Incidencias (antigüedad común: «20 días») y en el generador de Incidencias |
| A-B7 · «(22-jul, 11-sep)» y «Rol de Mili» | **Arreglado.** Fuera las fechas; fuente «Ronda de Mili» |
| A-B8 · «en«definir»tras» | **Arreglado** (`textoLlano`: espacios alrededor de «») |
| A-A2 / A-A3 / B-M4 · consejos con horas, de otros o sin decisiones | **Apoyo en Mi día**: el consejo se filtra por pestaña de puesto y por dueño (tú o tu gente directa; en dirección, solo lo tuyo) y «Imputa las horas» no va primero si hay otro. Las reglas son de V2-B (`ia.py`/`motor_consejos.py`) |
| A-A7 · Coti jefa de SEO | **No aplica**: Jerónimo es el jefe de SEO (decisión de Tomás del 2-oct) |
| B-A2 · Akua «Captación en crítico» frente a «Atención» | **Arreglado en Mi día.** «Akua · publicidad urgente (cliente en atención)» en «Lo mío» y en los bloques; el color, la gravedad de la verdad |
| B-A3 · cartera de Lina 21/14/19; Fuegos 3 frente a 2 + 2 | **Arreglado.** Cifras únicas de Captación (`carteras_publicidad`, `criticos_casa`): «Lina · 19 clientes (+2 de apoyo) · 14 con cuenta de Meta · 9 con Meta encendida · 3 en crítico»; Valeria 11 (+8) · 10 · 6 · 1; suma = Fuegos (4). Prueba nueva en `pruebas_coherencia.py` |
| B-M5 · «Encendido · encendido el día 10»; 8 / 16 / 17 | **Arreglado.** «siguiente paso: accesos (objetivo encender el día 10, límite 12)»; el número explica «De 17 altas en curso, 8 ya se pueden juzgar… y 9 siguen en plazo» |
| B-M6 · «Sin dato. Sin dato:»; 53 (30 d) frente a 25 | **Arreglado.** Un solo «Sin dato» y la ventana al lado: «53 citas de los últimos 30 días» / «25 citas de los últimos 14 días» |
| B-M7 · Miguel Vargas «todo bien» sin cartera | **Arreglado.** Sin clientes en la silla del puesto, los bloques de lo suyo y el número dicen en gris «Aún no llevas clientes como GoHighLevel (CRM)» con el MISMO motivo que su «Lo mío» |
| B-M8 · SEO en rojo con SE Ranking en duda | **Arreglado.** Gris con `resumen.estado_mostrado` y su motivo («Dato en duda…») y chip «Dato en duda» |
| B-M10 · posponer Akua y vuelve como «cuenta crítica» | **Arreglado.** `apartadasLoMio()`: lo que trata de una alerta pospuesta (mismo tema u objeto) no sale; probado en el navegador (7 → 6 y sin fila de Akua, también al recargar) |
| B-B2 · plurales | **Arreglado** (`plural` en filas y `unidadDe()` para la cifra 1) |
| B-B7 · «(el medidor de entregabilidad)» repetido | **Arreglado** en la configuración |
| C-1 · Lara 14/25 frente a 4/10 | **Arreglado** (V2-C2 adoptó la misma silla de redes): 0 de 14 en las dos |
| C-6 / C-10 · «vence 2-oct» no vencida; «Sin fecha» en tareas vencidas | **Arreglado.** La cola con `alDia()` de `produccion_comun.js`; la tarea vencida de «Lo mío» lleva su fecha («venció el mié 30-sep · Vencido hace 2 días») y se ordena por ella |
| C-7 · cambiar de pestaña (Jerónimo) no cambia «Lo mío» ni el consejo | **Arreglado.** «Lo mío» por pestaña (`config.comun.lo_mio_departamentos`): SEO 37 alertas de SEO, Ficha de Google sin las webs caídas; las piezas, en la jefatura; el botón «Alertas · 47» sigue siendo «Mías» |
| C-8 / C-9 · web: «Fase 2» frente a «60 de 64»; lentas 3 + 10 frente a 14 | **Arreglado.** «Webs que responden 60 de 64» (`resumen.responden`) con las suyas al lado; lentas con `webs.json → lenta` (14, las tuyas marcadas) |
| C-17 · «Bloqueadas por el cliente» con tareas internas | **Arreglado.** Solo con cliente de verdad; «Gates» → «Controles de calidad» |
| C-23 · Maps 10 frente a 11 | **Arreglado.** La jefa cuenta todas, como SEO, ficha y webs (11) |
| C-24 · copiloto repetido a Jerónimo | **Arreglado.** Solo al account, plegado |
| C-3 · Eulimar ve las 97 | **Hecho por R16** (el servidor recorta por su cartera): Mi día cuenta lo que recibe (96, las suyas) |
| R16 · contratos nuevos de «Tu primera semana» (`primera_semana.js`) | **Hecho.** El paso «Algo va mal» se marca solo también para el jefe directo (`/api/opiniones → equipo[persona] = {alguna, primera}`, solo el hecho); el número que manda se pinta con `numero_tabla` (tabla densa: quién, número, verde, ámbar, rojo) o, si no hay filas, el texto llano; cada uno marca solo sus pasos y un 403 se dice en llano («Solo la propia persona marca sus pasos») |
| Barrido v1 · RO-#### en texto plano; «--en-vivo» | **Arreglado** (`textoLlano` en Mi día; enlace en «Para Tomás» de Incidencias; el generador ya no lo mete en el texto) |

**Pruebas V2-A:** 13 personas (+ sofia, lina, gustavo, camilo, eulimar, carlos_viur) a 1440/1024/390: 0 errores de consola, 0 desbordes, ≤ 7 piezas a la vista, número arriba a 1024 (89-145 px). `pruebas_coherencia.py` sección «V2-A · MI DÍA» (5 comprobaciones nuevas). Resultado de las demás pruebas, en el informe del carril.
