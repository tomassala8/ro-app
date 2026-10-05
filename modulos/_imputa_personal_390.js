//390 · Horas personales observadas, nunca horas de los clientes ni evaluación de jornada.
import {ambitoHistorial364,cargarHistorial364,historialVigente364} from './_historial_diario_364.js';
import {bandaHoras381} from './_bandas_horas_381.js';
const arr=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
const fecha=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
const anteriores=hoy=>Array.from({length:7},(_,i)=>new Date(Date.parse(hoy+'T00:00Z')-(7-i)*864e5).toISOString().slice(0,10));
const formato=x=>x>0&&x<0.1?'<0,1':new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(x);
const unknown=detalle=>({valor:'—',estado:'gris',total:null,observadas:null,detalle:detalle||'Sin horas personales acreditadas para estas fechas; no equivale a cero.',banda_referencia:null});
export function ambitoImputa390(ctx,accountIds){try{
 if(!Array.isArray(accountIds)||!accountIds.every(id)||new Set(accountIds).size!==accountIds.length||!fecha(ctx.hoy))return null;
 const ps=arr(ctx.datos?.personas),H={personas:ps.map(p=>({persona_id:p?.id}))},hist=ambitoHistorial364(ctx,H);if(!hist)return null;
 const ids=accountIds.filter(pid=>{const xs=ps.filter(p=>p?.id===pid);return xs.length===1&&xs[0].estado==='activo'&&xs[0].activo!==false&&Array.isArray(xs[0].puestos)&&xs[0].puestos.length>0&&xs[0].puestos.every(id)&&new Set(xs[0].puestos).size===xs[0].puestos.length&&xs[0].puestos.includes('account')&&hist.ids.includes(pid);});
 return {ids,H,hist,firma:JSON.stringify([hist.firma,accountIds,ids])};
 }catch{return null;}}
export function modeloImputa390(ctx,accountIds,hist,antes){try{
 const scope=ambitoImputa390(ctx,accountIds);if(!scope||!antes||scope.firma!==antes.firma||hist?.denegado||!historialVigente364(ctx,scope.H,hist)||!(hist.series instanceof Map))return null;
 const fechas=anteriores(ctx.hoy),laborables=fechas.filter(f=>![0,6].includes(new Date(f+'T00:00Z').getUTCDay())).length,ref=laborables*8,celdas=new Map();
 for(const pid of scope.ids){
  const s=hist.series.get(pid);if(!s){celdas.set(pid,unknown());continue;}
  // El día del reloj de lectura, en la zona de esa persona, aún no era completo.
  const diaLectura=new Intl.DateTimeFormat('sv-SE',{timeZone:s.zona,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(s.fecha_fuente));
  const observadas=s.dias.filter(d=>fechas.includes(d.fecha)&&d.fecha<diaLectura&&d.estado==='observado'&&typeof d.horas==='number'&&Number.isFinite(d.horas)&&d.horas>=0&&Number.isSafeInteger(d.entradas)&&d.entradas>0);
  const total=observadas.length?observadas.reduce((n,d)=>n+d.horas,0):null;
  if(total===null||!Number.isFinite(total)){celdas.set(pid,unknown(total===null?'Sin registros observados de fechas completas en este rango; no ausencia de trabajo.':'Suma fuera de rango; no se presenta una cifra.'));continue;}
  const b=bandaHoras381(total,{tipo:'porcentaje',observado:true,fuente:'ClickUp entradas',cobertura:'parcial',hoy:ctx.hoy,fecha_fuente:s.fecha_fuente,desde:fechas[0],hasta:fechas.at(-1),referencia_horas:ref,laborables});
  celdas.set(pid,{valor:total>0&&total<0.1?'<0,1':total,estado:'gris',total,observadas:observadas.length,
   desde:fechas[0],hasta:fechas.at(-1),zona:s.zona,fecha:s.fecha_fuente,referencia_horas:ref,banda_referencia:b,
   detalle:`${formato(total)} h personales observadas · ${observadas.length}/7 fechas naturales con registros. Rango ${fechas[0]} → ${fechas.at(-1)}. Fuente ClickUp entradas, ${s.fecha_fuente}; zona ${s.zona}. Sólo fechas anteriores al día local de lectura ${diaLectura}. Copia parcial atribuida al inicio, duración cerrada no confirmada; días sin registros desconocidos. Referencia ${ref} h =8 h × ${laborables} días L–V, no calendario laboral confirmado, capacidad, jornada ni cumplimiento. No suma horas de los proyectos del account.`});
 }
 return {firma:scope.firma,accountIds:[...accountIds],celdas,desde:fechas[0],hasta:fechas.at(-1),cobertura:'parcial',fuente:'ClickUp entradas',generado:hist.generado};
 }catch{return null;}}
export async function cargarImputa390(ctx,accountIds){
 const antes=ambitoImputa390(ctx,accountIds);if(!antes||!antes.ids.length)return null;
 const hist=await cargarHistorial364(ctx,antes.H);return modeloImputa390(ctx,accountIds,hist,antes);
}
export function imputaVigente390(ctx,modelo){return !!modelo&&ambitoImputa390(ctx,modelo.accountIds)?.firma===modelo.firma;}
export function celdaImputa390(ctx,modelo,pid){return imputaVigente390(ctx,modelo)&&id(pid)&&modelo.celdas.has(pid)?modelo.celdas.get(pid):unknown('La medición no está disponible en el permiso actual.');}
