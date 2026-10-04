const PERIODO='2026-09',HASH='4afc61a142faadf9631141c3a33109712cfd9ecfdf832a99e469731e970f5bc2';
const arr=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,150}$/.test(x),activo=p=>p?.estado==='activo'&&p.activo!==false;
const dia=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
const roles=(a,b)=>Array.isArray(a)&&Array.isArray(b)&&a.length>0&&a.every(id)&&b.every(id)&&new Set(a).size===a.length&&new Set(b).size===b.length&&JSON.stringify([...a].sort())===JSON.stringify([...b].sort());
function fechaAware353(x,hoy){if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(x)||!dia(x.slice(0,10)))return false;const m=/T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|([+-])(\d{2}):(\d{2}))$/.exec(x);if(!m||+m[1]>23||+m[2]>59||+m[3]>59||(m[4]!=='Z'&&(+m[6]>14||+m[7]>59||(+m[6]===14&&+m[7]!==0))))return false;const d=new Date(x);return Number.isFinite(d.getTime())&&new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(d)<=hoy;}
export function ambitoLlamadas353(ctx){try{
 if(ctx.servidor!==true||ctx.vigente?.()===false||!ctx.veModulo?.('bandeja')||typeof ctx.ver!=='function'||!dia(ctx.hoy)||ctx.hoy<'2026-10-01')return null;
 const ps=arr(ctx.datos?.personas),actores=[ctx.real,ctx.persona];
 if(!actores.every(p=>id(p?.id)&&activo(p)&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&activo(x)&&roles(x.puestos,p.puestos))&&p.puestos.some(r=>['direccion','operaciones','account'].includes(r))))return null;
 const cs=arr(ctx.clientesVisibles),propia=ctx.persona.puestos.includes('account')&&!ctx.persona.puestos.some(r=>['operaciones','direccion'].includes(r)),cartera=new Set(ctx.carteraPorSilla?.account||[]);
 const clientes=cs.filter(c=>id(c?.id)&&cs.filter(x=>x?.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle===true&&(!propia||cartera.has(c.id))&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true),ids=clientes.map(c=>c.id).sort();
 return {ids,firma:JSON.stringify([actores.map(p=>[p.id,p.estado,p.activo,p.puestos]),ctx.hoy,ids,[...cartera].sort(),ps.map(p=>[p.id,p.estado,p.activo,p.puestos]),arr(ctx.datos?.asignaciones).map(a=>[a?.cliente_id,a?.persona_id,a?.silla,a?.desde,a?.hasta,a?.principal,a?.confianza,a?.duda,a?.suplencia]),clientes.map(c=>[c.id,arr(c.equipo?.account).map(a=>[a?.persona_id,a?.desde,a?.hasta,a?.principal,a?.confianza,a?.duda,a?.suplencia])])])};
 }catch{return null;}}
export function proyectarLlamadas353(ctx,d,antes){try{
 const actual=ambitoLlamadas353(ctx);if(!antes||!actual||actual.firma!==antes.firma||!d||d.version!=='350.1'||d.periodo!==PERIODO||!fechaAware353(d.generado,ctx.hoy)||!Array.isArray(d.filas)||!['copia_historica','sin_dato'].includes(d.estado))return null;
 const fuente=d.cobertura==='parcial'&&d.fuente==='Zadarma · agregado histórico local'&&d.sha256_candidato===HASH;
 const ausente=d.cobertura==='desconocida'&&d.fuente===null&&d.sha256_candidato===null;
 if(!fuente&&!ausente)return null;
 const vistos=new Set(),filas=[];
 for(const r of d.filas){
  if(!id(r?.cliente_id)||!actual.ids.includes(r.cliente_id)||vistos.has(r.cliente_id)||r.periodo!==PERIODO||r.unidad!=='llamadas_respondidas_30s'||r.actor_id!==null||r.direccion!==null||r.registro!=='historico'||r.verificacion_externa!==false||r.cumplimiento!==null)return null;
  const conocido=Number.isSafeInteger(r.llamadas_30s)&&r.llamadas_30s>0;
  if(conocido?(!fuente||r.estado!=='copia_historica'):(r.llamadas_30s!==null||r.estado!=='sin_dato'))return null;
  vistos.add(r.cliente_id);filas.push({cliente_id:r.cliente_id,llamadas_30s:r.llamadas_30s});
 }
 if((filas.some(r=>r.llamadas_30s!==null)?'copia_historica':'sin_dato')!==d.estado)return null;
 return {firma:actual.firma,periodo:PERIODO,generado:d.generado,fuente:fuente?d.fuente:null,hash:fuente?HASH:null,filas};
 }catch{return null;}}
const desconocido=()=>({valor:'—',estado:'gris',detalle:'Sin agregado histórico autorizado para septiembre2026. Ausencia de fila o dato no acredita cero llamadas.',total:null});
function modeloValido353(ctx,m,scope){return !!m&&m.firma===scope?.firma&&m.periodo===PERIODO&&fechaAware353(m.generado,ctx.hoy)&&((m.fuente==='Zadarma · agregado histórico local'&&m.hash===HASH)||(m.fuente===null&&m.hash===null))&&Array.isArray(m.filas)&&new Set(m.filas.map(r=>r?.cliente_id)).size===m.filas.length&&m.filas.every(r=>scope.ids.includes(r?.cliente_id)&&(r.llamadas_30s===null||(m.fuente!==null&&Number.isSafeInteger(r.llamadas_30s)&&r.llamadas_30s>0)));}
const huella=m=>JSON.stringify([m?.periodo,m?.generado,m?.fuente,m?.hash,m?.filas]);
const lecturaMadrid353=x=>new Intl.DateTimeFormat('es-ES',{timeZone:'Europe/Madrid',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(x))+' (Madrid)';
export function celdaLlamadas353(ctx,modelo,ids){
 const scope=ambitoLlamadas353(ctx);if(!scope||!modeloValido353(ctx,modelo,scope)||!Array.isArray(ids)||new Set(ids).size!==ids.length||!ids.every(cid=>scope.ids.includes(cid)))return desconocido();
 const xs=modelo.filas.filter(r=>ids.includes(r.cliente_id)&&Number.isSafeInteger(r.llamadas_30s)&&r.llamadas_30s>0),total=xs.reduce((n,r)=>n+r.llamadas_30s,0);
 if(!xs.length||!Number.isSafeInteger(total))return desconocido();
 return {valor:`≥${total} · sep2026`,estado:'gris',total,medidos:xs.length,clientes:ids.length,periodo:PERIODO,fecha:modelo.generado,fecha_texto:lecturaMadrid353(modelo.generado),fuente:modelo.fuente,ambito353:scope.firma,fuente353:huella(modelo),
 detalle:`Septiembre2026: mínimo observado de ${total} llamadas respondidas de al menos30 segundos, ${xs.length}/${ids.length} clientes con dato histórico; resto desconocido. Copia parcial de Zadarma, lectura del agregado ${lecturaMadrid353(modelo.generado)}. Actor y dirección desconocidos; no atribuye estas llamadas al account actual. Agrupación por cartera actual sólo para consulta. No mide esta semana ni octubre, contacto semanal, ejecución de pedidos o cumplimiento.`};
}
export function celdaLlamadasVigente353(ctx,modelo,celda){return !celda?.ambito353?celda?.total===null:modeloValido353(ctx,modelo,ambitoLlamadas353(ctx))&&modelo.firma===celda.ambito353&&huella(modelo)===celda.fuente353;}
