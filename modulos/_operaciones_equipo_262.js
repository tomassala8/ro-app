import {celdaPlanning681,metricaPlanning681,fuentePlanning681} from './_planning_transiciones_681.js';
import {ordenarHorasCliente555,porcentajeMinimo555} from './_orden_horas_cliente_555.js';
import {ordenarEquipoDia539} from './_orden_equipo_dia_539.js';
import {ordenarHorasArtifact447} from './_orden_horas_artifact_447.js';
import {panelEjemplosCreador438} from './_ejemplos_creador_438.js';
import {bandaHoras381,formatearBanda381,cssBandas381,leyendaHoras381} from './_bandas_horas_381.js';
import {cabeceraOperaciones423} from './_cabeceras_operaciones_423.js';
import {renderAgrupaciones376} from './_agrupaciones_tarea_376.js';
import {ambitoHistorial364,cargarHistorial364,historialVigente364,horasHistorialRango364} from './_historial_diario_364.js';
import { comparacionCreadores320 } from './_planning_comparacion_320.js';
import {panelPlanningObservado360} from './_planning_observado_360.js';
import { pautaProporcional306 } from './_pauta_proporcional_306.js';
import {pautaHorasControl} from './control_cartera.js';
import { h } from '../componentes.js';
import { creadasSemana287, panelComparacionSemanal296 } from './_produccion_creadas_287.js';
import { filaAvisado269 } from './_operaciones_registros_269.js';
import { controlAnomalia276 } from './_operaciones_anomalias_276.js';
import { panelEquipoNotas281, observacionesSemana281 } from './_operaciones_notas_equipo_281.js';
import { serieHorasDiaria238 } from './_horas_diarias_238.js';
import { planificacionBaseline } from './_produccion_baseline.js';

export const INVENTARIO_EQUIPO_262 = {
  'equipo-dia': [['Avisado','Persona','Día 1','Día 2','Día 3','Día 4','Día 5','Semanal','Diario','Cerradas ayer','¿Trabajo?']],
  horas: [['Persona','Horas','%','','Días con horas','Última hora'],['Cliente','Reales','Pautadas','%']],
  'alerta-personas': [['Persona','Motivos']],
  anomalias: [['Persona','Qué','Horas','Por qué llama la atención','']],
  'tipos-tarea': [['Tipo de tarea','Casos','Mediana','Máximo','Horas totales']],
  notas: [['Persona','Horas sem. pasada','Esta semana','Nota','Hecho que lo prueba','Acción','']],
  planificacion: [['Quién crea','Creadas','Al planning','Fuegos directos','Rompen el semanal','Semana pasada','Ejemplos']]
};
const rutas262={equipo:'equipo-dia',equipo_dia:'equipo-dia',alerta:'alerta-personas',raras:'anomalias',tipos:'tipos-tarea',planning:'planificacion'};
const arr=x=>Array.isArray(x)?x:[];
const num=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
const dia=x=>{if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x))return false;const d=new Date(x+'T00:00:00Z');return Number.isFinite(+d)&&d.toISOString().slice(0,10)===x;};
const fmt=x=>num(x)?new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(x):'—';
// Sólo la presentación de mínimos: nunca elevar el dato parcial por redondeo.
const fmtMinimo262=(x,digitos=1)=>{
 if(!num(x))return '—';
 const escala=10**digitos,paso=1/escala;
 let v=x>Number.MAX_VALUE/escala?x:Math.floor(x*escala)/escala;
 if(v>x)v=Math.max(0,v-paso);
 let salida=new Intl.NumberFormat('es-ES',{maximumFractionDigits:digitos}).format(v);
 const leido=Number(salida.replace(/\./g,'').replace(',','.'));
 if(!Number.isFinite(leido)||leido>x){
  v=Math.max(0,v-Math.max(paso,Math.abs(v)*Number.EPSILON));
  salida=new Intl.NumberFormat('es-ES',{maximumFractionDigits:digitos}).format(v);
  if(!Number.isFinite(Number(salida.replace(/\./g,'').replace(',','.')))||Number(salida.replace(/\./g,'').replace(',','.'))>x)return '—';
 }
 return salida;
};
const fmtHoras262=(x,minimo=false)=>!num(x)?'—':x>0&&x<0.1?'<0,1':minimo?'≥'+fmtMinimo262(x):fmt(x);
const fmtPorcentajeMinimo262=(x,banda=false)=>{
 if(!num(x))return '—';
 const original=banda?formatearBanda381(x,'porcentaje'):null;
 if(original?.startsWith('<'))return original+' %';
 const digitos=original?.includes(',')?original.split(',')[1].length:1;
 return '≥'+fmtMinimo262(x,digitos)+' %';
};
const nombre=p=>p?.alias||p?.nombre||p?.persona_id||'Sin identidad';
function unicos262(ps){const n=new Map();for(const p of arr(ps))if(typeof p?.persona_id==='string')n.set(p.persona_id,(n.get(p.persona_id)||0)+1);return arr(ps).filter(p=>n.get(p?.persona_id)===1);}
export function diasLaborables262(hoy){if(!dia(hoy))return [];const r=[],d=new Date(hoy+'T00:00:00Z');while(r.length<5){d.setUTCDate(d.getUTCDate()-1);if(d.getUTCDay()>0&&d.getUTCDay()<6)r.unshift(d.toISOString().slice(0,10));}return r;}
function rango262(hoy,preset){if(!dia(hoy))return null;const d=new Date(hoy+'T00:00:00Z'),l=new Date(d);l.setUTCDate(l.getUTCDate()-((l.getUTCDay()+6)%7));let a,b=hoy;
 if(preset==='semant'){l.setUTCDate(l.getUTCDate()-7);a=l.toISOString().slice(0,10);l.setUTCDate(l.getUTCDate()+6);b=l.toISOString().slice(0,10);}
 else if(preset==='sem')a=l.toISOString().slice(0,10);
 else if(preset==='mesant'){const z=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),0));b=z.toISOString().slice(0,10);a=b.slice(0,7)+'-01';}
 else if(preset==='30'){d.setUTCDate(d.getUTCDate()-29);a=d.toISOString().slice(0,10);}
 else a=hoy.slice(0,7)+'-01';return {desde:a,hasta:b};}
export function horasRango262(p,D,r,historial=null){
 const medida90=historial?horasHistorialRango364(historial,r):null;if(medida90)return medida90;
 if(!r||!dia(r.desde)||!dia(r.hasta)||r.desde>r.hasta)return {valor:null,dias:null,ultima:null};
 const s=serieHorasDiaria238(p,D.hoy),observados=s?.dias.filter(d=>d.fecha>=r.desde&&d.fecha<=r.hasta&&d.estado==='observado')||[];
 const month=r.desde.slice(0,7),fullMonth=r.desde===month+'-01'&&r.hasta===new Date(Date.UTC(+month.slice(0,4),+month.slice(5,7),0)).toISOString().slice(0,10);
 const candidatos=(fullMonth||(r.desde===month+'-01'&&r.hasta===D.hoy&&month===D.hoy.slice(0,7)))?arr(p.meses).filter(m=>m?.mes===month):[];
 const mes=candidatos.length===1?candidatos[0]:null,usaMes=!!(mes&&num(mes.imputadas)&&mes.imputadas>0);
 // No usar pct/esperadas ni sumar la serie corta al total mensual (doble conteo).
 const v=usaMes?mes.imputadas:observados.length?observados.reduce((s,d)=>s+d.horas,0):null;
 return {valor:num(v)?v:null,tipo:usaMes?'referencia_mensual':num(v)?'observado_diario':'sin_dato',
 dias:observados.length||null,ultima:observados.at(-1)?.fecha||null,parcial:true,
 detalle:usaMes?'Referencia mensual heredada: sin descriptor de medición ni cobertura confirmado. Días y última fecha proceden sólo de la muestra diaria disponible. No es cumplimiento ni total mensual verificado.':num(v)&&observados.length?'Suma sólo de días observados de la serie disponible, no cobertura completa del rango.':'No hay observaciones compatibles; no equivale a cero.'};
}
function selloProyecto262(s){
 if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(s)||!dia(s.slice(0,10)))return false;
 const h=/[T ](\d{2}):(\d{2})(?::(\d{2}))?/.exec(s);return !h||(+h[1]<24&&+h[2]<60&&+(h[3]||0)<60);
}
export function horasProyectoRango262(p,D,r,hoy){
 const desconocida={valor:null,periodo:null,parcial:true,detalle:'Sin descriptor mensual observado compatible con este rango.'};
 if(!r||!dia(r.desde)||!dia(r.hasta)||r.desde>r.hasta||!dia(hoy)||!dia(D?.hoy)||D.hoy>hoy)return desconocida;
 const m=p?.horas_medicion,mes=m?.periodo;
 if(m?.estado!=='medido'||m.cobertura!=='parcial'||typeof mes!=='string'||!/^\d{4}-(0[1-9]|1[0-2])$/.test(mes)||typeof m.fuente!=='string'||!m.fuente.trim()||!selloProyecto262(m.fecha)||m.fecha.slice(0,10)>D.hoy||!num(p.horas_mes))return desconocida;
 const finMes=new Date(Date.UTC(+mes.slice(0,4),+mes.slice(5,7),0)).toISOString().slice(0,10);
 const entero=r.desde===mes+'-01'&&r.hasta===finMes&&r.hasta<=hoy;
 const actual=r.desde===mes+'-01'&&r.hasta===D.hoy&&mes===hoy.slice(0,7)&&mes===D.hoy.slice(0,7)&&m.fecha.slice(0,10)===D.hoy;
 if(!entero&&!actual)return desconocida;
 return {valor:p.horas_mes,periodo:mes,parcial:true,fecha:m.fecha,fuente:m.fuente,detalle:`Entradas observadas ${mes}, corte ${m.fecha}; copia parcial, no acredita horas sin registrar ni cobertura completa del rango.`};
}
function clienteHoras262(ctx,cid){const xs=arr(ctx.clientesVisibles).filter(c=>c?.id===cid);return typeof cid==='string'&&xs.length===1&&xs[0].activo_confirmado===true&&xs[0].detalle===true&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:cid})?.ok===true;}
function permisoPauta262(ctx,cid){return ctx.servidor===true&&ctx.real?.id===ctx.persona?.id&&ctx.veModulo?.('dinero-cliente')===true&&clienteHoras262(ctx,cid)&&ctx.ver?.({tipo:'horas_pautadas',cliente_id:cid})?.ok===true;}
export function pautaProyectoRango262(ctx,doc,cid,r,medicion){
 if(!permisoPauta262(ctx,cid)||!r||!dia(r.desde)||!dia(r.hasta)||r.desde>r.hasta||r.desde!==r.desde?.slice(0,7)+'-01')return null;
 const p=pautaHorasControl(doc,cid,ctx.hoy,[cid]);
 if(!p||p.periodo!==r.desde.slice(0,7)||r.hasta.slice(0,7)!==p.periodo)return null;
 // Referencia mensual completa, no prorrateo de capacidad ni presupuesto.
 return {...p,porcentaje:medicion?.periodo===p.periodo&&num(medicion.valor)&&p.horas>0?medicion.valor/p.horas*100:null};
}
export function referenciaHoras262(r,hoy){
 if(!r||!dia(r.desde)||!dia(r.hasta)||!dia(hoy)||r.desde>r.hasta)return null;
 const hasta=r.hasta<hoy?r.hasta:hoy;if(r.desde>hasta)return null;
 let dias=0,d=new Date(r.desde+'T00:00:00Z');const fin=new Date(hasta+'T00:00:00Z');
 if((fin-d)/864e5>3660)return null;
 while(d<=fin){if(d.getUTCDay()>0&&d.getUTCDay()<6)dias++;d.setUTCDate(d.getUTCDate()+1);}
 return {dias,horas:dias*8};
}
const refColor262=(valor,amarillo,verde)=>num(valor)?valor>=verde?'ref-verde':valor>=amarillo?'ref-ambar':'ref-rojo':'';
const css262=`.op-equipo262{font-family:system-ui,-apple-system,sans-serif;color:#171b35}.op-equipo262 .oe-panel{background:#fff;border:1px solid #e1e4f1;border-radius:14px;overflow:hidden;margin:0 0 18px;box-shadow:0 1px 2px #10132b08}.op-equipo262 header{padding:14px 18px;display:flex;align-items:baseline;justify-content:space-between;gap:12px;border-bottom:1px solid #eceef7}.op-equipo262 h2{font-size:15px;margin:0;font-weight:600}.op-equipo262 .oe-sub{font-size:12px;color:#777d9b}.op-equipo262 .oe-scroll{overflow:auto}.op-equipo262 table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}.op-equipo262 th{padding:9px 12px;text-align:left;font-size:10.5px;font-weight:700;color:#777d9b;text-transform:uppercase;letter-spacing:.05em;background:#f7f8fc}.op-equipo262 td{padding:6px 12px;border-bottom:1px solid #eceef7;vertical-align:middle}.op-equipo262 .oe-num{text-align:right}.op-equipo262 .oe-missing{color:#9298ac}.op-equipo262 .oe-chips,.op-equipo262 .oe-range{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:10px 18px}.op-equipo262 button,.op-equipo262 input,.op-equipo262 select{min-height:44px;border:1px solid #e1e4f1;border-radius:8px;background:#fff;font:inherit;padding:6px 10px}.op-equipo262 input[type=checkbox]{min-height:16px;height:16px;width:16px;padding:0}.op-equipo262 td{height:44px;box-sizing:border-box}.op-equipo262 button[aria-pressed=true]{background:#ecebff;color:#5046ca;border-color:#cdc9fa}.op-equipo262 button:focus-visible,.op-equipo262 input:focus-visible,.op-equipo262 select:focus-visible{outline:2px solid #6366f1;outline-offset:2px}.op-equipo262 .oe-kpis{display:flex;flex-wrap:wrap;gap:8px 20px;padding:10px 18px}.op-equipo262 .oe-kpi{flex:1;min-width:160px;display:grid;grid-template-columns:1fr auto;align-items:baseline;gap:4px 10px;font-size:12px}.op-equipo262 .oe-kpi strong{font-size:17px;margin:0;white-space:nowrap}.op-equipo262 .oe-kpi small{grid-column:1/-1}.op-equipo262 th:first-child,.op-equipo262 td:first-child{position:sticky;left:0;z-index:1;background:#fff}.op-equipo262 th:first-child{background:#f7f8fc;z-index:2}.op-equipo262 .oe-daily th:first-child,.op-equipo262 .oe-daily td:first-child{position:static}.op-equipo262 .oe-daily th:nth-child(2),.op-equipo262 .oe-daily td:nth-child(2){position:sticky;left:0;z-index:1;background:#fff;text-align:left;min-width:135px}.op-equipo262 .oe-daily th:nth-child(2){background:#f7f8fc;z-index:2}.op-equipo262 details{padding:8px 18px;font-size:12px;color:#777d9b}.op-equipo262 .oe-bar{height:6px;border-radius:5px;background:#f0f1f7;min-width:80px}.op-equipo262 .ref-verde{background:#e3f5e8;color:#237648}.op-equipo262 .ref-ambar{background:#fff2cc;color:#805500}.op-equipo262 .ref-rojo{background:#fde8e9;color:#a7444e}.op-equipo262 .oe-ref{border-radius:5px;padding:3px 6px;border-bottom:1px dotted currentColor}.op-equipo262 .oe-observado{background:#f0f1f7;color:#555d73}.op-equipo262 .oe-note{padding:10px 18px;color:#777d9b;font-size:12px}.op-equipo262 small{display:block;color:#777d9b;font-size:11px}.op-equipo262 td>details{padding:0;font-size:12px}.op-equipo262 td>details[open]{padding-bottom:8px}.op-equipo262 .oe-daily{min-width:940px}.op-equipo262 .oe-daily th,.op-equipo262 .oe-daily td{padding-left:8px;padding-right:8px}@media(max-width:600px){.op-equipo262 button,.op-equipo262 input,.op-equipo262 select{min-height:44px}.op-equipo262 header{align-items:start;flex-direction:column}.op-equipo262 th,.op-equipo262 td{padding:8px 10px}}`;
export async function renderEquipo262(cont,ctx,subruta='equipo-dia'){
 const ruta=rutas262[subruta]||subruta;if(!(ruta in INVENTARIO_EQUIPO_262))return false;
 const identidad=[ctx.real?.id,ctx.persona?.id],vigente=()=>identidad[0]===ctx.real?.id&&identidad[1]===ctx.persona?.id&&(typeof ctx.vigente!=='function'||ctx.vigente());
 const selloLecturaPlanning491=()=>JSON.stringify([ctx.real,ctx.persona,ctx.hoy,ctx.datos?.personas,ctx.clientes,ctx.clientesVisibles,ctx.veModulo?.('produccion'),arr(ctx.datos?.personas).map(p=>[p.id,ctx.ver?.({tipo:'horas_persona',persona_id:p.id})?.ok]),arr(ctx.clientesVisibles).map(c=>[c.id,ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok])]);
 const lecturaPlanning491=ruta==='planificacion'?selloLecturaPlanning491():null;
 const fuentes={},fallos=[];
 const leer=async(id,path)=>{if(typeof ctx.veModulo!=='function'||!ctx.veModulo(id)){fallos.push(id);return null;}try{const d=await ctx.datosModulo(path);if(!vigente()||!ctx.veModulo(id))return null;fuentes[id]=d;return d;}catch{fallos.push(id);return null;}};
 const necesitasH=['equipo-dia','horas','anomalias','tipos-tarea','notas'].includes(ruta),necesitasP=['equipo-dia','horas','planificacion'].includes(ruta);
 const leerPauta=ruta==='horas'&&arr(ctx.clientesVisibles).some(c=>permisoPauta262(ctx,c?.id));
 const datos=await Promise.all([necesitasH?leer('horas','horas/horas'):null,necesitasP?leer('produccion','produccion/produccion'):null,ruta==='alerta-personas'?leer('personas','personas_m20/equipo'):null,leerPauta?leer('dinero-cliente','dinero_cliente/dinero_cliente'):null]);
 if(!vigente()||(ruta==='planificacion'&&selloLecturaPlanning491()!==lecturaPlanning491))return false;
 const [H,PR,E,PAUTA]=datos;
 const usaHistorial=['horas','equipo-dia'].includes(ruta),histScope=usaHistorial?ambitoHistorial364(ctx,H):null;
 if(ctx.servidor===true&&usaHistorial&&!histScope){cont.append(h('section',{class:'oe-panel',role:'status'},h('p',{},'Datos de horas no disponibles con los permisos actuales.')));return false;}
 const historial=usaHistorial?await cargarHistorial364(ctx,H):null;
 if(historial?.denegado===true){if(vigente())cont.append(h('section',{class:'oe-panel',role:'status'},h('p',{},'Datos de horas no disponibles con los permisos actuales.')));return false;}
 if(!vigente()||(histScope&&ambitoHistorial364(ctx,H)?.firma!==histScope.firma))return false;
 const root=h('div',{class:'op-equipo262'},h('style',{},css262+cssBandas381));cont.append(root);
 const vivo=()=>{const ok=root.isConnected!==false&&vigente()&&Object.keys(fuentes).every(id=>ctx.veModulo(id))&&(!histScope||ambitoHistorial364(ctx,H)?.firma===histScope.firma)&&(!historial||historialVigente364(ctx,H,historial));if(!ok&&histScope)root.replaceChildren();return ok;};
 const serie90=p=>historial?.series.get(p.persona_id)||null;
 const primeras=[...historial?.series.values()||[]];
 const fuenteHistorial=historial?`Historial90d ${primeras[0]?.desde||'—'} → ${primeras[0]?.hasta||'—'} · corte ${primeras[0]?.corte||'—'} · fuente UTC ${[...new Set([...historial.series.values()].map(s=>s.fecha_fuente))].join(' / ')||'sin observaciones'} · cobertura parcial`:'Historial90d no disponible; muestra diaria / referencia mensual heredada';
 const missing=texto=>h('span',{class:'oe-missing',title:texto||'Sin dato autorizado compatible.'},'—');
 const valor=(x,detail)=>num(x)?h('span',{title:detail||'Observado en la copia parcial.'},fmt(x)):missing(detail);
 const table=(titulo,cols,rows,sub='',className='')=>h('section',{class:'oe-panel'},h('header',{},h('h2',{},titulo),h('span',{class:'oe-sub'},sub)),h('div',{class:'oe-scroll',role:'region','aria-label':titulo,tabIndex:0},h('table',{class:className},h('thead',{},h('tr',{},cols.map((c,i)=>{const m=cabeceraOperaciones423(c);return h('th',{scope:'col',class:i?'oe-num':'',title:m.completo||null,'aria-label':m.completo||null},m.breve);}))),h('tbody',{},rows.length?rows.map(r=>h('tr',{},r.map((x,i)=>h('td',{class:i?'oe-num':''},x??missing())))):h('tr',{},h('td',{colspan:String(cols.length),class:'oe-missing'},'Sin filas disponibles en este ámbito; no acredita ausencia.'))))));
 const ref=texto=>h('details',{},h('summary',{},'Fuente y referencias del artifact'),h('p',{},texto));
 const people=unicos262(H?.personas).filter(p=>!histScope||histScope.ids.includes(p.persona_id)),prPeople=unicos262(PR?.personas),today=dia(ctx.hoy)?ctx.hoy:null;
 const names=new Map([...people,...prPeople,...unicos262(E?.personas)].map(p=>[p.persona_id,nombre(p)]));
 if(ruta==='equipo-dia'){
   const dias=diasLaborables262(today),base=people.length?people:prPeople.filter(p=>!histScope||histScope.ids.includes(p.persona_id));
   const ordenadas539=ordenarEquipoDia539(base.map(p=>({persona:p,serie:serie90(p)||serieHorasDiaria238(p,H?.hoy)})),dias,today);
   const rows=ordenadas539.map(({persona:p,serie:s})=>{const diasH=dias.map(f=>s?.dias.find(d=>d.fecha===f&&d.estado==='observado'));
     const workload=prPeople.find(q=>q.persona_id===p.persona_id);
     return [filaAvisado269(ctx,p.persona_id),nombre(p),...Array.from({length:5},(_,i)=>diasH[i]).map(d=>{if(!d)return missing();const b=bandaHoras381(d.horas,{tipo:'diaria',observado:true,fuente:'ClickUp entradas',cobertura:'parcial',hoy:today,fecha:d.fecha,fecha_fuente:s.fecha_fuente,referencia_horas:8});return h('span',{class:'oe-ref oe-observado '+(b?.clase||''),title:`${d.fecha}: horas observadas en copia parcial. Fuente ${s.fecha_fuente}; zona ${s.zona}. ${b?.detalle||'Referencia sin descriptor suficiente; no se evalúa jornada.'}`},b?formatearBanda381(d.horas,'diaria'):fmtHoras262(d.horas));}),
       valor(workload?.semana,'Campo semanal de la copia: no acredita una estimación de carga en horas.'),valor(workload?.hoy,'Pendientes de la fecha fuente, no historial de cumplimiento diario.'),missing('No hay fecha de cierre por persona y día acreditada.'),missing('No hay estimaciones y disponibilidad confirmadas para concluir si hay trabajo suficiente.')];});
   const ayer=dias.at(-1),hs=base.map(p=>(serie90(p)||serieHorasDiaria238(p,H?.hoy))?.dias.find(d=>d.fecha===ayer&&d.estado==='observado')?.horas).filter(num);
   const kpis=[['Última fecha: registros con 0 h',hs.length?hs.filter(v=>v===0).length:null],['Registros menores de 8 h ref.',hs.length?hs.filter(v=>v>0&&v<8).length:null],['Diario sin cumplir',null],['Poca carga esta semana',null]];
   root.append(h('section',{class:'oe-panel'},h('header',{},h('h2',{},'El equipo, día a día'),h('span',{class:'oe-sub'},`Última fecha laboral ${ayer||'sin fecha'} · ${fuenteHistorial}`)),h('div',{class:'oe-kpis'},kpis.map(([label,n])=>h('div',{class:'oe-kpi',title:'Referencia del artifact · sólo registros observados; resto sin dato'},h('span',{},label),h('strong',{},fmt(n)))))),table('Equipo · últimos cinco laborables',['Avisado','Persona',...Array.from({length:5},(_,i)=>dias[i]?.slice(5)||`Día ${i+1}`),'Semanal','Diario','Cerradas ayer','¿Trabajo?'],rows,'Horas observadas · referencia6/8h, sin evaluar jornada','oe-daily'),leyendaHoras381(h,'diaria'),ref('Referencia original: 8 h/día y avisos por debajo de 6/8 h. Jornada y ausencias por confirmar. Los registros respetan la zona horaria de cada persona; los laborables fuera de la serie quedan desconocidos. “Avisado” registra una declaración propia con autor y fecha.'));
 }else if(ruta==='horas'){
   let range=rango262(today,'sem'),selected='sem';const zona=h('div');
   const pintar=()=>{if(!vivo())return;zona.replaceChildren();
     const ref=referenciaHoras262(range,H?.hoy);
     const ordenadas=ordenarHorasArtifact447(people.map(p=>({persona:p,medicion:horasRango262(p,H,range,serie90(p)),rango:range})),range);
     const rows=ordenadas.map(({persona:p,medicion:m})=>{const calculado=num(m.valor)&&ref?.horas>0?m.valor/ref.horas*100:null,pct=num(calculado)?calculado:null,s=serie90(p)||serieHorasDiaria238(p,H?.hoy),b=bandaHoras381(m.valor,{tipo:'porcentaje',observado:['observado_historial_90d','observado_diario'].includes(m.tipo),fuente:'ClickUp entradas',fecha_fuente:s?.fecha_fuente,cobertura:'parcial',hoy:today,desde:range?.desde,hasta:range?.hasta,referencia_horas:ref?.horas,laborables:ref?.dias});return [nombre(p),m.tipo==='observado_historial_90d'?h('span',{title:m.detalle},fmtHoras262(m.valor,true)):valor(m.valor,m.detalle),pct!==null?h('span',{class:'oe-ref oe-observado '+(b?.clase||''),'aria-label':`Porcentaje mínimo observado respecto a8h por laborable; numerador parcial, no capacidad contractual.`,title:`${b?.detalle||'Sin banda de referencia acreditada. '}Simulación referencia8h por laborable (${ref.horas}h), no capacidad contractual. Numerador parcial: porcentaje mínimo observado.`},fmtPorcentajeMinimo262(pct,!!b)):missing(),h('div',{class:'oe-bar',title:'Barra de referencia histórica, no cumplimiento vigente'},pct!==null?h('i',{style:`display:block;height:6px;border-radius:5px;background:${b?({rojo:'#e76f73',ambar:'#e3b33f',verde:'#4ba66c'})[b.color]:'#b8b4ec'};width:${Math.min(pct,100)}%` }):null),m.dias!==null?h('span',{'aria-label':m.total_dias?`${m.dias} días con horas positivas observadas de ${m.total_dias} días del rango; cobertura parcial.`:`${m.dias} días con horas positivas observadas de la muestra disponible; no cobertura completa del rango.`,title:m.detalle||'Sólo fechas observadas de la serie diaria disponible; no cobertura completa del rango ni del total mensual.'},m.total_dias?`${m.dias}/${m.total_dias} días`:`${m.dias} obs.`):missing(),m.ultima?h('span',{title:m.detalle||'Última fecha observada en la serie diaria disponible, no última imputación de todo el mes.'},m.ultima):missing('Último registro dentro del rango sin acreditar')];});
     const from=h('input',{type:'date',value:range?.desde||'','aria-label':'Desde',on:{change:e=>{if(!vivo())return;range={...range,desde:e.target.value};selected='';pintar();}}}),to=h('input',{type:'date',value:range?.hasta||'','aria-label':'Hasta',on:{change:e=>{if(!vivo())return;range={...range,hasta:e.target.value};selected='';pintar();}}});
     const medidas=people.map(p=>horasRango262(p,H,range,serie90(p)).valor).filter(num),total=medidas.length?medidas.reduce((a,b)=>a+b,0):null,teamPct=total!==null&&ref?.horas>0&&people.length?total/(ref.horas*people.length)*100:null,above=medidas.length&&ref?.horas>0?medidas.filter(x=>x/ref.horas>=.9).length:null;
     zona.append(h('section',{class:'oe-panel'},h('div',{class:'oe-chips'},[['semant','Semana pasada'],['sem','Esta semana'],['mesant','Mes pasado'],['mes','Este mes'],['30','Últimos 30 días']].map(([id,label])=>h('button',{type:'button','aria-pressed':selected===id,on:{click:()=>{if(!vivo())return;range=rango262(today,id);selected=id;pintar();}}},label))),h('div',{class:'oe-range'},h('label',{},'Desde',from),h('label',{},'Hasta',to),h('span',{class:'oe-sub'},`Referencia8h × ${ref?.dias??'—'} laborables = ${ref?.horas??'—'}h · no capacidad contractual`)),h('div',{class:'oe-kpis'},[['Equipo · referencia',teamPct!==null?`${fmtPorcentajeMinimo262(teamPct)} ref.`:null],['A cero',null],['Al menos 90 % ref.',above]].map(([x,n])=>h('div',{class:'oe-kpi'},x,h('strong',{},typeof n==='string'?n:fmt(n)),h('small',{},x==='Equipo · referencia'?'Porcentaje mínimo observado':x==='A cero'?'Sin cobertura para afirmarlo':'No evalúa cumplimiento'))))));
     zona.append(table('Por persona',INVENTARIO_EQUIPO_262.horas[0],rows,`${range?.desde||'—'} → ${range?.hasta||'—'} · menor → mayor observado · referencias y sin dato al final`),leyendaHoras381(h,'porcentaje'));
     const cs=arr(PR?.proyectos),counts=new Map();for(const p of cs)counts.set(p?.cliente_id,(counts.get(p?.cliente_id)||0)+1);
     const clienteFilas555=cs.filter(p=>p?.cliente_id&&counts.get(p.cliente_id)===1&&clienteHoras262(ctx,p.cliente_id)).map(p=>{const m=horasProyectoRango262(p,PR,range,ctx.hoy),mensual=pautaProyectoRango262(ctx,PAUTA,p.cliente_id,range?{desde:range.desde.slice(0,7)+'-01',hasta:range.hasta}:null,m);return {proyecto:p,medicion:m,pauta:pautaProporcional306(mensual,range,ctx.hoy,m),autorizada:permisoPauta262(ctx,p.cliente_id)};});
     const ordenClientes555=ordenarHorasCliente555(clienteFilas555,range,ctx.hoy);
     zona.append(table('Por cliente',INVENTARIO_EQUIPO_262.horas[1],ordenClientes555.filas.map(({proyecto:p,medicion:m,pauta})=>{
       return [p.cliente||p.nombre||p.cliente_id,valor(m.valor,m.detalle),pauta?h('span',{'aria-label':'Horas de pauta económica mensual proporcional de referencia, no presupuesto contractual.',title:`${pauta.detalle} Lectura ${pauta.fecha}; fuente ${pauta.fuente}.`},`${fmt(pauta.horas)} h`):missing('Sin pauta económica mensual autorizada y compatible; no se presume cero.'),pauta?.porcentaje!==null&&pauta?.porcentaje!==undefined?h('span',{class:pauta.porcentaje>130?'oe-ref ref-ambar':'','aria-label':'Porcentaje mínimo observado sobre pauta económica mensual proporcional de referencia, no capacidad ni cumplimiento contractual.',title:`Referencia original: aviso por encima del130%; una copia parcial no acredita bajo consumo ni cumplimiento. Horas observadas / pauta mensual × ${pauta.laborables} laborables /21 (${pauta.periodo}). Numerador parcial; no acredita consumo total, capacidad ni cumplimiento contractual.`},porcentajeMinimo555(pauta.porcentaje)):missing('Porcentaje sólo entre el mismo mes y pauta positiva autorizada; no equivale a presupuesto.')];
     }),`${range?.desde||'—'} → ${range?.hasta||'—'} · fuente ${PR?.fuentes?.horas?.hora||PR?.generado||'sin fecha'} · pauta × laborables /21 de referencia, no presupuesto contractual · ${ordenClientes555.detalle}`));
   };root.append(zona);pintar();root.append(h('details',{},h('summary',{},'Fuente de las horas'),h('p',{},fuenteHistorial+' · copia base '+(H?.generado||'sin fecha')+'. Los días sin registros no equivalen a cero. Las horas se atribuyen al día de inicio; no acreditan jornada completa.')),ref('Artifact original: 8 h por laborable y objetivo 90%; pauta por cuota dividida por tarifa. Se conservan columnas y controles, pero no se calculan capacidad universal, presupuestos ni cumplimiento. Rango libre: sólo se suman observaciones locales disponibles, no se extrapolan los cinco días al mes.'));
 }else if(ruta==='alerta-personas'){
   const ps=unicos262(E?.personas).filter(p=>p.alerta);
   root.append(table('Personas en alerta',INVENTARIO_EQUIPO_262[ruta][0],ps.map(p=>[nombre(p),h('div',{},arr(p.alerta?.motivos).map(m=>h('span',{class:'oe-sub'},typeof m==='string'?m:typeof m?.texto==='string'?m.texto:'Motivo registrado sin texto compatible')))]),`Fuente ${E?._meta?.generado||E?._meta?.fecha||'sin fecha'}`),ref('Motivos de la fuente autorizada, no evaluación automática ni propuesta de salida. Referencia original: mantener/formar/reorientar/salida y nota1–10; requiere revisión humana. Ausencia de fila no certifica normalidad.'));
 }else if(ruta==='anomalias'){
   const rows=arr(H?.raras).filter(r=>names.has(r?.persona_id)),zona=h('div');let filtro='';
   const pintar=()=>{if(!vivo())return;zona.replaceChildren(table('Horas para revisar',INVENTARIO_EQUIPO_262[ruta][0],rows.filter(r=>!filtro||r.persona_id===filtro).map(r=>[h('span',{},names.get(r.persona_id),h('small',{},r.fecha||'Fecha desconocida')),h('span',{},r.tarea||'Tarea sin texto',h('small',{},r.tipo||'Tipo desconocido')),valor(r.horas),r.motivo||'Motivo sin dato',controlAnomalia276(ctx,r)]),`Fuente ${H?.generado||'sin fecha'} · registros señalados, no acusaciones`));};
   root.append(h('div',{class:'oe-range'},h('label',{},'Persona',h('select',{'aria-label':'Persona en horas para revisar',on:{change:e=>{if(!vivo())return;filtro=e.target.value;pintar();}}},h('option',{value:''},'Todas'),[...new Set(rows.map(r=>r.persona_id))].map(id=>h('option',{value:id},names.get(id)))))),zona);pintar();
 }else if(ruta==='tipos-tarea'){
   const agrupaciones=await renderAgrupaciones376(h,ctx);if(!vivo())return false;root.append(agrupaciones);
 }else if(ruta==='notas'){
   const catalogo=arr(ctx.datos?.personas),counts=new Map();for(const p of catalogo)counts.set(p?.id,(counts.get(p?.id)||0)+1);
   const filas=catalogo.filter(p=>typeof p?.id==='string'&&counts.get(p.id)===1&&p.estado==='activo'&&p.activo!==false&&ctx.ver?.({tipo:'notas_persona',persona_id:p.id})?.ok===true).map(p=>{
     const hp=people.find(x=>x.persona_id===p.id);
     return {persona_id:p.id,nombre:p.alias||p.nombre||p.id,horas_semana_pasada:observacionesSemana281(hp,today,true),horas_esta_semana:observacionesSemana281(hp,today,false)};
   });
   panelEquipoNotas281(root,ctx,filas,{hoy:today});
 }else if(ruta==='planificacion'){
   const creadores491=prPeople.filter(p=>ctx.servidor!==true||(arr(ctx.datos?.personas).filter(q=>q?.id===p.persona_id).length===1&&arr(ctx.datos?.personas).some(q=>q.id===p.persona_id&&q.estado==='activo'&&q.activo!==false)&&ctx.ver?.({tipo:'horas_persona',persona_id:p.persona_id})?.ok===true));
   const source=planificacionBaseline(PR||{},creadores491),by=new Map(creadores491.map(p=>[p.persona_id,p])),comparacion=comparacionCreadores320(ctx,PR),adicional=comparacion.size>0;
   const actuales=creadores491.flatMap(p=>{const c=creadasSemana287(p,PR,ctx.hoy),m=p._evidencia_equipo_275;return c&&c.valor!==null&&m?[{...m,detalle:c.detalle}]:[];});
   const firmasActuales=[...new Set(actuales.map(m=>m.lunes+'|'+m.corte))],firmasAnteriores=[...new Set([...comparacion.values()].map(m=>m.desde+'|'+m.hasta_exclusiva+'|'+m.corte))];
   const actual=firmasActuales.length===1?actuales[0]:null,anterior=firmasAnteriores.length===1?[...comparacion.values()][0]:null;
   const diaCorte=m=>new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(m.corte));
   const cabecera=h('span',{},
     actuales.length?h('small',{title:actuales.map(m=>m.detalle).join(' · ')},actual?`Creadas actuales ${actual.lunes} → ${diaCorte(actual)} · corte ${actual.corte}`:'Creadas actuales: cortes distintos; consulta cada celda'):null,
     adicional?h('small',{title:anterior?.detalle||'Cortes de comparación distintos; consulta cada celda'},anterior?`Creadas anteriores ${anterior.desde} → ${anterior.hasta_exclusiva} (fin exclusivo) · corte ${anterior.corte}`:'Creadas anteriores: cortes distintos; consulta cada celda'):null,
     h('small',{},`Legado planificación · semana ${PR?.lunes||'sin fecha'} · fuente ${source.fecha||'sin fecha'}; no es el corte de creaciones`));
   const columnas=adicional?[...INVENTARIO_EQUIPO_262[ruta][0].slice(0,6),'Creadas semana pasada',...INVENTARIO_EQUIPO_262[ruta][0].slice(6)]:INVENTARIO_EQUIPO_262[ruta][0];
   const firmaPlanning491=()=>{
     if(!vivo()||!ctx.veModulo?.('produccion'))return null;
     const ps=arr(ctx.datos?.personas),actors=[ctx.real,ctx.persona];
     if(ctx.servidor===true&&!actors.every(a=>{const xs=ps.filter(p=>p?.id===a?.id);return typeof a?.id==='string'&&xs.length===1&&a.estado==='activo'&&a.activo!==false&&xs[0].estado==='activo'&&xs[0].activo!==false&&Array.isArray(a.puestos)&&a.puestos.length>0&&new Set(a.puestos).size===a.puestos.length&&a.puestos.every(x=>typeof x==='string')&&Array.isArray(xs[0].puestos)&&new Set(xs[0].puestos).size===xs[0].puestos.length&&JSON.stringify([...a.puestos].sort())===JSON.stringify([...xs[0].puestos].sort());}))return null;
     if(ctx.servidor===true&&!arr(PR?.proyectos).every(p=>{const cid=p?.cliente_id,canon=arr(ctx.clientes).filter(c=>c?.id===cid),visible=arr(ctx.clientesVisibles).filter(c=>c?.id===cid);return typeof cid==='string'&&canon.length===1&&visible.length===1&&[canon[0],visible[0]].every(c=>c.activo_confirmado===true&&c.activo!==false&&c.estado!=='baja'&&c.detalle===true)&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:cid})?.ok===true;}))return null;
     return JSON.stringify([actors,ctx.hoy,ps,ctx.clientes,ctx.clientesVisibles,prPeople.map(p=>[p.persona_id,ctx.ver?.({tipo:'horas_persona',persona_id:p.persona_id})?.ok]),arr(ctx.clientesVisibles).map(c=>[c.id,ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok])]);
   };
   const firma491=firmaPlanning491(),actual491=()=>{const ok=firma491!==null&&firmaPlanning491()===firma491;if(!ok)root.replaceChildren();return ok;};
   if(!actual491())return false;
   const fuente681=fuentePlanning681(creadores491,PR,{hoy:ctx.hoy,vigente:actual491});if(fuente681)cabecera.append(h('small',{},fuente681));
   // El inventario observado se presenta antes de la matriz histórica de disciplina.
   await panelPlanningObservado360(root,ctx);
   if(!actual491())return false;
   const modelos491=creadores491.map(p=>{const actual=creadasSemana287(p,PR,ctx.hoy),anterior=comparacion.get(p.persona_id);return {id:p.persona_id,nombre:nombre(p),observado:[actual?.valor,anterior?.valor,...['al_planning','fuegos_directos','rompen_semanal'].map(k=>metricaPlanning681(p,PR,k,{hoy:ctx.hoy,vigente:actual491})?.valor)].some(v=>typeof v==='number'&&Number.isFinite(v)&&v>=0)};});
   let filtro491='observados',busqueda491='';
   const selector491=h('select',{'aria-label':'Cobertura de creadores',on:{change:()=>{if(!actual491())return;filtro491=selector491.value;pintar491();}}},
     h('option',{value:'observados'},'Con observaciones'),h('option',{value:'todos'},'Todos'),h('option',{value:'pendientes'},'Cobertura pendiente'));
   selector491.value='observados';
   const buscar491=h('input',{type:'search',placeholder:'Buscar creador','aria-label':'Buscar creador',style:{minWidth:'0',flex:'1 1 180px',maxWidth:'280px'},on:{input:()=>{if(!actual491())return;busqueda491=buscar491.value||'';pintar491();}}});
   const zona491=h('div',{'data-planning-creadores491':''}),cuenta491=h('span',{class:'oe-sub',role:'status'});
   root.append(h('div',{class:'oe-range','data-planning-filtros491':''},selector491,buscar491,cuenta491),zona491);
   const filas491=creadores491.map(p=>({...p,...source.filas.find(f=>f.persona_id===p.persona_id)})).map(p=>[nombre(by.get(p.persona_id)),(()=>{const c=creadasSemana287(by.get(p.persona_id),PR,ctx.hoy);return c?c.valor===null?missing(c.detalle):h('span',{title:c.detalle},'≥'+fmt(c.valor)):valor(p.creadas,'Referencia de creación en la copia, no historia de entrada al planning');})(),celdaPlanning681(p,PR,'al_planning',{h,hoy:ctx.hoy,vigente:actual491}),celdaPlanning681(p,PR,'fuegos_directos',{h,hoy:ctx.hoy,vigente:actual491}),celdaPlanning681(p,PR,'rompen_semanal',{h,hoy:ctx.hoy,vigente:actual491}),missing('Rupturas de planificación de la semana pasada: sin historial acreditado; no equivale a creaciones'),...(adicional?[(()=>{const c=comparacion.get(p.persona_id);return c&&c.valor!==null?h('span',{title:c.detalle},'≥'+fmt(c.valor)):missing(c?.detalle||'Sin comparación de creaciones autorizada compatible');})()]:[]),missing('Ejemplos legacy sin referencia exacta; consulta la fuente independiente por creador')]);
   function pintar491(){
     if(!actual491())return;
     const term=busqueda491.trim().toLocaleLowerCase('es');
     const ids=new Set(modelos491.filter(m=>(filtro491==='todos'||(filtro491==='observados'?m.observado:!m.observado))&&m.nombre.toLocaleLowerCase('es').includes(term)).map(m=>m.id));
     const visibles=filas491.filter((_,i)=>ids.has(creadores491[i].persona_id));
     cuenta491.replaceChildren(`${visibles.length}/${modelos491.length} creadores · ${modelos491.filter(m=>m.observado).length} con observaciones`);
     zona491.replaceChildren(table('Disciplina de planificación',columnas,visibles,cabecera),ref(source.detalle+' Semana pasada conserva rupturas de planificación desconocidas. Creadas semana pasada es una comparación adicional, no sustituye ese KPI. Referencia original: mensual → semanal → diario,3porpersona/5porproyecto; no aplicar a nombres ni snapshot actual como si fueran transiciones históricas. El filtro Con observaciones utiliza sólo creaciones con descriptor aceptado; la referencia legacy no acredita una observación.'));
   }
   pintar491();
   root.__planningVigente491=actual491;
 }
 if(ruta==='planificacion'&&PR&&vivo())root.append(panelComparacionSemanal296(ctx,PR));

 if(ruta==='planificacion'&&vivo())await panelEjemplosCreador438(root,ctx);
 if(!vivo()||(ruta==='planificacion'&&root.__planningVigente491&&!root.__planningVigente491())){root.replaceChildren();return false;}
 if(fallos.length)root.append(h('p',{class:'oe-note'},'Parte de las fuentes no está disponible en este ámbito. Las celdas desconocidas no equivalen a cero.'));
 return true;
}
