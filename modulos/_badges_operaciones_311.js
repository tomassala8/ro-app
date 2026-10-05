// Contadores de navegación: mínimos de copias autorizadas, nunca salud/cumplimiento.
export const CONTADORES_ORIGINALES311=['dia','produccion','bandeja','fuegos','hoy','clientes','fichas','accounts','nuevos','viernes','incongruencias','tomas','rastro'];
const array=v=>Array.isArray(v)?v:[];
const dia=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T12:00:00Z'))&&new Date(v+'T12:00:00Z').toISOString().slice(0,10)===v;
const fecha=(v,hoy)=>typeof v==='string'&&dia(v.slice(0,10))&&v.slice(0,10)<=hoy&&Number.isFinite(Date.parse(v.replace(' ','T')))?v:null;
const actores=ctx=>[ctx.real,ctx.persona].every(p=>typeof p?.id==='string'&&p.id&&p.estado==='activo'&&p.activo!==false);
const unico=(rs,key)=>{const xs=array(rs),n=new Map();for(const x of xs)if(typeof x?.[key]==='string'&&x[key])n.set(x[key],(n.get(x[key])||0)+1);return xs.filter(x=>typeof x?.[key]==='string'&&n.get(x[key])===1);};
export function ambitoBadges311(ctx){
 const cs=Array.isArray(ctx.clientesVisibles)?ctx.clientesVisibles:ctx.clientes;
 const ids=(actores(ctx)?unico(array(cs),'id'):[]).filter(c=>c.activo_confirmado===true&&c.detalle!==false&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
 return {ids,firma:JSON.stringify([ctx.real?.id,ctx.persona?.id,ctx.real?.estado,ctx.persona?.estado,ctx.real?.activo,ctx.persona?.activo,ctx.real?.puestos,ctx.persona?.puestos,ctx.hoy,ids,['mi-dia','ficha','clientes-nuevos','produccion','alertas','en-rojo'].map(m=>ctx.veModulo?.(m)===true)] )};
}
const vacio=detalle=>({texto:'—',valor:null,estado:'gris',detalle});
const minimo=(n,detalle)=>Number.isSafeInteger(n)&&n>0?{texto:'≥'+n,valor:n,estado:'gris',detalle}:vacio(detalle+' Sin observaciones no acredita cero pendientes.');
export function contadoresOperaciones311(ctx,docs={}){
 const out=Object.fromEntries(CONTADORES_ORIGINALES311.map(k=>[k,vacio('Contador original pendiente de fuente y cobertura compatibles. No equivale a cero.') ]));
 if(!dia(ctx.hoy)||!actores(ctx))return out;
 const scope=new Set(ambitoBadges311(ctx).ids),actuales=array(ctx.clientesVisibles||ctx.clientes).filter(c=>scope.has(c?.id));
 if(ctx.veModulo?.('mi-dia')===true)out.clientes=actuales.length?{texto:String(actuales.length),valor:actuales.length,estado:'gris',detalle:'Clientes ACT únicos con detalle permitido en el ámbito actual; inventario autorizado, no pendientes ni cumplimiento.'}:vacio('Sin clientes ACT acreditados en este ámbito; no se afirma cero global.');
 if(ctx.veModulo?.('ficha')===true&&fecha(docs.portal?._meta?.generado||docs.portal?.generado,ctx.hoy)&&Array.isArray(docs.portal?.filas))out.fichas=minimo(unico(docs.portal.filas,'cliente_id').filter(x=>scope.has(x.cliente_id)).length,`Fichas con fila única · lectura ${docs.portal?._meta?.generado||docs.portal.generado}. Ámbito ACT autorizado, copia parcial; no mide trabajo pendiente.`);
 if(ctx.veModulo?.('clientes-nuevos')===true&&docs.nuevos?.hoy===ctx.hoy&&fecha(docs.nuevos?.generado,ctx.hoy)&&Array.isArray(docs.nuevos?.altas))out.nuevos=minimo(unico(docs.nuevos.altas,'cliente_id').filter(x=>scope.has(x.cliente_id)&&dia(x.alta)&&x.alta<=ctx.hoy&&(Date.parse(ctx.hoy+'T12:00Z')-Date.parse(x.alta+'T12:00Z'))/864e5<=90).length,`Altas observadas en primeros90d · corte ${docs.nuevos.generado}. No acredita completitud de onboarding ni hitos.`);
 if(ctx.veModulo?.('mi-dia')===true){
  const personas=unico(array(ctx.datos?.personas),'id'),owners=new Set();
  for(const c of actuales){const candidatos=array(c.equipo?.account).filter(a=>a?.principal===true&&!a.duda&&!a.suplencia&&['confirmada','alta'].includes(a.confianza)&&(!a.desde||(dia(a.desde)&&a.desde<=ctx.hoy))&&(!a.hasta||(dia(a.hasta)&&a.hasta>=ctx.hoy))&&personas.some(p=>p.id===a.persona_id&&p.estado==='activo'&&p.activo!==false));const ids=[...new Set(candidatos.map(a=>a.persona_id))];if(ids.length===1)owners.add(ids[0]);}
  out.accounts=minimo(owners.size,'Responsables Account registrados en proyectos ACT autorizados; asignación alta puede estar por confirmar. IDs únicos/personas activas; no cumplimiento ni todo el equipo.');
 }
 const alarmas=ctx.datos?.alarmas,sello=fecha(ctx.datos?.meta?.construido,ctx.hoy);
 if(ctx.veModulo?.('en-rojo')===true&&sello&&typeof ctx.verdad==='function'){
  out.fuegos=vacio('Urgencias actuales pendientes de lectura conjunta. La gravedad roja del cliente no cuenta como fuego.');
 }
 if(ctx.veModulo?.('alertas')===true&&sello&&Array.isArray(alarmas))out.hoy=minimo(unico(alarmas,'id').filter(a=>a.gravedad==='rojo'&&scope.has(a.cliente_id)).length,`Alarmas de cliente en rojo registradas · fuente núcleo ${sello}. Sólo IDs únicos de clientes ACT autorizados; cobertura parcial, no todas las alarmas del equipo.`);
 const P=docs.produccion,fp=fecha(P?.fuentes?.tareas?.hora,ctx.hoy);
 if(ctx.veModulo?.('produccion')===true&&fp&&P?.hoy===ctx.hoy&&Array.isArray(P.revisiones)){
  const rs=unico(P.revisiones,'id').filter(r=>scope.has(r.cliente_id)&&r.estado_determinado===true&&['account','tecnica'].includes(r.revisa)&&r.mas48===true&&typeof r.dias==='number'&&Number.isFinite(r.dias)&&r.dias>2);
  out.produccion=minimo(rs.length,`Revisiones Account/técnica+48h observadas con estado determinado · copia ${fp}. Edades acreditadas por fila; cobertura parcial, no se mezclan stocks nuevos con edad antigua.`);
 }
 return out;
}
export function iniciarBadges311(ctx,{vigente,pintar}){
 const docs={},antes=ambitoBadges311(ctx).firma;
 const vivo=()=>vigente()&&(!ctx.vigente||ctx.vigente())&&ambitoBadges311(ctx).firma===antes;
 const actualizar=()=>{if(vivo())pintar(contadoresOperaciones311(ctx,docs));else pintar({});};
 actualizar();
 const trabajos=(ctx.servidor===true&&actores(ctx)?[['ficha','ficha/portal','portal'],['clientes-nuevos','nuevos/nuevos','nuevos'],['produccion','produccion/produccion','produccion']]:[]).filter(([m])=>ctx.veModulo?.(m)===true);
 let indice=0;
 const trabajador=async()=>{while(vivo()&&indice<trabajos.length){const [m,ruta,key]=trabajos[indice++];try{const d=await ctx.datosModulo(ruta);if(!vivo()||ctx.veModulo?.(m)!==true){actualizar();return;}docs[key]=d;actualizar();}catch{if(vivo())actualizar();}}};
 const promesa=Promise.all([trabajador(),trabajador()]);
 return {promesa,actualizar};
}
