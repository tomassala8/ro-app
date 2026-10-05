// Lectura compacta de observaciones existentes; no capacidad, evaluación ni acciones.
import {cargarHistorial364,historialVigente364} from './_historial_diario_364.js';
const ar=x=>Array.isArray(x)?x:[],id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
const active=p=>p?.estado==='activo'&&p.activo!==false;
export function ambitoNotasHoras383(ctx,filas){try{
 if(ctx.servidor!==true||!day(ctx.hoy)||ctx.vigente?.()===false||!ctx.veModulo?.('mi-dia')||!ctx.veModulo?.('horas'))return null;
 const ps=ar(ctx.datos?.personas);
 for(const p of [ctx.real,ctx.persona]){const xs=ps.filter(x=>id(x?.id)&&x.id===p?.id);if(xs.length!==1||!active(xs[0])||!active(p)||!Array.isArray(p.puestos)||!p.puestos.length||p.puestos.some(x=>!id(x))||new Set(p.puestos).size!==p.puestos.length||!Array.isArray(xs[0].puestos)||!xs[0].puestos.length||xs[0].puestos.some(x=>!id(x))||new Set(xs[0].puestos).size!==xs[0].puestos.length||JSON.stringify([...p.puestos].sort())!==JSON.stringify([...xs[0].puestos].sort()))return null;}
 const rows=ar(filas),ids=rows.filter(p=>id(p?.persona_id)&&rows.filter(x=>x?.persona_id===p.persona_id).length===1&&ps.filter(x=>x?.id===p.persona_id).length===1&&ps.some(x=>x.id===p.persona_id&&active(x))&&ctx.ver?.({tipo:'notas_persona',persona_id:p.persona_id})?.ok===true&&ctx.ver?.({tipo:'horas_persona',persona_id:p.persona_id})?.ok===true).map(p=>p.persona_id).sort();
 if(!ids.length)return null;
 return {ids,firma:JSON.stringify([ctx.real,ctx.persona,ps,ctx.hoy,ids,rows.map(p=>[p?.persona_id,ctx.ver?.({tipo:'notas_persona',persona_id:p?.persona_id})?.ok===true,ctx.ver?.({tipo:'horas_persona',persona_id:p?.persona_id})?.ok===true])])};
 }catch{return null;}}
export async function cargarNotasHoras383(ctx,filas){
 const scope=ambitoNotasHoras383(ctx,filas);if(!scope)return null;
 const H={personas:scope.ids.map(persona_id=>({persona_id}))};
 const modelo=await cargarHistorial364(ctx,H);
 if(ambitoNotasHoras383(ctx,filas)?.firma!==scope.firma)return {denegado:true};
 if(modelo?.denegado)return {denegado:true};
 return modelo?{scope,H,modelo}:null;
}
export function notasHorasVigentes383(ctx,filas,copia){return !!copia&&!copia.denegado&&ambitoNotasHoras383(ctx,filas)?.firma===copia.scope.firma&&historialVigente364(ctx,copia.H,copia.modelo);}
export function serieNota383(serie,hoy){
 if(!day(hoy)||!serie||!id(serie.persona_id)||!day(serie.desde)||!day(serie.hasta)||!day(serie.corte)||serie.corte>hoy||serie.hasta>=serie.corte||!Array.isArray(serie.dias)||serie.dias.length!==90||typeof serie.fecha_fuente!=='string')return null;
 const m=/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|\+00:00)$/.exec(serie.fecha_fuente);
 const stamp=Date.parse(serie.fecha_fuente);if(!m||!day(m[1])||+m[2]>23||+m[3]>59||+m[4]>59||!Number.isFinite(stamp)||m[1]>hoy)return null;
 try{if(typeof serie.zona!=='string')return null;new Intl.DateTimeFormat('es-ES',{timeZone:serie.zona});}catch{return null;}
 const start=Date.parse(serie.corte+'T00:00:00Z')-90*864e5;
 for(let i=0;i<90;i++){const d=serie.dias[i],fecha=new Date(start+i*864e5).toISOString().slice(0,10);if(d?.fecha!==fecha)return null;
  if(d.estado==='observado'){if(typeof d.horas!=='number'||!Number.isFinite(d.horas)||d.horas<0||!Number.isSafeInteger(d.entradas)||d.entradas<1)return null;}
  else if(d.estado!=='sin_dato'||d.horas!==null||d.entradas!==null)return null;
 }
 if(serie.desde!==serie.dias[0].fecha||serie.hasta!==serie.dias.at(-1).fecha)return null;
 return {dias:serie.dias.slice(-14).map(d=>({...d})),desde:serie.dias.at(-14).fecha,hasta:serie.hasta,corte:serie.corte,zona:serie.zona,fecha_fuente:serie.fecha_fuente};
}
export function semanaNota383(serie,hoy,anterior=false){
 const s=serieNota383(serie,hoy);if(!s)return null;
 const d=new Date(hoy+'T00:00:00Z');d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7)-(anterior?7:0));const desde=d.toISOString().slice(0,10);d.setUTCDate(d.getUTCDate()+6);const hasta=anterior?d.toISOString().slice(0,10):hoy;
 const ds=serie.dias.filter(x=>x.fecha>=desde&&x.fecha<=hasta&&x.estado==='observado');
 const total=ds.reduce((n,x)=>n+x.horas,0);if(!ds.length||!Number.isFinite(total))return null;
 return {valor:total,desde,hasta,fecha_fuente:s.fecha_fuente,estado:'observado',cobertura:'parcial',dias_observados:ds.length,zona:s.zona};
}
export function graficoNota383(h,s){
 const root=h('div',{'data-horas-nota-383':'',style:{display:'flex',alignItems:'flex-end',gap:'2px',height:'26px',maxWidth:'112px'},role:'img','aria-label':`Horas observadas ${s.desde} a ${s.hasta}; copia parcial, zona ${s.zona}. Los huecos no equivalen a cero.`});
 const max=Math.max(...s.dias.filter(d=>d.estado==='observado').map(d=>d.horas),0);
 for(const d of s.dias){const observado=d.estado==='observado',height=observado?(d.horas===0?2:Math.max(2,d.horas/(max||1)*24)):2;
  root.append(h('span',{title:`${d.fecha}: ${observado?(d.horas>0&&d.horas<0.001?'<0,001':d.horas.toLocaleString('es-ES'))+' h observadas':'sin datos'}`,style:{display:'block',flex:'1',minWidth:'2px',height:height+'px',background:observado?'var(--azul, #2563eb)':'transparent',borderBottom:observado?'0':'1px dotted var(--texto-suave, #64748b)'}}));
 }
 return root;
}
