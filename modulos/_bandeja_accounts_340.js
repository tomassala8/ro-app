const arr=v=>Array.isArray(v)?v:[];
const fecha=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
export const SIN_ACCOUNT340='__sin_account__';
export function catalogoAccounts340(ctx,ids){
 const personas=arr(ctx.datos?.personas),cs=arr(ctx.clientesVisibles),mapa=Object.create(null),opciones=new Map();
 const vigente=a=>a?.principal===true&&!a.duda&&!a.suplencia&&(!a.desde||(fecha(a.desde)&&a.desde<=ctx.hoy))&&(!a.hasta||(fecha(a.hasta)&&a.hasta>=ctx.hoy));
 for(const cid of arr(ids).filter(x=>typeof x==='string')){
  const clientes=cs.filter(c=>c?.id===cid);let owner=null,confirmado=false;
  if(clientes.length===1&&fecha(ctx.hoy)){
   const fuentes=[arr(ctx.datos?.asignaciones).filter(a=>a?.cliente_id===cid&&a.silla==='account'),arr(clientes[0].equipo?.account)];
   const filas=fuentes.map(xs=>xs.filter(vigente));
   const duplicado=filas.some(xs=>xs.some(a=>xs.filter(b=>b.persona_id===a.persona_id).length>1));
   const candidates=[...new Set(filas.flat().map(a=>a.persona_id))];
   if(!duplicado&&candidates.length===1&&typeof candidates[0]==='string'){
    const ps=personas.filter(p=>p?.id===candidates[0]),xs=filas.flat();
    if(ps.length===1&&ps[0].estado==='activo'&&ps[0].activo!==false&&arr(ps[0].puestos).includes('account')&&xs.every(a=>['confirmada','alta'].includes(a.confianza))){
     owner=ps[0].id;confirmado=xs.some(a=>a.confianza==='confirmada');
     opciones.set(owner,{id:owner,nombre:typeof ps[0].nombre==='string'?ps[0].nombre:owner});
    }
   }
  }
  mapa[cid]={account_id:owner,confirmado};
 }
 const cuentas=[...opciones.values()].sort((a,b)=>a.nombre.localeCompare(b.nombre,'es'));
 return {mapa,cuentas,firma:JSON.stringify([cuentas,arr(ids).slice().sort().map(id=>[id,mapa[id]])])};
}
export function filtrarAccount340(filas,catalogo,account=''){
 return arr(filas).filter(x=>!account||(typeof x?.cliente_id==='string'&&x.cliente_id&&(account===SIN_ACCOUNT340?!catalogo.mapa[x?.cliente_id]?.account_id:catalogo.mapa[x?.cliente_id]?.account_id===account)));
}
export function gruposAccount340(filas,catalogo){
 const grupos=new Map();for(const x of arr(filas)){
  const id=catalogo.mapa[x?.cliente_id]?.account_id||SIN_ACCOUNT340;
  if(!grupos.has(id))grupos.set(id,[]);grupos.get(id).push(x);
 }
 return [...grupos].map(([id,rows])=>({id,rows,nombre:catalogo.cuentas.find(x=>x.id===id)?.nombre||'Sin asignación inequívoca',por_confirmar:rows.some(x=>catalogo.mapa[x?.cliente_id]?.account_id&&catalogo.mapa[x.cliente_id].confirmado!==true)}));
}
