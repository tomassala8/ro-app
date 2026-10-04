# Cerebros de área (4-oct-2026)

Doce cerebros, uno por área, con **fichas de situación**: lo que le pasa a alguien del equipo y qué hacer.
Sirven para aconsejar al equipo gastando muy poca IA.

## Cómo funciona

1. Algo pasa en la app: salta una alerta, un consejo o un indicador, o alguien escribe su problema con sus palabras.
2. `buscar.py` localiza la ficha **sin IA**: por disparador (tipo de consejo, alerta, indicador, regla) o por texto libre.
3. Sin clave de IA, la ficha se enseña tal cual. Ya sirve: diagnóstico en orden, causas, solución, guiones y cuándo escalar.
4. Con clave, la IA recibe solo `para_ia(ficha)` (≈ 500-1.500 tokens) más los datos del cliente, y adapta. No razona desde cero.

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
```

## Editar un cerebro

- Cambia el `<area>.json`, sube `_meta.version` y pon la fuente con fichero y línea.
- Si es criterio sin documento, `{"fichero": "criterio", "autor": "RO", "nota": "sin fuente"}`.
- Nada de correos, teléfonos, claves ni datos de personas. Las pruebas lo vigilan.
- `_meta.pendientes_tomas` recoge lo que solo Tomás puede decidir.
