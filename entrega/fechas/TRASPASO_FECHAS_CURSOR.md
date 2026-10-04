# Traspaso a Cursor · Fechas RO

Verificación de solo lectura cerrada: 2026-10-04T14:11:27+02:00. Prototipo: `/Users/tomassala/Downloads/APP_RO_ROLES_Y_PERMISOS_2026-10-02/30_APP_PROTOTIPO`. No se ha cambiado producto, contratos, DB, runtime ni Git; no se han consultado proveedores o datos reales.

**18 ejecuciones PASS**: seis arneses existentes, cada uno en Madrid, Buenos Aires y Makassar. Fuentes observadas idénticas entre inicio y fin. Detalle y logs: `resultados.json`, `hashes_inicio.json`, `hashes_fin.json`.

| Verificación actual | Casos/grupos por zona |
|---|---|
| Helper y contrato de fechas, fase1 | 65 casos |
| Módulos de fase2 con adaptación Deshacer real fase4 | 77 casos |
| Agenda, regresiones existentes | 4 suites, todas PASS |
| Reuniones/Horas/Personas, fase3 | 21 casos + 4 suites de regresión PASS |
| Comercial con revisión Ventas fase6 | 32 casos, incluidos los 26 de fase5 |

Son 195 casos contados por zona (585 ejecuciones de casos), más las suites de regresión; las coberturas se solapan. **No equivalen a E0 global, navegador real o validación de proveedores.** El arnés antiguo de fase2 quedó supersedido por fase4 tras el contrato594; fase6 sustituye el guard global de fase5. Mantener esas evidencias originales y ejecutar las versiones vigentes.

## Pendientes localizados

Inventario exacto, con ruta/función/línea y motivo: **`consumidores_pendientes.csv`** (52 entradas). Es revisión estática del código actual; antes de modificar, confirmar uso efectivo y contrato del sello. No se ha reproducido cada consumidor pendiente ni se ha auditado todo productor del repositorio.

| Punto | Prioridad para Cursor | Rutas/funciones principales |
|---|---|---|
| L18 · instante/edad/formato | Mi día y hechos, después módulos restantes | `modulos/mi_dia_bloques.js`: `fecha`, `edadH`, `fresco`, `reuPasada`, `lmFecha`; `modulos/mi_dia.js`: `filasLoMio`, `plazoTxt`, `botonPosponer`; `modulos/evidencias_kpi.js`: `fechaHechoLocal`, `crearRegistroHechos`; `modulos/dinero_comun.js`: `fresco`; `modulos/nuevos.js`: `tablaTalleres`; `modulos/ia_componentes.js`: `horaDatos`. Formateadores heredados restantes y validadores están listados en CSV. Captación se coordina con su propietario Paid. |
| L19 · hoy/mes coherente | Corregir mezclas del host con datos Madrid | `modulos/mi_dia_bloques.js`: registros `captacion_ro` (192), `vro_embudo` (1633), `vro_costes` (1645), `cierre_celebradas` (1893). `mesActual` ya usa Madrid: no cambiar el dato a un mes distinto para arreglar el rótulo o ritmo. |
| L20 · histórico frente a vigente | Primero acreditar periodo de origen | `mi_dia_bloques`: `adm_bajas` (423), `setter_celebradas` (1889); `dinero_cliente.pintar` (87/127); `outreach.pintarFrente` (220). Octubre/septiembre y proyección2026 pueden ser copias legítimas: conservar fecha/corte, no renombrar a mes actual. |
| L22 · reloj del servidor/IA | Separar calendario de negocio y persistencia | `servir.py.ahora` (254/255); `ia.py`: `cliente_para_borrador`, `contexto_borrador`, `contexto_copiloto`, `borrador`, `copiloto`, `copiloto_reglas`, `candidatos_vivos`, `candidatos_de`, `candidatos_al_momento`, `_con_ia`. CSV enumera los usos restantes de `datetime.now()` y caches de minuto. |

## Contrato que debe conservar Cursor

El helper ya congelado interpreta datetime sin zona como Madrid; offset/Z como instante declarado; fecha civil sin instante; salto/repetición DST sin offset no fabrica hora. Ausente/inválido/futuro no debe convertirse en edad0 ni frescuraok. Las colas que declaran UTC conservan UTC explícito. Días laborables/cadencias civiles no se convierten en SLA de horas transcurridas.

`app.js.crearCtx`, `componentes.js.fechasDe/rangoPeriodo`, `permisos.py.ahora_madrid/hoy_iso` e `ia_gasto.py.ahora` ya usan Madrid: su existencia no cierra todos los consumidores. UTC civil explícito, validadores con Z y sellos ISO de persistencia no son defectos por contener `Date`/UTC. No hacer reemplazos globales.

Ventas fase6 es la referencia para ausencia parcial: el histórico acreditado sigue visible y solo las cifras dependientes del mes actual faltante quedan desconocidas. No recalcular importes, metodología, permisos, identidades, cadencias o contratos para resolver fechas.

La siguiente validación debe repetir bordes de día/mes/año y DST con relojes sintéticos en los tres husos, conservar las regresiones y distinguir contrato de fuente desconocido de dato observado. Este traspaso no inicia otra migración ni un rediseño; root coordina la rama de entrega a Cursor.
