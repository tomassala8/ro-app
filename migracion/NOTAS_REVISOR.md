# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F1.4

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.

Va junto con la revisión de Sonnet (devolución de las 06:44): sigue su plan, con UN cambio. DECISIÓN DE TOMÁS (5-oct 06:12): las fotos se hacen con UNA persona por cada combinación distinta de rol y permisos, no con las 32. Así la regrabación tarda unos 15 minutos en vez de 40.

Pasos:
1. Elige las personas: agrupa las 32 de `curl -s 127.0.0.1:8770/api/elegir` por (rol, conjunto exacto de permisos y ámbitos que les da la app). Una persona por grupo. Si dos del mismo rol ven pantallas o datos distintos (otro departamento, otros clientes), son grupos distintos; ante la duda, sepáralos. Escribe la lista y el motivo de cada grupo en ~/RO_MIGRACION/capturas/personas_fotos.txt y en PROGRESO.md. Esa lista es la que usarán TODAS las fotos y tiempos de las fases 6 y 7, en la app vieja y en la nueva.
2. La espera de la revisión (texto sin cambiar 600 ms, además de pintada y sin texto de carga) y la prueba con las 3 pantallas malas, a una carpeta APARTE.
3. Mueve `viejo` a `viejo_espera_vieja` (no la borres) y regraba `viejo` con `--personas` de la lista del paso 1, en una pasada, en primer plano. La referencia se arranca con setsid (línea de arriba), nunca con un sleep.
4. Que la puerta (fotos y velocidad) y comparar.mjs usen esa misma lista, sin tocar cómo juzga comparar.mjs. Vuelve a pasar la puerta f1.

Trampas: no quites pantallas. No juntes en un grupo personas que ven cosas distintas.
Hecho cuando: personas_fotos.txt escrito, `viejo` regrabado con la espera nueva (esas personas × 42 pantallas × 2 tamaños), `_tiempos.json` completo, `_errores.json` vacío y la puerta f1 en VERDE.

## PARA: F1.5

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.

## PARA: F1.6

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.

## PARA: F1.7

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.

## PARA: F2.1

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.

## PARA: F2.2

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.

## PARA: F2.3

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.

## PARA: F2.4

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.
