// Registro local382. No ejecución del proveedor ni creación optimista de decisiones.
const uuid=x=>typeof x==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(x),arr=x=>Array.isArray(x)?x:[];
const id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,120}$/.test(x),revision=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
export function ambitoDecision382(ctx,cid,escritura=true){try{
 if(!ctx.servidor||ctx.vigente?.()===false||!ctx.veModulo?.('decisiones')||(escritura&&(ctx.real?.id!==ctx.persona?.id||ctx.soloLectura||ctx.pilotoLectura)))return null;
 const ps=arr(ctx.datos?.personas),actors=[ctx.real,ctx.persona];
 if(!actors.every(p=>id(p?.id)&&p.estado==='activo'&&p.activo!==false&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&x.estado==='activo'&&x.activo!==false&&Array.isArray(x.puestos)&&Array.isArray(p.puestos)&&p.puestos.every(id)&&new Set(p.puestos).size===p.puestos.length&&p.puestos.length&&JSON.stringify([...x.puestos].sort())===JSON.stringify([...p.puestos].sort()))))return null;
 if(cid!==null){if(!id(cid))return null;const cs=arr(ctx.clientesVisibles).filter(x=>x?.id===cid),canon=arr(ctx.clientes).filter(x=>x?.id===cid);if(cs.length!==1||cs[0].activo_confirmado!==true||cs[0].detalle===false||canon.length!==1||canon[0].activo_confirmado!==true||canon[0].detalle===false||ctx.ver?.({tipo:'cliente_detalle',cliente_id:cid})?.ok!==true)return null;}
 return JSON.stringify([actors,ps,cid,arr(ctx.clientes),arr(ctx.clientesVisibles),ctx.veModulo('decisiones'),cid===null?true:ctx.ver({tipo:'cliente_detalle',cliente_id:cid}).ok]);
}catch{return null;}}
export function prepararDecision382(ctx,b,clave,cliente_id=b.operacion==='nueva'?b.cliente_id:undefined,capacidad=null){
 if(!ambitoDecision382(ctx,cliente_id)||!uuid(clave)||!['nueva','responder'].includes(b.operacion))throw Error('Decisión no disponible con este contexto.');
 const fields=b.operacion==='nueva'?['operacion','cliente_id','tipo','titulo','problema','recomendacion']:['operacion','id','revision','decision','motivo','delegada_en'];
 if(JSON.stringify(Object.keys(b).sort())!==JSON.stringify(fields.sort())||Object.values(b).some(x=>x!==null&&typeof x!=='string'))throw Error('Contenido no admitido en esta decisión.');
 const payload=Object.freeze({...b,intencion_id:clave}),binding=JSON.stringify([ctx.real.id,ctx.persona.id,b.operacion,b.id??null,cliente_id]);
 if(b.operacion==='responder'&&(capacidad?.puede_responder!==true||capacidad.id!==b.id||capacidad.revision!==b.revision||capacidad.cliente_id!==cliente_id||!['para_tomas','para_coti','escalada'].includes(capacidad.tipo)))throw Error('Necesitas la capacidad actual de la decisión para responder.');
 if(b.operacion==='responder'&&(!/^db-[1-9][0-9]{0,12}$/.test(b.id||'')||!revision(b.revision)))throw Error('Lee primero la revisión actual de esta decisión.');
 return {payload,binding,cliente_id,scope:null,estado:'preparado',recibo:null,mensaje:'Decisión preparada; aún no guardada.'};
}
export function reciboDecision382(r,i){const g=r?.recibo,p=i.payload;
 if(r?.version!=='382.1'||!['guardado','duplicado'].includes(r.resultado)||g?.intencion_id!==p.intencion_id||g.operacion!==p.operacion||g.autor!==JSON.parse(i.binding)[0]||!/^db-[1-9][0-9]{0,12}$/.test(g.id||'')||!revision(g.revision)||g.guardado_local!==true||g.envio_realizado!==false||g.ejecucion_verificada!==false||(p.operacion==='responder'&&g.id!==p.id))return null;
 return Object.freeze({intencion_id:g.intencion_id,id:g.id,revision:g.revision,guardado_local:true,envio_realizado:false,ejecucion_verificada:false});
}
export async function guardarDecision382(ctx,i,enviar){
 const scope=ambitoDecision382(ctx,i.cliente_id),bound=JSON.parse(i.binding);
 if(!scope||bound[0]!==ctx.real.id||bound[1]!==ctx.persona.id||i.estado==='guardando'||i.recibo)return false;
 i.scope=scope;i.estado='guardando';i.mensaje='Guardando decisión en RO…';const vivo=()=>ambitoDecision382(ctx,i.cliente_id)===i.scope;
 try{const r=await enviar(i.payload);if(!vivo()){i.estado='sin_confirmar';i.mensaje='El contexto cambió. Conserva la intención y vuelve a consultar.';return false;}i.recibo=reciboDecision382(r,i);
 }catch{i.recibo=null;}
 i.estado=i.recibo?'guardado':'sin_confirmar';i.mensaje=i.recibo?'Decisión guardada en RO; no acredita ejecución ni envío.':'Resultado sin confirmar. Reintenta la misma intención y el mismo contenido.';
 return vivo();
}
// Integración futura: render con h real, cache de intentos en dueño de pantalla.
export function botonDecision382({h,ctx,intento,vigente=()=>true,alGuardado=()=>{}}){
 const root=h('div',{class:'fila'}),estado=h('span',{role:'status'},intento.mensaje);
 const vivo=()=>root.isConnected&&vigente()&&ambitoDecision382(ctx,intento.cliente_id)!==null;
 const b=h('button',{type:'button',class:'bt mini',style:{minHeight:'44px'},disabled:!!intento.recibo,on:{click:async()=>{
  if(!vivo()){root.replaceChildren();return;}if(intento.estado==='guardando'||intento.recibo)return;b.disabled=true;
  await guardarDecision382(ctx,intento,p=>ctx.api('operaciones/decisiones-locales',{metodo:'POST',cuerpo:p}));
  if(!vivo()){root.replaceChildren();return;}estado.replaceChildren(intento.mensaje);b.disabled=!!intento.recibo;b.replaceChildren(intento.recibo?'Guardado en RO':'Reintentar misma intención');if(intento.recibo)alGuardado(intento.recibo);
 }}},'Guardar decisión en RO');root.append(b,estado);return root;
}
