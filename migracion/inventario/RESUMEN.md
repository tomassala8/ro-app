# Inventario de la app de RO (generado)

Lo genera `python3 migracion/inventario.py`. No edites a mano: vuelve a generarlo.

| Qué | Cuántos |
|---|---|
| Pantallas en el menú (`modulos/indice.js`) | 37 (37 hechas) |
| Ficheros en `modulos/` | 61 (38 pantallas, 11 piezas comunes) |
| Líneas de front (módulos + carcasa + estilos) | 36459 |
| Rutas de API en `servir.py` | 37 (23 GET, 14 POST) |
| Ficheros que enchufan rutas a servir.py | 11 (62 rutas más; 5 con bucle propio) |
| Rutas distintas que llama el front (`ctx.api`) | 54 |
| Tablas | 40 |
| Puestos | 21 |
| Tipos de dato con regla | 39 |
| Ficheros de datos con permiso (`datos_de_modulo`) | 92 |
| Almacenes privados | 9 |
| Tipos de acción permitidos | 133 |
| Componentes exportados (`componentes.js`) | 107 |
| Campos de `ctx` | 40 |
| Pasos de la tubería | 50 |
| Generadores `fuentes_*/` | 86 |
| Baterías de prueba | 16 |

## Pantallas

| Ruta | Título | Grupo | Fichero | Estado |
|---|---|---|---|---|
| `#/mi-dia` | Mi día | Hoy | `./mi_dia.js` | hecho |
| `#/en-rojo` | En rojo | Hoy | `./en_rojo.js` | hecho |
| `#/bandeja` | Bandeja | Hoy | `./bandeja.js` | hecho |
| `#/agenda` | Agenda | Hoy | `./agenda.js` | hecho |
| `#/chat-equipo` | Chat del equipo | Hoy | `./chat_equipo.js` | hecho |
| `#/asistente-ia` | Asistente IA | Hoy | `./asistente_ia.js` | hecho |
| `#/alertas` | Alertas del departamento | Hoy | `./alertas.js` | hecho |
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
| GET | `/api/elegir` | 2072 |
| GET | `/api/` | 2076 |
| GET | `/vivo` | 2077 |
| GET | `/api/modulo/` | 2185 |
| GET | `/api/cliente/` | 2185 |
| GET | `/api/buscar` | 2185 |
| GET | `/api/sesion` | 2196 |
| GET | `/api/indicadores` | 2237 |
| GET | `/api/ajustes` | 2258 |
| GET | `/api/rastro` | 2280 |
| GET | `/api/acciones` | 2291 |
| GET | `/api/recarga` | 2321 |
| GET | `/api/avisos` | 2330 |
| GET | `/api/decisiones` | 2338 |
| GET | `/api/buscar/indice` | 2342 |
| GET | `/api/contadores` | 2361 |
| GET | `/api/perfil` | 2375 |
| GET | `/api/preferencias` | 2381 |
| GET | `/api/opiniones` | 2387 |
| GET | `/api/opiniones/captura` | 2387 |
| GET | `/api/respuestas_mili` | 2407 |
| GET | `/api/rastro/verificar` | 2463 |
| GET | `/api/salud` | 2478 |
| POST | `/api/ver_dato` | 2514 |
| POST | `/api/rastro` | 2517 |
| POST | `/api/acciones` | 2548 |
| POST | `/api/decisiones` | 2710 |
| POST | `/api/recarga` | 2713 |
| POST | `/api/perfil/zona` | 2736 |
| POST | `/api/preferencias` | 2741 |
| POST | `/api/opinion` | 2761 |
| POST | `/api/opiniones/estado` | 2792 |
| POST | `/api/avisos/visto` | 2805 |
| POST | `/api/ajustes/` | 2813 |
| POST | `/api/ajustes/persona` | 2867 |
| POST | `/api/ajustes/asignacion` | 2920 |
| POST | `/api/ajustes/confirmar` | 2941 |

## Rutas enchufadas desde otros ficheros

| Fichero | Rutas | ¿Bucle propio? |
|---|---|---|
| `altas_personas.py` | `/api/altas`, `/api/altas/`, `/api/altas/alta`, `/api/altas/baja`, `/api/altas/cambio`, `/api/altas/comprobar`, `/api/altas/departamento`, `/api/altas/guia`, `/api/altas/repartir`, `/api/altas/tarea_hecha` | no |
| `avisos.py` | `/api/canales`, `/api/canales/`, `/api/canales/buscar`, `/api/canales/campana`, `/api/canales/campana_vista`, `/api/canales/canal`, `/api/canales/clickup`, `/api/canales/estado`, `/api/canales/grupo`, `/api/canales/leido`, `/api/canales/mensaje`, `/api/canales/miembro`, `/api/canales/preferencias` | sí |
| `avisos_programados.py` | `/api/avisos_programados`, `/api/avisos_programados/`, `/api/avisos_programados/cambiar`, `/api/avisos_programados/ejecutar`, `/api/avisos_programados/hecho`, `/api/avisos_programados/vista_previa` | sí |
| `despliegue/vigia.py` | `/api/vigia`, `/api/vigia/probar` | sí |
| `envios.py` | `/api/acciones`, `/api/envios`, `/api/envios/`, `/api/envios/envio`, `/api/envios/reintentar` | sí |
| `fuentes_alertas/guardia_alertas.py` | `/api/acciones` | no |
| `fuentes_gbp/servidor_gbp.py` | `/api/gbp/borrador`, `/api/gbp/cola`, `/api/gbp/estado`, `/api/gbp/responder` | no |
| `fuentes_modular/acceso.py` | `/api/modular/acceso` | no |
| `ia.py` | `/api/ia/`, `/api/ia/borrador`, `/api/ia/consejo`, `/api/ia/consejo/informe`, `/api/ia/consejo/valorar`, `/api/ia/copiloto`, `/api/ia/estado`, `/api/ia/gasto`, `/api/ia/gasto/`, `/api/ia/lista` | no |
| `ia_gasto.py` | `/api/ia/gasto/reabrir`, `/api/ia/gasto/topes` | no |
| `sincronia.py` | `/api/acciones`, `/api/sincronia`, `/api/sincronia/`, `/api/sincronia/a_mano`, `/api/sincronia/cambio`, `/api/sincronia/elegir`, `/api/sincronia/objeto`, `/api/sincronia/reintentar` | sí |

## Rutas que llama el front

`/api/acciones`, `/api/ajustes`, `/api/ajustes/persona`, `/api/altas`, `/api/altas/alta`, `/api/altas/baja`, `/api/altas/cambio`, `/api/altas/comprobar`, `/api/altas/guia`, `/api/altas/repartir`, `/api/altas/tarea_hecha`, `/api/avisos`, `/api/avisos/visto`, `/api/avisos_programados`, `/api/avisos_programados/cambiar`, `/api/avisos_programados/ejecutar`, `/api/avisos_programados/hecho`, `/api/avisos_programados/vista_previa`, `/api/canales`, `/api/canales/buscar`, `/api/canales/campana`, `/api/canales/canal`, `/api/canales/clickup`, `/api/canales/estado`, `/api/canales/grupo`, `/api/canales/leido`, `/api/canales/mensaje`, `/api/canales/miembro`, `/api/canales/preferencias`, `/api/cliente/:x`, `/api/decisiones`, `/api/envios`, `/api/envios/reintentar`, `/api/gbp/borrador`, `/api/gbp/responder`, `/api/ia/borrador`, `/api/ia/copiloto`, `/api/ia/estado`, `/api/ia/gasto`, `/api/ia/gasto/reabrir`, `/api/ia/gasto/topes`, `/api/ia/lista`, `/api/modular/acceso`, `/api/modulo/prioridades/p_:x`, `/api/opiniones`, `/api/opiniones/estado`, `/api/perfil${pid `, `/api/perfil/zona`, `/api/rastro`, `/api/recarga`, `/api/sincronia`, `/api/sincronia/:x`, `/api/vigia`, `/api/vigia/probar`

## Tablas

- `acciones` (schema_v2.sql)
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
- `docs` (schema_v2.sql)
- `ejecuciones` (despliegue/estado.py)
- `envio_pasos` (envios.py)
- `envios` (envios.py)
- `historial` (schema_v2.sql)
- `ia_gasto` (ia_gasto.py)
- `ia_lotes` (ia_gasto.py)
- `ia_topes` (ia_gasto.py)
- `incidencias` (schema_v2.sql)
- `llaves` (despliegue/estado.py)
- `opiniones` (servir.py)
- `pasos` (despliegue/estado.py)
- `persona_puestos` (schema_v2.sql)
- `personas` (schema_v2.sql)
- `preferencias` (servir.py)
- `rastro_cortes` (servir.py)
- `rastro_incidencias` (servir.py)
- `recargas` (schema_v2.sql)
- `registro` (schema_v2.sql)
- `registro_huellas` (servir.py)
- `sellos` (despliegue/estado.py)
- `sinc_cambios` (sincronia.py)
- `sinc_pasos` (sincronia.py)

## Campos de ctx

`accion`, `alCambiarPeriodo`, `ambito`, `api`, `avisosCelebraciones`, `carteraIds`, `carteraPorSilla`, `celebraciones`, `clientes`, `clientesVisibles`, `cuotaEmpresa`, `datos`, `datosModulo`, `definiciones`, `diaDatos`, `fechas`, `fechasDe`, `hoy`, `indicador`, `indicadores`, `navegar`, `nivel`, `nombre`, `params`, `periodo`, `periodosConDatos`, `persona`, `plural`, `puestos`, `rastro`, `real`, `servidor`, `soloLectura`, `titulo`, `veModulo`, `ver`, `verDato`, `verdad`, `verdadComun`, `zona`

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
- `snov`
- `snov/sv.py`
- `zadarma/zd.py`
- `zoho`
- `zoho/zbookings.py`
- `zoho/zh.py`
- `zoom/zm.py`
