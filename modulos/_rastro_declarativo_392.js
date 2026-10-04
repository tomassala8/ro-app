import {h} from '../componentes.js';
const arr=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,120}$/.test(x),pid=x=>typeof x==='string'&&/^[A-Za-z0-9_:.-]{1,180}$/.test(x),hash=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const estados={empujado:'Pedido',resuelto:'Comprobado por mí',coti:'Escalado',na:'No aplica',anulado:'Marca anulada'};
const activo=p=>p?.estado==='activo'&&p.activo!==false,roles=x=>Array.isArray(x)&&x.length>0&&x.every(id)&&new Set(x).size===x.length;
function day(x){return typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;}
function stamp(x){if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(x)||!day(x.slice(0,10)))return null;const m=/T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|([+-])(\d{2}):(\d{2}))$/.exec(x);if(+m[1]>23||+m[2]>59||+m[3]>59||(m[4]!=='Z'&&(+m[6]>14||+m[7]>59||(+m[6]===14&&+m[7]!==0))))return null;const n=Date.parse(x);return Number.isFinite(n)?n:null;}
const madrid=n=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(n));
const hora=n=>new Intl.DateTimeFormat('es-ES',{timeZone:'Europe/Madrid',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(n));
export function ambitoRastro392(ctx){try{
 if(ctx.servidor!==true||ctx.vigente?.()===false||!day(ctx.hoy)||!ctx.veModulo?.('mi-dia')||!ctx.veModulo?.('alertas')||typeof ctx.ver!=='function')return null;
 const ps=arr(ctx.datos?.personas),actors=[ctx.real,ctx.persona];
 if(!actors.every(p=>id(p?.id)&&activo(p)&&roles(p.puestos)&&p.puestos.some(r=>['direccion','operaciones'].includes(r))&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&activo(x)&&roles(x.puestos)&&JSON.stringify([...x.puestos].sort())===JSON.stringify([...p.puestos].sort()))))return null;
 if(ctx.real.id!==ctx.persona.id&&ctx.ver({tipo:'ver_como',persona_id:ctx.persona.id})?.ok!==true)return null;
 const visible=arr(ctx.clientesVisibles),canon=arr(ctx.clientes),clientes=visible.filter(c=>id(c?.id)&&visible.filter(x=>x?.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle!==false&&canon.filter(x=>x?.id===c.id).length===1&&canon.some(x=>x.id===c.id&&x.activo_confirmado===true&&x.detalle!==false)&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true);
 return {clientes,ids:clientes.map(c=>c.id),actor:ctx.persona.id,firma:JSON.stringify([actors,ps,ctx.hoy,visible,canon,clientes.map(c=>[c.id,ctx.ver({tipo:'cliente_detalle',cliente_id:c.id}).ok]),ctx.veModulo('mi-dia'),ctx.veModulo('alertas')])};
}catch{return null;}}
export function proyectarRastro392(ctx,D,antes){try{
 const s=ambitoRastro392(ctx);if(!s||!antes||s.firma!==antes.firma||D?.version!=='300.1'||D.propietario!==s.actor||D.dia!==ctx.hoy||typeof D.puede_registrar!=='boolean'||!Array.isArray(D.prioridades)||D.prioridades.length>1000)return null;
 const refs=new Set(),seen=new Map(),uuids=new Map();let limitado=false;
 for(const r of D.prioridades){
  if(!r||!pid(r.prioridad_id)||refs.has(r.prioridad_id)||!hash(r.fuente_revision)||(r.cliente_id!==null&&!s.ids.includes(r.cliente_id))||!Number.isSafeInteger(r.revision)||r.revision<0||typeof r.historial_truncado!=='boolean'||!Array.isArray(r.historial)||r.historial.length>20||!(r.actual===null||typeof r.actual==='object'))return null;
  refs.add(r.prioridad_id);limitado ||= r.historial_truncado;
  if((r.actual===null&&r.revision!==0)||(r.actual!==null&&(r.actual.revision!==r.revision||r.actual.dia!==D.dia)))return null;
  const add=(e,actual)=>{
   if(!e||e.actor!==s.actor||e.prioridad_id!==r.prioridad_id||e.fuente_revision!==r.fuente_revision||!day(e.dia)||e.dia>D.dia||!Number.isSafeInteger(e.revision)||e.revision<1||typeof e.intencion_id!=='string'||!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(e.intencion_id)||!Object.keys(estados).includes(e.estado)||typeof e.nota!=='string'||e.nota.length>300||/[\u0000-\u0008]/.test(e.nota)||e.origen!=='local'||e.declarado!==true||e.envio_realizado!==false||e.ejecucion_verificada!==false)return false;
   const t=stamp(e.registrado_en);if(t===null||madrid(t)>ctx.hoy)return false;
   const key=JSON.stringify([e.actor,e.prioridad_id,e.fuente_revision,e.dia,e.revision]),copy={key,intencion_id:e.intencion_id,actor:e.actor,prioridad_id:e.prioridad_id,fuente_revision:e.fuente_revision,dia_declarado:e.dia,revision:e.revision,estado:e.estado,nota:e.nota,registrado_en:e.registrado_en,cliente_id:r.cliente_id,tiempo:t,dia:madrid(t)},encoded=JSON.stringify(copy);
   if(uuids.has(e.intencion_id)&&uuids.get(e.intencion_id)!==key)return false;
   if(seen.has(key)){if(seen.get(key).encoded!==encoded)return false;seen.get(key).fila.actual ||= actual;}
   else{seen.set(key,{encoded,fila:{...copy,actual}});uuids.set(e.intencion_id,key);}return true;
  };
  for(const e of r.historial)if(!add(e,false))return null;
  if(r.actual!==null&&!add(r.actual,true))return null;
 }
 return {firma:s.firma,filas:[...seen.values()].map(x=>x.fila).sort((a,b)=>b.tiempo-a.tiempo||a.key.localeCompare(b.key)),limitado,referencias:refs.size,actor:s.actor};
}catch{return null;}}
export function resumenRastro403(model,hoy){
 if(!model||!Array.isArray(model.filas)||!day(hoy))return null;
 const clientes=new Map(),marcas=new Set();let hoyLeidas=0;
 for(const r of model.filas){
  if(r.dia===hoy)hoyLeidas++;
  if(r.actual)marcas.add(r.prioridad_id);
  if(r.cliente_id!==null){
   if(!clientes.has(r.cliente_id))clientes.set(r.cliente_id,{cliente_id:r.cliente_id,revisiones:0,estados:{}});
   const c=clientes.get(r.cliente_id);c.revisiones++;c.estados[r.estado]=(c.estados[r.estado]||0)+1;
  }
 }
 return {leidas:model.filas.length,hoy:hoyLeidas,con_marca:marcas.size,clientes:[...clientes.values()]};
}
export async function renderRastroDeclarativo392(cont,ctx,{vigente=()=>true}={}){
 const scope=ambitoRastro392(ctx),root=h('section',{class:'panel','data-rastro-declarativo-392':''});cont.append(root);
 const status=h('p',{class:'sub',role:'status'},scope?'Consultando declaraciones locales…':'Declaraciones de prioridades no disponibles con estos permisos.');root.append(h('h2',{},'Declaraciones sobre prioridades vigentes'),status);
 const vivo=()=>root.isConnected&&vigente()&&scope!==null&&ambitoRastro392(ctx)?.firma===scope.firma;
 const guard=()=>{if(vivo())return true;root.replaceChildren();return false;};
 if(!scope)return root;
 let model;try{const D=await ctx.api('operaciones/prioridades');if(!guard())return root;model=proyectarRastro392(ctx,D,scope);}catch{if(!guard())return root;}
 if(!model){if(guard())status.replaceChildren('Fuente declarativa no disponible. No acredita ausencia de acciones.');return root;}
 status.replaceChildren(`${model.referencias} prioridades vigentes · fechas Madrid · declaración, no ejecución`);
 const resumen=resumenRastro403(model,ctx.hoy);
 const alcance='Solo referencias actuales y mismo hash de fuente; hasta 20 revisiones por prioridad. Conteos de declaraciones observadas, no ejecución ni historial completo.';
 root.append(h('div',{'data-resumen-rastro-403':'',style:{display:'flex',flexWrap:'wrap',gap:'8px 24px',padding:'8px 0'},title:alcance},...[["Revisiones leídas",resumen.leidas],["Hoy · Madrid",resumen.hoy],["Prioridades con marca",resumen.con_marca]].map(([titulo,n])=>h('div',{},h('span',{class:'sub'},titulo),h('strong',{style:{marginLeft:'8px',color:'#555b73'}},String(n))))));
 const leyenda=h('details',{on:{toggle:guard}},h('summary',{},model.limitado?'Historia limitada · fuente y alcance':'Fuente y alcance'),h('p',{},'Solo referencias actuales y mismo hash de fuente; hasta 20 revisiones por prioridad. Prioridades con marca cuenta la última marca de hoy, incluidas las anuladas; Hoy cuenta el día del registro en Madrid. Historial conserva revisiones anteriores. Los tres conteos incluyen registros de equipo sin cliente; Por cliente sólo cuenta los vinculados a cliente. No es historia completa de alarmas ni envío o resolución en el proveedor.'));
 root.append(leyenda);if(!model.filas.length){root.append(h('p',{},'Sin declaraciones leídas para estas referencias. No acredita que las acciones estén resueltas.'));return root;}
 const groups=new Map();for(const r of model.filas){if(!groups.has(r.dia))groups.set(r.dia,[]);groups.get(r.dia).push(r);}
 const nombre=()=>arr(ctx.datos?.personas).find(p=>p.id===model.actor)?.nombre||model.actor;
 for(const [dia,filas] of groups){let detalle;
  detalle=h('details',{on:{toggle:()=>{
   if(!guard())return;detalle.replaceChildren(h('summary',{style:{minHeight:'44px',padding:'8px 12px'}},`${dia} · ${filas.length} revisiones`));if(!detalle.open)return;
   const body=h('tbody',{},...filas.map(r=>h('tr',{},h('td',{title:`Fuente UTC: ${r.registrado_en}; revisión ${r.revision}; ${r.actual?'marca actual de hoy':'revisión anterior'}; día declarado ${r.dia_declarado}`,style:{whiteSpace:'nowrap'}},hora(r.tiempo)),h('td',{},r.cliente_id?scope.clientes.find(c=>c.id===r.cliente_id)?.nombre||r.cliente_id:'Equipo · sin cliente'),h('td',{},estados[r.estado]),h('td',{style:{maxWidth:'400px',overflowWrap:'anywhere'}},r.nota||'Sin nota registrada'),h('td',{},nombre()))));
   detalle.replaceChildren(h('summary',{style:{minHeight:'44px',padding:'8px 12px'}},`${dia} · ${filas.length} revisiones`),h('div',{class:'scroll'},h('table',{class:'t',style:{width:'100%'}},h('thead',{},h('tr',{},...['Hora','Cliente','Estado declarado','Nota','Autor'].map(x=>h('th',{scope:'col'},x)))),body)));
  }}},h('summary',{style:{minHeight:'44px',padding:'8px 12px'}},`${dia} · ${filas.length} revisiones`));root.append(detalle);
 }
 const porCliente=h('details',{'data-clientes-rastro-403':'',on:{toggle:()=>{
  if(!guard())return;
  const summary=h('summary',{style:{minHeight:'44px',padding:'8px 12px'}},'Por cliente · declaraciones leídas');
  porCliente.replaceChildren(summary);if(!porCliente.open)return;
  const filas=[...resumen.clientes].sort((a,b)=>String(scope.clientes.find(c=>c.id===a.cliente_id)?.nombre||a.cliente_id).localeCompare(String(scope.clientes.find(c=>c.id===b.cliente_id)?.nombre||b.cliente_id),'es'));
  const cuerpo=h('tbody',{},...filas.map(r=>h('tr',{},
   h('td',{},scope.clientes.find(c=>c.id===r.cliente_id)?.nombre||r.cliente_id),
   h('td',{},String(r.revisiones)),
   h('td',{title:'Revisiones leídas por estado; no estado actual del cliente ni ejecuciones verificadas.'},Object.entries(estados).filter(([key])=>r.estados[key]).map(([key,label])=>`${label}: ${r.estados[key]}`).join(' · '))
  )));
  const cabecera=h('thead',{},h('tr',{},...['Cliente','Revisiones','Estados declarados'].map(x=>h('th',{scope:'col'},x))));
  porCliente.append(h('div',{class:'scroll'},h('table',{class:'t',style:{width:'100%'}},cabecera,cuerpo)));
  if(!filas.length)porCliente.append(h('p',{class:'sub'},'Las declaraciones leídas son de equipo, sin cliente.'));
 }}},h('summary',{style:{minHeight:'44px',padding:'8px 12px'}},'Por cliente · declaraciones leídas'));
 root.append(porCliente);
 return root;
}
