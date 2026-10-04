const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync('modulos/panel_direccion.js','utf8'),b={};vm.createContext(b);vm.runInContext(src.slice(src.indexOf('function panelNominal249('),src.indexOf('async function pintar(cont')),b);
const tomas={id:'tomas',estado:'activo',puestos:['direccion']},otro={id:'nuevo',estado:'activo',puestos:['direccion']};
const ctx={real:{...tomas},persona:{...tomas},datos:{personas:[{...tomas}]}};
assert.equal(b.panelNominal249(ctx),true);let n=1;
for(const [real,persona]of[[otro,otro],[otro,tomas],[tomas,otro]]){assert.equal(b.panelNominal249({...ctx,real,persona}),false);n++}
for(const ps of[[],[tomas,tomas],[{...tomas,estado:'baja'}],[{...tomas,activo:false}],[{...tomas,puestos:[]}],null]){assert.equal(b.panelNominal249({...ctx,datos:{personas:ps}}),false);n++}
const reads=[];Object.assign(b,{vacio:o=>o,cargar:async()=>{reads.push(1);throw Error('No leer')},h:()=>({})});
vm.runInContext(src.slice(src.indexOf('async function pintar(cont'),src.indexOf('// ===================================================================== Resumen v4')),b);
(async()=>{const appended=[];await b.pintar({classList:{add:()=>{}},append:x=>appended.push(x)},{...ctx,real:otro,persona:otro});assert.equal(reads.length,0);assert.equal(appended[0].titulo,'Solo Tomás');n++;console.log(n+' grupos249 UI PASS: nominal/canónico/revocado/viewas y denegado sinlecturas.');})().catch(e=>{console.error(e);process.exitCode=1});
