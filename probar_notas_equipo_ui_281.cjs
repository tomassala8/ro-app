const fs=require('fs'),vm=require('vm'),assert=require('assert');
class E{
 constructor(t,a,...cs){this.tag=t;this.attrs=a||{};this.children=[];this.value=a?.value||'';this.listeners={};this.root=false;this.disabled=false;this.append(...cs.flat());}
 get isConnected(){return this.root||!!this.parent?.isConnected;}
 get childNodes(){return this.children;}
 set textContent(v){this.replaceChildren();this._text=String(v);}
 get textContent(){return this._text||'';}
 append(...cs){for(const c of cs.flat().filter(x=>x!=null)){this.children.push(c);if(typeof c==='object')c.parent=this;}}
 replaceChildren(...cs){for(const c of this.children)if(typeof c==='object')c.parent=null;this.children=[];this.append(...cs);}
 addEventListener(k,f){this.listeners[k]=f;}
}
const h=(t,a,...cs)=>new E(t,a,...cs),s={h,JSON,Array,Object,Number,String,Date,Map,RegExp,encodeURIComponent,crypto:{randomUUID:()=> '11111111-1111-4111-8111-111111111111'}};
vm.createContext(s);vm.runInContext(fs.readFileSync(__dirname+'/modulos/_horas_diarias_238.js','utf8').replace(/export /g,''),s);vm.runInContext(fs.readFileSync(__dirname+'/modulos/_operaciones_notas_equipo_281.js','utf8').replace(/^import .*;\n/gm,'').replace(/export /g,''),s);
const find=(n,t)=>[...(n.tag===t?[n]:[]),...(n.children||[]).filter(x=>typeof x==='object').flatMap(x=>find(x,t))];
const text=n=>typeof n==='object'?(n.textContent||'')+(n.children||[]).map(text).join(' '):String(n??'');
const root=()=>{const r=h('main',{});r.root=true;return r;};
const dto=()=>({version:'281.1',persona_id:'p',periodo_actual:'2026-10',revision:0,registro:null,puede_registrar:true});
const fixture={persona_id:'p',nombre:'Persona sintética',horas_semana_pasada:{valor:12,desde:'2026-09-21',hasta:'2026-09-27',fecha_fuente:'2026-10-03',estado:'observado',cobertura:'parcial'}};
function context(){return {real:{id:'m'},persona:{id:'m'},datos:{personas:[{id:'m',estado:'activo'},{id:'p',estado:'activo'}]},ver:()=>({ok:true}),veModulo:()=>true,vigente:()=>true,api:async()=>dto()};}
function montar(c=context()){const r=root();s.panelEquipoNotas281(r,c,[fixture],{hoy:'2026-10-03'});return {r,c,row:find(r,'tr')[1]};}
const boton=(r,t)=>find(r,'button').find(b=>text(b)===t);
let n=0;
(async()=>{
 let x=montar();assert.equal(find(x.r,'th').length,7);assert.equal(x.row.children.length,7);assert.equal(find(x.r,'select').length,2);assert(find(x.r,'input')[0].disabled);assert(text(x.r).includes('12 h'));n++;
 const obs={...fixture.horas_semana_pasada,desde:'2026-09-28',hasta:'2026-10-04'};
 assert.equal(s.horasNotas281(x.c,'p',obs,'2026-10-03',true),null);obs.hasta='2026-10-03';assert.equal(s.horasNotas281(x.c,'p',obs,'2026-10-03',false).valor,12);
 x.c.ver=()=>({ok:false});assert.equal(s.horasNotas281(x.c,'p',obs,'2026-10-03',false),null);n++;
 x=montar();let calls=0;x.c.api=async ruta=>{calls++;assert.equal(ruta,'operaciones/notas-equipo?persona_id=p');return dto();};assert.equal(calls,0);await boton(x.r,'Ver nota').listeners.click();assert.equal(calls,1);assert(!find(x.r,'input')[0].disabled);assert(text(x.r).includes('Período 2026-10'));n++;
 let post=0;x.c.api=async()=>{post++;throw Error('PRIVATE_ERROR');};await boton(x.r,'Guardar declaración').listeners.click();assert.equal(post,0);n++;
 const prueba=find(x.r,'input')[0],sels=find(x.r,'select');prueba.value='Hecho observable';sels[0].value='7';sels[1].value='formar';const bodies=[];x.c.api=async(path,o)=>{bodies.push(o.cuerpo);throw Error('PRIVATE_ERROR');};await boton(x.r,'Guardar declaración').listeners.click();await boton(x.r,'Guardar declaración').listeners.click();assert.equal(bodies.length,2);assert.strictEqual(bodies[0],bodies[1]);assert(prueba.disabled);assert(!text(x.r).includes('PRIVATE_ERROR'));assert(!('autor' in bodies[0]));n++;
 x.c.api=async(path,o)=>({version:'281.1',intencion_id:o.cuerpo.intencion_id,recibo:{...o.cuerpo,revision:1,autor:'m',registrado_en:'2026-10-03T10:00Z',puntuacion_automatica:false,decision_laboral:false,envio_realizado:false}});await boton(x.r,'Guardar declaración').listeners.click();assert(text(x.r).includes('propuesta no ejecutada'));assert(!prueba.disabled);n++;
 for(const change of [c=>c.persona.id='other',c=>c.ver=()=>({ok:false}),c=>c.datos.personas[1].estado='baja']){
  x=montar();let release;x.c.api=()=>new Promise(done=>release=done);const pending=boton(x.r,'Ver nota').listeners.click();change(x.c);release(dto());await pending;assert(!text(x.r).includes('Persona sintética'));assert.equal(find(x.r,'input').length,0);
 }n++;
 x=montar();await boton(x.r,'Ver nota').listeners.click();find(x.r,'input')[0].value='Hecho';let release;x.c.api=()=>new Promise(done=>release=done);const old=boton(x.r,'Guardar declaración'),p=old.listeners.click();x.r.replaceChildren();release({});await p;assert(old.disabled);n++;
 for(const change of [c=>c.soloLectura=true,c=>c.persona.id='other']){x=montar();await boton(x.r,'Ver nota').listeners.click();find(x.r,'input')[0].value='Hecho';const b=boton(x.r,'Guardar declaración');change(x.c);let count=0;x.c.api=async()=>{count++;return{};};await b.listeners.click();assert.equal(count,0);}n++;
 x=montar();let gets=0;x.c.api=async()=>{gets++;return dto();};await boton(x.r,'Ver nota').listeners.click();await boton(x.r,'Ver nota').listeners.click();assert.equal(gets,2);n++;
 const r=root(),c=context();c.ver=()=>({ok:false});s.panelEquipoNotas281(r,c,[fixture]);assert.equal(find(r,'input').length,0);assert(!text(r).includes('Persona sintética'));n++;
 x=montar();x.c.api=()=>new Promise(done=>release=done);const loading=boton(x.r,'Ver nota').listeners.click();x.c.ver=r=>({ok:r.tipo==='notas_persona'});release(dto());await loading;assert(!text(x.r).includes('12 h'));assert(!find(x.r,'input')[0].disabled);n++;
 const source=fs.readFileSync('/Users/tomassala/Downloads/PANEL_OPERACIONES_2026-10-01/plantilla.html','utf8'),start=source.indexOf('function vEquipoNotas()'),part=source.slice(start,source.indexOf('\n}',start));const columns=[...part.matchAll(/<th(?:\s[^>]*)?>(.*?)<\/th>/g)].map(x=>x[1].replace(/<[^>]+>/g,'').trim());assert.deepEqual(columns,['Persona','Horas sem. pasada','Esta semana','Nota','Hecho que lo prueba','Acción','']);n++;
 console.log(n+' grupos281 UI PASS: siete columnas originales, semanas exactas, notas humanas, prueba, recibo/retryUUID, scopes y revocación.');
})().catch(e=>{console.error(e);process.exit(1);});
