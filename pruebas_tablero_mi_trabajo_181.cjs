const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Nodo{
 constructor(tag,attrs={},...children){this.tag=tag;this.attrs=attrs;this.value=attrs.value||'';this.isConnected=true;this.children=[];this.append(...children);}
 append(...xs){for(const x of xs.flat(Infinity)){if(x==null)continue;if(typeof x==='object')x.parentNode=this;this.children.push(x);}}
 replaceChildren(...xs){for(const x of this.children)if(typeof x==='object'){x.parentNode=null;x.isConnected=false;}this.children=[];this.append(...xs);}
 querySelector(s){return buscar(this,n=>s==='details'?n.tag==='details':false)[0]||null;}
 querySelectorAll(){return [];}addEventListener(){}focus(){}
}
function buscar(n,p){let a=[];if(n&&typeof n==='object'){if(p(n))a.push(n);for(const x of n.children||[])a.push(...buscar(x,p));}return a;}
const text=n=>typeof n==='string'?n:typeof n==='number'?String(n):n?.children?.map(text).join(' ')||'';
const h=(...x)=>new Nodo(...x),store=new Map();let casos=0;
const c={console,Date,Set,Map,JSON,Promise,setTimeout,matchMedia:()=>({matches:false}),sessionStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)},
 h,poner:(n,...xs)=>n.replaceChildren(...xs),fmt:{num:String},icono:x=>h('ico',{},x),
 vacioLinea:t=>h('vacio',{},t),logoCliente:()=>h('logo'),avisoFlotante(){},filasFlexibles(){},barraProgreso:()=>h('barra'),tablaApilable:()=>h('tabla'),
 sumarDias:(d,n)=>{let x=new Date(d+'T12:00:00Z');x.setUTCDate(x.getUTCDate()+n);return x.toISOString().slice(0,10);},fechaCorta:x=>x,
 pantallaTrabajo:a=>h('pantalla',{},a.filtros,a.pestanas,a.lista,a.detalle,...a.contexto),
 chipsFiltro:a=>h('chips',{config:a},a.etiqueta),menuElegir:a=>h('menu',{config:a},a.etiqueta, a.valor),pestanas:a=>h('tabs',{config:a},a.pestanas.map(t=>t.texto)),
 botonDeshacer:a=>h('button',{disabled:a.soloLectura,config:a},a.texto),conDeshacer:()=>h('button'),bloqueTareaIA:()=>{throw Error('No lecturas remotas en piloto');}};
vm.createContext(c);
vm.runInContext(fs.readFileSync(__dirname+'/modulos/_horas_mi_trabajo_370.js','utf8').replace(/export function /g,'function '),c);
c.URL=URL;c.queueMicrotask=queueMicrotask;
vm.runInContext(fs.readFileSync(__dirname+'/modulos/_tarea_ia.js','utf8').replace(/export function /g,'function ').replace(/export const /g,'const '),c);
vm.runInContext(fs.readFileSync(__dirname+'/modulos/_detalle_tarea_197.js','utf8').replace(/import[^;]+;\s*/g,'').replace(/export function /g,'function ').replace(/export const /g,'const '),c);
vm.runInContext(fs.readFileSync(__dirname+'/modulos/_movimiento_tablero_192.js','utf8').replace(/export function /g,'function ').replace(/export async function /g,'async function ').replace(/export const /g,'const '),c);
vm.runInContext(fs.readFileSync(__dirname+'/modulos/_finalizar_tarea_203.js','utf8').replace(/export function /g,'function '),c);
vm.runInContext(fs.readFileSync(__dirname+'/modulos/_movimiento_detalle_200.js','utf8').replace(/import[^;]+;\s*/g,'').replace(/export function /g,'function '),c);
vm.runInContext(fs.readFileSync(__dirname+'/modulos/_tablero_mi_trabajo_181.js','utf8').replace(/export function /g,'function '),c);
vm.runInContext(fs.readFileSync(__dirname+'/modulos/_metadatos_tarea_225.js','utf8').replace(/export function /g,'function '),c);
Object.assign(c,vm.runInContext('(()=>{'+fs.readFileSync(__dirname+'/modulos/_comentario_durable_366.js','utf8').replace(/export /g,'')+';return {ambitoComentario366,prepararComentario366,reciboComentario366,guardarComentario366,panelComentario366};})()',c));
const source=fs.readFileSync(__dirname+'/modulos/mi_trabajo.js','utf8');
vm.runInContext(source.replace(/import[\s\S]*?from ['"][^'"]+['"];\n/g,'').replace('export default {','const modulo = {').replace(/export function /g,'function ')+';globalThis.modulo=modulo;',c);
// El panel de horas no es objeto de 181. El resto de pintar/detalle/render procede del archivo real.
vm.runInContext('bloqueTuDia=()=>h("horas");bloqueRarasEquipo=()=>null;',c);
const a={id:'task-a',lista_id:'list-1',lista:'Operaciones',cli:'cliente-1',cliente:'Proyecto autorizado',persona_id:'yo',tarea:'Tarea A',estado:'in progress',tipo_estado:'custom',grupo:'hoy',vence:null,prioridad:'high',etiquetas:['equipo']};
const closed={...a,id:'task-closed',tarea:'Tarea final observada',estado:'complete',tipo_estado:'closed',grupo:'completadas'};
const other={...a,id:'task-other',lista_id:'list-2',lista:'Otra lista',tarea:'Otra tarea',estado:'completado',tipo_estado:'custom'};
const cat={'list-1':[{estado:'in progress',tipo:'custom'},{estado:'complete',tipo:'closed'}],'list-2':[{estado:'completado',tipo:'custom'}],'catalogo-ajeno':[{estado:'done',tipo:'closed'}]};
let active=true,posts=0;
const E={D:{tareas:[{...a,persona_id:'otra'},a,closed,other],estados_detalle:cat,fuentes:{}},V:{yo:'yo',ve_equipo:true,estados_detalle:cat,estados_lista:{'list-1':['in progress','complete']},personas:[{id:'yo'},{id:'otra'}],cambios:[{tarea:a.id,quien:'yo',campo:'estado',tipo:'marcar_hecha',valor:'complete',estado:'simulado'}],dias:{},horas_app:[],jornada:[],raras:[]},local:[],cont:h('main'),ctx:{hoy:'2026-10-03',persona:{id:'yo',puestos:[]},real:{id:'yo'},servidor:true,soloLectura:true,pilotoLectura:true,clientes:[{id:'cliente-1'}],nombre:id=>id,accion:()=>{posts++;},vigente:()=>active},vigente:()=>active};
const adapt=(filas,lista='list-1')=>c.prepararTableroTrabajo181(filas,lista,t=>c.resolverEstadoTrabajo(E,t));
let out=adapt([a,{...a,persona_id:'otra'},closed]);assert.equal(out.tareas.length,2);assert.deepEqual(Array.from(out.tareas[0].asignados),['otra','yo']);assert(out.tareas[0].coherente);casos++;
assert.equal(adapt([a],'').tareas.length,0);assert.equal(adapt([a],'missing').lista_disponible,false);assert(!out.listas.some(l=>l.id==='catalogo-ajeno'));casos++;
for(const changed of [{lista_id:'list-2'},{cli:'otro'},{estado:'complete'},{tipo_estado:'closed'},{vence:'2026-10-04'},{tarea:'Otro título'},{prioridad:'low'},{etiquetas:['otra']}]){out=adapt([a,{...a,...changed}]);assert.equal(out.tareas.length,1);assert.equal(out.tareas[0].coherente,false);assert.equal(out.tareas[0].columna_tablero,null);casos++;}
out=adapt([a,{...a,lista_id:null}]);assert.equal(out.tareas[0].coherente,false);casos++;
out=adapt([other],'list-2');assert.equal(out.tareas[0].resolucion_estado.final_flujo,false,'completado es custom activo en su lista');casos++;
const saved=JSON.stringify(E.D);E.tableroLista='list-1';out=c.tareasTableroTrabajo181(E,'mias');assert.equal(out.tareas.length,2);assert.equal(out.tareas[0].persona_id,'yo');assert.equal(out.tareas[0].estado,'in progress');assert(out.tareas[0].capa.intencion_cierre);assert.equal(JSON.stringify(E.D),saved);casos++;
E.V.estados_detalle={};out=c.tareasTableroTrabajo181(E,'mias');assert.equal(out.tareas[0].columna_tablero,null);E.V.estados_detalle=cat;casos++;
E.D.tareas.push({...other,id:'legacy-active',grupo:'completadas'});E.tableroLista='list-2';out=c.tareasTableroTrabajo181(E,'mias');assert.equal(out.tareas.find(t=>t.id==='legacy-active').grupoV,'por_contrastar');E.D.tareas.pop();E.tableroLista='list-1';casos++;
// Vista real: selección explícita; filtros no se amplían al cambiar formato.
E.tableroLista='';E.filtros={cliente:'cliente-1',persona:'',estado:'',prioridad:'',etiqueta:''};c.pintar(E);
const config=(tag,label)=>buscar(E.cont,n=>n.tag===tag&&n.attrs.config?.etiqueta===label).slice(-1)[0]?.attrs.config;
config('chips','Vista de tareas').alCambiar('tablero');assert(text(E.cont).includes('Elige una lista'));assert.equal(buscar(E.cont,n=>n.attrs?.['data-tablero-tarea']).length,0);assert.equal(E.filtros.cliente,'cliente-1');casos++;
let listConfig=config('menu','Lista ClickUp');assert.equal(listConfig.opciones.length,2);assert(!listConfig.opciones.some(x=>x.valor==='catalogo-ajeno'));listConfig.alCambiar('list-1');let cards=buscar(E.cont,n=>n.attrs?.['data-tablero-tarea']);assert.equal(cards.length,1,'Hoy no añade finales ni otras listas');assert(text(cards[0]).includes('Cambio en RO sin confirmar'));assert(text(cards[0]).includes('otra, yo'));casos++;
let inv=buscar(E.cont,n=>n.tag==='button'&&text(n)==='Mi diario · periodo seleccionado')[0];inv.attrs.on.click();cards=buscar(E.cont,n=>n.attrs?.['data-tablero-tarea']);assert.equal(cards.length,2);assert(text(E.cont).includes('Inventario visible'));assert.equal(posts,0);casos++;
const opener=buscar(cards[0],n=>n.attrs?.['data-uso']==='abrir-tarea')[0];opener.attrs.on.click();assert(text(E.cont).includes('El contexto para IA no está disponible'));assert.equal(buscar(E.cont,n=>n.tag==='textarea'&&n.attrs?.['aria-label']==='Comentario').length,0);assert(text(E.cont).includes('Comentario no disponible con los permisos actuales'));assert.equal(posts,0);casos++;
config('menu','Persona');config('menu','Estado').alCambiar('estado-ausente');assert.equal(buscar(E.cont,n=>n.attrs?.['data-tablero-tarea']).length,0);assert.equal(E.filtros.estado,'estado-ausente');assert(text(E.cont).includes('Se conserva tu selección'));casos++;
config('chips','Vista de tareas').alCambiar('lista');assert.equal(E.filtros.estado,'estado-ausente');config('chips','Vista de tareas').alCambiar('tablero');assert.equal(E.filtros.estado,'estado-ausente');casos++;
config('menu','Estado').alCambiar('');config('menu','Lista ClickUp').alCambiar('lista-revocada');assert(text(E.cont).includes('no se amplía la selección automáticamente'));assert.equal(buscar(E.cont,n=>n.attrs?.['data-tablero-tarea']).length,0);casos++;
active=false;const unchanged=text(E.cont);listConfig.alCambiar('list-2');assert.equal(text(E.cont),unchanged);assert.equal(E.tableroLista,'lista-revocada');active=true;casos++;
// Equipo conserva una tarjeta con todos los responsables; prioridad/tag/persona reales.
store.set('ro.mt.modo','equipo');E.tableroLista='list-1';E.filtros={cliente:'',estado:'',persona:'otra',prioridad:'high',etiqueta:'equipo'};c.pintar(E);assert.equal(buscar(E.cont,n=>n.attrs?.['data-tablero-tarea']).length,1);assert.equal(config('menu','Persona').valor,'otra');casos++;
(async()=>{
 let resolve;const deferred=new Promise(r=>resolve=r),cont=h('main');active=true;
 const ctx={...E.ctx,titulo(){},datosModulo:()=>deferred,api:async()=>E.V,vigente:()=>active};
 const p=c.modulo.render(cont,ctx);active=false;resolve(E.D);await p;assert(text(cont).includes('Cargando'));assert.equal(buscar(cont,n=>n.attrs?.['data-tablero-181']!==undefined).length,0);casos++;
 assert.equal(posts,0);assert(!source.includes("ctx.api('tareas/tablero')"));console.log(casos+' casos181 PASS: scope, lista exacta, tipos, multiassigned, pending no cierre, filtros, render real y guards.');
})().catch(e=>{console.error(e);process.exitCode=1;});
