// Movimiento gated: recibos locales no son confirmación de proveedor ni nueva copia.
const ESTADOS = new Set(['simulado','pendiente','enviado','confirmado','fallido','conflicto','descartado']);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export const identidadMovimiento192 = ctx => JSON.stringify([ctx.real?.id || '',ctx.persona?.id || '']);
export function permisoMovimiento192(E,t,resolver) {
  const ctx=E.ctx, no=motivo=>({ok:false,motivo,destinos:[]});
  if(E.vigente && !E.vigente())return no('Esta vista ya no está vigente.');
  if(!ctx.servidor)return no('Movimiento no disponible sin servidor RO.');
  if(ctx.pilotoLectura || ctx.soloLectura || E.V.solo_lectura || !ctx.real?.id || ctx.real.id!==ctx.persona?.id)return no('Consulta de sólo lectura: no se pueden mover tareas.');
  if(!t.coherente || t.lista_id!==E.tableroLista || resolver(t,t.estado).estado!=='verificado')return no('Lista, identidad o estado de la copia por contrastar.');
  if(E.V.capacidad_transicion?.version!=='191.1' || E.V.capacidad_transicion.activo!==true)return no('El servidor no ha habilitado el movimiento durable para esta sesión.');
  const token=E.V.transiciones?.[t.id];
  if(!token || typeof token!=='object' || token.bloqueada!==false || token.lista_id!==t.lista_id || !/^[0-9a-f]{64}$/.test(token.revision || ''))return no('El servidor no ha habilitado esta transición con una revisión vigente.');
  if(token.expected_estado!==t.estado)return no('Hay un estado local distinto de la copia. Revisa Envíos y refresca antes de otro movimiento.');
  const cat=E.V.estados_detalle;
  if(!Array.isArray(cat?.[t.lista_id]))return no('No hay catálogo autorizado actual de esta lista.');
  const destinos=[...new Set(cat[t.lista_id].map(r=>r.estado))].filter(e=>typeof e==='string' && e!==t.estado && resolver(t,e,true).estado==='verificado');
  if(!destinos.length)return no('No hay otro estado exacto verificado en esta lista.');
  return {ok:true,motivo:'Al guardar, se solicitará el cambio en RO; el envío a ClickUp requiere confirmación.',destinos,token:{...token}};
}
export function crearIntentoMovimiento192(E,t,destino,resolver,uuid) {
  const permiso=permisoMovimiento192(E,t,resolver);
  if(!permiso.ok || !permiso.destinos.includes(destino))throw Error(permiso.ok?'El destino no es un estado exacto verificado de esta lista.':permiso.motivo);
  if(!UUID.test(uuid || ''))throw Error('No se pudo generar una intención única.');
  return {identidad:identidadMovimiento192(E.ctx),payload:{herramienta:'clickup',tipo:'cambiar_estado',objeto:t.id,intencion_id:uuid,
    texto:'Cambio de estado desde el tablero',vista_previa:{transicion_tablero:true,lista_id:t.lista_id,expected_estado:t.estado,revision:permiso.token.revision,a:destino}},estado:'preparado',mensaje:'Cambio preparado; todavía no guardado.'};
}
export function validarReciboMovimiento192(r,intento) {
  const p=intento.payload,v=p.vista_previa,ig=r?.intencion_guardada,sc=r?.recibo;
  const no=()=>({valido:false,mensaje:'No se ha acreditado el vínculo con la cola. Revisa Envíos o reintenta la misma intención; la tarjeta conserva su estado.'});
  if(r?.ok!==true || r.recibo_durable!==true || !Number.isInteger(r.id) || r.id<1 || ig?.id!==p.intencion_id || ig.accion_id!==r.id || typeof ig.repetida!=='boolean' || !sc || sc.accion_id!==r.id || !Number.isInteger(sc.cambio_id) || sc.cambio_id<1 || sc.tarea_id!==p.objeto || sc.lista_id!==v.lista_id || sc.desde!==v.expected_estado || sc.hasta!==v.a || sc.intencion_id!==p.intencion_id || !ESTADOS.has(sc.estado_cola) || r.cola_estado!==sc.estado_cola || typeof r.confirmacion_remota!=='boolean' || sc.confirmacion_remota!==r.confirmacion_remota || (r.confirmacion_remota && sc.estado_cola!=='confirmado'))return no();
  const mensajes={simulado:'Guardado en RO · no enviado a ClickUp.',pendiente:'Guardado en RO · pendiente de envío a ClickUp.',enviado:'Enviado · sin confirmación de ClickUp.',confirmado:r.confirmacion_remota?'ClickUp confirmó el cambio; la tarjeta conserva la copia hasta refrescar datos autorizados.':'Estado local confirmado; no hay comprobación remota acreditada.',fallido:'Cambio guardado con fallo · revisa Envíos. La tarjeta conserva su estado.',conflicto:'Cambio guardado con conflicto · revisa Envíos. La tarjeta conserva su estado.',descartado:'Cambio descartado · la tarjeta conserva el estado de la copia.'};
  return {valido:true,estado:sc.estado_cola,mensaje:mensajes[sc.estado_cola],recibo:{...sc}};
}
export async function guardarMovimiento192(E,t,intento,resolver,enviar) {
  const vivo=()=>(!E.vigente || E.vigente()) && identidadMovimiento192(E.ctx)===intento.identidad && E.ctx.servidor && !E.ctx.soloLectura && !E.ctx.pilotoLectura && !E.V.solo_lectura && E.tableroLista===intento.payload.vista_previa.lista_id && (E.D.tareas || []).some(r=>r.id===t.id && r.lista_id===t.lista_id && r.cli===t.cli) && permisoMovimiento192(E,t,resolver).ok;
  if(!vivo())return false;
  // Retry usa el mismo payload. Backend revalida permisos/CAS incluso si token cambió.
  const permiso=permisoMovimiento192(E,t,resolver);
  if(!permiso.ok)throw Error(permiso.motivo);
  if(intento.payload.objeto!==t.id || intento.payload.vista_previa.lista_id!==E.tableroLista)throw Error('La intención pertenece a otra tarea o lista.');
  if(intento.estado==='guardando')return false;
  if(intento.recibo)return false; // Nunca duplicar una intención que ya tiene recibo durable.
  intento.estado='guardando';intento.mensaje='Guardando cambio en RO…';
  try {
    const r=await enviar(intento.payload);
    if(!vivo())return false;
    const recibo=validarReciboMovimiento192(r,intento);
    intento.estado=recibo.valido?'con_recibo':'sin_confirmar';intento.mensaje=recibo.mensaje;
    if(recibo.valido)intento.recibo=recibo.recibo;
  }catch(e){if(!vivo())return false;intento.estado='sin_confirmar';intento.mensaje='No se ha podido confirmar el resultado. Revisa Envíos o reintenta la misma intención; no se ha movido la tarjeta.';}
  return vivo();
}
