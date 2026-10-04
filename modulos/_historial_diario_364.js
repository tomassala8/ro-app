// Historial personal362: lectura/proyección, sin mutaciones ni evaluación laboral.
const SHA364='21abf5db866bfd0ed9805b61bf686a625f613d37d21ce80095ef998f209f6280';
const array=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x),activo=p=>p?.estado==='activo'&&p.activo!==false;
const fecha=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
const roles=(a,b)=>Array.isArray(a)&&Array.isArray(b)&&a.length>0&&a.every(id)&&b.every(id)&&new Set(a).size===a.length&&new Set(b).size===b.length&&JSON.stringify([...a].sort())===JSON.stringify([...b].sort());
function instante(x){if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(x)||!fecha(x.slice(0,10)))return null;const m=/T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-](\d{2}):(\d{2}))$/.exec(x);if(!m||+m[1]>23||+m[2]>59||+m[3]>59||(m[4]!=='Z'&&(+m[5]>14||+m[6]>59||(+m[5]===14&&+m[6]!==0))))return null;const n=Date.parse(x);return Number.isFinite(n)?n:null;}
const madrid=n=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(n));
const anteriores=(c,n)=>Array.from({length:n},(_,i)=>new Date(Date.parse(c+'T00:00:00Z')-(n-i)*864e5).toISOString().slice(0,10));
export function ambitoHistorial364(ctx,H){try{
 if(ctx.servidor!==true||ctx.vigente?.()===false||!fecha(ctx.hoy)||!ctx.veModulo?.('horas')||typeof ctx.ver!=='function'||!Array.isArray(H?.personas))return null;
 const ps=array(ctx.datos?.personas),actors=[ctx.real,ctx.persona];
 if(!actors.every(p=>id(p?.id)&&activo(p)&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&activo(x)&&roles(x.puestos,p.puestos))))return null;
 const rows=H.personas,ids=rows.filter(p=>id(p?.persona_id)&&rows.filter(x=>x?.persona_id===p.persona_id).length===1&&ps.filter(x=>x?.id===p.persona_id).length===1&&ps.some(x=>x.id===p.persona_id&&activo(x))&&ctx.ver({tipo:'horas_persona',persona_id:p.persona_id})?.ok===true).map(p=>p.persona_id).sort();
 const grants=rows.filter(p=>id(p?.persona_id)).map(p=>[p.persona_id,ctx.ver({tipo:'horas_persona',persona_id:p.persona_id})?.ok===true]);
 return {ids,firma:JSON.stringify([actors,ctx.hoy,ps,rows.map(p=>p?.persona_id),grants,ctx.veModulo('horas')])};
 }catch{return null;}}
export function modeloHistorial364(ctx,D,H,antes){try{
 const scope=ambitoHistorial364(ctx,H),gen=instante(D?.generado);
 if(!scope||!antes||scope.firma!==antes.firma||D?.version!=='362.1'||gen===null||madrid(gen)>ctx.hoy||!Array.isArray(D.personas)||D.unidad!=='h'||D.cumplimiento!==null||D.capacidad_contractual!==null)return null;
 if(D.estado!=='copia_observada'||D.fuente!=='ClickUp entradas'||D.fuente_version!=='359.1'||D.sha256_candidato!==SHA364||D.cobertura!=='parcial')return null;
 const series=new Map(),seen=new Set();
 for(const row of D.personas){
  const pid=row?.persona_id,s=row?.historial_diario;if(!id(pid)||seen.has(pid)||!scope.ids.includes(pid))return null;seen.add(pid);
  const cut=s?.corte_fecha,stamp=instante(s?.fecha_fuente_utc);
  if(s?.version!=='359.1'||s.fuente!=='ClickUp entradas'||s.cobertura!=='parcial'||s.unidad!=='h'||s.zona_confirmada!==true||!fecha(cut)||cut>ctx.hoy||cut>madrid(gen)||stamp===null||stamp>gen||madrid(stamp)>cut||!/(Z|\+00:00)$/.test(s.fecha_fuente_utc)||s.atribucion!=='inicio'||s.duracion_cerrada_confirmada!==false||s.sin_registros_no_equivale_a_cero!==true)return null;
  try{if(typeof s.zona!=='string')return null;new Intl.DateTimeFormat('es-ES',{timeZone:s.zona});}catch{return null;}
  const dates=anteriores(cut,90);if(s.desde!==dates[0]||s.hasta!==dates.at(-1)||!Array.isArray(s.dias)||s.dias.length!==90)return null;
  const dias=[];
  for(let i=0;i<90;i++){
   const d=s.dias[i];if(!d||d.fecha!==dates[i])return null;
   if(d.estado==='observado'){if(typeof d.horas!=='number'||!Number.isFinite(d.horas)||d.horas<0||!Number.isSafeInteger(d.entradas)||d.entradas<1)return null;}
   else if(d.estado!=='sin_dato'||d.horas!==null||d.entradas!==null)return null;
   dias.push({fecha:d.fecha,horas:d.horas,entradas:d.entradas,estado:d.estado});
  }
  series.set(pid,{persona_id:pid,dias,zona:s.zona,fecha_fuente:s.fecha_fuente_utc,desde:s.desde,hasta:s.hasta,corte:cut});
 }
 if(new Set([...series.values()].map(s=>s.corte+'|'+s.fecha_fuente)).size>1)return null;
 return {firma:scope.firma,series,generado:D.generado,sha:SHA364};
 }catch{return null;}}
export function historialVigente364(ctx,H,modelo){return !!modelo&&ambitoHistorial364(ctx,H)?.firma===modelo.firma;}
export async function cargarHistorial364(ctx,H){
 const before=ambitoHistorial364(ctx,H);if(!before||typeof ctx.api!=='function')return null;
 try{const d=await ctx.api('horas/historial-diario');return modeloHistorial364(ctx,d,H,before);}catch(e){return [401,403].includes(e?.status)?{denegado:true}:null;}
}
export function horasHistorialRango364(s,r){
 if(!s||!Array.isArray(s.dias)||!fecha(r?.desde)||!fecha(r?.hasta)||r.desde>r.hasta||(Date.parse(r.hasta)-Date.parse(r.desde))/864e5>3660)return null;
 const total=Math.round((Date.parse(r.hasta+'T00:00:00Z')-Date.parse(r.desde+'T00:00:00Z'))/864e5)+1,observados=s.dias.filter(d=>d.fecha>=r.desde&&d.fecha<=r.hasta&&d.estado==='observado'),sum=observados.length?observados.reduce((a,d)=>a+d.horas,0):null;
 const valor=typeof sum==='number'&&Number.isFinite(sum)?sum:null,dias=observados.length?observados.filter(d=>d.horas>0).length:null,ultima=observados.at(-1)?.fecha||null;
 return {valor,tipo:valor===null?'sin_dato':'observado_historial_90d',dias,ultima,parcial:true,fechas_con_registros:observados.length||null,total_dias:total,fuera_ventana:r.desde<s.desde||r.hasta>s.hasta,fecha:s.fecha_fuente,
 detalle:`Suma observada ${valor===null?'sin dato':valor} h. Duración mínima observada ${r.desde} → ${r.hasta}: ${observados.length}/${total} fechas naturales con registros; ${dias===null?'sin dato':dias} días con horas positivas observadas. Historial ${s.desde} → ${s.hasta}; corte ${s.corte}; fuente UTC ${s.fecha_fuente}; zona ${s.zona}. Copia parcial, atribuida al inicio; sin registros no equivale a cero. ${r.desde<s.desde||r.hasta>s.hasta?'Parte del rango queda fuera de los 90 días. ':''}No acredita jornada ni capacidad contractual.`};
}
