# 620 · Reservas observadas como evidencia adicional

4 octubre 2026 · SOURCE_RELEASE puro. Integración y autorización621 pendientes de su propietario; no hay API/motor/UI editados aquí.

## Interfaz

`enriquecer_reservas620(resultado,lecturas,hoy,ahora=None)` en `30_APP_PROTOTIPO/cerebro_reservas_620.py`. Lecturas es dictCID→DTO público de listar467. Hoy YYYY-MM-DD en Madrid; ahora ISO aware explícito (621 aporta UTC). Sin ahora no se acredita actualidad ni se enriquece. Función sin IO/HTTP/import de lectores, y copia profunda del resultado: no modifica entradas.

Sólo recomendación existente `regla_id='crm_citas_sin_estado'`. Añade evidencia[] estándar {fuente:'crm_embudo_observado',fecha:hora_fuente,periodo:[recepción desde,hasta],cobertura:'registros_observados_no_exhaustivos',vigencia:'actual',texto}. A criterio_entrega añade una frase fija: reservas creadas no acreditan asistencia/venta/resultado y no cierran citas futuras. No reemite alertas ni cambia motivo/acción/prioridad/Score/owner, no calcula tasas, suma universos o identifica leads/reservas particulares. No usa asignado ni creator como actor de cita.

## Validación primaria467

Top whitelist exacta467.1/copia_observada/cliente_id exacto/medicion/diagnosticos/hora_fuente/desde/hasta/corte. Medición es la forma pública de `_medicion`467 (no agregado privado466), versión467.1, UTC, límites fijos, ventanas recepción/eventos coincidentes con top y observado_hasta igual al corte. Ambos universos se validan por separado; eventos del período pueden ser más que reservas en cohorte y nunca se mezclan en el texto.

Cohorte sólo parcial cuando recibidos>0, desconocido cuando0. Conteos safeint>=0, cita<=recibidos; etapas parciales cuando positivas y desconocidas cuando0, sin cualificación/contacto/respuesta/asistencia/venta instrumentalizados. Diagnósticos sólo códigos conocidos/conteos; fuente_reporta_errores positivo descarta el enriquecimiento. No se acepta texto/IDs libres ni campos adicionales.

Todas las fechas/hora son aware estrictas, calendario/offset≤14:00 válidos, fuente<=corte<=ahora y desde<=hasta<=corte. Fecha Madrid de ahora debe coincidir con hoy; fecha Madrid de fuente y corte debe tener edad0..2 días, sin rejuvenecerlas. Una hora futura del mismo día se rechaza. No se impone frescura a inicio de cohorte30d: se explicita la ventana.

Sin configuración/error/viejo/ausente/malformado devuelve contenido igual. Recibidos0/cita0 no añade observación falsa. Con recibidos positivos y cita0 se explicita desconocimiento de reservas observadas, no «0 reservas» ni ausencia. Citas pueden estar canceladas o agendadas para fecha futura: la cifra registra creación de reserva, nunca asistencia ni validez. Los resultados comerciales siguen pendientes.

Idempotencia del apéndice: reemplaza únicamente nuestra evidencia validada por fuente fija y añade la frase criterio una sola vez. No borra otras evidencias. El caller621 conserva puertas ACT/grants real∩vista y vigencia antes y después de las lecturas: este helper puro no concede permisos ni consulta catálogos.

## Pruebas

`python3 -m unittest probar_cerebro_reservas_620`: **20 PASS**. Incluye apéndice positivo, diferencias cohorte/eventos100 vs3 sin sumar, reservas canceladas/futuras como límite, cero desconocido, ambos0 skip, no reemisión, copia profunda, idempotencia, fechas Madrid/límite2 días/sin reloj/futuro mismo día, fuente>corte, error/viejo, offsets/calendario/naive, counts invalidos/estado completo/etapas no instrumentadas, ventanas divergentes, texto privado/diagnósticos desconocidos. Puente AST ejecuta `_medicion`467 real en fixture sintética y acredita igualdad con el DTO público esperado, sin importar sus lectores ni IO de datos.

Compilación de ambos archivos nuevos PASS. No lectura de candidatos/privados, llamadas, DB real, servidor/runtime, providers, generadores, UI ni cambios del motor. La evidencia será utilizable sólo al integrar621 y revisar su autorización; no se afirma validación actual de resultados del piloto a partir de estos fixtures.

## SHA-256

Helper: `1030ee3115497a441c258e1837e6f99311546ca73a7aaee1cc0305b2bee84d6e`

Pruebas: `b28b552a75f036574201bcea03b2788a6f6568a45a944c7076a2fb83044f1881`
