//440 · Consulta exacta437 antes de una intención local; ninguna escritura de proveedor.
import {ambitoTriaje432,previaTriaje432} from './_triaje_durable_432.js';
const uuid=v=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);
export function validarLecturaTriaje440(d,t){
 if(!d||d.version!=='437.1'||d.ticket_id!==t.id||d.cliente_id!==t.cliente_id||d.objeto!==t.numero||d.origen!=='ledger_local'||d.lectura_exacta!==true||d.confirmacion_desk!==false)return null;
 if(!d.tipos||Object.keys(d.tipos).sort().join(',')!=='asignar,cerrar')return null;
 for(const tipo of ['asignar','cerrar']){
  const x=d.tipos[tipo];
  if(!x||!Number.isSafeInteger(x.cantidad)||x.cantidad<0)return null;
  if(x.cantidad===0){if(x.ultima!==null)return null;continue;}
  const u=x.ultima;
  if(!u||!Number.isSafeInteger(u.accion_id)||u.accion_id<1||typeof u.propia!=='boolean'||typeof u.estado_registro!=='string'||!u.estado_registro||u.estado_registro.length>40||!(u.intencion_id===null||uuid(u.intencion_id))||(!u.propia&&u.intencion_id!==null))return null;
 }
 return d;
}
export async function consultarTriaje440(ctx,S,t,tipo){
 const antes=ambitoTriaje432(ctx,S,t,tipo);
 if(!antes||typeof ctx.api!=='function')throw Error('No se pudo comprobar el historial del ticket. Consulta Envíos.');
 let d;
 try{d=await ctx.api(`bandeja/triaje-intenciones?ticket_id=${encodeURIComponent(t.id)}&cliente_id=${encodeURIComponent(t.cliente_id)}`);}
 catch{throw Error('Historial exacto no disponible. No se ha guardado otra intención; consulta Envíos.');}
 if(ambitoTriaje432(ctx,S,t,tipo)!==antes)throw Error('El acceso o el ticket cambió; no se confirma esta intención.');
 const r=validarLecturaTriaje440(d,t);
 if(!r)throw Error('El historial no tiene una lectura exacta compatible. No se ha guardado otra intención.');
 const previa=previaTriaje432(ctx,S,t,tipo),propia=r.tipos[tipo],otra=r.tipos[tipo==='asignar'?'cerrar':'asignar'];
 if(otra.cantidad>0||propia.cantidad>0&&!(propia.cantidad===1&&propia.ultima.propia&&propia.ultima.estado_registro==='simulada'&&uuid(previa?.payload?.intencion_id)&&propia.ultima.intencion_id===previa.payload.intencion_id))throw Error('Ya hay un registro local de este ticket. Consulta Envíos antes de preparar otra intención.');
 return r;
}
