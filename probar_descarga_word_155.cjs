const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const s=fs.readFileSync(__dirname+'/modulos/_informe_word.js','utf8').replace(/export /g,'');
const box={Blob,Uint8Array,encodeURIComponent,fetch};vm.createContext(box);vm.runInContext(s+';this.obtener=obtenerWord',box);
const mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const ctx=()=>({servidor:true,real:{id:'tomas'},persona:{id:'carla'},clientes:[{id:'gac'}],ver:()=>({ok:true}),vigente:()=>true});
const response=()=>new Response(Uint8Array.of(80,75,3,4,1,2,3),{status:200,headers:{'Content-Type':mime,'Content-Length':'7'}});
(async()=>{
 let options,uri,calls=0;const c=ctx(),node={isConnected:true};
 const f=async(u,o)=>{uri=u;options=o;calls++;return response();};
 const b=await box.obtener(c,'gac','2026-09',node,f);assert.equal(b.size,7);assert.equal(options.headers['X-RO-Como'],'carla');assert.equal(options.credentials,'same-origin');assert.equal(options.redirect,'error');assert.match(uri,/cliente_id=gac&periodo_id=2026-09/);
 c.vigente=()=>false;await assert.rejects(box.obtener(c,'gac','2026-09',node,f));assert.equal(calls,1);
 c.vigente=()=>true;await assert.rejects(box.obtener(c,'otro','2026-09',node,f));assert.equal(calls,1);
 await assert.rejects(box.obtener(c,'gac','2026-09',node,async()=>new Response('{}',{headers:{'Content-Type':'application/json'}})));
 await assert.rejects(box.obtener(c,'gac','2026-09',node,async()=>new Response('incorrecto',{headers:{'Content-Type':mime}})));
 await assert.rejects(box.obtener(c,'gac','2026-09',node,async()=>new Response('PK',{headers:{'Content-Type':mime,'Content-Length':String(6*1024*1024)}})));
 await assert.rejects(box.obtener(c,'gac','2026-09',node,async()=>{node.isConnected=false;return response();}));
 console.log('155 PASS: identidad real/vista, descarga privada, permisos revocados, navegación, formato y tamaño controlados.');
})().catch(e=>{console.error(e);process.exitCode=1;});
