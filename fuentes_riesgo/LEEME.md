# Riesgo de baja: el semáforo del cliente en tres ejes (4-oct-2026)

Petición de Tomás: que el semáforo del cliente distinga **resultados**, **silencio** y **quejas**, para que los
accounts detecten las bajas con precisión. Buenos resultados con un cliente que se queja, o malos resultados con un
cliente que responde contento, son casos distintos y piden cosas distintas.

## Qué hace

`riesgo_baja.py` (sin red, sin IA) calcula cada eje en verde, ámbar, rojo o gris (sin dato), los combina en un
**patrón** con nombre y un **nivel de riesgo de baja** (bajo, vigilar, alto, crítico), y apunta a la ficha del cerebro
`fuentes_consejos/cerebros/riesgo_baja.json` que explica qué significa y qué hacer hoy.

| Eje | Verde | Ámbar | Rojo |
|---|---|---|---|
| Resultados | leads o citas ≥ 90 % del objetivo y coste por lead ≤ objetivo | 60-90 %, o coste hasta 1,3 × | < 60 %, coste > 1,3 ×, o gasta sin ningún lead en 14 días |
| Silencio | contesta | 7-13 días sin responder a nuestro último correo | 14 días o más; o 30 días sin ninguna respuesta suya |
| Quejas | ninguna en 30 días | se quejó en los últimos 30 días (ya cerrada) | queja abierta, o habla de baja, pausa o contrato |

- Resultados sin objetivo cargado: usa la salud del panel (provisional). En los primeros 60 días no pone rojo.
- Silencio: cuenta como respuesta un correo suyo (también los que esperan respuesta nuestra), una llamada contestada o
  una reunión. Con reunión agendada, el rojo baja a ámbar.
- Una queja de un cliente activo es P0 (C-D3-10): aunque los números vayan bien, el riesgo sale alto.

| Patrón | Nivel | Ficha |
|---|---|---|
| Los tres mal | crítico | `rb_los_tres_ejes_mal` |
| Se quejó y se ha callado | crítico | `rb_queja_y_silencio` |
| Sin resultados y se queja | alto (crítico con dos rojos) | `rb_sin_resultados_y_queja` |
| Sin resultados y no contesta | alto (crítico con dos rojos) | `rb_sin_resultados_y_silencio` |
| Buenos resultados y se queja | alto (vigilar si la queja ya se cerró) | `rb_queja_con_resultados` |
| Buenos resultados y no contesta | vigilar (alto con 14 días) | `rb_silencio_con_resultados` |
| Sin resultados pero contento | vigilar | `rb_sin_resultados_pero_contento` |
| Todo bien | bajo | `rb_sano_mantener` |
| Faltan datos | vigilar | `rb_sin_datos_para_juzgar` |

Si el cliente habla de baja o pausa, crítico siempre. Si el semáforo del lunes dice verde y los ejes dicen alto o
crítico (o al revés), la fila lo marca como discrepancia (`rb_semaforo_lunes_contradice`). Por account: cuántos
clientes en riesgo alto o crítico, con la escala de la D-41 (≤ 2 bien · 3-4 vigilar · ≥ 5 crítico,
`rb_cartera_en_riesgo_de_baja`).

**Los umbrales son una propuesta** (están todos en `UMBRALES`, arriba del fichero). `FIRMADO = True` cuando Tomás los firme.

## De dónde sale cada señal

| Señal | Hoy | Qué falta |
|---|---|---|
| Resultados | objetivo de la ficha + Meta (leads, coste) + GoHighLevel (citas); si no, salud del panel | nada para empezar; cuantos más objetivos cargados, mejor |
| Nuestro último correo | `desk.ult_correo_saliente` (panel) | — |
| Su última respuesta | correos suyos abiertos en la Bandeja, llamadas contestadas (Zadarma), reuniones | **su último correo en tickets ya cerrados**: `desk.ult_correo_entrante`. Sale de Zoho Desk (`customerResponseTime` del ticket más reciente de la cuenta, cerrados incluidos). Mientras falte, el eje sale con confianza «parcial» |
| Quejas | asunto del correo (expresión del panel), incidencias con queja, rojo a mano en ClickUp, y la casilla **«Se ha quejado esta semana»** del semáforo del lunes | el texto del correo (no solo el asunto), los resúmenes de Fathom y WhatsApp (W6, desde el 16-oct) |

## En la app

- **Ficha del cliente**, junto al semáforo del lunes: «Riesgo de baja» con su nivel, los tres chips (Resultados,
  Respuesta, Quejas), la lectura de una línea, los motivos y «Qué significa y qué hago» (abre la ficha del cerebro).
- **Semáforo del lunes**: nueva casilla «Se ha quejado esta semana». Viaja en la misma acción `semaforo_semanal`
  (`vista_previa.queja`), la leen `objetivos.py` y `objetivos_comun.js`.
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
