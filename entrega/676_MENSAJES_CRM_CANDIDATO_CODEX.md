# 676 · Mensajes CRM: candidato aislado

RELEASE de propuesta; no se ha integrado APP, ejecutado productor, consultado proveedor ni recalculado caché.

## Evidencia y corrección

El lector anterior aceptaba cualquier entrada del historial como `respondio=True`, incluso anterior a la creación del lead. Contaba salidas y llamadas históricas en sus canales y admitía registros sin estado de ejecución. Las pruebas reproducen esos casos con transporte ficticio del lector real extraído mediante AST.

El candidato sólo atribuye registros con binding explícito del contacto y fecha dentro de creación del lead → corte original. Preflight global de `messageID` dentro de cada subcuenta leída: las variantes incompatibles de identidad/contacto/fecha/tipo/dirección/origen/estado invalidan todas sus variantes antes de filtros. Replays idénticos se deduplican; campos API ajenos (cuerpo, adjuntos, extras) no causan conflicto. Identificadores numéricos opacos son válidos. El mismo ID en otra subcuenta no se mezcla.

Se mantienen lecturas existentes y límites de 150 leads × 2 conversaciones × 100 mensajes. Una respuesta que excede el límite conserva mínimos positivos de los primeros 100 y vuelve desconocidos los totales certificados. No hay nuevas consultas ni persistencia de mensajes crudos.

Una entrada textual observada no acredita respuesta humana, lectura, gestión, asistencia o venta. `respondio` sólo puede ser true (entrada positiva) o null; no se fabrica false. Entradas con origen automático conocido y llamadas no se presentan como respuesta textual. Salidas queued/pending/scheduled/draft no son contactos ejecutados. Salidas con estado desconocido no acreditan envío ni intento; se conserva separadamente el mínimo de registros con estado desconocido. Los contadores legacy `*_env` representan registros de salida con estado conocido, incluidos fallidos, no entrega exitosa.

Errores, fechas inválidas/futuras, bindings incompatibles y conflictos impiden certificar ceros. Mínimos positivos independientes sobreviven como metadatos separados; no se suman para fingir un total completo. Los pares enviados/fallidos agregan sólo filas tipadas del mismo corte y usan cobertura n/N. Sus faltantes no se convierten en cero. Guardas de umbral y recomendaciones ya admiten null sin TypeError. La ausencia automática se limita a registros observados en la copia parcial, no a un fallo actual probado del flujo.

`iso_ms` rechaza bool, NaN, infinito, ISO sin zona, offsets inválidos, epoch fraccionario/negativo/no representable. Preserva epoch cero y fechas con zona válidas. No adivina zona de proveedor.

## Contrato público 677

El `fl` real añade `creado_iso676` UTC aware y `respuesta_medicion676`, sólo si existe entrada positiva tipada y el corte original coincide al minuto Madrid con `hora_vivo`. Segundos del corte se conservan; la hora fuente no se rejuvenece. Caché legacy o incoherente no recibe descriptor inventado.

Descriptor reducido:

- version: 676.1; fuente: ghl_conversacion; estado: observado_parcial; completa: false.
- desde_ms, hasta_ms, ultima_entrada_ms; entradas_observadas entero positivo.
- respuesta_humana_confirmada: null; resultado_comercial_confirmado: null.
- cliente_id, sub_id, ref, exactamente ligados a la fila pública.

No incorpora ID de mensaje/contacto, cuerpos, direcciones, origen libre ni diagnósticos privados. El getter sintético `publico_fixture676()` en la prueba crea una fila usando `leer_subcuenta` y el AST de la asignación `fl` reales, para el puente 677 sin descriptor simulado. Devuelve `(fl, fuentes, hoy)`.

## Verificación

32 métodos PASS: antes/después históricos, ventana, replay/conflicto global entre contactos, tercer lead independiente, namespace entre subcuentas, binding malformado, exceso de límite, tipos contenedor, espacios, estados desconocidos, errores, gateway temporal, pares agregados, condiciones reales de main, exportación pública real y coherencia al minuto. Sólo AST y transporte falso; sin main ni imports con efectos. AST de timestamp_mensaje/resumir_intentos/intentos_medidos672 sigue idéntico al baseline.

Baseline SHA256: `351e948f005f93a0092a634b94118e0584e586595d21fd8aeb7c0a11dedf6724`.
Candidato SHA256: `f93f924a4bfd4730f2f67086e871c93dccb1fc7a0943dfd607e27bfded8ae2c0`.
Prueba SHA256: `1a464548d4596557c86b70545aeb3d03ea9d12e8fcc3b47d03b6f80ab6fc0443`.

Ejecutar `python3 -B probar_mensajes_crm_676.py` desde esta carpeta. `676_mensajes.patch` es diff reproducible contra el baseline; `manifest.json` identifica fuente y alcance.

## Límites e integración pendiente

Requiere revisión independiente678 y autorización de raíz antes de copiar APP. Los snapshots existentes no cambian. La batería672 futura necesita incluir funciones nuevas en su loader AST y fixtures con contacto/estado e IDs distintos por evento; no deben relajarse sus aserciones temporales. Persisten fuera de esta propuesta los agregados legacy de citas/ventas, clasificación general de salud y otras recomendaciones sin contrato de cohortes. No se ha probado UI ni cobertura exhaustiva del proveedor; la captura limitada siempre es parcial. Los nombres históricos humano_min/auto_min siguen contrato existente de intento clasificado por origen, no certifican participación humana.

## Correctivo678 y paquete portable (676.2)

Reproducciones confirmadas antes del correctivo: messageID dict/list daba TypeError en membership del conjunto global; contactID list fallaba al buscar citas. Ahora los IDs no string se mantienen desconocidos, sin consultar conversación con identidad inválida. También se filtra el set de contactos de citas por tipo string. No se relaja identidad opaca válida numérica.

Entrada positiva exige estado explícito en la lista conservadora received/delivered/read, normalizada case/espacios. Unknown, ausente, failed, bounced, undelivered y pendientes no acreditan entrada recibida. Es una regla defensiva de la proyección, no una certificación de exhaustividad de estados API ni prueba de respuesta humana.

`sin_tocar_medicion` nuevo requiere versión676.1, binding cliente_id/sub_id, fuente ghl_conversacion, corte hasta_ms, hora_fuente original coherente al minuto y intervalo de cohorte [desde_ms, cohorte_hasta_ms) cerrado a medianoche Madrid. Corte de conversaciones y fin de cohorte permanecen separados. Sólo se publica si al menos una fila tiene observación tipada válida; legacy o fuente incoherente devuelve null. No acredita ausencia de entradas del proveedor ni servicio actual incumplido.

Portable_APP contiene candidato espejo en fuentes_crm/generar_crm.py y cuatro archivos destinados a futura copia autorizada por raíz: probar_mensajes_crm_676.py, fixture_mensajes_crm_676.py (sólo funciones/constantes necesarias por AST), probar_intentos_crm_672.py y fixture_intentos_crm_672.py. La prueba676 apunta a fuente APP relativa, sin ruta de usuario. La672 conserva sus13 métodos/aserciones y sólo amplía dependencias del loader, JSON, bindings/status válidos del transporte y IDs de eventos únicos según timestamp. Ambas ejecutadas contra el candidato:32+13 PASS. Ningún fichero APP fue sustituido.

`publico_fixture676` ejecuta también la condición real posterior que añade cliente_id a fl; el descriptor bound no se simula. La colección pública sigue excluyendo IDs de mensajes/contactos y cuerpos.

SHA y hashes de cada archivo portable están en manifest.json. El diff ya incluye estos correctivos. Revisión678 y puente677 todavía deben cerrar aceptación independiente; no hay afirmación de UI ni ejecución real.

Gateway adicional: contexto de contacto inválido (numérico, bool, null, list/dict) no conserva mínimos positivos aunque los bindings coincidan; diagnósticos se conservan y métricas quedan desconocidas. La publicación reducida también exige contacto opaco válido antes de añadir descriptor. Nueva prueba realpura negativa; 32+13 PASS.

## Correctivo676.3 integrado en fuente, sin recalcular snapshots

Tras copia676.2 autorizada por raíz, revisión678 detectó conv.id con segmentos ../other, a/b o URL. Podía construir una ruta de mensajes distinta del segmento opaco esperado; no se ha demostrado SSRF de host ni se hizo ninguna red real. Correctivo autorizado exclusivamente productor/prueba676: cada ID de conversación debe cumplir [A-Za-z0-9_-]{1,160} antes de construir la ruta. El transporte falso prueba ausencia de consultas /messages para valores maliciosos, contenedores y longitud161, y conserva '123' válido.

Preflight y normalizador también rechazan conversacion_id suministrado no opaco. Packet puro con conversacion_id:null sólo se admite si trae binding opaco explícito contactId/contact_id del mensaje; raw conversationId, si existe, debe ser opaco y coincidir con el packet. Este permiso de normalización no genera rutas ni amplía acceso. Los conflictos invalidan todas las variantes del ID.

34 métodos676 +13reg672 +12cobertura CRM PASS en APP actual. Sólo AST/fake transporte, sin main, productor vivo, HTTP, credenciales, datos actuales, reinicio ni caches nuevos. Candidate/portableR sincronizados con APP para revisión; manifest contiene SHA exacto. Documento mantiene el historial de releases anteriores, no implica sus hashes continúen vigentes ni prueba de runtime/UI.
