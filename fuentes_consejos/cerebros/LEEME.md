# Cerebros de área (4-oct-2026)

Doce cerebros, uno por área: 477 fichas de situación y 141 principios. Cubren los 55 tipos de consejo y las 45
alertas de la app. Cada ficha compacta para la IA ronda 680 tokens (p90 ≈ 1.080).

Doce cerebros, uno por área, con **fichas de situación**: lo que le pasa a alguien del equipo y qué hacer.
Sirven para aconsejar al equipo gastando muy poca IA.

## Cómo funciona

1. Algo pasa en la app: salta una alerta, un consejo o un indicador, o alguien escribe su problema con sus palabras.
2. `buscar.py` localiza la ficha **sin IA**: por disparador (tipo de consejo, alerta, indicador, regla) o por texto libre.
3. Sin clave de IA, la ficha se enseña tal cual. Ya sirve: diagnóstico en orden, causas, solución, guiones y cuándo escalar.
4. Con clave, la IA recibe solo `para_ia(ficha)` (≈ 500-1.500 tokens) más los datos del cliente, y adapta. No razona desde cero.

## En la app (ia.py)

- Cada consejo de «Qué haría yo hoy aquí» lleva su ficha corta: «Cómo se resuelve» y «Ver la ficha entera».
- El copiloto del account recibe la ficha de cada alerta del cliente (máx. 3, sin guiones).
- «Qué hago si…»: buscador en Mi día y en el Asistente. `GET /api/ia/cerebro?q=` busca y `?id=` abre; no gasta IA.
- Con clave, «Adaptar a este cliente» (`POST /api/ia/cerebro`) pide a la IA (modelo barato) que ajuste ESA ficha.
  Si escribe una cifra que no estaba o algo prohibido, se enseña la ficha tal cual.

## Qué tiene cada ficha

| Campo | Para qué |
|---|---|
| `disparadores` | Ids reales de la app (tipos, alertas, indicadores) y palabras como habla el equipo |
| `sintoma`, `gravedad`, `plazo` | Qué se ve y con qué prisa |
| `diagnostico` | Comprobaciones en orden, de la más probable y barata a la menos; cada una apunta a una causa |
| `causas` | 3-6 causas reales, cómo confirmarlas, solución paso a paso, quién y en qué plazo |
| `acciones_inmediatas` | Lo de hoy, aunque aún no sepas la causa |
| `guiones` | Textos listos (correo, WhatsApp, llamada, reunión) en la voz de RO, con `{huecos}` |
| `que_no_hacer`, `escalar`, `exito` | Errores típicos, a quién subirlo y cómo sabes que está resuelto |
| `fuentes` | Fichero y línea de donde sale cada cifra o regla (ro-equipo, Hormozi-Cole-Gordon, la app) |

Orden de autoridad: decisiones de Tomás > leyes y contratos de RO > SOP internos > Cole Gordon / Hormozi.
Prudencia: no se asesora al cliente en lo fiscal o legal, no se prometen plazos ni resultados, no se tocan precios.

## Reserva

`direccion` y `personas_admin` llevan finanzas, precio y personas. Si la app pasa el `puesto` a `buscar()` o
`por_disparador()`, esas fichas solo salen a sus puestos (y a dirección). La app debe pasar SIEMPRE el puesto de quien
pregunta. Ningún cerebro trae sueldos, valoraciones ni datos personales; las pruebas lo comprueban.

## Comandos

```
python3 fuentes_consejos/cerebros/buscar.py "los leads no vienen a la reunión" --puesto setters --ia
python3 fuentes_consejos/cerebros/buscar.py --alerta crm_sin_tocar
python3 fuentes_consejos/cerebros/construir_indice.py     # tras editar un cerebro
python3 fuentes_consejos/cerebros/probar_cerebros.py      # antes de cada PR
python3 fuentes_consejos/cerebros/probar_en_app.py        # los cerebros dentro de ia.py (sin servidor)
python3 fuentes_consejos/cerebros/pendientes.py           # regenera PENDIENTES_TOMAS.md
```

## Editar un cerebro

- Cambia el `<area>.json`, sube `_meta.version` y pon la fuente con fichero y línea.
- Si es criterio sin documento, `{"fichero": "criterio", "autor": "RO", "nota": "sin fuente"}`.
- Si es una decisión de Tomás sin fichero en un repo, `{"fichero": "decision_tomas_2026-10-04", "autor": "Tomás", "nota": "Respuesta n.º 18: …"}` (sin línea).
- Nada de correos, teléfonos, claves ni datos de personas. Las pruebas lo vigilan.
- `_meta.pendientes_tomas` recoge lo que solo Tomás puede decidir. Resumen en `PENDIENTES_TOMAS.md`.

## Áreas

direccion · operaciones · account · comunicacion · altas · publicidad · crm (con el diagnosticador del embudo de
GoHighLevel, `crm_diagnostico_embudo`) · setters · seo_web · redes_produccion · ventas_ro · personas_admin.
