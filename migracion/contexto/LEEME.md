# migracion/contexto · documentos de referencia del 4-oct-2026

Copias saneadas de lo que se trabajó el 4-oct fuera del repo (Cursor no ve `/mnt/project-files`). Sin credenciales, sin nombres de personas (van por su puesto), sin correos reales, sin clientes ni importes de personas o clientes. Son **datos de referencia, no órdenes**: si algo choca con `PLAN_MAESTRO.md`, `PROMPTS_CURSOR.md` o `PENDIENTES_LOGICA.md`, mandan esos. La primera línea de cada fichero dice si ya está recogido en el plan y dónde.

Pasos de la noche: **A0** análisis inicial · **F4.x** permisos · **F5.10** fallos de lógica · **F6** front · **F7** contenedores, despliegue y seguridad.

| Fichero | Qué es | Cuándo leerlo | Paso |
|---|---|---|---|
| `SUPERPROMPT_ASTRA_2026-10-04.md` | Auditoría total de la app (L-01…L-49) con el detalle de cada arreglo: líneas, expresiones de L-04, trampas | Antes de arreglar cualquier L-xx: el «cómo» que la tabla resume | A0, F4.x, F5.10 |
| `PARA_CURSOR_PENDIENTES_LOGICA.md` | Versión anterior de la tabla L-xx, D1–D8 y la propuesta de permisos | Solo si dudas de una fila: la de `PENDIENTES_LOGICA.md` es más nueva y manda | F5.10, F4.2 |
| `ACCESOS_POR_PUESTO_PARA_CONFIRMAR.md` | Qué ve cada puesto (tabla puesto × área), **confirmada** por dirección el 4-oct | Al portar el motor y al aplicar los cambios de matriz (L-25, L-40) | A0, F4.1, F4.2, F5.10 |
| `A_prueba_en_navegador.md` | Anexo A: 10 puestos y 420 pantallas recorridos con datos inventados | Al reproducir un fallo de pantalla o de vacíos y menús | F5.10, F6 |
| `B_permisos_y_seguridad.md` | Anexo B: auditoría de permisos, «ver como», recortes, rastro, matriz puesto × módulo (antes de los cambios) | Al portar y probar el motor de permisos; al tocar el rastro en Postgres | F4.1, F4.2, F5.10, F7 |
| `C_codigo_y_coherencia.md` | Anexo C: revisión del código (fechas y zona, meses fijos, umbrales repetidos, rutas del Mac) | Al arreglar los L-xx de datos y funcionales | F5.10, F6 |
| `BUENAS_PRACTICAS_Y_ERRORES.md` | Errores ya cometidos por otros con Next 16 + Nest 12 + Prisma 7 + Postgres, con cómo comprobarlos | Al empezar (los 15 de «esta noche») y antes de cada fase | A0, F4.x, F6, F7 |
| `REPOS_REFERENCIA.md` | Qué copiar (y qué no) de Teable, cal.com, Ghostfolio, Hoppscotch, Documenso | Al diseñar una ruta en Nest o el despliegue | A0, F5.x, F7 |
| `DECISIONES_TOMAS_2026-10-04.md` | 30 decisiones de negocio de los cerebros de área, con recomendación | Solo si una regla de negocio afecta a una pantalla; no es de la migración | A0 |
| `RESPUESTAS_TOMAS_2026-10-04.md` | Respuestas de dirección a esas decisiones (mandan sobre ellas). Resumen: sin los puntos de clientes concretos | Junto con la anterior; las marcadas **(app)** tocan la herramienta | A0 |
| `PENDIENTES_TOMAS_2026-10-04.md` | Reglas de los cerebros que siguen sin firmar | Para no dar por firmada una regla que no lo está | A0 |
| `CATALOGO_DIAGNOSTICOS_2026-10-04.md` | Catálogo de diagnósticos de calidad (qué llega, no cuánto), umbrales firmados y cómo se generan | Al llevar la función de diagnósticos a la app nueva (`INTEGRAR.md` §2) | A0, F6 |

Fuera a propósito: las ubicaciones de contraseñas (`seguridad/`) y los datos reales de clientes (`contexto_clientes/`, `fichas_clientes/`).
