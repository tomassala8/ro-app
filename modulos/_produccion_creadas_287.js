const SHA='f2e568ced88d880a9df5aedde752d51d5d982ac52d7cb7b190fc9bf299bc49a2';
const fecha=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
export function creadasSemana287(p,D,hoy){
 const m=p?._evidencia_equipo_275;if(!m)return undefined;
 const desconocido={valor:null,detalle:'Descriptor de creación incompatible con el período/identidad actual; no acredita cero.'};
 if(!fecha(hoy)||m.version!=='275.1'||m.sha256_candidato!==SHA||m.fuente!=='clickup_cache_local'||m.cobertura!=='parcial'||m.zona!=='Europe/Madrid'||m.persona_id!==p.persona_id||m.criterio!=='creador_ID_canonico+clientes_del_DTO'||m.cierres_ayer!==null||m.al_planning!==null||m.rompen_semanal!==null)return desconocido;
 const rows=Array.isArray(D?.personas)?D.personas:[];if(rows.filter(x=>x?.persona_id===p.persona_id).length!==1)return desconocido;
 if(typeof m.corte!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(m.corte)||!Number.isFinite(Date.parse(m.corte)))return desconocido;
 const dia=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(m.corte));
 const lunes=new Date(hoy+'T00:00:00Z');lunes.setUTCDate(lunes.getUTCDate()-((lunes.getUTCDay()+6)%7));
 if(!fecha(dia)||dia>hoy||m.lunes!==lunes.toISOString().slice(0,10))return desconocido;
 const valor=m.creadas_semana;
 if(valor===null&&m.creadas_semana_observaciones===0)return {valor:null,detalle:`Sin creaciones observadas acreditadas en este ámbito; no equivale a cero. Corte ${m.corte}.`};
 if(!Number.isSafeInteger(valor)||valor<=0||valor!==m.creadas_semana_observaciones)return desconocido;
 return {valor,detalle:`${m.lunes} → ${dia} · ${valor} creaciones observadas de este creador canónico, sólo clientes del DTO autorizado. Copia parcial al ${m.corte}; no acredita paso por planning ni ruptura semanal.`};
}

//296: comparación adicional. «Semana pasada» del planning original sigue siendo rompen.
import { h } from '../componentes.js';
const SHA296='a6a010afd792d87263cb4e4b0854a9848e3e16e9d8a5aaab237e0de4f9d02b50';
const arr296=x=>Array.isArray(x)?x:[];
const entero296=x=>Number.isSafeInteger(x)&&x>=0;
function descriptor296(r,hoy,kind){
 const m=r?._comparacion_semanal_296;
 if(!m||!fecha(hoy)||m.version!=='296.1'||m.sha256_candidato!==SHA296||m.fuente!=='clickup_cache_local'||m.cobertura!=='parcial'||m.actor_cierre!==null||m.aceptacion_entrega!==null||m.comparacion_rendimiento!==null||m.columna_original_semana_pasada!=='rompen_semanal;no_sustituir_por_creaciones')return null;
 const cut=new Date(m.corte_utc);if(typeof m.corte_utc!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(m.corte_utc)||!Number.isFinite(+cut))return null;
 const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(cut).map(p=>[p.type,p.value]));const day=`${parts.year}-${parts.month}-${parts.day}`;
 if(!fecha(day)||day>hoy)return null;
 const monday=new Date(day+'T00:00:00Z');monday.setUTCDate(monday.getUTCDate()-((monday.getUTCDay()+6)%7));const prev=new Date(+monday-7*864e5);const windows=m.ventanas;
 if(!windows||Object.keys(windows).sort().join(',')!=='actual,anterior')return null;
 for(const [p,from,to,inc]of[['actual',monday.toISOString().slice(0,10),day,true],['anterior',prev.toISOString().slice(0,10),monday.toISOString().slice(0,10),false]]){
  const w=windows[p];if(!w||w.zona!=='Europe/Madrid'||w.cobertura!=='parcial'||w.hasta_inclusiva!==inc||typeof w.desde_madrid!=='string'||!w.desde_madrid.startsWith(from+'T00:00:00')||typeof w.hasta_madrid!=='string'||!w.hasta_madrid.startsWith(to+'T')||+new Date(w.desde_madrid)!==+new Date(w.desde_utc)||+new Date(w.hasta_madrid)!==+new Date(w.hasta_utc)||!Number.isFinite(+new Date(w.desde_utc)))return null;
  if(p==='actual'&&+new Date(w.hasta_utc)!==+cut||p==='anterior'&&(!w.hasta_madrid.startsWith(to+'T00:00:00')||+new Date(w.hasta_utc)!==+new Date(windows.actual.desde_utc)))return null;
 }
 if(kind==='proyecto'&&m.cliente_id!==r.cliente_id||kind==='creador'&&(m.persona_id!==r.persona_id||m.criterio!=='creador_ID_canonico+clientes_del_DTO'||m.rompen_semanal!==null||m.al_planning!==null||m.fuegos_directos!==null||'finales'in m))return null;
 for(const tipo of kind==='proyecto'?['creadas','finales']:['creadas']){
  if(!m[tipo]||Object.keys(m[tipo]).sort().join(',')!=='actual,anterior')return null;
  for(const p of ['actual','anterior']){
   const a=m[tipo][p],field=tipo==='finales'?'date_done_or_closed+catalogo_actual_terminal':kind==='creador'?'date_created+creator_ID_canonico':'date_created';
   if(!a||!entero296(a.observaciones)||a.valor!==(a.observaciones||null)||a.ventana!==p||a.campo!==field||a.atribucion!==kind||a.cobertura!=='parcial'||a.cero_no_acredita_ausencia!==true)return null;
  }
 }
 return m;
}
function owner296(ctx,c){
 const ps=arr296(ctx.datos?.personas),active=id=>{const p=ps.filter(x=>x?.id===id);return p.length===1&&p[0].estado==='activo'&&p[0].activo!==false;};
 const refs=[...arr296(c.equipo?.account),...arr296(ctx.datos?.asignaciones).filter(a=>a?.cliente_id===c.id&&a.silla==='account')].filter(a=>a?.principal===true&&!a.suplencia&&!a.duda&&active(a.persona_id)&&(!a.desde||fecha(a.desde)&&a.desde<=ctx.hoy)&&(!a.hasta||fecha(a.hasta)&&a.hasta>=ctx.hoy));
 const ids=[...new Set(refs.map(a=>a.persona_id))];return ids.length===1?{id:ids[0],confirmado:refs.some(a=>a.confianza==='confirmada')}:null;
}
export function modeloComparacionSemanal296(ctx,D){
 const projects=arr296(D?.proyectos),people=arr296(D?.personas),cs=arr296(ctx.clientes),unique=(xs,k,id)=>xs.filter(x=>x?.[k]===id).length===1;
 const filas=[];
 for(const r of projects){
  if(!unique(projects,'cliente_id',r?.cliente_id))continue;
  const c=cs.find(c=>c?.id===r.cliente_id);
  if(!c||!unique(cs,'id',c.id)||c.activo_confirmado!==true||c.detalle!==true)continue;
  const m=descriptor296(r,ctx.hoy,'proyecto');if(!m)continue;
  filas.push({cliente_id:c.id,nombre:c.nombre||c.id,account:owner296(ctx,c),medicion:m});
 }
 const creadores=[];
 for(const r of people){
  const p=arr296(ctx.datos?.personas).find(p=>p?.id===r?.persona_id);
  if(!p||p.estado!=='activo'||p.activo===false||!unique(ctx.datos.personas,'id',p.id)||!unique(people,'persona_id',r.persona_id))continue;
  const m=descriptor296(r,ctx.hoy,'creador');
  const scope=m?.cliente_ids_scope;
  if(m&&Array.isArray(scope)&&scope.every(id=>typeof id==='string'&&filas.some(f=>f.cliente_id===id))&&new Set(scope).size===scope.length)creadores.push({persona_id:p.id,nombre:p.nombre||p.id,medicion:m});
 }
 return {filas,creadores};
}
export function panelComparacionSemanal296(ctx,D){
 const root=h('details',{class:'panel','data-comparacion-semanal':'296'});const vivo=()=>root.isConnected&&(!ctx.vigente||ctx.vigente());
 if(ctx.vigente&&!ctx.vigente())return root;
 const model=modeloComparacionSemanal296(ctx,D),m=model.filas[0]?.medicion||model.creadores[0]?.medicion;
 root.append(h('summary',{style:{padding:'12px 16px',minHeight:'44px',boxSizing:'border-box',cursor:'pointer'}},'Creaciones y finales · comparación adicional'));
 if(!m){root.append(h('p',{class:'sub',style:{padding:'0 16px 12px'}},'Comparación pendiente de datos acreditados en tu ámbito.'));return root;}
 const label=p=>m.ventanas[p].desde_madrid.slice(0,10);const display=a=>a?.valor===null?'Sin dato':`≥${a.valor}`;
 const numeric=(r,t,p)=>h('td',{style:{textAlign:'right',whiteSpace:'nowrap'},title:`${r.medicion.ventanas[p].desde_madrid} → ${r.medicion.ventanas[p].hasta_madrid}. Observación parcial; sin observaciones no acredita cero.`},display(r.medicion[t][p]));
 const accountName=a=>{const p=arr296(ctx.datos?.personas).find(p=>p.id===a?.id);return a?(p?.nombre||a.id)+(a.confirmado?'':' · por confirmar'):'Por confirmar';};
 const body=h('tbody'),creatorBody=h('tbody');
 const table=h('table',{style:{width:'100%',borderCollapse:'collapse',fontSize:'13px',minWidth:'750px'}},h('thead',{},h('tr',{},['Proyecto','Account actual',`Creadas ${label('actual')}`,`Creadas ${label('anterior')}`,`Finales ${label('actual')}`,`Finales ${label('anterior')}`].map(x=>h('th',{scope:'col',style:{textAlign:'left',padding:'8px 10px',whiteSpace:'normal'}},x)))),body);
 let selected='';const accounts=[...new Set(model.filas.map(r=>r.account?.id).filter(Boolean))];
 const draw=(inicial=false)=>{if(ctx.vigente&&!ctx.vigente()||!inicial&&!root.isConnected)return;const latest=modeloComparacionSemanal296(ctx,D);body.replaceChildren(...latest.filas.filter(r=>!selected||r.account?.id===selected).map(r=>h('tr',{},h('td',{style:{padding:'8px 10px'}},h('a',{href:`#/ficha/${encodeURIComponent(r.cliente_id)}`,on:{click:e=>{if(!vivo()||!modeloComparacionSemanal296(ctx,D).filas.some(x=>x.cliente_id===r.cliente_id))e.preventDefault();}}},r.nombre)),h('td',{style:{padding:'8px 10px'}},accountName(r.account)),numeric(r,'creadas','actual'),numeric(r,'creadas','anterior'),numeric(r,'finales','actual'),numeric(r,'finales','anterior'))));creatorBody.replaceChildren(...latest.creadores.map(r=>h('tr',{},h('td',{},r.nombre),numeric(r,'creadas','actual'),numeric(r,'creadas','anterior'))));};
 root.append(h('div',{style:{padding:'0 16px 10px'}},h('label',{},'Account actual ',h('select',{'aria-label':'Filtrar comparación por account',style:{minHeight:'44px',border:'1px solid #e1e4f1',borderRadius:'8px',background:'#fff',padding:'6px 10px',font:'inherit',maxWidth:'100%'},on:{change:e=>{if(!vivo())return;selected=e.target.value;draw();}}},h('option',{value:''},'Todos los autorizados'),accounts.map(id=>h('option',{value:id},accountName(model.filas.find(r=>r.account?.id===id)?.account)))))),h('div',{style:{overflowX:'auto',padding:'0 6px'}},table));
 draw(true);
 root.append(h('p',{class:'sub',style:{padding:'8px 16px',margin:0}},`Copia parcial al ${m.corte_utc} · no es entrega aceptada ni cierre por persona. Account agrupa por asignación actual; no atribuye responsabilidad histórica.`));
 if(model.creadores.length)root.append(h('details',{style:{padding:'0 16px 12px'}},h('summary',{style:{minHeight:'44px'}},'Creaciones por creador · proyectos autorizados'),h('div',{style:{overflowX:'auto'}},h('table',{style:{width:'100%',fontSize:'13px'}},h('thead',{},h('tr',{},['Creador',label('actual'),label('anterior')].map(x=>h('th',{scope:'col'},x)))),creatorBody))));
 return root;
}
