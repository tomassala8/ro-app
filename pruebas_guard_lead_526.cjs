const fs=require('fs'),vm=require('vm'),assert=require('assert');
const text=fs.readFileSync(__dirname+'/modulos/crm.js','utf8');
const start=text.indexOf('async function verDatosLead('),end=text.indexOf('// ------------------------------------------------------------------ pantalla principal',start);
class N{
 constructor(tag,props={},...kids){this.tag=tag;this.props=props;this.children=kids;this.isConnected=false;this.events={};this.disabled=false;}
 addEventListener(name,fn){this.events[name]=fn;}
 replaceChildren(...kids){this.children=kids;}
 remove(){this.isConnected=false;this.removed=true;}
 connect(){this.isConnected=true;for(const n of this.children)if(n instanceof N)n.connect();return this;}
}
const h=(tag,props,...kids)=>new N(tag,props,...kids), notices=[];
const s={h,icono:()=>null,botonesContacto:v=>h('div',{synthetic:v}),avisoFlotante:t=>notices.push(t)};
vm.createContext(s);vm.runInContext(text.slice(start,end),s);
function fixture(){
 const p={id:'account',estado:'activo',puestos:['account']},c={id:'cid',activo_confirmado:true,detalle:true};
 const ctx={real:p,persona:p,datos:{personas:[p],asignaciones:[]},clientes:[c],clientesVisibles:[c],nivel:'suyo',
 servidor:true,soloLectura:false,pilotoLectura:false,vigente:()=>true,veModulo:()=>true,ver:()=>({ok:true,desenmascarable:true})};
 const row={ref:'fixture',cliente_id:'cid'};let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no});let calls=[];
 ctx.verDato=b=>{calls.push(b);return promise};
 const root=s.botonVerDatos(ctx,row,{resumen:false})?.connect();
 return {ctx,row,root,button:root?.children[0],box:root?.children[1],resolve,reject,calls};
}
const run=async fn=>{notices.length=0;await fn();};
(async()=>{
 await run(async()=>{const f=fixture(),pending=f.button.events.click();f.resolve({valor:{nombre:'Synthetic',telefono:'fixture'}});await pending;
 assert.equal(f.calls.length,1);assert.equal(f.box.children.length,1);assert.equal(f.button.removed,true);assert.equal(f.calls[0].ref,'fixture');});
 await run(async()=>{const f=fixture(),pending=f.button.events.click();await f.button.events.click();assert.equal(f.calls.length,1);f.resolve({valor:{}});await pending;});
 for(const revoke of [f=>f.ctx.vigente=()=>false,f=>f.ctx.real={...f.ctx.real,id:'other'},f=>f.ctx.ver=()=>({ok:false}),f=>f.ctx.clientes[0].activo_confirmado=false,
 f=>f.ctx.datos.personas.push({...f.ctx.persona}),f=>f.ctx.persona.puestos.push('account'),f=>f.row.ref='changed',f=>f.row.cliente_id='other',f=>f.box.isConnected=false,f=>f.button.isConnected=false,f=>f.ctx.veModulo=()=>false]){
  await run(async()=>{const f=fixture(),pending=f.button.events.click();revoke(f);f.resolve({valor:{nombre:'Synthetic'}});await pending;
   assert.equal(f.box.children.length,0);assert.equal(f.button.removed,undefined);assert.equal(f.button.disabled,true);assert.equal(notices.length,0);});
  await run(async()=>{const f=fixture();revoke(f);await f.button.events.click();assert.equal(f.calls.length,0);assert.equal(f.box.children.length,0);});
 }
 await run(async()=>{const f=fixture(),pending=f.button.events.click();f.reject(Error('network fixture'));await pending;
 assert.equal(f.button.disabled,false);assert.equal(f.box.children.length,0);assert.equal(notices.length,1);});
 await run(async()=>{const f=fixture(),pending=f.button.events.click();f.ctx.vigente=()=>false;f.reject(Error('network fixture'));await pending;
 assert.equal(f.button.disabled,true);assert.equal(notices.length,0);});
 await run(async()=>{const f=fixture(),pending=f.button.events.click();f.resolve({valor:{nombre:'Synthetic'}});await pending;
 f.ctx.ver=()=>({ok:false});let prevented=false,stopped=false;f.box.events.click({preventDefault(){prevented=true},stopPropagation(){stopped=true}});
 assert.equal(f.box.children.length,0);assert(prevented&&stopped);});
 for(const update of [f=>f.ctx.soloLectura=true,f=>f.ctx.servidor=false,f=>f.ctx.datos.personas=[],f=>f.ctx.clientes.push({...f.ctx.clientes[0]}),f=>f.ctx.pilotoLectura=true]){
 const f=fixture();update(f);assert.equal(s.botonVerDatos(f.ctx,f.row,{resumen:false}),null);}
 console.log('526: 32 escenarios PASS · source real · sin API/PII/negocio');
})().catch(e=>{console.error(e);process.exitCode=1});
