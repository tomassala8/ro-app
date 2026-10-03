# _ESTADO_avisos · Canales de avisos y avisos programados (3-oct-2026)

Encargos de Tomás: «en ClickUp tenemos los canales de avisos, grupos y alertas automáticas: que eso también exista» (N15, 2-oct) y «que en el chat de la app estén todas las automatizaciones» (3-oct). Inventario de lo que había: `../54_AUTOMATIZACIONES_INVENTARIO.md`. Contrato técnico en LEEME («N15» y «Avisos automáticos»).

## Estado: hecho · nada sale de la app
Los avisos se publican en los canales de la app y en la campana. No se escribe en ClickUp ni en ninguna herramienta. El reloj de los avisos programados corre dentro de `servir.py` (cada 2 min; `RO_AVISOS_SIN_BUCLE` lo apaga).

## Qué hay
| Pieza | Fichero | Qué hace |
|---|---|---|
| Canales y grupos | `avisos.py` | Canales de avisos por departamento (#avisos-web … #avisos-dirección) llenos con el motor de alertas y eventos del sistema; grupos por equipo, por cliente y propios; campana con no leídos, menciones y resumen diario a la hora de cada persona. «Lo tengo» y «Resuelta» escriben la misma acción que Alertas. Permisos: cada uno ve lo suyo; importes, contraseñas, correos, teléfonos y sueldos fuera |
| Avisos programados | `avisos_programados.py` + `data/avisos_programados/reglas.json` | **11 reglas activas:** horas de ayer, semáforo del lunes, cómo va el semáforo, informe mensual, cierre de facturación a Sofía, resumen de publicidad, resumen semanal a dirección, tareas vencidas, arranque de clientes nuevos, aviso del cierre semanal y factura del equipo. Clave única por regla, persona y día (nunca repite); solo avisa si el dato dice que falta; escalado si nadie pulsa «Ya lo he hecho». `no_se_hace_aun` = lo del inventario que aún no puede hacer y por qué |
| Botones en mensajes | `datos.botones` → `chat_equipo.js` | Hasta 5 botones por mensaje (ir a una pantalla o a un enlace) |
| Pantalla | `modulos/ajustes_avisos.js` (`#/avisos-automaticos`, grupo Sistema) | Todos ven lo que les llega; las jefas editan lo de su departamento (y Mili y Tomás todo), con rastro; «Ver cómo quedaría»; inventario para Mili y Tomás |
| Chat del equipo | `modulos/chat_equipo.js` | Ver `_ESTADO_chat_equipo.md` |

## Pruebas
- `python3 pruebas_seguridad.py` → bloque `avisos_automaticos` (37 casos con relojes fijados).
- Sin servidor: `python3 avisos_programados.py --simular --reloj 2026-10-05T09:00`.

## Pendiente
1. Lo que conviene apagar en las herramientas de origen (ClickUp, GoHighLevel…) queda como recomendación en cada regla (`apagar_en_origen`): lo decide Tomás; nada se ha apagado.
2. Las automatizaciones de `no_se_hace_aun` necesitan datos que la app todavía no tiene.
