# _ESTADO · Panel de dirección (carril C2) · 2-oct-2026

**Petición de Tomás:** «arrastra todo lo que ya tenemos en el panel de control de toda la empresa […] volcado a esta herramienta, pero solamente con acceso para mí».

**Hecho.** `#/panel-direccion`, grupo «Dinero», solo puesto dirección (Tomás). Nada escrito fuera; nada publicado.

## Cómo está hecho

- **No se recalcula nada.** `fuentes_panel_direccion/generar_panel_direccion.py` abre una copia de `~/Downloads/PANEL_RESULTADOS_RO_2026-09-18/ENTREGA/panel_v2.html` (la v29/v30 del artefacto privado `WeCVRWFTxD3MMdU2jb9siH`, salida de `build_dataset_ro.py` → … → `render_v2.py`) con Chrome sin ventana, le pega `extraer.js` y deja que **el propio `render()` del panel** pinte cada pestaña: 6 de la empresa y 6 de la captación × 5 periodos (septiembre, octubre en curso, todo desde el 1-ago, desde el 14-sep, 7 días). Guarda el HTML de cada pestaña (clases con prefijo `px-`, sin scripts ni manejadores) en `data/panel_direccion/`. Paridad por construcción: mismo código, mismos datos.
- **El módulo** (`modulos/panel_direccion.js`) lo vuelve a montar con la carcasa de la app: cada panel del original pasa a `panel()` con icono, cada fila de indicadores a `tiles()`, la cadena del coste a tiles pulsables, los avisos «Ver la agenda →» saltan de pestaña, y gráficos, tablas y notas se quedan como estaban con su hoja de estilos (`modulos/panel_direccion_estilo.js`, generada, ámbito `.pdir-c`).
- **Tres mundos (chips que se quedan):** La captación (primero: es lo de cada día) · La empresa · Panel original: la app no admite marcos ni scripts en línea (CSP de E0, ronda 6), así que el v30 con sus filtros finos (capa, fechas a medida, por cohorte, buscadores, orden de tablas) se abre en su artefacto privado o se descarga como .html (con rastro).
- **Finanzas (M19) no se duplica:** arriba de «La empresa», las cifras en vivo de M19 (`data/finanzas/direccion.json`) (cuota firmada, si firman, caja, beneficio del mes). Ingresos, Gastos y Caja y cobros llevan a la pestaña de Finanzas y dejan la versión del panel plegada. M19 ya enlaza a `#/panel-direccion` (solo en la vista de Tomás).
- **Error de divisa (25_AUDITORIA_CIERRE_SOFIA.md):** el v29 copia el cierre de Sofía, que suma las facturas en dólares como euros. Gasto, beneficio, margen, peso del equipo y meses de caja salen **solo** de M19 (`data/finanzas/direccion.json → direccion[0]`, recalculado; antes estaba en `finanzas.json`, el módulo lee los dos). En el v29 portado: los bloques que dependen del gasto se pliegan con aviso, los tiles de beneficio y margen se cambian por la cifra buena con «el v29 decía…», las frases con margen o beneficio se retiran con la cifra buena al lado, y el tile «Margen que deja» de la captación va en ámbar. No se usan el «1,4 meses de caja» ni los cobros de 1,17 M€.
- **Coste del equipo por persona** (regla nueva del 2-oct, dirección y RRHH): lista de las personas activas; cada una se abre con «Ver coste» → confirmación → `ctx.verDato({ almacen: 'sueldos/_privado/sueldos', ref: <persona>, campo: 'meses' })` (último mes con dato), con rastro. La hoja «Cuentas bancarias» no se lee nunca (E0 no la carga). En las capturas no sale ningún importe.

Rehacer: `python3 fuentes_panel_direccion/generar_panel_direccion.py` (3 s). Si cambia el panel: antes `INFORME_FINANCIERO/rehacer_v2.sh` en la carpeta del panel.

## Permisos (comprobado contra `servir.py` en el puerto 8793, base de pruebas aparte)

| Quién | Menú | Pantalla | `/api/modulo/panel_direccion/*` |
|---|---|---|---|
| Tomás | sí | entera | 200 |
| Mili | no | «no es de tu puesto» | **403** |
| Sofía | no | «no es de tu puesto» | **403** |
| Lucía, Valeria, Yessica, Constanza, Ana (setter) | no | «no es de tu puesto» | 403 |
| Mili «como Tomás» | — | **«Solo Tomás»** (no pinta ni pide datos) | 200 en el servidor → pedido a E0 (`solo_real`, ver `dudas_pintura.md` D-P-C2) |

Consola sin errores con `?yo=tomas, mili, lucia, valeria, yessica, constanza, setter_ana, sofia` y Mili «como Tomás». Recorrido completo como Tomás a 1440 y 390 px: 5 periodos, 6 + 7 pestañas, aviso que salta a «Agenda», «Ver coste» de una persona y la descarga del panel original: 0 errores, sin desplazamiento horizontal (390 = 390). `escaner_secretos.py`: limpio.

## Tabla de paridad · panel v29/v30 → app

| Panel v29/v30 | Bloques del original | En la app | Estado |
|---|---|---|---|
| **Empresa · Resumen financiero** | La empresa en 30 segundos · 6 cifras · Lo que hay que mirar · 13 indicadores destacados | La empresa › Resumen financiero (nativo): 7 tiles de dinero ene-ago **de M19**, mes a mes 2026 de M19, 12 indicadores del v29 que no dependen del gasto (cuota de octubre, ingresos 12 m, activos y rotación, concentración, crecimiento, retención neta, LTV, vida, coste por cliente, días de cobro) + el v29 entero plegado | **Corregido respecto al panel v29 por error de divisa** (gasto, beneficio, margen, peso del equipo, meses de caja, meses para recuperar, valor frente a coste) |
| **Empresa · Ingresos** | Mes a mes desde el inicio · Por año · Tabla mes a mes · Puente de la cuota | Enlace a Finanzas › Ingresos y clientes (M19, en vivo) + versión del panel plegada | Igual (ingresos y cuota valen) |
| **Empresa · Clientes** | Altas y bajas · Top 20 · Concentración · Cohortes por trimestre · Por qué se van · Bajas una a una · Activos uno a uno | La empresa › Clientes (portado entero, con nombres) | Igual |
| **Empresa · Gastos y proveedores** | Gasto por categoría 2026 · Por año · Top 20 proveedores | Enlace a Finanzas › Resultados y equipo + versión del panel plegada y con aviso en cada bloque | **Corregido por divisa** (se lee en M19) |
| **Empresa · Caja y cobros** | Saldo por cuenta · Entradas y salidas reales 2026 · Antigüedad de lo pendiente | Enlace a Finanzas › Cobros y caja + versión plegada; «Entradas y salidas» con aviso | Saldos iguales; **cobros 1,17 M€ no se usan** (traspasos internos) |
| **Empresa · Plan y año** | Cuenta de resultados · Real frente a presupuesto · Por año · Camino a 150.000 € · Cuota a fin de mes · Embudo hacia atrás · Equipo para el plan · Ingresos y gastos · De dónde sale lo firmado · Cierre del año · Lo que hay que mirar · Cuota cobrada | La empresa › Plan y año (portado entero). Cuenta de resultados, Real frente a presupuesto, Por año, Ingresos y gastos, Cierre del año y Lo que hay que mirar: plegados con aviso; «Beneficio hasta agosto» cambiado por el de M19; la frase con margen y beneficio, retirada con la cifra buena | **Corregido por divisa** en esos 6 bloques; el resto igual |
| Equipo (sueldos) | — (el v29 solo agregado) | La empresa › Coste del equipo: por persona con «ver datos» y rastro (almacén de E0) | Nuevo (regla del 2-oct) |
| **Captación · Resumen** | Lectura · cadena del coste y límite de 700 € · Cuota acumulada con curva · Pendiente de firma · Retorno de la publicidad (+ supuesto 3 meses y vida medida) · Qué mirar hoy · Embudo paso a paso · Ritmo de gasto · Retorno con la vida medida · Qué haría yo esta semana | Cadena en 7 tiles de la app (pulsables) + pestaña Resumen portada entera | Igual; tile «Margen que deja» en ámbar (usa el margen del v29) |
| **Captación · Publicidad** | Día a día · Por capa · Por anuncio (todos, con CTR y coste por clic) · El curso · Todo lo que ha entrado en GHL · El CRM entero · Desgaste semanal | Pestaña Publicidad (portada, con todos los anuncios desplegados) | Igual |
| **Captación · De qué anuncio** (v30) | Por anuncio · Una a una (atribución exacta) | Pestaña De qué anuncio | Igual |
| **Captación · Agenda** | Qué pasó con las citas · Según la distancia · Recordatorio · Llamadas de Zadarma · Precall pieza a pieza · Cuestionario · Casos de éxito · A qué hora se reserva · Formulario a medias | Pestaña Agenda | Igual |
| **Captación · Ventas** (+ Reuniones) | Circuito persona a persona · Propuestas, acuerdos y firmas · Todos los potenciales (los 96, desplegados) · Ventas RO hoy · Cohortes semanales · Velocidad · Reuniones: nota por fase, cómo acaban, lo que se repite, una a una | Pestaña Ventas | Igual (buscadores y filtros por fase: en el panel original) |
| **Captación · Operativa** (Rapidez + Medición) | Cuánto se tarda en contestar · Horario · Canal · Por persona · Sin fuente · Fuentes y comprobación · Salud de la medición | Pestaña Operativa | Igual |
| Filtros: capa · fechas (este mes, mes pasado, todo, desde el 14-sep, 7 días, 3 días, a medida) · por fecha / por cohorte | — | 5 periodos con `selectorPeriodo` (todas las capas, por fecha del hecho); el resto, en «Panel original» | 3 días, a medida, capa y cohorte: en el artefacto privado o el .html descargado |
| Pie con la frescura de cada fuente | — | Pie con `frescura()` de las 8 fuentes y la hora de la foto | Igual |

## Cifras contrastadas (5)

| # | Cifra en la app | Fuente contrastada a mano | Resultado |
|---|---|---|---|
| 1 | Inversión en Meta, septiembre: **9.559 €** | `_crudo/meta_ads_daily*.json` anuncio × día sin duplicar: 9.559,20 € · M19 `admin.meta_sin_factura.gasto_meta` 9.559,2 € | Cuadra |
| 2 | Citas reservadas, septiembre: **165** | `dataset_ro.json → citas` con reserva en septiembre, sin talleres ni canceladas: 165 | Cuadra |
| 3 | Firmados: **13** en septiembre, **15** hoy | Columna «Cliente» de Ventas RO en `_crudo/opps.json`: 15 tarjetas; con firma en septiembre: 13 | Cuadra |
| 4 | Cuota mensual acumulada: **22.050 €** | 15 firmados × 1.470 € (`sale.v` de cada tarjeta) | Cuadra |
| 5 | Empresa en vivo: cuota firmada **67.291 €**, si firman **73.171 €**, caja **62.109 €**, beneficio ene-ago **93.775 €** | `data/finanzas/direccion.json → direccion[0]` (M19, 17:13) | Cuadra con M19 (y con lo que pidió el coordinador). El v29 decía caja 60,6 mil € (Holded del 30-sep: otro día) y beneficio 54.425 € (error del dólar) |

## Pendiente

- E0: `solo_real` en `datos_de_modulo` para que «ver como Tomás» no reciba los datos (hoy solo los esconde el módulo); icono `medidor` en `ICONO_MODULO`.
- La foto del panel es la del 2-oct 04:47. Para tenerla al día: cadena del panel (`descarga_ghl.py` … `rehacer_v2.sh`) y luego el generador de este módulo. No se ha lanzado la descarga de GHL ni de Meta desde aquí.
- Cuando el cierre de septiembre venga con la conversión del dólar, rehacer el v29 y quitar las guardas que sobren.

## N6 · Diseño 10/10 (2-oct, noche) · nota que me pongo: **8,5 / 10** (auditoría 30: 4,5)

- **Fuera la hoja propia.** `panel_direccion_estilo.js` queda vacío (`CSS_PANEL = ''`) y el módulo no inyecta ningún `<style>`: 0 tamaños fuera de escala, 0 colores sueltos, 0 sombras/radios con número (`pruebas_diseno.py --estricto` en verde). Cada pieza del panel (clases `px-*`) se traduce a componentes comunes: `panel()`, `tiles()`, tablas `table.densa.apilable` (15 filas + «Ver las N filas»), `barraProgreso` (listas de barras, barras partidas, celdas con barra), `chipEstado` (etiquetas y píldoras), `vacioLinea`, `details.que-es` («Cómo se cuenta»), `meta-linea`, `rejilla`.
- **Un solo motor de gráficos.** Los 10 gráficos del panel (día a día, cuota acumulada, coste por cita, altas y bajas, concentración, ingresos por mes, gasto por categoría, cuota hacia 150.000 €, ingresos y gastos, horas de reserva) se vuelven a dibujar con `grafico()`: se leen del SVG del panel (ejes, barras, líneas y puntos; los `<title>` cuando los hay). Comprobado: inversión de septiembre suma 9.559 €, citas 165, cuota acumulada 19.110 €, coste por cita al céntimo. Apiladas → total en barras + una línea por parte (máx. 4 series; en «Gasto por categoría» del v29, plegado, se quedan fuera Publicidad propia y Estructura del gráfico). Letra 12 px a todos los anchos. Si un gráfico no se puede leer, sale el SVG tal cual con la letra a 12 px reales (hoy no pasa en ninguno).
- **Arriba lo que manda.** Coste por cliente firmado con `cifraPrincipal` y `colorCifra('coste_cliente')` (735 € en ámbar, igual que en Ventas de RO), barra contra el límite de 700 €, y el resumen a 15/22 con cifras en 600 (antes 28 px). Debajo, la cadena del coste en 6 tarjetas (3 + 3) con su «▲/▼ frente a los días previos» (antes escondido). En la pestaña Resumen, «Qué mirar hoy» sube lo primero.
- **Fuera de la vista principal** (menú «Más»): «Panel original y descarga» y «Abrir el panel privado». Fuera la píldora «Solo tú» (lo dice el subtítulo). Periodos con nombre corto (Sept. · Oct. · Desde 1-ago · Desde 14-sep · 7 días) para que quepan en una fila a 390 px; el nombre largo va en la línea de comparación.
- **Periodo:** no usa `usa_periodo`: son 5 fotos hechas por el generador, no rangos; «desde el 1-ago» y «desde el 14-sep» no existen en el periodo común y se perderían.
- **Paridad (lo pedido: no perder ninguna pestaña ni dato).** Las 13 pestañas (6 de captación × 5 periodos + 7 de empresa) siguen; «De qué anuncio» intacta. `capturas/_n6/n6_paridad.py` saca todas las cifras de cada pestaña antes y después y `n6_comparar.py` las cruza (`paridad_antes.json` / `paridad_despues.json`). Las que «faltan» son repeticiones que ya no se pintan dos veces: la cadena oculta del Resumen (salía en tarjetas y en una fila escondida), los números dentro de las barras partidas (siguen en su leyenda), las horas del eje («0 h, 3 h…», ahora en el gráfico) y «(M19)» en un título. Se ha añadido: el «frente a los días previos» de la cadena y «Corrección por divisa» como tarjeta.
- **Comprobado:** Tomás a 1440, 1024 y 390 en las 13 pestañas: sin scroll horizontal, 0 textos < 12 px, 0 errores de consola. Capturas en `capturas/_n6/panel_direccion/` (y `pestanas/`: `t_` 1440, `k_` 1024, `m_` 390).
- **Por qué no un 10:** la pestaña Ventas sigue siendo muy larga (274 reuniones plegadas, una por línea); las etiquetas de las barras van en una columna fija de 150 px que parte palabras como «Siguen en curso · 21,9 %»; el gráfico de «Ingresos y gastos» no dibuja la línea «Sin firmas nuevas» (viene en la tabla); el generador vuelve a escribir la hoja vieja si se relanza (ver dudas_pintura.md, D-P-N6).

## N6 · El generador solo produce datos (2-oct, 20:30)

- **Arreglado D-P-N6 (lo del generador).** `generar_panel_direccion.py` ya no escribe `modulos/panel_direccion_estilo.js` ni toca plantilla: fuera `hoja_estilos()`, `ESTILO_JS` y `CABECERA`. Solo escribe en `data/panel_direccion/` (8 JSON), de forma atómica (carpeta temporal dentro de `data/` y `os.replace` fichero a fichero).
- **Puerta antes de escribir:** si falta o sale vacía cualquiera de las 6 pestañas de empresa o de las 6 × 5 de captación, si el panel no trae la etiqueta `atr` («De qué anuncio» / Atribución: pasaría si alguien rehace la plantilla con `montar_v2.py`), si falta un rango o si no se lee alguna de las 5 cifras de paridad → sale con código ≠ 0 sin tocar nada y la tubería conserva el último dato bueno.
- **Probado:** copia de `data/panel_direccion/` en el bloc temporal de la sesión; `python3 despliegue/tuberia.py --crudo --solo panel_direccion --sin-avisos --forzar` → ok en 5,3 s. Los 8 JSON son idénticos a la copia (salvo `generado`); `panel_direccion_estilo.js` no cambia (mismo sha). `n6_paridad.py` contra 127.0.0.1:8916 y cruce con `capturas/_n6/paridad_despues.json`: 37 de 37 estados, 33.436 cifras, 0 diferencias salvo la hora de «montado en la app» (19:04 → 20:29). Las 5 «De qué anuncio» están. `pruebas_diseno.py --estricto` 42/42 limpio, `pruebas_e0.py` TODO BIEN (127.0.0.1:8917), `pruebas_coherencia.py` 0 errores. Servidores cerrados.
- **Pendiente de otros (no lo toco, son ficheros comunes):**
  - **C5 · `despliegue/pasos.json`, paso `panel_direccion`:** en `salidas` sigue `modulos/panel_direccion_estilo.js`. Ya no es una salida; se puede quitar (no rompe nada: solo hace que la instantánea lo copie de más).
  - **E0 · los 4 ajustes de D-P-N6 siguen sin hacer** (comprobado 20:30): (1) `.embudo-barras .et` sigue con la cifra a 54 px fijos (estilos.css l. 563; móvil 40 px, l. 573) → `minmax(54px, max-content)`; (2) `.que-es summary { width: max-content }` sin `max-width: 100%` (l. 546); (3) `selectorPeriodo` sigue sin envolver los botones a 390 px; (4) `tile()` sigue pasando el contexto por `limpiaTexto()` sin opción `crudo: true` (componentes.js l. 921).

## R12 · arreglos tras la auditoría final (2-oct, noche)
- **A-A6 · arreglado.** «Margen que deja, vida medida» se rehace con el margen bruto ÚNICO de Finanzas (`direccion.kpi.mb` = 37,3 %) y las tres cifras que enseña el propio panel: 22.050 €/mes × 7,2 meses × 37,3 % − 11.085 € = 48.132 € (antes 34,8 mil € con el 29 %). Si falta el margen de Finanzas, sale «sin dato», nunca la cifra mala. Ningún texto visible del panel da ya el 29 % (solo dentro de «Ver la versión del v29», con su aviso de no usar). `pruebas_coherencia.py` lo comprueba. Generador sin tocar: estilos y «De qué anuncio» intactos.

## V2 · carril V2-C2 (3-oct)
- **A-M2** coste por cliente: dice que es la misma cuenta y color que Ventas de RO con el mismo periodo · fuera «v29/v30» de lo que se lee («panel antiguo») · nombres sin superíndices.
