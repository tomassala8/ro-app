# _ESTADO_sincronia · Sincronía con ClickUp y copia de los cambios (3-oct-2026)

Encargo de Tomás: «que los cambios que hace el equipo en la plataforma impacten en ClickUp, pero también se guarden como copia por si no llegaran; y lo mismo con el chat». Documento completo: `../51_SINCRONIA_Y_CHAT.md`. Contrato técnico en LEEME («Sincronía con ClickUp»).

## Estado: hecho y **en simulación** · no se escribe nada en ClickUp
- `data/sincronia/interruptor.json`: `clickup_real: false`, `chat_puente: "apagado"`, `activado_por: null`.
- Para ClickUp real hacen falta **las tres cosas**: el fichero con `activado_por: "tomas"`, `RO_CLICKUP_REAL=si` y la llave de un **usuario de servicio** de ClickUp (miembro, nunca propietario) en el llavero como `clickup_token_servicio`. Solo Tomás.

## Qué hay
| Pieza | Fichero | Qué hace |
|---|---|---|
| Servidor | `sincronia.py` (enganchado a `servir.py` tras `envios.py`) | Toda acción con herramienta `clickup` deja al momento su cambio en `sinc_cambios` + `sinc_pasos` (imborrables, clave única por acción): esa es **la copia segura** aunque ClickUp no llegue. Estados simulado / pendiente → enviado → confirmado / fallido / conflicto → descartado. La respuesta dice «Hecho en la app · pendiente de ClickUp» |
| Tubería | `despliegue/reconciliar_clickup.py` (paso `reconciliar_clickup`) | Despacha, relee en ClickUp (solo lectura), detecta conflictos, reintenta e informa a diario de lo «sin reflejar» en #avisos-altas |
| Chat | `encolar_chat()` e `importar_chat()` en `sincronia.py`, enganche en `avisos.py`, `data/sincronia/puente_chat.json` | Puente de chat app ↔ ClickUp programado y **apagado** |
| Copia de la base | `despliegue/copia_seguridad.py` (ver LEEME «Vigía y copias») | Copia diaria verificada de `local.db` y `tuberia.db` |
| Pantalla | `modulos/envios.js`, pestañas Correos / ClickUp / Chat (`#/envios/clickup`, `#/envios/chat`) | Estado de cada cambio, reintentar, elegir en un conflicto, «a mano» |

## Pruebas
- `python3 despliegue/reconciliar_clickup.py --prueba-e2e`: 36 casos con ClickUp simulado sobre una copia de la base (también en `despliegue/pruebas_noche.py --solo-solidez`).
- `python3 pruebas_seguridad.py` → bloque `sincronia_clickup`.

## Pendiente
1. Tomás: crear el usuario de servicio de ClickUp y encender.
2. Tomás: decidir fecha de corte del chat de ClickUp y si se enciende el puente (`../51_SINCRONIA_Y_CHAT.md`).
3. Botón «Exportar conversación» para dirección (propuesto en el 51, sin hacer).
