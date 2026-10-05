## Actualización666
Gap target/catalog corregido e integrado por665; este informe recoge la reproducción previa. Ver666 y las pruebas APP portables actuales.

# 664 · Verificación independiente del puente Método → encargo

Corte: 4 de octubre de 2026. Sólo fixtures sintéticos; ningún proveedor, HTTP, dato privado, portapapeles real ni base principal. No se modificó APP.

## Resultado

5 pruebas Python y 5 casos JavaScript PASS. La prueba Python ejecuta `cerebro_api.enganchar`, su lectura de fuentes, `cerebro_operativo.generar`, responsables actuales, filtro308 y serializador337 reales. Sólo se sustituye `M.leer` por evidencia sintética; los módulos del servidor son documentos en memoria, no un motor simulado. El JavaScript ejecuta además la función `copiarBloque` extraída del consumidor real.

La cadena conserva la celebración declarada del 1 de octubre y la próxima revisión calculada del 16 de octubre, diferenciándolas del día de consulta (4 de octubre). Conserva ejecutor operativo Trafficker y comprobador Account, sin imprimir el ID del responsable. La revisión calculada no es una cita agendada; la fuente local no acredita participación externa ni responsable histórico.

Negativas: baja del responsable antes de respuesta elimina la recomendación; celebración retirada elimina ambas fechas y su evidencia; ACT revocado elimina la recomendación. `hoyActual` ausente o distinto suprime la nueva sección Método. Esto último no invalida por sí mismo las evidencias genéricas antiguas: corresponde al ámbito vigente del consumidor impedir copiar un contexto obsoleto.

Se introdujeron campos sintéticos de precio y texto privado en el origen: no sobreviven a la respuesta ni al encargo. El recorte del API opera sobre entradas; el DTO Método de salida se construye mediante whitelist308, no mediante un recorte monetario adicional de toda la recomendación. Esta prueba no certifica todos los canales de privacidad.

## Límite reproducible pendiente (337 / candidato665 separado)

La firma de `ambitoPrioridades337` no incluye el responsable operativo destinatario. Si éste pasa a baja después de recibir la recomendación, permaneciendo `ctx.vigente()` verdadero y el actor autorizado, la firma no cambia y el consumidor actual permite copiar el texto anterior. El quinto caso JS reproduce esta laguna; PASS significa reproducción, no corrección. No se corrigió en662/663 ni se declara cerrado aquí.

La revocación de permiso o epoch antes de copiar bloquea la llamada al portapapeles. Si ocurre durante un await de copia ya iniciado, se suprime el estado de éxito posterior; no puede deshacerse una copia que ya comenzó. Root debe verificar la incorporación del ámbito665 por separado, la vigencia justo antes de copiar y la invalidación del textarea antiguo.

## Contratos que deben mantenerse

- Fecha de celebración original y fuente admitida; nunca agenda/asistencia/venta inferidas.
- Revisión = última celebración +15 días, explícitamente calculada y no agendada.
- Papeles actuales del encargo separados de autoría o participación históricas.
- El criterio genérico que menciona programación no puede convertir una programación en celebración confirmada.
- Ningún cierre de cobertura exhaustiva, ausencia de reuniones o capacidad contractual deriva de estas pruebas.

## Ejecución portable

`python3 -B probar_puente_metodo_664.py` requiere Node en PATH o variable `RO_NODE` explícita. `node probar_copia_vigente_664.cjs`. Ambos localizan APP respecto al depósito R; no contienen rutas personales de Node ni leen fuentes privadas. Son fixtures de la cadena actual, no una prueba de navegador ni certificación integral de permisos.

## Fuentes verificadas

- consejo_metodo_308.py: SHA256 `1d041ec0d16191d10fba9cc2acca28980f138ca2ddc05e36fbc0a43ba3ea2a00` (662).
- modulos/_prioridades_contexto_337.js: SHA256 `92c6605364e8a7ddaf2d415609468ec8a10a333ceed38a85a091095be91f6cbd` (663, etiquetas finales).

Las expectativas se actualizaron exclusivamente a «Comprobador: Account» y «Ejecutor operativo: Trafficker». Permanecen las comprobaciones de fechas, separación de agenda, ausencia de IDs/texto privado y revocación.
