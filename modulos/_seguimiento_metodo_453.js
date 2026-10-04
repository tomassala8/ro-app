import {estadoCadencia,textoCadencia} from './_cadencia_metodo.js';
// Metadatos452 se presentan aparte de la celebración confirmada305, nunca como KPI.
const list=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[a-zA-Z0-9_-]{1,100}$/.test(x),activo=p=>p?.estado==='activo'&&p.activo!==false;
const dia=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T12:00Z'))&&new Date(x+'T12:00Z').toISOString().slice(0,10)===x;
const roles=p=>Array.isArray(p?.puestos)&&p.puestos.length>0&&p.puestos.every(id)&&new Set(p.puestos).size===p.puestos.length;
const FALTANTES=['celebracion','participacion_trafficker','responsable_en_fecha','cobertura_intervalo'];
export function ambitoSeguimiento453(ctx){try{
 if(!dia(ctx.hoy)||ctx.veModulo?.('reuniones')!==true||ctx.vigente?.()===false)return null;
 const ps=list(ctx.datos?.personas),cs=list(ctx.clientes),vs=list(ctx.clientesVisibles);
 for(const actor of [ctx.real,ctx.persona]){const xs=ps.filter(p=>p?.id===actor?.id);if(!id(actor?.id)||!activo(actor)||!roles(actor)||xs.length!==1||!activo(xs[0])||!roles(xs[0])||JSON.stringify([...actor.puestos].sort())!==JSON.stringify([...xs[0].puestos].sort()))return null;}
 const ids=cs.filter(c=>id(c?.id)&&cs.filter(x=>x?.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle!==false&&vs.filter(x=>x?.id===c.id).length===1&&vs.some(x=>x.id===c.id&&x.activo_confirmado===true&&x.detalle!==false)&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
 return {ids,firma:JSON.stringify([ctx.real,ctx.persona,ps,cs,vs,ctx.datos?.asignaciones,ctx.hoy,ctx.veModulo('reuniones'),ctx.veModulo('ficha'),cs.map(c=>[c?.id,ctx.ver?.({tipo:'cliente_detalle',cliente_id:c?.id})?.ok===true])])};
}catch{return null;}}
export function evidenciaSeguimiento453(e,hoy){
 const unknown={estado:'sin_dato',registros:null,ultima:null,importado:null,detalle:'Metadatos históricos no disponibles; no equivale a ausencia de reuniones.'};
 if(!dia(hoy)||e?.version!=='452.1'||!['disponible','sin_configurar','no_autorizado','no_disponible'].includes(e.estado_fuente)||e.responsable_historico!==null||e.celebracion_confirmada!==null||e.participacion_trafficker_confirmada!==null||!Array.isArray(e.faltantes)||e.faltantes.length!==4||new Set(e.faltantes).size!==4||!FALTANTES.every(x=>e.faltantes.includes(x)))return unknown;
 if(e.estado_fuente!=='disponible')return e.cobertura==='desconocida'&&e.registros_historicos_observados===null&&e.ultimo_registro_historico===null&&e.importado_el===null?{...unknown,estado:e.estado_fuente}:unknown;
 const n=e.registros_historicos_observados;
 if(e.cobertura!=='parcial'||!Number.isSafeInteger(n)||n<0||!dia(e.importado_el)||e.importado_el>hoy||(n===0?e.ultimo_registro_historico!==null:!dia(e.ultimo_registro_historico)||e.ultimo_registro_historico>e.importado_el))return unknown;
 return {estado:'disponible',registros:n,ultima:e.ultimo_registro_historico,importado:e.importado_el,detalle:`Archivo local importado ${e.importado_el}; cobertura parcial. ${n} registros históricos observados. No confirma celebración, participación del trafficker ni responsable histórico; no evalúa cumplimiento.`};
}
const corta=x=>dia(x)?`${x.slice(8,10)}-${['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][Number(x.slice(5,7))-1]}`:'—';
export function pintarSeguimiento453(h,ctx,filas,doc,{ambitoInicial=ambitoSeguimiento453(ctx),vigente=()=>true}={}){
 const root=h('div',{'data-seguimiento-453':'tabla',style:{minWidth:0,maxWidth:'100%'}}),autorizado=()=>{const a=ambitoSeguimiento453(ctx);return vigente()===true&&a&&ambitoInicial&&a.firma===ambitoInicial.firma;},actual=()=>root.isConnected&&autorizado(),limpiar=()=>root.replaceChildren();
 if(!autorizado())return root;
 const raw=list(doc?.sugerencias),counts=new Map();for(const r of raw)if(id(r?.cliente_id))counts.set(r.cliente_id,(counts.get(r.cliente_id)||0)+1);
 const rs=list(filas).filter(r=>ambitoInicial.ids.includes(r?.cliente_id)&&list(filas).filter(x=>x?.cliente_id===r.cliente_id).length===1);
 const historicoPermitido=[ctx.real,ctx.persona].every(p=>p.puestos.some(r=>['direccion','operaciones','account'].includes(r)));
 const detalles=h('div',{}),d=h('details',{style:{minWidth:0,maxWidth:'100%',overflowX:'auto'},on:{toggle:()=>{if(!actual()){limpiar();return;}detalles.replaceChildren();if(!d.open)return;detalles.append(h('table',{class:'densa',style:{minWidth:'640px',width:'100%'}},h('thead',{},h('tr',{},[
 ['Cliente','Cliente autorizado actual'],['Trafficker','Responsable actual; no atribución histórica'],['Últ. conf.','Última reunión celebrada confirmada'],['Próx. rev.','Próxima revisión de cadencia; no cita agendada'],['Reg. hist.','Registros históricos observados del archivo parcial'],['Últ. reg.','Última fecha de registro histórico; no reunión confirmada'],['Abrir','Abrir reunión e histórico local autorizado']].map(([t,title])=>h('th',{scope:'col',title,'aria-label':title},t)))),h('tbody',{},rs.map(r=>{
 const src=counts.get(r.cliente_id)===1?raw.find(x=>x.cliente_id===r.cliente_id):null;
 const ev=historicoPermitido&&doc?.hoy===ctx.hoy?evidenciaSeguimiento453(src?.evidencia_por_revisar,ctx.hoy):evidenciaSeguimiento453(null,ctx.hoy);
 const cliente=list(ctx.clientes).find(c=>c.id===r.cliente_id),owner=list(ctx.datos?.personas).filter(p=>p.id===r.responsable_id&&activo(p)),nombre=owner.length===1?(owner[0].nombre||owner[0].alias||r.responsable_id):'—';
 const ref=textoCadencia(r),tono=estadoCadencia(r),fechaCelda=(x,title)=>h('td',{title,'aria-label':title},corta(x));
 const enlace=ev.estado==='disponible'&&ev.registros>0&&ctx.veModulo?.('ficha')===true?h('a',{class:'bt mini',href:`#/ficha/${encodeURIComponent(r.cliente_id)}/reunion`,title:'Abrir reunión · histórico local; el registro no confirma celebración','aria-label':'Abrir reunión e histórico local de '+(cliente?.nombre||r.cliente_id),style:{minHeight:'44px'},on:{click:e=>{if(!actual()){e.preventDefault();limpiar();}}}},'Abrir'):h('span',{title:ev.detalle},'—');
 return h('tr',{},h('td',{},cliente?.nombre||r.cliente_id),h('td',{},nombre),fechaCelda(r.ultima_confirmada,ref),h('td',{title:ref,'aria-label':ref},h('span',{class:'chip '+tono},corta(r.proxima_revision))),h('td',{title:ev.detalle,'aria-label':ev.detalle},ev.registros===null?'—':String(ev.registros)),fechaCelda(ev.ultima,ev.detalle),h('td',{},enlace));
 }))));}}},h('summary',{style:{minHeight:'44px',cursor:'pointer'}},`${rs.length} cuentas · ${rs.filter(r=>estadoCadencia(r)==='gris').length} por confirmar · ver seguimiento`),detalles);
 root.append(h('p',{class:'sub'},'Registros históricos ≠ celebración ni participación confirmadas.'),d);return root;
}
