const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const APP=__dirname,CANDIDATO=path.join(APP,'modulos/_prioridades_contexto_337.js'),BASELINE=path.join(APP,'fixtures/prioridades_665_baseline.js');
let prefix=fs.readFileSync(path.join(APP,'probar_prioridades_contexto_337.cjs'),'utf8').split('let total=0;')[0];
prefix=prefix.replace("const APP=__dirname;","const APP="+JSON.stringify(APP)+";const CANDIDATO="+JSON.stringify(CANDIDATO)+";const BASELINE="+JSON.stringify(BASELINE)+";");
prefix=prefix.replace('function cargar(){','function cargar(candidate=false){').replace("path.join(APP,'modulos/_prioridades_contexto_337.js')","candidate?CANDIDATO:BASELINE");
const harness={require,console,process,setImmediate,URLSearchParams};vm.createContext(harness);vm.runInContext(prefix+';globalThis.F={cargar,contexto,main,boton,click,DATOS,defer,tick};',harness);const F=harness.F;
function contexto(){const c=F.contexto(async ruta=>ruta==='cerebro/operativo'?F.DATOS:{sugerencias:[]});c.hoy='2026-10-04';c.clientes=c.clientesVisibles.map(c=>({...c,activo:true,estado:'activo'}));c.datos.asignaciones=[];return c;}
let n=0;function check(t,f){f();n++;console.log('PASS '+t);}
(async()=>{
 const old=F.cargar(false),fix=F.cargar(true);
 for(const change of [c=>c.clientes[0].activo=false,c=>c.clientes[0].estado='baja',c=>c.clientes.push({...c.clientes[0]})]){
  const c=contexto();change(c);check('baseline admite catalogo revocado; candidato excluye',()=>{assert.equal(old.ambitoPrioridades337(c).ids.length,1);assert.equal(fix.ambitoPrioridades337(c).ids.length,0);});
 }
 for(const roles of [['account',{}],['account','account'],[]]){
  const c=contexto();c.real.puestos=roles;c.persona.puestos=roles;c.datos.personas[0].puestos=roles;
  check('roles malformados no scope',()=>{assert(old.ambitoPrioridades337(c));assert.equal(fix.ambitoPrioridades337(c),null);});
 }
 const c=contexto();check('positivo mismosclientes y nombres',()=>{assert.deepEqual(JSON.parse(JSON.stringify(fix.ambitoPrioridades337(c).ids)),['cliente-fixture']);});
 check('catalogoausente failclosed',()=>{const c=contexto();delete c.clientes;assert.equal(fix.ambitoPrioridades337(c),null);});
 for(const candidate of [false,true]){
  const b=F.cargar(candidate),ctx=contexto(),main=F.main();await b.modulo.render(main,ctx);await F.click(F.boton(main,'Revisar'));const button=F.boton(main,'Copiar encargo');ctx.clientes[0].activo=false;await F.click(button);
  check(candidate?'renderer actual con candidato bloquea copy y limpia':'renderer actualbaseline copia pese revocacioncatalogo',()=>{assert.equal(b.copies.length,candidate?0:1);if(candidate)assert(!main.textContent.includes('Evidencia fixture'));});
 }
 for(const change of [c=>c.datos.asignaciones.push({cliente_id:'cliente-fixture',persona_id:'persona-fixture',silla:'account'}),c=>c.datos.personas[0].puestos=['account',{}]]){
  const b=F.cargar(true),ctx=contexto(),main=F.main();await b.modulo.render(main,ctx);await F.click(F.boton(main,'Revisar'));const button=F.boton(main,'Copiar encargo');change(ctx);await F.click(button);check('cambio asignacion/roles antescopy no clipboard',()=>assert.equal(b.copies.length,0));
 }
 for(const candidate of [false,true]){
  const b=F.cargar(candidate),ctx=contexto(),main=F.main();ctx.datos.personas.push({id:'target-fixture',puestos:['trafficker'],estado:'activo',activo:true});
  await b.modulo.render(main,ctx);await F.click(F.boton(main,'Revisar'));const button=F.boton(main,'Copiar encargo');ctx.datos.personas[1].estado='baja';await F.click(button);
  check(candidate?'target baja despuesGET bloquea clipboard':'baseline target baja despuesGET conserva clipboard',()=>assert.equal(b.copies.length,candidate?0:1));
 }
 {const b=F.cargar(true),ctx=contexto(),main=F.main(),pending=F.defer();ctx.api=async ruta=>ruta==='cerebro/operativo'?pending.promise:{sugerencias:[]};const render=b.modulo.render(main,ctx);ctx.clientes[0].estado='baja';pending.resolve(F.DATOS);await render;check('revocacion duranteGET falso limpia sinfilas',()=>assert(!main.textContent.includes('Revisar dato')));}
 check('asignaciones ausentes no nuevo requisito',()=>{const c=contexto();delete c.datos.asignaciones;assert(fix.ambitoPrioridades337(c).ids.includes('cliente-fixture'));});
 check('firma metadata personas sin nombres/correos',()=>{const c=contexto();c.datos.personas[0].nombre='PERSONAL_NO_FIRMA';c.datos.personas[0].correo='PRIVATE_NO_FIRMA';const a=fix.ambitoPrioridades337(c);assert(!a.firma.includes('PERSONAL_NO_FIRMA'));assert(!a.firma.includes('PRIVATE_NO_FIRMA'));});
 console.log(n+' grupos665 PASS, source/helper/renderer reales y clipboard falso');
})().catch(e=>{console.error(e);process.exitCode=1});
