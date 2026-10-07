import { textoDetalle197 } from './_detalle_tarea_197.js';
// Contrato de revisión conectado a Producción por 211 y al endpoint local 208.
// Este helper valida intenciones y recibos; no llama proveedores ni acredita aceptación de entregables.
const TIPOS206=new Set(['pieza_aprobar','pieza_pedir_cambios','mover_estado']);
const TIPOS_CATALOGO206=new Set(['open','unstarted','custom','done','closed']);
const COLAS206=new Set(['simulado','pendiente','enviado','confirmado','fallido','conflicto','descartado']);
const UUID206=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export function prepararRevisionProduccion206(ctx,t,tipo,capacidad,token,catalogo) {
  const no=motivo=>({ok:false,motivo});
  if(!ctx?.servidor||ctx.soloLectura||ctx.pilotoLectura||!ctx.real?.id||ctx.real.id!==ctx.persona?.id)return no('Sesión de consulta: no permite guardar esta revisión.');
  if(ctx.vigente && !ctx.vigente())return no('Esta pantalla ya no está vigente.');
  if(ctx.veModulo?.('produccion')!==true)return no('No se confirmó acceso a Producción.');
  if(!TIPOS206.has(tipo)||!t?.id||!t.cli||!t.lista_id||typeof t.estado!=='string')return no('Identidad de pieza, cliente, lista o estado incompletos.');
  if(capacidad?.version!=='206.1'||capacidad.activo!==true)return no('La revisión durable de Producción aún no está habilitada.');
  const accion=token?.acciones?.[tipo];
  if(token?.modulo!=='produccion'||token.tarea_id!==t.id||token.cliente_id!==t.cli||token.lista_id!==t.lista_id||token.expected_estado!==t.estado||!/^[0-9a-f]{64}$/.test(token.revision||'')||token.bloqueada!==false||accion?.autorizacion_confirmada!==true)return no('No hay permiso de revisión ni copia vigente confirmados por el servidor.');
  const filas=Array.isArray(catalogo?.[t.lista_id])?catalogo[t.lista_id]:[];
  const actual=filas.filter(r=>r?.estado===t.estado),destino=filas.filter(r=>r?.estado===accion.destino);
  if(actual.length!==1||destino.length!==1||!TIPOS_CATALOGO206.has(actual[0].tipo)||!TIPOS_CATALOGO206.has(destino[0].tipo)||actual[0].tipo!==t.tipo_estado||accion.destino===t.estado)return no('Origen o destino no son estados únicos tipados de esta lista.');
  return {ok:true,tipo,destino:accion.destino,revision:token.revision,modulo:'produccion'};
}
export function crearIntencionRevision206(ctx,t,permiso,uuid,comentario='') {
  if(!permiso?.ok||permiso.modulo!=='produccion'||!TIPOS206.has(permiso.tipo)||!UUID206.test(uuid||''))throw Error('No hay revisión habilitada ni intención única.');
  const limpio=textoDetalle197(comentario,2000).trim();
  if(permiso.tipo==='pieza_pedir_cambios' && (typeof comentario!=='string'||comentario.length>2000||limpio.length<3))throw Error('Explica los cambios en un texto de 3 a 2.000 caracteres.');
  return {identidad:JSON.stringify([ctx.real.id,ctx.persona.id]),payload:{modulo:'produccion',herramienta:'clickup',tipo:permiso.tipo,objeto:t.id,intencion_id:uuid,
    texto:permiso.tipo==='pieza_pedir_cambios'?limpio:'Transición de revisión desde Producción',vista_previa:{transicion_produccion:true,lista_id:t.lista_id,expected_estado:t.estado,revision:permiso.revision,a:permiso.destino,...(permiso.tipo==='pieza_pedir_cambios'?{comentario:limpio}:{})}}};
}
export function validarReciboRevision206(r,intento) {
  const p=intento?.payload,v=p?.vista_previa,s=r?.recibo,ig=r?.intencion_guardada;
  if(!p||r?.ok!==true||r.recibo_durable!==true||!Number.isInteger(r.id)||r.id<1||ig?.id!==p.intencion_id||ig.accion_id!==r.id||typeof ig.repetida!=='boolean'||s?.accion_id!==r.id||!Number.isInteger(s.cambio_id)||s.cambio_id<1||s.tipo!==p.tipo||s.modulo!=='produccion'||s.tarea_id!==p.objeto||s.lista_id!==v.lista_id||s.desde!==v.expected_estado||s.hasta!==v.a||s.intencion_id!==p.intencion_id||!COLAS206.has(s.estado_cola)||r.cola_estado!==s.estado_cola||typeof s.confirmacion_remota!=='boolean'||r.confirmacion_remota!==s.confirmacion_remota||(s.confirmacion_remota&&s.estado_cola!=='confirmado'))return {valido:false,motivo:'No se acreditó vínculo durable con la cola de esta revisión.'};
  return {valido:true,estado:s.estado_cola,confirmacion_remota:s.confirmacion_remota,aceptacion_entregable:null};
}
