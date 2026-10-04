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
 const filas=Array.isArray(ctx.clientes)?ctx.clientes:Array.isArray(ctx.clientesVisibles)?ctx.clientesVisibles:[],counts=new Map();
 for(const c of filas)if(typeof c?.id==='string')counts.set(c.id,(counts.get(c.id)||0)+1);
 const ids=filas.filter(c=>counts.get(c?.id)===1&&c.activo_confirmado===true&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
 return {ids,personas:ctx.datos?.personas||[],hoy:ctx.hoy,firma:JSON.stringify([ctx.real?.id,ctx.persona?.id,ctx.real?.estado,ctx.persona?.estado,ctx.real?.activo,ctx.persona?.activo,ctx.real?.puestos,ctx.persona?.puestos,ctx.veModulo?.('reuniones'),ctx.hoy,ids])};
}
