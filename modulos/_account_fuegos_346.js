import {prepararControlCartera} from './control_cartera.js';

// Presentación de asignación vigente; no concede permisos ni atribuye trabajo histórico.
export function firmaAccountFuegos346(ctx) {
  try { return JSON.stringify(Array.isArray(ctx.datos?.asignaciones)?ctx.datos.asignaciones:[]); }
  catch { return null; }
}
export function accountFuego346(ctx,cliente) {
  const desconocido={id:null,confirmado:false,texto:'Account por confirmar'};
  try {
    if(!cliente||cliente.activo_confirmado!==true||cliente.detalle!==true||ctx.ver?.({tipo:'cliente_detalle',cliente_id:cliente.id})?.ok!==true)return desconocido;
    const filas=prepararControlCartera({clientes:[cliente],persona_id:ctx.persona?.id,esOps:true,carteraIds:[],asignaciones:ctx.datos?.asignaciones,personas:ctx.datos?.personas,fuentes:{},hoy:ctx.hoy});
    const fila=filas.length===1?filas[0]:null;
    const personas=(Array.isArray(ctx.datos?.personas)?ctx.datos.personas:[]).filter(p=>p?.id===fila?.account_id);
    if(!fila?.account_id||personas.length!==1||personas[0].estado!=='activo'||personas[0].activo===false||!Array.isArray(personas[0].puestos)||!personas[0].puestos.includes('account'))return desconocido;
    const nombre=ctx.nombre?.(fila.account_id)||fila.account_id;
    return {id:fila.account_id,confirmado:fila.owner_confirmado===true,texto:nombre+(fila.owner_confirmado===true?'':' · asignación por confirmar')};
  } catch { return desconocido; }
}
