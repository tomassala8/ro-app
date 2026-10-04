import { fechas as FECHAS_RO, fechaCorta as fechaCortaRO, sumarDias as sumarDiasRO } from '../componentes.js';
// modulos/agenda.js · M23 «Agenda» (petición de Tomás, 2-oct-2026).
// Cada persona ve su calendario: citas con clientes y prospectos y sus reuniones. Vistas Hoy y Semana, huecos libres,
// cruce con «En rojo» (cliente en rojo con reunión hoy) y enlace a la ficha del cliente.
// Datos: data/agenda/agenda.json (fuentes_agenda/generar_agenda.py): Zoho CRM (eventos del calendario de Zoho, incluidas
// las citas de Zoho Bookings que pasan al CRM), GoHighLevel de RO (citas de venta y talleres de Tomás; y de la setter que
// las agendó), Zoho Bookings (todo el personal) y Zoho Calendar (el de Tomás) con zbookings.py, y Zoom (grabadas, M15).
// Sólo referencias explícitas compartidas permiten consolidar; copias sin vínculo confirmado permanecen.
// Permisos (servir.py): cada fila lleva persona_id → la persona, su jefe, operaciones, RRHH y dirección. La pantalla
// enseña a cada uno la suya; a los jefes, su equipo; a Mili y Tomás, todos. Prospectos con iniciales: los nombres, solo
// su dueño con «Ver nombres» (ctx.verDato, queda en el rastro).

import { plegarConsejo } from './_plegar_consejo.js';
import {
  h, fmt, icono, tile, tiles, chipEstado, chipsFiltro, pestanas, vacio, avisoParcial, panel, frescura, iniciales,
  avisoFlotante, copiar, tablaApilable, vacioLinea, selectorPersona, menuMas,
} from '../componentes.js';

// Revisión 44 (textos cortados): lo que la pantalla corta con «…» (una línea o el límite de líneas) lleva el texto entero
// en el title, para que la regla de la tarjeta o el nombre largo no se pierdan. Mira el contenedor mientras se pinta.
const _SEL_CORTE = '.tile .tx, .tile .tt span, .tile em, .det, .mot, .sub, .t, td, .chip, summary, b, small';
function vigilarCortes(raiz) {
  if (!raiz || raiz.__cortes) return;
  raiz.__cortes = true;
  let t = 0;
  const mirar = () => { t = 0; for (const el of raiz.querySelectorAll(_SEL_CORTE)) {
    if (el.title || el.closest('[title]') !== null && el.closest('[title]') !== el || !el.isConnected) continue;
    if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 2) { const s = el.textContent.trim(); if (s && s.length > 8) el.title = s; } } };
  new MutationObserver(() => { if (!t) t = setTimeout(mirar, 400); }).observe(raiz, { childList: true, subtree: true });
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => { if (!t) t = setTimeout(mirar, 400); }).observe(raiz);
}

// Revisión 44 (§2.3): fechas con el formato único de la app: «2-oct» y «2-oct, 17:34» (nunca «2 oct» ni «sept»).
const _MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const fDiaRO = iso => fechaCortaRO(FECHAS_RO.dia(iso));
const fDiaHoraRO = iso => { const dia = FECHAS_RO.dia(iso), hora = FECHAS_RO.hora(iso); return dia ? `${fechaCortaRO(dia)}${hora ? `, ${hora}` : ''}` : '—'; };

const ID = 'agenda';
/** 248 · Sólo identidades explícitas del feed autorizado; hora/título/Zoom no prueban una copia. */
function prepararAgendaDuplicados248(eventos) {
  const opaco=v=>typeof v==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}$/.test(v);
  const fuentes=['bookings','ghl','crm','calendar','zoom'];
  const fecha = v => !!FECHAS_RO.instante(v);
  const rango=e=>opaco(e?.persona_id)&&fecha(e.inicio)&&fecha(e.fin)&&FECHAS_RO.horasDesde(e.inicio,e.fin)>0&&!e.todo_el_dia?JSON.stringify([e.persona_id,e.inicio,e.fin]):null;
  const clave=e=>{
    if(e.referencia_reunion!==undefined&&e.referencia_reunion!==null)return opaco(e.referencia_reunion)?'ref:'+e.referencia_reunion:null;
    const i=e.identidad_fuente;
    // El mismo proveedor/evento es fuerte; su ID no se compara entre proveedores distintos.
    if(i&&i.fuente===e.fuente&&i.ventana_confirmada===true&&opaco(i.source_event_id)&&fecha(i.inicio_utc)&&fecha(i.fin_utc)
      &&/(?:Z|[+-]\d{2}:\d{2})$/.test(e.inicio)&&/(?:Z|[+-]\d{2}:\d{2})$/.test(e.fin)
      &&+FECHAS_RO.instante(i.inicio_utc)===+FECHAS_RO.instante(e.inicio)&&+FECHAS_RO.instante(i.fin_utc)===+FECHAS_RO.instante(e.fin))
      return 'source:'+i.fuente+':'+i.source_event_id;
    return null;
  };
  const copia=(Array.isArray(eventos)?eventos:[]).map(e=>({...e}));
  const grupos=new Map();let retirados=0;
  for(const e of copia){const r=rango(e);if(!r||!fuentes.includes(e.fuente)||!opaco(e.id))continue;const k=clave(e);if(!k)continue;const key=r+'|'+k;const g=grupos.get(key)||[];g.push(e);grupos.set(key,g);}
  const eliminar=new Set();
  for(const g of grupos.values()){
    if(g.length<2)continue;
    const clientes=new Set(g.map(e=>e.cliente_ref).filter(x=>x!=null));
    const participantes=new Set(g.filter(e=>e.identidad_confirmada===true).map(e=>e.participante_ref).filter(x=>x!=null));
    const estados=new Set(g.map(e=>e.estado_cita).filter(x=>x!=null));
    const propietarios=new Set(g.map(e=>e.identidad_fuente?.source_owner_id).filter(x=>x!=null));
    const celebradas=new Set(g.map(e=>e.celebrada).filter(x=>typeof x==='boolean'));
    const salas=new Set(g.flatMap(enlacesZoom));
    if(clientes.size>1||participantes.size>1||estados.size>1||propietarios.size>1||celebradas.size>1||salas.size>1||g.some(e=>e.zoom_privado_disponible===true))continue;
    // Una referencia compartida con dos reservas en la misma fuente sigue siendo ambigua.
    if(g[0].referencia_reunion&&new Set(g.map(e=>e.fuente)).size!==g.length)continue;
    g.sort((a,b)=>fuentes.indexOf(a.fuente)-fuentes.indexOf(b.fuente));const principal=g[0];
    principal.origenes=g.flatMap(e=>[{fuente:e.fuente,id:e.id},...(Array.isArray(e.origenes)?e.origenes:[])]);
    principal.atajos=g.flatMap(e=>atajosDe(e));
    principal.tambien_en=[...new Set([...g.slice(1).map(e=>e.fuente),...g.flatMap(e=>Array.isArray(e.tambien_en)?e.tambien_en:[])])].filter(x=>x!==principal.fuente);
    if(celebradas.has(true))principal.celebrada=true;
    for(const campo of ['join_url','zoom_url','enlace_zoom'])for(const e of g)if(e[campo]&&!principal[campo])principal[campo]=e[campo];
    principal.consolidacion248='Identidad explícita y horario coincidentes; fuentes conservadas';
    for(const e of g.slice(1)){eliminar.add(e);retirados++;}
  }
  const visibles=copia.filter(e=>!eliminar.has(e)),slots=new Map();
  for(const e of visibles){const r=rango(e);if(!r||!fuentes.includes(e.fuente)||!['cliente','prospecto'].includes(e.tipo))continue;const g=slots.get(r)||[];g.push(e);slots.set(r,g);}
  for(const g of slots.values()){
    if(g.length<2||new Set(g.map(e=>e.fuente)).size<2)continue;
    const clientes=new Set(g.map(e=>e.cliente_ref).filter(x=>x!=null));if(clientes.size>1)continue;
    const referencias=new Set(g.map(e=>e.referencia_reunion).filter(opaco));
    const participantes=new Set(g.filter(e=>e.identidad_confirmada===true).map(e=>e.participante_ref).filter(opaco));
    if(referencias.size>1||participantes.size>1)continue;
    for(const e of g)e.coincidencia248='Otro registro a la misma hora; contrastar si es la misma cita. Se conservan ambos.';
  }
  return {eventos:visibles,retirados};
}
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const DIAS_C = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const TIPO = {
  cliente: { texto: 'Cliente', icono: 'maletin', estado: 'azul' },
  prospecto: { texto: 'Lead', icono: 'target', estado: 'gris' },
  interna: { texto: 'Interna', icono: 'eq', estado: 'gris' },
  fuera: { texto: 'De fuera', icono: 'mundo_web', estado: 'gris' },
  evento: { texto: 'Evento', icono: 'cal', estado: 'gris' },
};
// Calendar sin contacto comercial acreditado no es automáticamente un lead.
function normalizarTipoAgenda(e) {
  if (e?.fuente === 'calendar' && e.tipo === 'prospecto' && e.tipo_confirmado !== true)
    return { ...e, tipo: 'evento' };
  return e;
}
const FUENTE = {
  crm: { texto: 'Zoho', icono: 'cal', abrir: 'Abrir en Zoho CRM' },
  ghl: { texto: 'GoHighLevel', icono: 'base', abrir: 'Abrir en GHL' },
  zoom: { texto: 'Zoom', icono: 'video', abrir: 'Ver grabación' },
  bookings: { texto: 'Bookings', icono: 'cal', abrir: 'Abrir en Bookings' },
  calendar: { texto: 'Zoho Calendar', icono: 'cal', abrir: 'Abrir en Zoho Calendar' },
};
// Atajos «Abrir en…» de cada cita (formatos del 26, parte C): el sitio exacto en la herramienta de origen.
const ATAJO = {
  ghl: { texto: 'Contacto en GHL', icono: 'base' },
  ghl_calendario: { texto: 'Calendario en GHL', icono: 'cal' },
  crm: { texto: 'Evento en Zoho CRM', icono: 'cal' },
  crm_contacto: { texto: 'Contacto en Zoho CRM', icono: 'persona' },
  bookings: { texto: 'Zoho Bookings', icono: 'cal' },
  calendar: { texto: 'Zoho Calendar', icono: 'cal' },
  zoom: { texto: 'Grabación de Zoom', icono: 'video' },
};
function urlSegura(valor) {
  if(typeof valor!=='string'||valor.length>8192||/[\x00-\x20\x7f]/.test(valor))return null;
  try { const u = new URL(valor); return u.protocol === 'https:' && !u.username && !u.password ? u.href : null; } catch { return null; }
}
const atajosDe = e => (Array.isArray(e.atajos) ? e.atajos : (e.enlace ? [{ h: e.fuente, url: e.enlace }] : [])).filter(a => a && urlSegura(a.url)).map(a => ({ ...a, url: urlSegura(a.url) }));
function enlacesZoom(e) {
  const candidatos = [e.join_url, e.zoom_url, e.enlace_zoom, ...atajosDe(e).map(a => a.url)];
  return [...new Set(candidatos.map(urlSegura).filter(valor => {
    if (!valor) return false;
    const u = new URL(valor);
    return (u.hostname === 'zoom.us' || u.hostname.endsWith('.zoom.us')) && (!u.port || u.port === '443')
      && /^\/(?:j|my|join|wc\/join)\/[A-Za-z0-9_.-]+\/?$/.test(u.pathname)
      && ![...u.searchParams.keys()].some(k=>/^(?:zak|token|access_token|authorization)$/i.test(k));
  }))];
}
function enlaceZoom(e) { const enlaces=enlacesZoom(e);return enlaces.length===1?enlaces[0]:null; }
function salaPrivadaAgenda(ctx,e) {
  return e.zoom_privado_disponible===true && ctx.real?.id==='tomas' && ctx.persona?.id==='tomas'
    && ctx.real.puestos?.includes('direccion') && ctx.persona.puestos?.includes('direccion') && e.persona_id==='tomas'
    && typeof e.id==='string' && /^[A-Za-z0-9_-]{1,200}$/.test(e.id);
}
function cargarEstilosAgenda() {
  if (!document.getElementById('ro-agenda-css')) document.head.append(h('link', { id: 'ro-agenda-css', rel: 'stylesheet', href: './modulos/agenda.css' }));
}
/** En rojo = la verdad única (gravedad «crítico» y su motivo); si no hay verdad cargada, lo que trae el fichero. */
const enRojo = (S, e) => {
  if (!e.cliente_ref) return null;
  const v = S.ctx.verdad?.(e.cliente_ref);
  if (v) return v.gravedad === 'critico' ? [v.motivo || (v.motivos || [])[0] || 'Cliente en crítico'] : null;
  return e.en_rojo?.length ? e.en_rojo : null;
};
const H_INI = 8, H_FIN = 20, PX_H = 46;     // rejilla de la semana: de 8:00 a 20:00


// N6 (2-oct): sin hoja propia. Clases comunes (bt, chips-f, pestanas, panel, tiles, av, ico-c, chip, selcli, menu-flot)
// y estilos en línea que solo usan tokens. Lo que hacía @media lo decide ANCHO al pintar (y se repinta al cambiar de ancho).
const ANCHO = {
  estrecho: () => matchMedia('(max-width: 860px)').matches,
  movil: () => matchMedia('(max-width: 640px)').matches,
};
let oyenteAncho = null;
function vigilarAncho(raiz, S) {
  if (oyenteAncho) oyenteAncho.quitar();
  const mqs = [matchMedia('(max-width: 860px)'), matchMedia('(max-width: 640px)')];
  const fn = () => { if (!raiz.isConnected) return oyenteAncho?.quitar(); S.pintar(); };
  mqs.forEach(m => m.addEventListener('change', fn));
  oyenteAncho = { quitar: () => { mqs.forEach(m => m.removeEventListener('change', fn)); oyenteAncho = null; } };
}
const EST = {
  meta: { font: 'var(--t-meta)', color: 'var(--dim)' },
  eyebrow: { font: 'var(--t-eyebrow)', textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--dim)' },
  conIco: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)' },
  sep: { borderTop: 'var(--borde-suave)' },
};


// ===================================================================== fechas
const pad = n => String(n).padStart(2, '0');
const isoDia = d => Number.isFinite(+d) ? d.toISOString().slice(0,10) : null;
const diaDeclaradoRO = s => FECHAS_RO.dia(s) || (typeof s === 'string' && /^\d{4}-\d{2}-\d{2}[ T]/.test(s) ? FECHAS_RO.fechaCivil(s.slice(0,10)) : null);
const aFecha = s => { const dia = diaDeclaradoRO(s); return dia ? new Date(`${dia}T12:00:00Z`) : new Date(NaN); };
function relojMadrid(ahora = new Date()) {
  const dia = FECHAS_RO.dia(ahora), hm = FECHAS_RO.hora(ahora);
  return { dia, minutos: hm ? +hm.slice(0,2) * 60 + +hm.slice(3) : null };
}
const hoyMadrid = () => relojMadrid().dia;
function intervaloCita230(e) {
  const inicio=instanteAgenda175(e?.inicio),fin=instanteAgenda175(e?.fin);
  return {inicio,fin:inicio&&fin&&fin.ms>inicio.ms?fin:null};
}
function estadoTemporal(e, hoy, ahoraMin, instanteAhora = null) {
  if (e.todo_el_dia) return 'todo_el_dia';
  const {inicio,fin}=intervaloCita230(e);
  if(!inicio||!FECHAS_RO.fechaCivil(hoy)||!Number.isFinite(ahoraMin)||ahoraMin<0||ahoraMin>=1440)return 'sin_hora';
  const ahora = FECHAS_RO.instante(instanteAhora ?? `${hoy} ${hhmm(ahoraMin)}`);
  if (!ahora) return 'sin_hora';
  if (FECHAS_RO.horasHasta(new Date(inicio.ms), ahora) > 0) return 'proxima';
  if(!fin)return 'fin_desconocido';
  if(FECHAS_RO.horasHasta(new Date(fin.ms), ahora) <= 0)return 'pasada';
  return 'ahora';
}
const minutos = s => instanteAgenda175(s)?.min ?? null;
const aMin = t => { const m = /(\d{1,2}):(\d{2})/.exec(String(t || '')); return m ? +m[1] * 60 + +m[2] : null; };
const hhmm = m => `${pad(Math.floor(m / 60))}:${pad(m % 60)}`;
const sumarDias = (iso, n) => { const d = aFecha(iso); d.setUTCDate(d.getUTCDate() + n); return isoDia(d); };
const lunesDe = iso => { const d = aFecha(iso); const w = (d.getUTCDay() + 6) % 7; d.setUTCDate(d.getUTCDate() - w); return isoDia(d); };
const diaLargo = iso => { const d = aFecha(iso); return `${DIAS[d.getUTCDay()]} ${d.getUTCDate()} de ${MESES[d.getUTCMonth()]}`; };
const diaCorto = iso => { const d = aFecha(iso); return `${DIAS_C[d.getUTCDay()]} ${d.getUTCDate()} ${MESES[d.getUTCMonth()]}`; };
const durTxt = m => typeof m !== 'number' || !Number.isFinite(m) || m < 0 ? '—' : m < 60 ? `${m} min` : `${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60}` : ''}`;

/** Huecos libres de un día dentro de la jornada (L-V, 9-18), desde «ahora» si es hoy. */
function huecosDia(evs, iso, jornada, desdeMin = 0) {
  if (!FECHAS_RO.fechaCivil(iso) || !Number.isFinite(desdeMin) || evs.some(e => !FECHAS_RO.dia(e.inicio))) return null;
  const d = aFecha(iso).getUTCDay();
  if (!(jornada.dias || [0, 1, 2, 3, 4]).includes((d + 6) % 7)) return [];
  const ini = Math.max(aMin(jornada.inicio) ?? 540, desdeMin), fin = aMin(jornada.fin) ?? 1080;
  if (evs.some(e => !e.todo_el_dia && FECHAS_RO.dia(e.inicio) === iso && (!intervaloCita230(e).inicio || !intervaloCita230(e).fin))) return null;
  const ocup = [];
  for (const e of evs.filter(e => !e.todo_el_dia)) {
    const {inicio,fin:final} = intervaloCita230(e);
    if (!inicio || !final || inicio.dia > iso || final.dia < iso) continue;
    const a = inicio.dia === iso ? inicio.min : 0, b = final.dia === iso ? final.min : 1440;
    if (b <= a && inicio.dia === iso) return null; // eje civil ambiguo: no certificar huecos.
    ocup.push([a, Math.max(b, a + 15)]);
  }
  ocup.sort((a,b) => a[0] - b[0]);
  const out = []; let t = Math.ceil(ini / 15) * 15;
  for (const [a, b] of ocup) {
    if (a > t && a - t >= 15) out.push([t, Math.min(a, fin)]);
    t = Math.max(t, b);
    if (t >= fin) break;
  }
  if (fin - t >= 15) out.push([t, fin]);
  return out.filter(([a, b]) => b > a);
}


// ===================================================================== módulo
export default {
  id: ID,
  titulo: 'Agenda',
  grupo: 'Hoy',
  puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo' },
  async render(cont, ctx) {
    cargarEstilosAgenda();
    plegarConsejo(cont);   // ronda U (#1): el consejo de la carcasa, en una línea
    vigilarCortes(cont);
    let D;
    try { D = await ctx.datosModulo('agenda/agenda'); }
    catch (e) {
      if (!cont.isConnected || (ctx.vigente && !ctx.vigente())) return;
      const no = e?.status === 403;
      cont.append(vacio({ icono: no ? 'candado' : 'cal', tono: 'aviso', borde: true,
        titulo: no ? 'No puedo leer tu agenda ahora mismo' : 'La agenda no ha cargado',
        texto: no ? 'Recarga en un minuto. Si sigue igual, avisa a Tomás: el servidor no está dejando leer la agenda.' : 'Falta preparar los datos de la agenda de hoy. Ya está avisado quien la mantiene.',
        quien: 'Tomás', accion: h('button', { type: 'button', class: 'bt', on: { click: () => location.reload() } }, icono('recargar'), 'Recargar') }));
      return;
    }
    if (!cont.isConnected || (ctx.vigente && !ctx.vigente())) return;
    const yo = ctx.persona.id;
    const personas = new Map((ctx.datos.personas || []).map(p => [p.id, p]));
    const todo = ctx.nivel === 'todo';
    // Lo que el servidor manda ya viene recortado; la pantalla además se ciñe a la regla de Tomás:
    // cada uno la suya, los jefes su equipo, Mili y Tomás todos (RRHH recibe más del servidor: ver _ESTADO_agenda.md).
    const equipo = new Set([yo, ...[...personas.values()].filter(p => p.jefe === yo).map(p => p.id)]);
    const autorizados = (D.eventos || []).filter(e => e && Number.isFinite(+aFecha(e.inicio)) && (todo || equipo.has(e.persona_id)));
    const evs = ordenarEventosRO(prepararAgendaDuplicados248(autorizados).eventos.map(normalizarTipoAgenda));
    const ids = [...new Set([yo, ...evs.map(e => e.persona_id)])];
    const cuenta = id => evs.filter(e => e.persona_id === id && FECHAS_RO.dia(e.inicio) === hoyMadrid()).length;
    const S = {
      D, evs, personas, yo, ids, todo, ctx,
      quien: ids.includes(sessionStorage.getItem?.('ro.agenda.quien')) ? sessionStorage.getItem('ro.agenda.quien') : yo,
      filtro: '', semana: lunesDe(hoyMadrid()), dia: hoyMadrid(), nombres: {},
    };
    if (!ids.includes(S.quien)) S.quien = yo;
    S.cuenta = cuenta;
    const raiz = h('div', { class: 'ro-agenda', style: { minWidth: '0', maxWidth: '100%', display: 'grid', gap: 'var(--s-5)', gridTemplateColumns: 'minmax(0, 1fr)' } });
    cont.append(raiz);
    S.pintar = (p) => { if (!raiz.isConnected || (ctx.vigente && !ctx.vigente())) return; const act = raiz.querySelector('.pestanas-caja')?.activa?.(); raiz.replaceChildren(); pintar(raiz, S, p || act); };
    vigilarAncho(raiz, S);
    pintar(raiz, S);
  },
};

const nombreP = (S, id) => S.ctx.nombre ? S.ctx.nombre(id) : (S.personas.get(id)?.alias || S.personas.get(id)?.nombre || id);

/** De quién es la agenda: el selector de persona común (ronda 10), con buscador y avatares, en lugar de 15 chips. */
function selectorAgenda(S) {
  const orden = S.ids.slice().sort((a, b) => (a === S.yo ? -1 : b === S.yo ? 1 : nombreP(S, a).localeCompare(nombreP(S, b))));
  const lista = orden.map(id => ({ id, nombre: nombreP(S, id) }));
  return selectorPersona({
    personas: lista, actual: S.quien, etiqueta: 'Cambiar de persona',
    detalle: p => { const n = S.cuenta(p.id); return `${p.id === S.yo ? 'Mi agenda · ' : ''}${n ? `${fmt.num(n)} ${n === 1 ? 'cita' : 'citas'} hoy` : 'sin citas hoy'}`; },
    insignia: p => (S.evs.some(e => e.persona_id === p.id && FECHAS_RO.dia(e.inicio) === hoyMadrid() && enRojo(S, e)) ? chipEstado('rojo', 'Cliente crítico') : null),
    alElegir: p => { S.quien = p.id; S.nombres = {}; try { sessionStorage.setItem('ro.agenda.quien', p.id); } catch { /* */ } S.pintar(); },
  });
}

function pintar(raiz, S, pestanaInicial) {
  const { ctx } = S;
  S.ahora = new Date();
  const ahoraMadrid = relojMadrid(S.ahora), hoy = ahoraMadrid.dia, ahoraMin = ahoraMadrid.minutos;
  const meta = S.D._meta || {};
  const mias = ordenarEventosRO(S.evs.filter(e => e.persona_id === S.quien));
  const filtrar = l => S.filtro ? l.filter(e => e.tipo === S.filtro) : l;
  const deHoy = mias.filter(e => FECHAS_RO.dia(e.inicio) === hoy);
  const proxima = mias.find(e => FECHAS_RO.horasHasta(e.inicio, S.ahora || new Date()) !== null && FECHAS_RO.horasHasta(e.inicio, S.ahora || new Date()) >= 0);
  const rojosHoy = deHoy.filter(e => enRojo(S, e));
  const libresHoy = totalHuecosRO(huecosDia(mias, hoy, meta.jornada || {}, ahoraMin));
  const semIni = lunesDe(hoy), semFin = sumarDias(semIni, 6);
  const deSemana = mias.filter(e => FECHAS_RO.dia(e.inicio) >= semIni && FECHAS_RO.dia(e.inicio) <= semFin);
  const esMia = S.quien === S.yo;
  const quienTxt = esMia ? 'tu' : `la de ${nombreP(S, S.quien)}`;
  ctx.titulo('Agenda', esMia ? 'Tus citas con clientes y leads y tus reuniones' : `Agenda de ${nombreP(S, S.quien)}`);

  // ---------- cabecera: de quién es la agenda + frescura
  const fu = (meta.fuentes || []).filter(f => ['crm', 'ghl', 'bookings', 'calendar', 'zoom'].includes(f.id));
  raiz.append(h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-3) var(--s-4)', alignItems: 'center', justifyContent: 'space-between' } },
    S.ids.length > 1 ? selectorAgenda(S) : h('span', {}),
    h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-1) var(--s-3)', alignItems: 'center' } }, fu.map(f => frescura({ fuente: f.fuente.split(' · ')[0], fecha: f.hora, estado: f.estado === 'bien' ? 'ok' : 'retraso' })))));

  // El calendario tiene prioridad; cifras compactas, sin tarjetas que lo desplacen.
  raiz.append(h('div', { class: 'agenda-resumen', 'aria-label': 'Resumen de la agenda' },
    h('button', { type: 'button', class: 'bt', on: { click: () => { S.dia = hoy; S.pintar('hoy'); } } }, `${deHoy.length} citas hoy`),
    proxima ? h('span', {}, `Próxima: ${FECHAS_RO.dia(proxima.inicio) === hoy ? 'hoy' : diaCorto(proxima.inicio)} ${FECHAS_RO.hora(proxima.inicio)}`) : h('span', {}, 'Sin próximas citas en los datos leídos'),
    rojosHoy.length ? h('span', { class: 'chip rojo' }, `${rojosHoy.length} con cliente crítico hoy`) : null));

  // ---------- filtros por tipo (se aplican a Hoy y Semana)
  const base = mias.filter(e => FECHAS_RO.dia(e.inicio) >= sumarDias(hoy, -14));
  const chips = chipsFiltro({
    etiqueta: 'Con quién', clave: 'agenda-tipo', valor: S.filtro,
    opciones: [{ valor: '', texto: 'Todas', cuenta: base.length },
      ...['cliente', 'prospecto', 'interna', 'evento', 'fuera'].map(t => ({ valor: t, texto: TIPO[t].texto, icono: TIPO[t].icono, cuenta: base.filter(e => e.tipo === t).length }))
        .filter(o => o.cuenta)],
    alCambiar: v => { S.filtro = v; S.pintar(); },
  });
  S.filtro = chips.valor();

  const pests = [
    { id: 'hoy', texto: 'Día', icono: 'hoy', cuenta: deHoy.length, cuentaEstado: rojosHoy.length ? 'rojo' : null },
    { id: 'semana', texto: 'Semana', icono: 'cal' },
    { id: 'huecos', texto: 'Huecos libres', icono: 'ok' },
    ...(S.ids.length > 1 ? [{ id: 'equipo', texto: S.todo ? 'Todo el equipo' : 'Mi equipo', icono: 'eq' }] : []),
    { id: 'fuentes', texto: 'Fuentes', icono: 'plug', cuenta: (meta.fuentes || []).filter(f => f.estado !== 'bien').length || null },
  ];
  raiz.append(chips, pestanas({
    pestanas: pests, activa: pestanaInicial || 'hoy', clave: pestanaInicial ? null : 'agenda', etiqueta: 'Vistas de la agenda',
    pintar: (id, zona) => {
      if (id === 'hoy') zona.append(vistaDia(S, filtrar(mias), S.dia || hoy, ahoraMin, quienTxt));
      if (id === 'semana') zona.append(vistaSemana(S, filtrar(mias), hoy, ahoraMin));
      if (id === 'huecos') zona.append(vistaHuecos(S, mias, hoy, ahoraMin, meta));
      if (id === 'equipo') zona.append(vistaEquipo(S, hoy, ahoraMin, meta));
      if (id === 'fuentes') zona.append(vistaFuentes(S, meta));
    },
  }));
  // El aviso de la fuente a medias va al pie: arriba, lo de cada día (orden por frecuencia).
  if ((meta.fuentes || []).some(f => ['bookings', 'calendar'].includes(f.id) && f.estado !== 'bien')) {
    raiz.append(avisoParcial('Zoho Bookings o Zoho Calendar no han cargado en la última lectura: puede faltar alguna cita. El detalle, en la pestaña «Fuentes».', { tipo: 'parcial', titulo: 'Agenda a medias' }));
  }
}

// ===================================================================== una cita
/** Acciones de una cita: «Ficha del cliente» (la que más se usa), la grabación como ▶ y el resto dentro de «Abrir ▾». */
function accionesCita(S, e, visible, f) {
  const firma=()=>JSON.stringify([S.ctx.real?.id,S.ctx.persona?.id,S.ctx.real?.puestos||[],S.ctx.persona?.puestos||[]]);
  const identidad=firma();
  const privado = salaPrivadaAgenda(S.ctx,e)
    ? `/api/agenda/zoom?evento_id=${encodeURIComponent(e.id)}&yo=${encodeURIComponent(S.ctx.real.id)}` : null;
  const vigente=()=> (!S.ctx.vigente||S.ctx.vigente())&&identidad===firma()&&(!privado||salaPrivadaAgenda(S.ctx,e));
  const atajos = atajosDe(e), entrar = privado || enlaceZoom(e);
  const grabacion = atajos.find(a => { try { const u = new URL(a.url); return a.h === 'zoom' && (u.hostname === 'zoom.us' || u.hostname.endsWith('.zoom.us')) && (!u.port||u.port==='443') && /\/rec(?:\/|$)/.test(u.pathname) && ![...u.searchParams.keys()].some(k=>/^(?:zak|token|access_token|authorization)$/i.test(k)); } catch { return false; } });
  // No ofrecer enlaces de host/credenciales o salas ambiguas escondidos en el menú secundario.
  const resto = atajos.filter(a => {if(a===grabacion||a.url===entrar)return false;try{const u=new URL(a.url);return !(u.hostname==='zoom.us'||u.hostname.endsWith('.zoom.us'));}catch{return false;}});
  const proximamente = String(e.inicio || '').slice(0, 10) >= hoyMadrid() && !e.celebrada;
  return h('div', { class: 'agenda-acciones', style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)', justifyContent: 'flex-end', alignItems: 'center' } },
    entrar ? h('a', { class: 'bt pri', href: entrar, target: '_blank', rel: 'noopener noreferrer', 'aria-label': `${privado?'Abrir mi sala de Zoom':'Entrar en Zoom'}: ${tituloBonito(e.titulo)}`, 'data-uso': 'abrir-zoom',on:{click:ev=>{
      if(!vigente())ev.preventDefault();
    }} }, icono('video'), privado?'Abrir mi sala de Zoom':'Entrar en Zoom')
      : proximamente ? h('span', { class: 'agenda-sin-zoom' }, enlacesZoom(e).length>1?'Varios enlaces de Zoom: falta confirmar la sala':'Enlace de Zoom no disponible') : null,
    visible ? h('a', { class: 'bt', href: `#/ficha/${e.cliente_ref}/reunion`,on:{click:ev=>{if(!vigente())ev.preventDefault();}} }, icono('maletin'), 'Preparar') : null,
    e.cliente_ref && !visible && e.tipo === 'cliente' ? h('span', { style: EST.meta, title: 'Detalle reservado a quien lleva este cliente' }, icono('candado', { clase: 's' })) : null,
    grabacion ? h('a', { class: 'bt', href: grabacion.url, target: '_blank', rel: 'noopener noreferrer','aria-label':`Ver grabación: ${tituloBonito(e.titulo)}`,on:{click:ev=>{if(!vigente())ev.preventDefault();}} }, icono('video'), 'Ver grabación') : null,
    resto.length ? menuAbrir(resto.map(a => ({ texto: ATAJO[a.h]?.texto || f.abrir, icono: ATAJO[a.h]?.icono || 'ext', href: a.url })),vigente) : null);
}

/** «Abrir ▾» con los enlaces de la cita: el menuMas() común (ronda 10); cada enlace se abre en otra pestaña. */
function menuAbrir(items,vigente=()=>true) {
  return menuMas({ texto: 'Abrir', etiqueta: 'Abrir la cita en sus herramientas',
    items: items.map(it => ({ texto: it.texto, icono: it.icono, alPulsar: () => {if(vigente())window.open(it.href, '_blank', 'noopener');} })) });
}

function tarjeta(S, e, { ahoraMin, hoy, conDia = false } = {}) {
  const { ctx } = S;
  const t = TIPO[e.tipo] || TIPO.fuera;
  const intervalo=intervaloCita230(e);
  const temporal = estadoTemporal(e, hoy, ahoraMin, S.ahora || null);
  const pasada = temporal === 'pasada', ahora = temporal === 'ahora';
  const visible = e.cliente_ref && ctx.clientesVisibles.some(c => c.id === e.cliente_ref);
  const titulo = tituloBonito(S.nombres[e.id] || e.titulo);
  const f = FUENTE[e.fuente] || {texto:'Fuente por confirmar',icono:'cal',abrir:'Abrir enlace de origen'};
  const rojo = enRojo(S, e);
  const movil = ANCHO.movil();
  const acc = accionesCita(S, e, visible, f);
  if (movil) { acc.style.gridColumn = '2'; acc.style.justifyContent = 'flex-start'; }
  const meta1 = (ico, txt, extra = {}) => h('span', { style: EST.conIco, ...extra }, icono(ico, { clase: 's' }), txt);
  return h('div', { style: {
    display: 'grid', gridTemplateColumns: movil ? '56px minmax(0, 1fr)' : '72px minmax(0, 1fr) auto', gap: 'var(--s-2) var(--s-4)', alignItems: 'start',
    padding: 'var(--s-3) var(--s-5)', borderLeft: `3px solid ${rojo ? 'var(--bad)' : e.tipo === 'cliente' ? 'var(--accent)' : 'transparent'}`,
    // barrido v1: la cita pasada ya no se apaga con opacidad (bajaba el contraste a 2,6:1); lleva fondo gris suave
    background: rojo ? 'linear-gradient(90deg, var(--bad-soft), transparent 55%)' : ahora ? 'var(--accent-soft)' : pasada ? 'var(--card-2)' : '' } },
    h('div', { style: { display: 'grid', gap: 'var(--s-1)', font: 'var(--t-h2)', fontVariantNumeric: 'tabular-nums', color: 'var(--ink)' } },
      e.todo_el_dia ? 'Todo el día' : intervalo.inicio ? hhmm(intervalo.inicio.min) : 'Hora por confirmar',
      h('span', { style: EST.meta }, conDia && intervalo.inicio ? diaCorto(intervalo.inicio.dia) : (!e.todo_el_dia && intervalo.fin ? durTxt((intervalo.fin.ms-intervalo.inicio.ms)/60000) : '')),
      !e.todo_el_dia && intervalo.inicio && !intervalo.fin ? h('small',{style:EST.meta},e.fin?'Fin por contrastar':'Sin duración registrada') : null),
    h('div', { style: { display: 'grid', gap: 'var(--s-2)', minWidth: '0' } },
      h('b', { style: { font: 'var(--t-h3)', overflowWrap: 'anywhere' } }, titulo),
      h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-1) var(--s-3)', alignItems: 'center', ...EST.meta, color: 'var(--mid)', minWidth: '0' } },
        chipEstado(t.estado, t.texto),
        rojo ? h('span', { class: 'chip rojo sin-punto', style: { overflowWrap: 'anywhere', whiteSpace: 'normal' } }, icono('fire', { clase: 's' }), `Crítico · ${rojo.join(' · ')}`) : null,
        e.cliente_nombre && e.tipo === 'cliente' ? meta1('maletin', e.cliente_nombre) : null,
        e.con_quien_m && !S.nombres[e.id] ? meta1('persona', e.con_quien_m, { title: e.nombre_completo ? 'Es tu cita: ves el nombre completo (queda en el rastro)' : 'Lead con iniciales: el nombre solo lo ve el dueño de la cita' }) : null,
        e.calendario ? meta1('cal', e.calendario) : null,
        e.estado_cita && e.estado_cita !== 'confirmed' ? meta1('info', { new: 'Sin confirmar', showed: 'Se presentó', noshow: 'No se presentó', booked: 'Reservada', sin_marcar: 'Sin marcar si vino' }[e.estado_cita] || e.estado_cita) : null,
        e.agendada_por_ti ? meta1('auricular', 'La agendaste tú') : null,
        e.video && e.fuente !== 'zoom' ? meta1('video', e.video === 'zoom' ? 'Zoom' : 'Google Meet') : null,
        e.con_ro?.length > 1 ? meta1('eq', e.con_ro.join(', ')) : null,
        meta1(f.icono, f.texto, { title: e.origen }),
        e.coincidencia248 ? meta1('info','Coincidencia por contrastar',{title:e.coincidencia248}) : null,
        e.consolidacion248 ? meta1('capas','Fuentes consolidadas',{title:e.consolidacion248}) : null,
        intervalo.fin && intervalo.fin.dia!==intervalo.inicio.dia ? meta1('cal',`Fin ${diaCorto(intervalo.fin.dia)} · ${hhmm(intervalo.fin.min)}`) : null,
        ahora ? chipEstado('azul', 'Ahora') : null)),
    acc);
}

/** Las citas de Zoho Bookings entran al CRM como «<cliente> and <servicio>»: se leen mejor al revés. */
function tituloBonito(t) {
  const m = /^(.+?) and (.+)$/.exec(t || '');
  return m ? `${m[2]} · ${m[1]}` : t;
}

const lineaAhora = txt => h('div', { 'aria-label': 'Ahora', style: { display: 'flex', alignItems: 'center', gap: 'var(--s-2)', padding: '0 var(--s-5)', font: 'var(--t-meta)', fontWeight: '700', color: 'var(--bad-ink)', fontVariantNumeric: 'tabular-nums' } },
  txt, h('span', { style: { flex: '1', height: '2px', background: 'var(--bad)', borderRadius: 'var(--r-full)' } }));
const separadorDia = (izq, der, { esHoy = false, primero = false } = {}) => h('div', { style: { ...EST.eyebrow, color: esHoy ? 'var(--accent)' : 'var(--dim)', padding: 'var(--s-3) var(--s-5) var(--s-1)', borderTop: primero ? '0' : 'var(--borde-suave)', display: 'flex', justifyContent: 'space-between', gap: 'var(--s-2)' } }, h('span', {}, izq), der ? h('span', {}, der) : null);
/** Lista de citas con filete entre una y otra. */
const listaCitas = nodos => { const l = h('div', { style: { display: 'grid' } }); nodos.forEach((n, i) => { if (i && n.style && !n.getAttribute('aria-label') && l.lastChild?.getAttribute?.('aria-label') !== 'Ahora') n.style.borderTop = 'var(--borde-suave)'; l.append(n); }); return l; };

// ===================================================================== Hoy
function vistaDia(S, lista, hoy, ahoraMin, quienTxt) {
  const esHoy = hoy === hoyMadrid();
  const instanteAhora = S.ahora || FECHAS_RO.instante(`${hoy} ${hhmm(ahoraMin)}`);
  const del = ordenarEventosRO(lista.filter(e => FECHAS_RO.dia(e.inicio) === hoy));
  const nav = navegacionDia(S, hoy);
  const caja = panel({ titulo: diaLargo(hoy)[0].toUpperCase() + diaLargo(hoy).slice(1), icono: 'hoy', sub: `Las citas de ${quienTxt === 'tu' ? 'tu' : quienTxt.replace('la de ', 'la agenda de ')} agenda, por hora (Madrid).`, acciones: botonNombres(S, lista) });
  caja.append(nav);
  if (!del.length) {
    const sig = lista.find(e => FECHAS_RO.dia(e.inicio) > hoy);
    caja.append(h('div', { style: { padding: '0 var(--relleno)' } }, vacioLinea(
      (S.filtro ? `No hay citas de tipo «${TIPO[S.filtro]?.texto}». ` : 'No hay citas registradas este día. ') +
      (sig ? `La siguiente: ${diaLargo(sig.inicio)} a las ${FECHAS_RO.hora(sig.inicio)} · ${tituloBonito(S.nombres[sig.id] || sig.titulo)}.` : vacioSinCitas(S)),
      { icono: 'cal', quien: sig ? null : quienArregla(S) })));
  } else {
    const nodos = [];
    let lineaPuesta = false;
    for (const e of del) {
      if (esHoy && !lineaPuesta && FECHAS_RO.horasHasta(e.inicio, instanteAhora) !== null && FECHAS_RO.horasHasta(e.inicio, instanteAhora) > 0) { nodos.push(lineaAhora(hhmm(ahoraMin))); lineaPuesta = true; }
      nodos.push(tarjeta(S, e, { ahoraMin, hoy: hoyMadrid() }));
    }
    if (esHoy && !lineaPuesta) nodos.push(lineaAhora(hhmm(ahoraMin)));
    caja.append(listaCitas(nodos));
  }
  // Mañana, para no llegar en frío
  const man = lista.filter(e => FECHAS_RO.dia(e.inicio) > hoy).slice(0, 6);
  const cont = h('div', { style: { display: 'grid', gap: 'var(--s-4)' } }, caja);
  if (man.length && esHoy) {
    const lst = h('div', { style: { display: 'grid' } });
    let dia = '';
    for (const e of man) {
      if (FECHAS_RO.dia(e.inicio) !== dia) { lst.append(separadorDia(diaLargo(FECHAS_RO.dia(e.inicio)), null, { primero: !dia })); dia = FECHAS_RO.dia(e.inicio); }
      const t = tarjeta(S, e, { ahoraMin, hoy });
      lst.append(t);
    }
    cont.append(panel({ titulo: 'Lo siguiente', icono: 'derecha', sub: 'Las próximas seis citas, para prepararlas con tiempo.' }, lst));
  }
  return cont;
}

function vacioSinCitas(S) {
  const p = S.personas.get(S.quien);
  if ((p?.puestos || []).includes('setters')) return 'Cuando agendes una cita con la etiqueta setter:<tu nombre> en GoHighLevel, saldrá aquí con su hora.';
  return 'No hay próximas citas en los datos leídos. Si tienes una cita que no sale aquí, mira la pestaña «Fuentes».';
}
function quienArregla(S) {
  return (S.D._meta?.fuentes || []).some(f => f.id === 'bookings' && f.estado !== 'bien') ? 'Tomás' : null;
}

/** «Ver nombres»: solo el dueño de la agenda (o dirección); una sola lectura que queda en el rastro. */
function botonNombres(S, lista) {
  const pros = lista.filter(e => e.tipo === 'prospecto' || e.tipo === 'fuera');
  if (!pros.length) return null;
  // El servidor ya manda los nombres completos al dueño de cada cita (ronda 6); el botón solo hace falta si no llegaron.
  if (pros.every(e => e.nombre_completo)) return h('span', { style: { ...EST.meta, ...EST.conIco }, title: 'El servidor te los da porque son tus citas; cada lectura queda en el rastro' }, icono('ojo', { clase: 's' }), 'Nombres completos: son tus citas');
  if (Object.keys(S.nombres).length) return chipEstado('azul', 'Nombres a la vista · queda en el rastro');
  const puede = S.quien === S.yo;   // «solo lo tuyo»: los nombres de los prospectos los abre solo el dueño de la agenda
  if (!puede) return h('span', { style: { ...EST.meta, ...EST.conIco }, title: 'Los nombres de los leads solo los ve el dueño de la agenda' }, icono('candado', { clase: 's' }), 'Leads con iniciales');
  return h('button', { type: 'button', class: 'bt', on: { click: async ev => {
    const boton = ev.currentTarget, persona = S.quien;
    boton.disabled = true;
    try {
      const r = await S.ctx.verDato({ almacen: `agenda/_privado/${S.quien}`, ref: S.quien, campo: 'titulos' });
      if (S.quien !== persona || (S.ctx.vigente && !S.ctx.vigente())) return;
      S.nombres = r.valor || {};
      avisoFlotante('Nombres a la vista. Queda en el rastro.', { icono: 'ojo' });
      S.pintar();
    } catch (e) {
      if (S.quien !== persona || (S.ctx.vigente && !S.ctx.vigente())) return;
      boton.disabled = false;
      avisoFlotante(String(e?.message || 'No se pueden ver los nombres'), { icono: 'candado' });
    }
  } } }, icono('ojo'), 'Ver nombres');
}

// ===================================================================== Semana
function navegacionDia(S, dia) {
  const meta = S.D._meta || {};
  return h('div', { class: 'agenda-nav' },
    h('button', { type: 'button', class: 'bt icono', 'aria-label': 'Día anterior', disabled: dia <= meta.desde || null, on: { click: () => { S.dia = sumarDias(dia, -1); S.pintar('hoy'); } } }, icono('izquierda')),
    h('span', {}, diaCorto(dia)),
    h('button', { type: 'button', class: 'bt icono', 'aria-label': 'Día siguiente', disabled: dia >= meta.hasta || null, on: { click: () => { S.dia = sumarDias(dia, 1); S.pintar('hoy'); } } }, icono('derecha')),
    dia !== hoyMadrid() ? h('button', { type: 'button', class: 'bt', on: { click: () => { S.dia = hoyMadrid(); S.pintar('hoy'); } } }, 'Hoy') : null);
}
//175: intervalos de hora civil Madrid para pintar, nunca horas imputadas/disponibilidad.
function instanteAgenda175(valor) {
  const instante = FECHAS_RO.instante(valor);
  if (!instante) return null;
  const r = relojMadrid(instante);
  return {dia:r.dia,min:r.minutos,serial:Date.parse(r.dia+'T00:00:00Z')/60000+r.minutos,ms:+instante};
}
function layoutSemanaAgenda175(eventos,lunes,jornada={}) {
  const dias=Array.from({length:7},(_,i)=>sumarDias(lunes,i)),por=Object.fromEntries(dias.map(d=>[d,{segmentos:[],anotaciones:[]}])) ,sinFecha=[];
  for(const evento of eventos){
    const inicio=instanteAgenda175(evento.inicio),fin=instanteAgenda175(evento.fin);
    const fecha = diaDeclaradoRO(evento.inicio);
    if(evento.todo_el_dia){
      if(inicio&&fin&&fin.serial>inicio.serial){for(const dia of dias){const base=Date.parse(dia+'T00:00:00Z')/60000;if(Math.min(fin.serial,base+1440)>Math.max(inicio.serial,base))por[dia].anotaciones.push({evento,nota:'Todo el día registrado'+(dia!==inicio.dia?' · continúa desde '+inicio.dia:'')});}}
      else if(por[fecha])por[fecha].anotaciones.push({evento,nota:evento.fin?'Todo el día · fin por contrastar':'Todo el día registrado · sin intervalo de fin'});
      else if(!fecha)sinFecha.push({evento,nota:'Fecha por contrastar'});continue;
    }
    if(!inicio){if(por[fecha])por[fecha].anotaciones.push({evento,nota:'Hora por contrastar'});else if(!fecha)sinFecha.push({evento,nota:'Fecha/hora por contrastar'});continue;}
    const finalValido=fin&&fin.ms>inicio.ms;
    if(!finalValido){if(por[inicio.dia])por[inicio.dia].segmentos.push({evento,inicio_min:inicio.min,fin_min:inicio.min,nota:evento.fin?'Fin por contrastar':'Sin duración registrada',continuacion:false});continue;}
    if (fin.serial <= inicio.serial) { if (por[inicio.dia]) por[inicio.dia].anotaciones.push({evento,nota:`Intervalo real ${Math.round((fin.ms-inicio.ms)/60000)} min · cambio de hora o precisión inferior a un minuto; ver detalle`}); continue; }
    // Recortar en cada frontera civil: no copiar la duración del lunes al martes.
    for(const dia of dias){const base=Date.parse(dia+'T00:00:00Z')/60000,a=Math.max(inicio.serial,base),b=Math.min(fin.serial,base+1440);if(b>a)por[dia].segmentos.push({evento,inicio_min:a-base,fin_min:b-base,nota:[inicio.dia!==dia?'Continúa desde '+inicio.dia:fin.dia!==dia?'Continúa al día siguiente':'',fin.serial-inicio.serial!==(fin.ms-inicio.ms)/60000?`Intervalo real ${Math.round((fin.ms-inicio.ms)/60000)} min; eje de horas civiles`: ''].filter(Boolean).join(' · '),continuacion:inicio.dia!==dia});}
  }
  const segmentos=Object.values(por).flatMap(p=>p.segmentos);
  const ja=typeof jornada.inicio==='string'&&/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(jornada.inicio)?aMin(jornada.inicio):null;
  const jb=typeof jornada.fin==='string'&&/^(?:(?:[01]\d|2[0-3]):[0-5]\d|24:00)$/.test(jornada.fin)?aMin(jornada.fin):null;
  const jvalida=ja!==null&&jb!==null&&ja>=0&&jb<=1440&&jb>ja;
  const comienzos=segmentos.map(s=>s.inicio_min),finales=segmentos.map(s=>s.fin_min);
  if(jvalida){comienzos.push(ja);finales.push(jb);}
  const desde=comienzos.length?Math.floor(Math.min(...comienzos)/60)*60:0,hasta=finales.length?Math.min(1440,Math.max(desde+60,Math.ceil(Math.max(...finales)/60)*60)):1440;
  for(const p of Object.values(por)){
    p.segmentos.sort((a,b)=>a.inicio_min-b.inicio_min||b.fin_min-a.fin_min);
    let grupo=[],extremo=-1;p.bloques=[];
    // 35 minutos a escala 1,2 px/min son 42 px de área visible. Esta
    // separación es sólo visual; los intervalos originales no se modifican.
    const finVisual=s=>Math.max(s.fin_min,s.inicio_min+35);
    const cerrar=()=>{if(!grupo.length)return;const libres=[];for(const s of grupo){let col=libres.findIndex(f=>f<=s.inicio_min);if(col<0)col=libres.length;libres[col]=finVisual(s);s.columna=col;}for(const s of grupo)s.columnas=libres.length;p.bloques.push({segmentos:grupo.slice(),inicio_min:grupo[0].inicio_min,fin_visual:Math.max(...grupo.map(finVisual))});grupo=[];};
    for(const s of p.segmentos){if(s.inicio_min>=extremo){cerrar();extremo=-1;}grupo.push(s);extremo=Math.max(extremo,finVisual(s));}cerrar();
  }
  return {dias,por,sinFecha,desde,hasta,jornada_observada:jvalida,hay_intervalos:segmentos.length>0};
}

//322: agrupar sólo comienzos próximos, nunca toda una cadena de solapes.
// El contador ocupa 35 minutos visuales; el detalle conserva cada intervalo original.
function bloquesVisualesAgenda322(segmentos) {
  const orden=segmentos.slice().sort((a,b)=>a.inicio_min-b.inicio_min||b.fin_min-a.fin_min);
  const bloques=[];
  for(let i=0;i<orden.length;){
    let j=i+1;while(j<orden.length&&orden[j].inicio_min<orden[i].inicio_min+35)j++;
    const grupo=orden.slice(i,j);
    if(grupo.length>2)bloques.push({segmentos:grupo,inicio_min:grupo[0].inicio_min,fin_visual:grupo[0].inicio_min+35,agrupado:true});
    else for(const s of grupo)bloques.push({segmentos:[s],inicio_min:s.inicio_min,fin_visual:Math.max(s.fin_min,s.inicio_min+35),agrupado:false});
    i=j;
  }
  let conectados=[],extremo=-1;
  const cerrar=()=>{if(!conectados.length)return;const libres=[];for(const b of conectados){let col=libres.findIndex(f=>f<=b.inicio_min);if(col<0)col=libres.length;libres[col]=b.fin_visual;b.columna=col;}for(const b of conectados)b.columnas=libres.length;conectados=[];};
  for(const b of bloques){if(b.inicio_min>=extremo){cerrar();extremo=-1;}conectados.push(b);extremo=Math.max(extremo,b.fin_visual);}cerrar();
  return bloques;
}

function vistaSemana(S, lista, hoy, ahoraMin) {
  const meta = S.D._meta || {}, lun = S.semana;
  const dias = Array.from({ length: 7 }, (_, i) => sumarDias(lun, i));
  const horario=layoutSemanaAgenda175(lista,lun,meta.jornada || {});
  const delDia=d=>lista.filter(e=>horario.por[d].segmentos.some(s=>s.evento===e)||horario.por[d].anotaciones.some(a=>a.evento===e));
  const enSem=lista.filter(e=>dias.some(d=>delDia(d).includes(e)));
  const min = lunesDe(meta.desde || hoy), max = lunesDe(meta.hasta || hoy);
  const nav = h('div', { class: 'agenda-nav' },
    h('button', { type: 'button', class: 'bt icono', 'aria-label': 'Semana anterior', disabled: lun <= min || null, on: { click: () => { S.semana = sumarDias(lun, -7); S.pintar('semana'); } } }, icono('izquierda')),
    h('b', {}, `${diaCorto(dias[0])} – ${diaCorto(dias[6])}`),
    h('button', { type: 'button', class: 'bt icono', 'aria-label': 'Semana siguiente', disabled: lun >= max || null, on: { click: () => { S.semana = sumarDias(lun, 7); S.pintar('semana'); } } }, icono('derecha')),
    lun !== lunesDe(hoy) ? h('button', { type: 'button', class: 'bt', on: { click: () => { S.semana = lunesDe(hoy); S.pintar('semana'); } } }, 'Esta semana') : null,
    h('span', { class: 'agenda-nav-count' }, `${enSem.length} citas registradas`));
  const elegido = dias.includes(S.dia) ? S.dia : (dias.includes(hoy) ? hoy : dias[0]);
  S.dia = elegido;
  const strip = h('div', { class: 'agenda-dias', 'aria-label': 'Días de la semana' }, dias.map(d => {
    const dt = aFecha(d), n = delDia(d).length;
    return h('button', { type: 'button', class: `agenda-dia-boton${d === elegido ? ' seleccionado' : ''}${d === hoy ? ' hoy' : ''}`, 'aria-pressed': d === elegido ? 'true' : 'false', 'aria-label': `${diaLargo(d)}: ${n} citas`, on: { click: () => { S.dia = d; S.pintar('semana'); } } },
      h('span', {}, DIAS_C[dt.getUTCDay()]), h('b', {}, dt.getUTCDate()), h('small', {}, n || '—'));
  }));
  const pxMin=1.2,alto=(horario.hasta-horario.desde)*pxMin;
  const botonEvento=(e,etiqueta,style={},dia='')=>h('button',{type:'button',class:`agenda-evento agenda-tipo-${TIPO[e.tipo]?e.tipo:'fuera'}`,style,
    title:`${dia?diaLargo(dia)+' · ':''}${etiqueta}: ${tituloBonito(S.nombres[e.id] || e.titulo)}`,'aria-label':`${dia?diaLargo(dia)+' · ':''}${etiqueta}: ${tituloBonito(S.nombres[e.id] || e.titulo)}. Ver detalle`,on:{click:()=>abrirCita(S,e)}},
    h('b',{},etiqueta),h('span',{},tituloBonito(S.nombres[e.id] || e.titulo)),h('small',{},(TIPO[e.tipo] || TIPO.fuera).texto));
  const abrirBloque=(dia,bloque)=>{
    if(!S.abrirEn?.isConnected||(S.ctx.vigente&&!S.ctx.vigente()))return;
    S.abrirEn.replaceChildren(h('div',{class:'agenda-bloque-detalle'},
      h('h3',{},`${bloque.segmentos.length} citas · ${diaLargo(dia)}`),
      h('p',{class:'sub'},'Agrupadas sólo para leer el calendario. Cada registro conserva su horario, detalle y acceso a Zoom.'),
      bloque.segmentos.map(s=>h('div',{},h('p',{class:'sub'},`${hhmm(s.inicio_min)}${s.fin_min>s.inicio_min?'–'+hhmm(s.fin_min):''}${s.nota?' · '+s.nota:''}`),tarjeta(S,s.evento,{ahoraMin,hoy,conDia:true})))));
    S.abrirEn.scrollIntoView({block:'nearest',behavior:'smooth'});
  };
  const botonesBloque=(dia,bloque)=>{
    if(!bloque.agrupado)return bloque.segmentos.map(s=>botonEvento(s.evento,`${hhmm(s.inicio_min)}${s.fin_min>s.inicio_min?'–'+hhmm(s.fin_min):''}${s.nota?' · '+s.nota:''}`,
      {position:'absolute',top:`${(s.inicio_min-horario.desde)*pxMin}px`,height:`${Math.max(42,(s.fin_min-s.inicio_min)*pxMin)}px`,left:`calc(${bloque.columna/bloque.columnas*100}% + 2px)`,width:`calc(${100/bloque.columnas}% - 4px)`},dia));
    const n=bloque.segmentos.length, hora=hhmm(bloque.inicio_min),titulos=bloque.segmentos.map(s=>tituloBonito(S.nombres[s.evento.id]||s.evento.titulo)).join('; ');
    return h('button',{type:'button',class:'agenda-evento agenda-grupo-visual',
      'aria-label':`${n} citas agrupadas visualmente, ${diaLargo(dia)}, desde ${hora}: ${titulos}. Ver todos los registros`,title:`${diaLargo(dia)} · ${n} citas: ${titulos}`,
      style:{position:'absolute',top:`${(bloque.inicio_min-horario.desde)*pxMin}px`,height:`${Math.max(42,(bloque.fin_visual-bloque.inicio_min)*pxMin)}px`,left:`calc(${bloque.columna/bloque.columnas*100}% + 2px)`,width:`calc(${100/bloque.columnas}% - 4px)`},
      on:{click:()=>abrirBloque(dia,bloque)}},h('b',{},`${n} citas · ${hora}`),h('span',{},'Ver todas'));
  };
  const hayAnotaciones=dias.some(d=>horario.por[d].anotaciones.length>0),filaHoras=hayAnotaciones?'3':'2';
  const grid=h('div',{class:'agenda-semana agenda-horaria','aria-label':'Calendario semanal, de lunes a domingo',style:{gridTemplateRows:`auto ${hayAnotaciones?'auto ':''}${alto+42}px`}},
    h('div',{class:'agenda-eje-cabecera',style:{gridColumn:'1',gridRow:'1'}},'Madrid'),
    dias.map((d,i)=>h('button',{type:'button',class:`agenda-col-titulo${d===hoy?' hoy':''}`,style:{gridColumn:String(i+2),gridRow:'1'},on:{click:()=>{S.dia=d;S.pintar('hoy');}}},diaCorto(d))),
    hayAnotaciones?h('div',{class:'agenda-eje-cabecera',style:{gridColumn:'1',gridRow:'2'}},'Todo el día / sin hora'):null,
    hayAnotaciones?dias.map((d,i)=>h('div',{class:'agenda-todo-dia',style:{gridColumn:String(i+2),gridRow:'2'}},horario.por[d].anotaciones.map(a=>botonEvento(a.evento,a.nota)))):null,
    h('div',{class:'agenda-eje-horas',style:{gridColumn:'1',gridRow:filaHoras,height:`${alto+42}px`}},Array.from({length:Math.floor((horario.hasta-horario.desde)/60)+1},(_,i)=>h('span',{style:{top:`${i*60*pxMin}px`}},hhmm(horario.desde+i*60)))),
    dias.map((d,i)=>h('section',{class:`agenda-columna agenda-franja${d===hoy?' hoy':''}`,'aria-label':diaLargo(d),style:{gridColumn:String(i+2),gridRow:filaHoras,height:`${alto+42}px`,backgroundSize:`100% ${60*pxMin}px`}},
      bloquesVisualesAgenda322(horario.por[d].segmentos).map(b=>botonesBloque(d,b)),
      !horario.por[d].segmentos.length&&!horario.por[d].anotaciones.length?h('small',{class:'agenda-dia-vacio'},'Sin citas registradas'):null)));
  const movil = h('div', { class: 'agenda-detalle-dia' }, h('h3', {}, diaLargo(elegido)),
    delDia(elegido).length ? listaCitas(delDia(elegido).map(e=>h('div',{},FECHAS_RO.dia(e.inicio) !== elegido?h('p',{class:'sub'},`Continúa desde ${FECHAS_RO.dia(e.inicio) || diaDeclaradoRO(e.inicio)} · horas originales en el detalle`):null,tarjeta(S,e,{ahoraMin,hoy})))) : vacioLinea('Sin citas registradas este día.', {icono:'cal'}));
  const detalle = h('div', { 'aria-live': 'polite', class: 'agenda-detalle-evento' });
  S.abrirEn = detalle;
  return panel({ titulo: 'Calendario semanal', icono: 'cal', sub: 'Hora de Madrid · pulsa una cita para ver detalle y acceso a Zoom.', acciones: botonNombres(S, lista) }, nav, strip,h('details',{class:'agenda-horario-ayuda'},h('summary',{},'Cómo leer este calendario'),h('p',{class:'sub agenda-horario-nota'},`Escala ${hhmm(horario.desde)}–${hhmm(horario.hasta)}: ${horario.jornada_observada?'jornada de la fuente ampliada a citas observadas':horario.hay_intervalos?'horas observadas; sin jornada confirmada':'escala diaria de visualización; sin jornada confirmada'}. Tarjetas breves tienen tamaño mínimo visual; no indican duración ni disponibilidad. Más de dos comienzos cercanos se agrupan en un contador compacto: no representa duración ni disponibilidad. Pulsa para ver todos los registros.`)),grid, movil,horario.sinFecha.length?h('details',{},h('summary',{},`${horario.sinFecha.length} registros sin fecha/hora contrastada`),horario.sinFecha.map(a=>botonEvento(a.evento,a.nota))):null, detalle);
}

function abrirCita(S, e) {
  S.ahora = new Date();
  const ahoraMadrid = relojMadrid(S.ahora), hoy = ahoraMadrid.dia, ahoraMin = ahoraMadrid.minutos;
  if (!S.abrirEn || !S.abrirEn.isConnected || (S.ctx.vigente && !S.ctx.vigente())) return;
  S.abrirEn.replaceChildren(h('div', { style: { border: 'var(--borde)', borderRadius: 'var(--r-m)', boxShadow: 'var(--sombra-1)' } }, tarjeta(S, e, { ahoraMin, hoy, conDia: true })));
  S.abrirEn.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

// ===================================================================== Huecos libres
function vistaHuecos(S, mias, hoy, ahoraMin, meta) {
  const jornada = meta.jornada || { inicio: '09:00', fin: '18:00', dias: [0, 1, 2, 3, 4] };
  const dias = [];
  for (let i = 0; dias.length < 7 && i < 14; i++) {
    const d = sumarDias(hoy, i);
    if (!(jornada.dias || []).includes((aFecha(d).getUTCDay() + 6) % 7)) continue;
    if (d > (meta.hasta || d)) break;
    dias.push(d);
  }
  const jorMin = (aMin(jornada.fin) ?? 1080) - (aMin(jornada.inicio) ?? 540);
  const filas = dias.map(d => {
    const hs = huecosDia(mias, d, jornada, d === hoy ? ahoraMin : 0);
    const libres = totalHuecosRO(hs);
    const ocupado = d === hoy || libres === null ? null : Math.max(0, jorMin - libres);
    return { d, hs, libres, ocupado };
  });
  const texto = filas.filter(f => f.hs?.some(([a, b]) => b - a >= 30)).map(f => `${diaCorto(f.d)}: ${f.hs.filter(([a, b]) => b - a >= 30).map(([a, b]) => `${hhmm(a)}-${hhmm(b)}`).join(', ')}`).join('\n');
  const movil = ANCHO.movil();
  const lista = h('div', { style: { display: 'grid' } }, filas.map((f, i) => h('div', { style: { display: 'grid', gridTemplateColumns: movil ? 'minmax(0, 1fr)' : '128px minmax(0, 1fr) auto', gap: 'var(--s-2) var(--s-4)', alignItems: 'center', padding: 'var(--s-3) var(--relleno)', borderTop: i ? 'var(--borde-suave)' : '0' } },
    h('div', { style: { display: 'grid', font: 'var(--t-h3)', fontWeight: '700' } }, f.d === hoy ? 'Hoy' : diaCorto(f.d)[0].toUpperCase() + diaCorto(f.d).slice(1), h('span', { style: EST.meta }, `${durTxt(f.libres)} libres`)),
    f.hs === null ? h('span', { style: EST.meta }, 'Huecos por contrastar: fechas incompletas') : f.hs.length ? h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)' } }, f.hs.map(([a, b]) => h('span', { class: `chip sin-punto ${b - a < 30 ? 'gris' : 'verde'}`, style: { fontVariantNumeric: 'tabular-nums' }, title: durTxt(b - a) }, `${hhmm(a)} – ${hhmm(b)}`)))
      : h('span', { style: EST.meta }, f.d === hoy ? 'Ya no queda jornada libre hoy' : 'Día completo'),
    f.ocupado !== null ? h('div', { title: 'Parte de la jornada (9:00-18:00) con reuniones', style: { display: 'grid', gridTemplateColumns: 'minmax(72px, 1fr) auto', gap: 'var(--s-2)', alignItems: 'center', minWidth: '140px' } },
      h('span', { style: { height: '8px', borderRadius: 'var(--r-full)', background: 'var(--good-soft)', overflow: 'hidden' } }, h('i', { style: { display: 'block', height: '100%', background: 'var(--accent)', borderRadius: 'var(--r-full)', width: `${Math.min(100, Math.round(f.ocupado / jorMin * 100))}%` } })),
      h('span', { style: EST.meta }, `${fmt.num(Math.round(f.ocupado / jorMin * 100))} % reunido`)) : h('span', {}))));
  return h('div', { style: { display: 'grid', gap: 'var(--s-4)' } },
    panel({ titulo: 'Huecos libres', icono: 'ok', sub: `Jornada de ${jornada.inicio} a ${jornada.fin}, de lunes a viernes. En verde, tramos de 30 min o más; en gris, los cortos.`,
      acciones: texto ? h('button', { type: 'button', class: 'bt', on: { click: () => copiar(`Huecos libres de ${nombreP(S, S.quien)}:\n${texto}`, 'Huecos copiados') } }, icono('copy'), 'Copiar huecos') : null },
    lista),
    avisoParcial('Los huecos se calculan con lo que la app ve de tu calendario: Zoho CRM, Bookings, GoHighLevel y Zoom (y Zoho Calendar en el caso de Tomás). Un evento personal que solo esté en tu Zoho Calendar todavía no resta.', { tipo: 'parcial' }));
}

// ===================================================================== Equipo
function vistaEquipo(S, hoy, ahoraMin, meta) {
  const filas = S.ids.map(id => {
    const ev = ordenarEventosRO(S.evs.filter(e => e.persona_id === id));
    const hoyL = ev.filter(e => FECHAS_RO.dia(e.inicio) === hoy);
    const prox = ev.find(e => FECHAS_RO.horasHasta(e.inicio, S.ahora || new Date()) !== null && FECHAS_RO.horasHasta(e.inicio, S.ahora || new Date()) >= 0);
    const libres = totalHuecosRO(huecosDia(ev, hoy, meta.jornada || {}, ahoraMin));
    return { id, nombre: nombreP(S, id), hoy: hoyL.length, clientes: hoyL.filter(e => e.tipo === 'cliente').length,
      rojos: hoyL.filter(e => enRojo(S, e)).length, prox, libres, semana: ev.filter(e => FECHAS_RO.dia(e.inicio) >= lunesDe(hoy) && FECHAS_RO.dia(e.inicio) <= sumarDias(lunesDe(hoy), 6)).length };
  }).sort((a, b) => b.rojos - a.rojos || b.hoy - a.hoy || a.nombre.localeCompare(b.nombre));
  return panel({ titulo: S.todo ? 'Todo el equipo hoy' : 'Tu equipo hoy', icono: 'eq', sub: 'Citas y huecos de la copia del calendario. Pulsa una persona para abrir su agenda; los huecos no confirman disponibilidad personal.' },
    tablaApilable({
      columnas: [
        { titulo: 'Persona', principal: true, celda: f => h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-2)', font: 'var(--t-h3)' } }, h('span', { class: 'av s' }, iniciales(S.personas.get(f.id)?.nombre || f.id)), f.nombre) },
        { titulo: 'Hoy', num: true, celda: f => fmt.num(f.hoy) },
        { titulo: 'Con clientes', num: true, celda: f => fmt.num(f.clientes) },
        { titulo: 'Críticos', celda: f => f.rojos ? chipEstado('rojo', fmt.num(f.rojos)) : h('span', { style: EST.meta }, 'Ninguno') },
        { titulo: 'Próxima', celda: f => f.prox ? `${FECHAS_RO.dia(f.prox.inicio) === hoy ? 'hoy' : diaCorto(f.prox.inicio)} ${FECHAS_RO.hora(f.prox.inicio)}` : h('span', { style: EST.meta }, 'Sin citas') },
        { titulo: 'Huecos', tituloCompleto: 'Huecos en la copia de hoy; no disponibilidad confirmada', celda: f => h('span', {title:'Calculado con los eventos observados; puede faltar calendario personal'}, durTxt(f.libres)) },
        { titulo: 'Semana', num: true, celda: f => fmt.num(f.semana) },
      ],
      filas, etiquetaFila: f => `Abrir la agenda de ${f.nombre}`,
      alPulsar: f => { S.quien = f.id; S.nombres = {}; try { sessionStorage.setItem('ro.agenda.quien', f.id); } catch { /* */ } S.pintar('hoy'); },
    }));
}

// ===================================================================== Fuentes
function vistaFuentes(S, meta) {
  const est = { bien: ['verde', 'Conectada'], a_cero: ['ambar', 'Sin datos'], rota: ['rojo', 'Rota'], sin_conectar: ['gris', 'Sin conectar'] };
  const lista = h('div', {}, (meta.fuentes || []).map((f, i) => h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2) var(--s-3)', alignItems: 'flex-start', padding: 'var(--s-3) var(--relleno)', borderTop: i ? 'var(--borde-suave)' : '0' } },
    h('span', { class: `ico-c s ${est[f.estado]?.[0] || 'gris'}` }, icono({ crm: 'cal', ghl: 'base', zoom: 'video', bookings: 'cal', calendar: 'cal', dedup: 'capas' }[f.id] || 'plug')),
    h('div', { style: { flex: '1 1 240px', minWidth: '0' } }, h('b', { style: { font: 'var(--t-h3)' } }, f.fuente), h('p', { style: { margin: 'var(--s-1) 0 0', font: 'var(--t-cuerpo)', color: 'var(--mid)', maxWidth: '72ch' } }, f.detalle)),
    chipEstado(est[f.estado]?.[0] || 'gris', est[f.estado]?.[1] || f.estado))));
  const paso = h('div', { style: { display: 'grid', gap: 'var(--s-3)', font: 'var(--t-cuerpo)', color: 'var(--mid)', padding: 'var(--relleno)', maxWidth: '80ch' } },
    h('p', { style: { margin: '0' } }, h('b', {}, 'Cobertura que conviene contrastar:')),
    h('ol', { style: { margin: '0', paddingLeft: 'var(--s-5)', display: 'grid', gap: 'var(--s-2)' } },
      h('li', {}, 'El calendario de Zoho de cada persona: la llave de Zoho es de Tomás y Calendar solo da el suyo. El de cada uno llega cuando la app se publique y cada persona entre con su cuenta. Mientras, sus citas de Bookings y del CRM sí salen.'),
      h('li', {}, 'La cobertura de reuniones programadas de Zoom debe contrastarse con la última lectura. Una grabación no demuestra toda la agenda; si falta una cita, revisar la fuente antes de atribuirlo a un permiso pendiente.')),
    h('p', { style: { margin: '0' } }, 'Bookings y Calendar están conectados desde el 2 de octubre por la tarde (Tomás dio el permiso a la llave de Zoho).'));
  const gen = meta.generado ? fechaHora(meta.generado) : null;
  return h('div', { style: { display: 'grid', gap: 'var(--s-4)' } },
    panel({ titulo: 'De dónde sale la agenda', icono: 'plug', sub: `${gen ? `Leída el ${gen} · ` : ''}ventana del ${fDiaRO(meta.desde)} al ${fDiaRO(meta.hasta)}.` }, lista),
    panel({ titulo: 'Cobertura y pendientes', icono: 'key' }, paso),
    (meta.fuentes || []).some(f=>f.id==='dedup'&&f.n>0) && !(S.D.eventos || []).some(e=>e?.referencia_reunion || (e?.identidad_confirmada===true&&e?.participante_ref))
      ? avisoParcial('Esta copia informa consolidaciones previas, pero no conserva referencias compartidas para contrastarlas aquí. Pendiente revisar la lectura con el criterio actual; el nombre y la hora no bastan para eliminar citas.',{tipo:'parcial'}) : null);
}

/** «2 oct, 17:12» (nunca ISO). */
function fechaHora(s) {
  const t = String(s || '');
  const m = /(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(t);
  if (!m) return t;
  return `${+m[3]} ${MESES[+m[2] - 1]}, ${m[4]}:${m[5]}`;
}

function ordenarEventosRO(eventos) {
  return eventos.slice().sort((a,b) => {
    const da = FECHAS_RO.dia(a.inicio), db = FECHAS_RO.dia(b.inicio);
    if (da && db && da !== db) return da < db ? -1 : 1;
    if (!da || !db) return da ? -1 : db ? 1 : 0;
    const ia = FECHAS_RO.instante(a.inicio), ib = FECHAS_RO.instante(b.inicio);
    return ia && ib ? ia - ib : ia ? -1 : ib ? 1 : 0;
  });
}

function totalHuecosRO(huecos) { return Array.isArray(huecos) ? huecos.reduce((s,[a,b]) => s + b - a, 0) : null; }
