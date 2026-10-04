> Recogido en: `migracion/PENDIENTES_LOGICA.md` (L-01, L-15, L-18…L-49) y `SUPERPROMPT_ASTRA_2026-10-04.md`. Es la revisión de código que los originó (anexo C).
> **Copia saneada para Cursor (4-oct-2026).** Fuente: `/mnt/project-files/feedback_herramienta/anexos/`. Personas por su puesto; el cliente real citado en un comentario, como «cliente A».

# Informe C · Código y coherencia de la app de RO

Revisión del 4-oct-2026 sobre la copia de `ro-app` (rama `main`, commit `4f46378`), sin datos reales.
Todo lo de abajo se ha comprobado leyendo el código o ejecutándolo. Los números de línea son de esa copia.

Gravedad: **P0** rompe o expone · **P1** fallo funcional · **P2** coherencia o usabilidad · **P3** pulido o deuda.

---

## 0. Lo que se ha ejecutado

| Prueba | Resultado |
|---|---|
| `node --check` sobre los 66 `.js` (raíz y `modulos/`) | 0 errores de sintaxis |
| Import en seco con Node de los 61 módulos más `componentes.js`, `ayudas.js`, `carcasa.js`, `datos.js` y `permisos.js` (DOM simulado) | Los 66 enlazan y se evalúan. No falta ningún fichero importado ni ningún nombre exportado |
| Cruce de cada `fichero:` de `modulos/indice.js` con el disco | Todos existen. Los 41 están en `estado: 'hecho'`. No queda ningún «previsto» |
| `python3 -m py_compile` sobre todos los `.py` del repo | 0 errores |
| `ruff --select F821,F823,…` sobre todos los `.py` | **1 fallo real: `servir.py:687` F823** (ver P0-1) |
| `python3 pruebas_diseno.py --estricto` | Sale con 0. Los 61 módulos están limpios. `index.html` tiene 4 colores sueltos (meta `theme-color` y el SVG de la marca) y `estilos.css` tiene 1 radio con número |
| `python3 telefono.py --probar` | 23 de 23 bien |
| `python3 escaner_secretos.py --proyecto` | **Falla** por un falso positivo: toma `-iTCP@127.0.0.1` de `pruebas_seguridad.py:48` por un correo (P3-9) |
| `avisos_programados.py --simular` | No se puede correr sin `data/personas.json` (esperado) |

---

## P0 · Rompe o expone

### P0-1 · Contestar un «Para confirmar» en Ajustes rompe la recarga y luego impide arrancar el servidor
- **Dónde:** `servir.py:687` y `servir.py:692`, método `Estado.aplicar_ajustes`.
- **Qué pasa:** en la línea 687 se llama a `hoy()` (la función del módulo), pero en la 692 la misma función asigna `hoy = P.hoy_iso()`. Python trata entonces `hoy` como variable local en toda la función, y la línea 687 lanza `UnboundLocalError`. Ruff lo marca (F823) y lo he reproducido con un caso mínimo. La línea 687 solo corre cuando hay `respuestas` en la tabla `decisiones` de tipo `para_confirmar`.
  1. Operaciones contesta una duda en Ajustes › Para confirmar. `POST /api/ajustes/confirmar` (2940-2958) guarda la respuesta en `local.db` y llama a `E.recargar_personas()`. Esa llamada revienta y operaciones ve un 500. La respuesta queda guardada, pero la memoria no se actualiza.
  2. En el siguiente arranque, `main()` llama a `E.cargar()` sin `try` (línea 3121 aprox.). `cargar` entra en `aplicar_ajustes`, que lanza el mismo error, y **el servidor no arranca**. Una «Actualizar ahora» acaba igual: `E.cargar()` en `trabajador_recargas`.
- **Arreglo:** renombrar la variable local (`dia_hoy = P.hoy_iso()`) o calcular `dia_hoy = hoy()` una sola vez al principio y usarla en las dos líneas. Añadir a `pruebas_seguridad.py` un caso que conteste un «Para confirmar» y vuelva a cargar.

---

## P1 · Fallos funcionales

### P1-1 · Las horas sin zona de Madrid se leen con la zona del navegador: plazos, antigüedades y «vencida» se desfasan para quien no está en España
- **Qué pasa:** el contrato dice que las fechas sin zona de los datos («2026-10-02 23:14») ya están en hora de Madrid. Pero `componentes.js` no ofrece ninguna función que pase ese texto a un instante. Solo da `fechas.dia()`, `diasDesde()` y `antiguedad(horas)`. Cada módulo lo resuelve con `new Date(s.replace(' ', 'T'))`, que lo interpreta en la zona del navegador. Para un account en Buenos Aires, todo plazo vence 5 h tarde y toda antigüedad sale 5 h más corta. Para dirección en Bali sale 5-6 h más larga, o negativa y recortada a 0.
- **Dónde (decisiones, no solo textos):**
  - `alertas.js:68` (`aFecha`), `116-139` (`venceDe` y `nivelEscalado`: vencida y escalado frente a `S.ahora = new Date()`), `183-189` (`fechaVuelta`: «posponer a mañana a las 9» se calcula a las 9 locales y se guarda como si fuera la hora de Madrid).
  - `mi_dia_bloques.js:38-39` (`fecha`, `edadH`), `1674` (`reuPasada`), `2097-2151` (`alertasMias`, `apartadasLoMio` y `unirLoMio` con `ahora = new Date()`). Esto decide «Lo mío».
  - `mi_dia.js:747` (`vuelta`: «Pedido» vuelve mañana a las 9 locales).
  - `bandeja.js:77-80` (`edadH`: horas sin contestar, la regla de 48 h).
  - `incidencias.js:93-99` y `169-177` (`fechaLocal`; relojes de 48 h y 24 h, «sin_avisar» > 48 h), `991` y `1031` (`diaISO(new Date())`: «Toca revisarlo»), `1089-1090` (inicio de mes local).
  - `produccion_comun.js:150-159` (`vence()`: «Vencida hace N días» y «Vence hoy» con `new Date()` local). Lo usa `produccion.js:274` y `:498`.
  - `agenda.js:100`, `156`, `160`, `181`, `188-189` y `471-472` (`isoDia(new Date())` y la línea de «ahora» con `getHours()` local, sobre citas en hora de Madrid).
  - `_ventas_comun.js:33` y `50`, `captacion.js:238`, `dinero_comun.js:88`, `nuevos.js:57`, `outreach.js:175`, `setters.js:291` (horas que le quedan a la 2.ª llamada), `produccion_comun.js:181`, `decisiones.js:172`.
- **Arreglo:** añadir a `fechasDe()` un `instante(t)` que lea el texto sin zona como Europe/Madrid, más `horasDesde(t)` y `horasHasta(t)` sobre él. Después, cambiar los `edadH`, `aFecha`, `fechaLocal` y `fecha` locales de esos módulos por esas funciones. Para «posponer a mañana a las 9», construir `${fechas.manana()} 09:00` (texto de Madrid). Añadir una prueba con `TZ=America/Argentina/Buenos_Aires` en `barrido_total.py`.

### P1-2 · «Hoy», el mes y el trimestre calculados con `new Date()` (zona del Mac o UTC) en vez de `ctx.hoy` o `ctx.fechas`
La regla «Fechas: una sola vara» la incumplen los siguientes:

| Fichero:línea | Qué decide |
|---|---|
| `reuniones.js:138`, `155`, `287` | `new Date().toISOString().slice(0, 7)` = mes **en UTC**: el día 1 de 00:00 a 02:00 en Madrid, el «mes en curso» es el anterior |
| `reuniones.js:66` | año local |
| `personas.js:120` (`en14`, en UTC), `122` (`mesNota`, en UTC), `124` (trimestre local), `163` (`getDate() > 5` local: «Nota del mes en rojo») | plazos de 1:1, nota y ausencias |
| `ventas_ro.js:73-76` | mes natural local; si falta, cae en `v.meses['2026-10']` fijo |
| `ficha.js:928` | ritmo de la meta de leads = `getDate() / 30` local (y siempre 30 días) |
| `ficha_equipo.js:200` | «mes anterior» local |
| `mi_dia_bloques.js:234`, `1707`, `1719`, `1998` | nombre del mes y días del mes locales |
| `chat_equipo.js:78` (`diaTxt` «Hoy/Ayer») y `92` | local |
| `ia_componentes.js:390` | «de las HH:MM» frente a hoy local |
| `finanzas.js:34` | fecha propuesta del plan = hoy + 7 en UTC |
| `objetivos_comun.js:38` | lunes de hoy a partir de la hora UTC |
| `en_rojo.js:264`, `ficha.js:161` | días desde el alta con `Date.now()` |

En total: **17 de los 41 módulos de `indice.js` no usan ni `ctx.hoy` ni `ctx.fechas`** (agenda, alertas, bandeja, chat_equipo, decisiones, en_rojo, seo, crm, horas, dinero_cliente, envios, ajustes_avisos, ajustes_conexiones, gasto_ia, asistente_ia, indicadores y catalogo). En varios de ellos no hace falta. Agenda, alertas, bandeja, decisiones y chat sí deciden con la fecha.

- **Arreglo:** cambiar por `ctx.hoy.slice(0, 7)`, `ctx.fechas.relativo()`, `ctx.fechas.diasDesde()` y `sumarDias(ctx.hoy, n)`. Añadir a `pruebas_coherencia.py` una regla que busque `new Date().toISOString().slice(0, 7|10)` y `getDate()/getMonth()` en `modulos/`.

### P1-3 · Meses fijos en el código: desde el 1-nov las pantallas dirán «septiembre» con datos de octubre
- **Qué pasa:** muchas etiquetas y cálculos llevan «septiembre», «sep», «oct» o `'2026-09'` y `'2026-10'` escritos a mano, aunque el dato que pintan es «el mes anterior» o «este mes».
- **Dónde (agrupado):**
  - «septiembre» en textos de pantalla: `captacion.js` (26 veces; p. ej. `638` «Inversión gestionada · septiembre», `960`, `976`, `994`, `1137`, `1144`, `1186`), `ficha.js` (18; p. ej. `807` «Citas · septiembre», `820` «Horas · septiembre», `1088` «Reuniones · septiembre»), `dinero_cliente.js` (17; `103`, `160`, `262`, `318`: «horas de septiembre × 31,47 €»), `informe.js` (13), `ventas_ro.js` (7), `finanzas.js` (7) y `mi_dia_bloques.js` (5).
  - Meses fijos en la lógica: `informe.js:727`, `1113` y `1117` (la paridad con Looker compara siempre con `'2026-09'`), `ventas_ro.js:76` y `82` (`v.meses['2026-10']`, `v.meses['2026-09']`), `dinero_cliente.js:143-144` y `372`, `finanzas.js:471`, `483`, `528` y `870` (el desplegable «Coste del equipo» solo ofrece `['2026-09', '2026-10']`), `panel_direccion.js:1085`, `1097` y `1143`.
  - Panel de dirección › La captación: `panel_direccion.js:791-793` y `fuentes_panel_direccion/generar_panel_direccion.py:101` (`PERIODOS = ("sep", "oct", "todo", "d14", "d7")`, etiquetas «Sept.», «Oct.», «Desde 14-sep»). En noviembre seguirá ofreciendo sep y oct.
  - `informe.js:975-978`: fechas por cliente escritas a mano («Último dato en su Looker: 3-sep») con su color calculado sobre esas fechas.
  - Python: `fuentes/comun.py:139` `fecha(texto, anio=2026)` y `fuentes_informes/generar_informes.py:58` `mes_de_texto(texto, anio=2026)`. En enero de 2027, «02-01 07:00» se leerá como 2-ene-2026: la fuente saldrá con un año de retraso y se marcará como vieja.
- **Arreglo:** el generador ya deja `mes_anterior` y `mes`. Escribir la etiqueta con `nombreMes(D._meta.mes_anterior)` (o `mesMas(ctx.hoy.slice(0, 7), -1)`). Los periodos del panel, generados a partir de hoy (`mes`, `mes_ant`). El desplegable de coste, con los 2 últimos meses de `mesMas`. El año por defecto en Python, el del reloj de Madrid (o deducirlo del más cercano a hoy).

### P1-4 · El hilo de recargas puede morir en silencio y dejar «Actualizar ahora» colgado para siempre
- **Dónde:** `servir.py:1793-1829` (`trabajador_recargas`).
- **Qué pasa:** solo `subprocess.run` está dentro de un `try`. `json.loads(RECARGA_CFG.read_text())` (1807), los `conectar()` y `UPDATE` (1799-1823, p. ej. con «database is locked»), `registrar()` y `calcular_avisos()` no lo están. Una excepción mata el hilo (es `daemon`, nadie lo vuelve a lanzar). La fila se queda en `en_curso` y ninguna recarga posterior se atiende, sin aviso. Los bucles de `avisos.py:821` y `avisos_programados.py:787`, en cambio, sí envuelven cada vuelta.
- **Arreglo:** envolver el cuerpo de cada vuelta en `try/except` con `traceback`, marcar la fila como `con_fallos` en el `except`, y al arrancar pasar a `con_fallos` las filas que sigan `en_curso`.

---

## P2 · Coherencia y usabilidad

### P2-1 · Dos cifras distintas de «clientes bien» en el mismo Mi día
- **Dónde:** `mi_dia_bloques.js:856` (`clientes_tarjetas`: «N con salud ≥ 60», contando también a los críticos) frente a `mi_dia_bloques.js:1878` (`cartera_salud`: «salud ≥ 60 y ningún crítico»). El comentario de la 1876 lo explica con un ejemplo: un cliente (cliente A) está en crítico con salud 62. Con ese caso, un bloque dice «11 con salud ≥ 60» y el otro «10 de 12».
- **Arreglo:** una función común `estaBien(v)` (en `componentes.js` o junto a `verdad`) que use la misma regla en los dos sitios.

### P2-2 · Umbrales repetidos a mano que pueden divergir
- Salud verde ≥ 60 y ámbar ≥ 40: `componentes.js:379`, `ficha.js:456`, `en_rojo.js:353`, `mi_dia_bloques.js:856` y `1878`.
- Tarifa de 31,47 €/h: 10 veces en `dinero_cliente.js` (`62`, `102`, `103`, `160`, `258`, `262`, `318`, `322`, `330` con `ref: 31.47`, `333`), más `indice.js:123`. No hay constante.
- 128 h al mes: `personas.js:368`, `371`, `378` (×2) y `510`, `reuniones.js:199`, `207`, `470` y `493`, `horas.js:291`, `ajustes.js:222`, `mi_dia_bloques.js:763` e `indice.js:107`.
- Topes de cartera 12/16: `personas.js:26` (`CAP`) y `mi_dia_bloques.js:743` (`TOPE_SILLA`) son copias.
- **Arreglo:** un `modulos/_reglas.js` (o el `definiciones()` de la verdad única) con `TARIFA_HORA`, `HORAS_MES`, `TOPE_SILLA` y `SALUD_UMBRAL`. Que `pruebas_coherencia.py` falle si vuelve a aparecer un literal.

### P2-3 · «Sin imputar» definido de tres formas
- `verdad/equipo.json → no_imputan_ayer`: 0 h el último día laborable. Lo usan `personas.js:112-113` (tile) y `mi_dia_bloques.js:601`.
- `personas.js:290`: el filtro «cero» de la tabla usa `!p.horas.ayer` (dato de `personas_m20`), no la verdad. El tile y la lista filtrada pueden dar números distintos.
- `horas.js:299`: «laborables con menos de 15 minutos».
- `mi_dia_bloques.js:1584`: «Ayer no imputaste» con `p.ayer` de `horas.json`. Además escribe «día(s)», que va contra la regla de plural.
- **Arreglo:** en Personas, filtrar con `ceroIds` cuando haya `VE`. En Mi día, usar `no_imputan_ayer` y llamarlo «el {ultimoLaborable}». Unificar el umbral de 15 min en la verdad.

### P2-4 · Account del cliente: la ficha cae en el de la Cartera cuando la verdad no tiene
- **Dónde:** `ficha.js:287` y `ficha.js:745` (`accVerdad ? … : c.responsable || 'sin account'`), `incidencias.js:641` (`i.c.responsable`) y `mi_dia_bloques.js:515` (`?? x.account_id`).
- **Qué pasa:** el LEEME («Una sola verdad») dice: «Si no hay, `null`: nunca el de la Cartera ni el del CRM».
- **Arreglo:** si `verdad.account` es `null`, pintar `verdad.sin_account` («sin account · para confirmar»).

### P2-5 · Alertas no tiene «Deshacer», aunque el LEEME dice que sí
- **Dónde:** el LEEME (Ronda U, `_deshacer.js`) dice «Adoptado en … Alertas». `alertas.js` no importa `_deshacer.js`. `marcar()` (193-203) y `lote()` (210-224) escriben al momento con `ctx.accion` y solo dan un `avisoFlotante`. Un «Resuelta» o «No aplica» en lote de hasta `MAX_LOTE` alertas no se puede deshacer.
- **Arreglo:** pasar `marcar` y `lote` a `conDeshacer({ optimista, hacer, revertir })`, como «Lo mío» en `mi_dia.js`.

### P2-6 · La IA gasta en cuanto hay una clave en el entorno: no tiene interruptor de dos llaves como envíos y ClickUp
- **Dónde:** `ia.py:65-76` (`clave()`: `ANTHROPIC_API_KEY` del entorno, o el llavero) e `ia_gasto.py:63` (`"activa": True` por defecto).
- **Qué pasa:** envíos exige fichero firmado + `RO_ENVIOS_REALES=si` (`envios.py:201-205`). ClickUp exige fichero + `RO_CLICKUP_REAL=si` + llave de servicio (`sincronia.py:237-243`). Ficha de Google exige fichero + `RO_GBP_REAL`. La IA arranca en real con solo tener `ANTHROPIC_API_KEY` en el entorno del servidor o de la tubería (`fuentes_ia/lote_nocturno.py`). Esa variable es habitual en el shell de quien desarrolla con Claude. Los topes de 150 €/mes y 10 €/día limitan el daño, pero el «hoy gasto 0 €» del LEEME depende de que nadie exporte esa variable.
- **Arreglo:** exigir además `RO_IA_REAL=si` o `data/ia/interruptor.json` con `activado_por: "<id de dirección>"`, y leer solo `RO_ANTHROPIC_API_KEY`, no la genérica.

### P2-7 · «Reabrir» en Gasto de IA no maneja errores
- **Dónde:** `gasto_ia.js:183`. El `click: async () => { await ctx.api('ia/gasto/reabrir', …); pintar(); }` no tiene `try/catch`. Si falla (403 en «ver como», o la red), la promesa queda sin capturar y no hay ningún aviso. Es el único botón de escritura sin `catch` que he encontrado en un barrido automático de los `click: async`. El módulo tampoco mira `ctx.soloLectura` (el servidor sí lo frena).
- **Arreglo:** `try { … } catch (e) { avisoFlotante(e.message) }` y `aria-disabled` con `ctx.soloLectura`.

### P2-8 · Lecturas que se saltan `ctx`
- `ficha.js:183-184`: en modo sin servidor, `fetch('data/clientes/<id>.json')`. Está documentado como respaldo, y el servidor no sirve `data/clientes/`.
- `ficha.js:207-209`: `cargarPrivado` reimplementa `ctx.verDato` con un `fetch('api/ver_dato')` propio que copia las cabeceras `X-RO-App`, `X-RO-Yo` y `X-RO-Como`. Si cambia el contrato de identidad, esta copia se queda atrás.
- `panel_direccion.js:937`: `fetch('reglas_permisos.json')` desde el módulo, solo para saber si existe el almacén de sueldos.
- `dinero_comun.js:108`: rama `fetch('data/…')` cuando no hay `ctx.datosModulo` (código muerto hoy).
- **Arreglo:** usar `ctx.verDato()` (que el comentario dice que ya lleva la cabecera) y `ctx.ver({ tipo: 'sueldo_coste' })` o una ruta de la API. Borrar la rama muerta.

### P2-9 · `servir.ahora()` sin zona, pero etiquetada como Madrid
- **Dónde:** `servir.py:238-239` (`datetime.now().isoformat()`). Se usa en el ancla del rastro con `"zona": "Europe/Madrid"` (533), en la `hora` de `/api/sesion` (2203), de decisiones (2339), de acciones (2546 y 2790) y en «Para confirmar» (2953).
- **Qué pasa:** el Dockerfile pone `TZ=Europe/Madrid`, así que en Docker sale bien. Pero el propio comentario de `hoy()` (241-244) dice «Render, que va en UTC», y `render.yaml` depende de definir `TZ`. Además `ia.py` tiene 13 `datetime.now()` sin zona (p. ej. `298`, `338` y `410`: el «hoy» que se manda a la IA). Hay 105 apariciones de `datetime.now()` o `date.today()` sin zona en 56 ficheros de `fuentes_*` y `despliegue/`, todas sanas solo mientras `TZ` sea Madrid.
- **Arreglo:** `ahora()` → `datetime.now(MADRID)`. En `ia.py`, usar `P.hoy_iso()`. Que `entrada.sh` falle si `TZ` no es Europe/Madrid.

### P2-10 · Rutas del Mac de dirección en código que la tubería ejecuta
- **Resumen:** `config.py` centraliza las rutas (`RO_HOME`, `RO_CRUDOS`, `RO_HERRAMIENTAS`), pero **25 ficheros Python se lo saltan** con `Path.home()` o `os.path.expanduser('~/…')`. «Downloads» aparece 89 veces en 26 ficheros y «RO_HERRAMIENTAS» 85 veces en 41. Muchas de esas apariciones son comentarios o textos de pantalla.
- **14 pasos de `despliegue/pasos.json` corren scripts con ruta fija:** agenda, chat_equipo, dinero, ficha, gbp, hostinger, informe, lector_hoja_informes, mi_dia, modular, panel_direccion, paneles, sueldos y verificar_envios (este último respeta `RO_HERRAMIENTAS`).
- Ejemplos: `fuentes_informe/generar_informe.py:34` y `38`, `fuentes_panel_direccion/generar_panel_direccion.py:45`, `fuentes_dinero/generar_dinero.py:32-33`, `fuentes_dinero/generar_cuadre.py:33-34`, `fuentes_sueldos/generar_sueldos.py:24`, `fuentes_equipo/generar_equipo.py:32-35`, `fuentes_mi_dia/generar_mi_dia.py:32`, `fuentes_ficha/agenda_md.py:11`, `fuentes_chat_equipo/generar_chat_equipo.py:156` y `fuentes_produccion/generar_marca.py:31`. `build_data.py` lee `~/Downloads/PANEL_OPERACIONES_2026-10-01/…`.
- Llavero del Mac (`security find-generic-password`): 13 llamadas en 10 ficheros (`fuentes_chat_equipo`, `fuentes_dinero`, `sincronia.py`, `ia.py`, `ia_gasto.py`, `despliegue/vigia.py`…). `_ESTADO_C5.md` ya lo apunta como pendiente.
- `fuentes_consejos/conocimiento/reglas_minadas.json` lleva 103 rutas `/Users/<usuario>/…`.
- **Arreglo:** cambiar cada `Path.home()` por `config.CRUDOS`, `config.HERRAMIENTAS` y `config.secreto()`, y añadir a `pruebas_noche.py` un `grep` que falle con `Path.home()` o `~/` fuera de `config.py`.

### P2-11 · Logs con la lista de clientes subidos al repositorio «sin datos»
- **Dónde:** `fuentes_paneles/_log_{desk,ga,ghl,gsc2,gsc_idx,mc,meta,meta_kiosko,psi,zd}.txt` están en `git ls-files`. Contienen los ids de los 68 clientes y qué herramientas tiene cada uno.
- **Arreglo:** `git rm --cached fuentes_paneles/_log_*.txt` y añadir `_log_*.txt` al `.gitignore`.

### P2-12 · Elementos pulsables que no son `<button>` ni `<a>`
- `horas.js:208-213`: `<li tabindex=0>` con `click` y `Enter`, sin `role="button"` y sin Espacio.
- `chat_equipo.js:851-855`: `filaPulsable`, un `div` con `role=button` y `Enter`, sin Espacio.
- `reuniones.js:273`: un `span` con `click` (solo para `stopPropagation`, aceptable).
- **Arreglo:** usar un `<button class="fila-boton">` dentro del `li`, o la fila pulsable común de `tablaDensa`.

### P2-13 · El LEEME y los `_ESTADO` no cuadran con el código
- LEEME, «Módulos previstos»: dice **M16 Ventas de RO** y **M17 Prospección** «previsto», pero `indice.js:113` y `116` los tienen en `hecho` con fichero (`ventas_ro.js` y `outreach.js`). La frase «Los previstos ya salen en el menú… con la etiqueta previsto» ya no se cumple con nadie.
- LEEME (N1) y `componentes.js:1389` citan `modulos/paneles_periodo.js`, que **no existe** (la regla vive en `componentes.js` y `fuentes_paneles/periodos.py`).
- `_ESTADO_panel_direccion.md`, «Pendiente»: pide `solo_real` para el panel, pero ya está en `reglas_permisos.json` (todas las claves `panel_direccion/*`).
- `_ESTADO_alertas.md`: pide añadir `generar_alertas.py` a `recarga.json`, pero ya está en `despliegue/pasos.json` (1339-1347).
- LEEME (Ronda U): dice que Alertas adopta `_deshacer.js`, y no lo hace (P2-5).
- **Arreglo:** una pasada de cierre sobre esas líneas.

### P2-14 · «Días sin reunión» en la ficha frente a «Sin reunión el mes pasado» en el resto
- `ficha.js:814` pinta `dias_sin_reunion` con un semáforo de 30/35 días. En Rojo, Mi día y Reuniones usan `verdad.sin_reunion_mes_pasado` (ningún contacto en el mes natural anterior). Ejemplo: el 4-oct, un cliente cuya última reunión fue el 30-ago lleva 35 días: en la ficha sale ámbar, y en En rojo «sin reunión el mes pasado». Otro con reunión el 2-oct y ninguna en septiembre sale verde (2 días) en la ficha y «sin reunión» en En rojo.
- **Arreglo:** en la ficha, enseñar las dos cosas con el mismo color que la verdad.

---

## P3 · Pulido y deuda

1. **Ficheros enormes:** `mi_dia_bloques.js` 203 KB, `componentes.js` 191 KB, `servir.py` 189 KB, `ficha.js` 140 KB, `captacion.js` 130 KB, `informe.js` 113 KB, `incidencias.js` 109 KB, `bandeja.js` 106 KB, `finanzas.js` 104 KB, `nuevos.js` 103 KB, `panel_direccion.js` 101 KB, `estilos.css` 105 KB. Documentación: `LEEME.md` 129 KB y `_ESTADO_E0.md` 88 KB. `servir.py` engancha `avisos`, `envios`, `sincronia` e `ia` reescribiendo `Manejador._api_get` y `api_post` en cadena (`avisos.py:1107-1121`, `avisos_programados.py:1017-1033`…): el orden de importación decide qué ruta gana. Propuesta: partir `componentes.js` por familias (fechas, tablas, paneles v4, capas) y `servir.py` en un enrutador con tabla de rutas.
2. **Código muerto:** `modulos/rastro.js` (nadie lo importa; `decisiones.js` reimplementa su pestaña) y `modulos/panel_direccion_estilo.js` (vacío, «YA NO SE USA»).
3. **Acciones locales que nunca se leen en modo estático:** `_ventas_comun.js:91` guarda en `localStorage` sin el campo `modulo`, y `:84` filtra por `a.modulo === modulo`. Además `:80` lee todo `ctx.api('rastro')` en vez de `ctx.api('acciones?modulo=<id>')`, como pide el LEEME.
4. **`ficha.js:928`:** el ritmo de la meta divide entre 30 en todos los meses.
5. **`en_rojo.js:371`:** suma los días de encendido con `toISOString()` (UTC) a partir de un mediodía local. Funciona salvo en zonas muy alejadas.
6. **Plurales a mano:** `mi_dia_bloques.js:1584` («día(s)»), `produccion_comun.js:155` (`día${…}` en vez de `fmt.plural`).
7. **`gasto_ia.js:93` y `105`:** medidas en línea (`width: '112px'`, `padding: '4px 8px'`, `maxWidth: '480px'`). `pruebas_diseno.py` no mira `width` ni `maxWidth`, por eso sale limpio.
8. **`fuentes_agenda/generar_agenda.py:191`:** argumento mutable por defecto (ruff B006).
9. **`escaner_secretos.py --proyecto` falla** por el falso positivo `-iTCP@127.0.0.1` (`pruebas_seguridad.py:48`). La «puerta de secretos» que el LEEME manda correr la primera sale en rojo sin motivo. Arreglo: excluir `@127.0.0.1` del patrón de correo o añadirlo a `escaner_permitidos.json`.
10. **`index.html`:** 4 colores sueltos (`theme-color` y el SVG de la marca). Aceptable, pero `pruebas_diseno` no los cuenta en el estricto.
11. **`sw.js`:** caché `ro-pagina-v1` fija. Si la página cambia de forma incompatible, no hay forma de invalidarla salvo subir el nombre a mano.

---

## Lo que está bien (para no tocarlo)
- No hay `alert()`, `confirm()` ni `prompt()` en ningún fichero de la app.
- Todos los `ctx.accion` y `ctx.api` POST pasan por el servidor, que rechaza «ver como» (`servir.py:2510-2515`). Las 33 pantallas que escriben miran `soloLectura` al menos en parte, y el servidor cubre el resto.
- Los errores de `render()` los recoge `app.js:628-632` (nunca pantalla en blanco). Las cargas de datos de los módulos llevan su `catch`.
- Los interruptores de envíos, ClickUp, Ficha de Google y Modular piden dos o tres llaves y están apagados en el repo (`data/envios/interruptor.json`).
- La guía visual está limpia en los 61 módulos.
- Los bucles de `avisos.py` y `avisos_programados.py` sobreviven a las excepciones, y `zona_de()` aguanta zonas IANA no válidas.
