# _ESTADO · M9 «Redes» (2-oct-2026)

## Hecho
- `modulos/redes.js` (`#/redes` y `#/redes/<cliente>`): número que manda (% de clientes con los próximos 14 días cubiertos), huecos en 7 días, fallidas de 7 días, por aprobar, programadas, publicadas en fecha; «Lo primero hoy»; calendario de 14 días (una fila por cliente, un punto por día) con chips que se quedan; rendimiento de 30 días por red frente a la regla de RO; detalle día a día con huecos, fallidas con el motivo de la red, mejores y peores piezas, seguidores; botones Programar / Mover / Lo cubro / Avisar al account en simulación (doble confirmación: sale sola en la cuenta del cliente).
- Vistas: Constanza en resumen (cifras y calendario, sin detalle); persona de redes → sus clientes; account → los suyos; dirección y operaciones → todo.
- Datos: `fuentes_redes/generar_redes.py --en-vivo` (Metricool con `mc.py`: 25 marcas, `/v2/scheduler/posts` y `/v2/analytics/posts/<red>`) → `data/redes/redes.json` (filas con `cliente_id`). Alta en `reglas_permisos.json` (`redes/redes` → `redes`). Sin correos de quien crea la publicación ni gasto.
- 23 clientes (25 marcas menos Ranking Online y Tomás). Fuster, Centro Consulting y Consulting F se emparejan a mano en el script (E1 no los tenía).

## Hallazgos
- **0 de 23 clientes tienen los próximos 14 días cubiertos**; 23 con hueco ya en los próximos 7 días. 8 clientes no tienen nada programado del 2 al 15-oct (Innova Scala, Asetra, Aster, Bit24, Fitec, GAC, Musashi, Segú).
- Fallidas en los últimos 30 días: Instagram desconectado, «No Facebook page connected» y sesión de Facebook caducada (hay que reconectar).

## Cifras contrastadas
1. Adade Zaragoza, programadas 3-15 oct: 6 publicaciones (7, 9 y 14-oct, dos cada día) en el JSON y en el conector de Metricool (`getScheduledPosts`). Una del 14-oct pasó de borrador a programada después de la lectura.
2. GAC: el 21-sep publicada en Facebook, Instagram y LinkedIn (estado PUBLISHED en el programador), igual que el calendario.
3. Marcas: 25 en `/admin/simpleProfiles`, igual que la tabla de conexiones del 16 («Metricool: 25 marcas»).

## Falta / dudas
- **Aprobaciones**: la API no da pendiente / aprobado / rechazado; se cuentan los borradores con fecha. Recomendación: confirmar plan Advanced y usar su flujo de aprobación.
- **Plan por cliente** (C-G3-10) sin cargar: hueco = 4 días seguidos sin nada (plan por defecto de RO ≈ 3-4 piezas por semana). Cuando exista el plan, se cambia `HUECO_DIAS` por cliente.
- Racha de LinkedIn del titular, paquete del día 20 y comentarios < 24 h: «todavía no».
- Revisión con Coti, Mili y Agus (R15): pendiente.

## Pruebas
- Recorte: Tomás y Constanza 23, Lara 14, Lucía 8; Jerónimo, Carlos Viur, Valeria, Yessica y Ana (setter) 403.
- Sin errores de consola (portada y detalle) con tomas, mili, lucia, constanza, lara; valeria, yessica y setter_ana ven «no es de tu puesto».
- Capturas en `capturas/redes/`.

## Ronda 3 de arreglos (2-oct noche) · fallo de la auditoría → qué se ha hecho

| Fallo (auditoría) | Estado |
|---|---|
| Cifras E-11: emparejamiento de Metricool solo en `MANUAL` (Fuster, Consulting F, Centro Consulting) | **Arreglado.** Ya no existe `MANUAL`. Se empareja por el id de marca de E1 (y si no hay id, por el nombre de E1). Salen los mismos 23 clientes |
| Experiencia: error de Metricool en inglés | **Arreglado.** Los 6 errores conocidos se traducen («No hay página de Facebook conectada: el cliente tiene que reconectarla»…). «Publicado con avisos de etiquetas» ya no cuenta como fallida |
| Experiencia: «(SOP--09)» y «Lo cubro» | **Arreglado.** Ahora dice «Bien: todo publicado a su hora. Mal: menos del 95 %.» y «Me encargo» |
| Regla 1: verdad única (persona de redes y account) | **Adoptada.** Comprobación «redes y account de cada cliente» en ADOPTADOS, en verde |
| Regla 2: códigos y nombres | **Arreglado.** Fuera C-G3-10; nombres con `ctx.nombre()` |
| Regla 5: 7 días cerrados sin el día en curso | **Arreglado.** Las fallidas cuentan del día −7 al −1 |
| Escáner: teléfonos en `fuentes_redes/_cache/metricool.json` | **Arreglado.** Los teléfonos y correos del texto de las publicaciones se cambian por [teléfono] y [correo] al leer y al reescribir la caché. `escaner_secretos.py --proyecto`: limpio en mis ficheros |
| Atajos | Ya estaban: planificador de Metricool por marca y la publicación en su red |

**Para E0:** la copia antigua `despliegue/estado/instantaneas/vuelta_1/redes/fuentes_redes__cache/metricool.json` sigue con los 4 teléfonos. Es una instantánea vieja y no es mía; la siguiente vuelta ya copia la caché limpia.

Capturas: `capturas/redes/r3_*`.

## N6 · diseño 10/10 (2-oct, noche)
- **Fuera la hoja propia** (`red-estilos` con 10,5/12,5 px, radios de 4-6 px y espaciados 3/5/7/10/14). Solo tokens y componentes comunes.
- **Calendario de 14 días = tabla común**: cabecera en mayúsculas de 11 px y 700 («VI 2», «SÁ 3»…; hoy en azul), programadas como chip verde con el número, por aprobar en azul y los huecos como punto de 8 px (rojo en 7 días, ámbar en 8-14, gris «nada»). Leyenda en el pie del panel. En el móvil se desplaza dentro de la tabla.
- Tarjetas: 6 → 3 + 3, etiquetas de una línea, umbrales en la burbuja. «Lo primero hoy» con 7 y un pie «N clientes más con hueco». Rendimiento en tabla de 15 + «Ver más», sin apilar en el móvil. «Todavía no se mide», plegado al pie.
- Detalle: días como lista común (`lista-i`), miniatura de 40 px con `--r-s`, textos largos recortados; mejores/peores y fallidas en listas comunes; vacíos con `vacioLinea()`.
- **Periodo: no usa el común.** No hay serie diaria por cliente: el calendario mira 14 días adelante (fijo, de hoy a 13 días vista), las fallidas 7 días cerrados y lo publicado 30 días; se dice en cada etiqueta y en el subtítulo.
- Medidas (Tomás): 1440 → 3.604 a 3.306 px; móvil → 8.411 a 4.249 px. 0 errores, 0 scroll horizontal, 0 textos < 12 px con 7 personas × 3 anchos (portada y detalle). `pruebas_diseno.py`: limpio. Capturas en `capturas/_n6/redes/`.
- **Nota contra la auditoría 30: 6,0 → 8,5.** Lo que queda es de dato, no de pintura: hoy los 23 clientes tienen hueco en 7 días y el calendario sale casi entero con puntos rojos (es la verdad; el rojo se ha bajado a un punto de 8 px). `.dos` común sin apilar en el móvil: ver `dudas_pintura.md`.
- **N6 · segunda pasada:** en el calendario, el hueco va en rojo solo hoy y mañana (lo que hay que tapar ya); el resto de huecos, punto ámbar, y así lo dice la leyenda. «Lo primero hoy» en rojo solo si es fallida o el hueco empieza hoy o mañana, y como mucho el tercio de arriba. Cada fila con 1 acción + «⋯» (`details` + `.menu-flot`). Se repitieron las pantallas: 0 problemas. **Nota: 9,0.**

## R12 · Quién lleva qué (2-oct noche)
- Ver la tabla R12 en `_ESTADO_E0.md` (carril «asignaciones y verdad única»). En este módulo: C-A2 **arreglado en el dato** (`sin_metricool`, `por_persona`, `redes_apoyo`; la asignación manda); la pintura de `redes.js` va pedida en `dudas_pintura.md`.

## R12 · arreglos tras la auditoría final (carril E, 2-oct noche)
- **Botones < 32 px (nombres de cliente del calendario, 20 px) → arreglado:** 32 px de alto.
- **A2 periodo → no aplica, dicho:** línea llana bajo las cifras (14 días adelante y 30 atrás; Metricool no da serie diaria por cliente).
- Queda «Todavía no se mide · fase 2» (`pieFase2`, de componentes.js; apuntado para E0).
- **Cartera de la verdad (pedido del carril de asignaciones) → hecho:** el número que manda dice «de tus 10 clientes, 4 conectados en Metricool», la línea `por_persona` («Llevas 10… y ayudas en 15…») y un panel con los clientes sin marca en Metricool (`sin_metricool`; a Lara, los 6 suyos).

## V2 · carril V2-C2 (3-oct)
- **C-1 (ALTO) Lara 0 de 14 frente a 0 de 4 → arreglado.** Una base: la silla «redes» de asignaciones (los que lleva y en los que ayuda), la misma que Mi día. Redes dice «tu cartera de redes: 14 con calendario en Metricool (4 que llevas y 10 en que ayudas) · 11 sin marca, no cuentan» y añade el chip «Los que llevo». Prueba V2 en `pruebas_coherencia.py`.
- **C-6 «VI 2 · hoy» un sábado → arreglado.** El calendario empieza en el hoy real (`ctx.hoy`, respaldo `hoyMadrid`); si Metricool es de otro día, aviso «Datos de Metricool del vie 2…»; los días fuera de la lectura salen «sin dato todavía».
- Coti en «48 h sin cubrir»: se dice por qué («no hay jefa de redes»).
