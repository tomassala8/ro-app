import {h} from '../componentes.js';
const arr=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,150}$/.test(x);
const roles=['direccion','operaciones','account','trafficker','jefa_publicidad'];
const activo=x=>x?.estado==='activo'&&x.activo!==false;
export function ambitoUrgencias406(ctx){try{
 if(ctx.servidor!==true||ctx.vigente?.()===false||!roles.some(r=>ctx.persona?.puestos?.includes(r))||!roles.some(r=>ctx.real?.puestos?.includes(r))||(!ctx.veModulo?.('produccion')&&!ctx.veModulo?.('mi-trabajo')))return null;
 const ps=arr(ctx.datos?.personas);
 if(![ctx.real,ctx.persona].every(p=>id(p?.id)&&activo(p)&&ps.filter(x=>x?.id===p.id).length===1&&activo(ps.find(x=>x.id===p.id))&&Array.isArray(p.puestos)&&new Set(p.puestos).size===p.puestos.length&&JSON.stringify([...p.puestos].sort())===JSON.stringify([...ps.find(x=>x.id===p.id).puestos].sort())))return null;
 if(ctx.real.id!==ctx.persona.id&&ctx.ver?.({tipo:'ver_como',persona_id:ctx.persona.id})?.ok!==true)return null;
 const visibles=arr(ctx.clientesVisibles),canon=arr(ctx.clientes),clientes=visibles.filter(c=>id(c?.id)&&visibles.filter(x=>x?.id===c.id).length===1&&canon.filter(x=>x?.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle!==false&&canon.some(x=>x.id===c.id&&x.activo_confirmado===true&&x.detalle!==false)&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true);
 if(!clientes.length)return null;
 return {clientes,ids:clientes.map(c=>c.id),firma:JSON.stringify([ctx.real,ctx.persona,ps,visibles,canon,clientes,ctx.hoy,['produccion','mi-trabajo'].map(m=>ctx.veModulo(m))])};
}catch{return null;}}
const fecha=x=>{if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/.test(x))return null;const d=new Date(x);return Number.isFinite(+d)&&d.toISOString().slice(0,19)===x.slice(0,19)?+d:null;};
export function proyectarUrgencias406(ctx,D,antes){
 const s=ambitoUrgencias406(ctx);if(!s||s.firma!==antes?.firma||D?.version!=='402.1'||D.grupo!=='abiertas'||D.urgencias_actuales!==null||D.verificacion_conjunta!==false||D.cumplimiento!==null||!Array.isArray(D.cliente_ids)||new Set(D.cliente_ids).size!==D.cliente_ids.length||D.cliente_ids.some(cid=>!s.ids.includes(cid))||!Array.isArray(D.filas)||D.filas.length>20000)return null;
 if(D.estado==='sin_dato')return D.filas.length===0&&D.abiertas_en_copia===null?{filas:[],disponible:false}:null;
 const corte=fecha(D.corte_preparacion_utc),consulta=fecha(D.generado);
 if(D.estado!=='copia_observada'||D.fuente_version!=='398.1'||D.fuente!=='clickup_cache_local'||D.cobertura!=='parcial'||!Number.isFinite(corte)||!Number.isFinite(consulta)||corte>consulta)return null;
 const seen=new Set();
 for(const r of D.filas){const leido=fecha(r?.estado_leido_utc);if(!id(r?.tarea_id)||seen.has(r.tarea_id)||!id(r.lista_id)||!D.cliente_ids.includes(r.cliente_id)||r.prioridad!=='urgent'||r.final_flujo_en_copia!==false||!['open','custom','unstarted'].includes(r.tipo_estado)||r.clasificacion!=='abierta_en_copia_por_contrastar'||typeof r.estado!=='string'||!r.estado||r.estado.length>180||/[\u0000-\u001f]/.test(r.estado)||!Number.isFinite(leido)||leido>corte||r.estado_fuente!=='clickup'||r.prioridad_fuente!=='clickup_cache_literal'||r.prioridad_leida_utc!==null||r.medicion_urgencia!==null||r.es_fuego_actual!==null||r.verificacion_conjunta!==false||r.ejecucion_verificada!==false||r.aceptacion_verificada!==false)return null;seen.add(r.tarea_id);}
 if(D.abiertas_en_copia!==(D.filas.length||null)||D.observaciones!==(D.filas.length||null))return null;
 const lecturas=D.filas.map(r=>r.estado_leido_utc).sort((a,b)=>fecha(a)-fecha(b));
 if(D.lectura_desde_utc!==(lecturas[0]??null)||D.lectura_hasta_utc!==(lecturas.at(-1)??null))return null;
 for(const r of D.filas){
  // 485 aditivo: sin sidecar o consumidor antiguo conserva ID; no deduce título.
  if(r.titulo!==undefined){
   if(r.titulo===null){if(r.titulo_estado!=='no_disponible'||r.titulo_fuente!==null||r.titulo_leido_utc!==null)return null;}
   else if(typeof r.titulo!=='string'||!r.titulo.trim()||r.titulo.length>240||/[\u0000-\u001f\u202a-\u202e\u2066-\u2069<>]|https?:\/\/|[\w.+-]+@[\w.-]+\.[a-z]{2,}/i.test(r.titulo)||r.titulo_estado!=='observado_saneado'||r.titulo_fuente!=='clickup_cache_local'||r.titulo_leido_utc!==r.estado_leido_utc)return null;
  }
 }
 return {disponible:true,filas:D.filas.map(r=>({tarea_id:r.tarea_id,cliente_id:r.cliente_id,estado:r.estado,estado_leido_utc:r.estado_leido_utc,titulo:r.titulo??null})),hasta:D.lectura_hasta_utc};
}
const corta=x=>fecha(x)!==null?new Intl.DateTimeFormat('es-ES',{timeZone:'Europe/Madrid',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(new Date(x)):'—';
// La API admite microsegundos; Date sólo conserva milisegundos. No fusionar
// cortes distintos aunque su fecha abreviada se vea igual en pantalla.
const selloLectura502=x=>x.replace(/(?:\.(\d{1,6}))?Z$/,(_,fraccion='')=>`.${fraccion.padEnd(6,'0')}Z`);
export async function renderUrgencias406(cont,ctx){
 const scope=ambitoUrgencias406(ctx),root=h('section',{class:'panel','data-urgencias-406':''});cont.append(root);
 const vivo=()=>root.isConnected&&ctx.vigente?.()!==false&&scope&&ambitoUrgencias406(ctx)?.firma===scope.firma;
 const guard=()=>{if(vivo())return true;root.replaceChildren();return false;};
 root.append(h('h2',{},'Fuegos · urgencias concretas'));
 if(!scope){root.append(h('p',{class:'sub'},'Sin acceso a la cola de urgencias.'));return root;}
 const estado=h('p',{role:'status',class:'sub'},'Consultando la copia local…');root.append(estado);
 let m;try{const D=await ctx.api('produccion/urgencias-observadas');if(!guard())return root;m=proyectarUrgencias406(ctx,D,scope);}catch{if(!guard())return root;}
 if(!m?.disponible){estado.replaceChildren('Falta una lectura válida de urgencias. No se afirma que no haya fuegos.');return root;}
 estado.replaceChildren(`Urgencias abiertas observadas: ${m.filas.length||'—'} · estado hasta ${corta(m.hasta)} · pendientes de contraste.`);
 const groups=new Map();for(const r of m.filas){if(!groups.has(r.cliente_id))groups.set(r.cliente_id,[]);groups.get(r.cliente_id).push(r);}
 const filtro=h('input',{type:'search','aria-label':'Buscar cliente con urgencias',placeholder:'Buscar cliente',style:{minHeight:'42px',borderRadius:'10px',padding:'8px 12px',border:'1px solid var(--line,#e1e4f1)'}});
 const body=h('tbody'),detalle=h('section',{'aria-label':'Urgencias del cliente',tabindex:-1,style:{scrollMarginTop:'90px'}});
 const mostrar=(cid)=>{
  if(!guard())return;const filas=groups.get(cid);if(!filas)return;
  const c=scope.clientes.find(c=>c.id===cid);
  const lecturaComun=filas.every(r=>selloLectura502(r.estado_leido_utc)===selloLectura502(filas[0].estado_leido_utc));
  const cabeceras=lecturaComun?['Tarea','Estado observado','Abrir']:['Tarea','Estado observado','Lectura','Abrir'];
  detalle.replaceChildren(h('h3',{},c.nombre),
   h('p',{class:'sub'},'Prioridad urgent y título de la copia; consulta ClickUp para contrastar si sigue pendiente.'),
   lecturaComun?h('p',{class:'sub',title:`Lectura del estado en ClickUp: ${filas[0].estado_leido_utc}`},`Estado leído ${corta(filas[0].estado_leido_utc)} · Madrid`):null,
   h('div',{style:{overflowX:'auto'}},h('table',{class:'densa','aria-label':`Urgencias observadas de ${c.nombre}`,style:{width:'100%'}},
    h('thead',{},h('tr',{},cabeceras.map(x=>h('th',{scope:'col'},x)))),
    h('tbody',{},filas.map(r=>h('tr',{},
     h('td',{},h('span',{},r.titulo||'Título no disponible'),h('small',{class:'sub',style:{display:'block'}},r.tarea_id)),
     h('td',{},r.estado),
     lecturaComun?null:h('td',{title:r.estado_leido_utc},corta(r.estado_leido_utc)),
     h('td',{},h('a',{href:`https://app.clickup.com/t/${r.tarea_id}`,target:'_blank',rel:'noopener',on:{click:e=>{if(!guard())e.preventDefault();}}},'ClickUp'))))))));
  detalle.focus?.({preventScroll:true});detalle.scrollIntoView?.({block:'start',behavior:'smooth'});
 };
 const pintar=()=>{if(!guard())return;detalle.replaceChildren();const q=filtro.value?.trim().toLocaleLowerCase('es')||'';body.replaceChildren(...[...groups].sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0])).filter(([cid])=>scope.clientes.find(c=>c.id===cid).nombre.toLocaleLowerCase('es').includes(q)).map(([cid,filas])=>h('tr',{},h('th',{scope:'row',style:{textAlign:'left',position:'static',textTransform:'none',font:'inherit',fontWeight:'600',letterSpacing:'normal',color:'var(--ink)'}},scope.clientes.find(c=>c.id===cid).nombre),h('td',{},filas.length),h('td',{},corta(filas.map(r=>r.estado_leido_utc).sort().at(-1))),h('td',{},h('button',{type:'button',class:'bt mini',on:{click:()=>mostrar(cid)}},'Ver urgencias')))));};
 filtro.addEventListener('input',pintar);
 root.append(h('div',{style:{padding:'12px 0'}},filtro),h('div',{style:{overflowX:'auto'}},h('table',{class:'densa',style:{width:'100%',fontVariantNumeric:'tabular-nums'}},h('thead',{},h('tr',{},['Cliente','Abiertas en copia','Estado leído','Detalle'].map(x=>h('th',{scope:'col',style:{textAlign:'left'}},x)))),body)),h('p',{class:'sub'},'Fuegos actuales: por confirmar. El semáforo rojo del cliente es independiente. Esta copia no acredita lectura conjunta de prioridad y estado; no es un inventario completo de urgencias actuales.'),detalle);
 pintar();return root;
}
