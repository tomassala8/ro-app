const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const file=n=>fs.readFileSync(__dirname+'/modulos/'+n,'utf8');
const cargar=s=>import('data:text/javascript;base64,'+Buffer.from(s).toString('base64'));
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return{resolve,promise}};
class El{constructor(tag,a={},xs=[]){this.tag=tag;this.attrs=a;this.children=xs.flat(Infinity).filter(x=>x!=null);this.value=a.value||'';this.listeners=a.on||{};this.isConnected=true;this.textContent='';this.disabled=false}replaceChildren(...xs){this.children=xs.flat(Infinity)}append(...xs){this.children.push(...xs)}all(){return this.children.flatMap(x=>x instanceof El?[x,...x.all()]:[])}get texto(){return this.textContent+this.children.map(x=>x instanceof El?x.texto:String(x)).join(' ')}}
const ctx=()=>({servidor:true,pilotoLectura:false,soloLectura:false,real:{id:'ana',puestos:['account']},persona:{id:'ana',puestos:['account']},clientes:[{id:'fixture'}],ver:()=>({ok:true}),vigente:()=>true,nombre:p=>p});
(async()=>{
 let failures=[];
 const run=async(n,f)=>{try{await f();console.log('PASS '+n)}catch(e){failures.push(n);console.log('FAIL '+n+': '+e.message)}};
 const word=await cargar(file('_informe_word.js'));
 const mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document';
 await run('Word cambio de identidad durante fetch deniega',async()=>{
   const c=ctx(),d=deferred();const p=word.obtenerWord(c,'fixture','2026-09',{isConnected:true},()=>d.promise);
   c.real={id:'bea',puestos:['account']};c.persona={id:'bea',puestos:['account']};
   d.resolve(new Response(Uint8Array.of(80,75,3,4,1),{headers:{'Content-Type':mime}}));
   await assert.rejects(p);
 });
 await run('Word cambio de vista entre chunks cancela stream',async()=>{
   const c=ctx(),d=deferred();let n=0,cancelado=false;
   const reader={read:()=>++n===1?Promise.resolve({done:false,value:Uint8Array.of(80,75,3,4)}):d.promise,cancel:async()=>{cancelado=true}};
   const p=word.obtenerWord(c,'fixture','2026-09',{isConnected:true},async()=>({ok:true,headers:{get:k=>k==='Content-Type'?mime:null},body:{getReader:()=>reader}}));
   await new Promise(r=>setImmediate(r));c.persona={id:'bea',puestos:['account']};d.resolve({done:true});
   await assert.rejects(p);assert(cancelado);
 });
 await run('Word límite en stream sin Content-Length',async()=>{
   const r=new Response(new ReadableStream({start(c){c.enqueue(new Uint8Array(5*1024*1024+1));c.close()}}),{headers:{'Content-Type':mime}});
   await assert.rejects(word.obtenerWord(ctx(),'fixture','2026-09',{isConnected:true},async()=>r));
 });
 globalThis.__h=(tag,a,...xs)=>new El(tag,a,xs);
 const ui=await cargar(file('evidencias_kpi.js').replace(/^import .*;$/mg,'')+'\nconst h=globalThis.__h;');
 await run('Hechos revocación de permiso durante GET no renderiza',async()=>{
   const c=ctx(),d=deferred();c.api=()=>d.promise;const m=ui.crearRegistroHechos(c,'fixture');const p=m.cargar();
   c.ver=()=>({ok:false});c.persona.puestos=['seo'];
   d.resolve({cliente_id:'fixture',registros:[{id:'r1',tipo:'contacto',fecha_madrid:'2026-10-03',registrado_por:'NO_DEBE_RENDERIZAR',canal:'telefono',estado:'declarado'}]});await p;
   assert(!m.nodo.texto.includes('NO_DEBE_RENDERIZAR'));assert(!m.nodo.all().some(x=>x.tag==='form'));
   c.api=()=>{throw Error('No debe consultar')};await m.cargar();
 });
 await run('Revocar no reutiliza currentTarget tras await',async()=>{
   const c=ctx();c.api=async(route,o)=>o?{ok:true}:{cliente_id:'fixture',registros:[{id:'r1',tipo:'contacto',fecha_madrid:'2026-10-03',registrado_por:'ana',canal:'telefono',estado:'declarado'}]};
   const m=ui.crearRegistroHechos(c,'fixture');await m.cargar();const boton=m.nodo.all().find(x=>x.tag==='button'&&x.texto==='Revocar este registro');
   let reads=0;const event={get currentTarget(){return ++reads===1?boton:null}};
   await boton.listeners.click(event);
 });
 await run('Registro conserva UUID tras error y niega POST tras navegación',async()=>{
   const c=ctx();let keys=[],posts=0;c.api=async(route,o)=>{if(!o)return{cliente_id:'fixture',registros:[]};posts++;keys.push(o.cuerpo.clave);throw Error('fallo simulado')};
   const m=ui.crearRegistroHechos(c,'fixture');const form=m.nodo.all().find(x=>x.tag==='form');
   const selects=m.nodo.all().filter(x=>x.tag==='select');selects[0].value='contacto';selects[1].value='telefono';selects[2].value='seguimiento';
   const fecha=m.nodo.all().find(x=>x.tag==='input');fecha.value='2026-09-30T12:00';
   const event={preventDefault(){}};await form.listeners.submit(event);await form.listeners.submit(event);
   assert.equal(posts,2);assert.equal(keys[0],keys[1]);c.vigente=()=>false;await form.listeners.submit(event);assert.equal(posts,2);
 });
 console.log('156 resumen: '+failures.length+' hallazgos reproducidos');if(failures.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
