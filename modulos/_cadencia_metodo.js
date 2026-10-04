import { proyectarMetodo305 } from './_metodo_cohorte_305.js';
// Lectura del overlay autorizado. No infiere cohorte por importe ni agenda reuniones.
const validados=new WeakSet();
const hoyMadrid=()=>{const p=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());return ['year','month','day'].map(k=>p.find(x=>x.type===k)?.value).join('-');};
export function separarCadencias(clientes, metodo, opciones={}) {
  const filas=Array.isArray(clientes)?clientes:[],n=new Map();
  for(const r of filas)if(typeof r?.cliente_id==='string')n.set(r.cliente_id,(n.get(r.cliente_id)||0)+1);
  const ids=Array.isArray(opciones.ids)?opciones.ids:filas.filter(r=>n.get(r?.cliente_id)===1).map(r=>r.cliente_id);
  const porId=proyectarMetodo305(metodo,ids,opciones.personas||[],Object.prototype.hasOwnProperty.call(opciones,'hoy')?opciones.hoy:hoyMadrid());
  for(const [id,r] of porId){if(n.get(id)!==1){porId.delete(id);continue;}Object.freeze(r);validados.add(r);}
  return { historicos: filas.filter(c => (!Array.isArray(opciones.ids)||ids.includes(c?.cliente_id))&&!porId.has(c?.cliente_id)), seguimiento: [...porId.values()] };
}
export function textoCadencia(r) {
  if(!validados.has(r))return 'Confirma responsable y evidencia vigente antes de proponer fecha.';
  const ultima = r.ultima_confirmada ? `Última celebrada confirmada: ${r.ultima_confirmada}.` : 'Última celebrada: sin dato confirmado.';
  const revision = r.proxima_revision ? `Revisión de cadencia: ${r.proxima_revision}; no es una cita agendada.` : 'Próxima revisión pendiente de evidencia.';
  return `${ultima} ${revision} ${r.estado==='revisar_cadencia'?'Revisa el seguimiento con el trafficker; no se ha agendado nada.':r.estado==='en_cadencia'?'Prepara el siguiente seguimiento con el trafficker.':'Confirma responsable y recencia; sin registro no se afirma incumplimiento.'}`;
}
export function estadoCadencia(r) {
  return validados.has(r)?r.estado === 'en_cadencia' ? 'verde' : r.estado === 'revisar_cadencia' ? 'ambar' : 'gris':'gris';
}
export function ambitoCadencia307(ctx){
 const list=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
 const activo=p=>p?.estado==='activo'&&p.activo!==false,roles=p=>Array.isArray(p?.puestos)&&p.puestos.length>0&&p.puestos.every(id)&&new Set(p.puestos).size===p.puestos.length;
 const cs=list(ctx.clientes),vs=list(ctx.clientesVisibles),ps=list(ctx.datos?.personas),as=[ctx.real,ctx.persona];
 let ids=[];
 try{
 const actores=as.every(p=>{const xs=ps.filter(x=>x?.id===p?.id);return id(p?.id)&&activo(p)&&roles(p)&&xs.length===1&&activo(xs[0])&&roles(xs[0])&&JSON.stringify([...p.puestos].sort())===JSON.stringify([...xs[0].puestos].sort());});
 const permite=c=>id(c?.id)&&c.activo_confirmado===true&&c.detalle===true&&c.activo!==false&&c.estado!=='baja';
 if(actores&&ctx.vigente?.()!==false&&ctx.veModulo?.('reuniones')===true)ids=cs.filter(c=>permite(c)&&cs.filter(x=>x?.id===c.id).length===1&&vs.filter(x=>x?.id===c.id).length===1&&vs.some(x=>x?.id===c.id&&permite(x))&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
 const grants=cs.map(c=>[c?.id,ctx.ver?.({tipo:'cliente_detalle',cliente_id:c?.id})?.ok===true]);
 return {ids,personas:actores?ps:[],hoy:ctx.hoy,firma:JSON.stringify([as,ps,cs,vs,ctx.datos?.asignaciones,ctx.hoy,ctx.veModulo?.('reuniones'),ctx.veModulo?.('ficha'),grants,ids])};
 }catch{return {ids:[],personas:[],hoy:ctx.hoy,firma:null};}
}
