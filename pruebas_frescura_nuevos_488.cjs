const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const src=fs.readFileSync(__dirname+'/modulos/nuevos.js','utf8');
const ahora=Date.parse('2026-10-04T10:00:00Z');
class Reloj extends Date {static now(){return ahora;}}
const h=(tag,attrs,...kids)=>({tag,attrs,kids:kids.flat(Infinity)});
const C={Date:Reloj,Intl,Number,Object,h,S:{meta:{}},chipEstado:(estado,texto)=>({estado,texto}),frescura:x=>({frescura:x})};
vm.createContext(C);
vm.runInContext(src.slice(src.indexOf('function instanteFuente488'),src.indexOf('\n\n',src.indexOf('const fres =')))+'\n'+src.slice(src.indexOf('function avisoDatos('),src.indexOf('// ================================================================== fila de un alta'))+'\nthis.api={edadH,fres,avisoDatos,instanteFuente488};',C);
const a=C.api;let n=0;function test(t,f){f();n++;console.log('PASS '+t);}
test('30h incluida y mayor antigua',()=>{assert.equal(a.edadH('2026-10-03T04:00:00Z'),30);assert.equal(a.fres({hora:'2026-10-03T04:00:00Z',estado:'bien'}).estado,'ok');assert.equal(a.fres({hora:'2026-10-03T03:59:59Z',estado:'bien'}).estado,'viejo');});
test('fechas futuras no se redondean a cero',()=>{for(const x of ['2026-10-04T10:00:01Z','2026-10-04 12:01']){assert.equal(a.edadH(x),null);assert.equal(a.fres({hora:x,estado:'bien'}).estado,'sin datos');}});
test('ausencia/tipos/calendarios/reloj inválidos',()=>{for(const x of [null,undefined,'',3,{},'no fecha','2026-02-30 10:00','2026-10-04 24:00','2026-10-04T10:00:00+02:99','2026-10-04T10:00:00+14:01','2026-10-04T10:00:00+15:00'])assert.equal(a.edadH(x),null);assert.equal(a.edadH('2026-10-04T09:00:00Z',NaN),null);});
test('Madrid explícito y naive confirmada, independientemente zona máquina',()=>{assert.equal(a.edadH('2026-10-04 11:00'),1);assert.equal(a.edadH('2026-10-04T11:00:00+02:00'),1);assert.equal(a.edadH('2026-10-04T11:00:00+0200'),1);assert.equal(a.edadH('2026-10-04T09:00:00Z'),1);assert.equal(a.instanteFuente488('2026-01-10 10:00'),Date.parse('2026-01-10T09:00:00Z'));});
test('cambio horario inexistente/ambiguo no se inventa',()=>{assert.equal(a.instanteFuente488('2026-03-29 02:30'),null);assert.equal(a.instanteFuente488('2026-10-25 02:30'),null);assert.equal(a.instanteFuente488('2026-10-25T02:30:00+02:00'),Date.parse('2026-10-25T00:30:00Z'));});
test('fallo fuente reciente nunca ok; marca original conservada',()=>{const x=a.fres({hora:'2026-10-04 11:00',estado:'sin_conectar'},'Meta');assert.equal(x.estado,'sin datos');assert.equal(x.lectura,'2026-10-04 11:00');});
const texto=x=>JSON.stringify(x);
test('renderer real vacío no verde ni Datos al día',()=>{const x=texto(a.avisoDatos({}));assert.ok(x.includes('5 fuentes por revisar'));assert.ok(!x.includes('"estado":"verde"'));assert.ok(!x.includes('Datos al día'));});
test('renderer cinco recientes con advertencia cobertura y detalle original',()=>{const fuentes=Object.fromEntries(['sign','clickup','meta','ghl','dns'].map(k=>[k,{hora:'2026-10-04 11:00',estado:'bien'}]));const x=texto(a.avisoDatos({fuentes}));assert.ok(x.includes('Fuentes recientes'));assert.ok(x.includes('no acredita cobertura'));assert.ok(x.includes('Lectura original: 2026-10-04 11:00 · Europe/Madrid'));fuentes.ghl.hora='mal';const y=texto(a.avisoDatos({fuentes}));assert.ok(y.includes('1 fuente por revisar'));assert.ok(!y.includes('"estado":"verde"'));});
console.log(n+' grupos PASS');
// Regresión de módulo completo: no sustituye ni extrae filaAlta/renderer/utilidades.
(async()=>{
class Nodo{constructor(tag,attrs={},kids=[]){this.tag=tag;this.attrs=attrs;this.style={...(attrs.style||{})};this.children=[];this.append(...kids);}append(...xs){for(const x of xs.flat(Infinity))if(x!=null)this.children.push(x);}replaceChildren(...xs){this.children=[];this.append(...xs);}querySelectorAll(){return [];}get textContent(){return this.children.map(x=>x instanceof Nodo?x.textContent:String(x)).join(' ');}}
const H=(t,a,...k)=>new Nodo(t,a,k);
const base={Date:Reloj,Intl,Number,Object,Map,Set,Promise,Math,JSON,console,MutationObserver:class{observe(){}},setTimeout:()=>0,h:H,
fmt:{num:x=>String(x),pct:x=>`${x}%`},fechas:{hoy:()=> '2026-10-04',semana:()=>({desde:'2026-09-28',hasta:'2026-10-04'})},sumarDias:x=>x,
plegarConsejo:()=>{},veObjetivos:()=>false,cargarObjetivos:async()=>new Map(),puedeEditar:()=>false,
chipEstado:(e,t)=>H('span',{estado:e},t),frescura:x=>H('span',{},x.fuente),icono:x=>x,iniciales:x=>x.slice(0,2),
logoCliente:x=>H('span',{},x.nombre),tile:x=>H('div',{},x.etiqueta),tiles:xs=>H('div',{},xs),panel:(x,...k)=>H('section',{},x.titulo,...k),
avisoParcial:x=>H('p',{},x),chipsFiltro:()=>{const x=H('div',{});x.valor=()=>'';return x;}};
vm.createContext(base);vm.runInContext(src.replace(/import\s+[\s\S]*?from\s+['"][^'"]+['"];?/g,'').replace('export default {','this.modulo = {')+'\nthis.utilidades={fechaLarga,nombrePersona,verLeads,_M3N,_DSN};',base);
const altas=Array.from({length:17},(_,i)=>({cliente_id:`fixture-${i}`,nombre:`Alta sintética ${i}`,alta:'2026-09-28',dia:6,alertas:[],hitos:[],diferencias:[],plazo:{estado:'gris',dia_encendido:null,limite:'2026-10-10',texto:'Pendiente'},onboarding:{n:2,hechas:1,pct:50},dueno:{nombre:'Persona sintética'},equipo:{taller:{estado:'agendado',fecha:'2026-10-03 12:00'}}}));
const d={altas,fuentes:{},reglas:{encendido_limite:12,encendido_objetivo:10,sin_tareas_horas:48}};
const cont=H('main',{});let titulo='';let posts=0;
await base.modulo.render(cont,{params:[],nivel:'resumen',clientes:altas.map(x=>({id:x.cliente_id,nombre:x.nombre})),carteraIds:new Set(),datosModulo:async()=>d,api:async()=>({acciones:[]}),titulo:(...x)=>{titulo=x.join(' ');},accion:async()=>{posts++;throw Error('POST prohibido');}});
assert.ok(titulo.includes('17 altas'));assert.ok(cont.textContent.includes('28-sep'));assert.equal(cont.textContent.match(/Alta sintética/g).length,12);
const todos=[];function walk(x){if(x instanceof Nodo){todos.push(x);x.children.forEach(walk);}}walk(cont);const expandir=todos.find(x=>x.tag==='button'&&x.textContent.includes('Ver todas las altas (17)'));assert.equal(todos.filter(x=>x.attrs.role==='listitem').length,6);assert.ok(expandir);expandir.attrs.on.click();assert.equal(cont.textContent.match(/Alta sintética/g).length,34);const finales=[];function contar(x){if(x instanceof Nodo){finales.push(x);x.children.forEach(contar);}}contar(cont);assert.equal(finales.filter(x=>x.attrs.role==='listitem').length,17);assert.equal(posts,0);
assert.equal(base.utilidades.nombrePersona({nombre:'Sintética'}),'Sintética');assert.equal(base.utilidades.verLeads(1),'1 lead');assert.equal(base.utilidades._M3N.length,12);assert.equal(base.utilidades._DSN.length,7);
console.log('PASS render completo 17 altas + desplegar sin POST + utilidades restauradas');
})().catch(e=>{console.error(e);process.exitCode=1;});
