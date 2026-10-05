import {h} from '../componentes.js';
import {prepararControlCartera} from './control_cartera.js';
const SHA405='f0503e6e5edeaff1fabffb602e5a2bb80ed3e2c432c2bf9fad03ec25c0f8a292',ESTADOS405=['backlog','planning mensual','planning semanal','diario','en curso'];
const SHA='be7ff0dcc533d283d7fb2f02cc556b0fc0d9e39f080e5eb1b95ddde02818a7a4',arr=x=>Array.isArray(x)?x:[];
const id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,150}$/.test(x),active=p=>p?.estado==='activo'&&p.activo!==false;
const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
const roles=(a,b)=>Array.isArray(a)&&Array.isArray(b)&&a.length>0&&a.every(id)&&b.every(id)&&new Set(a).size===a.length&&new Set(b).size===b.length&&JSON.stringify([...a].sort())===JSON.stringify([...b].sort());
function timestamp(x){if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(x)||!day(x.slice(0,10)))return null;const m=/T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|([+-])(\d{2}):(\d{2}))$/.exec(x);if(!m||+m[1]>23||+m[2]>59||+m[3]>59||(m[4]!=='Z'&&(+m[6]>14||+m[7]>59||(+m[6]===14&&+m[7]!==0))))return null;const n=Date.parse(x);return Number.isFinite(n)?n:null;}
const Madrid=n=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(n));
const lectura360=x=>timestamp(x)===null?'Sin dato':new Intl.DateTimeFormat('es-ES',{timeZone:'Europe/Madrid',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(x))+' (Madrid)';
const horas=ms=>ms<360000?'<0,1 h':`${new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(ms/3600000)} h`;
export function ambitoPlanning360(ctx){try{
 if(ctx.servidor!==true||ctx.vigente?.()===false||!day(ctx.hoy)||!ctx.veModulo?.('produccion')||!ctx.veModulo?.('bandeja')||typeof ctx.ver!=='function')return null;
 const ps=arr(ctx.datos?.personas),actors=[ctx.real,ctx.persona];
 if(!actors.every(p=>id(p?.id)&&active(p)&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&active(x)&&roles(x.puestos,p.puestos))&&p.puestos.some(x=>['direccion','operaciones','account'].includes(x))))return null;
 if(ctx.real.id!==ctx.persona.id&&ctx.ver({tipo:'ver_como',persona_id:ctx.persona.id})?.ok!==true)return null;
 const canon=arr(ctx.clientes),cs=arr(ctx.clientesVisibles),own=ctx.persona.puestos.includes('account')&&!ctx.persona.puestos.some(x=>['direccion','operaciones'].includes(x)),cartera=new Set(ctx.carteraPorSilla?.account||[]);
 const clientes=cs.filter(c=>id(c?.id)&&cs.filter(x=>x?.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle===true&&canon.filter(x=>x?.id===c.id).length===1&&canon.some(x=>x.id===c.id&&x.activo_confirmado===true&&x.detalle===true)&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true&&(!own||(cartera.has(c.id)))).map(c=>({...c,equipo:canon.find(x=>x.id===c.id)?.equipo})),ids=clientes.map(c=>c.id).sort();
 return {ids,clientes,asignaciones:arr(ctx.datos?.asignaciones),personas:ps.filter(p=>id(p?.id)&&ps.filter(x=>x?.id===p.id).length===1&&active(p)),firma:JSON.stringify([actors,ctx.hoy,ids,ps,canon,arr(ctx.datos?.asignaciones),clientes,[...cartera].sort()])};
 }catch{return null;}}
export function proyectarPlanning360(ctx,d,antes){try{
 const s=ambitoPlanning360(ctx),gen=timestamp(d?.generado);
 if(!s||!antes||s.firma!==antes.firma||!d||!['356.1','405.1'].includes(d.version)||gen===null||Madrid(gen)>ctx.hoy||!Array.isArray(d.filas)||!Array.isArray(d.cliente_ids)||!d.cliente_ids.every(id)||new Set(d.cliente_ids).size!==d.cliente_ids.length||!d.cliente_ids.every(cid=>s.ids.includes(cid))||d.disciplina!==null||d.cumplimiento!==null)return null;
 const ampliado=d.version==='405.1',states=ampliado?ESTADOS405:['backlog','planning mensual'];
 if(ampliado&&(d.fuente_version!=='395.1'||d.sha256_candidato!==SHA405||!Array.isArray(d.estados_incluidos)||JSON.stringify([...d.estados_incluidos].sort())!==JSON.stringify([...ESTADOS405].sort())||timestamp(d.corte_preparacion_utc)===null||timestamp(d.corte_preparacion_utc)>gen))return null;
 const known=d.estado==='copia_observada'&&d.fuente_version===(ampliado?'395.1':'355.1')&&d.sha256_candidato===(ampliado?SHA405:SHA)&&d.fuente==='clickup_cache_local'&&d.cobertura==='parcial',unknown=d.estado==='sin_dato'&&d.fuente_version===null&&d.sha256_candidato===null&&d.fuente===null&&d.cobertura==='desconocida';
 if(!known&&!unknown)return null;
 const rows=[],seen=new Set();
 for(const r of d.filas){
  if(!known||!r||!['tarea_id','cliente_id','lista_id'].every(k=>id(r[k]))||seen.has(r.tarea_id)||!d.cliente_ids.includes(r.cliente_id)||!states.includes(r.estado)||!['open','custom','unstarted'].includes(r.tipo_estado)||r.estado_fuente!=='clickup'||r.cobertura!=='parcial'||['actor_historico','estado_inicial','rompe_semanal','fuego_confirmado'].some(k=>r[k]!==null))return null;
  const read=timestamp(r.estado_leido_utc);if(read===null||read>gen||(ampliado&&read>timestamp(d.corte_preparacion_utc)))return null;
  if(!Array.isArray(r.asignados_persona_ids)||!r.asignados_persona_ids.every(id)||new Set(r.asignados_persona_ids).size!==r.asignados_persona_ids.length||!Number.isSafeInteger(r.asignados_sin_identidad_confirmada)||r.asignados_sin_identidad_confirmada<0||!['observada','parcial'].includes(r.asignacion_estado)||(r.asignacion_estado==='observada'&&r.asignados_sin_identidad_confirmada!==0))return null;
  const dates={};for(const key of ['inicio','vence']){const v=r[key+'_utc'],state=r[key+'_estado'];if(state==='observada'){if(timestamp(v)===null)return null;dates[key]=Madrid(timestamp(v));}else if(['sin_dato','invalida'].includes(state)&&v===null)dates[key]=null;else return null;}
  const e=r.estimacion,v=e?.valor,isnum=typeof v==='number'&&Number.isFinite(v)&&v>0;if(e?.unidad!=='milisegundos'||(isnum?e.estado!=='observada':v!==null||e.estado!=='sin_dato'))return null;
  seen.add(r.tarea_id);const pids=r.asignados_persona_ids.filter(pid=>s.personas.some(p=>p.id===pid));rows.push({tarea_id:r.tarea_id,cliente_id:r.cliente_id,lista_id:r.lista_id,estado:r.estado,tipo_estado:r.tipo_estado,lectura:r.estado_leido_utc,pids,pendientes:r.asignados_sin_identidad_confirmada+r.asignados_persona_ids.length-pids.length,...dates,estimacion_ms:v});
 }
 if(d.observaciones!==(rows.length||null))return null;
 const readings=rows.map(r=>timestamp(r.lectura)).sort((a,b)=>a-b);
 if(rows.length?(timestamp(d.lectura_desde_utc)!==readings[0]||timestamp(d.lectura_hasta_utc)!==readings.at(-1)):d.lectura_desde_utc!==null||d.lectura_hasta_utc!==null)return null;
 return {firma:s.firma,filas:rows,cliente_ids:[...d.cliente_ids],estado:d.estado,generado:d.generado,desde:d.lectura_desde_utc,hasta:d.lectura_hasta_utc,estados:states,ampliado};
 }catch{return null;}}
export function accountPlanning405(scope,cid,hoy){
 const cliente=scope.clientes.find(c=>c.id===cid);if(!cliente)return null;
 const rows=prepararControlCartera({clientes:[cliente],personas:scope.personas,asignaciones:scope.asignaciones,hoy,fuentes:{},esOps:true});
 const r=rows.length===1?rows[0]:null,p=scope.personas.find(p=>p.id===r?.account_id);
 return r?.account_id&&p&&roles(p.puestos,p.puestos)&&p.puestos.includes('account')?{id:r.account_id,confirmada:r.owner_confirmado===true}:null;
}
export async function panelPlanningObservado360(cont,ctx){
 const initial=ambitoPlanning360(ctx);if(!initial)return false;
 const root=h('section',{class:'oe-panel','data-planning-observado':'360'});cont.append(root);
 const compact=h('style',{},'[data-planning-observado="360"] th,[data-planning-observado="360"] td{padding:6px 10px;line-height:1.35}[data-planning-observado="360"] td button{min-height:32px;padding:4px 10px}[data-planning-observado="360"] .oe-scroll{max-width:100%;overflow-x:auto}[data-planning-observado="360"] .oe-scroll table{width:100%}[data-planning-observado="360"] th:first-child,[data-planning-observado="360"] td:first-child{position:sticky;left:0;background:var(--panel,#fff);z-index:1}');
 const current=()=>{const ok=root.isConnected&&ctx.vigente?.()!==false&&ambitoPlanning360(ctx)?.firma===initial.firma;if(!ok)root.replaceChildren();return ok;};
 root.append(h('header',{},h('h2',{},'Inventario de planificación · copia observada')),h('p',{class:'oe-note',role:'status'},'Leyendo inventario autorizado…'));
 let model;try{if(typeof ctx.api!=='function')throw Error();const d=await ctx.api('produccion/planning-observado');if(!current())return false;model=proyectarPlanning360(ctx,d,initial);}catch{if(!current())return false;}
 if(!current())return false;
 if(!model){root.replaceChildren(h('header',{},h('h2',{},'Inventario de planificación · copia observada')),h('p',{class:'oe-note',role:'status'},'Inventario no disponible en esta sesión. No acredita ausencia de tareas.'));return false;}
 let cid='',pid='',projectOpen=false;const result=h('div');
 const dato=(texto,detalle)=>h('td',{title:detalle,'aria-label':`${texto}. ${detalle}`},texto);
 const cabecera443=x=>h('th',{scope:'col',title:x,'aria-label':x},({'Planning mensual':'Plan. mes','Planning semanal':'Plan. sem.'})[x]||x);
 const cuenta=(rows,state)=>{const n=rows.filter(r=>r.estado===state).length;return dato(n?'≥'+n:'—',n?`${state}: mínimo de ${n} tareas observadas; copia parcial.`:`${state}: sin observaciones acreditadas; no equivale a cero.`);};
 const selectClient=h('select',{'aria-label':'Cliente del inventario observado'},h('option',{value:''},'Todos los clientes autorizados'),model.cliente_ids.map(cid=>h('option',{value:cid},initial.clientes.find(c=>c.id===cid)?.nombre||cid)));
 const assigned=[...new Set(model.filas.flatMap(r=>r.pids))].sort();
 const selectPerson=h('select',{'aria-label':'Asignado del inventario observado'},h('option',{value:''},'Todos los asignados observados'),h('option',{value:'__unknown'},'Asignación por confirmar'),assigned.map(pid=>h('option',{value:pid},initial.personas.find(p=>p.id===pid)?.nombre||pid)));
 const headers=['Cliente',...(model.ampliado?['Backlog','Planning mensual','Planning semanal','Diario','En curso']:['Backlog','Planning mensual']),'Estimación observada','Detalle'];
 const paint=()=>{
  if(!current())return;result.replaceChildren();
  const rows=model.filas.filter(r=>(!cid||r.cliente_id===cid)&&(!pid||(pid==='__unknown'?r.pids.length===0||r.pendientes>0:r.pids.includes(pid))));
  const groups=[...new Set(rows.map(r=>r.cliente_id))].sort(),labels=cid=>initial.clientes.find(c=>c.id===cid)?.nombre||cid;
  const tbody=h('tbody'),details=h('div');
  for(const group of groups){const rs=rows.filter(r=>r.cliente_id===group),est=rs.filter(r=>r.estimacion_ms!==null),sum=est.reduce((s,r)=>s+r.estimacion_ms,0),estimate=est.length&&Number.isFinite(sum)?horas(sum):'—';
   let loaded=false,d;
   const fill=()=>{if(!current()||loaded||!d.open)return;loaded=true;
   const body=h('tbody',{},rs.map(r=>h('tr',{},h('td',{},h('a',{href:`#/produccion/tarea/${encodeURIComponent(r.tarea_id)}`,on:{click:e=>{if(!current())e.preventDefault();}}},r.tarea_id)),h('td',{},r.estado),h('td',{},r.pids.map(id=>initial.personas.find(p=>p.id===id)?.nombre||id).join(', ')+(r.pendientes?' · asignación por confirmar':'')||'Sin asignación observada'),dato(r.inicio||'—',r.inicio?'Fecha programada observada.':'Inicio sin dato acreditado.'),dato(r.vence||'—',r.vence?'Fecha programada observada.':'Vencimiento sin dato acreditado.'),dato(r.estimacion_ms===null?'—':horas(r.estimacion_ms),r.estimacion_ms===null?'Estimación sin dato acreditado.':'Estimación observada; no horas ejecutadas ni capacidad.'),h('td',{title:r.lectura},lectura360(r.lectura)))));
   d.append(h('div',{class:'oe-scroll',tabindex:0,'aria-label':`Tareas observadas de ${labels(group)}`},h('table',{},h('thead',{},h('tr',{},['ID tarea','Estado','Asignados observados','Inicio','Vence','Estimación','Lectura original'].map(cabecera443))),body)));};
   d=h('details',{'data-planning-cliente':group,on:{toggle:fill,click:()=>current(),keydown:()=>current()}},h('summary',{style:{minHeight:'44px',padding:'8px 12px',cursor:'pointer'}},`${labels(group)} · ${rs.length} ${rs.length===1?'tarea observada':'tareas observadas'}`));details.append(d);
   tbody.append(h('tr',{},h('td',{},labels(group)),...model.estados.map(state=>cuenta(rs,state)),dato(estimate,`${est.length}/${rs.length} tareas con estimación observada; suma parcial, no horas ejecutadas ni capacidad.`),h('td',{},h('button',{type:'button',on:{click:()=>{if(current()){d.open=true;fill();d.scrollIntoView?.({block:'nearest'});}}}},'Ver tareas'))));
  }
  if(!groups.length)tbody.append(h('tr',{},h('td',{colspan:headers.length},'Sin observaciones autorizadas con estos filtros. No acredita cero tareas.')));
  if(model.ampliado){
   const porAccount=new Map();for(const r of rows){const owner=accountPlanning405(initial,r.cliente_id,ctx.hoy),key=owner?.id||null;if(!porAccount.has(key))porAccount.set(key,{rows:[],confirmada:true});const g=porAccount.get(key);g.rows.push(r);g.confirmada&&=owner?.confirmada===true;}
   const body=h('tbody',{},...[...porAccount].map(([owner,g])=>h('tr',{},h('td',{title:owner&&!g.confirmada?'Asignación registrada por confirmar; no responsabilidad histórica.':'Asignación actual; no responsabilidad histórica.'},owner?initial.personas.find(p=>p.id===owner)?.nombre||owner:'Account por confirmar'),...model.estados.map(state=>cuenta(g.rows,state)))));
   result.append(h('h3',{},'Por account actual'),h('div',{class:'oe-scroll',tabindex:0,'aria-label':'Inventario observado por account actual'},h('table',{},h('thead',{},h('tr',{},...['Account','Backlog','Planning mensual','Planning semanal','Diario','En curso'].map(cabecera443))),body)));
  }
  const nota=h('p',{class:'oe-note'},model.filas.length?`${groups.length} proyectos · ${new Set(model.filas.map(r=>r.cliente_id)).size}/${model.cliente_ids.length} clientes con observaciones · copia parcial`:'Sin datos observados disponibles; inventario no acreditado.');
  const tabla=h('div',{class:'oe-scroll',tabindex:0,'aria-label':'Inventario observado por proyecto'},h('table',{},h('thead',{},h('tr',{},headers.map(cabecera443))),tbody));
  const summary=()=>h('summary',{style:{minHeight:'44px',padding:'8px 12px',cursor:'pointer'}},`Por proyecto · inventario de planning · ${groups.length}`);
  const proyectos=h('details',{'data-planning-proyectos-412':'',on:{toggle:()=>{
   if(!current())return;projectOpen=proyectos.open;proyectos.replaceChildren(summary());if(projectOpen)proyectos.append(nota,tabla,details);
  }}},summary());
  proyectos.open=projectOpen;if(projectOpen)proyectos.append(nota,tabla,details);
  result.append(h('p',{class:'oe-note'},'— sin dato · ≥ mínimo observado · estimación parcial, no horas ejecutadas.'),proyectos);

 };
 selectClient.addEventListener('change',()=>{if(current()){cid=selectClient.value;pid='';selectPerson.value='';paint();}});selectPerson.addEventListener('change',()=>{if(current()){pid=selectPerson.value;paint();}});
 const source=h('details',{on:{toggle:()=>current()}},h('summary',{},'Fuente y alcance'),h('p',{},`Estado observado entre ${lectura360(model.desde)} y ${lectura360(model.hasta)}. Lectura del agregado ${lectura360(model.generado)}. Parcial: sin diagnóstico de ruptura, fuego o disciplina. Estimación mínima observada, no capacidad ni presupuesto. Fechas programadas futuras no son incumplimientos. Asignados observados no acreditan autoría histórica.`));
 root.replaceChildren(compact,h('header',{},h('h2',{},'Inventario de planificación · copia observada')),h('div',{class:'oe-range'},h('label',{},'Cliente ',selectClient),h('label',{},'Asignado ',selectPerson)),result,source);paint();return true;
}
