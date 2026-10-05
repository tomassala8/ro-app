# Notas de Claude para la noche

Las escriben Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F1.4

Sustituye a las notas anteriores de F1.4 (networkidle y `_tiempos.json`), ya aplicadas. Va en la misma línea que la revisión de Sonnet: esto la concreta.

Por qué está mal: `capturar.mjs:66` espera solo al texto exacto «Cargando…». La app de hoy usa al menos 20 textos de carga distintos: «Cargando mensajes…», «Cargando tus tareas…», «Leyendo las fuentes autorizadas…», «Leyendo la ficha…», «Leyendo registros…», «Leyendo fuentes; las propuestas disponibles se mostrarán aquí.», etc. (`grep -rhoE "'(Cargando|Leyendo)[^']*'" static modulos app.js | sort -u`). La espera sale al momento y la foto sale a medio cargar.

Pasos:
1. v2/tools/capturas/capturar.mjs:66 → cambia la condición por:
   ```js
   await pagina.waitForFunction(() => !/(^|\n)\s*(Cargando|Leyendo)[^\n]*(…|\.\.\.)|Leyendo fuentes; las propuestas/.test(document.body.innerText), null, { timeout: 15_000 }).catch(() => {});
   ```
   Comprueba antes con el grep de arriba que la expresión cubre TODOS los textos que salen. Si alguno no encaja, amplíala; no quites ninguno.
2. Líneas 81–82: que una pasada parcial mezcle con lo anterior y no pise (código exacto en la nota de las 05:00, en el historial de este fichero: `git show 84ddbc1:migracion/NOTAS_REVISOR.md`).
3. Prueba con las 3 pantallas que salieron cargando, a una carpeta APARTE (no `viejo`). Sale bien si: ninguna de las fotos tiene «Cargando»/«Leyendo» (mira la imagen).
4. Regraba las 2.688 en una sola pasada a `viejo`. Después: `python3 -c 'import json;print(len(json.load(open("'$HOME'/RO_MIGRACION/capturas/viejo/_tiempos.json"))))'` → 2688, y `_errores.json` vacío.
5. Lista las fotos de menos de 25 KB y abre cada una. Las que sigan cargando no valen.

Trampas: no metas esas pantallas en excepciones.txt. No bajes personas ni pantallas. No subas el plazo de 15 s en vez de arreglar la condición.
Hecho cuando: 2.688 fotos, 0 errores, `_tiempos.json` con 2.688 entradas, ninguna foto con texto de carga, y la revisión dice BIEN.
