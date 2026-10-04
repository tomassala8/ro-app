const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(require('node:path').join(__dirname,'modulos','setters.js'),'utf8');
const start=source.indexOf('  const apuntar = (x, que, texto, nota) => {');
const end=source.indexOf('\n\n  // ---------------------------------------------------------------- fila de una reunión',start);
let action,calls=0,fail=true,draws=0;
const scope={ctx:{soloLectura:false},apuntados:new Map([['cita','Confirmada']]),pendientesApunte:new Set(),borradoresNotas:new Map([['lead','Mi nota de llamada']]),dibujar:()=>draws++,nombreLead:x=>x.id,
 conDeshacer:o=>{action=o;o.optimista();return o;},encolar:async()=>{calls++;if(fail)throw Error('Fallo');return {id:1};}};
vm.createContext(scope);vm.runInContext(source.slice(start,end)+';globalThis.apuntarTest=apuntar;',scope);
(async()=>{
 scope.apuntarTest({id:'cita'},'confirmacion_cita','Reagendar');assert.equal(scope.apuntados.get('cita'),'Reagendar');
 scope.apuntarTest({id:'cita'},'confirmacion_cita','Cancela');assert.equal(scope.apuntados.get('cita'),'Reagendar','No permite resultados concurrentes en la misma cita');
 try{await action.hacer();}catch{action.revertir();}assert.equal(scope.apuntados.get('cita'),'Confirmada','Fallo restaura estado confirmado anterior');assert.equal(scope.pendientesApunte.size,0);
 scope.apuntarTest({id:'lead'},'resultado_llamada','No contesta','Mi nota de llamada');try{await action.hacer();}catch{action.revertir();}
 assert.equal(scope.apuntados.has('lead'),false,'Lead reaparece tras fallo');assert.equal(scope.borradoresNotas.get('lead'),'Mi nota de llamada');
 fail=false;scope.apuntarTest({id:'lead'},'resultado_llamada','No contesta','Mi nota de llamada');await action.hacer();assert.equal(scope.apuntados.get('lead'),'No contesta');assert.equal(scope.borradoresNotas.has('lead'),false);assert.equal(scope.pendientesApunte.size,0);
 scope.ctx.soloLectura=true;const before=draws;scope.apuntarTest({id:'otro'},'resultado_llamada','No contesta');assert.equal(draws,before);assert.equal(calls,3);
 // Ejecuta el selector real para comprobar el orden del recorrido y de leads.
 const lsStart=source.indexOf('  function listas() {'),lsEnd=source.indexOf('\n\n  // Apuntar',lsStart);
 Object.assign(scope,{citasT:[{id:'futuro',dia:'mañana',cuando:'2026-10-04 11:00'},{id:'hoy2',dia:'hoy',cuando:'2026-10-03 12:00'},{id:'hoy1',dia:'hoy',cuando:'2026-10-03 09:00'}],leadsT:[{id:'sinTel',lista:'llamar_ya',grupo:'b',min:1,sin_tel:true},{id:'a',lista:'llamar_ya',grupo:'a',min:1},{id:'bviejo',lista:'llamar_ya',grupo:'b',min:100},{id:'bnuevo',lista:'llamar_ya',grupo:'b',min:2},{id:'pedida',lista:'llamar_ya',grupo:'b',min:1}],pasadasT:[],pedidas:new Map([['pedida','Cita pedida']]),RANGO_GRUPO:{b:0,a:1,c:2}});
 vm.runInContext(source.slice(lsStart,lsEnd)+';globalThis.seleccionar=listas;',scope);const ls=scope.seleccionar();assert.deepEqual(Array.from(ls.citasHoy,x=>x.id),['hoy1','hoy2']);assert.deepEqual(Array.from(ls.sinCita,x=>x.id),['bnuevo','bviejo','a','pedida','sinTel']);
 assert(source.indexOf('sec1, sec2, sec3')>0,'El primer paso es confirmar reuniones de hoy');
 const saveStart=source.indexOf("    guardar.addEventListener('click', async () => {");
 const saveEnd=source.indexOf('\n    caja.append(',saveStart);
 let handler,saveCalls=0,saveFail=true;
 Object.assign(scope,{ctx:{soloLectura:false},guardar:{disabled:false,addEventListener:(_e,f)=>handler=f,replaceChildren:()=>{}},elegido:'2026-10-05 11:00',resultado:{replaceChildren:()=>{}},x:{id:'nuevo'},titulo:{value:'Reunión'},notasCita:{value:'Notas cita'},notasLlamada:{value:'Notas llamada'},ayuda:null,reagenda:null,h:()=>({}),icono:()=>null,avisoParcial:()=>({}),avisoFlotante:()=>{},encolar:async()=>{saveCalls++;if(saveFail)throw Error('Guardado fallido');return {texto:'Cita guardada'};}});
 vm.runInContext(source.slice(saveStart,saveEnd),scope);
 await handler();assert.equal(scope.pedidas.has('nuevo'),false);assert.equal(scope.guardar.disabled,false);assert.equal(scope.notasLlamada.value,'Notas llamada');assert.equal(scope.elegido,'2026-10-05 11:00');
 saveFail=false;await handler();await handler();assert.equal(saveCalls,2,'Guardar cita no duplica un clic durante el guardado');assert.equal(scope.pedidas.get('nuevo'),'Cita guardada');
 console.log('OK: estado anterior restaurado tras fallo; lead y nota conservados; bloqueo concurrente/solo lectura; citas de hoy primero y prioridad real de leads.');
})().catch(e=>{console.error(e);process.exit(1)});
