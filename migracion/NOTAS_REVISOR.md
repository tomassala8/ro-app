# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F2.4

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1. Sonnet: F2.4, F3.1, F5.10, F6.2. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

Dirección de la base (F2.3 intento 1 falló por esto): usa SIEMPRE la forma con el usuario delante, `postgresql://ro:ro@127.0.0.1:5432/ro_app`, en TODAS las órdenes (pnpm db:deploy / prisma, validar_sqlite.py, copiar_sqlite_a_pg.py, publicacion.py, servir.py). Es la que usan `prisma.config.ts` y `puerta.sh` (`pg_url`). La forma `postgresql://127.0.0.1:5432/ro_app?user=ro&password=ro` de PROMPTS_CURSOR.md la acepta psql pero Prisma responde P1010. No toques los ficheros que juzgan para cambiarla: basta con exportar la buena en tu orden.

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.

Tareas largas que no bloquean el paso siguiente y NO miden tiempos (baterías largas, copias; las fotos y rendimiento.py miden tiempos: esas, solas y en primer plano): lánzalas en segundo plano con setsid y su log (`perl -MPOSIX -e 'setsid(); exec @ARGV' bash -c "<orden> > ~/RO_MIGRACION/logs/<nombre>.log 2>&1"`), apunta en PROGRESO.md que están en marcha, sigue con el paso siguiente y ciérralas cuando acaben. Nunca te quedes esperando una pasada larga si hay otro paso que no depende de ella.

## PARA: F3.1

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1. Sonnet: F2.4, F3.1, F5.10, F6.2. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F4.1

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1. Sonnet: F2.4, F3.1, F5.10, F6.2. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F4.2

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1. Sonnet: F2.4, F3.1, F5.10, F6.2. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F5.10

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1. Sonnet: F2.4, F3.1, F5.10, F6.2. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F5.11

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1. Sonnet: F2.4, F3.1, F5.10, F6.2. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

