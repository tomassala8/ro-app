import { clientesDia314, crmDia314 } from './_resultados_dia_314.js';
const count=v=>Number.isSafeInteger(v)&&v>=0?v:null;
export function sumarObservaciones317(filas,leer){const valores=filas.map(leer);return {valor:valores.some(v=>count(v)!==null)?valores.reduce((n,v)=>n+(count(v)??0),0):null,observadas:valores.filter(v=>count(v)!==null).length,total:filas.length};}
export function secundariosCRM317(ctx,crm){
 const filas=clientesDia314(ctx,crm?.subcuentas).filter(s=>s.tipo==='cliente').map(s=>crmDia314(s,crm,ctx.hoy));
 const citas={};for(const k of ['agendadas','celebradas','no_presentadas','sin_estado'])citas[k]=sumarObservaciones317(filas,s=>s.citas_30d?.[k]);
 const juzgables=sumarObservaciones317(filas,s=>s.velocidad?.juzgables),en1h=sumarObservaciones317(filas,s=>s.velocidad?.en_1h);
 // Cada pareja usa sólo las mismas subcuentas observadas; no cociente entre totales de distinta cobertura.
 const asistenciaFilas=filas.filter(s=>count(s.citas_30d?.celebradas)!==null&&count(s.citas_30d?.no_presentadas)!==null);
 const sh=asistenciaFilas.reduce((n,s)=>n+s.citas_30d.celebradas,0),ns=asistenciaFilas.reduce((n,s)=>n+s.citas_30d.no_presentadas,0);
 const velocidadFilas=filas.filter(s=>count(s.velocidad?.juzgables)!==null&&count(s.velocidad?.en_1h)!==null&&s.velocidad.en_1h<=s.velocidad.juzgables);
 const j=velocidadFilas.reduce((n,s)=>n+s.velocidad.juzgables,0),e=velocidadFilas.reduce((n,s)=>n+s.velocidad.en_1h,0);
 const personas=ctx.datos?.personas||[],g=new Map();
 for(const s of filas){const ps=personas.filter(p=>p.id===s.especialista_id&&p.estado==='activo'&&p.activo!==false);if(ps.length!==1)continue;const id=ps[0].id;if(!g.has(id))g.set(id,{id,nombre:ps[0].nombre||id,filas:[]});g.get(id).filas.push(s);}
 const especialistas=[...g.values()].map(p=>({...p,subcuentas:p.filas.length,sin_tocar:sumarObservaciones317(p.filas,s=>s.sin_tocar_24h),sin_estado:sumarObservaciones317(p.filas,s=>s.citas_14d?.sin_estado)}));
 return {filas,citas,juzgables,en1h,especialistas,asistencia:sh+ns>0?sh/(sh+ns)*100:null,asistencia_base:sh+ns,asistencia_subcuentas:asistenciaFilas.length,velocidad:j>0?e/j*100:null,velocidad_base:j,velocidad_subcuentas:velocidadFilas.length};
}
export function textoConteo317(m){return m?.valor!==null&&m?.valor!==undefined?`${m.valor} observado${m.valor===1?'':'s'} (${m.observadas}/${m.total} subcuentas con dato)`:'Sin dato';}
export function referenciaAlta317(n){const r=n?.resumen||{};return {carga:count(r.carga_semana),tope:typeof r.carga_tope==='number'&&Number.isFinite(r.carga_tope)&&r.carga_tope>0?r.carga_tope:null,mediana:typeof r.primer_lead_mediana_dias==='number'&&Number.isFinite(r.primer_lead_mediana_dias)&&r.primer_lead_mediana_dias>=0?r.primer_lead_mediana_dias:null};}
