const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const b={Intl,URLSearchParams};vm.createContext(b);
const strip=s=>s.replace(/^import .*;\n/gm,'').replace(/export /g,'');
function load(file,names){vm.runInContext(`Object.assign(globalThis,(()=>{${strip(fs.readFileSync('modulos/'+file+'.js','utf8'))};return {${names.join(',')}};})());`,b);}
load('control_cartera',['pautaHorasControl','prepararControlCartera']);load('_operaciones_equipo_262',['horasProyectoRango262','pautaProyectoRango262']);load('_horas_fuegos_341',['ambitoFuegos341','horasFuego341']);
class N{constructor(tag,a={},kids=[]){this.tag=tag;this.attrs=a;this.children=[];this.append(...kids);}get isConnected(){return this.main||!!this.parent?.isConnected;}append(...ns){for(const n of ns.flat(Infinity).filter(x=>x!=null)){if(n instanceof N)n.parent=this;this.children.push(n);}}replaceChildren(...ns){for(const n of this.children)if(n instanceof N)n.parent=null;this.children=[];this.append(...ns);}get textContent(){return this.children.map(n=>n instanceof N?n.textContent:String(n)).join(' ');}}
b.h=(t,a,...ns)=>new N(t,a,ns);b.chipEstado=(e,t)=>b.h('span',{'data-estado':e},t);b.panelPlanFuego255=()=>b.h('p',{},'Plan fixture');b.metricasProyectoBaseline=()=>null;
load('_account_fuegos_346',['accountFuego346','firmaAccountFuegos346']);load('_meta_semantica_285',['semanticaMeta285']);load('_cabeceras_operaciones_423',['cabeceraOperaciones423']);load('_operaciones_fuegos_268',['renderFuegos268']);
const ctx=()=>({servidor:true,hoy:'2026-10-03',real:{id:'ops',estado:'activo',puestos:['operaciones']},persona:{id:'ops',estado:'activo',puestos:['operaciones']},datos:{personas:[{id:'ops',estado:'activo',puestos:['operaciones']}]},clientesVisibles:[{id:'c',nombre:'Fixture',activo_confirmado:true,detalle:true}],veModulo:()=>true,ver:x=>({ok:x.cliente_id==='c'}),verdad:()=>({cliente_id:'c',gravedad:'critico'}),nombre:()=>'',vigente:()=>true});
const P=()=>({hoy:'2026-10-03',proyectos:[{cliente_id:'c',horas_mes:14,horas_medicion:{estado:'medido',fuente:'horas',periodo:'2026-10',fecha:'2026-10-03 02:56',cobertura:'parcial'}}]});
const D=()=>({generado:'2026-10-03 03:00',mes_cuota:'2026-10',clientes:[{cliente_id:'c',cuota_horas:{pautadas:10}}]});
let count=0;const t=(name,f)=>{f();count++;console.log('PASS',name)};
t('positivo parcial misma ventana',()=>{const m=b.horasFuego341(ctx(),P(),D(),'c');assert.equal(m.horas,14);assert.equal(m.porcentaje,140);assert.equal(m.estado,'rojo');assert.match(m.detalle,/no presupuesto aprobado/)});
t('bajo referencia no acredita cumplimiento',()=>{const p=P();p.proyectos[0].horas_mes=2;assert.equal(b.horasFuego341(ctx(),p,D(),'c').estado,'gris')});
t('cero observado válido',()=>{const p=P();p.proyectos[0].horas_mes=0;assert.equal(b.horasFuego341(ctx(),p,D(),'c').porcentaje,0)});
t('sin permiso conserva horas sin filtrar pauta',()=>{const c=ctx();c.ver=x=>({ok:x.tipo==='cliente_detalle'});const m=b.horasFuego341(c,P(),D(),'c');assert.equal(m.horas,14);assert.equal(m.porcentaje,null);assert.doesNotMatch(m.detalle,/10 h/)});
t('pauta otro mes no ratio',()=>{const d=D();d.mes_cuota='2026-09';assert.equal(b.horasFuego341(ctx(),P(),d,'c').porcentaje,null)});
t('pauta cero no division',()=>{const d=D();d.clientes[0].cuota_horas.pautadas=0;assert.equal(b.horasFuego341(ctx(),P(),d,'c').porcentaje,null)});
t('suplantación sin pauta',()=>{const c=ctx();c.real={...c.real,id:'real'};c.datos.personas.push(c.real);assert.equal(b.horasFuego341(c,P(),D(),'c').porcentaje,null)});
t('proyecto duplicado',()=>{const p=P();p.proyectos.push(p.proyectos[0]);assert.equal(b.horasFuego341(ctx(),p,D(),'c'),null)});
t('descriptor sin dato no legado',()=>{const p=P();p.proyectos[0].horas_medicion.estado='sin_dato';assert.equal(b.horasFuego341(ctx(),p,D(),'c'),null)});
t('fecha futura y distinto corte',()=>{const p=P();p.proyectos[0].horas_medicion.fecha='2026-10-04 01:00';assert.equal(b.horasFuego341(ctx(),p,D(),'c'),null);p.proyectos[0].horas_medicion.fecha='2026-10-02';assert.equal(b.horasFuego341(ctx(),p,D(),'c'),null)});
t('ACT catálogo y cliente duplicado',()=>{const c=ctx();c.clientesVisibles[0].activo_confirmado=false;assert.equal(b.horasFuego341(c,P(),D(),'c'),null);const x=ctx();x.datos.personas.push(x.persona);assert.equal(b.ambitoFuegos341(x),null)});
t('rol cambiado en catálogo invalida ámbito',()=>{const c=ctx();c.datos.personas[0].puestos=['seo'];assert.equal(b.ambitoFuegos341(c),null)});
t('pauta duplicada no ratio',()=>{const d=D();d.clientes.push(d.clientes[0]);assert.equal(b.horasFuego341(ctx(),P(),d,'c').porcentaje,null)});
t('módulo horas de proyecto revocado',()=>{const c=ctx();c.veModulo=x=>x!=='produccion';assert.equal(b.horasFuego341(c,P(),D(),'c'),null)});
const main=()=>{const n=new N('main');n.main=true;return n};
(async()=>{
 let gets=[];const c=ctx();c.ver=x=>({ok:x.tipo==='cliente_detalle'});c.datosModulo=async r=>{gets.push(r);return r.startsWith('produccion')?P():null};const cont=main();await b.renderFuegos268(cont,c);
 t('render horas sin GET pauta privada',()=>{assert(cont.textContent.includes('14 h'));assert(!gets.some(x=>x.includes('dinero_cliente')))});
 const c2=ctx();c2.datosModulo=async r=>r.startsWith('produccion')?P():r.startsWith('dinero')?D():null;const v=main();await b.renderFuegos268(v,c2);t('render porcentaje y 12 métricas',()=>{assert(v.textContent.includes('≥140 %'));assert(v.textContent.includes('Outreach · leads'))});
 const walk=n=>n instanceof N?[n,...n.children.flatMap(walk)]:[];
 c2.ver=x=>({ok:x.tipo==='cliente_detalle'});walk(v).find(n=>n.tag==='details').attrs.on.toggle();t('pauta revocada al abrir detalle limpia raíz',()=>assert.equal(v.textContent,''));
 const c3=ctx(),v3=main();c3.datosModulo=c2.datosModulo;await b.renderFuegos268(v3,c3);const link=walk(v3).find(n=>n.tag==='a');c3.clientesVisibles[0].activo_confirmado=false;let denied=false;link.attrs.on.click({preventDefault:()=>denied=true});t('enlace revocado no navega ni conserva métricas',()=>{assert(denied);assert.equal(v3.textContent,'')});
 let resolve;const wait=new Promise(r=>resolve=r),s=ctx(),old=main();s.datosModulo=()=>wait;const pending=b.renderFuegos268(old,s);s.datos.personas[0].estado='baja';resolve(P());await pending;t('revocación durante GET borra copia',()=>assert.equal(old.textContent,''));
 t('actor inválido cero lecturas',()=>assert.equal(b.ambitoFuegos341({...ctx(),servidor:false}),null));
 console.log(count+' grupos341 PASS: helpers262 reales, pauta autorizada, renderer y await revocado.');
})().catch(e=>{console.error(e);process.exitCode=1});
