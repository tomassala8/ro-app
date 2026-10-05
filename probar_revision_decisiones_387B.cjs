// Revisión independiente: módulos reales y DOM sintético, sin red/DB principal.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const fixture=fs.readFileSync(__dirname+'/probar_decision_durable_382.cjs','utf8').split('(async()=>{')[0];
const {s,ctx,H,E,text,UUID}=new Function('require','__dirname',fixture+';return {s,ctx,H,E,text,UUID};')(require,__dirname);
s.crypto={randomUUID:()=>UUID};
vm.runInContext('(function(){'+fs.readFileSync(__dirname+'/modulos/_operaciones_decisiones_387.js','utf8').replace(/^import .*;$/gm,'').replace(/export /g,'')+';globalThis.proyectarDecisiones387=proyectarDecisiones387;globalThis.renderDecisiones387=renderDecisiones387;})();',s);
const all=n=>[n,...(n.children||[]).flatMap(all)].filter(x=>x instanceof E),tag=(n,t)=>all(n).filter(x=>x.tag===t);
const row=()=>({id:'db-1',tipo:'para_tomas',cliente_id:'ok',quien:'tomas',titulo:'Revisión local',problema:'Alcance pendiente',recomendacion:'Confirmar alcance',creada:'2026-10-04 08:00:00',respondida:null,respondida_por:null,respuesta:null,revision:H,puede_responder:true,origen:'registro_local',ejecucion_verificada:false,envio_realizado:false});
const doc=r=>({version:'382.1',origen:'registro_local',envio_realizado:false,truncado:false,decisiones:[r||row()]});
const ack=b=>({version:'382.1',resultado:'guardado',recibo:{intencion_id:b.intencion_id,id:'db-1',operacion:b.operacion,revision:H,autor:'tomas',guardado_local:true,envio_realizado:false,ejecucion_verificada:false}});
async function mount(c){const out=new E('div');await s.renderDecisiones387(out,c);return out;}
(async()=>{
 let n=0;
 const c=ctx(),r=row();r.creada=null;assert(s.proyectarDecisiones387(c,doc(r)),'Fecha desconocida no debe descartar colección autorizada');n++;
 const historico=row();historico.creada=null;historico.respondida=null;historico.respuesta_registrada=true;historico.puede_responder=false;const ch=ctx();ch.api=async()=>doc(historico);const hist=await mount(ch);assert(text(hist).includes('Respuesta registrada'));assert(!text(hist).includes('Pendiente de decisión'));assert.equal(tag(hist,'textarea').length,2);n++;
 for(const cambio of [c=>c.datos.personas[0].estado='baja',c=>c.persona.id='otra',c=>c.clientes.splice(0),c=>c.veModulo=()=>false]){
  const c=ctx();let resolve,gets=0;c.api=()=>{gets++;return new Promise(r=>resolve=r);};const out=new E('div'),pending=s.renderDecisiones387(out,c);cambio(c);resolve(doc());await pending;
  assert.equal(gets,1);assert(!text(out).includes('Revisión local'));n++;
 }
 for(const mode of ['actor','catalogo','desconexion']){
  const c=ctx();let done,posts=0,gets=0;c.api=async(path,opt)=>{if(!opt){gets++;return doc();}posts++;return await new Promise(r=>done=()=>r(ack(opt.cuerpo)));};
  const out=await mount(c),form=tag(out,'details')[0];tag(form,'input')[0].value='Decisión';tag(form,'textarea').forEach(x=>x.value='Texto operativo');tag(form,'select')[0].value='ok';
  const pending=tag(form,'button')[0].events.click();
  if(mode==='actor')c.persona.id='otra';else if(mode==='catalogo')c.clientes[0].activo_confirmado=false;else {all(out).forEach(x=>x.isConnected=false);out.replaceChildren();}
  done();await pending;assert.equal(posts,1);assert.equal(gets,1,'No nuevo GET tras cambio de ámbito o desconexión');assert(!text(out).includes('Guardado en RO'));n++;
 }
 console.log(n+' grupos independientes387B PASS: fecha unknown y respuestas tardías con revocación/desconexión.');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
