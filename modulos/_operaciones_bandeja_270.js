import {catalogoAccounts340,filtrarAccount340,gruposAccount340,SIN_ACCOUNT340} from './_bandeja_accounts_340.js';
import {crearConsultasPedidos294,crearPedidoAccount294,renderColaPedidosAccount294} from './_pedidos_account_local.js';
import { renderFeedback273 } from './_operaciones_feedback_273.js';
import { semanticaMeta285 } from './_meta_semantica_285.js';
//270 · vBandeja719 + vTriaje899 + vLeadsFb886. Lectura scoped; ningún envío.
import {h,chipEstado} from '../componentes.js';
export const COLUMNAS_FB270=['Conseguida','Cliente','Leads 30 días','Qué dijo'];
export const COLUMNAS_TRIAJE270=['Ticket','Propuesta','Por qué',''];
export const GRUPOS_TRIAJE270=[['dudoso','Dudosos: confirma la propuesta','ambar'],['seguro','Claros: asígnalos tal cual','verde'],['sin_cliente','Sin cliente: decide tú','rojo'],['ruido','Ruido interno','gris']];
const arr=v=>Array.isArray(v)?v:[];
const num=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
const dia=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
const fecha=(v,hoy)=>typeof v==='string'&&dia(v.slice(0,10))&&v.slice(0,10)<=hoy&&Number.isFinite(Date.parse(v.replace(' ','T')))?v:null;
const unicos=xs=>arr(xs).filter(x=>typeof x?.id==='string'&&x.id&&xs.filter(z=>z?.id===x.id).length===1);
export function ambitoBandeja335(ctx){
 try{
  const ps=[ctx.real,ctx.persona];if(!ctx.servidor||!ctx.veModulo?.('bandeja')||typeof ctx.ver!=='function'||!ps.every(p=>typeof p?.id==='string'&&p.estado==='activo'&&p.activo!==false))return null;
  const ids=unicos(arr(ctx.clientesVisibles)).filter(c=>c.activo_confirmado===true&&c.detalle===true&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
  const cuentas=catalogoAccounts340(ctx,ids);
  return {ids,firma:JSON.stringify([cuentas.firma,ps.map(p=>[p.id,p.estado,p.activo,p.puestos]),ctx.hoy,!!ctx.soloLectura,ids,['bandeja','captacion','ficha'].map(m=>[m,ctx.veModulo?.(m)===true])])};
 }catch{return null;}
}
export const historicoCorreo335=x=>x?.viejo===true||(Number.isSafeInteger(x?.dias_laborables)&&x.dias_laborables>22);
function fuente270(D,key,hoy){const x=D?.fuentes?.[key],a=fecha(x?.hora,hoy),b=fecha(D?.generado,hoy);return a&&b&&Date.parse(a.replace(' ','T'))<=Date.parse(b.replace(' ','T'))&&['bien','dato_viejo'].includes(x?.estado)?{fecha:a,historica:x.estado==='dato_viejo'}:null;}
export function muestraLeads270(c,C,hoy,cliente={}){
 const fin=C?.ventanas?.serie?.[1];if(!dia(hoy)||!dia(fin)||fin>hoy)return null;
 const d=new Date(fin+'T00:00:00Z');d.setUTCDate(d.getUTCDate()-29);const desde=d.toISOString().slice(0,10);
 const xs=arr(c?.serie).filter(x=>dia(x?.d)&&x.d>=desde&&x.d<=fin);if(new Set(xs.map(x=>x.d)).size!==xs.length)return null;
 // Cero heredado sin descriptor no acredita cobertura completa; mínimos positivos no son leads únicos ni calidad.
 const semantica=semanticaMeta285(xs,cliente,hoy);
 const pos=xs.filter(x=>Number.isSafeInteger(x.leads_meta)&&x.leads_meta>=0&&(x.leads_meta>0||semantica.eventos_lead_acreditados));
 const valor=pos.reduce((s,x)=>s+x.leads_meta,0);
 return pos.length&&Number.isSafeInteger(valor)?{valor,desde,hasta:fin,dias:xs.length,cobertura:'parcial',semantica}:null;
}
function inicioLlamadas270(hoy){const d=new Date(hoy+'T00:00:00Z');let n=0;while(n<5){const w=d.getUTCDay();if(w>0&&w<6)n++;if(n<5)d.setUTCDate(d.getUTCDate()-1);}return d.toISOString().slice(0,10);}
export function prepararBandeja270(ctx,B,C){
 const ids=[ctx.real,ctx.persona],ambito=ambitoBandeja335(ctx),permitido=!!ambito;
 if(!permitido||!dia(ctx.hoy))return {permitido:false,correos:[],llamadas:[],triaje:[],feedback:[],fuentes:{}};
 const catalogo=arr(ctx.clientesVisibles),clientes=new Map(unicos(catalogo).filter(c=>c.activo_confirmado===true&&c.detalle===true&&ambito.ids.includes(c.id)).map(c=>[c.id,c]));
 const ops=ids.every(p=>arr(p.puestos).some(x=>['direccion','operaciones'].includes(x)));
 const scope=x=>clientes.has(x?.cliente_id),cl=x=>({...x,nombre_cliente:clientes.get(x.cliente_id)?.nombre||'Sin cliente confirmado'});
 const desk=fuente270(B,'desk',ctx.hoy),z=fuente270(B,'zadarma',ctx.hoy);
 if(desk){const deps=arr(B?.departamentos);if(deps.length&&deps.every(x=>typeof x?.legible==='boolean'))desk.cobertura=`${deps.filter(x=>x.legible).length} de ${deps.length} departamentos legibles`;}
 const correos=unicos(arr(B?.correos)).filter(scope).map(cl);
 const llamadas=unicos(arr(B?.llamadas)).filter(scope).filter(x=>dia(x.ultima?.slice(0,10))&&x.ultima.slice(0,10)<=ctx.hoy&&x.ultima.slice(0,10)>=inicioLlamadas270(ctx.hoy)&&Number.isSafeInteger(x.dias_laborables)&&x.dias_laborables>=0&&x.dias_laborables<=5).map(cl);
 const triaje=unicos(arr(B?.triaje)).filter(x=>scope(x)||(!x.cliente_id&&ops)).filter(x=>GRUPOS_TRIAJE270.some(g=>g[0]===x.propuesta)).map(cl);
 const feedback=[];if(ctx.veModulo?.('captacion'))for(const c of clientes.values()){
   const paid=arr(C?.clientes).filter(x=>x?.cliente_id===c.id);if(paid.length!==1)continue;
   const muestra=muestraLeads270(paid[0],C,ctx.hoy,c);
   if(muestra)feedback.push({cliente_id:c.id,nombre_cliente:c.nombre,muestra});
 }
 feedback.sort((a,b)=>b.muestra.valor-a.muestra.valor);
 return {permitido:true,correos,llamadas,triaje,feedback,fuentes:{desk,zadarma:z},captacion_disponible:!!C};
}
function tabla270(titulo,cols,rows,celda,nota=''){
 return h('section',{class:'ob-panel270'},h('header',{},h('h2',{},titulo),nota?h('small',{},nota):null),h('div',{class:'ob-scroll270'},h('table',{},h('thead',{},h('tr',{},cols.map(t=>h('th',{scope:'col'},t)))),h('tbody',{},rows.length?rows.map(r=>h('tr',{},cols.map((_,i)=>h('td',{},celda(r,i))))):h('tr',{},h('td',{colspan:cols.length},'Sin filas observadas compatibles; no acredita ausencia de actividad ni inventario completo.'))))));
}
const CSS270=`.ob270{display:grid;gap:16px;font-family:system-ui,sans-serif;color:#10132b}.ob-panel270{background:white;border:1px solid #e1e4f1;border-radius:14px;overflow:hidden}.ob-panel270 header{padding:14px 18px;border-bottom:1px solid #eceef7;display:flex;flex-wrap:wrap;gap:6px 16px;align-items:baseline}.ob-panel270 h2{font-size:15px;margin:0}.ob-panel270 small{color:#777d9b;font-size:12px}.ob-scroll270{overflow:auto;padding:4px 14px 10px}.ob270 table{border-collapse:collapse;width:100%;min-width:760px;font-size:13px}.ob270 td,.ob270 th{padding:10px 8px;border-bottom:1px solid #eceef7;text-align:left;vertical-align:middle}.ob270 th{font-size:11px;text-transform:uppercase;color:#777d9b}.ob270 .filters270{display:flex;flex-wrap:wrap;gap:8px}.ob270 details>summary{cursor:pointer;padding:10px 14px}.ob270 details p{padding:0 14px;font-size:13px}.ob270 button[disabled]{opacity:.65;cursor:not-allowed}`;
export async function renderBandeja270(cont,ctx,params=[]){
 const root=h('div',{class:'ob270'});cont.append(root);const inicial=ambitoBandeja335(ctx);
 const vigente=()=>{const a=ambitoBandeja335(ctx),ok=!!inicial&&root.isConnected&&(!ctx.vigente||ctx.vigente())&&a?.firma===inicial.firma;if(!ok)root.replaceChildren();return ok;};
 if(!vigente())return;
 const leer=async(mod,p)=>{if(!ctx.veModulo(mod))return null;try{return await ctx.datosModulo(p);}catch{return null;}};
 const [B,C]=await Promise.all([leer('bandeja','bandeja/bandeja'),leer('captacion','captacion/captacion')]);if(!vigente())return;
 const d=prepararBandeja270(ctx,B,C);if(!d.permitido)return;
 const guardia=e=>{if(!vigente()){e?.preventDefault?.();return false;}return true;};
 const enlace=x=>h('a',{on:{click:guardia},href:`#/bandeja/${encodeURIComponent(x.id)}`},`${x.numero||'Abrir'}${x.asunto?' · '+x.asunto:''}`);
 const cli=x=>ctx.veModulo('ficha')&&x.cliente_id?h('a',{on:{click:guardia},href:`#/ficha/${encodeURIComponent(x.cliente_id)}`},x.nombre_cliente):x.nombre_cliente;
 root.replaceChildren(h('style',{},CSS270));
 const consultasPedidos=crearConsultasPedidos294(ctx);
 const colaPedidos=h('div',{});root.append(colaPedidos);renderColaPedidosAccount294(colaPedidos,ctx,consultasPedidos);
 root.append(h('nav',{class:'filters270'},h('a',{href:'#/bandeja',class:'bt mini'},'Contestar y gestionar en Bandeja'),h('a',{href:'#/bandeja',class:'bt mini'},'Abrir reparto en Bandeja')));
 let min=24,account='';const cuentas=catalogoAccounts340(ctx,inicial.ids);const zona=h('div',{}),filters=h('div',{class:'filters270'});
 const pintarCorreos=()=>{if(!vigente())return;const xs=filtrarAccount340(d.correos,cuentas,account).filter(x=>!x.auto&&!x.boletin&&num(x.horas)&&x.horas>=min).sort((a,b)=>Number(!!b.queja)-Number(!!a.queja)||b.horas-a.horas);
   const nota=d.fuentes.desk?`Lectura ${d.fuentes.desk.fecha} · copia parcial${d.fuentes.desk.historica?' histórica':''}${d.fuentes.desk.cobertura?' · '+d.fuentes.desk.cobertura:''}`:'Fecha de lectura de Desk sin confirmar';
   const tabla=(titulo,filas)=>tabla270(titulo,['Cliente','Ticket','Espera al corte','Pedido al account'],filas,(x,i)=>[()=>h('div',{},cli(x),x.queja?chipEstado('gris','Queja en la copia'):null),()=>enlace(x),()=>h('span',{title:`${x.horas>48?'Supera48 h':x.horas>24?'Supera24 h':'Hasta24 h'} en la copia. Estado y último mensaje actuales por contrastar.`},chipEstado('gris',`${x.horas} h`),h('small',{},x.estado_desk||'Estado por confirmar')),()=>crearPedidoAccount294(ctx,{cliente_id:x.cliente_id,tipo:'responder_correo',referencia_id:x.id},consultasPedidos).elemento][i](),nota);
   const agrupadas=(titulo,filas)=>h('section',{class:'ob-panel270'},h('header',{},h('h2',{},titulo),h('small',{},`${filas.length} registros observados · ${nota}`)),...gruposAccount340(filas,cuentas).map(g=>h('details',{open:!!account||g.rows.some(x=>x.queja===true),on:{toggle:guardia}},h('summary',{},`${g.nombre}${g.por_confirmar?' · asignación por confirmar':''} · ${g.rows.length}`),tabla('Tickets observados',g.rows))),filas.length?null:h('p',{},'Sin filas observadas para este filtro; copia parcial.'));
   const actuales=xs.filter(x=>!historicoCorreo335(x)),historicos=xs.filter(historicoCorreo335);
   zona.replaceChildren(h('p',{class:'sub',role:'status'},`${xs.length} correos observados con el filtro · ${actuales.length} recientes · ${historicos.length} históricos`),agrupadas('Copia de tickets pendientes · por contrastar',actuales),h('details',{on:{toggle:guardia}},h('summary',{},`Saneamiento histórico · ${historicos.length} registros observados`),agrupadas('Más de22 días laborables en la copia',historicos),h('p',{},'Conserva también las quejas antiguas. Verifica en Bandeja el último mensaje y si corresponde responder, esperar al cliente o cerrar.')));
 };
 for(const [v,t]of [[24,'Más de 24 h'],[48,'Más de 48 h'],[0,'Todos']])filters.append(h('button',{type:'button',class:'bt mini',on:{click:()=>{if(vigente()){min=v;pintarCorreos();}}}},t));
 const selector=h('select',{'aria-label':'Account',style:{minHeight:'44px'},on:{change:e=>{if(!vigente())return;const v=e.target.value;if(v!==''&&v!==SIN_ACCOUNT340&&!cuentas.cuentas.some(c=>c.id===v))return;account=v;pintarCorreos();pintarLlamadas();pintarTriaje();}}},h('option',{value:''},'Todos los accounts'),...cuentas.cuentas.map(c=>h('option',{value:c.id},c.nombre)),h('option',{value:SIN_ACCOUNT340},'Sin asignación inequívoca'));
 filters.append(h('label',{},'Account ',selector));
 root.append(filters,zona);pintarCorreos();
 const zonaLlamadas=h('div',{});root.append(zonaLlamadas);
 const pintarLlamadas=()=>{if(!vigente())return;zonaLlamadas.replaceChildren(tabla270('Llamadas de clientes perdidas y sin devolver',['Pedido devolver','Cliente','Llamadas / última','Responsable'],filtrarAccount340(d.llamadas,cuentas,account),(x,i)=>[()=>crearPedidoAccount294(ctx,{cliente_id:x.cliente_id,tipo:'devolver_llamada',referencia_id:x.id},consultasPedidos).elemento,()=>cli(x),()=>h('span',{},`${num(x.llamadas)?x.llamadas:'—'} · ${x.ultima}`),()=>h('span',{},'Consultar en Bandeja')][i](),d.fuentes.zadarma?`Zadarma · últimos5 días laborables según DTO · lectura ${d.fuentes.zadarma.fecha} · parcial`:'Sin lectura de Zadarma confirmada; la ausencia no acredita cero llamadas.'));};pintarLlamadas();
 const zonaTriaje=h('div',{});root.append(zonaTriaje);
 const pintarTriaje=()=>{if(!vigente())return;
 const triaje=h('section',{class:'ob-panel270'},h('header',{},h('h2',{},'Tickets sin asignar'),h('small',{},'Propuestas de la copia; asignar en Desk no se confirma por una marca local.')));
 for(const [g,t,color]of GRUPOS_TRIAJE270){const xs=filtrarAccount340(d.triaje,cuentas,account).filter(x=>x.propuesta===g).sort((a,b)=>(b.fecha||'').localeCompare(a.fecha||''));triaje.append(h('details',{open:g==='dudoso'||g==='seguro'},h('summary',{},t,' ',chipEstado(xs.length?color:'gris',String(xs.length)+' observados')),tabla270(t,COLUMNAS_TRIAJE270,xs,(x,i)=>[()=>h('span',{},`${x.numero||'Ticket'}${x.asunto?' · '+x.asunto:''}`),()=>h('div',{},cli(x),h('small',{},x.agente_propuesto_id?ctx.nombre?.(x.agente_propuesto_id)||'Responsable por confirmar':'Responsable por confirmar')),()=>x.motivo||'Sin evidencia de propuesta',()=>h('a',{href:'#/bandeja',class:'bt mini',title:'En Bandeja: abre Correos sin responsable. Este ticket de triaje no tiene ruta de conversación individual.'},'Abrir reparto')][i]())));}
 zonaTriaje.replaceChildren(triaje);
 };pintarTriaje();
 await renderFeedback273(root,ctx,d.feedback);
 if(!vigente())return;
 root.append(h('details',{},h('summary',{},'Fuentes, ausencias y acciones'),h('p',{},'Listas recortadas por identidad y cliente activo. ≥: mínimo observado de Meta de 30 días; no califica leads ni acredita ventas. El feedback permite registrar por separado una opinión pedida o conseguida, con autor y fecha. Los pedidos se registran en RO y se ven en la cola del account; resolver es una declaración, no un envío o llamada acreditados. Respuestas y asignaciones se gestionan en Bandeja.')));
}
