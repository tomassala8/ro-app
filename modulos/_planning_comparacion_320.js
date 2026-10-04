import { modeloComparacionSemanal296 } from './_produccion_creadas_287.js';
const arr=v=>Array.isArray(v)?v:[];
const dia=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
export function comparacionCreadores320(ctx,PR){
 const result=new Map();if(!dia(ctx.hoy)||ctx.vigente?.()===false||ctx.veModulo?.('produccion')!==true)return result;
 const lunes=new Date(ctx.hoy+'T00:00:00Z');lunes.setUTCDate(lunes.getUTCDate()-((lunes.getUTCDay()+6)%7));const actual=lunes.toISOString().slice(0,10),anterior=new Date(+lunes-7*864e5).toISOString().slice(0,10);
 const cs=arr(ctx.clientes||ctx.clientesVisibles),ps=arr(ctx.datos?.personas);
 const clientes=cs.filter(c=>cs.filter(x=>x.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle===true&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true);
 const personas=ps.filter(p=>ps.filter(x=>x.id===p.id).length===1&&p.estado==='activo'&&p.activo!==false&&ctx.ver?.({tipo:'horas_persona',persona_id:p.id})?.ok===true);
 const model=modeloComparacionSemanal296({...ctx,clientes,datos:{...ctx.datos,personas}},PR);
 for(const r of model.creadores){const m=r.medicion,scope=m.cliente_ids_scope;
  if(!scope.length||m.ventanas.actual.desde_madrid.slice(0,10)!==actual||m.ventanas.anterior.desde_madrid.slice(0,10)!==anterior||m.ventanas.anterior.hasta_madrid.slice(0,10)!==actual)continue;
  result.set(r.persona_id,{valor:m.creadas.anterior.valor,desde:anterior,hasta_exclusiva:actual,corte:m.corte_utc,detalle:`Creaciones observadas por creador canónico: ${anterior} → ${actual} (fin exclusivo), Europe/Madrid. Copia parcial al ${m.corte_utc}, sólo proyectos autorizados. Sin observaciones no acredita cero; no mide rupturas de planificación ni cierres.`});
 }
 return result;
}
