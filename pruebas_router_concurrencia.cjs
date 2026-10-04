const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync(require('node:path').join(__dirname,'app.js'),'utf8');
const router=src.slice(src.indexOf('let navegacionActual = 0;'),src.indexOf('\nfunction pintarSinPermiso'));
const ctxSource=src.slice(src.indexOf('function crearCtx('),src.indexOf('// --------------------------------------------------------------- cmd+K'));
const defer=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return {promise,resolve,reject};};
function element(tag,attrs={},...kids){const x={tag,attrs,parent:null,children:[],textContent:'',focusCalls:0,
 get isConnected(){return !!this.root||!!this.parent?.isConnected;},get childElementCount(){return this.children.length;},
 append(...cs){for(const c of cs.flat(Infinity)){if(c==null)continue;this.children.push(c);if(typeof c==='object')c.parent=this;}},
 replaceChildren(...cs){for(const c of this.children)if(typeof c==='object')c.parent=null;this.children=[];this.append(...cs);},
 remove(){if(this.parent){const p=this.parent;p.children=p.children.filter(c=>c!==this);this.parent=null;}},focus(){this.focusCalls++;}};x.append(...kids);return x;}
function setup(){
 const nodes={'#main':element('main'),'#titulo':element('title'),'#subtitulo':element('subtitle')}; nodes['#main'].root=true;
 const persona={id:'yo',puestos:[]};const estado={persona,real:persona,datos:{clientes:[],personas:[]},crudo:{personas:[]},modulos:[],servidor:true};
 let tasks=[],seq=0,scrolls=0,marked=[];
 const c={medidorUso:null,estado,location:{hash:'#/old'},history:{replaceState(){}},document:{title:'',querySelectorAll:()=>[]},window:{scrollY:50,scrollTo(){scrolls++;}},
  $:id=>nodes[id],h:element,modulosVisibles:()=>estado.modulos,inicioPropio:()=>null,INICIO_PREFERIDO:{},PUESTO:{},cerrarMenuMovil(){},
  _repintarT:null,pintura:{usadas:new Set(),estadosLectura:new Map()},periodoVivo:{valor:null,oyentes:[]},marcarGuardado:i=>marked.push(i),
  detalleLecturas487(){},estadoDatoCambiado487(){},estadoGuardado487(){return c.pintura.guardado||null;},
  cargarModulo:async()=>{},pintarMenu(){},catalogoIndicadores:async()=>{},usaPeriodo:()=>false,pintarBarraPeriodo(){},estadoVacio:o=>element('error',{},o.titulo),esqueleto:()=>element('skeleton'),
  setTimeout:f=>{const id=++seq;tasks.push({id,f});return id;},clearTimeout:id=>{tasks=tasks.filter(t=>t.id!==id);},repintarLuego(){throw Error('Unexpected stale repaint');},
  nivelModulo:()=> 'todo',fechas:{hoy:()=> '2026-10-03'},fechasDe(){},fmt:{plural(){}},ver(){},api(){},ctx_accion(){},apuntar(){},verDato(){},console,
 };
 vm.createContext(c);vm.runInContext(router+'\n'+ctxSource+'\nglobalThis.go=ruta;',c);
 return {c,nodes,estado,timers:()=>tasks,flush(){const ts=tasks;tasks=[];ts.forEach(t=>t.f());},scrolls:()=>scrolls,marked};
}
(async()=>{
 let t=setup(),wait=defer(),oldCont,oldCtx;
 t.estado.modulos=[{id:'old',titulo:'Old',estado:'hecho',async render(cont,ctx){oldCont=cont;oldCtx=ctx;await wait.promise;cont.append(element('oldLate'));ctx.titulo('OLD LATE');ctx.periodosConDatos([]);ctx.alCambiarPeriodo(()=>{});}},{id:'new',titulo:'New',estado:'hecho',render(cont,ctx){cont.append(element('newContent'));ctx.titulo('NEW TITLE');}}];
 const old=t.c.go(true,{refresco:true});await new Promise(setImmediate);assert.ok(oldCont.isConnected);
 t.c.location.hash='#/new';await t.c.go(true);assert.equal(oldCont.isConnected,false);assert.equal(t.nodes['#titulo'].textContent,'NEW TITLE');
 wait.resolve();await old;t.flush();assert.equal(t.nodes['#titulo'].textContent,'NEW TITLE');assert.equal(t.c.document.title,'NEW TITLE · App RO');assert.equal(t.nodes['#main'].children[0].attrs['data-ruta'],'new');assert.equal(t.nodes['#main'].children[0].children[0].tag,'newContent');assert.equal(t.scrolls(),0);assert.equal(t.nodes['#main'].focusCalls,1);assert.equal(t.c.periodoVivo.oyentes.length,0);
 oldCtx.navegar('old');assert.equal(t.c.location.hash,'#/new');
 t=setup();wait=defer();let oldRendered=0,catalogCalls=0;
 t.c.catalogoIndicadores=()=>++catalogCalls===1?wait.promise:Promise.resolve();
 t.estado.modulos=[{id:'old',titulo:'Old',estado:'hecho',render(){oldRendered++;}},{id:'new',titulo:'New',estado:'hecho',render(cont){cont.append(element('new'));}}];
 const catalogOld=t.c.go(true);t.c.location.hash='#/new';await t.c.go(true);wait.resolve();await catalogOld;assert.equal(oldRendered,0);assert.equal(t.nodes['#titulo'].textContent,'New');
 t=setup();wait=defer();oldRendered=0;
 t.c.cargarModulo=async m=>{await wait.promise;m.render=()=>oldRendered++;};
 t.estado.modulos=[{id:'old',titulo:'Old',estado:'hecho',fichero:'old.js'},{id:'new',titulo:'New',estado:'hecho',render(cont){cont.append(element('new'));}}];
 const importing=t.c.go(true);t.c.location.hash='#/new';await t.c.go(true);t.flush();assert.equal(t.nodes['#main'].children[0].children[0].tag,'new');wait.resolve();await importing;assert.equal(oldRendered,0);
 t=setup();wait=defer();t.estado.modulos=[{id:'old',titulo:'Old',estado:'hecho',async render(){await wait.promise;throw Error('stale fail');}},{id:'new',titulo:'New',estado:'hecho',render(cont){cont.append(element('new'));}}];
 const failed=t.c.go(true);await new Promise(setImmediate);t.c.location.hash='#/new';await t.c.go(true);wait.resolve();await failed;assert.equal(t.nodes['#main'].children[0].children[0].tag,'new');assert.equal(t.c.pintura.enCurso,false);
 t=setup();t.estado.sesion={soloLectura:true,pilotoLectura:true};assert.equal(t.c.crearCtx({id:'pilot'}, []).soloLectura,true);
 t.estado.sesion={soloLectura:false};assert.equal(t.c.crearCtx({id:'normal'}, []).soloLectura,false);
 let envios=0;t.c.ctx_accion=()=>{envios++;return {ok:true};};
 const viejo=t.c.crearCtx({id:'normal'}, [],()=>false);assert.equal(viejo.vigente(),false);await assert.rejects(viejo.accion({}),/pantalla ha cambiado/);assert.equal(envios,0);
 t.estado.sesion={soloLectura:true};await assert.rejects(t.c.crearCtx({id:'pilot'}, []).accion({}),/piloto es de consulta/);assert.equal(envios,0);
 t.estado.sesion={soloLectura:false};await t.c.crearCtx({id:'normal'}, []).accion({});assert.equal(envios,1);
 console.log('OK: pilot session is read only in real context; late render/title/period listeners/navigation cannot replace current route, detached old container, stale skeleton/import/catalog/error/scroll/focus guarded.');
})().catch(e=>{console.error(e);process.exitCode=1;});
