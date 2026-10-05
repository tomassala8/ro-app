const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {e,N,h}=require('./fixture_harness_paid_687.cjs');
const realTable=e.tablaDensa;let model;e.tablaDensa=o=>(model=o,realTable(o));
const actor={id:'actor',estado:'activo',puestos:['trafficker']};
const c={cliente_id:'c1',nombre:'Fixture',gravedad:'atencion',severidad:'dato',equipo:{trafficker:'actor'},meta_activa:true,dinero:false,leads:{},gasto:{},motivos:[],panelEspecialista:{real:null,objetivo:null,hasta:null,racha:null,creativos:null,accion:'Contrastar'}};
const ctx={nivel:'todo',soloLectura:true,hoy:'2026-10-04',navegar(){},fechas:{esHoy:()=>false},vigente:()=>true};
const d={parametros:{},bitacora:new Map(),anuncios_generado:'2026-10-03T08:00:00Z'};
const one={ad_id:'ad1',cansada:true,vigilar:false,senales:['Frecuencia','Caída CTR']};
const two={ad_id:'ad2',cansada:false,vigilar:true,senales:['Frecuencia']};
const nodes=(n)=>n instanceof N?[n,...n.children.flatMap(nodes)]:[];
const render=(anuncios,data=d)=>{const root=h('main',{});e.pCuentas(root,ctx,data,[{...c,anuncios}],{},{});return {root,col:model.columnas.find(x=>x.clave==='creativos'),row:model.filas[0],model};};
let n=0;const test=f=>{f();n++;};
test(()=>{const {root,col,row,model}=render({anuncios:[one]});assert.equal(row.creativos508.valor,1);assert.equal(col.celda(row).textContent,'1');assert.equal(col.titulo,'Anun.');assert(col.tituloCompleto.includes('cada anuncio se cuenta una vez'));assert(col.celda(row).attrs.title.includes('no la cantidad de señales'));assert(nodes(root).some(x=>x.tag==='th'&&x.textContent==='Anun.'));assert.equal(model.columnas.length,9);});
test(()=>{const {col,row}=render({anuncios:[one,two]});assert.equal(col.celda(row).textContent,'2');assert.equal(one.senales.length+two.senales.length,3);});
test(()=>{const {col,row}=render({anuncios:[{ad_id:'normal',cansada:false,vigilar:false,senales:[]}]});assert.equal(col.celda(row).textContent,'0');assert(col.celda(row).attrs.title.includes('cobertura parcial'));assert(!String(col.celda(row).attrs.class||'').includes('verde'));});
for(const anuncios of [undefined,null,{}, {anuncios:[]}, {anuncios:[null]}, {anuncios:[{cansada:'false',vigilar:false}]}, {anuncios:[{cansada:null,vigilar:false}]}])test(()=>{const {col,row}=render(anuncios);assert.equal(col.celda(row).textContent,'—');});
test(()=>{const {col,row}=render({anuncios:[one]}, {...d,anuncios_generado:'2026-10-05'});assert.equal(col.celda(row).textContent,'—');});
test(()=>{const ad={...one},before=JSON.stringify(ad);const {model}=render({anuncios:[ad]});assert.equal(JSON.stringify(ad),before);const money=model.columnas.find(c=>c.clave==='gasto7').celda({...model.filas[0],dinero:false,gasto7:500});assert(money.textContent.includes('Reservado'));assert(!money.textContent.includes('500'));});

for(const ads of [[one,{...one}],[one,{...one,cansada:false,vigilar:false}],[{cansada:true,vigilar:false}],[{...one,ad_id:null}],[{...one,ad_id:1}],[{...one,ad_id:''}],[{...one,ad_id:' ad1'}],[{...one,ad_id:'ad\u0000x'}]])test(()=>{const {col,row}=render({anuncios:ads});assert.equal(col.celda(row).textContent,'—');});
test(()=>{const root=h('main',{});e.pCuentas(root,ctx,d,[{...c,anuncios:{anuncios:[one]}},{...c,cliente_id:'c2',nombre:'Second fixture',anuncios:{anuncios:[{...one}]}}],{},{});assert.equal(model.filas.length,2);for(const row of model.filas)assert.equal(model.columnas.find(x=>x.clave==='creativos').celda(row).textContent,'1');});
test(()=>{const original={};vm.createContext(original);vm.runInContext(fs.readFileSync('fixturebaseline_matriz_687.js','utf8').replaceAll('export ',''),original);assert.equal(original.creativosMatriz508({...c,anuncios:{anuncios:[one,{...one}]}},d,ctx.hoy).valor,2);const {col,row}=render({anuncios:[one,{...one}]});assert.equal(col.celda(row).textContent,'—');});
// Real frozen baseline still counts ads but labels that value as signals.
vm.runInContext(fs.readFileSync('fixturebaseline_captacion_687.js','utf8'),e);
test(()=>{const {col,row}=render({anuncios:[one]});assert.equal(col.titulo,'Señ.');assert.equal(col.celda(row).textContent,'1');assert.equal(one.senales.length,2);assert(col.celda(row).attrs.title.startsWith('Señales observadas'));});
console.log(n+' grupos687 PASS: tablaDensa/pCuentas reales, unidad anuncio≠señales, zero muestra gris, desconocidos, fuente futura, reservado y baseline.');
