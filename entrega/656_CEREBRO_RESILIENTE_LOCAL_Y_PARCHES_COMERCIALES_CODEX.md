# 656 · Cerebro resiliente integrado en local; contratos comerciales candidatos

Continuación local posterior a la entrega GitHub650 (commit1fdd99d). Sin nuevas escrituras externas. El corte publicado queda disponible para Fable; la revisión local añade654, y Cursor dispone del parche/fixtures portables en RO_MIGRACION/PARCHES_COMERCIALES_CODEX.

654 integrado sólo en APP después de comprobar baseline SHA de cerebro_operativo/meta_informe_291/paid_mediciones_331. Modificados los dos primeros;331 permanece idéntico. Contenedores por campo se validan independientemente y agregan brecha localizada; números que desbordan vuelven desconocidos. No catch global ni reinterpretaciónCSV/cobertura/permisos. Una velocidad inválida no quita WhatsApp válido del mismo cliente ni Paid/CRM de otro. Fuente/fechas de los argumentos no se mutan.

Verificación raíz sobre APP actual:9tests nuevos654,27regresiones motor,5auditoría184,7API y12puente621 PASS (60tests, coberturas solapadas). CuatroGET200 en runtime reiniciado: Operaciones/Account y filtrosCRM/Paid; sólo estados/tiempos/estructura guardados en verificacion_cerebro_656.json. Salidasapagadas/base separada. No prueba de carga/todaslaspantallas ni certificaciónglobal.

652 permanece candidato: lector de stock cerrado rechaza metadatos/total inválidos y conflictos deID por subcuenta/estado, con26pruebasPASS. Lector sigue sin activarse; stockwon no es evento venta/cobro ni fecha cierre.
653 permanece candidato: identidad source+event_id global antesCID impide doble tasa por evento compartido entre clientes.8nuevas+14regresionesPASS. No bypassactualAPI467 ni etapasnuevas. Integrarlo requiere contrato/whitelist/anclas actualizados explícitamente, preservando puertas y cobertura.

Paquete655 portable verificado también desde RO_MIGRACION: cinco ejecucionesPASS (26/8/14/9/27, no sumar como casos únicos). Baselines y regresiones dentro del paquete; no rutas a datosprivados. Nuevo estado656 supersede frase candidata654/noAPP de documentos previos655: ahora654APP local integrado;652/653 aún no.

APP no se reemplaza por paquete ni se modifica migracion/v2. GitHub650 no contiene esta continuación; comparar patch654 con la versión de Cursor antes de aplicar. Revisión local sigue127.0.0.1:8771. Objetivo amplio no completo: siguen participación/coberturahistórica, criterio comercial/venta/cobro/atribución, capacidadescontractuales, transiciones, universoKPIs y consumidoresUI/fecha. Sin49cierresextra/10/10.
