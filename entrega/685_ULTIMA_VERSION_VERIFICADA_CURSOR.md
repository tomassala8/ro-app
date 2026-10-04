# Entrega 685 · última versión verificada para Cursor

Esta entrega añade a 680 las mejoras 682 y 684, con revisión independiente. No modifica migracion/ ni v2/. Conserva ClickUp y GoHighLevel y no activa envíos ni IA real.

## Cambios

- Paid: CTR total con etiqueta corta, unidades y explicación accesible; admite ratios superiores a 100 % por clics no únicos. Valores inválidos quedan desconocidos. El cero previo no desaparece y no se afirma comparación sin ventanas compatibles.
- Accounts: conteos fraccionarios, inseguros y sumas desbordadas quedan desconocidos; conserva ceros explícitos, cobertura parcial y horas fraccionarias válidas.
- Dos cargadores de pruebas incorporan dependencias reales que faltaban, sin relajar sus comprobaciones.

## Verificación

52 grupos CTR, 3 casos fórmula real, 24 grupos Paid, 15 grupos nichos, 14 grupos agregados Accounts, 45 grupos Operaciones/Accounts y 153 comprobaciones de mediciones pasan en la copia local. Se repiten en la copia de entrega antes de publicar. Las pruebas usan datos sintéticos; no ejecutan proveedores.

## Pendientes y límites

681 (conexión de transiciones históricas de planificación) permanece aislado y pendiente de integración y auditoría final. Su fuente histórica real todavía no está disponible. No confundir estados actuales con eventos observados.

No se declara completado el objetivo ni toda la batería global en verde. Persisten los pendientes documentados en 680, incluida medición completa, revisión integral por rol y migración. No hay despliegue operativo: esta es una publicación de código en la rama de entrega.
