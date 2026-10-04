import {h,chipEstado} from '../componentes.js';
import {ambitoViernes347,filasViernes347} from './_viernes_accounts_347.js';
import {ambitoRepartir352,atribuirReparto352} from './_repartir_accounts_352.js';

const n=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
export const ambitoRepartir326=ctx=>ambitoRepartir352(ctx);
export function filasRepartir326(ctx,P,B){
  const scope=ambitoRepartir326(ctx);if(!scope)return {tareas:[],tickets:[]};
  const f=filasSaneamiento264({...ctx,clientesVisibles:scope.clientes},P,B);
  const vistos=new Set(f.tareas.map(t=>t.id));
  const tareas=atribuirReparto352(ctx,[...f.tareas,...f.bloqueadas.filter(t=>!vistos.has(t.id))]).map(t=>({...t,dias:n(t.dias)?t.dias:null}));
  return {tareas:tareas.sort((a,b)=>a.dias===null?b.dias===null?String(a.id).localeCompare(String(b.id)):1:b.dias===null?-1:b.dias-a.dias),tickets:atribuirReparto352(ctx,f.tickets.filter(t=>t.horas>30*24))};
}
export function filasSaneamiento264(ctx,P,B) {
  const catalogo=ctx.clientesVisibles||[];
  const clientes=new Map(catalogo.filter(c=>c.id&&catalogo.filter(x=>x.id===c.id).length===1&&c.detalle!==false&&c.activo_confirmado===true).map(c=>[c.id,c]));
  const unique=(rows)=>{const counts=new Map();rows.forEach(r=>counts.set(r.id,(counts.get(r.id)||0)+1));return rows.filter(r=>r.id&&counts.get(r.id)===1);};
  const tareas=unique((P?.revisiones||[]).filter(t=>clientes.has(t.cliente_id)&&['account','técnica','mili'].includes(t.revisa))).map(t=>({...t,account_id:clientes.get(t.cliente_id).responsable_id||t.account_id||null,cliente:clientes.get(t.cliente_id).nombre}));
  const tickets=unique((B?.correos||[]).filter(t=>clientes.has(t.cliente_id)&&!t.auto&&!t.boletin&&n(t.horas))).map(t=>({...t,account_id:clientes.get(t.cliente_id).responsable_id||t.account_id||null,cliente:clientes.get(t.cliente_id).nombre}));
  const bloqueadas=unique((P?.cola||[]).filter(t=>clientes.has(t.cli)&&t.grupo==='bloqueada'&&t.estado_determinado===true&&t.estado==='bloqueado')).map(t=>({...t,cliente_id:t.cli,account_id:clientes.get(t.cli).responsable_id||null,cliente:clientes.get(t.cli).nombre,dias:t.dias_estado}));
  return {tareas,tickets,bloqueadas};
}
export function resumenRepartir354(tf,kf) {
  const ids=new Set([...tf,...kf].map(f=>f.account_id||'__sin'));
  return [...ids].map(id=>{
    const tareas=tf.filter(t=>(t.account_id||'__sin')===id),tickets=kf.filter(t=>(t.account_id||'__sin')===id);
    const edades=tareas.map(t=>t.dias).filter(n);
    return {id,nombre:[...tareas,...tickets][0]?.account_texto||'Account por confirmar',tareas:tareas.length,tickets:tickets.length,edad:edades.length?Math.max(...edades):null};
  });
}
function tabla264(titulo,columnas,filas) {
  return h('section',{class:'panel'},h('header',{style:{padding:'12px 18px'}},h('h2',{style:{margin:'0',fontSize:'15px'}},titulo)),
    h('div',{style:{overflowX:'auto'}},h('table',{class:'densa',style:{width:'100%'}},
      h('thead',{},h('tr',{},columnas.map(c=>h('th',{scope:'col'},c[0])))),
      h('tbody',{},filas.length?filas.map(f=>h('tr',{},columnas.map(c=>h('td',{},c[1](f))))):h('tr',{},h('td',{colspan:String(columnas.length)},'Sin filas observadas en esta copia. No acredita inventario completo.'))))));
}
const cliente=(ctx,id)=>ctx.navegar(`operaciones/fichas/${id}`);
export async function renderRituales264(cont,ctx,clave) {
  const vigente=()=>cont.isConnected && (!ctx.vigente||ctx.vigente());
  if(clave==='puesto') {
    if(!ctx.veModulo('mi-dia'))return;
    const account=!(ctx.persona.puestos||[]).some(p=>['direccion','operaciones'].includes(p));
    if(account){const m=await import('./mi_perfil.js');if(vigente())await m.default.render(cont,ctx);return;}
    const d=await ctx.datosModulo('mi_dia/ronda_mili');if(!vigente())return;
    cont.append(h('section',{class:'panel'},h('h2',{},'Cinco principios'),h('ol',{},(d.principios||[]).map(p=>h('li',{},p)))));
    const groups=new Map();for(const i of d.items||[]){if(!groups.has(i.f))groups.set(i.f,[]);groups.get(i.f).push(i);}
    const destinos={dia:'dia',equipo:'equipo',produccion:'produccion',fuegos:'fuegos',accounts:'accounts',clientes:'clientes',cierre:'cierre',bandeja:'bandeja',tomas:'tomas',viernes:'viernes',repartir:'repartir',nuevos:'nuevos',hoy:'hoy',fichas:'fichas',rastro:'rastro',incongruencias:'incongruencias'};
    for(const [grupo,filas] of groups)cont.append(tabla264(grupo,[['Qué',f=>f.que],['Dónde lo ves',f=>h('a',{href:`#/operaciones/${destinos[f.donde]||'dia'}`},f.donde)],['Cómo queda la prueba',f=>f.prueba],['Lo pidió',f=>f.desde]],filas));
    return;
  }
  if(clave==='viernes') {
    const inicial=ambitoViernes347(ctx);if(!inicial)return;
    let raiz;
    const viernesVigente=()=>{const ok=raiz?.isConnected&&vigente()&&ambitoViernes347(ctx)?.firma===inicial.firma;if(!ok)raiz?.replaceChildren();return ok;};
    raiz=h('div',{'data-viernes-347':'lectura',on:{click:()=>viernesVigente(),focusin:()=>viernesVigente(),keydown:()=>viernesVigente()}});cont.append(raiz);
    let P,B;
    try { [P,B]=await Promise.all([ctx.datosModulo('produccion/produccion'),ctx.datosModulo('bandeja/bandeja')]); }
    catch { if(viernesVigente())raiz.append(h('p',{role:'status'},'No se pudo leer la copia de revisiones y tickets.'));return; }
    if(!viernesVigente())return;
    const filas=filasViernes347(ctx,filasSaneamiento264({...ctx,clientesVisibles:inicial.clientes},P,B));
    const g=new Map(),grupo=r=>{const id=r.account_id||'__sin';if(!g.has(id))g.set(id,{id,nombre:r.account_texto,tareas:0,tickets:0});return g.get(id);};
    filas.tareas.forEach(r=>grupo(r).tareas++);filas.tickets.forEach(r=>grupo(r).tickets++);
    if(!viernesVigente())return;
    raiz.append(h('p',{class:'sub'},`Copia parcial de producción ${P?.generado||'sin fecha'} y bandeja ${B?.generado||'sin fecha'}. Inventario observado; no es una foto certificada del viernes a las 18:00.`));
    raiz.append(tabla264('Lo que debe quedar a cero el viernes',[['Account',r=>r.nombre],['Tareas en revisión',r=>r.tareas||'—'],['Tickets sin contestar',r=>r.tickets||'—'],['Estado',r=>chipEstado('ambar','Pendiente en la copia')]],Array.from(g.values())));
    raiz.append(h('p',{class:'sub'},'Objetivo del ritual: cero revisiones internas y cero tickets esperando respuesta. La ausencia de registros no confirma que se haya cumplido.'));
    return;
  }
  if(!ctx.veModulo('produccion')||!ctx.veModulo('bandeja'))return;
  const ambito=clave==='repartir'?ambitoRepartir326(ctx):null;
  if(clave==='repartir'&&!ambito)return;
  const destino=clave==='repartir'?h('div',{'data-repartir-326':'lectura',on:{click:()=>repartoVigente(),focusin:()=>repartoVigente(),keydown:()=>repartoVigente()}}):cont;
  if(clave==='repartir')cont.append(destino);
  const repartoVigente=()=>{const ok=vigente()&&destino.isConnected&&ambitoRepartir326(ctx)?.firma===ambito?.firma;if(!ok&&clave==='repartir')destino.replaceChildren();return ok;};
  if(clave==='repartir'&&!repartoVigente())return;
  let P,B;try{[P,B]=await Promise.all([ctx.datosModulo('produccion/produccion'),ctx.datosModulo('bandeja/bandeja')]);}catch{if(clave==='repartir'&&repartoVigente())destino.append(h('p',{role:'status'},'No se pudo leer la copia de incidencias.'));return;}if(!vigente())return;
  if(clave==='repartir'&&!repartoVigente()){destino.replaceChildren();return;}
  destino.append(h('p',{class:'sub'},`Copia parcial de producción ${P?.generado||'sin fecha'} y bandeja ${B?.generado||'sin fecha'}. Asignación actual registrada; no atribuye autoría histórica de las incidencias.`));
  const reparto=filasRepartir326(ctx,P,B),tf=reparto.tareas,kf=reparto.tickets;
  const grupos=resumenRepartir354(tf,kf),cajas354=new Map();
  if(grupos.length)destino.append(tabla264('Pendientes observados por account',[
    ['Account',r=>h('button',{type:'button',class:'bt mini',on:{click:()=>{if(!repartoVigente())return;const d=cajas354.get(r.id);if(d){d.open=true;d.scrollIntoView?.({block:'start',behavior:'smooth'});}}}},r.nombre)],
    ['Tareas · revisión / bloqueo',r=>chipEstado(r.tareas?'ambar':'gris',String(r.tareas))],['Tickets · +30 días',r=>chipEstado(r.tickets?'ambar':'gris',String(r.tickets))],['Mayor edad · tareas',r=>r.edad===null?'Sin fecha':new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(r.edad)+' días'],
  ],grupos));
  for(const g of grupos){const pid=g.id,nombre=g.nombre;
    const caja354=h('details',{'data-repartir-detalle':'354',class:'panel',on:{toggle:()=>repartoVigente()}},h('summary',{style:{minHeight:'44px',padding:'12px 18px',boxSizing:'border-box',cursor:'pointer',fontWeight:'600'}},`${nombre} · ${g.tareas} ${g.tareas===1?'tarea':'tareas'} · ${g.tickets} ${g.tickets===1?'ticket observado':'tickets observados'}`));
    cajas354.set(pid,caja354);destino.append(caja354);
    caja354.append(tabla264(`Tareas en revisión o bloqueadas · ${nombre}`,[['Tarea',t=>h('a',{href:`#/produccion/tarea/${encodeURIComponent(t.id)}`,on:{click:e=>{if(!repartoVigente()){e.preventDefault();destino.replaceChildren();}}}},t.tarea)],['Cliente',t=>h('button',{class:'bt mini',on:{click:()=>{if(repartoVigente())cliente(ctx,t.cliente_id);else destino.replaceChildren();}}},t.cliente)],['Estado',t=>t.estado],['Días',t=>t.dias===null?'Sin fecha':t.dias]],tf.filter(t=>(t.account_id||'__sin')===pid)));
    caja354.append(tabla264(`Tickets viejos sin cerrar · ${nombre}`,[['Ticket',t=>h('a',{href:`#/bandeja/${encodeURIComponent(t.id)}`,on:{click:e=>{if(!repartoVigente()){e.preventDefault();destino.replaceChildren();}}}},`${t.numero||''} · ${t.asunto||''}`)],['Cliente',t=>t.cliente],['Último mensaje',t=>t.desde||'Sin fecha'],['Días',t=>Math.floor(t.horas/24)]],kf.filter(t=>(t.account_id||'__sin')===pid).sort((a,b)=>b.horas-a.horas)));
  }
  if(!grupos.length)destino.append(h('p',{},'Sin revisiones, bloqueos o tickets de más de30 días observados en esta copia. No acredita inventario completo.'));
}
