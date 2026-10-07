import {accountFuego346,firmaAccountFuegos346} from './_account_fuegos_346.js';
const arr=x=>Array.isArray(x)?x:[];
const dia=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
export function ambitoViernes347(ctx) {
  try {
    if(ctx.servidor!==true||!dia(ctx.hoy)||ctx.vigente?.()===false||!ctx.veModulo?.('produccion')||!ctx.veModulo?.('bandeja')||typeof ctx.ver!=='function')return null;
    const ps=arr(ctx.datos?.personas);
    if(![ctx.real,ctx.persona].every(p=>typeof p?.id==='string'&&p.estado==='activo'&&p.activo!==false&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&x.estado==='activo'&&x.activo!==false&&JSON.stringify(arr(x.puestos).slice().sort())===JSON.stringify(arr(p.puestos).slice().sort()))&&arr(p.puestos).some(r=>['account','operaciones','direccion'].includes(r))))return null;
    const cs=arr(ctx.clientesVisibles),propia=arr(ctx.persona.puestos).includes('account')&&!arr(ctx.persona.puestos).some(r=>['operaciones','direccion'].includes(r)),cartera=new Set(ctx.carteraPorSilla?.account||[]);
    const clientes=cs.filter(c=>typeof c?.id==='string'&&cs.filter(x=>x?.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle===true&&(!propia||cartera.has(c.id))&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true);
    const asignaciones=firmaAccountFuegos346(ctx);if(asignaciones===null)return null;
    return {clientes,firma:JSON.stringify([ctx.real,ctx.persona,ctx.hoy,ps,clientes,asignaciones,[...cartera].sort()])};
  } catch { return null; }
}
export function filasViernes347(ctx,filas) {
  const scope=ambitoViernes347(ctx);if(!scope)return {tareas:[],tickets:[]};
  const clientes=new Map(scope.clientes.map(c=>[c.id,c]));
  const proyectar=xs=>arr(xs).filter(r=>clientes.has(r?.cliente_id)).map(r=>{
    const account=accountFuego346(ctx,clientes.get(r.cliente_id));
    return {...r,account_id:account.id,account_texto:account.texto};
  });
  return {tareas:proyectar(filas?.tareas),tickets:proyectar(filas?.tickets)};
}
