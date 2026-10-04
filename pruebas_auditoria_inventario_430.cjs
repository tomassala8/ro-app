const fs=require('node:fs'),vm=require('node:vm');
let base=fs.readFileSync(__dirname+'/pruebas_auditoria_vigencia_428.cjs','utf8').split('(async()=>{')[0];
base=base.replace('function fixture(){','function fixture(rows=[row]){').replace('env.pAuditoria(ctx,data,[row])','env.pAuditoria(ctx,data,rows)');
const cases=`
(async()=>{
let n=0;const rows=Array.from({length:19},(_,i)=>({cliente_id:'c'+i,nombre:'Cuenta fixture '+i,meta_activa:true}));
let f=fixture([...rows,{cliente_id:'off',nombre:'INACTIVA_FIXTURE',meta_activa:false}]);f.mount();await tick();
const details=f.frame.all().find(x=>x.tag==='details');assert(details);assert(!details.open);assert.equal(details.children[0].text,'Resto de cuentas activas · 13');
assert.equal(f.buttons().length,57);assert.equal(details.all().filter(x=>x.tag==='button').length,39);
for(const r of rows)assert(f.frame.text.includes(r.nombre));assert(!f.frame.text.includes('INACTIVA_FIXTURE'));n++;
let posted;f.ctx.accion=async p=>{posted=p;return {ok:true}};await details.all().filter(x=>x.tag==='button').at(-1).attrs.onConfirm();assert.equal(posted.cliente_id,'c18');assert.equal(posted.texto,'No tocar');n++;
const old=details.all().find(x=>x.tag==='button');f.invalidate();details.open=true;details.attrs.on.toggle();assert.equal(details.children.length,0);assert(!f.frame.text.includes('Cuenta fixture'));await assert.rejects(old.attrs.onConfirm(),/La vista ha cambiado/);n++;
f=fixture(rows.slice(0,6));f.mount();await tick();assert.equal(f.buttons().length,18);assert(!f.frame.all().some(x=>x.tag==='details'));n++;
f=fixture(rows);f.mount();await tick();const d=f.frame.all().find(x=>x.tag==='details');f.ctx.persona.puestos.push('seo');d.open=true;d.attrs.on.toggle();assert.equal(d.children.length,0);assert.equal(f.buttons().length,0);n++;
// listaConIcono real: el vacío no debe usar su tarjeta vacio; registros mantienen seis elementos.
const componentes=fs.readFileSync(__dirname+'/componentes.js','utf8');
const inicio=componentes.indexOf('export function listaConIcono('),fin=componentes.indexOf('// ---------------------------------------------- barras',inicio);
env.icono=()=>h('i',{});env.vacio=()=>{throw Error('No debe construir vacío grande');};
vm.runInContext(componentes.slice(inicio,fin).replace('export function','function'),env);
f=fixture(rows);f.mount();await tick();assert(f.frame.text.includes('Sin decisiones en la respuesta disponible'));assert(f.frame.text.includes('Esta lectura no aplica un filtro de semana.'));assert(!f.frame.text.includes('Esta semana'));assert(!f.frame.all().some(x=>x.attrs.class==='lista-i'));n++;
f=fixture(rows);f.ctx.api=async()=>({acciones:Array.from({length:8},(_,i)=>({tipo:'auditoria_semanal',objeto:'DECISION'+i,texto:'observada',quien:'ops',creada:'2026-09-01'}))});f.mount();await tick();
const ul=f.frame.all().find(x=>x.attrs.class==='lista-i');assert(ul);assert.equal(ul.children.length,6);assert(f.frame.text.includes('DECISION5'));assert(!f.frame.text.includes('DECISION6'));assert(f.frame.text.includes('2026-09-01'));n++;
console.log(n+' grupos430 PASS: 19 cuentas/57 acciones completas, primeras6, resto13 cerrado, payload última cuenta, toggle revocado e identidad/roles; sin POST real.');
})().catch(e=>{console.error(e);process.exitCode=1});`;
vm.runInNewContext(base+cases,{require,__dirname,console,process,setImmediate,queueMicrotask},{filename:__filename});
