// Borrador manual. No envía mensajes, registra pedidos ni interpreta textos externos.
const texto=v=>typeof v==='string'?v.replace(/[<>\u0000-\u001f]/g,' ').trim().slice(0,120):'';
export function mensajeIncidencia330(ctx,row,cap){
 const cs=Array.isArray(ctx.clientesVisibles)?ctx.clientesVisibles.filter(c=>c?.id===row.cliente_id):[];
 if(ctx.servidor!==true||ctx.soloLectura===true||ctx.real?.id!==ctx.persona?.id||ctx.veModulo?.('bandeja')!==true||ctx.vigente?.()===false||cs.length!==1||cs[0].activo_confirmado!==true||cs[0].detalle!==true||ctx.ver?.({tipo:'cliente_detalle',cliente_id:row.cliente_id})?.ok!==true||ctx.ver?.({tipo:'responder_cliente',cliente_id:row.cliente_id})?.ok!==true||cap?.puede_registrar!==true||cap.cliente_id!==row.cliente_id||cap.tipo!==row.tipo||cap.referencia_id!==row.referencia_id||typeof cap.receptor!=='string'||!cap.receptor||!['responder_correo','devolver_llamada'].includes(row.tipo))return null;
 const cliente=texto(cs[0].nombre);if(!cliente)return null;
 const catalogo=Array.isArray(ctx.datos?.personas)?ctx.datos.personas:[];
 const ps=catalogo.filter(p=>p?.id===cap.receptor),actores=catalogo.filter(p=>p?.id===ctx.real?.id);
 // La capacidad de294 no sustituye el catálogo actual al componer un destinatario.
 if(ps.length!==1||ps[0].estado!=='activo'||ps[0].activo===false||actores.length!==1||actores[0].estado!=='activo'||actores[0].activo===false)return null;
 const receptor=texto(ps[0].alias||ps[0].nombre);if(!receptor||!texto(actores[0].alias||actores[0].nombre))return null;
 const accion=row.tipo==='responder_correo'?'revisar el correo señalado en Bandeja y confirmar si requiere respuesta':'revisar la llamada señalada en Bandeja y confirmar si requiere devolución';
 return `Hola ${receptor||'equipo'}, sobre ${cliente}: ¿puedes ${accion}? Confirma qué has hecho, si existe algún bloqueo y el siguiente paso con fecha. Este mensaje es un borrador manual; la incidencia de la copia requiere comprobar su estado actual.`;
}
export function crearMensajeIncidencia330(h,ctx,row,capacidad,vigente){
 const root=h('details',{'data-mensaje-incidencia':'330'}),area=h('textarea',{'aria-label':'Borrador de mensaje para el account',rows:4,style:'width:100%;box-sizing:border-box;font:inherit'}),estado=h('small',{},'Revisa y envía manualmente; copiar no envía ni registra una acción.'),btn=h('button',{type:'button',disabled:true,style:'min-height:44px'},'Copiar mensaje');
 root.append(h('summary',{},'Mensaje para el account'),area,btn,estado);const real=ctx.real?.id,vista=ctx.persona?.id;let original=null;
 const actual=()=>root.isConnected&&vigente()&&real===ctx.real?.id&&vista===ctx.persona?.id?mensajeIncidencia330(ctx,row,capacidad()):null;
 function actualizar(){const nuevo=actual();if(!nuevo){area.value='';btn.disabled=true;estado.textContent='Mensaje no disponible: revisa el acceso y el destinatario.';original=null;return;}if(original!==nuevo){area.value=nuevo;original=nuevo;}btn.disabled=false;}
 root.addEventListener('toggle',actualizar);
 btn.addEventListener('click',async()=>{if(!actual()){actualizar();return;}const draft=area.value;if(typeof draft!=='string'||!draft.trim()||draft.length>3000){estado.textContent='Revisa el borrador: vacío o demasiado largo.';return;}btn.disabled=true;
  try{if(!globalThis.navigator?.clipboard?.writeText)throw Error('sin portapapeles');await navigator.clipboard.writeText(draft);if(!actual()){actualizar();return;}estado.textContent='Copiado. No se ha enviado ni registrado ninguna acción.';}catch{if(actual())estado.textContent='No se pudo copiar. Selecciona el texto y cópialo manualmente.';}finally{if(actual())btn.disabled=false;}
 });return {elemento:root,actualizar};
}
