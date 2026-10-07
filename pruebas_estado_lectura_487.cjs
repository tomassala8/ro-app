// Eventos de transporte y fragmento real app.js; sin navegador ni peticiones reales.
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert/strict');
const datos=fs.readFileSync(path.join(__dirname,'datos.js'),'utf8').replace(/^import .*$/gm,'').replace(/\bexport\s+/g,'');
const app=fs.readFileSync(path.join(__dirname,'app.js'),'utf8');
const uiSource=app.slice(app.indexOf('// 487 ·'),app.indexOf('// Fin 487'));
class N{constructor(tag,attrs={},kids=[]){this.tag=tag;this.attrs=attrs;Object.assign(this,attrs);this.children=[];this.hidden=false;kids.flat(Infinity).filter(x=>x!==null&&x!==undefined).forEach(x=>this.append(x));}
 append(x){if(typeof x==='object')x.parent=this;this.children.push(x);}
 querySelector(s){return this.children.find(x=>x.attrs?.['data-lecturas-487'])||null;}
 remove(){this.parent.children=this.parent.children.filter(x=>x!==this);}
 get textContent(){return this.text??this.children.map(x=>typeof x==='string'?x:x.textContent).join('');}set textContent(v){this.text=v;this.children=[];}}
function env(){let now=Date.parse('2026-10-04T08:00:00Z'),calls=0;const replies=[],events=[];
 const D=class extends Date{static now(){return now;}};
 const ctx={Date:D,self:{},console,fetch:async()=>{calls++;let r=replies.shift();if(r?.promise)r=await r.promise;if(r instanceof Error)throw r;
 return {status:r.status??200,ok:(r.status??200)===200,text:async()=>r.text,headers:{get:()=>null}};}};
 vm.runInNewContext(datos+'\nthis.api={pedirDato,fijarPersonas,olvidarTodo,alCambiarDato,alCambiarEstadoDato,enVuelo};',ctx);
 const badge=new N('span'),detail=new N('details');const pintura={usadas:new Set(['modulo/crm/crm']),estadosLectura:new Map(),guardado:null};
 const uctx={Date:D,Number,document:{getElementById:id=>id==='dato-guardado'?badge:id==='frescura'?detail:null},
 pintura,fechas:{hora:s=>s.slice(11,16)},h:(t,a,...k)=>new N(t,a,k),alCambiarEstadoDato:ctx.api.alCambiarEstadoDato};
 vm.runInNewContext(uiSource+'\nthis.ui={estadoDatoCambiado487,estadoGuardado487,marcarGuardado};',uctx);
 ctx.api.alCambiarEstadoDato((r,m)=>events.push([r,m]));
 return {api:ctx.api,ui:uctx.ui,badge,detail,pintura,replies,events,get calls(){return calls;},advance:()=>now+=6000};}
const ruta='modulo/crm/crm',opts={yo:'a',como:'a'},res=(n,status=200)=>({status,text:JSON.stringify(n)});
async function drain(e){await Promise.all([...e.api.enVuelo.values()]);await new Promise(setImmediate);}
async function base(){const e=env();await e.api.fijarPersonas('a','a');e.replies.push(res({n:2}));await e.api.pedirDato(ruta,opts);e.advance();return e;}
let n=0;async function test(label,fn){await fn();n++;console.log('PASS',label);}
(async()=>{
 await test('fallo metadata sin cambio dato, repintado ni nueva petición',async()=>{const e=await base();let changes=0;e.api.alCambiarDato(()=>changes++);
  e.replies.push(Error('token secreto fixture'));await e.api.pedirDato(ruta,opts);await drain(e);assert.equal(e.calls,2);assert.equal(changes,0);
  assert.match(e.badge.textContent,/Última lectura válida 08:00 · actualización sin confirmar/);assert.equal(e.badge.hidden,false);
  assert.match(e.detail.textContent,/CRM · lectura válida/);assert.match(e.detail.textContent,/último intento 08:00/);assert.doesNotMatch(e.detail.textContent,/secreto|modulo\//);
 });
 await test('304 limpia fallo sin fabricar fecha proveedor',async()=>{const e=await base();e.replies.push(Error('red'));await e.api.pedirDato(ruta,opts);await drain(e);e.advance();
  e.replies.push({status:304});await e.api.pedirDato(ruta,opts);await drain(e);assert.equal(e.pintura.estadosLectura.size,0);assert.equal(e.detail.children.length,0);assert.equal(e.badge.hidden,true);
 });
 await test('éxito nuevo borra fallo y fecha previa',async()=>{const e=await base();e.replies.push({text:'{'});await e.api.pedirDato(ruta,opts);await drain(e);e.advance();e.replies.push(res({n:3}));await e.api.pedirDato(ruta,opts);await drain(e);assert.equal(e.detail.children.length,0);assert.equal(e.badge.hidden,true);});
 await test('401 403 404 limpian fallo y no conservan badge guardado denegado',async()=>{for(const status of [401,403,404]){const e=await base();e.replies.push(Error('red'));await e.api.pedirDato(ruta,opts);await drain(e);e.pintura.guardado={hora:Date.now(),ruta};e.advance();e.replies.push(res({error:'no'},status));await e.api.pedirDato(ruta,opts);await drain(e);assert.equal(e.badge.hidden,true);assert.equal(e.detail.children.length,0);}});
 await test('ruta no usada no publica metadatos y retorno tardío tras identidad no avisa',async()=>{const e=await base();e.pintura.usadas.clear();e.replies.push(Error('red'));await e.api.pedirDato(ruta,opts);await drain(e);assert.equal(e.badge.hidden,true);
  e.pintura.usadas.add(ruta);e.advance();let resolve;const promise=new Promise(r=>resolve=r);e.replies.push({promise});await e.api.pedirDato(ruta,opts);await e.api.fijarPersonas('b','b');const before=e.events.length;resolve(res({n:9}));await new Promise(setImmediate);assert.equal(e.events.length,before);assert.equal(e.detail.children.length,0);
 });
 await test('privados no emiten; label nunca imprime ruta query ID ni mensaje',async()=>{const e=env();e.replies.push(res({n:1}));await e.api.pedirDato('modulo/_privado/fixture',opts);assert.equal(e.events.length,0);
  const key='cliente/fixture-ID?token=no-publicar';e.pintura.usadas.add(key);e.ui.estadoDatoCambiado487(key,{hora:Date.now(),ultimoIntento:Date.now(),falloActualizacion:'secreto'});
  assert.match(e.detail.textContent,/Detalle de cliente/);assert.doesNotMatch(e.detail.textContent,/fixture-ID|token|secreto/);
 });
 await test('cero vacío éxito no verde ni fallo ficticio',async()=>{for(const v of [0,[],null]){const e=env();e.replies.push(res(v));await e.api.pedirDato(ruta,opts);assert.equal(e.badge.hidden,true);assert.equal(e.detail.children.length,0);}});
 await test('fechas finitas fuera rango y callbacks revocados no muestran error',async()=>{const e=env();e.ui.estadoDatoCambiado487(ruta,{hora:1e300,ultimoIntento:1e300,falloActualizacion:true});assert.equal(e.badge.hidden,true);
  e.pintura.usadas.clear();e.ui.estadoDatoCambiado487(ruta,{hora:Date.now(),ultimoIntento:Date.now(),falloActualizacion:true});assert.equal(e.detail.children.length,0);
 });
 await test('finally real preserva fallo y navegación real limpia mapa',async()=>{
  assert.ok(app.includes('marcarGuardado(estadoGuardado487())'));
  const timer=app.match(/else if \(pintura\.guardado\) setTimeout\(\(\) => \{.*\}, 6000\);/)[0];
  const e=env();e.pintura.guardado={hora:Date.now(),ruta};e.ui.estadoDatoCambiado487(ruta,{hora:Date.now(),ultimoIntento:Date.now(),falloActualizacion:true});let cb;
  vm.runInNewContext('if(false){} '+timer,{pintura:e.pintura,setTimeout:fn=>cb=fn,vigente:()=>true,...e.ui});cb();assert.equal(e.badge.hidden,false);
  const nav=app.slice(app.indexOf('  pintura.estadosLectura.clear();',app.indexOf('async function ruta(')),app.indexOf('  const vigente =',app.indexOf('async function ruta(')));
  vm.runInNewContext(nav,{pintura:e.pintura,...e.ui,detalleLecturas487:()=>e.detail.querySelector('[data-lecturas-487]')?.remove()});assert.equal(e.badge.hidden,true);assert.equal(e.pintura.estadosLectura.size,0);
 });
 console.log(n+' grupos487 PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
