const fs=require('fs'),vm=require('vm'),assert=require('assert');
class El{
 constructor(t,a,...c){this.tag=t;this.attrs=a||{};this.children=[];this.value=a?.value||'';this.listeners={};this.root=false;this.disabled=false;this.append(...c.flat());}
 get isConnected(){return this.root||!!this.parent?.isConnected;}
 append(...cs){for(const c of cs.flat().filter(x=>x!=null)){this.children.push(c);if(typeof c==='object')c.parent=this;}}
 replaceChildren(...cs){for(const c of this.children)if(typeof c==='object')c.parent=null;this.children=[];this.append(...cs);}
 addEventListener(k,f){this.listeners[k]=f;}
}
const h=(t,a,...c)=>new El(t,a,...c),s={h,JSON,Array,Object,String,Math,crypto:{randomUUID:()=> '11111111-1111-4111-8111-111111111111'},
panel:(o,c)=>h('section',{},h('h2',{},o.titulo),o.sub,c),tablaDensa:o=>h('table',{},o.filas.length?o.filas.map(r=>h('tr',{},o.columnas.map(c=>c.celda?c.celda(r):r[c.clave]))):o.vacio.titulo)};
vm.createContext(s);vm.runInContext(fs.readFileSync(__dirname+'/modulos/_operaciones_registros_272.js','utf8').replace(/^import .*;\n/m,'').replace(/export /g,''),s);
const find=(n,t)=>[...(n.tag===t?[n]:[]),...(n.children||[]).filter(c=>typeof c==='object').flatMap(c=>find(c,t))];
const text=n=>typeof n==='object'?(n.textContent||'')+(n.children||[]).map(text).join(' '):String(n??'');
const root=()=>{const r=h('main',{});r.root=true;return r;};
function ctx(rol='account'){const p={id:'a',estado:'activo',puestos:[rol]};return {real:{...p},persona:{...p},datos:{personas:[p]},clientesVisibles:[],nombre:id=>id,veModulo:()=>true,vigente:()=>true,ver:()=>({ok:true}),api:async()=>({version:'272.1',propietario:'a',registros:[],puede_registrar:true})};}
const encargo={tipo:'encargo',objeto:'11111111-1111-4111-8111-111111111111',autor:'a',asignado:'a',revision:1,titulo:'Fixture encargo',hecho:false,prueba:'',limite:null,registrado_por:'a',registrado_en:'2026-10-03T10:00Z'};
let casos=0;
(async()=>{
let c=ctx(),r=root();await s.panelEncargos272(r,c);assert(text(r).includes('Encargos de Tomás'));assert.equal(find(r,'button').length,1);assert(!find(r,'button')[0].disabled);casos++;
let calls=0,bodies=[];c.api=async(path,o)=>{calls++;bodies.push(o.cuerpo);return {version:'272.1',intencion_id:o.cuerpo.intencion_id,recibo:{...encargo,titulo:o.cuerpo.titulo}};};
await find(r,'button')[0].listeners.click();assert.equal(calls,0);find(r,'input')[0].value='Fixture encargo';await find(r,'button')[0].listeners.click();assert.equal(calls,1);assert.equal(bodies[0].revision,0);assert(!('autor' in bodies[0]));assert(text(r).includes('Fixture encargo'));casos++;
c=ctx();r=root();c.api=async()=>({version:'272.1',propietario:'a',registros:[encargo],puede_registrar:true});await s.panelEncargos272(r,c);const hecho=find(r,'button').find(b=>text(b)==='Guardar hecho');let post=0;c.api=async()=>{post++;throw Error('not expected');};await hecho.listeners.click();assert.equal(post,0);casos++;
const prueba=find(r,'input').find(x=>x.attrs['aria-label']==='Prueba del encargo');prueba.value='Fixture evidencia';const intents=[];c.api=async(path,o)=>{intents.push(o.cuerpo);throw Error('PRIVATE_ERROR');};await hecho.listeners.click();await hecho.listeners.click();assert.equal(intents.length,2);assert.equal(intents[0],intents[1]);assert(prueba.disabled);assert(!text(r).includes('PRIVATE_ERROR'));casos++;
c=ctx();r=root();await s.panelEncargos272(r,c);const boton=find(r,'button')[0];find(r,'input')[0].value='Fixture';let release;c.api=()=>new Promise(done=>release=done);const p=boton.listeners.click();boton.parent.replaceChildren();release({});await p;assert(boton.disabled);casos++;
for(const change of [c=>c.persona.id='other',c=>c.soloLectura=true,c=>c.veModulo=()=>false,c=>c.datos.personas.push({...c.real})]){
 c=ctx();r=root();await s.panelEncargos272(r,c);find(r,'input')[0].value='Fixture';const btn=find(r,'button')[0];change(c);let n=0;c.api=async()=>{n++;return {};};await btn.listeners.click();assert.equal(n,0);}casos++;
c=ctx('operaciones');r=root();await s.panelFotosControl272(r,c);assert(text(r).includes('Fotos de los miércoles y viernes'));assert.equal(find(r,'button').length,1);let fotoBody;c.api=async(path,o)=>{fotoBody=o.cuerpo;return {version:'272.1',intencion_id:o.cuerpo.intencion_id,recibo:{tipo:'foto',registrado_por:'a',registrado_en:'2026-10-03T10:00Z',cumplimiento:null,exhaustiva:false,metricas:Array.from({length:7},(_,i)=>({valor:i===0?0:null,detalle:'Copia parcial',fecha_fuente:null,estado:'desconocido',etiqueta:'Fixture'}))}};};await find(r,'button')[0].listeners.click();assert.equal(fotoBody.tipo,'foto');assert(!('metricas' in fotoBody));assert(!('registrado_en' in fotoBody));assert(text(r).includes('Cortes y cobertura'));casos++;
c=ctx();r=root();await s.panelFotosControl272(r,c);assert.equal(find(r,'button').length,0);casos++;
c=ctx();r=root();let res;c.api=()=>new Promise(done=>res=done);const loading=s.panelEncargos272(r,c);c.persona.id='other';res({version:'272.1',propietario:'a',registros:[encargo],puede_registrar:true});await loading;assert(!text(r).includes('Fixture encargo'));casos++;
console.log(casos+' grupos272 UI PASS: encargos/prueba, recibos, mismo UUID, nodo/identidad/permisos, fotos sin payload de métricas.');
})().catch(e=>{console.error(e);process.exit(1);});
