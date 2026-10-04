const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class N{constructor(tag,attrs={},kids=[]){this.tag=tag;this.attrs=attrs;this.style=attrs.style||{};this.children=[];this.append(...kids)}append(...kids){this.children.push(...kids.flat(Infinity).filter(x=>x!=null))}get textContent(){return this.children.map(x=>x instanceof N?x.textContent:String(x)).join(' ')}desc(){return this.children.filter(x=>x instanceof N).flatMap(x=>[x,...x.desc()])}}
const h=(tag,a,...kids)=>new N(tag,a,kids),src=fs.readFileSync(__dirname+'/modulos/captacion.js','utf8');
let actions=0,editor=0,tabs;
const env={h,S:{1:'4px',2:'8px',3:'12px',4:'16px'},GRAV:{dato:{t:'Sin dato'}},CUELLO:{paid:{t:'Paid',i:'paid'}},
 nombre:(_,id)=>id,crmTexto:()=> 'responsable CRM',iniciales:s=>s.slice(0,1),gc:()=>({e:'ambar',t:'Vigilar'}),
 logoCliente:(_,cls)=>h('img',{class:cls}),chipPub:()=>h('span',{class:'chip gris'},'Publicidad pendiente'),
 chipEstado:(e,t)=>h('span',{class:'chip '+e},t),esTienda:c=>!!c.tienda_online,chipCuello:()=>h('span',{},'Se rompe en: Paid'),icono:()=>null,
 chipCli:()=>null,selectorCliente:()=>h('button',{},'Cambiar cliente'),fDiaRO:x=>x,hoyMadrid:()=> '2026-10-04',
 textoMot:m=>m.texto,botonTarea:()=>h('button',{},'Tarea a Agus'),quienArregla:()=> 'responsable existente',
 medirCplPaid:()=>({real:null,estado:'gris',unidadAcreditada:false}),num:x=>x==null?'—':String(x),variacion:()=>null,
 tile:o=>h('div',{class:'tile '+o.estado},o.etiqueta,o.valor,o.contexto),tiles:t=>h('div',{'data-cifras':''},t),candado:t=>h('span',{},t),
 panel:(o,...kids)=>h('section',{'data-panel':o.titulo},o.titulo,...kids),acciones:()=>{actions++;return h('button',{},'Acción existente')},
 barraTarjeta:()=>{editor++;return h('div',{'data-editor':''},'Editor existente')},lineaFuentes:()=>h('details',{},'Fuentes existentes'),fuenteDe:()=>null,
 pestanas:o=>{tabs=o.pestanas;const n=h('div',{'data-tabs':''});o.pintar('resumen',n);return n;},avisoParcial:t=>h('p',{},t),NOTA_TIENDA:'Unidad pendiente',
 vacio:o=>h('p',{},o.titulo)};
vm.createContext(env);
vm.runInContext(src.slice(src.indexOf('function plegablePaid411('),src.indexOf('/** El contenedor es una rejilla')),env);
vm.runInContext(src.slice(src.indexOf('function pintarTarjeta('),src.indexOf('\nfunction quienArregla(')),env);
const c={cliente_id:'fixture',nombre:'Cliente fixture',severidad:'dato',equipo:{trafficker:'p1',account:'p2',crm:'p3',account_confianza:'confirmada'},nicho:'Sector observado',nuevo:true,cuello:['paid'],plataformas:['meta','google'],tienda_online:true,cuenta_meta:{estado:'restringida',enlace:'https://example.test/meta'},ghl:{enlace:'https://example.test/ghl'},motivos:[{texto:'Señal existente',clase_id:'paid',nivel:'atencion'}],avisos:[],objetivo:{cargado:false},leads:{'7d':5,'7d_prev':3,ayer:1,mes_anterior:4}};
const d={clientes:[c],parametros:{},datos_hasta:'2026-10-03'},ctx={nivel:'todo',clientes:[{id:'fixture'}],titulo(){},navegar(){}};
const out=h('div',{});env.pintarTarjeta(out,ctx,d,'fixture');
const cab=out.desc().find(n=>n.attrs['data-paid-cabecera']==='411'),fold=cab.desc().find(n=>n.tag==='details');
assert(cab);assert(!cab.desc().some(n=>n.tag==='h2'));assert(!fold.attrs.open);assert.equal(fold.children[0].textContent,'Equipo y contexto');
assert(fold.textContent.includes('Trafficker: p1'));assert(fold.textContent.includes('Account: p2'));assert(fold.textContent.includes('CRM: responsable CRM'));
assert(fold.textContent.includes('Sector observado'));assert(fold.textContent.includes('Tienda online'));assert(fold.textContent.includes('Se rompe en'));assert(fold.textContent.includes('Google Ads'));assert(fold.textContent.includes('Cliente nuevo'));
assert(cab.desc().some(n=>n.attrs.class==='chip ambar'&&n.textContent==='Estado: Vigilar'));
assert(cab.desc().some(n=>n.attrs.class==='chip rojo'&&n.textContent.includes('restringida')));
assert(cab.desc().some(n=>n.attrs.class==='chip ambar'&&n.textContent==='Objetivo sin cargar'));
assert.deepEqual(cab.desc().filter(n=>n.tag==='a').map(n=>n.attrs.href),['https://example.test/meta','https://example.test/ghl','#/en-rojo/fixture']);
assert(cab.desc().filter(n=>n.tag==='a'&&n.attrs.target).every(n=>n.attrs.rel==='noopener'));
const signals=out.desc().find(n=>n.tag==='details'&&n.children[0]?.textContent==='Señales y avisos (1)');assert(signals);assert(!signals.attrs.open);assert(signals.textContent.includes('Señal existente'));
const action=out.desc().find(n=>n.attrs['data-panel']==='Actuar');assert(action);assert(!signals.desc().includes(action));assert.equal(actions,1);assert.equal(editor,1);
assert.deepEqual(Array.from(tabs,t=>t.id),['resumen','ventanas','embudo','campanas','anuncios','metas','quincenal','historia']);
const summary=h('div',{});env.pintarTarjeta(summary,{...ctx,nivel:'resumen'},d,'fixture');assert.equal(editor,1);assert.equal(actions,2);
assert(out.desc().filter(n=>n.tag==='summary'&&n.style.minHeight).every(n=>n.style.minHeight==='44px'));
const absent=h('div',{});env.pintarTarjeta(absent,{...ctx,clientes:[]},d,'otro');assert(!absent.desc().some(n=>n.attrs['data-paid-cabecera']));assert.equal(actions,2);
assert(out.desc().find(n=>Object.hasOwn(n.attrs,'data-editor')));assert(out.desc().find(n=>Object.hasOwn(n.attrs,'data-cifras')));
console.log('9 grupos411 PASS · cabecera/detalle reales, campos y colores conservados, plegables cerrados, editor/acciones/pestañas intactos, cuenta ausente sin detalle.');
