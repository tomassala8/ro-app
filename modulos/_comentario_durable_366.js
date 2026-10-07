// Intención local194: no confirma cola ni entrega al hilo de ClickUp.
const id=v=>typeof v==='string'&&/^[A-Za-z0-9_-]{1,120}$/.test(v),arr=v=>Array.isArray(v)?v:[];
const uuid=v=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);
const roles=v=>Array.isArray(v)&&v.length>0&&v.every(id)&&new Set(v).size===v.length;
const cliente=v=>v===null||v===''?null:v;
const binding=(E,t)=>JSON.stringify([E.ctx.real?.id,E.ctx.persona?.id,t.id,t.lista_id,t.cli]);
export function ambitoComentario366(E,t){try{
 const c=E.ctx,ps=arr(c.datos?.personas),actors=[c.real,c.persona];
 if(!c.servidor||c.soloLectura||c.pilotoLectura||E.V?.solo_lectura||c.real?.id!==c.persona?.id||E.vigente?.()===false||c.vigente?.()===false||!c.veModulo?.('mi-trabajo'))return null;
 if(!actors.every(p=>id(p?.id)&&p.estado==='activo'&&p.activo!==false&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&x.estado==='activo'&&x.activo!==false&&roles(x.puestos)&&roles(p.puestos)&&JSON.stringify([...x.puestos].sort())===JSON.stringify([...p.puestos].sort()))))return null;
 if(![t.id,t.lista_id,t.persona_id].every(id))return null;
 const interna=t.cli===null||t.cli==='';if(!interna&&!id(t.cli))return null;
 const clients=arr(c.clientesVisibles).filter(x=>x?.id===t.cli);
 if(!interna&&(clients.length!==1||clients[0].activo_confirmado!==true||clients[0].detalle!==true||c.ver?.({tipo:'cliente_detalle',cliente_id:t.cli})?.ok!==true))return null;
 const rows=arr(E.D?.tareas).filter(x=>x?.id===t.id);
 if(!rows.length||!rows.some(x=>x.persona_id===t.persona_id)||rows.some(x=>x.lista_id!==t.lista_id||x.cli!==t.cli||!id(x.persona_id))||new Set(rows.map(x=>x.persona_id)).size!==rows.length)return null;
 // Sólo conserva la habilitación visual existente; el servidor204 autoriza el POST.
 const broad=c.persona.puestos.some(x=>['direccion','operaciones'].includes(x)),own=rows.some(x=>x.persona_id===c.persona.id),chief=ps.some(p=>p?.estado==='activo'&&p.activo!==false&&ps.filter(x=>x?.id===p.id).length===1&&rows.some(r=>r.persona_id===p.id)&&p.jefe===c.persona.id);
 if(!broad&&!own&&!chief)return null;
 return JSON.stringify([actors,ps,rows.map(x=>[x.id,x.lista_id,x.cli,x.persona_id]),clients,arr(c.datos?.asignaciones),interna?'interna_explicita':c.ver({tipo:'cliente_detalle',cliente_id:t.cli}).ok]);
 }catch{return null;}}
export function prepararComentario366(E,t,texto,clave){
 const scope=ambitoComentario366(E,t);
 if(!scope)throw Error('No se puede comentar con el contexto autorizado actual.');
 if(typeof texto!=='string'||texto.trim().length<2||texto.trim().length>2000||!uuid(clave))throw Error('Escribe entre 2 y 2000 caracteres y conserva una intención válida.');
 const payload=Object.freeze({herramienta:'clickup',tipo:'comentario',objeto:t.id,cliente_id:cliente(t.cli),intencion_id:clave,texto:texto.trim(),vista_previa:Object.freeze({})});
 return {scope,binding:binding(E,t),payload,estado:'preparado',mensaje:'Comentario preparado; aún no guardado.',recibo:null};
}
export function reciboComentario366(r,i){
 const p=i.payload,g=r?.intencion_guardada;
 if(r?.ok!==true||!Number.isSafeInteger(r.id)||r.id<1||g?.id!==p.intencion_id||g.accion_id!==r.id||typeof g.repetida!=='boolean'||r.texto!==p.texto||!r.vista_previa||Array.isArray(r.vista_previa)||Object.keys(r.vista_previa).length)return null;
 return {accion_id:r.id,intencion_id:g.id,repetida:g.repetida,guardado_local:true,confirmacion_remota:false};
}
export async function guardarComentario366(E,t,i,enviar){
 // El ámbito actual autoriza el intento, no forma parte de su identidad194.
 // Un cambio legítimo de roles no convierte una respuesta perdida en otra acción.
 const actual=ambitoComentario366(E,t);
 if(actual===null||i.binding!==binding(E,t)||i.payload.objeto!==t.id||i.payload.cliente_id!==cliente(t.cli)||i.estado==='guardando'||i.recibo)return false;
 i.scope=actual;
 const vivo=()=>ambitoComentario366(E,t)===i.scope;
 i.estado='guardando';i.mensaje='Guardando comentario en RO…';
 const noVigente=()=>{i.estado='sin_confirmar';i.mensaje='Resultado sin confirmar en un contexto que cambió. Revisa Envíos antes de otra intención.';return false;};
 try{const r=await enviar(i.payload);if(!vivo())return noVigente();const receipt=reciboComentario366(r,i);
  i.recibo=receipt;i.estado=receipt?'guardado':'sin_confirmar';i.mensaje=receipt?'Comentario guardado en RO · llegada a ClickUp sin confirmar.':'Resultado sin confirmar. Conserva el texto y reintenta la misma intención; revisa Envíos.';
 }catch{if(!vivo())return noVigente();i.estado='sin_confirmar';i.mensaje='Resultado sin confirmar. Conserva el texto y reintenta la misma intención; revisa Envíos.';}
 return vivo();
}
export function panelComentario366(E,t,h){
 E.comentarios366 ||= new Map();const key=JSON.stringify([E.ctx.real?.id,E.ctx.persona?.id,t.id,t.lista_id,t.cli]);
 let draft=E.comentarios366.get(key);if(!draft){draft={texto:'',intento:null};E.comentarios366.set(key,draft);}
 const scope=ambitoComentario366(E,t),root=h('section',{class:'pila','data-comentario-366':t.id,style:{gap:'8px'}});
 if(scope===null){root.append(h('b',{},'Comentar en RO'),h('p',{class:'sub',role:'status'},'Comentario no disponible con los permisos actuales. Consulta la tarea original.'));return root;}
 const vivo=()=>root.isConnected&&scope!==null&&ambitoComentario366(E,t)===scope;
 const textarea=h('textarea',{rows:2,value:draft.texto,placeholder:'Escribe un comentario para la tarea…','aria-label':'Comentario',maxlength:2000,disabled:!scope,style:{width:'100%',minWidth:'0',font:'inherit',padding:'8px 12px'},on:{input:()=>{
  if(!vivo()){root.replaceChildren();return;}if(draft.intento?.estado==='guardando')return;
  draft.texto=textarea.value;
  if(draft.intento&&draft.intento.payload.texto!==draft.texto.trim()){draft.intento=null;mensaje.replaceChildren('Texto cambiado: se preparará una nueva intención. La anterior puede estar guardada; comprueba Envíos.');}
  button.disabled=false;button.replaceChildren('Guardar comentario en RO');
 }}});textarea.value=draft.texto;
 const mensaje=h('p',{class:'sub',role:'status'},draft.intento?.mensaje||'Se guarda primero en RO; no acredita envío, mención ni notificación en ClickUp.'),button=h('button',{type:'button',class:'bt mini',disabled:!scope||draft.intento?.estado==='guardando'||!!draft.intento?.recibo,style:{minHeight:'44px'},on:{click:async()=>{
  if(!vivo()){root.replaceChildren();return;}if(draft.intento?.estado==='guardando'||draft.intento?.recibo)return;
  draft.texto=textarea.value;
  if(draft.intento&&draft.intento.payload.texto!==draft.texto.trim())draft.intento=null;
  try{draft.intento ||= prepararComentario366(E,t,draft.texto,crypto.randomUUID());}catch(e){mensaje.replaceChildren(e.message);return;}
  const intent=draft.intento;button.disabled=true;textarea.disabled=true;
  await guardarComentario366(E,t,intent,p=>E.ctx.accion(p));
  if(!vivo()){root.replaceChildren();return;}
  mensaje.replaceChildren(intent.mensaje);textarea.disabled=false;button.disabled=!!intent.recibo;
  button.replaceChildren(intent.recibo?'Guardado en RO':'Reintentar la misma intención');
  if(intent.recibo){if(textarea.value.trim()===intent.payload.texto){textarea.value='';draft.texto='';}
   E.local ||= [];if(!E.local.some(x=>x.intencion_id===intent.payload.intencion_id))E.local.push({tarea:t.id,quien:E.ctx.persona.id,campo:'comentario',tipo:'comentario',texto:intent.payload.texto,intencion_id:intent.payload.intencion_id,estado:'simulado',estado_texto:'Intención guardada en RO · cola y envío a ClickUp sin confirmar',creado:new Date().toISOString(),local:true});
  }
 }}},draft.intento?.estado==='sin_confirmar'?'Reintentar la misma intención':'Guardar comentario en RO');
 root.append(h('b',{},'Comentar en RO'),textarea,button,mensaje);return root;
}
