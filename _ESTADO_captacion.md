# M6 · Captación · estado (2-oct-2026)

**Lo primero.** La Torre de Control de Paid ya está dentro de la app. `#/captacion` cubre todo lo que hacía la Torre (T1-T13) con Meta y GoHighLevel. Google Ads va con la muestra manual de septiembre, marcada así, hasta que esté la clave de Windsor. Además trae las mejoras M1-M9 que no esperan permisos. Cada persona ve solo sus cuentas, y el dinero solo le llega a quien ve la inversión. Nada se escribe fuera: los botones dejan la acción en la cola «simulada».

## Pantallas

| Ruta | Qué |
|---|---|
| `#/captacion` | Cifras del día: el número que manda (vacío, con «objetivo sin cargar en N de N»), las cuentas en el techo de 35 €/lead, las cuentas en crítico, el gasto y los leads de 7 días, los leads que llegan al CRM y las creatividades cansadas. Después, «Lo primero hoy» (máximo 7, con el cuello de botella) y las pestañas **Cuentas** · **Por trafficker** (Valeria y dirección) · **Creatividades** · **El despacho** · **Google Ads** · **Paridad con la Torre** (dirección) |
| `#/captacion/<cliente>` | La tarjeta del cliente. Arriba: trafficker, account y CRM según las asignaciones, la gravedad, dónde se rompe, «objetivo sin cargar», y los botones «Abrir en Meta / GHL». Luego: motivos y avisos con quién los mueve, tiles (coste por cita a 14 días con la alarma de 100 €, coste por lead con muestra mínima, leads, leads que llegan al CRM, presupuesto y ritmo, Google Ads) y el panel **Actuar** (pausar anuncio, cambiar presupuesto, tarea al CRM, tarea al account, aviso de fuga y escalar a Valeria o a Mili, todo en simulación). Pestañas: gasto y leads por ventanas con 3 gráficos · embudo de GHL a 90 días con los estancados de 72 h · campañas · creatividades · metas · quincenal preparada (con copiar y «apuntar hecha») · historia |
| `#/captacion/~trafficker/<id>` | Las cuentas de un trafficker (se llega desde «Por trafficker») |

## Datos

- Están en `data/captacion/captacion.json` y los genera `fuentes_captacion/generar_captacion.py`, que hace 0 llamadas. Para regenerarlos: primero `~/RO_HERRAMIENTAS/captacion/captacion.py` y `python3 fuentes_captacion/anuncios_meta.py` (70 llamadas de solo lectura a Meta), y después el generador.
- El fichero está dado de alta en `reglas_permisos.json → datos_de_modulo` («captacion/captacion»: módulo captacion).
- Las claves de dinero siempre empiezan por `gasto*`, `coste*`, `cpl*` o `presupuesto_ads`, y las frases con euros van en `gasto_texto`, así que el servidor las quita a quien no ve la inversión. No hay datos de leads, solo recuentos. El escáner de secretos sale limpio.
- El responsable sale de `data/asignaciones.json` (sillas trafficker, account y CRM), no del «PM» escrito a mano de la Torre, que se enseña solo en la paridad.
- Google Ads: la muestra manual de `14_GOOGLE_ADS_VIA_WINDSOR.md` (Fountainhead = Accompany) lleva el sello «muestra manual». Aparte salen las cuentas paradas (Aselegal, FITEC, Greconsult, CE Zaragoza y BIT24), las que están fuera de Windsor (Asetra, Oteca y MG) y Taller del Patinete, que sigue gastando aunque el cliente está en cierre.

## Hallazgos que se ven bien

- **GAC:** Meta dio 101 leads en 7 días y a GHL llegaron 0. Sale como crítico en «Lo primero hoy» aunque la publicidad va bien, y hunde la cifra de la casa: el 15 % de los leads llega al CRM (19 de 130).
- **Concilia:** la cuenta de Meta está en «pago pendiente» y el último gasto fue el 22-sep. Es crítico y su cuello de botella es la integración.
- **Consulting F:** ningún lead llegó a cita en 90 días (84 contactos: 54 en Nuevo y 28 descartados), aunque el coste por lead es de 15,72 €. El cuello de botella es el seguimiento del despacho.
- También: Emex pasa a «Atención» por un coste por cita de 192 € (alarma de la D-03). Innova Scala tiene 3 anuncios rechazados o con problemas. Lina tiene 4 cuentas en crítico (franja ámbar de la D-41) y Vale ninguna.

## Cifras contrastadas con otra fuente

Lectura por anuncio (otra llamada a Meta) frente a lectura por campaña (`captacion.py`), 7 días:
1. **GAC:** 101 leads y 398,99 € en las dos.
2. **Akua:** 6 leads y 526,22 € en las dos.
3. **Innova Scala:** 4 leads y 432,69 € en las dos.

Además, Consulting F tiene 84 contactos (54 en Nuevo y 28 descartados), igual que en `20_FASE2_CAPTACION/RESUMEN.md`. Y los rojos por trafficker contados a mano: Lina tiene 4 (Akua, Concilia, Consulting F e Innova), igual que la pantalla; Vale tiene 0.

## Pruebas («hecho» del 16 §6)

- **Consola sin errores con:** tomas, mili, lucia, valeria, yessica, constanza, lina y setter_ana. La setter ve «Esta pantalla no es de tu puesto» y el servidor le da 403 a los datos.
- **Recorte comprobado en la respuesta del servidor:** Tomás, Mili y Valeria reciben 28 cuentas con dinero; Lina 17 y Lucía 5, sin dinero en bloque (se completa por cliente, ver D-P-CAP1); Gustavo 15 sin dinero; Jessi 28 sin dinero; Camilo 0.
- **Una acción simulada como Tomás** («Escalar a Valeria» en GAC) queda en `acciones` con estado «simulada». En «ver como» los botones están desactivados.
- **Las 6 pestañas de la lista y las 7 de la tarjeta** pintan sin errores.
- **A 390 px** no hay desplazamiento horizontal (comprobado por DOM).
- **Capturas** en `capturas/captacion/`: 13 a 1440 px y 7 a 390 px. Las de 390 px se hicieron con un iframe de 390 px, porque Chrome sin cabeza no baja de 500 px.

## Falta o espera

- **W2 (clave de Windsor):** Google Ads con campañas y serie diaria, y TikTok.
- **D-03:** cargar los objetivos de coste por cita y de coste por lead en el alta. Con eso el número que manda se calcula solo.
- **W7 (permiso ads_management de Meta):** pausar y cambiar presupuesto de verdad.
- **W3:** velocidad de contacto e intentos (D-46), y el tiempo real (M4).
- **M9 a 90 días:** cuando haya fotos diarias.
- La recarga programada (la Torre se recargaba de lunes a viernes a las 6:00).
- **Lo que pido a E0 y a la ola 0:** D-P-CAP1 (recortar el dinero por cliente en `/api/modulo`), D-P-CAP2 (nombres de dinero en la ficha de E1) y D-P-CAP3 (`main > * { min-width: 0 }` y los componentes de barra y embudo).
- **Antes de dar la Torre por archivada:** revisión con Valeria, Coti, Mili y Agus.

---

## Ronda de arreglos (2-oct, noche)

| Fallo de la auditoría | Estado |
|---|---|
| B-02 · GAC sale «Bien» con 101 leads perdidos | **Arreglado.** GAC sale en «Atención» con el motivo «Subcuenta de GoHighLevel sin usar (1 contacto en toda su historia): los 104 leads de Meta de 7 días no van a GoHighLevel. Confirmar con el cliente el servicio de CRM y dónde recibe los leads». No es una fuga: el «sin uso» lo da Salud del CRM. Una fuga grave de verdad pasa a «Crítico», con la misma regla que la verdad única |
| E-03 · «Leads que llegan a GHL»: Captación contaba oportunidades y CRM contactos | **Arreglado.** Captación toma `leads_ghl_7d` de `data/crm/crm.json`, sin recalcularlo: contacto nuevo con origen formulario o anuncio, sin pruebas, importados ni otros negocios. Se quitó el aviso por oportunidades de `captacion.py`. Ya no sale la alarma falsa de Akua: 13 contactos en GoHighLevel frente a 6 leads de Meta |
| E-13 · La subcuenta de GAC no se usa | **Arreglado** (ver B-02). Las subcuentas sin uso no cuentan en la cifra «Leads que llegan al CRM» |
| E-01 · Kiosko emparejado con «Kiosko II» | **Arreglado.** `captacion.py` lee primero `fuentes/emparejamientos_manual.json` de E1 (`meta`); si falta, usa un respaldo con la misma corrección. Kiosko → «Josep SG»: **5.563,11 € en 35 días**, igual que E1 (unos 5.563 €) |
| E-15 · Zona horaria (GAC y Deudout en hora de Los Ángeles) | **Arreglado.** Cada cuenta lee su `timezone_name`. Si no coincide con Madrid, Meta se lee por horas y cada hora se pasa a su día de Madrid; lo mismo con los anuncios. GAC en 7 días: 104 leads y 399,95 € en hora de Madrid, frente a 101 y 398,99 € en hora de California. Las cuentas en Canarias y Dublín también se convierten. La tarjeta lo avisa |
| E-17 · Moneda | **Arreglado.** Una cuenta en otra moneda no se suma al gasto de la casa y lo avisa. Hoy todas van en euros |
| E-18 · Proyección del presupuesto antes del día 5 | **Arreglado.** No se calcula (`captacion.py`) ni se pinta: «sin proyección hasta el día 5» |
| Parte C del 26 · Atajos a campaña y anuncio de Meta | **Hecho.** Botón «Abrir en Meta» por campaña (`selected_campaign_ids`) y por anuncio (`selected_ad_ids`). Ese formato no lo documenta Meta: si no selecciona, abre la cuenta |
| 29 · Lina no puede avisar al CRM | **Arreglado.** «Tarea al CRM (persona)» en cada fila de «Lo primero hoy» y en la tarjeta, con el especialista asignado ya puesto. Si el cliente no tiene especialista, va a Yessica (jefa de CRM) |
| 29 · «2535 €» sin punto de miles | **Arreglado.** Formato propio con punto de miles siempre |
| 29 · «Reglas de la Torre», «(D-03)» y códigos a la vista | **Arreglado.** Textos sin códigos, con `limpiaTexto()` en los motivos. «En crítico si: el lead cuesta 1,5 veces el máximo…» |
| 29 · La tabla queda debajo de 7 tarjetas | **Arreglado.** Ahora son 5 tarjetas: «Leads y gasto» van juntos y las creatividades pasan a su pestaña |
| 22 · «Vale» abreviado | **Arreglado.** Los nombres salen de `ctx.nombre()` (Valeria, Yessica) |
| Regla 1 · Verdad única | **Adoptada.** Equipo y «nuevo» salen de `data/verdad/clientes.json`, y la fuga sigue la misma regla. `captacion` está en `ADOPTADOS` y `pruebas_coherencia.py` da 0 errores |
| Regla 6 · Sin ceros ni verdes falsos | **Arreglado.** Sin dato de GoHighLevel, la tarjeta sale en gris y dice «sin dato» o «subcuenta sin usar» |
| Importes tapados por el servidor en las frases (ronda 6 de E0) | **Adaptado.** Las reglas de la casa (35 € y 100 €) ya no van dentro de la fila del cliente; la pantalla las añade desde los parámetros. Si el servidor tapa un importe, se usa la frase sin cifras |
| D-P-CAP1 · El dinero del trafficker | **Resuelto por E0** (recorte cliente a cliente): Lina recibe 16 cuentas con dinero |
| 27 M6 · Cachés con datos personales | **No aplica a Captación.** `fuentes_captacion/` solo guarda recuentos y nombres de anuncios, sin datos de leads |

**Cambio de datos que hay que saber:** Concilia ya **no** está en «pago pendiente». Meta da hoy la cuenta como activa (estado 1), así que Concilia sale «Sin pauta»: no gasta desde el 22-sep.

**Kiosko:** cuenta de tienda online. Meta da 1.419 «leads» en 7 días, que son conversiones del píxel, y suben mucho los leads de la casa. Hay que decidir si se separa del resto.

**Fountainhead:** aquí sigue como cuenta de Accompany, por la instrucción del encargo. En `emparejamientos_manual.json`, E1 la deja sin cliente («¿de quién es?»). Lo tiene que confirmar Agus.

**Pruebas de la ronda:** `pruebas_e0.py` sale «TODO BIEN» y `pruebas_coherencia.py` da 0 errores. No hay errores de consola (Chrome sin cabeza con registro de consola) con tomas, mili, lucia, valeria, yessica, constanza, setter_ana y lina, en la lista, en GAC y en Kiosko. El escáner sale limpio. Capturas en `capturas/captacion/r3_*`: 11 a 1440 px y 4 a 390 px.

**Fuentes nuevas:** `fuentes_captacion/ghl_totales.py` (respaldo: contactos de cada subcuenta en toda su historia). En `~/RO_HERRAMIENTAS/captacion/captacion.py` hay cambios de zona horaria, moneda, ids de campaña, emparejamiento manual e integración; la copia anterior está en el scratchpad (`captacion_antes_r3.py`).

## Ronda 4 · guía de diseño (auditoría 30) y encargos del coordinador · 2-oct noche
- Fuera las hojas de estilos propias (`seo-estilos`, `cap-estilos`, `eq-estilos`): clases comunes (fila, pila, sub, chip, lista-i, rejilla, titulo-seccion) y estilo en línea solo con tokens (`var(--s-*, valor)`), nada por debajo de 12 px, cifras con punto de miles. Estado de fila = punto + texto en tinta. Línea de fuentes → un chip «Datos al día» que se despliega.
- Gráficos: `barras()` de `produccion_comun.js` usa ya el motor común `grafico()` de componentes.js; barras de progreso, embudo y ventanas, los comunes.
- SEO/web: pestaña Webs con columnas de Modular DS (Copia · Actualizaciones · Seguridad · Fuera de RO, con «bloqueada solo para RO»); hoy «Modular sin conectar» con el paso de Tomás (clave de solo lectura + pegar.sh). Camino conectado probado con datos simulados en el navegador.
- Horas: zona horaria de cada persona desde personas.json (Valeria hora de Venezuela, Sofía hora de España) en cabecera, listas, tabla y ficha.
- Producción: Camilo con la etiqueta «transversal» (copy, responde ante Mili), «sin cartera propia».
- Captación: Kiosko (tienda online) fuera de los leads de la casa (143 en vez de 1.562) y del techo de 35 € (4 de 8 en vez de 5 de 9), con nota en su tarjeta.
- Pruebas: 7 personas × 1440/390 × 7 rutas con todas las pestañas: 0 errores, 0 desbordes, 0 textos < 12 px · coherencia 0 errores · escáner limpio · pruebas_e0: 1 fallo ajeno (/api/cliente de Gustavo, «serie»).

## N6 · diseño 10/10 (2-oct, noche)
- **Orden de la guía 3.6:** arriba «Lo primero hoy» (4 casos a la vista + «Ver 3 más»), luego la cifra que manda a 32 px con `cifraPrincipal()` — **«En el techo de 35 €: 4 de 8»** mientras no haya objetivos (nada de «—») — y 3 tarjetas de apoyo (En crítico · Llegan al CRM · Leads 7 días) en `rejillaTarjetas()`: 4 en fila, sin huérfana. Se quitó la tarjeta muerta de «coste por cita en objetivo».
- **Botones por caso:** 1 principal («Abrir tarjeta») + menú «⋯» (`menuMas`) con «Abrir en Meta/GoHighLevel» y «Tarea al CRM (persona)», que abre su confirmación Sí/No.
- **Fuentes:** el chip «Datos al día / N fuentes con retraso» va en la fila del alcance (una línea, se despliega). El aviso «objetivo sin cargar» y las reglas de crítico pasan al plegable «Cómo se mide cada cifra» del pie.
- **Móvil:** tabla de cuentas paginada (12 + «Ver más»): la página baja de 11.750 a ~6.200 px (Tomás, 390).
- **Sistema:** formateadores propios fuera (todo con `fmt`), coste por lead con `colorCifra('coste_lead')` en la tabla y en la tarjeta (con objetivo propio cargado, contra su objetivo), tarjetas sin dato con «Sin dato» pequeño y gris en vez del «—» gigante, carga con `esqueleto()`, radios y espaciados con tokens, textos sin nombres de fichero ni códigos (M7, M9, captacion.py).
- **Periodo:** NO adopta `usa_periodo`. Todo son ventanas fijas precalculadas (7 días frente a los 7 anteriores, coste por cita a 14 días, embudo a 90 días, septiembre de Google Ads por muestra manual); lo dice una línea bajo las cifras y el subtítulo de Google Ads. La serie diaria de la tarjeta cubre unas 5 semanas: cuando haya fotos diarias, se puede pasar la tarjeta a `ctx.periodo`.
- **Kiosko y Fountainhead:** sin cambios (Kiosko fuera de leads y del techo; Fountainhead en Accompany como muestra manual).
- **Pruebas:** `pruebas_diseno.py` → captacion.js en «Limpios»; capturas `capturas/_n6/captacion/` (7 personas × 1440/1024/390 × lista, GAC y Kiosko): 54 pantallas, 0 con problemas; pestañas de lista y tarjeta sin errores de consola; pruebas_e0 (puerto 8887), seguridad, coherencia y escáner en verde.
- **Remate (pedido del coordinador):** en el móvil (< 641 px) los filtros de la tabla (chips y desplegables) van en un plegable de una fila «Filtros (n activos)»; etiquetas de tarjeta cortas («Techo de 35 €», «En el CRM») que caben en una línea a 1024; el aviso «Hora de Madrid» de la tarjeta es ya una línea `.sub` con icono. Página de Tomás a 390: 5.838 px. Repasado: 54 pantallas (7 personas × 1440/1024/390 × lista, GAC y Kiosko), 0 con problemas; pruebas_diseno limpio.
- **Nota contra la auditoría 30:** 5,0 → **9,0**. Queda fuera de mi fichero: el «null» de `menuMas()` (lo quito aquí; apuntado en dudas_pintura.md) y que `tile()` pinte «Sin dato» por sí mismo.

## R12 · arreglos tras la auditoría final (carril E, 2-oct noche)
- **A2 periodo → hecho donde hay dato diario.** `usa_periodo` solo en la lista y con 7 días, 30 días, este mes y ayer (la serie diaria de Meta cubre unos 35 días). La tarjeta de leads y gasto suma la serie del periodo y compara con el anterior solo si la serie lo cubre entero (si no, «sin dato antes del 28-ago para comparar»). Lo que se juzga (crítico, techo, CRM) sigue en su ventana fija de 7 días y lo dice la línea de debajo. Comprobado: la serie de 7 días = la ventana de 7 días en las 28 cuentas.
- **«Mis cuentas 16» → arreglado:** sale de `carteras[]` (lo que llevas como principal): Lina 14, y un chip aparte «De apoyo 2» (Emex, Laver), con la línea del universo («14 de tus 19 clientes con cuenta de Meta…»). Comprobado en `pruebas_coherencia.py`.

## V2-C1 · una sola vara (3-oct)
- **B-A2 gravedad · arreglado.** «Crítico / Atención / Bien» en Captación = gravedad del cliente de la verdad única (`ctx.verdad`), igual que menú, Mi día, En rojo y ficha (Akua: Atención; GAC: Crítico). El estado de la cuenta de publicidad va con otro nombre: «Publicidad urgente / a vigilar / en orden / Sin pauta» (columna aparte en Cuentas y chip en la tarjeta). Filtros, tile «En crítico», «Lo primero hoy» (color = gravedad del cliente) y Por trafficker leen la verdad.
- **Accompany «Bien» con «CRM no conectado» · arreglado.** Nunca «en orden» con un aviso de integración abierto (generador y pantalla): pasa a «Publicidad a vigilar»; el cliente sigue en «Atención».
- **B-A3 cartera · arreglado aquí.** `carteras_publicidad` en captacion.json (de la verdad `carteras[]`): Lina 19 clientes (+2 de apoyo) · 14 con cuenta de Meta · 9 encendidas · 3 en crítico; Valeria 11 (+8) · 10 · 6 · 1. Línea «Tu cartera de publicidad…» y columna «Cartera» de Por trafficker. `criticos_casa` (4) para «Fuegos». Mi día y Personas: apuntado en dudas (V2).
- **B-M2 dueño de Google Ads · arreglado.** Captación lee `duenoConexion()` de Conexiones: «Lo hace Tomás: pegar la clave de Windsor; después Agus comprueba que llegan los datos».
- **B-M11 · arreglado.** «13 en GHL · 6 de Meta + 7 de otras vías», sin el 100 %.
- **B-M7 · arreglado.** Pantalla vacía con el motivo exacto («Tus 17 clientes están asignados como web; falta que Mili o Tomás te asignen clientes de GoHighLevel»), la misma frase en ficha y Salud del CRM. El consejo «Google Ads … lo conecta Agus» es de la IA: dudas.
- **B-B8 · arreglado** («Foto del 17 de septiembre (herramienta anterior)»). **B-B9 · arreglado** (campaña · conjunto · nº de anuncio). **B-B10 · arreglado** («CRM: sin especialista (cubre Yessica)» en los dos sitios). **B-B3 · no aplica aquí** (tildes del nombre del cliente vienen de clientes.json: dudas).
- **B-M1 (consejo de fuentes) · no aplica** (ia_componentes/ia.py).
- Pruebas: `pruebas_coherencia.py` sección V2-C1 (cartera, críticos, «en orden», vara única, dueño de conexión) en verde. Capturas `capturas/_v2c1/`.
