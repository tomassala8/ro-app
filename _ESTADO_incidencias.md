# _ESTADO · M14 Incidencias y control de Operaciones (2-oct-2026)

## Hecho
- `modulos/incidencias.js` (ruta `#/incidencias` y `#/incidencias/<id>`), alta en `modulos/indice.js` (con `proyectos: 'todo'` para Coti) y en `reglas_permisos.json → datos_de_modulo` con `solo_todo_sin_cliente` (lo de sistema solo llega a Tomás, Mili y Coti).
- `fuentes_incidencias/generar_incidencias.py` → `data/incidencias/incidencias.json` (pasa el escáner de secretos antes de escribir). `rastro_operaciones.json`: historia previa transcrita de `rastro_mili.md` (48 eventos con enlace al mensaje de ClickUp, 11 traspasos). `primera_vez.json`: recuerda el primer día de cada detección para el corte de 48 h.
- `fuentes_incidencias/probar_incidencias.py [puerto] [--ciclo]`: 7 personas × 1440/390 px, todas las pestañas, fichas, recorte y ciclo completo.
- **Ficha de incidencia**: cabecera con etapas (Detectada → Avisada → Reiterada → Escalada → Resuelta → Comprobada), «La respuesta en 10 segundos» (qué se incumple, quién, por qué, qué hizo Operaciones, resuelto o escalar), botones La he visto · Avisar/Reiterar (a quién, por dónde, mensaje listo, prueba) · Escalar a Coti 24 h · Escalar a Tomás 48 h (problema + recomendación + causa) · Decidir · Resuelta (prueba obligatoria) · Reabrir · Confirmar/cambiar causa (solo Tomás cambia una confirmada) · No aplica (motivo obligatorio, también en el rastro). El responsable tiene «Ya lo he hecho».
- **Vuelve arriba**: avisada hace > 48 h sin cambio → «Toca escalarlo»; sin aviso en 48 h → «Sin avisar»; escalado vencido → «Escalado sin respuesta». **Resuelto comprobado**: si la detección sigue en el dato de un día posterior, «Reabierta: el dato dice que sigue».
- **Detecciones**: Desk (correo de cliente > 48 h con agente: 39 clientes; sin agente > 4 h: 19; agentes desactivados con tickets: Carugatti y Cagnoli; 3 departamentos ilegibles), Zadarma (34 entrantes sin destino, 6 a extensiones inexistentes 01/03, extensiones 107 y 111 desconectadas y sin uso, 3 perdidas sin devolver), alarmas de cliente > 48 h con historia (12 clientes).
- Pestañas: Quién falla en qué (mapa de calor que filtra alarmas al pulsar + mapa de control por persona), Incongruencias (104 del panel v27 + cruce en vivo account ≠ agente de Desk; decidir/no aplica) y Accesos de quien ya no está (cuenta compartida «Acceso Equipo RO» activa en Desk, extensión 110 «Gestiona-Lourdes», Nadia en la lista de horas del panel), Traspasos (11, con revisión a 14 días y estado en app/Desk/CRM; registrar traspaso), Quién vio primero (Mili 12 de 15, Tomás 3: AyG, Avantik, ECIJA; 5 en rojo sin aviso de nadie), El mes (por qué/dónde, tiempo de resolución, informe de Operaciones generado y copiable, revisión mensual de la centralita, extensiones).

## Cifras contrastadas a mano
1. Carugatti: 60 tickets sin cerrar en Desk (consulta directa por agente: 58 «Abierto» + 1 «Por resolver» + 1 «En seguimiento»); la app dice 60 y 15 de ellos de clientes esperando respuesta.
2. Zadarma: 34 entrantes no contestadas sin extensión desde el 1-sep (recontado sobre `zadarma_crudo.json`); 107, 111 y 110 `is_online=false` en una segunda consulta en vivo.
3. Quién vio primero: AyG (Tomás 25-sep 13:41, Mili 19:44), Avantik (Tomás 1-oct 08:57, Mili 11:35) y ECIJA (Tomás 22-sep, Mili sin aviso) cuadran con el apartado 3 de `rastro_mili.md`.

## Pruebas
- Consola sin errores del módulo con tomas, mili, lucia, valeria, yessica, constanza y setter_ana a 1440 y 390 px; sin desplazamiento horizontal en ninguna pestaña. Los únicos errores vistos son `ERR_CONNECTION_RESET` de servir.py al cargar otros módulos a la vez (ver dudas).
- Recorte (respuesta del servidor): Lucía 13 incidencias (sus clientes, 0 de sistema), 7 incongruencias, su fila del mapa; Valeria y Jessi 71 de cliente y 0 de sistema; setter_ana 0 (estado vacío). Lucía abriendo una incidencia de un cliente ajeno: «no está en tu lista».
- Ciclo completo en local.db (como Mili, sobre «Extensiones sin registrar», textos «[prueba del ciclo]»): visto → avisar → reiterar → causa → escalar → resolver; `DELETE` rechazado («Las acciones no se borran»). **Ojo:** esa incidencia queda «resuelta · se comprueba mañana» y mañana saldrá reabierta (las extensiones siguen igual), como debe.

## Falta / dudas
- Sesión de revisión con Coti, Mili y Agus (R15).
- Detección de «departamento equivocado»: imposible hasta que la llave lea los 30 departamentos de Desk.
- Las incidencias se recalculan al lanzar el generador (no hay recarga automática todavía).
- Dudas para E0 y Tomás en `../dudas_pintura.md` (D-P · M14).

## Capturas
`capturas/incidencias/`: `<persona>_<ancho>.png`, pestañas de Tomás, Mili y Lucía, `mili_*_ficha_cliente|sistema`, `lucia_1440_ficha_ajena`, `mili_1440_mapa_filtrado`, `mili_1440_ciclo_*`, `tomas_1440_para_tomas`.

## Ronda 2-oct noche (19:00)
- Panel «Alertas de web y SEO» (N4) en la pestaña Incidencias (y en el vacío de quien no tiene incidencias): lo de su departamento, lo grave y vencido arriba, 10 visibles, «Lo tengo · Resuelta · No aplica» a la cola de Alertas. Tabla a 15 filas. Hoja de estilos reducida a maquetación (guía 30). Ver `_ESTADO_mi_dia.md`, misma ronda.

## N6 · Diseño 10/10 (2-oct, noche) · nota que me pongo: **8 / 10** (auditoría 30: 5,5)
- Sin hoja propia (fuera `inc-estilos`): formularios con `.campo`, mapas de calor y de control con casillas en línea (tokens) dentro de `.tabla-scroll` (en el móvil se desplazan dentro de su caja, la página no), «La respuesta en 10 segundos» en dos columnas que valen para todos los anchos, espaciados en línea pasados a la escala de 4.
- Orden: «Lo primero hoy» arriba y las cifras debajo; «Alertas de web y SEO» enseña 5 (antes 10) y «y N más». Rojo con cuentagotas en la tabla: si más del 30 % de filas son rojas, el rojo queda para el tercio más grave y el resto va en ámbar (el texto del estado no cambia). Etiquetas de tarjeta cortas («Gestión de Operaciones», «Escaladas vencidas»). Fuentes con nombre llano (no «zadarma_ext»).
- Pruebas: `pruebas_diseno.py` limpio; 7 personas × 3 anchos sin errores, sin scroll horizontal, sin texto < 12 px. Capturas en `capturas/_n6/incidencias/`.
- Por qué no 10: falta agrupar la tabla por estado con cabeceras plegables (hoy chips de estado + 15 filas); el filtro «Responsable» es un `<select>` nativo de `tablaDensa` (común).

## A1 (2-oct noche) · sin duplicados
«Lo primero hoy» ya no repite lo que sale en «Para Tomás»; «Alertas de web y SEO» quita las que apuntan a una incidencia ya arriba; el consejo de la IA oculta las filas que repiten una incidencia de esas dos listas. #/personas/<id> abre la ficha de esa persona (resaltada con `_ir.js › llevarA`).

## V2 · carril V2-A (3-oct)
| Hallazgo | Estado |
|---|---|
| Barrido v1 · `generar_incidencias.py:280` y `:293` meten «RO-####» y «478 h» en el texto | **Arreglado** en el generador (sin el número de ticket, que va en `tickets` y en la prueba; antigüedad en días; plurales sin «(s)»). Sale en la próxima vuelta de la tubería |
| 40_A B5 · antigüedad en horas grandes | **Arreglado** en pantalla (`enDias()`, la antigüedad común de `fechas`) mientras llega el dato nuevo |
| «Para Tomás» con tickets en texto plano | **Arreglado** (`conTickets`: enlace a ese correo en la Bandeja) |
| Mapa de control: Contesta 13 en Incidencias frente a 12 en la Bandeja de Lucía | **Arreglado.** «Contesta» con `controlPersona()` de `mi_dia_bloques.js` (la regla de la pantalla Bandeja, descontando lo ya despachado en su cola): 12 en Incidencias, en el día de Mili y en «Tu cumplimiento». «Revisa» = `revisionesDelAccount` (42 de 67), como Producción |
| 40_A B6 · «Lo mismo en 4 personas más» en el consejo | **No es de este carril**: texto de `ia.py`/`motor_consejos.py` (V2-B) |
