// 612: informes declarados por mes de informe. No verifica envío ni cumplimiento.
const arr = x => Array.isArray(x) ? x : [];
const objeto = x => !!x && typeof x === 'object' && !Array.isArray(x);
const id = x => typeof x === 'string' && /^[A-Za-z0-9_-]{1,150}$/.test(x);
const periodo = x => typeof x === 'string' && /^\d{4}-(0[1-9]|1[0-2])$/.test(x);
const activo = p => p?.estado === 'activo' && p.activo !== false;
const roles = (a,b) => Array.isArray(a) && Array.isArray(b) && a.length > 0 && a.every(id) && b.every(id)
  && new Set(a).size === a.length && new Set(b).size === b.length && JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
const contextos = new WeakMap();
/** Firma previa a GET. Caller añade vigente:()=>boolean que incluye ruta/epoch/mes seleccionado.
 * ctx.ver/veModulo reflejan vista; GET611 aplica real∩vista. Ambos actores/catálogos se revalidan aquí.
 */
export function ambitoResumenInformes612(ctx, mes) { try {
  if (!periodo(mes) || ctx.servidor !== true || typeof ctx.vigente !== 'function' || !ctx.vigente()
      || ctx.veModulo?.('mi-trabajo') !== true || typeof ctx.ver !== 'function') return null;
  const ps=arr(ctx.datos?.personas), actors=[ctx.real,ctx.persona];
  for (const p of actors) {
    const rows=ps.filter(x=>x?.id===p?.id);
    if (!id(p?.id) || !activo(p) || rows.length!==1 || !activo(rows[0]) || !roles(p.puestos,rows[0].puestos)) return null;
  }
  const cs=arr(ctx.clientes), vis=arr(ctx.clientesVisibles);
  if (cs.some(c=>!id(c?.id)) || vis.some(c=>!id(c?.id))) return null;
  const counts = rows => new Map(rows.map(c=>[c.id,rows.filter(x=>x.id===c.id).length]));
  const ac=counts(cs), vc=counts(vis), grants=[];
  const ids=cs.filter(c=>ac.get(c.id)===1 && vc.get(c.id)===1 && c.activo_confirmado===true && c.activo!==false && c.estado!=='baja' && c.detalle===true
    && vis.find(x=>x.id===c.id).activo_confirmado===true && vis.find(x=>x.id===c.id).activo!==false && vis.find(x=>x.id===c.id).estado!=='baja' && vis.find(x=>x.id===c.id).detalle===true
    && ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
  for (const c of cs) grants.push([c.id,ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})]);
  return {ids,periodo:mes,firma:JSON.stringify([actors,ps,cs,vis,grants,ctx.hoy,mes,ctx.veModulo('mi-trabajo')])};
} catch { return null; } }
function vigente(ctx, scope) { try {
  const actual=ambitoResumenInformes612(ctx,scope?.periodo);
  return typeof scope?.vigente==='function' && scope.vigente()===true && actual && actual.firma===scope.firma
    && Array.isArray(scope.ids) && scope.ids.every(id) && new Set(scope.ids).size===scope.ids.length
    && scope.ids.every(cid=>actual.ids.includes(cid));
} catch { return false; } }
const CAMPOS = new Set(['cliente_id','informes_declarados','source_kind','verificacion_externa','cumplimiento']);
const NOTA = 'Declaraciones activas por mes del informe, no por fecha de envío. Cero no acredita ausencia de envío ni cumplimiento; no hay verificación externa.';
const TOP = new Set(['nota','version','periodo_informe','clientes','source_kind','verificacion_externa','cumplimiento','cobertura']);
export function proyectarResumenInformes612(ctx, respuesta, scope) {
  if (!vigente(ctx,scope) || !objeto(respuesta) || Object.keys(respuesta).some(k=>!TOP.has(k))
      || respuesta.nota!==NOTA || respuesta.version!=='611.1' || respuesta.periodo_informe!==scope.periodo || respuesta.cobertura!=='parcial'
      || !Array.isArray(respuesta.clientes)) return null;
  for (const [k,v] of [['source_kind','registro_equipo'],['verificacion_externa',false],['cumplimiento',null]])
    if (respuesta[k]!==v) return null;
  const filas=new Map();
  for (const r of respuesta.clientes) {
    if (!objeto(r) || Object.keys(r).some(k=>!CAMPOS.has(k)) || !scope.ids.includes(r.cliente_id) || filas.has(r.cliente_id)
        || !Number.isSafeInteger(r.informes_declarados) || r.informes_declarados<0 || r.source_kind!=='registro_equipo'
        || r.verificacion_externa!==false || r.cumplimiento!==null) return null;
    filas.set(r.cliente_id,r.informes_declarados);
  }
  if (!vigente(ctx,scope)) return null;
  const modelo={periodo_informe:scope.periodo,estado:'declarado',cobertura:'parcial',cumplimiento:null};
  contextos.set(modelo,{ctx,scope:{...scope,ids:[...scope.ids]},filas});
  return modelo;
}
/** Callback consumidor debe comprobar celda.vigente() antes de abrir detalle/pintar. */
export function celdaInformeDeclarado612(modelo,cid) {
  const estado=contextos.get(modelo);
  const valida=()=>!!estado && vigente(estado.ctx,estado.scope) && estado.scope.ids.includes(cid);
  const detalle=`Informes declarados para ${estado?.scope.periodo||'mes desconocido'} (mes del informe, no mes de envío). Registro del equipo, cobertura parcial; no verifica envío, cumplimiento, Score ni responsable histórico. Cero sólo significa cero declaraciones explícitas en este registro.`;
  const n=valida()?estado.filas.get(cid):undefined;
  return {valor:Number.isSafeInteger(n)?`${n} decl.`:'—',estado:'gris',informes_declarados:Number.isSafeInteger(n)?n:null,
    detalle:Number.isSafeInteger(n)?detalle:'Sin fila válida autorizada para el mes del informe; no acredita ausencia de informes ni envío. '+detalle,
    vigente:valida};
}

/** 615: suma sólo filas explícitas. n/N expresa cobertura, nunca cumplimiento. */
export function agregarInformesDeclarados615(modelo, ids) {
  const estado=contextos.get(modelo);
  const seleccion=Array.isArray(ids)?[...ids]:null;
  const identidadValida=!!seleccion && seleccion.length>0 && seleccion.every(id) && new Set(seleccion).size===seleccion.length;
  const valida=()=>identidadValida && seleccion.every(cid=>celdaInformeDeclarado612(modelo,cid).vigente()===true);
  const mes=estado?.scope.periodo||'mes desconocido';
  const leyenda=`Informes declarados para ${mes} (mes del informe, no mes de envío). Registro del equipo, cobertura parcial; no verifica envío, cumplimiento ni Score, y no atribuye responsable histórico.`;
  const desconocido=(observados=null,total=null,motivo='Ámbito, fuente o suma no válidos.')=>({
    valor:'—',estado:'gris',informes_declarados:null,cobertura:{observados,total,parcial:true},
    detalle:`${motivo} ${leyenda}`,vigente:valida,
  });
  if (!valida()) return desconocido();
  let suma=0, observados=0;
  for (const cid of seleccion) {
    const celda=celdaInformeDeclarado612(modelo,cid),n=celda.informes_declarados;
    if (!celda.vigente()) return desconocido();
    if (n===null) continue;
    if (!Number.isSafeInteger(n)||n<0||!Number.isSafeInteger(suma+n)) return desconocido(null,seleccion.length,'Suma de declaraciones no representable con seguridad.');
    suma+=n;observados++;
  }
  if (!valida()) return desconocido();
  if (!observados) return desconocido(0,seleccion.length,`0/${seleccion.length} filas con declaración explícita; las filas ausentes no significan cero informes.`);
  return {valor:`${suma} decl.`,estado:'gris',informes_declarados:suma,
    cobertura:{observados,total:seleccion.length,parcial:true},
    detalle:`${leyenda} ${observados}/${seleccion.length} filas explícitas observadas. La suma sólo incluye esas filas; las ausentes son desconocidas. Cero significa cero declaraciones en las filas explícitas, no ausencia de envío.`,
    vigente:valida};
}
