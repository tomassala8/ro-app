# 657 · Candidato aislado para consejo Método308

RELEASE candidato, APP/GitHub/runtime/fuentes/bases intactos. Baseline consejo_metodo_308.py SHA-256: da9376db9b2be50c2611f959e0368a875d124e11b483f89353b378b2a5ee4cf7. Archivos en RECUPERACION_CODEX_2026-10-03/revision_metodo_cerebro_657.

## Reproducciones nuevas

- _scope308 incluye un CID catalogado activo:false o estado:baja cuando ACT aún devuelve true y P.cliente_detalle lo permite. Fixture usa P/contexto/módulos reales con Ops y catálogo ficticio; diverge del gate de metodo_cuentas actual. No es prueba de que ACT real esté desactualizado.
- responsable_confirmado308 acepta puestos='no_trafficker' o dict con key trafficker: membership no valida lista de roles. El helper puro declara responsable confirmado. En lectura integrada ficticia, la asignación es válida al calcular sugerencias y el target rota a string antes del segundo scope. Scope verifica actores, no target; la proyección final todavía declara el target confirmado. Transporte falso envuelve _scope real, sin sustituir sus grants; no HTTP real.
- Dos documentos se leen una vez y sólo se revalida scope. La fuente virtual de reuniones cambia de evento celebrado a lista vacía después de la lectura inicial: lectura308 conserva última confirmada anterior. Es un residuo de lectura concurrente, no prueba de escritura no autorizada del fichero.

## Candidato conservador

persona_unica exige ID sintáctico y roles list no vacía, strings IDs válidos únicos, además actividad previa. _scope excluye activo:false/baja junto con ACT y grants existentes. Sin ampliar ROLES, asignaciones ni módulos.

leer_metodo308 congela una copia del ámbito inicial, compara ambas lecturas del ámbito y relee política/reuniones antes de la última guardia. Cambios producen None, no propietario/cadencia reutilizados. Se conserva15d, todas las recomendaciones vigentes y reunión_agendada:null. No se añade programación, asistencia ni cumplimiento. Fallos se mantienen cerrados según el contrato existente de helper opcional.

6 tests propios PASS: catálogo/ACT divergentes, malformedroles, rotación del target, cambio de celebración, positivo idéntico y actor invalidado antes IO. 17 regresiones actuales seleccionadas contra candidato:16 PASS,1 requiere adaptar EXPECTATIVA de transporte a None cuando cambia ámbito (test_revocation_during_read_no_metadata_exposed esperaba DTO vacío). No se modificó su test ni se relajó assertion: callers actuales ya toleran None. Se excluyó del ensayo la prueba test_current_actual_policy_14_without_external_reads porque abre la política operativa real, fuera del alcance.

No certifica toda API ni capa frontend305/307. Los objetos/ficheros/config siguen controlados por el mismo usuario privilegiado; no existe snapshot transaccional de ficheros, ni garantía contra rotación después de la última lectura. Integración requiere QA de raíz y esa compatibilidad de fixture; no reemplazar source publicado automáticamente.

## Hashes candidatos

- consejo_metodo_candidato_657.py: f7028bc76b34c4a89ddd0e02ee548140c16a0ceb86938ee2eefda8569ec4b047
- consejo_metodo_657.patch: 02d4d3e7d2a662b8745206e48f61f867bc4d9784b79257cd8a8e2d62713930bd
- probar_revision_metodo_657.py: d773751339e8ec6ab167290adfe6fc52ec641e8d617ca35e7feb4d223aabf5db

## Integración local autorizada · RELEASE657

Baseline comprobado idéntico antes de copiar el candidato a APP/consejo_metodo_308.py. Adaptación explícita del test de revocación en probar_consejo_metodo_308.py: espera None, sin DTO ni metadatos. Nueva APP/probar_revision_metodo_657.py portable, sin R/spec/import de candidato; ejerce helper actual con P real y fuentes ficticias. Positivo verifica responsable, fecha/proxima+15, preparar_seguimiento y reunión_agendada:null. 51 PASS: probar_consejo_metodo_308 (18), probar_revision_metodo_657 (6), pruebas_metodo_cuentas (10), pruebas_metodo_cuentas_305 (9), probar_lector_metodo_649 (8). AST de los tres ficheros válido.

Corrida adicional473:24 casos,23 PASS y1 expectativa obsoleta del evento sin evento_id: tras640 queda sin_dato, pero test antiguo esperaba confirmar_recencia. Ese caso sólo usa metodo_cuentas (no consejo308), no prueba regresión657. No se editó473 por no pertenecer al scope cedido. No afirmar todas las regresiones verdes. APP cambiado exclusivamente esos tres ficheros; sin runtime/Git/provider/DB/migración.

SHA-256 RELEASElocal:

- consejo_metodo_308.py: f7028bc76b34c4a89ddd0e02ee548140c16a0ceb86938ee2eefda8569ec4b047
- probar_consejo_metodo_308.py: fcc4c0d0d7b683a82b529213a7c21005908461a3dc5741736983c92a55fff2e9
- probar_revision_metodo_657.py: 1f62f8e9eed4b81557cd8d0f6ed5bafd6345f5e9c04a66ae87b1877fbc1aa334
