// Una revisión local no cambia la asistencia ni el resultado comercial de la fuente.
export function revisionCita334(x,revisados){
 const a=revisados?.get?.(`cita ${x.ref}`);
 return a?.tipo==='revisado_cita'&&a.objeto===`cita ${x.ref}`&&a.cliente_id===x.cliente_id&&typeof x.cliente_id==='string'&&x.cliente_id&&Number.isSafeInteger(a.id)&&a.id>0?{registrada:true,asistencia_verificada:false,venta_verificada:false,texto:'Revisión local registrada · resultado pendiente en la fuente'}:{registrada:false,asistencia_verificada:false,venta_verificada:false,texto:'Sin revisión local registrada · resultado pendiente en la fuente'};
}
export function citasPendientes334(rows,base){
 return (Array.isArray(rows)?rows:[]).filter(x=>{const fs=(Array.isArray(base)?base:[]).filter(f=>f.sub_id===x.sub_id&&f.cliente_id===x.cliente_id);return fs.length===1;});
}
export function estadoRevisionCita334(h,x,d){const n=h('small',{},revisionCita334(x,d.revisados).texto);d.nodosRevisionCita334??=new Map();const key=`cita ${x.ref}`;if(!d.nodosRevisionCita334.has(key))d.nodosRevisionCita334.set(key,new Set());d.nodosRevisionCita334.get(key).add(n);return n;}
export function crearRevisionCita334(h,ctx,x,d,motivos){
 const real=ctx.real?.id,vista=ctx.persona?.id;let busy=false;
 const root=h('details',{}),status=h('small',{role:'status'},revisionCita334(x,d.revisados).texto);
 const scope=()=>{const cs=(ctx.clientesVisibles||[]).filter(c=>c?.id===x.cliente_id);return cs.length===1&&cs[0].activo_confirmado===true&&cs[0].detalle===true&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:x.cliente_id})?.ok===true;};
 const actoresActivos=()=>{const ps=Array.isArray(ctx.datos?.personas)?ctx.datos.personas:[];return [ctx.real,ctx.persona].every(actor=>{const xs=ps.filter(p=>p?.id===actor?.id);return actor?.estado==='activo'&&actor.activo!==false&&xs.length===1&&xs[0].estado==='activo'&&xs[0].activo!==false;});};
 const vivo=()=>root.isConnected&&real===ctx.real?.id&&vista===ctx.persona?.id&&ctx.vigente?.()!==false&&ctx.veModulo?.('salud-crm')===true&&scope()&&actoresActivos();
 const editable=()=>vivo()&&real===vista&&ctx.servidor===true&&ctx.soloLectura!==true&&typeof x.ref==='string'&&x.ref;
 root.append(h('summary',{'aria-label':`Registrar revisión local de cita (${x.subcuenta})`},'Revisión RO'),status);
 for(const motivo of motivos){let intento=null;const b=h('button',{type:'button',class:'bt mini',style:{minHeight:'44px'}},motivo);root.append(b);
 b.addEventListener('click',async()=>{if(busy||!editable())return;
  if(!intento){const id=globalThis.crypto?.randomUUID?.();if(!id){status.textContent='No se puede crear una intención segura.';return;}intento={herramienta:'app',tipo:'revisado_cita',objeto:`cita ${x.ref}`,cliente_id:x.cliente_id,texto:motivo,vista_previa:'Revisión declarada en RO; no actualiza GHL ni acredita asistencia o resultado comercial.',intencion_id:id};}
  busy=true;b.disabled=true;status.textContent='Guardando revisión local…';
  try{if(!editable())throw Error('Acceso cambiado.');const r=await ctx.accion(intento);if(!vivo())return;
   if(r?.ok!==true||r.estado!=='simulada'||!Number.isSafeInteger(r.id)||r.id<1||r.intencion_guardada?.id!==intento.intencion_id||r.intencion_guardada?.accion_id!==r.id)throw Error('No se confirmó el registro local.');
   d.revisados?.set(intento.objeto,{...intento,id:r.id,hora:r.hora});intento=null;status.textContent=revisionCita334(x,d.revisados).texto;for(const node of d.nodosRevisionCita334?.get(`cita ${x.ref}`)||[])if(node.isConnected)node.textContent=status.textContent;
  }catch(e){if(vivo())status.textContent=`${e.message||'No se guardó la revisión.'} La cita sigue pendiente; reintenta el mismo motivo.`;}
  finally{busy=false;if(vivo())b.disabled=false;}
 });}
 return root;
}
