const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const fuente = fs.readFileSync(path.join(__dirname, 'modulos/agenda.js'),'utf8');
const body = fuente.replace(/import\s+[\s\S]*?from\s+['"][^'"]+['"];\s*/g,'').replace('export default {','const modulo = {');
class Nodo {
 constructor(tag,attrs={},...children){this.tag=tag;this.attrs=attrs;this.style=attrs.style||{};this.children=[];this.isConnected=true;this.append(...children);}
 append(...xs){for(const x of xs.flat(Infinity)){if(x!==null&&x!==undefined)this.children.push(x);}}
 replaceChildren(...xs){this.children=[];this.append(...xs);}
 querySelector(sel){return sel==='.pestanas-caja'? buscar(this,n=>n.tag==='pestanas')[0]||null:null;}
 querySelectorAll(){return [];}
 getAttribute(k){return this.attrs[k];}
 addEventListener(){} scrollIntoView(){}
}
function buscar(n,p){const xs=[]; if(n&&typeof n==='object'){if(p(n))xs.push(n);for(const c of n.children||[])xs.push(...buscar(c,p));}return xs;}
const h=(...a)=>new Nodo(...a), text=n=>typeof n==='string'?n:n?.children?.map(text).join(' ')||'';
let mobile=false, notices=[], captureSelector, captureTabs;
const dom={head:h('head'),getElementById:()=>null};
const c={URL,Intl,Date,console,document:dom,location:{reload(){}},sessionStorage:{getItem:()=>null,setItem(){}},
 MutationObserver:class{observe(){}},matchMedia:()=>({matches:mobile,addEventListener(){},removeEventListener(){}}),
 h,fmt:{num:String},icono:x=>h('ico',{},x),panel:(a,...b)=>h('panel',{},h('header',{},a.titulo,a.sub,a.acciones),...b),
 chipEstado:(a,b)=>h('chip',{},b),chipsFiltro:a=>{const n=h('filtro');n.valor=()=>a.valor;return n;},
 pestanas:a=>{captureTabs=a;const n=h('pestanas');n.activa=()=>a.activa;const z=h('zona');a.pintar(a.activa,z);n.append(z);return n;},
 frescura:x=>h('fuente',{},x.fuente),vacio:()=>h('vacio'),vacioLinea:t=>h('vacio',{},t),avisoParcial:t=>h('aviso',{},t),
 plegarConsejo(){},selectorPersona:a=>{captureSelector=a;return h('selector');},menuMas:a=>h('menu',{},...a.items.map(x=>x.texto)),
 avisoFlotante:t=>notices.push(t),iniciales:x=>x,tablaApilable:()=>h('tabla'),copiar(){}};
vm.createContext(c);vm.runInContext(body + '\nObject.assign(globalThis,{lunesDe,sumarDias,aFecha});',c);
const evento={id:'e',persona_id:'yo',tipo:'cliente',titulo:'Cita autorizada',inicio:'2026-10-03 10:00',fin:'2026-10-03 11:00',atajos:[]};
const S={D:{_meta:{desde:'2026-09-19',hasta:'2026-10-24',fuentes:[]}},ctx:{clientesVisibles:[],verdad:()=>null,vigente:()=>true},personas:new Map(),quien:'yo',yo:'yo',nombres:{},filtro:'',semana:'2026-09-28',dia:'2026-10-03',pintar(){}};
assert.equal(c.lunesDe('2026-10-04'),'2026-09-28');assert.equal(c.lunesDe('2026-10-05'),'2026-10-05');assert.equal(c.sumarDias('2026-12-28',6),'2027-01-03');
assert(Number.isNaN(+c.aFecha('2026-02-30')));
assert.deepEqual(JSON.parse(JSON.stringify(c.relojMadrid(new Date('2026-03-29T01:30:00Z')))),{dia:'2026-03-29',minutos:210});
assert.equal(c.estadoTemporal(evento,'2026-10-03',630),'ahora');assert.equal(c.estadoTemporal(evento,'2026-10-03',660),'pasada');assert.equal(c.estadoTemporal({...evento,todo_el_dia:true},'2026-10-03',660),'todo_el_dia');
for(const u of ['javascript:alert(1)','http://zoom.us/j/123','https://zoom.us.evil.com/j/123','https://zoom.us@evil.com/j/123','https://evil@zoom.us/j/123','https://zoom.us/s/123','https://zoom.us/rec/share/abc','https://zoom.us:444/j/123'])assert.equal(c.enlaceZoom({...evento,join_url:u}),null,u);
assert.equal(c.enlaceZoom({...evento,join_url:'https://us02web.zoom.us/j/123?pwd=abc'}),'https://us02web.zoom.us/j/123?pwd=abc');
let actions=c.accionesCita(S,{...evento,join_url:'https://zoom.us/j/123'},false,{abrir:'Zoho'});
assert.equal(buscar(actions,n=>n.attrs?.class==='bt pri')[0].attrs.href,'https://zoom.us/j/123');assert(text(actions).includes('Entrar en Zoom'));
actions=c.accionesCita(S,{...evento,inicio:'2099-10-03 10:00',atajos:[{h:'zoom',url:'https://zoom.us/rec/share/a'},{h:'crm',url:'javascript:bad'}]},false,{abrir:'Zoho'});
assert(text(actions).includes('Enlace de Zoom no disponible'));assert(text(actions).includes('Ver grabación'));assert(!text(actions).includes('Entrar en Zoom'));assert(!buscar(actions,n=>n.attrs?.href?.startsWith('javascript:')).length);
const allDay={...evento,id:'all',inicio:'2026-09-28 00:00',todo_el_dia:true,titulo:'Todo el día'};
const late={...evento,id:'late',inicio:'2026-10-04 22:00',fin:'2026-10-04 23:00',titulo:'Cita de noche'};
let week=c.vistaSemana(S,[evento,allDay,late],'2026-10-03',630);
const columns=buscar(week,n=>n.tag==='section');assert.equal(columns.length,7);assert.equal(columns[0].attrs['aria-label'],'lunes 28 de sep');assert.equal(columns[6].attrs['aria-label'],'domingo 4 de oct');assert(text(week).includes('Todo el día'));assert(text(week).includes('Cita de noche'));
const dayButtons=buscar(week,n=>n.attrs?.class?.startsWith('agenda-dia-boton'));assert.equal(dayButtons.length,7);dayButtons[0].attrs.on.click();assert.equal(S.dia,'2026-09-28');
mobile=true;week=c.vistaSemana(S,[evento,allDay,late],'2026-10-03',630);assert(text(buscar(week,n=>n.attrs?.class==='agenda-detalle-dia')[0]).includes('Todo el día'));
const past=c.vistaDia(S,[allDay],'2026-09-28',630,'tu');assert.equal(buscar(past,n=>n.attrs?.['aria-label']==='Ahora').length,0);
(async()=>{
 const deferred=()=>{let resolve;return {promise:new Promise(r=>resolve=r),resolve};};
 const wait=deferred(),cont=h('main');let active=true;
 const ctx={persona:{id:'yo'},datos:{personas:[{id:'yo'},{id:'otro'}]},nivel:'todo',clientesVisibles:[],verdad:()=>null,titulo(){},vigente:()=>active,datosModulo:()=>wait.promise};
 c._cont=cont;c._ctx=ctx;const render=vm.runInContext('modulo.render(_cont,_ctx)',c);active=false;wait.resolve({_meta:{},eventos:[evento]});await render;assert.equal(cont.children.length,0,'late data cannot paint after route change');
 // Actual module render, selector and tabs, not copied functions.
 active=true;ctx.datosModulo=async()=>({_meta:S.D._meta,eventos:[evento,{...evento,id:'otro',persona_id:'otro'}]});await vm.runInContext('modulo.render(_cont,_ctx)',c);assert(text(cont).includes('citas hoy'));assert(!text(cont).includes('Huecos libres hoy'));assert.equal(captureTabs.pestanas[0].texto,'Día');
 // Late private names from a different selected person must not mutate or notify.
 const names=deferred(),old=Object.assign({},S,{ctx:{...S.ctx,verDato:()=>names.promise},quien:'yo',nombres:{},pintar(){throw Error('stale repaint');}});
 const b=c.botonNombres(old,[{...evento,tipo:'prospecto'}]);const promise=b.attrs.on.click({currentTarget:b});old.quien='otro';names.resolve({valor:{e:'Nombre privado'}});await promise;assert.equal(Object.keys(old.nombres).length,0);assert.equal(notices.length,0);
 console.log('Agenda 111: calendario real, fechas Madrid, URLs, estados y aislamiento async OK');
})().catch(e=>{console.error(e);process.exitCode=1;});
