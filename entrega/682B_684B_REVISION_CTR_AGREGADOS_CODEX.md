# Revisión independiente 682B/684B — fuentes locales

Resultado: aprobación acotada de los cambios inspeccionados. No se reproduce un defecto nuevo en los contratos examinados. Ningún archivo de APP se ha modificado durante esta revisión.

## CTR total 682

La fuente `fuentes_captacion/anuncios_meta.py:141–142` calcula clics totales / impresiones ×100, y `generar_captacion.py:181` conserva esos componentes y el porcentaje. Los clics no son únicos: no es una probabilidad y no procede un límite universal de 100 %. El candidato actual admite 250 % con 5 clics/2 impresiones. Un denominador explícito cero o inválido no acredita el porcentaje. El cero legítimo con impresiones positivas se conserva. Valores negativos, no numéricos o no finitos se rechazan.

La celda permanece referencia gris y explica que no acredita CTR de enlace ni comparación vigente. La ausencia de fechas/descriptores comparables sigue pendiente; este cambio de presentación no demuestra fatiga ni autoriza una acción. El helper muestra el porcentaje registrado, no reconstruye ni certifica toda su coherencia con componentes legados.

## Agregados Accounts 684

El modelo agrega sólo filas que recibe de la matriz autorizada; no crea permisos. Los conteos individuales deben ser enteros seguros no negativos. Una suma que excede la precisión segura queda desconocida, conservando cuántas filas tenían medición. La celda agregada real de 263 responde con raya gris y explicación, nunca cero. Los ceros explícitos se distinguen de ausencia.

Las horas fraccionarias se conservan y sólo se suman con un periodo común. El productor del modelo exige descriptor de medición, mes válido y sello de fuente; esta revisión no convierte una pauta mensual en capacidad ni presupuesto. Se comprobó separación de grupos, horas 1,125+0,875, desbordamiento de horas y conteos, y ausencia junto a cero explícito.

## Pruebas y huellas

- Candidato 682: 52 grupos propios PASS.
- APP 684: 14 grupos propios PASS.
- Revisión independiente: 8 casos PASS en `RECUPERACION_CODEX_2026-10-03/probar_revision_ctr_accounts_682_684.cjs`, con comprobación de que las tres fuentes no cambiaron durante su ejecución.
- `_ctr_paid_682.js`: `12f26f362a2ba55951ec164306747046377eb9500a786f2e14670d97ec1436ab`.
- `control_cartera.js`: `f1c5878abb91650684358bfd927175d67414d2c5d5c42aa7d10e769e9032213d`.
- `_operaciones_accounts_263.js`: `90bbd866bad5a9f74e6513946706da1d748eb4e91c8e96b71eda3954159c0cba`.

Límites: sólo código y fixtures ficticias. Sin lectura de datos personales, proveedor, navegador, servidor, DB principal, publicación ni activación. No es una auditoría completa de autorización de todas las rutas; se conserva la frontera existente de filas autorizadas, que debe seguir validándose por sus lectores/callers.
