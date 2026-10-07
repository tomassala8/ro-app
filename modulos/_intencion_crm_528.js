//528/531 · recibo local194; no envío ni ejecución en GHL/ClickUp.
const pendientes528=new Map();
const id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
const arr=x=>Array.isArray(x)?x:[];
const uuid=x=>typeof x==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(x);
export function jsonCRM528(x){
 if(x===null||typeof x==='string'||typeof x==='boolean')return JSON.stringify(x);
 if(typeof x==='number'&&Number.isFinite(x))return JSON.stringify(x);
 if(Array.isArray(x))return '['+x.map(jsonCRM528).join(',')+']';
 if(x&&typeof x==='object'&&Object.getPrototypeOf(x)===Object.prototype)return '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+jsonCRM528(x[k])).join(',')+'}';
 throw Error('Contenido de la intención no válido.');
}
const JEFATURA528=['direccion','finanzas_direccion','operaciones','proyectos','jefa_crm','tecnico_altas'];
export function ambitoCRM528(ctx,cid,global=false){try{
 if(ctx.servidor!==true||ctx.soloLectura===true||ctx.nivel==='resumen'||ctx.vigente?.()===false||ctx.veModulo?.('salud-crm')!==true||ctx.real?.id!==ctx.persona?.id)return null;
 const ps=arr(ctx.datos?.personas);
 for(const actor of [ctx.real,ctx.persona]){const xs=ps.filter(p=>p?.id===actor?.id),rs=actor?.puestos;if(!id(actor?.id)||xs.length!==1||actor.estado!=='activo'||actor.activo===false||xs[0].estado!=='activo'||xs[0].activo===false||!Array.isArray(rs)||!rs.length||!rs.every(id)||new Set(rs).size!==rs.length||!Array.isArray(xs[0].puestos)||jsonCRM528([...xs[0].puestos].sort())!==jsonCRM528([...rs].sort()))return null;}
 const core=arr(ctx.clientes),vs=arr(ctx.clientesVisibles),cs=vs.filter(c=>id(c?.id)&&c.activo_confirmado===true&&c.activo!==false&&c.estado!=='baja'&&c.detalle!==false&&vs.filter(x=>x?.id===c.id).length===1&&core.filter(x=>x?.id===c.id).length===1&&core.some(x=>x.id===c.id&&x.activo_confirmado===true&&x.activo!==false&&x.estado!=='baja'&&x.detalle!==false)&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
 if(global){if(cid!==null||ctx.nivel!=='todo'||![ctx.real,ctx.persona].every(p=>p.puestos.some(r=>JEFATURA528.includes(r))))return null;}else if(!id(cid)||!cs.includes(cid))return null;
 return{firma:jsonCRM528([ctx.real,ctx.persona,ps,core,vs,ctx.nivel??null,ctx.veModulo('salud-crm'),cs.map(c=>[c,ctx.ver({tipo:'cliente_detalle',cliente_id:c})])]),real:ctx.real.id,vista:ctx.persona.id};
}catch{return null;}}
function tipoCRM528(p,global){
 const allowed={ghl:['nota','mover_oportunidad','marcar_cita','reprogramar_cita'],clickup:['tarea'],app:['casilla_montaje','escalar','aviso_integracion']};
 if(global){if(p.herramienta!=='app'||p.tipo!=='proponer_reasignacion'||p.objeto!=='Subcuentas sin especialista'||p.cliente_id!==null)throw Error('Propuesta general no válida.');}
 else if(!allowed[p.herramienta]?.includes(p.tipo))throw Error('Tipo de intención CRM no reconocido.');
 return p.herramienta+':'+p.tipo;
}
function congelar528(x){if(x&&typeof x==='object'){Object.values(x).forEach(congelar528);Object.freeze(x);}return x;}
async function hash528(s,crypto){if(!crypto?.subtle)throw Error('No se puede custodiar esta intención; no se ha enviado.');return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s))),b=>b.toString(16).padStart(2,'0')).join('');}
function registro528(raw,contexto){
 if(raw===null)return null;
 let r;try{r=JSON.parse(raw);}catch{throw Error('La custodia de una intención necesita revisión; no se enviará otra.');}
 if(!r||jsonCRM528(Object.keys(r).sort())!==jsonCRM528(['version','contexto','intencion_id','huella','estado'].sort())||r.version!=='528.1'||r.contexto!==contexto||!uuid(r.intencion_id)||typeof r.huella!=='string'||!/^[a-f0-9]{64}$/.test(r.huella)||!['pendiente','guardada'].includes(r.estado))throw Error('La custodia de una intención necesita revisión; no se enviará otra.');
 return r;
}
export function reciboCRM528(r,p){try{
 return r?.ok===true&&r.estado==='simulada'&&Number.isSafeInteger(r.id)&&r.id>0&&r.texto===p.texto&&jsonCRM528(r.vista_previa)===jsonCRM528(p.vista_previa)&&r.intencion_guardada?.id===p.intencion_id&&r.intencion_guardada?.accion_id===r.id&&typeof r.intencion_guardada?.repetida==='boolean';
}catch{return false;}}
export async function guardarCRM528(ctx,cuerpo,op={}){
 const global=op.global===true,cid=cuerpo?.cliente_id,s=ambitoCRM528(ctx,cid,global);
 if(!s)throw Error('No puedes guardar desde este contexto.');
 if((!global&&!id(cid))||typeof cuerpo.texto!=='string'||!cuerpo.texto.trim()||typeof cuerpo.objeto!=='string'||!cuerpo.objeto.trim()||Object.hasOwn(cuerpo,'intencion_id'))throw Error('La intención no es válida.');
 const tipo=tipoCRM528(cuerpo,global),origen=op.origen??globalThis.location?.origin;
 if(typeof origen!=='string'||!/^https?:\/\/[^/?#]+$/.test(origen))throw Error('No se puede custodiar la intención de esta sesión.');
 const crypto=op.crypto??globalThis.crypto,storage=op.storage??globalThis.localStorage;
 const referencia=await hash528(cuerpo.objeto,crypto);
 const contexto=jsonCRM528([origen,s.real,s.vista,'salud-crm',cid,tipo,referencia]),clave='ro.crm528:'+encodeURIComponent(contexto);
 const contenido=JSON.parse(jsonCRM528({...cuerpo,modulo:'salud-crm'})),huella=await hash528(jsonCRM528(contenido),crypto);
 if(ambitoCRM528(ctx,cid,global)?.firma!==s.firma)throw Error('El contexto cambió; revisa la vista actual.');
 let r;try{if(!storage?.getItem||!storage?.setItem)throw Error();r=registro528(storage.getItem(clave),contexto);}catch(e){throw Error(e?.message||'No se puede custodiar la intención; no se ha enviado.');}
 if(r?.estado==='pendiente'&&r.huella!==huella)throw Error('Hay una intención pendiente. Reintroduce su contenido exacto para reintentar o compruébala en Envíos; no se enviará otra.');
 const previo=pendientes528.get(clave);
 if(previo&&previo.huella===huella&&previo.enCurso)return previo.enCurso;
 const uid=r?.huella===huella?r.intencion_id:crypto?.randomUUID?.();
 if(!uuid(uid))throw Error('No se puede crear una intención durable; no se ha enviado.');
 const payload=previo?.huella===huella&&previo.payload?.intencion_id===uid?previo.payload:congelar528({...contenido,intencion_id:uid});
 const registro={version:'528.1',contexto,intencion_id:uid,huella,estado:'pendiente'};
 try{storage.setItem(clave,JSON.stringify(registro));if(storage.getItem(clave)!==JSON.stringify(registro))throw Error();}catch{throw Error('No se pudo custodiar la intención; no se ha enviado.');}
 const intento={huella,payload,enCurso:null};pendientes528.set(clave,intento);
 intento.enCurso=(async()=>{
  if(ambitoCRM528(ctx,cid,global)?.firma!==s.firma)throw Error('El contexto cambió; la intención sigue pendiente de comprobar.');
  const resultado=await ctx.accion(payload);
  if(ambitoCRM528(ctx,cid,global)?.firma!==s.firma)throw Error('El acceso cambió; la intención sigue pendiente de comprobar.');
  if(!reciboCRM528(resultado,payload))throw Error('Sin recibo local válido. La intención sigue pendiente; reintenta el mismo contenido.');
  try{const actual=registro528(storage.getItem(clave),contexto);if(actual?.huella!==huella||actual?.intencion_id!==uid)throw Error();storage.setItem(clave,JSON.stringify({...registro,estado:'guardada'}));}catch{throw Error('Hay un recibo local, pero su custodia necesita revisión. No se enviará otra intención.');}
  return {accion_id:resultado.id,intencion_id:uid,repetida:resultado.intencion_guardada.repetida,payload,estado:'guardada_local'};
 })();
 try{return await intento.enCurso;}finally{intento.enCurso=null;}
}

/** Confirmación propia para no pintar éxito/error de un ámbito revocado desde botonConfirmar genérico. */
export function crearAccionCRM528(h,ctx,o){
 const global=o.globalCRM528===true,cid=global?null:o.cliente_id,scope=ambitoCRM528(ctx,cid,global),root=h('span',{class:'confirmar'});let busy=false;
 const vivo=()=>root.isConnected&&scope!==null&&ambitoCRM528(ctx,cid,global)?.firma===scope.firma;
 const limpiar=()=>root.replaceChildren();
 const cls=`bt${o.mini!==false?' mini':''}${o.peligro?' peligro':''}`;
 const inicial=()=>{root.replaceChildren(h('button',{type:'button',class:cls,disabled:!scope,'aria-disabled':scope?null:'true',title:scope?null:'Sólo lectura o permisos actuales no disponibles',on:{click:()=>{if(!vivo()){limpiar();return;}preguntar();}}},o.texto));};
 function preguntar(error=''){
  const status=h('span',{class:error?'estado error':'sub',role:error?'alert':'status'},error||'Sólo intención local; no cambia GHL/ClickUp ni envía mensajes.');
  const no=h('button',{type:'button',class:cls,on:{click:()=>{if(!vivo()){limpiar();return;}inicial();}}},'No');
  const si=h('button',{type:'button',class:cls+' pri',on:{click:async()=>{
   if(busy)return;if(!vivo()){limpiar();return;}busy=true;si.disabled=true;no.disabled=true;
   try{
    const prev=typeof o.vista_previa==='function'?o.vista_previa():o.vista_previa;
    const objeto=typeof o.objeto==='function'?o.objeto():o.objeto;
    if(typeof prev!=='string'||!prev.trim()||typeof objeto!=='string'||!objeto.trim())throw Error('Rellena el dato antes.');
    await guardarCRM528(ctx,{herramienta:o.herramienta||'ghl',tipo:o.tipo,objeto:objeto.slice(0,200),cliente_id:cid,texto:prev,vista_previa:prev},{global});
    if(!vivo()){limpiar();return;}
    root.replaceChildren(h('span',{class:'estado',role:'status'},'Intención local guardada; cambio externo sin confirmar.'));
   }catch(e){if(!vivo()){limpiar();return;}preguntar(e?.message||'Sin confirmación local; reintenta la misma intención.');}
   finally{busy=false;}
  }}},'Guardar intención local');
  root.replaceChildren(h('span',{class:'preg'},'¿Guardar esta intención local?'),status,si,no);
  root.onkeydown=e=>{if(e.key==='Escape'&&!busy){if(vivo())inicial();else limpiar();}};
 }
 inicial();return root;
}
