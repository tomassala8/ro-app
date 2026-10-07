const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const viejoHarness=fs.readFileSync(require('node:path').join(__dirname,'pruebas_router_concurrencia.cjs'),'utf8');
const modulo={exports:{}};
new Function('require','module','__dirname',viejoHarness.slice(0,viejoHarness.indexOf('(async()=>{'))+'\nmodule.exports={setup,defer,src};')(require,modulo,__dirname);
const {setup:setupBase,defer,src}=modulo.exports;
function setup(){
 const t=setupBase();t.c.pintura.estadosLectura=new Map();
 // Estado487 pertenece al transporte/cabecera; no altera el router ni sus asserts.
 t.c.detalleLecturas487=()=>{};
 t.c.estadoGuardado487=()=>t.c.pintura.guardado||null;
 t.c.estadoDatoCambiado487=()=>{};
 return t;
}
const dato=src.slice(src.indexOf('function datoCambiado('),src.indexOf('function repintarLuego('));
const apiFuente=src.slice(src.indexOf('async function api('),src.indexOf('/** Ronda 5 · la verdad'));
const comunes=src.slice(src.indexOf('async function cargarVerdad('),src.indexOf('// ----------------------------------------------------------------- rastro'));
const tick=()=>new Promise(setImmediate);
function escenario(func=dato){
 const t=setup();let menus=0,repaints=0,renders=0;const ui={area:'',cliente:''};
 t.estado.modulos=[{id:'prioridades-cliente',titulo:'Prioridades',estado:'hecho',render(){renders++;ui.area='';ui.cliente='';}}];
 t.c.location.hash='#/prioridades-cliente';
 t.c.cargarVerdad=async()=>{};t.c.pintarMenu=()=>menus++;
 t.c.repintarLuego=()=>{repaints++;void t.c.go(false,{refresco:true});};
 vm.runInContext(func+'\nglobalThis.cambiar=datoCambiado;globalThis.bump=()=>navegacionActual++;',t.c);
 return {...t,ui,menus:()=>menus,repaints:()=>repaints,renders:()=>renders};
}
(async()=>{
 // Reproduce la ruta original: fuente común ajena reiniciaba exactamente los filtros.
 const original=`function datoCambiado(r){if(r==='modulo/verdad/clientes'||r==='indicadores'){estado.indicadores=null;Promise.all([cargarVerdad(),catalogoIndicadores()]).then(()=>{pintarMenu();repintarLuego();});return;}if(!pintura.usadas.has(r))return;repintarLuego();}`;
 let t=escenario(original);await t.c.go(false);t.ui.area='paid';t.ui.cliente='akua';t.c.cambiar('indicadores');await tick();assert.equal(t.ui.area,'');assert.equal(t.renders(),2);
 t=escenario();await t.c.go(false);t.ui.area='paid';t.ui.cliente='akua';t.c.cambiar('indicadores');await tick();assert.equal(t.ui.area,'paid');assert.equal(t.ui.cliente,'akua');assert.equal(t.renders(),1);assert.equal(t.menus(),1);
 // Getter del módulo registra dependencia incluso cuando el dato común vino de cache.
 let ctx=t.c.crearCtx(t.estado.modulos[0],[],()=>true);ctx.indicadores();assert.ok(t.c.pintura.usadas.has('indicadores'));t.c.cambiar('indicadores');await tick();assert.equal(t.renders(),2);
 ctx=t.c.crearCtx(t.estado.modulos[0],[],()=>true);ctx.verdad('akua');t.c.cambiar('modulo/verdad/clientes');await tick();assert.equal(t.renders(),3);
 t.c.pintura.usadas.clear();ctx=t.c.crearCtx(t.estado.modulos[0],[],()=>false);ctx.verdad('akua');ctx.indicadores();assert.equal(t.c.pintura.usadas.size,0);
 // Cambio de ruta/persona mientras refresca común no redibuja la nueva pantalla.
 for(const cambio of ['ruta','persona']){
  t=escenario();await t.c.go(false);t.c.pintura.usadas.add('indicadores');const gate=defer();t.c.cargarVerdad=()=>gate.promise;t.c.cambiar('indicadores');
  if(cambio==='ruta')t.c.bump();else t.estado.persona={id:'otro',puestos:[]};gate.resolve();await tick();assert.equal(t.repaints(),0);if(cambio==='persona')assert.equal(t.menus(),0);
 }
 // API real: lectura shell no contamina usadas ni guardado, módulo sí conserva caché/rastro.
 t=setup();vm.runInContext(apiFuente+'\nglobalThis.leerApi=api;',t.c);
 t.c.pedirDato=async(r,op)=>{op.info.guardado=true;return {dato:r};};
 await t.c.leerApi('indicadores',{rastrear:false});assert.equal(t.c.pintura.usadas.size,0);assert.equal(t.c.pintura.guardado,undefined);
 await t.c.leerApi('modulo/captacion/captacion');assert.ok(t.c.pintura.usadas.has('modulo/captacion/captacion'));assert.equal(t.c.pintura.guardado.guardado,true);
 // Loaders reales no aplican respuestas/catch anteriores a otro real o ver-como.
 for(const loader of ['cargarVerdad','catalogoIndicadores'])for(const campo of ['real','persona'])for(const falla of [false,true]){
  t=setup();t.estado.modulos=[{id:'en-rojo'}];t.c.guardarLocal=()=>{};t.c.nivelModulo=()=>true;t.estado.verdad={marcador:'nueva'};t.estado.indicadores=null;
  const gate=defer();let op;t.c.api=(r,o)=>{op=o;return gate.promise;};vm.runInContext(comunes,t.c);
  const promise=t.c[loader]();assert.equal(op.rastrear,false);t.estado[campo]={id:'nuevo',puestos:[]};t.estado.indicadores={marcador:'nuevo-catalogo'};
  if(falla)gate.reject(Error('viejo'));else gate.resolve({clientes:[{cliente_id:'privado-otra-vista'}],indicadores:[]});await promise;
  assert.equal(t.estado.verdad.marcador,'nueva');assert.equal(t.estado.indicadores.marcador,'nuevo-catalogo');
 }

 // Arranque completo: navegación durante uso/aviso no permite un segundo render tardío.
 const bootSource=src.slice(src.indexOf('async function arrancar()'),src.indexOf('// --------------------------------------------- ronda 14'));
 async function bootAsync(original=false, permiteModulo=true){
  const t=escenario();let hashHandler;const gate=defer();let usoOp;
  Object.assign(t.c,{URLSearchParams,location:{hash:'#/prioridades-cliente',search:'?yo=yo',hostname:'127.0.0.1'},
   MODULOS:t.estado.modulos,document:{...t.c.document,cookie:''},leerLocal:()=>null,comoGuardado:()=>null,
   // Arranque actual consume permisos del servidor: {} significa ninguna pantalla,
   // no «todas». El escenario de refresco necesita autorizar su módulo sintético.
   pedirDato:async()=>({}),fijarPersonas:async()=>{},cargarServidor:async()=>({real:t.estado.real,persona:t.estado.persona,datos:{personas:[t.estado.persona],meta:{}},modulos_puestos:permiteModulo?{'prioridades-cliente':{'*':'todo'}}:{}}),
   ponerCookie(){},ponerPersona:async p=>{t.estado.persona=p;},pintarVerComo(){},pintarRecarga(){},conectarMenuYo(){},conectarTeclado(){},conectarMenuMovil(){},
   alCambiarDato(){},precargarEnReposo(){},iniciarUsoLocal:()=>null,formatoTexto:x=>x,
   api:async(r,op)=>{if(r==='uso/aviso'){usoOp=op;return gate.promise;}return {};},
  });
  t.c.window.addEventListener=(evento,fn)=>{if(evento==='hashchange')hashHandler=fn;};
  const codigo=original?bootSource.replace('if (navegacionAlArrancar === navegacionActual) await ruta(false);\n  else if (pintura.id) medidorUso?.pantalla(pintura.id);','await ruta(false);'):bootSource;
  vm.runInContext(codigo+'\nglobalThis.boot=arrancar;',t.c);
  const boot=t.c.boot();for(let i=0;i<12&&!hashHandler;i++)await tick();assert.ok(hashHandler);
  await hashHandler();t.ui.area='paid';t.ui.cliente='akua';gate.resolve({disponible:false});await boot;
  assert.equal(usoOp.rastrear,false);return t;
 }
 let boot=await bootAsync(true);assert.equal(boot.renders(),2);assert.equal(boot.ui.area,'');
 boot=await bootAsync();assert.equal(boot.renders(),1);assert.equal(boot.ui.area,'paid');assert.equal(boot.ui.cliente,'akua');
 // Sin módulo autorizado, la ruta no debe recuperar la pantalla desde el índice.
 boot=await bootAsync(false,false);assert.equal(boot.renders(),0);assert.equal(boot.estado.modulos.length,0);
 // Wiring real de ayudas: API y ctxPara no etiquetan como dependencia de la pantalla sus contadores.
 const ayudasSource=src.slice(src.indexOf('let _ayudas = null;'),src.indexOf('const conAyudas'));
 t=setup();vm.runInContext(apiFuente+'\nglobalThis.leerApi=api;',t.c);t.c.pedirDato=async()=>({});
 t.c.apuntar=()=>{};t.c.puedeVerComo=()=>true;t.c.idsMisClientes=()=>[];
 let config;t.c._importarAyudas=async()=>({iniciar:op=>{config=op;}});
 vm.runInContext(ayudasSource.replace("import('./ayudas.js')","_importarAyudas()")+'\nglobalThis.abrirAyudas=ayudas;',t.c);
 await t.c.abrirAyudas();const helperCtx=config.ctxPara('mi-dia');helperCtx.verdad('akua');helperCtx.indicadores();
 await config.api('modulo/bandeja/bandeja');await helperCtx.api('indicadores');
 assert.equal(t.c.pintura.usadas.size,0);
 const moduloCtx=t.c.crearCtx({id:'prioridades-cliente'},[],()=>true);moduloCtx.indicadores();assert.ok(t.c.pintura.usadas.has('indicadores'));
 console.log('OK: reproduced initial filter loss, non-consumer keeps filters, consumers refresh, shell not tracked, stale route/real/view/common responses ignored; full boot delayed telemetry and helpers cannot reset filters.');
})().catch(e=>{console.error(e);process.exitCode=1;});
