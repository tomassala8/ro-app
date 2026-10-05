# 615 · Subtotal de informes declarados

4 octubre 2026 · SOURCE_RELEASE. Añadido sólo export `agregarInformesDeclarados615(modelo,ids)` en el helper612; sin editar263/backend/contratos611, ni fuentes/shared tests.

## Contrato

Usa exclusivamente `celdaInformeDeclarado612` y su callback vigente; no lee directamente DTO ni reconstruye actores, autoría o datos Desk. Exige selección de IDs strings canónicos, única, no vacía, contenida en el ámbito vigente original. Copia los IDs al construir el subtotal y revalida antes, durante y después de la suma y en su callback.

Salida: `{valor:'N decl.'|'—',estado:'gris',informes_declarados:n|null,cobertura:{observados:n|null,total:N|null,parcial:true},detalle,vigente}`. El detalle explicita mes del informe≠mes de envío, filas n/N, cobertura parcial y ausencia de verificación/cumplimiento/Score/autor histórico.

Sólo suma safeint≥0 de filas explícitas. Filas ausentes quedan desconocidas: 2+missing devuelve2decl., cobertura1/2; 0 explícito+missing devuelve0decl., cobertura1/2 exclusivamente de esa fila, sin afirmar ausencia de informes del resto; ambas missing devuelven—, cobertura0/2. Una selección vacía no se convierte en0. Duplicados, ID ajeno/inválido, modelo desconocido/revocado o suma overflow devuelven—, sin publicar subtotal que parezca completo.

La vigencia sigue las comprobaciones612 canónicas de ambas identidades, ACT/detalle/clientes/grants y callback epoch/ruta/mes. El caller debe actualizar el estado capturado por su callback, no reemplazar la función de un scope ya proyectado para definir otro ámbito. No hay porcentajes, Score ni suma con Desk; el renderer617 de raíz mantiene las procedencias separadas.

## Pruebas

`node pruebas_informes_agregados_615.cjs`: **20 grupos PASS**. Positivos2+3, explícitos0, missing parcial/completo desconocido, IDs duplicados/malformados/ajenos, maxsafe y overflow, actor/catálogo/roles/ACT/grants/módulo/período revocados, callback obsoleto, copia de selección y revocación durante suma. Funciones reales en VM, sin API/POST/DB.

`node pruebas_informes_declarados_612.cjs`: **31 grupos PASS**; sintaxis ESM del helper PASS. Fuente615 queda liberada para integración617/revisión618 por raíz: no implica QA visual ni verificación de envío.

## SHA-256

Helper612 con añadido615: `d20c178eb95f2b8e3e82c7d9593e12cfd32aaf8b200d5c355e7b2fce29e28243`

Pruebas615: `56efaa6b6952b1275161391e4860674c30060c7a3035ad6810dd6c28afad7181`
