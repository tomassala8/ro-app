-- actas.py
CREATE TABLE IF NOT EXISTS actas_lotes (quien TEXT NOT NULL, cliente_id TEXT NOT NULL, huella TEXT NOT NULL, resultado TEXT NOT NULL, PRIMARY KEY (quien, cliente_id, huella));

-- actas.py
CREATE TABLE IF NOT EXISTS actas_claves (quien TEXT NOT NULL, clave TEXT NOT NULL, cliente_id TEXT NOT NULL, huella TEXT NOT NULL, PRIMARY KEY (quien, clave));

-- altas_personas.py
CREATE TABLE IF NOT EXISTS altas_recibos (
  clave TEXT PRIMARY KEY, quien TEXT NOT NULL, persona_id TEXT NOT NULL,
  resultado TEXT NOT NULL, correo_guardado INTEGER NOT NULL DEFAULT 0,
  lista_guardada INTEGER NOT NULL DEFAULT 0);

-- altas_personas.py
CREATE TABLE IF NOT EXISTS altas_tareas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  creada TEXT NOT NULL DEFAULT (datetime('now')),
  para TEXT NOT NULL,                                -- tomas | mili_o_tomas
  tipo TEXT NOT NULL CHECK (tipo IN ('access_anadir','access_quitar','repartir_cartera')),
  persona_id TEXT NOT NULL,
  texto TEXT NOT NULL,                               -- en llano y SIN el correo (el correo vive en data/_privado)
  quien TEXT NOT NULL,
  estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','hecha')),
  hecha TEXT, hecha_por TEXT);

-- altas_personas.py
CREATE TRIGGER IF NOT EXISTS altas_tareas_sin_delete BEFORE DELETE ON altas_tareas BEGIN SELECT RAISE(ABORT, 'Una tarea no se borra'); END;

-- altas_personas.py
CREATE TRIGGER IF NOT EXISTS altas_tareas_solo_estado BEFORE UPDATE ON altas_tareas
  WHEN NEW.para IS NOT OLD.para OR NEW.tipo IS NOT OLD.tipo OR NEW.persona_id IS NOT OLD.persona_id OR NEW.texto IS NOT OLD.texto
    OR NEW.quien IS NOT OLD.quien OR NEW.creada IS NOT OLD.creada OR OLD.estado = 'hecha'
  BEGIN SELECT RAISE(ABORT, 'De una tarea solo se marca «hecha», una vez'); END;

-- avisos.py
CREATE TABLE IF NOT EXISTS canal_grupos (
  id TEXT PRIMARY KEY, nombre TEXT NOT NULL, cliente_id TEXT, creado_por TEXT NOT NULL,
  creado TEXT NOT NULL DEFAULT (datetime('now')));

-- avisos.py
CREATE TABLE IF NOT EXISTS canal_miembros (
  n INTEGER PRIMARY KEY AUTOINCREMENT, canal_id TEXT NOT NULL, persona_id TEXT NOT NULL,
  operacion TEXT NOT NULL CHECK (operacion IN ('anadir','quitar')), quien TEXT NOT NULL,
  hora TEXT NOT NULL DEFAULT (datetime('now')));

-- avisos.py
CREATE TABLE IF NOT EXISTS canal_mensajes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, canal_id TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('mensaje','aviso','evento')), quien TEXT, texto TEXT NOT NULL, hilo_de INTEGER,
  menciones TEXT, clave TEXT UNIQUE, alerta_id TEXT, cliente_id TEXT, dueno_id TEXT, vence TEXT, ver TEXT, datos TEXT,
  creado TEXT NOT NULL DEFAULT (datetime('now')));

-- avisos.py
CREATE INDEX IF NOT EXISTS canal_mensajes_canal ON canal_mensajes (canal_id, id);

-- avisos.py
CREATE TABLE IF NOT EXISTS canal_leidos (
  persona_id TEXT NOT NULL, canal_id TEXT NOT NULL, ultimo_id INTEGER NOT NULL, hora TEXT NOT NULL,
  PRIMARY KEY (persona_id, canal_id));

-- avisos.py
CREATE TABLE IF NOT EXISTS canal_preferencias (
  persona_id TEXT PRIMARY KEY, silenciados TEXT, hora_resumen TEXT, actualizado TEXT);

-- avisos.py
CREATE TABLE IF NOT EXISTS canal_resumenes (
  persona_id TEXT NOT NULL, dia TEXT NOT NULL, titulo TEXT, texto TEXT, datos TEXT,
  creado TEXT NOT NULL DEFAULT (datetime('now')), PRIMARY KEY (persona_id, dia));

-- avisos.py
CREATE TABLE IF NOT EXISTS canal_campana (
  persona_id TEXT PRIMARY KEY, hasta_id INTEGER NOT NULL DEFAULT 0, resumen_visto TEXT, hora TEXT);

-- avisos.py
CREATE TRIGGER IF NOT EXISTS canal_mensajes_sin_update BEFORE UPDATE ON canal_mensajes BEGIN SELECT RAISE(ABORT, 'Un mensaje no se cambia'); END;

-- avisos.py
CREATE TRIGGER IF NOT EXISTS canal_mensajes_sin_delete BEFORE DELETE ON canal_mensajes BEGIN SELECT RAISE(ABORT, 'Un mensaje no se borra'); END;

-- avisos.py
CREATE TRIGGER IF NOT EXISTS canal_miembros_sin_update BEFORE UPDATE ON canal_miembros BEGIN SELECT RAISE(ABORT, 'El historial de miembros no se cambia'); END;

-- avisos.py
CREATE TRIGGER IF NOT EXISTS canal_miembros_sin_delete BEFORE DELETE ON canal_miembros BEGIN SELECT RAISE(ABORT, 'El historial de miembros no se borra'); END;

-- avisos.py
CREATE TRIGGER IF NOT EXISTS canal_grupos_sin_delete BEFORE DELETE ON canal_grupos BEGIN SELECT RAISE(ABORT, 'Un grupo no se borra'); END;

-- avisos.py
CREATE TRIGGER IF NOT EXISTS canal_resumenes_sin_delete BEFORE DELETE ON canal_resumenes BEGIN SELECT RAISE(ABORT, 'Un resumen no se borra'); END;

-- avisos_programados.py
CREATE TABLE IF NOT EXISTS avisos_prog_cambios (
  n INTEGER PRIMARY KEY AUTOINCREMENT, regla_id TEXT NOT NULL, campo TEXT NOT NULL, valor TEXT, antes TEXT,
  quien TEXT NOT NULL, hora TEXT NOT NULL DEFAULT (datetime('now')));

-- avisos_programados.py
CREATE TABLE IF NOT EXISTS avisos_prog_hechos (
  n INTEGER PRIMARY KEY AUTOINCREMENT, clave TEXT NOT NULL, quien TEXT NOT NULL, hora TEXT NOT NULL DEFAULT (datetime('now')));

-- avisos_programados.py
CREATE INDEX IF NOT EXISTS avisos_prog_hechos_clave ON avisos_prog_hechos (clave);

-- avisos_programados.py
CREATE TRIGGER IF NOT EXISTS avisos_prog_cambios_sin_update BEFORE UPDATE ON avisos_prog_cambios BEGIN SELECT RAISE(ABORT, 'Un cambio de regla no se cambia'); END;

-- avisos_programados.py
CREATE TRIGGER IF NOT EXISTS avisos_prog_cambios_sin_delete BEFORE DELETE ON avisos_prog_cambios BEGIN SELECT RAISE(ABORT, 'Un cambio de regla no se borra'); END;

-- avisos_programados.py
CREATE TRIGGER IF NOT EXISTS avisos_prog_hechos_sin_update BEFORE UPDATE ON avisos_prog_hechos BEGIN SELECT RAISE(ABORT, 'Un «hecho» no se cambia'); END;

-- avisos_programados.py
CREATE TRIGGER IF NOT EXISTS avisos_prog_hechos_sin_delete BEFORE DELETE ON avisos_prog_hechos BEGIN SELECT RAISE(ABORT, 'Un «hecho» no se borra'); END;

-- decisiones_durables_382.py
CREATE TABLE IF NOT EXISTS decisiones_intenciones_382 (intencion_id TEXT PRIMARY KEY,autor TEXT NOT NULL,huella TEXT NOT NULL,decision_id INTEGER NOT NULL,operacion TEXT NOT NULL,revision_final TEXT NOT NULL,registrado_en TEXT NOT NULL DEFAULT (datetime('now')));

-- decisiones_durables_382.py
CREATE TRIGGER IF NOT EXISTS decisiones382_no_UPDATE BEFORE UPDATE ON decisiones_intenciones_382 BEGIN SELECT RAISE(ABORT,'Intención inmutable'); END;

-- decisiones_durables_382.py
CREATE TRIGGER IF NOT EXISTS decisiones382_no_DELETE BEFORE DELETE ON decisiones_intenciones_382 BEGIN SELECT RAISE(ABORT,'Intención inmutable'); END;

-- despliegue/estado.py
CREATE TABLE IF NOT EXISTS ejecuciones (id {pk}, modo TEXT, quien TEXT, inicio TEXT, fin TEXT, estado TEXT, resumen TEXT);

-- despliegue/estado.py
CREATE TABLE IF NOT EXISTS pasos (id {pk}, ejecucion INTEGER, paso TEXT, intento INTEGER, inicio TEXT, segundos REAL,
                                  estado TEXT, salida TEXT, error TEXT);

-- despliegue/estado.py
CREATE TABLE IF NOT EXISTS llaves (nombre TEXT PRIMARY KEY, valor TEXT, rotada TEXT, rotaciones INTEGER DEFAULT 0, origen TEXT);

-- despliegue/estado.py
CREATE TABLE IF NOT EXISTS tuberia_avisos (id {pk}, dia TEXT, tipo TEXT, clave TEXT, texto TEXT, estado TEXT, creado TEXT);

-- despliegue/estado.py
CREATE TABLE IF NOT EXISTS sellos (paso TEXT PRIMARY KEY, ultimo_bueno TEXT, ultimo_intento TEXT, estado TEXT, motivo TEXT);

-- despliegue/publicacion.py
CREATE TABLE IF NOT EXISTS datos_blob (sha TEXT PRIMARY KEY, contenido {blob});

-- despliegue/publicacion.py
CREATE TABLE IF NOT EXISTS datos_version (id {pk}, espacio TEXT, creada TEXT, origen TEXT, estado TEXT, ficheros INTEGER, bytes INTEGER);

-- despliegue/publicacion.py
CREATE TABLE IF NOT EXISTS datos_fichero (version INTEGER, ruta TEXT, sha TEXT, PRIMARY KEY (version, ruta));

-- envios.py
CREATE TABLE IF NOT EXISTS envios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clave TEXT NOT NULL UNIQUE,                -- idempotencia: una por envío (sha256 de la acción); el proveedor la recibe
  accion_id INTEGER UNIQUE,                  -- la acción de la cola de la que nace (NULL en canario y pruebas)
  creado TEXT NOT NULL DEFAULT (datetime('now')),
  quien TEXT NOT NULL,
  canal TEXT NOT NULL CHECK (canal IN ('desk','whatsapp','ghl')),
  tipo TEXT NOT NULL,
  objeto TEXT NOT NULL,
  cliente_id TEXT,
  modulo TEXT,
  destinatario TEXT NOT NULL,                -- JSON resuelto por el SERVIDOR (tipo, ref, nombre); nunca una dirección escrita
  remitente TEXT,                            -- JSON: departamento y dirección de envío (los pone el servidor)
  asunto TEXT,
  texto TEXT,
  huella_texto TEXT NOT NULL,
  modo TEXT NOT NULL CHECK (modo IN ('simulado','real','prueba','canario'))
);

-- envios.py
CREATE INDEX IF NOT EXISTS i_envios_quien ON envios(quien);

-- envios.py
CREATE TABLE IF NOT EXISTS envio_pasos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  envio_id INTEGER NOT NULL REFERENCES envios(id),
  estado TEXT NOT NULL CHECK (estado IN ('simulado','pendiente','enviado','confirmado','fallido','rebotado')),
  evento TEXT NOT NULL,
  hora TEXT NOT NULL DEFAULT (datetime('now')),
  quien TEXT,
  intento INTEGER NOT NULL DEFAULT 0,
  motivo TEXT,
  detalle TEXT
);

-- envios.py
CREATE INDEX IF NOT EXISTS i_envio_pasos ON envio_pasos(envio_id, id);

-- envios.py
CREATE TRIGGER IF NOT EXISTS envios_sin_update BEFORE UPDATE ON envios BEGIN SELECT RAISE(ABORT, 'Un envío no se cambia: se añade un paso'); END;

-- envios.py
CREATE TRIGGER IF NOT EXISTS envios_sin_delete BEFORE DELETE ON envios BEGIN SELECT RAISE(ABORT, 'Un envío no se borra'); END;

-- envios.py
CREATE TRIGGER IF NOT EXISTS envio_pasos_sin_update BEFORE UPDATE ON envio_pasos BEGIN SELECT RAISE(ABORT, 'Un paso no se cambia'); END;

-- envios.py
CREATE TRIGGER IF NOT EXISTS envio_pasos_sin_delete BEFORE DELETE ON envio_pasos BEGIN SELECT RAISE(ABORT, 'Un paso no se borra'); END;

-- evidencias_kpi.py
CREATE TABLE IF NOT EXISTS registros(id TEXT PRIMARY KEY,clave TEXT UNIQUE NOT NULL,cliente TEXT NOT NULL,actor TEXT NOT NULL,payload TEXT NOT NULL,hash TEXT NOT NULL,estado TEXT NOT NULL,creado TEXT NOT NULL);

-- evidencias_kpi.py
CREATE TABLE IF NOT EXISTS eventos(n INTEGER PRIMARY KEY AUTOINCREMENT,registro TEXT NOT NULL,operacion TEXT NOT NULL,actor TEXT NOT NULL,fecha TEXT NOT NULL,datos TEXT NOT NULL);

-- evidencias_kpi.py
CREATE TABLE IF NOT EXISTS revocaciones(clave TEXT PRIMARY KEY,registro TEXT NOT NULL,actor TEXT NOT NULL,motivo TEXT NOT NULL);

-- ia_gasto.py
CREATE TABLE IF NOT EXISTS ia_gasto (
  id INTEGER PRIMARY KEY AUTOINCREMENT, creada TEXT NOT NULL, dia TEXT NOT NULL, mes TEXT NOT NULL,
  quien TEXT NOT NULL, tarea TEXT NOT NULL, objeto TEXT, modelo TEXT, llave TEXT NOT NULL, lote INTEGER NOT NULL DEFAULT 0,
  entrada INTEGER NOT NULL DEFAULT 0, cache_escrita INTEGER NOT NULL DEFAULT 0, cache_leida INTEGER NOT NULL DEFAULT 0,
  salida INTEGER NOT NULL DEFAULT 0, coste_usd REAL NOT NULL DEFAULT 0, coste_eur REAL NOT NULL DEFAULT 0,
  ok INTEGER NOT NULL, motivo TEXT, peticion TEXT);

-- ia_gasto.py
CREATE INDEX IF NOT EXISTS ia_gasto_mes ON ia_gasto (mes, dia);

-- ia_gasto.py
CREATE TRIGGER IF NOT EXISTS ia_gasto_sin_update BEFORE UPDATE ON ia_gasto BEGIN SELECT RAISE(ABORT, 'El gasto de la IA no se cambia'); END;

-- ia_gasto.py
CREATE TRIGGER IF NOT EXISTS ia_gasto_sin_delete BEFORE DELETE ON ia_gasto BEGIN SELECT RAISE(ABORT, 'El gasto de la IA no se borra'); END;

-- ia_gasto.py
CREATE TABLE IF NOT EXISTS ia_topes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, creada TEXT NOT NULL, quien TEXT NOT NULL, valores TEXT NOT NULL, motivo TEXT);

-- ia_gasto.py
CREATE TRIGGER IF NOT EXISTS ia_topes_sin_update BEFORE UPDATE ON ia_topes BEGIN SELECT RAISE(ABORT, 'Un cambio de topes no se reescribe'); END;

-- ia_gasto.py
CREATE TRIGGER IF NOT EXISTS ia_topes_sin_delete BEFORE DELETE ON ia_topes BEGIN SELECT RAISE(ABORT, 'Un cambio de topes no se borra'); END;

-- ia_gasto.py
CREATE TABLE IF NOT EXISTS ia_reservas (
  id TEXT PRIMARY KEY, creada TEXT NOT NULL, tarea TEXT NOT NULL, quien TEXT NOT NULL,
  llave TEXT NOT NULL, reservado_eur REAL NOT NULL CHECK(reservado_eur >= 0),
  estado TEXT NOT NULL CHECK(estado IN ('activa','incierta','cerrada')));

-- ia_gasto.py
CREATE TRIGGER IF NOT EXISTS ia_reservas_sin_delete BEFORE DELETE ON ia_reservas BEGIN SELECT RAISE(ABORT,'Una reserva no se borra'); END;

-- ia_gasto.py
CREATE TABLE IF NOT EXISTS ia_lotes (
  id TEXT PRIMARY KEY, creado TEXT NOT NULL, quien TEXT NOT NULL, tarea TEXT NOT NULL, llave TEXT NOT NULL, modelo TEXT,
  n INTEGER NOT NULL, reservado_eur REAL NOT NULL, estado TEXT NOT NULL, cerrado TEXT, peticiones TEXT);

-- intenciones_acciones.py
CREATE TABLE IF NOT EXISTS intenciones_acciones (
        actor TEXT NOT NULL,
        intencion TEXT NOT NULL,
        huella TEXT NOT NULL,
        accion_id INTEGER NOT NULL REFERENCES acciones(id),
        PRIMARY KEY(actor, intencion)
    );

-- leads_archivo.py
CREATE TABLE IF NOT EXISTS leads_meta (version INTEGER NOT NULL);

-- leads_archivo.py
CREATE TABLE IF NOT EXISTS leads_eventos (
                    cliente_id TEXT NOT NULL, source TEXT NOT NULL, event_id TEXT NOT NULL,
                    payload TEXT NOT NULL, huella TEXT NOT NULL, actor_id TEXT NOT NULL,
                    fuente_key TEXT NOT NULL, registrado TEXT NOT NULL,
                    PRIMARY KEY(cliente_id,source,event_id));

-- leads_archivo.py
CREATE TABLE IF NOT EXISTS leads_recibos (
                    recibo_id TEXT PRIMARY KEY, cliente_id TEXT NOT NULL, source TEXT NOT NULL,
                    event_id TEXT, actor_id TEXT NOT NULL, resultado TEXT NOT NULL,
                    motivo TEXT NOT NULL, registrado TEXT NOT NULL);

-- mi_trabajo.py
CREATE TABLE IF NOT EXISTS mt_crono (
  persona TEXT PRIMARY KEY,                 -- un cronómetro en marcha por persona
  tarea TEXT NOT NULL,
  inicio TEXT NOT NULL                      -- UTC, ISO
);

-- operaciones_anomalias_276.py
CREATE TABLE IF NOT EXISTS operaciones_anomalias_276 (id INTEGER PRIMARY KEY AUTOINCREMENT, anomalia TEXT NOT NULL, revision INTEGER NOT NULL, actor TEXT NOT NULL, persona_id TEXT NOT NULL, origen_hash TEXT NOT NULL, decision TEXT NOT NULL, prueba TEXT NOT NULL, hora TEXT NOT NULL, intencion TEXT NOT NULL, request_hash TEXT NOT NULL, UNIQUE(anomalia,revision), UNIQUE(actor,intencion));

-- operaciones_anomalias_276.py
CREATE TRIGGER IF NOT EXISTS operaciones_276_sin_update BEFORE UPDATE ON operaciones_anomalias_276 BEGIN SELECT RAISE(ABORT,'Revisión de horas inmutable'); END;

-- operaciones_anomalias_276.py
CREATE TRIGGER IF NOT EXISTS operaciones_276_sin_delete BEFORE DELETE ON operaciones_anomalias_276 BEGIN SELECT RAISE(ABORT,'Revisión de horas inmutable'); END;

-- operaciones_feedback_273.py
CREATE TABLE IF NOT EXISTS operaciones_feedback_273 (intencion_id TEXT PRIMARY KEY, cliente_id TEXT NOT NULL, semana TEXT NOT NULL, revision INTEGER NOT NULL, autor TEXT NOT NULL, registrado_en TEXT NOT NULL, estado TEXT NOT NULL, nota TEXT NOT NULL, huella TEXT NOT NULL, UNIQUE(cliente_id,semana,revision));

-- operaciones_feedback_273.py
CREATE TRIGGER IF NOT EXISTS feedback273_sin_update BEFORE UPDATE ON operaciones_feedback_273 BEGIN SELECT RAISE(ABORT,'Opinión declarada inmutable'); END;

-- operaciones_feedback_273.py
CREATE TRIGGER IF NOT EXISTS feedback273_sin_delete BEFORE DELETE ON operaciones_feedback_273 BEGIN SELECT RAISE(ABORT,'Opinión declarada inmutable'); END;

-- operaciones_notas_equipo_281.py
CREATE TABLE IF NOT EXISTS operaciones_notas_equipo_281 (id INTEGER PRIMARY KEY AUTOINCREMENT, persona_id TEXT NOT NULL, periodo TEXT NOT NULL, revision INTEGER NOT NULL, autor TEXT NOT NULL, hora TEXT NOT NULL, nota INTEGER, prueba TEXT NOT NULL, accion TEXT, intencion TEXT NOT NULL, huella TEXT NOT NULL, UNIQUE(persona_id,revision), UNIQUE(autor,intencion));

-- operaciones_notas_equipo_281.py
CREATE TRIGGER IF NOT EXISTS operaciones_281_sin_update BEFORE UPDATE ON operaciones_notas_equipo_281 BEGIN SELECT RAISE(ABORT,'Nota humana inmutable'); END;

-- operaciones_notas_equipo_281.py
CREATE TRIGGER IF NOT EXISTS operaciones_281_sin_delete BEFORE DELETE ON operaciones_notas_equipo_281 BEGIN SELECT RAISE(ABORT,'Nota humana inmutable'); END;

-- operaciones_pedidos_account.py
CREATE TABLE IF NOT EXISTS operaciones_pedidos_account_294 (intencion_id TEXT PRIMARY KEY,cliente_id TEXT NOT NULL,tipo TEXT NOT NULL,referencia_id TEXT NOT NULL,revision INTEGER NOT NULL,autor TEXT NOT NULL,receptor TEXT NOT NULL,estado TEXT NOT NULL,registrado_en TEXT NOT NULL,revision_fuente TEXT NOT NULL,huella TEXT NOT NULL,UNIQUE(cliente_id,tipo,referencia_id,revision));

-- operaciones_pedidos_account.py
CREATE TRIGGER IF NOT EXISTS pedidos294_no_UPDATE BEFORE UPDATE ON operaciones_pedidos_account_294 BEGIN SELECT RAISE(ABORT,'Pedido inmutable'); END;

-- operaciones_pedidos_account.py
CREATE TRIGGER IF NOT EXISTS pedidos294_no_DELETE BEFORE DELETE ON operaciones_pedidos_account_294 BEGIN SELECT RAISE(ABORT,'Pedido inmutable'); END;

-- operaciones_prioridades_300.py
CREATE TABLE IF NOT EXISTS operaciones_prioridades_300 (intencion_id TEXT PRIMARY KEY,actor TEXT NOT NULL,prioridad_id TEXT NOT NULL,fuente_revision TEXT NOT NULL,dia TEXT NOT NULL,revision INTEGER NOT NULL,estado TEXT NOT NULL,nota TEXT NOT NULL,registrado_en TEXT NOT NULL,huella TEXT NOT NULL,UNIQUE(actor,prioridad_id,fuente_revision,dia,revision));

-- operaciones_prioridades_300.py
CREATE TRIGGER IF NOT EXISTS prioridades300_sin_update BEFORE UPDATE ON operaciones_prioridades_300 BEGIN SELECT RAISE(ABORT,'Rastro propio inmutable'); END;

-- operaciones_prioridades_300.py
CREATE TRIGGER IF NOT EXISTS prioridades300_sin_delete BEFORE DELETE ON operaciones_prioridades_300 BEGIN SELECT RAISE(ABORT,'Rastro propio inmutable'); END;

-- operaciones_registros_269.py
CREATE TABLE IF NOT EXISTS operaciones_registros_269 (id INTEGER PRIMARY KEY AUTOINCREMENT, propietario TEXT NOT NULL, clave TEXT NOT NULL, revision INTEGER NOT NULL, autor TEXT NOT NULL, registrado_en TEXT NOT NULL, contenido TEXT NOT NULL, intencion TEXT NOT NULL, huella TEXT NOT NULL, UNIQUE(autor,intencion), UNIQUE(propietario,clave,revision));

-- operaciones_registros_269.py
CREATE TRIGGER IF NOT EXISTS operaciones_269_sin_update BEFORE UPDATE ON operaciones_registros_269 BEGIN SELECT RAISE(ABORT,'Registro operativo inmutable'); END;

-- operaciones_registros_269.py
CREATE TRIGGER IF NOT EXISTS operaciones_269_sin_delete BEFORE DELETE ON operaciones_registros_269 BEGIN SELECT RAISE(ABORT,'Registro operativo inmutable'); END;

-- operaciones_registros_272.py
CREATE TABLE IF NOT EXISTS operaciones_control_272 (id INTEGER PRIMARY KEY AUTOINCREMENT, objeto TEXT NOT NULL, revision INTEGER NOT NULL, actor TEXT NOT NULL, autor TEXT NOT NULL, asignado TEXT NOT NULL, tipo TEXT NOT NULL, hora TEXT NOT NULL, contenido TEXT NOT NULL, intencion TEXT NOT NULL, huella TEXT NOT NULL, UNIQUE(actor,intencion), UNIQUE(objeto,revision));

-- operaciones_registros_272.py
CREATE TRIGGER IF NOT EXISTS operaciones_272_sin_update BEFORE UPDATE ON operaciones_control_272 BEGIN SELECT RAISE(ABORT,'Registro de control inmutable'); END;

-- operaciones_registros_272.py
CREATE TRIGGER IF NOT EXISTS operaciones_272_sin_delete BEFORE DELETE ON operaciones_control_272 BEGIN SELECT RAISE(ABORT,'Registro de control inmutable'); END;

-- planes_fuegos_255.py
CREATE TABLE IF NOT EXISTS planes_fuegos_255 (
  accion_id TEXT PRIMARY KEY, cliente_id TEXT NOT NULL, version INTEGER NOT NULL,
  operacion TEXT NOT NULL, actor_id TEXT NOT NULL, hora TEXT NOT NULL,
  payload_hash TEXT NOT NULL, datos TEXT NOT NULL, UNIQUE(cliente_id, version)
);

-- planes_fuegos_255.py
CREATE TRIGGER IF NOT EXISTS fuego255_sin_update BEFORE UPDATE ON planes_fuegos_255 BEGIN SELECT RAISE(ABORT, 'El historial de planes no se modifica'); END;

-- planes_fuegos_255.py
CREATE TRIGGER IF NOT EXISTS fuego255_sin_delete BEFORE DELETE ON planes_fuegos_255 BEGIN SELECT RAISE(ABORT, 'El historial de planes no se borra'); END;

-- schema_v2.sql
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

-- schema_v2.sql
CREATE TABLE IF NOT EXISTS persona_puestos (
  persona_id  TEXT NOT NULL REFERENCES personas(id),
  puesto      TEXT NOT NULL CHECK (puesto IN (
                'direccion','finanzas_direccion','administracion','operaciones','proyectos','rrhh','account',
                'trafficker','jefa_publicidad','especialista_ghl','jefa_crm','tecnico_altas','jefa_seo','seo',
                'ficha_google','web','redes','produccion','setters','ventas_ro','outreach')),
  principal   INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (persona_id, puesto)
);

-- schema_v2.sql
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

-- schema_v2.sql
CREATE INDEX IF NOT EXISTS i_asig_persona ON asignaciones(persona_id, hasta);

-- schema_v2.sql
CREATE INDEX IF NOT EXISTS i_asig_cliente ON asignaciones(cliente_id, silla, hasta);

-- schema_v2.sql
CREATE VIEW IF NOT EXISTS v_cartera_hoy AS
  SELECT persona_id, cliente_id, silla, CASE WHEN suplencia = 1 THEN 'suplencia' ELSE 'titular' END AS via
    FROM asignaciones
   WHERE (desde IS NULL OR desde <= date('now')) AND (hasta IS NULL OR hasta >= date('now'));

-- schema_v2.sql
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

-- schema_v2.sql
CREATE INDEX IF NOT EXISTS i_reg_col ON registro(coleccion, clave);

-- schema_v2.sql
CREATE INDEX IF NOT EXISTS i_reg_quien ON registro(quien, creada);

-- schema_v2.sql
CREATE TRIGGER IF NOT EXISTS registro_sin_update BEFORE UPDATE ON registro BEGIN SELECT RAISE(ABORT, 'El rastro no se modifica: crea una anulación'); END;

-- schema_v2.sql
CREATE TRIGGER IF NOT EXISTS registro_sin_delete BEFORE DELETE ON registro BEGIN SELECT RAISE(ABORT, 'El rastro no se borra: crea una anulación'); END;

-- schema_v2.sql
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

-- schema_v2.sql
CREATE TRIGGER IF NOT EXISTS historial_sin_update BEFORE UPDATE ON historial BEGIN SELECT RAISE(ABORT, 'El historial no se modifica'); END;

-- schema_v2.sql
CREATE TRIGGER IF NOT EXISTS historial_sin_delete BEFORE DELETE ON historial BEGIN SELECT RAISE(ABORT, 'El historial no se borra'); END;

-- schema_v2.sql
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

-- schema_v2.sql
CREATE INDEX IF NOT EXISTS i_acc_obj ON acciones(objeto);

-- schema_v2.sql
CREATE TRIGGER IF NOT EXISTS acciones_sin_delete BEFORE DELETE ON acciones BEGIN SELECT RAISE(ABORT, 'Las acciones no se borran'); END;

-- schema_v2.sql
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

-- schema_v2.sql
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

-- schema_v2.sql
CREATE TABLE IF NOT EXISTS docs (
  coleccion TEXT NOT NULL, id TEXT NOT NULL, datos TEXT NOT NULL, uid TEXT, ts TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (coleccion, id)
);

-- schema_v2.sql
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

-- schema_v2.sql
CREATE TRIGGER IF NOT EXISTS recargas_sin_delete BEFORE DELETE ON recargas BEGIN SELECT RAISE(ABORT, 'Las recargas no se borran'); END;

-- schema_v2.sql
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

-- schema_v2.sql
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

-- schema_v2.sql
CREATE INDEX IF NOT EXISTS i_fuente_lectura ON fuente_lectura(fuente, recurso, ok, id);

-- schema_v2.sql
CREATE VIEW IF NOT EXISTS fuente_ultimo_bueno AS
  SELECT f.* FROM fuente_lectura f
   WHERE f.ok = 1
     AND f.id = (SELECT MAX(g.id) FROM fuente_lectura g WHERE g.fuente = f.fuente AND g.recurso = f.recurso AND g.ok = 1);

-- servir.py
CREATE TABLE IF NOT EXISTS preferencias (persona TEXT NOT NULL, clave TEXT NOT NULL, valor TEXT NOT NULL,
  cambiado TEXT NOT NULL DEFAULT (datetime('now')), PRIMARY KEY (persona, clave));

-- servir.py
CREATE TABLE IF NOT EXISTS opiniones (
  id INTEGER PRIMARY KEY AUTOINCREMENT, creada TEXT NOT NULL DEFAULT (datetime('now')), quien TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('fallo','idea')), prioridad TEXT NOT NULL DEFAULT 'gris' CHECK (prioridad IN ('rojo','ambar','gris')),
  texto TEXT NOT NULL, esperaba TEXT, ruta TEXT, pantalla TEXT, ancho INTEGER, alto INTEGER, frescura TEXT, captura TEXT,
  estado TEXT NOT NULL DEFAULT 'nueva' CHECK (estado IN ('nueva','vista','resuelta')), estado_por TEXT, estado_hora TEXT);

-- servir.py
CREATE TRIGGER IF NOT EXISTS opiniones_sin_delete BEFORE DELETE ON opiniones BEGIN SELECT RAISE(ABORT, 'Las opiniones no se borran'); END;

-- servir.py
CREATE TRIGGER IF NOT EXISTS opiniones_solo_estado BEFORE UPDATE ON opiniones
  WHEN NEW.quien IS NOT OLD.quien OR NEW.texto IS NOT OLD.texto OR NEW.creada IS NOT OLD.creada OR NEW.tipo IS NOT OLD.tipo OR NEW.captura IS NOT OLD.captura
  BEGIN SELECT RAISE(ABORT, 'De una opinión solo cambia el estado'); END;

-- servir.py
CREATE TABLE IF NOT EXISTS registro_huellas (id INTEGER PRIMARY KEY, huella TEXT NOT NULL);

-- servir.py
CREATE TABLE IF NOT EXISTS rastro_cortes (id INTEGER PRIMARY KEY, motivo TEXT NOT NULL, anotado TEXT NOT NULL DEFAULT (datetime('now')));

-- servir.py
CREATE TABLE IF NOT EXISTS rastro_incidencias (n INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL CHECK (tipo IN ('corte','sin_huella','nota')),
  desde INTEGER NOT NULL, hasta INTEGER NOT NULL, motivo TEXT NOT NULL, anotado TEXT NOT NULL DEFAULT (datetime('now')));

-- servir.py
CREATE TRIGGER IF NOT EXISTS incidencias_sin_update BEFORE UPDATE ON rastro_incidencias BEGIN SELECT RAISE(ABORT, 'Una incidencia del rastro no se cambia'); END;

-- servir.py
CREATE TRIGGER IF NOT EXISTS incidencias_sin_delete BEFORE DELETE ON rastro_incidencias BEGIN SELECT RAISE(ABORT, 'Una incidencia del rastro no se borra'); END;

-- servir.py
CREATE TRIGGER IF NOT EXISTS cortes_sin_update BEFORE UPDATE ON rastro_cortes BEGIN SELECT RAISE(ABORT, 'Un corte anotado no se cambia'); END;

-- servir.py
CREATE TRIGGER IF NOT EXISTS cortes_sin_delete BEFORE DELETE ON rastro_cortes BEGIN SELECT RAISE(ABORT, 'Un corte anotado no se borra'); END;

-- servir.py
CREATE TRIGGER IF NOT EXISTS huellas_sin_update BEFORE UPDATE ON registro_huellas BEGIN SELECT RAISE(ABORT, 'La huella del rastro no se modifica'); END;

-- servir.py
CREATE TRIGGER IF NOT EXISTS huellas_sin_delete BEFORE DELETE ON registro_huellas BEGIN SELECT RAISE(ABORT, 'La huella del rastro no se borra'); END;

-- servir.py
CREATE TRIGGER IF NOT EXISTS decisiones_sin_delete BEFORE DELETE ON decisiones BEGIN SELECT RAISE(ABORT, 'Las decisiones no se borran'); END;

-- servir.py
CREATE TRIGGER IF NOT EXISTS decisiones_una_respuesta BEFORE UPDATE ON decisiones
  WHEN OLD.respondida IS NOT NULL OR NEW.quien IS NOT OLD.quien OR NEW.tipo IS NOT OLD.tipo OR NEW.problema IS NOT OLD.problema
    OR NEW.recomendacion IS NOT OLD.recomendacion OR NEW.titulo IS NOT OLD.titulo OR NEW.creada IS NOT OLD.creada
  BEGIN SELECT RAISE(ABORT, 'Una decisión solo se contesta una vez y no se reescribe'); END;

-- servir.py
CREATE TRIGGER IF NOT EXISTS acciones_solo_estado BEFORE UPDATE ON acciones
  WHEN NEW.quien IS NOT OLD.quien OR NEW.herramienta IS NOT OLD.herramienta OR NEW.tipo IS NOT OLD.tipo OR NEW.objeto IS NOT OLD.objeto
    OR NEW.cliente_id IS NOT OLD.cliente_id OR NEW.texto IS NOT OLD.texto OR NEW.vista_previa IS NOT OLD.vista_previa OR NEW.creada IS NOT OLD.creada
  BEGIN SELECT RAISE(ABORT, 'De una acción solo puede avanzar el estado'); END;

-- servir.py
CREATE TRIGGER IF NOT EXISTS registro_sin_reinsertar_569 BEFORE INSERT ON registro
WHEN NEW.id > 0 AND NEW.id <= (SELECT MAX(id) FROM registro)
BEGIN SELECT RAISE(ABORT, 'El rastro no reutiliza IDs: crea una anulación'); END;

-- servir.py
CREATE TRIGGER IF NOT EXISTS huellas_sin_reinsertar_569 BEFORE INSERT ON registro_huellas
WHEN NEW.id > 0 AND NEW.id <= (SELECT MAX(id) FROM registro_huellas)
BEGIN SELECT RAISE(ABORT, 'La huella del rastro no reutiliza IDs'); END;

-- sincronia.py
CREATE TABLE IF NOT EXISTS sinc_cambios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clave TEXT NOT NULL UNIQUE,                 -- idempotencia: una por acción (o por mensaje del chat)
  accion_id INTEGER UNIQUE,                   -- la acción de la cola de la que nace
  mensaje_id INTEGER UNIQUE,                  -- o el mensaje de un grupo de la app (puente de chat)
  creado TEXT NOT NULL DEFAULT (datetime('now')),
  quien TEXT NOT NULL,
  canal TEXT NOT NULL CHECK (canal IN ('clickup','chat')),
  tipo TEXT NOT NULL,
  objeto TEXT NOT NULL,                       -- JSON: {tipo: tarea|lista|canal, ref, nombre, url, resuelto} (servidor)
  objeto_ref TEXT NOT NULL,                   -- para el orden por objeto
  cliente_id TEXT,
  modulo TEXT,
  cambio TEXT NOT NULL,                       -- JSON: el cambio EXACTO (servidor)
  base TEXT,                                  -- JSON: lo que la app creía que había en ClickUp al hacerlo
  ignorado TEXT,                              -- JSON: lo que mandó el navegador y no se usó
  modo TEXT NOT NULL CHECK (modo IN ('simulado','real','prueba'))
);

-- sincronia.py
CREATE INDEX IF NOT EXISTS i_sinc_obj ON sinc_cambios(objeto_ref, id);

-- sincronia.py
CREATE INDEX IF NOT EXISTS i_sinc_quien ON sinc_cambios(quien);

-- sincronia.py
CREATE TABLE IF NOT EXISTS sinc_pasos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cambio_id INTEGER NOT NULL REFERENCES sinc_cambios(id),
  estado TEXT NOT NULL CHECK (estado IN ('simulado','pendiente','enviado','confirmado','fallido','conflicto','descartado')),
  evento TEXT NOT NULL,
  hora TEXT NOT NULL DEFAULT (datetime('now')),
  quien TEXT,
  intento INTEGER NOT NULL DEFAULT 0,
  motivo TEXT,
  detalle TEXT
);

-- sincronia.py
CREATE INDEX IF NOT EXISTS i_sinc_pasos ON sinc_pasos(cambio_id, id);

-- sincronia.py
CREATE TRIGGER IF NOT EXISTS sinc_cambios_sin_update BEFORE UPDATE ON sinc_cambios BEGIN SELECT RAISE(ABORT, 'Un cambio no se cambia: se añade un paso'); END;

-- sincronia.py
CREATE TRIGGER IF NOT EXISTS sinc_cambios_sin_delete BEFORE DELETE ON sinc_cambios BEGIN SELECT RAISE(ABORT, 'Un cambio no se borra'); END;

-- sincronia.py
CREATE TRIGGER IF NOT EXISTS sinc_pasos_sin_update BEFORE UPDATE ON sinc_pasos BEGIN SELECT RAISE(ABORT, 'Un paso no se cambia'); END;

-- sincronia.py
CREATE TRIGGER IF NOT EXISTS sinc_pasos_sin_delete BEFORE DELETE ON sinc_pasos BEGIN SELECT RAISE(ABORT, 'Un paso no se borra'); END;

-- uso_local.py
CREATE TABLE IF NOT EXISTS uso_eventos (
 id INTEGER PRIMARY KEY, instante REAL NOT NULL, actor TEXT NOT NULL,
 visto TEXT NOT NULL, pantalla TEXT NOT NULL, accion TEXT NOT NULL, control TEXT NOT NULL, activo_ms INTEGER NOT NULL);

-- uso_local.py
CREATE INDEX IF NOT EXISTS uso_instante ON uso_eventos(instante);

-- uso_local.py
CREATE INDEX IF NOT EXISTS uso_actor ON uso_eventos(actor, instante);

-- uso_local.py
CREATE TABLE IF NOT EXISTS uso_sesiones (
 actor TEXT NOT NULL, sesion TEXT NOT NULL, secuencia INTEGER NOT NULL,
 instante REAL NOT NULL, visto TEXT NOT NULL, pantalla TEXT NOT NULL,
 PRIMARY KEY(actor,sesion));

-- uso_local.py
CREATE TABLE IF NOT EXISTS uso_ventanas (
 actor TEXT PRIMARY KEY, fin REAL NOT NULL);

-- vistas_tareas.py
CREATE TABLE IF NOT EXISTS tareas_vistas_privadas (
        propietario TEXT NOT NULL, id TEXT NOT NULL, nombre TEXT NOT NULL,
        filtros TEXT NOT NULL, version INTEGER NOT NULL, revision INTEGER NOT NULL,
        PRIMARY KEY(propietario,id));

-- servir.py
ALTER TABLE decisiones ADD COLUMN IF NOT EXISTS titulo TEXT;

-- servir.py
ALTER TABLE decisiones ADD COLUMN IF NOT EXISTS cliente_id TEXT;

-- servir.py
ALTER TABLE decisiones ADD COLUMN IF NOT EXISTS datos TEXT;

-- servir.py
ALTER TABLE registro ADD COLUMN IF NOT EXISTS huella_previa TEXT;
