#675 · Última entrega de código RO para el plan D

Rama: codex/ro-entrega-cursor-2026-10-04, repositorio tomassala8/ro-app. Integrar desde esta rama conservando commits; no sustituir main ni la rama de migración automáticamente.

## Historial posterior al último corte remoto650
-21db936(660): resiliencia del cerebro por campo, sin convertir lecturas inválidas en0 ni perder otros clientes.
-0ac41fa(661): seguimiento Accounts y traspaso de pendientes reproducibles.
-8ba43d6(666): contexto quincenal con fuente y fecha, papeles operativos y copia invalidada si cambia el ámbito.
-66e2709(670): integridad de oportunidades cerradas y eventos del embudo; reconstrucción offline y contrato actualizados coordinadamente.
-9e7ad79(674): Paid por nicho con universo/moneda/unidad/semana compatibles; intentos CRM dentro del período del lead; auditoría antigua de correo como referencia gris.
-Este commit675 actualiza únicamente la nota de entrega y el traspaso para publicación autorizada.

## Lectura y validación
674_PAID_Y_SEGUIMIENTO_CRM_LOCAL_CODEX.md,670_INTEGRACION_CRM_LOCAL_VERIFICADA_CODEX.md y666_CONTEXTO_METODO_Y_COPIA_VIGENTE_CODEX.md contienen alcance y pruebas. Las pruebas focalizadas pasaron en APP y checkout de entrega.29 suites aisladas de seguridad pasaron durante670. No equivalen a todas las baterías globales, navegador completo, carga, restauración o Postgres.

El checkpoint local final contiene1050archivos/4335365bytes; es código, no copia de datos operativos. Los patches/diffs históricos se conservan con sus huellas originales: sus líneas de contexto contienen espacios propios del formato. La comprobación de espacios del código y documentos, excluyendo esos artefactos históricos, pasa.

## Condiciones de migración
Mantener prioridades Operaciones→Accounts→Paid, ACT y permisos del servidor/viewas; missing≠0, fuente histórica≠dato actual, reserva≠asistencia, stock ganado≠venta/cobro, referencia≠objetivo contractual y fuego≠cliente rojo. Mantener ClickUp/GHL operativos y todas las salidas apagadas.

No ampliar etapas CRM ni rejuvenecer snapshots. El productor principal todavía no incorpora una fuente de cierre histórico; las oportunidades abiertas no permiten recuperarla. El cambio672 no recalcula caches antiguos porque faltan mensajes originales. Quedan pendientes varios agregados legacy, mediciones completas del artifact, jornada/capacidad aprobada, transiciones/participación, respuesta/cualificación/ventas/cobros/atribución y consumidores de fechas.

La tabla49 externa conserva sus estados; sóloL16 tiene cierre formal. No tocar migracion/ niv2/ ni reemplazar bases/fuentes con fixtures. No se certifica10/10 ni objetivo completo. Publicar esta rama no despliega la aplicación ni activa proveedores.
