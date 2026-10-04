import {h,chipEstado} from '../componentes.js';
const ESTADOS=[['empujado','Pedido al account · declarado'],['resuelto','Comprobado por mí · declarado'],['coti','Escalado · declarado'],['na','No aplica · declarado'],['anulado','Sin marca vigente']];
const arr=x=>Array.isArray(x)?x:[];
const firma=c=>JSON.stringify([c.real?.id,c.persona?.id]);
export function progreso300(filas,registros){
 const ids=arr(filas).map(x=>x?.id),counts=new Map();ids.forEach(id=>counts.set(id,(counts.get(id)||0)+1));
 const unicos=ids.filter(id=>typeof id==='string'&&counts.get(id)===1);
 const hechas=unicos.filter(id=>registros.get(id)?.actual&&registros.get(id).actual.estado!=='anulado').length;
 return {total:unicos.length,registradas:hechas,porcentaje:unicos.length?Math.round(hechas/unicos.length*100):null};
}
function ordenar300(x){if(Array.isArray(x))return x.map(ordenar300);if(x&&typeof x==='object')return Object.fromEntries(Object.keys(x).sort().map(k=>[k,ordenar300(x[k])]));return x;}
export async function hashFuente300(actor,row){if(!globalThis.crypto?.subtle)return null;const b=new TextEncoder().encode(JSON.stringify(ordenar300(['300.1',actor,row])));return [...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(x=>x.toString(16).padStart(2,'0')).join('');}
function registroValido(r,x,d,actor){return r&&r.actor===actor&&r.prioridad_id===x.prioridad_id&&r.fuente_revision===x.fuente_revision&&r.dia===d&&Number.isSafeInteger(r.revision)&&r.revision>0&&ESTADOS.some(([s])=>s===r.estado)&&typeof r.nota==='string'&&r.nota.length<=300&&typeof r.registrado_en==='string'&&Number.isFinite(Date.parse(r.registrado_en))&&r.origen==='local'&&r.declarado===true&&r.envio_realizado===false&&r.ejecucion_verificada===false;}
export async function renderPrioridades300(cont,ctx,filas,nombreCliente,vigenciaPadre=()=>true){
 const original=firma(ctx),root=h('section',{class:'panel prioridades300'});cont.append(root);
 const vigente=()=>root.isConnected&&firma(ctx)===original&&vigenciaPadre()&&(!ctx.vigente||ctx.vigente());
 const registros=new Map(),rows=arr(filas),primarias=rows.slice(0,20),resumen=h('small',{class:'sub',role:'status'},'Avance de hoy: pendiente de registrar.'),barra=h('progress',{max:100,value:0,'aria-label':'Prioridades con rastro local',style:{width:'100%',height:'6px',display:'block',accentColor:'var(--accent,#6366f1)'}});
 root.append(h('header',{},h('h2',{},'Tus prioridades de hoy'),resumen),barra);
 const estadoCarga=h('small',{class:'sub',role:'status'},'Leyendo el rastro local…');
 const cuerpo=h('tbody',{}),siguientes=h('tbody',{}),resto=h('tbody',{}),tabla=body=>h('table',{class:'densa',style:{width:'100%'}},h('thead',{},h('tr',{},[['Prioridad','Qué hay que empujar'],['Cliente / equipo','Cliente / equipo'],['Rastro','Seguimiento local'],['Abrir','Abrir']].map(([breve,completo])=>h('th',{scope:'col',title:completo,'aria-label':completo},breve)))),body);
 root.append(h('div',{'data-prioridades-visibles':'6',style:{overflowX:'auto'}},tabla(cuerpo)));
 const plegado=(marca,titulo,body)=>{const d=h('details',{[marca]:'300',on:{toggle:()=>{if(!vigente())root.replaceChildren();}}},h('summary',{style:{minHeight:'44px',padding:'12px 16px',boxSizing:'border-box',cursor:'pointer'}},titulo),h('div',{style:{overflowX:'auto'}},tabla(body)));return d;};
 if(primarias.length>6)root.append(plegado('data-prioridades-siguientes',`Siguientes ${primarias.length-6} · completan las primeras ${primarias.length}`,siguientes));
 if(rows.length>20)root.append(plegado('data-prioridades-resto',`Todas las demás prioridades · ${rows.length-20}`,resto));
 root.append(estadoCarga);
 if(!rows.length){estadoCarga.textContent='Sin prioridades en la copia disponible; no acredita que todo esté resuelto.';barra.removeAttribute('value');return;}
 let dia=null,permiso=false,cargando=false;const editores=[];
 const progreso=()=>{const p=progreso300(primarias,registros);resumen.textContent=`${p.registradas} de ${p.total} prioridades con rastro local${rows.length>20?' · primeras 20':''}`;if(p.porcentaje===null)barra.removeAttribute('value');else barra.value=p.porcentaje;};
 const clienteVivo=a=>!a.cliente_id||arr(ctx.clientesVisibles).filter(c=>c?.id===a.cliente_id).length===1&&arr(ctx.clientesVisibles).some(c=>c.id===a.cliente_id&&c.activo_confirmado===true&&c.detalle!==false)&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:a.cliente_id})?.ok===true;
 const puede=a=>vigente()&&clienteVivo(a)&&permiso&&!ctx.soloLectura&&ctx.real?.id===ctx.persona?.id;
 const cargar=async()=>{
  if(!vigente()||cargando)return;cargando=true;editores.forEach(e=>e.controles());
  try{const d=await ctx.api('operaciones/prioridades');if(!vigente())return;
   if(d?.version!=='300.1'||d.propietario!==ctx.persona.id||typeof d.dia!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(d.dia)||!Array.isArray(d.prioridades)||typeof d.puede_registrar!=='boolean')throw Error('Respuesta incompatible');
   const next=new Map();for(const a of rows){const xs=d.prioridades.filter(x=>x?.prioridad_id===a.id&&x.cliente_id===(a.cliente_id??null));if(xs.length!==1||!clienteVivo(a))continue;const x=xs[0];const tokenLocal=await hashFuente300(ctx.persona.id,a);if(!vigente())return;
    if(tokenLocal!==x.fuente_revision)continue;
    if(!/^[a-f0-9]{64}$/.test(x.fuente_revision)||!Number.isSafeInteger(x.revision)||x.revision<0||!(x.revision===0&&x.actual===null||registroValido(x.actual,x,d.dia,ctx.persona.id)&&x.actual.revision===x.revision)||!Array.isArray(x.historial)||x.historial.length>20||!x.historial.every(r=>/^\d{4}-\d{2}-\d{2}$/.test(r?.dia||'')&&registroValido(r,x,r.dia,ctx.persona.id)))continue;next.set(a.id,x);}
   registros.clear();next.forEach((v,k)=>registros.set(k,v));dia=d.dia;permiso=d.puede_registrar;editores.forEach(e=>e.reflejar());progreso();estadoCarga.textContent='Rastro propio local. No envía mensajes ni acredita ejecución externa.';
  }catch{if(vigente()){permiso=false;estadoCarga.textContent='Rastro no disponible. Las prioridades siguen visibles; no se ha confirmado ningún avance.';}}
  finally{cargando=false;if(vigente())editores.forEach(e=>e.controles());}
 };
 for(const [indice,a] of rows.entries()){
  const indicador=h('span',{title:'Sin registro confirmado','aria-label':'Sin registro confirmado'},chipEstado('gris','—')),nota=h('textarea',{rows:2,maxlength:300,'aria-label':'Nota del avance',placeholder:'A quién, qué respondió o qué comprobaste; sin contactos ni importes.',style:{width:'100%',minHeight:'64px',boxSizing:'border-box',border:'1px solid var(--line,#e1e4f1)',borderRadius:'8px',padding:'8px 10px',font:'inherit'}}),select=h('select',{'aria-label':'Seguimiento declarado',style:{width:'100%',minHeight:'44px',border:'1px solid var(--line,#e1e4f1)',borderRadius:'8px',padding:'6px 10px',font:'inherit',background:'#fff'}},ESTADOS.map(([s,t])=>h('option',{value:s},t))),guardar=h('button',{type:'button',class:'bt',disabled:true},'Guardar en RO'),recargar=h('button',{type:'button',class:'bt'},'Recargar versión'),mensaje=h('small',{role:'status',class:'sub'}),historia=h('details',{},h('summary',{},'Autor, fecha e historial'));
  const editor=h('details',{},h('summary',{title:'Registrar avance · seguimiento local',style:{minHeight:'44px',display:'flex',alignItems:'center',gap:'8px',boxSizing:'border-box',cursor:'pointer'}},indicador,h('span',{},'Registrar avance'),h('span',{'aria-hidden':'true'},'▸')),h('div',{style:{display:'grid',gap:'8px',minWidth:'200px',maxWidth:'360px',paddingBottom:'10px'}},select,nota,h('div',{style:{display:'flex',flexWrap:'wrap',gap:'6px'}},guardar,recargar),mensaje,historia));
  const ir=/^#\/[\w\-/]+$/.test(a.ir||'')?a.ir:'#/alertas';
  const tr=h('tr',{},h('td',{},a.titulo||a.tipo||'Prioridad'),h('td',{},a.cliente_id?nombreCliente(a.cliente_id):'Equipo'),h('td',{},editor),h('td',{},h('a',{href:ir,on:{click:e=>{if(!vigente()||!clienteVivo(a))e.preventDefault();}}},'Abrir')));(indice<6?cuerpo:indice<20?siguientes:resto).append(tr);
  let pendiente=null,enCurso=false,conflicto=false;
  const vivo=()=>vigente()&&tr.isConnected&&clienteVivo(a);
  const controles=()=>{guardar.disabled=!puede(a)||!registros.has(a.id)||enCurso||cargando||conflicto;nota.disabled=!puede(a)||enCurso||!!pendiente;select.disabled=nota.disabled;recargar.disabled=enCurso||cargando;};
  const reflejar=()=>{const x=registros.get(a.id),r=x?.actual;pendiente=null;conflicto=false;const etiqueta=r?ESTADOS.find(([s])=>s===r.estado)?.[1]:'Sin registro confirmado';indicador.setAttribute('title',etiqueta);indicador.setAttribute('aria-label',etiqueta);indicador.replaceChildren(chipEstado(r&&r.estado!=='anulado'?'azul':'gris',r?etiqueta:'—'));select.value=r?.estado||'empujado';nota.value=r?.nota||'';historia.replaceChildren(h('summary',{},'Autor, fecha e historial'),arr(x?.historial).map(y=>h('p',{class:'sub'},`${y.dia} · ${y.estado} · ${y.actor} · ${y.registrado_en} · ${y.nota||''}`)));mensaje.textContent=r?`Declarado por ${r.actor} · ${r.registrado_en}`:x?'Sin marca para hoy.':'Referencia exacta no disponible; consulta la alerta.';};
  recargar.addEventListener('click',async()=>{const texto=nota.value,estado=select.value;await cargar();if(vivo()){nota.value=texto;select.value=estado;}});
  guardar.addEventListener('click',async()=>{
   if(!vivo()||!puede(a)||enCurso||conflicto)return;const x=registros.get(a.id);if(!x)return;
   if(!pendiente){const uid=globalThis.crypto?.randomUUID?.();if(!uid){mensaje.textContent='No se pudo preparar una intención segura.';return;}pendiente={prioridad_id:a.id,fuente_revision:x.fuente_revision,dia,revision:x.revision,estado:select.value,nota:nota.value||'',intencion_id:uid};}
   enCurso=true;controles();mensaje.textContent='Guardando rastro en RO…';
   try{const d=await ctx.api('operaciones/prioridades',{metodo:'POST',cuerpo:pendiente});if(!vivo())return;const r=d?.recibo;
    if(d.version!=='300.1'||d.recibo_durable!==true||!['guardado','duplicado'].includes(d.resultado)||!registroValido(r,x,pendiente.dia,ctx.real.id)||r.revision!==pendiente.revision+1||r.estado!==pendiente.estado||r.intencion_id!==pendiente.intencion_id)throw Error('Recibo incompatible');
    registros.set(a.id,{...x,revision:r.revision,actual:r,historial:[r,...arr(x.historial)]});pendiente=null;reflejar();progreso();mensaje.textContent='Guardado en RO · declaración local; sin envío ni ejecución confirmados.';guardar.textContent='Guardar en RO';
   }catch(e){if(!vivo())return;conflicto=e?.codigo===409||e?.status===409||e?.code===409;mensaje.textContent=conflicto?'La prioridad o el avance cambió. Recarga conservando tu nota.':'Sin recibo confirmado. Reintenta la misma intención.';guardar.textContent='Reintentar guardado';}
   finally{enCurso=false;if(vivo())controles();}
  });editores.push({reflejar,controles});
 }
 // Las primeras veinte definen el avance; el resto sigue disponible en la misma tabla.
 if(!ctx.servidor){estadoCarga.textContent='Rastro local no disponible en esta copia estática.';return;}await cargar();
}
