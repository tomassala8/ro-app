# _ESTADO · M4 Ficha del cliente (id `ficha`) · 2-oct-2026

## Hecho
- `modulos/ficha.js`: la ficha v3 (`~/Downloads/HERRAMIENTA_RO_2026-10-02/plantilla.html`) portada al contrato de módulo. Ruta `#/ficha/<cliente>/<pestaña>` (la pestaña queda en la dirección y se recuerda; al cambiar de cliente te quedas en la misma pestaña). Sin cliente en la ruta abre el último que abriste o el de tu cartera con peor salud.
- **Cabecera:** logo, nombre del portal, account, «Cliente desde», cuota (solo si `c.cuota` llega), especialidad, web, chips de semáforo, salud, riesgo y «N en rojo» (enlace a En rojo), «Llamar a…» (sip: Zadarma) + WhatsApp (wa.me) + Correo, accesos directos (ClickUp, Drive, Meta, Analytics, Search Console, Desk) y barra de etapas.
- **Barra:** selector de cliente con logo, account y buscador (solo `clientesVisibles`, los tuyos primero; tecla «c» lo abre) y periodo único 7/30 días con su comparación.
- **10 pestañas con icono y contador** (rojo solo si hay que actuar), **ordenadas por puesto** (account: Comunicación y Chat detrás de Resumen; publicidad y CRM: Resultados; SEO: Web y SEO; redes: Redes; dirección/operaciones: Comunicación y Resultados). Resumen primero y Rastro último siempre.
  - Resumen: 8 tiles que llevan a su pestaña (correos sin contestar D-29, leads 7 d, coste por lead, citas 14 d, revisiones > 48 h, días sin reunión, visitas web, horas como aviso D-27), nota de «en rojo a mano», «Qué hay que mover hoy» (alarmas recortadas de `ctx.datos.alarmas`, marcar visto con rastro), últimos movimientos y equipo del cliente.
  - Contactos: chips Todo/Personas/Móviles/Correos con contador + buscador; personas con dato en tarjetas (principal marcada), las que no tienen teléfono ni correo en lista compacta; móviles de la agenda; correos ordenados por uso (veces en Desk, GHL, CRM y portal). Cada clic de llamar/WhatsApp/correo deja rastro.
  - Resultados: Meta (leads, gasto, coste por lead, meta del mes; tiles que cambian el gráfico diario), campañas, avisos de la Torre, embudo de su GHL con citas, Google Ads (muestra de septiembre) y outreach de Snov.io.
  - Web y SEO: GA4 y Search Console con comparación, gráfico diario, páginas, búsquedas, canales traducidos y SE Ranking como hueco explicado.
  - Redes (Metricool), Comunicación (Desk, Zadarma por persona sin números, reuniones CRM/Fathom, Zoom), Trabajo (horas si `horas_cliente`, revisiones con enlace, estados, informes mensuales D-09), Accesos y contrato (los 10 recursos del portal con copiar y pendientes en gris, cuota/segmento/facturado según permiso, hitos, equipo), Rastro (acciones simuladas + registro del servidor + historia, con chips).
  - Chat: canal de ClickUp real (últimos 30 mensajes, claves ocultas, imágenes y enlaces limpiados), caja de escribir (Intro envía) → `ctx.accion` en cola **simulada** hasta W1, botones Llamar y «Videollamada Zoom» (simulada, W4), «Abrir en ClickUp».
- **Datos nuevos** (`fuentes_ficha/generar_ficha.py`, 0 llamadas, puerta de secretos antes de escribir): `data/ficha/portal.json`, `data/ficha/web.json` (recortados por `cliente_id`), `data/ficha/_privado/contactos.json` (64 clientes) y `chat.json` (46 canales). Alta en `reglas_permisos.json`: `datos_de_modulo` (2), `almacenes_privados` (2) y tipos `contactos_cliente` y `chat_cliente`. `modulos/indice.js`: entrada M4 con id `ficha`, `fichero`, `estado: 'hecho'`.
- **Mejoras pedidas sobre la v3:** nada se sale a 1440 (rejillas `minmax(0,1fr)`, textos largos con puntos suspensivos, pestañas con desplazamiento propio); 390 px sin desplazamiento horizontal; clics lógicos (tile → su pestaña, cliente → misma pestaña, número → prueba); orden por frecuencia; iconos en todo; estados vacíos con quién lo arregla.

## Pruebas (servir.py en 127.0.0.1:8774, Playwright con el Chrome instalado)
- 60 combinaciones (tomas, lucia, mili, valeria, yessica en GAC; constanza en Kiosko Box; 10 pestañas cada uno) + setter_ana + Lucía en Musashi + Torrevieja web + las 10 pestañas a 390 px: **0 errores de consola propios, 0 pestañas caídas, scrollWidth = ancho** en todas. (Los únicos avisos en consola son de otros módulos en obras: `nuevos.js`, `informe.js`.)
- Permisos vistos en la respuesta del servidor: Lucía abre sus 12 clientes y no Musashi (pantalla «no es de tu puesto», sin pedir datos); Jessi ve GAC pero no sus contactos ni el gasto; Vale (trafficker de GAC) ve gasto y contactos, no la cuota; Coti y Mili ven contactos de Musashi; setter_ana no tiene la pantalla (403 en datos de módulo).
- Envío del chat como Lucía: burbuja «Simulado: se envía con W1», fila en `acciones` (`mensaje_chat`, simulada). Periodo 7 días cambia los tiles; tile de Resumen lleva a Comunicación; «c» + «fuster» + Intro cambia a FusterGüell en la misma pestaña.
- `escaner_secretos.py`: limpio.

## Cifras contrastadas con su origen
1. GAC · Meta 25-sep→1-oct: **101 leads y 398,99 €** en la ficha = API de Meta (`mt.py`, `act_28911839/insights`): 101 leads, 398,99 €.
2. GAC · GA4 2-sep→1-oct: **1.326 usuarios y 1.534 sesiones** = API de Analytics (`gg.py`, propiedad 467078581): 1326 / 1534.
3. GAC · agenda: **1 móvil y 12 correos** = índice de `MOVILES_Y_CORREOS_CLIENTES_RO_2026-10-02.md` («GAC Grup | Lucía | sí (1) | 12»).

## Capturas
`capturas/ficha/`: 15 a 1440 px (Tomás en las 10 pestañas, Lucía resumen, Coti Kiosko Box, Jessi con contactos bloqueados, Lucía sin permiso en Musashi, Torrevieja web) y 5 a 390 px (resumen, contactos, chat, resultados, trabajo).

## Falta / dudas (detalle en `../dudas_pintura.md`, «D-P · M4»)
- Que ⌘K y el detalle de En rojo lleven a `#/ficha/<id>` (ficheros de otros).
- Fuga en `/api/cliente`: presupuesto, serie de gasto, `libro.meses`/`ltv` llegan a quien no ve dinero (la ficha los tapa, el servidor no).
- «Ver como» no abre contactos ni chat (POST bloqueado).
- Contrato de Zoho Sign: hueco preparado en «Accesos y contrato».
- Enviar al chat de verdad y llamar de un clic: W1; videollamada: W4.
- Revisión con Coti, Mili y Agus (R15): pendiente.

---

# Ronda de contactos y ronda de arreglos (2-oct, noche)

## Contactos: el documento del 2-oct, perfecto en la app
- **Lectura estricta** (`fuentes_ficha/agenda_md.py`): 64 clientes, **82 móviles y 344 correos**, igual que el índice del documento, línea a línea (0 líneas sin leer). Los 64 títulos casan con un cliente de la app.
- **Cuadre cliente a cliente** (`fuentes_ficha/_privado/cuadre_contactos.json`): **0 móviles y 0 correos perdidos**. Ninguno con dominio ajeno al despacho (salvo gmail/hotmail personales, que están en el documento).
  - **De más**: 28 teléfonos y 13 correos que no salen en el documento pero sí en el portal de clientes, en 24 clientes (Adade, Ahedo, Asetra, Avantik, Bonet, Busbac, Centro Consulting, Consulting F, ECIJA, Fitec, FusterGüell, GAC, Garmande, Greconsult, J&D, MG, Musashi, Octoedro, Orejana, Oteca, PGB, Prodegest, Torrevieja y Xterna). Son sobre todo fijos de oficina y correos del portal. En la ficha llevan la marca «Solo en el portal». Los de proveedores y colaboradores (24 personas: IT, hosting, RGPD, canal de denuncias…) van aparte como «Externos al despacho».
  - Un móvil del portal mal guardado («+6559973830» de Segú) se descarta porque es el mismo que el del documento.
- **Una persona, un nombre** (`fuentes_ficha/personas_cliente.py`):
  - **Se unen** por mismo correo, mismo móvil (los fijos no unen), misma dirección en dos dominios del despacho, nombre y apellido iguales o contenidos, y nombre de pila suelto cuando hay una sola persona que se llama así (102 uniones de este tipo).
  - **Nombre elegido**: como firma él mismo en Desk, si no el del portal, si no el de Zoho CRM, si no el más usado. Se prefiere la grafía con tildes. Las demás formas van plegadas en «También aparece como».
  - Los nombres de remitente que no casan con la dirección no unen personas (p. ej. «Carlos Niño» como remitente de jbascon@).
  - **Resultado**: 377 fichas = 314 personas + 39 buzones generales + 24 externos. 44 direcciones sin nombre en ninguna fuente salen como «Sin nombre (xxx@)».
- **Quién es cada uno, siempre con su fuente** (nada inventado):
  - **Fuentes del cargo**:
    - portal de clientes;
    - documento de móviles;
    - Zoho CRM (Title/Designation, solo 1 con dato);
    - Zoho Desk (title del contacto: 1);
    - **firmas de sus correos en Desk** (24 cargos, leídos de su último correo con el ticket citado);
    - nombre del chat de WhatsApp.
  - GHL no se ha consultado porque su llave rota en cada uso y la lleva la tubería. El portal antiguo de Lovable no trae contactos (vivían en su Supabase); solo se usó como referencia de nombres.
  - **Marcas**:
    - **«Decisor»** (60): la fuente dice decisor, socio, director, gerente o CEO (nunca si es externo).
    - **«Día a día»** (62): la fuente dice interlocutor o día a día; si no, por uso, explicado en pantalla.
    - **«Principal»**: el que más interactúa (uno por cliente).
  - 149 personas con cargo; el resto sale como «Rol sin confirmar».
- **Pestaña Contactos**:
  - Tarjetas por persona con iniciales, nombre, cargo (y su fuente al pasar el ratón), marcas, llamar (sip:), WhatsApp, correo y copiar, veces y «en copia», último correo suyo (Desk) y «De dónde sale».
  - Chips: Personas · Con móvil · Decisores · Día a día · Buzones · Externos · Todo. Buscador.
  - **Accompany, Bonet, J&D y Oteca**: aviso «Sin móvil: pídeselo», con el fijo para llamar y un botón «Pedir el móvil» (cola simulada).
  - Todo va en almacén privado; abrirlo deja rastro.
- **Permisos** (probado en el servidor): contactos para su **account**, operaciones, proyectos y dirección.
  - Lucía abre GAC pero no Musashi.
  - Valeria (trafficker de GAC), Jessi y Camilo no los abren.
  - La regla `contactos_cliente` pasa de «cualquier silla» a «account».

### 5 clientes contrastados a mano contra el documento
| Cliente | Documento | App |
|---|---|---|
| Abner | 1 móvil (Miguel Rutea) y 2 correos | Miguel Rutea (Decisor · contacto de la venta, GHL) con su móvil y su correo; «Sin nombre (nasensi@)» |
| Adade | 1 móvil y 6 correos | Antonio Tomás (Socio / Decisor), Raúl Ladrero, Teresa, pladrero@ y 2 buzones (clientes@, zaragoza@) |
| Xterna | 1 móvil (WhatsApp «Miquel XTERNA») y 24 correos | 24 correos en 23 fichas + buzón web@; Miquel Sánchez con su móvil y el nombre de WhatsApp; Fermín Liébana como firma él (en el documento, «Fermí») |
| Oteca | sin móvil, fijo teléfono del cliente | Aviso «pedir móvil» con el fijo; Ignacio Moreno Martín (CEO · Director Gerente) |
| GAC | 1 móvil (Oficina Barcelona) y 12 correos | Antonio Hermosilla Moratalla con el móvil «guardado como Oficina Barcelona»; Patricia Hermosilla principal y día a día; 12 correos en su sitio |

### Dudas de contactos para Tomás (no se han adivinado)
1. **Accompany**: ¿«Gerben Geerse» o «Gert Jan Geerse»? (correo del cliente y correo del cliente). Hoy se enseña «Gerben Geerse» (portal), con la marca «Nombre por confirmar».
2. **Ahedo**: el portal da a **Belén** el mismo móvil que a **Óscar** (teléfono del cliente). ¿De quién es? Hoy van como dos personas.
3. **Bonet Asesores**: ¿«Joan J. Bonet» o «José Javier Bonet»? (correo del cliente y correo del cliente, que se han unido).
4. **Centro Consulting**: **Ricardo** y **Víctor Martínez** con el mismo móvil (teléfono del cliente).
5. **ECIJA**: correo del cliente sale como «Ignacio Wucherpfennig»: el correo no casa con el apellido.
6. **Fitec**: correo del cliente aparece como «Cristina Antúnez» en el portal y como «Tino Antúnez» en Desk y CRM, y hay también otro correo a nombre de Tino. ¿Son la misma persona o dos?
7. **FusterGüell**: jmolist@ aparece como «Joan Molist» y como «Jordi Molist». ¿Cuál es?
8. **GAC**: «Laura» (portal, equipo comercial de cierre) puede ser Laura González o Laura Tomasa.

## Ronda de arreglos: fallo de la auditoría → qué se ha hecho
| Fallo (22, 26, 27, 28 y 29) | Estado |
|---|---|
| Comunicación lee Desk de las 07:00, cuenta contestados y avisos de Zapier y da los días en laborables mientras la Bandeja los da en naturales (E-07) | **Arreglado**: `data/ficha/correos.json` es la copia de la Bandeja (misma regla y misma hora). Los avisos automáticos van aparte, plegados. «Días laborables» = horas de lunes a viernes ÷ 24, la misma unidad que la Bandeja. Si alguien no tiene la Bandeja, cae a Desk con la etiqueta «lectura de las 07:00» |
| «Prueba de la ficha M4 (simulada)» en el chat de GAC (P-10) | **Arreglado en pantalla**: la ficha no enseña los envíos de prueba (ni en el chat ni en el rastro). La fila sigue en `local.db` porque la cola es imborrable (disparador). Ver dudas |
| Cuota de FusterGüell 500 € y Akua 1.270 € (E-05) | **Arreglado**: la cuota sale de la fuente única de Dinero por cliente (Airtable de octubre): FusterGüell **999 €**, Akua **1.290 €**. `pruebas_coherencia.py` comprueba «cuota de la ficha = cuota de Dinero» |
| Concilia «publicidad prevista» y cuenta en pago pendiente (E-12) | **Arreglado en la ficha**: «Publicidad: sí» si hay cuenta de Meta emparejada con gasto o leads, sea alta o no. Aviso rojo «La cuenta de Meta está en "pago pendiente"» en el Resumen |
| Camilo tiene la ficha en el menú y no la puede abrir (F-13) | **Arreglado**: ficha básica de solo lectura con los clientes de sus tareas (`data/ficha/basica.json`, filas por persona). Enseña web, descripción, account, Drive de materiales, Metricool y sus tareas con enlace. Sin dinero ni contactos |
| Sofía recibe la ficha casi completa (I-02) | **Arreglado**: administración ve solo la cabecera, Accesos y contrato, y Rastro. No pide web ni correos |
| Falta la subcuenta de GHL, Metricool y SE Ranking (26 C.3) | **Arreglado**: atajos «Abrir en» GoHighLevel, Metricool y SE Ranking. Si falta el identificador, salen en gris con «falta emparejar». Cada clic deja rastro |
| «7 días» con el periodo en 30 (P-11); la ficha abre en 30 | **Arreglado**: los tiles del Resumen siguen el periodo, que arranca en 7 días |
| «Lucía · tuyo» para Lina (P-15) | **Arreglado**: «Account: Lucía · tú llevas la publicidad» |
| Pestañas cortadas a 1440 | **Arreglado**: en escritorio la barra pasa a dos filas; nada queda oculto |
| Códigos D-xx, W1, R10… a la vista; «LSO»; «Semáforo: definir»; «· : rojo > 48 h» | **Arreglado**: textos llanos, la sigla fuera de la especialidad, «Semáforo sin poner» y «Ninguno de más de 48 h» |
| Sin migas en la ficha | **Arreglado**: Clientes › GAC › Resultados (se actualiza al cambiar de pestaña) |
| Account y equipo de dos fuentes; persona de baja en el equipo (E-20) | **Arreglado**: account y equipo de `ctx.verdad()` y nombres con `ctx.nombre()`. «ficha» está en `ADOPTADOS` de `pruebas_coherencia.py` (account y cuota en verde) |
| Salud 100 frente a «crítico» en Captación | **Arreglado**: chip «Estado: crítico / atención / bien» y salud de la verdad única |
| Cifras del mismo cliente a horas distintas (E-23) | **Arreglado**: aviso en el Resumen si las fuentes se separan más de 6 h, y la hora al pie de cada cifra |
| Search Console con días vacíos al final (E-10) | **Avisado** en Web y SEO: «datos hasta el 29-sep». El corte de la ventana es de `externos.py` |
| GA4 que deja de medir sale como «a cero» gris (E-22) | **Arreglado**: si el periodo anterior tuvo más de 50 usuarios y el actual 0, aviso rojo con dueño |
| Emparejamiento con una landing u otra propiedad (Consulting F, FusterGüell) | **No aplica a la ficha**: es de E1. La ficha enseña qué propiedad y qué sitio lee («Se lee Analytics: …») para verlo de un vistazo |
| `ver_dato` con cliente_id de otro cliente (27) | **Lo cerró E0** (`"cliente": "ref"` en los almacenes). La ficha manda ref = cliente |
| «duda» del portal con euros a quien no ve cuota (27 A3) | **Arreglado**: los importes de la duda se sustituyen por «[importe]» |
| Correos de contactos en `fuentes_ficha/_cache` (27) | **Arreglado** (lo movió el auditor a `fuentes_ficha/_privado/`; el generador ya escribe ahí) |
| Liébana con cuota de 52 € | **Se queda en duda**: con la fuente única sale la de Airtable; si sigue en 52, hay que confirmarlo con Sofía |
| Zonas horarias de Meta (E-15) | **No aplica aquí**: lo arregla `captacion.py`. La ficha pinta lo que trae |

## Pruebas de esta ronda (servir.py en 127.0.0.1:8774, ya cerrado)
- 60 combinaciones (tomas, lucia, valeria y yessica en GAC; mili en FusterGüell; constanza en Kiosko Box; las 10 pestañas cada uno) + Sofía + Camilo (1440 y 390) + setter_ana + Lucía en Musashi + las 10 pestañas de Tomás a 390.
  - 0 pestañas caídas y 0 errores de consola de la ficha.
  - 0 desbordes: a 390 los tiles van en carrusel, un diseño común de E0.
- `pruebas_e0.py`: TODO BIEN. `pruebas_coherencia.py`: «ficha» en verde (el único error que queda es de Agenda). `escaner_secretos.py`: limpio.
- Capturas nuevas: `capturas/ficha/r3_*` (9 a 1440 y 4 a 390).

## Notas de compatibilidad
- `servir.py` (ronda 6 de E0) exige `X-RO-App` en los POST y `datos.js` aún no la manda. La ficha llama a `/api/ver_dato` con esa cabecera para que contactos y chat funcionen sin 403. Cuando `datos.js` la mande, se puede volver a `ctx.verDato`.
- Mientras tanto, `ctx.rastro` y `ctx.accion` (POST de la app común) pueden fallar con ese servidor: es de E0.

## Respuestas de Tomás a las 8 dudas (aplicadas, 2-oct noche)
Viven en `fuentes_ficha/_privado/contactos_manual.json` (privado desde el 2-oct noche: el escáner y la subida no lo recorren) y mandan sobre cualquier fuente. `personas_cliente.py` las aplica antes de unir.
| # | Respuesta | Resultado en la app (contrastado tras regenerar) |
|---|---|---|
| 1 | Accompany: «Gert Jan Geerse» | Una persona «Gert Jan Geerse» con correo del cliente y correo del cliente. «Gerben Geerse (Geert)» queda plegado. La nota del documento ya dice «Solo correo (Gert Jan Geerse)» |
| 2 | Ahedo: el móvil es de Óscar | Óscar Tejerina tiene teléfono del cliente y Belén ya no |
| 3 | Bonet: «José Javier Bonet» | Una persona con jjbonet@ de los dos dominios. La nota del fijo, corregida («(José Javier Bonet)») |
| 4 | Centro Consulting: no se sabe de quién es el móvil | Está en Ricardo y en Víctor Martínez, sin unirlos, con «Móvil compartido · de quién es, sin confirmar» bajo el número |
| 5 | ECIJA: «Ignacio Wucherpfennig» es correcto | Confirmado, sin duda |
| 6 | Fitec: dos personas | Cristina Antúnez (c.antunez@) y Tino Antúnez (tino.antunez@) por separado. Ninguna enseña el nombre de la otra en «También aparece como» |
| 7 | FusterGüell: jmolist@ es «Jordi Molist» | Jordi Molist con jmolist@ (el «Joan Molist» del portal llevaba el mismo correo: es él, plegado) |
| 8 | GAC: la «Laura» del portal es Laura Tomasa | Unida a Laura Tomasa (lts@), con el cargo del portal «Equipo comercial cierre» |

Tras regenerar: siguen **82 móviles y 344 correos, 0 perdidos**. Escáner limpio. Contactos de Centro Consulting, Fitec, Accompany (390), Ahedo y GAC (Lucía) sin errores ni desbordes. Valeria sigue sin acceso. Captura: `capturas/ficha/r4_*`.

**Duda nueva (detectada al regenerar, no unida):** Centro Consulting, «Gemma Gregorio» (portal, «Representante central CE Consulting») y «Gema Gregorio» (correo del cliente, 9 correos). ¿Son la misma persona?

## N2 · Pestaña «Informes» (histórico de informes del cliente)
- `fuentes_ficha/generar_ficha.py` → `data/ficha/informes.json` (alta en `datos_de_modulo`, fuera administración; filas por `cliente_id`, recortadas por el servidor). Junta para cada cliente:
  - los 12 meses de la hoja «Informes mensuales» de Zoho (`data/informes/historico.json`): enlace al informe, enlace a estadísticas, contado en reunión y enviado;
  - el seguimiento de M13 (`data/informes/informes.json`): estado, retraso, tarea de ClickUp y correo de Desk con que se envió;
  - el Looker y la carpeta de informes del portal;
  - el «Informe del cliente» de la app por mes (`#/informe-cliente/<cliente>/<mes>`, solo para quien ve esa pantalla);
  - la lista de fotos diarias de la app (`historia/`). Se citan pero no se abren desde aquí, porque no se sirven.
- **En la pantalla**:
  - 3 cifras arriba (meses con informe, enviados, contados en reunión).
  - Chips Todos · Con informe · Sin informe · Enviados, y buscador por mes («agosto», «2026-07»).
  - Una fila por mes con sus enlaces; cada clic deja rastro.
- **Contraste con GAC**: 12 meses en la hoja, 9 con informe. Agosto: enviado el 7-sep por Desk RO-6706, 2 días tarde (igual que M13). Julio, con informe y estadísticas.
- **Permisos**: Lucía recibe sus 12 clientes; Sofía recibe 403 (su ficha es solo contrato); setter_ana no tiene la pantalla.
- **Pruebas**: Tomás, Lucía (390), Jessi, Coti, Valeria, Sofía, Camilo, Mili y setter_ana sin errores ni desbordes. `pruebas_e0.py` TODO BIEN. `pruebas_coherencia.py`: 0 errores. Escáner limpio. Capturas `r5_*`.
- No he necesitado otro formato del dueño de M13: leo sus dos ficheros tal cual.

## Ronda IA + diseño (2-oct, noche)
- **IA:** `panelCopiloto(ctx, id)` en la cabecera del cliente (compacto si la persona ve «Asistente IA»), solo para quien abre el detalle del cliente y nunca administración. En Comunicación, cada correo sin contestar lleva «Sugerir respuesta» (`botonIA` sin destino: copiar o contestar en la Bandeja); nada se envía solo.
- **Correos:** cifras de `data/bandeja/por_cliente.json` (regla única de la Bandeja, días laborables); la lista de cada correo, de su copia `data/ficha/correos.json` (ahora con `dias_laborables`). Ya no se cae al bloque de Desk de las 07:00: sin el resumen, «sin dato» en gris. Administración no pide ni ve correos.
- **Pestañas en una fila** a todos los anchos: las que caben y el resto en «Más (n) ▾» (menú común); la activa siempre a la vista; se recoloca al cambiar el ancho. Probado a 1440 (7 + Más) y 390 (1 + Más).
- **Guía de diseño:** fuera la hoja propia (`ficha-estilos`); solo clases comunes y tokens; 0 textos < 12 px. El selector de cliente es el título (sin migas ni nombre repetido). Periodo común de la carcasa (`usa_periodo: ['7d','30d']`, escucha `ctx.alCambiarPeriodo`), sin selector propio. `rejillaTarjetas`, `esqueleto`, `menuMas`, `.campo`, `vacioLinea`.
- **Gemma / Gema Gregorio (Centro Consulting):** no se unen; aviso «Duda para Tomás» y marca «¿Misma persona?» solo para dirección (Tomás sí, Mili y Lucía no).
- **`contactos_manual.json`** movido a `fuentes_ficha/_privado/` (lo lee `personas_cliente.py`): el escáner `--proyecto` y la subida ya no lo ven.
- **Pruebas** (servir.py en 127.0.0.1:8851, cerrado): las 11 pestañas × tomas, mili, lucia, valeria, yessica, sofia, setter_ana × 1440/390 → 0 errores, 0 desborde, 0 textos < 12 px, 0 «null», pestañas en 1 fila; Sofía sin IA ni correos. `pruebas_e0.py` TODO BIEN · `pruebas_coherencia.py` 0 errores · `pruebas_diseno.py` ficha limpia · escáner limpio (data/ y --proyecto). Capturas `capturas/ficha/r6_*`.

## Ronda 7 de la ficha (2-oct, noche): auditoría 35 y ronda 10-11 de E0
- **Nunca «[importe]»**: `generar_ficha.py` escribe `duda` y `descripcion` sin cifra (misma regla que `P.sin_importes`) y, solo si había importe, el original en `duda_completa` / `descripcion_completa`. Son filas con `cliente_id`: el servidor les quita el importe a quien no ve ese dinero (Jerónimo y Yessica reciben «Ley de Segunda Oportunidad»; Tomás, «… (deudas de más de 20.000 €)»; la duda de Sintaer «Solo mantenimiento (67 €/mes)» solo a quien ve la cuota). `basica.json` (producción) va sin cifra y sin campo completo. La ficha pinta `…_completa || …`.
- **Parches fuera**: `menuMasLimpio()` y `pestanasEnUnaFila()` borrados; la ficha usa `pestanas({ unaFila: true })` común.
- **Privacidad**: el comentario de `personas_cliente.py` (1b) lleva un ejemplo inventado (@ejemplo.es / @ejemplo.com); su huella sale de `escaner_permitidos.json`.
- **Pruebas** (127.0.0.1:8960, copia de local.db, cerrado): pruebas_e0 TODO BIEN · pruebas_seguridad TODO BIEN · pruebas_coherencia 0 errores · pruebas_diseno --estricto 42/42 limpios · escaner --proyecto limpio. Capturas `capturas/ficha/r7_*.jpg` (Lucía GAC, Jerónimo Deudot, Tomás Sintaer/Deudot; 1440 y 390): 0 «[importe]», 0 «null», 0 errores de consola, 0 desborde, pestañas en 1 fila con «Más».
- **Duda para E0**: una búsqueda de Search Console de un cliente («delito fiscal 120.000 euros anuales», `web.json`) es texto con importe; el recorte del servidor la deja mutilada a quien no ve dinero. No es dinero: convendría que `recortar_modulo` no toque la lista `consultas`.

## A4 · objetivo del cliente y semáforo del lunes desde la cabecera (2-oct, noche)
- **Cabecera**: dos botones nuevos, «Semáforo del lunes» (color de esta semana, quién y cuándo) y «Objetivo» (leads/mes, coste por lead, coste por cita, ventas/mes). Semáforo = abrir + pulsar el color (el color guarda, con una línea de nota opcional, sin importes). Objetivo = abrir + «Guardar objetivo». Historial de las 8 últimas semanas y de los 5 últimos cambios del objetivo, con quién y cuándo.
- **Un solo almacén**: la tabla `acciones` de la base (modo simulación, con rastro), tipos `objetivo_alta` (el mismo que ya usaba Clientes nuevos) y `semaforo_semanal`. Lectura común: `fuentes_objetivos/objetivos.py` (Python: Captación → captacion.json → Mi día; escribe `data/objetivos/objetivos.json` desde `generar_ficha.py`) y `modulos/objetivos_comun.js` (ficha y Clientes nuevos: el fichero + lo guardado después, en vivo). Misma regla de reducción en los dos.
- **Permisos** (`reglas_permisos.json`): tipo `editar_objetivo_cliente` (su account, operaciones y dirección), `acciones_regla_cliente` (el servidor lo exige por cliente), `acciones_vista_previa_recortada` (al leer /api/acciones, coste_*/inversion_*/presupuesto solo a quien ve la inversión), `acciones_permitidas.ficha = [semaforo_semanal]`, `datos_de_modulo["objetivos/objetivos"]`. En `servir.py`, dos ediciones localizadas que leen esas dos claves (POST y GET de /api/acciones).
- **Otros ficheros tocados (solo para leer el mismo almacén)**: `generar_captacion.py` (el objetivo de la app manda; coste por cita contra su objetivo), `nuevos.js` (lee de `objetivos_comun.js`; botón solo para quien puede), `pruebas_coherencia.py` (5 comprobaciones «objetivos (A4)»), `pruebas_seguridad.py` (`ronda_a4`, 34 casos).
- **Probado** (copia de la app y de local.db en 127.0.0.1:9050; `fuentes_ficha/probar_a4.py`): Lucía, Candela, Mili y Jerónimo a 1440 y 390, sin errores ni desbordes; Jerónimo lo ve sin costes y sin editar. Tras cargar el objetivo de GAC y rehacer captación y Mi día en la copia: Captación «objetivos cargados» 0 → 1 y el número que manda de Lucía 50 % → 0 % («Fuera: GAC (coste por lead por encima del techo)»). Capturas `capturas/ficha/a4_*.jpg`.

## N14 · fallos de medición en la ficha (2-oct, noche)
- Lee `data/fuentes/hallazgos_medicion.json` (alta en `datos_de_modulo`, recortado por cliente; sin él, las alertas «Medición: …» de cada fuente de E1). Cabecera: «N fallos de medición · lo arregla X» (lleva a la pestaña de la fuente). Arriba de Web y SEO, Resultados, Chat o Comunicación: cada fallo con gravedad, texto, dueño y qué hacer. Capturas `capturas/ficha/n14_*.jpg`.
- **Ajuste del coordinador (A4)**: el objetivo usa la regla `editar_objetivo_alta`. Pueden cargarlo su account, operaciones y dirección. En los clientes en alta, también proyectos (Coti) y el técnico de altas (Agus). El semáforo sigue con `editar_objetivo_cliente`. La condición `cliente_nuevo` se añade en `permisos.py` y `permisos.js`. Si el cliente está en alta lo decide el servidor (`clientes.json`), nunca el navegador. 10 casos más en `pruebas_seguridad.py`.

## V2-C1 (3-oct)
- **B-A2 gravedad · ya cumplía:** «Estado: …» sale de la verdad única (Akua «Atención», igual que Captación ahora).
- **B-A4 / 39b-9 cabecera a 390 · arreglado:** el candado de contactos baja a su línea (`flex: 1 1 240px`) y la columna de datos tiene base de 260 px: nada de una palabra por línea; «Ficha» como título corto a ≤ 480 px; el desborde de 1 px venía de la frescura «Reuniones (CRM, Fathom y verificación manual)» y ahora parte línea. 0 desbordes a 390.
- **C-16 ficha ajena · arreglado:** `#/ficha/laver` para Camilo ya no enseña Orejana: «La ficha de este cliente no es de tu puesto… (Casiana)» con «Ver mis fichas (n)».
- **39b-4 tickets · arreglado:** Rastro e Informes pintan «RO-6740» como enlace a la Bandeja (`conTickets`, zona de 32 px); «a rladrero/[correo]» → «al cliente».
- **C-31 · arreglado:** la ficha básica oculta la barra de periodo. **39b-12 enlace «GSC» · no aparece ya** (facundo/greconsult a 390 sin toques pequeños). **C-20 tickets de 53×15** son del copiloto (ia_componentes): dudas.
- **B-M7 · arreglado:** `motivoSinCartera(ctx)` (exportada aquí) da el motivo exacto en las pantallas vacías.

## Puesta al día 3-oct-2026
- **Bloque «Estado de la web (Modular)»** en la pestaña «Web y SEO» (`modulos/_modular.js → bloqueEstadoWeb`): cifras de la web, problemas con acción y dueño, o «Añadir a Modular» si la web no está. Detalle en `_ESTADO_modular.md`.
- **Teléfonos de los contactos en formato internacional: en curso** en otro carril (`telefono.py`, `modulos/_telefono.js`).
