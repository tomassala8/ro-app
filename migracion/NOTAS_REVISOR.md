# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F1.4

Corrige la nota anterior (la del sandbox de Chromium): era un diagnóstico equivocado. Descártala.

Por qué está mal: v2/tools/capturas/capturar.mjs:64 abre cada pantalla con `waitUntil: 'networkidle'` (45 s). La app de hoy manda `POST api/uso` con `keepalive: true` (app.js:135), y la red nunca queda en silencio. Salta el plazo, el `catch` no guarda la foto y sigue con la siguiente: 45 s por pantalla y 0 fotos. Pasaría igual desde cualquier terminal. No es un fallo de la app ni de la referencia: no toques ninguna de las dos.

Pasos:
1. v2/tools/capturas/capturar.mjs:64 → cambia `waitUntil: 'networkidle'` por `waitUntil: 'load'`. Nada más en esa línea. La espera de «Cargando…» de la línea 66 ya cubre el pintado.
2. Prueba con una persona:
   Orden: `node v2/tools/capturas/capturar.mjs --personas $(curl -s 127.0.0.1:8770/api/elegir | python3 -c 'import sys,json;print(json.load(sys.stdin)["personas"][0]["id"])')`
   Sale bien si: hay .png nuevos bajo la carpeta de salida y cada pantalla tarda segundos, no 45 s.
3. Con fotos buenas, lanza la orden completa de fotos de F1.4 tal como la pide el plan.

Trampas: no cambies comparar.mjs (juzga). No bajes el número de pantallas ni de personas. No metas pantallas en excepciones.txt por este fallo. No toques app.js ni quites el envío de uso. No subas los plazos en vez de cambiar la espera.
Hecho cuando: la puerta de F1.4 en VERDE con las fotos de las 42 pantallas grabadas.
Si falla: apunta la salida del punto 2 en «Intentos y notas» y sigue el plan B de F1.4.

## PARA: F1.4 (añadido 05:00 — vale si F1.4 sigue abierto)

Por qué: las 2.688 fotos de ~/RO_MIGRACION/capturas/viejo son buenas. Lo único roto es `viejo/_tiempos.json`: la repetición parcial de 3 pantallas lo reescribió entero y dejó solo 3 entradas. `capturar.mjs` pisa `_tiempos.json` y `_errores.json` en cada pasada, aunque sea parcial.

Pasos:
1. NO borres ni regrabes las fotos de `viejo`.
2. Si `viejo_pasada2/_tiempos.json` existe y tiene 2.688 entradas:
   Orden: `python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))))' ~/RO_MIGRACION/capturas/viejo_pasada2/_tiempos.json`
   Si sale 2688: `cp ~/RO_MIGRACION/capturas/viejo_pasada2/_tiempos.json ~/RO_MIGRACION/capturas/viejo/_tiempos.json`. Hecho.
3. Si no existe o tiene menos: relanza la pasada completa a `viejo_pasada2` LO PRIMERO de la vuelta (unos 40 min) y luego el punto 2.
4. Arreglo de fondo en v2/tools/capturas/capturar.mjs, líneas 81–82: que una pasada mezcle con lo que ya había en vez de pisarlo. Código exacto:
   ```js
   const previo = (f) => { try { return JSON.parse(readFileSync(join(salida, f), 'utf8')); } catch { return null; } };
   const tiemposPrevios = previo('_tiempos.json') || {};
   const erroresPrevios = (previo('_errores.json') || []).filter((e) => !errores.some((x) => x.persona === e.persona && x.tamano === e.tamano && x.pantalla === e.pantalla));
   writeFileSync(join(salida, '_errores.json'), JSON.stringify([...erroresPrevios, ...errores], null, 1));
   writeFileSync(join(salida, '_tiempos.json'), JSON.stringify({ ...tiemposPrevios, ...tiempos }, null, 1));
   ```

Trampas: no uses `--personas` ni pasadas parciales sobre `viejo` antes del arreglo del punto 4. No inventes ni rellenes tiempos a mano.
Hecho cuando: `viejo/_tiempos.json` tiene 2.688 entradas y la puerta de F1.4 está en VERDE.
