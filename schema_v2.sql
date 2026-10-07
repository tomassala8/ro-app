-- schema_v2.sql · base de la app de RO (E0, 2-oct-2026). NO DESPLEGADA.
-- Amplía ~/RO_HERRAMIENTAS/servidor_panel/schema.sql (acciones, registro, docs, historial) y recoge la
-- propuesta schema_fase0.sql (personas, persona_puestos, asignaciones, suplencias), con los 21 puestos de la app.
-- Sirve igual para SQLite local (local.db, servir.py) y para D1 de Cloudflare (W1): solo SQL estándar de SQLite.
--
-- Reglas que la base hace cumplir sola:
--   · Rastro imborrable: `registro`, `historial` y `acciones` no admiten UPDATE ni DELETE (disparadores).
--     Desmarcar = una fila nueva con anula_a = id de la fila anulada (regla R14).
--   · «No aplica» exige motivo (CHECK).
--   · Sin sueldos ni contraseñas: no hay columnas para ellos.
--   · Hora del servidor (DEFAULT de la base), nunca la del navegador.

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------------ personas
CREATE TABLE IF NOT EXISTS personas (
  id            TEXT PRIMARY KEY,
  nombre        TEXT NOT NULL,
  alias         TEXT,                          -- alias corto para la interfaz («Coti», «Jessi»)
  alias_todos   TEXT,                          -- JSON
  correo        TEXT UNIQUE,                   -- correo de RO con el que entra (Cloudflare Access); NULL = aún no puede entrar
  otros_correos TEXT,                          -- JSON
  nivel         INTEGER CHECK (nivel BETWEEN 1 AND 7),
  jefe_id       TEXT,
  horas_mes     REAL NOT NULL DEFAULT 128,     -- D-25
  imputa_horas  TEXT,                          -- 'sí' | 'no'
  estado        TEXT NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo','dudoso','por_incorporar','baja')),
  activo        INTEGER NOT NULL DEFAULT 1,
  nota          TEXT,
  actualizado   TEXT NOT NULL DEFAULT (datetime('now')),
  actualizado_por TEXT
);

-- Varios puestos por persona (D-01). Puestos = los 21 de reglas_permisos.json.
CREATE TABLE IF NOT EXISTS persona_puestos (
  persona_id  TEXT NOT NULL REFERENCES personas(id),
  puesto      TEXT NOT NULL CHECK (puesto IN (
                'direccion','finanzas_direccion','administracion','operaciones','proyectos','rrhh','account',
                'trafficker','jefa_publicidad','especialista_ghl','jefa_crm','tecnico_altas','jefa_seo','seo',
                'ficha_google','web','redes','produccion','setters','ventas_ro','outreach')),
  principal   INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (persona_id, puesto)
);

-- ------------------------------------------------------------------ asignaciones
-- Cliente × persona × silla. Vigente = (desde IS NULL o desde <= hoy) y (hasta IS NULL o hasta >= hoy).
-- Nada se borra: un cambio cierra la fila con «hasta» y abre otra.
CREATE TABLE IF NOT EXISTS asignaciones (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente_id  TEXT NOT NULL,                   -- id de la app (slug del panel); el del portal va en cliente_id_portal
  cliente_id_portal TEXT,
  persona_id  TEXT NOT NULL,
  silla       TEXT NOT NULL CHECK (silla IN ('account','trafficker','crm','ghl','seo','web','redes','produccion','outreach')),
  principal   INTEGER NOT NULL DEFAULT 1,
  suplencia   INTEGER NOT NULL DEFAULT 0,
  titular_id  TEXT,                            -- solo suplencias
  desde       TEXT,
  hasta       TEXT,
  fuente      TEXT,
  confianza   TEXT CHECK (confianza IN ('alta','media','baja','confirmada')),
  duda        TEXT,
  creado      TEXT NOT NULL DEFAULT (datetime('now')),
  creado_por  TEXT,
  CHECK (suplencia = 0 OR hasta IS NOT NULL)   -- no hay suplencias sin fecha de fin
);
CREATE INDEX IF NOT EXISTS i_asig_persona ON asignaciones(persona_id, hasta);
CREATE INDEX IF NOT EXISTS i_asig_cliente ON asignaciones(cliente_id, silla, hasta);

CREATE VIEW IF NOT EXISTS v_cartera_hoy AS
  SELECT persona_id, cliente_id, silla, CASE WHEN suplencia = 1 THEN 'suplencia' ELSE 'titular' END AS via
    FROM asignaciones
   WHERE (desde IS NULL OR desde <= date('now')) AND (hasta IS NULL OR hasta >= date('now'));

-- ------------------------------------------------------------------ rastro (imborrable)
-- Una fila por cosa que pasa: ver como, ver datos de un lead, cambiar una asignación, marcar algo…
CREATE TABLE IF NOT EXISTS registro (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  creada      TEXT NOT NULL DEFAULT (datetime('now')),   -- hora del servidor
  quien       TEXT NOT NULL,                             -- persona real (en producción: correo de Access)
  como        TEXT,                                      -- persona vista con «ver como» (si aplica)
  coleccion   TEXT NOT NULL,                             -- modulo o colección del panel (registro, rituales, rojos…)
  accion      TEXT,                                      -- ver_como | ver_lead | marcar | no_aplica | cambio_asignacion…
  clave       TEXT,                                      -- sobre qué (cliente, alarma, persona…)
  datos       TEXT,                                      -- JSON
  motivo      TEXT,
  anula_a     INTEGER REFERENCES registro(id),           -- desmarcar = anular, nunca borrar
  origen      TEXT NOT NULL DEFAULT 'app',               -- app | panel_v7 (importado del artefacto)
  CHECK (accion IS NULL OR accion <> 'no_aplica' OR (motivo IS NOT NULL AND length(trim(motivo)) > 0))
);
CREATE INDEX IF NOT EXISTS i_reg_col ON registro(coleccion, clave);
CREATE INDEX IF NOT EXISTS i_reg_quien ON registro(quien, creada);
CREATE TRIGGER IF NOT EXISTS registro_sin_update BEFORE UPDATE ON registro BEGIN SELECT RAISE(ABORT, 'El rastro no se modifica: crea una anulación'); END;
CREATE TRIGGER IF NOT EXISTS registro_sin_delete BEFORE DELETE ON registro BEGIN SELECT RAISE(ABORT, 'El rastro no se borra: crea una anulación'); END;

-- Cambios de personas y asignaciones hechos desde «Ajustes», con antes y después.
CREATE TABLE IF NOT EXISTS historial (
  n           INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          TEXT NOT NULL DEFAULT (datetime('now')),
  quien       TEXT NOT NULL,
  coleccion   TEXT NOT NULL,                   -- personas | asignaciones | decisiones | docs…
  id          TEXT NOT NULL,
  operacion   TEXT NOT NULL,                   -- crear | cambiar | cerrar | confirmar
  antes       TEXT,                            -- JSON
  datos       TEXT                             -- JSON (después)
);
CREATE TRIGGER IF NOT EXISTS historial_sin_update BEFORE UPDATE ON historial BEGIN SELECT RAISE(ABORT, 'El historial no se modifica'); END;
CREATE TRIGGER IF NOT EXISTS historial_sin_delete BEFORE DELETE ON historial BEGIN SELECT RAISE(ABORT, 'El historial no se borra'); END;

-- ------------------------------------------------------------------ acciones (botones)
-- En el prototipo todas quedan «simulada» con su vista previa; con W1 pasan a «pendiente» → «ok» | «error».
CREATE TABLE IF NOT EXISTS acciones (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  creada      TEXT NOT NULL DEFAULT (datetime('now')),
  quien       TEXT NOT NULL,
  herramienta TEXT NOT NULL,                   -- desk | clickup | ghl | meta | zadarma | sign | metricool | app
  tipo        TEXT NOT NULL,                   -- responder | cerrar | asignar | nota | cerrar_tarea | mover_tarea…
  objeto      TEXT NOT NULL,                   -- id del ticket, tarea, contacto…
  cliente_id  TEXT,
  modulo      TEXT,
  texto       TEXT,                            -- lo que se enviaría (siempre visible antes)
  vista_previa TEXT,                           -- JSON: qué haría exactamente
  estado      TEXT NOT NULL DEFAULT 'simulada' CHECK (estado IN ('simulada','pendiente','ok','error')),
  resultado   TEXT,
  detalle     TEXT
);
CREATE INDEX IF NOT EXISTS i_acc_obj ON acciones(objeto);
CREATE TRIGGER IF NOT EXISTS acciones_sin_delete BEFORE DELETE ON acciones BEGIN SELECT RAISE(ABORT, 'Las acciones no se borran'); END;

-- ------------------------------------------------------------------ incidencias (regla R13)
CREATE TABLE IF NOT EXISTS incidencias (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  creada      TEXT NOT NULL DEFAULT (datetime('now')),
  quien       TEXT NOT NULL,                   -- quien escala
  cliente_id  TEXT,
  titulo      TEXT NOT NULL,
  donde       TEXT CHECK (donde IN ('publicidad','despacho','integracion','produccion','contacto_cliente')),
  por_que     TEXT CHECK (por_que IN ('sistema','configuracion','ejecucion','gestion_operaciones')),
  por_que_cambiado_por TEXT,                   -- Tomás puede cambiar la causa (D-37)
  prueba_aviso TEXT,                           -- sin prueba de aviso cuenta como gestión de Operaciones (D13)
  estado      TEXT NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta','en_curso','resuelta','descartada')),
  responsable_id TEXT,
  cerrada     TEXT,
  datos       TEXT
);

-- ------------------------------------------------------------------ decisiones
-- «Para Tomás» (reloj de 48 h) y las respuestas de Mili a «Para confirmar».
CREATE TABLE IF NOT EXISTS decisiones (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  creada      TEXT NOT NULL DEFAULT (datetime('now')),
  quien       TEXT NOT NULL,
  tipo        TEXT NOT NULL,                   -- para_tomas | para_confirmar
  clave       TEXT,                            -- D-xx, A1…
  problema    TEXT,
  recomendacion TEXT,
  respuesta   TEXT,                            -- JSON (para_confirmar: formato de respuestas_mili.json)
  respondida  TEXT,
  respondida_por TEXT,
  anula_a     INTEGER REFERENCES decisiones(id),
  titulo      TEXT,                            -- ronda 4: qué hay que decidir, en una línea
  cliente_id  TEXT,
  datos       TEXT                             -- JSON: opciones, fecha límite, prueba…
);

-- ------------------------------------------------------------------ docs (compatibilidad con el artefacto)
CREATE TABLE IF NOT EXISTS docs (
  coleccion TEXT NOT NULL, id TEXT NOT NULL, datos TEXT NOT NULL, uid TEXT, ts TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (coleccion, id)
);

-- ------------------------------------------------------------------ E0 ronda 3: «Actualizar ahora» y avisos
-- Cola de recargas pedidas desde la cabecera (solo Mili y Tomás). Una a la vez; los pasos salen de recarga.json.
CREATE TABLE IF NOT EXISTS recargas (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  pedida      TEXT NOT NULL DEFAULT (datetime('now')),
  quien       TEXT NOT NULL,
  modo        TEXT NOT NULL DEFAULT 'ligera',
  estado      TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','en_curso','ok','con_fallos')),
  empezada    TEXT,
  terminada   TEXT,
  pasos       TEXT                             -- JSON: [{id, ok, segundos, salida (últimas líneas)}]
);
CREATE TRIGGER IF NOT EXISTS recargas_sin_delete BEFORE DELETE ON recargas BEGIN SELECT RAISE(ABORT, 'Las recargas no se borran'); END;

-- Avisos a Tomás cuando algo falla. Como mucho 3 «para avisar» al día; el resto queda «retenido» (se ve en Ajustes).
-- La notificación real (escritorio y móvil) llega con W1; en el prototipo se ven en Ajustes › Avisos.
CREATE TABLE IF NOT EXISTS avisos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  creado      TEXT NOT NULL DEFAULT (datetime('now')),
  dia         TEXT NOT NULL,                   -- AAAA-MM-DD (para el tope de 3 al día y no repetir)
  tipo        TEXT NOT NULL,                   -- fuente_rota | fuente_vieja | recarga_fallida
  clave       TEXT NOT NULL,                   -- id de la fuente o del paso
  texto       TEXT NOT NULL,                   -- una línea
  estado      TEXT NOT NULL DEFAULT 'para_avisar' CHECK (estado IN ('para_avisar','retenido')),
  visto       TEXT,
  visto_por   TEXT,
  UNIQUE (dia, tipo, clave)
);

-- ------------------------------------------------------------------ F5.10 · N-01: copia propia de lo que llega de las APIs
-- Una fila por lectura de una API (buena o con error). La escribe solo fuentes/lectura.py › leer().
-- Si la API falla, da cero o vacío, se sirve la última buena con su hora: nunca un 0 ni un vacío.
-- Se guardan las 30 últimas buenas por fuente y recurso y 30 días de errores (lectura.podar). Sin disparador de borrado.
CREATE TABLE IF NOT EXISTS fuente_lectura (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  fuente      TEXT NOT NULL,                   -- gsc | metricool | ghl | hostinger | holded…
  recurso     TEXT NOT NULL,                   -- cliente, cuenta o subcuenta ('' si la fuente es una sola)
  hora        TEXT NOT NULL DEFAULT (datetime('now')),
  ok          INTEGER NOT NULL CHECK (ok IN (0,1)),
  codigo      TEXT,                            -- en error: código HTTP, «vacio», «a_cero», «sospechoso» o la excepción
  error       TEXT,                            -- una línea
  cuerpo      TEXT,                            -- JSON de lo que devolvió la API
  huella      TEXT                             -- sha256 del JSON canónico
);
CREATE INDEX IF NOT EXISTS i_fuente_lectura ON fuente_lectura(fuente, recurso, ok, id);

CREATE VIEW IF NOT EXISTS fuente_ultimo_bueno AS
  SELECT f.* FROM fuente_lectura f
   WHERE f.ok = 1
     AND f.id = (SELECT MAX(g.id) FROM fuente_lectura g WHERE g.fuente = f.fuente AND g.recurso = f.recurso AND g.ok = 1);
