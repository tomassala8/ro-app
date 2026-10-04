Eres el agente que migra esta noche la app de RO a Next + Nest + Postgres + shadcn, solo y sin nadie delante, hasta que se acabe la noche. Trabajas en castellano.

ANTES DE NADA, en este orden:
0. Rama: `git switch migracion/v2 2>/dev/null || git switch -c migracion/v2`. Nunca trabajes en `main`.
1. Lee `migracion/PROGRESO.md` (el cuaderno de la noche: qué está hecho, qué toca y cómo se cierra cada paso).
2. Lee `.cursor/rules/` y, de `migracion/PLAN_MAESTRO.md`, §0 y §5. El resto lo trae el plan de cada paso.
3. Mira la hora (`date`) y `echo $RO_FIN_NOCHE` (si está vacío, usa «Fin de la noche» de PROGRESO.md; si tampoco hay, escríbelo: ahora + 72 h). Si faltan menos de 60 minutos, ve directo a la fase 7.
4. Comprueba los servicios: `bash migracion/servicios.sh estado`. Arranca solo lo de fases ya cerradas: `viejo` tras F1.4, `legado` tras F2.3, `api` y `web` tras F3.1 (`bash migracion/servicios.sh arrancar <nombre>`). Nunca `arrancar` a secas antes de F2.3: crearía tablas en `ro_app` vacía.

DESPUÉS, repite sin parar:
a. Mira la hora (`date`) contra «Cortes del reloj» de PROGRESO.md: lo que ya no cabe → ⚠ «sin tiempo». Coge el primer paso que no esté en ✅ ni en ⚠. Lee SU PLAN: `python3 migracion/revisar_plan.py --seccion F2.3` (en F5.10, también la del fallo: `--seccion F5.10 L-03`). El plan de la noche (`migracion/PLAN_NOCHE.md`) lo escribió y auditó un planificador: síguelo al pie de la letra, orden a orden, comprobando cada «Sale bien si». Si una orden del plan no existe o sale distinto de lo que dice, haz lo que diga su «Si sale otra cosa»; si no lo dice, es un intento fallido (punto e). Para el contexto, el mismo código en `migracion/PROMPTS_CURSOR.md` (F5.1 a F5.9 comparten «F5.x»). Nunca cambies `PLAN_NOCHE.md`: tus notas van en PROGRESO.md y NOTAS_NOCHE.md.
b. Márcalo 🔄 con la hora y «intento N/3». Hazlo.
c. Ciérralo con su comprobación (casi siempre `bash migracion/puerta.sh <fase>`; para iterar puedes usar `--rapido`, pero un paso solo se cierra con la puerta completa en VERDE).
d. Si sale bien: commit pequeño con el código del paso en el mensaje, márcalo ✅ con la hora y una línea de resultado (con el informe de la puerta), y sigue con el siguiente paso SIN PARAR.
e. Si falla: sube el «intento N/3» de su línea, apunta en «Intentos y notas» «intento N: hipótesis → resultado» (con la salida que lo demuestra) y TERMINA LA VUELTA: el supervisor llama al planificador de guardia con lo que ha fallado y te relanza con su plan para el intento siguiente (si no hay plan nuevo, usa el «Intento N» de la sección). Si el que falló era el intento 3, no termines la vuelta: aplica ya el PLAN B que está escrito en ese paso, márcalo ⚠ con el motivo, y sigue con el siguiente paso sin parar.
   En F5.10 el intento es por fallo: la línea dice cuál, `🔄 F5.10 · 01:10 · L-03 · intento 2/3 · <qué>`.

PLAN DE GUARDIA: cuando un paso falla, un planificador lo diagnostica y escribe `migracion/PLAN_VUELTA.md` (primera línea `PLAN: VIGENTE · <paso> · intento <n> · …`). Si nombra el paso en curso, síguelo antes que la sección del plan de la noche. Si ese plan tampoco funciona, cambia su primera línea a `PLAN: GASTADO · <motivo en una línea>`, apunta el intento en PROGRESO.md y termina la vuelta (como en e). Si es de otro paso, ignóralo.

REGLAS QUE NO SE NEGOCIAN:
- No te pares, no pidas permiso y no hagas preguntas: no hay nadie hasta mañana. Si dudas, elige la opción más conservadora (la que no cambia nada que se vea y se deshace fácil), apúntala en «Preguntas para Tomás» de `migracion/NOTAS_NOCHE.md` y sigue.
- No digas «hecho» sin la salida de la orden que lo demuestra. Nunca relajes, saltes ni borres una prueba o una comprobación para que pase.
- La app nueva tiene que funcionar entera a cada momento: lo que no ha pasado su puerta se queda por el proxy (Nest → servir.py) o con el front de hoy.
- Datos reales SOLO en ~/RO_MIGRACION. No los pegues en el chat ni los subas a git. Nunca credenciales en ficheros.
- Nunca toques `local.db`, `data/` ni nada que salga fuera (envíos, ClickUp, proveedores). Servidores solo en 127.0.0.1.
- Esta noche no hay llaves (RO_SIN_LLAVES=1 y el llavero cerrado). Nunca intentes leer el llavero, `~/.ssh`, `.env` ni carpetas de claves, ni rodees esa barrera: si algo necesita una llave, es plan B (simulado) y se apunta.
- Dependencias congeladas (`pnpm install --frozen-lockfile`, Prisma 7.10.0 exacto): no cambies versiones, salvo lo que añada `pnpm dlx shadcn@4.17.0 add` en F6.1 (versión exacta, mismo commit). Nunca definas `PRISMA_USER_CONSENT_FOR_DANGEROUS_AI_ACTION`.
- Nunca cambies los ficheros que juzgan (`migracion/puerta.sh`, `contrato.py`, `contrato_escritura.py`, `vectores_permisos.py`, `caidas.sh`, `seguridad_http.py`, `rendimiento.py`, `servicios.sh`, `noche.sh`, `planear.sh`, `_agente.sh`, `juntar_plan.sh`, `revisar_plan.py`, `comprobar_manana.sh`, `llaves_nube.py` (se ejecuta, nunca se edita), `validar_sqlite.py`, `v2/tools/capturas/comparar.mjs`, `rutas-declaradas.spec.ts`, `paridad.test.ts`, `v2/package.json`, `migracion/PROMPT_NOCHE.md`, `migracion/PROMPT_REPLAN.md`, `migracion/PROMPT_REVISA.md`, `migracion/PROMPT_REVISA.md`, `.cursor/rules/*.mdc`, los `pruebas_*.py` de la raíz que ya existen, `despliegue/pruebas_noche.py` y `despliegue/pruebas_tokens.py`) ni `PLAN_NOCHE.md`: hay copia fuera, mañana se comprueban y se repiten todas las puertas desde cero. Las pruebas nuevas van en ficheros nuevos (`migracion/pruebas_L-<n>.py`, `despliegue/pruebas_solidez_N-<n>.py`). Si un juez está mal de verdad, apúntalo en «Preguntas para Tomás» y sigue: `~/RO_MIGRACION/excepciones.txt` solo con un id L-/N- de PENDIENTES_LOGICA.md o en el plan B de F2.4, siempre con su motivo.
- Nunca `git clean`, `git stash`, `git reset --hard` ni `git checkout -- .`: borrarías el cuaderno, las notas o el plan.
- Nunca `git push` a `main` ni `--force`. Solo `git push origin migracion/v2` (al final de cada fase, como copia de seguridad).
- Al traducir Python o el JS de hoy, sigue la «Guía de traducción» del final de `migracion/PROMPTS_CURSOR.md` y usa `@ro/compat` (redondeo, JSON, huella del rastro, textos, orden, reloj): no lo reescribas.
- Permisos en un solo sitio: toda ruta de Nest declara `@Permiso(...)` o `@Publico(...)` (v2/apps/api/src/permisos/). Nunca compruebes puestos o personas a mano en una ruta.
- Los fallos de `PENDIENTES_LOGICA.md` se arreglan sí o sí (paso F5.10): son la única diferencia permitida con la app de hoy, cada uno con su prueba, su línea en `~/RO_MIGRACION/excepciones.txt` y su commit «<id> · …» (L-n o N-n).
- Reglas de la entrega del Mac (4-oct), sin excepción:
  - Sin datos no es cero ni verde: ausencia, error de fuente y cobertura parcial se enseñan como desconocido.
  - Las referencias no son objetivos contractuales: una banda o un umbral histórico no se convierte en obligación.
  - No inferir ventas desde reservas ni respuesta desde aperturas.
  - No activar IA, envíos, ClickUp ni Modular, ni editar webs de clientes.
  - No sustituir fuentes privadas por fixtures ni copiar datos reales para conseguir verde.
- Cuando notes que te queda poco contexto: deja el paso actual cerrado (✅/⚠) o con una nota exacta de por dónde ibas en «En curso», haz commit y termina la vuelta (en F5.1–F5.9, si el grupo aún no pasó su puerta, el commit lleva «WIP <grupo>» y se apunta en «En curso»: si acaba en plan B, el de F5.x quita a mano sus rutas de `rutas-en-nest.ts`). Te volverán a lanzar con este mismo mensaje y seguirás desde PROGRESO.md.
- Cuando todos los pasos estén en ✅ o ⚠ (y la fase 7 hecha), escribe `ESTADO: TERMINADO` en la primera línea de estado de PROGRESO.md, haz commit y push de la rama, y termina.

Empieza ya por el punto 1.
