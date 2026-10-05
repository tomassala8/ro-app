// Una declaración RO no acredita llamada, respuesta, cualificación ni resolución en GHL.
const arr=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,120}$/.test(x);
const roles=x=>Array.isArray(x)&&x.length>0&&x.every(id)&&new Set(x).size===x.length;
const iguales=(a,b)=>roles(a)&&roles(b)&&JSON.stringify([...a].sort())===JSON.stringify([...b].sort());
const drafts=new Map(),binding=(ctx,x)=>JSON.stringify([ctx.real?.id,ctx.persona?.id,x.ref,x.sub_id,x.cliente_id]);
export function leadsPendientes369(rows,base){return arr(rows).filter(x=>id(x?.ref)&&id(x.sub_id)&&id(x.cliente_id)&&arr(rows).filter(r=>r?.ref===x.ref).length===1&&arr(base).filter(f=>f?.sub_id===x.sub_id).length===1&&arr(base).some(f=>f?.sub_id===x.sub_id&&f.cliente_id===x.cliente_id));}
export function revisionLead369(x,revisados){const a=revisados?.get?.(`lead ${x.ref}`);const registrada=a?.tipo==='revisado_lead'&&a.objeto===`lead ${x.ref}`&&a.cliente_id===x.cliente_id&&id(x.cliente_id)&&Number.isSafeInteger(a.id)&&a.id>0;return {registrada,contacto_verificado:false,resuelto_en_ghl:false,texto:registrada?'Revisión registrada en RO · pendiente en GHL':'Sin revisión RO · pendiente en GHL'};}
export function ambitoLead369(ctx,x,d){try{
 if(ctx.vigente?.()===false||ctx.veModulo?.('salud-crm')!==true)return null;
 const ps=arr(ctx.datos?.personas),as=[ctx.real,ctx.persona];
 if(!as.every(p=>id(p?.id)&&p.estado==='activo'&&p.activo!==false&&ps.filter(z=>z?.id===p.id).length===1&&ps.some(z=>z.id===p.id&&z.estado==='activo'&&z.activo!==false&&iguales(z.puestos,p.puestos))))return null;
 const cs=arr(ctx.clientesVisibles).filter(c=>c?.id===x.cliente_id);
 if(cs.length!==1||cs[0].activo_confirmado!==true||cs[0].detalle!==true||ctx.ver?.({tipo:'cliente_detalle',cliente_id:x.cliente_id})?.ok!==true)return null;
 if(!leadsPendientes369(d.leads_sin_tocar,d.subcuentas).some(r=>r.ref===x.ref&&r.sub_id===x.sub_id&&r.cliente_id===x.cliente_id))return null;
 return JSON.stringify([as,ps,cs,x.ref,x.sub_id,x.cliente_id,arr(ctx.datos?.asignaciones),d.subcuentas.map(r=>[r.sub_id,r.cliente_id]),ctx.ver({tipo:'cliente_detalle',cliente_id:x.cliente_id}).ok]);
 }catch{return null;}}
export function estadoRevisionLead369(h,x,d){const n=h('small',{},revisionLead369(x,d.revisados).texto);d.nodosRevisionLead369??=new Map();const key=`lead ${x.ref}`;if(!d.nodosRevisionLead369.has(key))d.nodosRevisionLead369.set(key,new Set());d.nodosRevisionLead369.get(key).add(n);return n;}
export function crearRevisionLead369(h,ctx,x,d,motivos){
 const root=h('details',{'data-revision-lead-369':x.ref}),key=binding(ctx,x),scope=ambitoLead369(ctx,x,d);
 const viva=()=>root.isConnected&&scope!==null&&ambitoLead369(ctx,x,d)===scope;
 const editable=()=>viva()&&ctx.servidor===true&&ctx.real.id===ctx.persona.id&&!ctx.soloLectura&&!ctx.pilotoLectura;
 const clear=()=>root.replaceChildren(h('small',{role:'status'},'Revisión no disponible con los permisos actuales.'));
 if(scope===null){clear();return root;}
 const status=h('small',{role:'status'},revisionLead369(x,d.revisados).texto);
 root.append(h('summary',{},'Revisión RO'),status);
 root.addEventListener('toggle',()=>{if(!viva())clear();});
 if(ctx.servidor!==true||ctx.real.id!==ctx.persona.id||ctx.soloLectura||ctx.pilotoLectura)return root;
 let draft=drafts.get(key);if(!draft){draft={intento:null,busy:false};drafts.set(key,draft);}
 for(const motivo of arr(motivos).filter(m=>typeof m==='string'&&m.length>0&&m.length<=300)){
 const b=h('button',{type:'button',class:'bt mini',style:{minHeight:'44px'}},motivo);root.append(b);
 b.addEventListener('click',async()=>{
  if(!editable()){clear();return;}if(draft.busy)return;
  // Una respuesta perdida bloquea otro motivo hasta confirmar la misma intención.
  if(draft.intento&&draft.intento.texto!==motivo){status.textContent='Hay una revisión sin confirmar. Reintenta el mismo motivo antes de preparar otra.';return;}
  if(!draft.intento){const uuid=globalThis.crypto?.randomUUID?.();if(!uuid){status.textContent='No se puede crear una intención segura.';return;}
   draft.intento=Object.freeze({herramienta:'app',tipo:'revisado_lead',objeto:`lead ${x.ref}`,cliente_id:x.cliente_id,texto:motivo,vista_previa:'Declaración de revisión en RO. No actualiza GHL ni acredita llamada, respuesta o resolución del lead.',intencion_id:uuid});}
  const intento=draft.intento;draft.busy=true;b.disabled=true;status.textContent='Guardando revisión en RO…';
  try{const r=await ctx.accion(intento);if(!viva()){clear();return;}
   if(r?.ok!==true||r.estado!=='simulada'||!Number.isSafeInteger(r.id)||r.id<1||r.texto!==intento.texto||r.vista_previa!==intento.vista_previa||r.intencion_guardada?.id!==intento.intencion_id||r.intencion_guardada?.accion_id!==r.id||typeof r.intencion_guardada.repetida!=='boolean')throw Error('Sin recibo local válido.');
   d.revisados??=new Map();d.revisados.set(intento.objeto,{...intento,id:r.id});draft.intento=null;
   status.textContent=revisionLead369(x,d.revisados).texto;
   for(const node of d.nodosRevisionLead369?.get(intento.objeto)||[])if(node.isConnected)node.textContent=status.textContent;
  }catch{if(viva())status.textContent='Registro sin confirmar. El lead sigue pendiente; reintenta el mismo motivo con la misma intención.';else clear();}
  finally{draft.busy=false;if(viva())b.disabled=false;}
 });}
 return root;
}
