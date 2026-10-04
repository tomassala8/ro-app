const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
class N {
 constructor(tag,attrs,...children){this.tag=tag;this.attrs=attrs||{};this.children=[];this.value=this.attrs.value||'';this.checked=false;this.isConnected=true;this.handlers={};this.append(...children);}
 append(...xs){for(const x of xs.flat(Infinity))if(x!==null&&x!==undefined&&x!==false)this.children.push(x);}
 replaceChildren(...xs){this.children=[];this.append(...xs);}
 addEventListener(k,f){this.handlers[k]=f;}
 set textContent(v){this.replaceChildren(v);}get textContent(){return this.children.map(x=>x instanceof N?x.textContent:String(x)).join(' ');}
}
const src=fs.readFileSync(path.join(__dirname,'modulos/mi_dia.js'),'utf8');
const panel=src.slice(src.indexOf('function semanaDeclaracionesControl'),src.indexOf('// ================================================================== el número que manda'));
const tick=()=>new Promise(r=>setImmediate(r));let cases=0;
function create(ops=false){
 let hoy='2026-10-03',alive=true,resolve,reject,calls=0;const b={Intl,console,Promise,Map,Set,Date,h:(...a)=>new N(...a),chipEstado:(c,t)=>new N('chip',{color:c},t),vacioLinea:t=>new N('p',{},t),hoyMadrid:()=>hoy};vm.createContext(b);
 for(const file of ['control_cartera.js','_evidencias_resumen.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'modulos',file),'utf8').replace(/export /g,''),b);
 vm.runInContext(panel,b);
 const clients=['uno','dos','extra'].map(id=>({id,nombre:id,activo_confirmado:true,servicios:{}}));
 const p={id:ops?'ops':'own',puestos:[ops?'operaciones':'account']};
 const ctx={persona:p,real:p,servidor:true,clientes:clients,clientesVisibles:clients.slice(0,2),carteraPorSilla:{account:new Set(['uno'])},datos:{personas:[{...p,estado:'activo'}],asignaciones:[]},veModulo:()=>true,ver:()=>({ok:true}),api:()=>{calls++;return new Promise((r,j)=>{resolve=r;reject=j;});},nombre:id=>id};
 const n=b.panelControlCartera(ctx,{opcional:()=>null},ops?'operaciones':'account',()=>alive);
 const r=id=>({cliente_id:id,contactos_declarados:id==='uno'?2:7,reuniones_declaradas:1,source_kind:'registro_equipo',verificacion_externa:false,cumplimiento:null});
 const response={semana_inicio:'2026-09-28',clientes:clients.map(c=>r(c.id)),cobertura:'parcial',verificacion_externa:false,cumplimiento:null};
 return {ctx,n,response,b,finish:()=>resolve(response),fail:()=>reject(Error('fixture')),count:()=>calls,stop:()=>alive=false,date:d=>hoy=d};
}
function find(n,p){if(n instanceof N&&p(n))return n;for(const c of n.children||[]){const r=find(c,p);if(r)return r;}}
(async()=>{
 let t=create();await tick();assert.equal(t.count(),1);t.finish();await tick();assert(t.n.textContent.includes('2 contactos declarados'));assert(!t.n.textContent.includes('7 contactos declarados'));assert(t.n.textContent.includes('1 reunión declarada'));cases++;
 const search=find(t.n,n=>n.tag==='input'&&n.attrs.type==='search');search.value='no-coincide';search.handlers.input();assert.equal(t.count(),1);assert(t.n.textContent.includes('0 de 1'));search.value='';search.handlers.input();assert(t.n.textContent.includes('2 contactos declarados'));cases++;
 t=create(true);await tick();t.finish();await tick();assert(t.n.textContent.includes('9 contactos declarados'));assert(t.n.textContent.includes('2 reuniones declaradas'));assert(!t.n.textContent.includes('16 contactos declarados'));cases++;
 for(const alter of [t=>t.stop(),t=>t.ctx.persona={id:'other',puestos:['account']},t=>t.ctx.ver=()=>({ok:false}),t=>t.ctx.clientes.pop(),t=>t.date('2026-10-05'),t=>t.ctx.real.puestos=['seo']]){
  t=create();await tick();alter(t);t.finish();await tick();assert(!t.n.textContent.includes('2 contactos declarados'));cases++;
 }
 for(const alter of [r=>r.clientes.push({...r.clientes[0]}),r=>r.clientes[0].contactos_declarados=null,r=>r.clientes[0].verificacion_externa=true,r=>r.clientes.push({...r.clientes[0],cliente_id:'ajeno'})]){
  t=create();await tick();alter(t.response);t.finish();await tick();assert(!t.n.textContent.includes('2 contactos declarados'));assert(!t.n.textContent.includes('0 contactos declarados'));cases++;
 }
 t=create();await tick();t.response.clientes=t.response.clientes.filter(r=>r.cliente_id!=='uno');t.finish();await tick();assert(!t.n.textContent.includes('0 contactos declarados'));cases++;
 t=create();await tick();t.response.clientes[0].contactos_declarados=0;t.finish();await tick();assert(t.n.textContent.includes('0 contactos declarados'));assert(t.n.textContent.includes('Cero no significa ausencia de actividad'));cases++;
 t=create();await tick();t.fail();await tick();assert(!t.n.textContent.includes('0 contactos declarados'));assert(t.n.textContent.includes('Sin dato'));cases++;
 t=create();t.n.isConnected=false;await tick();assert.equal(t.count(),0);cases++;
 t=create();t.n.isConnected=false;t.n.isConnected=true;await tick();assert.equal(t.count(),1);t.finish();await tick();assert(t.n.textContent.includes('2 contactos declarados'));cases++;
 t=create();await tick();const q=find(t.n,n=>n.tag==='input'&&n.attrs.type==='search');q.value='no-coincide';q.handlers.input();t.finish();await tick();assert.equal(q.value,'no-coincide');assert(t.n.textContent.includes('0 de 1'));assert.equal(t.count(),1);cases++;
 assert.equal(t.b.semanaDeclaracionesControl('2026-10-04'),'2026-09-28');assert.equal(t.b.semanaDeclaracionesControl('2026-02-30'),null);cases++;
 console.log(`${cases} casos de panel real pasan: una GET, scope/intersección, filtros, guards y neutralidad.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
