const fs436=require('node:fs'),vm436=require('node:vm');
const prefix436=fs436.readFileSync(__dirname+'/pruebas_triaje_durable_432.cjs','utf8').split('let count=0;')[0];
vm436.runInNewContext(prefix436+`
(async()=>{
let n=0;const pass=()=>n++;
// ACK perdido incluso tras guardar: recarga restaura mismo UUID y cuerpo, no confirma Desk.
let {ctx,S,t}=fixture();const submitted=[];ctx.accion=async p=>{submitted.push(JSON.parse(JSON.stringify(p)));throw Error('lost');};
let i=e.intencionTriaje432(ctx,S,t,'asignar');await e.guardarTriaje432(ctx,S,t,i);
let reload=fixture(false);reload.S.porObjeto.set(t.numero,[{tipo:'asignar'}]);let j=e.intencionTriaje432(reload.ctx,reload.S,reload.t,'asignar');
assert.equal(j.recibo,null);assert.equal(j.payload.intencion_id,i.payload.intencion_id);assert.deepEqual(JSON.parse(JSON.stringify(j.payload)),submitted[0]);
reload.ctx.accion=async p=>({...ack(p),intencion_guardada:{id:p.intencion_id,accion_id:7,repetida:true}});await e.guardarTriaje432(reload.ctx,reload.S,reload.t,j);assert(j.recibo.repetida);assert.equal(j.recibo.confirmacion_desk,false);assert.equal(e.filasTriaje432(reload.ctx,reload.S).length,1);pass();
// Cambio real de fuente no puede reaprovechar la intención para otro receptor.
reload=fixture(false);reload.t.agente_propuesto_id='ops';assert.throws(()=>e.intencionTriaje432(reload.ctx,reload.S,reload.t,'asignar'));pass();
({ctx,S,t}=fixture());i=e.intencionTriaje432(ctx,S,t,'cerrar');let resolve;ctx.accion=p=>new Promise(r=>resolve=()=>r(ack(p)));let running=e.guardarTriaje432(ctx,S,t,i);ctx.veModulo=()=>false;resolve();assert.equal(await running,false);assert.equal(i.recibo,null);pass();
// ACK parcial, id inválido, cuerpo ajeno o indicador local no constituyen recibo194.
({ctx,S,t}=fixture());i=e.intencionTriaje432(ctx,S,t,'cerrar');for(const changed of [r=>({...r,id:true}),r=>({...r,intencion_guardada:{...r.intencion_guardada,accion_id:8}}),r=>({...r,local:true,intencion_guardada:null}),r=>({...r,vista_previa:{estado:'Cerrado',ticket:'OTHER'}})])assert.equal(e.reciboTriaje432(changed(ack(i.payload)),i),null);pass();
// Error500 no borra el ticket ni emite éxito; la misma intención sirve para reintento.
({ctx,S,t}=fixture());let calls=0;ctx.accion=async p=>{calls++;if(calls===1)throw Error('500');return ack(p);};i=e.intencionTriaje432(ctx,S,t,'cerrar');assert(await e.guardarTriaje432(ctx,S,t,i));assert.equal(i.estado,'sin_confirmar');assert.equal(e.filasTriaje432(ctx,S).length,1);const uuid=i.payload.intencion_id;await e.guardarTriaje432(ctx,S,t,e.intencionTriaje432(ctx,S,t,'cerrar'));assert.equal(i.payload.intencion_id,uuid);assert(i.recibo);pass();
// Lectura de acciones fallida inhibe escrituras, mantiene inventario visible.
({ctx,S,t}=fixture());S.accionesTriajeLeidas432=false;assert.equal(e.ambitoTriaje432(ctx,S,t,'cerrar'),null);assert.equal(e.filasTriaje432(ctx,S).length,1);pass();
// Límite documentado: una ventana de500 acciones ajenas no acredita ausencia de legacy más antiguo.
({ctx,S,t}=fixture());const hist=Array.from({length:501},(_,k)=>({id:k+1,tipo:k===0?'asignar':'otro',objeto:k===0?t.numero:'T'+k}));const last500=hist.slice(-500);S.porObjeto=new Map(last500.map(x=>[x.objeto,[x]]));assert.equal(last500.some(x=>x.objeto===t.numero),false);assert(e.ambitoTriaje432(ctx,S,t,'asignar'));pass();
// Inicio no declara guardado ni envío; source conserva el ticket después del ACK.
({ctx,S,t}=fixture());assert.equal(e.estadoTriaje432(ctx,S,t),'Sin intención local confirmada');ctx.accion=async p=>ack(p);i=e.intencionTriaje432(ctx,S,t,'cerrar');await e.guardarTriaje432(ctx,S,t,i);assert.match(e.estadoTriaje432(ctx,S,t),/local guardada.*Desk sin confirmar/);assert.equal(e.filasTriaje432(ctx,S).length,1);pass();
console.log(n+' grupos independientes436 PASS · incluye límite legacy500 documentado; sin red/POST real.');
})().catch(e=>{console.error(e);process.exitCode=1});
`,{require,console,__dirname,process},{filename:__filename});
