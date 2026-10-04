const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
class N{
 constructor(tag,a={},c=[]){this.tag=tag;this.a=a;this.value=a.value??'';this.disabled=!!a.disabled;this.hidden=!!a.hidden;this.children=[];this.append(...c);if(tag==='select')this.value=this.children[0]?.a.value??'';}
 get isConnected(){return this.attached||!!this.parent?.isConnected;}
 append(...xs){for(const x of xs.flat(Infinity)){if(x==null)continue;if(x instanceof N)x.parent=this;this.children.push(x);}}
 replaceChildren(...xs){this.children=[];this.append(...xs);}
}
const h=(t,a,...c)=>new N(t,a,c),b={h,Date,Intl,crypto,encodeURIComponent};vm.createContext(b);
vm.runInContext(fs.readFileSync('modulos/evidencias_kpi.js','utf8').replace(/^import.*;\n/,'').replace(/export /g,'')+';this.crear=crearRegistroHechos',b);
const find=(n,p)=>n instanceof N?(p(n)?n:n.children.map(x=>find(x,p)).find(Boolean)):null;
(async()=>{
 let calls=[],fail=true;const ctx={servidor:true,soloLectura:false,real:{id:'actor-fixture',puestos:['account']},persona:{id:'actor-fixture',puestos:['account']},clientes:[{id:'cliente-fixture'}],ver:()=>({ok:true}),vigente:()=>true,
 api:async(url,opt)=>{calls.push({url,opt});if(!opt)return{cliente_id:'cliente-fixture',registros:[]};if(fail){fail=false;throw new Error('fixture retry');}return{registro:{cliente_id:'cliente-fixture'}};}};
 const view=b.crear(ctx,'cliente-fixture');view.nodo.attached=true;await view.cargar();
 const form=find(view.nodo,n=>n.tag==='form'),tipo=find(form,n=>n.a['aria-label']==='Hecho realizado'),canal=find(form,n=>n.a['aria-label']==='Canal del hecho'),fecha=find(form,n=>n.a.type==='datetime-local'),periodo=find(form,n=>n.a.type==='month'),ref=find(form,n=>n.a.type==='url');
 assert(periodo.disabled && ref.disabled,'campos informe no fuerzan contacto');
 tipo.value='informe_enviado';tipo.a.on.change();assert(!periodo.disabled&&!ref.disabled&&periodo.required&&ref.required);assert.equal(canal.value,'email');
 const submit=()=>form.a.on.submit({preventDefault(){}}),writes=()=>calls.filter(x=>x.opt);
 fecha.value='2020-10-02T12:00';await submit();assert.equal(writes().length,0,'sin mes no escribe');
 periodo.value='2020-09';await submit();assert.equal(writes().length,0,'sin referencia no escribe');
 ref.value='https://app.clickup.com/t/fixture';await submit();await submit();assert.equal(writes().length,2);
 const x=writes()[0].opt.cuerpo;assert.equal(x.tipo,'informe_enviado');assert.equal(x.periodo_informe,'2020-09');assert.equal(x.enlace,ref.value);assert.equal(x.clave,writes()[1].opt.cuerpo.clave);assert(!('cumplimiento' in x));assert(!('autor_envio' in x));
 ctx.soloLectura=true;await submit();assert.equal(writes().length,2,'revocación sin POST');ctx.soloLectura=false;
 tipo.value='contacto';tipo.a.on.change();assert(periodo.disabled&&ref.disabled&&!periodo.required&&!ref.required);
 await submit();assert.equal(writes().length,3);assert(!('periodo_informe' in writes()[2].opt.cuerpo));assert(!('enlace' in writes()[2].opt.cuerpo));
 const reader=b.crear({...ctx,soloLectura:true},'cliente-fixture');assert(!find(reader.nodo,n=>n.tag==='form'));
 console.log('596 formulario PASS: mes/referencia obligatorios, contacto intacto, idempotencia, revocación y vercomo; DOM ficticio, sin HTTP');
})().catch(e=>{console.error(e);process.exitCode=1;});
