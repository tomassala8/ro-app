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
