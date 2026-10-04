// Proyección de una regla confirmada por el servidor: jamás deduce cohorte por precio.
const dia=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T12:00:00Z'))&&new Date(v+'T12:00:00Z').toISOString().slice(0,10)===v;
const filas=v=>Array.isArray(v)?v:[];
const siguiente=v=>new Date(Date.parse(v+'T12:00:00Z')+15*864e5).toISOString().slice(0,10);
export function proyectarMetodo305(doc,ids,personas,hoy){
 const out=new Map();if(!dia(hoy)||doc?.hoy!==hoy||!Array.isArray(doc?.sugerencias)||!Array.isArray(ids)||new Set(ids).size!==ids.length)return out;
 const scope=new Set(ids),counts=new Map();for(const r of doc.sugerencias)if(typeof r?.cliente_id==='string')counts.set(r.cliente_id,(counts.get(r.cliente_id)||0)+1);
 for(const r of doc.sugerencias){
  if(!scope.has(r?.cliente_id)||counts.get(r.cliente_id)!==1||r.regla_id!=='seguimiento_quincenal_especialista'||r.cadencia_dias!==15||r.responsable_role!=='trafficker'||r.incumplimiento!==null)continue;
  if(!['sin_dato','confirmar_responsable','en_cadencia','revisar_cadencia','confirmar_recencia'].includes(r.estado))continue;
  const owners=filas(r.responsables_ids),ps=filas(personas).filter(p=>p?.id===r.responsable_id),owner=owners.length===1&&owners[0]===r.responsable_id&&ps.length===1&&ps[0].estado==='activo'&&ps[0].activo!==false&&Array.isArray(ps[0].puestos)&&ps[0].puestos.length>0&&ps[0].puestos.every(x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x))&&new Set(ps[0].puestos).size===ps[0].puestos.length&&ps[0].puestos.includes('trafficker')?r.responsable_id:null;
  const ultima=dia(r.ultima_confirmada)&&r.ultima_confirmada<=hoy&&filas(r.fuentes_operativas).some(e=>e?.tipo==='reunion_celebrada'&&e.fecha===r.ultima_confirmada)?r.ultima_confirmada:null;
  const proxima=ultima&&r.proxima_revision===siguiente(ultima)?r.proxima_revision:null;
  const coherente=owner&&ultima&&proxima;
  const estado=r.estado==='en_cadencia'?(coherente&&hoy<=proxima?'en_cadencia':'sin_dato'):r.estado==='revisar_cadencia'?(coherente&&hoy>proxima&&doc.cobertura_reuniones?.completa===true&&dia(doc.cobertura_reuniones.desde)&&doc.cobertura_reuniones.desde<=ultima&&dia(doc.cobertura_reuniones.hasta)&&doc.cobertura_reuniones.hasta>=hoy?'revisar_cadencia':'confirmar_recencia'):r.estado;
  out.set(r.cliente_id,{cliente_id:r.cliente_id,responsable_id:owner,ultima_confirmada:ultima,proxima_revision:proxima,estado,fecha_fuente:hoy,cadencia_dias:15,responsable_role:'trafficker'});
 }
 return out;
}
export function hitoReferencia305(hito,metodo){return !!metodo&&hito?.id==='reunion_resultados';}
