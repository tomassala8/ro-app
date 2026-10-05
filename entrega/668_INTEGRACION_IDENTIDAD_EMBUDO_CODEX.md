# 668 — propuesta aislada de integridad de eventos

RELEASE del candidato aislado. No integrado en APP, API, manifest privado, runtime ni Git. Sólo fixtures ficticios; ninguna lectura de contactos o ejecución de proveedor.

## Defecto reproducido y corrección

El motor original agrupa identidad por cliente/source/event_id: una misma identidad de evento atribuida a dos clientes produce dos resultados y, con cobertura completa sintética, dos tasas confirmadas de venta, asistencia o cualificación. La prueba `test_baseline_falsa_doble_tasa_y_candidato` ejecuta original y candidato y acredita ambas situaciones; no confunde una reproducción PASS con producto corregido.

El candidato conserva schema1 y añade un preflight global `(source,event_id)` antes de descartar variantes no confirmadas, fechas o clientes malformados. Si hay dos atribuciones de cliente, bloquea el evento en ambos ámbitos y hace desconocida la cobertura afectada. No elimina el grupo ni modifica recomendaciones de un tercer cliente no afectado. Añade únicamente `event_id_ambito_conflictivo`; no crea etapas, ventas ni confirmaciones. Fuentes distintas mantienen namespaces separados.

Una variante con cliente inválido y la misma identidad también impide acreditar la variante aparentemente válida. Este cierre conservador requiere comparar el conjunto de eventos de entrada: no detecta una variante conflictiva que el llamador haya eliminado previamente.

## Compatibilidad real con GHL466

`ghl_embudo_observado_466.py:105` identifica recibidos con hash(SID,'recibido',contacto); línea124 identifica reservas con hash(SID,'cita',cita). El lead incluye SID. IDs locales iguales entre subcuentas distintas no colisionan; recibido y reserva tampoco colisionan aunque sus IDs locales sean iguales. Misma SID atribuida a dos CID sí es conflicto, no dos tenants legítimos. No se cambia466 ni su contrato466.1. Una reserva futura sólo conserva su creación histórica observada: no confirma asistencia, cualificación o venta.

## Integración futura: cambios necesarios, no aplicados

1. Sustituir motor sólo tras revisar baseline y SHA candidato.
2. `crm_embudo_api_467.py:22` debe admitir la única nueva incidencia en `INCIDENCIAS_MOTOR`; el validador estricto de línea109 actualmente la rechaza si aparece. Sin incidencia, salidas anteriores son idénticas.
3. Línea146 de467 ancla SHA del motor y adaptador. El cambio del motor invalida la dependencia del manifest470 aunque los agregados sean byteidénticos. Crear depósito nuevo privado y manifest/pins nuevos mediante preparación revisada; nunca modificar depósitos existentes ni sólo cambiar pins para saltar la integridad. No se han recalculado datos reales.
4. No cambia620/621 ni se amplían etapas públicas permitidas. La revisión669 coordina preparación/allowlist por separado.

## Pruebas y trazabilidad

45 PASS: 8 integridad653, 14 motor original, 17 adaptador466, 6 nuevas cadena466→motor. Las nuevas cubren SID distintos con mismos IDs locales, SID único atribuido a dos CID, namespace por etapa, tercer cliente intacto, salida agregada sin IDs privados y reserva futura sin asistencia. Fuentes originales y adaptador copiado comprobados por SHA.

Comando portable desde este directorio:

`python3 -m unittest probar_namespaces_668 probar_integridad_653_668 probar_embudo_eventos probar_ghl_embudo_observado_466 -q`

Motor original: `656c5ce7d91d8d95dce385b25f41ae734e910dd8568c80d86b3a4458cce5a3f9`.
Motor candidato: `fa0186a9c7f8122c9eb0efa281d6999f4e777305c449e14af6d18b5949777e2d`.
Adaptador copiado sin cambios: `bc7791e800257929690313643573065df79bd867c4e8b9a31355a39211ea87a2`.
`manifest_668.json` contiene hashes de todos los archivos; `candidato_668.diff` contiene el único cambio de producto propuesto. Carpeta baseline permite reproducciones sin depender del checkout APP.

Límite: no se ha certificado integridad global del embudo ni exhaustividad de proveedores; esto cierra una identidad conflictiva concreta en el motor puro. APP sigue sin esta corrección hasta integración autorizada.

## Integración local autorizada posterior

Raíz autorizó copiar el motor a APP después de verificar SHA baseline656c5… idéntico. Integración realizada y 45 pruebas PASS desde APP. Añadidos baselinefixture_embudo_668.py (original congelado), probar_integridad_653_668.py (8 contratos before/after) y probar_namespaces_668.py (6 cadena466). Ambas pruebas portables usan únicamente vecinos APP, sin rutas R ni lecturas privadas. Regresiones originales14+17 intactas.

- `embudo_eventos.py`: `fa0186a9c7f8122c9eb0efa281d6999f4e777305c449e14af6d18b5949777e2d`.
- `baselinefixture_embudo_668.py`: `656c5ce7d91d8d95dce385b25f41ae734e910dd8568c80d86b3a4458cce5a3f9`.
- `probar_integridad_653_668.py`: `7a81c253a2f1d9fa6f7b76a6e9b6318d5e7a5648578fedded08182182048619f`.
- `probar_namespaces_668.py`: `95fc468b0ccca709ceefbb618b473f188c3deee1e1555b9949eed8b7cf6319e9`.

No se modificaron adaptador466, API467, sus pruebas, pins, launcher ni runtime. Raíz coordina allowlist467 y manifest/pins nuevos; hasta completar esa secuencia el snapshot anterior puede rechazarse por su ancla de motor, sin intentar salvarla ni omitir integridad. El estado de RELEASE aislado del inicio queda actualizado por esta integración local autorizada.
