# Notas de Claude para la noche

Las escribe Claude desde fuera. noche.sh las lee cada 5 minutos. No mandan sobre PROMPT_NOCHE.md ni .cursor/rules.

## PARA: F2.2

ANTES de F2.2: si F1.5, F1.6, F1.7 o F2.1 están en 🔄 por la nota de las 06:47, fue un error de la maquinaria. NO los rehagas: comprueba su «Hecho cuando» con lo que ya hay y vuelve a marcarlos ✅ con la hora y el resultado de antes. Si F1.4 sigue regrabando fotos, deja que termine antes de copiar la base (las fotos miden tiempos y la copia cargaría el Mac).

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.

Tareas largas que no bloquean el paso siguiente y NO miden tiempos (baterías largas, copias; las fotos y rendimiento.py miden tiempos: esas, solas y en primer plano): lánzalas en segundo plano con setsid y su log (`perl -MPOSIX -e 'setsid(); exec @ARGV' bash -c "<orden> > ~/RO_MIGRACION/logs/<nombre>.log 2>&1"`), apunta en PROGRESO.md que están en marcha, sigue con el paso siguiente y ciérralas cuando acaben. Nunca te quedes esperando una pasada larga si hay otro paso que no depende de ella.

## PARA: F2.3

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.

Tareas largas que no bloquean el paso siguiente y NO miden tiempos (baterías largas, copias; las fotos y rendimiento.py miden tiempos: esas, solas y en primer plano): lánzalas en segundo plano con setsid y su log (`perl -MPOSIX -e 'setsid(); exec @ARGV' bash -c "<orden> > ~/RO_MIGRACION/logs/<nombre>.log 2>&1"`), apunta en PROGRESO.md que están en marcha, sigue con el paso siguiente y ciérralas cuando acaben. Nunca te quedes esperando una pasada larga si hay otro paso que no depende de ella.

## PARA: F2.4

Servicios (vale para este paso y todos los que arranquen servicios): Cursor mata el grupo de procesos al acabar cada orden y el nohup de servicios.sh no basta. Arráncalos SIEMPRE así: `perl -MPOSIX -e 'setsid(); exec @ARGV' bash migracion/servicios.sh arrancar viejo` (igual con legado, api, web). Comprobado el 5-oct: así sobreviven al cierre de la orden. PROHIBIDO dejar un `sleep` largo o una «sesión larga» para mantenerlos vivos: cursor-agent -p no termina mientras ese shell viva y la vuelta se cuelga 90 minutos (pasó en las vueltas 2 y 4). Las pasadas largas (fotos, contrato) lánzalas en primer plano y espera a que acaben.

Tareas largas que no bloquean el paso siguiente y NO miden tiempos (baterías largas, copias; las fotos y rendimiento.py miden tiempos: esas, solas y en primer plano): lánzalas en segundo plano con setsid y su log (`perl -MPOSIX -e 'setsid(); exec @ARGV' bash -c "<orden> > ~/RO_MIGRACION/logs/<nombre>.log 2>&1"`), apunta en PROGRESO.md que están en marcha, sigue con el paso siguiente y ciérralas cuando acaben. Nunca te quedes esperando una pasada larga si hay otro paso que no depende de ella.
