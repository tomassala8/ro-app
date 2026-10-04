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
function contexto(api){let ok=true;const c={servidor:true,persona:{id:'persona-fixture',estado:'activo',puestos:['account']},real:{id:'persona-fixture',estado:'activo',puestos:['account']},datos:{personas:[{id:'persona-fixture',estado:'activo',puestos:['account']}]},soloLectura:false,clientesVisibles:[{id:'cliente-fixture',nombre:'Cliente de prueba',activo_confirmado:true,detalle:true}],veModulo:m=>m==='prioridades-cliente',ver:()=>({ok:true}),nombre:id=>id,titulo:()=>{},vigente:()=>ok,invalidar:()=>{ok=false},api};return c;}
function main(){const n=new Nodo();n.main=true;return n;}
function boton(root,txt){const n=root.descendants().find(n=>n.tag==='button'&&(n.textContent===txt||n.attrs['data-uso']===txt));assert(n,'Falta botón '+txt);return n;}
const click=n=>n.attrs.on.click({currentTarget:n});
async function lista(){const b=cargar(),m=main();const c=contexto(async ruta=>ruta==='cerebro/operativo'?DATOS:{sugerencias:[]});await b.modulo.render(m,c);await click(boton(m,'Revisar'));return{b,m,c};}

let total=0;const check=(t,f)=>{f();total++;console.log('PASS',t);};
(async()=>{
 const b=cargar();
 const r={...RECO,titulo:'Revisar Meta',motivo:'Observación sin resultado demostrado',criterio_entrega:'Documento contrastado con lectura del periodo',evidencias:[{fuente:'meta_insights',fecha:'2026-10-03',periodo:{desde:'2026-09-25',hasta:'2026-10-02'},cobertura:{completa:false,dias_observados:3},vigencia:'referencia anterior',texto:'8 resultados observados'}]};
 const out=b.instrucciones(r,'Cliente fixture');
 check('metadatos presentes sin inventar medición',()=>{for(const t of ['2026-09-25 → 2026-10-02','completa: false','dias_observados: 3','referencia anterior','Documento contrastado','Acceso: Desconocido','Meta Ads'])assert(out.includes(t),t);});
 check('campos desconocidos explícitos',()=>{const t=b.instrucciones(RECO,'Cliente');assert(t.includes('Pendiente de confirmar'));assert(b.evidenciaEncargo337({}).includes('Periodo: Periodo sin confirmar'));assert(b.evidenciaEncargo337({}).includes('Cobertura: sin confirmar'));});
 check('sanitización real de contexto y metadatos',()=>{const evil='Correo prueba@example.invalid, +34 612345678, 250€\npassword=fixture-secret';const t=b.instrucciones({...r,titulo:evil,accion:evil,criterio_entrega:evil,evidencias:[{fuente:evil,fecha:'no fecha',cobertura:evil,vigencia:evil,texto:evil,periodo:evil}]},evil);for(const v of ['prueba@example.invalid','612345678','250€','fixture-secret'])assert(!t.includes(v),v);assert(t.includes('omitido'));assert(t.includes('Fecha: sin confirmar'));});
 check('metadatos adicionales no se serializan',()=>{const t=b.evidenciaEncargo337({cobertura:{completa:false,contacto:'PII_PROHIBIDA'},periodo:{desde:'2026-09-01',hasta:'2026-09-30',secret:'NO_SERIALIZAR'}});assert(!t.includes('PII_PROHIBIDA'));assert(!t.includes('NO_SERIALIZAR'));});
 const c=contexto(async()=>DATOS);
 check('ámbito legítimo canónico',()=>assert(b.ambitoPrioridades337(c).ids.includes('cliente-fixture')));
 for(const [name,change] of [['persona duplicada',x=>x.datos.personas.push({...x.datos.personas[0]})],['persona ausente',x=>x.datos.personas=[]],['catálogo inactivo',x=>x.datos.personas[0].estado='baja'],['rol no canónico',x=>x.persona.puestos=['direccion']],['real inactivo',x=>x.real.activo=false],['módulo revocado',x=>x.veModulo=()=>false]])check(name,()=>{const x=contexto(async()=>DATOS);change(x);assert.equal(b.ambitoPrioridades337(x),null);});
 check('cliente ACT y detalle/grant únicos',()=>{for(const change of [x=>x.clientesVisibles[0].activo_confirmado=false,x=>x.clientesVisibles.push({...x.clientesVisibles[0]}),x=>x.ver=()=>({ok:false})]){const x=contexto(async()=>DATOS);change(x);assert.equal(b.ambitoPrioridades337(x).ids.length,0);}});
 let deniedCalls=0;const denied=contexto(async()=>{deniedCalls++;return DATOS;});denied.datos.personas=[];const deniedMain=main();await b.modulo.render(deniedMain,denied);
 check('render sin catálogo no inicia ninguna lectura',()=>{assert.equal(deniedCalls,0);assert.equal(deniedMain.descendants().filter(n=>n.tag==='table').length,0);});
 const foreign=main();await b.modulo.render(foreign,contexto(async ruta=>ruta==='cerebro/operativo'?{recomendaciones:[RECO,{...RECO,cliente_id:'otro',titulo:'NO_AUTORIZADO'}],cobertura:{clientes:[{cliente_id:'otro',cadena:{paid:'NO_AUTORIZADO'}}]}}:{sugerencias:[]}));
 check('respuesta ajena no amplía recomendaciones ni cobertura',()=>assert(!foreign.textContent.includes('NO_AUTORIZADO')));
 const loaded=await lista();
 check('render encargo real incluye accesos',()=>{const t=loaded.m.descendants().find(n=>n.tag==='textarea'&&n.attrs['aria-label'].startsWith('Encargo'));assert(t.value.includes('Acceso: Desconocido'));assert(t.value.includes('ClickUp'));});
 let calls=0,gate=defer();const cx=contexto(async ruta=>{calls++;return gate.promise;}),m=main();const pending=b.modulo.render(m,cx);cx.ver=()=>({ok:false});gate.resolve(DATOS);await pending;
 check('permiso cambia durante GET: borra y no repinta',()=>{assert.equal(m.textContent,'');assert.equal(m.descendants().filter(n=>n.tag==='table').length,0);});
 const l=await lista();const preparar=boton(l.m,'Preparar borrador');l.c.datos.personas[0].estado='baja';await click(preparar);
 check('catálogo revocado antes preparar no llama API',()=>assert.equal(l.m.textContent,''));
 const l2=await lista();let draft=defer(),ncall=0;l2.c.api=async()=>{ncall++;return draft.promise;};const prep=click(boton(l2.m,'Preparar borrador'));l2.c.datos.personas.push({...l2.c.datos.personas[0]});draft.resolve({estado:'borrador',enviable:false,payload:{name:'BORRADOR_PROHIBIDO',description:'texto'}});await prep;
 check('catálogo ambiguo durante borrador: no muestra resultado',()=>{assert.equal(ncall,1);assert.equal(l2.m.textContent,'');});
 const l3=await lista(),cop=boton(l3.m,'copiar-ia');l3.c.clientesVisibles[0].activo_confirmado=false;await click(cop);
 check('copy revocado no entrega texto al clipboard',()=>{assert.equal(l3.b.copies.length,0);assert.equal(l3.m.textContent,'');});
 const l4=await lista();let promise=defer();l4.b.navigator.clipboard.writeText=()=>promise.promise;const copying=click(boton(l4.m,'copiar-ia'));l4.c.ver=()=>({ok:false});promise.resolve();await copying;
 check('revocación durante clipboard: no éxito ni fallback posterior',()=>{assert.equal(l4.b.alerts.length,0);assert.equal(l4.b.execs,0);assert.equal(l4.m.textContent,'');});
 const l5=await lista();l5.b.navigator.clipboard.writeText=async()=>{throw Error('fixture');};await click(boton(l5.m,'copiar-ia'));
 check('fallo clipboard usa fallback solo vigente',()=>{assert.equal(l5.b.execs,1);assert.equal(l5.b.alerts.length,1);});
 const l6=await lista();l6.c.clientesVisibles.push({...l6.c.clientesVisibles[0]});const filter=l6.m.descendants().find(n=>n.tag==='select'&&n.attrs['aria-label']==='Área');filter.attrs.on.change({target:{value:'paid'}});
 check('repintado tras duplicar cliente borra datos',()=>assert.equal(l6.m.textContent,''));
 const ui=cargar(),um=main(),segunda={...RECO,regla_id:'otra',titulo:'Segunda propuesta completa',motivo:'Motivo largo que sigue completo en detalle',accion:'Acción larga con todos los pasos y criterio íntegros',area:'crm',criterio_entrega:'Verificar evidencia completa'};
 ui.location.hash='#/prioridades-cliente?area=paid';const uc=contexto(async route=>route==='cerebro/operativo'?{recomendaciones:[RECO,segunda],cobertura:{clientes:[]}}:{sugerencias:[]});await ui.modulo.render(um,uc);
 check('484 headers compactos con nombre completo y filtros desde enlace',()=>{const hs=um.descendants().filter(n=>n.tag==='th');assert.deepEqual(hs.map(n=>n.textContent),['Cliente','Señal','Acción','Resp.','Abrir']);assert(hs.every(n=>n.attrs.title&&n.attrs['aria-label']));assert.equal(um.descendants().find(n=>n.tag==='select'&&n.attrs['aria-label']==='Área').value,'paid');assert(um.descendants().some(n=>n.attrs.class==='prioridades-filtros484'));});
 const ar=um.descendants().find(n=>n.tag==='select'&&n.attrs['aria-label']==='Área');ar.attrs.on.change({target:{value:''}});await click(boton(um,'Revisar'));
 check('484 detalle conserva todas las acciones y motivos completos tras filtro',()=>{const as=um.descendants().filter(n=>n.tag==='article'&&n.attrs.class==='ro-prioridades-accion');assert.equal(as.length,2);assert(um.textContent.includes(segunda.motivo));assert(um.textContent.includes(segunda.accion));assert(um.textContent.includes(segunda.criterio_entrega));assert.equal(um.descendants().filter(n=>n.tag==='button'&&n.textContent==='Preparar borrador').length,2);});
 uc.ver=()=>({ok:false});const ev=um.descendants().find(n=>n.tag==='summary'&&n.textContent==='Ver evidencia').parentNode;ev.attrs.on.toggle();check('484 disclosure mantiene guard y limpia al revocar',()=>assert.equal(um.textContent,''));
 //484 correctivo: ejecutar consejoCompacto REAL con un DOM conectado y observador controlado.
 const cj=cargar(),cm=main(),observers=[];cm.attrs.id='main';
 Nodo.prototype.closest=function(sel){let x=this;while(x){if(sel==='#main'&&x.attrs.id==='main')return x;x=x.parentNode;}return null;};
 const consulta=Nodo.prototype.querySelector;Nodo.prototype.querySelector=function(sel){if(sel===':scope > [data-ia="consejo"]')return this.childNodes.find(n=>n instanceof Nodo&&n.attrs['data-ia']==='consejo')||null;if(sel==='ol.ia-acciones')return this.descendants().find(n=>n.tag==='ol'&&n.attrs.class==='ia-acciones')||null;if(sel===':scope > .ia-sub')return this.childNodes.find(n=>n instanceof Nodo&&n.attrs.class==='ia-sub')||null;return consulta.call(this,sel);};
 Object.defineProperty(Nodo.prototype,'nextElementSibling',{get(){const xs=this.parentNode?.childNodes||[],i=xs.indexOf(this);return xs.slice(i+1).find(n=>n instanceof Nodo)||null;}});
 Nodo.prototype.after=function(n){if(n.parentNode)n.parentNode.childNodes=n.parentNode.childNodes.filter(x=>x!==n);const p=this.parentNode,i=p.childNodes.indexOf(this);p.childNodes.splice(i+1,0,n);n.parentNode=p;};
 cj.MutationObserver=class{constructor(cb){this.cb=cb;observers.push(this);}observe(){}disconnect(){this.dead=true;}};
 const trabajo=fs.readFileSync(path.join(APP,'modulos/_trabajo.js'),'utf8');vm.runInContext(trabajo.slice(trabajo.indexOf('export function plegarConsejo('),trabajo.indexOf('export function pantallaTrabajo(')).replace(/export function /g,'function '),cj);
 const cc=contexto(async route=>route==='cerebro/operativo'?DATOS:{sugerencias:[]});await cj.modulo.render(cm,cc);
 const advice=h('section',{'data-ia':'consejo'}),adList=h('ol',{class:'ia-acciones'},'Consejo fixture completo'),adSummary=h('p',{class:'ia-sub'},'Resumen fixture');advice.dataset={};advice.append(adList,adSummary);advice.parentNode=cm;cm.childNodes.unshift(advice);observers[0].cb();
 check('484 consejo común real queda plegado después del módulo sin duplicarse',()=>{assert.equal(cm.childNodes.at(-1),advice);assert(adList.hidden);assert.equal(cm.childNodes.filter(n=>n.attrs?.['data-ia']==='consejo').length,1);assert(advice.textContent.includes('Consejo fixture completo'));});
 cc.ver=()=>({ok:false});cm.descendants().find(n=>n.tag==='select').attrs.on.change({target:{value:'paid'}});check('484 guard detiene observador del consejo al revocar',()=>assert(observers[0].dead));
 console.log(total+' grupos337 PASS: helpers reales, render y promesas sin proveedor');
})().catch(e=>{console.error(e);process.exitCode=1});
