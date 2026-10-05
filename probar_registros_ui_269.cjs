const fs=require('fs'),vm=require('vm'),assert=require('assert');
class El {
 constructor(t,a,...children){this.tag=t;this.attrs=a||{};this.children=[];this.value=a?.value||'';this.disabled=false;this.listeners={};this.root=false;this.append(...children.flat());}
 get isConnected(){return this.root||!!this.parent?.isConnected;}
 append(...cs){for(const c of cs.flat().filter(x=>x!=null)){this.children.push(c);if(typeof c==='object')c.parent=this;}}
 replaceChildren(...cs){for(const c of this.children)if(typeof c==='object')c.parent=null;this.children=[];this.append(...cs);}
 addEventListener(e,f){this.listeners[e]=f;}
}
const h=(t,a,...c)=>new El(t,a,...c),sandbox={h,panel:(o,c)=>h('section',{},h('h2',{},o.titulo),c),JSON,Array,Object,String,queueMicrotask,crypto:{randomUUID:()=> '11111111-1111-4111-8111-111111111111'}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(__dirname+'/modulos/_operaciones_registros_269.js','utf8').replace(/^import .*;\n/m,'').replace(/export /g,''),sandbox);
const find=(n,t)=>[...(n.tag===t?[n]:[]),...(n.children||[]).filter(c=>typeof c==='object').flatMap(c=>find(c,t))];
const text=n=>typeof n==='object'?(n.textContent||'')+(n.children||[]).map(text).join(' '):String(n||'');
const p={id:'a',estado:'activo',puestos:['account']},periodos={manana:'2026-10-03',cierre:'2026-10-03',lunes:'2026-09-28',viernes:'2026-09-28',mes:'2026-10'};
function ctx(){return {real:{...p},persona:{...p},veModulo:()=>true,vigente:()=>true,api:async()=>({version:'269.1',propietario:'a',periodos,registros:[],puede_registrar:true})};}
const root=()=>{const r=h('main',{});r.root=true;return r;};
let casos=0;
(async()=>{
let c=ctx(),r=root();await sandbox.panelRituales269(r,c);assert.equal(find(r,'button').length,5);assert(find(r,'button').every(b=>!b.disabled));casos++;
let post=0,bodies=[];c.api=async(path,options)=>{if(!options)return {version:'269.1',propietario:'a',periodos,registros:[],puede_registrar:true};post++;bodies.push(options.cuerpo);return {version:'269.1',intencion_id:options.cuerpo.intencion_id,recibo:{...options.cuerpo,autor:'a',revision:1,envio_realizado:false,registrado_en:'2026-10-03T12:00:00Z'}};};
await find(r,'button')[0].listeners.click();assert.equal(post,1);assert.equal(bodies[0].revision,0);assert(!('autor' in bodies[0]));assert(text(r).includes('Guardado en RO'));casos++;
for(const cambio of [()=>c.persona.id='other',()=>c.soloLectura=true,()=>r.root=false,()=>c.veModulo=()=>false]){
 c=ctx();r=root();await sandbox.panelRituales269(r,c);c.api=async()=>{post++;throw Error('no');};const before=post;cambio();await find(r,'button')[0].listeners.click();assert.equal(post,before);}casos++;
c=ctx();r=root();let release;c.api=()=>new Promise(done=>release=done);const promise=sandbox.panelRituales269(r,c);c.real.id='revoked';release({version:'269.1',propietario:'a',periodos,registros:[],puede_registrar:true});await promise;assert.equal(find(r,'button').length,0);casos++;
c=ctx();r=root();await sandbox.panelRituales269(r,c);const b=find(r,'button')[0];let resolvePost;c.api=()=>new Promise(done=>resolvePost=done);const pending=b.listeners.click();r.root=false;resolvePost({});await pending;assert(b.disabled);casos++;
c=ctx();r=root();await sandbox.panelRituales269(r,c);const boton=find(r,'button')[0];const intents=[];c.api=async(path,o)=>{intents.push(o.cuerpo);throw Error('PRIVATE_ERROR');};await boton.listeners.click();await boton.listeners.click();assert.equal(intents.length,2);assert.equal(intents[0],intents[1]);assert.equal(intents[0].intencion_id,intents[1].intencion_id);assert(!text(r).includes('PRIVATE_ERROR'));assert(find(r,'input')[0].disabled);casos++;
c=ctx();r=root();c.soloLectura=true;await sandbox.panelRituales269(r,c);assert(find(r,'button').every(b=>b.disabled));casos++;
console.log(casos+' grupos269 UI PASS: cinco rituales, recibo, identidad/nodo/permiso, retraso y mismo UUID tras fallo.');
})().catch(e=>{console.error(e);process.exit(1);});
