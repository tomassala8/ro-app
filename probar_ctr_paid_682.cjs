const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {e,N,h}=require('./fixture_harness_ctr_682.cjs');
e.tiles=x=>h('div',{},x);e.tile=o=>h('div',{},o.valor);e.contadorObservado648=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0?x:null;
const renderDense=e.tablaDensa;
let model;e.tablaDensa=o=>(model=o,h('table',{}));e.tablaApilable=o=>{if(o.columnas.some(c=>c.clave==='ctr'))model=o;return h('table',{});};
const ctx={soloLectura:true,nivel:'todo',vigente:()=>true,navegar:()=>{}};
function creative(ad){e.pCreatividades(h('main',{}),ctx,{},[{cliente_id:'fixture',nombre:'Fixture',dinero:false,anuncios:{anuncios:[ad]}}]);return model;}
function detail(ad){e.tAnuncios(h('main',{}),ctx,{}, {cliente_id:'fixture',dinero:false,anuncios:{anuncios:[ad],problemas:[]}});return model;}
let n=0;const test=f=>{f();n++;};const text=x=>x instanceof N?x.textContent:x;
for(const render of [creative,detail]){
 test(()=>{const m=render({ctr_7d:2,ctr_previo:0,caida_ctr_pct:Infinity});const col=m.columnas.find(c=>['ctr','ctr_7d'].includes(c.clave));assert.equal(col.titulo,'CTR tot.');assert(col.tituloCompleto.includes('clics totales / impresiones'));const c=col.celda(m.filas[0]);assert.equal(text(c),'2 %');assert(c.attrs.title.includes('Periodo anterior: 0 %'));assert(c.attrs.title.includes('referencia'));assert(c.attrs['aria-label'].includes('CTR total'));assert(!text(c).includes('Infinity'));assert(!text(c).includes('−'));});
 for(const val of [undefined,null,true,false,'2',NaN,Infinity,-1])test(()=>{const m=render({ctr_7d:val});const cell=m.columnas.find(c=>['ctr','ctr_7d'].includes(c.clave)).celda(m.filas[0]);assert.equal(text(cell),'—');assert(!cell.attrs['aria-label'].includes('0 por ciento'));});
 for(const val of [0,0.01,100,200,100.01])test(()=>{const m=render({ctr_7d:val});const cell=m.columnas.find(c=>['ctr','ctr_7d'].includes(c.clave)).celda(m.filas[0]);assert.equal(text(cell),`${val} %`);assert(cell.attrs.title.includes('no acredita CTR de enlace'));assert(!String(cell.attrs.class).includes('verde'));});
 test(()=>{const row={ctr_7d:2,ctr_previo:'4',caida_ctr_pct:50};const original=JSON.stringify(row);const m=render(row);const cell=m.columnas.find(c=>['ctr','ctr_7d'].includes(c.clave)).celda(m.filas[0]);assert.equal(text(cell),'2 %');assert(!cell.attrs.title.includes('anterior: 4'));assert.equal(JSON.stringify(row),original);});
}
test(()=>{const m=creative({ctr_7d:2});assert.equal(m.columnas.length,8);assert.equal(text(m.columnas.find(c=>c.clave==='cpl_7d').celda({dinero:false})),'—');const d=detail({ctr_7d:2});assert.equal(d.columnas.length,8);});
test(()=>{const m=creative({ctr_7d:2,ctr_previo:0,nombre:'Fixture'});const table=renderDense(m);const nodes=table.desc();assert(nodes.some(n=>n.tag==='th'&&n.textContent.includes('CTR tot.')));assert(nodes.some(n=>n.attrs.title?.includes('clics totales / impresiones')));assert(table.textContent.includes('2 %'));});
for(const render of [creative,detail])for(const base of [{impresiones_7d:0},{impresiones_7d:null},{impresiones_7d:'1'},{impresiones_7d:true},{impresiones_7d:Infinity},{impresiones_7d:-1},{clics_7d:'2'},{clics_7d:NaN}])test(()=>{const m=render({ctr_7d:200,...base});assert.equal(text(m.columnas.find(c=>['ctr','ctr_7d'].includes(c.clave)).celda(m.filas[0])),'—');});
for(const render of [creative,detail])test(()=>{const m=render({ctr_7d:200,impresiones_7d:1,clics_7d:2});const c=m.columnas.find(c=>['ctr','ctr_7d'].includes(c.clave)).celda(m.filas[0]);assert.equal(text(c),'200 %');assert(c.attrs.title.includes('clics no únicos'));assert(c.attrs.title.includes('puede superar 100 %'));});
// Baseline function bodies reproduce defects, in a separate VM and same DOM harness.
const old=fs.readFileSync('fixturebaseline_captacion_682.js','utf8');
vm.runInContext(old.slice(old.indexOf('function tAnuncios('),old.indexOf('function tMetas(')),e);
test(()=>{const m=detail({ctr_7d:null,ctr_previo:0});assert.equal(m.columnas.find(c=>c.clave==='ctr').titulo,'% de clics');assert.equal(text(m.columnas.find(c=>c.clave==='ctr').celda(m.filas[0])),'— %');});
test(()=>{const m=detail({ctr_7d:-1,ctr_previo:0});assert.equal(text(m.columnas.find(c=>c.clave==='ctr').celda(m.filas[0])),'-1 %');});
console.log(n+' grupos682 PASS: render real de las dos tablas, CTR total/entrada tipada/previo0/legacy gris/unknown y baseline antes.');
