const fs=require('fs'),vm=require('vm'),assert=require('assert');
const b={};vm.createContext(b);vm.runInContext(fs.readFileSync(__dirname+'/modulos/_cierre_artifact_253.js','utf8').replace(/export /g,''),b);
let n=0;function test(name,fn){fn();n++;console.log('PASS '+name)}
const row=(id,h,p)=>({cliente_id:id,nombre:id,account_id:'ops',reales:h,pautadas:p,pct:h!==null&&p>0?h/p*100:null});
test('subtotales separados y ratio sólo pares iguales',()=>{const s=b.resumenCierre361([row('a',20,10),row('b',30,null),row('c',null,90)]);assert.equal(s.reales,50);assert.equal(s.pautadas,100);assert.equal(s.comparables,1);assert.equal(s.ratio,200);assert.equal(s.medidos,2);assert.equal(s.pautados,2)});
test('ratio ponderado, no media de porcentajes',()=>{assert.equal(b.resumenCierre361([row('a',20,10),row('b',30,90)]).ratio,50)});
test('sin medición ni pauta no cero ni comparación',()=>{const s=b.resumenCierre361([row('a',null,null)]);assert.equal(s.reales,null);assert.equal(s.pautadas,null);assert.equal(s.ratio,null)});
test('cero legacy no confirma medición',()=>{assert.equal(b.resumenCierre361([row('a',0,10)]).reales,null)});
test('duplicado y entrada inválida no subtotal',()=>{assert.equal(b.resumenCierre361([row('a',1,1),row('a',1,1)]),null);assert.equal(b.resumenCierre361(null),null)});
test('sumas desbordadas no ratio',()=>assert.equal(b.resumenCierre361([row('a',1e308,1),row('b',1e308,1)]),null));
test('ratio no finito queda desconocido',()=>{assert.equal(b.resumenCierre361([row('a',1e308,1e-308)]).ratio,null)});
test('mes distinto e inactivos quedan fuera de agregados',()=>{const rs=b.prepararCierre253({mes_horas:'2026-09',mes_cuota:'2026-10',clientes:[{cliente_id:'a',coste_horas:{sep:10},cuota_horas:{pautadas:10}},{cliente_id:'b',coste_horas:{sep:100},cuota_horas:{pautadas:100}}]},[{id:'a',activo_confirmado:true},{id:'b',activo_confirmado:false}]);const s=b.resumenCierre361(rs);assert.equal(s.reales,10);assert.equal(s.pautadas,null);assert.equal(s.ratio,null);assert.equal(s.clientes,1)});
function h(tag,attrs,...kids){return {tag,attrs,kids:kids.flat(Infinity),append(...xs){this.kids.push(...xs.flat(Infinity))}}}
function walk(x){return !x||typeof x!=='object'?[]:[x,...(x.kids||[]).flatMap(walk)]}
function text(x){return typeof x==='string'?x:(x?.kids||[]).map(text).join(' ')}
function render(values){return b.pintarCierre253({h,d:{mes_horas:'2026-09',mes_cuota:'2026-09',clientes:values.map(([id,hrs,p])=>({cliente_id:id,nombre:id,account_id:'ops',coste_horas:{sep:hrs},cuota_horas:{pautadas:p}}))},clientes:values.map(([id])=>({id,activo_confirmado:true})),verdad:()=>null,nombre:()=> 'Ops'})}
test('render siete columnas y subtotal con cobertura',()=>{const tree=render([['a',20,10],['b',30,null]]);assert.equal(walk(tree).filter(x=>x.tag==='th').length,7);const s=walk(tree).find(x=>x.attrs?.['data-cierre-resumen']==='361');assert(text(s).includes('≥50 h observadas'));assert(text(s).includes('10 h pautadas'));assert(text(s).includes('1/2 comparables'));assert(!text(tree).includes('€'))});
test('exceso parcial rojo y mínimo bajo sin falso verde/amarillo',()=>{let tree=render([['a',20,10]]);assert(walk(tree).filter(x=>x.attrs?.class==='ratio361 rojo').length===2);tree=render([['a',1,10]]);const ratios=walk(tree).filter(x=>x.attrs?.class?.startsWith('ratio361'));assert.equal(ratios.length,2);assert(ratios.every(x=>x.attrs.class==='ratio361'));assert(text(tree).includes('≥10 % ref.'))});
test('sin pauta muestra falta de comparación',()=>{assert(text(render([['a',10,null]])).includes('Sin comparación del mismo mes'))});
console.log(n+' grupos cierre361 PASS');
