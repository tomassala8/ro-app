# Formato de `data/modular/webs.json` (N5 · Modular DS)

Lo escribe `fuentes_modular/generar_modular.py`. Solo lectura de la API pública de Modular DS. Sin clave, el fichero existe igual con `_meta.estado = "sin_conectar"` y listas vacías: **nunca** pintar verdes con él.

## Claves de primer nivel
| Clave | Qué es |
|---|---|
| `_meta` | `generado`, `leido`, `estado` (`conectado` / `sin_conectar`), `motivo` y `que_hacer` si no conecta, `errores_parciales` (p. ej. el rol de la clave no ve copias → 404 en esa parte), `enlace` (panel de Modular), `doc_api` |
| `resumen` | `webs_modular`, `emparejadas`, `sin_cliente`, `clientes_con_web_fuera_de_modular`, `rojo`, `ambar`, `verde`, `gris`, `caidas_ahora`, `vulnerabilidades_graves`, `actualizaciones_pendientes` |
| `webs[]` | Una fila por web de Modular **emparejada** con un cliente (por dominio, con o sin `www`, admite subdominio) |
| `sin_cliente[]` | Webs de Modular que no casan con ningún cliente activo (la nuestra, pruebas, bajas): `modular_id, nombre, dominio, estado, motivos` |
| `clientes_sin_modular[]` | Clientes con web en su ficha que no están en Modular |
| `alertas[]` | Todas las incidencias de todas las webs, ya en el formato de N4 (abajo) |

## Fila de `webs[]`
`modular_id, nombre, dominio, url, cliente_id, cliente, web_id, web_nombre` (persona principal de web según `data/verdad/clientes.json`), `conectada, wordpress, php, sincronizada`,
`disponibilidad {monitor, estado up|down|unknown, desde, ultimo_ping, codigo, ms, error, ultima_caida}`,
`copias {ultima, fase_ultima, ultima_buena, dias_sin_copia_buena, total, espacio_mb}` (null si el rol no ve copias),
`actualizaciones {pendientes, detalle[≤30] {tipo, nombre, de, a, con_vulnerabilidad}}`,
`vulnerabilidades {total, criticas, altas, sin_parche, lista[≤10] {gravedad, componente, tipo, nombre, sin_parche, fuente}}`,
`certificado {dias, caduca, estado}` (solo con `--certificados`),
`estado` (`rojo` / `ambar` / `verde` / `gris`), `motivos[]` (el peor primero), `incidencias[]`.

Nota sobre «última caída»: la API da el estado actual y **desde cuándo**. Si está caída, `ultima_caida` = inicio de la caída. Si está arriba, `desde` = cuando volvió (o cuando empezó a vigilarse); el historial completo de caídas no lo da la API pública.

## Incidencia (formato para N4 · alertas de web)
```json
{"id": "modular:<regla>:<modular_id>", "departamento": "web", "regla": "web_caida",
 "gravedad": "rojo|ambar", "cliente_id": "busbac" | null, "web": "busbac.com",
 "titulo": "La web está caída", "texto": "…", "que_hacer": "…",
 "fuente": "Modular DS", "fuente_enlace": "https://app.modulards.com/",
 "detectado": "2026-10-02 18:00", "desde": "2026-10-02T10:00:00Z" | null}
```
`id` es estable: N4 lo usa para no duplicar y para cerrar la alerta cuando deja de salir.

| Regla | Gravedad | Cuándo |
|---|---|---|
| `web_caida` | rojo | Monitor encendido y estado `down` |
| `copia_nunca` | rojo | Ninguna copia buena |
| `copia_atrasada` | ámbar ≥ 2 días · rojo ≥ 7 días | Días desde la última copia buena |
| `vulnerabilidad` | rojo si hay crítica · ámbar si solo alta | Vulnerabilidades conocidas de gravedad crítica o alta |
| `actualizaciones` | ámbar | 5 o más pendientes |
| `modular_desconectada` | ámbar | Modular no conecta con el WordPress |
| `certificado` | ámbar ≤ 14 días · rojo ≤ 3 | Solo con `--certificados` |

Dueño de la alerta: `web_id` de la fila (persona principal de web del cliente). Sin `cliente_id` → solo la ve dirección y el responsable del equipo web (como las filas sin cliente del resto de la app).

## Para el dueño de SEO/webs (`modulos/seo.js`, pestaña «Webs»)
- Cruce por `cliente_id` con `data/seo/webs.json` (`cliente`). Modular **complementa** al monitor propio: el monitor dice si responde desde la IP de RO; Modular dice si responde desde fuera, copias, actualizaciones y seguridad. Con los dos: caída de verdad = falla en ambos; «bloqueada solo para RO» = Modular `up` y monitor de RO en rojo.
- Columnas sugeridas: Copia (días desde la última buena), Actualizaciones (n.º), Seguridad (críticas/altas), Fuera de RO (up/down). Si `_meta.estado = "sin_conectar"`: una sola etiqueta gris «Modular sin conectar» con `que_hacer`.
- Alta pendiente en `reglas_permisos.json → datos_de_modulo` (fichero común, no lo he tocado): `"modular/webs": ["seo-web"]`, igual que `seo/webs`.

## Cómo se refresca
`python3 fuentes_modular/generar_modular.py` (≈ 6-15 peticiones; el límite es 120 por minuto). Cada hora es más que suficiente: el monitor de Modular mira cada 2-15 min según plan y avisa él mismo por correo o WhatsApp.

## Ampliación 3-oct (encargo «Modular en cada cliente y para el equipo web»)
- **Lectura**: cada hora (paso `modular` de `despliegue/pasos.json`, `cada_min` 55) las listas globales (webs, disponibilidad, copias, vulnerabilidades, actualizaciones, malware `/site-scans`) y, **por turnos**, el detalle de 8 webs (17 en la completa) + las caídas: `/sites/{id}/uptime` (1 d · 7 d · 30 d), `/sites/{id}/health`, `/site-broken-link-issues/stats`, `/sites/{id}/certificate`. Guardado en `_cache/detalle.json`. Nunca `/sites/count` (eso es del vigía); si el vigía ve la clave rota hace < 20 min, no se llama y se marca `_meta.dato_viejo`. Solo GET.
- **Fila nueva**: `account_id/nombre`, `dueno_id/dueno` (web del cliente o, sin persona, el jefe de web), `enlace_modular` + `enlace_nota` (la API no da la URL de cada web en el panel), `disponibilidad.dia/semana/mes`, `monitor_ro` (monitor propio desde la IP de RO), `actualizaciones.nucleo/plugins/temas`, `vulnerabilidades.medias/bajas`, `certificado` (Modular o, si no lo vigila, monitor de RO con `fuente`), `salud`, `malware`, `enlaces_rotos`, `detalle_leido`, `problemas[]` ({clave, gravedad, titulo, detalle, accion, dueno}) y `urgencia` (orden del tablero). `sin_cliente[]` lleva ya la fila entera.
- **Caída «solo desde fuera»**: Modular `down` y el monitor de RO responde → `web_caida` en ámbar con el porqué (p. ej. octoedro.com: Modular recibe 301 y solo acepta 2xx).
- **`data/modular/tablero.json`**: todas las webs con clave `cliente` (sin `cliente_id`) + `fuera_de_modular[]`; solo web, jefa_seo, operaciones y dirección.
- **Alertas (N4)**: `de_modular()` lee `webs.json › alertas` → reglas `modular_caida`, `modular_copia` (> 2 días o ninguna), `modular_vulnerabilidad` (solo críticas), `modular_certificado` (< 15 días); dueño = silla web; van a #avisos-web.
- **Acceso de un clic** (`POST /api/modular/acceso`, `acceso.py`): tipo `modular_acceso` (web, jefa_seo, direccion), rastro `modular_acceso[_denegado]`; **apagado** hasta interruptor + `RO_MODULAR_ACCESO=si` + clave aparte `modulards_acceso_key`.
