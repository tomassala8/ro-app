const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const s={Date,Map,Set,JSON,Number,Array,Promise};vm.createContext(s);vm.runInContext(fs.readFileSync(__dirname+'/modulos/_planes_pendientes_327.js','utf8').replace(/export /g,''),s);
const ctx=()=>({real:{id:'tomas'},persona:{id:'tomas'},servidor:true,veModulo:()=>true,ver:()=>({ok:true}),clientesVisibles:[{id:'c',activo_confirmado:true,detalle:true}],datos:{personas:[{id:'constanza',estado:'activo',puestos:['proyectos']}]} });
const plan={version:1,que:'Acción concreta',responsable_id:'account',plazo:'2026-10-12'},empty={cliente_id:'c',version:0,plan:null,revision:null,historial:[],origen:'local',capacidades:{}},dto={...empty,version:2,plan,revision:{version:2,plan_version:1,actor_id:'constanza',estado:'visto'}};
const clas=(d,c=ctx())=>s.clasificarPlan327(c,'c',d).estado;
(async()=>{
 assert.equal(clas(empty),'sin_plan');assert.equal(clas({...dto,revision:null}),'sin_revision');assert.equal(clas(dto),'visto');assert.equal(clas({...dto,revision:{...dto.revision,estado:'pedir_cambios'}}),'cambios');
 for(const d of [{},{...dto,cliente_id:'ajeno'},{...dto,origen:'externo'},{...dto,version:0},{...dto,plan:{...plan,plazo:'2026-02-30'}},{...dto,revision:{...dto.revision,plan_version:3}},{...dto,revision:{...dto.revision,version:1}},{...dto,revision:{...dto.revision,actor_id:'tomas'}}])assert.equal(clas(d),'desconocido');
 const inactive=ctx();inactive.datos.personas[0].estado='baja';assert.equal(clas(dto,inactive),'desconocido');
 const denied=ctx();denied.ver=()=>({ok:false});assert.equal(clas(dto,denied),'desconocido');let calls=0;denied.api=async()=>{calls++;return dto;};assert.equal((await s.leerPlanes327(denied,[{cliente_id:'c'}],()=>true)).length,0);assert.equal(calls,0);
 const ok=ctx();ok.api=async ruta=>{calls++;assert.equal(ruta,'en-rojo/planes?cliente_id=c');return dto;};assert.equal((await s.leerPlanes327(ok,[{cliente_id:'c'}],()=>true))[0].estado,'visto');
 assert.equal((await s.leerPlanes327(ok,[{cliente_id:'c'},{cliente_id:'c'}],()=>true)).length,0);
 const changed=ctx();changed.api=async()=>{changed.ver=()=>({ok:false});return dto;};assert.equal(await s.leerPlanes327(changed,[{cliente_id:'c'}],()=>true),null);
 const role=ctx();role.api=async()=>{role.datos.personas[0].estado='baja';return dto;};assert.equal(await s.leerPlanes327(role,[{cliente_id:'c'}],()=>true),null);
 const failed=ctx();failed.api=async()=>{throw Error('fuente');};assert.equal((await s.leerPlanes327(failed,[{cliente_id:'c'}],()=>true))[0].estado,'desconocido');
 const demo=ctx();demo.servidor=false;demo.api=async()=>{throw Error('no debe llamar');};assert.equal((await s.leerPlanes327(demo,[{cliente_id:'c'}],()=>true))[0].estado,'desconocido');
 console.log('12 grupos327 PASS: planes/revisiones versionadas, Coti canónica, ámbito y revocación async.');
})().catch(e=>{console.error(e);process.exitCode=1;});
