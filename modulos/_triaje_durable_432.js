//432 · Intenciones locales194. No acredita asignación/cierre en Desk ni oculta su fuente.
const arr=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,120}$/.test(x);
const roles=x=>Array.isArray(x)&&x.length>0&&x.every(id)&&new Set(x).size===x.length;
const uuid=x=>typeof x==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(x);
function actores(ctx){const ps=arr(ctx.datos?.personas);return [ctx.real,ctx.persona].every(p=>id(p?.id)&&p.estado==='activo'&&p.activo!==false&&roles(p.puestos)&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&x.estado==='activo'&&x.activo!==false&&roles(x.puestos)&&JSON.stringify([...x.puestos].sort())===JSON.stringify([...p.puestos].sort())));}
function cliente(ctx,t){if(t.cliente_id===null)return ctx.persona.puestos.some(x=>['direccion','operaciones','proyectos'].includes(x));if(!id(t.cliente_id))return false;return [ctx.clientes,ctx.clientesVisibles].every(xs=>{const cs=arr(xs).filter(x=>x?.id===t.cliente_id);return cs.length===1&&cs[0].activo_confirmado===true&&cs[0].detalle!==false;})&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:t.cliente_id})?.ok===true;}
export function filasTriaje432(ctx,S){try{
 if(ctx.vigente?.()===false||ctx.veModulo?.('bandeja')!==true||!actores(ctx)||!Array.isArray(S.triaje))return null;
 const source=S.triaje;return source.filter(t=>id(t?.id)&&id(t.numero)&&['seguro','dudoso','sin_cliente','ruido'].includes(t.propuesta)&&source.filter(x=>x?.id===t.id).length===1&&source.filter(x=>x?.numero===t.numero).length===1&&cliente(ctx,t));
 }catch{return null;}}
const referencia=t=>[t.id,t.numero,t.cliente_id,t.propuesta,t.agente_propuesto_id??null,t.fecha??null];
export function ambitoTriaje432(ctx,S,t,tipo=null){try{
 const rows=filasTriaje432(ctx,S),row=rows?.find(x=>x.id===t?.id);
 if(!row||JSON.stringify(referencia(row))!==JSON.stringify(referencia(t)))return null;
 if(tipo!==null){
  if(!['asignar','cerrar'].includes(tipo)||ctx.servidor!==true||S.accionesTriajeLeidas432!==true||ctx.soloLectura||ctx.pilotoLectura||ctx.real.id!==ctx.persona.id||!id(t.cliente_id))return null;
  // Tras recargar, un registro previo sin la intención original no autoriza otro UUID.
  if(arr(S.porObjeto?.get(t.numero)).some(x=>['asignar','cerrar'].includes(x?.tipo))&&!previaTriaje432(ctx,S,t,tipo)&&!persistida432(ctx,t,tipo)?.valida)return null;
  if(tipo==='asignar'){
   if(!ctx.persona.puestos.some(x=>['direccion','operaciones','proyectos'].includes(x))||!id(t.agente_propuesto_id))return null;
   const ps=arr(ctx.datos?.personas).filter(x=>x?.id===t.agente_propuesto_id);
   if(ps.length!==1||ps[0].estado!=='activo'||ps[0].activo===false||!roles(ps[0].puestos))return null;
  }
 }
 return JSON.stringify([ctx.real,ctx.persona,ctx.datos?.personas,ctx.clientes,ctx.clientesVisibles,ctx.veModulo('bandeja'),ctx.soloLectura,ctx.pilotoLectura,referencia(t),rows.map(referencia),t.cliente_id===null?null:ctx.ver({tipo:'cliente_detalle',cliente_id:t.cliente_id}),tipo]);
 }catch{return null;}}
const binding=(ctx,t,tipo)=>JSON.stringify([ctx.real?.id,ctx.persona?.id,tipo,...referencia(t)]);
function clavePersistida432(ctx,t,tipo){const origin=globalThis.location?.origin;if(typeof origin!=='string'||!/^https?:\/\/[^\s]{1,200}$/.test(origin))throw Error('No se pudo acreditar el origen de esta intención.');return 'ro.triaje432:'+JSON.stringify([origin,ctx.real?.id,ctx.persona?.id,t.id,t.numero,tipo]);}
function persistida432(ctx,t,tipo){try{const raw=globalThis.localStorage?.getItem(clavePersistida432(ctx,t,tipo));if(raw===null)return null;if(typeof raw!=='string'||raw.length>1800)return {valida:false};const x=JSON.parse(raw);return {valida:x&&Object.keys(x).length===2&&uuid(x.uuid)&&x.binding===binding(ctx,t,tipo),uuid:x?.uuid};}catch{return {valida:false};}}
function conservar432(ctx,t,tipo,i){const raw=JSON.stringify({uuid:i.payload.intencion_id,binding:i.binding}),key=clavePersistida432(ctx,t,tipo);try{globalThis.localStorage.setItem(key,raw);if(globalThis.localStorage.getItem(key)!==raw)throw Error();}catch{throw Error('No se pudo conservar la intención para reintentar. No se ha solicitado guardar; consulta Envíos.');}}
export function prepararTriaje432(ctx,S,t,tipo,clave){
 const scope=ambitoTriaje432(ctx,S,t,tipo);if(!scope||!uuid(clave))throw Error('Revisa el ticket y los permisos actuales antes de guardar.');
 const vista_previa=Object.freeze(tipo==='asignar'?{a:t.agente_propuesto_id,ticket:t.numero,origen:'triaje'}:{estado:'Cerrado',ticket:t.numero});
 const payload=Object.freeze({modulo:'bandeja',herramienta:'desk',tipo,objeto:t.numero,cliente_id:t.cliente_id,intencion_id:clave,texto:tipo==='asignar'?`Solicitar asignación del ticket ${t.numero}`:`Solicitar cierre del ticket ${t.numero} desde el reparto`,vista_previa});
 return {scope,binding:binding(ctx,t,tipo),payload,estado:'preparado',recibo:null,mensaje:'Todavía no guardada.'};
}
export function reciboTriaje432(r,i){const p=i.payload,g=r?.intencion_guardada;
 const v=r?.vista_previa,w=p.vista_previa;
 const igual=v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).length===Object.keys(w).length&&Object.keys(w).every(k=>Object.hasOwn(v,k)&&v[k]===w[k]);
 if(r?.ok!==true||r.estado!=='simulada'||!Number.isSafeInteger(r.id)||r.id<1||g?.id!==p.intencion_id||g.accion_id!==r.id||typeof g.repetida!=='boolean'||r.texto!==p.texto||!igual)return null;
 return {accion_id:r.id,intencion_id:g.id,guardado_local:true,confirmacion_desk:false,repetida:g.repetida};
}
export async function guardarTriaje432(ctx,S,t,i){
 const scope=ambitoTriaje432(ctx,S,t,i.payload.tipo);if(!scope||i.binding!==binding(ctx,t,i.payload.tipo)||i.estado==='guardando'||i.recibo)return false;
 const saved=persistida432(ctx,t,i.payload.tipo);if(!saved?.valida||saved.uuid!==i.payload.intencion_id){i.estado='sin_confirmar';i.mensaje='La intención conservada cambió o no se puede leer. Consulta Envíos antes de guardar.';return false;}
 i.scope=scope;i.estado='guardando';i.mensaje='Guardando intención local…';
 const vivo=()=>ambitoTriaje432(ctx,S,t,i.payload.tipo)===scope;
 try {const r=await ctx.accion(i.payload);if(!vivo()){i.estado='sin_confirmar';i.mensaje='El contexto cambió; consulta Envíos antes de otra intención.';return false;}
  i.recibo=reciboTriaje432(r,i);i.estado=i.recibo?'guardada':'sin_confirmar';i.mensaje=i.recibo?'Intención local guardada · Desk sin confirmar.':'Sin recibo válido. Reintenta la misma intención; consulta Envíos.';
 } catch {i.estado='sin_confirmar';i.mensaje='Resultado sin confirmar. Reintenta la misma intención; consulta Envíos.';}
 return vivo();
}
export function intencionTriaje432(ctx,S,t,tipo){
 S.intencionesTriaje432 ||= new Map();const key=JSON.stringify([ctx.real?.id,ctx.persona?.id,t.id,t.numero,tipo]);
 let i=S.intencionesTriaje432.get(key);
 if(i&&i.binding!==binding(ctx,t,tipo))throw Error('Cambió la propuesta o el cliente. Consulta Envíos antes de preparar otra intención.');
 if(!i){const saved=persistida432(ctx,t,tipo);if(saved&&!saved.valida)throw Error('Hay una intención anterior que no coincide o no se pudo leer. Consulta Envíos antes de preparar otra.');i=prepararTriaje432(ctx,S,t,tipo,saved?.uuid||globalThis.crypto?.randomUUID?.());conservar432(ctx,t,tipo,i);S.intencionesTriaje432.set(key,i);}return i;
}
export function previaTriaje432(ctx,S,t,tipo){const i=S.intencionesTriaje432?.get(JSON.stringify([ctx.real?.id,ctx.persona?.id,t.id,t.numero,tipo]));if(i)return i;const saved=persistida432(ctx,t,tipo);return saved?.valida?{binding:binding(ctx,t,tipo),payload:{tipo,intencion_id:saved.uuid},estado:'sin_confirmar',recibo:null}:null;}
export function estadoTriaje432(ctx,S,t){
 const local=arr(S.porObjeto?.get(t.numero)).some(x=>['asignar','cerrar'].includes(x?.tipo));
 const previas=['asignar','cerrar'].map(tipo=>previaTriaje432(ctx,S,t,tipo)).filter(Boolean);
 if(previas.some(i=>i.binding!==binding(ctx,t,i.payload.tipo)))return 'Propuesta cambiada · consulta Envíos antes de otra intención';
 const intents=previas;
 if(intents.some(i=>i.recibo))return 'Intención local guardada · Desk sin confirmar';
 if(intents.some(i=>i.estado==='sin_confirmar'))return 'Resultado sin confirmar · conserva la misma intención';
 if(intents.some(i=>i.estado==='guardando'))return 'Guardando intención local…';
 return local?'Registro local previo · Desk sin confirmar':'Sin intención local confirmada';
}
