# Estado · M13 Informes mensuales y M15 Reuniones (2-oct-2026)

## Hecho

| Módulo | Fichero | Datos | Generador |
|---|---|---|---|
| M13 Informes mensuales (`#/informes-mensuales`) | `modulos/informes_mensuales.js` | `data/informes/informes.json` | `fuentes_informes/generar_informes.py` (ClickUp `cu.py` + Desk `zh.py`, en vivo; `--ficheros` = última lectura) |
| M15 Reuniones (`#/reuniones`) | `modulos/reuniones.js` | `data/reuniones/reuniones.json` | `fuentes_reuniones/generar_reuniones.py` (Zoom `zm.py` en vivo + capa E1 + panel; `--ficheros` = copia saneada) |

Altas comunes (ediciones localizadas): `reglas_permisos.json → datos_de_modulo` (`informes/informes`, `reuniones/reuniones`), `modulos/indice.js` (las dos entradas a «hecho»), una línea por módulo en `LEEME.md`, apunte en `dudas_pintura.md`. Iconos: ya estaban en `ICONO_MODULO` (`doc`, `video`).

### M13 · Informes mensuales (punto 2 de Mili, D-09)
- **Hecho** = tarea del informe del mes cerrada en ClickUp (8.983 tareas actualizadas desde el 1-ago leídas con la llave propia; 364 de informe). **Enviado** = correo saliente en Desk (los 30 departamentos) a un contacto del cliente con «informe/resultados/reporte» y el mes o «mensual» en el asunto; el cliente se reconoce por el dominio del destinatario (gacgrup.es casa con gacgrup.com) o el nombre. Un correo con PDF pero sin el mes en el asunto sale como **«posible»** (panel «Correos para mirar a mano»), nunca como enviado: la primera pasada marcó a Greconsult por un PDF de «informe de migración» y se corrigió (cero falsos «enviado»).
- Plazo D-09: franja arriba («Quedan 3 días para el día 5»); desde el 6, rojo + botón «Avisar a Mili» (cola simulada, chat de ClickUp con W1). Tiles: enviados a tiempo, pendientes, hechos sin enviar, sin tarea, días para el límite. Por account (barras, pulsar filtra la tabla). Tabla con chips que se quedan. «Enviado por otra vía» con motivo, detalle y enlace → `ctx.accion` (`enviado_otra_via`), sello en la fila y en el rastro. Mes anterior (agosto) en el selector.
- Exentos (mantenimiento y «sin contacto mensual»), altas del propio mes = «no aplica» (ver duda).
- **Histórico (W5):** hueco con el formato exacto de la hoja (cliente, mes, enlace informe, enlace estadísticas, informado en reunión, enviado) e importador `fuentes_informes/importar_hoja_w5.py` (CSV hoy; Zoho Sheet con llave en W5; rechaza la pestaña «Credenciales» por nombre).

### M15 · Reuniones (punto 8 de Mili, D-06)
- **Permisos de Zoom comprobados hoy:** grabaciones de la cuenta ✔, participantes de reuniones pasadas ✔ (`/past_meetings/<uuid>/participants`), resumen de Zoom ✔. **No** hay `meeting:read:list_meetings` / `past_meeting` ni informes: las reuniones no grabadas no se ven. Dicho en una franja fija arriba: «Lo que no pasa por el Zoom de RO no se cuenta…».
- 31 grabaciones en 120 días (3 en agosto, 12 en septiembre, 16 el 1-2 de octubre: la grabación automática empezó el 2-oct); 3 de menos de 2 minutos descartadas → 28 reuniones, 64 asistencias, 17 personas.
- Interna / con cliente / con gente de fuera por el dominio de los participantes (y el nombre del cliente en el título). Tipo por el prefijo (Daily, Coordinación, 1:1, Seguimiento, Formación, Cliente); hoy **ninguna** lleva prefijo → «Sin tipo · ¿sugerido?» con desplegable (`ctx.accion` `clasificar_reunion`).
- Pestañas: Reuniones (por día, con grabación / transcripción / resumen enlazados al portal de Zoom —nunca el enlace con código—, «Acta» para enlazar o subir documento en simulación, resumen de Zoom solo en internas) · Por persona (horas, % de 128 h, internas, con fuera, reparto por tipo, sin acta) · Reunión con cada cliente (mes pasado, CRM + Fathom + verificación + Zoom ≥ 20 min; mantenimiento exento) · Dailies (Mili y dirección; hoy vacío que explica la norma D-06 y quién la comunica).
- Títulos de reuniones sin cliente reconocido: se quita el nombre de la persona de fuera («Reunión con Tomás · con persona de fuera») por D-88.

## Cifras contrastadas con su fuente
1. **GAC, informe de agosto enviado el 7-sep, RO-6706**: leído hilo a hilo en Desk por API (saliente 2026-09-07 17:48 a tres contactos @gacgrup.es). Coincide con la verificación manual del panel.
2. **Informes de septiembre enviados a 2-oct = 0**: Desk en vivo; coincide con la nota del panel («a 2-oct no hay ningún correo de informe de septiembre en Desk»). Agosto: 33 enviados, igual que `informes_mensuales.json` (33), 5 de ellos el día 5 o antes.
3. **Clientes sin reunión en septiembre = 6** (Campalans, Consulting F, J&D Consulting, Joan Lluís Vives, Torrevieja Consult, Tribulex): idéntico a `sin_reunion_mes_ant` del panel de Mili (`datos.json`).
4. **Grabaciones de Zoom**: 3 / 12 / 16 por mes según `/accounts/me/recordings` (sondeo independiente del generador).
5. **Cartera de Lucía**: 13 clientes en `clientes.json` = 13 filas de septiembre que le sirve el servidor.

## Pruebas (`fuentes_reuniones/probar_m13_m15.py`, Playwright + Chrome, servir.py en 8793)
- `?yo=` tomas, mili, lucia, valeria, yessica, constanza, setter_ana × 1440 y 390 px × 2 módulos: **0 errores de consola propios, 0 px de desborde**. (Se filtran los 404 de `personas.js`, `decisiones.js`, `incidencias.js`, dados de alta por otros agentes antes de existir.)
- Recorte en el servidor (respuesta de red, no pantalla): informes → Tomás/Mili/Constanza 130 filas, Lucía 24 (sus 12-13 clientes × 2 meses), Valeria/Yessica/Ana **403**. Reuniones → Tomás/Mili 64 asistencias de 17 personas; Lucía 1 (la suya); Valeria 6 (las suyas); Yessica 7 (ella y su equipo); Ana 0 y vacío útil.
- Chips, filtro por account, formulario «Enviado por otra vía», cambio de mes, las 4 pestañas; «ver como» Mili → desplegables y botones en solo lectura.
- Escáner de secretos: `data/informes/` y `data/reuniones/` limpios. (Avisa en `data/ajustes/conexiones.json`, que no es de este módulo.)
- Capturas: `capturas/informes-mensuales/` y `capturas/reuniones/` (cada persona a 1440 y 390, completas de Tomás, Mili y Lucía, interacciones).

## Falta / espera acceso
- **W4** (Zoom: reuniones pasadas no grabadas + `meeting:write`): sin él, solo las grabadas. Hasta octubre no habrá un mes completo con grabación automática.
- **W5** (Zoho Sheet): histórico de la hoja; el importador espera la llave.
- **W1**: «Avisar a Mili», «Enviado por otra vía», clasificar reunión y subir acta quedan en la cola simulada (almacén de actas en Cloudflare).
- Revisión de argentinismos del adjunto (exigencia 47): no se baja el adjunto; pendiente.
- Norma D-06 de nombres: hasta que se use, el tipo es manual o sugerido.
- Sesión de revisión con Coti, Mili y Agus (R15): pendiente.

## Dudas para Tomás (con la recomendación que se sigue)
- Altas del propio mes en informes = «no aplica» (el panel excluía 90 días). Se sigue así.
- Agosto: solo 5 de 33 informes salieron el día 5 o antes (la mayoría el 7-8 de septiembre). Con la D-09 eso sería rojo; se enseña como «tarde», sin alarma retroactiva.
- La reunión de equipo del 2-oct («Lucía Caso's Zoom Meeting», 12 de RO + 1 invitado sin correo) cuenta como «con gente de fuera». Con la norma de nombres («Coordinación ·») se clasifica sola.

## Cómo regenerar
```bash
cd 30_APP_PROTOTIPO
python3 fuentes_informes/generar_informes.py     # ClickUp + Desk en vivo (~7 min, ~170 llamadas)
python3 fuentes_reuniones/generar_reuniones.py   # Zoom en vivo (~60 llamadas)
python3 fuentes_reuniones/probar_m13_m15.py 8793 # con servir.py --puerto 8793 en marcha
```

---

## Ronda de arreglos (2-oct noche)

| Fallo de la auditoría | Estado |
|---|---|
| Reuniones con otro account en Campalans, Emex y Quique (coherencia) | **Arreglado**: account = `verdad.account` (principal vigente; Campalans sale «Sin account», como en la verdad). `reuniones` añadido a `ADOPTADOS`: `pruebas_coherencia.py` sin errores ni avisos de este módulo. Informes también toma el account de la verdad |
| «6 sin reunión» frente a «1» de En rojo (22 I-09) | **Arreglado/unificado**: la verdad y la base ya dan 6 con la misma regla; en pantalla dice «Misma regla que En rojo». Se suman las reuniones de los grupos de WhatsApp (`data/whatsapp/whatsapp.json`) en cuanto haya datos; hoy «sin dato» en gris (no se conectó) |
| Sofía recibe las reuniones de 67 clientes (22 I-02, 26 E45) | **Arreglado**: `administracion: null` en la entrada de `indice.js`; el servidor le da 403 |
| Títulos en inglés y la reunión con AGC como «Interna» (22 P-05, 29 nº 39) | **Arreglado**: «with» → «con», «X's Zoom Meeting» → «Reunión de X», «Call» → «Llamada», «Meeting created by» → «Reunión creada por», palabra cortada «A…» fuera; siglas cortas («AGC») casan con el cliente → «Reunión de Tomás con AGC», con cliente |
| «Dailies» y «Norma : el tipo» (29) | **Arreglado**: «Reuniones diarias»; textos reescritos sin códigos (nada de D-06, D-25, D15, W1, W4, D-09, D-01 en pantalla) |
| 14 desplegables nativos (29) | **Arreglado**: botón «Sin tipo · ¿sugerido?» que abre los 6 tipos como chips (el sugerido primero), Esc cancela |
| Letra de 11,5 px (29) | **Arreglado** a 12 px (las mayúsculas espaciadas siguen a 11) |
| Faltan atajos a Fathom y al evento del CRM (26 C.3) | **Arreglado**: columna «Abrir» por cliente con Fathom (`fathom.video/calls/<id>`, de las llamadas de Tomás del panel de dirección casadas por despacho), evento del CRM de Zoho (`crm.zoho.eu/crm/tab/Events/<id>`, de la agenda) y grabación de Zoom. Los ids van como número (el escáner leía un id de 9 cifras como teléfono) |
| Atajo a cada correo de Desk (Informes) | **Ya estaba**: cada «enviado» y cada «posible» llevan su ticket de Desk; la tarea, su ClickUp; ahora además el informe y las estadísticas de la hoja |
| Informes: «D-09» a la vista y «: verde si…» (22, 29) | **Arreglado**: textos sin códigos |
| Informes: tabla cortada a 1024 (29) | **Arreglado**: el account va bajo el nombre del cliente (una columna menos) |
| Histórico de la hoja de Zoho | **Hecho por API** (llave nueva con ZohoSheet.dataAPI.READ). Solo se pide la lista de nombres de hojas y el rango de «Informes mensuales » (sheetid 22, con espacio final en Zoho); «Credenciales» se rechaza por nombre antes de cualquier llamada. `worksheet.content.get` devuelve el **hipervínculo de cada celda** (campo `url`). La hoja es irregular (bloques de 4 a 7 columnas, etiqueta del mes desplazada, «Septimebre»): se lee por las cabeceras de la fila 2. Resultado: **650 filas de 61 clientes, de oct-2025 a sep-2026, 371 con enlace, 250 enviados**; 15 nombres de la hoja sin cliente activo (bajas) quedan con su nombre; `emparejamiento_hoja.json` casa SOL4 GESTION, FITECC y E Advisory (= ECIJA, a confirmar por Mili) |
| Cuadre hoja frente a la app | **Hecho**: agosto y septiembre, 86 comparados, 79 coinciden, **7 diferencias** (agosto): la hoja marca enviado y en Desk no hay correo en Accompany, Aster Asesoría, BIT 24, Ecom Advisory, J&D Consulting y Musashi; Desk tiene el correo y la hoja no lo marca en Proincentiva. Se ven en la columna «Hoja de Zoho» y en el panel del histórico. Con esto la hoja deja de hacer falta |
| Nombres de prospectos enmascarados para el propio Tomás (29 F-10) | **No aplica a este módulo** (es de Ventas y Agenda; aquí los títulos de reuniones sin cliente ya llevan «con persona de fuera») |

**Pruebas de esta ronda** (servir.py en 8797, cerrado): `probar_m13_m15.py` con las 7 personas a 1440 y 390 px → **TODO BIEN** (0 errores propios, 0 desborde; capturas `capturas/*/r3_*`); Sofía → 403 en Reuniones; `pruebas_coherencia.py` → reuniones ✓ account y ✓ sin reunión, 0 errores; `pruebas_e0.py` → solo falla el escáner por `data/agenda/agenda.json` (92 hallazgos, de otro módulo); `data/informes/` y `data/reuniones/` limpios.

**Regenerar el histórico:** `python3 fuentes_informes/importar_hoja_w5.py --zoho` (o `--reemparejar` sin llamar a Zoho) y después `python3 fuentes_informes/generar_informes.py --ficheros`. Zoho limita los canjes de llave por minuto: el importador reintenta 4 veces.

## N6 · diseño 10/10 (2-oct)
**Qué cambió (solo presentación; datos, permisos, acciones y teclado igual):**
- Los dos módulos sin hoja propia (fuera `ESTILO`/`estilos()`): clases comunes + `style` con tokens. `pruebas_diseno.py`: ambos en «Limpios».
- Periodo común: `usa_periodo` y `ctx.periodo` + `ctx.alCambiarPeriodo`; fuera los selectores de mes propios.
  - Reuniones: `['mes','mes_ant']` (se mide por mes con capacidad de 128 h). Mes = `periodo.desde`, comparación = mes de `periodo.comp` («Sin comparar» quita la comparación; mes sin datos → «sin datos de …»).
  - Informes mensuales: `['mes','mes_ant','trim','anio']`. El informe del mes M se envía en M+1: «Este mes» enseña el informe de septiembre (el del ciclo), «Mes anterior» el de agosto; trimestre o año juntan los meses medidos (tarjetas sumadas, tabla con el mes en cada fila). Ventana sin meses medidos → una línea que lo explica.
- Informes mensuales: enlaces de celda (ClickUp, Desk, hoja, histórico) → botones `bt mini` (32 px; 44 en el móvil); el nombre del cliente ya no es enlace: la fila entera abre la ficha. Tablas paginadas a 25 (10 en el móvil). Lista propia que parte líneas (la `.lista-i` común corta con «…»). Formulario «Enviado por otra vía» con `chipsFiltro` + `campoTexto` (fuera el `<select>`). Reglas plegadas al pie («Cómo se cuenta»). Móvil: página de 28.815 px → 9.124 px; objetivos < 24 px: 168 → 0.
- Reuniones: aviso del límite en una línea (el detalle, plegado al pie); cabecera limpia (sin selector ni contadores sueltos); «Resumen de Zoom» → resumen plegable con `summary` de 32 px; enlaces Grabación/Transcripción/Resumen/Fathom/CRM como `bt mini`; formulario de acta con `campoTexto`; barra de capacidad con `barraProgreso()`; vacíos de bloque con `vacioLinea()`; filas de la tabla de clientes abren la ficha.
**n6_revisar (7 personas × 1440/1024/390):** antes 18 de 30 pantallas con algo (informes: hasta 178 clics < 24 y 10 desbordes; reuniones: «Resumen de Zoom» 20 px); después 9 de 30, y todo lo que queda es de lo común: cabeceras ordenables de `tablaDensa` (16 px) a 1440/1024 y el `<thead>` oculto de la tabla apilable que «desborda» a 390.
**Queda / peticiones a E0:** cabeceras de `tablaDensa` a ≥ 24 px en ordenador; `.lista-i` con opción de varias líneas; `chipEstado` sin estado «azul» con icono propio (hoy uso punto). La barra de reparto por tipo y la de «Por account» son barras finas en línea (no `grafico()`): si E0 quiere, una `barraApilada()` común.
**Nota que me pongo (contra la auditoría 30):** Informes mensuales 7,0 → 9,0; Reuniones 6,5 → 9,0. No llego a 10 por lo común pendiente (cabeceras de tabla) y porque la tabla de informes sigue siendo larga en el móvil (10 filas apiladas de 6 datos).

## R12 · Quién lleva qué (2-oct noche)
- Ver la tabla R12 en `_ESTADO_E0.md` (carril «asignaciones y verdad única»). En este módulo: Emex ≠ Romero Martínez **arreglado** (un apellido corriente suelto no empareja).

## R12 · arreglos tras la auditoría final (carril E, 2-oct noche)
- **A2 «Este mes» no cambia nada → arreglado (y apuntado para E0).** Las cifras sí cambian con el periodo (probado mes, mes anterior, trimestre y año por enlace), pero el selector común solo enseña «Este mes», que ya está elegido; el resto va en «Más». El subtítulo lo dice ahora («el mes anterior, en «Más», arriba»). Propuesta para E0 en dudas_pintura.md: si un módulo tiene pocos periodos, enseñarlos todos a la vista.
