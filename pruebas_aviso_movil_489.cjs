// Fragmento real487/489 y DOM sintético; sin UI real/red/datos privados.
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert/strict');
const app=fs.readFileSync(path.join(__dirname,'app.js'),'utf8'),css=fs.readFileSync(path.join(__dirname,'estilos.css'),'utf8');
const code=app.slice(app.indexOf('// 487 ·'),app.indexOf('// Fin 487'));
function setup(){const nodes={},created=[];
 class N{constructor(t,a={},ks=[]){this.tag=t;this.attrs=a;Object.assign(this,a);this.children=[];ks.flat(Infinity).filter(x=>x!=null).forEach(x=>this.append(x));}
  append(x){if(typeof x==='object')x.parent=this;this.children.push(x);}remove(){this.parent.children=this.parent.children.filter(x=>x!==this);}
  querySelector(){return this.children.find(x=>x.attrs?.['data-lecturas-487'])||null;}
  get textContent(){return this.text??this.children.map(x=>typeof x==='string'?x:x.textContent).join('');}set textContent(x){this.text=x;this.children=[];}}
 const header=new N('header',{class:'topbar'}),badge=new N('span',{hidden:true}),detail=new N('details');
 header.after=x=>{created.push(x);nodes[x.id]=x;};nodes['dato-guardado']=badge;nodes.frescura=detail;
 const pintura={usadas:new Set(['modulo/crm/crm']),estadosLectura:new Map(),guardado:null};
 const ctx={pintura,Date,Number,document:{getElementById:k=>nodes[k],querySelector:s=>s==='.topbar'?header:null},
  h:(t,a,...ks)=>new N(t,a,ks),fechas:{hora:s=>new Date(s).toLocaleTimeString('es-ES',{hour:'2-digit',minute:'2-digit',timeZone:'Europe/Madrid'})},alCambiarEstadoDato(){}};
 vm.createContext(ctx);vm.runInContext(code+'\nthis.ui={estadoDatoCambiado487,marcarGuardado,estadoGuardado487,detalleLecturas487};',ctx);
 return {ctx,nodes,created,header,badge,detail,pintura,ui:ctx.ui};}
const route='modulo/crm/crm',info={hora:Date.parse('2026-10-03T08:00:00Z'),ultimoIntento:Date.parse('2026-10-04T08:00:00Z'),falloActualizacion:'mensaje privado no publicable'};
let n=0;function test(name,fn){fn();n++;console.log('PASS',name);}
test('fallo crea banda hermana fuera cabecera una vez, texto neutral accesible',()=>{
 const e=setup();e.ui.estadoDatoCambiado487(route,info);const b=e.nodes['lectura-fallo-489'];assert.equal(e.created.length,1);assert.equal(b.role,'status');assert.equal(b.attrs['aria-live'],'polite');assert.equal(b.hidden,false);
 assert.match(b.textContent,/0?3\/10, 10:00 · actualización sin confirmar/);assert.doesNotMatch(b.textContent,/privado|modulo|crm|verde/);assert.match(b.title,/no es la fecha de observación/);assert.equal(e.header.children.length,0);
 e.ui.estadoDatoCambiado487(route,info);assert.equal(e.created.length,1);
});
test('sin fallo no añade banda ni espacio; éxito y304 retiran banda existente',()=>{
 const e=setup();e.ui.estadoDatoCambiado487(route,{hora:info.hora});assert.equal(e.created.length,0);
 e.ui.estadoDatoCambiado487(route,info);e.ui.estadoDatoCambiado487(route,{hora:info.hora,falloActualizacion:null});assert.equal(e.nodes['lectura-fallo-489'].hidden,true);assert.equal(e.nodes['lectura-fallo-489'].textContent,'');
});
test('denegación entrada y limpieza global de identidad eliminan texto',()=>{
 for(const clave of [route,null]){const e=setup();e.pintura.guardado={guardado:true,hora:info.hora,ruta:route};e.ui.estadoDatoCambiado487(route,info);
 e.ui.estadoDatoCambiado487(clave,null);assert.equal(e.nodes['lectura-fallo-489'].hidden,true);assert.equal(e.nodes['lectura-fallo-489'].textContent,'');assert.equal(e.detail.children.length,0);}
});
test('navegación real limpia y respuestas de otra ruta no publican',()=>{
 const e=setup();e.ui.estadoDatoCambiado487(route,info);
 const nav=app.slice(app.indexOf('  pintura.estadosLectura.clear();',app.indexOf('async function ruta(')),app.indexOf('  const vigente =',app.indexOf('async function ruta(')));
 vm.runInContext(nav,e.ctx);assert.equal(e.nodes['lectura-fallo-489'].hidden,true);e.pintura.usadas.clear();e.ui.estadoDatoCambiado487(route,info);assert.equal(e.nodes['lectura-fallo-489'].hidden,true);
});
test('timer real seis segundos no oculta fallo móvil',()=>{
 const e=setup();e.pintura.guardado={hora:info.hora};e.ui.estadoDatoCambiado487(route,info);let cb;
 e.ctx.setTimeout=f=>cb=f;e.ctx.vigente=()=>true;
 const timer=app.match(/else if \(pintura\.guardado\) setTimeout\(\(\) => \{.*\}, 6000\);/)[0];vm.runInContext('if(false){} '+timer,e.ctx);cb();assert.equal(e.nodes['lectura-fallo-489'].hidden,false);
});
test('varias fuentes muestran fecha más antigua y ocultar última elimina banda',()=>{
 const e=setup();e.pintura.usadas.add('modulo/seo/seo');e.ui.estadoDatoCambiado487(route,info);e.ui.estadoDatoCambiado487('modulo/seo/seo',{...info,hora:info.hora-86400000});assert.match(e.nodes['lectura-fallo-489'].textContent,/0?2\/10/);
 e.ui.estadoDatoCambiado487('modulo/seo/seo',null);assert.match(e.nodes['lectura-fallo-489'].textContent,/0?3\/10/);e.ui.estadoDatoCambiado487(route,null);assert.equal(e.nodes['lectura-fallo-489'].hidden,true);
});
test('CSS sólo móvil, ancho acotado, wrap sin modificar topbar ni fuente pequeña',()=>{
 const region=css.slice(css.indexOf('/* 489 ·'),css.indexOf('@media (max-width: 640px)',css.indexOf('/* 489 ·')));
 assert.match(region,/\.lectura-fallo-489 \{ display: none;/);assert.match(region,/@media \(max-width: 720px\)/);assert.match(region,/display: block/);assert.match(region,/max-width: 100%/);assert.match(region,/white-space: normal/);assert.match(region,/overflow-wrap: anywhere/);assert.doesNotMatch(region,/\.topbar|font-size:\s*\d/);
});
console.log(n+' grupos489 PASS');
