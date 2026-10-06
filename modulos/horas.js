import { fechas as FECHAS_RO, fechaCorta as fechaCortaRO } from '../componentes.js';
import { matrizHorasDiaria238 } from './_horas_diarias_238.js';
import { rangoEquipo254, filaEquipo254 } from './_equipo_horas_254.js';
// modulos/horas.js · M11 Horas y productividad (E7 del plan v2 · puntos 4 y 5 de Mili · fichas G1 de Mili y Cecilia).
// Horas por persona y mes separando accounts de especialistas · imputado frente a esperado (128 h menos ausencias,
// D-25) con el sello «horas incompletas» (D-27: solo aviso) · días sin imputar · horas raras (detector de build.py)
// · horas por tipo de tarea · productividad = tareas que entraron en revisión del account / revisión del cliente /
// ver cliente / completado frente a horas, comparando a cada persona consigo misma y con su tipo de tarea.
// NUNCA un ranking general (D-83): cada uno ve la suya; la comparación, jefes, Mili, Cecilia y Tomás.
// Datos: data/horas/horas.json (fuentes_horas/generar_horas.py; ClickUp con la llave propia). Sin sueldos ni euros.
// El servidor recorta por persona (horas_persona); el cliente de una hora rara solo llega a quien ve ese cliente.

import {
  h, fmt, tile, tiles, chipEstado, chipsFiltro, pestanas, vacio, avisoParcial, panel, frescura, icono, iniciales,
  tablaDensa, copiar, fichaCatalogo, vacioLinea, filaPulsable,
} from '../componentes.js';
import { fechaControl227, ventanasHoras227 } from './_control_periodos_227.js';
import { plegarConsejo } from './_plegar_consejo.js';
import { HORAS_MES_REFERENCIA } from './_constantes_ro.js';   // L-34
import { botonDeshacer } from './_deshacer.js';   // Ronda U (50 #4)
import { selectorPersona, barras, barraMini, S, R, punto, estadoTexto, lineaFuentes, zonaTxt, ancharBuscador, dosColumnas, esMovil } from './produccion_comun.js';

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

const ID = 'horas';
const GRUPOS = ['Accounts', 'Especialistas', 'Jefes y coordinación'];   // revisión 44 (H1): con Jerónimo dentro, «Jefes»
const OBJ = 90; // objetivo de imputación de Mili para el 9-oct (ficha G1); por debajo, aviso (D-27: nunca rojo)
const estPct = p => (p === null || p === undefined ? 'gris' : p >= OBJ ? 'verde' : 'ambar');
const TIPOS_RARA = { 'Tarea con horas fuera de lo normal': 'medidor', 'Registro de más de 8 h seguidas': 'clock', 'Horas sin tarea': 'vacio', 'Horas solapadas': 'capas' };

// La raíz pertenece a una única navegación e identidad; el contenedor principal se reutiliza.
export function montarVistaVigente(cont, ctx) {
  const raiz = h('div', { class: 'pila', 'data-vista-operativa': ID });
  cont.replaceChildren(raiz);
  const identidad = [ctx.persona?.id, ctx.real?.id, !!ctx.soloLectura];
  const ruta = typeof location === 'undefined' ? null : location.hash;
  const vigente = () => raiz.isConnected && raiz.parentNode === cont &&
    (typeof ctx.vigente !== 'function' || ctx.vigente()) &&
    (ruta === null || location.hash === ruta) &&
    identidad[0] === ctx.persona?.id && identidad[1] === ctx.real?.id && identidad[2] === !!ctx.soloLectura;
  return { raiz, vigente };
}

export function estadoAccionLocal(a) {
  const estado = a?.envio_estado !== undefined && a.envio_estado !== null
    ? a.envio_estado : a?.estado;
  const remoto = a?.envio_estado !== undefined && a.envio_estado !== null;
  const conocido = remoto || ['simulada', 'simulado', 'pendiente', 'ok'].includes(estado);
  const textos = { simulada: 'Simulación local · sin envío confirmado', simulado: 'Simulación local · sin envío confirmado',
    pendiente: 'Pendiente · sin envío confirmado', enviado: 'Enviado · confirmación pendiente',
    confirmado: 'Envío confirmado · contrastar resultado en ClickUp', ok: 'Registro local · sin confirmación del proveedor' };
  return { valida: conocido && Object.hasOwn(textos, estado), estado, texto: (conocido && textos[estado]) || 'Acción no confirmada; revisar Envíos',
    confirmada: a?.envio_estado === 'confirmado' };
}

export function decisionesVisibles(acciones, bases, tipos) {
  const permitidas = new Map(bases.map(x => [String(x.id), x]));
  const out = new Map();
  // GET acciones devuelve id DESC. La última acción sustituye la anterior, incluso si falla.
  for (const a of (acciones || []).slice().reverse()) {
    const id = String(a.objeto), base = permitidas.get(id);
    if (!base || !tipos.includes(a.tipo)) continue;
    const cli = base.cli ?? base.cliente_id;
    if (a.cliente_id && a.cliente_id !== cli) continue;
    const estado = estadoAccionLocal(a);
    out.delete(id);
    if (estado.valida) out.set(id, { ...a, seguimiento: estado });
  }
  return out;
}

export async function registrarAccionVigente(ctx, vigente, accion) {
  if (!vigente() || ctx.soloLectura || !ctx.servidor) throw new Error('Vista obsoleta o sólo lectura: no se guarda la acción.');
  const respuesta = await ctx.accion(accion);
  if (!vigente()) throw new Error('La vista ha cambiado; revisa el registro local en Envíos.');
  if (respuesta?.ok !== true || !estadoAccionLocal(respuesta).valida) throw new Error('La acción no tiene un registro válido confirmado por el servidor; revisa Envíos.');
  return respuesta;
}

// 115: resumen de registros autorizados; disponibilidad no se inventa desde 8h/128h.
export function resumenHorasPersona(persona, mes, datos) {
  const numero = v => typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null;
  const filas = (persona.meses || []).filter(m => m.mes === mes);
  const m = filas.length === 1 ? filas[0] : null;
  return { persona_id: persona.persona_id, nombre: persona.nombre || persona.alias || persona.persona_id,
    equipo: persona.equipo || '', dia_fecha: fechaControl227(persona.ayer_fecha) || (persona.ayer_fecha == null ? fechaControl227(datos.ayer) : null),
    dia: numero(persona.ayer), semana: numero(persona.semana), mes: m && !m.antes_de_imputar ? numero(m.imputadas) : null,
    referencia_mes: m && !m.antes_de_imputar ? numero(m.esperadas) : null,
    disponibilidad: null, fuente: 'Registros ClickUp', fecha: datos.fuentes?.horas?.hora || datos.generado || null,
    semana_corte: fechaControl227(datos.hoy) || fechaControl227(datos.ayer) };
}
export function panoramaHoras(ctx, personasAutorizadas, mes, datos, { alAbrir } = {}) {
  const repeticiones = new Map();
  for (const p of datos.personas || []) repeticiones.set(p?.persona_id,(repeticiones.get(p?.persona_id)||0)+1);
  const base = new Map((datos.personas || []).filter(p=>p && typeof p.persona_id==='string' && repeticiones.get(p.persona_id)===1).map(p => [p.persona_id, p]));
  const ids = [...new Set(personasAutorizadas.map(p => p.persona_id))].filter(id => base.has(id));
  const filas = ids.map(id => resumenHorasPersona(base.get(id), mes, datos));
  const valor = v => v === null ? 'Sin dato' : `${fmt.num(v, 1)} h`;
  const ventanas = ventanasHoras227(datos,mes);
  const diarios = matrizHorasDiaria238(ids.map(id=>base.get(id)), datos.hoy);
  const rangoInicial = rangoEquipo254('cinco',datos.hoy,mes);
  const fechas = diarios?.fechas || (rangoInicial ? Array.from({length:5},(_,i)=>new Date(Date.parse(rangoInicial.desde+'T00:00:00Z')+i*864e5).toISOString().slice(0,10)) : []);
  const cajaTabla = h('div',{'data-equipo-horas-254':'',style:{minWidth:'0'}});
  let rango = rangoInicial;
  const identidad254 = [ctx.real?.id,ctx.persona?.id];
  const vivo = () => (typeof ctx.vigente !== 'function' || ctx.vigente()) && identidad254[0]===ctx.real?.id && identidad254[1]===ctx.persona?.id && (typeof ctx.veModulo !== 'function' || ctx.veModulo(ID));
  const resumenRango = h('p',{class:'sub',style:{margin:'8px 0'}});
  const desde = h('input',{type:'date',value:rango?.desde || '', 'aria-label':'Horas desde',style:{minHeight:'44px',maxWidth:'160px'}});
  const hasta = h('input',{type:'date',value:rango?.hasta || '', 'aria-label':'Horas hasta',style:{minHeight:'44px',maxWidth:'160px'}});
  function pintarMatriz() {
    if (!vivo()) return;
    const registros = ids.map(id=>filaEquipo254(base.get(id),datos,rango));
    const conocidos = registros.filter(r=>r.horas!==null);
    const suma254 = conocidos.length ? conocidos.reduce((s,r)=>s+r.horas,0) : null;
    const total = typeof suma254==='number' && Number.isFinite(suma254) ? suma254 : null;
    resumenRango.replaceChildren(`${rango?.desde || 'Sin fecha'} a ${rango?.hasta || 'sin fecha'} · ${total===null?'sin total observado':valor(total)+' registradas'} · ${conocidos.length}/${registros.length} personas con dato · capacidad contractual por confirmar.`);
    cajaTabla.replaceChildren(tablaDensa({filas:registros,porPagina:Math.max(1,registros.length),
      buscar:{campos:['nombre','equipo'],placeholder:'Buscar persona o equipo'},
      columnas:[{clave:'nombre',titulo:'Persona',principal:true,minAncho:'190px',celda:r=>h('span',{title:`${r.nombre} · ${r.equipo}`,style:{display:'block',minWidth:'0'}},h('span',{style:{display:'block',whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis',lineHeight:'18px'}},r.nombre),h('small',{class:'sub',style:{display:'block',whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis',lineHeight:'16px'}},r.equipo))},
        ...fechas.map((f,i)=>({clave:`dia${i}`,titulo:new Intl.DateTimeFormat('es-ES',{weekday:'short',day:'numeric',month:'short',timeZone:'UTC'}).format(new Date(f+'T00:00:00Z')),num:true,
          celda:r=>{const d=r.serie?.dias[i];return h('span',{title:r.serie?`${f} · ${r.serie.zona} · ${d?.entradas??'sin'} registros válidos · fuente ${r.serie.fecha_fuente}`:'Sin serie diaria tipada o zona confirmada',style:{fontWeight:'600',whiteSpace:'nowrap'}},d?.estado==='observado'?valor(d.horas):'—');}})),
        {clave:'total5',titulo:'Total 5 fechas',num:true,celda:r=>h('span',{title:'Suma parcial de fechas con registros; no rellena huecos'},r.total5===null?'—':valor(r.total5))},
        {clave:'horas',titulo:'Rango elegido',num:true,celda:r=>h('span',{title:r.detalle},r.horas===null?'—':valor(r.horas))},
        {clave:'porcentaje',titulo:'% imputado',num:true,celda:r=>h('span',{title:`Pendiente de jornada, calendario y ausencias confirmados para el mismo período; no se usa 8 h/40 h/${HORAS_MES_REFERENCIA} h por defecto`},'—')},
        {clave:'ultima',titulo:'Último registro',celda:r=>h('span',{class:'sub',title:'Última fecha observada en las cinco fechas; no es la última de todo el histórico'},r.ultima?fDiaRO(r.ultima):'—')}],
      alPulsar:r=>{if(vivo() && cajaTabla.isConnected)alAbrir?.(r.persona_id);},etiquetaFila:r=>`Ver registros de ${r.nombre}`,
      vacio:{titulo:'Sin registros diarios autorizados',porque:'Contrasta la cobertura de la copia.'}}));
  }
  const elegir = tipo => {if(!vivo() || !cajaTabla.isConnected)return;rango=rangoEquipo254(tipo,datos.hoy,mes);desde.value=rango?.desde||'';hasta.value=rango?.hasta||'';pintarMatriz();};
  const cambiarFechas=()=>{if(!vivo() || !cajaTabla.isConnected)return;rango={tipo:'libre',desde:desde.value,hasta:hasta.value};pintarMatriz();};
  desde.addEventListener('change',cambiarFechas);hasta.addEventListener('change',cambiarFechas);
  const tablaDiaria = h('section',{'aria-label':'Equipo y horas por fechas',style:{minWidth:'0'}},
    h('style',{},'[data-equipo-horas-254] table.densa{min-width:1100px;width:100%;table-layout:fixed}[data-equipo-horas-254] table.densa th:first-child,[data-equipo-horas-254] table.densa td:first-child{width:200px;min-width:190px;max-width:200px}[data-equipo-horas-254] table.densa th:not(:first-child),[data-equipo-horas-254] table.densa td:not(:first-child){width:100px;white-space:nowrap}[data-equipo-horas-254] table.densa td{padding:6px 12px;height:44px;box-sizing:border-box}'),
    h('h3',{style:{margin:'0 0 8px'}},'El equipo, día a día'),
    h('div',{class:'fila',style:{gap:'8px',flexWrap:'wrap'}},
      [['dia','Último día'],['semana','Esta semana'],['mes','Mes elegido'],['cinco','Cinco fechas']].map(([k,t])=>h('button',{type:'button',class:'bt',style:{minHeight:'44px'},on:{click:()=>elegir(k)}},t)),
      h('label',{},'Desde ',desde),h('label',{},'Hasta ',hasta)),resumenRango,cajaTabla,
    h('details',{},h('summary',{style:{minHeight:'44px'}},'Cómo interpretar las horas'),
      h('p',{class:'sub'},'Las cinco fechas son las publicadas por ClickUp en la zona de cada persona. Cero sólo aparece con registros válidos de cero horas; — indica falta de dato. Los rangos diarios sólo se suman dentro de esas cinco fechas; el mes usa el agregado mensual de Madrid. No se mezclan ventanas ni se evalúa rendimiento.')));
  pintarMatriz();
  return panel({ titulo: 'Equipo y horas', icono: 'clock',
    sub: 'Todas las personas autorizadas en esta vista · abre una fila para ver sus registros.' },
    h('div', { class: 'cuerpo' }, tablaDiaria, h('details',{},h('summary',{style:{minHeight:'44px'}},'Ver agregados de día, semana y mes'),h('p',{class:'sub'},ventanas.detalle),tablaDensa({ filas, porPagina: esMovil() ? 8 : 15,
      buscar: { campos: ['nombre', 'equipo'], placeholder: 'Buscar persona o equipo' }, columnas: [
        { clave: 'nombre', titulo: 'Persona', principal: true }, { clave: 'equipo', titulo: 'Equipo' },
        { clave: 'dia', titulo: ventanas.dia, celda: r => h('span', {}, valor(r.dia), h('small', { class: 'sub', style: { display: 'block' } }, r.dia_fecha || 'Fecha no disponible')) },
        { clave: 'semana', titulo: ventanas.semana, celda: r => h('span',{},valor(r.semana),h('small',{class:'sub',style:{display:'block'}},`Corte global ${ventanas.corte || 'sin fecha'} · zona de la persona`)) },
        { clave: 'mes', titulo: ventanas.mes_titulo, celda: r => valor(r.mes) },
        { clave: 'disponibilidad', titulo: 'Disponibles', celda: () => h('span', { class: 'sub', title: 'Día, semana y mes: sin calendario ni ausencias confirmados' }, 'Sin dato') },
      ], alPulsar: r => { if (!ctx.vigente || ctx.vigente()) alAbrir?.(r.persona_id); }, etiquetaFila: r => `Ver el detalle de ${r.nombre}`,
      vacio: { titulo: 'Sin registros autorizados para esta vista', porque: 'La ausencia de registros no acredita ausencia de trabajo.' } })),
      h('details', {class:'que-es'}, h('summary', {style:{minHeight:'44px'}}, 'Ver fuentes y referencias mensuales'),
        tablaDensa({filas, porPagina:15, columnas:[
          {clave:'nombre', titulo:'Persona', principal:true},
          {clave:'referencia_mes', titulo:'Referencia estimada', celda:r=>h('span', {}, valor(r.referencia_mes), h('small', {class:'sub',style:{display:'block'}}, 'No contractual; no indica capacidad libre'))},
          {clave:'fecha', titulo:'Fuente y lectura', celda:r=>h('span', {class:'sub'}, `${r.fuente} · ${r.fecha || 'sin fecha'}`)},
        ]}))));
}

export default {
  id: ID,
  titulo: 'Horas y productividad',
  grupo: 'Equipo',
  async render(cont, ctx) {
    const vista = montarVistaVigente(cont, ctx);
    const vigente = vista.vigente;
    plegarConsejo(vista.raiz, { despues: true });
    cont = vista.raiz;
    vigilarCortes(cont);
    let D;
    try { D = await ctx.datosModulo('horas/horas'); } catch (e) {
      if (!vigente()) return;
      cont.append(vacio({ icono: 'alert', tono: 'aviso', titulo: 'No se han podido leer las horas', texto: String(e.message || e), quien: 'quien mantiene la app' }));
      return;
    }
    if (!vigente()) return;
    const yo = ctx.persona.id;
    // Zona horaria de cada persona: personas.json (ctx.zona) manda; si no, la que dejó el generador. Valeria → Venezuela, Sofía → España.
    const zonaDe = (pid, respaldo) => ((ctx.datos?.personas || []).find(x => x.id === pid)?.zona) || respaldo || (typeof ctx.zona === 'function' ? ctx.zona(pid) : null);
    const zonaP = p => zonaTxt(zonaDe(p.persona_id, p.zona?.zona));
    const puestos = ctx.persona.puestos || [];
    const comparar = ctx.ver({ tipo: 'comparar_personas' }).ok;
    const validar = puestos.some(p => ['direccion', 'operaciones', 'rrhh'].includes(p)) || comparar;
    // Revisión 44 (H1, H2): «Jefes y coordinación» (hay jefes y jefas) y la técnica de altas con las especialistas, no
    // con los accounts. Se corrige aquí también para los datos ya generados.
    const personas = (D.personas || []).map(p => {
      const grupo = p.grupo === 'Jefas y coordinación' ? 'Jefes y coordinación' : p.puesto === 'tecnico_altas' && p.grupo === 'Accounts' ? 'Especialistas' : p.grupo;
      const equipo = p.equipo === 'Jefas y coordinación' ? 'Jefes y coordinación' : p.puesto === 'tecnico_altas' && p.equipo === 'Accounts' ? 'Técnica de altas' : p.equipo;
      return grupo === p.grupo && equipo === p.equipo ? p : { ...p, grupo, equipo };
    });
    const propia = personas.find(p => p.persona_id === yo);
    const clienteRara = new Map((D.raras_cliente || []).map(r => [r.id, r]));
    const MESES = D.meses || [];
    const ultCerrado = MESES.length > 1 ? MESES[MESES.length - 2] : MESES.at(-1);
    const nomMes = m => (personas[0]?.meses || []).find(x => x.mes === m)?.nombre_mes || m;

    ctx.titulo('Horas y productividad', comparar ? 'Por persona y mes · accounts y especialistas por separado · solo para avisar, nunca un ranking' : 'Tus horas y tu productividad frente a ti mismo · solo para avisar');

    // cola de validaciones de horas raras ya hechas (simuladas)
    const hechas = new Map();
    if (ctx.servidor) {
      try { const r = await ctx.api(`acciones?modulo=${ID}`); if (!vigente()) return; const validas = decisionesVisibles(r.acciones, D.raras || [], ['hora_rara_correcto', 'hora_rara_hablar', 'hora_rara_error']); for (const [id, a] of validas) hechas.set(id, a); } catch { /* sin cola */ }
    }

    if (!vigente()) return;
    const F = D.fuentes || {};
    cont.append(h('div', { class: 'fila', style: { justifyContent: 'space-between', gap: `${S[2]} ${S[3]}` } },
      lineaFuentes([{ fuente: 'ClickUp horas', nombre: 'Horas', fecha: F.horas?.hora, limite_h: F.horas?.limite_h || 3 }, { fuente: 'ClickUp estados', nombre: 'Estados', fecha: F.tareas?.hora, limite_h: F.tareas?.limite_h || 8 }, F.raras?.hora ? { fuente: 'Horas raras', fecha: F.raras.hora } : null], { quien: 'Mili', como: '«Actualizar ahora»' }),
      h('span', { class: 'fila', style: { gap: S[2] } },
        h('span', { class: 'sub', title: 'De personas.json' }, `Tu zona: ${zonaTxt(zonaDe(yo, propia?.zona?.zona))}`),
        h('a', { class: 'bt mini', href: 'https://app.clickup.com/90152357276/timesheets', target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir mis horas en ClickUp'))));
    cont.append(h('p', {class:'sub'}, 'Registros parciales de ClickUp · jornada y ausencias por confirmar. Sin registro no significa sin trabajo.'));
    const comoSeCuenta = h('details', { class: 'que-es', style: { marginTop: S[6] } },
      h('summary', { style: { minHeight: '32px', display: 'inline-flex', alignItems: 'center' } }, 'Cómo se cuentan las horas'),
      h('p', { class: 'sub', style: { maxWidth: '72ch', marginTop: S[2] } }, 'La referencia mensual procede de esta copia; todavía no hay una tabla de ausencias ni un calendario individual confirmado. No es una comprobación de jornada contractual. El día de cada registro se cuenta en la zona horaria de cada persona (la de su ficha: Argentina, Venezuela o España); el mes, en hora de España, como ClickUp.'),
      h('p', { class: 'sub', style: { maxWidth: '72ch', marginTop: S[2] } }, 'Periodo: las horas se guardan por mes completo, así que esta pantalla elige el mes con sus propios botones y no cambia con el periodo de otras pantallas. «Ayer» y «esta semana» son ventanas fijas (último día laborable y semana en curso hasta ayer); las horas raras, los últimos 30 días.'));

    if (!personas.length) {
      cont.append(vacio({ icono: 'clock', titulo: 'No hay horas tuyas que enseñar', texto: `No hay registros de horas disponibles para esta vista. Contrasta la cobertura en ClickUp; esto no demuestra ausencia de trabajo. La fecha del registro se cuenta en ${zonaTxt(zonaDe(yo))}.`, quien: 'Cecilia (RRHH)' }));
      return;
    }

    // mes elegido (se queda): por defecto el último cerrado. Solo en las vistas por mes; «Ayer y esta semana» no lo usa.
    let mes = ultCerrado;
    const chipsMes = () => {
      const c = chipsFiltro({ etiqueta: 'Mes', clave: `${ID}.mes`, valor: ultCerrado,
        opciones: MESES.slice().reverse().map(m => ({ valor: m, texto: nomMes(m)[0].toUpperCase() + nomMes(m).slice(1) + (m === MESES.at(-1) ? ' (hasta ayer)' : '') })),
        alCambiar: v => { mes = v; rehacer(); } });
      mes = c.valor() || ultCerrado;
      return h('div', { class: 'fila', style: { marginTop: S[4], gap: `${S[2]} ${S[3]}` } }, c, h('span', { class: 'sub' }, 'Mes completo (ClickUp guarda las horas por mes)'));
    };
    { const c = chipsMes(); void c; }
    // filtro por puesto (Mili): account, publicidad, CRM, SEO, web, redes, producción…; se queda
    let puesto = '';
    const chipsPuesto = alCambiar => {
      const cuenta = new Map();
      for (const p of personas) cuenta.set(p.equipo, (cuenta.get(p.equipo) || 0) + 1);
      const c = chipsFiltro({ etiqueta: 'Puesto', clave: `${ID}.puesto`, opciones: [{ valor: '', texto: 'Todos', cuenta: personas.length },
        ...[...cuenta.entries()].sort((a, b) => a[0].localeCompare(b[0], 'es')).map(([e, n]) => ({ valor: e, texto: e, cuenta: n }))],
        alCambiar: v => { puesto = v; alCambiar(); } });
      puesto = c.valor();
      return c;
    };
    const dePuesto = ps => ps.filter(p => !puesto || p.equipo === puesto);
    const nom = id => ctx.nombre ? ctx.nombre(id) : id;

    const personaRuta = personas.find(p => p.persona_id === ctx.params?.[0]);
    let verDe = personaRuta?.persona_id || (propia ? yo : personas[0].persona_id);
    const raras = D.raras || [];
    const pend = raras.filter(r => !hechas.has(String(r.id)));
    const P = {
      imputa: { id: 'imputa', texto: 'Ayer y esta semana', icono: 'check' },
      equipo: { id: 'equipo', texto: 'Equipo y horas', icono: 'eq' },
      persona: { id: 'persona', texto: personas.length > 1 ? 'Por persona' : 'Mis horas', icono: 'persona' },
      raras: { id: 'raras', texto: 'Horas raras', icono: 'alert', cuenta: pend.length || null, cuentaEstado: 'rojo' },
    };
    const orden = (comparar && personas.length > 1) ? ['imputa', 'equipo', 'persona', 'raras'] : ['persona', 'raras'];
    const M = (p, m = mes) => (p.meses || []).find(x => x.mes === m) || {};
    let tabs;
    const zonaTabs = h('div');
    const rehacer = () => { if (!vigente()) return; const act = tabs?.activa(); zonaTabs.replaceChildren(); tabs = crearTabs(act); zonaTabs.append(tabs); };
    const crearTabs = act => pestanas({
      pestanas: orden.map(k => P[k]), activa: act, clave: `${ID}.pestana.${yo}`, etiqueta: 'Vistas de horas',
      pintar: (id, z) => ({ imputa: pintarImputa, equipo: pintarEquipo, persona: pintarPersona, raras: pintarRaras })[id](z),
    });
    const irAPersona = pid => { verDe = pid; tabs.elegir('persona'); };
    tabs = crearTabs(personaRuta ? 'persona' : undefined);
    zonaTabs.append(tabs);
    cont.append(zonaTabs, comoSeCuenta);

    for (const el of cont.children) el.style.minWidth = '0'; // main es una rejilla: que nada estire la página en móvil

    // ================================================================ ayer y esta semana (Mili y Cecilia, diario; sin selector de mes)
    function pintarImputa(z) {
      // Definición única de la app («no imputan ayer»): personas activas que imputan horas (sin bajas ni setters),
      // 0 h el último día laborable en SU zona horaria. La misma lista que cuenta Personas.
      const cuentan = personas.filter(p => p.estado_persona === 'activo');
      const caja = h('div', { class: 'pila' });
      const chips = chipsPuesto(() => pinta());
      const fechaAyer = fDiaRO(D.ayer);
      const pinta = () => {
        const ps = dePuesto(cuentan);
        const cero = ps.filter(p => !p.ayer);
        const bajo8 = ps.filter(p => p.ayer > 0 && p.ayer < 8);
        const diasSem = ps[0]?.dias_lab_semana || 0;
        const semImp = ps.reduce((s, p) => s + p.semana, 0), semEsp = 8 * diasSem * ps.length;
        const mc = MESES.at(-1);
        const mesImp = ps.reduce((s, p) => s + (M(p, mc).imputadas || 0), 0), mesEsp = ps.reduce((s, p) => s + (M(p, mc).antes_de_imputar ? 0 : (M(p, mc).esperadas || 0)), 0);
        const indRRHH = ctx.indicador('rrhh.imputacion_del_dia_aviso_de_disciplina');
        const nBajo = cero.length + bajo8.length;
        caja.replaceChildren(...[
          chipsMes(),
          panoramaHoras({...ctx,vigente}, ps, mes, D, { alAbrir: irAPersona }),
          h('details', { class: 'que-es' }, h('summary', {style:{minHeight:'44px'}}, `Registros a contrastar · ${cero.length} personas sin registro ayer`),
          // lo que pide acción primero (guía 3.6): quién está por debajo; luego las cifras
          panel({ titulo: `Sin registro disponible ayer · ${cero.length}`, icono: 'vacio', sub: 'Contrasta fecha, cobertura y jornada antes de recordar. Este botón sólo copia un texto; no lo envía.',
            acciones: cero.length ? h('button', { type: 'button', class: 'bt', on: { click: () => copiar(`Hola, ayer (${fechaAyer}) no veo registros de horas en esta copia de ClickUp. ¿Puedes contrastarlo con tu jornada y tus registros? Gracias.`, 'Recordatorio copiado') } }, icono('copy'), 'Copiar recordatorio') : null },
            cero.length ? listaPersonas(cero.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')), p => [estadoTexto('ambar', 'sin registro'), h('span', { class: 'x' }, p.semana ? `${fmt.num(p.semana, 1)} h esta semana` : 'sin registros esta semana')])
              : h('div', { class: 'cuerpo' }, vacioLinea('Todas las personas de esta vista tienen algún registro ayer en esta copia.', { icono: 'ok' })))),
          bajo8.length ? h('details', {class:'que-es'}, h('summary',{style:{minHeight:'44px'}}, `Referencia de 8 h · ${bajo8.length} registros por debajo`), panel({ titulo: `Imputaron menos de 8 h · ${bajo8.length}`, icono: 'clock', sub: 'Comparación con una referencia de 8 h, no con la jornada individual confirmada. Revisa calendario, ausencias y cobertura.' },
            listaPersonas(bajo8.sort((a, b) => a.ayer - b.ayer), p => [estadoTexto('gris', `${fmt.num(p.ayer, 1)} h ayer`), h('span', { class: 'x' }, `${fmt.num(p.semana, 1)} h esta semana`)]))) : null,
          // el indicador del catálogo de RRHH es la tarjeta «Ayer por debajo de 8 h» (mismo número y umbral): no se repite; su «¿Qué es?», plegado al pie
          indRRHH ? h('details', { class: 'que-es' }, h('summary', { style: { minHeight: '32px', display: 'inline-flex', alignItems: 'center' } }, 'Qué es «Ayer por debajo de 8 h»'),
            h('p', { class: 'sub', style: { maxWidth: '72ch', marginTop: S[2] } }, 'Cuenta registros por debajo de una referencia fija de 8 h. No se han confirmado jornada, ausencias y cobertura por persona; no permite evaluar disciplina ni rendimiento.')) : null,
        ].filter(Boolean)); // replaceChildren pinta «null» si le llega un null: fuera
      };
      pinta();
      z.append(h('div', { class: 'pila', style: { marginTop: S[4] } },
        h('div', { class: 'fila' }, chips),
        h('p', { class: 'sub', style: { maxWidth: '72ch' } }, `${cuentan.length} personas activas · día registrado en su zona horaria · sin bajas ni setters.`),
        caja));
    }

    // lista de personas con 8 a la vista y «Ver todas (N)» que despliega el resto (guía 3.8)
    function listaPersonas(ps, extra, visibles = 8) {
      const ul = listaPersonasTodas(ps, extra);
      if (ps.length <= visibles) return ul;
      const resto = [...ul.children].slice(visibles);
      resto.forEach(li => { li.hidden = true; });
      const bt = h('button', { type: 'button', class: 'bt', 'aria-expanded': 'false', on: { click: () => {
        const abrir = bt.getAttribute('aria-expanded') !== 'true';
        resto.forEach(li => { li.hidden = !abrir; });
        bt.setAttribute('aria-expanded', String(abrir));
        bt.replaceChildren(...(abrir ? ['Ver menos'] : [icono('mas', { clase: 's' }), `Ver todas (${fmt.num(ps.length)})`]));
      } } }, icono('mas', { clase: 's' }), `Ver todas (${fmt.num(ps.length)})`);
      return h('div', {}, ul, h('div', { class: 'cuerpo fila', style: { justifyContent: 'space-between' } }, h('span', { class: 'sub' }, `${fmt.num(visibles)} de ${fmt.num(ps.length)} a la vista`), bt));
    }
    function listaPersonasTodas(ps, extra) {
      return h('ul', { class: 'lista-i cuerpo', style: { paddingTop: S[1], paddingBottom: S[1] } }, ps.map(p => {
        return filaPulsable(h('li', { 'aria-label': `Ver las horas de ${p.nombre}` },
          h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(p.nombre)),
          h('span', { class: 't pila', style: { gap: 'var(--s-1)' } }, h('b', {}, p.nombre), h('span', { class: 'sub' }, `${p.equipo} · ${zonaP(p)}`)), ...extra(p)), () => irAPersona(p.persona_id));
      }));
    }

    // ================================================================ equipo por mes (comparación: solo jefes, Mili, Cecilia y Tomás)
    function pintarEquipo(z) {
      let grupo = '';
      const chips = chipsFiltro({ etiqueta: 'Grupo', clave: `${ID}.grupo`, opciones: [{ valor: '', texto: 'Todos', cuenta: personas.length }, ...GRUPOS.map(g => ({ valor: g, texto: g, icono: g === 'Accounts' ? 'cli' : g === 'Especialistas' ? 'aj' : 'crown', cuenta: personas.filter(p => p.grupo === g).length }))],
        alCambiar: v => { grupo = v; pintarT(); } });
      grupo = chips.valor();
      const chipsP = chipsPuesto(() => pintarT());
      // serie de 7 meses por grupo (agregado de las personas que ve)
      const serie = g => MESES.map(m => {
        const ps = personas.filter(p => p.grupo === g && !M(p, m).antes_de_imputar);
        const suma = campo => { if(!ps.length || !ps.every(p => typeof M(p,m)[campo]==='number' && Number.isFinite(M(p,m)[campo]) && M(p,m)[campo]>=0))return null;const total=ps.reduce((s,p)=>s+M(p,m)[campo],0);return Number.isFinite(total)?total:null; };
        return { etiqueta: nomMes(m).slice(0, 3), valor: suma('imputadas'), ref: suma('esperadas'), estado: 'gris', curso: m === MESES.at(-1) };
      });
      const graf = dosColumnas( ...['Accounts', 'Especialistas'].filter(g => personas.some(p => p.grupo === g)).map(g =>
        panel({ titulo: `${g} · registros de horas`, icono: 'grafico', sub: 'Horas de la copia y referencia estimada del generador anterior. No confirman jornada, disponibilidad ni cumplimiento; un agregado incompleto queda sin dato.' },
          h('div', { class: 'cuerpo' }, barras({ puntos: serie(g), formato: v => `${fmt.num(v)} h`, titulo: `${g}: registros de horas por mes`, nombreBarras: 'Horas registradas en la copia', nombreRef:'Referencia estimada anterior', textoRef: 'Referencia estimada anterior; no es jornada confirmada' })))));
      const caja = h('div');
      function pintarT() {
        const ps = dePuesto(personas.filter(p => !grupo || p.grupo === grupo)).map(p => ({ ...p, m: M(p), puestoTxt: p.equipo, zonaTxt: zonaP(p) }));
        caja.replaceChildren(panoramaHoras({...ctx,vigente}, ps, mes, D, { alAbrir: irAPersona }));
      }
      pintarT();
      z.append(chipsMes(), h('div', { class: 'pila', style: { marginTop: S[4] } },
        panel({ titulo: `Equipo · ${nomMes(mes)}`, icono: 'eq', sub: 'Filtra el grupo y abre una persona para contrastar sus registros. No es un ranking ni una evaluación de jornada.' },
          h('div', { class: 'cuerpo pila', style: { paddingBottom: S[1], gap: S[2] } }, chips, chipsP), caja), h('details', {}, h('summary', {}, 'Ver evolución de registros frente a la referencia estimada'), graf)));
    }

    // ================================================================ una persona (cada uno ve la suya)
    function pintarPersona(z) {
      const cab = h('div', { class: 'fila', style: { marginTop: S[4], justifyContent: 'space-between' } });
      const zonaCab = h('span', { class: 'sub' });
      const dentro = h('div', { class: 'pila', style: { marginTop: S[4] } });
      z.append(chipsMes(), cab, dentro);
      if (personas.length > 1) cab.append(selectorPersona({ personas: personas.map(p => ({ ...p, grupo: p.grupo })), actual: verDe, etiqueta: 'Horas de', alElegir: pid => { verDe = pid; pintarP(); } }));
      cab.append(zonaCab);
      const pintarP = () => {
        dentro.replaceChildren();
        const p = personas.find(x => x.persona_id === verDe) || personas[0];
        zonaCab.replaceChildren(icono('clock', { clase: 's' }), ` Su día de trabajo se cuenta en ${zonaP(p)}`);
        const m = M(p);
        const yoMismo = p.persona_id === yo;
        const numeroObservado = x => typeof x==='number' && Number.isFinite(x) && x>=0 ? x : null;
        const horasObservadas = x => numeroObservado(x)===null ? null : fmt.num(x,1);
        const diferenciaObservada = x => typeof x==='number' && Number.isFinite(x) ? `${x>0?'+':''}${fmt.num(x)} %` : null;
        dentro.append(panoramaHoras({...ctx,vigente},[p],mes,D));
        dentro.append(tiles([
          tile({ icono: 'clock', etiqueta: `Imputadas en ${nomMes(mes)}`, valor: m.antes_de_imputar ? null : horasObservadas(m.imputadas), unidad: 'h registradas en la copia',
            estado: 'gris', comparacion: null,
            contexto: m.antes_de_imputar ? 'Antes de su primera imputación en la copia' : 'Registros parciales; no confirman jornada, disponibilidad ni cumplimiento', medible: 'medias', medibleDetalle: 'Fuente parcial; contrasta cobertura y calendario individual', frescura: { fuente: 'ClickUp', fecha: F.horas?.hora } }),
          tile({ icono: 'hoy', etiqueta: `Ayer (${fDiaRO(p.ayer_fecha || D.ayer)})`, valor: horasObservadas(p.ayer), unidad: 'h registradas en la copia', estado: 'gris', contexto: `Fecha local del registro (${zonaP(p)}); no acredita jornada ni ausencia` }),
          tile({ icono: 'cal', etiqueta: 'Esta semana', valor: horasObservadas(p.semana), unidad: 'h registradas en la copia', estado: 'gris', contexto: 'Semana hasta ayer; calendario individual, ausencias y cobertura por confirmar' }),
          tile({ icono: 'vacio', etiqueta: 'Fechas candidatas a contrastar', valor: typeof m.dias_sin_imputar==='number' && Number.isInteger(m.dias_sin_imputar) && m.dias_sin_imputar>=0 ? m.dias_sin_imputar : null, unidad: '', estado: 'gris', contexto: 'Conteo anterior: laborables de referencia con menos de 15 min en la copia. No confirma jornada ni ausencia de trabajo' }),
          tile({ icono: 'check', etiqueta: 'Hitos de tareas registrados', valor: Number.isInteger(m.tareas) && m.tareas>=0 ? m.tareas : null, unidad: numeroObservado(m.horas_por_tarea)!==null ? `${fmt.num(m.horas_por_tarea, 1)} h por hito de la copia` : '', estado:'gris',
            comparacion: {texto: diferenciaObservada(m.desvio_pct)!==null ? `Diferencia observada: ${diferenciaObservada(m.desvio_pct)} frente a su mediana histórica; no evalúa rendimiento` : 'Diferencia histórica no disponible'},
            contexto: 'Estados de revisión o nombres de cierre en la copia histórica; no acredita entrega aceptada. Medición pendiente de catálogo por lista', medible: 'medias', medibleDetalle: 'Ratio histórico del generador anterior, pendiente de catálogo por lista y cohorte; no acredita tareas aceptadas ni productividad' }),
          tile({ icono: 'alert', etiqueta: 'Horas raras', valor: raras.filter(r => r.persona_id === p.persona_id).length, estado: raras.some(r => r.persona_id === p.persona_id && !hechas.has(String(r.id))) ? 'ambar' : 'verde', contexto: '> 8 h seguidas, solapes, sin tarea o fuera de lo normal', ir: 'Ver las horas raras', alPulsar: () => tabs.elegir('raras') }),
        ]));
        if (m.desvio && numeroObservado(m.horas_por_tarea)!==null && numeroObservado(m.mediana_propia)!==null) dentro.append(h('p',{class:'sub'},`Diferencia histórica observada en ${nomMes(mes)}: ${fmt.num(m.horas_por_tarea,1)} h por hito de tarea de la copia frente a ${fmt.num(m.mediana_propia,1)} h de su mediana anterior${diferenciaObservada(m.desvio_pct)!==null?' ('+diferenciaObservada(m.desvio_pct)+')':''}. No evalúa rendimiento ni acredita entrega aceptada: faltan catálogo por lista y cohortes comparables; tamaño y tipo de tarea pueden cambiar.`));
        // serie de 7 meses: imputado frente a esperado
        const pts = (p.meses || []).map(x => ({ etiqueta: x.nombre_mes.slice(0, 3), valor: x.antes_de_imputar ? null : numeroObservado(x.imputadas), ref: x.antes_de_imputar ? null : numeroObservado(x.esperadas), estado: 'gris', curso: x.en_curso }));
        dentro.append(dosColumnas(
          panel({ titulo: 'Horas por mes', icono: 'grafico', sub: 'Barra: registros en la copia. Raya: referencia estimada del generador anterior; no es jornada ni capacidad confirmada.' },
            h('div', { class: 'cuerpo pila' }, barras({ puntos: pts, formato: v => fmt.num(v), titulo: `Horas registradas por mes de ${p.nombre}`,nombreBarras:'Horas registradas en la copia',nombreRef:'Referencia estimada anterior',textoRef:'Referencia estimada anterior; no es jornada confirmada' }),
              h('p', { class: 'sub' }, `La referencia anterior usa ${HORAS_MES_REFERENCIA} h mensuales y ausencias no registradas como cero. No permite evaluar cumplimiento; contrasta calendario, ausencias y cobertura antes de interpretar diferencias.`))),
          panel({ titulo: `En qué se fueron las horas · ${nomMes(mes)}`, icono: 'capas', sub: 'Por tipo de tarea (sin el cliente), como el detector de horas raras.' },
            h('div', { class: 'cuerpo' }, (m.tipos || []).length ? h('div', { style: { display: 'grid', gap: S[2] } }, m.tipos.map(t => h('div', { style: { display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(56px,128px) auto', gap: S[3], alignItems: 'center' } },
              h('span', { title: t.tipo, style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, t.tipo === 'sin tarea' ? h('b', {}, 'Sin tarea') : t.tipo[0].toUpperCase() + t.tipo.slice(1)),
              barraMini(t.horas, m.tipos[0].horas, t.tipo === 'sin tarea' ? 'ambar' : '', ''), h('span', { style: { textAlign: 'right', color: 'var(--mid)', fontWeight: '600', whiteSpace: 'nowrap' } }, `${fmt.num(t.horas, 1)} h`))))
              : vacioLinea('No hay desglose por tipo de tarea disponible en esta copia. No permite concluir ausencia de horas ni trabajo en ClickUp.', { icono: 'vacio', quien: yoMismo ? 'tú (imputar en ClickUp)' : p.nombre })))));
        if ((m.fechas_sin_imputar || []).length) dentro.append(panel({ titulo: `Fechas a contrastar · ${nomMes(mes)}`, icono: 'cal', sub: 'Selección del generador anterior: fechas laborables de referencia con menos de 15 min registrados en la copia. No acredita días trabajados, ausencia ni falta de imputación; calendario y ausencias por confirmar.' },
          h('div', { class: 'cuerpo fila', style: { gap: S[1] } }, m.fechas_sin_imputar.map(d => chipEstado('gris', fDiaRO(d), { punto: false })))));
        // productividad: consigo misma y con su tipo de tarea
        const filasM = (p.meses || []).filter(x => !x.antes_de_imputar).slice().reverse();
        dentro.append(dosColumnas(
          panel({ titulo: 'Ratios históricos de la copia', icono: 'medidor', sub: 'Horas registradas ÷ hitos de tareas del generador anterior, comparadas con su mediana histórica. No evalúa rendimiento ni acredita entregas aceptadas: catálogo por lista y cohorte pendientes.' },
            tablaDensa({ filas: filasM, apilable: true, columnas: [
              { clave: 'nombre_mes', titulo: 'Mes', principal: true, ordenable: false, celda: x => x.nombre_mes + (x.en_curso ? ' (en curso)' : '') },
              { clave: 'tareas', titulo: 'Hitos en copia', num: true, ordenable: false },
              { clave: 'imputadas', titulo: 'Horas', num: true, ordenable: false, celda: x => fmt.num(x.imputadas, 1) },
              { clave: 'horas_por_tarea', titulo: 'h por hito', num: true, ordenable: false, celda: x => numeroObservado(x.horas_por_tarea)!==null ? fmt.num(x.horas_por_tarea, 1) : '—' },
              { clave: 'mediana_propia', titulo: 'Su mediana', num: true, ordenable: false, celda: x => numeroObservado(x.mediana_propia)!==null ? fmt.num(x.mediana_propia, 1) : '—' },
              { clave: 'desvio_pct', titulo: 'Diferencia observada', num: true, ordenable: false, celda: x => estadoTexto('gris',diferenciaObservada(x.desvio_pct) ?? '—') },
            ], vacio: { titulo: 'Sin meses con horas', porque: 'Todavía no hay registros.' } })),
          panel({ titulo: 'Ratios históricos por tipo', icono: 'capas', sub: 'Últimos 3 meses cerrados: ratio histórico de la copia y mediana por tipo (5 casos o más). No acredita tareas aceptadas ni rendimiento; exige contrastar catálogo, cobertura y cohortes.' },
            (p.por_tipo || []).length ? tablaDensa({ filas: p.por_tipo, apilable: true, columnas: [
              { clave: 'tipo', titulo: 'Tipo de tarea', principal: true, ordenable: false, celda: x => x.tipo[0].toUpperCase() + x.tipo.slice(1) },
              { clave: 'tareas', titulo: 'Hitos en copia', num: true, ordenable: false },
              { clave: 'horas_por_tarea', titulo: 'h por hito', num: true, ordenable: false, celda: x => fmt.num(x.horas_por_tarea, 1) },
              { clave: 'mediana_equipo', titulo: 'Mediana del tipo', num: true, ordenable: false, celda: x => `${fmt.num(x.mediana_equipo, 1)} (${x.casos_equipo})` },
              { clave: 'desvio_pct', titulo: 'Diferencia observada', num: true, ordenable: false, celda: x => estadoTexto('gris',diferenciaObservada(x.desvio_pct) ?? '—') },
            ] }) : h('div', { class: 'cuerpo' }, vacioLinea('Sin ratios por tipo disponibles en esta copia: el generador anterior exige 2 hitos con horas por tipo y 5 casos del equipo. Esto no acredita aceptación ni comparabilidad.', { icono: 'capas' })))));
        const misRaras = raras.filter(r => r.persona_id === p.persona_id);
        if (misRaras.length) dentro.append(panel({ titulo: 'Sus horas raras', icono: 'alert', sub: 'Del detector del panel de Mili (últimos 30 días).' }, listaRaras(misRaras)));
      };
      pintarP();
    }

    // ================================================================ horas raras (validar: Mili, Cecilia, jefes y Tomás)
    function pintarRaras(z) {
      if (!raras.length) { z.append(h('div', { style: { marginTop: S[4] } }, vacio({ icono: 'ok', tono: 'celebrar', titulo: 'Sin horas raras', texto: 'Nada fuera de lo normal en los últimos 30 días.' }))); return; }
      let tipo = '';
      const tipos = [...new Set(raras.map(r => r.tipo))];
      const chips = chipsFiltro({ etiqueta: 'Tipo', clave: `${ID}.rara`, opciones: [{ valor: '', texto: 'Todas', cuenta: raras.length }, { valor: '__pend', texto: 'Sin revisar', cuenta: pend.length, cuentaEstado: 'rojo' }, ...tipos.map(t => ({ valor: t, texto: t, icono: TIPOS_RARA[t] || 'alert', cuenta: raras.filter(r => r.tipo === t).length }))],
        alCambiar: v => { tipo = v; pinta(); } });
      tipo = chips.valor();
      const caja = h('div');
      const pinta = () => caja.replaceChildren(listaRaras(raras.filter(r => !tipo || (tipo === '__pend' ? !hechas.has(String(r.id)) : r.tipo === tipo))));
      pinta();
      const revisadas = raras.length - pend.length;
      z.append(h('div', { class: 'pila', style: { marginTop: S[4] } },
        tiles([
          tile({ icono: 'alert', etiqueta: 'Horas raras', valor: fmt.num(raras.length), contexto: 'Últimos 30 días' }),
          tile({ icono: 'check', etiqueta: 'Revisadas', valor: fmt.pct(revisadas / raras.length * 100), unidad: `${fmt.num(revisadas)} de ${fmt.num(raras.length)}`, estado: revisadas === raras.length ? 'verde' : revisadas / raras.length > 0.5 ? 'ambar' : 'rojo', contexto: 'Catálogo de RRHH: 100 % · > 50 % · < 50 %', medible: 'hoy' }),
        ]),
        panel({ titulo: 'Horas raras por revisar', icono: 'alert', sub: validar ? 'Lo que marques (Correcto, Hablar o Error) queda en la cola simulada con tu nombre y la hora. La tarea va sin el cliente; el cliente solo lo ve quien lo lleva.' : 'Las revisa Mili, Cecilia o tu jefa. Si alguna es un error, corrígela en ClickUp.' },
          h('div', { class: 'cuerpo', style: { paddingBottom: S[1] } }, chips), caja)));
    }

    function listaRaras(rs) {
      if (!rs.length) return h('div', { class: 'cuerpo' }, vacioLinea('Nada en este filtro.', { icono: 'ok' }));
      const alias = id => personas.find(p => p.persona_id === id)?.nombre || id;
      // guía 3.8: 15 a la vista y «Ver más» (antes, hasta 120 seguidas: 22.000 px en el móvil)
      const POR = esMovil() ? 8 : 15;
      let vistas = POR;
      const ul = h('ul', { style: { listStyle: 'none', margin: '0', padding: '0', display: 'grid' } });
      const pie = h('div', { class: 'cuerpo fila', style: { justifyContent: 'space-between' } });
      const pintarL = () => {
        ul.replaceChildren(...rs.slice(0, vistas).map(filaRara));
        pie.replaceChildren(h('span', { class: 'sub' }, `${fmt.num(Math.min(vistas, rs.length))} de ${fmt.num(rs.length)}`),
          ...(vistas < rs.length ? [h('button', { type: 'button', class: 'bt', on: { click: () => { vistas += POR; pintarL(); } } }, icono('mas'), `Ver ${Math.min(POR, rs.length - vistas)} más`)] : []));
      };
      const filaRara = r => {
        const c = clienteRara.get(r.id);
        const hecha = hechas.get(String(r.id));
        return h('li', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: `${S[2]} ${S[3]}`, padding: `${S[3]} ${S[5]}`, borderBottom: '1px solid var(--line-soft)' } },
          h('span', { class: 'ico-c s ambar', title: r.tipo }, icono(TIPOS_RARA[r.tipo] || 'alert', { clase: 's' })),
          h('div', { style: { flex: '1 1 260px', minWidth: '0', display: 'grid', gap: S[1] } },
            h('b', { style: { overflowWrap: 'anywhere' } }, `${alias(r.persona_id)} · ${fmt.num(r.horas, 1)} h · ${r.tipo}`),
            h('div', { class: 'fila sub', style: { gap: `${S[1]} ${S[3]}` } },
              h('span', { style: { overflowWrap: 'anywhere' } }, c ? c.tarea_completa : r.tarea),
              c ? h('span', { class: 'fila', style: { gap: S[1], flexWrap: 'nowrap', fontWeight: '600', color: 'var(--mid)' } }, icono('cli', { clase: 's' }), c.cliente) : null,
              h('span', {}, fDiaRO(r.fecha))),
            h('div', { class: 'sub' }, r.motivo)),
          h('div', { class: 'fila', style: { gap: S[2], flex: 'none' } },
            r.url ? h('a', { class: 'bt mini', href: r.url, target: '_blank', rel: 'noopener' }, icono('ext'), 'ClickUp') : null,
            hecha ? chipEstado('gris', `${(hecha.tipo || '').replace('hora_rara_', '')} · ${hecha.quien} · ${hecha.seguimiento.texto}`) :
              // Ronda U (50 #4): Correcto / Hablar / Error al primer clic, con «Deshacer» 8 s (antes «¿Marcar como…? Sí»)
              validar ? ['Correcto', 'Hablar', 'Error'].map(dec => botonDeshacer({ validar: () => !vigente() ? 'Esta vista ya no está activa.' : null, texto: dec, hecho: `${dec} · propuesta local`, soloLectura: ctx.soloLectura, pri: dec === 'Correcto',
                alHacer: async () => { const resultado = await registrarAccionVigente(ctx, vigente, { herramienta: 'app', tipo: `hora_rara_${dec.toLowerCase()}`, objeto: r.id, texto: dec, vista_previa: { decision: dec, registro: r.id } }); hechas.set(String(r.id), { tipo: `hora_rara_${dec.toLowerCase()}`, quien: ctx.persona.alias || 'tú', seguimiento: estadoAccionLocal(resultado) }); return estadoAccionLocal(resultado).texto; } })) : chipEstado('gris', 'Sin revisar')));
      };
      pintarL();
      return h('div', {}, ul, rs.length > POR ? pie : null);
    }
  },
};
