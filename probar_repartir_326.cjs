const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs={},kids=[]){this.tag=tag;this.attrs=attrs;this.children=[];this.isConnected=true;this.append(...kids);}append(...xs){for(const x of xs.flat(Infinity))if(x!=null)this.children.push(x);}replaceChildren(...xs){this.children=[];this.append(...xs);}get text(){return this.children.map(x=>x instanceof Node?x.text:String(x)).join(' ');}}
const h=(tag,attrs,...kids)=>new Node(tag,attrs,kids), chipEstado=(c,t)=>h('span',{},t);
let src=fs.readFileSync(__dirname+'/modulos/_operaciones_rituales_264.js','utf8').replace(/^import .*;$/mg,'').replace(/export /g,'');
const box={h,chipEstado,console,Intl};vm.createContext(box);
function load(file,names){let source=fs.readFileSync(__dirname+'/modulos/'+file+'.js','utf8').replace(/^import .*;$/mg,'').replace(/export /g,'');vm.runInContext(`Object.assign(globalThis,(()=>{${source};return {${names.join(',')}};})());`,box);}
load('control_cartera',['prepararControlCartera']);load('_account_fuegos_346',['accountFuego346','firmaAccountFuegos346']);load('_viernes_accounts_347',['ambitoViernes347','filasViernes347']);load('_repartir_accounts_352',['ambitoRepartir352','atribuirReparto352']);vm.runInContext(src+';this.API={filasRepartir326,renderRituales264};',box);const A=box.API;
function ctx(){const p={id:'ops',estado:'activo',puestos:['operaciones']},owner={id:'account',estado:'activo',puestos:['account']};return {servidor:true,real:p,persona:p,hoy:'2026-10-03',datos:{personas:[p,owner],asignaciones:[{cliente_id:'c',persona_id:'account',silla:'account',principal:true,confianza:'confirmada'}]},clientesVisibles:[{id:'c',nombre:'CLIENTE',activo_confirmado:true,detalle:true}],veModulo:()=>true,ver:()=>({ok:true}),vigente:()=>true,nombre:x=>x,navegar:()=>{}};}
const P={generado:'2026-10-03',revisiones:[{id:'r2',cliente_id:'c',tarea:'RECENT2',estado:'revisión técnica',revisa:'técnica',dias:2},{id:'r31',cliente_id:'c',tarea:'OLD31',estado:'revisión técnica',revisa:'técnica',dias:31},{id:'missing',cliente_id:'c',tarea:'UNKNOWN',estado:'revisión técnica',revisa:'técnica',dias:null}],cola:[{id:'b10',cli:'c',tarea:'BLOCK10',grupo:'bloqueada',estado_determinado:true,estado:'bloqueado',dias_estado:10}]};
const B={correos:[{id:'k29',cliente_id:'c',asunto:'TICKET29',horas:29*24},{id:'k31',cliente_id:'c',asunto:'TICKET31',horas:31*24}]};
(async()=>{
 let c=ctx(),r=A.filasRepartir326(c,P,B);assert.deepEqual(Array.from(r.tareas,x=>x.id),['r31','b10','r2','missing']);assert.deepEqual(Array.from(r.tickets,x=>x.id),['k31']);
 let cont=new Node('main');c.datosModulo=async s=>s.startsWith('produccion')?P:B;await A.renderRituales264(cont,c,'repartir');for(const tx of ['RECENT2','OLD31','BLOCK10','UNKNOWN','Sin fecha','TICKET31'])assert(cont.text.includes(tx),tx);assert(!cont.text.includes('TICKET29'));
 c=ctx();c.ver=()=>({ok:false});assert.equal(A.filasRepartir326(c,P,B).tareas.length,0);
 c=ctx();c.clientesVisibles[0].activo_confirmado=false;assert.equal(A.filasRepartir326(c,P,B).tareas.length,0);
 c=ctx();c.clientesVisibles.push({...c.clientesVisibles[0]});assert.equal(A.filasRepartir326(c,P,B).tareas.length,0);
 c=ctx();c.datos.asignaciones=[];c.clientesVisibles[0].responsable_id='account';assert(A.filasRepartir326(c,P,B).tareas.every(x=>x.account_id===null));
 c=ctx();c.datos.personas[1].estado='inactivo';assert(A.filasRepartir326(c,P,B).tareas.every(x=>x.account_id===null));
 c=ctx();c.datos.personas.push({...c.datos.personas[1]});assert(A.filasRepartir326(c,P,B).tareas.every(x=>x.account_id===null));
 c=ctx();c.real={...c.real,estado:'inactivo'};assert.equal(A.filasRepartir326(c,P,B).tareas.length,0);
 c=ctx();const amb=JSON.parse(JSON.stringify(P));amb.revisiones.push({...amb.revisiones[0]});assert(!A.filasRepartir326(c,amb,B).tareas.some(x=>x.id==='r2'));
 c=ctx();let resolve;const pending=new Promise(r=>resolve=r);c.datosModulo=s=>s.startsWith('produccion')?pending:Promise.resolve(B);cont=new Node('main');const promise=A.renderRituales264(cont,c,'repartir');c.ver=()=>({ok:false});resolve(P);await promise;assert(!cont.text.includes('RECENT2'));
 c=ctx();c.datosModulo=async s=>s.startsWith('produccion')?P:B;cont=new Node('main');await A.renderRituales264(cont,c,'repartir');const walk=n=>n instanceof Node?[n,...n.children.flatMap(walk)]:[];const link=walk(cont).find(x=>x.tag==='a'&&x.text==='RECENT2');c.ver=()=>({ok:false});let prevented=false;link.attrs.on.click({preventDefault:()=>prevented=true});assert(prevented);assert(!cont.text.includes('RECENT2'));
 console.log('326:12 grupos PASS (funciones y render reales, sin proveedores/POST).');
})().catch(e=>{console.error(e);process.exit(1);});
