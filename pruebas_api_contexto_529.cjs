// API y adaptador verDato reales, transporte sintético; ningún POST de negocio.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync(__dirname+'/app.js','utf8');
const fn=src.slice(src.indexOf('async function api('),src.indexOf('/** Ronda 5 · la verdad única por cliente'));
const line=src.split('\n').find(x=>x.trim().startsWith('verDato:'));
const adapter=line.slice(line.indexOf(':')+1).trim().replace(/,$/,'');
function fixture(){let actual=true,calls=0,invalidations=0;
 const replies=[],c={estado:{servidor:true,real:{id:'a'},persona:{id:'a'}},pintura:{usadas:new Set()},medidorUso:null,_ayudas:null,
 vigente:()=>actual,rastrear:false,olvidarTrasCambio:()=>invalidations++,cabeceras:(yo,como)=>({yo,como}),
 fetch:async(_,op)=>{calls++;const r=replies.shift();return r.promise?await r.promise:r;}};
 vm.createContext(c);vm.runInContext(fn+`;this.call=api;this.verDato=${adapter};`,c);
 return {c,replies,setActual:x=>actual=x,get calls(){return calls;},get invalidations(){return invalidations;}};
}
const response=(d,ok=true)=>({ok,status:ok?200:403,json:async()=>d});
const req={almacen:'crm/_privado/leads',ref:'fixture-ref',campo:'datos',cliente_id:'fixture-client'};
const fail=e=>e.status===409&&!e.message.includes('fixture-private');
(async()=>{
 let e=fixture();e.setActual(false);await assert.rejects(e.c.verDato(req),fail);assert.equal(e.calls,0);assert.equal(e.invalidations,0);
 console.log('PASS adaptador privado stale no inicia petición');
 for(const change of ['real','persona','route']){e=fixture();let resolve;const promise=new Promise(r=>resolve=r);e.replies.push({promise});const pending=e.c.verDato(req);
  if(change==='route')e.setActual(false);else e.c.estado[change]={id:'otro'};resolve(response({valor:'fixture-private'}));await assert.rejects(pending,fail);assert.equal(e.calls,1);}
 console.log('PASS identidad real/vista o ruta cambia: respuesta privada no devuelta');
 e=fixture();let parsed;const body=new Promise(r=>parsed=r);e.replies.push({ok:true,status:200,json:()=>body});const pending=e.c.verDato(req);
 await Promise.resolve();e.setActual(false);parsed({valor:'fixture-private'});await assert.rejects(pending,fail);
 console.log('PASS contexto revalidado después de leer JSON');
 e=fixture();e.replies.push(response({valor:'fixture-private'}));const valid=await e.c.verDato(req);assert.equal(valid.valor,'fixture-private');assert.equal(e.calls,1);
 console.log('PASS respuesta autorizada conserva contrato');
 e=fixture();e.replies.push(response({error:'denegado'},false));await assert.rejects(e.c.verDato(req),x=>x.status===403);
 console.log('PASS error HTTP vigente conserva código');
 e=fixture();let resolve;const promise=new Promise(r=>resolve=r);e.replies.push({promise});const mutation=e.c.call('acciones',{metodo:'POST',cuerpo:{intencion_id:'fixture'}});
 e.c.estado.persona={id:'otro'};resolve(response({ok:true,intencion_guardada:{id:'fixture'}}));await assert.rejects(mutation,fail);assert.equal(e.calls,1);
 console.log('PASS mutación incierta no devuelve éxito en otra vista ni reenvía');
 console.log('6 grupos529 PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
