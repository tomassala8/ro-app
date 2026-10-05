import {crearMensajeIncidencia330} from './_mensaje_incidente_330.js';
import {h} from '../componentes.js';
const RUTA='operaciones/pedidos-account',ESTADOS=['pedido','anulado','resuelto_declarado'];
const etiquetas={pedido:'Pedido en RO',anulado:'Pedido anulado',resuelto_declarado:'Resuelto declarado'};
export function reciboPedido294(res,b,actor,receptor){
 const r=res?.recibo;
 return res?.version==='294.1'&&['guardado','duplicado'].includes(res.resultado)&&r?.intencion_id===b.intencion_id&&r.cliente_id===b.cliente_id&&r.tipo===b.tipo&&r.referencia_id===b.referencia_id&&r.estado===b.estado&&r.autor===actor&&r.receptor===receptor&&r.revision===b.revision+1&&r.origen==='registro_equipo'&&r.declarado===true&&r.envio_realizado===false&&r.llamada_realizada===false&&r.respuesta_verificada===false;
}
// Cache de promesas limitado a esta renderización/identidad; nunca global ni entre sesiones.
export function crearConsultasPedidos294(ctx){
 const real=ctx.real?.id,vista=ctx.persona?.id,cache=new Map(),listeners=new Map();
 const vigente=()=>ctx.real?.id===real&&ctx.persona?.id===vista&&(!ctx.vigente||ctx.vigente())&&ctx.veModulo?.('bandeja')===true;
 return {leer(cid){if(!vigente())return Promise.reject(Error('La sesión cambió.'));if(!cache.has(cid)){const p=ctx.api(`${RUTA}?cliente_id=${encodeURIComponent(cid)}`);cache.set(cid,p);p.catch(()=>{if(cache.get(cid)===p)cache.delete(cid);});}return cache.get(cid);},invalidar(cid){cache.delete(cid);for(const fn of [...listeners.get(cid)||[],...listeners.get('*')||[]])fn();},suscribir(cid,fn){if(!listeners.has(cid))listeners.set(cid,new Set());listeners.get(cid).add(fn);}};
}
export function crearPedidoAccount294(ctx,{cliente_id,tipo,referencia_id},consultas=null){
 const root=h('details',{'data-pedido-account':'294'}),estado=h('small',{},'Consultar pedido'),nota=h('small',{}),selector=h('select',{'aria-label':'Estado del pedido en RO',style:'max-width:100%;min-height:36px;padding:4px 8px;border:1px solid var(--linea,#dde0e8);border-radius:6px;background:var(--panel,#fff);font:inherit'},...ESTADOS.map(e=>h('option',{value:e},etiquetas[e]))),boton=h('button',{type:'button',style:'min-height:36px;padding:6px 10px;border:1px solid #dde0e8;border-radius:6px;background:#fff;color:#171b35;font:inherit;cursor:pointer',disabled:true},'Guardar pedido en RO');
 const recargar=h('button',{type:'button',style:'min-height:36px;padding:6px 10px;border:1px solid #dde0e8;border-radius:6px;background:#fff;color:#171b35;font:inherit;cursor:pointer',hidden:true},'Recargar copia');root.append(h('summary',{},estado),h('div',{style:'display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding-top:6px'},selector,boton,recargar,nota));const real=ctx.real?.id,vista=ctx.persona?.id;let cap=null,intento=null,busy=false,conflicto=false,lectura=0;
 const scope=()=>{const cs=(ctx.clientesVisibles||[]).filter(c=>c?.id===cliente_id);return cs.length===1&&cs[0].activo_confirmado===true&&cs[0].detalle===true;};
 const vivo=()=>scope()&&root.isConnected&&(!ctx.vigente||ctx.vigente())&&ctx.real?.id===real&&ctx.persona?.id===vista&&ctx.veModulo?.('bandeja')===true&&ctx.ver?.({tipo:'cliente_detalle',cliente_id})?.ok===true;
 const mensaje=crearMensajeIncidencia330(h,ctx,{cliente_id,tipo,referencia_id},()=>cap,()=>vivo());root.append(mensaje.elemento);
 const capValida=()=>typeof cap?.receptor==='string'&&Number.isSafeInteger(cap?.revision)&&cap.revision>=0&&typeof cap?.revision_fuente==='string'&&/^[a-f0-9]{64}$/.test(cap.revision_fuente);
 const editable=()=>!conflicto&&capValida()&&vivo()&&ctx.servidor===true&&ctx.soloLectura!==true&&ctx.ver?.({tipo:'responder_cliente',cliente_id})?.ok===true&&real===vista&&cap?.puede_registrar===true;
 async function cargar(){
  if(!vivo())return;
  const turno=++lectura;boton.disabled=true;
  try{
   const d=await (consultas?consultas.leer(cliente_id):ctx.api(`${RUTA}?cliente_id=${encodeURIComponent(cliente_id)}`));if(!vivo()||turno!==lectura)return;
   const rs=Array.isArray(d?.capacidades)?d.capacidades.filter(r=>r.cliente_id===cliente_id&&r.tipo===tipo&&r.referencia_id===referencia_id):[];
   if(d?.version!=='294.1'||d.cliente_id!==cliente_id||rs.length!==1)throw Error('No hay una capacidad única para este pedido.');
   cap=rs[0];mensaje.actualizar();estado.textContent=cap.actual?etiquetas[cap.actual.estado]||'Estado local por confirmar':'Sin pedido local registrado';
   if(!intento)selector.value=cap.actual?.estado||'pedido';
   nota.textContent=cap.puede_registrar?'Sólo registro en RO; no envía mensajes ni realiza llamadas.':cap.motivo||'Pedido no disponible en esta sesión.';
   boton.disabled=!editable()||(!intento&&selector.value===cap?.actual?.estado);selector.disabled=!editable();
  }catch(e){if(vivo()&&turno===lectura){cap=null;mensaje.actualizar();estado.textContent='Pedido sin consultar';nota.textContent=e.message||'No se pudo consultar el pedido.';boton.disabled=true;selector.disabled=true;}}
 }
 recargar.addEventListener('click',async()=>{if(!vivo()||busy)return;conflicto=false;intento=null;recargar.hidden=true;consultas?.invalidar(cliente_id);await cargar();});
 selector.addEventListener('change',()=>{if(vivo()&&!busy){intento=null;boton.textContent='Guardar en RO';boton.disabled=!editable()||selector.value===cap?.actual?.estado;}});
 boton.addEventListener('click',async()=>{
  if(busy||!editable()||!ESTADOS.includes(selector.value))return;
  if(!intento){const uuid=globalThis.crypto?.randomUUID?.();if(!uuid){nota.textContent='No se puede crear una intención segura en este navegador.';return;}intento={cliente_id,tipo,referencia_id,estado:selector.value,revision:cap.revision,revision_fuente:cap.revision_fuente,intencion_id:uuid};}
  busy=true;lectura++;boton.disabled=true;selector.disabled=true;nota.textContent='Guardando pedido local…';
  try{
   if(!editable())throw Error('La sesión o el acceso cambió.');
   const res=await ctx.api(RUTA,{metodo:'POST',cuerpo:intento});if(!vivo())return;
   if(!reciboPedido294(res,intento,real,cap.receptor))throw Error('No llegó un recibo coherente. Reintenta la misma intención.');
   intento=null;consultas?.invalidar(cliente_id);nota.textContent='Registro guardado en RO. Sin envío externo ni llamada realizada.';await cargar();
  }catch(e){if(vivo()){nota.textContent=e.message||'No se confirmó el registro. Conserva este intento para reintentar.';conflicto=e.status===409;recargar.hidden=!conflicto;boton.textContent=conflicto?'Recarga antes de guardar':'Reintentar mismo pedido';}}
  finally{busy=false;if(vivo()){boton.disabled=!editable()||(!intento&&selector.value===cap?.actual?.estado);selector.disabled=!editable();}}
 });
 // Las celdas se construyen detached; consultar después del montaje, sin bucle/poll.
 consultas?.suscribir(cliente_id,()=>{if(vivo()&&!busy)cargar();});queueMicrotask(cargar);return {elemento:root,cargar};
}
export async function renderColaPedidosAccount294(cont,ctx,consultas=null){
 const root=h('details',{'data-cola-pedidos':'294'}),cuerpo=h('div',{},'Consultando pedidos locales…');const resumen=h('summary',{},'Pedidos al account · RO');root.append(resumen,cuerpo);cont.append(root);
 const real=ctx.real?.id,vista=ctx.persona?.id;const vivo=()=>root.isConnected&&(!ctx.vigente||ctx.vigente())&&ctx.real?.id===real&&ctx.persona?.id===vista&&ctx.veModulo?.('bandeja')===true;
 let lecturaCola=0;
 async function cargarCola(){
 if(!vivo())return;const turno=++lecturaCola;
 try{
  const d=await ctx.api(RUTA);if(!vivo()||turno!==lecturaCola)return;
  if(d?.version!=='294.1'||d.cliente_id!==null||!Array.isArray(d.pedidos))throw Error('Cola local no disponible.');
  const cs=ctx.clientesVisibles||[];const scope=new Map(cs.filter(c=>cs.filter(z=>z?.id===c?.id).length===1&&c?.activo_confirmado===true&&c.detalle===true&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>[c.id,c]));
  const rs=d.pedidos.filter(r=>scope.has(r.cliente_id)&&r.declarado===true&&r.envio_realizado===false&&r.llamada_realizada===false&&ESTADOS.includes(r.estado));
  resumen.textContent=`Pedidos al account · ${rs.filter(r=>r.estado==='pedido').length} pendientes en RO`;
  cuerpo.replaceChildren(h('p',{},'Pedidos registrados localmente. No equivalen a respuesta enviada o llamada realizada.'),...(rs.length?rs.map(r=>h('div',{},h('strong',{},scope.get(r.cliente_id).nombre||r.cliente_id),` · ${r.tipo==='devolver_llamada'?'Devolver llamada':'Responder correo'} · ${etiquetas[r.estado]} · ${r.registrado_en}`,crearPedidoAccount294(ctx,r,consultas).elemento)):[h('p',{},'Sin pedidos locales visibles en esta copia.')]),d.truncado?h('p',{},'Lista parcial: consulta el cliente para ver sus pedidos.'):null);
 }catch(e){if(vivo()&&turno===lecturaCola)cuerpo.textContent=e.message||'No se pudo consultar la cola local.';}
 }
 consultas?.suscribir('*',()=>{if(vivo())cargarCola();});await cargarCola();
}
