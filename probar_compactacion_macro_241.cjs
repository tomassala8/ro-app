const fs=require('node:fs');
const prefijo=fs.readFileSync(__dirname+'/pruebas_control_macro_138.cjs','utf8').split('const macros=root.desc()')[0];
new Function('require','__dirname',prefijo+String.raw`
const table=root.desc().find(n=>n.tag==='table'),body=table.desc().find(n=>n.tag==='tbody');
assert.equal(body.k.length,3);
for(const row of body.k){assert.equal(row.k.length,10);assert.equal(row.desc().filter(n=>n.tag==='button').length,10);assert.equal(row.desc().filter(n=>n.tag==='details').length,0);}
assert.equal(table.desc().filter(n=>n.tag==='th').length,10);
assert(table.textContent.includes('—'));
assert(table.desc().some(n=>n.tag==='button'&&n.attrs['aria-label']?.includes('Sin dato')));
assert(!table.desc().some(n=>n.tag==='button'&&n.attrs.class?.includes('c250')&&n.textContent.includes('Sin dato')));
assert(!table.desc().some(n=>n.attrs.class?.includes('verde')));
assert.equal(root.desc().filter(n=>n.tag==='summary'&&n.textContent==='Cómo interpretar').length,1);
assert(root.textContent.includes('Cero declaraciones no significa'));
const src=fs.readFileSync(__dirname+'/modulos/_control_artifact_250.js','utf8');
assert(src.includes('min-height:44px'));
console.log('241→250 baseline PASS: diez columnas artifact, tres grupos incluidos sin account, sin verdes sin evidencia, controles accesibles.');
`)(require,__dirname);
