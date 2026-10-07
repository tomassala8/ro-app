// Caracterización readonly521: funciones reales, datos sintéticos, sin API/DOM real.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),os=require('os'),path=require('path'),{pathToFileURL}=require('url');
const source=fs.readFileSync(__dirname+'/modulos/crm.js','utf8');
const part=(a,b)=>source.slice(source.indexOf(a),source.indexOf(b,source.indexOf(a)));
const code=part('async function verDatosLead(', 'function botonVerDatos(')+part('function cuentagotas(', 'const pesoSub');
const logs=[];const sandbox={botonesContacto:v=>({synthetic:v}),avisoFlotante:v=>logs.push(v),botonConfirmar:o=>o};
vm.createContext(sandbox);vm.runInContext(code,sandbox);
(async()=>{
 let resolve,calls=0,valid=true;const promise=new Promise(r=>resolve=r);
 const ctx={vigente:()=>valid,ver:()=>({desenmascarable:false}),verDato:()=>{calls++;return promise}};
 const box={isConnected:true,values:[],replaceChildren(...values){this.values=values}};
 const button={isConnected:true,disabled:false,removed:false,remove(){this.removed=true}};
 const pending=sandbox.verDatosLead(ctx,{ref:'synthetic',cliente_id:'cid'},box,button);
 valid=false;resolve({valor:{nombre:'Synthetic',telefono:'fixture-only'}});await pending;
 // 526 exige guardia de origen; este callback directo sin guardia no pide.
 assert.equal(calls,0);assert.equal(box.values.length,0);assert.equal(button.removed,false);
 console.log('FIX526: callback sin guardia no solicita ni pinta privado');
 let requested=0;ctx.verDato=async()=>{requested++;return {valor:{}}};
 await sandbox.verDatosLead(ctx,{ref:'synthetic',cliente_id:'cid'},box,button);
 assert.equal(requested,0);
 console.log('FIX526: callback stale sin guardia no inicia verDato');
 // La reproducción histórica Encola sin recibo está resuelta531. Delegación y helper reales, sin stub de éxito.
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'crm521-')),helper=path.join(dir,'helper.mjs');
 fs.copyFileSync(__dirname+'/modulos/_intencion_crm_528.js',helper);
 try{
  const M=await import(pathToFileURL(helper).href);
  class N{constructor(tag,a={},xs=[]){this.tag=tag;this.a=a;this.on=a.on||{};this.isConnected=true;this.children=[];this.append(...xs)}append(...xs){this.children.push(...xs.flat(Infinity).filter(x=>x!=null))}replaceChildren(...xs){this.children=[];this.append(...xs)}get textContent(){return this.children.map(x=>x instanceof N?x.textContent:String(x)).join(' ')}desc(){return this.children.filter(x=>x instanceof N).flatMap(x=>[x,...x.desc()])}click(){return this.on.click?.()}}
  const h=(t,a,...xs)=>new N(t,a,xs),actionReal=new Function('h','crearAccionCRM528',part('function accionSim(', 'const tareaAccount')+';return accionSim;')(h,M.crearAccionCRM528);
  const persona={id:'actor521',estado:'activo',puestos:['especialista_ghl']},cliente={id:'cliente521',activo_confirmado:true,detalle:true};let enviados=0;
  const current={servidor:true,soloLectura:false,nivel:'todo',real:persona,persona,datos:{personas:[persona]},clientes:[cliente],clientesVisibles:[{...cliente}],vigente:()=>true,veModulo:x=>x==='salud-crm',ver:()=>({ok:true}),accion:async()=>{enviados++;return {ok:false,estado:'pendiente_recuperacion'}}};
  const stored=new Map();globalThis.crypto=require('crypto').webcrypto;globalThis.location={origin:'http://127.0.0.1:8771'};globalThis.localStorage={getItem:k=>stored.get(k)??null,setItem:(k,v)=>stored.set(k,v)};
  const action=actionReal(current,{texto:'Nota',tipo:'nota',objeto:'Objeto sintético',cliente_id:cliente.id,vista_previa:'Nota sintética'});
  await action.desc()[0].click();await action.desc().find(x=>x.tag==='button'&&x.textContent==='Guardar intención local').click();
  assert.equal(enviados,1);assert(!action.textContent.includes('En la cola'));assert(!action.textContent.includes('Intención local guardada'));assert(action.textContent.includes('Sin recibo local válido'));assert.equal(JSON.parse([...stored.values()][0]).estado,'pendiente');
  console.log('FIX531: recibo desconocido no acredita guardado ni cola; intención pendiente');
 }finally{fs.rmSync(dir,{recursive:true,force:true})}
 const rows=Array.from({length:6},(_,i)=>({id:i,estado:'rojo',peso:6-i}));
 const whole=sandbox.cuentagotas(rows,r=>r.estado,r=>r.peso);
 const selected=sandbox.cuentagotas([rows[5]],r=>r.estado,r=>r.peso);
 assert.equal(whole(rows[5]),'rojo');assert.equal(selected(rows[5]),'rojo');
 console.log('FIX541: misma señal conserva color al filtrar, sin cuota1/3');
 const normal=fs.readFileSync(__dirname+'/modulos/_crm_mediciones.js','utf8').replace(/export /g,'');
 vm.runInContext(normal,sandbox);
 const f=vm.runInContext(`normalizarFilaCRM({estado:'rojo',motivos:[{clave:'sin_tocar',nivel:'rojo'}]}, {hora:'2026-10-04T04:00:00+02:00',estado:'bien'},'2026-10-04')`,sandbox);
 assert.equal(f.estado,'gris');assert.equal(f.estado_referencia,'rojo');assert.equal(f.motivos[0].nivel,'dato');assert.equal(f._medicionCRM.cobertura,'registros_observados_no_exhaustivos');
 console.log('FIX541: rojo heredado queda referencia gris, sin afirmar cumplimiento');
})().catch(e=>{console.error(e);process.exitCode=1});
