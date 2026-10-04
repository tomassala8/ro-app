const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const helper=fs.readFileSync(path.join(__dirname,'modulos/_informe_evidencia.js'),'utf8').replace(/export /g,'');
const defer=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j});return {promise,resolve,reject}};
let casos=0;
async function main(){
 const b={};vm.createContext(b);vm.runInContext(helper,b);
 let now=0,carga=0;const cache=new Map(),opts={ttl:10,ahora:()=>now};
 const leer=()=>b.lecturaInforme(cache,'k',()=>++carga,opts);
 assert.equal(await leer(),1);now=9;assert.equal(await leer(),1);now=10;assert.equal(await leer(),2);casos++;
 await assert.rejects(b.lecturaInforme(cache,'error',()=>Promise.reject(Error('fixture')),opts));
 assert.equal(await b.lecturaInforme(cache,'error',()=>4,opts),4);casos++;
 for(const value of [undefined,null]){let n=0;await b.lecturaInforme(cache,'ausente',()=>{n++;return value},opts);await b.lecturaInforme(cache,'ausente',()=>{n++;return value},opts);assert.equal(n,2)}casos++;
 let n=0;const espera=defer();const p=b.lecturaInforme(cache,'paralelo',()=>{n++;return espera.promise},opts),q=b.lecturaInforme(cache,'paralelo',()=>{n++;return 8},opts);
 await Promise.resolve();assert.equal(n,1);espera.resolve(7);assert.equal(await p,7);assert.equal(await q,7);casos++;
 const vieja=defer();now=0;const a=b.lecturaInforme(cache,'carrera',()=>vieja.promise,opts);await Promise.resolve();now=11;
 assert.equal(await b.lecturaInforme(cache,'carrera',()=>9,opts),9);vieja.reject(Error('antigua'));await assert.rejects(a);assert.equal(await b.lecturaInforme(cache,'carrera',()=>99,opts),9);casos++;
 const anterior=defer();now=20;const anteriorP=b.lecturaInforme(cache,'respuesta-vieja',()=>anterior.promise,opts);await Promise.resolve();now=31;
 assert.equal(await b.lecturaInforme(cache,'respuesta-vieja',()=>10,opts),10);anterior.resolve(1);assert.equal(await anteriorP,1);assert.equal(await b.lecturaInforme(cache,'respuesta-vieja',()=>99,opts),10);casos++;
 now=1;assert.equal(await b.lecturaInforme(cache,'respuesta-vieja',()=>11,opts),11);casos++;
 const source=fs.readFileSync(path.join(__dirname,'modulos/informe.js'),'utf8');const trozo=source.slice(source.indexOf('async function periodo(ctx, pid)'),source.indexOf('const vp = a =>')).replace(/export /g,'');
 Object.assign(b,{CACHE:{periodo:new Map(),indice:new Map(),fila:new Map(),acciones:new Map()},MOD:'informe-cliente'});vm.runInContext(trozo,b);
 let intentos=0;const ctx={real:{id:'real'},persona:{id:'vista'},servidor:true,clientesVisibles:[{id:'c'}],datosModulo:async()=>{intentos++;if(intentos===1)throw Error('carga fallida');return {filas:[{cliente_id:'c'}]}},api:async()=>({acciones:[]})};
 await assert.rejects(b.periodo(ctx,'mes'));assert.equal((await b.periodo(ctx,'mes')).filas[0].cliente_id,'c');assert.equal(intentos,2);casos++;
 let apis=0;ctx.api=async()=>{apis++;if(apis===1)throw Error('red');return {acciones:[{cliente_id:'c'}]}};
 assert.equal((await b.acciones(ctx)).length,0);assert.equal((await b.acciones(ctx)).length,1);assert.equal(apis,2);casos++;
 let missing=0;ctx.datosModulo=async()=>{missing++;return {filas:[]}};assert.equal(await b.filaCliente(ctx,'m','c'),null);assert.equal(await b.filaCliente(ctx,'m','c'),null);assert.equal(missing,2);casos++;
 const revision=fs.readFileSync(path.join(__dirname,'modulos/informe_revisar.js'),'utf8').replace(/^import .*;$/gm,'').replace(/^export \{.*\} from .*;$/gm,'').replace(/export /g,'');
 class N{constructor(tag,attrs,kids){this.tag=tag;this.attrs=attrs||{};this.kids=kids.flat(Infinity).filter(x=>x!=null);this.value='';this.isConnected=true;this.textContent=''}append(...n){this.kids.push(...n.flat(Infinity))}replaceChildren(...n){this.kids=n.flat(Infinity)}addEventListener(){}scrollIntoView(){}}
 const h=(tag,attrs,...kids)=>new N(tag,attrs,kids);const walk=n=>[n,...(n.kids||[]).flatMap(x=>typeof x==='object'?walk(x):[])];
 async function panel(){
  let valid=true;const posts=[],pend=[],timers=[],cambios=[];const s={h,fmt:{num:String,eur:String},icono:()=>null,chipEstado:()=>h('chip'),vacioLinea:()=>h('vacio'),avisoFlotante:()=>{},variacion:()=>0,logoInforme:()=>null,exigirInformeVigente:b.exigirInformeVigente,
   botonDeshacer:o=>h('deshacer',o),filaCliente:async()=>({}),invalidarAccionesInforme:()=>{},analisisDe:()=>({actual:null}),borrador:()=>({mes:'Propuesta'}),avisosDe:()=>[],bloqueaPDF:()=>false,APARTADOS:[['mes','Mes']],RE_LEAD:/email-imposible/,enlacePeriodo:()=>null,
   estadoInforme:()=>({}),textoEstadoInforme:()=>'',setTimeout:f=>{timers.push(f)},queueMicrotask:()=>{}};
  vm.createContext(s);vm.runInContext(revision,s);
  const c={id:'c',nombre:'Cliente fixture'};const context={servidor:true,soloLectura:false,real:{id:'real'},vigente:()=>valid,nombre:()=>'',ver:()=>({ok:false}),datosModulo:async()=>({periodos:[{id:'m',texto:'Mes fixture'}]}),api:async(r,o)=>{if(!o)return {acciones:[]};posts.push(o.cuerpo);const d=defer();pend.push(d);return d.promise}};
  const node=await s.panelRevisar(context,{c,pid:'m'},{alCambio:async e=>cambios.push(e)});walk(node).find(x=>x.tag==='textarea').value='Análisis válido';
  return {node,posts,pend,timers,cambios,ctx:context,nav:()=>{valid=false},marcar:()=>walk(node).find(x=>x.tag==='deshacer').attrs.alHacer(),guardar:()=>walk(node).find(x=>x.tag==='button'&&x.kids.includes('Guardar borrador')).attrs.on.click()};
 }
 let r=await panel();let work=r.marcar();assert.equal(r.posts.length,1);r.nav();r.pend[0].resolve({id:1});await assert.rejects(work,/pantalla/);assert.equal(r.posts.length,1);assert.equal(r.cambios.length,0);assert.equal(r.timers.length,0);casos++;
 r=await panel();work=r.guardar();assert.equal(r.posts.length,1);r.nav();r.pend[0].resolve({id:1});await work;assert.equal(r.posts.length,1);assert.equal(r.cambios.length,0);casos++;
 r=await panel();r.node.isConnected=false;await assert.rejects(r.marcar(),/pantalla/);assert.equal(r.posts.length,0);casos++;
 r=await panel();work=r.marcar();r.pend[0].resolve({id:1});await new Promise(setImmediate);assert.equal(r.posts.length,2);r.nav();r.pend[1].resolve({id:2});await assert.rejects(work,/pantalla/);assert.equal(r.cambios.length,0);casos++;
 r=await panel();work=r.marcar();r.pend[0].resolve({id:1});await new Promise(setImmediate);r.pend[1].resolve({id:2});assert.match(await work,/Revisado/);assert.equal(r.posts.length,2);assert.equal(r.cambios.length,1);casos++;
 console.log(`${casos} grupos asíncronos de informe pasan`);
}
main().catch(e=>{console.error(e);process.exitCode=1});
