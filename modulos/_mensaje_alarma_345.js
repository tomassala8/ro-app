// Mensaje interno editable: copia manual, sin envío ni registro de actividad.
const arr=x=>Array.isArray(x)?x:[];
const id=x=>typeof x==='string'&&/^[a-zA-Z0-9_-]{1,200}$/.test(x);
const activo=p=>p?.estado==='activo'&&p.activo!==false;
const roles=(a,b)=>Array.isArray(a)&&Array.isArray(b)&&a.length>0&&a.every(id)&&b.every(id)&&new Set(a).size===a.length&&new Set(b).size===b.length&&JSON.stringify([...a].sort())===JSON.stringify([...b].sort());
const fecha=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
const nombre=x=>typeof x==='string'&&!/[<>\u0000-\u001f]|https?:|www\.|@|\b\d{7,}\b/i.test(x)&&x.trim().length>0&&x.trim().length<=160?x.trim():null;
function receptorActual(ctx,c){
 const ps=arr(ctx.datos?.personas),rows=[...arr(c.equipo?.account),...arr(ctx.datos?.asignaciones).filter(a=>a?.cliente_id===c.id&&a.silla==='account')];
 const actuales=[];
 for(const a of rows){
  if(!a||typeof a!=='object')return null;
  if(a.desde!=null&&(!fecha(a.desde)))return null;if(a.hasta!=null&&!fecha(a.hasta))return null;
  if((a.desde&&a.desde>ctx.hoy)||(a.hasta&&a.hasta<ctx.hoy)||a.principal===false||a.suplencia===true)continue;
  // Un registro ambiguo no se descarta para escoger otro más conveniente.
  if(a.principal!==true||a.duda||a.confianza!=='confirmada'||!id(a.persona_id))return null;
  actuales.push(a.persona_id);
 }
 const ids=[...new Set(actuales)];if(ids.length!==1)return null;
 const p=ps.filter(p=>p?.id===ids[0]);return p.length===1&&activo(p[0])&&arr(p[0].puestos).includes('account')&&nombre(p[0].alias||p[0].nombre)?p[0]:null;
}
export function contextoMensajeAlarma345(ctx,a,categoria){try{
 if(!ctx.servidor||ctx.soloLectura||ctx.pilotoLectura||ctx.real?.id!==ctx.persona?.id||ctx.vigente?.()===false||!ctx.veModulo?.('bandeja')||!ctx.veModulo?.('alertas')||!fecha(ctx.hoy)||typeof ctx.ver!=='function'||!id(a?.cliente_id)||!id(a?.tipo)||typeof a?.id!=='string'||!a.id||a.id.length>300||!nombre(categoria)||categoria==='Otro tipo de alarma')return null;
 const ps=arr(ctx.datos?.personas),actores=[ctx.real,ctx.persona];
 if(!actores.every(p=>id(p?.id)&&activo(p)&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&activo(x)&&roles(p.puestos,x.puestos))&&arr(p.puestos).some(r=>['account','operaciones','direccion'].includes(r))))return null;
 const cs=arr(ctx.clientesVisibles).filter(c=>c?.id===a.cliente_id);if(cs.length!==1||cs[0].activo_confirmado!==true||cs[0].detalle!==true||!nombre(cs[0].nombre))return null;
 if(!['cliente_detalle','alarma_detalle'].every(tipo=>ctx.ver({tipo,cliente_id:a.cliente_id})?.ok===true))return null;
 const receptor=receptorActual(ctx,cs[0]);if(!receptor)return null;
 const propia=ctx.persona.puestos.includes('account')&&!ctx.persona.puestos.some(r=>['operaciones','direccion'].includes(r));
 if(propia&&(!new Set(ctx.carteraPorSilla?.account||[]).has(a.cliente_id)||receptor.id!==ctx.persona.id))return null;
 const corte=typeof a.corte==='string'?a.corte:'';if(!fecha(corte.slice(0,10))||corte.slice(0,10)>ctx.hoy||!Number.isFinite(Date.parse(corte.replace(' ','T'))))return null;
 return {receptor_id:receptor.id,receptor:nombre(receptor.alias||receptor.nombre),cliente:nombre(cs[0].nombre),categoria,corte,
  firma:JSON.stringify([actores,ctx.hoy,cs[0],ps,arr(ctx.datos?.asignaciones),[...(ctx.carteraPorSilla?.account||[])].sort(),a.id,a.tipo,categoria,corte])};
 }catch{return null;}}
export function borradorMensajeAlarma345(ctx,a,categoria){
 const c=contextoMensajeAlarma345(ctx,a,categoria);if(!c)return null;
 const peticion=a.tipo.startsWith('alta_')?'comprueba el estado del arranque y acuerda el siguiente paso con fecha':a.tipo.startsWith('crm_')?'contrasta el registro del CRM y el resultado pendiente con el despacho':a.tipo.startsWith('pub_')?'contrasta con el especialista la medición, el estado de la campaña y qué revisión corresponde':a.tipo.startsWith('acc_informe')?'comprueba el informe y su evidencia de envío antes de darlo por resuelto':a.tipo.startsWith('acc_sin_reunion')?'comprueba las reuniones registradas y qué seguimiento corresponde según el método vigente':'comprueba su estado actual con la fuente y el especialista correspondiente';
 return {...c,texto:`Hola ${c.receptor}, sobre ${c.cliente}: en la copia del ${c.corte} aparece «${c.categoria}». ¿Puedes revisarlo? ${peticion.charAt(0).toUpperCase()+peticion.slice(1)}. Confirma qué está comprobado, qué falta, quién se encarga y el próximo paso con fecha. Es un borrador interno: la incidencia de la copia no acredita el estado actual ni que se haya enviado o ejecutado ninguna acción.`};
}
export function crearMensajeAlarma345(h,ctx,alarma,categoria,vigente=()=>true){
 const root=h('details',{'data-mensaje-alarma':'345'}),area=h('textarea',{'aria-label':'Borrador interno para el account',rows:4,style:{width:'100%',boxSizing:'border-box',font:'inherit',padding:'10px',border:'1px solid #e1e4f1',borderRadius:'8px',background:'#fff',color:'inherit'}}),status=h('small',{role:'status'},'Copiar no envía ni registra una acción.'),btn=h('button',{type:'button',class:'bt mini',disabled:true,style:{minHeight:'44px',marginTop:'8px',marginRight:'8px'}},'Copiar borrador');
 root.append(h('summary',{},'Mensaje interno para el account'),area,btn,status);
 let original=null,firma=null;
 const actual=()=>root.isConnected&&vigente()?borradorMensajeAlarma345(ctx,alarma(),categoria):null;
 function limpiar(){area.value='';btn.disabled=true;status.textContent='Borrador no disponible: comprueba acceso y account confirmado.';original=firma=null;}
 function actualizar(){const d=actual();if(!d){limpiar();return;}if(firma!==d.firma||original!==d.texto){area.value=d.texto;original=d.texto;firma=d.firma;}btn.disabled=false;}
 root.addEventListener('toggle',actualizar);area.addEventListener('input',()=>{const d=actual();if(!d||d.firma!==firma)limpiar();});
 btn.addEventListener('click',async()=>{const d=actual();if(!d||d.firma!==firma){limpiar();return;}const texto=area.value;if(typeof texto!=='string'||!texto.trim()||texto.length>3000||/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(texto)){status.textContent='Revisa el borrador: vacío, inválido o demasiado largo.';return;}btn.disabled=true;
  try{if(!globalThis.navigator?.clipboard?.writeText)throw Error('sin portapapeles');await navigator.clipboard.writeText(texto);const despues=actual();if(!despues||despues.firma!==firma){limpiar();return;}status.textContent='Copiado. No se ha enviado ni registrado ninguna acción.';
  }catch{const despues=actual();if(!despues||despues.firma!==firma)limpiar();else status.textContent='No se pudo copiar. Selecciona el texto y cópialo manualmente.';
  }finally{const despues=actual();if(despues&&despues.firma===firma)btn.disabled=false;}
 });return {elemento:root,actualizar};
}
