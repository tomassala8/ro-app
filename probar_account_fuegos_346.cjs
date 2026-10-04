const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const b={Intl,URLSearchParams};vm.createContext(b);
const strip=s=>s.replace(/^import .*;\n/gm,'').replace(/export /g,'');
function load(file,names){vm.runInContext(`Object.assign(globalThis,(()=>{${strip(fs.readFileSync(__dirname+'/modulos/'+file+'.js','utf8'))};return {${names.join(',')}};})());`,b);}
load('control_cartera',['pautaHorasControl','prepararControlCartera']);load('_operaciones_equipo_262',['horasProyectoRango262','pautaProyectoRango262']);load('_horas_fuegos_341',['ambitoFuegos341','horasFuego341']);
class N{constructor(tag,a={},kids=[]){this.tag=tag;this.attrs=a;this.children=[];this.append(...kids);}get isConnected(){return this.main||!!this.parent?.isConnected;}append(...ns){for(const n of ns.flat(Infinity).filter(x=>x!=null)){if(n instanceof N)n.parent=this;this.children.push(n);}}replaceChildren(...ns){for(const n of this.children)if(n instanceof N)n.parent=null;this.children=[];this.append(...ns);}get textContent(){return this.children.map(n=>n instanceof N?n.textContent:String(n)).join(' ');}}
b.h=(t,a,...ns)=>new N(t,a,ns);b.chipEstado=(e,t)=>b.h('span',{'data-estado':e},t);b.panelPlanFuego255=()=>b.h('p',{},'Plan fixture');b.metricasProyectoBaseline=()=>null;
load('_account_fuegos_346',['accountFuego346','firmaAccountFuegos346']);load('_meta_semantica_285',['semanticaMeta285']);load('_cabeceras_operaciones_423',['cabeceraOperaciones423']);load('_operaciones_fuegos_268',['renderFuegos268']);
const ctx=()=>({servidor:true,hoy:'2026-10-03',real:{id:'ops',estado:'activo',puestos:['operaciones']},persona:{id:'ops',estado:'activo',puestos:['operaciones']},datos:{personas:[{id:'ops',estado:'activo',puestos:['operaciones']}]},clientesVisibles:[{id:'c',nombre:'Fixture',activo_confirmado:true,detalle:true}],veModulo:()=>true,ver:x=>({ok:x.cliente_id==='c'}),verdad:()=>({cliente_id:'c',gravedad:'critico'}),nombre:()=>'',vigente:()=>true});
const P=()=>({hoy:'2026-10-03',proyectos:[{cliente_id:'c',horas_mes:14,horas_medicion:{estado:'medido',fuente:'horas',periodo:'2026-10',fecha:'2026-10-03 02:56',cobertura:'parcial'}}]});
const D=()=>({generado:'2026-10-03 03:00',mes_cuota:'2026-10',clientes:[{cliente_id:'c',cuota_horas:{pautadas:10}}]});
let count=0;const t=(name,f)=>{f();count++;console.log('PASS',name)};

const walk=n=>n instanceof N?[n,...n.children.flatMap(walk)]:[];
const fixture=()=>{const c=ctx();c.datos.personas.push({id:'actual',estado:'activo',puestos:['account']},{id:'persona_legacy_baja346',estado:'baja',puestos:['seo']});c.datos.asignaciones=[{cliente_id:'c',silla:'account',persona_id:'actual',principal:true,confianza:'confirmada'}];c.clientesVisibles[0].equipo={account:[{persona_id:'actual',principal:true,confianza:'confirmada'}]};c.verdad=()=>({cliente_id:'c',gravedad:'critico',account:{persona_id:'persona_legacy_baja346'}});c.nombre=id=>id||'Sin nombre';c.datosModulo=async()=>null;return c;};
const main=()=>{const x=new N('main');x.main=true;return x;};
(async()=>{
const c=fixture(),v=main();await b.renderFuegos268(v,c);
t('cache account inactivo no sustituye asignación canónica en tabla/detalle',()=>{assert.equal(b.accountFuego346(c,c.clientesVisibles[0]).id,'actual');assert(!v.textContent.includes('persona_legacy_baja346'));assert.equal(walk(v).filter(n=>n.tag==='td'&&n.textContent==='actual').length,1);assert(walk(v).some(n=>n.tag==='span'&&n.textContent==='actual'));});
for(const [label,change]of [
 ['sin asignación',x=>{x.datos.asignaciones=[];delete x.clientesVisibles[0].equipo;x.clientesVisibles[0].responsable_id='persona_legacy_baja346';}],
 ['persona duplicada',x=>x.datos.personas.push({...x.datos.personas[1]})],
 ['baja',x=>x.datos.personas[1].estado='baja'],
 ['otro puesto',x=>x.datos.personas[1].puestos=['seo']],
 ['conflicto fuentes',x=>{x.datos.personas.push({id:'otro',estado:'activo',puestos:['account']});x.datos.asignaciones[0].persona_id='otro';}],
 ['fecha caducada',x=>{x.datos.asignaciones[0].hasta='2026-10-02';x.clientesVisibles[0].equipo.account[0].hasta='2026-10-02';}]
]){const x=fixture();change(x);const box=main();await b.renderFuegos268(box,x);t(label+' no oculta cliente ni inventa Account',()=>{assert.equal(b.accountFuego346(x,x.clientesVisibles[0]).id,null);assert(box.textContent.includes('Fixture'));assert(box.textContent.includes('Account por confirmar'));assert(!box.textContent.includes('persona_legacy_baja346'));});}
const alta=fixture();alta.datos.asignaciones[0].confianza='alta';alta.clientesVisibles[0].equipo.account[0].confianza='alta';t('identidad alta conserva persona sin acreditar confirmación',()=>{const a=b.accountFuego346(alta,alta.clientesVisibles[0]);assert.equal(a.id,'actual');assert.equal(a.confirmado,false);assert.match(a.texto,/asignación por confirmar/);});
const x=fixture();let resolve;const wait=new Promise(r=>resolve=r);x.datosModulo=()=>wait;const box=main(),promise=b.renderFuegos268(box,x);x.datos.asignaciones[0].persona_id='persona_legacy_baja346';resolve(null);await promise;t('cambio asignación durante GET borra vista',()=>assert.equal(box.textContent,''));
for(const [label,change]of [['asignación',x=>x.datos.asignaciones[0].persona_id='persona_legacy_baja346'],['equipo',x=>x.clientesVisibles[0].equipo.account[0].persona_id='persona_legacy_baja346'],['persona',x=>x.datos.personas[1].estado='baja'],['ACT',x=>x.clientesVisibles[0].activo_confirmado=false],['grant',x=>x.ver=()=>({ok:false})]]){const x=fixture(),box=main();await b.renderFuegos268(box,x);const d=walk(box).find(n=>n.tag==='details');change(x);d.attrs.on.toggle();t('abrir detalle después revocar '+label+' no conserva atribución',()=>assert.equal(box.textContent,''));}
const rev=fixture(),box2=main();await b.renderFuegos268(box2,rev);const a=walk(box2).find(n=>n.tag==='a');rev.datos.asignaciones=[];let denied=false;a.attrs.on.click({preventDefault:()=>denied=true});t('link no navega con asignación cambiada',()=>{assert(denied);assert.equal(box2.textContent,'');});
console.log(count+' grupos346 PASS · resolverControlCartera y renderer268 reales, sin datos privados ni proveedores.');
})().catch(e=>{console.error(e);process.exitCode=1;});
