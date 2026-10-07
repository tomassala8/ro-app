# Plan acelerado hasta Cursor · 4 octubre 2026

Objetivo del corte: entregar esta tarde una copia local verificable, con fallos corregidos y pendientes trazados para la reescritura. Prioridad de producto: Dirección de Operaciones, Accounts y Paid, con tablas compactas, cifras y semáforos fundamentados. No prometer totalidad ni 10/10 por consumo de créditos.

## Siete frentes coordinados

|Frente|Responsable y propiedad|Entrega concreta|
|---|---|---|
|Integración|Chat principal, pruebas centrales y documentos|Aceptar cambios por evidencia, comprobar regresiones, reinicios sólo del coordinador y corte estable|
|Backend crítico|Subagente audit_permissions, servir.py/build_data.py según cesión|575.1 trabajador de recargas; después validaciones restantes L13 y parches backend acordados|
|Dinero y privacidad|Subagente audit_workflows, propuesta576 y archivos nuevos|Alias y clasificación por proximidad con matriz vigente; aplicar sólo después de revisión y asignación explícita de permisos.py|
|Alcance por cliente|Subagente clickup_parity, propuesta578 y archivos nuevos|Reproducción L05/L10, 403 cliente ajeno/resumen limitado/contrato administración preservado|
|Fechas y periodos|RO · Fechas y periodos fiables, componentes.js y helpers propios|Contrato común Madrid con DST y pruebas de zona; consumidores pendientes como parches separados|
|Navegación|RO · Navegación compacta y accesible, carcasa.js/ayudas.js/catalogo.js/estilos.css|Más por rol, paleta y accesibilidad, todos los permisos y accesos autorizados conservados|
|Baterías completas|RO · Pruebas completas en entorno ficticio, sólo outputs propios|Staging de código y datos sintéticos, DB desde esquema, runner preparado sin copiar datos ni ejecutar contra revisión viva|

Los tres chats nuevos ya están activos. Sus identificadores:
- Fechas:01a1065e-2928-7303-8500-b073ce19fd4b.
- Navegación:01a1065e-46d0-7382-b027-7f08bcd9af12.
- Pruebas:01a1065e-5c82-7ea2-8a44-369b3862ac10.

Cada responsable conoce sus archivos exclusivos. No toca migracion/,v2/,Git, datos/base existentes, proveedores ni proceso de revisión. No se lanzan dos escritores de servir.py. Los chats paralelos no se comunican entre sí: el coordinador compara e integra. La disponibilidad de créditos no elimina los límites de concurrencia ni permite saltarse verificaciones.

## Hitos de Madrid

- Primera entrega útil alrededor de14:30: corregir bloqueos confirmados y revisar contratos de fechas/navegación. Este hito orienta la priorización, no certifica todos los puntos.
- Hasta17:30: integrar cambios probados, conectar consumidores de fechas por lotes de archivos asignados y ejecutar pruebas sintéticas/lecturas locales. Resolver defectos antes de ampliar funciones.
- A18:00: congelar fuentes de cada frente y registrar RELEASE, hashes y pruebas. Nada de empezar un rediseño global o nueva integración de proveedor.
- Hasta18:30: integración conjunta, comprobaciones de permisos, funciones y UI dentro del alcance disponible; recopilar pendientes que no se puedan cerrar con evidencia.
- A19:00: corte para Cursor, tabla externa y copia de código local verificadas. Commits sólo de cambios revisables y propios. Si una batería falla o no se ejecuta, registrarlo; no convertirlo en verde por omitir el caso.

Los hitos se ajustan al avance comprobado. No se retrasa el traspaso por intentar completar una funcionalidad no esencial.

## Criterios para aceptar

Reproducir el fallo en la versión vigente, corregir, demostrar los negativos y el camino válido, revisar que no cambia los permisos ni el significado del dato, y comprobar integración. Roles o clientes desconocidos no reciben grants. Ausencia de datos no equivale a cero, umbral histórico no equivale a contrato. Las métricas principales siguen visibles y el detalle secundario se despliega.

El menú se agrupa visualmente sin ampliar ni recortar derechos. Cambios de matriz atribuidos a terceros no se trasladan automáticamente. Los contactos y el dinero no se exponen en logs, capturas, fixtures ni mensajes. No hay envío ni despliegue; ClickUp y GoHighLevel permanecen operativos.

Las baterías originales tienen efectos sobre datos reales (573): hasta aislarlas no se ejecutan sobre la copia viva. Los76 casos aislados ya verificados no equivalen a pasar esas baterías. Los nuevos chats entregan una mejora real o un bloqueo demostrado, no otra lista genérica.

## Corte de partida

Informe564: revisión8771sesión75034,76casos aislados PASS, fuente estable hasta572, checkpoint1030archivos4.240.757bytes. L16commit local9a02a06 sin push.575.1 liberado con16pruebas propias y pendiente aceptación/integración root. Escáner y diseño global siguen con fallos documentados.49filas externas: no marcar cierre sin el commit y evidencia requeridos. Objetivo activo.

Actualización de ejecución:575.1 aceptado por root, carril central ampliado a92casos/8suites PASS. Continúan579(validacionesL13),580(textos económicos) y578(alcancecliente). El runtime75034ycheckpoint1030aún corresponden al corte previo a575: el siguiente reinicio/copia espera liberación coordinada de fuentes. Primer snapshot de los tres chats confirma trabajo activo; sus avances han identificado fallos vigentes, no sólo propuestas generales.


Reparto y resultados posteriores actualizados en599: tres chats y tres subagentes coordinados; central242casos aislados. Nuevo603L11enimplementación exclusiva de validadores de acciones;601/602frentesfrontend sin colisión; fechas fase5ventas y matriz49 en curso. NavegaciónPaid fase5 liberada y comprobada33+97 porroot. El checkpoint y reinicio siguiente esperan liberación603.
