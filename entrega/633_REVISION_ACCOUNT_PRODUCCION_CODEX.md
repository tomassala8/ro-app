# 633 · Descriptor actual de revisión account

SOURCE_RELEASE. Sólo `_produccion_baseline.js` y prueba propia `pruebas_revision_account_633.cjs`.

`revisionAccount633(p,D)` admite exclusivamente estado medido, fuente flujo, fecha válida igual al sello de flujo del DTO, cliente/proyecto único y contadores enteros seguros no negativos, +48 h ≤ total. Valida calendario, reloj y offset ≤14:00; rechaza fecha posterior a `D.hoy`. Las fechas naive legítimas siguen siendo naive: no se les asigna zona nueva. Cero explícito es una observación parcial; ausencia/malformado no se convierte en cero.

`metricasProyectoBaseline` consume el descriptor antes del formato heredado, pero 256 conserva su precedencia tanto para totales positivos como para ausencia de observaciones. No combina edades de flujo antiguo con el snapshot nuevo. Las sumas por account usan el agregador existente y requieren cohorte/corte compatibles; filas faltantes conservan cobertura n/N. Colores/columnas actuales intactos; una edad >48 h respaldada puede activar la banda de referencia existente409, nunca verde por cero parcial. No atribución histórica ni cambios de autores.

Validación: 15 grupos específicos633 (forma de productor, 0 vs desconocido, fuente/contadores, duplicados, cortes, futuro/offset, agregación y pintor real); 2 pruebas AST del productor131; 15 grupos del renderer baseline252; sintaxis ESM PASS. La suite252 existente también lee el descriptor del candidato256 para su regresión de precedencia; no se modificó ni volcó su contenido. No generadores, APIs, escrituras de datos, bases, runtime ni proveedores.

Límite: esto no garantiza que una fila actual sin descriptor o con snapshot256 pase a mostrar antigüedad. Mantiene desconocido cuando la evidencia disponible no permite decidir. QA visual/integración del corte corresponde a ROOT.
