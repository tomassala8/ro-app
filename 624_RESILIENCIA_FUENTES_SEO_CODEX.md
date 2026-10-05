# 624 · Fuentes SEO locales independientes

4 octubre 2026 · SOURCE_RELEASE. Sólo `fuentes_seo/seo_prioridades_fuentes.py`; nuevas pruebas `probar_seo_fuentes_624.py`. No API625/UI626/motor ni datasets editados.

## Defecto y solución

`cargar_local` hacía json.loads sin tratamiento de errores y encadenaba las tres lecturas: un JSON corrupto en GSC, SE Ranking o contexto de motores abortaba toda la respuesta. También se pasaban colecciones de forma incorrecta a .get/iteración y posiciones antiguas junto a `_source_error` podían seguir alimentando el evaluador.

Cada recurso se lee por separado. Ausente, corrupto, no disponible, JSON duplicado/NaN/estructura/identidad inválida o error declarado quedan desconocidos sólo para ese recurso. El evaluador existente sigue recibiendo posiciones/páginas de las demás fuentes compatibles. No se recupera automáticamente otra copia, no se escribe caché ni se llama proveedor.

Lectura local acotada10MB, UTF-8, descriptor sin seguir symlink final y sin bloqueoFIFO, archivo regular y marca estable antes/después. Los fallos nunca incluyen rutas, excepciones ni datos del proveedor en el resultado. No hay IO al importar el adaptador.

## Identidad, error y fechas

Validación top clientes=dict, claves CID canónicas y filas dict con cliente_id coincidente si existe. El CID continúa suministrado por el contexto autorizado del caller; no se deduce de títulos/URLs ni se conceden permisos.

Ranking requiere motores/listas de palabras tipadas, ID de motor numérico acotado y único; palabras exactas no duplicadas (casefold/espacios, conservando tildes/variantes históricas diferentes). GSC exige páginas/listas/ventanas, números finitos no negativos o null y URL única. Datos erróneos no se transforman en0, ni se elige una variante duplicada. `_error`, `_source_error` o error declarado en top/registro/motor/palabra excluyen la fuente afectada: las posiciones retenidas bajo un fallo no se promueven como observación actual. Contexto de motores inválido no borra posiciones ni clics independientes.

El adaptador conserva las fechas originales. El motor existente excluye fechas futuras y sigue mostrando antigüedad/fecha para una observación histórica válida; no se inventa umbral de frescura ni se rejuvenece a hoy. Una referencia antigua sin error no se convierte en fuente nueva. Cero de posición sigue desconocido; clic0 explícito con impresiones reales conserva su señal observada.

## Salida para625

Campos objetivos/prioridades/contenido/cobertura existentes intactos; se añade `diagnosticos_fuentes`:

`{seranking:codigo,gsc:codigo,seranking_motores:codigo}`

Códigos fijos: disponible, ausente, no_disponible, copia_invalida, estructura_invalida, identidad_invalida, identidad_duplicada, fuente_con_error, valor_invalido, sin_registro. Sin conteos completos ni contactos/errores libres/rutas. El recurso disponible puede tener muestra vacía explícita: no significa inventario exhaustivo ni0 global. Coberturas descriptivas existentes se mantienen; API625 puede whitelistear estos estados seguros sin propagar documentos originales.

## Verificación

`PYTHONPATH=fuentes_seo python3 -m unittest fuentes_seo.test_seo_prioridades fuentes_seo.probar_contexto_286b fuentes_seo.probar_motores_contexto probar_seo_fuentes_624`: **55 PASS (16 nuevos624 +39 regresiones)**. Motor y cargar_local reales con cachés temporales sintéticas: corruptGSC→SR6 conservado; corruptSR→GSC5clics conservados; todo ausente unknown; errores con posición anterior no se acreditan; JSON/ID/motor/keyword/URL duplicados; estructuras/valores malformados; contexto corrupto; NaN/infinito/entero desbordado; futuros/antigüedad original; posición0≠clic0; symlink y no mutación de entradas. Compilación de dos archivos PASS.

La primera invocación conjunta desde fuentes_seo tuvo sólo un fallo de import de probar_contexto286b (requiere APP en sys.path); se repitió con rutas de ambos módulos correctas, sin cambios de producto ni assertions relajadas. No pruebas reales de proveedor, API o UI; runtime sigue bajo raíz.

## SHA-256

Fuente: `c9195e9e3efd098e9cec3d3fae786cef5330af0f58bb33504841acc003471f67`

Pruebas: `151017e2aa6f3b09b9883735f1464c80945593999f6fda98028a054d5bef69e1`
