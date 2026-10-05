# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F3.1

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1. Sonnet: F2.4, F3.1, F5.10, F6.2. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F4.1

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1. Sonnet: F2.4, F3.1, F5.10, F6.2. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F4.2

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1. Sonnet: F2.4, F3.1, F5.10, F6.2. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F5.10

Fallo nuevo N-24 (Claude, 5-oct, al revisar F2.4 ⚠): las 11 rutas «503 por diseño» de la puerta f2 NO son aceptables para el piloto. Son funciones de Operaciones que Astra escribió solo para SQLite y que en la nube (Postgres) se niegan a funcionar: `operaciones_registros_269.py:158`, `operaciones_registros_272.py:271`, `operaciones_feedback_273.py:132`, `operaciones_anomalias_276.py:140`, `operaciones_notas_equipo_281.py:102`, `operaciones_prioridades_300.py:122`, `operaciones_pedidos_account.py:252`, `decisiones_durables_382.py:178`, `evidencias_kpi_api.py:76` (más `actas.py:119` y `fuentes_objetivos/objetivos.py:57`: revisa si también apagan algo). Regla de Tomás: los fallos se arreglan sí o sí.
1. Añade la fila N-24 a PENDIENTES_LOGICA.md (gravedad: datos; dónde: esos ficheros; qué pasa: en Postgres responden 503 y Operaciones pierde decisiones, feedback, anomalías, notas, prioridades, pedidos y registros; qué debe pasar: funcionan igual sobre Postgres por `despliegue/base.py` (`SI.conectar()` / la misma conexión que servir.py); prueba: con `DATABASE_URL` de `ro_esc`, cada ruta responde como la app de hoy y escribe lo mismo; estado: abierto).
2. Arréglalo en el bloque de datos de F5.10: quita cada guarda `if DATABASE_URL … raise …(503)` y haz que el módulo use la conexión común (si usa SQL propio de SQLite, que pase por `traducir()` de base.py). Commit «N-24 · …» por módulo, con su prueba en `migracion/pruebas_N-24.py`.
3. Al arreglar cada ruta, BÓRRALA de `~/RO_MIGRACION/excepciones.txt` y de `excepciones_rendimiento.txt`, y pasa `bash migracion/puerta.sh f2` sin ella. Hecho cuando: ninguna ruta de Operaciones queda en excepciones por «503 por diseño».

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1. Sonnet: F2.4, F3.1, F5.10, F6.2. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

## PARA: F5.11

Cambio de modelo (decisión de Tomás, 4-oct): los pasos tienen dueño. Opus: F4.1, F4.2, F5.1. Sonnet: F2.4, F3.1, F5.10, F6.2. Grok: todos los demás. El supervisor elige el modelo al EMPEZAR cada vuelta, según el paso que toca. Por eso, al cerrar un paso (punto d de PROMPT_NOCHE.md), mira de quién es el siguiente: si es de otro dueño que el paso que acabas de cerrar, NO lo empieces. Haz commit, deja el cuaderno al día con «Siguiente: <paso>» y TERMINA LA VUELTA; el supervisor te relanza con el modelo que toca. Esto manda sobre el «sigue sin parar» del punto d. Sobre todo antes de F4.1 (Opus): nunca lo empieces si no eres Opus.

