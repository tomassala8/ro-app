import {paginasSEO,fechaSEO} from './_seo_mediciones.js';
// Sólo filas del DTO autorizado; ninguna lectura/proveedor ni taxonomía inferida.
export function ambitoOportunidades332(ctx){
 try{
  if(ctx.servidor!==true||ctx.veModulo?.('seo-web')!==true||typeof ctx.ver!=='function'||ctx.vigente&& !ctx.vigente())return null;
  const ps=Array.isArray(ctx.datos?.personas)?ctx.datos.personas:[];
  if(![ctx.real,ctx.persona].every(p=>p?.estado==='activo'&&p.activo!==false&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&x.estado==='activo'&&x.activo!==false)))return null;
  const cs=Array.isArray(ctx.clientesVisibles)?ctx.clientesVisibles:[];
  const ids=cs.filter(c=>typeof c?.id==='string'&&cs.filter(x=>x?.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle===true&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
  return {ids,firma:JSON.stringify([ctx.real,ctx.persona,ps,ids,ctx.hoy])};
 }catch{return null;}
}
export function oportunidadPagina332(f,meta,ctx){
 const scope=ambitoOportunidades332(ctx);
 if(!scope||typeof f?.cliente_id!=='string'||!scope.ids.includes(f.cliente_id))return null;
 const m=paginasSEO(f,meta,ctx.hoy),v=m.ventana;
 if(!m.medido||!v||Date.parse(v.hasta+'T00:00:00Z')-Date.parse(v.desde+'T00:00:00Z')!==27*864e5||f.clics?.hasta!==v.hasta||fechaSEO(m.lectura)<v.hasta)return null;
 const cuentas=new Map();for(const r of m.filas)cuentas.set(r.url,(cuentas.get(r.url)||0)+1);
 const rows=m.filas.filter(r=>cuentas.get(r.url)===1&&r.enlace&&r.clics!==null&&r.impresiones!==null&&r.clics<=r.impresiones&&(r.perdidos>0||r.impresiones>0)).filter(r=>{
   try{const u=new URL(r.enlace);return !u.search&&!u.hash&&!u.username&&!u.password&&!/@|(?:password|contrase[ñn]a|token|secret|api[_-]?key)/i.test(decodeURIComponent(u.pathname));}catch{return false;}
 });
 const score=r=>r.perdidos>0?0:r.impresiones>0&&r.clics===0?1:2;
 rows.sort((a,b)=>score(a)-score(b)||(b.perdidos||0)-(a.perdidos||0)||b.impresiones-a.impresiones||a.url.localeCompare(b.url));
 const r=rows[0];if(!r)return null;
 const u=new URL(r.enlace),tipo=score(r)===0?'descenso':score(r)===1?'impresiones_sin_clics':'exposicion';
 return {cliente_id:f.cliente_id,url:r.enlace,ruta:u.pathname||'/',tipo,
   clics:r.clics,impresiones:r.impresiones,anterior:r.anterior,perdidos:r.perdidos,
   accion:tipo==='descenso'?`Revisar pérdida observada: ${r.perdidos} clics menos.`:tipo==='impresiones_sin_clics'?'Revisar consultas y título: impresiones sin clics.':'Revisar consultas de la página con más impresiones.',
   ventana:v,lectura:m.lectura,cobertura:'parcial',scope_firma:scope.firma,
   ir:`seo-web/${encodeURIComponent(f.cliente_id)}/clics`,
   nota:'Muestra parcial de Search Console; no acredita causa, posición puntual, Maps, publicación ni ventas.'};
}
