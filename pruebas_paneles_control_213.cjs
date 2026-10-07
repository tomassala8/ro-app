const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class N{constructor(tag,attrs={},...cs){this.tag=tag;this.attrs=attrs;this.isConnected=true;this.children=[];this.append(...cs);}append(...cs){for(const c of cs.flat(Infinity))if(c!=null)this.children.push(c);}replaceChildren(...cs){this.children=[];this.append(...cs);}querySelectorAll(){return [];}get lastElementChild(){return this.children.filter(x=>typeof x==='object').at(-1);}}
const text=n=>typeof n==='string'?n:n?.children?.map(text).join(' ')||'';const find=(n,p)=>typeof n==='object'?[...(p(n)?[n]:[]),...(n.children||[]).flatMap(x=>find(x,p))]:[];
const h=(...a)=>new N(...a);const c={URL,console,Date,Map,Set,Promise,localStorage:{getItem(){return null;},setItem(){}},MutationObserver:class{observe(){}},h,fmt:{num:String,pct:String,eur:String},icono:x=>h('ico',{},x),menuMas:o=>h('menu',{config:o}),selectorCliente:o=>h('select',{config:o}),pestanas:o=>h('tabs',{config:o}),chipsFiltro:o=>h('chips',{config:o}),serviciosActivos:()=>[],ordenHerramientas:o=>o,hoyMadrid:()=> '2026-10-03',sumarDias:()=> '2026-09-19',periodoCompleto:x=>x,leerPeriodo:()=>({id:'7d'}),consejoCompacto:()=>{c.consejos++;},consejos:0,vacio:o=>h('vacio',{},o.titulo),frescura:o=>h('fuente',{},o.fecha)};vm.createContext(c);
vm.runInContext(fs.readFileSync(__dirname+'/modulos/_control_paneles_213.js','utf8').replace(/export function /g,'function '),c);
vm.runInContext(fs.readFileSync(__dirname+'/modulos/_meta_mediciones_216.js','utf8').replace(/export function /g,'function '),c);
const source=fs.readFileSync(__dirname+'/modulos/paneles.js','utf8');vm.runInContext(source.replace(/^import[\s\S]*?from ['"][^'"]+['"];[^\n]*\n/gm,'').replace('export default {','const modulo = {')+';globalThis.modulo=modulo;',c);
vm.runInContext('pintarDesk=(z,d,P)=>z.append(h("desk",{},String(P.id)));pintarGA=(z,d,P)=>z.append(h("ga",{},String(P.id)));',c);
let count=0;
const ctx=()=>({persona:{id:'account',puestos:['account']},real:{id:'account',puestos:['account']},params:[],clientesVisibles:[{id:'client'}],carteraIds:new Set(['client']),veModulo:()=>true,titulo(){},navegar(){},alCambiarPeriodo(fn){this.periodoFn=fn;return ()=>{this.quitados=(this.quitados||0)+1;}},periodo:{id:'7d'},vigente:()=>true});
const links=cx=>c.controlesPaneles213(cx);
let x=ctx();assert(links(x).some(x=>x.href==='#/mi-dia/account'));assert(links(x).some(x=>x.href==='#/horas'));count++;
x=ctx();x.persona.puestos=['operaciones'];x.real.puestos=['operaciones'];assert(links(x).some(x=>x.href==='#/mi-dia/operaciones'));count++;
x=ctx();x.veModulo=()=>false;assert.equal(links(x).length,0);count++;
x=ctx();x.veModulo=k=>k==='horas';assert.deepEqual(Array.from(links(x),r=>r.href),['#/horas']);count++;
x=ctx();x.persona.puestos=['seo'];assert(!links(x).some(x=>x.href.startsWith('#/mi-dia/')));count++;
(async()=>{
let resolve,reject,navs=0,titles=0;const pending=()=>new Promise((a,b)=>{resolve=a;reject=b;});
// Indice lento obsoleto: no título, listener ni consejo después de cambiar ruta.
x=ctx();x.datosModulo=pending;x.navegar=()=>navs++;x.titulo=()=>titles++;let root=h('main');let p=c.modulo.render(root,x);x.params=['otra'];resolve({filas:[{cliente_id:'client',fuentes:{ga4:{estado:'bien'}}}]});await p;assert.equal(root.children.length,0);assert.equal(titles,0);assert.equal(c.consejos,0);count++;
// Error tardío también se ignora.
x=ctx();x.datosModulo=pending;root=h('main');p=c.modulo.render(root,x);root.isConnected=false;reject(Error('fixture'));await p;assert.equal(root.children.length,0);count++;
// Selección herramienta obsoleta no redirige por copia antigua.
x=ctx();let calls=0;x.datosModulo=()=>++calls===1?Promise.resolve({filas:[{cliente_id:'client',fuentes:{ga4:{estado:'bien'},gsc:{estado:'bien'}}}]}):pending();x.navegar=()=>navs++;root=h('main');p=c.modulo.render(root,x);await new Promise(r=>setImmediate(r));x.persona.id='otro';resolve({filas:[{serie:{'2026-01-01':{}}}]});await p;assert.equal(navs,0);assert.equal(c.consejos,0);count++;
// Empresa: listener válido repinta, después de revocación no toca DOM.
x=ctx();x.persona.puestos=x.real.puestos=['operaciones'];x.params=['empresa','desk'];x.datosModulo=async()=>({leido:'2026-10-03'});root=h('main');await c.modulo.render(root,x);assert(text(root).includes('7d'));x.periodoFn({id:'30d'});assert(text(root).includes('30d'));const before=text(root);x.veModulo=()=>false;x.periodoFn({id:'mes'});assert.equal(text(root),before);count++;
// Empresa respuesta tras cambio identidad no pinta ni reemplaza listener actual.
x=ctx();x.persona.puestos=x.real.puestos=['operaciones'];x.params=['empresa','desk'];let started=false;x.datosModulo=path=>path==='paneles/indice'?Promise.resolve({filas:[]}):(started=true,pending());root=h('main');p=c.modulo.render(root,x);await new Promise(r=>setImmediate(r));assert(started);x.real.id='other';resolve({leido:'2026-10-03'});await p;assert.equal(find(root,n=>n.tag==='desk').length,0);count++;
// Callback de navegación del selector revocado no se ejecuta.
x=ctx();x.datosModulo=async path=>path==='paneles/indice'?{filas:[{cliente_id:'client',fuentes:{ga4:{estado:'bien'}}}]}:{filas:[{serie:{'2026-10-03':{}}}]};x.navegar=()=>navs++;root=h('main');await c.modulo.render(root,x);const select=find(root,n=>n.tag==='select')[0];assert(select);const previous=navs;x.clientesVisibles=[];select.attrs.config.alElegir({id:'client'});assert.equal(navs,previous);count++;
// Nueva petición mantiene enlaces reales de control, sin KPI ni fuente adicional.
x=ctx();x.params=['mapa'];root=h('main');vm.runInContext('pintarMapa=(z,ctx)=>z.append(h("mapa"));',c);await c.modulo.render(root,x);const menu=find(root,n=>n.tag==='menu')[0];assert(menu.attrs.config.items.some(x=>x.href==='#/mi-dia/account'));count++;
console.log(count+' pruebas213 PASS: links scope, ruta/identidad/cartera, awaits/error tardíos, periodo revocado y render real.');
})().catch(e=>{console.error(e);process.exitCode=1;});
