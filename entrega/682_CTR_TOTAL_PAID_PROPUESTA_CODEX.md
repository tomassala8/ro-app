# 682 · CTR total de creatividades, propuesta aislada

RELEASE del candidato; APP intacta. Sólo import y dos celdas CTR, sin columnas adicionales, cambios de cálculo, Score, colores de estados, CPL ni permisos.

## Defecto reproducido

`fuentes_captacion/anuncios_meta.py:141–142` construye `clics` desde `f['clicks']` y CTR desde clicks / impressions. `fuentes_captacion/generar_captacion.py:145` copia ese CTR a ctr_7d. Son clics totales, mientras `modulos/paneles.js:358` calcula explícitamente CTR de enlace usando clics_enlace. Antes las tablas de creatividades mostraban «CTR»/«% de clics», indistinguibles. El detalle además mostraba `— %` para null, `-1 %` y omitía previo cero.

## Corrección

Las dos cabeceras dicen CTR tot., con título completo accesible. Sólo número finito no negativo (puede superar100 %): cero numérico permanece visible; null/boolean/string/NaN/Infinity/negativo/fuera de rango quedan —. La celda no acredita cobertura ni vigencia del legado. El previo 0 se conserva en title como referencia guardada. Caída y previo dejan de ocupar el texto numérico; no se calcula comparación sin ventanas compatibles. No se atribuyen clics de enlace, leads, ventas ni resultados humanos. Las rutas y filtros actuales permanecen y usan las filas ya autorizadas del renderer.

## Evidencia

52 casos nuevos ejecutan las funciones pCreatividades y tAnuncios reales y tablaDensa real: baseline defectuoso y candidato, cabecera/title/ARIA, cero, límites, datos malformados, previo cero, sin infinito, no mutación, 8 columnas y reserva monetaria. Regresiones 425:24 y nichos671:15 PASS (94 grupos, incluyendo3 pruebas AST de fórmula real). Sintaxis de ambos candidatos validada. Harness425 aislado sólo carga dependencia real549 y nuevo helper682; assertions intactas.

153 no es regresión necesaria de estas celdas: su extracción antigua de sumar CRM falta agregarMensajesCRM597; intento aislado evidenció ReferenceError, no se alteró ni se presentará como PASS.

## Entrega y límites

- Baseline captacion APP: `0f0956356073bbda479b15ff9ac59a6313885b279401f4b61ea4eed82ac99b91`.
- Candidato captacion: `4f113f0c9b1f63b881bde10625bb626721013eb064c194cbfa81aaa2915ee293`.
- Helper: `12f26f362a2ba55951ec164306747046377eb9500a786f2e14670d97ec1436ab`.
- candidato.diff / manifest_682.json y probar_ctr_paid_682.cjs son locales.

671 queda byteidéntico. CPC/CPM/CTR de paneles no cambian: CPM417 ya tiene contrato propio; Meta diaria etiqueta CTR total y paneles CTR enlace. No se derivan CPC/CTR por cuenta sumando ads ni se agregan nuevos datos. Corrección de revisión raíz: la fórmula real permite200 % (2clics/1impresión); no es probabilidad de clics únicos y no tiene techo100. La UI preserva200 registrado gris. Si impresiones_7d está presente debe ser entero seguro positivo; clics_7d presente debe ser entero seguro no negativo. Denominador0/ausente inválido explícito no acredita ratio; sin campo se conserva sólo referencia CTR legado, sin derivar nuevo ratio. La fuente aún carece de descriptor suficiente para acreditar CTR como periodo actual completo. Ningún proveedor, dataset, runtime, API real o Git fue usado.

## Cierre correctivo682B

52 renderer +3 fórmula AST real +24reg425 +15reg671 =94 PASS. Fuente productora sólo leída/copiada para prueba AST, jamás importada ni ejecutada como generador. Cadena fórmula imp1/clicks2→200 y renderer200 % conserva unidad de clics totales. NoAPP cambios.
