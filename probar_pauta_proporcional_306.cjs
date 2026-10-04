const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const c={Date,Number};vm.createContext(c);vm.runInContext(fs.readFileSync(__dirname+'/modulos/_pauta_proporcional_306.js','utf8').replace('export ',''),c);
const fn=c.pautaProporcional306,p={origen:'referencia_economica',presupuesto_confirmado:false,horas:21,periodo:'2026-10',porcentaje:999},r={desde:'2026-10-01',hasta:'2026-10-03'},m={valor:5,periodo:'2026-10'};let n=0;
function test(name,f){f();n++;}
test('octubre parcial aplica referencia original /21 sin mutación',()=>{const before=JSON.stringify(p),x=fn(p,r,'2026-10-03',m);assert.equal(x.horas,2);assert.equal(x.mensual_ref,21);assert.equal(x.porcentaje,250);assert.equal(JSON.stringify(p),before);});
test('fin de semana sin división y sin cero cumplimiento',()=>{const x=fn(p,{desde:'2026-10-03',hasta:'2026-10-04'},'2026-10-04',m);assert.equal(x.horas,0);assert.equal(x.porcentaje,null);});
test('no mezclar periodos de pauta y horas',()=>{assert.equal(fn(p,{desde:'2026-09-28',hasta:'2026-10-03'},'2026-10-03',m),null);assert.equal(fn(p,r,'2026-10-03',{...m,periodo:'2026-09'}).porcentaje,null);});
test('no pauta futura/rango inválido',()=>{for(const q of [{desde:'2026-10-01',hasta:'2026-10-04'},{desde:'2026-10-03',hasta:'2026-10-01'},{desde:'2026-02-30',hasta:'2026-10-01'}])assert.equal(fn(p,q,'2026-10-03',m),null);});
test('no medida heredada o contractual',()=>{for(const q of [{...p,origen:'otro'},{...p,presupuesto_confirmado:true},{...p,horas:NaN},{...p,horas:true}])assert.equal(fn(q,r,'2026-10-03',m),null);});
test('ausencia nunca se restaura desde porcentaje previo',()=>{assert.equal(fn(p,r,'2026-10-03',{valor:null,periodo:p.periodo}).porcentaje,null);assert.equal(fn(p,r,'2026-10-03',{valor:false,periodo:p.periodo}).porcentaje,null);});
test('mes histórico completo sigue referencia laboral original',()=>{const x=fn({...p,periodo:'2026-09'},{desde:'2026-09-01',hasta:'2026-09-30'},'2026-10-03',{valor:22,periodo:'2026-09'});assert.equal(x.laborables,22);assert.equal(x.horas,22);assert.equal(x.porcentaje,100);});
console.log(n+' casos306 PASS');
