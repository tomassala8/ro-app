// Una lista recibida se usa sólo mientras permanece el mismo ámbito autorizado.
const arr=x=>Array.isArray(x)?x:[];
export function alcanceAsistente333(ctx){
 if(ctx.servidor!==true||ctx.vigente?.()===false||ctx.veModulo?.('asistente-ia')!==true)return null;
 const ps=arr(ctx.datos?.personas);
 if(![ctx.real,ctx.persona].every(p=>{const xs=ps.filter(x=>x?.id===p?.id);return typeof p?.id==='string'&&xs.length===1&&p.estado==='activo'&&p.activo!==false&&xs[0].estado==='activo'&&xs[0].activo!==false;}))return null;
 try{return JSON.stringify([ctx.real,ctx.persona,ps,arr(ctx.clientesVisibles).map(c=>[c?.id,c?.nombre,c?.activo_confirmado,c?.detalle,ctx.ver?.({tipo:'cliente_detalle',cliente_id:c?.id})?.ok===true])]);}catch{return null;}
}
export function listaAsistente333(ctx,dto){
 if(!alcanceAsistente333(ctx)||!dto||!Array.isArray(dto.copiloto)||!Array.isArray(dto.borradores))return null;
 const cs=arr(ctx.clientesVisibles),cliente=id=>{const xs=cs.filter(c=>c?.id===id);return typeof id==='string'&&xs.length===1&&xs[0].activo_confirmado===true&&xs[0].detalle===true&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:id})?.ok===true?xs[0]:null;};
 const uniq=(rows,key)=>{const counts=new Map();for(const r of rows)counts.set(r?.[key],(counts.get(r?.[key])||0)+1);return rows.filter(r=>typeof r?.[key]==='string'&&r[key].trim()&&counts.get(r[key])===1&&cliente(r.cliente_id));};
 return {...dto,copiloto:uniq(dto.copiloto,'cliente_id').map(c=>({...c,nombre:cliente(c.cliente_id).nombre||c.cliente_id})),borradores:uniq(dto.borradores,'ticket').map(b=>({...b,cliente:cliente(b.cliente_id).nombre||b.cliente_id}))};
}
