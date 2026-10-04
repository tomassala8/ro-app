const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c={URL};vm.createContext(c);
for(const f of ['_tarea_ia.js','_detalle_tarea_197.js','_transicion_produccion_206.js']) vm.runInContext(fs.readFileSync(__dirname+'/modulos/'+f,'utf8').replace(/^import[^;]+;\s*/gm,'').replace(/export function /g,'function ').replace(/export const /g,'const '),c);
const source=fs.readFileSync(__dirname+'/modulos/produccion.js','utf8');
vm.runInContext(source.slice(source.indexOf('const INTENCIONES_REVISION211'),source.indexOf('export default')).replace(/export function /g,'function '),c);
let n=0,serial=0;
const fixture=()=>{
 const k=++serial,tid='task-'+k,ctx={servidor:true,real:{id:'r-'+k},persona:{id:'r-'+k},veModulo:()=>true};
 const t={id:tid,cli:'client-'+k,estado:'revisión técnica'};
 const token={modulo:'produccion',tarea_id:tid,cliente_id:t.cli,lista_id:'list-'+k,tipo_estado:'custom',expected_estado:t.estado,revision:'a'.repeat(64),bloqueada:false,acciones:{pieza_aprobar:{autorizacion_confirmada:true,destino:'revisión project manager'},pieza_pedir_cambios:{autorizacion_confirmada:true,destino:'corrección'},mover_estado:{autorizacion_confirmada:true,destino:'revisión project manager'}}};
 const datos={capacidad_revision:{version:'206.1',activo:true},transiciones_revision:{[tid]:token},estados_detalle:{[token.lista_id]:[{estado:t.estado,tipo:'custom'},{estado:'revisión project manager',tipo:'custom'},{estado:'corrección',tipo:'custom'}]}};
 const uuid='22222222-2222-4222-8222-222222222222';
 const respuesta=b=>({ok:true,id:1,intencion_guardada:{id:b.intencion_id,accion_id:1,repetida:false},recibo_durable:true,cola_estado:'simulado',confirmacion_remota:false,recibo:{accion_id:1,cambio_id:2,tarea_id:tid,lista_id:token.lista_id,desde:b.vista_previa.expected_estado,hasta:b.vista_previa.a,intencion_id:b.intencion_id,tipo:b.tipo,modulo:b.modulo,estado_cola:'simulado',confirmacion_remota:false}});
 return {ctx,t,datos,token,uuid,respuesta};
};
(async()=>{
 let f=fixture(),calls=[];f.ctx.accion=async b=>{calls.push(b);return f.respuesta(b)};
 let ctrl=c.crearControlRevision211(f.ctx,()=>true,f.datos,()=>f.uuid);assert(ctrl.permiso(f.t,'pieza_aprobar').ok);n++;
 const r=await ctrl.enviar(f.t,'pieza_aprobar');assert.equal(r.estado,'simulado');assert(!r.confirmacion_remota);assert.match(r.texto,/sin envío confirmado/);assert(!('lista_id'in f.t));n++;
 assert.equal(calls[0].modulo,'produccion');assert.equal(calls[0].tipo,'pieza_aprobar');assert(calls[0].vista_previa.transicion_produccion);assert(!calls[0].vista_previa.transicion_tablero);n++;
 await ctrl.enviar(f.t,'pieza_aprobar');assert.equal(calls.length,1);n++;
 for(const patch of [{soloLectura:true},{pilotoLectura:true},{servidor:false},{real:{id:'foreign'}},{veModulo:()=>false}]){
  f=fixture();let count=0;Object.assign(f.ctx,patch);f.ctx.accion=async()=>{count++;throw Error('No debería')};ctrl=c.crearControlRevision211(f.ctx,()=>true,f.datos,()=>f.uuid);
  await assert.rejects(ctrl.enviar(f.t,'pieza_aprobar'));assert.equal(count,0);n++;
 }
 f=fixture();f.token.cliente_id='foreign';ctrl=c.crearControlRevision211(f.ctx,()=>true,f.datos,()=>f.uuid);assert(!ctrl.permiso(f.t,'pieza_aprobar').ok);n++;
 f=fixture();assert.equal(c.piezaRevision211({...f.t,lista_id:'foreign'},f.datos),null);assert.equal(c.piezaRevision211({...f.t,tipo_estado:'closed'},f.datos),null);n++;
 f=fixture();delete f.token.tipo_estado;assert.equal(c.piezaRevision211(f.t,f.datos),null);n++;
 f=fixture();calls=[];let fail=true;f.ctx.accion=async b=>{calls.push(b);if(fail)throw Error('lost response');return f.respuesta(b)};ctrl=c.crearControlRevision211(f.ctx,()=>true,f.datos,()=>f.uuid);
 await assert.rejects(ctrl.enviar(f.t,'pieza_pedir_cambios','Corrige titular'));assert(ctrl.estado(f.t));fail=false;
 await ctrl.enviar(f.t,'pieza_pedir_cambios','Texto cambiado');assert.equal(JSON.stringify(calls[0]),JSON.stringify(calls[1]));assert.equal(calls[1].vista_previa.comentario,'Corrige titular');n++;
 f=fixture();let finish;f.ctx.accion=b=>new Promise(res=>{finish=()=>res(f.respuesta(b))});ctrl=c.crearControlRevision211(f.ctx,()=>true,f.datos,()=>f.uuid);
 let pending=ctrl.enviar(f.t,'pieza_aprobar');await assert.rejects(ctrl.enviar(f.t,'pieza_aprobar'),/curso/);finish();await pending;n++;
 f=fixture();let active=true;f.ctx.accion=b=>new Promise(res=>{finish=()=>res(f.respuesta(b))});ctrl=c.crearControlRevision211(f.ctx,()=>active,f.datos,()=>f.uuid);
 pending=ctrl.enviar(f.t,'pieza_aprobar');active=false;finish();await assert.rejects(pending,/vista cambió/);assert.equal(ctrl.estado(f.t).resultado,null);assert.equal(ctrl.estado(f.t).enCurso,false);n++;
 f=fixture();f.ctx.accion=async()=>({ok:true,id:1});ctrl=c.crearControlRevision211(f.ctx,()=>true,f.datos,()=>f.uuid);
 await assert.rejects(ctrl.enviar(f.t,'pieza_aprobar'),/recibo/);assert.equal(ctrl.estado(f.t).resultado,null);await assert.rejects(ctrl.enviar(f.t,'pieza_pedir_cambios','Cambio'),/otra intención/);n++;
 f=fixture();let count=0;f.ctx.accion=async b=>{count++;throw Error('lost')};ctrl=c.crearControlRevision211(f.ctx,()=>true,f.datos,()=>f.uuid);
 await assert.rejects(ctrl.enviar(f.t,'pieza_aprobar'));await assert.rejects(ctrl.enviar({...f.t,cli:'other-client'},'pieza_aprobar'),/cliente/);assert.equal(count,1);n++;
 f=fixture();let datos=f.datos;datos.capacidad_revision.activo=false;f.ctx.accion=async()=>{throw Error('No ejecutar')};ctrl=c.crearControlRevision211(f.ctx,()=>true,datos,()=>f.uuid);await assert.rejects(ctrl.enviar(f.t,'pieza_aprobar'));n++;
 // Ejecutar el callback DOM real, además del controlador: sin éxito optimista ni repintado obsoleto.
 const montar=(f,active)=>{
  class Nodo {constructor(tag,props,children){this.tag=tag;this.props=props;this.children=children;this.isConnected=true;this.disabled=props.disabled;this.events=props.on||{};} replaceChildren(...x){this.children=x;} append(...x){this.children.push(...x);} }
  c.h=(tag,props,...children)=>new Nodo(tag,props||{},children);c.S={1:4};c.ctx=f.ctx;c.vigente=()=>active.valor;c.datosRevision=f.datos;
  c.controlRevision=c.crearControlRevision211(f.ctx,c.vigente,f.datos,()=>f.uuid);
  const fragment=source.slice(source.indexOf('    const accionRevision ='),source.indexOf('    const yo ='));
  const accion=vm.runInContext('(function(){'+fragment+' return accionRevision;})()',c);
  const texto=node=>typeof node==='string'?node:(node?.children||[]).map(texto).join(' ');
  return {accion,texto};
 };
 f=fixture();let vis={valor:true};f.ctx.accion=b=>new Promise(res=>{finish=()=>res(f.respuesta(b))});
 let dom=montar(f,vis),box=dom.accion(f.t,'pieza_aprobar'),button=box.children[0];
 pending=button.events.click();assert.equal(button.disabled,true);assert(!/Registrado|confirmado en ClickUp/.test(dom.texto(box)));finish();await pending;
 assert.match(dom.texto(box),/simulación, sin envío confirmado/);assert.equal(f.t.estado,'revisión técnica');assert.equal(box.children[0].disabled,true);n++;
 f=fixture();vis={valor:true};f.ctx.accion=b=>new Promise(res=>{finish=()=>res(f.respuesta(b))});
 dom=montar(f,vis);box=dom.accion(f.t,'pieza_aprobar');pending=box.children[0].events.click();const original=box.children;vis.valor=false;finish();await pending;
 assert.equal(box.children,original);assert(!/Registrado/.test(dom.texto(box)));n++;
 f=fixture();vis={valor:true};calls=[];let lost=true;f.ctx.accion=async b=>{calls.push(b);if(lost)throw Error('Respuesta perdida');return f.respuesta(b);};
 dom=montar(f,vis);box=dom.accion(f.t,'pieza_pedir_cambios','Corrección original');await box.children[0].events.click();
 assert.match(dom.texto(box),/Reintentar misma intención/);assert.match(dom.texto(box),/Respuesta perdida/);lost=false;await box.children[0].events.click();
 assert.equal(JSON.stringify(calls[0]),JSON.stringify(calls[1]));assert.match(dom.texto(box),/sin envío confirmado/);n++;
 f=fixture();vis={valor:true};let clicks=0;f.ctx.accion=async b=>{clicks++;return f.respuesta(b)};
 dom=montar(f,vis);box=dom.accion(f.t,'pieza_aprobar');box.isConnected=false;await box.children[0].events.click();assert.equal(clicks,0);n++;
 // Verificar wiring de las tres acciones sin interpretar/invocar proveedores.
 assert(source.includes("ctx.api('produccion/transiciones')"));assert(source.includes("accionRevision(x, 'pieza_aprobar')"));assert(source.includes("accionRevision(x, 'pieza_pedir_cambios', texto)"));assert(source.includes("accionRevision(r, 'mover_estado')"));
 assert(!source.includes("hecho: 'Pasada a revisión del account'"));assert(!source.includes("tipo: 'pieza_aprobar', objeto:"));n++;
 console.log(n+' grupos211 PASS: contrato208/209/206 real, scopes, fallos, UUID estable, concurrencia, stale y wiring.');
})().catch(e=>{console.error(e);process.exitCode=1});
