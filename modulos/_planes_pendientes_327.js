// Lectura de planes locales255. Nunca confunde «señal vista» con revisión del plan.
const lista=x=>Array.isArray(x)?x:[];
const fecha=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T12:00:00Z'))&&new Date(x+'T12:00:00Z').toISOString().slice(0,10)===x;
const pendiente=cid=>({cliente_id:cid,estado:'desconocido',texto:'Plan / revisión no comprobados'});
const autorizado=(ctx,cid)=>{const cs=lista(ctx.clientesVisibles).filter(c=>c?.id===cid);return typeof cid==='string'&&/^[\w-]{1,80}$/.test(cid)&&cs.length===1&&cs[0].activo_confirmado===true&&cs[0].detalle===true&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:cid})?.ok===true;};
export function clasificarPlan327(ctx,cid,d){
 const desconocido=pendiente(cid);
 if(!autorizado(ctx,cid)||d?.cliente_id!==cid||d.origen!=='local'||!Number.isInteger(d.version)||d.version<0||!Array.isArray(d.historial)||!d.capacidades)return desconocido;
 const p=d.plan,r=d.revision;
 if(p===null&&r===null&&d.version===0&&d.historial.length===0)return {...desconocido,estado:'sin_plan',texto:'Sin plan local registrado'};
 if(!p||!Number.isInteger(p.version)||p.version<1||p.version>d.version||typeof p.que!=='string'||p.que.trim().length<3||typeof p.responsable_id!=='string'||!p.responsable_id||!fecha(p.plazo))return desconocido;
 if(r===null)return {...desconocido,estado:'sin_revision',texto:`Plan versión ${p.version} · pendiente de revisión`};
 const revisor=lista(ctx.datos?.personas).filter(x=>x?.id==='constanza');
 if(!r||r.plan_version!==p.version||!Number.isInteger(r.version)||r.version<=p.version||r.version>d.version||r.actor_id!=='constanza'||revisor.length!==1||revisor[0].estado!=='activo'||revisor[0].activo===false||!lista(revisor[0].puestos).includes('proyectos')||!['visto','pedir_cambios'].includes(r.estado))return desconocido;
 return {...desconocido,estado:r.estado==='visto'?'visto':'cambios',texto:r.estado==='visto'?`Visto de Coti · versión ${p.version}`:`Cambios pedidos · versión ${p.version}`};
}
export async function leerPlanes327(ctx,rojos,vigente){
 const cuentas=new Map();for(const r of lista(rojos))if(typeof r?.cliente_id==='string')cuentas.set(r.cliente_id,(cuentas.get(r.cliente_id)||0)+1);
 const ids=[...cuentas].filter(([cid,n])=>n===1&&autorizado(ctx,cid)).map(([cid])=>cid);
 const firma=()=>JSON.stringify([ctx.real?.id,ctx.persona?.id,ctx.veModulo?.('en-rojo'),ids.map(cid=>[cid,autorizado(ctx,cid)]),lista(ctx.datos?.personas).map(p=>[p?.id,p?.estado,p?.activo,p?.puestos])]);
 const inicial=firma(),vivo=()=>vigente()&&firma()===inicial;
 if(!vivo())return null;
 if(ctx.servidor!==true||!ctx.veModulo?.('en-rojo')||typeof ctx.api!=='function')return ids.map(pendiente);
 const resultados=await Promise.all(ids.map(async cid=>{try{if(!vivo())return pendiente(cid);const d=await ctx.api(`en-rojo/planes?cliente_id=${encodeURIComponent(cid)}`);return vivo()?clasificarPlan327(ctx,cid,d):pendiente(cid);}catch{return pendiente(cid);}}));
 return vivo()?resultados:null;
}
