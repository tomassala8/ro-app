import { prepararControlCartera } from './control_cartera.js';
const arr = v => Array.isArray(v) ? v : [];
const count = v => Number.isSafeInteger(v) && v >= 0;
// Recibe exclusivamente la proyección vigente autorizada y proyectos preparados con descriptor 137.
export function resumirAccountsProduccion237({ proyectos, clientes, personas, asignaciones, hoy }) {
  const cids = new Map(); for (const c of arr(clientes)) cids.set(c?.id,(cids.get(c?.id)||0)+1);
  const canonicos = arr(clientes).filter(c=>c && cids.get(c.id)===1 && c.activo_confirmado===true && c.detalle);
  const activo = id => {const ps=arr(personas).filter(p=>p?.id===id);return ps.length===1 && ps[0].estado==='activo' && ps[0].activo!==false;};
  const actuales=arr(asignaciones).filter(a=>a && activo(a.persona_id) && ['confirmada','alta'].includes(a.confianza));
  const owners = new Map(prepararControlCartera({ clientes:canonicos,personas,asignaciones:actuales,esOps:true,hoy,fuentes:{} }).map(r=>[r.cliente_id,r]));
  const pidCounts = new Map(); for (const p of arr(proyectos)) pidCounts.set(p?.cliente_id,(pidCounts.get(p?.cliente_id)||0)+1);
  const rows = arr(proyectos).filter(p=>p && owners.has(p.cliente_id) && pidCounts.get(p.cliente_id)===1);
  const grupos = new Map();
  for (const p of rows) {
    const owner=owners.get(p.cliente_id),key=owner.account_id || '__sin';
    if(!grupos.has(key))grupos.set(key,{account_id:owner.account_id,confirmados:0,por_confirmar:0,clientes_ids:[],revisiones_account:[],revisiones_tecnica:[]});
    const g=grupos.get(key);g.clientes_ids.push(p.cliente_id);
    if(owner.account_id)(owner.owner_confirmado?g.confirmados++:g.por_confirmar++);
    for(const tipo of ['account','tecnica']){
      const m=p['_revision_'+tipo];
      if(m && count(m.n) && count(m.mas48) && m.mas48<=m.n)g['revisiones_'+tipo].push(m);
    }
  }
  const sumar = (ms,total) => {
    const n=ms.reduce((s,m)=>s+m.n,0),mas48=ms.reduce((s,m)=>s+m.mas48,0);
    return {observadas:ms.length && count(n)?n:null,mas48:ms.length && count(mas48)?mas48:null,medidos:ms.length,total,
      completo_en_copia:ms.length===total && total>0,fechas:[...new Set(ms.map(m=>m.fecha).filter(Boolean))]};
  };
  return { proyectos:rows,grupos:[...grupos.values()].map(g=>({...g,proyectos:g.clientes_ids.length,
    account:sumar(g.revisiones_account,g.clientes_ids.length),tecnica:sumar(g.revisiones_tecnica,g.clientes_ids.length)})),
    excluidos:arr(proyectos).length-rows.length };
}
export function textoRevisionAccount237(m,edad=false) {
  const valor=edad?m.mas48:m.observadas;
  return {principal:valor===null?'Sin dato':String(valor),cobertura:`${m.medidos}/${m.total} proyectos medidos`,
    detalle:`${m.completo_en_copia?'Todos estos proyectos tienen descriptor':'Suma parcial de proyectos con descriptor'}. Copia parcial del flujo; no acredita inventario completo ni aceptación de entregables.${m.fechas.length?' Fuente: '+m.fechas.join(' · '):''}`};
}
