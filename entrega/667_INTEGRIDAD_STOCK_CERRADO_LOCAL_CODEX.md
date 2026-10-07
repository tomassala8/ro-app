# 667 · Integración local de integridad del lector de stock cerrado

RELEASE local. Baseline fd41b8c6540dd46572ceeb780c93a5e86b3d1a5843bcd2fb9c546e5fd5e53c47 confirmado antes de editar. Se instala exactamente la propuesta652; sin activar lector, transporte, productor, API ni nuevas etapas.

## Contrato conservado y corregido

Total explícito exige entero seguro no negativo; bool, NaN, Infinity, fracción, texto, null y valor mayor de 2^53−1 no acreditan completitud ni cero medido. Un total legítimo0 conserva su cobertura si la lectura termina correctamente. Meta de tipo incorrecto no se normaliza a un objeto vacío; ausencia/null conserva la paginación histórica sin total declarado.

La identidad se indexa antes de filtrar location/status. Variantes incompatibles de un mismo ID invalidan todas sus observaciones, en cualquier orden. Location omitida y location explícita igual a la subcuenta consultada son coherentes; replay idéntico conserva una observación.

Sigue siendo stock won/lost/abandoned: `fecha_cierre`, `cierres_del_periodo` y `ratio_leads_ventas` continúan null. updatedAt nunca acredita un cierre. No se añaden etapas cualificado/asistencia/venta ni ingresos, PII o nueva autorización.

## Pruebas

`python3 probar_cerradas_integridad_667.py`: 26 PASS =12 negativas/positivos nuevos +14 regresiones originales con aserciones intactas. Baseline preservado en fixtures; la prueba muestra NaN/meta[] previamente complete y variante conflictiva previamente retenida, frente a resultado conservador actual. Transporte inyectado ficticio; ninguna API/red ni dato privado. Tres archivos pasan análisis sintáctico.

## Límites

El caller debe seguir acreditando cliente/subcuenta y permisos vigentes antes/después: este lector no autoriza ACT ni acceso por sí mismo. Completitud corresponde a terminación de la consulta según metadata/transporte, no a snapshot transaccional, cohorte de ventas ni ausencia de cambios concurrentes del proveedor. Sin Git, runtime, servidor, proveedores o bases reales; integración futura depende de raíz.

## SHA-256

- `fuentes_crm/oportunidades_cerradas.py`: `6c959b1e6c8fb88a55a7bd764055b28dec444d88328e77ce80fe79b28d97b4ba`
- `probar_cerradas_integridad_667.py`: `e239195f086d855c66db3f63fad7108de65db7a5bc9f42bcf9502403848773cf`
- `fixtures/oportunidades_cerradas_667_baseline.py`: `fd41b8c6540dd46572ceeb780c93a5e86b3d1a5843bcd2fb9c546e5fd5e53c47`
