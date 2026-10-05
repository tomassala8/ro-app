# Navegación y Paid · verificación final para Cursor

4 de octubre de 2026. Sólo lectura del producto; los seis archivos entregados mantienen RELEASE2/4/5 y sus hashes. La publicación de `codex/ro-entrega-cursor-2026-10-04` corresponde al root y no se verificó desde este chat.

**Comprobado con fixtures:** navegación163 + regresión26; catálogo11, consejo16 y menú418 once grupos; Paid33 casos RELEASE5 + diez RELEASE4 + catorce suites con las dos adaptaciones conocidas; navegador Paid97 comprobaciones, cero solicitudes de red. Menús conservan rutas autorizadas, doce accesos primarios cuando procede y «Más» por rol; búsqueda/Escape/foco y preferencia del consejo pasan. Captación conserva tabla compacta/detalle; Meta conserva siglas/title/ARIA, leyenda y contexto cerrado. A1326/390px, incluso con nombres Meta extensos, no hay desbordamiento del documento y la primera fila del fixture queda por debajo de300px.

**Pendientes concretos, sin corregir en esta revisión:**

| Prioridad | Ubicación relativa en la app | Defecto y criterio para Cursor |
|---|---|---|
| P1 | `modulos/captacion.js:773`, `:782`, `:787` — Por trafficker | Gravedad ausente termina en cero críticos y la tarjeta de equipo puede quedar verde; «paradas» vacía también termina en verde sin cobertura de observación. Añadir cobertura/null a estas proyecciones secundarias; conservar cero observado, sin acreditarlo como universo. Es lectura de ramas, no reproducción en UI real. |
| P1 | `modulos/captacion.js:319`, `:321`, `:822` — agregados secundarios | Señales/rechazos y gasto/contadores por nicho usan `||0`. Datos ausentes pueden aparecer como cero. Propagar ausencia/cobertura y mantener permisos/unidad/ventana; no rescatar legacy para fabricar CPL real. |
| P1 | `modulos/captacion.js:1314` — anuncios de una cuenta | Las tarjetas individuales «Cansadas», «Con una señal» y «Rechazados» aún colorean cero legacy verde sin validar lectura/cobertura. RELEASE4 neutralizó la matriz/vista general, no este consumidor. Aplicar la misma distinción entre señal histórica y evaluación acreditada. |
| P2 | `estilos.css` — `.vacio` / `.vacio-g` en640px y escritorio | El fixture extremo sin separadores sigue desbordando:640→1377px y1366→1401px.390/639 están contenidos y los casos cortos pasan. Revisar contención en el límite640/escritorio, preservando tablas y acciones. Evidencia en `VERIFICACION_FINAL_resultados.json`. |
| P2 | `modulos/captacion.js:1306` — vacío de campañas | Sin filas, el copy afirma que la cuenta no ha gastado desde agosto sin acreditar exhaustividad. Cambiar a ausencia de filas en la copia con cobertura/fecha, evitando inferir ausencia de actividad. Hallazgo por código. |
| P2 | `pruebas_captacion_compacta_243.cjs`, `pruebas_matriz_paid_508.cjs` | Las originales siguen fallando porque exigen «Sin res.» en tabla; RELEASE4 la trasladó a «Ver». Actualizar oficialmente las expectativas manteniendo racha/error/reserva/detalle; actualmente sólo pasan adaptadas en memoria. Fallos originales repetidos y registrados en `VERIFICACION_FINAL_originales243_508.json`. |

CPC/CTR de cuenta y antigüedad del creativo siguen pendientes de descriptor compatible: no convertir el CTR de enlace de Paneles ni la fecha de lectura en esas métricas. Los objetivos pueden seguir con‡ si falta ratificación/vigencia; no rebajar `medirCplPaid` para colorearlos.

Evidencias: `VERIFICACION_FINAL_suites.json`, `VERIFICACION_FINAL_resultados.json`, `VERIFICACION_FINAL_regresion_dom.json`, `VERIFICACION_FINAL_PAID_browser.json`, `VERIFICACION_FINAL_hashes.json` y capturas exclusivamente sintéticas. Las suites adaptadas no ocultan los dos fallos originales.

Sin cambios de producto/runtime/config/datos, HTTP real, UI real, proveedores, DB, Git, migración/v2 o nuevos agentes. No se certifican todos los roles reales, recortes económicos generales, otros paneles ni una UI perfecta. Las pruebas de presentación no sustituyen una validación completa de permisos y datos en el entorno de entrega.
