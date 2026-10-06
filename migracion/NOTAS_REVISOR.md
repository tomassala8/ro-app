# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F5.1

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

SIN PANTALLAS (decisión de Tomás, 6-oct 19:02): «vamos a montar pantallas distintas a las que ya teníamos; no avancemos con la parte de pantallas». La noche termina en las rutas (F5.1–F5.9) y luego va directa a F7. No se hace nada de F6.
1. En cuanto leas esto, en `migracion/PROGRESO.md` cambia F6.1, F6.2, F6.3 y F6.4 a `- ⚠ F6.x · HH:MM · fuera de alcance: decisión de Tomás 6-oct 19:02, las pantallas nuevas serán distintas; no se hace`. No instales shadcn, no toques `v2/apps/web` ni la carcasa, no grabes fotos nuevas.
2. «/» lo sigue sirviendo el front de hoy a través de Next, como ahora (`RO_CARCASA` apagado).
3. En F7: contenedores, `render.yaml`, informe y `puerta.sh f7`. Si la puerta f7 pide algo de la carcasa o de pantallas en React, esa parte no aplica: apúntala en `~/RO_MIGRACION/excepciones.txt` con el motivo «F6 fuera de alcance, decisión de Tomás 6-oct» y en el informe.
4. En `INFORME_NOCHE.md`, una sección «Para las pantallas nuevas»: lista de rutas de la API nueva con su permiso y su forma de respuesta, para quien monte las pantallas.
Hecho cuando: F6.1–F6.4 en ⚠ fuera de alcance, sin cambios en `v2/apps/web`, y la noche pasa de F5.9 a F7.1.

Datos reales (regla N-26, decisión de Tomás 6-oct 10:41, vale para todas las puertas que quedan): si un fichero del `data/` de la raíz cambia sin que lo escriba ninguna orden tuya, es una tarea de Tomás ajena a la noche. No lo repongas ni lo reescribas: apúntalo en N-26 de `migracion/PENDIENTES_LOGICA.md` y añade su ruta a `~/RO_MIGRACION/excepciones.txt` con el motivo. La noche no lanza generadores ni pruebas que escriban en el `data/` de la raíz (copia temporal si hace falta).
