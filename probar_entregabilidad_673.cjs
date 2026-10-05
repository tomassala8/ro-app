const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class N{constructor(tag,a={},kids=[]){this.tag=tag;this.attrs=a;this.children=[];this.append(...kids)}append(...k){this.children.push(...k.flat(Infinity).filter(x=>x!=null))}replaceChildren(...k){this.children=[];this.append(...k)}get textContent(){return this.children.map(x=>x instanceof N?x.textContent:String(x)).join(' ')}desc(){return this.children.filter(x=>x instanceof N).flatMap(x=>[x,...x.desc()])}}
const h=(t,a,...kids)=>new N(t,a,kids);
const baseline=fs.readFileSync(__dirname+'/fixturebaseline_crm_673.js','utf8'),candidate=fs.readFileSync(__dirname+'/modulos/crm.js','utf8');
function run(s,ro,valid=true,hoy='2026-10-04'){const e={h,Number,Date,Array,ID:'salud-crm',MOVIL:()=>false,logoCliente:()=>null,abrirGHL:()=>null,tablaDensa:()=>h('table',{}),panel:(o,...k)=>h('section',{},h('header',{},o.titulo,o.sub),...k),notaCompacta336:(h,t,...k)=>h('details',{},h('summary',{},t),...k),fmt:{num:n=>n==null||Number.isNaN(n)?'—':String(Number(n))},chipEstado:(c,t)=>h('span',{'data-state':c},t),fDiaRO:x=>x};
 vm.createContext(e);vm.runInContext(fs.readFileSync(__dirname+'/fixture_semaforo_673.js','utf8'),e);
 vm.runInContext(s.slice(s.indexOf('function pintarFlujos('),s.indexOf('// ------------------------------------------------------------------ pestaña: montajes de altas')),e);
 const zone=h('main',{});e.pintarFlujos(zone,{vigente:()=>valid,hoy},{correo_ro:ro},{base:[]});return zone;}
const chip=z=>z.desc().find(n=>n.attrs['data-state']);
assert.equal(chip(run(baseline,{rebote_pct:'0',fecha:'2026-10-01'})).attrs['data-state'],'verde','Defecto previo: string0 verde');
assert.equal(chip(run(baseline,{rebote_pct:false,fecha:'2026-10-01'})).attrs['data-state'],'verde','Defecto previo: booleano verde');
assert.equal(chip(run(baseline,{rebote_pct:1,fecha:'2026-10-01'})).attrs['data-state'],'verde','Defecto previo: referencia anterior verde');
let count=0;
for(const value of [undefined,null,'0',false,NaN,Infinity,-1,101,{},[]]){const z=run(candidate,{rebote_pct:value,fecha:'2026-10-01'});assert.equal(chip(z).textContent,'Subcuenta de RO: —');assert.equal(chip(z).attrs['data-state'],'gris');count++;}
for(const value of [0,1,2.4,100]){const ro={rebote_pct:value,fecha:'2026-10-01',fuente:'Auditoría fixture',nota:'Nota fixture'},before=JSON.stringify(ro),z=run(candidate,ro);assert.equal(chip(z).textContent,`Subcuenta de RO: ${value} % de rebote`);assert.equal(chip(z).attrs['data-state'],'gris');assert(z.textContent.includes('2026-10-01'));assert(z.textContent.includes('Auditoría fixture'));assert.equal(JSON.stringify(ro),before);const det=z.desc().find(n=>n.tag==='details'&&n.textContent.includes('Fuente y límites'));assert(det);assert.equal(det.attrs.open,undefined);assert(det.textContent.includes('quejas ≥ 0,3'));assert(det.textContent.includes('Nota fixture'));count++;}
for(const fecha of [undefined,null,'2026-02-30','2026-10-01T00:00:00Z',12]){assert.equal(chip(run(candidate,{rebote_pct:0,fecha})).textContent,'Subcuenta de RO: —');count++;}
const revoked=run(candidate,{rebote_pct:1,fecha:'2026-10-01'},false);assert.equal(revoked.children.length,0);count++;
for(const hoy of [undefined,null,'','2026-02-30','2026-09-30']){const z=run(candidate,{rebote_pct:0,fecha:'2026-10-01'},true,hoy===undefined?null:hoy);assert.equal(chip(z).textContent,'Subcuenta de RO: —');assert(z.textContent.includes('2026-10-01'));count++;}
console.log(`${count} escenarios candidato PASS +3 reproducciones before; sin API/PII/proveedores.`);
