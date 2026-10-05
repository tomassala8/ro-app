// Fuente real, respuestas sintéticas; sin navegador, API, DB o datos privados.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'datos.js'),'utf8').replace(/^import .*$/gm,'').replace(/\bexport\s+/g,'');
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
function env(){
  let now=100000,calls=0;const queue=[],store=new Map(),diskWrites=[];
  const db={transaction(){const t={};t.objectStore=()=>({
    get:k=>operation(()=>store.get(k)),put:(v,k)=>operation(()=>{store.set(k,structuredClone(v));diskWrites.push(k);}),
    delete:k=>operation(()=>store.delete(k)),clear:()=>operation(()=>store.clear())});
    function operation(fn){const r={};queueMicrotask(()=>{r.result=fn();r.onsuccess?.();queueMicrotask(()=>t.oncomplete?.());});return r;}
    return t;}};
  const indexedDB={open(){const r={};queueMicrotask(()=>{r.result=db;r.onsuccess?.();});return r;}};
  const ctx={Date:{now:()=>now},self:{indexedDB},indexedDB,console,fetch:async()=>{
    calls++;let r=queue.shift();if(!r)throw Error('Fixture sin respuesta');if(r.promise)r=await r.promise;
    if(r instanceof Error)throw r;
    return {status:r.status??200,ok:(r.status??200)===200,headers:{get:()=>r.etag??'v1'},text:async()=>r.text};
  }};
  vm.runInNewContext(source+'\nthis.api={pedirDato,fijarPersonas,olvidarTodo,MEM,enVuelo,alCambiarDato};',ctx);
  return {api:ctx.api,queue,store,diskWrites,get calls(){return calls;},advance:()=>now+=6000};
}
const opts={yo:'a',como:'a'},route='modulo/fixture';
const response=(value,status=200)=>({status,text:JSON.stringify(value)});
async function drain(e){await Promise.all([...e.api.enVuelo.values()]);await new Promise(setImmediate);}
async function base(){const e=env();await e.api.fijarPersonas('a','a');e.queue.push(response({n:12}));await e.api.pedirDato(route,opts);await drain(e);e.advance();return e;}
let groups=0;
async function test(name,fn){await fn();groups++;console.log('PASS',name);}
(async()=>{
  await test('inicial malformado no se promueve y permite recuperar',async()=>{
    const e=env();e.queue.push({text:'JSON inválido'});await assert.rejects(e.api.pedirDato(route,opts),x=>x.name==='SyntaxError');
    assert.equal(e.api.MEM.size,0);e.queue.push(response({n:7}));assert.equal((await e.api.pedirDato(route,opts)).n,7);
  });
  await test('refresco malformado conserva bytes/fecha/ETag válidos y metadata',async()=>{
    const e=await base(),before=structuredClone([...e.api.MEM.values()][0]);e.queue.push({text:'{'});
    assert.equal((await e.api.pedirDato(route,opts)).n,12);await drain(e);
    const after=[...e.api.MEM.values()][0];assert.equal(after.texto,before.texto);assert.equal(after.hora,before.hora);assert.equal(after.etag,before.etag);
    const info={};assert.equal((await e.api.pedirDato(route,{...opts,info})).n,12);assert.ok(info.ultimoIntento);assert.ok(info.falloActualizacion);
    assert.equal(e.store.get('a|a|'+route).texto,before.texto);
  });
  await test('cero null false y colecciones vacías JSON legítimos',async()=>{
    for(const v of [0,null,false,[],{},'']){const e=env();e.queue.push(response(v));assert.equal(JSON.stringify(await e.api.pedirDato(route,opts)),JSON.stringify(v));assert.equal(e.api.MEM.size,1);}
    const e=await base();e.queue.push(response([]));await e.api.pedirDato(route,opts);await drain(e);assert.equal(JSON.stringify(await e.api.pedirDato(route,opts)),'[]');
  });
  await test('500 y red conservan última válida sin promover errores',async()=>{
    for(const r of [response({error:'fallo'},500),Error('red')]){const e=await base();e.queue.push(r);await e.api.pedirDato(route,opts);await drain(e);assert.equal((await e.api.pedirDato(route,opts)).n,12);}
  });
  await test('401 limpia todo;403 y404 eliminan entrada sin fallback',async()=>{
    for(const status of [401,403,404]){const e=await base();e.queue.push(response({error:'denegado'},status));await e.api.pedirDato(route,opts);await drain(e);assert.equal(e.api.MEM.size,0);assert.equal(e.store.has('a|a|'+route),false);
      e.queue.push(response({error:'denegado'},status));await assert.rejects(e.api.pedirDato(route,opts),x=>x.status===status);}
  });
  await test('304 conserva válido y borra fallo anterior',async()=>{
    const e=await base();e.queue.push(Error('red'));await e.api.pedirDato(route,opts);await drain(e);e.advance();e.queue.push({status:304});await e.api.pedirDato(route,opts);await drain(e);const info={};await e.api.pedirDato(route,{...opts,info});assert.equal(info.falloActualizacion,null);
  });
  await test('304 inicial no fabrica dato ni guarda',async()=>{
    const e=env();e.queue.push({status:304});await assert.rejects(e.api.pedirDato(route,opts));assert.equal(e.api.MEM.size,0);
  });
  await test('respuesta inicial tardía tras cambio real/vista no devuelve ni guarda',async()=>{
    for(const next of [['b','b'],['a','b']]){const e=env();await e.api.fijarPersonas('a','a');const d=deferred();e.queue.push(d);const p=e.api.pedirDato(route,opts);await new Promise(setImmediate);assert.equal(e.calls,1);await e.api.fijarPersonas(...next);d.resolve(response({n:99}));await assert.rejects(p,x=>x.status===409);await drain(e);assert.equal(e.api.MEM.size,0);assert.equal(e.store.has('a|a|'+route),false);}
  });
  await test('refresco tardío tras salir no guarda ni notifica',async()=>{
    const e=await base();let changed=0;e.api.alCambiarDato(()=>changed++);const d=deferred();e.queue.push(d);await e.api.pedirDato(route,opts);await e.api.olvidarTodo();d.resolve(response({n:99}));await new Promise(setImmediate);assert.equal(e.api.MEM.size,0);assert.equal(changed,0);assert.equal(e.store.has('a|a|'+route),false);
  });
  await test('401 tardío de identidad anterior no borra nueva lectura',async()=>{
    const e=await base(),d=deferred();e.queue.push(d);await e.api.pedirDato(route,opts);await e.api.fijarPersonas('b','b');e.queue.push(response({n:8}));await e.api.pedirDato(route,{yo:'b',como:'b'});d.resolve(response({error:'caducada'},401));await new Promise(setImmediate);assert.equal((await e.api.pedirDato(route,{yo:'b',como:'b'})).n,8);
  });
  await test('cache persistida inválida se elimina y se consulta de nuevo',async()=>{
    const e=env();await e.api.fijarPersonas('a','a');e.store.set('a|a|'+route,{texto:'{',etag:'malo',hora:1});e.queue.push(response({n:4}));assert.equal((await e.api.pedirDato(route,opts)).n,4);await drain(e);assert.equal(e.store.get('a|a|'+route).texto,'{"n":4}');
  });
  await test('peticiones iniciales concurrentes comparten lectura válida',async()=>{
    const e=env(),d=deferred();e.queue.push(d);const a=e.api.pedirDato(route,opts),b=e.api.pedirDato(route,opts);d.resolve(response({n:6}));assert.equal((await a).n,6);assert.equal((await b).n,6);assert.equal(e.calls,1);
  });
  await test('salida y vuelta misma identidad permiten lectura nueva sin esperar antigua',async()=>{
    const e=env();await e.api.fijarPersonas('a','a');const old=deferred(),fresh=deferred();e.queue.push(old);
    const p=e.api.pedirDato(route,opts);await new Promise(setImmediate);assert.equal(e.calls,1);
    await e.api.olvidarTodo();await e.api.fijarPersonas('a','a');
    e.queue.push(fresh);const q=e.api.pedirDato(route,opts);old.resolve(response({n:1}));await assert.rejects(p,x=>x.status===409);
    assert.equal(e.api.enVuelo.size,1);fresh.resolve(response({n:2}));assert.equal((await q).n,2);await drain(e);
    assert.equal(e.store.get('a|a|'+route).texto,'{"n":2}');
  });
  await test('fijarPersonas concurrentes no restaura dueño antiguo',async()=>{
    const e=env();await Promise.all([e.api.fijarPersonas('a','a'),e.api.fijarPersonas('b','b')]);
    e.queue.push(response({n:3}));await e.api.pedirDato(route,{yo:'b',como:'b'});await drain(e);
    assert.equal(e.store.get('__dueno'),'b');assert.equal(e.store.has('b|b|'+route),true);
  });
  await test('ver como permanece sólo memoria y rutas excluidas no persisten',async()=>{
    const e=env();await e.api.fijarPersonas('a','b');e.queue.push(response({n:3}));await e.api.pedirDato(route,{yo:'a',como:'b'});await drain(e);
    assert.equal(e.store.has('a|b|'+route),false);
    e.queue.push(response({n:4}));assert.equal((await e.api.pedirDato('sueldos',opts)).n,4);
    assert.equal(e.api.MEM.size,1);
  });
  console.log(`${groups} grupos PASS`);
})().catch(e=>{console.error(e);process.exitCode=1;});
