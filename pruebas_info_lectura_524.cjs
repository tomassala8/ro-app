// Metadata del transporte real: preservar fecha de recepción al recuperar copia.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const baseline=fs.readFileSync(__dirname+'/pruebas_estado_lectura_487.cjs','utf8');
const env=new Function('require','__dirname',baseline.slice(0,baseline.indexOf("const ruta='modulo/crm/crm'"))+';return env;')(require,__dirname);
const opts={yo:'a',como:'a'},ruta='acciones?modulo=captacion';
const res=n=>({status:200,text:JSON.stringify(n)});
const drain=async e=>{await Promise.all([...e.api.enVuelo.values()]);await new Promise(setImmediate);};
(async()=>{
 const e=env();await e.api.fijarPersonas('a','a');e.replies.push(res({n:2}));const info={};
 await e.api.pedirDato(ruta,{...opts,info});assert.equal(info.guardado,false);assert.equal(info.hora,Date.parse('2026-10-04T08:00:00Z'));
 e.advance();e.replies.push(Error('red'));const copia={};await e.api.pedirDato(ruta,{...opts,info:copia});await drain(e);
 assert.equal(copia.hora,info.hora);assert.equal(copia.guardado,true);
 const fallida={};await e.api.pedirDato(ruta,{...opts,info:fallida});assert.equal(fallida.hora,info.hora);assert(fallida.falloActualizacion);assert(fallida.ultimoIntento>=info.hora);
 console.log('PASS recepción original y recuperación con fallo no rejuvenecen copia');
 const sin=env();sin.replies.push(res({n:1}));const infoSin={};await sin.api.pedirDato('crm/ultima-valida',{...opts,info:infoSin});assert.equal(infoSin.guardado,false);assert(Number.isFinite(infoSin.hora));
 console.log('PASS recurso sin caché comunica sello de recepción HTTP');
 const concurrente=env();await concurrente.api.fijarPersonas('a','a');let resolve;const promise=new Promise(r=>resolve=r);concurrente.replies.push({promise});const uno={},dos={};
 const p=concurrente.api.pedirDato(ruta,{...opts,info:uno}),q=concurrente.api.pedirDato(ruta,{...opts,info:dos});resolve(res({n:4}));await Promise.all([p,q]);assert.equal(uno.hora,dos.hora);assert.equal(concurrente.calls,1);
 console.log('PASS lectura concurrente conserva un único sello original');
 const cambiado=env();await cambiado.api.fijarPersonas('a','a');let resolver;const pendiente=new Promise(r=>resolver=r);cambiado.replies.push({promise:pendiente});const anterior={};
 const consulta=cambiado.api.pedirDato(ruta,{...opts,info:anterior});await cambiado.api.fijarPersonas('b','b');resolver(res({n:3}));await assert.rejects(consulta,x=>x.status===409);assert.deepEqual(anterior,{});
 console.log('PASS cambio de identidad no publica metadata del resultado obsoleto');
 const app=fs.readFileSync(__dirname+'/app.js','utf8');const start=app.indexOf('async function api(');
 const body=app.indexOf("  if (!estado.servidor)",start);
 // Delimitación por siguiente declaración estable, sin importar la aplicación.
 const next=app.indexOf('\nfunction ',body);const fn=app.slice(start,next);
 const sandbox={estado:{servidor:true,real:{id:'a'},persona:{id:'a'}},pintura:{usadas:new Set()},medidorUso:null,
 pedirDato:async(_,o)=>{Object.assign(o.info,{hora:123,guardado:true});return {n:1};},estadoDatoCambiado487:()=>{}};
 vm.createContext(sandbox);vm.runInContext(fn+';this.call=api;',sandbox);const exposed={};await sandbox.call(ruta,{info:exposed});assert.equal(exposed.hora,123);
 console.log('PASS wrapper actual ctx.api transmite info sin cambiar DTO');
 console.log('5 grupos524 PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
