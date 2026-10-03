# E1 · Capa de datos · estado

**2-oct-2026, 14:45.** Hecho y probado. Nada escrito en ninguna herramienta externa; claves solo del llavero, sin imprimirlas; ningún dato personal de leads, ni teléfonos ni correos en los JSON (el escáner lo comprueba antes de escribir).

## En una frase

**68 clientes con un fichero cada uno y 24 fuentes con su sello; 86 de 86 cifras cotejadas con el origen y el gasto de Meta de septiembre idéntico al de la API en 3 cuentas.** Lo que falla es de acceso, no de código: SE Ranking tiene la clave mal (403), Windsor no tiene clave (Google Ads va con la muestra manual de septiembre) y TikTok no da nada.

## Ronda de arreglos (2-oct, 17:30): fallo de la auditoría → qué se ha hecho

Recarga de las 17:28 con Analytics, Search Console, Metricool, GHL y Snov leídos de nuevo, y Meta en vivo. Pruebas (17:36): `comprobar.py` (86/86 y 14/14 arreglos), `pruebas_coherencia.py` (0 errores), `pruebas_seguridad.py` (todo bien). En `pruebas_e0.py` solo falla el escáner por `data/agenda/agenda.json` (92 correos en enlaces), que no es de E1. Los ficheros de E1 pasan limpios.

| Fallo (auditoría de cifras, 28) | Estado | Qué se ha hecho |
|---|---|---|
| E-01 Kiosko Box con «Kiosko II» | **Arreglado** | `emparejamientos_manual.json → meta`: act_292218051469540 «Josep SG». E1 la lee directamente de Meta (`f_meta_directo.py`, 2 llamadas, mismas ventanas y misma definición de lead que Captación): 5.563 € en 35 días. «Kiosko II» queda en `meta_excluir`. **Falta que `captacion.py` (Captación) recoja la corrección**: hasta entonces `captacion.json` sigue con «Kiosko II» y E1 la descarta |
| E-01 prueba «cuenta > 500 € sin cliente» | **Arreglado** | Lista de las 74 cuentas con gasto de 30 días, zona y moneda (1 llamada). Por indicación de Tomás, Taller del Patinete se marca «ex cliente · gasto propio del cliente» y la cuenta propia de RO como nuestra captación (`meta_sin_cliente_conocidas`, `ex_clientes`). Quedan fuera de la prueba, de las dudas y de cualquier alerta, también en Google Ads y SE Ranking. Cualquier otra cuenta con gasto hace fallar la prueba (hoy no hay ninguna) |
| E-10 Search Console sin descontar el retraso | **Arreglado** | Edición localizada en `~/RO_HERRAMIENTAS/externos.py` (`gsc_report`): las dos ventanas de 30 días se cierran en el último día con datos. Cada bloque lleva `datos_hasta` y la nota «datos hasta el 29-09». 30 de 30 sitios |
| E-11 Metricool y GHL fuera de los emparejamientos | **Arreglado** | Id de marca en `emparejamientos.json` (FusterGüell 4373133, Consulting F 5749251, Centro Consulting 5531327 y Musashi 5625829; el resto, el id que da `externos.py`). Consulting F con `ghl` = xtSjLv44F9uT5sDpXnHC, el mismo que el embudo. Nueva comprobación: `ghl_distinto_entre_resumen_y_embudo` (vacía) |
| E-12 Concilia «publicidad prevista» | **Arreglado** | Regla de cruce: si su cuenta de Meta gastó, `servicios.publicidad = sí` con la fuente («122,66 €»). El pago pendiente es una **alerta roja** del bloque de Meta y del cliente |
| E-15 Zonas horarias de Meta | **Arreglado (en E1)** | Cada bloque de Meta lleva `zona` y `moneda`. Si el desfase con Madrid no es 0, alerta ámbar con las horas (GAC y Deudout, 9 h). Captación ya convierte a Madrid (`convertida_a_madrid`): por eso Deudout da 14,67 € en la app y 16,83 € en la API (mes en hora de California). `comprobar.py` lo explica en lugar de darlo por error |
| E-17 Monedas | **Arreglado (aviso)** | Alerta ámbar si la cuenta no factura en euros. Las duplicadas de Bit24 en INR y USD, en `meta_excluir` |
| E-20 Bautista (baja) en Musashi | **Arreglado** | Las personas con estado «baja» en la fase 0 salen de las sillas y de las filas; ocupa la silla el siguiente (Musashi, outreach → Eulimar). Lista `fuera_por_baja`. La ficha (`build_data.py`) es de E0: debería leer esto |
| E-22 Musashi Analytics «a cero» gris | **Arreglado** | Si el periodo anterior midió y el actual nada, el estado es `rota` y lleva medición «no» y alerta roja «Analytics no mide desde hace más de un mes», con dueño en web. Nunca un cero gris |
| Consulting F: Analytics y Search Console de la landing | **Arreglado (indicación de Tomás, 17:35)** | Se queda la landing como **fuente parcial**: Analytics properties/522055940 y Search Console info.consultingf.com, con sello «a medias» y la nota «solo la landing info.consultingf.com». Está en los dos manuales y se ha releído en vivo. En las dudas para Agus: pedir al cliente acceso de lector para gmb1@rankingonline.es a G-MM80LFHK4L (GTM-TLFRT2SW) y a Search Console de consultingf.com |
| FusterGüell Analytics | **Arreglado** | properties/480200463 «FusterGA4 New» en los dos manuales, leída en vivo |
| Atajos «Abrir en …» (26, parte C) | **Arreglado** | Cada bloque lleva `abrir {texto, url}`, con un único constructor (`comun.enlace`) y los formatos de C.2. Si falta el id: `url: null` y «Falta emparejar». Snov no tiene formato comprobado y va sin atajo. Prueba: 0 fuentes emparejadas sin atajo |
| Textos con códigos y ficheros | **Arreglado** | `llano()` limpia todas las notas de bloques y fuentes (sin D-xx, W2 ni «.json»). Prueba: 0 |
| Nada de ceros falsos | **Arreglado** | Las correcciones a mano que aún no se han leído salen `rota` («corregida a mano y todavía sin leer»), nunca con el dato de la cuenta mala |
| Asetra en Search Console con el sitio vacío (lo detectó SEO) | **Arreglado (17:50)** | El emparejado automático de la relectura completa cogió https://www.asetra.net/ (0 clics) en lugar de https://asetra.net/ (702 clics en 30 días). Lo he fijado a mano en los dos manuales. Al revisarlo encontré lo mismo en **Musashi** (sc-domain, error 403, → https://musashi.es/), **Greconsult** (→ https://www.greconsult.com/) y **Busbac** (busbac.com, error 403, → https://busbac.es/, que tiene datos). Los tres están fijados y releídos. Además: `externos.py` (edición localizada) ya no convierte un 403 en ceros, sino que el sitio sale «sin permiso» (`rota`). Las dudas listan los emparejamientos que cambian de una recarga a otra y los sitios de Search Console a cero (hoy: la landing de Consulting F y Romero Martínez) |
| E-02 a E-09, E-13, E-14, E-16, E-18, E-19, E-21 y E-23 | No aplica | Son de Nuevos, Captación (módulo), Dinero, `build_data.py`, Bandeja, Ficha, CRM, SEO u Horas. E1 ya les da la base: zona, moneda, `datos_hasta`, una sola subcuenta de GHL y las alertas |
| Verdad única, `ctx.*`, ADOPTADOS, capturas | No aplica | E1 no tiene pantalla: es la capa de datos que leen `generar_verdad.py` y los módulos. `pruebas_coherencia.py` sigue en verde |
| Avantik y Fitec con GHL duplicada, ECIJA, Busbac y Greconsult con Analytics muertas, Aselegal con la landing nueva, Centro Consulting con dos proyectos de SE Ranking | Pendiente de Agus | Están en `dudas_emparejamiento.md`. No hay id seguro para cambiarlos sin él |

**Para quien mantiene la tubería: orden de una sola pasada** (también en `FORMATO.md`):
1. `externos.py`, una vez al día: tarda unos 30 minutos.
2. `snov/por_cliente.py` justo después, porque `externos.py` reescribe `externos.json` sin Snov.
3. `captacion.py`.
4. `build_data.py`.
5. `fuentes/generar_datos.py --en-vivo meta` (2 llamadas). En la recarga ligera va sin `--en-vivo`.
6. Los generadores de los módulos.
7. `fuentes_verdad/generar_verdad.py`.
8. El catálogo y `foto_diaria.py`.

`recarga.json` no tiene los pasos 1, 2, 3 ni `generar_verdad.py`: lo propongo y no lo toco, porque es común.

**Para Captación:** que `captacion.py` lea `fuentes/emparejamientos_manual.json → meta` y `meta_excluir`, así el arreglo de Kiosko llega también a su pantalla. `fuentes_informe/generar_informe.py` lleva sus propias correcciones (Consulting F, FusterGüell): ahora ya están en E1 y las puede quitar.

## Carril N14 (2-oct, 22:45): cada fuente es del cliente correcto

Detalle en `../42_AUDITORIA_FUENTES_CLIENTE.md`. Corregido en `emparejamientos_manual.json` (con motivo y fecha): Busbac GA4 → 372386569 (la de su web); ECIJA y Greconsult sin Analytics (leían propiedades que no están en su web); Romero Martínez y Optimalia sin Search Console (403); Sol-4 sin GHL (cogía una plantilla de RO); Gómez y Carvacho con su Search Console; canal de ClickUp corregido en AGC, MG Economistes, Gómez y Carvacho y Consulting F (nueva sección `chat`). Consultas de Search Console sin filas de exportaciones de Google Ads (Octoedro). Hallazgos de medición con dueño en `data/fuentes/hallazgos_medicion.json`; los rojos y ámbar entran como alertas del cliente. Nueva prueba: ninguna fuente en dos clientes.

## Qué hay

| Fichero | Qué es |
|---|---|
| `fuentes/generar_datos.py` | La recarga. Plan B por defecto (0 llamadas, lee lo último de cada lector); `--en-vivo zoom,seranking,externos,windsor` o `todo` para plan A. |
| `fuentes/comun.py`, `universo.py` | Rutas, saneado, escáner de secretos, escritura atómica; universo de clientes y cruce de identificadores (app, panel, portal, fase 0, captación, libro). |
| `fuentes/f_panel.py` | 11 fuentes del panel de Mili (cartera, horas, tareas, informes, Desk, Zadarma, reuniones, outreach, alarmas, arranque, chat). |
| `fuentes/f_externos.py` | GA4, Search Console, Metricool, GHL (resumen) y Snov. |
| `fuentes/f_captacion.py` | Meta y embudo de GHL desde `20_FASE2_CAPTACION/captacion.json` (**integrado**: el fichero de `captacion.py` ya existía; E1 solo lo lee). Plan B: `meta_clientes.json` del panel. |
| `fuentes/f_windsor.py` | Google Ads y TikTok. Hoy plan C (muestra manual); listo para `ws.py` en cuanto haya clave. |
| `fuentes/f_seranking.py`, `f_zoom.py`, `f_libro.py` | SE Ranking (emparejado por dominio), Zoom (grabaciones, copia saneada en `_cache/`), libro de clientes + Holded y asignaciones de la fase 0. |
| `fuentes/emparejamientos_manual.json` | Correcciones por identificador (Google Ads, SE Ranking). Lo revisa Agus. |
| `fuentes/dudas_emparejamiento.md` | Dudas para Agus (se rehace en cada recarga). |
| `fuentes/comprobar.py` · `_comprobacion_E1.json` | Prueba de aceptación y su resultado. |
| `fuentes/FORMATO.md` | El contrato para los módulos. |
| `data/clientes/<id>.json` (68) · `data/indice_clientes.json` · `data/fuentes.json` · `data/emparejamientos.json` | La salida. 1,6 MB en total. |

## Salud de las fuentes (recarga de las 14:29, plan B + Zoom leído a las 14:29)

| Fuente | Estado | Edad | Clientes con dato | Plan | Nota |
|---|---|---:|---:|---|---|
| Cartera (ClickUp) | bien | 5 h | 66 | B | |
| Horas (ClickUp) | **dato viejo** | 5,2 h (límite 3) | 66 | B | recarga del panel 09:16; a medias (52 % imputado) |
| Tareas (ClickUp) | bien | 5 h | 52 | B | 14 sin carpeta de cliente |
| Informes mensuales | bien | 14 h | 66 | B | |
| Desk | **dato viejo** | 7,5 h (límite 3) | 57 | B | foto de las 07:00; 9 sin cuenta en Desk |
| Zadarma | bien | 8 h | 66 (29 con llamadas) | B | sin números de teléfono |
| Reuniones (CRM + Fathom) | bien | 29 h | 66 | B | a medias |
| Outreach (chats y hojas) | bien | 14 h | 14 | B | muchas cifras a null |
| Alarmas del panel | bien | 3 h | 66 | B | |
| Arranque de altas | bien | 3 h | 16 | B | |
| Canal de ClickUp | bien | 1 h | 46 | B | |
| GA4 | bien | 0,3 h | 33 (4 a cero) | B | Musashi, FusterGüell, Busbac y ECIJA sin datos en 30 días: ¿etiqueta caída? |
| Search Console | bien | 0,3 h | 31 | B | |
| Metricool | bien | 0,3 h | 20 | B | seguidores sí; programado todavía no |
| GHL (resumen) | bien | 0,3 h | 37 | B | |
| Snov | bien | 0,3 h | 11 | B | |
| Meta | bien | 0,2 h | 28 | A (captacion.json) | 16 con gasto, 12 a cero |
| Embudo GHL | bien | 0,2 h | 21 | A (captacion.json) | 7 cuentas de Meta sin subcuenta de GHL |
| Google Ads | **sin conectar** (muestra) | — | 10 | C · muestra manual 2-oct | 5 con gasto en sep (AyG, Kiosko, Consulting F, GAC, Busbac) + 5 parados sin id |
| TikTok | **sin conectar** | — | 0 | C | la consulta del 2-oct se cortó |
| SE Ranking | **rota** | — | 0 (40 emparejados) | B · lista del conector | la clave de proyectos del llavero da 403 |
| Zoom | bien | 0 h | 4 | A/B (`_cache/`) | 27 grabaciones en 30 días; solo 4 clientes con su nombre en el título (D-06) |
| Libro + Holded | bien | 30 h | 61 | B · libro del 1-oct | Holded por cliente en vivo todavía no (hd.py solo lee compras) |
| Asignaciones (fase 0) | bien | 0,3 h | 64 | B · borrador | sin validar por Mili |

Frecuencias previstas (04 §4, A10): ClickUp, Desk y Meta cada hora; GA4, Search Console, SE Ranking, Windsor, Zoom y libro, diario. **La recarga periódica no está programada**: ClickUp y Desk dependen de la recarga del panel (07:38 y 14:38) y Meta de `captacion.py`. Propuesta: un `launchd` que lance `generar_datos.py` a los 10 minutos de cada recarga del panel y `--en-vivo zoom,externos` una vez al día. No lo he creado (es configuración persistente: lo decide Tomás).

## Pruebas de aceptación (`comprobar.py`, semilla 20261002)

- **10 clientes al azar** (Conficonsulting, CIB Partners, MG Economistes, Emex, Liébana, Deudot, Segú, Akua, Joan Lluís Vives, Geslabor): **86/86 cifras coinciden** con el origen leído por otro camino. Ojo: para las fuentes del panel y de externos el «origen» es el JSON que deja su lector, no la API; eso prueba que E1 no pierde ni cambia nada, no que el lector acierte.
- **Meta contra la API en vivo** (3 llamadas): Emex 115,34 €, Deudot 16,83 € y Akua 2.343,73 € de gasto en septiembre, **idénticos** a la app.
- **Cada fuente con su sello**: 0 bloques sin estado u hora.
- **Ningún dato personal**: escáner limpio (correos, teléfonos, claves, códigos de grabación). Zadarma va sin números (ni enmascarados); Zoom sin enlaces, códigos ni correo del anfitrión; SE Ranking sin los enlaces de invitado.
- **Cero emparejamientos copiados** entre clientes (`copiados_entre_clientes` vacío).

## Huecos y dudas

**Para Tomás (accesos, 30 segundos cada uno):**
1. **SE Ranking:** la clave `seranking_project_key` devuelve 403. Pegar la de «API de proyectos» con `bash ~/RO_HERRAMIENTAS/seranking/pegar.sh`. Con eso salen posiciones de 40 clientes ya emparejados por dominio (no gasta créditos).
2. **Windsor (W2):** guardar `windsor_api_key` (`bash ~/RO_HERRAMIENTAS/windsor/pegar.sh`). El lector está listo: pasa solo de la muestra a `ws.py`, con campañas y meses.
3. **Recarga programada** (arriba): ¿la dejo con `launchd`?

**Para Agus (`dudas_emparejamiento.md`):**
- 13 clientes con publicidad «sí» o «prevista» y **sin cuenta de Meta emparejada** (Sol-4, Geslabor, AGC, CIB, Abner y Gestió Plural con «sí»; los 7 nuevos del Motor con «prevista»).
- Google Ads: **Fountainhead Holding** (308 € en sep) no es ningún cliente; **Taller del Patinete** sigue gastando en Google Ads y tiene proyecto activo en SE Ranking; 5 cuentas paradas (Aselegal, FITEC, Greconsult, CE Consulting, BIT24) sin id de cuenta; Asetra, Oteca y MG no están en Windsor.
- SE Ranking: Centro Consulting tiene dos proyectos (web de la franquicia y web propia; tomo la propia); 9 proyectos activos sin cliente (QualityConta, CLCripto, Medalva, GEMAP, Novacofm, Pummba…): ¿se siguen pagando?
- Libro: activos sin cliente en la app (Gema Mishel García Gómez, Legal4U, Gold Global Projects: ¿Gestió Plural factura como Gold Global Projects?) y clientes de la app que no están en el libro (PGB Auditores, Laver, Quique, Marlex, Gestió Plural, Gómez y Carvacho, Think Value). Barreda Díaz **no** se casa con Quique (memoria 1-oct).

**Para E0 y la base:**
- La fase 0 usa el id del **portal** (`abner`, `ayg`) y la app el slug del panel (`abner-advisory`, `ayg-asesores`). Cada fichero de cliente trae `ids.fase0` para unirlos; conviene que E0 normalice `asignaciones.json` al id de la app.
- La foto diaria en `historia/AAAA-MM-DD/` (M9, 7/30/90 días) es de E0: basta con copiar `data/clientes/` y `data/fuentes.json` tras cada recarga.
- `data/clientes/*.json` llevan cuota, facturación e inversión: **no deben servirse tal cual al navegador**; los recorta `servir.py` (R8).

**Lo que no se ha hecho (fuera de E1 o sin acceso):** Holded por cliente en vivo (hd.py solo lee compras; uso el libro del 1-oct), publicaciones programadas de Metricool, reuniones de Zoom no grabadas (W4), WhatsApp (W6), escritura en cualquier herramienta.

## Cobertura por cliente

B bien · V dato viejo · 0 a cero · R rota · · sin conectar · – no aplica. «Con dato» = bien + viejo + a cero sobre las fuentes aplicables.

| Cliente | Libro | cartera | horas | tareas | informes | desk | zadarma | reuniones | outreach | alarmas | arranque | chat | ga4 | gsc | metricool | ghl | snov | meta | captacion_ghl | google_ads | tiktok | seranking | zoom | libro | asignaciones | Con dato |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Abner Advisory | Activo | B | V | · | B | · | B | B | – | B | B | B | · | · | · | 0 | – | · | · | – | · | · | 0 | B | B | 12/21 |
| Accompany | Activo | B | V | B | B | V | 0 | B | – | B | – | B | B | · | · | · | – | B | · | – | · | R | 0 | B | B | 14/20 |
| Adade Zaragoza | Activo | B | V | B | B | V | B | B | – | B | – | B | B | B | B | B | – | 0 | B | – | · | R | 0 | B | B | 18/20 |
| AGC | Activo | B | 0 | · | B | · | 0 | B | – | B | B | B | · | · | · | 0 | – | · | · | – | · | · | 0 | B | B | 12/21 |
| Ahedo | Activo | B | V | B | B | V | 0 | B | – | B | – | B | · | · | B | · | – | · | · | – | · | R | 0 | B | B | 13/20 |
| Akua | Activo | B | V | B | B | V | 0 | B | – | B | – | · | · | · | · | B | – | B | B | – | · | · | 0 | B | B | 14/20 |
| Aselegal | Activo | B | V | B | B | V | 0 | B | B | B | – | B | B | B | B | B | 0 | 0 | B | 0 | · | R | B | B | B | 21/23 |
| Asetra | Activo | B | V | B | B | V | B | B | – | B | – | B | B | B | B | · | – | · | · | · | · | R | 0 | B | B | 15/21 |
| Aster Asesoría | Activo | B | V | B | B | V | 0 | B | – | B | – | B | · | B | B | B | – | 0 | B | – | · | R | 0 | B | B | 17/20 |
| Avantik | Activo | B | V | B | B | V | 0 | B | – | B | – | · | B | B | B | B | – | · | · | – | · | R | 0 | B | B | 15/20 |
| AyG Asesores | Activo | B | V | B | B | V | 0 | B | – | B | – | B | B | B | B | · | – | 0 | · | B | · | R | 0 | B | B | 17/21 |
| Billeo | Activo | B | 0 | · | B | · | B | B | – | B | B | · | · | · | · | 0 | – | · | · | – | · | · | 0 | B | B | 11/21 |
| BIT 24 | Activo | B | V | B | B | V | 0 | B | – | B | – | B | · | · | B | · | – | B | · | 0 | · | R | 0 | B | B | 15/21 |
| Bonet Asesores | Activo | B | V | B | B | V | B | B | – | B | – | B | · | B | B | B | – | 0 | 0 | – | · | R | 0 | B | B | 17/20 |
| Busbac | Activo | B | V | B | B | V | 0 | B | B | B | – | B | 0 | 0 | · | B | B | B | 0 | B | · | R | 0 | B | B | 20/23 |
| Campalans | Extras sueltos | B | V | B | B | V | 0 | B | – | B | – | · | B | · | · | · | – | · | · | – | · | · | 0 | B | · | 11/20 |
| Centro Consulting | Activo | B | V | B | B | V | B | B | B | B | – | B | · | · | · | B | B | 0 | 0 | 0 | · | R | 0 | B | B | 18/23 |
| Christian Sanchez | Activo | B | V | B | B | 0 | 0 | B | – | 0 | – | B | B | B | · | B | – | · | · | – | · | R | 0 | B | B | 15/20 |
| CIB Partners | Activo | B | 0 | · | B | · | B | B | – | B | B | · | · | · | · | 0 | – | · | · | – | · | · | 0 | B | B | 11/21 |
| Concilia | Activo | B | V | B | B | V | 0 | B | – | B | – | B | · | · | · | B | – | B | B | – | · | · | 0 | B | B | 15/20 |
| Conficonsulting | Activo | B | 0 | · | B | V | B | B | – | B | B | · | · | · | · | 0 | – | · | · | – | · | · | 0 | B | B | 12/21 |
| Consulting F | Activo | B | V | B | B | V | B | B | – | B | – | · | B | 0 | · | · | – | B | B | B | · | R | 0 | B | B | 16/21 |
| Deudot | Activo | B | V | B | B | V | 0 | B | – | B | B | B | · | · | B | B | – | B | B | – | · | R | 0 | B | B | 17/21 |
| ECIJA Advisory | Activo | B | V | B | B | V | B | B | B | B | – | B | 0 | B | · | · | B | · | · | – | · | R | 0 | B | B | 16/22 |
| Ecom Advisory | Activo | B | V | B | B | V | 0 | B | B | B | – | B | · | · | B | B | B | B | B | – | · | R | 0 | B | B | 18/22 |
| Emex | Activo | B | V | B | B | V | B | B | – | B | B | B | · | · | · | B | – | B | B | – | · | · | 0 | B | B | 16/21 |
| Finexen | Activo | B | V | B | B | V | 0 | B | B | B | – | · | · | · | · | · | B | · | · | – | · | · | 0 | B | B | 13/22 |
| Fitec Asesores | Activo | B | V | B | B | V | B | B | – | B | – | · | B | B | B | B | – | · | · | 0 | · | R | 0 | B | B | 16/21 |
| FusterGüell | Activo | B | V | B | B | V | B | B | – | B | – | · | 0 | B | · | · | – | · | · | – | · | R | 0 | B | B | 13/20 |
| GAC | Activo | B | V | B | B | V | B | B | B | B | – | B | B | · | B | B | B | B | B | B | · | R | 0 | B | B | 20/23 |
| Garmande | Activo | B | V | B | B | V | B | B | – | B | B | B | · | · | · | B | – | 0 | B | – | · | · | 0 | B | B | 16/21 |
| Geslabor | Activo | B | V | · | B | V | B | B | – | B | B | B | · | · | · | 0 | – | · | · | – | · | · | 0 | B | B | 13/21 |
| Gestanex | Activo | B | V | B | B | V | 0 | B | – | B | – | B | · | · | · | · | – | B | · | – | · | R | 0 | B | B | 13/20 |
| Gestió Plural | — | B | V | · | B | · | 0 | B | – | B | B | B | · | · | · | 0 | – | · | · | – | · | · | 0 | · | B | 11/21 |
| Gomez y Carvacho | — | B | V | B | B | V | 0 | B | – | 0 | – | B | B | · | · | · | – | · | · | – | · | · | 0 | · | · | 11/20 |
| Greconsult | Activo | B | V | B | B | V | B | B | B | B | – | B | B | B | · | · | B | · | · | 0 | · | R | B | B | B | 17/23 |
| Imfor Asesores | Activo | B | 0 | · | B | · | B | B | – | B | B | · | · | · | · | · | – | · | · | – | · | · | 0 | B | B | 10/21 |
| Impulsa CFO | Activo | B | 0 | · | B | V | B | B | – | B | B | · | · | · | · | 0 | – | · | · | – | · | · | 0 | B | B | 12/21 |
| Innova Scala | Activo | B | V | B | B | V | B | B | – | B | – | B | B | B | B | B | – | B | B | – | · | R | 0 | B | B | 18/20 |
| IP Forense | Activo | B | V | B | B | 0 | 0 | B | – | B | – | B | B | B | · | · | – | 0 | · | – | · | R | 0 | B | B | 15/20 |
| J&D Consulting | Activo | B | V | B | B | V | B | B | – | B | – | · | B | · | · | · | – | · | · | – | · | R | 0 | B | B | 12/20 |
| Jesús Navarro (JENASA) | Proyecto | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | – | · | · | – | · | · | 0 | B | B | 3/22 |
| Joan Lluís Vives | Activo | B | V | B | B | V | B | B | – | B | – | B | B | B | B | · | – | B | · | – | · | R | 0 | B | B | 16/20 |
| Kiosko Box | Activo | B | V | B | B | V | 0 | B | – | B | – | B | B | B | · | · | – | 0 | · | B | · | R | 0 | B | B | 16/21 |
| Laver | — | B | V | B | B | V | 0 | B | – | B | B | B | B | B | · | B | – | B | B | – | · | R | 0 | · | B | 17/21 |
| Liebana Consulting | Activo | B | V | · | B | V | 0 | B | – | 0 | – | · | · | · | · | · | – | · | · | – | · | · | 0 | B | B | 10/20 |
| Lobo | Activo | B | V | B | B | V | B | B | – | B | B | B | · | · | · | B | – | 0 | B | – | · | · | 0 | B | B | 16/21 |
| Marlex Consulting | — | B | 0 | · | B | · | 0 | B | – | B | B | · | · | · | · | · | – | · | · | – | · | · | 0 | · | B | 9/21 |
| MG Economistes | Activo | B | V | B | B | V | 0 | B | – | B | – | B | B | B | · | · | – | · | · | · | · | R | 0 | B | B | 14/21 |
| Musashi Consultores | Activo | B | V | B | B | V | 0 | B | B | B | – | B | 0 | B | B | B | B | B | B | – | · | R | 0 | B | B | 20/22 |
| Octoedro | Activo | B | V | B | B | V | 0 | B | B | 0 | – | B | B | B | · | B | – | · | · | – | · | R | 0 | B | B | 16/21 |
| Optimalia | Proyecto | B | V | B | B | V | B | B | – | B | – | · | · | 0 | · | · | – | · | · | – | · | · | 0 | B | B | 12/20 |
| Orejana | Activo | B | V | B | B | V | 0 | B | B | B | – | B | B | B | · | B | – | B | 0 | – | · | R | B | B | B | 18/21 |
| Oteca | Activo | B | V | B | B | V | 0 | B | – | B | – | B | B | B | B | B | – | 0 | B | · | · | R | 0 | B | B | 18/21 |
| PGB Auditores | — | B | V | B | B | V | 0 | B | B | B | – | · | · | · | · | · | B | · | · | – | · | · | 0 | · | B | 12/22 |
| Prodegest | Activo | B | V | B | B | V | 0 | B | – | B | – | B | B | B | · | B | – | · | · | – | · | R | 0 | B | B | 15/20 |
| Proincentiva | Activo | B | V | B | B | V | 0 | B | B | B | – | B | · | · | · | B | B | · | · | – | · | · | 0 | B | B | 15/22 |
| Quique Gomez Barreda | — | B | V | B | B | V | B | B | – | B | – | B | · | · | · | B | – | 0 | 0 | – | · | · | 0 | · | · | 13/20 |
| Romero Martínez | Activo | B | V | B | B | V | 0 | B | B | B | – | B | · | 0 | B | · | – | · | · | – | · | R | B | B | B | 15/21 |
| Segú Assessors | Activo | B | V | B | B | V | B | B | – | 0 | – | B | B | B | B | B | – | · | · | – | · | R | 0 | B | B | 16/20 |
| Sintaer | Activo | B | V | · | B | · | 0 | B | – | 0 | – | · | · | · | · | · | – | · | · | – | · | · | 0 | B | B | 9/20 |
| Sol-4 | Activo | B | V | B | B | V | 0 | B | – | B | – | B | B | B | · | · | – | · | · | – | · | R | 0 | B | B | 14/20 |
| Think Value | — | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | – | · | · | – | · | · | 0 | · | B | 2/22 |
| Torrevieja Consult | Activo | B | V | B | B | V | B | B | – | B | – | B | B | B | B | B | – | · | · | – | · | R | 0 | B | B | 16/20 |
| Tribulex | Activo | B | V | B | B | V | 0 | B | – | B | – | B | B | B | · | · | – | · | · | – | · | R | 0 | B | B | 14/20 |
| TST Consulting | Activo | B | 0 | · | B | · | B | B | – | B | B | · | · | · | · | 0 | – | · | · | – | · | · | 0 | B | B | 11/21 |
| Volatt | Baja | B | V | · | B | V | 0 | B | – | 0 | – | · | · | · | · | · | – | · | · | – | · | · | 0 | B | · | 9/20 |
| Xterna | Activo | B | V | B | B | V | B | B | – | B | – | B | B | · | · | · | – | · | · | – | · | R | 0 | B | B | 13/20 |
