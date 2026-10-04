# Nota de traspaso · estado de RO desde la revisión local

Fecha: 4 de octubre de 2026. Autor: Codex, revisión local de RO. Este archivo es la nota solicitada como `NOTA_ASTRA.md`; no atribuye a otro modelo las verificaciones realizadas.

## Alcance de esta entrega

Esta entrega añade únicamente esta nota a la rama `claude/project-thread-rjes21`. No publica la aplicación local, sus bases, sus fuentes privadas ni sus últimas modificaciones de código. La copia local continúa teniendo cambios pendientes de integrar respecto a GitHub. No se debe tratar la raíz de esta rama ni su inventario anterior como la última versión verificada del producto.

La revisión funcional se ha hecho en `127.0.0.1:8771`, con una base separada y las salidas externas desactivadas. No se ha desplegado, modificado webs de clientes ni escrito en proveedores. ClickUp permanece como repositorio operativo y GoHighLevel sigue siendo el CRM; no está aprobada su sustitución mediante esta nota.

El checkpoint local de código se comprueba por hashes e integridad del archivo, pero excluye bases, fuentes privadas, cachés y dependencias. No demuestra restauración operativa ni constituye por sí solo una copia completa del sistema.

### Actualización 4 de octubre de 2026, tarde: el código del Mac ya está en la rama

Lo de arriba describe la nota tal como llegó. Desde entonces, el código del Mac hasta el corte 650 se publicó como rama de entrega (`codex/ro-entrega-cursor-2026-10-04`, con `ENTREGA_CURSOR_CODEX.md` y `entrega/*.md`) y está juntado en `claude/project-thread-rjes21` con los PR #2, #3 y #4; los choques se resolvieron el 4-oct. La tabla «Mejoras locales recientes» de abajo ya está en la rama: el inventario regenerado la recoge.

- El Mac no cambia de rama. `preparar_noche.sh` trae de esta rama solo `migracion/`, `v2/`, `.cursor/` y `AGENTS.md`. `juntar_plan.sh` (lo lanza `noche.sh`) trae lo demás fichero a fichero, con mezcla a tres contra `main`: donde el Mac sigue en el corte 650 no hace nada, y lo que Astra cambió después se respeta.
- La instantánea de F1.3 solo recoge lo que cambió en el Mac después del corte 650, fichero a fichero. Nunca `git add -A`.
- Los ficheros privados que la entrega sacó de git (estados `_ESTADO_*.md`, catálogos y criterios, cachés y logs de fuentes; lista: `git diff --name-status main origin/codex/ro-entrega-cursor-2026-10-04 | grep ^D`) se quedan en el Mac y ya están en `.gitignore`. Nunca se vuelven a añadir.

## Qué es prioritario para el producto

1. Dirección de operaciones: recuperar todas las métricas y secciones del artifact original, con tablas densas, claras y comparables. Incluye equipo y horas, producción, planificación semanal, revisiones account/técnicas, bloqueos, proyectos, accounts, cierres y fuegos.
2. Account managers: la misma claridad aplicada exclusivamente a sus proyectos. Visión conjunta de contacto semanal, reuniones, horas frente a objetivo, revisiones, tickets y antigüedad, con detalle por cliente bajo demanda.
3. Paid: panel central sintético y detalle de cada cuenta. Separar métricas de Meta, contactos de CRM, cualificación y ventas; una coincidencia de recuentos no acredita conversión.

Fuegos significa urgencias operativas abiertas, incluidas las de días anteriores. No equivale a clientes con semáforo rojo. Solo clientes activos en las alertas operativas. El propósito es facilitar decisiones y ejecución al equipo sin saturar la pantalla ni escalar innecesariamente a dirección.

## Reglas de presentación que hay que conservar

- Números y colores como protagonistas; poco texto en las celdas. Explicaciones, criterios y fuentes en leyendas, ayuda accesible o detalle.
- Cabeceras con siglas o abreviaturas reconocibles y consistentes cuando falte espacio. Nombre completo en `title` y ARIA. Mantener unidad, ventana temporal y distinción entre dato observado y confirmado.
- No abreviar tanto que se confundan dos métricas o periodos. Por ejemplo, las ventanas de citas y asistencia son distintas.
- Verde, amarillo y rojo solo con evidencia y una regla aplicable. Ausencia de datos no es cero, cumplimiento ni incumplimiento; debe aparecer como desconocido.
- Reducir información secundaria en la parte superior. Tablas macro primero, profundización después. Mantener escritorio, móvil y la posibilidad de contraer el menú.
- No convertir histórico, referencia anterior o declaración manual en un KPI actual confirmado.

## Mejoras locales recientes que deben entrar en el inventario actualizado

Las referencias numéricas siguientes son identificadores de fases/documentos locales, no versiones de despliegue. Algunos archivos de esta lista pueden no estar aún en esta rama.

| Área | Implementación local | Comportamiento que preservar |
|---|---|---|
| Triaje | `triaje_guardia_445.py`, integración en `servir.py` | Exclusión transaccional SQLite por ticket/alias y acción validada; replay idempotente del mismo identificador bajo autoridad actual; rollback si cambian fuente o permisos. No es exclusión universal para todas las acciones. La vía PostgreSQL de esta operación devuelve 503 mientras no esté verificada. |
| Horas | `modulos/_orden_horas_artifact_447.js`, panel 262 | Orden ascendente del porcentaje medido para el mismo periodo; desconocidos al final. No recuperar valores heredados para fabricar comparaciones. |
| Paid | `modulos/_metricas_campanas_448.js`, integración 386 | Resumen de impresiones, clics, CTR, gasto y CPM de las filas de campañas recibidas en el mismo periodo. Ratios de sumas, no media de ratios diarios. No representa censo completo de cuenta ni conversión con CRM. |
| Operaciones | `modulos/_numeros_semanales_449.js`, integración 265 | Tres cifras en tabla compacta; criterio y fuente bajo demanda. Conserva la separación entre histórico y medición actual. |
| Horas | Panel 262, ajuste 450 | Celdas numéricas compactas, sin texto repetido de referencias. Pauta y cobertura explicadas fuera de las filas; conserva cálculos y colores. |
| Método e histórico | `metodo_evidencia_452.py`, `metodo_cuentas.py` | Evidencia histórica aditiva, por cohorte confirmada, procedente del archivo privado autorizado. No modifica última reunión confirmada, próxima revisión ni estado de cadencia. |
| Reuniones | `modulos/_seguimiento_metodo_453.js`, `modulos/reuniones.js` | Tabla de seguimiento quincenal; histórico separado de celebración y participación confirmadas. Enlace a la pestaña Reunión de la ficha. Revalidación de ámbito antes de interacción. |
| Cabeceras | `componentes.js`, ampliación 457 de `cabeceraCompacta421` | Vocabulario común para tablas densas y apilables, con metadatos accesibles intactos. Hay renderers específicos que aún necesitan adaptación propia. |

También se han trabajado antes el control de cartera, las vistas de producción, el rastro declarado, las referencias de planificación por creador y las miniseries de fotos compatibles. Su existencia no demuestra que todas las fuentes estén completas o que todo el artifact tenga paridad operativa. Hay un inventario local de sus funciones/secciones; debe cotejarse con la versión que realmente se migre.

## Seguridad y contratos que no deben degradarse

- Autoridad del servidor: intersección entre persona real y vista seleccionada. «Ver como» no concede permisos nuevos.
- Personas activas, roles canónicos y cartera/asignación actual; clientes activos para las acciones correspondientes.
- Contratos y datos privados reservados al rol autorizado. No confiar únicamente en ocultar componentes del navegador.
- Fuente privada de reuniones: validación de formato, permisos de archivo, integridad y ámbito. Si un cliente no aparece en el inventario, su número de registros es desconocido; solo una lista vacía explícita permite cero observado en ese corpus parcial.
- Histórico no acredita por sí solo celebración, participación del especialista ni account responsable en la fecha.
- Revalidar permisos, políticas y fuentes durante la lectura y antes de responder; invalidar vistas/callbacks si cambia el ámbito.
- Mantener cero medido, ausencia de dato, error de fuente, cobertura parcial y referencia histórica como estados distintos.
- Ninguna sincronización externa ni automatización de envíos debe activarse por defecto durante la migración o el ensayo.

## Evidencia de pruebas disponible

Pruebas focalizadas realizadas en local; no son una certificación de toda la aplicación:

- Método/histórico: 64 pruebas Python conjuntas y 9 pruebas independientes adicionales, correctas. Cubren, entre otros casos, ausencia de cliente, corrupción de fuente, colisiones e invalidación por cambios de autoridad.
- Tabla de reuniones: 19 pruebas focalizadas, además de regresiones de cadencia y cobertura, correctas. La revisión real detectó y corrigió la construcción inicial fuera del DOM y un enlace que abría una pestaña sin el histórico.
- Triaje: 52 pruebas HTTP aisladas, correctas, más revisión independiente. La exclusión se prueba en SQLite; no debe extrapolarse a PostgreSQL.
- Métricas de campañas: 23 grupos puros, 5 de renderer y 9 de regresión, correctos.
- Cabeceras: suites existentes de 16, 25 y 9 grupos, correctas. Revisión visual real en CRM, SEO y Web; prueba de Web en escritorio y móvil sin desbordamiento del documento.

Las pruebas sintéticas no acreditan cobertura de proveedores ni comportamiento exhaustivo con datos vivos. Existe al menos una incidencia anterior de una batería de integridad documentada; no se han relajado sus verificaciones para hacerla pasar. Tampoco se ha afirmado que todas las baterías globales estén verdes.

## Pendientes reales y límites

- Confirmación de celebración, asistentes/especialista y responsable histórico; cobertura del intervalo para evaluar KPIs actuales.
- Datos actuales y cobertura suficiente de contactos, llamadas, horas/capacidad, planificación, respuestas y demás indicadores. No sustituirlos por textos o ceros supuestos.
- Integración y revisión completa del artifact original en operaciones y su derivación por cartera en accounts.
- Revisión de las pantallas restantes, especialmente las tablas con renderer propio y la información secundaria superior.
- Embudo: medir etapas con fuentes tipadas, periodo, denominador y atribución; distinguir intento de contacto, respuesta, cita, asistencia, cualificación y venta. Las acciones sugeridas deben tener evidencia y un criterio posterior de comprobación.
- PageSpeed: preparar una clave nueva de Google Cloud; no se ha activado una conexión nueva en esta revisión. Confirmar también la cobertura efectiva de SE Ranking.
- Recepción de leads de webs sin CRM/WPForms: diferida expresamente; mantener en la hoja de ruta.
- Prueba de restauración operativa y ensayo completo de despliegue. No hay evidencia para declarar 10/10, objetivo completo o disponibilidad garantizada para el equipo.

## Ajustes que conviene hacer al plan de migración

Estas son recomendaciones de traspaso para quien revise el PR; esta entrega no modifica `PLAN_MAESTRO.md` ni ejecuta sus scripts.

1. Actualizar el inventario a partir del código local vigente y cotejarlo con la rama. Antes de transportar código, revisar secretos, datos reales, fuentes privadas y archivos de estado. No hacer un commit/push indiscriminado del árbol local.
2. Fijar una instantánea funcional revisada como referencia. El inventario antiguo y las fotos de una versión anterior no bastan si el producto ha cambiado.
3. Mantener la tubería Python y ClickUp/GHL mientras se migra la estructura. El puente debe conservar API, permisos, semántica de desconocidos y rutas de detalle; igualdad visual sola no acredita paridad funcional.
4. Ampliar las puertas de migración con revocación durante lectura/interacción, real frente a «ver como», fuentes parciales/corruptas, ámbitos cruzados y replay/concurrencia.
5. Añadir una puerta específica de PostgreSQL para las acciones actualmente verificadas solo en SQLite: transacciones, exclusión concurrente, replay y rollback. Un 503 conocido debe figurar como bloqueo de esa función, no como función ya migrada.
6. Usar exclusivamente fixtures sintéticos en el repositorio y en el ensayo cloud. Mantener grabaciones, bases, vectores reales, capturas con datos de negocio y credenciales fuera de GitHub.
7. No prometer fecha de despliegue por la presencia de un puente. El piloto requiere permisos reales verificados, recuperación ensayada, fuentes necesarias disponibles y funciones operativas críticas probadas.

La prioridad es conservar lo que el equipo necesita para trabajar, con claridad y seguridad, mientras se mejora la base técnica. Esta nota no autoriza publicaciones adicionales, cambios de proveedores ni un despliegue.
