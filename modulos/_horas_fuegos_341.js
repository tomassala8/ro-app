import {horasProyectoRango262,pautaProyectoRango262} from './_operaciones_equipo_262.js';
const arr=x=>Array.isArray(x)?x:[];
export function ambitoFuegos341(ctx){
 try{
  if(ctx.servidor!==true||ctx.vigente?.()===false||ctx.veModulo?.('en-rojo')!==true)return null;
  const ps=arr(ctx.datos?.personas);
  if(![ctx.real,ctx.persona].every(p=>typeof p?.id==='string'&&p.estado==='activo'&&p.activo!==false&&ps.filter(x=>x?.id===p.id).length===1&&ps.find(x=>x?.id===p.id)?.estado==='activo'&&ps.find(x=>x?.id===p.id)?.activo!==false&&JSON.stringify(arr(p.puestos).slice().sort())===JSON.stringify(arr(ps.find(x=>x?.id===p.id)?.puestos).slice().sort())))return null;
  const cs=arr(ctx.clientesVisibles),clientes=cs.filter(c=>typeof c?.id==='string'&&cs.filter(x=>x?.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle===true&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true);
  const pautas=ctx.real.id===ctx.persona.id&&ctx.veModulo?.('dinero-cliente')===true?clientes.filter(c=>ctx.ver?.({tipo:'horas_pautadas',cliente_id:c.id})?.ok===true).map(c=>c.id).sort():[];
  return {clientes,pautas,firma:JSON.stringify([ctx.real,ctx.persona,ps,ctx.hoy,clientes,pautas,['en-rojo','produccion','captacion','dinero-cliente'].map(m=>[m,ctx.veModulo?.(m)===true])])};
 }catch{return null;}
}
export function horasFuego341(ctx,P,doc,cid){
 const a=ambitoFuegos341(ctx);if(!a||!a.clientes.some(c=>c.id===cid)||ctx.veModulo?.('produccion')!==true)return null;
 const xs=arr(P?.proyectos).filter(p=>p?.cliente_id===cid);if(xs.length!==1)return null;
 const r={desde:ctx.hoy?.slice(0,7)+'-01',hasta:P?.hoy};
 const m=horasProyectoRango262(xs[0],P,r,ctx.hoy);
 if(m.valor===null||m.valor===undefined)return null;
 const pauta=a.pautas.includes(cid)?pautaProyectoRango262(ctx,doc,cid,r,m):null;
 const pct=pauta?.porcentaje;
 return {horas:m.valor,periodo:m.periodo,fecha:m.fecha,fuente:m.fuente,porcentaje:typeof pct==='number'&&Number.isFinite(pct)&&pct>=0?pct:null,
  estado:typeof pct==='number'&&Number.isFinite(pct)&&pct>130?'rojo':'gris',
  detalle:`${m.valor} h observadas. ${m.detalle} ${pauta?`Referencia mensual ${pauta.periodo}: ${pauta.horas} h. Numerador parcial / referencia mensual; no presupuesto aprobado ni cumplimiento. Umbral original >130% sólo señala exceso sobre esa referencia.`:'Sin pauta mensual autorizada y compatible; porcentaje pendiente. No se deduce consumo bajo ni cumplimiento.'}`};
}
