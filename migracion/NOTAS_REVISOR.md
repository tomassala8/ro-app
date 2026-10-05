# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F1.4

Por qué está mal: las fotos fallan dos veces igual (02:25 y 02:39): Chromium arranca y se cierra antes de la primera página («browser has been closed» en v2/tools/capturas/capturar.mjs:54, en `newContext`). Fotos: 0. Comprobado fuera de Cursor: el mismo Chromium, contra la misma referencia en 127.0.0.1:8770, desde el Terminal de Tomás y con el entorno de la noche, SÍ funciona. Solo falla cuando lo lanza el agente. No es un fallo de la app ni de la referencia: no toques la app ni la referencia.

Pasos:
1. Ver por qué muere, antes de cambiar nada:
   Orden: `DEBUG=pw:browser* node v2/tools/capturas/capturar.mjs --personas $(curl -s 127.0.0.1:8770/api/elegir | python3 -c 'import sys,json;print(json.load(sys.stdin)["personas"][0]["id"])') 2>&1 | tail -60 > ~/RO_MIGRACION/logs/f14_chromium_debug.txt; tail -60 ~/RO_MIGRACION/logs/f14_chromium_debug.txt`
   Sale bien si: ves la última línea de stderr de Chromium (sandbox, crashpad, TMPDIR, GPU…). Apúntala en «Intentos y notas».
2. v2/tools/capturas/capturar.mjs, línea del `chromium.launch(...)` → lanza sin el sandbox propio de Chromium y sin GPU (dentro del shell del agente el sandbox de Chromium no puede arrancar). Código exacto:
   ```js
   const opciones = { chromiumSandbox: false, args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--disable-crash-reporter'] };
   if (existsSync('/opt/pw-browsers/chromium')) opciones.executablePath = '/opt/pw-browsers/chromium';
   const navegador = await chromium.launch(opciones);
   ```
   Orden: la misma del punto 1. Sale bien si: hay al menos 1 .png nuevo bajo la carpeta de salida.
3. Si el punto 1 nombra TMPDIR o una carpeta sin permiso: lanza las fotos con `TMPDIR=$HOME/RO_MIGRACION/tmp_chromium` (créala antes con mkdir -p). Nada más.
4. Con 1 foto buena, lanza la orden completa de fotos de F1.4 tal como la pide el plan.

Trampas: no cambies comparar.mjs (juzga). No bajes el número de pantallas ni de personas para que «pase». No metas pantallas en excepciones.txt por este fallo: es del navegador, no de las pantallas. No toques la app de hoy.
Hecho cuando: la puerta de F1.4 en VERDE con las fotos de las 42 pantallas grabadas.
Si falla: tras los pasos 1–3 sin ninguna foto, apunta la salida del punto 1 en «Intentos y notas» y sigue el plan B de F1.4 del plan. Tomás puede regrabar las fotos desde su Terminal por la mañana (allí funciona).
