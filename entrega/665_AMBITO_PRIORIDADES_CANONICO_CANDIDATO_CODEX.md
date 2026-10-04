# 665 · Candidato aislado de ámbito Prioridades/portapapeles

RELEASE candidato en RECUPERACION_CODEX_2026-10-03/revision_scope_prioridades_665. APP no editado. Se esperó RELEASE663 y su pulido final. Baseline337 SHA92c6605364e8a7ddaf2d415609468ec8a10a333ceed38a85a091095be91f6cbd permanece idéntico.

## Fallos reproducidos en renderer actual y transporte ficticio

El ámbito337 original valida clientesVisibles pero ignora ctx.clientes. Cambiar sólo el catálogo canónico a activo:false, estado:baja o duplicado mantiene IDs/firma y la copia de la UI se ejecuta. Cuando se da de baja un target distinto del actor tras GET, la firma original tampoco cambia y permite copiar. Roles actor/canónico con entries no-string, repetidas o vacíos se comparan tras filtrar, en vez de rechazarse. No se demuestra autorización HTTP para esas identidades inválidas: es guard de contexto local obsoleto.

La prueba VM ejecuta helpers reales _tarea_ia/clipboard337 y renderer prioridades_cliente, reutilizando el harness DOM actual. Sólo API/clipboard son falsos y sin salida externa. No navegador/servidor/datos reales/DB.

## Candidato mínimo

Exige roles list no vacía de strings IDs válidos y únicos tanto en actores como canónicos; cliente elegible debe existir único en ctx.clientes y clientesVisibles, ambos con ACTconfirmado:true, detalle:true, activo!=false/estado!=baja y grant ctx.ver actual. Sin catálogo canónico no se concede scope.

Firma incorpora personas exclusivamente ID/roles/estado/activo; excluye nombres/correos. Incluye proyección actual de ambos catálogos clientes/grants y asignaciones semánticas (IDs, silla, fechas/principal/suplencia/titular/confianza/duda), si ya existen. Ausencia asignaciones no es requisito nuevo ni implica dueño confirmado. No se introduce epoch, nueva fuente, permisos ni inferencia de tenure/objetivo; cambio de esos metadatos invalida el contexto anterior en callbacks ya existentes.

La sección663 y el resto del helper desde periodo337 son byteporbyte idénticos: ejecutor/comprobador legibles, cuatro argumentos/fecha actual y límites metodológicos no se modifican. No se toca renderer ni copiarInstrucciones; una copia nativa ya invocada mientras era autorizada no puede deshacerse posteriormente.

## Pruebas y compatibilidad

17 grupos PASS: catálogo false/baja/duplicado; malformedroles; positivo; catálogo ausente; renderer baseline copia después de revocación y candidato bloquea/limpia; cambio asignaciones/roles; targetbaja trasGET; revocación durante GET ficticio; asignaciones ausentes; firma sin nombres/correos. Ambas negativas de renderer usan source real y nodes conectados; no sólo prueban un helper aislado.

Antes de integrar habría que adaptar fixtures positivos337 que omitían ctx.clientes; la app real sí lo provee. No se ejecutan como verde todos esos tests antiguos contra un contexto incompleto ni se debilitan sus aserciones. Candidato no activo, no garantía de producción ni reparación de caches backend. No APP/Git/flags/runtime/proveedores/migración.

## SHA-256 candidato

- _prioridades_contexto_candidato_665.js: c53489693b3657f947e3ce8675652eb3a2489ae821b722d20d0ba6164fbc80f1
- prioridades_scope_665.patch: 132b5468fe546833fcbcf35cc6a91b577f4413b49433529577dc9fde1a80a79e
- probar_scope_prioridades_665.cjs: 917e5d14466b0265947ec1dd6f97c9ef3a9e1af121d226fbbf144826dc2035d2


## Integración local autorizada — RELEASE 665

Baseline final663 verificado por SHA antes de modificar APP. Se ha instalado el candidato sin cambios adicionales. La sección desde `periodo337` conserva exactamente el contenido de663, incluidos labels y cuarto argumento del encargo. El baseline sintético de comparación queda en `fixtures/prioridades_665_baseline.js`; la prueba independiente ahora es portable dentro de APP.

Fixtures positivos337/308 incorporan `ctx.clientes` canónico como el contexto real app.js;663 reemplaza coherentemente ambos catálogos al cambiar su cliente ficticio. No se han relajado aserciones negativas.

Resultado: 90 grupos PASS = 17 independientes665 +27 helpers/renderer337 +43 serialización/puente663 +3 renderer308. No servidor, clipboard nativo, API ni fuentes privadas. Sigue pendiente QA e integración/publicación gestionadas por raíz.

SHA-256:

- modulos/_prioridades_contexto_337.js: c53489693b3657f947e3ce8675652eb3a2489ae821b722d20d0ba6164fbc80f1
- fixtures/prioridades_665_baseline.js: 92c6605364e8a7ddaf2d415609468ec8a10a333ceed38a85a091095be91f6cbd
- probar_scope_prioridades_665.cjs: 74d43fc7ba719660dfb315b4cdd2abc3b808a7e2b32ba2f3deb7d74c789297c3
- probar_prioridades_contexto_337.cjs: e931b2d80a2a8703177e49034e6b16ddceaf014bd2a1e82bb45206f7cc40cbdf
- pruebas_encargo_metodo_663.cjs: 07f470900915f417f8e1c3a0beede4aabf928f2491feb8b0ac07c86c5af618af
- pruebas_prioridades_metodo_308.cjs: 02158787ea64286facb24f89a8e6814834d5b29bbd43b505280eb5f53d095b2e

Compatibilidad adicional autorizada: fixture622 sustituía clientesVisibles por c1 pero conservaba el catálogo previo. Se sincroniza únicamente su catálogo canónico positivo; las seis aserciones permanecen. 6 grupos622 DOM PASS, total propio 96. Root comunica además 5 Python+5 JS independientes664 PASS contra APP665. SHA622: 089fbab624261e77c35fa3cb399106479a3566e41c5fb060673a10a5dd50cad3
