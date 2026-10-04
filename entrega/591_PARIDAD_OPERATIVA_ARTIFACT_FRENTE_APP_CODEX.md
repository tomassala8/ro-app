# 591 — Paridad operativa del artifact frente a la app actual

4 de octubre de 2026. Auditoría de código y documentación, sólo lectura. No valores de datasets reales, navegador, HTTP, bases, proveedores, regeneración ni cambios de producto. Prioridad: Operaciones y cartera propia de Accounts; no duplica la auditoría Paid.

## Requisitos y método de comparación

Referencia exacta: `/Users/tomassala/Downloads/PANEL_OPERACIONES_2026-10-01/plantilla.html` y `build/build.py`. SHA256 de plantilla: `468e796d0dab7e8b366ba37c97d0a1e1c7b93b9e82e79ea967ccd6aefa2e01a5`. Base de requisitos: funciones y cabeceras originales, inventario301, trazabilidad136 y cortes377/399/507/552. Las deudas históricas se contrastan otra vez con los archivos actuales; no se suman como pendientes funciones ya integradas después.

El requisito de interfaz es conservar los apartados, tablas, columnas, controles y acceso al detalle. El requisito de medición es conservar **unidad, período, actor, cliente, definición y cobertura**. Mostrar una columna con `—` recupera su estructura, pero no recupera su medición. Recuperar todos los números antiguos por defecto tampoco demuestra paridad: el original usaba nombres/ceros y referencias sin la trazabilidad actual.

La plantilla exige: macro de cartera/fuegos; equipo cinco fechas, carga semanal/diaria y cierres; horas por persona y cliente con rangos; planificación siete columnas; producción doce columnas por account/nueve por proyecto; nuevos90 días/hitos; cierre mensual siete columnas; score ocho KPIs/nota/pesos; contacto y reuniones por cliente; decisiones/tendencias/rastro y controles humanos. Las bandas6/8h,60/90%,12proyectos,50/130%,80/60 y los pesos originales son requisitos de referencia visual, **no capacidad/contratos ratificados**. La regla vigente15d del trafficker en cohortes confirmadas no se sustituye por reunión mensual del account.

Comprobación independiente: **34 funciones mapeadas**, **17 rutas originales conservadas en orden**, más `rojos` como separación deliberada: **18 rutas actuales**. Tres pruebas de inventario301 ejecutadas PASS (funciones, cabeceras compuestas y umbrales); comprobación adicional del orden excluyendo sólo `rojos`, PASS. No se ejecuta la antigua aserción de exactamente17 rutas, incompatible con la ampliación deliberada. Esto verifica inventario, no todas las interacciones.

## Matriz completa de funciones

E = estructura/control equivalente localizado; P = medición o semántica sólo parcial; A = adaptación deliberada de privacidad/declaración local. Archivos relativos a `30_APP_PROTOTIPO/modulos/`.

| Original | Ruta / implementación actual | Estado y límite vigente |
|---|---|---|
|vDia576|dia ·265/274/300|E/P: prioridades6+14+resto accesibles, seis indicadores/tres números; varias mediciones siguen referencias.|
|vFuegos627|rojos ·268/255; fuegos ·406|E/P/A: mapa de clientes rojos y planes separado de urgencias; copia de alertas no urgencia actual confirmada.|
|vCierre651|cierre ·253/361/553/556|E/P: siete columnas, subtotales y mínimos conservados; pauta/horas sólo mismo mes, semáforo actual distinto de fotoSep.|
|vRastro662|rastro ·265/379/392/403|E/P: resumen cliente y detalle día; técnico/declarado separados, no historial total ni ejecución.|
|vScore682|accounts ·263/408|E/P: nota+ocho columnas+pesos/bandas; n/N es cobertura, falta cumplimiento/nota calculable.|
|vEquipo695|equipo ·operaciones/262|E: composición de seis bloques y subvistas adicionales; cada bloque mantiene su puerta.|
|vEquipoNotas696|equipo/notas ·281/383|E/P/A: siete columnas, nota humana durable y gráfica; sin evaluación laboral automática.|
|vBandeja719|bandeja ·270/340|E/P: filtros/agrupación, pedidos y pérdidas; copia antigua/pedido no respuesta o devolución realizada.|
|vHoras756|equipo/horas ·262/364/381/555|E/P: cinco presets+rango libre, seis/cuatro columnas, orden de ratios compatibles; referencia no jornada.|
|vEncargos789|dia/tomas ·272|E/A: registro/versiones/prueba locales, no aceptación externa por guardar.|
|vEquipoDia804|equipo/equipo-dia ·262/539|E/P: once columnas/cinco fechas; Cerradas ayer y ¿Trabajo? no medidos.|
|vProduccion837|produccion ·produccion/baseline256/409/405|E/P: account/proyecto/inventario; ausencia, transición y edad no siempre acreditadas.|
|vTomas866|tomas ·265/387/492/500|E/P: decisiones inline/relojes/planes; siete tendencias dependen de pares compatibles.|
|vLeadsFb886|bandeja ·273|E/A: feedback durable; declaración conseguida no cualificación/resultado externo.|
|vTriaje899|bandeja ·270→bandeja/432/440/445|E/A con desvío: shell abre reparto; control durable está en Bandeja, no inline en tabla270.|
|vResumen914|dia ·274/517/530/535|E/P: once indicadores, macro primero, seis+cinco y badges; no anillo que certifique cumplimiento.|
|vAccMini951|dia ·274/263|E/P: Account/Clientes/Nota/Carga; capacidad y nota no ratificadas.|
|vControl960|accounts/clientes ·250/263/390|E/P: diez señales y detalle; imputa observado, varias señales de actividad sin fuente compatible.|
|vPasos977|dia ·274/433|E/P: siete pasos/enlaces y badges; abrir no completar paso.|
|vAnomalias994|equipo/anomalias ·276/370|E/A: cinco columnas y validación durable; no modificación de entrada ClickUp.|
|vPlanificacion1010|equipo/planificacion ·262/320/405/438/491|E/P: siete columnas, comparación adicional y ejemplos por creator exacto; cuatro transiciones desconocidas.|
|vPuesto1021|puesto ·264/547|E/A: principios/ronda y registros; referencias8h separadas de obligación.|
|vAlertaPersonas1094|equipo/alerta-personas ·262/281|E/P/A: motivos y notas; no juicio laboral por datos parciales.|
|vTiposTarea1099|equipo/tipos-tarea ·376|E/P: cinco columnas,60fechas y mínimo de casos; agrupación orientativa, no taxonomía oficial.|
|vInformeYBajas1120|tomas ·265/498/272|E/P/A: informe editable/copiar, fotos y bajas; sin envío automático, datos comerciales según grant.|
|vHoy1131|hoy ·263/388/414/342|E/P: Top6 antes de colección completa, filtros/detalles; edad de copia no plazo actual.|
|vClientes1199|clientes ·263/348/353/404|E/P: nueve columnas, orden/filtros/dots y seguimiento separado; Sep no llamadas7d.|
|vFichas1226|fichas ·271/277/ficha|E/P/A: tarjetas/búsqueda/orden; cuotas/contratos protegidos y mediciones según fuente.|
|vAccounts1257|accounts ·263/315/344/404|E/P: macro→matrices→clientes→detalle; responsable actual separado de receptor histórico.|
|vNuevos1281|nuevos ·271/488/305/452/453|E/P:90d/hitos/fechas,15d aparte; alta/firma/encendido no intercambiables.|
|vViernes1298|viernes ·264/347/269|E/P/A: revisión/tickets/registro ritual; no foto exhaustiva viernes18h por defecto.|
|vInc1311|incongruencias ·278|E/P: incidencias/contrastes; resolución no automática ni identidad fuzzy.|
|vRepartir1320|repartir ·264/352|E/A: fuentes/enlaces/receptores; original no ejecutaba asignaciones externas, no exigirlas como omisión.|
|abrirFicha1332|ficha/:id ·ficha/129/151/548|E/P/A: ficha y fuentes/privados por puerta; no reproducir privilegios amplios del HTML.|

## Cuatro huecos de mayor impacto operativo

### 1. Planificación mide creación, todavía no entrada al planning ni ruptura

**Evidencia:** `_operaciones_equipo_262.js:195` construye literalmente `—` para Al planning, Fuegos directos, Rompen semanal y Semana pasada; sus títulos explican falta de estado inicial/transiciones. `_produccion_baseline.js:21` rechaza no_plan/sin_mes como mediciones acreditadas. Original `vPlanificacion:1010` exige esas cuatro cifras por **creador**, y `vProduccion:837` define no planificada como entrada directa a semanal/diario/en curso sin mensual.

Es hueco de medición funcional, **no de tabla**. 438 prueba creación por creator/taskID,405 estado observado; ninguna acredita toda la secuencia. Próximo incremento: ledger de transiciones tipadas con taskID/lista/actor/estado anterior+nuevo/instante/fuente y catálogo exacto, sin atribuir transición al asignado actual. Para intervalo anterior sin eventos, conservar desconocido. No promover cache de estado como historia.

**Prueba propuesta:** creada→mensual→semanal no rompe; creada→semanal no-fuego sí, sólo con evidencia de secuencia completa; tarea yaexistente/cambio externo/fuego acreditado/creator ambiguo/cliente revocado. Creadas semana pasada no rellena rupturas.

### 2. Equipo tiene horas, pero no cierres atribuibles ni suficiencia de trabajo/capacidad

**Evidencia:** `_operaciones_equipo_262.js:126–128` deja Cerradas ayer y ¿Trabajo? sin medición; Diario sin cumplir/Poca carga tampoco tienen valor. Su Horas calcula contra8h×laborables explícitamente como referencia, no contrato. La suma personal390 es observación7fechas, no porcentaje real de jornada. El original pide ambas columnas y porcentajes por día/rango.

Dos contratos de fuente faltan: quién realizó el cierre en qué instante; y disponibilidad/capacidad individual vigente/calendario/ausencias más estimaciones de carga. `date_done` con lista terminal da cierre de tarea, no actor que la cerró; persona asignada no sustituye autor. La UI ya deja visible el hueco: ocultarlo o colorear8h no lo resuelve.

**Próximo incremento:** DTO separado de cierres observados por **actor exacto** si hay evento; registro de disponibilidad aprobado por persona/período para un porcentaje diferente de la referencia. No extrapolar los cinco días ni inferir cero mensual. **Prueba:** cambio de asignación tras cierre, cierre de otro actor, timezone y medianoche, baja/duplicados, calendario parcial, ausencia aprobada, no datos→null y no verde.

### 3. Control Accounts aún no mide varias actividades exigidas por cliente/semana

**Evidencia:** `prepararAccounts263:143,169–171` deja llamadas salientes7d, contacto semanal verificado, abandono14d, planificación y reuniones tarde45d sin medición. Registros semanales151 y el histórico129/446/452 aparecen aparte: participación trafficker, celebración, responsable en fecha y cobertura intervalo se devuelven desconocidos. Método vigente distingue última confirmada/próxima revisión de registro histórico.

Es falta de **unión/evidencia temporal**, no falta de casillas ni incumplimiento probado. LlamadasSep≥30s no llamadas7d, cita/archivo no celebración, contacto declarado no correo saliente. No se puede restaurar la conclusión negativa original desde ausencia de filas de una copia parcial.

**Próximo incremento local útil:** confirmar únicamente evidencia que conserve clienteID, dirección/autor del contacto, timestamp y responsable histórico; proyectar positivos observados separados de cobertura. Para15d, añadir participante trafficker y celebración ratificada por evento o declaración explícita con procedencia; no reutilizar `registros_historicos_observados` como count de reuniones celebradas.

**Prueba:** reunión programada/cancelada no celebrada; account histórico≠actual; correo entrante≠saliente; llamada perdida≠saliente; cero declaraciones≠sin contacto; intervalo incompleto no dispara abandono; intersección real/vista y ACT antes/después IO.

### 4. Score y plazos no tienen aún denominadores que permitan el resultado original

**Evidencia:** `prepararAccounts263:129–166` trata ocho KPIs como registros/cobertura y mantiene Nota—. Los pesos15/20/10/20/10/10/5/10 y bandas80/60 están recuperados en408: no falta leyenda. Faltan hechos acreditados de envío de informe, reunión mensual, contacto semanal, respuesta/revisión48h, actualización de semáforo, horas compatibles y alta/hitos en plazo. `modelo265:185–192` tampoco puede derivar cumplimiento/nota/tendencia de referencias.

Original `build.py:604–627` calculaba porcentajes y nota renormalizando sólo partes disponibles; copiarlo daría una nota engañosa. Timeline271 ya conserva90d y hitos, pero firma/alta y estado registrado no garantizan encendido o entrega. **Próximo incremento:** empezar con un KPI positivo acotado — informe enviado con cliente, período, timestamp y prueba — y definir su universo elegible completo y tratamiento desconocido. Nota total sólo con contrato de denominadores confirmado; no promedio de n/N ni cambio cosmético a verde.

**Prueba:** informe preparado≠enviado, duplicados, cambio de owner, envío después de plazo, distinto mes/corte, cliente exento sin regla acreditada, desaparece una fuente y nota no aumenta por renormalizar. Cadencia15d no cuenta como cumplimiento mensual de Account.

## Diferencias menores y deudas que no deben reabrirse

La tabla Triaje270 tiene enlace a reparto, no los dos controles inline del original; Bandeja ofrece solicitar asignación/cierre local432 con lectura previa440 y guardia445. Un incremento de comodidad podría montar ese control autorizado en la fila270, manteniendo recibo local y sin marcar asignación externa. **El original899 no tenía selección/lote:**377 describía esa deuda incorrectamente; no implementar bulk como supuesta paridad.

Ya están recuperados: desplegable Rastro por día379; decisiones inline387; notas/gráfico383; tipos cinco columnas376; Top6 antes de alarmas414; compactación prioridades427; ejemplos exactos438; pesosScore408; seguimiento404/453; semáforos de referencia381/409; orden por ratio compatible555 y mínimos/compactación Cierre553/556. No repetir esos trabajos porque301/377 los mostraban futuros.

Las siete tendencias tienen comparación/mini-serie329/439, pero muchas fotos272 carecen de cohorte/unidad/definición acreditada. Otra foto con mismo corte no crea tendencia. Cierre de septiembre conserva referencias y mínimos: semáforo actual no sustituye semáforo históricoSep, reuniones observadas no asistencia completa, pauta económica no presupuesto contractual. Son lagunas de evidencia, no motivo para añadir tablas repetidas.

## Recomendación de secuencia y límites de aceptación

1. Recuperar eventos de planificación sólo desde una fuente con actor/estado/instante verificables; mantener estructura existente.
2. Añadir un KPI cliente positivo con evidencia (p.ej. envío de informe), cliente/período/owner diferenciados, sin calcular aún Score.
3. Resolver cierres por actor y disponibilidad individual antes de prometer porcentaje imputado contractual o carga suficiente.

La prioridad3 Accounts/contacto puede empezar con revisión local de evidencia ya existente, sin nueva captura externa. No se ha leído contenido de contratos/correos/llamadas ni contado clientes actuales para este informe; no se afirma que ese dato no exista en todo el ordenador. Se confirma que **los modelos autorizados examinados no lo convierten hoy en esas mediciones**.

La matriz cubre las34 entradas funcionales y las18 rutas actuales por fuente. No acredita geometría, callbacks de todas las vistas, permisos exhaustivos, servidor cargado, autenticación de producción ni100% del objetivo. El siguiente QA deberá probar el recorrido Ops y cartera propia/vercomo con fuentes sintéticas compatibles, después cada integración concreta. No hay cambios de producto ni ownership retenida.
