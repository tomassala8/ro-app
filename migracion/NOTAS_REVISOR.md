# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F5.10

L-50 cerrado por Opus (057c493, 6-oct 14:31). El bucle de las vueltas 30–33 ya está resuelto: no vuelvas a escribir la marca de L-50 en la línea 🔄. Sigue con el cierre de F5.10 (puerta y baterías del paso) según el plan.

Copia de fuera desfasada (6-oct 14:52): `revisar_plan.abiertos()` junta `migracion/PENDIENTES_LOGICA.md` con `~/RO_MIGRACION/PENDIENTES_LOGICA.md`, y la de fuera manda. Esa copia nadie la actualiza y sigue con 48 «abierto» que en el repo ya están cerrados.
1. `cp ~/RO_MIGRACION/PENDIENTES_LOGICA.md ~/RO_MIGRACION/PENDIENTES_LOGICA.antes_sync_2026-10-06.md`
2. En la copia de fuera, cambia SOLO la columna Estado de cada id que en el repo ya no está «abierto», poniendo el mismo texto que en el repo. No toques filas que solo existen fuera ni otras columnas. No edites `revisar_plan.py`.
3. `python3 -c "import sys; sys.path.insert(0,'migracion'); import revisar_plan as r; print(r.abiertos())"` debe dar `[]` (o solo ids que también están abiertos en el repo).
Hecho cuando: `abiertos()` coincide con el repo y la copia de antes queda guardada.

Velocidad en la puerta f2 (14:33–14:43): contrato y escrituras en verde; 4 rutas ×2 más lentas que la referencia, sin cambios de código desde la última puerta verde y con el Mac cargado (carga 6–8, videollamada). No es fallo del código: no toques código por esto. Espera a que baje la carga (mira `uptime`, por debajo de 3) y repite `bash migracion/puerta.sh f2`.

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

Datos reales (decisión de Tomás, 6-oct 10:41, «Excepción»): `data/telefonos/dudosos.json` cambió (2 → 128 entradas). NO lo escribe la noche: lo actualiza una tarea de Tomás ajena a la migración. NO se repone ni se edita nada dentro de `data/`. Vale para F5.10 y para todos los pasos siguientes que pasen puerta.
1. Abre N-26 en `migracion/PENDIENTES_LOGICA.md`, gravedad «datos», estado «conocido»: «los datos reales de `data/` cambian durante la migración por tareas del Mac ajenas a la noche; la referencia de la fase 1 es de la madrugada del 5-oct».
2. Añade a `~/RO_MIGRACION/excepciones.txt`: `/api/modulo/telefonos/dudosos  # N-26: fichero de datos reales actualizado por una tarea de Tomás ajena a la migración; no es un cambio de código` (si la diferencia sale como `foto:` o `tabla:`, añade también esa forma con el mismo motivo).
3. Si otro fichero de `data/` cambia igual sin que lo escriba ninguna orden tuya: misma regla, mismo id N-26, y apúntalo en NOTAS.
4. Repite `bash migracion/puerta.sh f2` y sigue con L-09 y L-50.
Sigue valiendo: la noche no lanza generadores ni pruebas que escriban en el `data/` de la raíz (copia temporal si hace falta).
Hecho cuando: puerta f2 VERDE con N-26 documentado y `data/telefonos/dudosos.json` sin tocar por la noche.

## PARA: F5.11

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F5.1

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F6.2

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.
