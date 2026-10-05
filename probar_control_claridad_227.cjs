const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
// Harness existente + función real panelControlCartera. Sin sustituir cálculos/filtros.
const base=fs.readFileSync(__dirname+'/pruebas_control_macro_138.cjs','utf8').split('const macros=root.desc()')[0];
new Function('require','__dirname',base+`
let casos=0,focus=0,scroll=0;
N.prototype.focus=function(){focus++;this.focused=true};N.prototype.scrollIntoView=function(o){scroll++;this.scrollOpts=o};
const tabla=root.desc().find(n=>n.attrs['aria-label']==='Clientes y proyectos agrupados · tabla de la cartera filtrada');
const boton=root.desc().find(n=>n.tag==='button'&&n.attrs['aria-label']==='Ver proyectos de otro');
const reset=root.desc().find(n=>n.tag==='button'&&n.textContent==='Restablecer filtros');
assert(tabla&&boton&&reset);assert.equal(reset.disabled,true);casos++;
boton.listeners.click();assert(tabla.focused);assert.equal(focus,1);assert.equal(scroll,1);assert(root.textContent.includes('otro · 1 de 3'));assert(!root.textContent.includes('Cliente uno'));assert.equal(reset.disabled,false);casos++;
reset.listeners.click();assert(root.textContent.includes('Cliente uno'));assert(root.textContent.includes('Cliente dos'));assert.equal(reset.disabled,true);assert.equal(focus,2);casos++;
const buscador=root.desc().find(n=>n.tag==='input'&&n.attrs.type==='search');buscador.value='no existe';buscador.listeners.input();assert.equal(reset.disabled,false);assert(root.textContent.includes('Ningún cliente coincide'));reset.listeners.click();assert(root.textContent.includes('3 de 3'));casos++;
const before=root.textContent;vigente=false;boton.listeners.click();reset.listeners.click();assert.equal(root.textContent,before);assert.equal(focus,3);assert.equal(scroll,1);casos++;
console.log(casos+' pruebas227 macro real PASS: foco/scroll, restablecer, contador seleccionado, no coincidencias, guard obsoleto.');
`)(require,__dirname);
