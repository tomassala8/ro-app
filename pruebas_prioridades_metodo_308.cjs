const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const APP=__dirname;
class Nodo{
 constructor(tag='div',attrs={}){this.tag=tag;this.attrs=attrs;this.style=attrs?.style||{};this.parentNode=null;this.childNodes=[];this.main=false;this.disabled=false;this._value=undefined;}
 get isConnected(){return this.main||!!this.parentNode?.isConnected;}
 get parentElement(){return this.parentNode;}
 append(...ns){for(const n of ns.flat(Infinity).filter(x=>x!=null)){if(n instanceof Nodo)n.parentNode=this;this.childNodes.push(n);}}
 replaceChildren(...ns){for(const n of this.childNodes)if(n instanceof Nodo)n.parentNode=null;this.childNodes=[];this.append(...ns);}
 get textContent(){return this.childNodes.map(n=>n instanceof Nodo?n.textContent:String(n)).join('');}
 set textContent(v){this.replaceChildren(String(v));}
 get value(){return this._value===undefined?this.textContent:this._value;}
 set value(v){this._value=v;}
 focus(){this.focused=true;}
 select(){this.selected=true;}
 descendants(){return this.childNodes.filter(n=>n instanceof Nodo).flatMap(n=>[n,...n.descendants()]);}
 querySelector(sel){return this.descendants().find(n=>n.tag===sel)||null;}
}
const h=(tag,attrs,...kids)=>{const n=new Nodo(tag,attrs);n.append(...kids);return n;};
const defer=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return{promise,resolve,reject};};
const tick=()=>new Promise(r=>setImmediate(r));
function cargar(){
 const alerts=[],copies=[];const b={URLSearchParams,h,panel:(p,...ns)=>h('section',{},h('h2',{},p.titulo),...ns),chipEstado:(e,t)=>h('span',{},t),vacioLinea:t=>h('p',{},t),avisoFlotante:t=>alerts.push(t),conectoresPara:()=>[],location:{hash:'#/prioridades-cliente'},navigator:{clipboard:{writeText:async t=>{copies.push(t);}}},document:{execCommand:()=>{b.execs++;return true}},execs:0,alerts,copies};
 vm.createContext(b);
 const strip=s=>s.replace(/^import[\s\S]*?;\s*/gm,'').replace(/export (async )?function /g,'$1function ').replace('export default {','globalThis.modulo = {');
 // También ejecutamos el helper real de clipboard y fallback, sin importar sus dependencias.
 vm.runInContext(strip(fs.readFileSync(path.join(APP,'modulos/tarea_ia.js'),'utf8')),b);
 vm.runInContext(strip(fs.readFileSync(path.join(APP,'modulos/_tarea_ia.js'),'utf8')),b);
 vm.runInContext(strip(fs.readFileSync(path.join(APP,'modulos/_prioridades_contexto_337.js'),'utf8')),b);
 vm.runInContext(strip(fs.readFileSync(path.join(APP,'modulos/prioridades_cliente.js'),'utf8')),b);return b;
}
const RECO={cliente_id:'cliente-fixture',regla_id:'regla-fixture',area:'paid',titulo:'Revisar dato',motivo:'Evidencia fixture',accion:'Preparar revisión',evidencias:[]};
const DATOS={recomendaciones:[RECO],cobertura:{clientes:[]}};
function contexto(api){let ok=true;const c={servidor:true,persona:{id:'persona-fixture',estado:'activo',puestos:['account']},real:{id:'persona-fixture',estado:'activo',puestos:['account']},datos:{personas:[{id:'persona-fixture',estado:'activo',puestos:['account']}]},soloLectura:false,clientesVisibles:[{id:'cliente-fixture',nombre:'Cliente de prueba',activo_confirmado:true,detalle:true}],veModulo:m=>m==='prioridades-cliente',ver:()=>({ok:true}),nombre:id=>id,titulo:()=>{},vigente:()=>ok,invalidar:()=>{ok=false},api};c.clientes=c.clientesVisibles.map(x=>({...x,activo:true,estado:"activo"}));return c;}
function main(){const n=new Nodo();n.main=true;return n;}
function boton(root,txt){const n=root.descendants().find(n=>n.tag==='button'&&(n.textContent===txt||n.attrs['data-uso']===txt));assert(n,'Falta botón '+txt);return n;}
const click=n=>n.attrs.on.click({currentTarget:n});
async function lista(){const b=cargar(),m=main();const c=contexto(async ruta=>ruta==='cerebro/operativo'?DATOS:{sugerencias:[]});await b.modulo.render(m,c);await click(boton(m,'Revisar'));return{b,m,c};}

(async()=>{
 const b=cargar(),m=main();
 const raw={cliente_id:'cliente-fixture',regla_id:'seguimiento_quincenal_especialista',recomendacion:'RAW_DUPLICADO_NO_USAR',estado:'sin_dato',responsables_ids:['p']};
 const canonical={...RECO,regla_id:'seguimiento_quincenal_especialista',titulo:'Canónico quincenal',metodo_308:{incumplimiento:null,reunion_agendada:null}};
 const c=contexto(async r=>r==='cerebro/operativo'?{recomendaciones:[canonical],cobertura:{clientes:[]}}:{sugerencias:[raw,raw]});
 await b.modulo.render(m,c);
 assert(m.textContent.includes('Canónico quincenal'));assert(!m.textContent.includes('RAW_DUPLICADO_NO_USAR'));
 assert.equal(m.descendants().filter(n=>n.tag==='button'&&n.textContent==='Revisar').length,1);
 await click(boton(m,'Revisar'));assert(m.textContent.includes('Canónico quincenal'));assert(!m.textContent.includes('RAW_DUPLICADO_NO_USAR'));
 c.invalidar();const before=m.textContent;await click(boton(m,'Preparar borrador'));assert.equal(m.textContent,'');assert(!m.textContent.includes('Canónico quincenal'));
 console.log('3 grupos308 PASS: renderer real, recomendación canónica única, raw descartado y vigencia.');
})().catch(e=>{console.error(e);process.exitCode=1});
