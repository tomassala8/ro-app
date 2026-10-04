const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
const APP=__dirname;const c={URL,Date,Intl,Number};vm.createContext(c);
for(const f of ['_tarea_ia.js','_prioridades_contexto_337.js'])vm.runInContext(fs.readFileSync(APP+'/modulos/'+f,'utf8').replace(/^import[^;]+;\s*/gm,'').replace(/export /g,''),c);
const source=fs.readFileSync(APP+'/modulos/prioridades_cliente.js','utf8'),a=source.indexOf('    async function copiarBloque('),b=source.indexOf('    function borradorTarea(',a);assert(a>=0&&b>a);vm.runInContext(source.slice(a,b)+';this.copiarReal=copiarBloque;',c);
let count=0,status=0,allowed=true,epoch=true,mid=null;
const ops={id:'ops_fixture',estado:'activo',puestos:['operaciones']},paid={id:'paid_fixture',estado:'activo',puestos:['trafficker']};const ctx={servidor:true,real:ops,persona:ops,hoy:'2026-10-04',datos:{personas:[ops,paid]},clientesVisibles:[{id:'fixture',activo_confirmado:true,detalle:true}],veModulo:()=>true,ver:()=>({ok:allowed}),vigente:()=>epoch};
ctx.clientes=ctx.clientesVisibles.map(c=>({...c,activo:true,estado:'activo'}));c.ctx=ctx;const start=c.ambitoPrioridades337(ctx);assert(start);c.vigente=()=>epoch&&c.ambitoPrioridades337(ctx)?.firma===start.firma;c.avisoFlotante=()=>{status++;};c.document={execCommand:()=>false};c.copiarInstrucciones=async()=>{count++;if(mid)mid();return true;};
const button=()=>({isConnected:true,disabled:false}),text=()=>({isConnected:true,value:'Borrador ficticio autorizado',focus(){},select(){}});
(async()=>{
 await c.copiarReal(button(),text(),'Listo');assert.equal(count,1);assert.equal(status,1);
 allowed=false;await c.copiarReal(button(),text(),'Listo');assert.equal(count,1);allowed=true;
 epoch=false;await c.copiarReal(button(),text(),'Listo');assert.equal(count,1);epoch=true;
 mid=()=>{allowed=false;};await c.copiarReal(button(),text(),'Listo');assert.equal(count,2);assert.equal(status,1);allowed=true;mid=null;
 //665: la baja del responsable invalida el contexto antes del portapapeles.
 paid.estado='baja';assert.notEqual(c.ambitoPrioridades337(ctx)?.firma,start.firma);await c.copiarReal(button(),text(),'Listo');assert.equal(count,2);
 console.log('5 casos guardia real copiar664/665 PASS; baja del responsable impide nueva copia');
})().catch(e=>{console.error(e);process.exitCode=1;});
