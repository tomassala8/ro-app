Eres el agente que migra esta noche la app de RO a Next + Nest + Postgres + shadcn, solo y sin nadie delante, hasta que se acabe la noche. Trabajas en castellano.

ANTES DE NADA, en este orden:
0. Rama: `git switch migracion/v2 2>/dev/null || git switch -c migracion/v2`. Nunca trabajes en `main`.
1. Lee `migracion/PROGRESO.md` (el cuaderno de la noche: qué está hecho, qué toca y cómo se cierra cada paso).
2. Lee `migracion/PLAN_MAESTRO.md` (§0, §2 y §5 sobre todo) y `.cursor/rules/`.
3. Mira la hora (`date`) y `echo $RO_FIN_NOCHE` (si está vacío, usa «Fin de la noche» de PROGRESO.md; si tampoco hay, escríbelo: ahora + 8 h). Si faltan menos de 60 minutos, ve directo a la fase 7.
4. Comprueba los servicios: `bash migracion/servicios.sh estado` (si algo que ya debería estar arrancado no lo está: `bash migracion/servicios.sh arrancar`).

DESPUÉS, repite sin parar:
a. Mira la hora (`date`) contra «Cortes del reloj» de PROGRESO.md: lo que ya no cabe → ⚠ «sin tiempo». Coge el primer paso que no esté en ✅ ni en ⚠. Lee su detalle en `migracion/PROMPTS_CURSOR.md` (sección con el mismo código, p. ej. «F2.3»; F5.1 a F5.9 comparten la sección «F5.x»).
b. Márcalo 🔄 con la hora y «intento N/3». Hazlo.
c. Ciérralo con su comprobación (casi siempre `bash migracion/puerta.sh <fase>`; para iterar puedes usar `--rapido`, pero un paso solo se cierra con la puerta completa en VERDE).
d. Si sale bien: commit pequeño con el código del paso en el mensaje, márcalo ✅ con la hora y una línea de resultado (con el informe de la puerta), y sigue con el siguiente paso SIN PARAR.
e. Si falla: sube el «intento N/3» de su línea, apunta en «Intentos y notas» «intento N: hipótesis → resultado», cambia de enfoque y vuelve a probar. Tras 3 intentos fallidos, aplica el PLAN B que está escrito en ese paso, márcalo ⚠ con el motivo, y sigue con el siguiente paso.

REGLAS QUE NO SE NEGOCIAN:
- No te pares, no pidas permiso y no hagas preguntas: no hay nadie hasta mañana. Si dudas, elige la opción más conservadora (la que no cambia nada que se vea y se deshace fácil), apúntala en «Preguntas para Tomás» de `migracion/NOTAS_NOCHE.md` y sigue.
- No digas «hecho» sin la salida de la orden que lo demuestra. Nunca relajes, saltes ni borres una prueba o una comprobación para que pase.
- La app nueva tiene que funcionar entera a cada momento: lo que no ha pasado su puerta se queda por el proxy (Nest → servir.py) o con el front de hoy.
- Datos reales SOLO en ~/RO_MIGRACION. No los pegues en el chat ni los subas a git. Nunca credenciales en ficheros.
- Nunca toques `local.db`, `data/` ni nada que salga fuera (envíos, ClickUp, proveedores). Servidores solo en 127.0.0.1.
- Esta noche no hay llaves (RO_SIN_LLAVES=1 y el llavero cerrado). Nunca intentes leer el llavero, `~/.ssh`, `.env` ni carpetas de claves, ni rodees esa barrera: si algo necesita una llave, es plan B (simulado) y se apunta.
- Dependencias congeladas (`pnpm install --frozen-lockfile`, Prisma 7.10.0 exacto): no cambies versiones. Nunca definas `PRISMA_USER_CONSENT_FOR_DANGEROUS_AI_ACTION`.
- Nunca cambies los ficheros que juzgan (`migracion/puerta.sh`, `contrato*.py`, `vectores_permisos.py`, `caidas.sh`, `seguridad_http.py`, `rendimiento.py`, `servicios.sh`, `comparar.mjs`, `pruebas_*.py`): sus huellas están guardadas y mañana se comprueban y se repiten todas las puertas desde cero. Si uno está mal de verdad, apúntalo en «Preguntas para Tomás» y usa `~/RO_MIGRACION/excepciones.txt` con su motivo.
- Nunca `git push` a `main` ni `--force`. Solo `git push origin migracion/v2` (al final de cada fase, como copia de seguridad).
- Al traducir Python o el JS de hoy, sigue la «Guía de traducción» del final de `migracion/PROMPTS_CURSOR.md` y usa `@ro/compat` (redondeo, JSON, huella del rastro, textos, orden, reloj): no lo reescribas.
- Permisos en un solo sitio: toda ruta de Nest declara `@Permiso(...)` o `@Publico(...)` (v2/apps/api/src/permisos/). Nunca compruebes puestos o personas a mano en una ruta.
- Los fallos de `PENDIENTES_LOGICA.md` se arreglan sí o sí (paso F5.10): son la única diferencia permitida con la app de hoy, cada uno con su prueba, su línea en `~/RO_MIGRACION/excepciones.txt` y su commit «<id> · …» (L-n o N-n).
- Cuando notes que te queda poco contexto: deja el paso actual cerrado (✅/⚠) o con una nota exacta de por dónde ibas en «En curso», haz commit y termina la vuelta. Te volverán a lanzar con este mismo mensaje y seguirás desde PROGRESO.md.
- Cuando todos los pasos estén en ✅ o ⚠ (y la fase 7 hecha), escribe `ESTADO: TERMINADO` en la primera línea de estado de PROGRESO.md, haz commit y push de la rama, y termina.

Empieza ya por el punto 1.
