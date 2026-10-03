# _ESTADO_envios · Envíos verificados (3-oct-2026)

Encargo de Tomás: «cualquier correo que se envíe, asegurarnos de que se está enviando bien; que el sistema nunca esté fallando». Documento completo: `../46_ENVIOS_VERIFICADOS.md`. Contrato técnico en LEEME («Envíos verificados»).

## Estado: hecho y **en simulación** · nada sale de la app
- `data/envios/interruptor.json`: `envios_reales: false`, los tres canales (Desk, WhatsApp, GoHighLevel) apagados, `activado_por: null`. Canario apagado.
- Hacen falta **las dos llaves** para enviar de verdad: el fichero con `activado_por: "tomas"` **y** `RO_ENVIOS_REALES=si` en el entorno del servidor y de la tubería. Solo Tomás.

## Qué hay
| Pieza | Fichero | Qué hace |
|---|---|---|
| Servidor | `envios.py` (enganchado a `servir.py`) | Cada envío nace de una acción de la cola; clave única (no se manda dos veces); estados simulado → pendiente → enviado → confirmado / fallido / rebotado, cada paso con su hora e imborrable. Destinatario y remitente los pone el servidor, nunca el navegador |
| Verificador | `despliegue/verificar_envios.py` (paso `verificar_envios` de la tubería) | Relee el hilo en la herramienta (texto y destinatario), rebotes durante 48 h, un solo reintento seguro, avisos a quien lo mandó y a Agus |
| Salud | `despliegue/salud_conexiones.py` → conexión «Envío de correos (Desk)» | Llave de escritura y permiso, departamento, dirección de envío, firmas (9 de 11 el 3-oct: faltan Candela y Facundo), cupo |
| Pantalla | `modulos/envios.js` (`#/envios`, grupo Sistema) | Cola con lo fallido primero, pasos, % confirmados a 7 y 30 días, «Reintentar» (simulado). Tomás, Mili y Agus |

## Pruebas
- `python3 pruebas_seguridad.py` → bloque `envios_verificados`.
- `python3 despliegue/verificar_envios.py --prueba-e2e` (proveedor simulado sobre una copia de la base; también en `despliegue/pruebas_noche.py --solo-solidez`).

## Pendiente
1. Tomás: activar canal por canal y elegir el buzón del canario (`data/envios/_privado/canario.json`, no se sube).
2. Firmas de Candela y Facundo en Desk.
3. Añadir a Agus a #avisos-dirección (hoy recibe la copia en #avisos-altas). Solo Tomás.
