# Inventario de la app de RO (generado)

Lo genera `python3 migracion/inventario.py`. No edites a mano: vuelve a generarlo.

| Qué | Cuántos |
|---|---|
| Pantallas en el menú (`modulos/indice.js`) | 42 (42 hechas) |
| Ficheros en `modulos/` | 196 (44 pantallas, 137 piezas comunes) |
| Líneas de front (módulos + carcasa + estilos) | 48567 |
| Rutas de API en `servir.py` | 37 (22 GET, 15 POST) |
| Ficheros que enchufan rutas a servir.py | 49 (125 rutas más; 5 con bucle propio) |
| Rutas distintas que llama el front (`ctx.api`) | 86 |
| Tablas | 66 |
| Puestos | 21 |
| Tipos de dato con regla | 41 |
| Ficheros de datos con permiso (`datos_de_modulo`) | 100 |
| Almacenes privados | 9 |
| Tipos de acción permitidos | 140 |
| Componentes exportados (`componentes.js`) | 107 |
| Campos de `ctx` | 43 |
| Pasos de la tubería | 52 |
| Generadores `fuentes_*/` | 176 |
| Baterías de prueba | 66 |

## Pantallas

| Ruta | Título | Grupo | Fichero | Estado |
|---|---|---|---|---|
| `#/operaciones` | Dirección de operaciones | Operaciones | `./operaciones.js` | hecho |
| `#/prioridades-cliente` | Prioridades por cliente | Hoy | `./prioridades_cliente.js` | hecho |
| `#/uso-app` | Uso y mejoras | Equipo | `./uso_app.js` | hecho |
| `#/mi-dia` | Mi día | Hoy | `./mi_dia.js` | hecho |
| `#/mi-trabajo` | Mi trabajo | Hoy | `./mi_trabajo.js` | hecho |
| `#/en-rojo` | En rojo | Hoy | `./en_rojo.js` | hecho |
| `#/bandeja` | Bandeja | Hoy | `./bandeja.js` | hecho |
| `#/agenda` | Agenda | Hoy | `./agenda.js` | hecho |
| `#/chat-equipo` | Chat del equipo | Hoy | `./chat_equipo.js` | hecho |
| `#/asistente-ia` | Asistente IA | Hoy | `./asistente_ia.js` | hecho |
| `#/alertas` | Alertas del departamento | Hoy | `./alertas.js` | hecho |
| `#/producto` | Dirección de producto | Clientes | `./producto.js` | hecho |
| `#/ficha` | Ficha del cliente | Clientes | `./ficha.js` | hecho |
| `#/informe-cliente` | Informe del cliente | Clientes | `./informe.js` | hecho |
| `#/paneles` | Paneles de herramientas | Clientes | `./paneles.js` | hecho |
| `#/clientes-nuevos` | Clientes nuevos | Clientes | `./nuevos.js` | hecho |
| `#/informes-mensuales` | Informes mensuales | Clientes | `./informes_mensuales.js` | hecho |
| `#/incidencias` | Incidencias | Clientes | `./incidencias.js` | hecho |
| `#/captacion` | Captación | Captación y CRM | `./captacion.js` | hecho |
| `#/salud-crm` | Salud del CRM | Captación y CRM | `./crm.js` | hecho |
| `#/seo-web` | SEO, ficha y webs | SEO, web y redes | `./seo.js` | hecho |
| `#/redes` | Redes | SEO, web y redes | `./redes.js` | hecho |
| `#/produccion` | Producción | Equipo | `./produccion.js` | hecho |
| `#/horas` | Horas y productividad | Equipo | `./horas.js` | hecho |
| `#/reuniones` | Reuniones | Equipo | `./reuniones.js` | hecho |
| `#/personas` | Personas | Equipo | `./personas.js` | hecho |
| `#/setters` | Mi día del setter | Ventas de RO | `./setters.js` | hecho |
| `#/ventas-ro` | Ventas de RO | Ventas de RO | `./ventas_ro.js` | hecho |
| `#/prospeccion` | Prospección y outreach | Ventas de RO | `./outreach.js` | hecho |
| `#/dinero-cliente` | Dinero por cliente | Dinero | `./dinero_cliente.js` | hecho |
| `#/finanzas` | Finanzas de la empresa | Dinero | `./finanzas.js` | hecho |
| `#/panel-direccion` | Panel de dirección | Dinero | `./panel_direccion.js` | hecho |
| `#/decisiones` | Decisiones y rastro | Sistema | `./decisiones.js` | hecho |
| `#/ajustes` | Ajustes | Sistema | `./ajustes.js` | hecho |
| `#/indicadores` | Catálogo de indicadores | Sistema | `./indicadores.js` | hecho |
| `#/componentes` | Componentes | Sistema | `./catalogo.js` | hecho |
| `#/primera-semana` | Tu primera semana | Bienvenida | `./primera_semana.js` | hecho |
| `#/mi-perfil` | Mi perfil | Perfil | `./mi_perfil.js` | hecho |
| `#/conexiones` | Salud del sistema | Sistema | `./ajustes_conexiones.js` | hecho |
| `#/envios` | Envíos | Sistema | `./envios.js` | hecho |
| `#/avisos-automaticos` | Avisos automáticos | Sistema | `./ajustes_avisos.js` | hecho |
| `#/gasto-ia` | Gasto de IA | Sistema | `./gasto_ia.js` | hecho |

## Rutas de API

| Método | Ruta | Línea en servir.py |
|---|---|---|
| GET | `/api/elegir` | 2552 |
| GET | `/api/` | 2556 |
| GET | `/vivo` | 2557 |
| GET | `/api/en-rojo/planes` | 2681 |
| GET | `/api/sesion` | 2685 |
| GET | `/api/indicadores` | 2744 |
| GET | `/api/ajustes` | 2765 |
| GET | `/api/rastro` | 2787 |
| GET | `/api/acciones` | 2820 |
| GET | `/api/recarga` | 2871 |
| GET | `/api/avisos` | 2880 |
| GET | `/api/decisiones` | 2888 |
| GET | `/api/buscar/indice` | 2902 |
| GET | `/api/buscar` | 2902 |
| GET | `/api/contadores` | 2921 |
| GET | `/api/perfil` | 2935 |
| GET | `/api/preferencias` | 2941 |
| GET | `/api/opiniones` | 2947 |
| GET | `/api/opiniones/captura` | 2947 |
| GET | `/api/respuestas_mili` | 2974 |
| GET | `/api/rastro/verificar` | 3044 |
| GET | `/api/salud` | 3059 |
| POST | `/api/ver_dato` | 3243 |
| POST | `/api/en-rojo/planes` | 3246 |
| POST | `/api/rastro` | 3250 |
| POST | `/api/acciones` | 3281 |
| POST | `/api/decisiones` | 3390 |
| POST | `/api/recarga` | 3393 |
| POST | `/api/perfil/zona` | 3416 |
| POST | `/api/preferencias` | 3421 |
| POST | `/api/opinion` | 3441 |
| POST | `/api/opiniones/estado` | 3472 |
| POST | `/api/avisos/visto` | 3485 |
| POST | `/api/ajustes/` | 3493 |
| POST | `/api/ajustes/persona` | 3562 |
| POST | `/api/ajustes/asignacion` | 3621 |
| POST | `/api/ajustes/confirmar` | 3638 |

## Rutas enchufadas desde otros ficheros

| Fichero | Rutas | ¿Bucle propio? |
|---|---|---|
| `actas.py` | `/api/ficha/acta` | no |
| `agenda_zoom_api.py` | `/api/agenda/zoom` | no |
| `agrupaciones_tarea_api_376.py` | `/api/horas/agrupaciones-tarea` | no |
| `altas_personas.py` | `/api/altas`, `/api/altas/`, `/api/altas/alta`, `/api/altas/baja`, `/api/altas/cambio`, `/api/altas/comprobar`, `/api/altas/departamento`, `/api/altas/guia`, `/api/altas/repartir`, `/api/altas/tarea_hecha` | no |
| `avisos.py` | `/api/canales`, `/api/canales/`, `/api/canales/adjuntables`, `/api/canales/buscar`, `/api/canales/campana`, `/api/canales/campana_vista`, `/api/canales/canal`, `/api/canales/clickup`, `/api/canales/escalado`, `/api/canales/escalar`, `/api/canales/estado`, `/api/canales/grupo`, `/api/canales/leido`, `/api/canales/llamadas`, `/api/canales/llamar`, `/api/canales/mensaje`, `/api/canales/miembro`, `/api/canales/preferencias`, `/api/canales/videollamada` | sí |
| `avisos_programados.py` | `/api/avisos_programados`, `/api/avisos_programados/`, `/api/avisos_programados/cambiar`, `/api/avisos_programados/ejecutar`, `/api/avisos_programados/hecho`, `/api/avisos_programados/vista_previa` | sí |
| `borradores_api.py` | `/api/cerebro/borrador` | no |
| `cerebro_api.py` | `/api/cerebro/operativo` | no |
| `cerebro_seo_api.py` | `/api/cerebro/seo` | no |
| `contratos_privados.py` |  | no |
| `crm_embudo_api_467.py` |  | no |
| `crm_ultima_valida_api_513.py` | `/api/crm/ultima-valida` | no |
| `decisiones_durables_382.py` | `/api/operaciones/decisiones-locales` | no |
| `despliegue/vigia.py` | `/api/vigia`, `/api/vigia/probar` | sí |
| `ejemplos_creador_api_438.py` | `/api/produccion/ejemplos-creador` | no |
| `envios.py` | `/api/acciones`, `/api/envios`, `/api/envios/`, `/api/envios/envio`, `/api/envios/reintentar` | sí |
| `evidencias_kpi_api.py` | `/api/clientes/evidencias_kpi` | no |
| `fuentes_alertas/guardia_alertas.py` | `/api/acciones` | no |
| `fuentes_gbp/servidor_gbp.py` | `/api/gbp/borrador`, `/api/gbp/cola`, `/api/gbp/estado`, `/api/gbp/responder` | no |
| `fuentes_modular/acceso.py` | `/api/modular/acceso` | no |
| `fuentes_pagespeed/lectura_api.py` | `/api/pagespeed/cache` | no |
| `fuentes_reuniones/propuesta_reunion.py` | `/api/reuniones/propuesta`, `/api/reuniones/propuesta/calidad` | no |
| `historial_diario_api_362.py` | `/api/horas/historial-diario` | no |
| `historial_reuniones_api.py` | `/api/historial/reuniones` | no |
| `historico_llamadas_350.py` | `/api/operaciones/llamadas/historico` | no |
| `ia.py` | `/api/ia/`, `/api/ia/borrador`, `/api/ia/cerebro`, `/api/ia/consejo`, `/api/ia/consejo/informe`, `/api/ia/consejo/valorar`, `/api/ia/copiloto`, `/api/ia/estado`, `/api/ia/gasto`, `/api/ia/gasto/`, `/api/ia/lista` | no |
| `ia_gasto.py` | `/api/ia/gasto/reabrir`, `/api/ia/gasto/topes` | no |
| `informe_word_api.py` | `/api/informes/word` | no |
| `informes_tareas_api.py` | `/api/informes/tareas_ejecutadas` | no |
| `meta_diaria_api_385.py` |  | no |
| `metodo_cuentas.py` | `/api/metodo/sugerencias` | no |
| `mi_trabajo.py` | `/api/acciones`, `/api/mi_trabajo`, `/api/mi_trabajo/contexto_ia`, `/api/mi_trabajo/crono`, `/api/mi_trabajo/metadatos` | no |
| `operaciones_anomalias_276.py` | `/api/operaciones/anomalias` | no |
| `operaciones_feedback_273.py` | `/api/operaciones/feedback` | no |
| `operaciones_notas_equipo_281.py` | `/api/operaciones/notas-equipo` | no |
| `operaciones_pedidos_account.py` | `/api/operaciones/pedidos-account` | no |
| `operaciones_prioridades_300.py` | `/api/operaciones/prioridades` | no |
| `operaciones_registros_269.py` | `/api/operaciones/registros` | no |
| `operaciones_registros_272.py` | `/api/operaciones/control` | no |
| `piloto_lectura.py` | `/api/bandeja/triaje-intenciones`, `/api/cerebro/borrador`, `/api/cerebro/operativo`, `/api/cerebro/seo`, `/api/cliente/`, `/api/en-rojo/planes`, `/api/historial/reuniones`, `/api/metodo/sugerencias`, `/api/mi_trabajo`, `/api/modulo/`, `/api/produccion/urgencias-observadas`, `/api/recarga`, `/api/sesion`, `/api/uso/aviso` | no |
| `planning_observado_api_356.py` | `/api/produccion/planning-observado` | no |
| `planning_observado_api_405.py` |  | no |
| `setters_srv.py` | `/api/acciones`, `/api/setters/propuesta_cita` | no |
| `sincronia.py` | `/api/acciones`, `/api/sincronia`, `/api/sincronia/`, `/api/sincronia/a_mano`, `/api/sincronia/cambio`, `/api/sincronia/elegir`, `/api/sincronia/objeto`, `/api/sincronia/reintentar` | sí |
| `tareas_local.py` | `/api/tareas/cambio`, `/api/tareas/tablero`, `/api/tareas/vistas` | no |
| `transiciones_produccion_208.py` | `/api/produccion/transiciones` | no |
| `triaje_intenciones_437.py` | `/api/bandeja/triaje-intenciones` | no |
| `urgencias_observadas_api_402.py` | `/api/produccion/urgencias-observadas` | no |
| `uso_local.py` | `/api/uso`, `/api/uso/aviso` | no |

## Rutas que llama el front

`/api/:x`, `/api/acciones`, `/api/ajustes`, `/api/ajustes/persona`, `/api/altas`, `/api/altas/alta`, `/api/altas/baja`, `/api/altas/cambio`, `/api/altas/comprobar`, `/api/altas/guia`, `/api/altas/repartir`, `/api/altas/tarea_hecha`, `/api/avisos`, `/api/avisos/visto`, `/api/avisos_programados`, `/api/avisos_programados/cambiar`, `/api/avisos_programados/ejecutar`, `/api/avisos_programados/hecho`, `/api/avisos_programados/vista_previa`, `/api/bandeja/triaje-intenciones`, `/api/canales`, `/api/canales/campana`, `/api/canales/canal`, `/api/canales/mensaje`, `/api/cerebro/borrador`, `/api/cerebro/seo`, `/api/cliente/:x`, `/api/clientes/evidencias_kpi`, `/api/clientes/evidencias_kpi/informes`, `/api/clientes/evidencias_kpi/resumen`, `/api/crm/embudo-observado`, `/api/decisiones`, `/api/en-rojo/planes`, `/api/envios`, `/api/envios/reintentar`, `/api/ficha/acta`, `/api/gbp/borrador`, `/api/gbp/responder`, `/api/historial/reuniones`, `/api/horas/agrupaciones-tarea`, `/api/horas/historial-diario`, `/api/ia/borrador`, `/api/ia/cerebro`, `/api/ia/copiloto`, `/api/ia/estado`, `/api/ia/gasto`, `/api/ia/gasto/reabrir`, `/api/ia/gasto/topes`, `/api/ia/lista`, `/api/informes/tareas_ejecutadas`, `/api/metodo/sugerencias`, `/api/mi_trabajo`, `/api/mi_trabajo/crono`, `/api/mi_trabajo/metadatos`, `/api/modular/acceso`, `/api/modulo/prioridades/p_:x`, `/api/operaciones/anomalias`, `/api/operaciones/control`, `/api/operaciones/decisiones-locales`, `/api/operaciones/feedback`, `/api/operaciones/llamadas/historico`, `/api/operaciones/notas-equipo`, `/api/operaciones/pedidos-account/resumen`, `/api/operaciones/prioridades`, `/api/operaciones/registros`, `/api/opiniones`, `/api/opiniones/estado`, `/api/paid/mediciones-diarias`, `/api/perfil${pid `, `/api/perfil/zona`, `/api/produccion/ejemplos-creador`, `/api/produccion/planning-observado`, `/api/produccion/transiciones`, `/api/produccion/urgencias-observadas`, `/api/rastro`, `/api/recarga`, `/api/reuniones/propuesta`, `/api/reuniones/propuesta/calidad`, `/api/setters/propuesta_cita`, `/api/sincronia`, `/api/sincronia/:x`, `/api/tareas/tablero`, `/api/tareas/vistas`, `/api/uso`, `/api/vigia`, `/api/vigia/probar`

## Tablas

- `acciones` (schema_v2.sql)
- `actas_claves` (actas.py)
- `actas_lotes` (actas.py)
- `altas_recibos` (altas_personas.py)
- `altas_tareas` (altas_personas.py)
- `asignaciones` (schema_v2.sql)
- `avisos` (despliegue/estado.py, schema_v2.sql)
- `avisos_prog_cambios` (avisos_programados.py)
- `avisos_prog_hechos` (avisos_programados.py)
- `canal_campana` (avisos.py)
- `canal_grupos` (avisos.py)
- `canal_leidos` (avisos.py)
- `canal_mensajes` (avisos.py)
- `canal_miembros` (avisos.py)
- `canal_preferencias` (avisos.py)
- `canal_resumenes` (avisos.py)
- `datos_blob` (despliegue/publicacion.py)
- `datos_fichero` (despliegue/publicacion.py)
- `datos_version` (despliegue/publicacion.py)
- `decisiones` (schema_v2.sql)
- `decisiones_intenciones_382` (decisiones_durables_382.py)
- `docs` (schema_v2.sql)
- `ejecuciones` (despliegue/estado.py)
- `envio_pasos` (envios.py)
- `envios` (envios.py)
- `eventos` (evidencias_kpi.py)
- `fuente_lectura` (schema_v2.sql)
- `historial` (schema_v2.sql)
- `ia_gasto` (ia_gasto.py)
- `ia_lotes` (ia_gasto.py)
- `ia_reservas` (ia_gasto.py)
- `ia_topes` (ia_gasto.py)
- `incidencias` (schema_v2.sql)
- `intenciones_acciones` (intenciones_acciones.py)
- `leads_eventos` (leads_archivo.py)
- `leads_meta` (leads_archivo.py)
- `leads_recibos` (leads_archivo.py)
- `llaves` (despliegue/estado.py)
- `mt_crono` (mi_trabajo.py)
- `operaciones_anomalias_276` (operaciones_anomalias_276.py)
- `operaciones_control_272` (operaciones_registros_272.py)
- `operaciones_feedback_273` (operaciones_feedback_273.py)
- `operaciones_notas_equipo_281` (operaciones_notas_equipo_281.py)
- `operaciones_pedidos_account_294` (operaciones_pedidos_account.py)
- `operaciones_prioridades_300` (operaciones_prioridades_300.py)
- `operaciones_registros_269` (operaciones_registros_269.py)
- `opiniones` (servir.py)
- `pasos` (despliegue/estado.py)
- `persona_puestos` (schema_v2.sql)
- `personas` (schema_v2.sql)
- `planes_fuegos_255` (planes_fuegos_255.py)
- `preferencias` (servir.py)
- `rastro_cortes` (servir.py)
- `rastro_incidencias` (servir.py)
- `recargas` (schema_v2.sql)
- `registro` (schema_v2.sql)
- `registro_huellas` (servir.py)
- `registros` (evidencias_kpi.py)
- `revocaciones` (evidencias_kpi.py)
- `sellos` (despliegue/estado.py)
- `sinc_cambios` (sincronia.py)
- `sinc_pasos` (sincronia.py)
- `tareas_vistas_privadas` (vistas_tareas.py)
- `uso_eventos` (uso_local.py)
- `uso_sesiones` (uso_local.py)
- `uso_ventanas` (uso_local.py)

## Campos de ctx

`accion`, `alCambiarPeriodo`, `ambito`, `api`, `avisosCelebraciones`, `carteraIds`, `carteraPorSilla`, `celebraciones`, `clientes`, `clientesVisibles`, `cuotaEmpresa`, `datos`, `datosModulo`, `definiciones`, `diaDatos`, `fechas`, `fechasDe`, `hoy`, `indicador`, `indicadores`, `navegar`, `nivel`, `nombre`, `params`, `periodo`, `periodosConDatos`, `persona`, `pilotoLectura`, `plural`, `puestos`, `rastro`, `real`, `servidor`, `soloLectura`, `soloSuCartera`, `titulo`, `veModulo`, `ver`, `verDato`, `verdad`, `verdadComun`, `vigente`, `zona`

## Dependencias fuera del repositorio (`~/RO_HERRAMIENTAS`)

- `captacion/captacion.py`
- `clickup_api`
- `clickup_api/chat.py`
- `clickup_api/cu.py`
- `externos.py`
- `ghl_agencia`
- `ghl_agencia/app.py`
- `google`
- `google/gbp.py`
- `holded`
- `holded/hd.py`
- `hostinger`
- `hostinger/hg.py`
- `hostinger/pegar.sh`
- `hostinger/pegar.sh.`
- `meta`
- `metricool/mc.py`
- `modular`
- `modular/pegar.sh`
- `modular/pegar.sh.`
- `seranking/pegar.sh.`
- `snov`
- `snov/sv.py`
- `zadarma/zd.py`
- `zoho`
- `zoho/zbookings.py`
- `zoho/zh.py`
- `zoom/zm.py`
