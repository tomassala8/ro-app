// Objetivos aspiracionales y observaciones locales: sin inferir ciudades ni servicios.
const arr=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,120}$/.test(x);
const roles=x=>Array.isArray(x)&&x.length>0&&x.every(id)&&new Set(x).size===x.length;
const txt=x=>typeof x==='string'&&x.trim().length<=240&&!/[\x00-\x1f]|https?:\/\/|@|[€$]|\b(?:password|contrase[ñn]a|token|secret|api[_-]?key)\b/i.test(x)?x.trim():null;
const dia=x=>{if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x))return null;const d=new Date(x+'T00:00:00Z');return Number.isFinite(+d)&&d.toISOString().slice(0,10)===x?x:null;};
const pos=x=>typeof x==='number'&&Number.isSafeInteger(x)&&x>=1?x:null;
export function ambitoObjetivos374(ctx){try{
 if(ctx.servidor!==true||ctx.vigente?.()===false||ctx.veModulo?.('seo-web')!==true||ctx.veModulo?.('prioridades-cliente')!==true||!dia(ctx.hoy))return null;
 const ps=arr(ctx.datos?.personas),as=[ctx.real,ctx.persona];
 if(!as.every(p=>id(p?.id)&&p.estado==='activo'&&p.activo!==false&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&x.estado==='activo'&&x.activo!==false&&roles(p.puestos)&&roles(x.puestos)&&JSON.stringify([...p.puestos].sort())===JSON.stringify([...x.puestos].sort()))))return null;
 const cs=arr(ctx.clientesVisibles),catalogo=arr(ctx.clientes);
 const activo=c=>c?.activo_confirmado===true&&c.detalle===true&&c.activo!==false&&c.estado!=='baja';
 const allowed=cs.filter(c=>id(c?.id)&&cs.filter(x=>x?.id===c.id).length===1&&activo(c)&&catalogo.filter(x=>x?.id===c.id).length===1&&catalogo.some(x=>x?.id===c.id&&activo(x))&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true);
 return {ids:allowed.map(c=>c.id).sort(),firma:JSON.stringify([as,ps,catalogo,allowed,arr(ctx.datos?.asignaciones),ctx.hoy])};
 }catch{return null;}}
export async function cargarObjetivos374(ctx){
 const a=ambitoObjetivos374(ctx);if(!a||typeof ctx.api!=='function')return {estado:'no_disponible',firma:null,datos:null};
 try{const datos=await ctx.api('cerebro/seo');if(ambitoObjetivos374(ctx)?.firma!==a.firma)return {estado:'revocado',firma:null,datos:null};
 if(!datos||!dia(datos.fecha)||datos.fecha>ctx.hoy||!Array.isArray(datos.clientes))return {estado:'no_disponible',firma:a.firma,datos:null};
 return {estado:'leido',firma:a.firma,datos};
 }catch{return {estado:ambitoObjetivos374(ctx)?.firma===a.firma?'no_disponible':'revocado',firma:a.firma,datos:null};}
}
export function modeloObjetivos374(ctx,carga,cid=null){
 const a=ambitoObjetivos374(ctx);if(!a||a.firma!==carga?.firma||carga.estado!=='leido'||!dia(carga.datos?.fecha)||carga.datos.fecha>ctx.hoy)return [];
 const clients=arr(carga.datos.clientes),names=arr(ctx.clientesVisibles),rows=[];
 for(const c of clients){
  if(!id(c?.cliente_id)||!a.ids.includes(c.cliente_id)||(cid&&cid!==c.cliente_id)||clients.filter(x=>x?.cliente_id===c.cliente_id).length!==1)continue;
  const cli=names.find(x=>x.id===c.cliente_id),nombre=txt(cli.nombre)||c.cliente_id,objectives=c.habilitado===true?arr(c.objetivos):[],grupos=new Map();
  for(const o of objectives){
   const consulta=txt(o?.consulta),ciudad=txt(o?.ciudad);if(!consulta||!ciudad||!['organico','maps'].includes(o.canal))continue;
   const motor=o.medicion_id==null?null:id(o.medicion_id)?o.medicion_id:null;
   if(o.medicion_id!=null&&motor===null)continue;
   const device=['desktop','movil'].includes(o.dispositivo)?o.dispositivo:null,ubicacion=txt(o.ubicacion_medicion);
   const medida=o.consulta_medida==null?consulta:txt(o.consulta_medida),fuente=o.fuente==null?null:txt(o.fuente);
   if(!medida||(o.fuente!=null&&!fuente))continue;
   // El motor conserva variantes acentuadas y fuentes distintas; no fusionarlas.
   const key=JSON.stringify([consulta,medida.toLocaleLowerCase('es').replace(/\s+/g,' '),ciudad,motor,device,ubicacion,fuente]);
   if(!grupos.has(key))grupos.set(key,{cliente_id:c.cliente_id,nombre,ciudad,ciudad_id:null,consulta:medida,consulta_objetivo:consulta,servicio:txt(o.servicio)||'Servicio documentado; detalle pendiente',motor,device,ubicacion,organico:[],maps:[],historico:false});
   grupos.get(key)[o.canal].push(o);
  }
  const value=xs=>{if(xs.length!==1)return {valor:null,fecha:null,acreditada:false,nota:xs.length>1?'Lecturas ambiguas':'Sin medición'};const x=xs[0],f=dia(x.fecha);return {valor:f&&f<=ctx.hoy?pos(x.posicion):null,fecha:f&&f<=ctx.hoy?f:null,acreditada:!!f&&f<=ctx.hoy&&pos(x.posicion)!==null&&x.objetivo_local_acreditado===true&&!!contextoCompleto374(x),nota:'Posición observada; no cumplimiento acreditado'};};
  for(const g of grupos.values())rows.push({...g,organico:value(g.organico),maps:value(g.maps),contexto:g.device&&g.ubicacion?`${g.device} · ${g.ubicacion}`:'Ubicación/dispositivo por verificar',objetivo:'#1 aspiracional'});
  if(!grupos.size){
   const hs=arr(c.objetivos_historicos).filter(x=>x?.activar_consultas===false&&x.benchmark_confirmado===false&&dia(x.fecha_documento)&&x.fecha_documento<=ctx.hoy&&txt(x.valor));
   const cities=hs.filter(x=>x.tipo==='Ciudad documentada'),services=hs.filter(x=>['Servicio prioritario','Servicio documentado','Servicio del brief','Prioridad comercial','Servicios documentados'].includes(x.tipo));
   rows.push({cliente_id:c.cliente_id,nombre,ciudad:cities.length?cities.map(x=>txt(x.valor)).join(' · '):'Ciudad pendiente',ciudad_id:null,consulta:'Consultas actuales pendientes',servicio:services.length?services.map(x=>txt(x.valor)).join(' · '):'Servicios por verificar',motor:null,device:null,ubicacion:null,organico:{valor:null},maps:{valor:null},contexto:'Sin consultas actuales acreditadas',objetivo:'#1 aspiracional',historico:hs.length>0,referencias:hs.map(x=>({tipo:txt(x.tipo),valor:txt(x.valor),fecha:x.fecha_documento,razones:arr(x.razones).map(txt).filter(Boolean)}))});
  }
 }
 return rows;
}
const contextoCompleto374=x=>['desktop','movil'].includes(x.dispositivo)&&txt(x.ubicacion_medicion);
export function celdaObjetivo374(h,ctx,carga,cid){
 const rows=modeloObjetivos374(ctx,carga,cid),ref=rows.find(x=>!x.historico&&x.ciudad!=='Ciudad pendiente'),link=h('a',{href:`#/prioridades-cliente?cliente=${encodeURIComponent(cid)}`,class:'sub enlace',on:{click:e=>{if(!ambitoObjetivos374(ctx)?.ids.includes(cid)||ambitoObjetivos374(ctx)?.firma!==carga?.firma)e.preventDefault();}}},ref?`#1 · ${ref.ciudad}`:rows.some(x=>x.historico)?'Objetivo · referencia histórica':'Objetivo por confirmar');
 return link;
}
export function renderObjetivos374(h,ctx,carga,cid=null){
 const root=h('section',{'data-objetivos-seo-374':'',class:'panel',style:{minWidth:'0'}}),firma=ambitoObjetivos374(ctx)?.firma;
 const vivo=()=>root.isConnected&&firma&&firma===ambitoObjetivos374(ctx)?.firma&&firma===carga?.firma;
 const clear=()=>root.replaceChildren(h('p',{class:'sub',role:'status'},'Objetivos no disponibles con el contexto actual.'));
 const rows=modeloObjetivos374(ctx,carga,cid);
 if(!rows.length){root.append(h('p',{class:'sub'},carga?.estado==='leido'?'Sin objetivos locales en la fuente autorizada.':'Objetivos locales: fuente no disponible.'));return root;}
 root.append(h('header',{style:{padding:'8px 12px'}},h('b',{},'Objetivos locales · #1 aspiracional')));
 const table=h('table',{class:'densa',style:{width:'100%',minWidth:'950px',fontSize:'13px'}}),body=h('tbody',{});
 table.append(h('thead',{},h('tr',{},['Cliente','Ciudad / servicio','Consulta','Orgánico','Maps','Fecha / contexto','Revisar'].map(t=>h('th',{scope:'col'},t)))),body);
 const metric=x=>x.valor===null||x.valor===undefined?'Sin dato':String(x.valor);
 for(const r of rows){
  const fechas=[r.organico.fecha?`Org ${r.organico.fecha}`:null,r.maps.fecha?`Maps ${r.maps.fecha}`:null].filter(Boolean).join(' · ');
  const detalle=h('details',{},h('summary',{style:{minHeight:'44px',cursor:'pointer'},title:r.contexto},fechas|| (r.historico?'Referencia histórica':'Fecha pendiente · fuente')),h('p',{class:'sub'},r.contexto),h('p',{class:'sub'},r.historico?'Documento anterior: no activa ciudades, servicios ni consultas actuales.':'Objetivo #1 como aspiración. Puestos observados; no acreditan cumplimiento local sin contexto temporal del motor.'),h('p',{class:'sub'},'Ciudad documentada; ID canónico no disponible. No se infiere de la consulta ni de la dirección.'),arr(r.referencias).map(x=>h('p',{class:'sub'},`${x.tipo}: ${x.valor} · ${x.fecha}. ${x.razones.join(' · ')}`)));
  detalle.addEventListener('toggle',()=>{if(!vivo())clear();});
  const link=h('a',{href:`#/seo-web/${encodeURIComponent(r.cliente_id)}/clics`,class:'bt mini',on:{click:e=>{if(!vivo()){e.preventDefault();clear();}}}},'Páginas');
  const target=h('a',{href:`#/prioridades-cliente?cliente=${encodeURIComponent(r.cliente_id)}`,class:'sub enlace',on:{click:e=>{if(!vivo()){e.preventDefault();clear();}}}},'Objetivo');
  body.append(h('tr',{},h('td',{},r.nombre),h('td',{},r.ciudad,r.historico?h('small',{},' · histórico'):null,h('small',{style:{display:'block'}},r.servicio)),h('td',{},r.consulta),h('td',{},metric(r.organico)),h('td',{},metric(r.maps)),h('td',{},detalle),h('td',{},link,target)));
 }
 root.append(h('div',{class:'tabla-scroll'},table));return root;
}
