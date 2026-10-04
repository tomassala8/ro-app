import { fechas as FECHAS_RO, fechaCorta as fechaCortaRO } from '../componentes.js';
import {ambitoSeguimiento453,pintarSeguimiento453} from './_seguimiento_metodo_453.js';
import { separarCadencias, textoCadencia, estadoCadencia, ambitoCadencia307 } from './_cadencia_metodo.js';
// modulos/reuniones.js · M15 «Reuniones» (E11 del plan v2 · punto 8 de Mili · D-06).
// Reuniones de Zoom de toda la cuenta de RO: internas, con cliente o con gente de fuera (por los dominios de los
// participantes), tipo por el prefijo del nombre (Daily, Coordinación, 1:1, Seguimiento, Formación, Cliente) o «sin tipo»
// con desplegable; horas de reunión por persona y mes y su % de capacidad (128 h); la reunión del ciclo con cada cliente
// el mes pasado (alarma si no hubo; mantenimiento exento); actas (grabación y resumen de Zoom enlazados; subir acta en
// simulación). Aviso visible: lo que no pasa por el Zoom de RO no se cuenta; hoy solo las grabadas (W4).
// Datos: data/reuniones/reuniones.json (fuentes_reuniones/generar_reuniones.py), recortado por servir.py:
//   · asistencias y por_persona_mes llevan persona_id → cada uno ve las suyas; su jefe, Operaciones, RRHH y dirección, las de su gente.
//   · clientes lleva cliente_id → cada uno ve solo los clientes que puede abrir.

import {
  h, fmt, icono, tile, tiles, chipEstado, chipsFiltro, pestanas, vacio, vacioLinea, avisoParcial, panel,
  logoCliente, iniciales, tablaDensa, avisoFlotante, campoTexto, barraProgreso,
} from '../componentes.js';
import { llevarA } from './_ir.js';
import { plegarConsejo } from './_plegar_consejo.js';
import { botonConfirmar } from '../componentes.js';
import { PUESTO } from '../permisos.js';
import { botonProponerFecha } from './_propuesta_reunion.js';

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

/** Revisión 44 (R2): el puesto por su nombre («Técnica de altas»), no el id con el guion bajo quitado («tecnico altas»). */
const puestoLegible = (id, nombre = '') => {
  let t = PUESTO[id]?.nombre || String(id || '').replace(/_/g, ' ');
  if (/a$/i.test(String(nombre).trim().split(/\s+/)[0] || '')) t = t.replace(/^Técnico\b/, 'Técnica');   // forma femenina por persona
  return t.replace(/^Setters$/, 'Setter');
};

// La capacidad del DTO puede proceder del fallback128h del productor: sólo referencia.
export function referenciaCapacidadReuniones280(p){
 const h=p?.horas,c=p?.capacidad_h;
 if(typeof h!=='number'||!Number.isFinite(h)||h<0||typeof c!=='number'||!Number.isFinite(c)||c<=0)return null;
 return {horas:h,referencia_h:c,pct:h/c*100};
}
const ID = 'reuniones';
const MES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const nombreMes = m => MES[Number(String(m).slice(5, 7)) - 1] || m;
const Mayus = t => t ? t[0].toUpperCase() + t.slice(1) : t;
const MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const diaSeparador = iso => { const dia = FECHAS_RO.dia(iso); return dia ? `${Mayus(FECHAS_RO.diaSemana(dia, true))} ${fechaCortaRO(dia)}` : 'Fecha por contrastar'; };
const TIPOS = ['Daily', 'Coordinación', '1:1', 'Seguimiento', 'Formación', 'Cliente'];
const ICONO_TIPO = { Daily: 'cal', 'Coordinación': 'eq', '1:1': 'persona', Seguimiento: 'hist', 'Formación': 'libro', Cliente: 'maletin', 'Sin tipo': 'info' };
const AMBITO = {
  interna: { texto: 'Interna', icono: 'eq', estado: 'gris' },
  cliente: { texto: 'Con cliente', icono: 'maletin', estado: 'azul' },
  externa: { texto: 'Con gente de fuera', icono: 'mundo_web', estado: 'azul' },
};
// Tonos de marca para repartir por tipo (sin semáforo: no es bueno ni malo, es reparto)
const TONO_TIPO = { Daily: 'var(--navy)', 'Coordinación': 'var(--accent)', '1:1': 'var(--accent-2)', Seguimiento: 'var(--mid)', 'Formación': 'var(--dim)', Cliente: 'var(--accent-ink)', 'Sin tipo': 'var(--off)' };
const hm = h_ => { if(typeof h_!=='number'||!Number.isFinite(h_)||h_<0)return 'Sin dato'; const m = Math.round(h_ * 60); return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60} min` : ''}`; };

// Sin hoja propia (N6, auditoría 30): solo clases comunes de estilos.css y atributos style con tokens.
const ALTO_CLIC = () => (matchMedia('(max-width: 640px)').matches ? 'calc(var(--s-10) + var(--s-1))' : 'var(--s-8)');
const nombreMesAnio = m => `${nombreMes(m)}${String(m).slice(0, 4) !== FECHAS_RO.hoy().slice(0, 4) ? ` de ${String(m).slice(0, 4)}` : ''}`;
/** Enlace a una herramienta de fuera con forma de botón pequeño (objetivo de clic ≥ 32 px; 44 en el móvil). */
const enlaceBt = (href, ico, texto, title) => h('a', { class: 'bt mini', href, target: '_blank', rel: 'noopener', title: title || null, style: { minHeight: ALTO_CLIC() } }, icono(ico), texto);

// ===================================================================== datos
/** Las asistencias (una fila por persona y reunión) se juntan en reuniones; el tipo marcado a mano manda. */
function juntar(D, cola) {
  const porReu = new Map();
  for (const a of D.asistencias || []) {
    if (!porReu.has(a.reunion)) porReu.set(a.reunion, { ...a, mias: [] });
    porReu.get(a.reunion).mias.push(a);
  }
  return [...porReu.values()].map(r => {
    const cl = cola.tipos.get(r.reunion);
    const actas = cola.actas.get(r.reunion);
    return { ...r, tipo_final: r.tipo || cl?.texto || null, clasificada: cl || null, acta_subida: actas || null,
      con_acta: !!(r.acta.grabacion || r.acta.resumen || actas) };
  }).sort((a, b) => (b.fecha + b.hora).localeCompare(a.fecha + a.hora));
}

// ===================================================================== render
export default {
  id: ID,
  titulo: 'Reuniones',
  grupo: 'Equipo',
  // Periodo común (ronda 9): las reuniones se cuentan por mes (capacidad de 128 h al mes) → este mes o el anterior.
  usa_periodo: ['mes', 'mes_ant'],
  async render(cont, ctx) {
    const identidad=[ctx.real?.id,ctx.persona?.id];
    const vigente307=()=>identidad[0]===ctx.real?.id&&identidad[1]===ctx.persona?.id&&(typeof ctx.vigente!=='function'||ctx.vigente())&&(typeof ctx.veModulo!=='function'||ctx.veModulo(ID)===true);
    if(!vigente307())return;
    const ambito307=ambitoCadencia307(ctx);
    const ambitoMetodo453=ambitoSeguimiento453(ctx);
    vigilarCortes(cont);
    let D;
    try { D = await ctx.datosModulo('reuniones/reuniones'); }
    catch (e) {
      if(!vigente307()||!cont.isConnected)return;
      cont.append(vacio({ icono: 'video', tono: 'aviso', borde: true, titulo: 'No se pudieron leer las reuniones', texto: String(e?.message || e), quien: 'Tomás (volver a generar los datos de reuniones)' }));
      return;
    }
    if(!vigente307()||!cont.isConnected)return;
    const cola = { tipos: new Map(), actas: new Map() };
    if (ctx.servidor) {
      try {
        const r = await ctx.api(`acciones?modulo=${ID}`);
        for (const a of (r.acciones || []).slice().reverse()) {
          if (a.tipo === 'clasificar_reunion') cola.tipos.set(String(a.objeto), a);
          if (a.tipo === 'acta') cola.actas.set(String(a.objeto), a);
        }
      } catch { /* sin cola */ }
    }
    if(!vigente307()||!cont.isConnected)return;
    const raiz = h('div', { class: 'pila', style: { gap: 'var(--s-5)', minWidth: '0' } });
    cont.append(raiz);
    let metodo = null;
    if (ctx.servidor && ctx.api) {
      try { metodo = await ctx.api('metodo/sugerencias'); }
      catch { /* Overlay no disponible: conservar listas históricas con su límite explícito. */ }
    }
    if (!cont.isConnected||!vigente307()) return;
    if(ambito307.firma!==ambitoCadencia307(ctx).firma)metodo=null;
    const S = { D, cola, metodo, ambitoMetodo453, firmaMetodo307:ambito307.firma, vigente307, reuniones: juntar(D, cola), periodo: ctx.periodo };
    // R15b: #/reuniones/<id> (id de la reunión, de la asistencia «reunión·persona» o «AAAA-MM-DD_HHMM») abre esa reunión:
    // su mes, la pestaña de la lista sin filtro y la tarjeta resaltada, al centro y con el foco (llevarA de _ir.js).
    const objetivo = ctx.params?.[0] ? buscarReunion(S.reuniones, ctx.params[0]) : null;
    if (objetivo) S.mesForzado = objetivo.mes;
    S.rehacer = () => { if(!vigente307()||!raiz.isConnected)return; S.reuniones = juntar(D, S.cola); raiz.replaceChildren(); pintar(raiz, ctx, S); };
    ctx.alCambiarPeriodo?.(p => { if (!raiz.isConnected||!vigente307()) return; S.periodo = p; S.mesForzado = null; raiz.replaceChildren(); pintar(raiz, ctx, S); });
    pintar(raiz, ctx, S);
    if (objetivo) {
      irA(raiz, 'lista', '', { suave: false });
      llevarA(raiz, r => r.querySelector(`[data-reunion="${CSS.escape(objetivo.reunion)}"]`));
    } else if (ctx.params?.[0]) {
      raiz.prepend(avisoParcial('Esa reunión no está entre las que puedes ver (o es de antes de lo que guarda Zoom). Abajo tienes las del mes.', { titulo: 'No encuentro esa reunión.' }));
    }
  },
};

// ===================================================================== pantalla
/** Mes que se enseña y mes con el que se compara, sacados del periodo común (este mes · mes anterior). */
function mesesDelPeriodo(S) {
  if (S.mesForzado) {   // R15b: se llegó a una reunión exacta → su mes, comparado con el anterior que tenga datos
    const mes = FECHAS_RO.mes(S.mesForzado);
    return { mes, mesAnt: (S.D._meta?.meses || []).filter(m => m < mes).pop() || null, comparar: true };
  }
  const p = S.periodo;
  const hoyMes = FECHAS_RO.mes();
  const mes = p?.desde == null ? hoyMes : FECHAS_RO.mes(p.desde);
  const mesAnt = p ? (p.comp ? FECHAS_RO.mes(p.comp.desde) : null) : ((S.D._meta?.meses || []).filter(m => m < mes).pop() || null);
  return { mes, mesAnt, comparar: p ? p.comparar !== 'no' : true };
}

function pintar(raiz, ctx, S) {
  const meta = S.D._meta || {};
  const todo = ctx.nivel === 'todo';
  const yo = ctx.persona.id;
  const personasVistas = new Set((S.D.por_persona_mes || []).map(x => x.persona_id));
  const veEquipo = todo || personasVistas.size > 1 || [...personasVistas].some(p => p !== yo);

  // ---- el límite, siempre a la vista y en una línea (pedido: «lo que no pasa por el Zoom de RO no se cuenta») ----
  plegarConsejo(raiz);   // ronda U (#1): el consejo de la carcasa, en una línea

  const { mes, mesAnt, comparar } = mesesDelPeriodo(S);
  if (!mes) { raiz.append(avisoParcial('El periodo no tiene una fecha válida; elige un periodo para ver los registros.', { titulo: 'Periodo por contrastar.' })); return; }
  const mesPeriodo = S.periodo?.desde == null ? FECHAS_RO.mes() : FECHAS_RO.mes(S.periodo.desde);
  if (S.mesForzado && S.mesForzado !== mesPeriodo) {   // R15b: se llegó por enlace a una reunión de otro mes
    raiz.append(avisoParcial(h('span', {}, `Has llegado por un enlace: ves ${nombreMesAnio(mes)}, el mes de esa reunión. `,
      h('button', { type: 'button', class: 'bt mini', style: { minHeight: ALTO_CLIC() }, on: { click: () => { S.mesForzado = null; history.replaceState(null, '', `#/${ID}`); raiz.replaceChildren(); pintar(raiz, ctx, S); } } },
        `Volver a ${nombreMesAnio(mesPeriodo)}`)), { tipo: 'info' }));
  }
  const cuerpo = h('div', { class: 'pila', style: { gap: 'var(--s-5)', minWidth: '0' } });
  raiz.append(cuerpo);
  pintarMes(cuerpo, ctx, S, mes, comparar ? mesAnt : null, veEquipo, comparar);

  // ---- al pie, plegado: cómo se cuenta ----
  raiz.append(h('details', { class: 'que-es panel', style: { padding: 'var(--s-3) var(--relleno)' } },
    h('summary', { style: { minHeight: ALTO_CLIC(), display: 'flex', alignItems: 'center', gap: 'var(--s-2)' } }, icono('info', { clase: 's' }), 'Cómo se cuenta'),
    h('div', { class: 'pila', style: { marginTop: 'var(--s-2)' } },
      h('p', {}, h('b', {}, 'Solo cuenta lo que pasa por el Zoom de RO y queda grabado (desde el 2-oct se graban todas solas). '), 'Lo que no pasa por el Zoom de RO no se cuenta. Hoy solo se ven las reuniones grabadas: falta el permiso de Zoom para leer las no grabadas. La grabación automática está activada y bloqueada para toda la cuenta desde el 2-oct; antes solo están las que alguien grabó a mano. Zoom las borra a los 120 días.'),
      h('p', {}, 'Tipo de reunión: por el principio del nombre (Daily, Coordinación, 1:1, Seguimiento, Formación, Cliente). Si no lo lleva, se clasifica a mano con un clic.'),
      h('p', {}, 'Ámbito: interna si solo hay gente de RO; con cliente o con gente de fuera según el dominio del correo de quien entra.'),
      h('p', { class: 'sub' }, `${fmt.num(meta.reuniones || 0)} reuniones grabadas y ${fmt.num(meta.asistencias || 0)} asistencias leídas de Zoom${meta.zoom_leido ? ` · ${fDiaRO(meta.zoom_leido)}` : ''}.`))));
}

function pintarMes(cont, ctx, S, mes, mesAnt, veEquipo, comparar) {
  const meta = S.D._meta || {};
  const todo = ctx.nivel === 'todo';
  const yo = ctx.persona.id;
  const delMes = S.reuniones.filter(r => r.mes === mes);
  const pm = (S.D.por_persona_mes || []).filter(x => x.mes === mes);
  const pmAnt = (S.D.por_persona_mes || []).filter(x => x.mes === mesAnt);
  const mio = pm.find(x => x.persona_id === yo);
  const mioAnt = pmAnt.find(x => x.persona_id === yo);
  const horas = veEquipo ? (pm.length&&pm.every(x=>typeof x.horas==='number'&&Number.isFinite(x.horas)&&x.horas>=0)?pm.reduce((s,x)=>s+x.horas,0):null) : (typeof mio?.horas==='number'&&Number.isFinite(mio.horas)&&mio.horas>=0?mio.horas:null);
  const horasAnt = veEquipo ? (pmAnt.length&&pmAnt.every(x=>typeof x.horas==='number'&&Number.isFinite(x.horas)&&x.horas>=0)?pmAnt.reduce((s,x)=>s+x.horas,0):null) : (typeof mioAnt?.horas==='number'&&Number.isFinite(mioAnt.horas)&&mioAnt.horas>=0?mioAnt.horas:null);
  const internas = delMes.filter(r => r.ambito === 'interna');
  const conCli = delMes.filter(r => r.ambito !== 'interna');
  const sinTipo = delMes.filter(r => !r.tipo_final);
  const sinActa = delMes.filter(r => !r.con_acta);
  const ambito307=ambitoCadencia307(ctx);
  const metodo307=S.firmaMetodo307===ambito307.firma?S.metodo:null;
  const cadencias = separarCadencias(S.D.clientes || [], metodo307,ambito307);
  const cli = cadencias.historicos;
  const sinReu = cli.filter(c => c.estado === 'sin_reunion');
  const conDatosAnt = mesAnt && (meta.meses || []).includes(mesAnt);
  const comp = textoAnt => (!comparar ? null : { texto: compTexto(mes, mesAnt, conDatosAnt ? textoAnt : null) });

  ctx.titulo('Reuniones', `${Mayus(nombreMesAnio(mes))} · ${fmt.plural(delMes.length, 'reunión grabada', 'reuniones grabadas')} en el Zoom de RO · ${veEquipo ? (todo ? 'todo el equipo' : 'tú y tu equipo') : 'las tuyas'}`
    + (S.periodo?.id === 'mes' ? ' · el mes anterior, en «Más», arriba' : ''));   // R12 (A2): «Este mes» ya está elegido

  // ---- tiles: ronda U (#1, molde común) pasan a «Contexto y cifras» (plegado, debajo); arriba van las pestañas ----
  const refCap = veEquipo ? null : referenciaCapacidadReuniones280(mio);
  const tarjetas = (tiles([
    tile({ icono: 'video', etiqueta: veEquipo ? 'Reuniones del mes' : 'Mis reuniones', valor: fmt.num(delMes.length), unidad: 'grabadas',
      comparacion: comp(`${fmt.num(S.reuniones.filter(r => r.mes === mesAnt).length)} en ${nombreMes(mesAnt || '')}`),
      contexto: `${fmt.num(internas.length)} internas · ${fmt.num(conCli.length)} con cliente o gente de fuera`, medible: 'medias', medibleDetalle: 'Solo las grabadas: las demás llegan cuando Zoom dé el permiso', frescura: { fuente: 'Zoom', fecha: meta.zoom_leido },
      ir: 'Ver la lista', alPulsar: () => irA(cont, 'lista', '') }),
    tile({ icono: 'clock', etiqueta: veEquipo ? 'Horas en reuniones' : 'Mis horas en reuniones', valor: hm(horas), unidad: veEquipo ? `${fmt.num(pm.length)} personas` : refCap ? `${fmt.num(refCap.pct, 1)} % ref. ${refCap.referencia_h} h` : 'Referencia de capacidad: sin dato',
      comparacion: comp(`${hm(horasAnt)} en ${nombreMes(mesAnt || '')}`),
      contexto: 'Tiempo conectado a reuniones grabadas · cobertura parcial; capacidad del DTO sólo como referencia', medible: 'medias', medibleDetalle: 'Solo reuniones grabadas', frescura: { fuente: 'Zoom', fecha: meta.zoom_leido },
      ir: veEquipo ? 'Ver por persona' : 'Ver la lista', alPulsar: () => irA(cont, veEquipo ? 'personas' : 'lista', '') }),
    tile({ icono: 'flag', etiqueta: 'Sin tipo', valor: fmt.num(sinTipo.length), unidad: `de ${fmt.num(delMes.length)}`,
      estado: delMes.length ? (sinTipo.length === 0 ? 'verde' : 'ambar') : '', contexto: 'El tipo va al principio del nombre («Daily ·», «Cliente ·»…). Clasifícalas con un clic', medible: 'hoy',
      ir: 'Clasificar', alPulsar: () => irA(cont, 'lista', 'sin_tipo') }),
    tile({ icono: 'doc', etiqueta: 'Sin acta', valor: fmt.num(sinActa.length), unidad: `de ${fmt.num(delMes.length)}`,
      estado: delMes.length ? (sinActa.length === 0 ? 'verde' : 'ambar') : '', contexto: 'Acta = grabación o resumen de Zoom, o un documento subido', medible: 'hoy',
      ir: 'Ver cuáles', alPulsar: () => irA(cont, 'lista', 'sin_acta') }),
    cli.length ? tile({ icono: 'maletin', etiqueta: `Clientes sin registro de reunión en ${nombreMes(meta.mes_pasado)}`, valor: fmt.num(sinReu.length), unidad: `de ${fmt.num(cli.filter(c => c.estado !== 'exento' && c.estado !== 'no_aplica').length)}`,
      estado: 'gris', contexto: 'Regla histórica mensual: falta de registro en fuentes parciales; no prueba ausencia de reunión ni incumplimiento. Cohorte15d excluida.',
      medible: 'medias', medibleDetalle: 'CRM, Fathom, verificación, Zoom grabado y WhatsApp cuando esté conectado', frescura: { fuente: 'CRM + Zoom', fecha: meta.generado },
      ir: 'Ver cuáles', alPulsar: () => irA(cont, 'clientes', 'sin_reunion') }) : null,
  ].filter(Boolean)));

  if (cadencias.seguimiento.length) {
    cont.append(panel({ titulo: 'Seguimiento cada 15 días · trafficker', icono: 'video',
      sub: 'El trafficker lleva la reunión; el account coordina y verifica el registro. La cohorte confirmada se evalúa aparte de la regla mensual antigua.' },
      h('div', { class: 'cuerpo pila' },
        h('p', { class: 'sub', style: { margin: 0 } }, `Cobertura: ${metodo307?.cobertura_reuniones?.completa ? 'completa para el intervalo declarado' : 'parcial'}. Sin evidencia no se afirma incumplimiento. Evaluación: ${metodo307?.hoy || 'sin fecha'}.`),
        pintarSeguimiento453(h,ctx,cadencias.seguimiento,metodo307,{ambitoInicial:S.ambitoMetodo453,vigente:()=>cont.isConnected&&S.vigente307()&&ambito307.firma===ambitoCadencia307(ctx).firma}))));
  }
  else if (!metodo307) cont.append(avisoParcial('No se pudo contrastar el seguimiento de 15 días. Las listas mensuales inferiores son referencias antiguas de registros, no una evaluación del método vigente ni de incumplimiento.', { titulo: 'Cadencia pendiente de contraste.' }));

  // ---- pestañas: lo de cada día, primero ----
  // Ronda U (#9): la vista por defecto es «Sin registro mensual · otras cuentas» con «Preparar» (la hoja de la reunión en la ficha)
  // y «Proponer fecha»; las grabaciones van en la segunda pestaña.
  const hoyMes = FECHAS_RO.mes(ctx.hoy || FECHAS_RO.hoy());
  const sinEsteMes = cli.filter(c => c.estado !== 'exento' && c.estado !== 'no_aplica' && !(c.ultima && FECHAS_RO.mes(c.ultima) >= hoyMes) && !(c.proxima && FECHAS_RO.mes(c.proxima) === hoyMes));
  const tabs = [
    cli.length ? { id: 'mes', texto: 'Sin registro mensual · otras cuentas', icono: 'maletin', cuenta: sinEsteMes.length || null, cuentaEstado: 'rojo' } : null,
    { id: 'lista', texto: veEquipo ? 'Grabaciones' : 'Mis grabaciones', icono: 'video', cuenta: sinTipo.length || null, cuentaEstado: 'rojo' },
    veEquipo ? { id: 'personas', texto: 'Por persona', icono: 'eq' } : null,
    cli.length ? { id: 'clientes', texto: 'Reunión con cada cliente', icono: 'maletin', cuenta: sinReu.length || null, cuentaEstado: 'rojo' } : null,
    (todo || ctx.persona.puestos.includes('operaciones')) ? { id: 'dailies', texto: 'Reuniones diarias', icono: 'cal' } : null,
  ].filter(Boolean);
  const pt = pestanas({
    pestanas: tabs, clave: `${ID}.pestana.u`, etiqueta: 'Vistas de reuniones',
    pintar: (id, zona) => {
      if (id === 'mes') zona.append(pintarClientesMes(cli, sinEsteMes, ctx, hoyMes));
      if (id === 'lista') zona.append(pintarLista(delMes, ctx, S, mes));
      if (id === 'personas') zona.append(pintarPersonas(pm, pmAnt, ctx, mes));
      if (id === 'clientes') zona.append(pintarClientes(cli, ctx, meta));
      if (id === 'dailies') zona.append(pintarDailies(delMes, ctx, S));
    },
  });
  pt.id = 'reu-pestanas';
  cont.append(pt, h('details', { class: 'que-es panel', style: { padding: 'var(--s-3) var(--relleno)' } },
    h('summary', { style: { minHeight: ALTO_CLIC(), display: 'flex', alignItems: 'center', gap: 'var(--s-2)' } }, icono('grafico', { clase: 's' }), 'Contexto y cifras del mes'),
    h('div', { style: { marginTop: 'var(--s-3)' } }, tarjetas)));
}

// ------------------------------------------- ronda U · clientes sin reunión este mes
const MES_NOMBRE = m => MES[Number(String(m).slice(5, 7)) - 1] || m;
function pintarClientesMes(cli, sinEsteMes, ctx, hoyMes) {
  const cliPorId = new Map(ctx.clientes.map(c => [c.id, c]));
  const filas = sinEsteMes.map(c => ({ ...c, cli: cliPorId.get(c.cliente_id) || { nombre: c.cliente } }))
    .sort((a, b) => (b.dias_sin ?? 999) - (a.dias_sin ?? 999));
  const mesTxt = MES_NOMBRE(hoyMes);
  // 3-oct (Tomás): «Proponer fecha» abre el correo YA REDACTADO (huecos de la agenda, motivo, firma) en un editor grande;
  // «Enviar» → «Enviado · Deshacer» y pasa por envios.py (hoy, simulado). Pieza común: _propuesta_reunion.js.
  const proponer = c => botonProponerFecha(ctx, { cliente_id: c.cliente_id, cliente: c.cliente });
  const sub2 = t => h('span', { style: { display: 'block', font: 'var(--t-meta)', color: 'var(--dim)' } }, t);
  return panel({ titulo: `Clientes sin registro de reunión en ${mesTxt}`, icono: 'maletin', sub: 'Lo más antiguo arriba. «Preparar» abre la hoja de la reunión en la ficha (resultados, lo pendiente, temas abiertos y el acta).' },
    tablaDensa({
      filas, buscar: filas.length > 8 ? { campos: ['cliente', 'account'], placeholder: 'Buscar cliente o account' } : null, porPagina: 25,
      alPulsar: c => ctx.navegar(`ficha/${c.cliente_id}/reunion`), puedePulsar: c => !!c.cli.detalle,
      columnas: [
        { clave: 'cliente', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c.cli), h('span', { style: { display: 'grid', minWidth: '0' } }, h('span', { style: { overflowWrap: 'anywhere' } }, c.cliente), sub2(c.account_id ? ctx.nombre(c.account_id) : 'sin account'))) },
        { clave: 'accion', titulo: 'Acción', ordenable: false, celda: c => h('span', { class: 'fila', style: { gap: 'var(--s-1)' } },
          c.cli.detalle ? h('a', { class: 'bt mini pri', href: `#/ficha/${c.cliente_id}/reunion`, style: { minHeight: ALTO_CLIC() }, on: { click: e => e.stopPropagation() } }, icono('video', { clase: 's' }), 'Preparar') : null,
          c.cli.detalle ? h('span', { on: { click: e => e.stopPropagation() } }, proponer(c)) : null) },
        { clave: 'dias_sin', titulo: 'Última', num: true, celda: c => h('span', {}, c.ultima ? fDiaRO(c.ultima) : 'sin dato', c.dias_sin != null ? sub2(`hace ${fmt.plural(c.dias_sin, 'día', 'días')}`) : null) },
        { clave: 'estado', titulo: 'Mes pasado', celda: c => c.estado === 'sin_reunion' ? chipEstado('gris', 'Sin registro') : chipEstado('gris', 'Registro · ver fuente') },
        { clave: 'enlaces', titulo: 'Abrir', ordenable: false, celda: c => atajos(c) },
      ],
      etiquetaFila: c => `${c.cliente}: preparar la reunión`,
      vacio: { titulo: `No hay casos sin registro en ${mesTxt}`, porque: 'No hay casos en la copia disponible; una fecha programada no confirma celebración ni cobertura completa.', celebrar: false },
    }));
}

/** Comparación honesta: un mes en curso no se compara en número con uno cerrado. */
function compTexto(mes, mesAnt, textoAnt) {
  if (!mesAnt) return 'primer mes con datos';
  if (!textoAnt) return `sin datos de ${nombreMesAnio(mesAnt)}`;
  const hoy = FECHAS_RO.mes();
  return mes === hoy ? `mes en curso · ${textoAnt}` : textoAnt;
}

/** R15b: la reunión de la ruta, por su id, por el id de una asistencia o por «AAAA-MM-DD_HHMM» (fecha y hora). */
function buscarReunion(reus, clave) {
  const k = String(clave);
  const fh = k.match(/^(\d{4}-\d{2}-\d{2})_(\d{2}):?(\d{2})$/);
  return reus.find(r => r.reunion === k) || reus.find(r => (r.mias || []).some(a => a.id === k))
    || (fh ? reus.find(r => r.fecha === fh[1] && String(r.hora || '').replace(':', '') === fh[2] + fh[3]) : null) || null;
}

function irA(cont, pestana, chip, { suave = true } = {}) {
  const pt = cont.querySelector('#reu-pestanas');
  if (!pt) return;
  pt.elegir(pestana);
  if (chip !== undefined) {
    const b = pt.querySelector(`.chips-f button[data-v="${chip}"]`);
    if (b && b.getAttribute('aria-pressed') !== 'true') b.click();
  }
  if (suave) pt.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ------------------------------------------------------------------- lista
function pintarLista(reus, ctx, S, mes) {
  const cuenta = p => reus.filter(p).length;
  const opciones = [
    { valor: '', texto: 'Todas', cuenta: reus.length },
    { valor: 'interna', texto: 'Internas', icono: 'eq', cuenta: cuenta(r => r.ambito === 'interna') },
    { valor: 'cliente', texto: 'Con cliente', icono: 'maletin', cuenta: cuenta(r => r.ambito === 'cliente') },
    { valor: 'externa', texto: 'Con gente de fuera', icono: 'mundo_web', cuenta: cuenta(r => r.ambito === 'externa') },
    { valor: 'sin_tipo', texto: 'Sin tipo', icono: 'flag', cuenta: cuenta(r => !r.tipo_final), cuentaEstado: 'rojo' },
    { valor: 'sin_acta', texto: 'Sin acta', icono: 'doc', cuenta: cuenta(r => !r.con_acta), cuentaEstado: 'rojo' },
  ];
  const caja = h('div', {});
  const chips = chipsFiltro({ etiqueta: 'Ver', clave: `${ID}.chip`, opciones, alCambiar: () => repintar() });
  const marcar = () => chips.querySelectorAll('button').forEach((b, i) => { if (opciones[i]) b.dataset.v = opciones[i].valor; });
  marcar();
  const repintar = () => {
    marcar();
    const v = chips.valor();
    const lista = reus.filter(r => !v ? true : v === 'sin_tipo' ? !r.tipo_final : v === 'sin_acta' ? !r.con_acta : r.ambito === v);
    if (!lista.length) {
      caja.replaceChildren(h('div', { class: 'cuerpo' }, vacioLinea(reus.length
        ? (v === 'sin_tipo' ? 'Todas tienen tipo.' : v === 'sin_acta' ? 'Todas tienen acta.' : 'Ninguna con este filtro: cambia el filtro para ver el resto.')
        : `Ninguna reunión grabada en ${nombreMesAnio(mes)}. Si una no aparece, confirma fecha, grabación y cobertura; no se puede deducir dónde se hizo.`,
      { icono: reus.length && (v === 'sin_tipo' || v === 'sin_acta') ? 'ok' : 'video', quien: reus.length ? null : 'Cada persona (reuniones siempre desde una cuenta de Zoom de RO)' })));
      return;
    }
    const porDia = new Map();
    for (const r of lista) { if (!porDia.has(r.fecha)) porDia.set(r.fecha, []); porDia.get(r.fecha).push(r); }
    caja.replaceChildren(...[...porDia.entries()].flatMap(([dia, rs], i) => [
      // R3: separador de día en minúscula y con el formato común («Viernes 2-oct»), no un H3 en mayúsculas.
      h('h3', { style: { font: 'var(--t-h3)', color: 'var(--dim)', margin: '0', padding: 'var(--s-3) var(--relleno) var(--s-1)', borderTop: i ? 'var(--borde-suave)' : '0' } },
        diaSeparador(dia)),
      ...rs.map((r, j) => itemReunion(r, ctx, S, j > 0)),
    ]));
  };
  repintar();
  return h('div', { class: 'panel' }, h('div', { class: 'cuerpo', style: { paddingBottom: 'var(--s-2)' } }, chips), caja);
}

function selectorTipo(r, ctx, S) {
  if (r.tipo) return h('span', { title: 'Tipo por el nombre de la reunión' }, chipEstado('azul', r.tipo));
  if (r.clasificada) return h('span', { class: 'fila', style: { gap: 'var(--s-1) var(--s-2)' }, title: `Clasificada a mano por ${ctx.nombre(r.clasificada.quien)} (simulación: se guardará al desplegar la app)` },
    chipEstado('azul', r.clasificada.texto), h('span', { class: 'sub', style: { font: 'var(--t-meta)' } }, `a mano · ${ctx.nombre(r.clasificada.quien)}`));
  const caja = h('span', { class: 'fila', style: { gap: 'var(--s-1)' } });
  const guardar = async t => {
    try {
      await ctx.accion({ herramienta: 'app', tipo: 'clasificar_reunion', objeto: r.reunion, texto: t, cliente_id: null,
        vista_previa: { tema: r.tema, fecha: r.fecha, tipo: t, sugerido: r.tipo_sugerido } });
      S.cola.tipos.set(r.reunion, { texto: t, quien: ctx.real.id });
      avisoFlotante(`Clasificada como ${t} (queda en el rastro)`);
      S.rehacer();
    } catch (e) { avisoFlotante(`No se pudo: ${e.message}`, { icono: 'alert' }); }
  };
  const inicial = () => {
    const b = h('button', { type: 'button', class: 'bt mini', 'aria-disabled': ctx.soloLectura ? 'true' : null, 'aria-expanded': 'false',
      title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : 'Sin tipo en el nombre: pulsa para elegirlo',
      style: { minHeight: ALTO_CLIC(), background: 'var(--warn-soft)', borderColor: 'var(--warn-line)', color: 'var(--warn-ink)' } },
    icono('flag'), `Sin tipo · ¿${r.tipo_sugerido}? Sí`);
    // Ronda U (#9): el tipo sugerido se acepta en UN clic; «Otro» abre los demás.
    b.title = ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : `Clasificarla como ${r.tipo_sugerido} (un clic)`;
    b.addEventListener('click', () => { if (!ctx.soloLectura) guardar(r.tipo_sugerido); });
    const otro = h('button', { type: 'button', class: 'bt mini', 'aria-disabled': ctx.soloLectura ? 'true' : null, style: { minHeight: ALTO_CLIC() }, on: { click: () => { if (!ctx.soloLectura) abrir(); } } }, 'Otro tipo');
    caja.replaceChildren(b, otro);
    return b;
  };
  const abrir = () => {
    const ops = [r.tipo_sugerido, ...TIPOS.filter(t => t !== r.tipo_sugerido)].map((t, i) =>
      h('button', { type: 'button', class: `bt mini${i === 0 ? ' pri' : ''}`, style: { minHeight: ALTO_CLIC() }, on: { click: () => guardar(t) } }, icono(ICONO_TIPO[t] || 'info'), t));
    const no = h('button', { type: 'button', class: 'bt mini', 'aria-label': 'Cancelar', style: { minHeight: ALTO_CLIC() }, on: { click: () => inicial().focus() } }, icono('cerrar'));
    const g = h('span', { class: 'fila', style: { gap: 'var(--s-1)' }, role: 'group', 'aria-label': `Tipo de «${r.tema}»` }, ops, no);
    g.addEventListener('keydown', e => { if (e.key === 'Escape') { e.stopPropagation(); inicial().focus(); } });
    caja.replaceChildren(g);
    ops[0].focus();
  };
  inicial();
  return caja;
}

function itemReunion(r, ctx, S, raya = true) {
  const amb = AMBITO[r.ambito] || AMBITO.externa;
  const yo = r.mias.find(a => a.persona_id === ctx.persona.id);
  const gente = r.internos || [];
  const actas = h('div', { class: 'fila', style: { gap: 'var(--s-2)', flex: '0 1 auto', justifyContent: 'flex-start' } },
    r.acta.grabacion ? enlaceBt(r.acta.enlace_grabacion, 'video', 'Grabación', 'Grabación en el portal de Zoom (pide iniciar sesión; nunca el enlace con código)') : null,
    r.acta.transcripcion ? enlaceBt(r.acta.enlace_grabacion, 'doc', 'Transcripción') : null,
    r.acta.resumen ? enlaceBt(r.acta.enlace_resumen || r.acta.enlace_grabacion, 'spark', 'Resumen de Zoom') : null,
    r.acta_subida ? h('span', { title: `Subida por ${ctx.nombre(r.acta_subida.quien)} (simulación: se guardará al desplegar la app)` }, chipEstado('verde', 'Acta subida')) : null,
    !r.con_acta ? chipEstado('ambar', 'Sin acta') : null,
    botonSubirActa(r, ctx, S));
  return h('article', { 'aria-label': `${r.hora}, ${r.tema}`, 'data-reunion': r.reunion,
    style: { display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', gap: 'var(--s-2) var(--s-4)', padding: 'var(--s-3) var(--relleno)', borderTop: raya ? 'var(--borde-suave)' : '0' } },
    h('div', { style: { flex: '0 0 var(--s-16)', display: 'grid', gap: 'var(--s-1)', font: 'var(--t-h3)' } }, r.hora, h('span', { style: { font: 'var(--t-meta)', color: 'var(--dim)' } }, hm(r.minutos_reunion / 60))),
    h('div', { style: { flex: '1 1 240px', minWidth: '0', display: 'grid', gap: 'var(--s-2)' } },
      h('b', { style: { font: 'var(--t-h3)', overflowWrap: 'anywhere' } }, r.tema),
      h('div', { class: 'meta-linea', style: { font: 'var(--t-meta)', gap: 'var(--s-2) var(--s-3)', alignItems: 'center' } },
        selectorTipo(r, ctx, S),
        chipEstado(amb.estado, r.ambito === 'cliente' && r.cliente ? `Cliente · ${r.cliente}` : amb.texto),
        h('span', { title: gente.join(', '), style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)', flexWrap: 'wrap' } }, gente.slice(0, 6).map(n => h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(n))),
          h('span', { style: { marginLeft: 'var(--s-1)' } }, `${gente.length} de RO${r.n_externos ? ` · ${r.n_externos} de fuera` : ''}`)),
        r.dominios_externos?.length ? h('span', { title: 'Dominio de los participantes de fuera', style: { overflowWrap: 'anywhere' } }, icono('mundo_web'), r.dominios_externos.join(', ')) : null,
        r.anfitrion ? h('span', {}, icono('persona'), `Anfitrión: ${r.anfitrion}`) : null,
        yo && yo.minutos !== r.minutos_reunion ? h('span', {}, icono('clock'), `Tú: ${hm(yo.minutos / 60)}`) : null),
      r.resumen?.texto ? h('details', { class: 'que-es', style: { background: 'var(--card-2)', border: 'var(--borde-suave)', borderRadius: 'var(--r-m)', padding: '0 var(--s-3)' } },
        h('summary', { style: { minHeight: ALTO_CLIC(), display: 'flex', alignItems: 'center', gap: 'var(--s-2)' } }, icono('spark', { clase: 's' }), 'Leer el resumen de Zoom'),
        h('p', { style: { margin: '0 0 var(--s-2)' } }, r.resumen.texto),
        r.resumen.pasos?.length ? h('ul', { style: { margin: '0 0 var(--s-3)', paddingLeft: 'var(--s-5)' } }, r.resumen.pasos.map(p => h('li', {}, p))) : null) : null),
    actas);
}

function botonSubirActa(r, ctx, S) {
  if (r.acta.resumen || r.acta_subida) return null;
  const caja = h('span', { style: { minWidth: '0' } });
  const inicial = () => {
    const b = h('button', { type: 'button', class: 'bt mini', style: { minHeight: ALTO_CLIC() }, 'aria-disabled': ctx.soloLectura ? 'true' : null, title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : 'Enlazar o subir el acta (en la prueba queda en local; al desplegar la app, en su almacén)' }, icono('mas'), 'Acta');
    b.addEventListener('click', () => { if (!ctx.soloLectura) form(); });
    caja.replaceChildren(b);
    return b;
  };
  const form = () => {
    const cEnlace = campoTexto({ etiqueta: 'Enlace al acta', tipo: 'url', placeholder: 'Drive, Docs…' });
    const cFichero = campoTexto({ etiqueta: 'O sube un documento', tipo: 'file' });
    const enlace = cEnlace.querySelector('input');
    const fichero = cFichero.querySelector('input');
    fichero.accept = '.pdf,.doc,.docx,.txt,.md';
    const err = h('span', { class: 'sub', role: 'alert' });
    const ok = h('button', { type: 'button', class: 'bt mini pri', style: { minHeight: ALTO_CLIC() } }, icono('ok'), 'Guardar');
    const no = h('button', { type: 'button', class: 'bt mini', style: { minHeight: ALTO_CLIC() } }, 'Cancelar');
    no.addEventListener('click', () => inicial().focus());
    ok.addEventListener('click', async () => {
      const f = fichero.files?.[0];
      if (!enlace.value && !f) { err.textContent = 'Pega un enlace o elige un documento.'; return; }
      if (enlace.value && !/^https?:\/\//.test(enlace.value)) { err.textContent = 'El enlace debe empezar por https://'; return; }
      ok.disabled = true;
      try {
        await ctx.accion({ herramienta: 'app', tipo: 'acta', objeto: r.reunion, texto: f ? `Documento: ${f.name}` : `Enlace: ${enlace.value}`,
          vista_previa: { tema: r.tema, fecha: r.fecha, enlace: enlace.value || null, documento: f ? { nombre: f.name, bytes: f.size } : null, almacen: 'local (prototipo); Cloudflare con W1' } });
        S.cola.actas.set(r.reunion, { quien: ctx.real.id });
        avisoFlotante('Acta guardada en la cola simulada (queda en el rastro)');
        S.rehacer();
      } catch (e) { err.textContent = `No se pudo: ${e.message}`; ok.disabled = false; }
    });
    const caja2 = h('div', { class: 'pila', role: 'group', 'aria-label': `Acta de ${r.tema}`,
      style: { gap: 'var(--s-2)', padding: 'var(--s-3)', border: 'var(--borde)', borderRadius: 'var(--r-m)', background: 'var(--card-2)', minWidth: 'min(100%, 260px)' } },
    cEnlace, cFichero, err, h('div', { class: 'fila', style: { justifyContent: 'flex-end' } }, no, ok));
    caja2.addEventListener('keydown', e => { if (e.key === 'Escape') { e.stopPropagation(); inicial().focus(); } });
    caja.replaceChildren(caja2);
    enlace.focus();
  };
  inicial();
  return caja;
}

// --------------------------------------------------------------- por persona
function pintarPersonas(pm, pmAnt, ctx, mes) {
  if (!pm.length) return h('div', { class: 'panel' }, h('div', { class: 'cuerpo' }, vacioLinea(`Nadie con reuniones grabadas en ${nombreMesAnio(mes)}. Solo cuentan las del Zoom de RO que quedaron grabadas.`, { icono: 'eq' })));
  const ant = new Map(pmAnt.map(x => [x.persona_id, x]));
  const tiposPresentes = [...new Set(pm.flatMap(x => Object.keys(x.por_tipo || {})))].sort((a, b) => (TIPOS.indexOf(a) + 1 || 99) - (TIPOS.indexOf(b) + 1 || 99));
  const filas = pm.map(x => ({ ...x, ant: ant.get(x.persona_id) || null })).sort((a, b) => b.horas - a.horas);
  const cuadro = t => h('i', { 'aria-hidden': 'true', style: { width: 'var(--s-3)', height: 'var(--s-3)', borderRadius: 'var(--r-s)', display: 'inline-block', background: TONO_TIPO[t] || 'var(--off)' } });
  return h('div', { class: 'pila' },
    panel({ titulo: 'Horas de reunión por persona', icono: 'eq', sub: 'Horas en reuniones grabadas. Porcentaje respecto a referencia del DTO, no jornada contractual ni evaluación de desempeño.' },
      tablaDensa({
        filas, buscar: { campos: ['persona', 'nombre'], placeholder: 'Buscar persona' },
        columnas: [
          { clave: 'persona', titulo: 'Persona', principal: true, celda: x => h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(x.nombre || x.persona)), h('span', { style: { display: 'grid' } }, h('span', { style: { font: 'var(--t-h3)' } }, x.persona), h('span', { style: { font: 'var(--t-meta)', color: 'var(--dim)' } }, (x.puestos || []).slice(0, 2).map(p => puestoLegible(p, x.nombre || x.persona)).join(' · ')))) },
          { clave: 'reuniones', titulo: 'Reuniones', num: true, celda: x => fmt.num(x.reuniones) },
          { clave: 'horas', titulo: 'Horas', num: true, celda: x => h('span', { style: { display: 'grid', justifyItems: 'end' } }, hm(x.horas), x.ant ? h('span', { style: { font: 'var(--t-meta)', color: 'var(--dim)' } }, `${x.horas >= x.ant.horas ? '▲' : '▼'} ${hm(Math.abs(x.horas - x.ant.horas))}`) : null) },
          { clave: 'pct_capacidad', titulo: '% / referencia', num: true, celda: x => {
            const r=referenciaCapacidadReuniones280(x);
            if(!r)return h('span',{class:'sub'},'Sin dato');
            return h('span',{title:`${hm(r.horas)} registradas / referencia del DTO ${r.referencia_h} h; cobertura parcial, no jornada pactada.`,style:{display:'grid',justifyItems:'end'}},`${fmt.num(r.pct,1)} % ref.`,h('small',{},`${r.referencia_h} h de referencia`));
          } },
          { clave: 'horas_internas', titulo: 'Internas', num: true, celda: x => hm(x.horas_internas) },
          { clave: 'horas_cliente', titulo: 'Con fuera', num: true, valor: x => x.horas_cliente + x.horas_externas, celda: x => hm(x.horas_cliente + x.horas_externas) },
          { clave: 'por_tipo', titulo: 'Reparto por tipo', ordenable: false, celda: x => {
            const tot = Object.values(x.por_tipo || {}).reduce((s, v) => s + v, 0) || 1;
            const txt = Object.entries(x.por_tipo || {}).map(([t, v]) => `${t}: ${hm(v)}`).join(' · ');
            return h('span', { role: 'img', 'aria-label': txt, title: txt, style: { display: 'flex', height: 'var(--s-2)', borderRadius: 'var(--r-full)', overflow: 'hidden', background: 'var(--line-soft)', minWidth: '110px' } },
              Object.entries(x.por_tipo || {}).map(([t, v]) => h('i', { style: { display: 'block', height: '100%', width: `${v / tot * 100}%`, background: TONO_TIPO[t] || 'var(--off)' } })));
          } },
          { clave: 'sin_acta', titulo: 'Sin acta', num: true, celda: x => x.sin_acta ? chipEstado('ambar', fmt.num(x.sin_acta)) : '0' },
        ],
        etiquetaFila: x => `${x.persona}: ${x.reuniones} reuniones, ${hm(x.horas)}`,
      }),
      h('div', { class: 'cuerpo fila', style: { gap: 'var(--s-2) var(--s-4)', font: 'var(--t-meta)', color: 'var(--dim)' } },
        h('span', {}, 'Reparto por tipo:'), tiposPresentes.map(t => h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, cuadro(t), t)))),
    avisoParcial('La proporción usa sólo horas registradas en reuniones grabadas y la referencia numérica recibida. El productor puede rellenar esa referencia con128h: no confirma jornada, calendario ni cobertura del mes. Un mes sin filas no equivale a cero reuniones.', { titulo: 'Orientativo.' }));
}

// --------------------------------------------------- reunión con cada cliente
function pintarClientes(cli, ctx, meta) {
  const mes = meta.mes_pasado;
  const cuenta = e => cli.filter(c => c.estado === e).length;
  const opciones = [
    { valor: 'sin_reunion', texto: 'Sin registro', icono: 'alert', cuenta: cuenta('sin_reunion'), cuentaEstado: 'gris' },
    { valor: 'ok', texto: 'Con registro', icono: 'ok', cuenta: cuenta('ok') },
    { valor: 'exento', texto: 'Exentos', icono: 'escudo', cuenta: cuenta('exento') },
    { valor: 'no_aplica', texto: 'No aplica', icono: 'info', cuenta: cuenta('no_aplica') },
    { valor: '', texto: 'Todos', cuenta: cli.length },
  ];
  const caja = h('div', {});
  const chips = chipsFiltro({ etiqueta: 'Estado', clave: `${ID}.cli`, opciones, valor: 'sin_reunion', alCambiar: () => repintar() });
  const marcar = () => chips.querySelectorAll('button').forEach((b, i) => { if (opciones[i]) b.dataset.v = opciones[i].valor; });
  const cliPorId = new Map(ctx.clientes.map(c => [c.id, c]));
  const sub2 = t => h('span', { style: { display: 'block', font: 'var(--t-meta)', color: 'var(--dim)' } }, t);
  const repintar = () => {
    marcar();
    const v = chips.valor();
    const filas = cli.filter(c => !v || c.estado === v).map(c => ({ ...c, cli: cliPorId.get(c.cliente_id) || { nombre: c.cliente } }));
    caja.replaceChildren(tablaDensa({
      filas, buscar: { campos: ['cliente', 'account'], placeholder: 'Buscar cliente o account' },
      alPulsar: c => ctx.navegar(`ficha/${c.cliente_id}/reunion`)   /* ronda U (#5): el mismo destino que «Preparar» */, puedePulsar: c => !!c.cli.detalle,
      columnas: [
        { clave: 'cliente', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c.cli), h('span', { style: { overflowWrap: 'anywhere' } }, c.cliente)) },
        { clave: 'account', titulo: 'Account', celda: c => c.account_id ? h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(ctx.nombre(c.account_id))), ctx.nombre(c.account_id)) : chipEstado('ambar', 'Sin account') },
        { clave: 'estado', titulo: `Reunión en ${nombreMes(mes)}`, celda: c => c.estado === 'ok' ? chipEstado('gris', (n => Number.isFinite(n)&&n>0 ? `${fmt.num(n)} ${n === 1 ? 'registro' : 'registros'}` : 'Registro · ver fuente')(c.reuniones_crm + c.reuniones_zoom + (c.reuniones_fathom || 0) + (c.reuniones_whatsapp || 0)))
          : c.estado === 'sin_reunion' ? chipEstado('gris', 'Sin registro') : c.estado === 'exento' ? h('span', {}, chipEstado('gris', 'Exento'), sub2(c.motivo_exento || ''))
            : h('span', {}, chipEstado('gris', 'No aplica'), sub2(c.motivo_no_aplica || '')) },
        { clave: 'fuentes', titulo: 'Dónde', ordenable: false, celda: c => {
          const n = [['CRM', c.reuniones_crm], ['Fathom', c.reuniones_fathom], ['Zoom', c.reuniones_zoom], ['WhatsApp', c.whatsapp_conectado ? c.reuniones_whatsapp : null]];
          const con = n.filter(([, v]) => v);
          return h('span', { style: { display: 'grid', gap: 'var(--s-1)', justifyItems: 'start' } }, con.length ? h('span', {}, con.map(([t, v]) => `${t} ${v}`).join(' · ')) : sub2('sin registros observados en estas fuentes'),
            c.whatsapp_conectado ? null : h('span', { title: 'Los grupos de WhatsApp aún no están conectados', style: { font: 'var(--t-meta)', color: 'var(--dim)' } }, 'WhatsApp: sin dato'));
        } },
        { clave: 'ultima', titulo: 'Última', celda: c => h('span', {}, c.ultima ? fDiaRO(c.ultima) : 'sin dato', c.ultima ? sub2(fmt.hace(c.ultima)) : null, c.proxima ? sub2(`próxima ${fDiaRO(c.proxima)}`) : null) },
        { clave: 'dias_sin', titulo: 'Días sin', num: true, celda: c => c.dias_sin === null || c.dias_sin === undefined ? sub2('sin dato') : h('b', { title:'Antigüedad del último registro observado; no prueba ausencia de reuniones.', style: { color: 'var(--dim)' } }, fmt.num(c.dias_sin)) },
        { clave: 'enlaces', titulo: 'Abrir', ordenable: false, celda: c => atajos(c) },
      ],
      etiquetaFila: c => `${c.cliente}: ${c.estado}. Abrir la ficha`,
      vacio: { titulo: v === 'sin_reunion' ? 'Sin casos en la lectura disponible' : 'Ninguno con este filtro', porque: v === 'sin_reunion' ? `No hay casos sin registro en ${nombreMes(mes)}.` : '', celebrar: false },
    }));
  };
  repintar();
  return h('div', { class: 'pila' },
    panel({ titulo: `Registros mensuales · ${nombreMes(mes)}`, icono: 'maletin', sub: meta.regla_cliente },
      h('div', { class: 'cuerpo', style: { paddingBottom: 'var(--s-1)' } }, chips), caja),
    avisoParcial('Cuenta las reuniones del CRM, las llamadas de Fathom de Tomás, la verificación manual de septiembre, las del Zoom de RO de 20 minutos o más con un cliente reconocido y las de los grupos de WhatsApp en cuanto estén conectados. Es la misma regla que usa En rojo. Las videollamadas por Meet o el teléfono personal no se ven.', { titulo: 'De dónde sale.' }));
}

/** Atajos a la herramienta de origen de cada reunión: Fathom, evento del CRM de Zoho y grabación de Zoom. */
const URL_FUENTE = { Fathom: id => `https://fathom.video/calls/${id}`, CRM: id => `https://crm.zoho.eu/crm/tab/Events/${id}` };
function atajos(c) {
  const ls = (c.enlaces || []).map(e => ({ ...e, url: e.enlace || (URL_FUENTE[e.fuente] && e.id ? URL_FUENTE[e.fuente](e.id) : null) })).filter(e => e.url);
  if (!ls.length) return h('span', { style: { font: 'var(--t-meta)', color: 'var(--dim)' } }, 'sin enlace');
  return h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, ls.slice(0, 3).map(e =>
    enlaceBt(e.url, e.fuente === 'Zoom' ? 'video' : e.fuente === 'Fathom' ? 'spark' : 'cal', `${e.fuente} ${fDiaRO(e.fecha)}`,
      `Abrir en ${e.fuente === 'CRM' ? 'el CRM de Zoho' : e.fuente} · ${fDiaRO(e.fecha)}${e.quien ? ` · ${e.quien}` : ''}`)));
}

// ------------------------------------------------------------------ dailies
function pintarDailies(reus, ctx, S) {
  const dailies = reus.filter(r => r.tipo_final === 'Daily');
  const candidatas = reus.filter(r => !r.tipo_final && r.tipo_sugerido === 'Daily');
  const norma = h('div', { class: 'fila' }, ['Daily ·', 'Coordinación ·', '1:1 ·', 'Seguimiento ·', 'Formación ·', 'Cliente ·'].map(t => h('code', { class: 'chip azul sin-punto mono' }, t)));
  if (!dailies.length) {
    return h('div', { class: 'pila' },
      panel({ titulo: 'Reuniones diarias con grabación y resumen', icono: 'cal', sub: 'Para revisarlas sin asistir' },
        h('div', { class: 'cuerpo' }, vacioLinea(`Ninguna reunión diaria identificada este mes. ${candidatas.length ? `Hay ${fmt.num(candidatas.length)} que lo parecen: clasifícalas en la pestaña Reuniones.` : 'Ninguna reunión lleva todavía el tipo en el nombre.'}`,
          { icono: 'cal', quien: 'Mili (comunicar la norma de nombres)' }))),
      panel({ titulo: 'La norma de nombres', icono: 'flag', sub: 'Cada daily se llama «Daily · equipo» y se hace desde el Zoom de RO (se graba sola desde el 2-oct, con resumen). El tipo al principio del nombre: así se clasifica sola.' }, h('div', { class: 'cuerpo' }, norma)));
  }
  return h('div', { class: 'pila' }, panel({ titulo: 'Reuniones diarias con grabación y resumen', icono: 'cal', sub: 'Para revisarlas sin asistir' },
    ...dailies.map((r, i) => itemReunion(r, ctx, S, i > 0))));
}
