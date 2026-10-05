const fs=require('node:fs');
const prefijo=fs.readFileSync(__dirname+'/pruebas_control_macro_138.cjs','utf8').split('const macros=root.desc()')[0];
new Function('require','__dirname',prefijo+String.raw`
let casos=0;
const zona=n=>n.desc().find(x=>x.attrs['aria-label']==='Clientes y proyectos agrupados · tabla de la cartera filtrada');
const tabla=n=>zona(n).desc().find(x=>x.tag==='table');
const visibles=n=>typeof n==='string'?n:typeof n==='number'?String(n):n?.tag==='details'?n.k.filter(x=>x?.tag==='summary').map(visibles).join(' '):(n?.k||[]).map(visibles).join(' ');
let matrix=tabla(root);assert.equal(matrix.desc().find(x=>x.tag==='thead').desc().filter(x=>x.tag==='th').length,9);casos++;
const filas=matrix.desc().find(x=>x.tag==='tbody').k;assert.equal(filas.length,3);for(const f of filas){assert.equal(f.k.length,9);assert.equal(f.desc().filter(x=>x.tag==='details').length,1);assert(!f.k.slice(0,-1).some(x=>x.desc().some(n=>n.tag==='p')));}casos++;
assert(!visibles(matrix).includes('Copia parcial'));assert(matrix.textContent.includes('Copia parcial'));assert(matrix.textContent.includes('fecha no disponible'));casos++;
assert(visibles(matrix).includes('Objetivo: por confirmar'));assert(!visibles(matrix).includes('Bien'));casos++;
ctx.verdad=id=>({id,gravedad:id==='uno'?'critico':id==='dos'?'bien':'atencion'});
let con=b.panelControlCartera(ctx,D,'operaciones',()=>true);let text=visibles(tabla(con));assert(text.includes('Crítico'));assert(text.includes('Bien'));assert(text.includes('Vigilar'));assert(text.includes('Objetivo: por confirmar'));casos++;
ctx.verdad=id=>({id:'other',gravedad:'critico'});con=b.panelControlCartera(ctx,D,'operaciones',()=>true);assert(!visibles(tabla(con)).includes('Crítico'));casos++;
ctx.verdad=id=>({id,cliente_id:'other',gravedad:'bien'});con=b.panelControlCartera(ctx,D,'operaciones',()=>true);assert(!visibles(tabla(con)).includes('Bien'));casos++;
ctx.verdad=id=>({id,gravedad:'inventado'});con=b.panelControlCartera(ctx,D,'account',()=>true);assert.equal(con.desc().filter(x=>x.tag==='table').length,1);assert(con.textContent.includes('Cliente uno'));assert(!con.textContent.includes('Cliente dos'));casos++;
console.log(casos+' grupos235 PASS: matriz real9columnas, un detalle/fila, fuentes plegadas, verdad canónica exacta, no nuevo semáforo por KPI y cartera.');
`)(require,__dirname);
const decl=fs.readFileSync(__dirname+'/pruebas_declaraciones_macro_159.cjs','utf8').split('(async()=>{')[0];
new Function('require','__dirname',decl+String.raw`
(async()=>{
 const t=create();t.response.clientes[0].contactos_declarados=0;t.response.clientes[0].reuniones_declaradas=0;
 await tick();t.finish();await tick();
 const table=find(t.n,n=>n.tag==='table');
 const visible=n=>typeof n==='string'?n:n?.tag==='details'?n.children.filter(x=>x?.tag==='summary').map(visible).join(' '):(n?.children||[]).map(visible).join(' ');
 const v=visible(table);assert(v.includes('0 declarados · sin verificar'));assert(v.includes('0 declaradas · sin verificar'));assert(v.includes('Por confirmar'));assert(!v.includes('No llamado'));assert(!v.includes('Cumplido'));assert(t.n.textContent.includes('0 contactos declarados'));
 console.log('1 grupo235 adicional PASS: declaraciones cero no acreditan ausencia de contacto ni de reunión.');
})().catch(e=>{console.error(e);process.exitCode=1});
`)(require,__dirname);
