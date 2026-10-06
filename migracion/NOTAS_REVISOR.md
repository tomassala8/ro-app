# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F5.1

PUERTA f5 DE F5.1 (23:13): lo esencial en verde (compila, e2e, contrato, escrituras, velocidad). Quedan dos cosas:
1. SEGURIDAD, fallo real, arréglalo antes de cerrar: `/api/sesion`, servida ya por Nest, sale sin las cabeceras de seguridad que pone la app de hoy (Content-Security-Policy, X-Frame-Options o frame-ancestors, y las otras que marque `seguridad_http.py`). Ponlas UNA vez y de forma global en Nest (middleware o interceptor registrado en `main.ts` o en el módulo raíz), con los mismos valores que `servir.py`, para que valgan en todas las rutas que se muden en F5.2–F5.9. Añade una prueba e2e que pida `/api/sesion` y `/vivo` y compruebe cada cabecera. No toques `seguridad_http.py`.
2. CAÍDAS, «sin legado responde 200»: es lo esperado, porque `/api/sesion` ya no pasa por el legado. NO edites `caidas.sh`: es un juez con huella. Aplica la regla de las excepciones: abre N-29 en `migracion/PENDIENTES_LOGICA.md` (gravedad «pruebas», estado «conocido»: «caidas.sh prueba la caída del legado con /api/sesion, que desde F5.1 sirve Nest; el juez debe usar una ruta que siga por el proxy; lo cambia Claude de día»). Compruébalo a mano: con el legado parado, una ruta que siga por el proxy (por ejemplo `/api/indicadores`) da 502/503 en < 6 s. Si es así, esa línea no decide el paso. Apunta la orden y su salida en PROGRESO.
3. Baterías contra la app nueva: cada rojo nuevo (no estaba en la última puerta f3) es del paso y se arregla. Los rojos que ya estaban, se apuntan.
Hecho cuando: cabeceras globales con su e2e en verde, `seguridad_http.py` en verde, N-29 apuntado con la prueba manual, y baterías sin rojos nuevos.

FOTOS Y 30 PERSONAS EN LA PUERTA f5 (6-oct 22:15; vale para F5.1–F5.9). Las pantallas se rediseñan (decisión de Tomás, 6-oct 19:02) y estas dos líneas ya salían rojas en F3.1 por causas conocidas y ajenas a las rutas: 96/2100 fotos por las 4 causas de F3.1, y «30 personas» por la cola de 8770 en macOS.
1. Si en `bash migracion/puerta.sh f5` lo ÚNICO rojo es «fotos» y/o «30 personas», compara con la línea base de F3.1. Fotos: las pantallas distintas son un subconjunto de las 96 de F3.1. 30 personas: la app nueva (8771/3000) no da ningún 5xx propio y los errores vienen de la cola de 8770. Si cumple, cierra el paso ✅, apunta N-28 en `migracion/PENDIENTES_LOGICA.md` (gravedad «presentación», estado «conocido», «fotos y 30 personas iguales que la línea base de F3.1; no deciden pasos de rutas»), y no hagas intentos extra.
2. Si sale una pantalla distinta NUEVA (no está entre las 96) o un 5xx de la app nueva, es fallo real del paso: sigue el plan normal.
3. La cascada «F5.1 ⚠ → F5.2–F5.9 sin intentarlo» SOLO vale si falla la identidad, la sesión o el rastro: compila, e2e, contrato o escrituras en rojo. Nunca por fotos, 30 personas o velocidad.
4. Mientras iteras usa `bash migracion/puerta.sh f5 --rapido`. La puerta completa, una sola vez al cerrar.
5. Copia esta regla a las notas generales de `migracion/PROGRESO.md`.
Hecho cuando: el paso se cierra con N-28 apuntado, o se identifica la pantalla o el 5xx nuevo.

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1 y los fallos de SEGURIDAD de F5.10. Sonnet: F2.4, F3.1, F6.2 y los fallos de datos, funcional y presentación de F5.10. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

SIN PANTALLAS (decisión de Tomás, 6-oct 19:02): «vamos a montar pantallas distintas a las que ya teníamos; no avancemos con la parte de pantallas». La noche termina en las rutas (F5.1–F5.9) y luego va directa a F7. No se hace nada de F6.
1. En cuanto leas esto, en `migracion/PROGRESO.md` cambia F6.1, F6.2, F6.3 y F6.4 a `- ⚠ F6.x · HH:MM · fuera de alcance: decisión de Tomás 6-oct 19:02, las pantallas nuevas serán distintas; no se hace`. No instales shadcn, no toques `v2/apps/web` ni la carcasa, no grabes fotos nuevas.
2. «/» lo sigue sirviendo el front de hoy a través de Next, como ahora (`RO_CARCASA` apagado).
3. En F7: contenedores, `render.yaml`, informe y `puerta.sh f7`. Si la puerta f7 pide algo de la carcasa o de pantallas en React, esa parte no aplica: apúntala en `~/RO_MIGRACION/excepciones.txt` con el motivo «F6 fuera de alcance, decisión de Tomás 6-oct» y en el informe.
4. En `INFORME_NOCHE.md`, una sección «Para las pantallas nuevas»: lista de rutas de la API nueva con su permiso y su forma de respuesta, para quien monte las pantallas.
Hecho cuando: F6.1–F6.4 en ⚠ fuera de alcance, sin cambios en `v2/apps/web`, y la noche pasa de F5.9 a F7.1.

Datos reales (regla N-26, decisión de Tomás 6-oct 10:41, vale para todas las puertas que quedan): si un fichero del `data/` de la raíz cambia sin que lo escriba ninguna orden tuya, es una tarea de Tomás ajena a la noche. No lo repongas ni lo reescribas: apúntalo en N-26 de `migracion/PENDIENTES_LOGICA.md` y añade su ruta a `~/RO_MIGRACION/excepciones.txt` con el motivo. La noche no lanza generadores ni pruebas que escriban en el `data/` de la raíz (copia temporal si hace falta).

## PARA: F5.2

FOTOS Y 30 PERSONAS EN LA PUERTA f5 (6-oct 22:15; vale para F5.1–F5.9). Las pantallas se rediseñan (decisión de Tomás, 6-oct 19:02) y estas dos líneas ya salían rojas en F3.1 por causas conocidas y ajenas a las rutas: 96/2100 fotos por las 4 causas de F3.1, y «30 personas» por la cola de 8770 en macOS.
1. Si en `bash migracion/puerta.sh f5` lo ÚNICO rojo es «fotos» y/o «30 personas», compara con la línea base de F3.1. Fotos: las pantallas distintas son un subconjunto de las 96 de F3.1. 30 personas: la app nueva (8771/3000) no da ningún 5xx propio y los errores vienen de la cola de 8770. Si cumple, cierra el paso ✅, apunta N-28 en `migracion/PENDIENTES_LOGICA.md` (gravedad «presentación», estado «conocido», «fotos y 30 personas iguales que la línea base de F3.1; no deciden pasos de rutas»), y no hagas intentos extra.
2. Si sale una pantalla distinta NUEVA (no está entre las 96) o un 5xx de la app nueva, es fallo real del paso: sigue el plan normal.
3. La cascada «F5.1 ⚠ → F5.2–F5.9 sin intentarlo» SOLO vale si falla la identidad, la sesión o el rastro: compila, e2e, contrato o escrituras en rojo. Nunca por fotos, 30 personas o velocidad.
4. Mientras iteras usa `bash migracion/puerta.sh f5 --rapido`. La puerta completa, una sola vez al cerrar.
5. Copia esta regla a las notas generales de `migracion/PROGRESO.md`.
Hecho cuando: el paso se cierra con N-28 apuntado, o se identifica la pantalla o el 5xx nuevo.
