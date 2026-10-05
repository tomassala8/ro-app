# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F1.4

Sustituye a todas las notas anteriores de F1.4. Es para el intento 3 (Fable de guardia: úsala como base del plan).

Por qué falla: el diagnóstico de Grok es correcto. Justo tras `load` el cuerpo está vacío; la espera «¿no hay texto de carga?» da «no hay» porque aún no hay nada, y la foto sale 0,4 s después con el cascarón. A los 2 s la pantalla ya está pintada. Las APIs responden en 0,01–0,4 s: no es lentitud, es el momento de la foto.

Pasos:
1. v2/tools/capturas/capturar.mjs, línea 66: cambia la espera por esta (espera a que haya algo pintado y luego a que no haya texto de carga y el contenido esté quieto 800 ms):
   ```js
   await pagina.waitForFunction(() => document.body.innerText.trim().length > 0, null, { timeout: 15_000 }).catch(() => {});
   await pagina.waitForFunction(() => {
     const t = document.body.innerText;
     if (/(Cargando|Leyendo|Pidiendo)[^\n]*(…|\.\.\.)|Leyendo fuentes; las propuestas/.test(t) || window.__largo !== t.length) { window.__largo = t.length; window.__desde = Date.now(); return false; }
     return Date.now() - window.__desde >= 800;
   }, null, { timeout: 15_000, polling: 100 }).catch(() => {});
   ```
   Antes, comprueba que la expresión cubre todos los textos de carga: `grep -rhoE "'(Cargando|Leyendo|Pidiendo)[^']*'" static modulos app.js | sort -u`.
2. Líneas 81–82: que una pasada parcial mezcle con lo anterior y no pise (código en `git show 84ddbc1:migracion/NOTAS_REVISOR.md`).
3. Prueba con las pantallas que fallaban (mi-trabajo, producción, operaciones; móvil y escritorio) a una carpeta APARTE. Abre las fotos: ninguna con texto de carga ni vacía.
4. Si sale bien: regraba las 2.688 en una pasada a `viejo`. `_tiempos.json` con 2.688 entradas y `_errores.json` vacío.

Trampas: no metas pantallas en excepciones.txt mientras el paso 3 no se haya probado. No bajes personas ni pantallas.
Hecho cuando: 2.688 fotos sin texto de carga, 0 errores, 2.688 tiempos, y la revisión dice BIEN.
Si falla el paso 3: plan B del paso (apuntar esas pantallas, fuera de la comparación por foto, y seguir a F1.5). Tomás las revisa por la mañana.
