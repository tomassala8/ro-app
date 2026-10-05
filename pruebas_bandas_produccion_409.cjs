const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
const base=fs.readFileSync(path.join(__dirname,'pruebas_produccion_baseline.cjs'),'utf8');
const harness=base.slice(0,base.indexOf('let live='));
const checks=`
let checks=0;const check=fn=>{fn();checks++;};
const m=(valor,more={})=>({valor,cohorte:'256:fixture:2026-10-03T13:08:00Z:bloqueadas',referencia:false,...more});
check(()=>{for(const [key,w,b] of [['account_48',1,6],['tecnica_48',3,10],['bloqueadas',1,5],['sin_mes',1,2],['no_plan',3,8]]){for(const [v,color] of [[0,null],[w-1,null],[w,'ambar'],[b-1,'ambar'],[b,'rojo'],[b+1,'rojo']])assert.equal(c.bandaProduccion409(m(v),key,'account'),color,key+':'+v);}});
check(()=>{for(const v of [null,undefined,-1,.5,Infinity,NaN,true,'5'])assert.equal(c.bandaProduccion409(m(v),'bloqueadas','account'),null);});
check(()=>{for(const more of [{referencia:true},{cohorte:null},{cohorte:'sin prueba'},{medidos:0,total:8},{medidos:2,total:1}])assert.equal(c.bandaProduccion409(m(8,more),'bloqueadas','account'),null);});
check(()=>{assert.equal(c.bandaProduccion409(m(5,{medidos:1,total:8}),'bloqueadas','account'),'rojo');assert.equal(c.bandaProduccion409(m(0,{medidos:1,total:8}),'bloqueadas','account'),null);});
check(()=>{for(const key of ['account','tecnica','bloqueadas']){assert.equal(c.bandaProduccion409(m(8,{mas48:null}),key,'proyecto'),null);assert.equal(c.bandaProduccion409(m(8,{mas48:0}),key,'proyecto'),null);assert.equal(c.bandaProduccion409(m(8,{mas48:1}),key,'proyecto'),'rojo');assert.equal(c.bandaProduccion409(m(8,{mas48:9}),key,'proyecto'),null);}});
check(()=>{assert.equal(c.bandaProduccion409(m(4),'no_plan','proyecto'),null);assert.equal(c.bandaProduccion409(m(5),'no_plan','proyecto'),'ambar');for(const key of ['cliente','creadas_mes','creadas_semana','cerradas_semana'])assert.equal(c.bandaProduccion409(m(99),key,'account'),null);});
check(()=>{const x=c.sumarMetricaBaseline([m(4),m(1)],2);assert.equal(c.bandaProduccion409(x,'bloqueadas','account'),'rojo');const mixed=c.sumarMetricaBaseline([m(4),m(1,{cohorte:'256:otra:fecha:bloqueadas'})],2);assert.equal(mixed.valor,null);assert.equal(c.bandaProduccion409(mixed,'bloqueadas','account'),null);});
check(()=>{const table=c.tablaProduccionBaseline({h,ambito:'account',titulo:'Por account',filas:[{}],columnas:[{titulo:'Bloqueadas',clave:'bloqueadas',valor:()=>m(5,{medidos:1,total:8})}]});const span=all(table,n=>n.tag==='span')[0];assert(span.attrs.class.includes('pb-cell-rojo'));assert.equal(text(span),'5');assert(span.attrs.title.includes('referencia del artifact'));assert(span.attrs.title.includes('1/8'));assert(!span.attrs.class.includes('verde'));});
check(()=>{const table=c.tablaProduccionBaseline({h,ambito:'account',titulo:'Por account',filas:[{}],columnas:[{titulo:'Bloqueadas',clave:'bloqueadas',valor:()=>m(8,{referencia:true})}]});const span=all(table,n=>n.tag==='span')[0];assert.equal(text(span),'8');assert(!span.attrs.class.includes('pb-cell-rojo'));assert(span.attrs.title.includes('Referencia de copia'));});
check(()=>{const d=doc(),p=proyecto();d.proyectos=[p];const raw=JSON.parse(fs.readFileSync(path.join(__dirname,'../RECUPERACION_CODEX_2026-10-03/staging_produccion_typed_256/produccion.json'),'utf8'));p._evidencia_produccion_256=JSON.parse(JSON.stringify(raw.proyectos.find(p=>p._evidencia_produccion_256)._evidencia_produccion_256));p._evidencia_produccion_256.cliente_id=p.cliente_id;const metrics=c.metricasProyectoBaseline(p,d);assert.equal(metrics.account.mas48,null);assert.equal(c.bandaProduccion409(metrics.account,'account','proyecto'),null);assert.equal(c.bandaProduccion409(metrics.no_plan,'no_plan','account'),null);});
console.log(checks+' grupos bandas Producción409 PASS');
`;
vm.runInNewContext(harness+checks,{require,__dirname,console},{filename:__filename});

// Consumidor REAL: todas las claves corresponden a su dimensión, no al texto del encabezado.
const integrado=base.replace(/console.log\(`\$\{total\} grupos baseline252 PASS`\);/, '')+`
let integration=0;
d.proyectos=rows;d.revisiones=Array.from({length:5},(_,i)=>({id:'bloqueo-'+i,cliente_id:'c',estado:'bloqueado',dias:4,mas48:true}));
rows[0]._revision_account={n:6,mas48:6,fecha:'2026-10-02 09:16'};
rows[0]._revision_tecnica={n:10,mas48:10,fecha:'2026-10-02 09:16'};
render();
const tb=all(root,x=>x.tag==='table'),ar=all(tb[0],x=>x.tag==='tbody')[0].children[0],pr=all(tb[1],x=>x.tag==='tbody')[0].children[0];
for(const index of [3,5,6]){const cells=ar.children;assert(all(cells[index],x=>x.tag==='span').some(x=>x.attrs.class.includes('pb-cell-rojo')));integration++;}
for(const index of [1,2,3]){assert(all(pr.children[index],x=>x.tag==='span').some(x=>x.attrs.class.includes('pb-cell-rojo')));integration++;}
rows[1]._revision_account={n:4,mas48:4,fecha:'2026-10-01 09:16'};render();
const sum=c.sumarMetricaBaseline(rows.map(p=>c.metricasProyectoBaseline(p,d).account),2,'mas48');assert.equal(sum.valor,null);integration++;
console.log(integration+' comprobaciones consumidor409 PASS');
`;
vm.runInNewContext(integrado,{require,__dirname,console},{filename:__filename});
