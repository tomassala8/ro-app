// Pedidos declarados al receptor histórico. No mide contactos ni ejecución.
const arr=x=>Array.isArray(x)?x:[];
const activo=p=>p?.estado==='activo'&&p.activo!==false;
const id=x=>typeof x==='string'&&/^[a-zA-Z0-9_-]{1,200}$/.test(x);
const dia=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
const roles=(a,b)=>Array.isArray(a)&&Array.isArray(b)&&a.length>0&&a.every(id)&&b.every(id)&&new Set(a).size===a.length&&new Set(b).size===b.length&&JSON.stringify([...a].sort())===JSON.stringify([...b].sort());
const instant=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:0\d|1[0-4]):[0-5]\d)$/.test(x)&&dia(x.slice(0,10))&&Number.isFinite(Date.parse(x))&&+x.slice(11,13)<24&&+x.slice(14,16)<60&&+x.slice(17,19)<60;
const madrid=x=>{const ps=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(x));return ['year','month','day'].map(k=>ps.find(p=>p.type===k).value).join('-');};
export function semanaPedidos344(hoy){if(!dia(hoy))return null;const d=new Date(hoy+'T12:00Z');d.setUTCDate(d.getUTCDate()-(d.getUTCDay()+6)%7);return d.toISOString().slice(0,10);}
export function ambitoPedidos344(ctx){try{
 const ps=arr(ctx.datos?.personas),actores=[ctx.real,ctx.persona];
 if(!ctx.servidor||!dia(ctx.hoy)||!ctx.veModulo?.('bandeja')||typeof ctx.ver!=='function'||!actores.every(p=>id(p?.id)&&activo(p)&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&activo(x)&&roles(p.puestos,x.puestos))))return null;
 const permitidos=['account','operaciones','direccion'];if(!actores.every(p=>p.puestos.some(r=>permitidos.includes(r))))return null;
 const propia=ctx.persona.puestos.includes('account')&&!ctx.persona.puestos.some(r=>['operaciones','direccion'].includes(r)),cartera=new Set(ctx.carteraPorSilla?.account||[]),cs=arr(ctx.clientesVisibles);
 const ids=cs.filter(c=>id(c?.id)&&cs.filter(x=>x?.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle===true&&(!propia||cartera.has(c.id))&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
 return {ids,personas:ps.filter(p=>id(p?.id)&&ps.filter(x=>x?.id===p.id).length===1&&activo(p)&&arr(p.puestos).includes('account')).map(p=>p.id),vista:ctx.persona.id,propia,hoy:ctx.hoy,desde:semanaPedidos344(ctx.hoy),firma:JSON.stringify([actores,ctx.hoy,ids,ps,[...cartera].sort(),arr(ctx.datos?.asignaciones),cs.map(c=>c.equipo)])};
 }catch{return null;}}
const sinDato=detalle=>({valor:'—',estado:'gris',detalle});
export function proyectarPedidos344(ctx,D,antes){
 const actual=ambitoPedidos344(ctx);if(!antes||actual?.firma!==antes.firma)return null;
 const autores=arr(ctx.datos?.personas).filter(p=>p?.id==='mili');if(autores.length!==1||!activo(autores[0])||!arr(autores[0].puestos).includes('operaciones'))return null;
 if(!D||D.version!=='343.1'||D.estado!=='medido'||D.origen!=='ledger_pedidos_account_294'||D.autor_id!=='mili'||D.hoy!==actual.hoy||D.desde!==actual.desde||D.hasta!==actual.hoy||D.zona!=='Europe/Madrid'||D.declarado!==true||D.envio_realizado!==false||D.llamada_realizada!==false||D.ejecucion_verificada!==false||!instant(D.generado)||!instant(D.corte_utc)||Date.parse(D.corte_utc)>Date.parse(D.generado)||madrid(D.corte_utc)!==actual.hoy||madrid(D.generado)!==actual.hoy||D.cobertura?.ambito!=='real_interseccion_vista_ACT'||D.cobertura.completa_ledger!==true||D.cobertura.semana_en_curso!==true||D.cobertura.truncado!==false||!Array.isArray(D.filas))return null;
 if(!Array.isArray(D.cliente_ids_autorizados)||!D.cliente_ids_autorizados.every(cid=>actual.ids.includes(cid))||new Set(D.cliente_ids_autorizados).size!==D.cliente_ids_autorizados.length||!Array.isArray(D.receptor_ids_autorizados)||!D.receptor_ids_autorizados.every(pid=>actual.personas.includes(pid))||new Set(D.receptor_ids_autorizados).size!==D.receptor_ids_autorizados.length)return null;
 const filas=new Map();for(const f of D.filas){
  if(!id(f?.receptor_id)||filas.has(f.receptor_id)||!D.receptor_ids_autorizados.includes(f.receptor_id)||(actual.propia&&f.receptor_id!==actual.vista)||!Array.isArray(f.cliente_ids)||!f.cliente_ids.every(cid=>D.cliente_ids_autorizados.includes(cid))||new Set(f.cliente_ids).size!==f.cliente_ids.length||!Number.isSafeInteger(f.pedidos_semana)||f.pedidos_semana<0||!Number.isSafeInteger(f.pendientes)||f.pendientes<0||f.receptores_historicos!==true||typeof f.asignacion_actual_confirmada!=='boolean')return null;
  if(f.ultima_declaracion!==null&&(!instant(f.ultima_declaracion)||madrid(f.ultima_declaracion)>actual.hoy||Date.parse(f.ultima_declaracion)>Date.parse(D.corte_utc)))return null;
  if(f.pedidos_semana>0&&f.ultima_declaracion!==null&&madrid(f.ultima_declaracion)<actual.desde)return null;
  if((f.pedidos_semana>0||f.pendientes>0)&&f.ultima_declaracion===null)return null;
  if(f.pedidos_semana===0&&f.pendientes===0&&f.ultima_declaracion!==null)return null;
  filas.set(f.receptor_id,{receptor_id:f.receptor_id,cliente_ids:[...f.cliente_ids],pedidos_semana:f.pedidos_semana,pendientes:f.pendientes,ultima_declaracion:f.ultima_declaracion,receptores_historicos:true,asignacion_actual_confirmada:f.asignacion_actual_confirmada});
 }
 return {filas,scope:actual,corte:D.corte_utc,desde:D.desde,hasta:D.hasta};
}
export function celdaPedidos344(ctx,modelo,receptor){
 const f=modelo?.filas.get(receptor),scope=ambitoPedidos344(ctx);
 if(!f||scope?.firma!==modelo?.scope.firma)return sinDato('Pedidos locales de Mili: sin fila medida compatible en el registro autorizado; no acredita ausencia de actividad.');
 return {valor:`${f.pedidos_semana} semana · ${f.pendientes} pendientes`,estado:'gris',ambito344:scope.firma,detalle:`Pedidos locales declarados por Mili del ${modelo.desde} al ${modelo.hasta} (Europe/Madrid). Corte ${modelo.corte}. Receptor histórico del pedido; ${f.asignacion_actual_confirmada?'asignación actual confirmada en la fuente':'asignación actual no confirmada, sin reasignar contadores a otro account'}. ${f.ultima_declaracion?'Última declaración '+f.ultima_declaracion+'. ':''}Pendientes al corte incluye pedidos de semanas anteriores. No acredita contacto, envío, llamada ni ejecución. Cero sólo significa cero pedidos declarados en este ledger medido, no ausencia de acciones externas.`};
}
export const celdaPedidosVigente344=(ctx,c)=>!c?.ambito344||ambitoPedidos344(ctx)?.firma===c.ambito344;

export function receptoresSinCartera344(ctx,modelo,gruposIds=[]){
 if(!modelo||ambitoPedidos344(ctx)?.firma!==modelo.scope.firma||!Array.isArray(gruposIds))return [];
 const actuales=new Set(gruposIds);return [...modelo.filas.values()].filter(f=>!actuales.has(f.receptor_id)).map(f=>({...f,cliente_ids:[...f.cliente_ids]}));
}
