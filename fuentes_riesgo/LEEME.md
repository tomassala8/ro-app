# Riesgo de baja: el semáforo del cliente en tres ejes (4-oct-2026)

Petición de Tomás: que el semáforo del cliente distinga **resultados**, **silencio** y **quejas**, para que los
accounts detecten las bajas con precisión. Después añadió **si el cliente asiste a las reuniones**: entra en el eje de
silencio, que en pantalla se llama «Relación» (contesta, viene y está cálido).

**La idea que manda (Tomás, 4-oct):** los accounts ponen verde porque en la reunión el cliente no dice nada malo,
pero no está recibiendo resultados; muchos se callan y luego lo sueltan de golpe. Por eso los resultados se miden
con datos y nunca con el tono de la reunión, y la relación va aparte. Si el semáforo del lunes está en verde y los
resultados medidos en ámbar o rojo, la ficha lo dice («falso verde»). Sin resultados en rojo, el riesgo sale alto
aunque el cliente esté contento (salvo en los primeros 60 días). Buenos resultados con un cliente que se queja, o malos resultados con un
cliente que responde contento, son casos distintos y piden cosas distintas.

## Qué hace

`riesgo_baja.py` (sin red, sin IA) calcula cada eje en verde, ámbar, rojo o gris (sin dato), los combina en un
**patrón** con nombre y un **nivel de riesgo de baja** (bajo, vigilar, alto, crítico), y apunta a la ficha del cerebro
`fuentes_consejos/cerebros/riesgo_baja.json` que explica qué significa y qué hacer hoy.

| Eje | Verde | Ámbar | Rojo |
|---|---|---|---|
| Resultados | leads o citas ≥ 90 % del objetivo y coste por lead ≤ objetivo | 60-90 %, o coste hasta 1,3 × | < 60 %, coste > 1,3 ×, o gasta sin ningún lead en 14 días |
| Silencio («Relación») | contesta, viene y está cálido | 7-13 días sin responder a nuestro último correo; no se presentó a 1 reunión en 30 días o la canceló sin reagendar; 2 reuniones sin constancia de celebrarse; o frío en la reunión 1 de las últimas 4 semanas | 14 días o más; 30 días sin ninguna respuesta suya; 2 reuniones en 30 días sin presentarse o canceladas sin reagendar; o frío 2 de las últimas 4 semanas |
| Quejas | ninguna en 30 días | se quejó en los últimos 30 días (ya cerrada) | queja abierta, o habla de baja, pausa o contrato |

- Resultados sin objetivo cargado: usa la salud del panel (provisional). En los primeros 60 días no pone rojo.
- Silencio: cuenta como respuesta un correo suyo (también los que esperan respuesta nuestra), una llamada contestada o
  una reunión. Con reunión agendada, el rojo baja a ámbar, salvo que haya faltado a alguna.
- Asistencia: de la agenda (`data/agenda/agenda.json`, últimos 30 días): «noshow» en Bookings o GoHighLevel = no
  vino; «showed», grabación de Zoom pegada o reunión en el historial de Reuniones ese día = vino; lo demás, sin constancia.
  Las reuniones con clientes canceladas van en la lista aparte `canceladas` (no se pintan en la agenda): si después no
  hay otra reunión con ese cliente, cuenta como «canceló sin reagendar», igual que una ausencia.
- Una queja de un cliente activo es P0 (C-D3-10): aunque los números vayan bien, el riesgo sale alto.

| Patrón | Nivel | Ficha |
|---|---|---|
| Los tres mal | crítico | `rb_los_tres_ejes_mal` |
| Se quejó y se ha callado | crítico | `rb_queja_y_silencio` |
| Sin resultados y se queja | alto (crítico con dos rojos) | `rb_sin_resultados_y_queja` |
| Sin resultados y no contesta | alto (crítico con dos rojos) | `rb_sin_resultados_y_silencio` |
| Buenos resultados y se queja | alto (vigilar si la queja ya se cerró) | `rb_queja_con_resultados` |
| Buenos resultados y no contesta | vigilar (alto con 14 días) | `rb_silencio_con_resultados` |
| Sin resultados pero contento («falso verde») | alto con resultados en rojo; vigilar en ámbar o en arranque | `rb_sin_resultados_pero_contento` |
| Todo bien | bajo | `rb_sano_mantener` |
| Faltan datos | vigilar | `rb_sin_datos_para_juzgar` |

Si el cliente habla de baja o pausa, crítico siempre. Si el semáforo del lunes dice verde y los ejes dicen alto o
crítico (o al revés), la fila lo marca como discrepancia (`rb_semaforo_lunes_contradice`). Por account: cuántos
clientes en riesgo alto o crítico, con la escala de la D-41 (≤ 2 bien · 3-4 vigilar · ≥ 5 crítico,
`rb_cartera_en_riesgo_de_baja`).

**Umbrales firmados por Tomás el 4-oct-2026, todos los de la tabla** (`FIRMADO = True`). La cartera usa la escala de
la D-41. Están en `UMBRALES`, arriba del fichero.

## De dónde sale cada señal

| Señal | Hoy | Qué falta |
|---|---|---|
| Resultados | objetivo de la ficha + Meta (leads, coste) + GoHighLevel (citas); si no, salud del panel. Con resultados en ámbar o rojo, la causa probable sale del veredicto del embudo (`data/diagnosticos/diagnosticos.json`, PR #3: leads malos, despacho que no atiende, no vienen…) | nada para empezar; cuantos más objetivos cargados, mejor |
| Nuestro último correo | `desk.ult_correo_saliente` (panel) | — |
| Su última respuesta | correos suyos abiertos en la Bandeja, llamadas contestadas (Zadarma), reuniones | **su último correo en tickets ya cerrados**: `desk.ult_correo_entrante`. Sale de Zoho Desk (`customerResponseTime` del ticket más reciente de la cuenta, cerrados incluidos). Mientras falte, el eje sale con confianza «parcial» |
| Calidez en la reunión | el account la marca cada lunes en el semáforo: cálido, normal o frío (`vista_previa.tono`) | leerla de las actas de Fathom con IA, como propuesta para que el account la confirme |
| Asistencia a reuniones | agenda: estado de la cita en Zoho Bookings y GoHighLevel, grabaciones de Zoom, historial de Reuniones | las canceladas de GoHighLevel ya llegan (lista `canceladas`); las de Bookings, solo si el lector `zbookings.py` (fuera del repo) las deja pasar. La agenda mira 30 días atrás desde el 4-oct. Las citas del calendario de Zoho CRM no traen si el cliente vino |
| Quejas | asunto del correo (expresión del panel), incidencias con queja, rojo a mano en ClickUp, y la casilla **«Se ha quejado esta semana»** del semáforo del lunes | el texto del correo (no solo el asunto), los resúmenes de Fathom y WhatsApp (W6, desde el 16-oct) |

## En la app

- **Ficha del cliente**, junto al semáforo del lunes: «Riesgo de baja» con su nivel, los tres chips (Resultados,
  Relación, Quejas), la lectura de una línea, los motivos y «Qué significa y qué hago» (abre la ficha del cerebro).
- **Semáforo del lunes**: nueva casilla «Se ha quejado esta semana» y «En la reunión o la llamada estuvo: cálido,
  normal o frío». El color pasa a ser la lectura de la relación; los resultados los mide la app. Viaja en la misma acción `semaforo_semanal`
  (`vista_previa.queja` y `vista_previa.tono`), la leen `objetivos.py` y `objetivos_comun.js`.
- **Copiloto**: `ia.cliente_para_borrador` lleva el bloque `riesgo_baja` para que la IA lo tenga en cuenta.
- Fichero `data/riesgo/riesgo_baja.json`, dado de alta en `reglas_permisos.json` (ficha, Mi día, En rojo; no
  administración). Cada fila lleva `cliente_id` y cada cartera `persona_id`: el servidor recorta.
- Tubería: paso `riesgo_baja` en `despliegue/pasos.json`, tras la verdad.

## Comandos

```
python3 fuentes_riesgo/riesgo_baja.py                 # escribe data/riesgo/riesgo_baja.json
python3 fuentes_riesgo/riesgo_baja.py --cliente gac   # un cliente, sin escribir
python3 fuentes_riesgo/probar_riesgo.py               # pruebas con clientes inventados
python3 fuentes_consejos/cerebros/probar_cerebros.py  # tras tocar el cerebro riesgo_baja
```
