//273 · Declaración semanal propia. Conseguida no es pedida ni respuesta verificada por API.
import {h,chipEstado} from '../componentes.js';
export const COLUMNAS_FEEDBACK273=['Conseguida','Cliente','Leads 30 días','Qué dijo'];
const ESTADOS273=[['sin_opinion','Sin opinión registrada'],['pedida','Pedida'],['conseguida','Conseguida · declarada']];
const arr=v=>Array.isArray(v)?v:[];
const dia=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s+'T00:00:00Z'))&&new Date(s+'T00:00:00Z').toISOString().slice(0,10)===s;
const semana=s=>dia(s)&&new Date(s+'T00:00:00Z').getUTCDay()===1;
const identidad=ctx=>JSON.stringify([ctx.real?.id,ctx.persona?.id]);
function validoRegistro(r,cid,sem,revision){return r&&r.cliente_id===cid&&r.semana===sem&&r.revision===revision&&ESTADOS273.some(x=>x[0]===r.estado)&&typeof r.autor==='string'&&typeof r.nota==='string'&&r.nota.length<=300&&typeof r.registrado_en==='string'&&Number.isFinite(Date.parse(r.registrado_en))&&r.declarado===true&&r.origen==='local'&&r.envio_realizado===false&&r.respuesta_verificada===false;}
function validoGet(d,cid){return d?.version==='273.1'&&d.cliente_id===cid&&semana(d.semana)&&Number.isSafeInteger(d.revision)&&d.revision>=0&&d.capacidades&&typeof d.capacidades.puede_registrar==='boolean'&&((d.revision===0&&d.actual===null)||(d.revision>0&&validoRegistro(d.actual,cid,d.semana,d.revision)))&&Array.isArray(d.historial)&&d.historial.every(r=>Number.isSafeInteger(r?.revision)&&r.revision>0&&semana(r.semana)&&validoRegistro(r,cid,r.semana,r.revision));}
export async function renderFeedback273(cont,ctx,filas=[]){
 const firma=identidad(ctx),root=h('section',{class:'panel feedback273','data-feedback-273':'273.1'});cont.append(root);
 const vigente=()=>root.isConnected&&identidad(ctx)===firma&&(!ctx.vigente||ctx.vigente())&&ctx.veModulo?.('bandeja');
 if(!ctx.servidor||!ctx.veModulo?.('bandeja'))return;
 const catalogo=arr(ctx.clientesVisibles),ids=new Map();for(const f of arr(filas))ids.set(f?.cliente_id,(ids.get(f?.cliente_id)||0)+1);
 const autorizadas=arr(filas).filter(f=>ids.get(f?.cliente_id)===1&&catalogo.filter(c=>c?.id===f.cliente_id).length===1&&catalogo.some(c=>c.id===f.cliente_id&&c.activo_confirmado===true&&c.detalle===true));
 root.append(h('style',{},'.feedback273 td{padding:8px 10px;vertical-align:middle;font-size:13px;line-height:1.3}.feedback273 .fb273-nota{display:block;max-width:32ch;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.feedback273 details>summary{cursor:pointer;font-size:12px;padding:4px 0}.feedback273 .fb273-editor{display:grid;gap:8px;padding:10px 0}.feedback273 .fb273-editor button,.feedback273 .fb273-editor select{min-height:44px}.feedback273 textarea{width:100%;box-sizing:border-box}.feedback273 th{white-space:normal}'));
 root.append(h('header',{},h('h2',{},'Opinión del cliente sobre la captación · esta semana'),h('small',{class:'sub'},'Conseguida requiere la opinión del cliente; pedirla no basta. Registro propio local.')));
 const body=h('tbody',{});root.append(h('div',{style:{overflowX:'auto'}},h('table',{class:'densa',style:{width:'100%',minWidth:'760px'}},h('thead',{},h('tr',{},COLUMNAS_FEEDBACK273.map((t,i)=>h('th',{scope:'col'},i===2?'Recuento Meta · 30 días':t)))),body)));
 if(!autorizadas.length){body.append(h('tr',{},h('td',{colspan:4},'Sin filas autorizadas; no acredita que no haya leads ni opiniones.')));return;}
 const montar=async(f)=>{
  const cid=f.cliente_id,c=catalogo.find(x=>x.id===cid),estado=h('select',{'aria-label':`Estado de opinión de ${c.nombre}`},ESTADOS273.map(([id,t])=>h('option',{value:id},t))),nota=h('textarea',{rows:2,maxlength:300,'aria-label':`Qué dijo ${c.nombre}`,placeholder:'Nota opcional de la opinión; sin contactos ni importes.'});
  const status=h('small',{class:'sub',role:'status'},'Leyendo registro…'),guardar=h('button',{type:'button',class:'bt mini',disabled:true},'Guardar en RO'),recargar=h('button',{type:'button',class:'bt mini'},'Recargar versión'),historia=h('details',{},h('summary',{},'Autor, fecha e historial'));
  const m=f.muestra,acreditado=m?.semantica?.eventos_lead_acreditados===true;
  const leads=Number.isSafeInteger(m?.valor)&&m.valor>=0&&(m.valor>0||acreditado)?`≥${m.valor}`:'Sin dato';
  const indicador=h('span',{},chipEstado('gris','Leyendo')),resumenNota=h('span',{class:'fb273-nota'},'Sin dato');
  const editor=h('details',{},h('summary',{},'Editar registro'),h('div',{class:'fb273-editor'},estado,nota,h('div',{},guardar,recargar),status,historia));
  const tr=h('tr',{},h('td',{},indicador),h('td',{},ctx.veModulo('ficha')?h('a',{href:`#/ficha/${encodeURIComponent(cid)}`},c.nombre):c.nombre),h('td',{title:m?`${m.desde||'Sin fecha'} → ${m.hasta||'Sin fecha'}; copia parcial; ${m.semantica?.detalle||'Definición de evento pendiente; no acredita leads ni compras.'}`:'Sin serie30d compatible.'},leads,h('small',{style:{display:'block',fontSize:'11px',color:'#777d9b'}},acreditado?'Eventos lead Meta':'Evento por confirmar')),h('td',{},resumenNota,editor));body.append(tr);
  let lectura=null,pendiente=null,enCurso=false,conflicto=false;
  const vivo=()=>vigente()&&tr.isConnected;
  const puede=()=>vivo()&&lectura?.capacidades?.puede_registrar===true&&!ctx.soloLectura&&ctx.real?.id===ctx.persona?.id;
  const reflejar=r=>{const texto=r?.estado==='conseguida'?'Conseguida · declarada':r?.estado==='pedida'?'Pedida':'Sin opinión registrada';indicador.replaceChildren(chipEstado(r?.estado==='conseguida'?'verde':r?.estado==='pedida'?'ambar':'gris',texto));resumenNota.textContent=r?.nota||'Sin nota';resumenNota.title=r?.nota||'Nota opcional; opinión declarada, no recepción verificada automáticamente.';};
  const controles=()=>{guardar.disabled=!puede()||enCurso||conflicto;nota.disabled=!puede()||enCurso||!!pendiente;estado.disabled=nota.disabled;recargar.disabled=enCurso;};
  const cargar=async(conservar=false)=>{
   if(!vivo()||enCurso)return;enCurso=true;controles();
   try{const d=await ctx.api(`operaciones/feedback?cliente_id=${encodeURIComponent(cid)}`);if(!vivo())return;if(!validoGet(d,cid))throw Error('Respuesta incompatible');
     lectura=d;pendiente=null;conflicto=false;reflejar(d.actual);
     if(!conservar){estado.value=d.actual?.estado||'sin_opinion';nota.value=d.actual?.nota||'';}
     status.textContent=d.actual?`Declarado por ${d.actual.autor} · ${d.actual.registrado_en} · no es envío ni recepción automática`:'Sin declaración de opinión esta semana.';
     historia.replaceChildren(h('summary',{},'Autor, fecha e historial'),...d.historial.map(r=>h('p',{class:'sub'},`${r.semana} · ${r.estado} · ${r.autor} · ${r.registrado_en}${r.nota?' · '+r.nota:''}`)),d.historial_truncado?h('small',{},'Historial limitado a los últimos100 registros.'):null);
   }catch{if(vivo()){lectura=null;indicador.replaceChildren(chipEstado('gris','Sin dato'));status.textContent='No se pudo leer el registro. No se confirma ninguna opinión.';}}
   finally{enCurso=false;if(vivo())controles();}
  };
  recargar.addEventListener('click',()=>cargar(true));
  guardar.addEventListener('click',async()=>{
   if(!puede()||enCurso||conflicto)return;
   if(!pendiente){const uid=globalThis.crypto?.randomUUID?.();if(!uid){status.textContent='No se puede crear una intención segura en este navegador.';return;}pendiente={cliente_id:cid,semana:lectura.semana,estado:estado.value,nota:nota.value||'',revision:lectura.revision,intencion_id:uid};}
   enCurso=true;controles();status.textContent='Guardando declaración en RO…';
   try{const d=await ctx.api('operaciones/feedback',{metodo:'POST',cuerpo:pendiente});if(!vivo())return;
     const r=d?.recibo;if(!['guardado','duplicado'].includes(d?.resultado)||d.version!=='273.1'||d.cliente_id!==cid||d.semana!==pendiente.semana||d.intencion_id!==pendiente.intencion_id||!validoRegistro(r,cid,pendiente.semana,pendiente.revision+1)||r.autor!==ctx.real.id||r.estado!==pendiente.estado||r.intencion_id!==pendiente.intencion_id)throw Error('Recibo incompatible');
     lectura={...lectura,revision:r.revision,actual:r};pendiente=null;reflejar(r);nota.value=r.nota;status.textContent=`Guardado en RO · ${r.autor} · ${r.registrado_en} · declaración propia, no envío ni recepción automática`;guardar.textContent='Guardar en RO';
     historia.append(h('p',{class:'sub'},`${r.semana} · ${r.estado} · ${r.autor} · ${r.registrado_en}`));
   }catch(e){if(!vivo())return;conflicto=e?.codigo===409||e?.status===409||e?.code===409;
     status.textContent=conflicto?'Cambió el registro. Recarga la versión conservando tu nota antes de guardar.':'Sin recibo confirmado. Reintenta la misma intención o recarga conservando tu nota.';guardar.textContent='Reintentar guardado';
   }finally{enCurso=false;if(vivo())controles();}
  });
  controles();await cargar();
 };
 await Promise.all(autorizadas.map(montar));
}
// Alias sencillo para integrar desde270 o una ficha, conservando las cuatro columnas.
export const panelFeedback273=(cont,ctx,cliente,muestra=null)=>renderFeedback273(cont,ctx,[{cliente_id:cliente?.id||cliente?.cliente_id,muestra}]);
