# _ESTADO · M18 Dinero por cliente · M19 Finanzas · bloques 8-9 de M16 (E10, 2-oct-2026)

## Hecho
- `fuentes_dinero/generar_dinero.py` (solo GET; Holded y Airtable en vivo con copia en `_cache/`; `--sin-red`) → `data/dinero_cliente/dinero_cliente.json`, `data/finanzas/finanzas.json`, `data/ventas_ro_extra/anuncios.json`. Puerta de secretos propia + `escaner_secretos.py` en verde. Ningún sueldo: equipo solo por áreas de 3 o más (paid, vídeo y SEO, juntas).
- `modulos/dinero_cliente.js` (M18), `modulos/finanzas.js` (M19), `modulos/dinero_m16_anuncios.js` (bloques 8 y 9 llamados desde `ventas_ro.js`, 2 líneas), `modulos/dinero_comun.js` (estilos y componentes locales).
- Comunes tocados con Edit localizado: `modulos/indice.js` (M18 y M19 → hecho), `reglas_permisos.json → datos_de_modulo` (3 ficheros, con `solo_todo_sin_cliente`), `LEEME.md` (líneas M18/M19), `ventas_ro.js` (import + llamada).

## Quién recibe qué (comprobado en la respuesta de servir.py, no en pantalla)
| Persona | M18 | M19 | M16 bloques 8-9 |
|---|---|---|---|
| Tomás | 67 clientes, cuota, horas, rentabilidad a tarifa y real | todo (`direccion` + `admin`) | 149 conversiones + previsión con accounts |
| Mili | 67, cuota, horas, rentabilidad a tarifa | 403 | por anuncio + accounts, sin lista de conversiones |
| Coti (constanza) | igual que Mili | 403 | por anuncio, sin accounts ni conversiones |
| Sofía | 67, cuota y valor de vida, **sin horas ni rentabilidad** | `admin` sí, `direccion` vacía | 403 |
| Lucía (account) | sus 12, cuota y horas | 403 | 403 |
| Valeria / Lina | 67 / 18 de su cartera, horas **sin euros** | 403 | 403 |
| Jessi | 403 | 403 | resumen | 
| setter_ana | 403 | 403 | 403 |
Consola sin errores propios con tomas, mili, lucia, valeria, yessica, constanza, setter_ana y sofia (Chrome sin cabeza; los «Failed to fetch» de otros módulos son cortes de servir.py con cargas simultáneas, ver D-P M14).

## Cifras contrastadas a mano
1. Cuota recurrente de octubre en Airtable (activos) **64.351 €** = libro de clientes «Cuota de octubre de los activos» 64.351 € = Holded `cuota_oct` del panel financiero.
2. Caja Holded en vivo (tesorería): BBVA 46.754,68 € + Sabadell 8.468,86 € + Wise EUR 4.052,49 € + Wise USD 3.240,61 $ + caja 18 € = **62.109 €**.
3. Carga por account (≤ 12): Lucía 12, Carla 10, Nati 8, Casiana 8, Candela 6, Facundo 6, Dana 5 = `21_CARGA_ACCOUNTS_2OCT.md`.
4. Atribución: 149 conversiones, 6 de 15 clientes vienen de un anuncio, 01A con 47 conversiones y 3 clientes = memoria del 2-oct.

## Hallazgos para Tomás
- Firmada 67.291 €/mes (63 clientes); **si firman los 4 contratos enviados, 73.171 €**; 45 % del objetivo de 150.000 € en diciembre.
- Agosto, último mes cerrado: beneficio **−61 €** (real −7.349 €). Caja para **1,1 meses**. Equipo = 74 % de los ingresos.
- **Think Value y Marlex** firmados sin línea de octubre en Airtable. 9 recibos vencidos (19.150 €), 1 con más de 60 días (IP Forense, 109 €); Taller del Patinete 11.007 €.
- A 31,47 €/h, 24 de 53 clientes en pérdida en septiembre (GAC −185 %, Ecom −174 %, BIT 24 −143 %), con horas al 51,7 %: aviso, no prueba.
- Previsión: ~9 altas en el embudo frente a 14 huecos útiles (29 brutos; Candela con 6 arranques no cuenta): cabe, justo.

## Falta / fase 2
- Rentabilidad por servicio y nicho (no existe «servicio contratado»), herramientas por cliente, segundo mes de horas.
- Pestañas «Ingresos», «Top 20», «Resultados» y «Cobros» de M19 probadas en el navegador interno solo en carga; capturas solo del «Resumen» (la pestaña se recuerda por sesión).
- Coste agregado del equipo: formulario en cola simulada; lo lee el modelo de equipo del panel v29 hasta W1.
- Revisión con Coti, Mili y Agus (R15) pendiente.

## Capturas
`capturas/dinero_cliente/` (tomas, mili, constanza, sofia, lucia, valeria; 1440 y 390), `capturas/finanzas/` (tomas, sofia; 1440 y 390), `capturas/ventas_ro_extra/` (tomas 1440 y 390, mili 1440).

## Para el agente del «Panel de dirección» (panel-direccion, solo Tomás)
- M19 lleva arriba el enlace «Ver el panel de dirección completo» → `#/panel-direccion`. No se han portado las pestañas del panel v29/v30 (Empresa, Captación de RO, Clientes…).
- Reutilizable: `fuentes_dinero/generar_dinero.py` NO ejecuta `build_financiero.py`; lee `~/Downloads/PANEL_RESULTADOS_RO_2026-09-18/ENTREGA/financiero_ro.json` (ing, anios, ab, puente, top, conc, gmes, gan, prov12, pyg, tes, cobro, kpi), `finanzas_ajustes.json`, `equipo_ro.json` (solo `areas`, agrupando las de < 3 personas) y `atribucion_anuncios.json`, y lo vuelca en `data/finanzas/finanzas.json → direccion[0]` (solo nivel «todo») y `data/ventas_ro_extra/anuncios.json`.
- Lectores en vivo reutilizables en el mismo script: `holded('invoicing/v1/treasury')` y facturas de venta (vía `hd.py`), `airtable_lineas()` (tabla «Facturación mensual», `cellFormat=string`, solo GET) y el emparejador de nombres fiscales `emparejador()` + `ALIAS`.
- Componentes locales `barrasMes()` y `numeroGrande()` en `modulos/dinero_comun.js`.

## Ronda de corrección · auditoría del cierre de Sofía (25_AUDITORIA_CIERRE_SOFIA.md, 2-oct)
- `generar_dinero.py` ya NO copia los gastos del cierre: lee cada línea de Datos_Gastos (categoría de Sofía) y la convierte con el `currencyChange` de su factura en Holded (compras 2026 leídas mes a mes, 1.356, caché `_cache/holded_compras_2026.json`). Quita las 4 repetidas, usa KLIP-0367 (550 €) en lugar de la cargada con IVA y añade las 2 facturas de agosto que faltaban. Rupias y pesos (3, 858 €) se dejan y se avisan.
- **Cifras que salen (las que debe usar el Panel de dirección):** agosto beneficio **3.859,87 €**, con gasto sin factura **−3.428,03 €**, gastos 51.488 €. Ene-ago: gastos **376.638 €**, beneficio **93.775 €**, con gasto sin factura **76.674 €**, margen 19,9 % (16,3 %), margen bruto **37,3 %**, equipo **64,7 %** del año y **67,8 %** en agosto (37.535 €), coste real por hora 9,16 €/h. Caja 74.513 € a 31-ago (fiable) y 62.109 € hoy; 1,3 meses «si no entrara nada» con el gasto medio corregido (47.080 €/mes); flujo del año +22.648 €. Ingresos, cuota, concentración e impagos, sin cambios.
- **Diferencia con la auditoría:** 141 € en mayo (herramientas en dólares: aquí se convierten 141 € más). Por eso el año da 93.775 € / 76.674 € frente a 93.634 € / 76.534 € de la auditoría; agosto cuadra al céntimo. Sin resolver: pedir a quien hizo la auditoría su lista de mayo.
- Quitados: el «runway 1,4 meses» y cualquier cobro con traspasos internos (no se usaba el cashflow). El gasto sin factura sale como techo, con aviso de doble conteo.
- M19 suma «Fiabilidad del cierre» (14 hojas fiable / con errores / no fiable, 4 repetidas, 3 dudosas, recomendación de conversión para septiembre). Tomás lo ve en «Resultados y equipo» junto a «2025 frente a 2026, en euros los dos»; Sofía, al pie de su «Mi día» (sin beneficio). La cuenta de resultados enseña también la columna «Decía el cierre».

## Ronda de arreglos (2-oct noche) · fallo de la auditoría → estado
| Fallo | Estado |
|---|---|
| 28 E-04 · FusterGüell 281 % (pautadas de la cuota vieja de ClickUp) | **Arreglado**: pautadas = cuota ÷ 31,47 siempre → 31,7 h y **141 %**. Si la Cartera pauta otra cosa (> 5 %), aviso «cuota vieja» en la fila |
| 28 E-05 · Akua 1.270 (ClickUp) frente a 1.290 (Airtable y Holded) | **Arreglado**: 1.290 €. Cuota de cada cliente con UNA regla (Airtable de octubre; si no, proyecto de Airtable; si no, factura de octubre en Holded; si no, firmado sin ficha a 1.470 €). El libro y la Cartera ya no dan cuota. Se exporta a `fuentes_dinero/cuotas.json` para la ficha; `pruebas_coherencia.py` «ficha · cuota = Dinero» en verde |
| FusterGüell dos sociedades | **Arreglado**: suma de las dos líneas de Airtable (2 × 499,50 = 999 €) |
| Corrección de cuota de Tomás (Marlex y Think Value, Ramallo) | **Arreglado**: cuota recurrente firmada **67.291 €** · cuota de octubre con proyectos **70.781 €** · facturable en octubre **70.581 €** (= cifra firmada en memoria) · emitido en Holded 65.341 € · cobrado 0 € (SEPA el día 2). Desglose línea a línea en M19 y contraste con Holded: GAC emitida a 1.205 € sin el descuento de 200 €, Jenasa 2.500 € sin emitir, Think Value y Marlex sin factura. Pendientes esperados: Vinces y Tax & Advise |
| 22 I-01 / 27 A3 · cuota deducible por las pautadas (Lina, Valeria) | **Arreglado**: pautadas y % van en `cuota_horas` (se quitan a quien no ve la cuota); tarifa, segmento, vida y «en facturación» con prefijo `cuota_`. Lina y Valeria reciben solo horas consumidas |
| 27 M5 · dirección protegida por el nombre de una lista | **Arreglado**: `finanzas/direccion.json` con `puestos: [direccion, finanzas_direccion]`; rentabilidad en `dinero_cliente/rentabilidad.json` con `puestos` de dirección, operaciones y proyectos. En «ver como», Mili como Tomás → 403 |
| 26 C · Dinero por cliente sin atajos | **Arreglado**: botones «Holded» (factura de octubre) y «Airtable» (línea del cliente) por fila, solo a quien ve cobros |
| 29 · textos con códigos (D-xx, NORTE §1, SP14, MEM, AMI, KPF, FIN, «Top 20», «(E1)», «2026-08») | **Arreglado** en M18, M19 y bloques 8-9 de M16 |
| 29 · desborde de 8 px a 390 en Dinero y Finanzas | **Arreglado**: ancho de página 390 con las 4 personas (Playwright) |
| 29 F-01 · 64.351 frente a 67.291 sin explicar | **Arreglado**: las dos pantallas dicen «Cuota de octubre» = 70.781 € con el mismo desglose |
| Verdad única | **Adoptada** para account y «nuevo»; `dinero-cliente` añadido a ADOPTADOS en `pruebas_coherencia.py` (0 errores) |
| Factura anulada F-26-412 (Hacelerix) contada como impago; UHY Fay emparejada con PGB Auditores | **Arreglado**: fuera las anuladas (estado 3); UHY Fay, Power Global y Hacelerix sin cliente de la app |
| Sofía no recibía filas con cliente en M19 (nivel «suyo» = solo su cartera, ronda 6 de E0) | **Arreglado**: Sofía ve M19 con nivel «todo» (lo de dirección ya va aparte) |
| Mayo: 141 € de diferencia con la auditoría 25 | **Sin cerrar**. Candidatas: Mango Technologies ES2026-6896 (565,41 $, 78,8 € de conversión) y OpenAI A6F8E4B6-0020 (454,41 $, 63,3 €) = 142 €: si la auditoría las tomó en euros, cuadra. Pedir la lista de mayo a quien hizo la auditoría |
| Zonas horarias, ventanas de 7 días | No aplica (cifras mensuales y saldos; hora de Madrid) |

Pruebas: `pruebas_e0.py` TODO BIEN · `pruebas_coherencia.py` 0 errores · escáner limpio en mis ficheros · sin errores de consola con tomas, mili, lucia, valeria, yessica, constanza, setter_ana y sofia. Capturas `capturas/*/r3_*` (16). Ojo: a las 17:37 el servidor dejó de servir NADA por un hallazgo del escáner en `data/personas.json` (correos de E0, no míos): la última prueba de Sofía con servidor quedó pendiente de repetir.

## Cuadre final con el CSV de mayo de la auditoría (2-oct noche)
- La diferencia era doble: (1) el abono de Windsor TZT4XHFM-0002 (−1.034,93 $ en el cierre) no se convertía (−140,57 €); (2) OpenAI A6F8E4B6-0020 y ClickUp ES2026-6896 se convertían y son euros (+142,16 €). Antes salían 141 € MENOS de gasto que la auditoría, por eso el beneficio era más alto (93.775 €): el signo estaba bien, la premisa de «141 € más» no.
- Ahora: mayo **57.871,70 €** de gasto (CSV + las dos en euros = 57.871,68 €). Las dos facturas salen en M19 como «en euros, a confirmar con el PDF».
- **Cifras finales en `data/finanzas/direccion.json`:** ene-ago gastos 376.921 €, **beneficio 93.492 €**, con gasto sin factura **76.392 €**; agosto **3.859,87 €** y **−3.428,03 €**; margen 19,9 % (16,2 %), margen bruto 37,3 %, equipo 64,7 % (agosto 67,8 %). Cuota en `finanzas.json → admin.cuota_tres`: recurrente 67.291 €, del mes 70.781 €, facturable 70.581 €.
- Sofía con el servidor desbloqueado: finanzas 200 (2 firmas sin alta, 70 facturas pendientes, facturable 70.581 €, fiabilidad), `finanzas/direccion` 403 y rentabilidad 403. Tomás 200/200; Mili 403/200; Lucía 403/403. Consola limpia con 8 personas; `pruebas_e0.py` y `pruebas_coherencia.py` en verde; escáner limpio.

## N6 · Diseño 10/10 (2-oct, noche)

**Finanzas · 8,5 / 10** (auditoría 30: 5,0) · **Dinero por cliente · 8 / 10** (5,5) · bloques de anuncios de Ventas · 8,5.
- `dinero_comun.js` sin hoja propia (`estilos()` queda vacía por compatibilidad). `barrasMes()` dibuja con `grafico()` (letra 12 px, marcas redondas 0 · 10.000 · 20.000 €, sin «25.001 €», sin el choque «0 € / −1730 €», burbuja al pasar el ratón; apiladas → total en barras + línea por parte). `numeroGrande()` usa `cifraPrincipal()` (una sola cifra a 32 px por pantalla; la cuota pasa a tarjeta con `secundaria: true`). `filasConBarra()` (tramos de impagos, coste por área) y `quinceFilas()` (15 filas + «Ver las N filas») con clases comunes. El pie de fuentes es un solo «Datos al día / N fuentes con retraso» que despliega el detalle.
- **Finanzas:** beneficio con `colorCifra('beneficio')`: **3.860 € en verde** (igual que en Mi día); tablas de beneficio y comparación 2025/2026 con la misma regla. Tarjetas 4 + 4. «Altas y bajas»: líneas de altas, bajas y activos y, plegados, «Ver los 47 meses con nombres» (antes los nombres solo estaban en la burbuja de cada barra). Formularios con `campoTexto`/`.campo`. Calendario de Sofía en tarjetas comunes. Sofía ya no pide `finanzas/direccion` (antes, un 403 en su consola).
- **Dinero por cliente:** celdas con `.celda-cli`, tabla a 15 filas + «Ver las N», gráfico nuevo «Rentabilidad cliente a cliente» (barras con el umbral del 10 %). Sofía ya no pide `rentabilidad` ni `finanzas/direccion` (dos 403 menos).
- **Ventas de RO:** coste por cliente con `colorCifra('coste_cliente')` (735 € ámbar, el mismo que el Panel). Los bloques 8 y 9 (`dinero_m16_anuncios.js`) no estaban enganchados: ahora son la pestaña «De qué anuncio» (los permisos los recorta `servir.py`, como antes).
- Comprobado con tomas, mili, sofia, cecilia, lucia, valeria y constanza (cada una ve lo de su puesto) a 1440, 1024 y 390: sin scroll horizontal, 0 textos < 12 px, 0 errores de consola. Capturas en `capturas/_n6/finanzas/`, `capturas/_n6/dinero_cliente/`, `capturas/_n6/ventas_ro/`; antes en `capturas/_n6/_antes/`.
- **Por qué no un 10:** `.embudo-barras` y `tablaDensa` no son míos y siguen con su ancho; la página de Dinero por cliente en el móvil sigue larga (las tarjetas apiladas); la burbuja de las altas y bajas ya no lleva nombres (están en la tabla plegada).

## R12 · arreglos tras la auditoría final (2-oct, noche) · carril ventas y dinero
- **A-A2 · arreglado en Finanzas y Dinero por cliente.** `usa_periodo: ['mes','mes_ant','trim','anio','medida']`, por meses enteros (los datos son mensuales; `mesesPeriodo`, `textoMeses`, `sumaMeses` en dinero_comun.js). Finanzas: panel «En el periodo» con facturado, cobrado de lo facturado, beneficio, margen bruto y altas/bajas (con comparación); la cuenta de resultados, el puente y las altas/bajas se filtran a esos meses. Sofía ve facturado y cobrado del periodo (`admin.facturado_mes`, la misma serie que la de dirección). Dinero por cliente: «Facturado a estos clientes» y columna por cliente (`cuota_facturado_mes`, Holded desde abril; solo a quien ve la cuota). No cambian, y se dice: caja, cobros, impagos, cuota de octubre, los 20 principales; horas y rentabilidad (septiembre).
- **A medio «gasto medio — al mes» · no aplica aquí (es de mi_dia_bloques.js).** Finanzas ya daba 47.115 €/mes. Añadido `caja.meses_31ago` y `gasto_medio_texto`; el parche exacto está en `../dudas_pintura.md` (R12).
- De paso: Sofía ya no ve tiles de horas vacíos en Dinero por cliente (la clave `coste_horas` venía siempre, aunque fuese vacía).

## V2 · carril V2-C2 · Finanzas, Dinero por cliente, Ventas de RO, Setters, Prospección (3-oct)
- **A-M3** «▲ 19 %» frente a «▲ 12 %»: dicho en pantalla. Dinero por cliente compara con ESTOS MISMOS clientes y añade la cifra de toda la empresa (la de Finanzas); Finanzas dice «toda la empresa, también clientes que ya se fueron». «Sin línea en facturación»: un solo recuento (7, el del chip) partido por su porqué (2 altas firmadas = las de Finanzas).
- **A-A6** Sofía: «No ves este dato por tu puesto: el importe de Meta lo ve dirección. Pídele la cifra a Tomás»; fuera «(panel financiero, FIN §6)» del generador y del dato. Mi día: pedido.
- **A-M2** coste por cliente: misma cuenta y regla (septiembre 735 € en las dos); Ventas, con otro periodo, dice al lado «Septiembre entero: 735 € (13 firmados), la cifra que manda en el Panel de dirección».
- **C-14** «citas ya pasadas y marcadas» frente a «citas agendadas». **C-6** «Reuniones del vie, 2 oct (3) · datos de esa lectura» un sábado. **A-M13** calendario administrativo con el hoy real (un día 3 no dice «Día 2 · hoy»). **M7** fuera «Promethean» y «v29/v30».
- **C-11 setters** siguiente llamada = la más urgente (confirmación delante solo si es hoy), el día de la cita con el hoy real, botón «Ver los 22 de «Llamar ya»» · **C-32** «Ver completo».
- **C-2/C-3 outreach** Eulimar ve solo sus campañas (12 clientes de su cartera) y «Ver respuesta» con nombre, correo y extracto (por `ver_dato`, con rastro); recorte del servidor: R16 (dudas V2). «Elegir todas» a 20 px.
- **C-28** «Pinheiro Leonardo⁷» → sin superíndice (Panel). **C-12** ⌘K y **C-15** consejos de ventas: de `ayudas.js` / `ia.py`.
- **A-M1** beneficio en Mi día y **M17** móvil largo: pedidos (dudas V2).

## Finanzas v3 (3-oct) · beneficio claro, equipo mes a mes, cuadre de fuentes e impagos
- **Nuevo generador** `fuentes_dinero/generar_cuadre.py` (después de `generar_dinero.py`; solo GET, Holded mes a mes porque corta en 500): `data/finanzas/cuadre.json` (solo dirección), `cuadre_facturacion.json` (dirección + administración, solo lo facturado), `impagos.json` (dirección + administración) e `impagos_clientes.json` (ficha y finanzas: el account ve que hay impago; el importe va en `cuota_vencida` y servir.py lo quita a quien no ve la cuota). Estado manual de cobro en `fuentes_dinero/impagos_estado.json` (Taller del Patinete, IP Forense).
- `generar_dinero.py`: los impagos leen también las facturas sin cobrar de ene-2025 a mar-2026 (salían 3, 1.236,90 €, que no estaban). Alertas y Mi día regenerados: 11 impagos en las tres pantallas.
- **Pantalla:** Resumen abre con «Beneficio mes a mes» (barras verde/rojo, 2025 en gris estimado, margen % con eje propio, conmutador con/sin gasto sin factura, desglose al pasar el ratón). Altas y bajas en su gráfico (altas arriba, bajas abajo, neto en línea) y activos aparte; tabla con altas, cuota nueva, bajas, cuota perdida y neto en columnas. Resultados: «Coste del equipo mes a mes» por fuente. Pestañas nuevas «Impagos» y «Cuadre de fuentes» (Sofía: «Impagos» y «Cuadre de facturación»). La ficha del cliente avisa del impago.
- **Comunes:** `grafico()` admite `barras.clase`, `barras.leyenda`, `barras.nombreDe`, `barras2`, `serie.escalaPropia` (eje derecho), `detalle(i)` y `barrasPrimero` (compatibles); clases `.barra.pos/.est` en estilos.css. `reglas_permisos.json`: 4 ficheros nuevos y acciones `impago_estado` y `cuadre_decision`.
- **Pruebas:** `pruebas_e0.py --puerto 9200` TODO BIEN (diseño estricto) · `pruebas_seguridad.py` TODO BIEN (bloque «FIN v3») · `pruebas_coherencia.py` con dos comprobaciones v3 en verde (beneficio igual en Finanzas, Mi día y Panel; impagos = alertas = «Lo mío») · `escaner_secretos.py --proyecto` limpio. Capturas en `capturas/_finanzas_v3/` (tomas y sofia a 1440, 1024 y 390; sin desborde, 0 letras < 12 px, 0 errores de consola).
- **Decisiones para Tomás:** `../45_CUADRE_FINANZAS.md` (12 incongruencias con propuesta).

## Paneles v4 (3-oct) · Finanzas y Dinero por cliente al nivel de los mejores (48_BENCHMARK_DASHBOARDS.md)
- **Comunes nuevos** (dueño ahora: este carril): `tarjetaKpi`, `selectorComparar`, `lineaComparacion`, `minilinea`, `cascada`, `barrasGanadoPerdido`, `mapaCalor`, `barraObjetivo` (+ `bandasObjetivo`, `estadoObjetivo`), `previsionCaja`, `barrasDivergentes`, `enlaceFuente`; `barraApilada` con `rojo-claro`. Referencia y umbrales con fuente en `modulos/dinero_v4.js`. Detalle en LEEME › «Paneles v4». Catálogo vivo en Sistema › Componentes.
- **Finanzas · Resumen (Tomás):** «Comparar con» (mes anterior · mismo mes 2025 · plan) · beneficio de agosto 3.859,87 € (−3.428,03 € con gasto sin factura; ene-ago 93.492 / 76.392 €) con su minilínea · cuota contra el plan de octubre (95.921 €, bandas Databox) y el objetivo de diciembre · 6 tarjetas: margen bruto media 3 meses 41,6 % (ene-ago 37,3 %), meses de caja 1,3, vencido 17.967 €, cuota recurrente 67.291 €, peso del equipo 67,8 %, retención neta 60,5 % **(fórmula pendiente de confirmar por Tomás)** · lo que pide decisión · cascada del beneficio y del plan al real (−700 → +1.348 → +3.212 → 3.860) · puente de la cuota (mes a elegir, 12 meses con octubre rayado, fuga: rebajas 4,0 %/mes y 30.940 € en 12 meses frente a bajas 3,3 % y 20.727 €) · caja a 90 días con el mínimo de 2 meses (94.230 €) y sus supuestos · cobros por antigüedad · peso del equipo mes a mes. Cada bloque con su acción (ver cobros, reclamar, pedir a Mili que revise las rebajas — Hecho · Deshacer, simulado).
- **Sofía:** sus 6 cifras de cobro con línea, umbral y fuente; sin beneficio, margen ni equipo (comprobado en pantalla). Impagos: barra apilada por antigüedad.
- **Dinero por cliente (Tomás, Mili; Coti hoy solo recibe 1 cliente):** margen de la cartera al mes (Tomás con coste real 39.485 €; a tarifa 769 €) · cuota media, tarifa efectiva 31,91 €/h, 24 de 54 en pérdida a tarifa, horas imputadas 51,7 % (gris) · ranking divergente (a tarifa / con coste real) · concentración (2,3 / 11,4 / 22,8 %, misma base que Finanzas) · valor de vida 11.531 €, recuperación 1,3 meses, 5,9 veces (gris: referencia SaaS) · cohortes (`data/dinero_cliente/cohortes.json`, nuevo) · tabla plegada.
- Pruebas: `pruebas_e0` TODO BIEN · `pruebas_seguridad` TODO BIEN · `pruebas_coherencia` 2 errores de datos ajenos (producción/bloqueos e incidencias «Revisa») · escáner limpio en lo mío (avisa de `fuentes_ia/probar_gasto.py`, claves simuladas de otro carril, 04:54). Capturas `capturas/_paneles_v4/` (tomas y sofia, Finanzas, Impagos y Dinero a 1440/1024/390; mili; catálogo): sin desborde, sin letra < 12 px, consola limpia.
