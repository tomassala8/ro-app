
CREATE FUNCTION public.acciones_solo_estado_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN IF (NEW.quien IS DISTINCT FROM OLD.quien OR NEW.herramienta IS DISTINCT FROM OLD.herramienta OR NEW.tipo IS DISTINCT FROM OLD.tipo OR NEW.objeto IS DISTINCT FROM OLD.objeto OR NEW.cliente_id IS DISTINCT FROM OLD.cliente_id OR NEW.texto IS DISTINCT FROM OLD.texto OR NEW.vista_previa IS DISTINCT FROM OLD.vista_previa OR NEW.creada IS DISTINCT FROM OLD.creada) THEN RAISE EXCEPTION '%', 'De una acción solo puede avanzar el estado'; END IF; RETURN NEW; END $$;

CREATE FUNCTION public.altas_tareas_solo_estado_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN IF (NEW.para IS DISTINCT FROM OLD.para OR NEW.tipo IS DISTINCT FROM OLD.tipo OR NEW.persona_id IS DISTINCT FROM OLD.persona_id OR NEW.texto IS DISTINCT FROM OLD.texto OR NEW.quien IS DISTINCT FROM OLD.quien OR NEW.creada IS DISTINCT FROM OLD.creada OR OLD.estado = 'hecha') THEN RAISE EXCEPTION '%', 'De una tarea solo se marca «hecha», una vez'; END IF; RETURN NEW; END $$;

CREATE FUNCTION public.decisiones_una_respuesta_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN IF (OLD.respondida IS NOT NULL OR NEW.quien IS DISTINCT FROM OLD.quien OR NEW.tipo IS DISTINCT FROM OLD.tipo OR NEW.problema IS DISTINCT FROM OLD.problema OR NEW.recomendacion IS DISTINCT FROM OLD.recomendacion OR NEW.titulo IS DISTINCT FROM OLD.titulo OR NEW.creada IS DISTINCT FROM OLD.creada) THEN RAISE EXCEPTION '%', 'Una decisión solo se contesta una vez y no se reescribe'; END IF; RETURN NEW; END $$;

CREATE FUNCTION public.huellas_sin_reinsertar_569_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN IF (NEW.id > 0 AND NEW.id <= (SELECT MAX(id) FROM registro_huellas)) THEN RAISE EXCEPTION '%', 'La huella del rastro no reutiliza IDs'; END IF; RETURN NEW; END $$;

CREATE FUNCTION public.opiniones_solo_estado_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN IF (NEW.quien IS DISTINCT FROM OLD.quien OR NEW.texto IS DISTINCT FROM OLD.texto OR NEW.creada IS DISTINCT FROM OLD.creada OR NEW.tipo IS DISTINCT FROM OLD.tipo OR NEW.captura IS DISTINCT FROM OLD.captura) THEN RAISE EXCEPTION '%', 'De una opinión solo cambia el estado'; END IF; RETURN NEW; END $$;

CREATE FUNCTION public.registro_sin_reinsertar_569_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN IF (NEW.id > 0 AND NEW.id <= (SELECT MAX(id) FROM registro)) THEN RAISE EXCEPTION '%', 'El rastro no reutiliza IDs: crea una anulación'; END IF; RETURN NEW; END $$;

CREATE FUNCTION public.ro_prohibido() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN RAISE EXCEPTION '%', TG_ARGV[0]; END $$;

CREATE TABLE public.acciones (
    id bigint NOT NULL,
    creada text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    quien text NOT NULL,
    herramienta text NOT NULL,
    tipo text NOT NULL,
    objeto text NOT NULL,
    cliente_id text,
    modulo text,
    texto text,
    vista_previa text,
    estado text DEFAULT 'simulada'::text NOT NULL,
    resultado text,
    detalle text,
    CONSTRAINT acciones_estado_check CHECK ((estado = ANY (ARRAY['simulada'::text, 'pendiente'::text, 'ok'::text, 'error'::text])))
);

CREATE SEQUENCE public.acciones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.acciones_id_seq OWNED BY public.acciones.id;

CREATE TABLE public.actas_claves (
    quien text NOT NULL,
    clave text NOT NULL,
    cliente_id text NOT NULL,
    huella text NOT NULL
);

CREATE TABLE public.actas_lotes (
    quien text NOT NULL,
    cliente_id text NOT NULL,
    huella text NOT NULL,
    resultado text NOT NULL
);

CREATE TABLE public.altas_recibos (
    clave text NOT NULL,
    quien text NOT NULL,
    persona_id text NOT NULL,
    resultado text NOT NULL,
    correo_guardado integer DEFAULT 0 NOT NULL,
    lista_guardada integer DEFAULT 0 NOT NULL
);

CREATE TABLE public.altas_tareas (
    id bigint NOT NULL,
    creada text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    para text NOT NULL,
    tipo text NOT NULL,
    persona_id text NOT NULL,
    texto text NOT NULL,
    quien text NOT NULL,
    estado text DEFAULT 'pendiente'::text NOT NULL,
    hecha text,
    hecha_por text,
    CONSTRAINT altas_tareas_estado_check CHECK ((estado = ANY (ARRAY['pendiente'::text, 'hecha'::text]))),
    CONSTRAINT altas_tareas_tipo_check CHECK ((tipo = ANY (ARRAY['access_anadir'::text, 'access_quitar'::text, 'repartir_cartera'::text])))
);

CREATE SEQUENCE public.altas_tareas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.altas_tareas_id_seq OWNED BY public.altas_tareas.id;

CREATE TABLE public.asignaciones (
    id bigint NOT NULL,
    cliente_id text NOT NULL,
    cliente_id_portal text,
    persona_id text NOT NULL,
    silla text NOT NULL,
    principal integer DEFAULT 1 NOT NULL,
    suplencia integer DEFAULT 0 NOT NULL,
    titular_id text,
    desde text,
    hasta text,
    fuente text,
    confianza text,
    duda text,
    creado text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    creado_por text,
    CONSTRAINT asignaciones_check CHECK (((suplencia = 0) OR (hasta IS NOT NULL))),
    CONSTRAINT asignaciones_confianza_check CHECK ((confianza = ANY (ARRAY['alta'::text, 'media'::text, 'baja'::text, 'confirmada'::text]))),
    CONSTRAINT asignaciones_silla_check CHECK ((silla = ANY (ARRAY['account'::text, 'trafficker'::text, 'crm'::text, 'ghl'::text, 'seo'::text, 'web'::text, 'redes'::text, 'produccion'::text, 'outreach'::text])))
);

CREATE SEQUENCE public.asignaciones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.asignaciones_id_seq OWNED BY public.asignaciones.id;

CREATE TABLE public.avisos (
    id bigint NOT NULL,
    creado text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    dia text NOT NULL,
    tipo text NOT NULL,
    clave text NOT NULL,
    texto text NOT NULL,
    estado text DEFAULT 'para_avisar'::text NOT NULL,
    visto text,
    visto_por text,
    CONSTRAINT avisos_estado_check CHECK ((estado = ANY (ARRAY['para_avisar'::text, 'retenido'::text])))
);

CREATE SEQUENCE public.avisos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.avisos_id_seq OWNED BY public.avisos.id;

CREATE TABLE public.avisos_prog_cambios (
    n bigint NOT NULL,
    regla_id text NOT NULL,
    campo text NOT NULL,
    valor text,
    antes text,
    quien text NOT NULL,
    hora text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL
);

CREATE SEQUENCE public.avisos_prog_cambios_n_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.avisos_prog_cambios_n_seq OWNED BY public.avisos_prog_cambios.n;

CREATE TABLE public.avisos_prog_hechos (
    n bigint NOT NULL,
    clave text NOT NULL,
    quien text NOT NULL,
    hora text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL
);

CREATE SEQUENCE public.avisos_prog_hechos_n_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.avisos_prog_hechos_n_seq OWNED BY public.avisos_prog_hechos.n;

CREATE TABLE public.canal_campana (
    persona_id text NOT NULL,
    hasta_id integer DEFAULT 0 NOT NULL,
    resumen_visto text,
    hora text
);

CREATE TABLE public.canal_grupos (
    id text NOT NULL,
    nombre text NOT NULL,
    cliente_id text,
    creado_por text NOT NULL,
    creado text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL
);

CREATE TABLE public.canal_leidos (
    persona_id text NOT NULL,
    canal_id text NOT NULL,
    ultimo_id integer NOT NULL,
    hora text NOT NULL
);

CREATE TABLE public.canal_mensajes (
    id bigint NOT NULL,
    canal_id text NOT NULL,
    tipo text NOT NULL,
    quien text,
    texto text NOT NULL,
    hilo_de integer,
    menciones text,
    clave text,
    alerta_id text,
    cliente_id text,
    dueno_id text,
    vence text,
    ver text,
    datos text,
    creado text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    CONSTRAINT canal_mensajes_tipo_check CHECK ((tipo = ANY (ARRAY['mensaje'::text, 'aviso'::text, 'evento'::text])))
);

CREATE SEQUENCE public.canal_mensajes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.canal_mensajes_id_seq OWNED BY public.canal_mensajes.id;

CREATE TABLE public.canal_miembros (
    n bigint NOT NULL,
    canal_id text NOT NULL,
    persona_id text NOT NULL,
    operacion text NOT NULL,
    quien text NOT NULL,
    hora text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    CONSTRAINT canal_miembros_operacion_check CHECK ((operacion = ANY (ARRAY['anadir'::text, 'quitar'::text])))
);

CREATE SEQUENCE public.canal_miembros_n_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.canal_miembros_n_seq OWNED BY public.canal_miembros.n;

CREATE TABLE public.canal_preferencias (
    persona_id text NOT NULL,
    silenciados text,
    hora_resumen text,
    actualizado text
);

CREATE TABLE public.canal_resumenes (
    persona_id text NOT NULL,
    dia text NOT NULL,
    titulo text,
    texto text,
    datos text,
    creado text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL
);

CREATE TABLE public.datos_blob (
    sha text NOT NULL,
    contenido bytea
);

CREATE TABLE public.datos_fichero (
    version integer NOT NULL,
    ruta text NOT NULL,
    sha text
);

CREATE TABLE public.datos_version (
    id bigint NOT NULL,
    espacio text,
    creada text,
    origen text,
    estado text,
    ficheros integer,
    bytes integer
);

CREATE SEQUENCE public.datos_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.datos_version_id_seq OWNED BY public.datos_version.id;

CREATE TABLE public.decisiones (
    id bigint NOT NULL,
    creada text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    quien text NOT NULL,
    tipo text NOT NULL,
    clave text,
    problema text,
    recomendacion text,
    respuesta text,
    respondida text,
    respondida_por text,
    anula_a bigint,
    titulo text,
    cliente_id text,
    datos text
);

CREATE SEQUENCE public.decisiones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.decisiones_id_seq OWNED BY public.decisiones.id;

CREATE TABLE public.decisiones_intenciones_382 (
    intencion_id text NOT NULL,
    autor text NOT NULL,
    huella text NOT NULL,
    decision_id integer NOT NULL,
    operacion text NOT NULL,
    revision_final text NOT NULL,
    registrado_en text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL
);

CREATE TABLE public.docs (
    coleccion text NOT NULL,
    id text NOT NULL,
    datos text NOT NULL,
    uid text,
    ts text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL
);

CREATE TABLE public.ejecuciones (
    id bigint NOT NULL,
    modo text,
    quien text,
    inicio text,
    fin text,
    estado text,
    resumen text
);

CREATE SEQUENCE public.ejecuciones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.ejecuciones_id_seq OWNED BY public.ejecuciones.id;

CREATE TABLE public.envio_pasos (
    id bigint NOT NULL,
    envio_id bigint NOT NULL,
    estado text NOT NULL,
    evento text NOT NULL,
    hora text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    quien text,
    intento integer DEFAULT 0 NOT NULL,
    motivo text,
    detalle text,
    CONSTRAINT envio_pasos_estado_check CHECK ((estado = ANY (ARRAY['simulado'::text, 'pendiente'::text, 'enviado'::text, 'confirmado'::text, 'fallido'::text, 'rebotado'::text])))
);

CREATE SEQUENCE public.envio_pasos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.envio_pasos_id_seq OWNED BY public.envio_pasos.id;

CREATE TABLE public.envios (
    id bigint NOT NULL,
    clave text NOT NULL,
    accion_id integer,
    creado text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    quien text NOT NULL,
    canal text NOT NULL,
    tipo text NOT NULL,
    objeto text NOT NULL,
    cliente_id text,
    modulo text,
    destinatario text NOT NULL,
    remitente text,
    asunto text,
    texto text,
    huella_texto text NOT NULL,
    modo text NOT NULL,
    CONSTRAINT envios_canal_check CHECK ((canal = ANY (ARRAY['desk'::text, 'whatsapp'::text, 'ghl'::text]))),
    CONSTRAINT envios_modo_check CHECK ((modo = ANY (ARRAY['simulado'::text, 'real'::text, 'prueba'::text, 'canario'::text])))
);

CREATE SEQUENCE public.envios_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.envios_id_seq OWNED BY public.envios.id;

CREATE TABLE public.eventos (
    n bigint NOT NULL,
    registro text NOT NULL,
    operacion text NOT NULL,
    actor text NOT NULL,
    fecha text NOT NULL,
    datos text NOT NULL
);

CREATE SEQUENCE public.eventos_n_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.eventos_n_seq OWNED BY public.eventos.n;

CREATE TABLE public.fuente_lectura (
    id bigint NOT NULL,
    fuente text NOT NULL,
    recurso text NOT NULL,
    hora text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    ok integer NOT NULL,
    codigo text,
    error text,
    cuerpo text,
    huella text,
    CONSTRAINT fuente_lectura_ok_check CHECK ((ok = ANY (ARRAY[0, 1])))
);

CREATE SEQUENCE public.fuente_lectura_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.fuente_lectura_id_seq OWNED BY public.fuente_lectura.id;

CREATE VIEW public.fuente_ultimo_bueno AS
 SELECT id,
    fuente,
    recurso,
    hora,
    ok,
    codigo,
    error,
    cuerpo,
    huella
   FROM public.fuente_lectura f
  WHERE ((ok = 1) AND (id = ( SELECT max(g.id) AS max
           FROM public.fuente_lectura g
          WHERE ((g.fuente = f.fuente) AND (g.recurso = f.recurso) AND (g.ok = 1)))));

CREATE TABLE public.historial (
    n bigint NOT NULL,
    ts text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    quien text NOT NULL,
    coleccion text NOT NULL,
    id text NOT NULL,
    operacion text NOT NULL,
    antes text,
    datos text
);

CREATE SEQUENCE public.historial_n_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.historial_n_seq OWNED BY public.historial.n;

CREATE TABLE public.ia_gasto (
    id bigint NOT NULL,
    creada text NOT NULL,
    dia text NOT NULL,
    mes text NOT NULL,
    quien text NOT NULL,
    tarea text NOT NULL,
    objeto text,
    modelo text,
    llave text NOT NULL,
    lote integer DEFAULT 0 NOT NULL,
    entrada integer DEFAULT 0 NOT NULL,
    cache_escrita integer DEFAULT 0 NOT NULL,
    cache_leida integer DEFAULT 0 NOT NULL,
    salida integer DEFAULT 0 NOT NULL,
    coste_usd real DEFAULT 0 NOT NULL,
    coste_eur real DEFAULT 0 NOT NULL,
    ok integer NOT NULL,
    motivo text,
    peticion text
);

CREATE SEQUENCE public.ia_gasto_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.ia_gasto_id_seq OWNED BY public.ia_gasto.id;

CREATE TABLE public.ia_lotes (
    id text NOT NULL,
    creado text NOT NULL,
    quien text NOT NULL,
    tarea text NOT NULL,
    llave text NOT NULL,
    modelo text,
    n integer NOT NULL,
    reservado_eur real NOT NULL,
    estado text NOT NULL,
    cerrado text,
    peticiones text
);

CREATE TABLE public.ia_reservas (
    id text NOT NULL,
    creada text NOT NULL,
    tarea text NOT NULL,
    quien text NOT NULL,
    llave text NOT NULL,
    reservado_eur real NOT NULL,
    estado text NOT NULL,
    CONSTRAINT ia_reservas_estado_check CHECK ((estado = ANY (ARRAY['activa'::text, 'incierta'::text, 'cerrada'::text]))),
    CONSTRAINT ia_reservas_reservado_eur_check CHECK ((reservado_eur >= (0)::double precision))
);

CREATE TABLE public.ia_topes (
    id bigint NOT NULL,
    creada text NOT NULL,
    quien text NOT NULL,
    valores text NOT NULL,
    motivo text
);

CREATE SEQUENCE public.ia_topes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.ia_topes_id_seq OWNED BY public.ia_topes.id;

CREATE TABLE public.incidencias (
    id bigint NOT NULL,
    creada text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    quien text NOT NULL,
    cliente_id text,
    titulo text NOT NULL,
    donde text,
    por_que text,
    por_que_cambiado_por text,
    prueba_aviso text,
    estado text DEFAULT 'abierta'::text NOT NULL,
    responsable_id text,
    cerrada text,
    datos text,
    CONSTRAINT incidencias_donde_check CHECK ((donde = ANY (ARRAY['publicidad'::text, 'despacho'::text, 'integracion'::text, 'produccion'::text, 'contacto_cliente'::text]))),
    CONSTRAINT incidencias_estado_check CHECK ((estado = ANY (ARRAY['abierta'::text, 'en_curso'::text, 'resuelta'::text, 'descartada'::text]))),
    CONSTRAINT incidencias_por_que_check CHECK ((por_que = ANY (ARRAY['sistema'::text, 'configuracion'::text, 'ejecucion'::text, 'gestion_operaciones'::text])))
);

CREATE SEQUENCE public.incidencias_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.incidencias_id_seq OWNED BY public.incidencias.id;

CREATE TABLE public.intenciones_acciones (
    actor text NOT NULL,
    intencion text NOT NULL,
    huella text NOT NULL,
    accion_id bigint NOT NULL
);

CREATE TABLE public.leads_eventos (
    cliente_id text NOT NULL,
    source text NOT NULL,
    event_id text NOT NULL,
    payload text NOT NULL,
    huella text NOT NULL,
    actor_id text NOT NULL,
    fuente_key text NOT NULL,
    registrado text NOT NULL
);

CREATE TABLE public.leads_meta (
    version integer NOT NULL
);

CREATE TABLE public.leads_recibos (
    recibo_id text NOT NULL,
    cliente_id text NOT NULL,
    source text NOT NULL,
    event_id text,
    actor_id text NOT NULL,
    resultado text NOT NULL,
    motivo text NOT NULL,
    registrado text NOT NULL
);

CREATE TABLE public.llaves (
    nombre text NOT NULL,
    valor text,
    rotada text,
    rotaciones integer DEFAULT 0,
    origen text
);

CREATE TABLE public.mt_crono (
    persona text NOT NULL,
    tarea text NOT NULL,
    inicio text NOT NULL
);

CREATE TABLE public.operaciones_anomalias_276 (
    id bigint NOT NULL,
    anomalia text NOT NULL,
    revision integer NOT NULL,
    actor text NOT NULL,
    persona_id text NOT NULL,
    origen_hash text NOT NULL,
    decision text NOT NULL,
    prueba text NOT NULL,
    hora text NOT NULL,
    intencion text NOT NULL,
    request_hash text NOT NULL
);

CREATE SEQUENCE public.operaciones_anomalias_276_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.operaciones_anomalias_276_id_seq OWNED BY public.operaciones_anomalias_276.id;

CREATE TABLE public.operaciones_control_272 (
    id bigint NOT NULL,
    objeto text NOT NULL,
    revision integer NOT NULL,
    actor text NOT NULL,
    autor text NOT NULL,
    asignado text NOT NULL,
    tipo text NOT NULL,
    hora text NOT NULL,
    contenido text NOT NULL,
    intencion text NOT NULL,
    huella text NOT NULL
);

CREATE SEQUENCE public.operaciones_control_272_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.operaciones_control_272_id_seq OWNED BY public.operaciones_control_272.id;

CREATE TABLE public.operaciones_feedback_273 (
    intencion_id text NOT NULL,
    cliente_id text NOT NULL,
    semana text NOT NULL,
    revision integer NOT NULL,
    autor text NOT NULL,
    registrado_en text NOT NULL,
    estado text NOT NULL,
    nota text NOT NULL,
    huella text NOT NULL
);

CREATE TABLE public.operaciones_notas_equipo_281 (
    id bigint NOT NULL,
    persona_id text NOT NULL,
    periodo text NOT NULL,
    revision integer NOT NULL,
    autor text NOT NULL,
    hora text NOT NULL,
    nota integer,
    prueba text NOT NULL,
    accion text,
    intencion text NOT NULL,
    huella text NOT NULL
);

CREATE SEQUENCE public.operaciones_notas_equipo_281_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.operaciones_notas_equipo_281_id_seq OWNED BY public.operaciones_notas_equipo_281.id;

CREATE TABLE public.operaciones_pedidos_account_294 (
    intencion_id text NOT NULL,
    cliente_id text NOT NULL,
    tipo text NOT NULL,
    referencia_id text NOT NULL,
    revision integer NOT NULL,
    autor text NOT NULL,
    receptor text NOT NULL,
    estado text NOT NULL,
    registrado_en text NOT NULL,
    revision_fuente text NOT NULL,
    huella text NOT NULL
);

CREATE TABLE public.operaciones_prioridades_300 (
    intencion_id text NOT NULL,
    actor text NOT NULL,
    prioridad_id text NOT NULL,
    fuente_revision text NOT NULL,
    dia text NOT NULL,
    revision integer NOT NULL,
    estado text NOT NULL,
    nota text NOT NULL,
    registrado_en text NOT NULL,
    huella text NOT NULL
);

CREATE TABLE public.operaciones_registros_269 (
    id bigint NOT NULL,
    propietario text NOT NULL,
    clave text NOT NULL,
    revision integer NOT NULL,
    autor text NOT NULL,
    registrado_en text NOT NULL,
    contenido text NOT NULL,
    intencion text NOT NULL,
    huella text NOT NULL
);

CREATE SEQUENCE public.operaciones_registros_269_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.operaciones_registros_269_id_seq OWNED BY public.operaciones_registros_269.id;

CREATE TABLE public.opiniones (
    id bigint NOT NULL,
    creada text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    quien text NOT NULL,
    tipo text NOT NULL,
    prioridad text DEFAULT 'gris'::text NOT NULL,
    texto text NOT NULL,
    esperaba text,
    ruta text,
    pantalla text,
    ancho integer,
    alto integer,
    frescura text,
    captura text,
    estado text DEFAULT 'nueva'::text NOT NULL,
    estado_por text,
    estado_hora text,
    CONSTRAINT opiniones_estado_check CHECK ((estado = ANY (ARRAY['nueva'::text, 'vista'::text, 'resuelta'::text]))),
    CONSTRAINT opiniones_prioridad_check CHECK ((prioridad = ANY (ARRAY['rojo'::text, 'ambar'::text, 'gris'::text]))),
    CONSTRAINT opiniones_tipo_check CHECK ((tipo = ANY (ARRAY['fallo'::text, 'idea'::text])))
);

CREATE SEQUENCE public.opiniones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.opiniones_id_seq OWNED BY public.opiniones.id;

CREATE TABLE public.pasos (
    id bigint NOT NULL,
    ejecucion integer,
    paso text,
    intento integer,
    inicio text,
    segundos real,
    estado text,
    salida text,
    error text
);

CREATE SEQUENCE public.pasos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.pasos_id_seq OWNED BY public.pasos.id;

CREATE TABLE public.persona_puestos (
    persona_id text NOT NULL,
    puesto text NOT NULL,
    principal integer DEFAULT 0 NOT NULL,
    CONSTRAINT persona_puestos_puesto_check CHECK ((puesto = ANY (ARRAY['direccion'::text, 'finanzas_direccion'::text, 'administracion'::text, 'operaciones'::text, 'proyectos'::text, 'rrhh'::text, 'account'::text, 'trafficker'::text, 'jefa_publicidad'::text, 'especialista_ghl'::text, 'jefa_crm'::text, 'tecnico_altas'::text, 'jefa_seo'::text, 'seo'::text, 'ficha_google'::text, 'web'::text, 'redes'::text, 'produccion'::text, 'setters'::text, 'ventas_ro'::text, 'outreach'::text])))
);

CREATE TABLE public.personas (
    id text NOT NULL,
    nombre text NOT NULL,
    alias text,
    alias_todos text,
    correo text,
    otros_correos text,
    nivel integer,
    jefe_id text,
    horas_mes real DEFAULT 128 NOT NULL,
    imputa_horas text,
    estado text DEFAULT 'activo'::text NOT NULL,
    activo integer DEFAULT 1 NOT NULL,
    nota text,
    actualizado text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    actualizado_por text,
    CONSTRAINT personas_estado_check CHECK ((estado = ANY (ARRAY['activo'::text, 'dudoso'::text, 'por_incorporar'::text, 'baja'::text]))),
    CONSTRAINT personas_nivel_check CHECK (((nivel >= 1) AND (nivel <= 7)))
);

CREATE TABLE public.planes_fuegos_255 (
    accion_id text NOT NULL,
    cliente_id text NOT NULL,
    version integer NOT NULL,
    operacion text NOT NULL,
    actor_id text NOT NULL,
    hora text NOT NULL,
    payload_hash text NOT NULL,
    datos text NOT NULL
);

CREATE TABLE public.preferencias (
    persona text NOT NULL,
    clave text NOT NULL,
    valor text NOT NULL,
    cambiado text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL
);

CREATE TABLE public.rastro_cortes (
    id integer NOT NULL,
    motivo text NOT NULL,
    anotado text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL
);

CREATE TABLE public.rastro_incidencias (
    n bigint NOT NULL,
    tipo text NOT NULL,
    desde integer NOT NULL,
    hasta integer NOT NULL,
    motivo text NOT NULL,
    anotado text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    CONSTRAINT rastro_incidencias_tipo_check CHECK ((tipo = ANY (ARRAY['corte'::text, 'sin_huella'::text, 'nota'::text])))
);

CREATE SEQUENCE public.rastro_incidencias_n_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.rastro_incidencias_n_seq OWNED BY public.rastro_incidencias.n;

CREATE TABLE public.recargas (
    id bigint NOT NULL,
    pedida text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    quien text NOT NULL,
    modo text DEFAULT 'ligera'::text NOT NULL,
    estado text DEFAULT 'pendiente'::text NOT NULL,
    empezada text,
    terminada text,
    pasos text,
    CONSTRAINT recargas_estado_check CHECK ((estado = ANY (ARRAY['pendiente'::text, 'en_curso'::text, 'ok'::text, 'con_fallos'::text])))
);

CREATE SEQUENCE public.recargas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.recargas_id_seq OWNED BY public.recargas.id;

CREATE TABLE public.registro (
    id bigint NOT NULL,
    creada text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    quien text NOT NULL,
    como text,
    coleccion text NOT NULL,
    accion text,
    clave text,
    datos text,
    motivo text,
    anula_a bigint,
    origen text DEFAULT 'app'::text NOT NULL,
    huella_previa text,
    CONSTRAINT registro_check CHECK (((accion IS NULL) OR (accion <> 'no_aplica'::text) OR ((motivo IS NOT NULL) AND (length(TRIM(BOTH FROM motivo)) > 0))))
);

CREATE TABLE public.registro_huellas (
    id integer NOT NULL,
    huella text NOT NULL
);

CREATE SEQUENCE public.registro_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.registro_id_seq OWNED BY public.registro.id;

CREATE TABLE public.registros (
    id text NOT NULL,
    clave text NOT NULL,
    cliente text NOT NULL,
    actor text NOT NULL,
    payload text NOT NULL,
    hash text NOT NULL,
    estado text NOT NULL,
    creado text NOT NULL
);

CREATE TABLE public.revocaciones (
    clave text NOT NULL,
    registro text NOT NULL,
    actor text NOT NULL,
    motivo text NOT NULL
);

CREATE TABLE public.sellos (
    paso text NOT NULL,
    ultimo_bueno text,
    ultimo_intento text,
    estado text,
    motivo text
);

CREATE TABLE public.sinc_cambios (
    id bigint NOT NULL,
    clave text NOT NULL,
    accion_id integer,
    mensaje_id integer,
    creado text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    quien text NOT NULL,
    canal text NOT NULL,
    tipo text NOT NULL,
    objeto text NOT NULL,
    objeto_ref text NOT NULL,
    cliente_id text,
    modulo text,
    cambio text NOT NULL,
    base text,
    ignorado text,
    modo text NOT NULL,
    CONSTRAINT sinc_cambios_canal_check CHECK ((canal = ANY (ARRAY['clickup'::text, 'chat'::text]))),
    CONSTRAINT sinc_cambios_modo_check CHECK ((modo = ANY (ARRAY['simulado'::text, 'real'::text, 'prueba'::text])))
);

CREATE SEQUENCE public.sinc_cambios_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.sinc_cambios_id_seq OWNED BY public.sinc_cambios.id;

CREATE TABLE public.sinc_pasos (
    id bigint NOT NULL,
    cambio_id bigint NOT NULL,
    estado text NOT NULL,
    evento text NOT NULL,
    hora text DEFAULT to_char((now() AT TIME ZONE 'UTC'::text), 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    quien text,
    intento integer DEFAULT 0 NOT NULL,
    motivo text,
    detalle text,
    CONSTRAINT sinc_pasos_estado_check CHECK ((estado = ANY (ARRAY['simulado'::text, 'pendiente'::text, 'enviado'::text, 'confirmado'::text, 'fallido'::text, 'conflicto'::text, 'descartado'::text])))
);

CREATE SEQUENCE public.sinc_pasos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.sinc_pasos_id_seq OWNED BY public.sinc_pasos.id;

CREATE TABLE public.tareas_vistas_privadas (
    propietario text NOT NULL,
    id text NOT NULL,
    nombre text NOT NULL,
    filtros text NOT NULL,
    version integer NOT NULL,
    revision integer NOT NULL
);

CREATE TABLE public.tuberia_avisos (
    id bigint NOT NULL,
    dia text,
    tipo text,
    clave text,
    texto text,
    estado text,
    creado text
);

CREATE SEQUENCE public.tuberia_avisos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.tuberia_avisos_id_seq OWNED BY public.tuberia_avisos.id;

CREATE TABLE public.uso_eventos (
    id integer NOT NULL,
    instante real NOT NULL,
    actor text NOT NULL,
    visto text NOT NULL,
    pantalla text NOT NULL,
    accion text NOT NULL,
    control text NOT NULL,
    activo_ms integer NOT NULL
);

CREATE TABLE public.uso_sesiones (
    actor text NOT NULL,
    sesion text NOT NULL,
    secuencia integer NOT NULL,
    instante real NOT NULL,
    visto text NOT NULL,
    pantalla text NOT NULL
);

CREATE TABLE public.uso_ventanas (
    actor text NOT NULL,
    fin real NOT NULL
);

CREATE VIEW public.v_cartera_hoy AS
 SELECT persona_id,
    cliente_id,
    silla,
        CASE
            WHEN (suplencia = 1) THEN 'suplencia'::text
            ELSE 'titular'::text
        END AS via
   FROM public.asignaciones
  WHERE (((desde IS NULL) OR (desde <= to_char((CURRENT_DATE)::timestamp with time zone, 'YYYY-MM-DD'::text))) AND ((hasta IS NULL) OR (hasta >= to_char((CURRENT_DATE)::timestamp with time zone, 'YYYY-MM-DD'::text))));

ALTER TABLE ONLY public.acciones ALTER COLUMN id SET DEFAULT nextval('public.acciones_id_seq'::regclass);

ALTER TABLE ONLY public.altas_tareas ALTER COLUMN id SET DEFAULT nextval('public.altas_tareas_id_seq'::regclass);

ALTER TABLE ONLY public.asignaciones ALTER COLUMN id SET DEFAULT nextval('public.asignaciones_id_seq'::regclass);

ALTER TABLE ONLY public.avisos ALTER COLUMN id SET DEFAULT nextval('public.avisos_id_seq'::regclass);

ALTER TABLE ONLY public.avisos_prog_cambios ALTER COLUMN n SET DEFAULT nextval('public.avisos_prog_cambios_n_seq'::regclass);

ALTER TABLE ONLY public.avisos_prog_hechos ALTER COLUMN n SET DEFAULT nextval('public.avisos_prog_hechos_n_seq'::regclass);

ALTER TABLE ONLY public.canal_mensajes ALTER COLUMN id SET DEFAULT nextval('public.canal_mensajes_id_seq'::regclass);

ALTER TABLE ONLY public.canal_miembros ALTER COLUMN n SET DEFAULT nextval('public.canal_miembros_n_seq'::regclass);

ALTER TABLE ONLY public.datos_version ALTER COLUMN id SET DEFAULT nextval('public.datos_version_id_seq'::regclass);

ALTER TABLE ONLY public.decisiones ALTER COLUMN id SET DEFAULT nextval('public.decisiones_id_seq'::regclass);

ALTER TABLE ONLY public.ejecuciones ALTER COLUMN id SET DEFAULT nextval('public.ejecuciones_id_seq'::regclass);

ALTER TABLE ONLY public.envio_pasos ALTER COLUMN id SET DEFAULT nextval('public.envio_pasos_id_seq'::regclass);

ALTER TABLE ONLY public.envios ALTER COLUMN id SET DEFAULT nextval('public.envios_id_seq'::regclass);

ALTER TABLE ONLY public.eventos ALTER COLUMN n SET DEFAULT nextval('public.eventos_n_seq'::regclass);

ALTER TABLE ONLY public.fuente_lectura ALTER COLUMN id SET DEFAULT nextval('public.fuente_lectura_id_seq'::regclass);

ALTER TABLE ONLY public.historial ALTER COLUMN n SET DEFAULT nextval('public.historial_n_seq'::regclass);

ALTER TABLE ONLY public.ia_gasto ALTER COLUMN id SET DEFAULT nextval('public.ia_gasto_id_seq'::regclass);

ALTER TABLE ONLY public.ia_topes ALTER COLUMN id SET DEFAULT nextval('public.ia_topes_id_seq'::regclass);

ALTER TABLE ONLY public.incidencias ALTER COLUMN id SET DEFAULT nextval('public.incidencias_id_seq'::regclass);

ALTER TABLE ONLY public.operaciones_anomalias_276 ALTER COLUMN id SET DEFAULT nextval('public.operaciones_anomalias_276_id_seq'::regclass);

ALTER TABLE ONLY public.operaciones_control_272 ALTER COLUMN id SET DEFAULT nextval('public.operaciones_control_272_id_seq'::regclass);

ALTER TABLE ONLY public.operaciones_notas_equipo_281 ALTER COLUMN id SET DEFAULT nextval('public.operaciones_notas_equipo_281_id_seq'::regclass);

ALTER TABLE ONLY public.operaciones_registros_269 ALTER COLUMN id SET DEFAULT nextval('public.operaciones_registros_269_id_seq'::regclass);

ALTER TABLE ONLY public.opiniones ALTER COLUMN id SET DEFAULT nextval('public.opiniones_id_seq'::regclass);

ALTER TABLE ONLY public.pasos ALTER COLUMN id SET DEFAULT nextval('public.pasos_id_seq'::regclass);

ALTER TABLE ONLY public.rastro_incidencias ALTER COLUMN n SET DEFAULT nextval('public.rastro_incidencias_n_seq'::regclass);

ALTER TABLE ONLY public.recargas ALTER COLUMN id SET DEFAULT nextval('public.recargas_id_seq'::regclass);

ALTER TABLE ONLY public.registro ALTER COLUMN id SET DEFAULT nextval('public.registro_id_seq'::regclass);

ALTER TABLE ONLY public.sinc_cambios ALTER COLUMN id SET DEFAULT nextval('public.sinc_cambios_id_seq'::regclass);

ALTER TABLE ONLY public.sinc_pasos ALTER COLUMN id SET DEFAULT nextval('public.sinc_pasos_id_seq'::regclass);

ALTER TABLE ONLY public.tuberia_avisos ALTER COLUMN id SET DEFAULT nextval('public.tuberia_avisos_id_seq'::regclass);

ALTER TABLE ONLY public.acciones
    ADD CONSTRAINT acciones_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.actas_claves
    ADD CONSTRAINT actas_claves_pkey PRIMARY KEY (quien, clave);

ALTER TABLE ONLY public.actas_lotes
    ADD CONSTRAINT actas_lotes_pkey PRIMARY KEY (quien, cliente_id, huella);

ALTER TABLE ONLY public.altas_recibos
    ADD CONSTRAINT altas_recibos_pkey PRIMARY KEY (clave);

ALTER TABLE ONLY public.altas_tareas
    ADD CONSTRAINT altas_tareas_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.asignaciones
    ADD CONSTRAINT asignaciones_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.avisos
    ADD CONSTRAINT avisos_dia_tipo_clave_key UNIQUE (dia, tipo, clave);

ALTER TABLE ONLY public.avisos
    ADD CONSTRAINT avisos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.avisos_prog_cambios
    ADD CONSTRAINT avisos_prog_cambios_pkey PRIMARY KEY (n);

ALTER TABLE ONLY public.avisos_prog_hechos
    ADD CONSTRAINT avisos_prog_hechos_pkey PRIMARY KEY (n);

ALTER TABLE ONLY public.canal_campana
    ADD CONSTRAINT canal_campana_pkey PRIMARY KEY (persona_id);

ALTER TABLE ONLY public.canal_grupos
    ADD CONSTRAINT canal_grupos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.canal_leidos
    ADD CONSTRAINT canal_leidos_pkey PRIMARY KEY (persona_id, canal_id);

ALTER TABLE ONLY public.canal_mensajes
    ADD CONSTRAINT canal_mensajes_clave_key UNIQUE (clave);

ALTER TABLE ONLY public.canal_mensajes
    ADD CONSTRAINT canal_mensajes_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.canal_miembros
    ADD CONSTRAINT canal_miembros_pkey PRIMARY KEY (n);

ALTER TABLE ONLY public.canal_preferencias
    ADD CONSTRAINT canal_preferencias_pkey PRIMARY KEY (persona_id);

ALTER TABLE ONLY public.canal_resumenes
    ADD CONSTRAINT canal_resumenes_pkey PRIMARY KEY (persona_id, dia);

ALTER TABLE ONLY public.datos_blob
    ADD CONSTRAINT datos_blob_pkey PRIMARY KEY (sha);

ALTER TABLE ONLY public.datos_fichero
    ADD CONSTRAINT datos_fichero_pkey PRIMARY KEY (version, ruta);

ALTER TABLE ONLY public.datos_version
    ADD CONSTRAINT datos_version_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.decisiones_intenciones_382
    ADD CONSTRAINT decisiones_intenciones_382_pkey PRIMARY KEY (intencion_id);

ALTER TABLE ONLY public.decisiones
    ADD CONSTRAINT decisiones_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.docs
    ADD CONSTRAINT docs_pkey PRIMARY KEY (coleccion, id);

ALTER TABLE ONLY public.ejecuciones
    ADD CONSTRAINT ejecuciones_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.envio_pasos
    ADD CONSTRAINT envio_pasos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.envios
    ADD CONSTRAINT envios_accion_id_key UNIQUE (accion_id);

ALTER TABLE ONLY public.envios
    ADD CONSTRAINT envios_clave_key UNIQUE (clave);

ALTER TABLE ONLY public.envios
    ADD CONSTRAINT envios_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.eventos
    ADD CONSTRAINT eventos_pkey PRIMARY KEY (n);

ALTER TABLE ONLY public.fuente_lectura
    ADD CONSTRAINT fuente_lectura_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.historial
    ADD CONSTRAINT historial_pkey PRIMARY KEY (n);

ALTER TABLE ONLY public.ia_gasto
    ADD CONSTRAINT ia_gasto_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ia_lotes
    ADD CONSTRAINT ia_lotes_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ia_reservas
    ADD CONSTRAINT ia_reservas_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ia_topes
    ADD CONSTRAINT ia_topes_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.incidencias
    ADD CONSTRAINT incidencias_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.intenciones_acciones
    ADD CONSTRAINT intenciones_acciones_pkey PRIMARY KEY (actor, intencion);

ALTER TABLE ONLY public.leads_eventos
    ADD CONSTRAINT leads_eventos_pkey PRIMARY KEY (cliente_id, source, event_id);

ALTER TABLE ONLY public.leads_recibos
    ADD CONSTRAINT leads_recibos_pkey PRIMARY KEY (recibo_id);

ALTER TABLE ONLY public.llaves
    ADD CONSTRAINT llaves_pkey PRIMARY KEY (nombre);

ALTER TABLE ONLY public.mt_crono
    ADD CONSTRAINT mt_crono_pkey PRIMARY KEY (persona);

ALTER TABLE ONLY public.operaciones_anomalias_276
    ADD CONSTRAINT operaciones_anomalias_276_actor_intencion_key UNIQUE (actor, intencion);

ALTER TABLE ONLY public.operaciones_anomalias_276
    ADD CONSTRAINT operaciones_anomalias_276_anomalia_revision_key UNIQUE (anomalia, revision);

ALTER TABLE ONLY public.operaciones_anomalias_276
    ADD CONSTRAINT operaciones_anomalias_276_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.operaciones_control_272
    ADD CONSTRAINT operaciones_control_272_actor_intencion_key UNIQUE (actor, intencion);

ALTER TABLE ONLY public.operaciones_control_272
    ADD CONSTRAINT operaciones_control_272_objeto_revision_key UNIQUE (objeto, revision);

ALTER TABLE ONLY public.operaciones_control_272
    ADD CONSTRAINT operaciones_control_272_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.operaciones_feedback_273
    ADD CONSTRAINT operaciones_feedback_273_cliente_id_semana_revision_key UNIQUE (cliente_id, semana, revision);

ALTER TABLE ONLY public.operaciones_feedback_273
    ADD CONSTRAINT operaciones_feedback_273_pkey PRIMARY KEY (intencion_id);

ALTER TABLE ONLY public.operaciones_notas_equipo_281
    ADD CONSTRAINT operaciones_notas_equipo_281_autor_intencion_key UNIQUE (autor, intencion);

ALTER TABLE ONLY public.operaciones_notas_equipo_281
    ADD CONSTRAINT operaciones_notas_equipo_281_persona_id_revision_key UNIQUE (persona_id, revision);

ALTER TABLE ONLY public.operaciones_notas_equipo_281
    ADD CONSTRAINT operaciones_notas_equipo_281_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.operaciones_pedidos_account_294
    ADD CONSTRAINT operaciones_pedidos_account_294_pkey PRIMARY KEY (intencion_id);

ALTER TABLE ONLY public.operaciones_pedidos_account_294
    ADD CONSTRAINT operaciones_pedidos_account_2_cliente_id_tipo_referencia_id_key UNIQUE (cliente_id, tipo, referencia_id, revision);

ALTER TABLE ONLY public.operaciones_prioridades_300
    ADD CONSTRAINT operaciones_prioridades_300_actor_prioridad_id_fuente_revis_key UNIQUE (actor, prioridad_id, fuente_revision, dia, revision);

ALTER TABLE ONLY public.operaciones_prioridades_300
    ADD CONSTRAINT operaciones_prioridades_300_pkey PRIMARY KEY (intencion_id);

ALTER TABLE ONLY public.operaciones_registros_269
    ADD CONSTRAINT operaciones_registros_269_autor_intencion_key UNIQUE (autor, intencion);

ALTER TABLE ONLY public.operaciones_registros_269
    ADD CONSTRAINT operaciones_registros_269_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.operaciones_registros_269
    ADD CONSTRAINT operaciones_registros_269_propietario_clave_revision_key UNIQUE (propietario, clave, revision);

ALTER TABLE ONLY public.opiniones
    ADD CONSTRAINT opiniones_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.pasos
    ADD CONSTRAINT pasos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.persona_puestos
    ADD CONSTRAINT persona_puestos_pkey PRIMARY KEY (persona_id, puesto);

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_correo_key UNIQUE (correo);

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.planes_fuegos_255
    ADD CONSTRAINT planes_fuegos_255_cliente_id_version_key UNIQUE (cliente_id, version);

ALTER TABLE ONLY public.planes_fuegos_255
    ADD CONSTRAINT planes_fuegos_255_pkey PRIMARY KEY (accion_id);

ALTER TABLE ONLY public.preferencias
    ADD CONSTRAINT preferencias_pkey PRIMARY KEY (persona, clave);

ALTER TABLE ONLY public.rastro_cortes
    ADD CONSTRAINT rastro_cortes_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.rastro_incidencias
    ADD CONSTRAINT rastro_incidencias_pkey PRIMARY KEY (n);

ALTER TABLE ONLY public.recargas
    ADD CONSTRAINT recargas_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.registro_huellas
    ADD CONSTRAINT registro_huellas_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.registro
    ADD CONSTRAINT registro_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.registros
    ADD CONSTRAINT registros_clave_key UNIQUE (clave);

ALTER TABLE ONLY public.registros
    ADD CONSTRAINT registros_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.revocaciones
    ADD CONSTRAINT revocaciones_pkey PRIMARY KEY (clave);

ALTER TABLE ONLY public.sellos
    ADD CONSTRAINT sellos_pkey PRIMARY KEY (paso);

ALTER TABLE ONLY public.sinc_cambios
    ADD CONSTRAINT sinc_cambios_accion_id_key UNIQUE (accion_id);

ALTER TABLE ONLY public.sinc_cambios
    ADD CONSTRAINT sinc_cambios_clave_key UNIQUE (clave);

ALTER TABLE ONLY public.sinc_cambios
    ADD CONSTRAINT sinc_cambios_mensaje_id_key UNIQUE (mensaje_id);

ALTER TABLE ONLY public.sinc_cambios
    ADD CONSTRAINT sinc_cambios_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.sinc_pasos
    ADD CONSTRAINT sinc_pasos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.tareas_vistas_privadas
    ADD CONSTRAINT tareas_vistas_privadas_pkey PRIMARY KEY (propietario, id);

ALTER TABLE ONLY public.tuberia_avisos
    ADD CONSTRAINT tuberia_avisos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.uso_eventos
    ADD CONSTRAINT uso_eventos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.uso_sesiones
    ADD CONSTRAINT uso_sesiones_pkey PRIMARY KEY (actor, sesion);

ALTER TABLE ONLY public.uso_ventanas
    ADD CONSTRAINT uso_ventanas_pkey PRIMARY KEY (actor);

CREATE INDEX avisos_prog_hechos_clave ON public.avisos_prog_hechos USING btree (clave);

CREATE INDEX canal_mensajes_canal ON public.canal_mensajes USING btree (canal_id, id);

CREATE INDEX i_acc_obj ON public.acciones USING btree (objeto);

CREATE INDEX i_asig_cliente ON public.asignaciones USING btree (cliente_id, silla, hasta);

CREATE INDEX i_asig_persona ON public.asignaciones USING btree (persona_id, hasta);

CREATE INDEX i_envio_pasos ON public.envio_pasos USING btree (envio_id, id);

CREATE INDEX i_envios_quien ON public.envios USING btree (quien);

CREATE INDEX i_fuente_lectura ON public.fuente_lectura USING btree (fuente, recurso, ok, id);

CREATE INDEX i_reg_col ON public.registro USING btree (coleccion, clave);

CREATE INDEX i_reg_quien ON public.registro USING btree (quien, creada);

CREATE INDEX i_sinc_obj ON public.sinc_cambios USING btree (objeto_ref, id);

CREATE INDEX i_sinc_pasos ON public.sinc_pasos USING btree (cambio_id, id);

CREATE INDEX i_sinc_quien ON public.sinc_cambios USING btree (quien);

CREATE INDEX ia_gasto_mes ON public.ia_gasto USING btree (mes, dia);

CREATE INDEX uso_actor ON public.uso_eventos USING btree (actor, instante);

CREATE INDEX uso_instante ON public.uso_eventos USING btree (instante);

CREATE TRIGGER acciones_sin_delete BEFORE DELETE ON public.acciones FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Las acciones no se borran');

CREATE TRIGGER acciones_sin_delete_truncate BEFORE TRUNCATE ON public.acciones FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Las acciones no se borran');

CREATE TRIGGER acciones_solo_estado BEFORE UPDATE ON public.acciones FOR EACH ROW EXECUTE FUNCTION public.acciones_solo_estado_fn();

CREATE TRIGGER altas_tareas_sin_delete BEFORE DELETE ON public.altas_tareas FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Una tarea no se borra');

CREATE TRIGGER altas_tareas_sin_delete_truncate BEFORE TRUNCATE ON public.altas_tareas FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Una tarea no se borra');

CREATE TRIGGER altas_tareas_solo_estado BEFORE UPDATE ON public.altas_tareas FOR EACH ROW EXECUTE FUNCTION public.altas_tareas_solo_estado_fn();

CREATE TRIGGER avisos_prog_cambios_sin_delete BEFORE DELETE ON public.avisos_prog_cambios FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un cambio de regla no se borra');

CREATE TRIGGER avisos_prog_cambios_sin_delete_truncate BEFORE TRUNCATE ON public.avisos_prog_cambios FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Un cambio de regla no se borra');

CREATE TRIGGER avisos_prog_cambios_sin_update BEFORE UPDATE ON public.avisos_prog_cambios FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un cambio de regla no se cambia');

CREATE TRIGGER avisos_prog_hechos_sin_delete BEFORE DELETE ON public.avisos_prog_hechos FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un «hecho» no se borra');

CREATE TRIGGER avisos_prog_hechos_sin_delete_truncate BEFORE TRUNCATE ON public.avisos_prog_hechos FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Un «hecho» no se borra');

CREATE TRIGGER avisos_prog_hechos_sin_update BEFORE UPDATE ON public.avisos_prog_hechos FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un «hecho» no se cambia');

CREATE TRIGGER canal_grupos_sin_delete BEFORE DELETE ON public.canal_grupos FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un grupo no se borra');

CREATE TRIGGER canal_grupos_sin_delete_truncate BEFORE TRUNCATE ON public.canal_grupos FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Un grupo no se borra');

CREATE TRIGGER canal_mensajes_sin_delete BEFORE DELETE ON public.canal_mensajes FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un mensaje no se borra');

CREATE TRIGGER canal_mensajes_sin_delete_truncate BEFORE TRUNCATE ON public.canal_mensajes FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Un mensaje no se borra');

CREATE TRIGGER canal_mensajes_sin_update BEFORE UPDATE ON public.canal_mensajes FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un mensaje no se cambia');

CREATE TRIGGER canal_miembros_sin_delete BEFORE DELETE ON public.canal_miembros FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('El historial de miembros no se borra');

CREATE TRIGGER canal_miembros_sin_delete_truncate BEFORE TRUNCATE ON public.canal_miembros FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('El historial de miembros no se borra');

CREATE TRIGGER canal_miembros_sin_update BEFORE UPDATE ON public.canal_miembros FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('El historial de miembros no se cambia');

CREATE TRIGGER canal_resumenes_sin_delete BEFORE DELETE ON public.canal_resumenes FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un resumen no se borra');

CREATE TRIGGER canal_resumenes_sin_delete_truncate BEFORE TRUNCATE ON public.canal_resumenes FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Un resumen no se borra');

CREATE TRIGGER cortes_sin_delete BEFORE DELETE ON public.rastro_cortes FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un corte anotado no se borra');

CREATE TRIGGER cortes_sin_delete_truncate BEFORE TRUNCATE ON public.rastro_cortes FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Un corte anotado no se borra');

CREATE TRIGGER cortes_sin_update BEFORE UPDATE ON public.rastro_cortes FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un corte anotado no se cambia');

CREATE TRIGGER decisiones382_no_delete BEFORE DELETE ON public.decisiones_intenciones_382 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Intención inmutable');

CREATE TRIGGER decisiones382_no_delete_truncate BEFORE TRUNCATE ON public.decisiones_intenciones_382 FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Intención inmutable');

CREATE TRIGGER decisiones382_no_update BEFORE UPDATE ON public.decisiones_intenciones_382 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Intención inmutable');

CREATE TRIGGER decisiones_sin_delete BEFORE DELETE ON public.decisiones FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Las decisiones no se borran');

CREATE TRIGGER decisiones_sin_delete_truncate BEFORE TRUNCATE ON public.decisiones FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Las decisiones no se borran');

CREATE TRIGGER decisiones_una_respuesta BEFORE UPDATE ON public.decisiones FOR EACH ROW EXECUTE FUNCTION public.decisiones_una_respuesta_fn();

CREATE TRIGGER envio_pasos_sin_delete BEFORE DELETE ON public.envio_pasos FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un paso no se borra');

CREATE TRIGGER envio_pasos_sin_delete_truncate BEFORE TRUNCATE ON public.envio_pasos FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Un paso no se borra');

CREATE TRIGGER envio_pasos_sin_update BEFORE UPDATE ON public.envio_pasos FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un paso no se cambia');

CREATE TRIGGER envios_sin_delete BEFORE DELETE ON public.envios FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un envío no se borra');

CREATE TRIGGER envios_sin_delete_truncate BEFORE TRUNCATE ON public.envios FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Un envío no se borra');

CREATE TRIGGER envios_sin_update BEFORE UPDATE ON public.envios FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un envío no se cambia: se añade un paso');

CREATE TRIGGER feedback273_sin_delete BEFORE DELETE ON public.operaciones_feedback_273 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Opinión declarada inmutable');

CREATE TRIGGER feedback273_sin_delete_truncate BEFORE TRUNCATE ON public.operaciones_feedback_273 FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Opinión declarada inmutable');

CREATE TRIGGER feedback273_sin_update BEFORE UPDATE ON public.operaciones_feedback_273 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Opinión declarada inmutable');

CREATE TRIGGER fuego255_sin_delete BEFORE DELETE ON public.planes_fuegos_255 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('El historial de planes no se borra');

CREATE TRIGGER fuego255_sin_delete_truncate BEFORE TRUNCATE ON public.planes_fuegos_255 FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('El historial de planes no se borra');

CREATE TRIGGER fuego255_sin_update BEFORE UPDATE ON public.planes_fuegos_255 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('El historial de planes no se modifica');

CREATE TRIGGER historial_sin_delete BEFORE DELETE ON public.historial FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('El historial no se borra');

CREATE TRIGGER historial_sin_delete_truncate BEFORE TRUNCATE ON public.historial FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('El historial no se borra');

CREATE TRIGGER historial_sin_update BEFORE UPDATE ON public.historial FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('El historial no se modifica');

CREATE TRIGGER huellas_sin_delete BEFORE DELETE ON public.registro_huellas FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('La huella del rastro no se borra');

CREATE TRIGGER huellas_sin_delete_truncate BEFORE TRUNCATE ON public.registro_huellas FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('La huella del rastro no se borra');

CREATE TRIGGER huellas_sin_reinsertar_569 BEFORE INSERT ON public.registro_huellas FOR EACH ROW EXECUTE FUNCTION public.huellas_sin_reinsertar_569_fn();

CREATE TRIGGER huellas_sin_update BEFORE UPDATE ON public.registro_huellas FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('La huella del rastro no se modifica');

CREATE TRIGGER ia_gasto_sin_delete BEFORE DELETE ON public.ia_gasto FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('El gasto de la IA no se borra');

CREATE TRIGGER ia_gasto_sin_delete_truncate BEFORE TRUNCATE ON public.ia_gasto FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('El gasto de la IA no se borra');

CREATE TRIGGER ia_gasto_sin_update BEFORE UPDATE ON public.ia_gasto FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('El gasto de la IA no se cambia');

CREATE TRIGGER ia_reservas_sin_delete BEFORE DELETE ON public.ia_reservas FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Una reserva no se borra');

CREATE TRIGGER ia_reservas_sin_delete_truncate BEFORE TRUNCATE ON public.ia_reservas FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Una reserva no se borra');

CREATE TRIGGER ia_topes_sin_delete BEFORE DELETE ON public.ia_topes FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un cambio de topes no se borra');

CREATE TRIGGER ia_topes_sin_delete_truncate BEFORE TRUNCATE ON public.ia_topes FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Un cambio de topes no se borra');

CREATE TRIGGER ia_topes_sin_update BEFORE UPDATE ON public.ia_topes FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un cambio de topes no se reescribe');

CREATE TRIGGER incidencias_sin_delete BEFORE DELETE ON public.rastro_incidencias FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Una incidencia del rastro no se borra');

CREATE TRIGGER incidencias_sin_delete_truncate BEFORE TRUNCATE ON public.rastro_incidencias FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Una incidencia del rastro no se borra');

CREATE TRIGGER incidencias_sin_update BEFORE UPDATE ON public.rastro_incidencias FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Una incidencia del rastro no se cambia');

CREATE TRIGGER operaciones_269_sin_delete BEFORE DELETE ON public.operaciones_registros_269 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Registro operativo inmutable');

CREATE TRIGGER operaciones_269_sin_delete_truncate BEFORE TRUNCATE ON public.operaciones_registros_269 FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Registro operativo inmutable');

CREATE TRIGGER operaciones_269_sin_update BEFORE UPDATE ON public.operaciones_registros_269 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Registro operativo inmutable');

CREATE TRIGGER operaciones_272_sin_delete BEFORE DELETE ON public.operaciones_control_272 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Registro de control inmutable');

CREATE TRIGGER operaciones_272_sin_delete_truncate BEFORE TRUNCATE ON public.operaciones_control_272 FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Registro de control inmutable');

CREATE TRIGGER operaciones_272_sin_update BEFORE UPDATE ON public.operaciones_control_272 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Registro de control inmutable');

CREATE TRIGGER operaciones_276_sin_delete BEFORE DELETE ON public.operaciones_anomalias_276 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Revisión de horas inmutable');

CREATE TRIGGER operaciones_276_sin_delete_truncate BEFORE TRUNCATE ON public.operaciones_anomalias_276 FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Revisión de horas inmutable');

CREATE TRIGGER operaciones_276_sin_update BEFORE UPDATE ON public.operaciones_anomalias_276 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Revisión de horas inmutable');

CREATE TRIGGER operaciones_281_sin_delete BEFORE DELETE ON public.operaciones_notas_equipo_281 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Nota humana inmutable');

CREATE TRIGGER operaciones_281_sin_delete_truncate BEFORE TRUNCATE ON public.operaciones_notas_equipo_281 FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Nota humana inmutable');

CREATE TRIGGER operaciones_281_sin_update BEFORE UPDATE ON public.operaciones_notas_equipo_281 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Nota humana inmutable');

CREATE TRIGGER opiniones_sin_delete BEFORE DELETE ON public.opiniones FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Las opiniones no se borran');

CREATE TRIGGER opiniones_sin_delete_truncate BEFORE TRUNCATE ON public.opiniones FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Las opiniones no se borran');

CREATE TRIGGER opiniones_solo_estado BEFORE UPDATE ON public.opiniones FOR EACH ROW EXECUTE FUNCTION public.opiniones_solo_estado_fn();

CREATE TRIGGER pedidos294_no_delete BEFORE DELETE ON public.operaciones_pedidos_account_294 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Pedido inmutable');

CREATE TRIGGER pedidos294_no_delete_truncate BEFORE TRUNCATE ON public.operaciones_pedidos_account_294 FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Pedido inmutable');

CREATE TRIGGER pedidos294_no_update BEFORE UPDATE ON public.operaciones_pedidos_account_294 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Pedido inmutable');

CREATE TRIGGER prioridades300_sin_delete BEFORE DELETE ON public.operaciones_prioridades_300 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Rastro propio inmutable');

CREATE TRIGGER prioridades300_sin_delete_truncate BEFORE TRUNCATE ON public.operaciones_prioridades_300 FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Rastro propio inmutable');

CREATE TRIGGER prioridades300_sin_update BEFORE UPDATE ON public.operaciones_prioridades_300 FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Rastro propio inmutable');

CREATE TRIGGER recargas_sin_delete BEFORE DELETE ON public.recargas FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Las recargas no se borran');

CREATE TRIGGER recargas_sin_delete_truncate BEFORE TRUNCATE ON public.recargas FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Las recargas no se borran');

CREATE TRIGGER registro_sin_delete BEFORE DELETE ON public.registro FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('El rastro no se borra: crea una anulación');

CREATE TRIGGER registro_sin_delete_truncate BEFORE TRUNCATE ON public.registro FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('El rastro no se borra: crea una anulación');

CREATE TRIGGER registro_sin_reinsertar_569 BEFORE INSERT ON public.registro FOR EACH ROW EXECUTE FUNCTION public.registro_sin_reinsertar_569_fn();

CREATE TRIGGER registro_sin_update BEFORE UPDATE ON public.registro FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('El rastro no se modifica: crea una anulación');

CREATE TRIGGER sinc_cambios_sin_delete BEFORE DELETE ON public.sinc_cambios FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un cambio no se borra');

CREATE TRIGGER sinc_cambios_sin_delete_truncate BEFORE TRUNCATE ON public.sinc_cambios FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Un cambio no se borra');

CREATE TRIGGER sinc_cambios_sin_update BEFORE UPDATE ON public.sinc_cambios FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un cambio no se cambia: se añade un paso');

CREATE TRIGGER sinc_pasos_sin_delete BEFORE DELETE ON public.sinc_pasos FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un paso no se borra');

CREATE TRIGGER sinc_pasos_sin_delete_truncate BEFORE TRUNCATE ON public.sinc_pasos FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido('Un paso no se borra');

CREATE TRIGGER sinc_pasos_sin_update BEFORE UPDATE ON public.sinc_pasos FOR EACH ROW EXECUTE FUNCTION public.ro_prohibido('Un paso no se cambia');

ALTER TABLE ONLY public.decisiones
    ADD CONSTRAINT decisiones_anula_a_fkey FOREIGN KEY (anula_a) REFERENCES public.decisiones(id);

ALTER TABLE ONLY public.envio_pasos
    ADD CONSTRAINT envio_pasos_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES public.envios(id);

ALTER TABLE ONLY public.intenciones_acciones
    ADD CONSTRAINT intenciones_acciones_accion_id_fkey FOREIGN KEY (accion_id) REFERENCES public.acciones(id);

ALTER TABLE ONLY public.persona_puestos
    ADD CONSTRAINT persona_puestos_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES public.personas(id);

ALTER TABLE ONLY public.registro
    ADD CONSTRAINT registro_anula_a_fkey FOREIGN KEY (anula_a) REFERENCES public.registro(id);

ALTER TABLE ONLY public.sinc_pasos
    ADD CONSTRAINT sinc_pasos_cambio_id_fkey FOREIGN KEY (cambio_id) REFERENCES public.sinc_cambios(id);

