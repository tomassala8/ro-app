# 662 · Evidencias del Método en recomendaciones

RELEASE local. Baseline consejo_metodo_308.py comprobado f7028bc76b34c4a89ddd0e02ee548140c16a0ceb86938ee2eefda8569ec4b047 antes de editar. Sólo ese archivo y nueva prueba portable probar_contexto_metodo_662.py; sin UI337/copy, fuentes, proveedores, runtime, Git ni migración/v2.

## Contrato aditivo

El DTO metodo_308 permanece intacto: responsable_confirmado/responsable_id actuales, ultima_confirmada/fuente_celebracion validadas, proxima_revision/hoy, reunion_agendada:null e incumplimiento:null. Top conserva ejecutor_operativo:'trafficker', comprobador_role por área y criterio actual.

En evidencias se mantiene la regla actual con fecha de consulta. Sólo si la celebración ya fue validada se añade fuente='metodo_celebracion_confirmada', fecha original sin rejuvenecer, periodo:null, cobertura='registro_confirmado_no_historial_exhaustivo', vigencia='referencia_historica', texto con fuente validada y aclaración: no atribuye participantes ni responsable histórico. No se inventa checker ni identidad del asistente.

Sólo si proxima_revision coincide con ultima+15 se añade fuente='metodo_revision_calculada', fecha=hoy (fecha del cálculo), periodo:null, cobertura='calculo_cadencia_no_agenda', vigencia='actual', texto fecha de revisión y explícitamente no acredita reunión programada/agendada. No se convierte ese intervalo en ventana observada ni medición. Una propuesta sin celebración/fuente o próxima válida no fabrica evidencias.

No lee otra fuente ni cambia autoridad657. Paid/Accounts conservan las mismas recomendaciones y responsabilidad actual. Una fuente no permitida/URL arbitraria o fecha futura no aparece. Datos históricos no prueban atribución al responsable actual ni cumplimiento; sigue requerido contraste humano.

## Verificación

31 PASS =7 propias662 +18 consejo308 +6 seguridad657. Positivos fuente/fechas originales y revisión calculada en ambas áreas, resultado inmutable, evidencias independientes; negativos reunión sólo programada/ausente, fuente inválida/futura, próxima incoherente, dueño revocado sin atribución histórica y CID fuera de scope/duplicado. AST de ambos archivos válido. No prueba HTTP/DOM real ni nueva autorización contractual.

## SHA-256 RELEASE

- consejo_metodo_308.py: 1d041ec0d16191d10fba9cc2acca28980f138ca2ddc05e36fbc0a43ba3ea2a00
- probar_contexto_metodo_662.py: fbc310f56a9fa5fbbf01183e7ddaa5be53d36cc0ad87e2f06badad18502a6077
