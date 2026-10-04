//516 · recibo local194; no envío ni ejecución en Meta/ClickUp.
const pendientes516=new Map(),lecturas516=new Map();
const id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
const arr=x=>Array.isArray(x)?x:[];
const uuid=x=>typeof x==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(x);
export function jsonPaid516(x){
 if(x===null||typeof x==='string'||typeof x==='boolean')return JSON.stringify(x);
 if(typeof x==='number'&&Number.isFinite(x))return JSON.stringify(x);
 if(Array.isArray(x))return '['+x.map(jsonPaid516).join(',')+']';
 if(x&&typeof x==='object'&&Object.getPrototypeOf(x)===Object.prototype)return '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+jsonPaid516(x[k])).join(',')+'}';
 throw Error('Contenido de la intención no válido.');
}
export function ambitoPaid516(ctx,cid=null,escritura=false){try{
 if(ctx.servidor!==true||ctx.vigente?.()===false||ctx.veModulo?.('captacion')!==true)return null;
 if(escritura&&(ctx.soloLectura||ctx.real?.id!==ctx.persona?.id||ctx.nivel==='resumen'))return null;
 const ps=arr(ctx.datos?.personas);
 for(const actor of [ctx.real,ctx.persona]){
  const xs=ps.filter(p=>p?.id===actor?.id),roles=actor?.puestos;
  if(!id(actor?.id)||xs.length!==1||actor.estado!=='activo'||actor.activo===false||xs[0].estado!=='activo'||xs[0].activo===false||!Array.isArray(roles)||!roles.length||!roles.every(id)||new Set(roles).size!==roles.length||!Array.isArray(xs[0].puestos)||jsonPaid516([...xs[0].puestos].sort())!==jsonPaid516([...roles].sort()))return null;
 }
 const core=arr(ctx.clientes),visible=arr(ctx.clientesVisibles),cids=visible.filter(c=>id(c?.id)&&c.activo_confirmado===true&&c.activo!==false&&c.estado!=='baja'&&c.detalle!==false&&visible.filter(x=>x?.id===c.id).length===1&&core.filter(x=>x?.id===c.id).length===1&&core.some(x=>x.id===c.id&&x.activo_confirmado===true&&x.activo!==false&&x.estado!=='baja'&&x.detalle!==false)&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
 if(!cids.length||cid!==null&&(!id(cid)||!cids.includes(cid)))return null;
 return {firma:jsonPaid516([ctx.real,ctx.persona,ps,core,visible,ctx.nivel??null,ctx.soloLectura===true,ctx.veModulo('captacion'),cids.map(c=>[c,ctx.ver({tipo:'cliente_detalle',cliente_id:c}),ctx.ver({tipo:'inversion',cliente_id:c})])]),cids,real:ctx.real.id,vista:ctx.persona.id};
}catch{return null;}}
function tipoPaid516(p){
 if(p?.herramienta==='app'&&p.tipo==='bitacora_cuenta')return 'bitacora_cuenta';
 if(p?.herramienta==='clickup'&&p.tipo==='tarea'&&p.vista_previa?.pedido_creatividad===true)return 'pedido_creatividad';
 throw Error('Tipo de intención Paid no reconocido.');
}
function congelar516(x){if(x&&typeof x==='object'){Object.values(x).forEach(congelar516);Object.freeze(x);}return x;}
async function hash516(s,crypto){if(!crypto?.subtle)throw Error('No se puede custodiar esta intención; no se ha enviado.');return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s))),b=>b.toString(16).padStart(2,'0')).join('');}
function registro516(raw,contexto){
 if(raw===null)return null;
 let r;try{r=JSON.parse(raw);}catch{throw Error('La custodia de una intención necesita revisión; no se enviará otra.');}
 if(!r||jsonPaid516(Object.keys(r).sort())!==jsonPaid516(['version','contexto','intencion_id','huella','estado'].sort())||r.version!=='516.1'||r.contexto!==contexto||!uuid(r.intencion_id)||typeof r.huella!=='string'||!/^[a-f0-9]{64}$/.test(r.huella)||!['pendiente','guardada'].includes(r.estado))throw Error('La custodia de una intención necesita revisión; no se enviará otra.');
 return r;
}
export function reciboPaid516(r,p){try{
 return r?.ok===true&&r.estado==='simulada'&&Number.isSafeInteger(r.id)&&r.id>0&&r.texto===p.texto&&jsonPaid516(r.vista_previa)===jsonPaid516(p.vista_previa)&&r.intencion_guardada?.id===p.intencion_id&&r.intencion_guardada?.accion_id===r.id&&typeof r.intencion_guardada?.repetida==='boolean';
}catch{return false;}}
export async function guardarPaid516(ctx,cuerpo,op={}){
 const cid=cuerpo?.cliente_id,s=ambitoPaid516(ctx,cid,true);
 if(!s)throw Error('No puedes guardar desde este contexto.');
 if(!id(cid)||typeof cuerpo.texto!=='string'||!cuerpo.texto.trim()||typeof cuerpo.objeto!=='string'||!cuerpo.objeto.trim()||Object.hasOwn(cuerpo,'intencion_id'))throw Error('La intención no es válida.');
 const tipo=tipoPaid516(cuerpo),origen=op.origen??globalThis.location?.origin;
 if(typeof origen!=='string'||!/^https?:\/\/[^/?#]+$/.test(origen))throw Error('No se puede custodiar la intención de esta sesión.');
 const contexto=jsonPaid516([origen,s.real,s.vista,'captacion',cid,tipo]),clave='ro.paid516:'+encodeURIComponent(contexto);
 const crypto=op.crypto??globalThis.crypto,storage=op.storage??globalThis.localStorage;
 const contenido=JSON.parse(jsonPaid516({...cuerpo,modulo:'captacion'})),huella=await hash516(jsonPaid516(contenido),crypto);
 if(ambitoPaid516(ctx,cid,true)?.firma!==s.firma)throw Error('El contexto cambió; revisa la vista actual.');
 let r;try{if(!storage?.getItem||!storage?.setItem)throw Error();r=registro516(storage.getItem(clave),contexto);}catch(e){throw Error(e?.message||'No se puede custodiar la intención; no se ha enviado.');}
 if(r?.estado==='pendiente'&&r.huella!==huella)throw Error('Hay una intención pendiente. Reintroduce su contenido exacto para reintentar o compruébala en Envíos; no se enviará otra.');
 const previo=pendientes516.get(clave);
 if(previo&&previo.huella===huella&&previo.enCurso)return previo.enCurso;
 const uid=r?.huella===huella?r.intencion_id:crypto?.randomUUID?.();
 if(!uuid(uid))throw Error('No se puede crear una intención durable; no se ha enviado.');
 const payload=previo?.huella===huella&&previo.payload?.intencion_id===uid?previo.payload:congelar516({...contenido,intencion_id:uid});
 const registro={version:'516.1',contexto,intencion_id:uid,huella,estado:'pendiente'};
 try{storage.setItem(clave,JSON.stringify(registro));if(storage.getItem(clave)!==JSON.stringify(registro))throw Error();}catch{throw Error('No se pudo custodiar la intención; no se ha enviado.');}
 const intento={huella,payload,enCurso:null};pendientes516.set(clave,intento);
 intento.enCurso=(async()=>{
  if(ambitoPaid516(ctx,cid,true)?.firma!==s.firma)throw Error('El contexto cambió; la intención sigue pendiente de comprobar.');
  const resultado=await ctx.accion(payload);
  if(ambitoPaid516(ctx,cid,true)?.firma!==s.firma)throw Error('El acceso cambió; la intención sigue pendiente de comprobar.');
  if(!reciboPaid516(resultado,payload))throw Error('Sin recibo local válido. La intención sigue pendiente; reintenta el mismo contenido.');
  try{const actual=registro516(storage.getItem(clave),contexto);if(actual?.huella!==huella||actual?.intencion_id!==uid)throw Error();storage.setItem(clave,JSON.stringify({...registro,estado:'guardada'}));}catch{throw Error('Hay un recibo local, pero su custodia necesita revisión. No se enviará otra intención.');}
  return {accion_id:resultado.id,intencion_id:uid,repetida:resultado.intencion_guardada.repetida,payload,estado:'guardada_local'};
 })();
 try{return await intento.enCurso;}finally{intento.enCurso=null;}
}
function fechaAccion516(s){
 if(typeof s!=='string')return false;
 const m=/^(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(Z|[+-]\d{2}:\d{2})?$/.exec(s);
 if(!m||Number(m[2])>23||Number(m[3])>59||Number(m[4])>59)return false;
 const dia=Date.parse(m[1]+'T00:00:00Z');if(!Number.isFinite(dia)||new Date(dia).toISOString().slice(0,10)!==m[1])return false;
 if(m[5]&&m[5]!=='Z'){const h=Number(m[5].slice(1,3)),min=Number(m[5].slice(4,6));if(h>14||min>59||h===14&&min!==0)return false;}
 const t=Date.parse(s.replace(' ','T')+(m[5]?'':'Z'));return Number.isFinite(t)&&t<=Date.now();
}
function proyectarLectura516(ctx,r,s){
 if(r?.modulo!=='captacion'||!Array.isArray(r.acciones)||r.acciones.length>500)throw Error('Lectura no válida.');
 const ids=new Set(),filas=[];
 for(const a of r.acciones){
  if(!a||!Number.isSafeInteger(a.id)||a.id<1||ids.has(a.id)||typeof a.tipo!=='string'||a.modulo!=='captacion'||!id(a.quien))throw Error('Lectura no válida.');ids.add(a.id);
  if(!s.cids.includes(a.cliente_id)||!ambitoPaid516(ctx,a.cliente_id))continue;
  if(a.tipo==='bitacora_cuenta'){
   if(typeof a.texto!=='string'||!fechaAccion516(a.creada))throw Error('Lectura no válida.');filas.push({...a});
  }else if(a.tipo==='tarea'){
   let vp;try{vp=typeof a.vista_previa==='string'?JSON.parse(a.vista_previa):a.vista_previa;}catch{throw Error('Lectura no válida.');}
   if(vp?.pedido_creatividad===true){if(typeof a.texto!=='string'||!fechaAccion516(a.creada))throw Error('Lectura no válida.');filas.push({...a,vista_previa:vp});}
  }
 }
 return filas;
}
function fechaLectura516(iso){
 if(!iso)return 'fecha desconocida';
 return new Intl.DateTimeFormat('es-ES',{timeZone:'Europe/Madrid',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(iso));
}
export async function cargarLecturaPaid516(ctx,d){
 const s=ambitoPaid516(ctx),clave=s?jsonPaid516([s.real,s.vista]):null;
 const limpiar=()=>{d.bitacora=new Map();d.pedidos=new Map();d.lecturaPaid516={estado:'denegada',leido_en:null,aviso:'Estos registros no están disponibles con los permisos actuales.'};if(clave)lecturas516.delete(clave);};
 if(!s){limpiar();return;}
 // Nunca se conserva una lectura cuya firma de autoridad haya cambiado.
 let anterior=lecturas516.get(clave);if(anterior?.firma!==s.firma){lecturas516.delete(clave);anterior=null;}
 try{
  const info={};
  const respuesta=await ctx.api('acciones?modulo=captacion',{info});
  if(ambitoPaid516(ctx)?.firma!==s.firma){limpiar();return;}
  const filas=proyectarLectura516(ctx,respuesta,s);
  if(ambitoPaid516(ctx)?.firma!==s.firma){limpiar();return;}
  const hora=typeof info.hora==='number'&&Number.isFinite(info.hora)&&info.hora>0&&info.hora<=Date.now()&&Number.isFinite(new Date(info.hora).getTime())?new Date(info.hora).toISOString():null;
  anterior={firma:s.firma,filas,leido_en:hora};lecturas516.set(clave,anterior);
  const copia=info.guardado===true||info.falloActualizacion===true;
  d.lecturaPaid516={estado:copia?'anterior':'observada',leido_en:hora,aviso:`${copia?'Copia guardada; actualización sin confirmar. ':''}Lectura local HTTP: ${fechaLectura516(hora)} (Madrid). Últimas acciones disponibles (hasta500); no historial completo ni ejecución externa.`};
 }catch(e){
  if([401,403].includes(e?.status??e?.codigo)||ambitoPaid516(ctx)?.firma!==s.firma){limpiar();return;}
  d.lecturaPaid516={estado:anterior?'anterior':'sin_dato',leido_en:anterior?.leido_en||null,aviso:anterior?`No se pudo actualizar. Última lectura local: ${fechaLectura516(anterior.leido_en)} (Madrid); no fecha del proveedor.`:'No se pudo leer el registro local. No acredita ausencia de apuntes o pedidos.'};
 }
 d.bitacora=new Map();d.pedidos=new Map();
 for(const a of anterior?.filas||[]){const m=a.tipo==='bitacora_cuenta'?d.bitacora:d.pedidos;if(!m.has(a.cliente_id))m.set(a.cliente_id,[]);m.get(a.cliente_id).push(a);}
 for(const m of [d.bitacora,d.pedidos])for(const filas of m.values())filas.sort((a,b)=>b.id-a.id);
}
