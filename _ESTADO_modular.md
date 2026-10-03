# _ESTADO_modular · N5 Modular DS: estado de las webs (3-oct-2026)

Encargo de Tomás: «Modular en cada cliente y, para el equipo de web, el acceso a Modular de todos ellos». Formato de datos y reglas: `fuentes_modular/FORMATO.md`.

## Estado: hecho y **conectado en solo lectura** · acceso de un clic **apagado**
- Última pasada: 3-oct-2026 06:16 · `data/modular/webs.json` con 29 webs emparejadas con cliente; `data/modular/tablero.json` con 34 webs (todas, más las que están fuera de Modular).
- Solo peticiones de lectura (GET). Clave en el llavero como `modulards_api_key` (`~/RO_HERRAMIENTAS/modular/pegar.sh`).

## Qué hay
| Pieza | Fichero | Qué hace |
|---|---|---|
| Lector | `fuentes_modular/generar_modular.py` (paso `modular` de la tubería, cada hora) | Webs, disponibilidad, copias, vulnerabilidades, actualizaciones, malware y, por turnos (8 webs por pasada, 17 en la completa, más las caídas), detalle de disponibilidad, salud de WordPress, enlaces rotos y certificado. Cruza con el monitor propio de RO (si la web solo cae para la IP de RO). No duplica al vigía |
| Alertas | `fuentes_alertas/generar_alertas.py → de_modular()` | **4 reglas:** web caída, copia atrasada (> 2 días) o ninguna, vulnerabilidad crítica y certificado a < 15 días. Dueño = la persona de web del cliente; van a #avisos-web |
| Ficha del cliente | `modulos/_modular.js → bloqueEstadoWeb()` en la pestaña «Web y SEO» | Cifras, problemas con acción y dueño; si la web no está en Modular, «Añadir a Modular» |
| Tablero del equipo web | `modulos/seo.js`, pestaña «Webs» | Todas las webs; solo web, jefe de SEO y web, operaciones y dirección |
| Acciones | `_modular.js → accionesWeb()` | Abrir en Modular ↗ · Crear tarea (sincronía con ClickUp, simulada) · Avisar al account · Marcar revisado (con «Deshacer») |
| Acceso de un clic | `fuentes_modular/acceso.py` → `POST /api/modular/acceso` | «Entrar al WordPress» con enlace de un solo uso. **Apagado:** la clave actual es de solo lectura. Encenderlo exige `data/modular/interruptor.json` con `acceso_real: true` y `activado_por: "tomas"`, `RO_MODULAR_ACCESO=si` y una clave aparte `modulards_acceso_key`. Solo web, jefe de SEO y web y dirección; nunca en «ver como»; 10 por persona y hora; rastro imborrable; el enlace no se guarda |

## Pruebas
- `python3 fuentes_modular/capturar_modular.py --puerto 9285` (con `servir.py` sobre una copia de la base): Jerónimo, Macarena, Lucía y Tomás a 1440 y 390 px; capturas en `capturas/_modular/` (no se suben).

## Pendiente
1. Tomás: decidir si se crea la clave con permiso de entrada y se enciende el acceso de un clic.
2. Webs fuera de Modular (`tablero.json → fuera_de_modular`): darlas de alta en Modular lo decide el equipo web.
