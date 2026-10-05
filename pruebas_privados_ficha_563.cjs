// Cargar privado + contexto233 + api/verDato529 reales; transporte sólo sintético.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ficha=fs.readFileSync(__dirname+'/modulos/ficha.js','utf8'),app=fs.readFileSync(__dirname+'/app.js','utf8');
const carga=ficha.slice(ficha.indexOf('async function cargarPrivado('),ficha.indexOf('// =================================================================== render'));
const ayuda=fs.readFileSync(__dirname+'/modulos/_contexto_ficha_233.js','utf8').replace(/export /g,'');
const api=app.slice(app.indexOf('async function api('),app.indexOf('/** Ronda 5 · la verdad única por cliente'));
const linea=app.split('\n').find(x=>x.trim().startsWith('verDato:'));
const adaptador=linea.slice(linea.indexOf(':')+1).trim().replace(/,$/,'');
function fixture(){let actual=true,permitido=true,lecturas=0;const requests=[],replies=[];
 const root={isConnected:true,children:['private previo'],replaceChildren(...xs){this.children=xs;}};
 const cliente={id:'c',detalle:true};
 const box={estado:{servidor:true,real:{id:'dir'},persona:{id:'dir'}},pintura:{usadas:new Set()},medidorUso:null,_ayudas:null,
 vigente:()=>actual,rastrear:false,olvidarTrasCambio(){},cabeceras:(yo,como)=>({yo,como}),
 fetch:async(ruta,op)=>{lecturas++;requests.push({ruta,op});return await replies.shift();}};
 vm.createContext(box);vm.runInContext(ayuda+'\n'+api+'\n'+carga+`;this.verDato=${adaptador};`,box);
 const base={servidor:true,soloLectura:false,real:{id:'dir',puestos:['direccion'],estado:'activo'},persona:{id:'dir',puestos:['direccion'],estado:'activo'},
 clientes:[cliente],clientesVisibles:[cliente],veModulo:()=>true,ver:()=>({ok:permitido}),vigente:()=>actual,verDato:box.verDato};
 return {box,base,root,replies,requests,get lecturas(){return lecturas;},setActual:v=>actual=v,revoke:()=>permitido=false,
 scope:()=>box.contextoFicha233(base,root,'c')};
}
const response=(valor,status=200)=>({ok:status===200,status,json:async()=>status===200?{valor}:{error:'No disponible'}});
const defer=()=>{let resolve;return {promise:new Promise(r=>resolve=r),get resolve(){return resolve;}};};
(async()=>{
 let casos=0;
 for(const valor of [0,{datos:[{nombre:'fixture'}]},null]){
  const f=fixture();f.replies.push(response(valor));const res=await f.box.cargarPrivado(f.scope(),'contactos','c');
  assert.deepEqual(JSON.parse(JSON.stringify(res)),{valor});assert.equal(f.lecturas,1);
  const req=f.requests[0];assert.equal(req.ruta,'api/ver_dato');assert.deepEqual(JSON.parse(req.op.body),{almacen:'ficha/_privado/contactos',ref:'c',campo:'datos',cliente_id:'c'});casos++;
 }
 for(const status of [403,404,500]){
  const f=fixture();f.replies.push(response(null,status));const res=await f.box.cargarPrivado(f.scope(),'chat','c');
  if(status===404)assert.equal(res.valor,null);else assert(res.negado);
  assert.equal(f.root.children.length,1,'fallo privado no vacía toda la ficha vigente');casos++;
 }
 for(const cambio of ['real','vista','ruta','permiso','roles','cliente','modulo','lectura']){
  const f=fixture(),p=defer();f.replies.push(p.promise);const scope=f.scope();const lectura=f.box.cargarPrivado(scope,'contactos','c');
  assert.equal(f.lecturas,1);
  if(cambio==='real')f.box.estado.real={id:'otro'};
  if(cambio==='vista')f.box.estado.persona={id:'otro'};
  if(cambio==='ruta')f.setActual(false);
  if(cambio==='permiso')f.revoke();
  if(cambio==='roles')f.base.persona.puestos.push('seo');
  if(cambio==='cliente')f.base.clientes=[];
  if(cambio==='modulo')f.base.veModulo=()=>false;
  if(cambio==='lectura')f.base.soloLectura=true;
  p.resolve(response('PRIVATE-LATE'));
  let resultado;try{resultado=await lectura;}catch(e){assert(!String(e).includes('PRIVATE-LATE'));}
  assert(!String(JSON.stringify(resultado)).includes('PRIVATE-LATE'));
  //529 bloquea otra identidad global;233 limpia la raíz cuando la revocación afecta al contexto de ficha.
  if(!['real','vista'].includes(cambio))assert.equal(f.root.children.length,0);casos++;
 }
 const f=fixture(),d=defer();f.replies.push({ok:true,status:200,json:()=>d.promise});const pending=f.box.cargarPrivado(f.scope(),'chat','c');
 await Promise.resolve();await Promise.resolve();f.revoke();d.resolve({valor:'PRIVATE-JSON-LATE'});await assert.rejects(pending);assert.equal(f.root.children.length,0);casos++;
 for(const cambio of ['sinServidor','verComo','denegado','sinPuerta']){
  const f=fixture();if(cambio==='sinServidor')f.base.servidor=false;if(cambio==='verComo')f.base.soloLectura=true;if(cambio==='denegado')f.base.ver=({tipo})=>({ok:tipo==='cliente_detalle'});if(cambio==='sinPuerta')delete f.base.verDato;
  assert((await f.box.cargarPrivado(f.scope(),'chat','c')).negado);assert.equal(f.lecturas,0);casos++;
 }
 assert(!carga.includes('fetch('));assert(!carga.includes('X-RO-'));assert(carga.includes('ctx.verDato(cuerpo)'));
 console.log(`${casos} grupos563 PASS: puerta real529, DTO, privacidad tardía, errores parciales y scopes233.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
