const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class N{constructor(t,a={},kids=[]){this.tag=t;this.attrs=a;this.children=[];this.append(...kids)}append(...xs){for(const x of xs.flat(Infinity)){if(x==null)continue;if(x instanceof N)x.parent=this;this.children.push(x)}}get isConnected(){return this.connected===true||!!this.parent?.isConnected}replaceChildren(...xs){for(const x of this.children)if(x instanceof N)x.parent=null;this.children=[];this.append(...xs)}get text(){return this.children.map(x=>x instanceof N?x.text:String(x)).join(' ')}focus(){}addEventListener(){}all(){return [this,...this.children.filter(x=>x instanceof N).flatMap(x=>x.all())]}}
const h=(t,a,...xs)=>new N(t,a,xs),tick=()=>new Promise(r=>setImmediate(r));
const source=fs.readFileSync(__dirname+'/modulos/captacion.js','utf8'),a=source.indexOf('function pAuditoria('),b=source.indexOf('// ------------------------------------------------------------------ pestaña · creatividades',a),env={h,S:{1:'4px',2:'8px'},queueMicrotask,logoCliente:()=>null,chipCli:()=>null,nombre:(_,id)=>id,fDiaRO:x=>x,listaConIcono:rows=>h('ul',{},rows.map(x=>h('li',{},x.texto,x.extra))),botonConfirmar:o=>h('button',{'data-action':o.texto,onConfirm:o.alConfirmar},o.texto),panel:(o,...xs)=>h('section',{},h('h2',{},o.titulo),...xs),vacio:o=>h('p',{},o.titulo)};vm.createContext(env);vm.runInContext(source.slice(a,b),env);
const deferred=()=>{let resolve,reject;const p=new Promise((a,b)=>{resolve=a;reject=b});return {p,resolve,reject}},row={cliente_id:'c',nombre:'Cliente fixture428',meta_activa:true},data={};
function fixture(){let valid=true;const ctx={servidor:true,real:{id:'ops',puestos:['operaciones']},persona:{id:'ops',puestos:['operaciones']},vigente:()=>valid,api:async()=>({acciones:[]}),accion:async()=>({ok:true})};const main=h('main',{});main.connected=true;const frame=env.pAuditoria(ctx,data,[row]);return {ctx,frame,mount:()=>main.append(frame),invalidate:()=>valid=false,buttons:()=>frame.all().filter(n=>n.tag==='button')};}
(async()=>{
let n=0;const pass=()=>n++;
let f=fixture(),calls=0;f.ctx.api=async()=>{calls++;return {acciones:[]}};await tick();assert.equal(calls,0);f.mount();pass();
f=fixture();const get=deferred();f.ctx.api=()=>get.p;f.mount();await tick();f.invalidate();get.resolve({acciones:[{tipo:'auditoria_semanal',objeto:'STALE_PRIVATE_FIXTURE',texto:'decisión',quien:'ops'}]});await tick();assert(!f.frame.text.includes('STALE_PRIVATE_FIXTURE'));assert(!f.frame.text.includes(row.nombre));pass();
f=fixture();const fail=deferred();f.ctx.api=()=>fail.p;f.mount();await tick();f.invalidate();fail.reject(Error('STALE_ERROR_FIXTURE'));await tick();assert(!f.frame.text.includes('STALE_ERROR_FIXTURE'));pass();
f=fixture();f.mount();await tick();let actions=0;f.ctx.accion=async()=>actions++;const btn=f.buttons()[0];f.invalidate();await assert.rejects(btn.attrs.onConfirm(),/La vista ha cambiado/);assert.equal(actions,0);pass();
f=fixture();f.mount();await tick();const write=deferred();f.ctx.accion=()=>write.p;const action=f.buttons()[0].attrs.onConfirm();f.ctx.persona.id='other';write.resolve({ok:true});await assert.rejects(action,/La vista ha cambiado/);assert(!f.frame.text.includes(row.nombre));pass();
f=fixture();f.mount();await tick();f.ctx.soloLectura=true;f.ctx.accion=async()=>{throw Error('must not call')};await assert.rejects(f.buttons()[0].attrs.onConfirm(),/La vista ha cambiado/);pass();
f=fixture();f.mount();await tick();f.ctx.accion=async()=>{throw Error('fixture rejected')};await assert.rejects(f.buttons()[0].attrs.onConfirm(),/fixture rejected/);pass();
f=fixture();f.mount();await tick();f.ctx.persona.puestos.push('seo');await assert.rejects(f.buttons()[0].attrs.onConfirm(),/La vista ha cambiado/);pass();
f=fixture();f.mount();await tick();const first=deferred(),second=deferred();let reads=0;f.ctx.api=()=> (++reads===1?first.p:second.p);const x=f.buttons()[0].attrs.onConfirm(),y=f.buttons()[1].attrs.onConfirm();await tick();second.resolve({acciones:[{tipo:'auditoria_semanal',objeto:'NEW_FIXTURE',texto:'n',quien:'ops'}]});await y;first.resolve({acciones:[{tipo:'auditoria_semanal',objeto:'OLD_FIXTURE',texto:'o',quien:'ops'}]});await x;assert(f.frame.text.includes('NEW_FIXTURE'));assert(!f.frame.text.includes('OLD_FIXTURE'));pass();
f=fixture();f.mount();await tick();let posted;f.ctx.accion=async x=>{posted=x;return {ok:true}};const answer=await f.buttons()[0].attrs.onConfirm();assert.equal(posted.tipo,'auditoria_semanal');assert.equal(posted.cliente_id,'c');assert(answer.includes('simulación'));pass();
// El componente real considera null como éxito: el guard debe rechazar, nunca devolver null.
const comps=fs.readFileSync(__dirname+'/componentes.js','utf8');
const ca=comps.indexOf('export function botonConfirmar(o)'),cb=comps.indexOf('/** candado(',ca);
vm.runInContext(comps.slice(ca,cb).replace('export function','function'),env);
f=fixture();f.mount();await tick();
let wrap=f.frame.all().find(x=>x.attrs.class==='confirmar');
wrap.children[0].attrs.on.click();
const yes=wrap.children.find(x=>x instanceof N&&x.tag==='button'&&x.text==='Apuntar');
f.invalidate();await yes.attrs.on.click();
assert(!wrap.text.includes('✓'));assert(!wrap.text.includes('Hecho'));assert(wrap.text.includes('La vista ha cambiado'));pass();
console.log(n+' grupos428 PASS: función real, montaje, lateGET/error, acción/rechazo, identidad/roles, sólolectura, respuestasfueraorden y contrato intacto; sin red/POST real.');
})().catch(e=>{console.error(e);process.exitCode=1});
