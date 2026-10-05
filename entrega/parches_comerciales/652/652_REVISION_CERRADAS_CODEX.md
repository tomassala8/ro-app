# 652 · Revisión aislada de stock cerrado GHL

Propuesta NO aplicada ni activada. Sólo depósito local `RECUPERACION_CODEX_2026-10-03/revision_cerradas_652`; APP/DB/runtime/Git/migración intactos. Transporte falso, sin credenciales, HTTP ni fuentes reales.

## Defectos nuevos reproducidos

1. Respuesta vacía con `meta.total=NaN` emite cobertura completa=true y conteos0, sin incidencias. `meta=[]` también se vuelve `{}` por `or {}`, eludiendo validación. Esta cobertura puede confundir ausencia de evidencia con inventario completo.
2. Dos variantes del mismo ID dentro/fuera de locationId autorizada conservan la válida y cuentan1. La variante fuera de filtro se elimina antes de indexar conflictos. Lo mismo ocurre ante variante status incompatible. El registro ambiguo debe excluirse entero, no escogerse por filtro.

## Parche aislado

`oportunidades_cerradas.py` conserva stock won/lost/abandoned y limita la modificación a validación de metadatos e indexación de scope:

- Total presente exige entero seguro no negativo, no bool, fracción, NaN/Infinity, string/null ni entero mayor de2^53−1. Inválido marca total_invalido y cobertura parcial; conserva observaciones válidas ya leídas. No exporta NaN.
- `meta` vacío de tipo incorrecto no se normaliza a diccionario. Metadatos omitidos/null conservan el contrato legacy de paginar hasta respuesta vacía; no se inventa un total declarado.
- Indexa ID/scope global antes del filtro. Colisión de location/status invalida todas las variantes del ID; ausencia locationId y locationId explícita igual al autorizado son coherentes porque la consulta ya es scoped. Replay con mismo scope conserva una observación.
- No cambia fecha_cierre=null, cierres_del_periodo=null ni ratio_leads_ventas=null; stock observado no venta, cobro ni fecha de cierre. Sin campos PII nuevos. No siguen URLs devueltas por proveedor.

12 pruebas propias +14 originales sin cambiar aserciones =26 PASS. Las originales se ejecutan con inyección del collect propuesto y transporte falso, sin modificar su archivo APP. Baseline reproduce cobertura falsa/variante retenida y propuesta rechaza ambas. No se repiten las reglas temporales637; ese frente no está cambiado por este parche.

## Integración pendiente y límites

El llamador sigue debiendo autorizar cliente/subcuenta y vigencia/grants antes/después; el lector recibe una subcuenta ya autorizada y no acredita ACT ni permisos por sí solo. Cobertura completa es terminación de esta lectura de estados según respuesta/transporte, no snapshot transaccional ni cohorte de ventas. No hay fuente nueva ni reader activado. ROOT/Cursor deben revisar antes de aplicar `652_cerradas.patch`.

SHA baseline APP: `fd41b8c6540dd46572ceeb780c93a5e86b3d1a5843bcd2fb9c546e5fd5e53c47`.
SHA propuesta: `6c959b1e6c8fb88a55a7bd764055b28dec444d88328e77ce80fe79b28d97b4ba`.
