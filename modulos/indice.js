// modulos/indice.js · catálogo de módulos M1-M22 del 00 §2 (y el catálogo de componentes).
//
// Cada entrada lleva los metadatos que necesita la carcasa para pintar el menú ANTES de cargar
// el módulo. Cuando un módulo se construye:
//   1. se crea modulos/<id>.js con el contrato (ver LEEME.md),
//   2. aquí se pone  fichero: './<id>.js'  y  estado: 'hecho'.
// Si el fichero exporta sus propios puestos_que_lo_ven, mandan los del fichero.
//
// puestos_que_lo_ven: { puesto_id: 'todo' | 'suyo' | 'resumen' }  ('*' = todos los puestos; null = excluido)
//   todo = ● (todo lo de su ámbito) · suyo = ◐ (solo lo suyo o su cartera) · resumen = ○ (cifras sin detalle)
// Sale de la matriz de la v1 (sigue valiendo) con los cambios de la v2: «En rojo» lo ven todos;
// la productividad, cada uno la suya.

const TODOS = { '*': 'todo' };
const DIR = { direccion: 'todo', finanzas_direccion: 'todo', operaciones: 'todo', proyectos: 'todo' };

export const GRUPOS = ['Operaciones', 'Hoy', 'Clientes', 'Captación y CRM', 'SEO, web y redes', 'Equipo', 'Ventas de RO', 'Dinero', 'Sistema'];

export const MODULOS = [
  { id: 'operaciones', num: 'OP1', titulo: 'Dirección de operaciones', grupo: 'Operaciones', fase: 1, estado: 'hecho', fichero: './operaciones.js',
    puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo', account: 'suyo' },
    resumen: 'Los 17 apartados del panel original, con control macro para Operaciones y cartera propia para accounts.' },
  { id: 'prioridades-cliente', num: 'C01', titulo: 'Prioridades por cliente', grupo: 'Hoy', fase: 1, estado: 'hecho', fichero: './prioridades_cliente.js',
    puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo', proyectos: 'todo', account: 'suyo', trafficker: 'suyo', jefa_publicidad: 'todo', especialista_ghl: 'suyo', jefa_crm: 'todo', seo: 'suyo', jefa_seo: 'todo' },
    resumen: 'Evidencia, recomendaciones y mediciones pendientes por cliente. Primera entrega Paid y CRM, sin ejecutar cambios externos.' },
  { id: 'uso-app', num: 'U01', titulo: 'Uso y mejoras', grupo: 'Equipo', fase: 1, estado: 'hecho', fichero: './uso_app.js',
    puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo' }, resumen: 'Pantallas, acciones y tiempo activo para mejorar la facilidad de uso.' },
  // M1 (2-oct): orquestador. Bloques por puesto en data/mi_dia/config.json; datos de los demás módulos ya recortados
  // (ctx.datosModulo) + data/mi_dia/cambios.json y ronda_mili.json (fuentes_mi_dia/generar_mi_dia.py). Ruta #/mi-dia/<puesto>.
  { id: 'mi-dia', num: 'M1', titulo: 'Mi día', grupo: 'Hoy', fase: 1, estado: 'hecho', fichero: './mi_dia.js', puestos_que_lo_ven: { ...TODOS, setters: null },   // ronda 9 (D-P-MID2): los setters van directos a #/setters
    resumen: 'Lo primero que hacer hoy según el puesto: el número que manda, lo primero hoy (máx. 3) y hasta 7 bloques, cliente primero.' },
  // Mi trabajo (3-oct, encargo de Tomás «que el equipo deje de usar ClickUp en el día a día»): sus tareas hoy, semana y mes,
  // actuar sin salir (estado, hecha, fecha, comentario) e imputar horas. Todo a la copia segura de sincronia.py (mi_trabajo.py).
  // Datos: data/mi_trabajo/mi_trabajo.json (fuentes_mi_trabajo/generar_mi_trabajo.py). Lo ven quienes tienen tareas o imputan horas.
  { id: 'mi-trabajo', num: 'MT1', titulo: 'Mi trabajo', grupo: 'Hoy', fase: 1, estado: 'hecho', fichero: './mi_trabajo.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', rrhh: 'todo', proyectos: 'todo', jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo', setters: null, administracion: null },
    resumen: 'Tus tareas de ClickUp de hoy, la semana y el mes: cambiar estado, marcar hecha, cambiar fecha, comentar e imputar horas con cronómetro, sin salir de la app. Se pasa a ClickUp cuando se active la sincronía.' },
  { id: 'en-rojo', num: 'M2', titulo: 'En rojo', grupo: 'Hoy', fase: 1, estado: 'hecho', fichero: './en_rojo.js', puestos_que_lo_ven: TODOS,
    resumen: 'Clientes en rojo con motivo y responsable; detalle solo para quien lo lleva.' },
  { id: 'bandeja', num: 'M3', titulo: 'Bandeja', grupo: 'Hoy', fase: 1, estado: 'hecho', fichero: './bandeja.js',
    puestos_que_lo_ven: { ...DIR, tecnico_altas: 'suyo', jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo', account: 'suyo', trafficker: 'suyo', especialista_ghl: 'suyo' },
    resumen: 'Correos de clientes con 24/48 h (Desk), llamadas sin devolver (Zadarma), quejas arriba, por account y día; contestar con tu firma, nota, asignar, cerrar, «no aplica» (simulado hasta W1); triaje sin agente; WhatsApp en W6.' },
  // M23 y M24 (2-oct, petición de Tomás). Datos: data/agenda/ (fuentes_agenda/generar_agenda.py) y data/chat_equipo/p_<persona>.json
  // (fuentes_chat_equipo/generar_chat_equipo.py). Cada uno ve lo suyo; jefes su equipo (agenda); Mili y Tomás, todo.
  { id: 'agenda', num: 'M23', titulo: 'Agenda', grupo: 'Hoy', fase: 1, estado: 'hecho', fichero: './agenda.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo' },
    resumen: 'Tu calendario: citas con clientes y prospectos (Zoho CRM con Bookings, GHL de RO, Zoom), hoy y semana, huecos libres y clientes en rojo con reunión hoy.' },
  { id: 'chat-equipo', num: 'M24', titulo: 'Chat del equipo', grupo: 'Hoy', fase: 1, estado: 'hecho', fichero: './chat_equipo.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo' },
    resumen: 'Canales internos y directos de ClickUp aquí dentro: hilos, búsqueda, menciones y no leídos; escribir en simulación hasta W1 (cada uno con su cuenta de ClickUp).' },
  // N3 (2-oct noche): IA. Servidor ia.py (/api/ia/*), componentes en ia_componentes.js (Bandeja, ficha y Mi día los enganchan).
  { id: 'asistente-ia', num: 'N3', titulo: 'Asistente IA', grupo: 'Hoy', fase: 1, estado: 'hecho', fichero: './asistente_ia.js',
    puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo', proyectos: 'todo', jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo', account: 'suyo' },
    resumen: 'Qué haría hoy con cada cliente (diagnóstico y 3 acciones con su prueba) y borradores de respuesta a los correos de Desk en la voz de RO. Lo revisa una persona; no se envía nada.' },
  // N4 (2-oct noche): motor único de alertas por departamento. No recalcula: reúne lo que ya calculan los módulos.
  // Datos: data/alertas/p_<persona>.json (solo_propio) y alertas.json (dirección y operaciones) ← fuentes_alertas/generar_alertas.py.
  { id: 'alertas', num: 'N4', titulo: 'Alertas del departamento', grupo: 'Hoy', fase: 1, estado: 'hecho', fichero: './alertas.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', proyectos: 'todo', rrhh: 'todo', administracion: 'todo', tecnico_altas: 'todo', jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo', setters: null },
    resumen: 'Cada alerta con su departamento, dueño, motivo, plazo, gravedad y escalado (dueño → jefe → Mili): web, SEO, CRM, publicidad, redes, accounts, altas, administración, RRHH y dirección. Lo tengo, resuelta (se comprueba con el dato siguiente) y no aplica, con rastro.' },

  // Producto (3-oct, encargo de Tomás): pantalla de inicio de Coti (directora de producto, puesto proyectos). Talleres de la
  // oferta, semáforo ESTRATÉGICO (resultados frente al objetivo del cliente) y avance. Datos: data/verdad/objetivos_clientes.json
  // (fuentes_verdad/generar_objetivos_clientes.py). Lo operativo (plazos, correos, reuniones) sigue en «En rojo» / Operaciones.
  { id: 'producto', num: 'P1', titulo: 'Dirección de producto', grupo: 'Clientes', fase: 1, estado: 'hecho', fichero: './producto.js',
    puestos_que_lo_ven: { direccion: 'todo', proyectos: 'todo', operaciones: 'resumen' },
    resumen: 'Talleres de la oferta de cada cliente nuevo, semáforo estratégico de todos los clientes por resultados frente a su objetivo, avance hacia el objetivo, renovaciones y la recomendación del cerebro para cada crítico.' },

  // M4 (2-oct): la ficha v3 de «Panel de operaciones para Mili» como módulo. Ruta #/ficha/<cliente>/<pestaña>.
  // Datos: data/clientes/<id>.json (E1, /api/cliente) + data/ficha/ (fuentes_ficha/generar_ficha.py; contactos y chat en _privado/).
  { id: 'ficha', num: 'M4', titulo: 'Ficha del cliente', grupo: 'Clientes', fase: 1, estado: 'hecho', fichero: './ficha.js',
    puestos_que_lo_ven: { ...DIR, tecnico_altas: 'todo', jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo', account: 'suyo', trafficker: 'suyo', especialista_ghl: 'suyo', seo: 'suyo', ficha_google: 'suyo', web: 'suyo', redes: 'resumen', produccion: 'resumen', administracion: 'resumen' },
    resumen: '10 pestañas: Resumen · Contactos · Resultados · Web y SEO · Redes · Comunicación · Chat · Trabajo · Accesos y contrato · Rastro.' },
  // M5 (2-oct): informe del cliente que sustituye a Looker + comparador de paridad. Ruta #/informe-cliente/<cliente>/<periodo>
  // y #/informe-cliente/paridad. Datos: data/informe/ (fuentes_informe/generar_informe.py). Análisis del mes: cola de acciones.
  { id: 'informe-cliente', num: 'M5', titulo: 'Informe del cliente', grupo: 'Clientes', fase: 3, estado: 'hecho', fichero: './informe.js',
    puestos_que_lo_ven: { ...DIR, jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo', account: 'suyo', trafficker: 'suyo', seo: 'suyo', ficha_google: 'suyo', outreach: 'suyo' },
    resumen: 'Sustituye a Looker cliente a cliente: 13 bloques con selector de fechas, comparación, avisos de fuente rota y paridad comprobada.' },
  // N1 (2-oct noche): las vistas estándar de cada herramienta por cliente con periodo común y comparación.
  // Datos: data/paneles/ (fuentes_paneles/generar_paneles.py). Ruta #/paneles/<cliente>/<herramienta>/<vista>, #/paneles/empresa/<desk|zadarma>, #/paneles/mapa.
  { id: 'paneles', num: 'N1', titulo: 'Paneles de herramientas', grupo: 'Clientes', fase: 3, estado: 'hecho', fichero: './paneles.js',
    puestos_que_lo_ven: { ...DIR, jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo', tecnico_altas: 'todo', account: 'suyo', trafficker: 'suyo', especialista_ghl: 'suyo', seo: 'suyo', ficha_google: 'suyo', web: 'suyo', redes: 'suyo' },
    resumen: 'Meta Ads, GoHighLevel, Analytics, Search Console y Metricool como en cada herramienta (campañas, embudo, informes estándar, indexación, experiencia, analítica por red), con periodo y comparación; Zoho Desk y Zadarma para dirección; y dónde está cada panel.' },
  { id: 'clientes-nuevos', num: 'M12', titulo: 'Clientes nuevos', grupo: 'Clientes', fase: 1, estado: 'hecho', fichero: './nuevos.js',
    puestos_que_lo_ven: { ...DIR, tecnico_altas: 'todo', jefa_publicidad: 'todo', jefa_crm: 'todo', jefa_seo: 'resumen', account: 'suyo', trafficker: 'suyo', especialista_ghl: 'suyo', administracion: 'resumen' },
    resumen: 'Hoja de ruta de la firma al día 90 (encendido el día 10, límite 12).' },
  // E3 (2-oct): M13. Datos en data/informes/ (fuentes_informes/generar_informes.py: ClickUp cu.py + Desk zh.py).
  { id: 'informes-mensuales', num: 'M13', titulo: 'Informes mensuales', grupo: 'Clientes', fase: 1, estado: 'hecho', fichero: './informes_mensuales.js',
    puestos_que_lo_ven: { ...DIR, account: 'suyo' },
    resumen: 'Hecho (ClickUp) / enviado (Desk) / pendiente por cliente y mes; verde el día 5, rojo el 6 con aviso a Mili (D-09); «enviado por otra vía»; histórico de la hoja en W5.' },
  // M14 (2-oct): ficha con ciclo detectada → avisada → reiterada → escalada → resuelta (comprobada con el dato del día
  // siguiente) y causa R13; detecciones de Desk y Zadarma; incongruencias, accesos, traspasos, quién vio primero, mapas.
  // Datos: data/incidencias/incidencias.json (fuentes_incidencias/generar_incidencias.py). Coti (proyectos) recibe escalados: todo.
  { id: 'incidencias', num: 'M14', titulo: 'Incidencias', grupo: 'Clientes', fase: 1, estado: 'hecho', fichero: './incidencias.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', proyectos: 'todo' },
    resumen: 'Cada fallo con su historia: detectada, avisada, reiterada, escalada (reloj de 48 h para Tomás) y resuelta con prueba; causa en dos campos. Desk, Zadarma, incongruencias ClickUp ↔ Desk ↔ CRM, accesos, traspasos y mapas de control.' },

  { id: 'captacion', num: 'M6', titulo: 'Captación', grupo: 'Captación y CRM', fase: 2, estado: 'hecho', fichero: './captacion.js',
    puestos_que_lo_ven: { ...DIR, jefa_publicidad: 'todo', tecnico_altas: 'resumen', jefa_crm: 'resumen', account: 'suyo', trafficker: 'suyo', especialista_ghl: 'resumen', produccion: 'resumen' },
    resumen: 'Publicidad + embudo GHL: coste por cita frente al objetivo del cliente.' },
  // M7 (2-oct): datos en data/crm/ (fuentes_crm/generar_crm.py: GHL de las 66 subcuentas + captacion.json).
  { id: 'salud-crm', num: 'M7', titulo: 'Salud del CRM', grupo: 'Captación y CRM', fase: 2, estado: 'hecho', fichero: './crm.js',
    puestos_que_lo_ven: { ...DIR, tecnico_altas: 'todo', jefa_crm: 'todo', jefa_publicidad: 'resumen', account: 'suyo', trafficker: 'resumen', especialista_ghl: 'suyo' },
    resumen: 'Leads sin tocar, velocidad, flujos con error, citas sin estado, asistencia.' },

  // E8 (2-oct): datos en data/seo/ (fuentes_seo/generar_seo.py) y data/redes/ (fuentes_redes/generar_redes.py).
  { id: 'seo-web', num: 'M8', titulo: 'SEO, ficha y webs', grupo: 'SEO, web y redes', fase: 4, estado: 'hecho', fichero: './seo.js',
    puestos_que_lo_ven: { ...DIR, jefa_seo: 'todo', tecnico_altas: 'resumen', jefa_publicidad: 'resumen', account: 'suyo', trafficker: 'suyo', seo: 'suyo', ficha_google: 'suyo', web: 'suyo' },
    resumen: 'Posiciones, clics, ficha de Google y monitor de webs desde fuera y desde RO.' },
  { id: 'redes', num: 'M9', titulo: 'Redes', grupo: 'SEO, web y redes', fase: 4, estado: 'hecho', fichero: './redes.js',
    puestos_que_lo_ven: { ...DIR, jefa_seo: 'resumen', account: 'suyo', redes: 'suyo', produccion: 'resumen' },
    resumen: 'Próximos 14 días cubiertos, huecos y aprobaciones (Metricool).' },

  // E7 (2-oct): M10 y M11. Datos en data/produccion/ y data/horas/ (fuentes_produccion/ y fuentes_horas/, ClickUp con la llave propia).
  { id: 'produccion', num: 'M10', titulo: 'Producción', grupo: 'Equipo', fase: 1, estado: 'hecho', fichero: './produccion.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', proyectos: 'todo', rrhh: 'resumen', setters: null, administracion: null },
    resumen: 'Tareas de tu equipo, revisiones pendientes y plazos por cliente.' },
  { id: 'horas', num: 'M11', titulo: 'Horas y productividad', grupo: 'Equipo', fase: 1, estado: 'hecho', fichero: './horas.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', rrhh: 'todo', jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo' },
    resumen: 'Cada uno ve lo suyo; la comparación, solo jefes, Mili, Cecilia y Tomás. Las horas, solo como aviso (D-27).' },
  // E11 (2-oct): M15. Datos en data/reuniones/ (fuentes_reuniones/generar_reuniones.py: Zoom zm.py + capa E1).
  { id: 'reuniones', num: 'M15', titulo: 'Reuniones', grupo: 'Equipo', fase: 5, estado: 'hecho', fichero: './reuniones.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', administracion: null },
    resumen: 'Zoom de RO (solo grabadas hasta W4): internas frente a clientes, tipo por el nombre (D-06) o desplegable, horas y % de capacidad por persona y mes, reunión del ciclo con cada cliente y actas.' },
  // M20 (2-oct): datos en data/personas/ (fuentes_personas/generar_personas.py). Cada uno ve lo suyo; jefas, su equipo;
  // Cecilia, Mili y Tomás, todos (recorte por persona_id en servir.py). Contratación solo con Ajustes (Mili, Tomás, Cecilia).
  { id: 'personas', num: 'M20', titulo: 'Personas', grupo: 'Equipo', fase: 5, estado: 'hecho', fichero: './personas.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', rrhh: 'todo' },
    resumen: 'Personas en alerta con su plan, carga frente a 128 h, quién no imputa, ausencias, 1:1, nota 1-10 y contratación. Sin sueldos.' },

  // E6 (2-oct): setters, ventas de RO y outreach. Datos en data/ventas_ro/ (fuentes_ventas/generar_ventas_ro.py).
  { id: 'setters', num: 'M16a', titulo: 'Mi día del setter', grupo: 'Ventas de RO', fase: 5, estado: 'hecho', fichero: './setters.js',
    puestos_que_lo_ven: { setters: 'suyo', direccion: 'todo', ventas_ro: 'todo', jefa_crm: 'resumen', operaciones: 'resumen' },
    resumen: 'Llamar ya, segundas, citas por confirmar, citas sin resultado, marcador e informe de fin de día. Móvil primero.' },
  { id: 'ventas-ro', num: 'M16', titulo: 'Ventas de RO', grupo: 'Ventas de RO', fase: 5, estado: 'hecho', fichero: './ventas_ro.js',
    puestos_que_lo_ven: { direccion: 'todo', ventas_ro: 'todo', operaciones: 'resumen', proyectos: 'resumen', jefa_crm: 'resumen', outreach: 'resumen' },
    resumen: 'Reuniones de hoy, propuestas, contratos, embudo con ritmo, coste por cita y por cliente, huecos de 45 min.' },
  { id: 'prospeccion', num: 'M17', titulo: 'Prospección y outreach', grupo: 'Ventas de RO', fase: 5, estado: 'hecho', fichero: './outreach.js',
    puestos_que_lo_ven: { direccion: 'todo', jefa_crm: 'todo', outreach: 'suyo', operaciones: 'resumen' },
    resumen: 'Respuestas sin dueño, campañas, resultados por cliente y hoja semanal declarada. Clientes y RO por separado.' },

  // E10 (2-oct): M18 y M19. Datos en data/dinero_cliente/ y data/finanzas/ (fuentes_dinero/generar_dinero.py: Holded y Airtable en lectura).
  { id: 'dinero-cliente', num: 'M18', titulo: 'Dinero por cliente', grupo: 'Dinero', fase: 5, estado: 'hecho', fichero: './dinero_cliente.js',
    puestos_que_lo_ven: { direccion: 'todo', finanzas_direccion: 'todo', operaciones: 'todo', proyectos: 'todo', administracion: 'todo', account: 'suyo', jefa_publicidad: 'resumen', trafficker: 'resumen' },
    resumen: 'Cuota, horas frente a cuota (31,47 €/h) y rentabilidad.' },
  { id: 'finanzas', num: 'M19', titulo: 'Finanzas de la empresa', grupo: 'Dinero', fase: 5, estado: 'hecho', fichero: './finanzas.js',
    puestos_que_lo_ven: { direccion: 'todo', finanzas_direccion: 'todo', administracion: 'todo' },
    resumen: 'Solo Tomás; Sofía, cobros, impagos y saldos por banco.' },
  // C2 (2-oct): el panel de resultados v29/v30 entero, SOLO Tomás. Datos en data/panel_direccion/ (fuentes_panel_direccion/generar_panel_direccion.py).
  { id: 'panel-direccion', num: 'C2', titulo: 'Panel de dirección', grupo: 'Dinero', fase: 5, estado: 'hecho', fichero: './panel_direccion.js',
    puestos_que_lo_ven: { direccion: 'todo' },
    resumen: 'El panel de resultados v29/v30 dentro de la app: la empresa (informe financiero) y la captación de RO en sus pestañas, con nombres. Solo Tomás.' },

  // M21 (2-oct): decisiones.js envuelve el rastro de E0 (rastro.js, sin cambios) en su pestaña «Rastro».
  // Datos en data/decisiones/ (fuentes_decisiones/generar_decisiones.py): reloj (tabla decisiones de local.db), 101 firmadas, informe y cierre.
  { id: 'decisiones', num: 'M21', titulo: 'Decisiones y rastro', grupo: 'Sistema', fase: 0, estado: 'hecho', fichero: './decisiones.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo' },
    resumen: 'Decisiones con reloj de 48 h, las 101 firmadas, informe semanal para Tomás, cierre de mes y rastro imborrable.' },
  { id: 'ajustes', num: 'M22', titulo: 'Ajustes', grupo: 'Sistema', fase: 0, estado: 'hecho', fichero: './ajustes.js',
    puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo', rrhh: 'resumen' },
    resumen: 'Personas, asignaciones, suplencias y «ver como».' },
  { id: 'indicadores', num: '—', titulo: 'Catálogo de indicadores', grupo: 'Sistema', fase: 0, estado: 'hecho', fichero: './indicadores.js',
    puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo' },
    resumen: 'Los 228 indicadores de las fichas (y 23 de fase 2) con umbral, origen y estado de medición (E0).' },
  { id: 'componentes', num: '—', titulo: 'Componentes', grupo: 'Sistema', fase: 0, estado: 'hecho', fichero: './catalogo.js',
    puestos_que_lo_ven: { direccion: 'todo' }, soloPrototipo: true,
    resumen: 'Catálogo vivo del sistema de diseño para quien construye módulos.' },
  // A10 (R15a, 2-oct): «Tu primera semana» para altas de los últimos 14 días. Grupo fuera del menú (se llega desde Mi día, Ajustes y ⌘K).
  // Datos: data/primera_semana/guias.json (fuentes_equipo/generar_primera_semana.py). La propia persona, su jefe, Mili y Tomás.
  { id: 'primera-semana', num: 'A10', titulo: 'Tu primera semana', grupo: 'Bienvenida', fase: 1, estado: 'hecho', fichero: './primera_semana.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', proyectos: 'todo', rrhh: 'todo', jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo' },
    resumen: 'Los 5 pasos del puesto (guía, 3 pantallas, número que manda, búsqueda y «Algo va mal»), su jefe y sus clientes, con lista que se marca.' },
  // Mi perfil (3-oct, encargo de Tomás «que el equipo pueda actualizar su timezone»). Grupo fuera del menú: se llega desde el
  // menú del avatar (carcasa.js) y con ⌘K. Cada uno el suyo; su jefe, Mili y Tomás cambian la zona de otros (reglas → zona_horaria).
  { id: 'mi-perfil', num: 'P1', titulo: 'Mi perfil', grupo: 'Perfil', fase: 0, estado: 'hecho', fichero: './mi_perfil.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', rrhh: 'todo' },
    resumen: 'Tu nombre, puesto, jefe y zona horaria; cámbiala tú y sale en tu hora (reloj, resumen diario y día de tus horas).' },
  // N11 (2-oct noche) → «Salud del sistema» (3-oct): el vigía (despliegue/vigia.py) cada 10 min; Agus (técnico) la ve sin entrar en Ajustes.
  { id: 'conexiones', num: 'N11', titulo: 'Salud del sistema', grupo: 'Sistema', fase: 0, estado: 'hecho', fichero: './ajustes_conexiones.js',
    puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo', tecnico_altas: 'todo' },
    resumen: 'Si todo funciona: cada herramienta (Google, GoHighLevel, ClickUp…) y la app por dentro, en verde, ámbar o rojo, desde cuándo, qué hacer y quién.' },
  // Envíos verificados (3-oct, encargo de Tomás «que el sistema nunca esté fallando»): cola de envíos con su estado, simulados hasta que Tomás los active (envios.py).
  { id: 'envios', num: 'EV1', titulo: 'Envíos', grupo: 'Sistema', fase: 0, estado: 'hecho', fichero: './envios.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', tecnico_altas: 'todo' },
    resumen: 'Cada correo, WhatsApp o mensaje de GHL que sale de la app: si salió, si llegó, si rebotó y quién lo pidió. Hoy en simulación.' },
  // Avisos automáticos (3-oct, encargo de Tomás «que en el chat de la app estén todas [las automatizaciones]»): recordatorios
  // programados en los canales de la app (horas, semáforo del lunes, informe, cierre de facturación, resúmenes). Cada jefa
  // cambia los de su departamento; Mili y Tomás, todos; el resto ve los que le llegan (avisos_programados.py).
  { id: 'avisos-automaticos', num: 'AV2', titulo: 'Avisos automáticos', grupo: 'Sistema', fase: 0, estado: 'hecho', fichero: './ajustes_avisos.js',
    puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo' },
    resumen: 'Lo que la app recuerda sola en el chat (imputar horas, semáforo del lunes, informes, cierre de facturación…): a quién, cuándo y solo si hace falta.' },
  // Gasto de IA (3-oct, encargo de Tomás «no quiero una IA con tokens infinitos»): topes en euros, coste real por llamada, modo reglas (ia_gasto.py). Solo Tomás.
  { id: 'gasto-ia', num: 'IA2', titulo: 'Gasto de IA', grupo: 'Sistema', fase: 0, estado: 'hecho', fichero: './gasto_ia.js',
    puestos_que_lo_ven: { direccion: 'todo' },
    resumen: 'Lo que gasta la IA: mes, día, previsión, por función y por persona, con topes que solo cambia Tomás. Al 100 %, modo reglas sin coste.' },
];
