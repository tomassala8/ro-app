const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),crypto=require('crypto');
let source=fs.readFileSync(__dirname+'/modulos/evidencias_kpi.js','utf8').replace(/^import .*;\n/,'').replace(/export /g,'');
class Nodo{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[];this.value=attrs.value??'';this.disabled=!!attrs.disabled;this.attached=false;this.append(...children);if(tag==='select')this.value=this.children[0]?.attrs.value??'';}
 get isConnected(){return this.attached||!!this.parent?.isConnected;}
 append(...xs){for(const x of xs.flat(Infinity)){if(x==null)continue;if(x instanceof Nodo)x.parent=this;this.children.push(x);}}
 replaceChildren(...xs){this.children=[];this.append(...xs);}
}
const h=(tag,attrs,...xs)=>new Nodo(tag,attrs,xs);
const sandbox={h,Date,Intl,crypto,encodeURIComponent};vm.createContext(sandbox);vm.runInContext(source+';this.fns={fechaHechoLocal,permisoRegistro,crearRegistroHechos}',sandbox);
const {fechaHechoLocal,permisoRegistro,crearRegistroHechos}=sandbox.fns;
const busca=(n,p)=>n instanceof Nodo?(p(n)?n:n.children.map(x=>busca(x,p)).find(Boolean)):undefined;
const base=()=>({servidor:true,soloLectura:false,real:{id:'carla',puestos:['account']},persona:{id:'carla',puestos:['account']},clientes:[{id:'gac'}],ver:()=>({ok:true}),vigente:()=>true,nombre:id=>id});
(async()=>{
 assert.throws(()=>fechaHechoLocal('2030-02-30T25:90'));
 assert.throws(()=>fechaHechoLocal('2999-01-01T12:00'));
 assert.throws(()=>fechaHechoLocal('2020-01-01'));
 assert.match(fechaHechoLocal('2020-01-01T12:00'),/^2020-01-01T/);
 assert.equal(!!permisoRegistro(base(),'gac'),true);
 for(const change of [{soloLectura:true},{servidor:false},{real:{id:'tomas',puestos:['direccion']}},{clientes:[]},{persona:{id:'carla',puestos:['seo']}},{ver:()=>({ok:'true'})}])assert.equal(!!permisoRegistro({...base(),...change},'gac'),false);
 let alive=true,calls=[],fail=true;
 const ctx={...base(),vigente:()=>alive,api:async(url,opt)=>{calls.push({url,opt});if(!opt)return{cliente_id:'gac',registros:[]};if(fail){fail=false;throw new Error('Sin confirmación');}return{registro:{cliente_id:'gac'}};}};
 const p=crearRegistroHechos(ctx,'gac');p.nodo.attached=true;await p.cargar();
 const form=busca(p.nodo,n=>n.tag==='form'),fecha=busca(form,n=>n.attrs.type==='datetime-local');fecha.value='2020-01-01T12:00';
 const submit=()=>form.attrs.on.submit({preventDefault(){}});
 await submit();await submit();const writes=calls.filter(c=>c.opt);assert.equal(writes.length,2);assert.equal(writes[0].opt.cuerpo.clave,writes[1].opt.cuerpo.clave,'retry conserva la misma intención');
 assert.equal(writes[0].opt.cuerpo.cliente_id,'gac');assert.equal(writes[0].opt.cuerpo.accion,'registrar');
 await submit();assert.equal(calls.filter(c=>c.opt)[2].opt.cuerpo.clave,writes[1].opt.cuerpo.clave,'repetir el mismo formulario confirmado tampoco duplica');
 alive=false;await submit();assert.equal(calls.filter(c=>c.opt).length,3,'navegación revocada no escribe');
 alive=true;ctx.soloLectura=true;await submit();assert.equal(calls.filter(c=>c.opt).length,3,'revocación de escritura evita POST');
 const reader=crearRegistroHechos({...base(),soloLectura:true},'gac');assert.equal(busca(reader.nodo,n=>n.tag==='form'),undefined);
 console.log('152 PASS: fecha válida, permisos exactos, consulta sin formulario, reintento sin duplicación y revocación antes de escribir.');
})().catch(e=>{console.error(e);process.exitCode=1;});
