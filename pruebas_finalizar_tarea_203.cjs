const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c={};vm.createContext(c);vm.runInContext(fs.readFileSync(__dirname+'/modulos/_finalizar_tarea_203.js','utf8').replace(/export function /g,'function '),c);
let n=0;const t={lista_id:'exacta'},types={complete:'closed',rechazado:'done',completado:'custom',planning:'unstarted'};
const resolver=(t,e)=>({estado:types[e]?'verificado':'indeterminado',tipo:types[e],final_flujo:['closed','done'].includes(types[e])});
let r=c.destinosFinales203(t,{ok:true,destinos:['complete','rechazado','completado','planning']},resolver);assert.deepEqual(Array.from(r.destinos),['complete','rechazado']);n++;
r=c.destinosFinales203(t,{ok:true,destinos:['completado']},resolver);assert.equal(r.ok,false);assert.equal(r.destinos.length,0);n++;
for(const permiso of [null,{ok:false,destinos:['complete']},{ok:true,destinos:null}]){assert.equal(c.destinosFinales203(t,permiso,resolver).ok,false);n++;}
for(const falseTyped of [{estado:'indeterminado',tipo:'closed',final_flujo:true},{estado:'verificado',tipo:'custom',final_flujo:true},{estado:'verificado',tipo:'closed',final_flujo:false}]){assert.equal(c.destinosFinales203(t,{ok:true,destinos:['complete']},()=>falseTyped).ok,false);n++;}
r=c.destinosFinales203(t,{ok:true,destinos:['complete','complete']},resolver);assert.equal(r.destinos.length,1);assert(r.motivo.includes('no acredita entrega aceptada'));n++;
console.log(n+' pruebas helper203 PASS: tipos por lista, final≠nombre, sin aceptación, scope gate.');
