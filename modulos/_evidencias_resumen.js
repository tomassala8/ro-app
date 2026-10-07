// 157: proyección neutral de declaraciones; no permisos nuevos ni cálculo de cumplimiento.
const ID = /^[A-Za-z0-9_-]{1,80}$/;
const CAMPOS = new Set(['cliente_id','contactos_declarados','reuniones_declaradas','source_kind','verificacion_externa','cumplimiento']);
const entero = n => Number.isSafeInteger(n) && n >= 0;
const objeto = v => !!v && typeof v === 'object' && !Array.isArray(v);
function lunes(v) {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return false;
  const d = new Date(`${v}T12:00:00Z`);
  return Number.isFinite(d.valueOf()) && d.toISOString().slice(0,10) === v && d.getUTCDay() === 1;
}
function mismaIdentidad(a,b) {
  return objeto(a) && objeto(b) && typeof a.real_id === 'string' && ID.test(a.real_id)
    && typeof a.vista_id === 'string' && ID.test(a.vista_id)
    && Number.isSafeInteger(a.generacion) && a.generacion >= 0
    && a.real_id === b.real_id && a.vista_id === b.vista_id && a.generacion === b.generacion;
}
function desconocido(cid,motivo) {
  return {cliente_id:cid,estado:'sin_dato',color:'gris',contactos_declarados:null,reuniones_declaradas:null,
    contacto_texto:'Sin dato',reunion_texto:'Sin dato',actividad:'desconocida',cumplimiento:null,
    verificacion_externa:false,motivo};
}
/** Scope debe proceder de la matriz ya autorizada, nunca del payload del resumen.
 * generacion cambia al cambiar identidad/cartera/permisos; vigente incluye guard de ruta.
 * No hace fetch ni guarda una copia anterior en errores.
 */
export function prepararResumenEvidencias({respuesta,semana_inicio,cliente_ids,identidad,identidad_actual,vigente}) {
  if (!Array.isArray(cliente_ids) || cliente_ids.some(id=>typeof id!=='string'||!ID.test(id)) || new Set(cliente_ids).size!==cliente_ids.length)
    return {estado:'sin_dato',filas:[],motivo:'Ámbito incoherente.'};
  const fallo = motivo => ({estado:'sin_dato',semana_inicio,filas:cliente_ids.map(cid=>desconocido(cid,motivo)),motivo});
  if (vigente !== true || !mismaIdentidad(identidad,identidad_actual)) return fallo('La identidad, los permisos o la pantalla han cambiado.');
  if (!lunes(semana_inicio) || !objeto(respuesta) || respuesta.semana_inicio !== semana_inicio
      || respuesta.cobertura !== 'parcial' || respuesta.verificacion_externa !== false || respuesta.cumplimiento !== null
      || !Array.isArray(respuesta.clientes)) return fallo('Resumen ausente o periodo/cobertura no contrastados.');
  const scope = new Set(cliente_ids), porCliente = new Map();
  for (const r of respuesta.clientes) {
    if (!objeto(r) || Object.keys(r).some(k=>!CAMPOS.has(k)) || !scope.has(r.cliente_id) || porCliente.has(r.cliente_id)
        || r.source_kind !== 'registro_equipo' || r.verificacion_externa !== false || r.cumplimiento !== null
        || !entero(r.contactos_declarados) || !entero(r.reuniones_declaradas)) return fallo('Resumen incoherente, ajeno o duplicado.');
    porCliente.set(r.cliente_id,r);
  }
  const filas = cliente_ids.map(cid => {
    const r = porCliente.get(cid);
    if (!r) return desconocido(cid,'El cliente no tiene fila autorizada en este resumen.');
    return {cliente_id:cid,estado:'declarado',color:'gris',contactos_declarados:r.contactos_declarados,
      reuniones_declaradas:r.reuniones_declaradas,contacto_texto:`${r.contactos_declarados} contacto${r.contactos_declarados===1?'':'s'} declarado${r.contactos_declarados===1?'':'s'}`,
      reunion_texto:`${r.reuniones_declaradas} ${r.reuniones_declaradas===1?'reunión declarada':'reuniones declaradas'}`,
      source_kind:'registro_equipo',actividad:'desconocida',verificacion_externa:false,cumplimiento:null,
      motivo:'Declaraciones vigentes del equipo en esta semana. Cero no significa ausencia de actividad; no verifica cumplimiento.'};
  });
  return {estado:filas.every(f=>f.estado==='declarado')?'declarado':'parcial',semana_inicio,filas,cobertura:'parcial',cumplimiento:null};
}
