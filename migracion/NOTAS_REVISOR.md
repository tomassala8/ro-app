# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F5.11

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

Datos reales (regla N-26, decisión de Tomás 6-oct 10:41, vale para todas las puertas que quedan): si un fichero del `data/` de la raíz cambia sin que lo escriba ninguna orden tuya, es una tarea de Tomás ajena a la noche. No lo repongas ni lo reescribas: apúntalo en N-26 de `migracion/PENDIENTES_LOGICA.md` y añade su ruta a `~/RO_MIGRACION/excepciones.txt` con el motivo. La noche no lanza generadores ni pruebas que escriban en el `data/` de la raíz (copia temporal si hace falta).

VELOCIDAD DE DÍA NO FRENA (decisión de Tomás, 6-oct 18:53, tarjeta «No frena»; vale para F5.11 y todos los pasos que quedan): si en una puerta lo ÚNICO rojo es la velocidad (rendimiento.py contra la referencia de madrugada) y la medida A/B a la vez de 8770 (app de hoy) y 8771 (app nueva) da diferencias de como mucho un 20 % en cada ruta, el paso se cierra ✅ con la nota «velocidad pendiente de la medida de madrugada». No esperes calma ni gastes intentos por eso. Si alguna ruta pasa del 20 % en la A/B, es un fallo real: sigue el plan normal.
1. Ahora, en F5.11: haz la A/B, y si cumple, cierra F5.11 y sigue con F5.1.
2. Apunta esta regla en las notas generales de `migracion/PROGRESO.md`, para que la vean los pasos siguientes.
3. Abre en `migracion/PENDIENTES_LOGICA.md` el id N-27, gravedad «rendimiento», estado «pendiente de medir»: «puerta de velocidad con el Mac en calma (madrugada); vigilar CRM y prioridades de Operaciones, +30 % sobre la referencia por la tarde del 6-oct». La primera vuelta que empiece entre las 02:00 y las 06:00 lanza `bash migracion/puerta.sh f2` completa y apunta el resultado en N-27.
Hecho cuando: F5.11 cerrado sin esperar calma, la regla en PROGRESO.md y N-27 abierto.

## PARA: F5.1

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F6.2

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.
