# 612 · Informes declarados mensuales, celda neutral

4 octubre 2026 · SOURCE_RELEASE helper sin integración propia.

Archivos exclusivos: `modulos/_informes_declarados_612.js`, `pruebas_informes_declarados_612.cjs`. Sin imports263, API/IO, rutas, backend, ledger, datos, proveedores o mutaciones.

## Contrato611 acordado

Top: version611.1, periodo_informe YYYY-MM, source_kind registro_equipo, cobertura parcial, verificacion_externa=false, cumplimiento=null y nota literal fija. Clientes: [{cliente_id,informes_declarados safeint>=0,source_kind registro_equipo,verificacion_externa=false,cumplimiento=null}]. Cobertura sólo top. La nota coincide exactamente con611; texto libre/HTML/otros campos se rechazan, no se renderizan. Ni fechas/envíos/actores/enlaces individuales ni dinero se propagan.

El período es el **mes del informe**, no mes de envío ni último mes con actividad. No se añade a Desk, a un Score ni a porcentaje de cumplimiento. Cuenta declarado localmente, no envío verificado ni responsabilidad histórica. Fila explícita0 válida→0 decl.; ausente/duplicada/malformada/fuera del ámbito→—. Fuente unavailable no se sustituye por una copia anterior.

## API frontend

1. `ambitoResumenInformes612(ctx,periodo)` devuelve {ids,periodo,firma}, o null. El caller añade `vigente:()=>boolean` de ruta/epoch/mes antes del GET611. Puede restringir ids a un subconjunto de esa misma firma.
2. `proyectarResumenInformes612(ctx,respuesta,scope)` rederiva autoridad antes y después de proyectar; retorna modelo o null. Toda fila debe pertenecer al ámbito solicitado; no se filtran silenciosamente filas ajenas.
3. `celdaInformeDeclarado612(modelo,cid)` retorna {valor,estado:'gris',informes_declarados,detalle,vigente}. El renderer comprueba vigente() antes de pintar/abrir detalle; si reconsulta la celda tras revocación devuelve—. Conserva los conteos en WeakMap, sin spread del DTO ni nombres/contactos visibles. El mes usado por el tooltip es el del ámbito almacenado, no una propiedad externa mutada.

Autoridad: servidor=true; vigente actual; mi-trabajo autorizado; ambos actores únicos, activos, activo!==false y roles canónicos exactos sin duplicados. Cliente único tanto en ctx.clientes como clientesVisibles, ACT confirmado, detalle verdadero, no activo:false/baja y cliente_detalle permitido. La firma incluye catálogo completo de personas/clientes, actores, grants actuales, fecha y período, por lo que cambio durante await/repintado invalida el resultado. No exige que ambos tengan rol Account ni rechaza ver como para lectura.

`ctx.ver`/`veModulo` corresponden a la vista en app.js; GET611 conserva autoridad servidor real∩vista. El helper no inventa un catálogo de permisos del actor real ni permite consultar fuentes privadas para reconstruirlo. Vigencia/firmas frontend complementan, no sustituyen, esa puerta backend.

## Pruebas

`node pruebas_informes_declarados_612.cjs`: **31 grupos PASS** sobre funciones reales en VM, sin HTTP/POST. Incluye positivo/0/null/missing, safeint, períodos y nota fija, schema fuente/cobertura/verificación/cumplimiento, privacidad monetary/unknownfields, catálogo duplicado/inactivo/roles, cliente ACT/baja/activo:false, revocaciones antes/después, ver como legítimo, callback epoch requerido, mutación DTO/modelo, reevaluación doble y callback de celda obsoleta.

Sintaxis ESM PASS. Resumen157 mantiene sus pruebas PASS (regresión de contrato existente; fuente no editada). Integración263/611 y QA real pertenecen a raíz/auditor613: no se certifican aquí a partir de fixtures.

## SHA-256

Helper: `6d6c0440d21fc00c6834e1d03e4b60901bd2e7b8299ef78c1ee7d6a7d7d5ee83`

Pruebas: `8e20ea07d884b0f4a3a48bd4d803d20ad800da568e5e9edf749e249044834d7a`
