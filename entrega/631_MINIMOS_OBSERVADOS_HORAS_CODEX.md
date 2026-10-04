# 631 · Formato conservador de mínimos observados

RELEASE. Cambio exclusivo de presentación en `30_APP_PROTOTIPO/modulos/_operaciones_equipo_262.js`; no se alteran sumas, bandas, fuentes, permisos, pautas, orden ni referencias. Sin proveedor, runtime, datos privados o migraciones.

630 reprodujo mediante renderer real el defecto1,06h→≥1,1h. La caracterización630 ahora exige el resultado corregido, sin quedar anclada al defecto histórico.

## Corrección

`fmtMinimo262` trunca de forma conservadora la cifra que acompañará≥. Evita multiplicación desbordada y comprueba que la representación decimal finita resultante no supere el dato original. Las observaciones normales siguen con el formato anterior. La rama pequeña conserva`<0,1`, sin convertirla en un mínimo cero.

Se aplica a las horas parciales90d de Por persona, al porcentaje mínimo de esa fila y al KPI mínimo de equipo de la misma rama. El porcentaje conserva la precisión adicional de381 junto a60/90 y sus límites con<; los colores se calculan con el valor original. Ejemplo1,06h de40h referencia:≥1h y≥2,6%, frente a las anteriores afirmaciones≥1,1h y≥2,7%. No son cumplimiento ni capacidad contractual.

## Verificación

- `pruebas_minimos_horas_631.cjs`: **12 grupos PASS**, renderer real262 y DTO362 sintético:1,06, cero explícito, enteros,5,99/7,99, extremo1e308, valor pequeño, desconocido, observación diaria normal, porcentaje desbordado y frontera59,99 roja.
- `pruebas_caracterizacion_horas_630.cjs`: **correctivo y control PASS**.
- `pruebas_bandas_horas_381.cjs`: **15 PASS**.
- `pruebas_operaciones_equipo_262.cjs`: **47 PASS**.
- `pruebas_horas_compactas_450.cjs`: **7 PASS**.
- Comprobación sintáctica ESM: PASS.

Sólo fixtures y render DOM simulado. No impresión, captura ni POST real. QA de navegador pendiente de raíz.

SHA256 de entrega:

- `_operaciones_equipo_262.js`: `db33b1918873f2db0466f08b4c496b57fe6cb2ab0cce0eadc33d3616efbd4cb0`
- `pruebas_minimos_horas_631.cjs`: `d3772dd9ad79b7c1438ebba238fec5da1cb486ad9c2ca84584d5c4bddc55df66`
- `pruebas_caracterizacion_horas_630.cjs`: `79d26bb9fcda24cbc5a39a35e7bb5093e766a213119c9ed1ae8fd26caea7ec93`
