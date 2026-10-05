import {metricasCampanas448} from './_metricas_campanas_448.js';
// Medición Meta observada386: sólo lectura del piloto privado385, sin acciones externas.
const arr=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
const dia=x=>{if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x))return false;const n=new Date(x+'T00:00:00Z');return Number.isFinite(+n)&&n.toISOString().slice(0,10)===x;};
const valor=(x,entero=false)=>x===null||(typeof x==='number'&&Number.isFinite(x)&&x>=0&&(!entero||Number.isSafeInteger(x)));
export function ambitoMeta386(ctx,cid){try{
 if(ctx.servidor!==true||ctx.vigente?.()===false||ctx.veModulo?.('captacion')!==true||!id(cid))return null;
 const ps=arr(ctx.datos?.personas),actors=[ctx.real,ctx.persona];
 for(const p of actors){const xs=ps.filter(x=>x?.id===p?.id);if(!id(p?.id)||xs.length!==1||xs[0].estado!=='activo'||xs[0].activo===false||p.estado!=='activo'||p.activo===false||!Array.isArray(p.puestos)||!p.puestos.length||new Set(p.puestos).size!==p.puestos.length||!p.puestos.every(id)||!Array.isArray(xs[0].puestos)||JSON.stringify([...p.puestos].sort())!==JSON.stringify([...xs[0].puestos].sort()))return null;}
 const actual=arr(ctx.clientes),vis=arr(ctx.clientesVisibles),cs=[actual,vis].map(xs=>xs.filter(x=>x?.id===cid));
 if(cs.some(xs=>xs.length!==1||xs[0].activo_confirmado!==true||xs[0].detalle===false)||ctx.ver?.({tipo:'cliente_detalle',cliente_id:cid})?.ok!==true)return null;
 return JSON.stringify([actors,ps,actual,vis,ctx.veModulo('captacion'),ctx.ver({tipo:'cliente_detalle',cliente_id:cid}),ctx.ver({tipo:'inversion',cliente_id:cid})]);
 }catch{return null;}}
export function modeloMeta386(dto,cid){try{
 if(dto?.version!=='385.1'||dto.cliente_id!==cid||dto.estado!=='copia_observada')return null;
 const m=dto.medicion,p=m?.periodo;
 if(m?.version!=='384.1'||m.cliente_id!==cid||m.nivel!=='campaign_diario'||m.cobertura!=='filas_recibidas_no_censo'||!dia(p?.desde)||!dia(p?.hasta)||p.desde>p.hasta||typeof p.zona!=='string'||typeof m.paginas_completas!=='boolean'||!Array.isArray(m.errores_tipados)||m.contactos_unicos!==null||m.leads_calificados!==null||m.ventas!==null||!Array.isArray(m.dias))return null;
 new Intl.DateTimeFormat('es-ES',{timeZone:p.zona});
 const n=(Date.parse(p.hasta)-Date.parse(p.desde))/864e5+1;
 if(n<1||n>366||m.dias.length!==n||!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(m.fecha_fuente||'')||!Number.isFinite(Date.parse(m.fecha_fuente)))return null;
 const gasto=Object.hasOwn(m,'gasto_observado');
 if(gasto&&(!valor(m.gasto_observado)||typeof m.moneda!=='string'||!/^[A-Z]{3}$/.test(m.moneda)))return null;
 const rows=[];
 for(let i=0;i<n;i++){const r=m.dias[i],esperado=new Date(Date.parse(p.desde)+i*864e5).toISOString().slice(0,10);
  if(r?.dia!==esperado||!Number.isSafeInteger(r.filas_recibidas)||r.filas_recibidas<0||!valor(r.leads_observados,true)||!valor(r.impresiones_observadas,true)||!valor(r.clics_observados,true)||(gasto&&!valor(r.gasto_observado)))return null;
  if(r.filas_recibidas===0&&[r.leads_observados,r.impresiones_observadas,r.clics_observados,...(gasto?[r.gasto_observado]:[])].some(x=>x!==null))return null;
  rows.push({dia:r.dia,leads:r.leads_observados,impresiones:r.impresiones_observadas,clics:r.clics_observados,...(gasto?{gasto:r.gasto_observado}:{})});
 }
 return {rows,gasto,moneda:gasto?m.moneda:null,zona:p.zona,fecha:m.fecha_fuente,parcial:!m.paginas_completas||m.errores_tipados.length>0};
 }catch{return null;}}
export async function renderMetaDiaria386(h,ctx,cid){
 const root=h('section',{'data-meta-diaria-386':'',class:'panel'}),firma=ambitoMeta386(ctx,cid),vivo=()=>firma&&ambitoMeta386(ctx,cid)===firma;
 if(!firma)return root;
 let dto;try{dto=await ctx.api('paid/mediciones-diarias/'+cid);}catch{if(vivo())root.append(h('p',{class:'sub'},'Medición diaria reciente pendiente de confirmar.'));return root;}
 if(!vivo())return root;
 const m=modeloMeta386(dto,cid);if(!m){root.append(h('p',{class:'sub'},'No hay una medición diaria compatible disponible.'));return root;}
 const mostrarGasto=m.gasto&&ctx.ver?.({tipo:'inversion',cliente_id:cid})?.ok===true;
 root.append(h('header',{},h('h2',{},'Medición diaria · Meta')),h('p',{class:'sub',style:{padding:'0 16px'}},`${m.rows[0].dia} → ${m.rows.at(-1).dia} · ${m.zona} · muestra de campañas recibidas${m.parcial?' · lectura incompleta':''}. — significa sin dato; los eventos no son leads calificados.`));
 const fmt=x=>x===null?'—':new Intl.NumberFormat('es-ES',{maximumFractionDigits:2}).format(x);
 const agregado=metricasCampanas448(dto);
 if(agregado){const detalle=`${agregado.periodo.desde} → ${agregado.periodo.hasta} · ${agregado.periodo.zona} · campañas recibidas, no total de cuenta. Lectura ${agregado.fecha}${agregado.parcial?' · incompleta':''}. CTR = clics totales/impresiones; CPM = gasto/impresiones ×1000. No mide conversión ni ventas.`,metricas=[['Impr.',agregado.impresiones,''],['Clics',agregado.clics,''],['CTR tot.',agregado.ctr,'%'],...(mostrarGasto?[['Gasto',agregado.gasto,agregado.moneda],['CPM',agregado.cpm,agregado.moneda]]:[])];
  root.append(h('div',{'data-metricas-campanas-448':'',role:'group','aria-label':'Resumen de campañas recibidas',title:detalle,style:{display:'flex',flexWrap:'wrap',gap:'8px 20px',padding:'12px 16px'}},...metricas.map(([label,value,unidad])=>h('span',{'aria-label':`${label}: ${value===null?'sin dato':fmt(value)+' '+unidad}. ${detalle}`,style:{display:'inline-flex',gap:'6px',alignItems:'baseline'}},label,h('b',{},fmt(value)),value===null?null:h('small',{},unidad)))));
 }

 root.append(h('div',{style:{overflowX:'auto'}},h('table',{class:'densa'},h('thead',{},h('tr',{},[['Día','Día de la cuenta'],['Ev. lead','Eventos lead, no leads calificados'],['Impr.','Impresiones'],['Clics','Clics'],...(mostrarGasto?[['Gasto · '+m.moneda,'Gasto observado · '+m.moneda]]:[])].map(([label,full])=>h('th',{scope:'col',title:full,'aria-label':full},label)))),h('tbody',{},m.rows.map(r=>h('tr',{},[r.dia,fmt(r.leads),fmt(r.impresiones),fmt(r.clics),...(mostrarGasto?[fmt(r.gasto)]:[])].map(x=>h('td',{},x))))))));
 root.append(h('details',{on:{toggle:()=>{if(!vivo())root.replaceChildren();}}},h('summary',{},'Fuente y cobertura'),h('p',{},`Meta Insights · ${m.fecha}. Fechas de la cuenta. No acredita censo de contactos, ventas ni cualificación; no se modifican campañas.`)));
 return root;
}
