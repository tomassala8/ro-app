# 643 · Fixtures de cadencia actual y negativas de autoridad

RELEASE local. Sólo se editaron pruebas; las fuentes 640/641 fueron copiadas por raíz. No se ejecutaron proveedores, HTTP, escrituras de negocio, Git ni migración/v2.

## Resultado

- Nueva `pruebas_cadencia_643.cjs`: 29 grupos PASS contra los tres helpers reales de APP, con renderer de Reuniones y siete columnas.
- 305: 8 grupos PASS; 307: 10; 453: 19; MiDía309: **10 grupos completos PASS**.
- `pruebas_cadencia_metodo.cjs`: batería completa PASS (cohorte, unknown, celebración/cita, histórico, fallo de API y aislamiento).
- Sintaxis de los seis archivos de pruebas: PASS.

## Adaptaciones concretas

Las fixtures positivas ahora aportan catálogo actual, clientes visibles independientes, detalle autorizado, actores canónicos activos y puestos íntegros. El especialista usa puesto `trafficker`; `publicidad` es servicio y no sustituye ese puesto. No se cambió la matriz de permisos.

En 309 la persona `otro` sin catálogo no obtiene overlay, incluso al añadir cartera; un Account legítimo separado sí mantiene la lectura. El caso de propietario dado de baja usa un Account activo distinto para comprobar unknown sin invalidar accidentalmente al propio actor. Los diez escenarios originales siguen presentes, incluidos cambio durante await, revocación posterior, fallo sin fallback y una sola lectura sin caché compartida.

453 carga las funciones reales de fecha y sus aliases de importación. Cuando el catálogo del actor se vuelve ambiguo durante la lectura, se exige ausencia completa del panel, en vez de tolerar un panel vacío conectado. No se relajaron negativas de permisos.

La nueva batería 643 cubre roles vacíos, duplicados, tipos inválidos, espacios y caracteres fuera del formato; ACT contradictorio, catálogo ausente/duplicado y visible contradictorio; cambios de propietario, catálogo, asignaciones y grants al abrir detalle y durante GET. El caso positivo conserva siete columnas e historial separado de celebración/programación, y la regla de quince días.

## Límites

Se validó comportamiento sintético de las fuentes actuales, no funcionamiento de proveedores ni exhaustividad de reuniones. Cero filas de reuniones confirmadas no acredita ausencia de reuniones. El helper de puestos valida formato, unicidad y presencia literal de trafficker; no recibe el catálogo completo de puestos de la política y no certifica todos los puestos adicionales como reconocidos.

## SHA-256

- `pruebas_metodo_cohorte_305.cjs`: `f72f6348af10c79340a687729c35a3079c4e79bb34865312d8ea775b2eab3c70`
- `pruebas_reuniones_cadencia_307.cjs`: `419f617d700b80bba33a938240f3c15628841931fcf36e844c8b2312110c4a69`
- `pruebas_seguimiento_metodo_453.cjs`: `69e067bf8674957999a69a7b810a2b50f18da38eb88de5e97294116c101e0a76`
- `pruebas_mi_dia_cadencia_309.cjs`: `d3c89e6586a20fff91ee633a1579334781a4a4e1f866a84ec8668e4a82b9017d`
- `pruebas_cadencia_metodo.cjs`: `9a2bf02300ed9ec622ffd5aa11346866f463f4286bf43aaebe4eddccc405d921`
- `pruebas_cadencia_643.cjs`: `572569ffe3175d3178b5137127fcfee12926081c15e0536400b91741357deee7`
- `modulos/_metodo_cohorte_305.js`: `46e93e5c39d17bcdb42797dc0c90183d378831dc9c4cd108d683922257292a4c`
- `modulos/_cadencia_metodo.js`: `3af9022446ffaf4ec8e95667f850e8c156ef88feefd0e6c434d7e08a1489427a`
- `modulos/_seguimiento_metodo_453.js`: `f57d43fa6bea278e2078fdbc8c9c8a9265d0944c9b2310ae2a3645df2decffcc`
