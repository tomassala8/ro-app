import {cargarImputa390} from './_imputa_personal_390.js';
// Subvista del módulo Mi día: nunca concede acceso a un módulo ni a una fuente.
const CONTROL = ['direccion', 'operaciones', 'account'];
export function puestoControl239(real, persona, solicitado = null) {
  if (!real?.id || !persona?.id || real.estado !== 'activo' || persona.estado !== 'activo') return null;
  const r = new Set(real.puestos || []), p = new Set(persona.puestos || []);
  const permitidos = CONTROL.filter(x => p.has(x) && (r.has(x) || (x === 'account' && (r.has('direccion') || r.has('operaciones')))));
  return solicitado ? (permitidos.includes(solicitado) ? solicitado : null) : permitidos[0] || null;
}
export const tituloControl239 = puesto => puesto === 'account' ? 'Control de cartera' : 'Control accounts y proyectos';
export function menuActual239(enlace, id, parametro = '') {
  return enlace.id === id && (enlace.subruta || '') === (id === 'mi-dia' && parametro === 'control-cartera' ? 'control-cartera' : '');
}
export async function renderControl239(cont, ctx, vigente, panel, h, estadoVacio) {
  const puesto = puestoControl239(ctx.real, ctx.persona, ctx.params?.[1] || null);
  if (!vigente()) return;
  if (!puesto || !ctx.veModulo('mi-dia')) {
    cont.replaceChildren(estadoVacio({titulo:'Control de cartera no disponible', porque:'Este puesto no tiene acceso a esta vista.', que_hacer:'Vuelve a Mi día.'}));
    return;
  }
  ctx.titulo(tituloControl239(puesto), 'Clientes y proyectos autorizados');
  const fuentes = [
    ['bandeja/por_cliente','bandeja'], ['produccion/produccion','produccion'],
    ['reuniones/reuniones','reuniones'], ['nuevos/nuevos','clientes-nuevos'],
    ['metodo/sugerencias','reuniones'],
  ];
  // ctx.ver evalúa la persona vista; sin una intersección explícita no se lee
  // esta fuente adicional en «ver como». La API conserva su propio recorte.
  const pautaPermitida = () => ctx.servidor && ctx.real?.id === ctx.persona?.id &&
    ctx.real?.estado === 'activo' && ctx.persona?.estado === 'activo' &&
    ctx.real.activo !== false && ctx.persona.activo !== false &&
    ctx.veModulo('dinero-cliente') && typeof ctx.ver === 'function' &&
    (ctx.clientesVisibles || []).some(c => c?.activo_confirmado === true &&
      ctx.ver({tipo:'cliente_detalle',cliente_id:c.id}).ok === true &&
      ctx.ver({tipo:'horas_pautadas',cliente_id:c.id}).ok === true);
  if (pautaPermitida()) fuentes.push(['dinero_cliente/dinero_cliente','dinero-cliente']);
  const lecturas = await Promise.all(fuentes.map(async ([nombre,modulo]) => {
    if (!ctx.veModulo(modulo)) return [nombre,null];
    try { return [nombre, await (nombre === 'metodo/sugerencias' ? ctx.api(nombre) : ctx.datosModulo(nombre))]; }
    catch { return [nombre,null]; }
  }));
  if (!vigente()) return;
  const datos = new Map(lecturas);
  const accountIds=(ctx.datos?.personas||[]).filter(p=>p?.estado==='activo'&&p.activo!==false&&Array.isArray(p.puestos)&&p.puestos.includes('account')).map(p=>p.id);
  const imputa=await cargarImputa390(ctx,accountIds);
  if(!vigente())return;
  if(imputa)datos.set('horas_personales/390',imputa);
  if (!pautaPermitida()) datos.delete('dinero_cliente/dinero_cliente');
  const destinos = [['mi-dia/'+puesto,'Mi día','mi-dia'],['horas','Horas del equipo','horas'],['produccion','Producción','produccion']];
  const nav = h('nav', {'aria-label':'Navegar desde control de cartera', class:'chips-f'},
    destinos.filter(x=>ctx.veModulo(x[2])).map(([ruta,titulo])=>h('a',{href:'#/'+ruta},titulo)));
  cont.replaceChildren(nav,panel(ctx,{opcional:nombre=>datos.get(nombre) || null},puesto,vigente));
}
