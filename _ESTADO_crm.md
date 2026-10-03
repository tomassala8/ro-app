# _ESTADO · M7 «Salud del CRM» (id de ruta `salud-crm`) · 2-oct-2026

## Hecho
- `modulos/crm.js` (ruta `#/salud-crm`, detalle `#/salud-crm/<id de subcuenta>`). Alta en `modulos/indice.js` (estado «hecho»; el id `salud-crm` ya existía con su icono `base`).
- `fuentes_crm/generar_crm.py` → `data/crm/crm.json` + `data/crm/_privado/leads.json`. Copia en bruto (no se sirve) en `fuentes_crm/_crudo/ghl_vivo.json`; `--desde-crudo` regenera sin llamar a GHL.
- `reglas_permisos.json`: `datos_de_modulo["crm/crm"]` (subcuentas, leads, citas y hallazgos sin cliente de la app, solo a quien lo ve todo) y `almacenes_privados["crm/_privado/leads"]` (tipo `lead`: especialista y account de su cartera, con rastro).
- Lectura GHL en vivo el 2-oct a las 15:41: 66 subcuentas, 968 lecturas, 1 renovación de la llave (`app.acceso()` la guarda sola en el llavero). Nada escrito.
- Pantalla (orden por frecuencia): cifras del día (8 tiles) → «Lo primero hoy» (7) → pestañas Subcuentas · Leads sin tocar · Citas sin estado · Por especialista · Flujos, WhatsApp y correo · Montajes de altas → hallazgos → indicadores del catálogo con «¿Qué es?» y Fase 2.
- Botones en simulación (`ctx.accion`): mover oportunidad, nota, marcar «se presentó / no vino» (aviso: manda WhatsApp al lead), reprogramar cita, tarea al account, escalar a Jessi, aviso a Agus, proponer reparto a Mili, casilla «formación dada». «Ver datos» del lead por `ctx.verDato` (rastro).

## Resultado a 2-oct (todas las subcuentas de clientes)
20 subcuentas encendidas, 2 en verde (10 %) · 240 leads en 30 días, 190 sin ningún intento apuntado en GHL > 24 h · primer intento < 1 h: 5,3 % (12 de 225) · 34 citas sin estado en 14 días; 62 citas pasadas en 30 días y **0 marcadas** «se presentó» o «no se presentó» (la asistencia no se puede calcular en ninguna subcuenta) · WhatsApp fallido 11 de 163 · carga: Gustavo 19 clientes (tope 16), Jessi 8; 4 encendidas sin especialista (Adade, Akua, Christian Sánchez, Torrevieja).

## Hallazgos señalados (con prueba en GHL)
- **GAC**: Meta dio 101 leads en 7 días y en GHL hay 1 contacto en 30 días (creado a mano) → integración rota, aviso a Agus.
- **ECOM**: 18 citas sin estado en 14 días (39 en 30 días; 113 citas en 90 días).
- **Innova Scala**: 4 citas sin estado en 14 días (8 en 30) y 32 leads sin tocar.
- **Consulting F**: 21 leads en 30 días y 0 citas en 90 días. También Akua, Torrevieja, Laver, Aster, Adade, Orejana, Benavides.

## Cifras contrastadas con su fuente
1. GAC: `captacion.json` (Meta, 7 días) = 101 leads; `/contacts/search` en vivo de la subcuenta BqXT3… = 1 contacto en 30 días, origen «CRM UI, manual» → 0 leads nuevos en GHL. Coincide con el aviso de captacion.json («llegaron 0»).
2. ECOM citas sin estado 14 días: módulo 18; `captacion.json` (14:25) decía 17. La ventana de 14 días se ha movido 1 h 15 min: entra una cita más. Explicado.
3. Innova Scala leads 30 días: módulo 40 = `/contacts/search` total 40 (sonda a mano: 21 Instagram, 9 formulario lead magnet, 4 sin origen, 3 calendario…).
4. Consulting F: 0 citas en 90 días en el módulo = motivo crítico de `captacion.json`.

## Pruebas (Chrome sin cabeza, servir.py en 127.0.0.1:8797)
- `?yo=tomas, mili, lucia, valeria, yessica, constanza, setter_ana, gustavo` a 1440 y 390 px: sin errores propios ni desplazamiento horizontal. Setter Ana: «no es de tu puesto». Los únicos avisos de consola son 404 de módulos de otros agentes dados de alta en `indice.js` sin fichero todavía (incidencias, dinero_cliente, personas, finanzas, decisiones).
- Recorte del servidor (`/api/modulo/crm/crm`): Tomás, Mili, Jessi y Constanza (proyectos) 66 subcuentas; Gustavo 13; Lucía 6 y 0 sin cliente; Valeria (resumen) 38; setter 403.
- Lucía abriendo la subcuenta de ECOM (no es suya): pantalla de «no es de tu puesto». «Ver datos» funciona para Gustavo y Lucía en sus leads (queda en el rastro); Jessi como jefa los ve enmascarados (salvo sus 8 clientes).
- Acción simulada como Gustavo («Escalar a Jessi»): «En la cola (simulación)».
- Escáner de secretos: `data/crm/crm.json` limpio (el escáner global sale en 1 por `data/ajustes/conexiones.json`, de otro módulo).
- Capturas: `capturas/crm/` (28: 8 personas × 2 anchos, detalle ECOM, GAC, Consulting F, cada pestaña).

## Falta / espera
- **W3**: `workflows.readonly` (hoy GHL responde 401; además «Needs Review» no está en la API), escritura de citas, oportunidades y notas, contacto de prueba diario (circuito y aviso < 1 min).
- Número de WhatsApp conectado: no medible por API. Entregabilidad de clientes: GHL no da rebote; se enseña el 2,4 % de RO (1-oct) y los correos marcados como fallidos.
- «Intento» = solo lo que pasa por GHL: si el despacho llama desde su móvil no consta (lo dice la pantalla). Por eso 190 sin tocar es un techo, no la cifra exacta.
- Valeria (resumen) recibe del servidor las filas de leads y citas sin datos personales; la pantalla no se las enseña. Si se quiere cortar en servidor, hace falta un recorte por nivel (E0).

## Dudas para Tomás / E0
- El catálogo marca «Carga por especialista» como «todavía no» (faltaba la tabla de asignaciones). Ya existe en borrador: lo pinto «a medias». Recomendación: E0 actualiza el catálogo.
- 21 subcuentas sin cliente de la app (más 7 de prueba o internas) (Torrevieja, Benavides, Vallparadís, Gestiona, ISE…): solo las ve quien lo ve todo. Recomendación: Agus las empareja en `emparejamientos_manual.json`.
- Revisión con Coti, Mili y Agus (R15): pendiente.

---

## Ronda 3 de arreglos (2-oct, 17:00-17:40) · lectura nueva de GoHighLevel a las 17:23 (927 lecturas, solo lectura)

Cifras nuevas: 16 encendidas, 2 en verde (12,5 %) · 211 leads en 30 días, 182 sin tocar > 24 h · primer intento < 1 h 4,3 % · 31 citas sin estado en 14 días (ECOM 17 e Innova 5: ahora coinciden con Captación) · 133 oportunidades paradas 72 h (de 176 del último mes).

| Fallo de la auditoría | Qué se ha hecho |
|---|---|
| 28 · Lobo: 7 contactos de demostración y 3 de FisioExpo contados como leads (E-08) | **Arreglado.** Una sola regla de «lead que llega», en `clasificar()`: contacto nuevo cuyo origen es un formulario o un anuncio. No cuentan los creados a mano, los importados, los de prueba (origen, etiqueta o correo de prueba), los que no son leads (candidaturas, cursos, clientes) ni los de otro negocio. Los de otro negocio van en `fuentes_crm/exclusiones.json` (Lobo: FisioExpo, contactos y calendario). Lobo da ahora 2 leads (7 de prueba y 3 de otro negocio fuera). El detalle dice cuántos no cuenta y por qué, y avisa del calendario ajeno |
| 28 · GAC «integración rota» con 1 contacto en toda su historia (E-13) | **Arreglado.** Si la subcuenta tiene menos de 5 contactos en total → «subcuenta sin usar: el cliente no usa GoHighLevel, confirmar el servicio». Sale en gris (no en rojo) y `leads_ghl_7d` = sin dato. Con eso la verdad única ya no ve una fuga en GAC. Sigue en crítico por los correos |
| 28 · «Leads que llegan»: Captación cuenta oportunidades y CRM contactos (E-03) | **Arreglado de mi lado.** CRM publica `leads_ghl_7d` con la regla única y la verdad lo lee de aquí. Que Captación lo tome de `crm.json` le toca a su dueño |
| 28 · Ventanas 7×24 h con hoy dentro (E-15) | **Arreglado.** Días naturales cerrados en hora de Madrid, sin el día en curso: 7 días = 25-sep a 1-oct, 30 días = 2-sep a 1-oct; citas 14/30/90 días igual. Las horas se pintan en hora de Madrid (`zoneinfo`) |
| 28 · Akua «ninguna cita en 90 días» con demos reservadas fuera (E-14) | **Arreglado.** Si los leads vienen de un formulario de cita y el calendario está vacío → «las citas se reservan fuera de GoHighLevel», informativo, no rojo |
| 26 C · atajos a contacto y oportunidad | **Arreglado.** «Abrir contacto en GHL» en cada lead, cita y oportunidad parada. La oportunidad abre el contacto, porque no hay enlace a una oportunidad suelta. Pestaña nueva «Oportunidades paradas» (lectura en vivo de las oportunidades abiertas) con «Mover» simulado. Se mantienen subcuenta, conversaciones, calendarios, oportunidades (lista), flujos y WhatsApp |
| 22 B-02 · GAC rojo en CRM y «Bien» en Captación | **Arreglado de mi lado.** GAC ya no sale como fuga. La regla de integración es la de la verdad (≥ 10 leads de Meta, grave si llega menos de la mitad, leve si menos del 80 %) |
| 22/29 · tabla cortada a la derecha | **Arreglado.** Fuera dos columnas de la tabla de subcuentas (las paradas y WhatsApp tienen su pestaña) y desplazamiento horizontal dentro del panel |
| 29 · «Gustavo 19» (nombre como cifra), «(propuesta )», «cohorte», «Lo arregla: Tomás (permiso W3)», «GHL» en títulos | **Arreglado.** Nueva tarjeta «Especialista con más carga · 19 de 16», con el nombre debajo. Textos llanos, sin códigos (D-xx, W3, nombres de fichero). «GoHighLevel» en títulos, avisos y subtítulos; «GHL» solo en tablas y botones |
| Regla 1 · verdad única | **Adoptada.** El account sale de `verdad.account` (generador y pantalla con `ctx.verdad`), encendida = `verdad.campana_activa`, y el detalle enseña la gravedad del cliente. `salud-crm` está en ADOPTADOS: `pruebas_coherencia.py` sin errores |
| Regla 2 · nombres | **Arreglado.** Personas con `ctx.nombre()` (Yessica con Y); el generador ya no escribe nombres, solo ids |
| Regla 6 · ceros y verdes falsos | **Arreglado.** Sin leads, sin citas o sin oportunidades → gris «sin dato», nunca verde |
| 27 M2/C · `crm/_privado/leads` decide el cliente con lo que manda quien llama | **Arreglado.** Cada lead guarda su `cliente_id` y el servidor lo saca de `crm/crm` (regla de E0). Probado: Lucía con un lead de ECOM y `cliente_id: gac` → 403 |
| 27 M6 · correos y teléfonos en `_crudo/` | **Arreglado** (E0 lo movió a `fuentes_crm/_privado/`; el generador ya escribe ahí). Se quitó un campo de correo que sobraba |
| 27 M7 · entran personas «dudoso» | **No aplica a este módulo.** Es de `servir.py` (E0) |
| 27 · nivel «resumen» quita los leads | **Arreglado** (E0, `filas_lead`). He añadido `oportunidades_paradas` en `reglas_permisos.json`. Valeria recibe 0 filas de leads |

Pruebas de la ronda (servidor en 127.0.0.1:8803, ya cerrado):
- `pruebas_coherencia.py`: 0 errores.
- `pruebas_e0.py`: 1 fallo, el escáner de `data/agenda/agenda.json`, que es de otro módulo. `crm.json` está limpio.
- 8 personas (Tomás, Mili, Lucía, Valeria, Yessica, Constanza, setter Ana y Gustavo) a 1440 y 390 px, más el detalle de Lobo, ECOM y GAC y todas las pestañas: sin errores propios ni desplazamiento horizontal. Solo salen 404 de módulos ajenos.
- Capturas en `capturas/crm/r3_*`.

**Aviso:** he relanzado `fuentes_verdad/generar_verdad.py` (de E0, solo lee) para que la verdad recoja la nueva cifra de GAC.

## N6 · diseño 10/10 (2-oct, noche)
**Qué cambió (solo presentación; datos, permisos, acciones y botonConfirmar igual).**
- Fuera la hoja propia (`estilos()` y `<style id="crm-estilos">`): solo clases comunes y `style` en línea con tokens (`--s-*`, `--fs-*`, `--t-*`, `--r-*`). `pruebas_diseno.py`: crm.js en «Limpios».
- Orden de la guía 3.6: «Lo primero hoy» arriba, luego 8 tarjetas (4 + 4; 7 = 4 + 3 sin jefatura) con etiqueta de una línea, cifra, una línea de contexto y adónde lleva (4 líneas). Sin dato = tarjeta gris con «Sin dato» pequeño, no un «—» de 24 px.
- Tabla de subcuentas: columna Subcuenta con mínimo de 200 px (el «sin cliente en la app» va en segunda línea), Estado con 240-320 px y el motivo en 2 líneas como mucho; la tabla se desplaza en horizontal en vez de aplastar. Estados con punto de color y texto en tinta; los números (sin tocar, citas) en negrita, sin pastilla roja en cada fila. Origen y Calendario con ancho mínimo.
- Todas las tablas paginan: 15 filas (8 en el móvil) + «Ver N más».
- Avatar «.av» de 10 px → `.av s` común (12 px). Barra de carga → `barraProgreso()` (con la marca del tope); embudo del detalle → `embudoBarras()`; carga → `esqueleto()`.
- Actuar: `<select>`/`<textarea>`/`<input>` propios → `chipsFiltro` (etapa) y `campoTexto` (nota y fecha), la vista previa de cada botón es la misma.
- Vacíos dentro de bloque → `vacioLinea()` (flujos, WhatsApp, embudo, encendidas sin especialista, altas, motivos).
- Hallazgos: 5 visibles (3 en el móvil) y el resto plegado; «Indicadores del puesto» y «Cómo se cuenta» plegados al pie. Altas: 6 fichas (3 en el móvil) y el resto plegado; las casillas que aún no se leen van en una línea aparte en vez de 4 pastillas grises.
- Pestañas más cortas («Paradas», «Especialistas», «Flujos y WhatsApp», «Altas») para que quepan en una fila a 1440.
- Medidas: alto en el móvil (Tomás) 12.400 → 5.655 px; pestaña Altas en el móvil 11.743 → 3.928 px; 15 pantallas (7 personas × 1440/1024/390, las que ven el módulo) con 0 problemas; detalle de subcuenta sin errores ni scroll horizontal.

**Periodo: no (`usa_periodo` no).** Todo son fotos de ahora con ventanas fijas (leads y citas de 30 días, citas sin estado de 14, «sin tocar» a las 24 h, paradas a las 72 h, embudo de 90 días); no hay series diarias. Se dice en llano en la línea de cabecera y en «Cómo se cuenta».

**Segunda pasada (por orden del coordinador).**
- Rojo con cuentagotas (guía 3.4) en las tablas de subcuentas, leads sin tocar, citas sin estado, paradas y las dos del detalle: de lo que el umbral pone en rojo, solo el tercio más grave (más leads y citas sin atender, o más horas esperando) lleva el punto rojo; el resto, ámbar. El texto («En rojo», las horas) no cambia. Explicado en «Cómo se cuenta».
- En el móvil, «Lo primero hoy» lleva un botón principal («Ver subcuenta») y el resto en «⋯» (un `<details>` con `.menu-flot` que se abre en su sitio, porque el panel recorta lo que flota y menuMas() pinta «null»).
- n6_cap.py (8888): 15 pantallas, 0 problemas; pruebas_diseno.py: crm.js limpio; pruebas_e0: todo bien.

**Nota contra la auditoría 30: 5,5 → 9.** Lo que queda depende de lo común: las tarjetas en el móvil son el carrusel común (la segunda se ve cortada) y los apuntes de ../dudas_pintura.md (`.primero li.gris`, `tile({ sinDato })`, ancho mínimo por columna en tablaDensa).

## R12 · Quién lleva qué (2-oct noche)
- Ver la tabla R12 en `_ESTADO_E0.md` (carril «asignaciones y verdad única»). En este módulo: B-C03 **arreglado** (especialista con nombre y desde asignaciones; `--solo-asignaciones` reaplica sin leer GoHighLevel).

## R12 · arreglos tras la auditoría final (carril E, 2-oct noche)
- **A2 periodo → no aplica:** GoHighLevel llega en ventanas fijas (24 h, 14, 30 y 90 días), sin serie diaria; la línea llana ya existía («foto de ahora con ventanas fijas…»). Sin botones < 32 px a 390.

## V2-C1 (3-oct)
- **B-M6 · arreglado en Salud del CRM:** «Asistencia · 30 días: Sin dato — Ninguna cita de los últimos 30 días tiene marcado si vino…»: una sola cifra a la vista (las 25 de «Citas sin estado · 14 d»), sin «Sin dato» repetido. Mi día: dudas.
- **R16 · arreglado:** «Mover oportunidad» de la ficha de subcuenta elige una oportunidad parada y manda `… · oportunidad <ref>`; sin paradas, lo dice en una línea.
- **B-M7 · arreglado:** pantalla vacía con el motivo exacto (Miguel Vargas).
