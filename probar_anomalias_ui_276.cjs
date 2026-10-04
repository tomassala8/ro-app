const fs=require('fs'),vm=require('vm'),assert=require('assert');
class El{
 constructor(t,a,...c){this.tag=t;this.attrs=a||{};this.children=[];this.value=a?.value||'';this.listeners={};this.root=false;this.disabled=false;this.open=false;this.append(...c.flat());}
 get isConnected(){return this.root||!!this.parent?.isConnected;}
 set textContent(v){this.replaceChildren();this._text=String(v);}
 get textContent(){return this._text||'';}
 append(...cs){for(const c of cs.flat().filter(x=>x!=null)){this.children.push(c);if(typeof c==='object')c.parent=this;}}
 replaceChildren(...cs){for(const c of this.children)if(typeof c==='object')c.parent=null;this.children=[];this.append(...cs);}
 addEventListener(k,f){this.listeners[k]=f;}
}
const h=(t,a,...c)=>new El(t,a,...c),s={h,JSON,Array,Object,String,Number,RegExp,encodeURIComponent,crypto:{randomUUID:()=> '11111111-1111-4111-8111-111111111111'}};
vm.createContext(s);vm.runInContext(fs.readFileSync(__dirname+'/modulos/_operaciones_anomalias_276.js','utf8').replace(/^import .*;\n/m,'').replace(/export /g,''),s);
const find=(n,t)=>[...(n.tag===t?[n]:[]),...(n.children||[]).filter(c=>typeof c==='object').flatMap(c=>find(c,t))];
const text=n=>typeof n==='object'?(n.textContent||'')+(n.children||[]).map(text).join(' '):String(n??'');
const tick=()=>new Promise(done=>setImmediate(done));
const fila={id:'entry_1',persona_id:'a'},hash='a'.repeat(64);
const dto=()=>({version:'276.1',origen:{id:fila.id,persona_id:'a',huella_origen:hash},revision:0,registro:null,puede_registrar:true});
function setup(){const p={id:'a',estado:'activo',puestos:['operaciones']};let calls=[];const c={real:{...p},persona:{...p},datos:{personas:[p]},veModulo:()=>true,vigente:()=>true,ver:()=>({ok:true}),api:async(path,o)=>{calls.push([path,o]);return dto();}};const root=h('main',{});root.root=true;const node=s.controlAnomalia276(c,fila);root.append(node);return {c,root,node,calls};}
async function open(x){x.node.open=true;x.node.listeners.toggle();await tick();}
function receipt(b){return {version:'276.1',intencion_id:b.intencion_id,recibo:{anomalia_id:b.anomalia_id,persona_id:'a',huella_origen:b.huella_origen,revision:b.revision+1,decision:b.decision,registrado_por:'a',registrado_en:'2026-10-03T10:00Z',entrada_modificada:false,envio_realizado:false}};}
let n=0;
(async()=>{
 let x=setup();assert.equal(x.calls.length,0);await open(x);assert.equal(x.calls.length,1);assert.equal(find(x.node,'button').length,3);assert(find(x.node,'button').every(b=>b.attrs.style.minHeight==='44px'));assert.equal(x.calls[0][0],'operaciones/anomalias?id=entry_1');n++;
 let post=0;x.c.api=async()=>{post++;return {};};await find(x.node,'button')[2].listeners.click();assert.equal(post,0);assert(text(x.node).includes('Escribe una prueba'));n++;
 const bodies=[];x.c.api=async(path,o)=>{bodies.push(o.cuerpo);throw Error('SECRET_PROVIDER_ERROR');};const btn=find(x.node,'button')[0];await btn.listeners.click();await btn.listeners.click();assert.equal(bodies.length,2);assert.strictEqual(bodies[0],bodies[1]);assert(find(x.node,'input')[0].disabled);assert(!text(x.node).includes('SECRET_PROVIDER_ERROR'));await find(x.node,'button')[1].listeners.click();assert.equal(bodies.length,2);n++;
 x.c.api=async(path,o)=>receipt(o.cuerpo);await btn.listeners.click();assert(text(x.node).includes('registrado en RO'));assert(!btn.isConnected);assert(btn.disabled);assert(find(x.node,'button').every(b=>!b.disabled));n++;
 x=setup();await open(x);let reads=0;x.c.api=async()=>{reads++;return dto();};x.node.open=false;x.node.listeners.toggle();await open(x);assert.equal(reads,1);n++;
 for(const revoke of [c=>c.persona.id='other',c=>c.veModulo=()=>false,c=>c.ver=()=>({ok:false}),c=>c.datos.personas[0].estado='baja',c=>c.datos.personas.push({...c.real})]){
  x=setup();let release;x.c.api=()=>new Promise(done=>release=done);x.node.open=true;x.node.listeners.toggle();revoke(x.c);release(dto());await tick();assert.equal(find(x.node,'button').length,0);assert.equal(find(x.node,'input').length,0);
 }n++;
 for(const revoke of [c=>c.persona.id='other',c=>c.ver=()=>({ok:false})]){
  x=setup();await open(x);const old=find(x.node,'button')[0];let release;x.c.api=(path,o)=>new Promise(done=>release=()=>done(receipt(o.cuerpo)));const saving=old.listeners.click();revoke(x.c);release();await saving;assert.equal(find(x.node,'input').length,0);assert(old.disabled);assert.equal(text(find(x.node,'summary')[0]),'Revisar');
 }n++;
 x=setup();await open(x);const old=find(x.node,'button')[0];let release;x.c.api=(path,o)=>new Promise(done=>release=()=>done(receipt(o.cuerpo)));const saving=old.listeners.click();x.root.replaceChildren();release();await saving;assert(old.disabled);n++;
 for(const change of [c=>c.soloLectura=true,c=>c.persona.id='other',c=>c.veModulo=()=>false]){
  x=setup();await open(x);const b=find(x.node,'button')[0];change(x.c);let p=0;x.c.api=async()=>{p++;return {};};await b.listeners.click();assert.equal(p,0);
 }n++;
 x=setup();x.c.api=async()=>({...dto(),registro:{decision:'correcto',registrado_por:'a',registrado_en:'2026-10-03T10:00Z'}});await open(x);let p=0;x.c.api=async()=>{p++;return {};};await find(x.node,'button')[1].listeners.click();assert.equal(p,0);n++;
 x=setup();x.c.api=async()=>({...dto(),origen:{...dto().origen,persona_id:'other'}});await open(x);assert.equal(find(x.node,'button').length,0);n++;
 console.log(n+' grupos276 UI PASS: lectura al abrir, prueba, UUID estable, recibo, refresh, revocación, nodo desconectado, solo lectura.');
})().catch(e=>{console.error(e);process.exit(1);});
