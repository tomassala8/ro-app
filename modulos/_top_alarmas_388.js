//388 · vHoy1131: selección rotativa, un cliente por tarjeta. Sólo copia autorizada342.
import {h,chipEstado} from '../componentes.js';
import {ambitoAlarmas342,proyectarAlarmas342} from './_alarmas_operaciones_342.js';
const arr=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
// Equivalencias por IDs explícitos, nunca por títulos ni coincidencias de texto.
const alertId=x=>typeof x==='string'&&x.length>0&&x.length<=300;
const grupos=[['acc_critico','Semáforo en rojo'],['alta_fuera_plazo','Cliente nuevo fuera de plazo'],['acc_correos','Sin responder'],['acc_sin_reunion'],['Revisión del account >48 h'],['Semáforo sin rellenar']];
const bucket=tipo=>{const i=grupos.findIndex(xs=>xs.includes(tipo));return i<0?'tipo:'+tipo:'original:'+i;};
export function seleccionarTop388(filas){
 const xs=arr(filas),counts=new Map();for(const x of xs)if(alertId(x?.id))counts.set(x.id,(counts.get(x.id)||0)+1);
 const candidatos=xs.filter(x=>alertId(x?.id)&&counts.get(x.id)===1&&id(x.cliente_id)&&typeof x.tipo==='string'&&x.tipo.length>0&&x.tipo.length<=300&&x.gravedad==='rojo');
 const porTipo=new Map();for(const x of candidatos){const k=bucket(x.tipo);if(!porTipo.has(k))porTipo.set(k,[]);porTipo.get(k).push(x);}
 const keys=[...porTipo.keys()].sort((a,b)=>{const ai=a.startsWith('original:')?+a.slice(9):Infinity,bi=b.startsWith('original:')?+b.slice(9):Infinity;return ai-bi||a.localeCompare(b,'es');});
 const vistos=new Set(),top=[];
 for(let ronda=0;ronda<6&&top.length<6;ronda++)for(const k of keys){const x=porTipo.get(k).find(y=>!vistos.has(y.cliente_id));if(x&&top.length<6){vistos.add(x.cliente_id);top.push(x);}}
 return top;
}
export function ambitoTop388(ctx){try{
 if(ctx.vigente?.()===false)return null;const a=ambitoAlarmas342(ctx);if(!a)return null;
 const actuales=arr(ctx.clientes),visibles=arr(ctx.clientesVisibles),ids=a.clientes.filter(cid=>[actuales,visibles].every(cs=>{const xs=cs.filter(c=>c?.id===cid);return xs.length===1&&xs[0].activo_confirmado===true&&xs[0].detalle===true;})&&ctx.ver({tipo:'cliente_detalle',cliente_id:cid})?.ok===true);
 return {ids,firma:JSON.stringify([a.firma,actuales,visibles,ids])};
 }catch{return null;}}
export function modeloTop388(ctx,D,rows=[],filtros={}){
 const scope=ambitoTop388(ctx),m=scope?proyectarAlarmas342(ctx,D,rows):null;if(!m)return null;
 const fs=m.filas.filter(x=>scope.ids.includes(x.cliente_id)&&(!filtros.account||(x.account_id||'__sin')===filtros.account)&&(!filtros.cliente||x.cliente_id===filtros.cliente)&&(!filtros.tipo||x.tipo===filtros.tipo)&&(!filtros.gravedad||x.gravedad===filtros.gravedad));
 return {top:seleccionarTop388(fs),fecha:m.fecha,cobertura:m.cobertura,registros:fs.length,clientes:new Set(fs.filter(x=>x.gravedad==='rojo').map(x=>x.cliente_id)).size,scope};
}
const CSS388=`.top388{margin:10px 0}.top388 h3{font-size:15px;margin:0}.top388 .rejilla388{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:8px}.top388 article{border:1px solid #efc8cb;border-radius:8px;background:#fff7f7;padding:10px;min-width:0}.top388 p{margin:4px 0;font-size:12px;line-height:1.4}.top388 .texto388{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.top388 summary,.top388 a{min-height:44px;display:flex;align-items:center;font-size:12px}.top388 details p{white-space:pre-wrap;overflow-wrap:anywhere}.top388 header small{font-size:11px;color:#666d89}@media(max-width:700px){.top388 .rejilla388{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:420px){.top388 .rejilla388{grid-template-columns:1fr}}`;
export function pintarTop388(cont,ctx,D,rows=[],vigente=()=>true,filtros={}){
 const root=h('section',{'data-top-alarmas':'388',class:'top388'});cont.append(root);const inicial=ambitoTop388(ctx);
 const vivo=()=>root.isConnected&&vigente()&&!!inicial&&ambitoTop388(ctx)?.firma===inicial.firma;
 const limpiar=()=>root.replaceChildren(h('p',{role:'status'},'Las prioridades no están disponibles en el ámbito actual.'));
 if(!vivo()){limpiar();return root;}const m=modeloTop388(ctx,D,rows,filtros);
 if(!m){root.append(h('p',{role:'status'},'Prioridades pendientes de una copia compatible.'));return root;}
 root.append(h('style',{},CSS388),h('header',{},h('h3',{},'Lo primero hoy · hasta 6 clientes'),h('small',{},`Señales de la copia · corte ${m.fecha} · cobertura parcial.`)));
 if(!m.top.length){root.append(h('p',{},'Sin señales rojas de cliente con estos filtros; consulta la colección completa. No acredita ausencia de incidencias.'));return root;}
 const guard=e=>{if(!vivo()){e?.preventDefault?.();limpiar();return false;}return true;};
 root.append(h('div',{class:'rejilla388'},m.top.map(a=>h('article',{'data-cliente-top':a.cliente_id},chipEstado(a.gravedad,a.tipo_label),h('p',{},h('strong',{},a.cliente)),h('p',{class:'texto388'},a.titulo),h('details',{on:{toggle:e=>guard(e)}},h('summary',{},'Evidencia y origen'),h('p',{},a.texto||'Detalle no disponible en el permiso actual.'),h('small',{},a.desde?`Desde ${a.desde} · fecha de la copia`:'Fecha del hecho pendiente de confirmar'),a.ruta?h('a',{href:a.ruta,on:{click:e=>guard(e)}},'Abrir origen'):null)))));
 return root;
}
