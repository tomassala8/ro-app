# 670 · Integración CRM verificada en local

667 integra el lector de oportunidades cerradas: valida totales enteros finitos y detecta oportunidades repetidas con ámbito o estado contradictorio. Un stock ganado no se convierte en evento de venta, cobro ni tasa. El productor principal todavía no llama a este lector: queda pendiente conectarlo con una fuente histórica de cierre verificable.

668 integra el motor que invalida eventos atribuidos a clientes distintos. El namespace del adaptador conserva los eventos legítimos de distintas subcuentas que compartan un ID de proveedor. No se amplían etapas públicas ni permisos.

669 añade preparación offline reproducible: lectura privada acotada, sin enlaces simbólicos, comprobación de huellas antes y después, joins ACT inequívocos y escritura atómica sin sobrescribir una copia existente. La fecha pertenece a la fuente; ejecutar de nuevo no rejuvenece el dato.

670 actualiza conjuntamente el lector467, el pin del manifiesto y la revisión local. Se conserva el payload anterior byte por byte y su fecha original. La respuesta HTTP local200 coincide con la huella canónica anterior. El manifiesto y las fuentes privadas permanecen fuera del paquete de código; el staging anterior se conserva.

## Pruebas
Diez ejecutables focalizados pasan en APP: integridad668(8), namespaces668(6), motor(14), adaptador466(17), API467(18), revisión468(8), reservas620(20), puente621(12), preparación669(13), cerradas667(26). Conjuntos solapados: no sumar como casos únicos. También pasan las29 suites aisladas de seguridad. No certifican las baterías globales, el recorrido completo de navegador, carga ni restauración.

Checkpoint:1043 archivos,4297470 bytes, integridad verificada. Sólo código; no es copia operativa de bases y fuentes. Hay17GiB libres. diff-check del APP completo detecta dos espacios finales ajenos a este bloque en ayudas.js y generar_agenda.py; no se modifican por coordinación.

## Estado de entrega
652 y653 dejan de ser candidatos sin integrar: están aplicados mediante667/668/670. Las notas655–666 conservan el estado histórico, y este corte manda para esos pendientes. No cerrar las49 filas por asociación: sóloL16 tiene cierre formal.

GitHub permanece en650, commit1fdd99d5446af130e14c768b14bd8d6ca16195f2. Los cambios posteriores se entregan en un commit y bundle locales. La publicación externa fue rechazada por revisión automática; no se reintenta bajo el objetivo vigente sin escrituras externas. migracion/ yv2/ intactos. Ningún proveedor, web, envío ni despliegue activado.

Pendiente: cualificación versionada, participación/celebración, fecha efectiva de cierre, ventas, cobros y atribución; mediciones completas del artifact, capacidad aprobada, transiciones históricas, consumidores de fechas restantes y migración Postgres/restauración. No10/10 ni objetivo completo.

La misma batería focalizada de diez ejecutables pasa también en el checkout de entrega. El escáner de los diez archivos nuevos/modificados sólo señala dos correos ficticios de pruebas en dominios example; se revisó que no son contactos ni credenciales reales. diff-check de la entrega pasa.
