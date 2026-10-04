import { horasDiaTrabajo370, textoHorasTrabajo370 } from './_horas_mi_trabajo_370.js';
// modulos/mi_trabajo.js · «Mi trabajo» (3-oct-2026). Encargo de Tomás: que el equipo deje de usar ClickUp en el día a día.
//
// Lo que hay:
//   · Tus tareas de ClickUp en Hoy / Semana / Mes, agrupadas por lo que va primero (vencidas, para hoy, bloqueadas, esta
//     semana, este mes) con cliente, estado, plazo y quién la pidió; lo que espera revisión de otro y lo olvidado, aparte.
//     Filtros rápidos por cliente, estado, prioridad y etiqueta real de ClickUp. Jefes: «Mi equipo» con las de su gente (y filtro por persona).
//   · Actuar sin salir: marcar hecha («Hecho · Deshacer»), cambiar estado (solo a estados de SU lista), cambiar fecha,
//     comentar. Imputar horas: cronómetro (empezar/parar, lo guarda el servidor) y «Añadir tiempo» (15 min, 30 min, 1 h o a
//     mano), de hoy o de días anteriores.
//   · Tu día: horas imputadas hoy (ClickUp + app, sin duplicar) frente a tu jornada; avisos amables SOLO de lo tuyo
//     («ayer no imputaste horas: añádelas aquí»). Resumen de horas raras del equipo solo para quien puede verlo.
//
// Datos: ctx.datosModulo('mi_trabajo/mi_trabajo') (recortado por persona en el servidor) + ctx.api('mi_trabajo') (lo que
// ya hizo la app, horas por día, raras, cronómetro). Acciones: ctx.accion({ herramienta: 'clickup', tipo, objeto, … }) →
// copia segura de sincronia.py. NADA se escribe en ClickUp mientras Tomás no active la sincronía.
//
// Diseño: piezas comunes (pantallaTrabajo, filasFlexibles, botonDeshacer/conDeshacer, menuElegir, pestanas, chipsFiltro,
// barraProgreso, vacioLinea, tablaApilable). Sin hoja de estilos propia; tokens en línea. Claro; 390 px sin desplazamiento.

import { h, fmt, icono, poner, pestanas, chipsFiltro, menuElegir, barraProgreso, vacioLinea, logoCliente, avisoFlotante,
  tablaApilable, sumarDias, fechaCorta } from '../componentes.js';
import { pantallaTrabajo, filasFlexibles } from './_trabajo.js';
import { botonDeshacer, conDeshacer } from './_deshacer.js';
import { bloqueTareaIA } from './tarea_ia.js';
import { destinosFinales203 } from './_finalizar_tarea_203.js';
import { contextoMovimientoDetalle200 } from './_movimiento_detalle_200.js';
import { prepararDetalleTarea197 } from './_detalle_tarea_197.js';
import { renderMetadatosTarea225 } from './_metadatos_tarea_225.js';
import { panelComentario366 } from './_comentario_durable_366.js';
import { prepararTableroTrabajo181 } from './_tablero_mi_trabajo_181.js';
import { permisoMovimiento192, crearIntentoMovimiento192, guardarMovimiento192, identidadMovimiento192 } from './_movimiento_tablero_192.js';

const COLOR = { verde: 'var(--good)', ambar: 'var(--warn)', rojo: 'var(--bad)', gris: 'var(--off)', azul: 'var(--accent)' };
const punto = e => h('span', { 'aria-hidden': 'true', style: { width: '8px', height: '8px', borderRadius: 'var(--r-full)', background: COLOR[e] || COLOR.gris, flex: 'none', display: 'inline-block' } });
const leer = k => { try { return sessionStorage.getItem(k); } catch { return null; } };
const guardar = (k, v) => { try { sessionStorage.setItem(k, v); } catch { /* sin almacenamiento */ } };
const esMovil = () => { try { return matchMedia('(max-width: 900px)').matches; } catch { return false; } };
const DIAS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const diaTxt = (t, hoy) => { if (!t) return '—'; if (t === hoy) return 'hoy'; if (t === sumarDias(hoy, -1)) return 'ayer'; if (t === sumarDias(hoy, 1)) return 'mañana'; const d = new Date(`${t}T12:00:00`); return `${DIAS[d.getDay()]} ${fechaCorta(t)}`; };
const horasTxt = hh => { if ((hh || 0) >= 10) return `${fmt.num(hh, 1)} h`; const m = Math.round((hh || 0) * 60); if (!m) return '0 h'; const H = Math.floor(m / 60), M = m % 60; return H && M ? `${H} h ${M} min` : H ? `${H} h` : `${M} min`; };
const ESTADO_TXT = { planing: 'Planificación', planning: 'Planificación', 'revisión project manager': 'Revisión del account', 'revisión técnica': 'Revisión técnica', 'revisión mili': 'Revisión de Mili', 'revisión tomás': 'Revisión de Tomás',
  'revisión cliente': 'Revisión del cliente', 'enviar  cliente': 'Enviar al cliente', 'planning semanal': 'Plan de la semana', 'planning mensual': 'Plan del mes', 'próximo sprint': 'Próxima tanda', backlog: 'Pendiente sin fecha' };
const estadoTxt = e => ESTADO_TXT[e] || (e ? e[0].toUpperCase() + e.slice(1) : '—');
// Piloto local: no abrir la lectura de contexto que consulta ClickUp remoto.
function consultaLocalTrabajo(ctx) {
  return ctx.pilotoLectura === true || (!!ctx.servidor && !!ctx.soloLectura && !!ctx.real?.id && ctx.real.id === ctx.persona?.id);
}
function avisoLecturaTrabajo(ctx) {
  if (ctx.pilotoLectura === true) return 'Piloto de consulta · solo lectura; no se guardan ni envían cambios';
  if (consultaLocalTrabajo(ctx)) return 'Consulta de solo lectura · no se guardan ni envían cambios';
  if (ctx.soloLectura && ctx.real?.id && ctx.persona?.id && ctx.real.id !== ctx.persona.id) return 'Estás en «ver como»: solo lectura';
  return ctx.soloLectura ? 'Solo lectura' : '';
}
function contextoTareaTrabajo(E, t) {
  if (consultaLocalTrabajo(E.ctx)) return vacioLinea('El contexto para IA no está disponible en este modo de consulta local: requiere una lectura actual de ClickUp. Puedes abrir la tarea original para consultar el brief.', { icono: 'info' });
  return bloqueTareaIA(E, t);
}
const TIPOS_ESTADO = new Set(['open', 'custom', 'unstarted', 'done', 'closed']);
const ESTADOS_PENDIENTES = new Set(['simulado', 'pendiente', 'enviado']);
const GRUPO = {
  vencida: { t: 'Vencidas', e: 'rojo', i: 'alert', orden: 0 }, hoy: { t: 'Para hoy', e: 'ambar', i: 'hoy', orden: 1 },
  bloqueada: { t: 'Bloqueadas', e: 'ambar', i: 'candado', orden: 2 }, semana: { t: 'Esta semana', e: 'azul', i: 'cal', orden: 3 },
  mes: { t: 'Este mes', e: 'gris', i: 'cal', orden: 4 }, revision: { t: 'Esperando revisión de otra persona', e: 'gris', i: 'ojo', orden: 5, plegado: true },
  sin_planificar: { t: 'Sin fecha o planificación disponible', e: 'gris', i: 'cal', orden: 6, plegado: true },
  por_contrastar: { t: 'Estado por contrastar con ClickUp', e: 'ambar', i: 'info', orden: 7 },
  olvidada: { t: 'Olvidadas (vencidas hace más de 30 días)', e: 'gris', i: 'hist', orden: 6, plegado: true },
};
const RARA = {
  sin_registros_copia: { t: 'Sin registros en la copia', i: 'clock' }, sin_horas: { t: 'Sin registros en la copia · referencia anterior', i: 'clock' }, mas_10: { t: 'Más de 10 h en un día', i: 'alert' }, fin_semana: { t: 'Horas en fin de semana', i: 'cal' },
  doble_estimacion: { t: 'Más del doble de lo estimado', i: 'medidor' }, cliente_ajeno: { t: 'Cliente que no es suyo', i: 'cli' },
};

export default {
  id: 'mi-trabajo',
  titulo: 'Mi trabajo',
  grupo: 'Hoy',
  async render(cont, ctx) {
    ctx.titulo('Mi trabajo', 'Tus tareas y tus horas sin salir de la app');
    const raiz = h('div', { class: 'pila', 'data-mi-trabajo-raiz': '', style: { gap: 'var(--s-3)' } });
    poner(cont, raiz);
    const vigente = () => raiz.isConnected && raiz.parentNode === cont && (typeof ctx.vigente !== 'function' || ctx.vigente());
    poner(raiz, vacioLinea('Cargando tus tareas…', { icono: 'clock' }));
    let D, V;
    try {
      [D, V] = await Promise.all([ctx.datosModulo('mi_trabajo/mi_trabajo'), ctx.servidor ? ctx.api('mi_trabajo') : Promise.resolve(null)]);
    } catch (e) {
      if (!vigente()) return;
      poner(raiz, vacioLinea(`No se pueden leer tus tareas: ${e.message}`, { icono: 'alert', quien: 'Agus' }));
      return;
    }
    if (!vigente()) return;
    V = V || { yo: ctx.persona.id, hoy: ctx.hoy, cambios: [], horas_app: [], dias: {}, raras: [], jornada: [], personas: [], estados_lista: D.estados_lista || {}, sincronia: { texto: 'Guardado en RO · envío a ClickUp sin confirmar' } };
    const E = { D, V, cont: raiz, ctx, vigente, abierta: leer('ro.mt.abierta'), local: [] };
    pintar(E);
  },
};

// ------------------------------------------------------------------ estado derivado
const yo = E => E.V.yo || E.ctx.persona.id;
const hoyZona = E => E.V.hoy || E.ctx.hoy;
const persona = (E, id) => (E.V.personas || []).find(p => p.id === id) || {};
const esJefeDe = (E, pid) => persona(E, pid).jefe === yo(E);
const puedeTocar = (E, t) => !!E.ctx.servidor && !E.ctx.soloLectura && (t.persona_id === yo(E) || esJefeDe(E, t.persona_id) || (E.ctx.persona.puestos || []).some(p => p === 'direccion' || p === 'operaciones'));
const clave = t => `${t.persona_id}:${t.id}`;

/** Lo que ya hizo la app sobre una tarea (último estado, fecha, hecha) — de la copia segura y de lo hecho en esta sesión. */
function capa(E, tid) {
  const c = [...(E.V.cambios || []), ...E.local].filter(x => x.tarea === tid);
  const ult = campo => {
    const x = c.filter(x => x.campo === campo && x.estado !== 'descartado').slice(-1)[0];
    return x && ['simulado', 'pendiente', 'enviado', 'confirmado'].includes(x.estado) ? x : null;
  };
  const est = ult('estado'), fe = ult('fecha');
  return { estado: est?.valor, fecha: fe?.valor, cambios: c, cambio_estado: est,
    intencion_cierre: !!(est && est.tipo === 'marcar_hecha' && ESTADOS_PENDIENTES.has(est.estado)) }; 
}

/** Final de flujo según lista y tipo ClickUp; no acredita resultado comercial ni aceptación. */
export function resolverEstadoTrabajo(E, t, estado = t.estado, local = false) {
  const duda = motivo => ({ estado: 'indeterminado', tipo: null, final_flujo: false, motivo });
  if (!t.lista_id || typeof estado !== 'string') return duda('Falta lista o estado exacto.');
  const v = E.V.estados_detalle, d = E.D.estados_detalle;
  const fila = cat => Array.isArray(cat?.[t.lista_id]) ? cat[t.lista_id].filter(r => r.estado === estado) : null;
  const rv = fila(v), rd = fila(d), filas = rv ?? rd;
  if (v != null && !rv) return duda('La lista no está en el catálogo autorizado actual.');
  if (!filas || filas.length !== 1 || !TIPOS_ESTADO.has(filas[0].tipo)) return duda('Falta un estado único con tipo conocido en el catálogo de esta lista.');
  const tipo = filas[0].tipo;
  if (rv && rd && (rd.length !== 1 || rd[0].tipo !== tipo)) return duda('Las copias del catálogo no coinciden.');
  if ((!local || estado === t.estado) && t.tipo_estado != null && t.tipo_estado !== tipo) return duda('La tarea y el catálogo no coinciden en el tipo de estado.');
  return { estado: 'verificado', tipo, final_flujo: tipo === 'done' || tipo === 'closed', motivo: null };
}

/** Grupo con el hoy real (misma regla que Producción y Mi día: vencida si la fecha pasó; > 30 días, olvidada). */
function grupoDe(E, t, vence) {
  const hoy = E.ctx.hoy;
  let g = t.grupo;
  if (vence && ['hoy', 'semana', 'despues', 'mes', 'vencida', 'olvidada'].includes(g)) {
    if (vence < hoy) g = (new Date(`${hoy}T12:00:00`) - new Date(`${vence}T12:00:00`)) / 864e5 > 30 ? 'olvidada' : 'vencida';
    else if (vence === hoy) g = 'hoy';
    else if (vence <= finSemana(hoy)) g = g === 'hoy' ? 'hoy' : 'semana';
    else if (vence <= finMes(hoy)) g = g === 'hoy' ? 'hoy' : g === 'semana' ? 'semana' : 'mes';
    else g = g === 'hoy' || g === 'semana' ? g : 'despues';
  }
  if (g === 'despues') g = vence && vence <= finMes(hoy) ? 'mes' : 'despues';
  return g;
}
const finSemana = hoy => { const d = new Date(`${hoy}T12:00:00`); return sumarDias(hoy, (7 - d.getDay()) % 7); };
const finMes = hoy => { const [a, m] = hoy.split('-').map(Number); return new Date(Date.UTC(a, m, 0)).toISOString().slice(0, 10); };
export function esFinDeSemanaTrabajo(fecha) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(fecha || ''))) return null;
  const dia = new Date(`${fecha}T12:00:00Z`).getUTCDay();
  return Number.isNaN(dia) ? null : dia === 0 || dia === 6;
}
const enCursoSinFecha = t => !t.vence && ['en curso', 'in progress'].includes(t.estado) && (t.grupoV || t.grupo) === 'hoy';
const tituloGrupo = (g, ts) => g === 'hoy' && ts.some(enCursoSinFecha) ? 'Para hoy y en curso' : GRUPO[g].t;
const VISTAS = { hoy: ['vencida', 'hoy', 'bloqueada'], semana: ['vencida', 'hoy', 'bloqueada', 'semana'], mes: ['vencida', 'hoy', 'bloqueada', 'semana', 'mes'] };

function tareas(E, modo) {
  const lista = (E.D.tareas || []).filter(t => (modo === 'equipo' ? t.persona_id !== yo(E) : t.persona_id === yo(E)));
  return lista.map(t => {
    const k = capa(E, t.id);
    const vence = k.fecha || t.vence;
    const estado = k.estado || t.estado;
    const resolucion = resolverEstadoTrabajo(E, t, estado, !!k.estado);
    const grupoBase = ({ vencidas: 'vencida', futuro: 'despues', sin_fecha: 'sin_planificar', backlog: 'sin_planificar' })[t.grupo] || t.grupo;
    let grupoV = grupoDe(E, { ...t, grupo: estadoGrupo({ ...t, grupo: grupoBase }, estado) }, vence);
    if (resolucion.estado === 'indeterminado' || (!resolucion.final_flujo && grupoV === 'completadas')) grupoV = 'por_contrastar';
    return { ...t, vence, estado, grupoV, resolucion_estado: resolucion, capa: k };
  }).filter(t => !t.capa.intencion_cierre && !t.resolucion_estado.final_flujo);
}
/** Si la app cambió el estado a una revisión o a bloqueado, la tarea cambia de grupo (como lo haría ClickUp). */
function estadoGrupo(t, estado) {
  if (estado === t.estado) return t.grupo;
  if (estado === 'bloqueado') return 'bloqueada';
  if (/^revisi|cliente|campaña en curso/.test(estado)) return 'revision';
  return ['revision', 'bloqueada'].includes(t.grupo) ? 'semana' : t.grupo;
}

// ------------------------------------------------------------------ pintar
const PRIORIDAD_TEXTO = { urgent: 'Urgente', high: 'Alta', normal: 'Normal', low: 'Baja' };
/** Sólo prioridad y etiquetas explícitas de la copia autorizada, sin deducirlas del título o plazo. */
export function filtrarTareasTrabajo(lista, filtros) {
  return lista.filter(t => (!filtros.cliente || (t.cli || `n:${t.cliente}`) === filtros.cliente)
    && (!filtros.estado || t.estado === filtros.estado)
    && (!filtros.persona || t.persona_id === filtros.persona)
    && (!filtros.prioridad || t.prioridad === filtros.prioridad)
    && (!filtros.etiqueta || (Array.isArray(t.etiquetas) && t.etiquetas.includes(filtros.etiqueta))));
}

/** Recuperación de cierres locales: sólo tareas base del alcance autorizado de esta vista. */
export function cierresPendientesTrabajo(E, modo) {
  if (!['mias', 'equipo'].includes(modo) || (modo === 'equipo' && !E.V.ve_equipo)) return [];
  const unicas = new Map();
  const autoresVisibles = new Set([yo(E), ...(E.V.personas || []).map(p => p.id)]);
  for (const t of E.D.tareas || []) {
    if (modo === 'equipo' ? t.persona_id === yo(E) : t.persona_id !== yo(E)) continue;
    const cambios = [...(E.V.cambios || []), ...E.local].filter(c => c.tarea === t.id && autoresVisibles.has(c.quien)
      && (c.cliente_id == null || (t.cli && c.cliente_id === t.cli)));
    const k = capa({ ...E, V: { ...E.V, cambios }, local: [] }, t.id);
    const ultimo = k.cambios.filter(c => c.campo === 'estado' && c.estado !== 'descartado').slice(-1)[0];
    const res = resolverEstadoTrabajo(E, t, k.estado || t.estado, !!k.estado);
    if (!(k.intencion_cierre || res.final_flujo) || !ultimo || !ESTADOS_PENDIENTES.has(ultimo.estado)) continue;
    if (!unicas.has(t.id)) unicas.set(t.id, { id: t.id, tarea: t.tarea, estado_local: ultimo.estado });
  }
  return [...unicas.values()];
}

function panelCierresPendientes(E, modo) {
  const filas = cierresPendientesTrabajo(E, modo);
  if (!filas.length) return null;
  const textoEstado = { simulado: 'Simulado en RO · no enviado a ClickUp', pendiente: 'Pendiente de envío · sin confirmar en ClickUp', enviado: 'Enviado · aún sin confirmación de ClickUp' };
  return h('details', { class: 'panel', 'data-cierres-pendientes': '' },
    h('summary', { style: { padding: 'var(--s-3)', minHeight: '44px', cursor: 'pointer', fontWeight: '600', overflowWrap: 'anywhere' } },
      `Cambios pendientes de confirmar en ClickUp · ${fmt.num(filas.length)}`),
    h('div', { class: 'pila', style: { padding: '0 var(--s-3) var(--s-3)', gap: 'var(--s-2)' } },
      h('p', { class: 'sub', style: { margin: '0', whiteSpace: 'normal' } }, 'Estas tareas se han marcado como hechas en RO, pero su cierre no está confirmado en ClickUp. Se mantienen aquí para revisarlas; no se suman a las abiertas. Este apartado conserva el alcance de Mis tareas/Mi equipo y no depende de los filtros o del periodo de abiertos.'),
      h('ul', { class: 'lista-i' }, filas.map(t => h('li', { style: { flexWrap: 'wrap', gap: 'var(--s-2)' } },
        h('span', { class: 't', style: { minWidth: '0', flex: '1 1 200px', whiteSpace: 'normal', overflowWrap: 'anywhere' } },
          h('b', {}, t.tarea || 'Tarea'), h('span', { class: 'sub', style: { display: 'block', whiteSpace: 'normal' } }, textoEstado[t.estado_local])),
        h('a', { class: 'bt mini', href: `https://app.clickup.com/t/${encodeURIComponent(t.id)}`, target: '_blank', rel: 'noopener',
          style: { minHeight: '44px' }, 'aria-label': `Abrir en ClickUp: ${t.tarea || 'tarea'}` }, 'Abrir en ClickUp')))),
      E.ctx.veModulo?.('envios') ? h('a', { class: 'bt', href: '#/envios', style: { minHeight: '44px', alignSelf: 'flex-start' } }, 'Revisar en Envíos') : null));
}

/** Tablero: conservar estado de la copia, incluso ante una intención local de cierre. */
function tareasTableroTrabajo181(E, modo) {
  const filas = (E.D.tareas || []).map(t => ({ ...t, capa: capa(E,t.id),
    grupoV: grupoDe(E, { ...t, grupo: ({vencidas:'vencida',futuro:'despues',sin_fecha:'sin_planificar',backlog:'sin_planificar'})[t.grupo] || t.grupo }, t.vence) }));
  const resultado = prepararTableroTrabajo181(filas, E.tableroLista, t => resolverEstadoTrabajo(E,t));
  const visible = t => modo === 'equipo' ? t.persona_id !== yo(E) : t.persona_id === yo(E);
  const ids = new Set(filas.filter(visible).map(t=>t.id));
  resultado.tareas = resultado.tareas.filter(t=>ids.has(t.id)).map(t=>({...t,persona_id:filas.find(r=>r.id===t.id && r.lista_id===E.tableroLista && visible(r))?.persona_id || t.persona_id,grupoV:t.resolucion_estado.estado==='indeterminado' || (t.grupoV==='completadas'&&!t.resolucion_estado.final_flujo) ? 'por_contrastar' : t.grupoV}));
  // Selector derivado sólo de filas dentro del alcance Mis tareas/Mi equipo.
  const listas = new Set(filas.filter(visible).map(t=>t.lista_id));
  resultado.listas = resultado.listas.filter(l=>listas.has(l.id));
  resultado.lista_disponible = resultado.lista_disponible && listas.has(E.tableroLista);
  if (!resultado.lista_disponible) resultado.tareas=[];
  return resultado;
}

function vistaTableroTrabajo181(E, tablero, lista, repintar) {
  if (!tablero.lista_disponible) return vacioLinea(E.tableroLista ? 'La lista seleccionada no está disponible en este alcance. Elige otra lista; no se amplía la selección automáticamente.' : 'Elige una lista de ClickUp para ver sus columnas exactas.', {icono:'info'});
  const cat=E.V.estados_detalle ?? E.D.estados_detalle;
  const catalogo=Array.isArray(cat?.[E.tableroLista]) ? cat[E.tableroLista] : [];
  const nombres=[...new Set(catalogo.map(c=>c.estado))].filter(e=>typeof e==='string' && resolverEstadoTrabajo(E,{lista_id:E.tableroLista,estado:e},e).estado==='verificado');
  const columnas=[...nombres.map(estado=>({estado,titulo:estado})),{estado:null,titulo:'Por contrastar'}];
  E.movimientos192 ||= new Map();
  const resolver=(t,e=t.estado,local=false)=>resolverEstadoTrabajo(E,t,e,local);
  const abrirMover=(t,destino='')=>{
    if(E.vigente&&!E.vigente())return;
    const permiso=permisoMovimiento192(E,t,resolver);
    if(!permiso.ok)return;
    const previo=E.movimientos192.get(t.id);
    if(previo){previo.abierto=true;repintar();return;}
    E.movimientos192.set(t.id,{abierto:true,destino:permiso.destinos.includes(destino)?destino:'',intento:null});repintar();
  };
  const panelMover=t=>{
    const permiso=permisoMovimiento192(E,t,resolver),estado=E.movimientos192.get(t.id);
    const vivo=()=>!E.vigente || E.vigente();
    const mensaje=estado?.intento?.mensaje || permiso.motivo;
    const guardar=async()=>{
      if(!vivo()||!permisoMovimiento192(E,t,resolver).ok)return;
      if(!estado.intento){try{estado.intento=crearIntentoMovimiento192(E,t,estado.destino,resolver,crypto.randomUUID());}catch(e){estado.error=e.message;repintar();return;}}
      const p=guardarMovimiento192(E,t,estado.intento,resolver,a=>E.ctx.accion(a));repintar();
      try{await p;}catch(e){if(vivo())estado.error=e.message;}
      if(vivo())repintar();
    };
    return h('div',{class:'pila',style:{gap:'6px'}},
      h('button',{type:'button',class:'bt mini',disabled:!permiso.ok || null,'aria-label':`Mover tarea: ${t.tarea || 'tarea'}`,style:{minHeight:'44px'},on:{click:()=>abrirMover(t)}},'Mover'),
      estado?.error || estado?.intento || !permiso.ok ? h('p',{class:'sub',role:'status',style:{margin:'0',whiteSpace:'normal'}},estado?.error || mensaje) : null,
      estado?.abierto && permiso.ok ? h('div',{class:'pila',style:{gap:'8px'}},
        
        !estado.intento ? menuElegir({etiqueta:'Estado exacto',todos:'Elige destino',valor:estado.destino,opciones:permiso.destinos.map(e=>({valor:e,texto:e})),alCambiar:e=>{if(vivo()&&!estado.intento){estado.destino=e;repintar();}}}) : h('span',{class:'sub'},`${estado.intento.payload.vista_previa.expected_estado} → ${estado.intento.payload.vista_previa.a}`),
        h('button',{type:'button',class:'bt',disabled:(!estado.destino && !estado.intento)||estado.intento?.estado==='guardando'||!!estado.intento?.recibo||null,style:{minHeight:'44px'},on:{click:guardar}},estado.intento?.estado==='sin_confirmar'?'Reintentar la misma intención':'Guardar cambio en RO'),
        h('button',{type:'button',class:'bt mini',disabled:estado.intento?.estado==='guardando'||null,style:{minHeight:'44px'},on:{click:()=>{if(!vivo())return;if(!estado.intento)E.movimientos192.delete(t.id);else estado.abierto=false;repintar();}}},'Cerrar')) : null);
  };
  const arrastrar=(ev,t)=>{
    if((E.vigente&&!E.vigente()) || !permisoMovimiento192(E,t,resolver).ok || E.movimientos192.get(t.id)?.intento){ev.preventDefault();return;}
    const token=crypto.randomUUID();E.arrastre192={token,tarea:t.id,lista:E.tableroLista,identidad:identidadMovimiento192(E.ctx)};
    ev.dataTransfer?.setData('application/x-ro-tablero',token);if(ev.dataTransfer)ev.dataTransfer.effectAllowed='move';
  };
  const soltar=(ev,destino)=>{
    const arrastre=E.arrastre192;E.arrastre192=null;
    if(!arrastre || (E.vigente&&!E.vigente()) || arrastre.lista!==E.tableroLista || arrastre.identidad!==identidadMovimiento192(E.ctx) || ev.dataTransfer?.getData('application/x-ro-tablero')!==arrastre.token)return;
    const t=lista.find(t=>t.id===arrastre.tarea);if(!t || !permisoMovimiento192(E,t,resolver).destinos.includes(destino))return;
    ev.preventDefault();abrirMover(t,destino); // Sólo prepara el mismo selector; no hace POST.
  };
  const abrir=t=>{if(E.vigente&&!E.vigente())return;E.abierta=E.abierta===clave(t)?null:clave(t);guardar('ro.mt.abierta',E.abierta||'');repintar();if(E.abierta)queueMicrotask(()=>{if(E.vigente&&!E.vigente())return;const panel=E.cont?.querySelector('[data-detalle-tablero-200]');panel?.focus();panel?.scrollIntoView?.({block:'nearest'});});};
  const cerrarDetalle=()=>{if(E.vigente&&!E.vigente())return;const abierta=E.abierta;E.abierta=null;guardar('ro.mt.abierta','');repintar();const t=lista.find(t=>clave(t)===abierta);for(const n of E.cont?.querySelectorAll('[data-tablero-tarea]') || [])if(n.dataset?.tableroTarea===t?.id){n.querySelector('button')?.focus();break;}};
  const tarjeta=t=>h('article',{'data-tablero-tarea':t.id,draggable:permisoMovimiento192(E,t,resolver).ok && !E.movimientos192.get(t.id)?.intento ? 'true' : 'false',on:{dragstart:ev=>arrastrar(ev,t),dragend:()=>{E.arrastre192=null;}},style:{border:'1px solid var(--line)',borderRadius:'var(--r-m)',background:'var(--card)',padding:'12px',display:'grid',gap:'6px',minWidth:'0'}},
    h('button',{type:'button',class:'bt',disabled:!t.coherente || null,'data-uso':'abrir-tarea','aria-label':`Abrir tarea: ${t.tarea || 'tarea'}`,'aria-expanded':String(E.abierta===clave(t)),style:{minHeight:'44px',textAlign:'left',whiteSpace:'normal',overflowWrap:'anywhere'},on:{click:()=>abrir(t)}},t.tarea || 'Tarea por contrastar'),
    h('span',{class:'sub',style:{whiteSpace:'normal',overflowWrap:'anywhere'}},t.cliente || 'Sin cliente identificado'),
    h('span',{class:'sub'},t.vence ? `Fecha límite: ${t.vence}` : 'Sin fecha límite registrada'),
    h('span',{class:'sub',style:{whiteSpace:'normal'}},`Asignación en la copia: ${t.asignados.map(id=>E.ctx.nombre(id)).join(', ') || 'por contrastar'}`),
    PRIORIDAD_TEXTO[t.prioridad] || t.etiquetas?.length ? h('span',{class:'sub',style:{whiteSpace:'normal',overflowWrap:'anywhere'}},[PRIORIDAD_TEXTO[t.prioridad] ? `Prioridad: ${PRIORIDAD_TEXTO[t.prioridad]}` : null,Array.isArray(t.etiquetas)?t.etiquetas.join(', '):null].filter(Boolean).join(' · ')) : null,
    t.capa.cambios.some(c=>['fallido','conflicto'].includes(c.estado)) ? h('span',{class:'sub'},'Cambio con fallo o conflicto · comprueba Envíos › ClickUp.') : null,
    t.resolucion_estado.estado!=='verificado' ? h('span',{class:'sub'},'Estado o identidad por contrastar; no se acredita cierre.') : null,
    t.capa.cambios.some(c=>ESTADOS_PENDIENTES.has(c.estado)) ? h('span',{class:'sub',style:{whiteSpace:'normal'}},'Cambio en RO sin confirmar en ClickUp. La tarjeta conserva el estado de la copia.') : null,
    panelMover(t));
  return h('div',{class:'pila',style:{gap:'12px'}},
    h('p',{class:'sub',style:{margin:'0',whiteSpace:'normal'}},'Tablero de la copia disponible · mover requiere autorización y revisión vigente del servidor. El guardado en RO no confirma el envío a ClickUp. Abre una tarjeta para el detalle y las acciones existentes. Los finales observados no acreditan entrega aceptada; una copia parcial no es todo ClickUp.'),
    !lista.length ? vacioLinea('Sin tareas en esta lista, periodo y filtros. Se conserva tu selección.',{icono:'info'}) : null,
    h('div',{'data-tablero-181':'',style:{display:'flex',gap:'12px',overflowX:'auto',alignItems:'flex-start',maxWidth:'100%',paddingBottom:'12px'}},columnas.filter(c=>c.estado!==null || lista.some(t=>t.columna_tablero===null)).map(c=>{
      const ts=lista.filter(t=>t.columna_tablero===c.estado);
      return h('section',{'aria-label':`Estado exacto: ${c.titulo}`,on:{dragover:ev=>{if(c.estado!==null && E.arrastre192 && (!E.vigente||E.vigente()))ev.preventDefault();},drop:ev=>soltar(ev,c.estado)},style:{flex:'0 0 260px',maxWidth:'85vw',display:'grid',gap:'8px',minWidth:'0'}},h('h2',{style:{fontSize:'14px',margin:'0',padding:'8px 0',overflowWrap:'anywhere'}},`${c.titulo} · ${ts.length}`),ts.map(tarjeta));
    })),
    (()=>{const t=lista.find(t=>t.coherente&&E.abierta===clave(t));return t?h('section',{'aria-label':`Detalle de tarea: ${t.tarea || 'tarea'}`,'data-detalle-tablero-200':'',tabindex:'-1',on:{keydown:ev=>{if(ev.key==='Escape'){ev.preventDefault();cerrarDetalle();}}},style:{width:'100%',minWidth:'0',overflowWrap:'anywhere'}},h('h2',{style:{fontSize:'16px'}},t.tarea || 'Detalle de tarea'),h('button',{type:'button',class:'bt mini',style:{minHeight:'44px'},on:{click:cerrarDetalle}},'Cerrar detalle'),detalle(E,t,repintar)):null;})());
}

function pintar(E) {
  if (E.vigente && !E.vigente()) return;
  const { ctx } = E;
  const veEquipo = !!E.V.ve_equipo && (E.D.tareas || []).some(t => t.persona_id !== yo(E));
  let modo = veEquipo && leer('ro.mt.modo') === 'equipo' ? 'equipo' : 'mias';
  let vista = leer('ro.mt.vista') || 'hoy';
  let presentacion = leer('ro.mt.presentacion') === 'tablero' ? 'tablero' : 'lista';
  let inventario = leer('ro.mt.inventario') === 'si';
  E.tableroLista = E.tableroLista ?? leer('ro.mt.lista-tablero') ?? '';
  if (!VISTAS[vista]) vista = 'hoy';
  const filtros = E.filtros || (E.filtros = { cliente: '', estado: '', persona: '', prioridad: '', etiqueta: '' });
  const listaCaja = h('div', { class: 'pila', style: { gap: 'var(--s-3)' } });
  const pendientesCaja = h('div');
  const listaConPendientes = h('div', { class: 'pila', style: { gap: 'var(--s-3)' } }, pendientesCaja, listaCaja);
  const cabFiltros = h('div', { class: 'fila', style: { gap: 'var(--s-2)' } });

  const repintarLista = () => {
    if (E.vigente && !E.vigente()) return;
    const tablero = presentacion === 'tablero' ? tareasTableroTrabajo181(E,modo) : null;
    const todas = tablero ? tablero.tareas : tareas(E, modo);
    const deVista = tablero && inventario ? todas : todas.filter(t => [...VISTAS[vista], 'revision', 'olvidada', 'por_contrastar', 'sin_planificar'].includes(t.grupoV));
    const f = tablero ? filtrarTareasTrabajo(deVista.filter(t=>!filtros.persona || t.asignados.includes(filtros.persona)),{...filtros,persona:''}) : filtrarTareasTrabajo(deVista, filtros);
    // filtros rápidos con lo que hay en esta vista
    const clientes = [...new Map(deVista.map(t => [t.cli || `n:${t.cliente}`, t.cliente || 'Sin cliente'])).entries()].sort((a, b) => a[1].localeCompare(b[1], 'es'));
    const estados = [...new Set(deVista.map(t => t.estado))].sort();
    const prioridades = Object.keys(PRIORIDAD_TEXTO).filter(p => p === filtros.prioridad || deVista.some(t => t.prioridad === p));
    const etiquetas = [...new Set(deVista.flatMap(t => Array.isArray(t.etiquetas) ? t.etiquetas.filter(x => typeof x === 'string' && x) : []))].sort((a, b) => a.localeCompare(b, 'es'));
    if (filtros.etiqueta && !etiquetas.includes(filtros.etiqueta)) etiquetas.push(filtros.etiqueta);
    const gente = [...new Set(deVista.flatMap(t => tablero ? t.asignados : [t.persona_id]))].map(id => ({ valor: id, texto: ctx.nombre(id) })).sort((a, b) => a.texto.localeCompare(b.texto, 'es'));
    poner(cabFiltros,
      tablero ? menuElegir({etiqueta:'Lista ClickUp',todos:'Elige una lista',opciones:tablero.listas.map(l=>({valor:l.id,texto:l.nombre})),valor:E.tableroLista,alCambiar:id=>{if(E.vigente&&!E.vigente())return;E.tableroLista=id;guardar('ro.mt.lista-tablero',id);repintarLista();}}) : null,
      menuElegir({ etiqueta: 'Cliente', opciones: clientes.map(([v, t]) => ({ valor: v, texto: t })), valor: filtros.cliente, alCambiar: v => { filtros.cliente = v; repintarLista(); } }),
      menuElegir({ etiqueta: 'Estado', opciones: estados.map(e => ({ valor: e, texto: estadoTxt(e) })), valor: filtros.estado, alCambiar: v => { filtros.estado = v; repintarLista(); } }),
      prioridades.length || filtros.prioridad ? menuElegir({ etiqueta: 'Prioridad ClickUp', opciones: prioridades.map(p => ({ valor: p, texto: PRIORIDAD_TEXTO[p] })), valor: filtros.prioridad, alCambiar: v => { filtros.prioridad = v; repintarLista(); } }) : null,
      etiquetas.length || filtros.etiqueta ? menuElegir({ etiqueta: 'Etiqueta', opciones: etiquetas.map(e => ({ valor: e, texto: e })), valor: filtros.etiqueta, alCambiar: v => { filtros.etiqueta = v; repintarLista(); } }) : null,
      modo === 'equipo' ? menuElegir({ etiqueta: 'Persona', opciones: gente, valor: filtros.persona, alCambiar: v => { filtros.persona = v; repintarLista(); } }) : null);
    poner(cajaPestanas, pestanasVista());
    const abierto = !!pendientesCaja.querySelector?.('details')?.open;
    const pendientes = panelCierresPendientes(E, modo);
    if (pendientes && abierto) pendientes.open = true;
    poner(pendientesCaja, pendientes);
    poner(listaCaja, tablero ? vistaTableroTrabajo181(E,tablero,f,repintarLista) : grupos(E, f, modo, repintarLista, vista));
  };

  const cuentas = m => { const base = presentacion==='tablero' ? tareasTableroTrabajo181(E,m).tareas : tareas(E,m); const t = presentacion==='tablero' ? filtrarTareasTrabajo(base.filter(t=>!filtros.persona || t.asignados.includes(filtros.persona)),{...filtros,persona:''}) : filtrarTareasTrabajo(base, filtros); const n = g => t.filter(x => [...VISTAS[g], 'revision', 'olvidada', 'por_contrastar', 'sin_planificar'].includes(x.grupoV)).length; return { hoy: n('hoy'), semana: n('semana'), mes: n('mes') }; };
  const pestanasVista = () => {
    const c = cuentas(modo);
    const venc = filtrarTareasTrabajo(tareas(E, modo), filtros).filter(x => ['vencida', 'olvidada'].includes(x.grupoV)).length;
    return h('div', {class:'fila',style:{gap:'8px',flexWrap:'wrap'}}, presentacion==='tablero' ? h('button',{type:'button',class:'bt','aria-pressed':String(inventario),style:{minHeight:'44px'},on:{click:()=>{if(E.vigente&&!E.vigente())return;inventario=!inventario;guardar('ro.mt.inventario',inventario?'si':'no');repintarLista();}}},inventario?'Inventario visible':'Mi diario · periodo seleccionado') : null, pestanas({ etiqueta: 'Periodo de las tareas', activa: vista, pestanas: [
      { id: 'hoy', texto: 'Hoy', icono: esMovil() ? null : 'hoy', cuenta: c.hoy, cuentaEstado: venc ? 'rojo' : '' },
      { id: 'semana', texto: 'Semana', icono: esMovil() ? null : 'cal', cuenta: c.semana },
      { id: 'mes', texto: 'Mes', icono: esMovil() ? null : 'cal', cuenta: c.mes }],
    alCambiar: id => {if(E.vigente&&!E.vigente())return;vista = id;inventario=false;guardar('ro.mt.inventario','no');guardar('ro.mt.vista', id); repintarLista(); } }));
  };
  const cajaPestanas = h('div', {}, pestanasVista());
  const conmutador = veEquipo ? chipsFiltro({ etiqueta: 'Ver', valor: modo, opciones: [
    { valor: 'mias', texto: 'Mis tareas', icono: 'persona' }, { valor: 'equipo', texto: 'Mi equipo', icono: 'users' }],
  alCambiar: v => {if(E.vigente&&!E.vigente())return;modo = v === 'equipo' ? 'equipo' : 'mias'; guardar('ro.mt.modo', modo); Object.assign(filtros, { persona: '', cliente: '', estado: '', prioridad: '', etiqueta: '' }); poner(cajaPestanas, pestanasVista()); repintarLista(); } }) : null;

  const formato = chipsFiltro({etiqueta:'Vista de tareas',valor:presentacion,opciones:[{valor:'lista',texto:'Lista'},{valor:'tablero',texto:'Tablero'}],alCambiar:v=>{if(E.vigente&&!E.vigente())return;presentacion=v==='tablero'?'tablero':'lista';guardar('ro.mt.presentacion',presentacion);repintarLista();}});
  const tuDia = bloqueTuDia(E, () => pintar(E));
  const raras = bloqueRarasEquipo(E);
  const el = pantallaTrabajo({
    id: 'mi-trabajo',
    filtros: h('div', { class: 'pila', style: { gap: 'var(--s-2)' } }, lineaDia(E), coberturaTrabajo(E), formato, h('div', { class: 'fila', style: { gap: 'var(--s-2) var(--s-3)', justifyContent: 'space-between' } }, conmutador, cabFiltros)),
    pestanas: cajaPestanas,
    lista: listaConPendientes,
    detalle: tuDia,
    contexto: [raras, comoFunciona(E)].filter(Boolean),
    tituloContexto: raras ? 'Horas raras del equipo y cómo funciona' : 'Cómo funciona',
  });
  poner(E.cont, el);
  repintarLista();
}

/** Una línea arriba (también en el móvil): horas de hoy frente a la jornada + cronómetro en marcha + guardado en la app. */
function lineaDia(E) {
  const j = (E.V.jornada || []).find(x => x.persona_id === yo(E));
  const hoy = hoyZona(E);
  const observacion = horasDiaTrabajo370(E, yo(E), hoy);
  const cr = E.V.crono;
  const t = cr ? (E.D.tareas || []).find(x => x.id === cr.tarea) : null;
  return h('div', { class: 'fila', style: { gap: 'var(--s-2) var(--s-3)', fontSize: '13px' } },
    h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, icono('clock', { clase: 's' }), h('span', {}, 'Hoy: ', h('b', {}, textoHorasTrabajo370(observacion)), j && esFinDeSemanaTrabajo(hoy) === false ? ` · referencia del generador (no jornada): ${horasTxt(j.horas_dia)}` : ' · sin objetivo diario confirmado para esta fecha')),
    cr ? h('span', { class: 'chip', style: { background: 'var(--accent-soft)', color: 'var(--accent-ink)', maxWidth: '100%', whiteSpace: 'normal' } }, icono('clock', { clase: 's' }),
      `Cronómetro en marcha desde las ${new Date(cr.inicio).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', timeZone: E.V.zona || undefined })}${t ? ` · ${t.tarea.slice(0, 40)}` : ''}`) : null,
    !E.ctx.servidor ? h('span', { class: 'sub' }, 'Sin servidor RO · solo lectura; cambios disponibles en ClickUp') : null,
    E.ctx.soloLectura ? h('span', { class: 'sub' }, avisoLecturaTrabajo(E.ctx)) : null);
}

function grupos(E, lista, modo, repintar, vista) {
  const { ctx } = E;
  if (!lista.length) {
    return [h('div', { class: 'pila', style: { gap: 'var(--s-2)' } },
      vacioLinea('No se muestran tareas en este periodo con los filtros actuales.', { icono: 'info' }),
      h('p', { class: 'sub' }, 'Esta es la copia disponible de tus tareas autorizadas, no una comprobación de todo ClickUp. Mira Semana o Mes y revisa la cobertura de la copia.'),
      Object.values(E.filtros || {}).some(Boolean) ? h('button', { type: 'button', class: 'bt', style: { minHeight: '44px', alignSelf: 'flex-start' },
        on: { click: () => { for (const k of Object.keys(E.filtros)) E.filtros[k] = ''; repintar(); } } }, 'Quitar filtros') : null)];
  }
  const por = new Map();
  for (const t of lista) { if (!GRUPO[t.grupoV]) continue; if (!por.has(t.grupoV)) por.set(t.grupoV, []); por.get(t.grupoV).push(t); }
  const out = [];
  for (const [g, ts] of [...por.entries()].sort((a, b) => GRUPO[a[0]].orden - GRUPO[b[0]].orden)) {
    ts.sort((a, b) => (a.vence || '9999').localeCompare(b.vence || '9999') || (a.prio_n || 5) - (b.prio_n || 5));
    const def = { ...GRUPO[g], t: tituloGrupo(g, ts) };
    const tope = esMovil() ? 8 : 15;
    const ol = h('ol', { class: 'primero', 'aria-label': def.t });
    const pintarFilas = n => { poner(ol, ts.slice(0, n).map(t => fila(E, t, modo, repintar))); filasFlexibles(ol, { minTexto: 220 }); };
    pintarFilas(tope);
    const mas = ts.length > tope ? h('button', { type: 'button', class: 'bt mini', style: { margin: 'var(--s-2) var(--relleno)' }, on: { click: e => { pintarFilas(ts.length); e.currentTarget.remove(); } } }, `Ver ${fmt.num(ts.length - tope)} más`) : null;
    const cab = h('header', { class: 'fila', style: { padding: 'var(--s-3) var(--relleno)', gap: 'var(--s-2)', borderBottom: '1px solid var(--line-soft)' } },
      punto(def.e), h('h2', { style: { fontSize: '15px', margin: '0', flex: '1 1 auto', textAlign: 'left' } }, def.t), h('span', { class: 'sub' }, fmt.num(ts.length)));
    if (def.plegado) {
      out.push(h('details', { class: 'panel' }, h('summary', { style: { padding: 'var(--s-3) var(--relleno)', cursor: 'pointer', fontWeight: '600' } }, `${def.t} · ${fmt.num(ts.length)}`), ol, mas));
    } else out.push(h('section', { class: 'panel', 'aria-label': def.t }, cab, ol, mas));
  }
  return out;
}

function fila(E, t, modo, repintar) {
  const { ctx } = E;
  const hoy = ctx.hoy;
  const cli = t.cli ? ctx.clientes.find(c => c.id === t.cli) : null;
  const abierta = E.abierta === clave(t);
  const venc = t.vence && t.vence < hoy;
  const pendiente = t.capa.cambios.some(x => ['simulado', 'pendiente', 'enviado'].includes(x.estado));
  const pidio = t.pidio === 'yo' ? 'te la pusiste tú' : t.pidio ? `la pidió ${ctx.nombre(t.pidio)}` : null;
  const meta = [
    h('span', { class: 'fila', style: { gap: '6px', flexWrap: 'nowrap' } }, punto(venc ? 'rojo' : t.vence === hoy ? 'ambar' : 'gris'), t.vence ? (venc ? `venció ${diaTxt(t.vence, hoy)}` : `vence ${diaTxt(t.vence, hoy)}`) : 'sin fecha'),
    enCursoSinFecha(t) ? 'se muestra aquí por su estado En curso en ClickUp; no hay fecha límite registrada' : null,
    !t.vence && t.estado === 'diario' ? 'aparece hoy por su estado Diario en ClickUp; no tiene fecha límite' : null,
    t.resolucion_estado?.estado === 'indeterminado' ? 'Estado indeterminado · contrasta con ClickUp' : t.resolucion_estado && !t.resolucion_estado.final_flujo ? 'Estado no final en esta lista' : null,
    t.cliente || null, PRIORIDAD_TEXTO[t.prioridad] ? `Prioridad: ${PRIORIDAD_TEXTO[t.prioridad]}` : null, estadoTxt(t.estado), modo === 'equipo' ? `de ${ctx.nombre(t.persona_id)}` : null, pidio,
    t.est_h ? `estimada ${horasTxt(t.est_h)}${t.horas_t ? ` · lleva ${horasTxt(t.horas_t)}` : ''}` : t.horas_t ? `lleva ${horasTxt(t.horas_t)}` : null,
    t.capa.cambios.some(x => ['fallido', 'conflicto'].includes(x.estado)) ? h('span', { style: { color: 'var(--warn-ink)', fontWeight: '600' } }, 'Cambios con fallo o conflicto · revisa Envíos › ClickUp') : null,
    pendiente ? h('span', { style: { color: 'var(--accent-ink)', fontWeight: '600' } }, 'con cambios en la app') : null,
  ].filter(Boolean);
  const titulo = h('button', { type: 'button', class: 'mot', 'aria-expanded': String(abierta), 'data-uso': 'abrir-tarea', style: { background: 'none', border: '0', padding: '0', textAlign: 'left', cursor: 'pointer', color: 'var(--ink)', minHeight: '32px', font: 'inherit', fontWeight: '600' },
    on: { click: () => { E.abierta = abierta ? null : clave(t); guardar('ro.mt.abierta', E.abierta || ''); repintar(); } } }, t.tarea);
  const mia = t.persona_id === yo(E);
  const enRevision = t.grupoV === 'revision';
  const acciones = h('div', { class: 'acc' },
    puedeTocar(E, t) && !enRevision ? botonFinalizar203(E,t,repintar) : null,
    mia && !ctx.soloLectura ? botonCrono(E, t) : null,
    h('button', { type: 'button', class: 'bt mini', 'aria-label': `${abierta ? 'Cerrar acciones' : 'Más acciones'}: ${t.tarea}`, 'aria-expanded': String(abierta), 'data-uso': 'abrir-tarea',
      on: { click: () => { E.abierta = abierta ? null : clave(t); guardar('ro.mt.abierta', E.abierta || ''); repintar(); } } }, icono(abierta ? 'cerrar' : 'opciones', { clase: 's' }), esMovil() ? null : (abierta ? 'Cerrar' : 'Más')));
  const li = h('li', { 'data-tarea': t.id, class: venc ? '' : 'gris' },
    logoCliente({ nombre: t.cliente || '·', logo: cli?.logo }),
    h('div', { style: { minWidth: '0', flex: '1 1 220px' } }, titulo, h('div', { class: 'det fila', style: { gap: '4px 10px', marginTop: '2px' } }, meta.map(m => h('span', {}, m)))),
    acciones);
  if (abierta) li.append(h('div', { style: { flex: '1 1 100%', minWidth: '0' } }, detalle(E, t, repintar)));
  return li;
}

/** Lectura de campos ya autorizados: sin llamadas a ClickUp ni HTML importado. */
function lecturaDetalle197(E,t) {
  const d=prepararDetalleTarea197({tarea_id:t.id,persona_id:t.persona_id,cliente_id:t.cli,lista_id:t.lista_id,tareasVisibles:E.D.tareas || [],cambios:[...(E.V.cambios || []),...E.local],actor_id:E.ctx.persona.id,fechaFuente:E.D.fuentes?.tareas?.hora || E.D.generado});
  if(!d.autorizado)return vacioLinea('No se confirmó la identidad de la tarea para consultar sus datos de la copia.',{icono:'info'});
  const enlace=(r,etiqueta)=>h('a',{class:'bt mini',href:r.url,target:'_blank',rel:'noopener',style:{minHeight:'44px',whiteSpace:'normal',overflowWrap:'anywhere'}},etiqueta || r.titulo);
  return h('div',{class:'pila','data-detalle-197':'',style:{gap:'8px'}},
    h('details',{},h('summary',{style:{minHeight:'44px',cursor:'pointer'}},d.brief?'Brief de la copia':'Brief no disponible en la copia'),
      h('p',{class:'sub'},d.fecha_fuente?`Fuente: copia autorizada de ClickUp · lectura ${d.fecha_fuente}.`:'Fuente: copia autorizada de ClickUp · fecha de lectura no disponible.'),
      h('p',{style:{whiteSpace:'pre-wrap',overflowWrap:'anywhere',margin:'0'}},d.brief || (d.brief_discrepante?'Las filas de esta tarea no coinciden en el brief. Contrasta la tarea original.':'Esta copia no incluye descripción; no significa que falte en ClickUp. Abre la tarea original para consultarla.')),
      d.brief_truncado?h('p',{class:'sub'},'Descripción recortada; consulta el original antes de tomar decisiones.'):null),
    h('details',{},h('summary',{style:{minHeight:'44px',cursor:'pointer'}},`Comentarios visibles en RO · ${d.comentarios_disponibles}`),
      h('p',{class:'sub'},'Sólo comentarios de esta identidad ya disponibles en RO; no es el hilo completo de ClickUp. No acredita menciones ni notificaciones. El estado local confirmado no demuestra lectura del destinatario.'),
      !d.comentarios.length?h('p',{class:'sub'},'No hay texto de comentarios disponible en este archivo para esta identidad; no permite concluir que no haya comentarios en ClickUp.'):null,
      d.comentarios_disponibles>20?h('p',{class:'sub'},'Se muestran los últimos 20 comentarios disponibles.'):null,
      d.comentarios.map(c=>h('div',{style:{borderTop:'1px solid var(--line)',padding:'8px 0'}},h('p',{class:'sub',style:{margin:'0'}},`${c.origen} · ${c.fecha || 'fecha por contrastar'} · ${c.estado}`),h('p',{style:{whiteSpace:'pre-wrap',overflowWrap:'anywhere',margin:'4px 0'}},c.texto)))),
    h('details',{},h('summary',{style:{minHeight:'44px',cursor:'pointer'}},`Relaciones de tareas en la copia · ${d.hijas_disponibles} subtareas visibles`),
      h('p',{class:'sub'},'Relaciones por IDs explícitos de la misma lista y cliente, dentro del alcance autorizado. Copia parcial: no indica todas las subtareas ni su aceptación.'),
      d.padre?enlace(d.padre,`Tarea padre: ${d.padre.titulo}`):d.padre_fuera_copia?h('p',{class:'sub'},'La tarea padre no está disponible en esta copia autorizada.'):null,
      d.hijas.length?h('ul',{},d.hijas.map(r=>h('li',{},enlace(r)))):h('p',{class:'sub'},'No hay subtareas visibles en esta copia; no significa que no existan en ClickUp.'),
      d.hijas_disponibles>30?h('p',{class:'sub'},'Se muestran hasta 30 relaciones visibles.'):null),
    renderMetadatosTarea225(E,t,h),
    h('p',{class:'sub'},'Las menciones y notificaciones de ClickUp no están acreditadas por esta copia. Consulta el hilo original.'),
    d.url?enlace({url:d.url},'Ver hilo, entregable y materiales en ClickUp'):null);
}

/** Acción de ClickUp por la copia segura. Devuelve el texto final para el botón. */
async function actuar(E, t, tipo, vp, hecho, repintar, texto) {
  if(tipo==='comentario')throw new Error('El comentario requiere una intención durable. Usa el editor de comentarios de la tarea.');
  if(['marcar_hecha','cambiar_estado'].includes(tipo))throw new Error('El estado requiere revisión del servidor e intención durable. Usa el selector de estado de la tarea.');
  if (E.vigente && !E.vigente()) return '';
  if (!E.ctx.servidor) throw new Error('Falta el servidor de RO: el cambio no se ha guardado. Abre ClickUp para hacerlo allí.');
  const r = await E.ctx.accion({ herramienta: 'clickup', tipo, objeto: t.id, cliente_id: null, texto: texto || hecho, vista_previa: vp });
  if (E.vigente && !E.vigente()) return '';
  const campo = tipo === 'cambiar_fecha' ? 'fecha' : tipo === 'imputar_horas' ? 'horas' : 'comentario';
  E.local.push({ tarea: t.id, quien: yo(E), tipo, campo, valor: vp.a || vp.dia, minutos: vp.minutos, dia: vp.dia, texto, local: true,
    estado: r?.sincronia?.estado || 'simulado', estado_texto: r?.sincronia?.texto || 'Hecho en la app · pendiente de ClickUp', creado: new Date().toISOString() });
  setTimeout(() => { if (!E.vigente || E.vigente()) { if (campo === 'horas') pintar(E); else repintar?.(); } }, 400);
  return `${hecho} · guardado en la app`;
}

function botonCrono(E, t) {
  const cr = E.V.crono;
  const enEsta = cr && cr.tarea === t.id;
  const otro = cr && !enEsta;
  return h('button', { type: 'button', class: `bt mini${enEsta ? ' pri' : ''}`, 'aria-pressed': String(!!enEsta), title: otro ? 'El cronómetro está en otra tarea: páralo antes' : enEsta ? 'Parar y apuntar el tiempo' : 'Empezar el cronómetro',
    'aria-label': `${enEsta ? 'Parar el cronómetro' : 'Empezar el cronómetro'}: ${t.tarea}`, disabled: otro || !E.ctx.servidor || E.ctx.soloLectura || null,
    on: { click: async e => {
      if ((E.vigente && !E.vigente()) || (E.ctx.vigente && !E.ctx.vigente()) || !E.ctx.servidor || E.ctx.soloLectura) return;
      const b = e.currentTarget; b.disabled = true;
      try {
        const r = await E.ctx.api('mi_trabajo/crono', { metodo: 'POST', cuerpo: { accion: enEsta ? 'parar' : 'empezar', tarea: t.id } });
        if (E.vigente && !E.vigente()) return;
        if (enEsta) {
          E.V.crono = null;
          E.local.push({ tarea: t.id, quien: yo(E), campo: 'horas', minutos: r.minutos, dia: r.dia, local: true, estado: 'simulado', estado_texto: 'Hecho en la app · pendiente de ClickUp', creado: new Date().toISOString() });
          avisoFlotante(`${horasTxt(r.minutos / 60)} apuntados · ${r.texto}${r.aviso ? `. ${r.aviso}` : ''}`);
        } else { E.V.crono = r.crono; avisoFlotante('Cronómetro en marcha. Sigue aunque cierres la app.', { icono: 'clock' }); }
        pintar(E);
      } catch (err) { if (E.vigente && !E.vigente()) return; b.disabled = false; avisoFlotante(`No se pudo: ${err.message}`, { icono: 'alert' }); }
    } } }, icono('clock', { clase: 's' }), esMovil() ? null : enEsta ? 'Parar' : 'Empezar');
}

/** Panel de acciones de una tarea: estado, fecha, comentario, tiempo, enlace a ClickUp e historial. */
function permisoFinalizar203(E,t) {
  const scope=contextoMovimientoDetalle200(E,t),resolver=(r,e=r.estado,l=false)=>resolverEstadoTrabajo(E,r,e,l);
  return destinosFinales203(scope.t,permisoMovimiento192(scope.E,scope.t,resolver),resolver);
}
function botonFinalizar203(E,t,repintar) {
  const permiso=permisoFinalizar203(E,t);
  return h('button',{type:'button',class:'bt mini','data-finalizar-203':t.id,disabled:!permiso.ok||null,'aria-label':`Elegir estado final: ${t.tarea}`,'aria-description':permiso.motivo,title:permiso.motivo,style:{minHeight:'44px'},on:{click:()=>{
    if(E.vigente&&!E.vigente())return;
    const actual=permisoFinalizar203(E,t);if(!actual.ok)return;
    E.movimientos192 ||= new Map();const previo=E.movimientos192.get(t.id);
    if(!previo?.intento)E.movimientos192.set(t.id,{abierto:true,finalizar203:true,destino:actual.destinos.length===1?actual.destinos[0]:'',intento:null});
    E.abierta=clave(t);guardar('ro.mt.abierta',E.abierta);repintar();
  }}},'Finalizar…');
}

function cambioEstadoDetalle200(E,t,repintar) {
  E.movimientos192 ||= new Map();
  const scope=contextoMovimientoDetalle200(E,t),resolver=(r,e=r.estado,l=false)=>resolverEstadoTrabajo(E,r,e,l);
  const permiso=permisoMovimiento192(scope.E,scope.t,resolver);
  let estado=E.movimientos192.get(t.id);
  if(!estado){estado={abierto:true,destino:'',intento:null};}
  const finales=estado.finalizar203 ? destinosFinales203(scope.t,permiso,resolver) : null;
  const destinos=finales?.destinos || permiso.destinos;
  const habilitado=permiso.ok && (!finales || finales.ok);
  const vivo=()=>scope.vigente();
  const guardarEstado=async()=>{
    if(!vivo()||!permisoMovimiento192(scope.E,scope.t,resolver).ok)return;
    if(estado.finalizar203 && !estado.intento && !permisoFinalizar203(E,t).destinos.includes(estado.destino))return;
    E.movimientos192.set(t.id,estado);
    if(!estado.intento){try{estado.intento=crearIntentoMovimiento192(scope.E,scope.t,estado.destino,resolver,crypto.randomUUID());}catch(e){estado.error=e.message;if(vivo())repintar();return;}}
    const p=guardarMovimiento192(scope.E,scope.t,estado.intento,resolver,a=>E.ctx.accion(a));if(vivo())repintar();
    try{await p;}catch(e){if(vivo())estado.error=e.message;}if(vivo())repintar();
  };
  return h('div',{'data-cambio-estado-200':t.id,class:'pila',style:{gap:'8px'}},
    !habilitado?h('p',{class:'sub',role:'status'},finales?.motivo || permiso.motivo):null,
    finales?h('p',{class:'sub'},'Elige el estado final exacto. Final de flujo no acredita entrega aceptada ni resultado comercial.'):null,
    habilitado && !estado.intento?menuElegir({etiqueta:'Estado exacto',todos:'Elige destino',valor:estado.destino,opciones:destinos.map(e=>({valor:e,texto:e})),alCambiar:e=>{if(vivo()&&!estado.intento){estado.destino=e;E.movimientos192.set(t.id,estado);repintar();}}}):null,
    finales && !estado.intento?h('button',{type:'button',class:'bt mini',style:{minHeight:'44px'},on:{click:()=>{if(!vivo())return;estado.finalizar203=false;estado.destino='';E.movimientos192.set(t.id,estado);repintar();}}},'Ver todos los estados de esta lista'):null,
    estado.intento?h('p',{class:'sub'},`${estado.intento.payload.vista_previa.expected_estado} → ${estado.intento.payload.vista_previa.a}`):null,
    estado.error||estado.intento?.mensaje?h('p',{class:'sub',role:'status'},estado.error||estado.intento.mensaje):null,
    h('button',{type:'button',class:'bt',disabled:!habilitado||(!estado.destino&&!estado.intento)||estado.intento?.estado==='guardando'||!!estado.intento?.recibo||null,'aria-label':`Guardar cambio de estado: ${t.tarea || 'tarea'}`,style:{minHeight:'44px'},on:{click:guardarEstado}},estado.intento?.estado==='sin_confirmar'?'Reintentar la misma intención':'Guardar cambio en RO'));
}

function detalle(E, t, repintar) {
  const { ctx } = E;
  const hoy = ctx.hoy;
  const ro = ctx.soloLectura || !puedeTocar(E, t);
  const mia = t.persona_id === yo(E);
  const enRevision = t.grupoV === 'revision';
  const estados = ((E.V.estados_lista || E.D.estados_lista || {})[t.lista_id] || []).filter(e => e !== t.estado);
  const caja = h('div', { class: 'pila', style: { gap: 'var(--s-3)', marginTop: 'var(--s-2)', padding: 'var(--s-3)', border: '1px solid var(--line)', borderRadius: 'var(--r-m)', background: 'var(--card)' } });
  const seccion = (titulo, ...hijos) => h('div', { class: 'pila', style: { gap: 'var(--s-2)' } }, h('b', { style: { fontSize: '13px' } }, titulo), ...hijos);

  // Estado: el detalle usa el mismo CAS, intención durable y recibo que el tablero.
  const selEstado = enRevision ? vacioLinea('Espera la revisión de otra persona: se aprueba o se piden cambios en Producción › Por revisar.', { icono: 'ojo' }) : cambioEstadoDetalle200(E,t,repintar);

  // fecha
  const inFecha = h('input', { type: 'date', value: t.vence || '', 'aria-label': 'Nueva fecha límite', min: sumarDias(hoy, -60), style: { minHeight: '32px', border: '1px solid var(--line)', borderRadius: 'var(--r-s)', padding: '4px 8px', maxWidth: '100%' } });
  const lunes = (() => { const d = new Date(`${hoy}T12:00:00`); return sumarDias(hoy, ((8 - d.getDay()) % 7) || 7); })();
  const rapida = (txt, dia) => h('button', { type: 'button', class: 'bt mini', disabled: ro || null, on: { click: () => { inFecha.value = dia; } } }, txt);
  const selFecha = enRevision ? null : h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, inFecha, rapida('Hoy', hoy), rapida('Mañana', sumarDias(hoy, 1)), rapida('Lunes', lunes),
    botonDeshacer({ texto: 'Cambiar fecha', hecho: 'Fecha cambiada', soloLectura: ro, validar: () => (!/^\d{4}-\d\d-\d\d$/.test(inFecha.value) ? 'Elige una fecha' : inFecha.value === t.vence ? 'Es la misma fecha' : null),
      alHacer: () => actuar(E, t, 'cambiar_fecha', { dia: inFecha.value }, `Fecha → ${diaTxt(inFecha.value, hoy)}`, repintar) }));

  // comentario
  const comentarioDurable=panelComentario366(E,t,h);

  // tiempo (solo en tus tareas: las horas son de quien las imputa)
  let diaHoras = hoyZona(E);
  const diasOp = [0, 1, 2, 3, 4, 5, 6].map(n => sumarDias(hoyZona(E), -n));
  const inMin = h('input', { type: 'number', min: 1, max: 720, step: 5, placeholder: 'min', 'aria-label': 'Minutos a mano', style: { width: '84px', minHeight: '32px', border: '1px solid var(--line)', borderRadius: 'var(--r-s)', padding: '4px 8px' } });
  const anadir = (min, etiqueta) => botonDeshacer({ texto: etiqueta, hecho: `${etiqueta} apuntados`, soloLectura: ctx.soloLectura || !ctx.servidor,
    validar: () => { const m = typeof min === 'function' ? min() : min; return !(m >= 1 && m <= 720) ? 'Entre 1 y 720 minutos' : null; },
    alHacer: () => { const m = typeof min === 'function' ? min() : min; return actuar(E, t, 'imputar_horas', { minutos: m, dia: diaHoras }, `${horasTxt(m / 60)} el ${diaTxt(diaHoras, hoyZona(E))}`, repintar,
      `${m} min desde Mi trabajo (${new Date().toLocaleTimeString('es-ES')})`); } });
  const tiempo = mia ? seccion('Añadir tiempo',
    h('div', { class: 'fila', style: { gap: 'var(--s-2)' } },
      menuElegir({ etiqueta: 'Día', todos: 'hoy', opciones: diasOp.slice(1).map(d => ({ valor: d, texto: diaTxt(d, hoyZona(E)) })), valor: '', alCambiar: v => { diaHoras = v || hoyZona(E); } }),
      anadir(15, '15 min'), anadir(30, '30 min'), anadir(60, '1 h')),
    h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, inMin, anadir(() => Math.round(Number(inMin.value)), 'Añadir'), botonCrono(E, t))) : null;

  const historial = t.capa.cambios.slice(-6).reverse();
  poner(caja,
    h('p', { class: 'sub', style: { margin: '0' } }, icono('info', { clase: 's' }), ' ', 'Los cambios se guardan primero en RO; comprueba el envío y la confirmación en ClickUp por cada acción.'),
    !ctx.servidor ? vacioLinea('Sin servidor de RO, esta vista es de lectura: los cambios no se guardarían. Abre la tarea en ClickUp.', { icono: 'info' }) : ro && !ctx.soloLectura ? vacioLinea('Esta tarea no es tuya ni de tu equipo: solo la ves.', { icono: 'candado' }) : null,
    lecturaDetalle197(E,t),
    contextoTareaTrabajo(E, t),
    seccion('Estado', selEstado),
    selFecha ? seccion('Fecha límite', selFecha) : null,
    comentarioDurable,
    h('p', { class: 'sub', style: { margin: '0' } }, 'Para registrar un entregable o una mención con notificación en la tarea original, abre ClickUp. Este panel aún no incluye esos campos.'),
    tiempo,
    h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, h('a', { class: 'bt mini', href: `https://app.clickup.com/t/${encodeURIComponent(t.id)}`, target: '_blank', rel: 'noopener' }, icono('ext', { clase: 's' }), 'Abrir en ClickUp')),
    historial.length ? seccion('Lo hecho en la app', h('ul', { class: 'lista-i' }, historial.map(c => h('li', {}, icono(c.campo === 'horas' ? 'clock' : c.campo === 'comentario' ? 'chat' : c.campo === 'fecha' ? 'cal' : 'check', { clase: 's' }),
      h('span', { class: 't', style: { whiteSpace: 'normal' } }, que(c, ctx, hoyZona(E))), h('span', { class: 'x' }, c.local ? 'pendiente de ClickUp' : (c.estado_texto || '').replace(' (simulación)', '')))))) : null);
  return caja;
}

const que = (c, ctx, hoy) => (c.campo === 'horas' ? `${horasTxt((c.minutos || 0) / 60)} el ${diaTxt(c.dia, hoy)}` : c.campo === 'fecha' ? `Fecha → ${diaTxt(c.valor, hoy)}`
  : c.campo === 'comentario' ? `Comentario${c.texto ? `: «${String(c.texto).slice(0, 60)}»` : ''}` : `Estado → ${estadoTxt(c.valor)}`) + (c.quien && c.quien !== ctx.persona.id ? ` · ${ctx.nombre(c.quien)}` : '');

// ------------------------------------------------------------------ Tu día (a la derecha; debajo en el móvil)
function bloqueTuDia(E, repintar) {
  const { ctx } = E;
  const hoy = hoyZona(E);
  const j = (E.V.jornada || []).find(x => x.persona_id === yo(E));
  const dias = E.V.dias?.[yo(E)] || {};
  const tot = d => horasDiaTrabajo370(E, yo(E), d);
  const llevas = tot(hoy);
  const deHoy = [...(E.V.horas_app || []), ...E.local.filter(x => x.campo === 'horas')].filter(x => x.dia === hoy && x.quien === yo(E));
  const mias = agrupar((E.V.raras || []).filter(r => r.persona_id === yo(E)));
  const semana = [6, 5, 4, 3, 2, 1, 0].map(n => sumarDias(hoy, -n));
  const mostrarReferencia = j && esFinDeSemanaTrabajo(hoy) === false;
  return h('section', { class: 'panel', 'aria-label': 'Tu día' },
    h('header', { style: { padding: 'var(--s-3) var(--relleno)' } }, h('h2', {}, icono('clock'), 'Tu día'),
      h('p', { class: 'sub' }, j ? `Referencia del generador: ${horasTxt(j.horas_dia)} por lunes-viernes (jornada no confirmada) (${fmt.num(j.horas_mes)} h al mes entre ${j.dias_lab_mes} días laborables) · ${hoy === ctx.hoy ? 'hoy' : `tu hoy es ${diaTxt(hoy, ctx.hoy)}`}` : 'No hay referencia del generador; jornada no confirmada.')),
    h('div', { class: 'pila', style: { padding: '0 var(--relleno) var(--s-4)', gap: 'var(--s-3)' } },
      h('div', { class: 'pila', style: { gap: '6px' } }, h('div', { class: 'fila', style: { justifyContent: 'space-between' } }, h('b', { style: { font: 'var(--t-h3)' } }, textoHorasTrabajo370(llevas)), h('span', { class: 'sub' }, mostrarReferencia ? `registradas · referencia laborable ${horasTxt(j.horas_dia)}` : 'registradas · sin objetivo diario confirmado')),
        h('p', {class:'sub',style:{margin:'0'}}, `ClickUp: ${llevas.cu===null?'sin registros':horasTxt(llevas.cu)} · declaraciones RO: ${llevas.ro===null?'sin registros':horasTxt(llevas.ro)}. Copia parcial; RO no confirma llegada a ClickUp.`)),
      h('div', { class: 'fila', style: { gap: '4px', flexWrap: 'nowrap', overflowX: 'auto', maxWidth: '100%' }, 'aria-label': 'Horas de los últimos 7 días' }, semana.map(d => {
        const v = tot(d);
        return h('div', { style: { flex: '1 1 0', minWidth: '36px', textAlign: 'center', fontSize: '12px', padding: '4px 2px', borderRadius: 'var(--r-s)', background: d === hoy ? 'var(--accent-soft)' : 'transparent' } },
          h('div', { class: 'sub', style: { fontSize: '12px' } }, DIAS[new Date(`${d}T12:00:00`).getDay()]), h('b', { style: { color: 'var(--ink)' } }, v.valor===null?'—':v.valor>0&&v.valor<0.1?'<0,1':fmt.num(v.valor, 1)));
      })),
      mias.length ? h('details', {}, h('summary',{style:{minHeight:'44px',cursor:'pointer'}},`Registros por contrastar · ${mias.length}`),h('p',{class:'sub'},'Avisos de la copia parcial; no acreditan ausencia de trabajo.'),h('div', { class: 'pila', style: { gap: 'var(--s-2)' } }, mias.map(r => avisoAmable(E, r)))) : j ? h('p', { class: 'sub', style: { margin: '0' } }, icono('ok', { clase: 's' }), ' No hay avisos de horas en los datos disponibles.') : null,
      h('p', { class: 'sub', style: { margin: '0' } }, 'Las horas son registros disponibles. No tener registros no demuestra que no se haya trabajado; esta referencia no confirma horarios de sábados, domingos, festivos o ausencias.'),
      deHoy.length ? h('div', {}, h('b', { style: { fontSize: '13px' } }, 'Apuntado hoy en la app'), h('ul', { class: 'lista-i' }, deHoy.slice(-6).map(x => {
        const t = (E.D.tareas || []).find(y => y.id === x.tarea);
        return h('li', {}, h('span', { class: 't' }, `${horasTxt((x.minutos || 0) / 60)} · ${t ? t.tarea : 'tarea'}`), h('span', { class: 'x' }, x.en_clickup ? 'ya en ClickUp' : 'pendiente de ClickUp'));
      }))) : null));
}

/** Varias horas en clientes que no son tuyos → un solo aviso con la suma (no una tarjeta por apunte). */
function agrupar(rs) {
  const aj = rs.filter(r => r.regla === 'cliente_ajeno');
  if (aj.length < 2) return rs;
  const cl = [...new Set(aj.map(r => r.cliente_id).filter(Boolean))];
  return [...rs.filter(r => r.regla !== 'cliente_ajeno'), { regla: 'cliente_ajeno', persona_id: aj[0].persona_id, varias: aj.length, horas: aj.reduce((a, r) => a + (r.horas || 0), 0), clientes: cl }];
}

/** Aviso amable de lo tuyo, con su atajo para arreglarlo. */
function avisoAmable(E, r) {
  const hoy = hoyZona(E);
  const d = r.dia ? diaTxt(r.dia, hoy) : '';
  const txt = {
    sin_registros_copia: `${d === 'ayer' ? 'Ayer' : `El ${d}`} no hay registros en esta copia parcial; no acredita ausencia de trabajo.`,
    sin_horas: `${d === 'ayer' ? 'Ayer' : `El ${d}`} no aparecen horas en esta copia parcial. Contrasta los registros de ClickUp${E.ctx.soloLectura ? '.' : ' y, si falta un apunte, añádelo en la tarea correspondiente.'}`, 
    mas_10: r.una_sola ? `El ${d} hay un apunte de ${horasTxt(r.horas)} seguidas: ¿se quedó el cronómetro encendido?` : `El ${d} tienes ${horasTxt(r.horas)} imputadas: ¿es correcto?`,
    fin_semana: `El ${d} (fin de semana) imputaste ${horasTxt(r.horas)}. Si fue a propósito, perfecto.`,
    doble_estimacion: `«${(r.tarea || '').slice(0, 60)}» lleva ${horasTxt(r.horas)} y estaba estimada en ${horasTxt(r.est_h)}. Si hace falta, cambia la estimación en ClickUp o coméntalo.`,
    cliente_ajeno: r.varias ? `En las dos últimas semanas imputaste ${horasTxt(r.horas)} en ${r.varias} tareas que no son tuyas de clientes que no son de tu cartera${r.clientes?.length ? ` (${r.clientes.map(c => E.ctx.clientes.find(x => x.id === c)?.nombre || 'cliente').slice(0, 3).join(', ')})` : ''}. Si es correcto, no hace falta nada.` : `El ${d} imputaste ${horasTxt(r.horas)} en una tarea que no es tuya de un cliente que no es de tu cartera${r.cliente_id ? ` (${E.ctx.clientes.find(c => c.id === r.cliente_id)?.nombre || 'cliente'})` : ''}. Si es correcto, no hace falta nada.`,
  }[r.regla] || '';
  const tarea = r.tarea_id ? (E.D.tareas || []).find(t => t.id === r.tarea_id && t.persona_id === yo(E)) : null;
  return h('div', { class: 'fila', role: 'note', style: { gap: 'var(--s-2)', alignItems: 'flex-start', flexWrap: 'nowrap', padding: 'var(--s-2) var(--s-3)', borderRadius: 'var(--r-m)', background: 'var(--warn-soft)', color: 'var(--ink)', fontSize: '13px' } },
    icono(RARA[r.regla]?.i || 'info', { clase: 's' }), h('span', { style: { minWidth: '0' } }, txt,
      tarea ? h('button', { type: 'button', class: 'bt mini', style: { marginLeft: 'var(--s-2)' }, on: { click: () => { E.abierta = clave(tarea); guardar('ro.mt.abierta', E.abierta); pintar(E); } } }, 'Abrir la tarea') : null));
}

// ------------------------------------------------------------------ resumen del equipo (RRHH, operaciones, dirección y cada jefe)
function bloqueRarasEquipo(E) {
  const { ctx } = E;
  const otras = (E.V.raras || []).filter(r => r.persona_id !== yo(E));
  if (!E.V.ve_equipo) return null;
  const por = new Map();
  for (const r of otras) {
    if (!por.has(r.persona_id)) por.set(r.persona_id, { persona_id: r.persona_id, sin_horas: 0, mas_10: 0, fin_semana: 0, doble_estimacion: 0, cliente_ajeno: 0, dias: new Set() });
    const x = por.get(r.persona_id); const regla = r.regla==='sin_registros_copia'?'sin_horas':r.regla; if(Object.hasOwn(x,regla)) x[regla] += 1; if (r.dia) x.dias.add(r.dia);
  }
  const filas = [...por.values()].sort((a, b) => ctx.nombre(a.persona_id).localeCompare(ctx.nombre(b.persona_id), 'es'));
  const n = k => filas.reduce((a, x) => a + x[k], 0);
  const celda = k => r => (r[k] ? h('b', {}, fmt.num(r[k])) : h('span', { class: 'sub' }, '—'));
  return h('section', { class: 'pila', 'aria-label': 'Horas raras del equipo', style: { gap: 'var(--s-2)' } },
    h('b', {}, `Horas raras de tu equipo · ${fmt.num(filas.length)} ${filas.length === 1 ? 'persona' : 'personas'}`),
    h('p', { class: 'sub', style: { margin: '0' } }, `Fechas sin registros en la copia (5 lunes-viernes anteriores): ${fmt.num(n('sin_horas'))} · más de 10 h: ${fmt.num(n('mas_10'))} · fin de semana: ${fmt.num(n('fin_semana'))} · doble de lo estimado: ${fmt.num(n('doble_estimacion'))} · cliente que no es suyo: ${fmt.num(n('cliente_ajeno'))}. Solo aviso: cada persona ve el suyo.`),
    filas.length ? tablaApilable({ porPagina: 0, columnas: [
      { titulo: 'Persona', principal: true, celda: r => ctx.nombre(r.persona_id) },
      { titulo: 'Sin registros', num: true, celda: celda('sin_horas') }, { titulo: '+10 h', num: true, celda: celda('mas_10') },
      { titulo: 'Finde', num: true, celda: celda('fin_semana') }, { titulo: '×2', num: true, celda: celda('doble_estimacion') },
      { titulo: 'Ajeno', num: true, celda: celda('cliente_ajeno') }], filas }) : vacioLinea('No hay avisos en los registros disponibles; cobertura parcial.', { icono: 'ok' }),
    filas.length ? h('p', { class: 'sub', style: { margin: '0' } }, 'Sin registros = fechas sin apuntes en una copia parcial; calendario no confirmado · +10 h = días de más de 10 h · Finde = fin de semana · ×2 = tareas con más del doble de lo estimado · Ajeno = horas en un cliente que no es suyo.') : null);
}

function coberturaTrabajo(E) {
  const c = E.V.cobertura_tareas || E.D.cobertura_tareas;
  const fecha = E.D.fuentes?.tareas?.hora;
  return h('details', { class: 'sub', style: { margin: '0', whiteSpace: 'normal' } },
    h('summary', { style: { cursor: 'pointer', minHeight: '32px' } },
      c?.completa === true ? 'Cobertura declarada de tareas · fuente y límites' : 'Copia parcial de tareas · fuente y límites'),
    h('p', { style: { margin: '6px 0' } },
    c?.completa === true ? 'Copia de tareas con cobertura completa declarada por la fuente.' : 'Copia parcial de tareas: no confirma todo el histórico ni las archivadas.',
    fecha ? ` Última lectura: ${fecha}.` : ' No consta la fecha de la última lectura.',
    ' Lista muestra tareas abiertas o por contrastar; Tablero permite consultar también finales de la copia en Inventario visible. Un final de flujo no acredita entrega aceptada. Los cambios en RO requieren confirmar su envío a ClickUp.'));
}

function comoFunciona(E) {
  const f = E.D.fuentes || {};
  return h('div', { class: 'pila', style: { gap: 'var(--s-2)', fontSize: '13px' } },
    h('p', { style: { margin: '0' } }, h('b', {}, E.ctx.soloLectura ? 'Esta vista es de consulta' : 'Los cambios se guardan primero en la app'), E.ctx.soloLectura ? '. No se guardan ni envían cambios desde aquí; puedes consultar la tarea original en ClickUp.' : '. El guardado local no confirma el envío a ClickUp: revisa el estado en Envíos › ClickUp o abre la tarea original.'),
    h('p', { class: 'sub', style: { margin: '0' } }, `Tareas de ClickUp de las ${(f.tareas?.hora || '—').slice(11, 16)} · horas de ClickUp de las ${(f.horas?.hora || '—').slice(11, 16)}. Las horas apuntadas en la app se suman al momento y no se cuentan dos veces cuando lleguen de ClickUp.`),
    h('p', { class: 'sub', style: { margin: '0' } }, E.D.notas?.jornada || ''),
    h('p', { class: 'sub', style: { margin: '0' } }, 'Vencidas, para hoy y esta semana con la misma regla que Producción y Mi día (calendario de la agencia). El día de tus horas va en tu zona horaria.'));
}
