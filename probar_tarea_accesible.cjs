const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const src=fs.readFileSync(path.join(__dirname,'modulos','_deshacer.js'),'utf8').replace(/^import .*;$/mg,'').replace(/export /g,'');
class El{constructor(tag,a={},cs=[]){this.tag=tag;this.a=a;this.cs=cs.flat().filter(Boolean);this.on=a.on||{};this.isConnected=true;}replaceChildren(...cs){this.cs=cs}append(...cs){this.cs.push(...cs)}querySelector(){return null}focus(){}addEventListener(k,f){this.on[k]=f}}
const scope={h:(t,a,...cs)=>new El(t,a,cs),ico:()=>null,setInterval:()=>1,clearInterval:()=>{},setTimeout:()=>1,clearTimeout:()=>{},document:{addEventListener:()=>{}},window:{addEventListener:()=>{}}};vm.createContext(scope);vm.runInContext(src+';globalThis.bot=botonDeshacer;globalThis.flush=encolarTodo;',scope);
(async()=>{
 let calls=0;const b=scope.bot({texto:'Hecha',etiqueta:'Marcar hecha: Preparar SEO',alHacer:async()=>{calls++;return 'Guardado';}});
 assert.equal(b.cs[0].a['aria-label'],'Marcar hecha: Preparar SEO');b.cs[0].on.click();assert.equal(b.cs[1].a['aria-label'],'Deshacer: Marcar hecha: Preparar SEO');scope.flush();await new Promise(r=>setImmediate(r));assert.equal(calls,1);
 const old=scope.bot({texto:'Hecho'});assert.equal(old.cs[0].a['aria-label'],null,'Default existente se conserva');
 const oldIcon=scope.bot({texto:'',titulo:'Marcar hecha'});assert.equal(oldIcon.cs[0].a['aria-label'],'Marcar hecha');
 const ro=scope.bot({texto:'Hecha',etiqueta:'Marcar hecha: X',soloLectura:true,alHacer:()=>calls++});ro.cs[0].on.click();scope.flush();assert.equal(calls,1);
 const undo=scope.bot({texto:'Hecha',etiqueta:'Marcar hecha: X',alHacer:()=>calls++});undo.cs[0].on.click();undo.cs[1].on.click();scope.flush();assert.equal(calls,1);assert.equal(undo.cs[0].a['aria-label'],'Marcar hecha: X');
 const task=fs.readFileSync(path.join(__dirname,'modulos','mi_trabajo.js'),'utf8');assert(task.includes('etiqueta: `Marcar hecha: ${t.tarea}`'));assert(task.includes("'aria-label': `${enEsta ? 'Parar el cronómetro' : 'Empezar el cronómetro'}: ${t.tarea}`"));assert(task.includes("'aria-label': `${abierta ? 'Cerrar acciones' : 'Más acciones'}: ${t.tarea}`"));assert(task.includes("planing: 'Planificación'"));
 const grouping=task.slice(task.indexOf('const enCursoSinFecha ='),task.indexOf('const VISTAS ='));
 vm.runInContext("const GRUPO={hoy:{t:'Para hoy'},semana:{t:'Esta semana'}};"+grouping+";globalThis.gTitle=tituloGrupo;",scope);
 assert.equal(scope.gTitle('hoy',[{estado:'en curso',vence:null,grupo:'hoy'}]),'Para hoy y en curso');
 assert.equal(scope.gTitle('hoy',[{estado:'en curso',vence:'2026-10-03',grupo:'hoy'}]),'Para hoy');
 assert.equal(scope.gTitle('hoy',[{estado:'diario',vence:null,grupo:'hoy'}]),'Para hoy');
 assert.equal(scope.gTitle('semana',[{estado:'en curso',vence:null,grupo:'hoy'}]),'Esta semana');
 assert(task.includes('se muestra aquí por su estado En curso en ClickUp; no hay fecha límite registrada'));
 console.log('OK: tarea identificable al marcar/deshacer, cronómetro y más acciones; default, éxito, deshacer y lectura preservados.');
})().catch(e=>{console.error(e);process.exit(1)});
