import {proyectarMetodo305} from './_metodo_cohorte_305.js';
// Lectura declarativa y metodología existente; no calcula cumplimiento ni agenda.
const array=x=>Array.isArray(x)?x:[];
const id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,200}$/.test(x);
const dia=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
const activo=p=>p?.estado==='activo'&&p.activo!==false;
const roles=p=>Array.isArray(p?.puestos)&&p.puestos.length>0&&p.puestos.every(id)&&new Set(p.puestos).size===p.puestos.length;
const iguales=(a,b)=>roles(a)&&roles(b)&&JSON.stringify([...a.puestos].sort())===JSON.stringify([...b.puestos].sort());
const corta=d=>dia(d)?`${d.slice(8,10)}/${d.slice(5,7)}/${d.slice(2,4)}`:'—';
const celda=(valor,detalle)=>({valor:String(valor),estado:'gris',detalle,cumplimiento:null,verificacion_externa:false});
const vacia=detalle=>celda('—',detalle);
export const COLUMNAS_SEGUIMIENTO_404=Object.freeze(['Cliente','Reuniones semana','Seguimiento quincenal','Trafficker','Última confirmada','Próxima revisión']);
export const LEYENDA_SEGUIMIENTO_404='Reuniones semana: declaraciones del equipo, no celebración verificada. Seguimiento: regla existente de 15 días con trafficker. Próxima revisión no es cita agendada. Registro histórico mensual separado en detalle.';
export function ambitoSeguimiento404(ctx,rows=null){try{
 if(!ctx.servidor||ctx.vigente?.()===false||!dia(ctx.hoy)||typeof ctx.ver!=='function'||ctx.veModulo?.('mi-dia')!==true||!Array.isArray(ctx.clientes)||!Array.isArray(ctx.datos?.personas))return null;
 const ps=ctx.datos.personas,actors=[ctx.real,ctx.persona];
 if(!actors.every(p=>id(p?.id)&&activo(p)&&roles(p)&&ps.filter(a=>a?.id===p.id).length===1&&ps.some(a=>a?.id===p.id&&activo(a)&&iguales(a,p))&&p.puestos.some(r=>['direccion','operaciones','account'].includes(r))))return null;
 const real=ctx.real.puestos,vista=ctx.persona.puestos;
 if(ctx.real.id!==ctx.persona.id&&!real.some(r=>['direccion','operaciones'].includes(r)))return null;
 const own=vista.includes('account')&&!vista.some(r=>['direccion','operaciones'].includes(r)),cartera=new Set(ctx.carteraPorSilla?.account||[]),visible=array(ctx.clientesVisibles);
 const ids=visible.filter(c=>id(c?.id)&&visible.filter(a=>a?.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle===true&&ctx.clientes.filter(a=>a?.id===c.id).length===1&&ctx.clientes.some(a=>a?.id===c.id&&a.activo_confirmado===true&&a.detalle===true)&&(!own||cartera.has(c.id))&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
 if(rows!==null&&(!Array.isArray(rows)||new Set(rows.map(r=>r?.cliente_id)).size!==rows.length||!rows.every(r=>ids.includes(r?.cliente_id))))return null;
 return {ids,firma:JSON.stringify([actors.map(p=>[p.id,p.estado,p.activo,p.puestos]),ctx.hoy,ctx.veModulo?.('mi-dia'),ctx.veModulo?.('mi-trabajo'),ctx.veModulo?.('reuniones'),ids,ctx.clientes.map(c=>[c?.id,c?.activo_confirmado,c?.detalle]),ps.map(p=>[p?.id,p?.estado,p?.activo,p?.puestos]),[...cartera].sort()])};
}catch{return null;}}
const ESTADOS404=Object.freeze({sin_dato:'Confirmar evidencia',confirmar_responsable:'Confirmar responsable',en_cadencia:'En cadencia',revisar_cadencia:'Revisar cadencia',confirmar_recencia:'Confirmar recencia'});
export function proyectarSeguimiento404(ctx,rows,{declaraciones=new Map(),semana,metodo=null}={}){
 const scope=ambitoSeguimiento404(ctx,rows);if(!scope)return [];
 const monday=new Date(ctx.hoy+'T12:00Z');monday.setUTCDate(monday.getUTCDate()-((monday.getUTCDay()+6)%7));
 const week=dia(semana)&&semana===monday.toISOString().slice(0,10);
 const current=ctx.veModulo?.('reuniones')===true&&metodo?.hoy===ctx.hoy&&Array.isArray(metodo?.sugerencias);
 const validados=current?proyectarMetodo305(metodo,scope.ids,ctx.datos.personas,ctx.hoy):new Map();
 return rows.map(r=>{
  const f=ctx.veModulo?.('mi-trabajo')===true&&week&&declaraciones instanceof Map?declaraciones.get(r.cliente_id):null;
  const declared=f?.cliente_id===r.cliente_id&&f.estado==='declarado'&&f.source_kind==='registro_equipo'&&f.verificacion_externa===false&&f.cumplimiento===null&&Number.isSafeInteger(f.reuniones_declaradas)&&f.reuniones_declaradas>=0;
  const reunion=declared?celda(f.reuniones_declaradas,`Semana desde ${semana}, Europe/Madrid. Registro manual del equipo. Cero significa cero declaraciones, no ausencia de actividad. No confirma celebración, asistencia ni cumplimiento.`):vacia('No hay declaración autorizada de reuniones de esta semana. No equivale a cero.');
  const history=r.reunion_historica;
  const historical=dia(history?.fecha_registro)&&history.fecha_registro<=ctx.hoy?`Último registro histórico: ${history.fecha_registro}; no confirma celebración ni cadencia vigente.`:'Sin último registro histórico acreditado.';
  const matches=current?metodo.sugerencias.filter(s=>s?.cliente_id===r.cliente_id):[];
  const s=matches.length===1?matches[0]:null;
  const typed=s&&s.regla_id==='seguimiento_quincenal_especialista'&&s.cadencia_dias===15&&s.responsable_role==='trafficker'&&Object.hasOwn(ESTADOS404,s.estado)&&s.incumplimiento===null;
  const acreditado=typed?validados.get(r.cliente_id):null;
  const candidates=typed?array(s.responsables_ids):[];
  const ps=typed&&id(s.responsable_id)&&candidates.length===1&&candidates[0]===s.responsable_id?ctx.datos.personas.filter(p=>p?.id===s.responsable_id):[];
  // Misma autoridad de seguimiento305: puesto trafficker íntegro, único y activo.
  const owner=acreditado?.responsable_id&&ps.length===1&&activo(ps[0])&&roles(ps[0])?ps[0]:null;
  const last=acreditado?.ultima_confirmada||null;
  const next=acreditado?.proxima_revision||null;
  const invalidDates=typed&&((s.ultima_confirmada!=null&&!last)||(s.proxima_revision!=null&&!next));
  // No se reconstruyen fechas, propietarios ni colores a partir de nombres.
  const needsDates=typed&&['en_cadencia','revisar_cadencia','confirmar_recencia'].includes(s.estado);
  const valid=typed&&!!acreditado&&!invalidDates&&(!needsDates||(owner!==null&&last!==null&&next!==null));
  const explanation=valid?`Regla existente: cada15 días con trafficker. Estado leído: ${ESTADOS404[acreditado.estado]}. Lectura operativa ${metodo.hoy}; cobertura de reuniones ${metodo.cobertura_reuniones?.completa===true?'declarada completa':'parcial o sin confirmar'}. Próxima revisión no es cita ni envío. ${historical}`:`Sin regla actual inequívoca y válida para este cliente. ${historical}`;
  return {cliente_id:r.cliente_id,firma404:scope.firma,celdas:[reunion,valid?celda(acreditado.estado==='sin_dato'?'—':ESTADOS404[acreditado.estado],explanation):vacia(explanation),valid&&owner?{...celda(owner.nombre||owner.alias||owner.id,`Trafficker actual canónico ${owner.id}, identificado en el DTO operativo. No asigna tareas ni envía mensajes. ${historical}`),persona_id:owner.id}:vacia('Trafficker sin identidad actual única y activa confirmada. '+historical),valid&&last?celda(corta(last),`Última confirmada en la fuente operativa: ${last}. No se deduce del registro mensual histórico. ${historical}`):vacia('Sin última confirmada en la fuente operativa. '+historical),valid&&next?celda(corta(next),`Próxima revisión según DTO operativo: ${next}. No es cita agendada ni promesa de celebración. ${historical}`):vacia('Sin próxima revisión acreditada en el DTO operativo. '+historical)]};
 });
}
export function seguimientoVigente404(ctx,rows,firma){return typeof firma==='string'&&ambitoSeguimiento404(ctx,rows)?.firma===firma;}
