// Guard de lectura del panel: ruta e identidades, sin fuentes nuevas ni permisos propios.
const firmaPanel213=ctx=>JSON.stringify([ctx.real?.id || ctx.persona?.id,ctx.persona?.id,ctx.real?.puestos || [],ctx.persona?.puestos || [],ctx.params || [],(ctx.clientesVisibles || ctx.clientes || []).map(c=>[c.id,c.activo_confirmado,c.activo]).sort((a,b)=>String(a[0]).localeCompare(String(b[0])))]);
export function vigentePaneles213(cont,ctx) {
  const firma=firmaPanel213(ctx);
  return ()=>cont?.isConnected===true && (typeof ctx.veModulo!=='function' || ctx.veModulo('paneles')===true) && (!ctx.vigente || ctx.vigente()) && firmaPanel213(ctx)===firma;
}
export function controlesPaneles213(ctx) {
  const p=ctx.persona?.puestos || [],r=ctx.real?.puestos || p;
  const roles=['operaciones','direccion','account'];
  const out=[];
  // Roles sólo seleccionan la vista; la visibilidad se exige a la política actual.
  const rol=roles.find(x=>p.includes(x));
  if(rol && r.some(x=>roles.includes(x)) && ctx.veModulo?.('mi-dia')===true)out.push({texto:'Control de cartera y Accounts',icono:'tabla',href:`#/mi-dia/${rol}`});
  if(ctx.veModulo?.('produccion')===true)out.push({texto:'Revisiones y pendientes',icono:'capas',href:'#/produccion'});
  if(ctx.veModulo?.('horas')===true)out.push({texto:'Horas registradas',icono:'clock',href:'#/horas'});
  return out;
}
