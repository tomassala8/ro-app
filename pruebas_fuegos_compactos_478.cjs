// Renderer268 real y dependencias del harness341; ninguna llamada externa.
const fs=require('fs');
const base=fs.readFileSync(__dirname+'/probar_horas_fuegos_341.cjs','utf8').split('let count=0;')[0];
const body=String.raw`
const walk478=n=>n instanceof N?[n,...n.children.flatMap(walk478)]:[];
const main478=()=>{const n=new N('main');n.main=true;return n;};
(async()=>{
let groups=0;
const render478=async({p=P(),d=D(),pauta=true}={})=>{const c=ctx(),v=main478();let gets=[];if(!pauta)c.ver=x=>({ok:x.tipo==='cliente_detalle'});c.datosModulo=async r=>{gets.push(r);return r.startsWith('produccion')?p:r.startsWith('dinero')?d:null;};await b.renderFuegos268(v,c);return {v,c,gets};};
const positive=await render478(),nodes=walk478(positive.v),table=nodes.find(n=>n.tag==='table'),heads=walk478(table).filter(n=>n.tag==='th'&&n.attrs.scope==='col'),cells=walk478(table).filter(n=>n.tag==='td');
assert.equal(heads.length,16);assert.equal(cells.length,15);groups++;
assert.equal(heads[10].textContent,'% pauta');assert.equal(heads[10].attrs.title,'% horas vs pautadas');assert.equal(heads[10].attrs['aria-label'],heads[10].attrs.title);assert(heads.every(n=>n.attrs.title&&n.attrs['aria-label']===n.attrs.title&&n.attrs.style.whiteSpace==='normal'));groups++;
assert.equal(cells[9].textContent,'≥140 %');assert.equal(cells[9].children[0].attrs['data-estado'],'rojo');assert(!cells.some(n=>/ref\.|% pendiente/.test(n.textContent)));assert.match(cells[9].attrs['aria-label'],/referencia|no presupuesto aprobado/);assert.match(nodes.find(n=>n.attrs['data-leyenda-horas']==='478').textContent,/no acredita presupuesto, capacidad ni cumplimiento/);groups++;
const no=await render478({pauta:false}),noCell=walk478(walk478(no.v).find(n=>n.tag==='table')).filter(n=>n.tag==='td')[9];assert.equal(noCell.textContent,'14 h');assert(!no.gets.some(x=>x.includes('dinero')));assert(!noCell.textContent.includes('10'));groups++;
const missing=await render478({p:{proyectos:[]}}),mcell=walk478(walk478(missing.v).find(n=>n.tag==='table')).filter(n=>n.tag==='td')[9];assert.equal(mcell.textContent,'—');assert(!walk478(mcell).some(n=>n.attrs['data-estado']==='verde'));groups++;
const zeroP=P();zeroP.proyectos[0].horas_mes=0;const zero=await render478({p:zeroP}),zcell=walk478(walk478(zero.v).find(n=>n.tag==='table')).filter(n=>n.tag==='td')[9];assert.equal(zcell.textContent,'≥0 %');assert.equal(zcell.children[0].attrs['data-estado'],'gris');groups++;
const detail=nodes.find(n=>n.tag==='details');positive.c.ver=()=>({ok:false});detail.attrs.on.toggle();assert.equal(positive.v.textContent,'');groups++;
console.log(groups+' grupos478 PASS: renderer real, cifras/cabeceras/ARIA, desconocidos y permisos intactos.');
})().catch(e=>{console.error(e);process.exitCode=1;});`;
new Function('require','__dirname',base+body)(require,__dirname);
