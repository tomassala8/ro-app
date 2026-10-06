# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F5.10

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

Datos reales (6-oct 09:50): `data/telefonos/dudosos.json` cambió (2 → 128 entradas). NO lo escribe la noche: lo actualizan tareas de Tomás que siguen corriendo en el Mac (Zadarma→GHL, panel-operaciones, servidores viejos). Decisión de Tomás (6-oct 10:35, «Excepción»): NO se repone ni se toca el fichero.
1. Apunta la diferencia como conocida en `~/RO_MIGRACION/excepciones.txt`, con el formato que ya usa la puerta para esa diferencia (ruta, `foto:` o `tabla:` según dónde salga), y motivo «datos reales que cambian solos durante la migración (tareas de Tomás), 6-oct».
2. Repite `bash migracion/puerta.sh f2` y sigue con L-09 y L-50.
3. Si otra ruta de `data/` cambia igual, misma regla: excepción con motivo, nunca reponer.
Sigue valiendo: la noche no lanza generadores ni pruebas que escriban en el `data/` de la raíz (copia temporal si hace falta).
Hecho cuando: puerta f2 VERDE con esa excepción documentada y `data/telefonos/dudosos.json` sin tocar por la noche.

## PARA: F5.11

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F5.1

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F6.2

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.
