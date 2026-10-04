//469 · sólo cohorte observada autorizada; sin acciones ni identificación de leads.
const etapas=[['recibido','Rec.','Recibidos observados'],['cualificado','Cual.','Cualificados'],['contacto','Cont.','Contacto humano'],['respuesta','Resp.','Respuesta'],['cita','Citas','Reservas creadas observadas'],['asistencia','Asist.','Asistencia'],['venta','Ventas','Ventas']];
const ids=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x),arr=x=>Array.isArray(x)?x:[],n=x=>Number.isSafeInteger(x)&&x>=0;
const keys=(x,ks)=>x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join('|')===[...ks].sort().join('|');
const instante=x=>{if(typeof x!=='string')return null;const m=x.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$/);if(!m)return null;const d=new Date(m[1]+'T00:00:00Z'),off=m[6];if(!Number.isFinite(+d)||d.toISOString().slice(0,10)!==m[1]||+m[2]>23||+m[3]>59||+m[4]>59)return null;if(off!=='Z'){const a=+off.slice(1,3),b=+off.slice(4,6);if(a>14||b>59||(a===14&&b))return null;}const t=Date.parse(x);return Number.isFinite(t)?t:null;};
const limites=['Copia parcial: sólo eventos observados, sin censo completo.','La cohorte de recibidos y los eventos del periodo son universos distintos.','Cita registra creación de un evento: puede estar cancelado o tener una fecha futura; no acredita asistencia o validez.','Sin tasas, conversión, cualificación automática ni cumplimiento contractual.','Una venta no acredita cobro, margen o rentabilidad; las etapas no se infieren entre sí.'];
const diaValido=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
const diagnosticos=new Set(['contacto_coleccion_invalida','contacto_identidad_invalida','contacto_payload_invalido','contacto_replay','contacto_conflicto','contacto_no_lead_explicito','contacto_fecha_invalida','contacto_fecha_futura','cita_coleccion_invalida','cita_identidad_invalida','cita_payload_invalido','cita_replay','cita_conflicto','cita_contacto_no_enlazado','cita_fecha_creacion_invalida','cita_fecha_futura','cita_anterior_recibido','fuente_reporta_errores']);
export function ambitoEmbudo469(ctx,cid){try{
 if(ctx.servidor!==true||ctx.vigente?.()===false||ctx.veModulo?.('salud-crm')!==true||!ids(cid))return null;
 const ps=arr(ctx.datos?.personas),actors=[ctx.real,ctx.persona];
 for(const p of actors){const xs=ps.filter(x=>x?.id===p?.id);if(!ids(p?.id)||xs.length!==1||p.estado!=='activo'||p.activo===false||xs[0].estado!=='activo'||xs[0].activo===false)return null;for(const r of [p.puestos,xs[0].puestos])if(!Array.isArray(r)||!r.length||!r.every(ids)||new Set(r).size!==r.length)return null;if(JSON.stringify([...p.puestos].sort())!==JSON.stringify([...xs[0].puestos].sort()))return null;}
 const cs=[arr(ctx.clientes),arr(ctx.clientesVisibles)].map(xs=>xs.filter(x=>x?.id===cid));
 if(cs.some(xs=>xs.length!==1||xs[0].activo_confirmado!==true||xs[0].activo===false||xs[0].estado==='baja'||xs[0].detalle===false)||ctx.ver?.({tipo:'cliente_detalle',cliente_id:cid})?.ok!==true)return null;
 return JSON.stringify([actors,ps,ctx.clientes,ctx.clientesVisibles,ctx.hoy,ctx.veModulo('salud-crm'),ctx.ver({tipo:'cliente_detalle',cliente_id:cid})]);
 }catch{return null;}}
export function modeloEmbudo469(dto,cid,hoy){try{
 if(!keys(dto,['version','estado','cliente_id','medicion','diagnosticos','hora_fuente','desde','hasta','corte'])||dto.version!=='467.1'||dto.cliente_id!==cid)return null;
 if(dto.estado==='sin_configurar')return ['medicion','diagnosticos','hora_fuente','desde','hasta','corte'].every(k=>dto[k]===null)?{disponible:false}:null;
 if(dto.estado!=='copia_observada'||!diaValido(hoy))return null;
 const ts=['desde','hasta','corte','hora_fuente'].map(k=>instante(dto[k]));if(ts.some(x=>x===null)||ts[0]>ts[1]||ts[1]>ts[2]||ts[3]>ts[2]||new Date(ts[2]).toISOString().slice(0,10)>hoy)return null;
 if(!keys(dto.diagnosticos,Object.keys(dto.diagnosticos||{}))||Object.entries(dto.diagnosticos).some(([k,v])=>!diagnosticos.has(k)||!n(v)))return null;
 const m=dto.medicion;if(!keys(m,['version','cohorte','eventos_periodo','observado_hasta','ventana_recepcion','ventana_eventos','zona','limites'])||m.version!=='467.1'||m.zona!=='UTC'||instante(m.observado_hasta)!==ts[2]||JSON.stringify(m.limites)!==JSON.stringify(limites))return null;
 for(const k of ['ventana_recepcion','ventana_eventos'])if(!keys(m[k],['desde','hasta'])||instante(m[k].desde)!==ts[0]||instante(m[k].hasta)!==ts[1])return null;
 const c=m.cohorte;if(!keys(c,['recibidos_observados','estado','etapas'])||!n(c.recibidos_observados)||c.estado!==(c.recibidos_observados?'parcial':'desconocido')||!keys(c.etapas,etapas.map(e=>e[0]))||!keys(m.eventos_periodo,etapas.map(e=>e[0])))return null;
 const vals={};for(const [k]of etapas){const e=c.etapas[k],p=m.eventos_periodo[k];if(!keys(e,['observados','estado'])||!n(e.observados)||e.observados>c.recibidos_observados||e.estado!==(e.observados?'parcial':'desconocido'))return null;
  if(!keys(p,['eventos_observados','leads_unicos_observados','estado'])||!n(p.eventos_observados)||!n(p.leads_unicos_observados)||p.leads_unicos_observados>p.eventos_observados||p.estado!==(p.eventos_observados?'parcial':'desconocido'))return null;
  if(!['recibido','cita'].includes(k)&&(e.observados!==0||p.eventos_observados!==0||p.leads_unicos_observados!==0))return null;vals[k]=e.observados>0?e.observados:null;
 }
 if(c.etapas.recibido.observados!==c.recibidos_observados)return null;
 return {disponible:true,vals,desde:new Date(ts[0]).toISOString(),hasta:new Date(ts[1]).toISOString(),corte:dto.corte,fuente:dto.hora_fuente};
 }catch{return null;}}
export function panelEmbudo469(ctx,cid,{h}){
 const root=h('details',{'data-embudo-observado-469':'',class:'panel'}),firma=ambitoEmbudo469(ctx,cid),body=h('div',{class:'cuerpo'});let ocupado=false,cargado=false;
 const autoridad=()=>firma!==null&&ambitoEmbudo469(ctx,cid)===firma;
 const vivo=()=>root.isConnected===true&&autoridad();
 const limpiar=()=>root.replaceChildren();
 if(!firma)return root;
 root.append(h('summary',{style:{minHeight:'44px',padding:'10px 16px'}},'Embudo observado · parcial'),body);
 root.addEventListener('toggle',async()=>{
  if(!vivo()){limpiar();return;}if(!root.open||ocupado||cargado)return;ocupado=true;body.replaceChildren(h('p',{role:'status',class:'sub'},'Consultando observaciones…'));
  try{const dto=await ctx.api('crm/embudo-observado/'+cid);if(!vivo()){limpiar();return;}const m=modeloEmbudo469(dto,cid,ctx.hoy);if(!m||!m.disponible){body.replaceChildren(h('p',{role:'status',class:'sub'},'Sin una copia compatible disponible. — no significa cero actividad.'));cargado=true;return;}
   body.replaceChildren(h('p',{class:'sub'},`Recepción: ${m.desde.slice(0,16).replace('T',' ')} → ${m.hasta.slice(0,16).replace('T',' ')} · UTC · parcial`),h('div',{style:{overflowX:'auto'}},h('table',{class:'densa',style:{width:'100%'}},h('thead',{},h('tr',{},...etapas.map(([,short,full])=>h('th',{scope:'col',title:full,'aria-label':full},short)))),h('tbody',{},h('tr',{},...etapas.map(([k,,full])=>h('td',{title:`${full}: ${m.vals[k]===null?'sin observaciones acreditadas; no equivale a cero':m.vals[k]+' observados en cohorte parcial'}`,'aria-label':`${full}: ${m.vals[k]===null?'sin dato':m.vals[k]+' observados'}`},m.vals[k]===null?'—':new Intl.NumberFormat('es-ES').format(m.vals[k]))))))),h('p',{class:'sub'},'—: sin dato o etapa no instrumentada. Reservas creadas, incluidas canceladas; no acreditan asistencia. Sin tasas ni conversión.'),h('details',{on:{toggle:()=>{if(!vivo())limpiar();}}},h('summary',{style:{minHeight:'44px'}},'Fuente y ventanas'),h('p',{class:'sub'},`GHL · lectura original ${m.fuente} · corte ${m.corte}. Recepción/eventos del período ${m.desde} → ${m.hasta}; son universos distintos. La tabla sólo muestra la cohorte de recibidos y sus etapas observadas hasta el corte. Copia parcial, no censo ni ejecución comercial verificada.`)));
   cargado=true;
  }catch{if(!vivo())limpiar();else body.replaceChildren(h('p',{role:'status',class:'sub'},'Observaciones no disponibles. No acredita ausencia de actividad.'));}finally{ocupado=false;}
 });
 return root;
}
