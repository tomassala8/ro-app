import {h} from '../componentes.js';
import {ambitoDecision382,prepararDecision382,guardarDecision382} from './_decision_durable_382.js';
const tipos={para_coti:'Coti · revisión de proyectos',para_tomas:'Tomás · dirección',escalada:'Escalada'},opciones=['Aprobar la recomendación','Rechazar','Delegar'];
const arr=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,120}$/.test(x),txt=(x,n)=>typeof x==='string'&&x.length<=n&&!/[\u0000-\u0008]/.test(x);
function persona(ctx,pid){if(!id(pid))return null;const ps=arr(ctx.datos?.personas).filter(p=>p?.id===pid);return ps.length===1&&ps[0].estado==='activo'&&ps[0].activo!==false&&Array.isArray(ps[0].puestos)&&ps[0].puestos.length>0&&ps[0].puestos.every(id)&&new Set(ps[0].puestos).size===ps[0].puestos.length&&txt(ps[0].nombre,200)?ps[0]:null;}
export function proyectarDecisiones387(ctx,D){
 if(!ambitoDecision382(ctx,null,false)||D?.version!=='382.1'||D.origen!=='registro_local'||D.envio_realizado!==false||typeof D.truncado!=='boolean'||!Array.isArray(D.decisiones)||D.decisiones.length>1000)return null;
 const out=[],seen=new Set();for(const r of D.decisiones){
  if(!r||!/^db-[1-9][0-9]{0,12}$/.test(r.id)||seen.has(r.id)||!Object.keys(tipos).includes(r.tipo)||!ambitoDecision382(ctx,r.cliente_id,false)||!txt(r.titulo,200)||!txt(r.problema,2000)||!txt(r.recomendacion,2000)||!(r.creada===null||txt(r.creada,80))||!(r.respondida===null||txt(r.respondida,80))||!/^([a-f0-9]{64})$/.test(r.revision)||r.origen!=='registro_local'||r.ejecucion_verificada!==false||r.envio_realizado!==false||typeof r.puede_responder!=='boolean')return null;
  const registrada=typeof r.respuesta_registrada==='boolean'?r.respuesta_registrada:r.respondida!==null;if((!registrada&&r.respondida!==null)||(registrada&&r.puede_responder))return null;seen.add(r.id);let respuesta=null;
  if(registrada&&r.respuesta&&opciones.includes(r.respuesta.decision)&&(r.respuesta.motivo===null||txt(r.respuesta.motivo,2000))&&(r.respuesta.delegada_en===null||persona(ctx,r.respuesta.delegada_en)))respuesta={decision:r.respuesta.decision,motivo:r.respuesta.motivo,delegada_en:r.respuesta.delegada_en};
  out.push({id:r.id,tipo:r.tipo,cliente_id:r.cliente_id,titulo:r.titulo,problema:r.problema,recomendacion:r.recomendacion,creada:r.creada,respondida:r.respondida,respuesta_registrada:registrada,revision:r.revision,puede_responder:r.puede_responder,quien:persona(ctx,r.quien)?.id||null,respondida_por:persona(ctx,r.respondida_por)?.id||null,respuesta});
 }return {filas:out,truncado:D.truncado};
}
export function fechaRegistro387(x){
 if(typeof x!=='string')return 'Sin fecha válida';
 let d;if(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(x)){
  d=new Date(x.replace(' ','T')+'Z');if(!Number.isFinite(d.getTime())||d.toISOString().slice(0,19)!==x.replace(' ','T'))return 'Sin fecha válida';
 }else if(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(x)){const dia=new Date(x.slice(0,10)+'T00:00:00Z');if(!Number.isFinite(dia.getTime())||dia.toISOString().slice(0,10)!==x.slice(0,10)||Number(x.slice(11,13))>=24||Number(x.slice(14,16))>=60||Number(x.slice(17,19))>=60)return 'Sin fecha válida';d=new Date(x);if(!Number.isFinite(d.getTime()))return 'Sin fecha válida';}
 else return 'Sin fecha válida';
 return new Intl.DateTimeFormat('es-ES',{timeZone:'Europe/Madrid',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(d)+' · Madrid';
}
// Montar en ParaTomás. No combina colecciones históricas ni acredita ejecución externa.
export async function renderDecisiones387(cont,ctx,{vigente=()=>true}={}){
 const base=h('section',{'data-decisiones-387':'',class:'panel pila',style:{padding:'var(--s-4)',gap:'var(--s-2)',minWidth:'0'}}),status=h('p',{role:'status',class:'sub'},'Consultando decisiones locales…'),body=h('div',{class:'pila',style:{gap:'var(--s-2)',minWidth:'0'}});
 cont.append(base);base.append(h('h2',{},'Decisiones para Tomás'),h('p',{class:'sub'},'Registro en RO · fechas Madrid · sin envío ni ejecución verificada'),status,body);
 const scope=()=>{const a=ambitoDecision382(ctx,null,false);if(!a)return null;return JSON.stringify([a,arr(ctx.clientesVisibles).map(c=>[c?.id,ambitoDecision382(ctx,c?.id,false)])]);};
 const inicial=scope(),vivo=()=>base.isConnected&&vigente()&&ctx.vigente?.()!==false&&inicial!==null&&scope()===inicial;
 const guard=()=>{if(vivo())return true;base.replaceChildren();return false;};
 if(!guard())return base;
 let model=null,epoch=0;
 const fecha=fechaRegistro387,breve=(x,n=140)=>x.length>n?x.slice(0,n)+'…':x;
 const nombre=x=>persona(ctx,x)?.nombre||'Identidad por confirmar';
 function editor(row=null){
  const form=h('div',{class:'pila'}),fields=[],mensaje=h('p',{role:'status',class:'sub'},''),button=h('button',{type:'button',class:'bt',style:{minHeight:'44px'}},row?'Guardar respuesta en RO':'Guardar decisión en RO');let intento=null;
  function campo(label,node){fields.push(node);node.addEventListener('focus',guard);node.addEventListener('input',guard);form.append(h('label',{},label,node));return node;}
  let title,problema,reco,cli,tipo,decision,motivo,delegado;
  if(!row){title=campo('Qué hay que decidir',h('input',{type:'text',maxLength:200}));problema=campo('Problema',h('textarea',{maxLength:2000}));reco=campo('Recomendación',h('textarea',{maxLength:2000}));cli=campo('Cliente',h('select',{},h('option',{value:''},'Interno · sin cliente'),...arr(ctx.clientesVisibles).filter(c=>ambitoDecision382(ctx,c.id)).map(c=>h('option',{value:c.id},c.nombre||c.id))));tipo=campo('Destinatario',h('select',{},...Object.entries(tipos).map(([k,v])=>h('option',{value:k},v))));tipo.value='para_coti';}
  else{decision=campo('Decisión',h('select',{},h('option',{value:''},'Elige una decisión'),...opciones.map(x=>h('option',{value:x},x))));motivo=campo('Motivo (obligatorio al rechazar o delegar)',h('textarea',{maxLength:2000}));delegado=campo('Delegar en (solo si eliges Delegar)',h('select',{},h('option',{value:''},'Elige una persona'),...arr(ctx.datos?.personas).filter(p=>persona(ctx,p.id)).map(p=>h('option',{value:p.id},p.nombre))));}
  button.addEventListener('click',async()=>{
   if(!form.isConnected||!guard())return;if(intento?.estado==='guardando'||intento?.recibo)return;
   const cid=row?row.cliente_id:cli.value||null;
   if(!ambitoDecision382(ctx,cid)){form.replaceChildren();return;}
   try{if(!intento){let b;if(row){if(!decision.value||(!motivo.value.trim()&&decision.value!=='Aprobar la recomendación'))throw Error('Elige decisión y motivo.');if(decision.value==='Delegar'&&!persona(ctx,delegado.value))throw Error('Elige una persona activa y única.');b={operacion:'responder',id:row.id,revision:row.revision,decision:decision.value,motivo:motivo.value.trim()||null,delegada_en:decision.value==='Delegar'?delegado.value:null};}
     else{if(!title.value.trim()||!problema.value.trim()||!reco.value.trim())throw Error('Completa título, problema y recomendación.');b={operacion:'nueva',cliente_id:cid,tipo:tipo.value,titulo:title.value.trim(),problema:problema.value.trim(),recomendacion:reco.value.trim()};}
     intento=prepararDecision382(ctx,b,crypto.randomUUID(),cid,row);fields.forEach(x=>x.disabled=true);}
    button.disabled=true;mensaje.replaceChildren('Guardando en RO…');await guardarDecision382(ctx,intento,p=>ctx.api('operaciones/decisiones-locales',{metodo:'POST',cuerpo:p}));
    if(!guard())return;mensaje.replaceChildren(intento.mensaje);button.disabled=!!intento.recibo;button.replaceChildren(intento.recibo?'Guardado en RO':'Reintentar mismo contenido');
    if(intento.recibo){status.replaceChildren('Guardado en RO. Consultando el registro; no acredita ejecución.');await cargar(false);}
   }catch(e){if(guard()){mensaje.replaceChildren(intento?'Resultado sin confirmar. Reintenta la misma intención.':e.message);button.disabled=false;}}
  });form.append(button,mensaje);return form;
 }
 function pintar(){if(!guard()||!model)return;body.replaceChildren();
  if(ambitoDecision382(ctx,null)){const nuevo=h('details',{on:{toggle:()=>{guard();}}},h('summary',{},'Nueva decisión · revisión de Coti por defecto'),editor());body.append(nuevo);}
  const table=h('table',{class:'densa'}),thead=h('thead',{},h('tr',{},...['Problema / título','Recomendación','Fecha','Destinatario','Estado','Decisión histórica / detalle'].map(x=>h('th',{scope:'col'},x)))),tbody=h('tbody',{});table.append(thead,tbody);
  for(const r of model.filas){const details=h('details',{on:{toggle:()=>{if(!guard())return;if(!ambitoDecision382(ctx,r.cliente_id,false))details.replaceChildren();}}},h('summary',{},'Abrir detalle'),h('p',{},r.problema),h('p',{},r.recomendacion));
   if(r.respuesta)details.append(h('p',{},r.respuesta.decision),h('p',{},r.respuesta.motivo||'Sin motivo registrado'),r.respuesta.delegada_en?h('p',{},`Delegada en ${nombre(r.respuesta.delegada_en)} · registro, no notificación`):h('span',{}));
   else if(r.respuesta_registrada)details.append(h('p',{},'Respuesta histórica sin contenido tipado disponible.'));
   if(r.puede_responder&&!r.respuesta_registrada&&ambitoDecision382(ctx,r.cliente_id))details.append(editor(r));
   tbody.append(h('tr',{},h('td',{},h('b',{},r.titulo),h('div',{class:'small'},breve(r.problema,120))),h('td',{},breve(r.recomendacion)),h('td',{class:'small',title:r.creada?'Fuente del registro UTC: '+r.creada:'Fecha de registro desconocida'},fecha(r.creada).replace(' · Madrid','')),h('td',{},tipos[r.tipo]),h('td',{},!r.respuesta_registrada?'Pendiente de decisión':'Respuesta registrada'),h('td',{},r.respuesta?h('div',{class:'small'},r.respuesta.decision):null,details)));
  }
  if(!model.filas.length)body.append(h('p',{class:'sub'},'Sin decisiones en la colección autorizada.'));
  else body.append(h('div',{class:'scroll'},table));status.replaceChildren(`${model.filas.length} registros locales${model.truncado?' · colección limitada a 1.000':''}. No acreditan ejecución.`);
 }
 async function cargar(inicialCarga=true){const n=++epoch;try{const D=await ctx.api('operaciones/decisiones-locales');if(!guard()||n!==epoch)return;const next=proyectarDecisiones387(ctx,D);if(!next)throw Error('Fuente no válida');model=next;pintar();}catch{if(guard()){status.replaceChildren('No se pudo consultar el registro actual. No se crean filas ni decisiones por defecto.');if(inicialCarga)body.replaceChildren();}}}
 await cargar();return base;
}
