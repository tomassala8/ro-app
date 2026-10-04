const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{const m=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(__dirname+'/modulos/_horas_mi_trabajo_370.js','utf8')).toString('base64'));const E={V:{dias:{p:{'2026-10-02':{cu:1e308,app:1e308,cu_observado:true,app_observado:true}}}},local:[]};let n=0;const check=f=>{f();n++};
check(()=>{const x=m.horasDiaTrabajo370(E,'p','2026-10-02');assert.equal(x.valor,null);assert(x.datos_invalidos);assert(!m.textoHorasTrabajo370(x).includes('∞'))});
check(()=>{E.V.dias.p['2026-10-02']={cu:null,app:0};assert.equal(m.horasDiaTrabajo370(E,'p','2026-10-02').valor,null)});
check(()=>{E.V.dias.p['2026-10-02']={cu:0,app:1};const x=m.horasDiaTrabajo370(E,'p','2026-10-02');assert.equal(x.cu,null);assert.equal(x.valor,1)});
check(()=>{E.V.dias.p['2026-10-02']={cu:0,app:null,cu_observado:true,app_observado:false};const x=m.horasDiaTrabajo370(E,'p','2026-10-02');assert.equal(x.cu,0);assert.equal(x.valor,0);assert.equal(x.ro,null)});
check(()=>{E.V.dias.p['2026-10-02']={cu:null,app:0,cu_observado:false,app_observado:true};const x=m.horasDiaTrabajo370(E,'p','2026-10-02');assert.equal(x.valor,0);assert.equal(x.cu,null);assert.equal(x.ro,0)});
check(()=>{E.V.dias.p['2026-10-02']={cu:2,app:null,cu_observado:true,app_observado:false};E.local=Array.from({length:120},()=>({campo:'horas',dia:'2026-10-02',quien:'p',minutos:1e308}));const x=m.horasDiaTrabajo370(E,'p','2026-10-02');assert.equal(x.valor,null);assert(x.datos_invalidos)});
check(()=>{E.local=[];delete E.V.dias.p['2026-10-02'];assert.equal(m.horasDiaTrabajo370(E,'p','2026-10-02').valor,null)});
console.log(n+' contratos370B helper real PASS');})().catch(e=>{console.error(e);process.exitCode=1});
// Renderer actual: el contrato tipado RO-only no fabrica ClickUp cero.
const base370B=fs.readFileSync(__dirname+'/pruebas_tablero_mi_trabajo_181.cjs','utf8').split('const a=')[0];
new Function('require','__dirname',base370B+String.raw`
const sourceB=fs.readFileSync(__dirname+'/modulos/mi_trabajo.js','utf8');vm.runInContext(sourceB.slice(sourceB.indexOf('function lineaDia('),sourceB.indexOf('function grupos('))+sourceB.slice(sourceB.indexOf('function bloqueTuDia('),sourceB.indexOf('function coberturaTrabajo(')),c);
const e={ctx:{persona:{id:'p'},hoy:'2026-10-03',nombre:x=>x,clientes:[],servidor:true},D:{tareas:[]},V:{yo:'p',hoy:'2026-10-03',dias:{p:{'2026-10-03':{cu:null,app:1,cu_observado:false,app_observado:true}}},jornada:[],raras:[]},local:[]};
const rendered=text(c.bloqueTuDia(e,()=>{}));assert(rendered.includes('ClickUp: sin registros'));assert(rendered.includes('declaraciones RO: 1'));assert(!rendered.includes('ClickUp: 0'));console.log('370B renderer real RO-only PASS');
`)(require,__dirname);
