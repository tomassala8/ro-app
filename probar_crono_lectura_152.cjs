const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync(__dirname+'/modulos/mi_trabajo.js','utf8');
const inicio=source.indexOf('function botonCrono(E, t) {'),fin=source.indexOf('\n}\n',inicio)+2;
assert(inicio>=0&&fin>inicio);
const sandbox={h:(tag,attrs)=>({tag,attrs}),icono:()=>null,esMovil:()=>false};vm.createContext(sandbox);vm.runInContext(source.slice(inicio,fin)+';this.boton=botonCrono;',sandbox);
(async()=>{
 let posts=0;const ctx={servidor:true,soloLectura:true,vigente:()=>true,api:async()=>{posts++;}};
 const E={V:{crono:null},ctx,vigente:()=>true},t={id:'ficticia',tarea:'Tarea ficticia'};
 let b=sandbox.boton(E,t);assert.equal(b.attrs.disabled,true);await b.attrs.on.click({currentTarget:{}});assert.equal(posts,0);
 ctx.soloLectura=false;ctx.vigente=()=>false;b=sandbox.boton(E,t);await b.attrs.on.click({currentTarget:{}});assert.equal(posts,0);
 ctx.vigente=()=>true;ctx.servidor=false;b=sandbox.boton(E,t);assert.equal(b.attrs.disabled,true);await b.attrs.on.click({currentTarget:{}});assert.equal(posts,0);
 console.log('152 PASS: cronómetro de consulta/offline desactivado y guardia evita POST incluso si se invoca el manejador o se revoca la pantalla.');
})().catch(e=>{console.error(e);process.exitCode=1;});
