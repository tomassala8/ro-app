const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const src=fs.readFileSync('modulos/ficha.js','utf8');
const body=src.match(/  reunion\(z, ctx, F\) \{([\s\S]*?)\n  \},/)[1];
function el(){return{children:[],append(...a){this.children.push(...a)},replaceChildren(...a){this.children=a}}}
(async()=>{
let resolver;const espera=new Promise(r=>resolver=r),host=el(),history=el(),facts=el();let loaded=0;
const fn=vm.runInNewContext('(function(z,ctx,F){'+body+'})',{
 queueMicrotask,h:()=>el(),correosCliente:()=>[],pintarReunion:async z=>{z.replaceChildren('cargando');await espera;z.replaceChildren('hoja');},
 pintarHistorialReuniones:z=>z.append(history),permisoLecturaHechos:()=>true,
 crearRegistroHechos:()=>({nodo:facts,cargar:()=>loaded++}),panelBitacora:()=>Promise.resolve(el())
});
fn(host,{veModulo:()=>false},{c:{id:'fixture'}});assert.equal(loaded,0);await Promise.resolve();assert.equal(loaded,1);assert.deepEqual(host.children,[host.children[0],history,facts]);
resolver();await espera;await Promise.resolve();assert.equal(host.children[0].children[0],'hoja');assert.equal(host.children[1],history);assert.equal(host.children[2],facts);
host.children[0].replaceChildren('hoja guardada');assert.equal(host.children[2],facts);
console.log('161 PASS: carga tardía y repintado de la hoja conservan histórico y registro independientes.');
})().catch(e=>{console.error(e);process.exitCode=1});
