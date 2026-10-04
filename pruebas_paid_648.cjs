const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class N{constructor(tag,attrs={},kids=[]){this.tag=tag;this.attrs=attrs;this.style=attrs.style||{};this.children=[];this.append(...kids)}append(...xs){this.children.push(...xs.flat(Infinity).filter(x=>x!=null))}setAttribute(k,v){this.attrs[k]=v}get textContent(){return this.children.map(x=>x instanceof N?x.textContent:String(x)).join(' ')}desc(){return this.children.filter(x=>x instanceof N).flatMap(x=>[x,...x.desc()])}}
const h=(t,a,...xs)=>new N(t,a,xs),s=fs.readFileSync(__dirname+(process.argv.includes('--antes')?'/fixtures/captacion_648_baseline.js':'/modulos/captacion.js'),'utf8');
let tables=[],tiles=[],audits=0,navigated=[],storage=[];
const env={h,S:{1:'4px',2:'8px',3:'12px',4:'16px'},NOWRAP:{whiteSpace:'nowrap'},esTienda:c=>!!c.tienda_online,nombre:(_,id)=>id,num:x=>String(x),eur:x=>x==null?'—':x+'€',iniciales:x=>x.slice(0,1),icono:()=>null,fuenteDe:()=>null,candado:()=>h('span',{'data-reservado':''},'—'),chipEstado:(e,t)=>h('span',{'data-estado':e},t),fmt:{plural:(n,t)=>n+' '+t},
 tile:o=>{tiles.push(o);return h('article',{'data-tile':o.etiqueta},o.etiqueta,o.valor,o.contexto)},tiles:xs=>h('div',{'data-tiles':''},xs),
 panel:(o,...xs)=>h('section',{'data-panel':o.titulo},h('h2',{},o.titulo),o.sub,...xs),
 tablaApilable:o=>{tables.push(o);return h('table',{},h('thead',{},o.columnas.map(c=>h('th',{},c.titulo))),h('tbody',{},o.filas.map(x=>h('tr',{},o.columnas.map(c=>h('td',{},c.celda?c.celda(x):x[c.clave]))))))},
 pAuditoria:()=>{audits++;return h('section',{'data-auditoria':''},'Auditoría existente')},sessionStorage:{setItem:(k,v)=>storage.push([k,v])}};
vm.createContext(env);
vm.runInContext(s.slice(s.indexOf('function plegablePaid411('),s.indexOf('function cabeceraPaid411(')),env);
vm.runInContext(s.slice(s.indexOf('function cifras('),s.indexOf('// ================================================================== LISTA')),env);
vm.runInContext(s.slice(s.indexOf('function pEquipo('),s.indexOf('/** Auditoría semanal:')),env);

vm.runInContext(s.slice(s.indexOf('function tAnuncios('),s.indexOf('function tMetas(')),env);
env.vacio=o=>h('div',{},o.titulo,o.texto);env.listaConIcono=xs=>h('ul',{},xs.map(x=>h('li',{},x.texto)));env.fDiaRO=x=>x;env.distingue=()=>'';
const d={parametros:{rojos_trafficker:[2,4],techo_cpl:15},datos_hasta:'2026-10-03'},ctx={soloLectura:true,nivel:'resumen',navegar:()=>{}};
const account=patch=>({cliente_id:'c',nombre:'Fixture',equipo:{trafficker:'t'},meta_activa:true,dinero:false,...patch});
const eq=rows=>{tiles=[];tables=[];const out=h('main',{});env.pEquipo(out,ctx,d,rows);return tiles;};
const tileBy=(ts,label)=>ts.find(x=>x.etiqueta===label);
let checks=0,fallosAntes=0;const check=f=>{try{f();checks++;}catch(e){if(!process.argv.includes('--antes'))throw e;fallosAntes++;}};
for(const bad of [undefined,null,'critico',NaN]){
 check(()=>{const t=eq([account({gravedad:bad==='critico'?'not-a-state':bad})])[0];assert.equal(t.valor,null);assert.equal(t.estado,'gris');assert.equal(t.medible,'medias');});
}
check(()=>{const t=eq([account({gravedad:'bien'})])[0];assert.equal(t.valor,0);assert.equal(t.estado,'gris');assert(t.contexto.includes('no exhaustiva'));});
check(()=>{const t=eq(Array.from({length:5},(_,i)=>account({cliente_id:'c'+i,gravedad:'critico'})))[0];assert.equal(t.valor,1);assert.equal(t.estado,'rojo');assert(t.contexto.includes('Señales observadas'));});
check(()=>{const t=eq([account({gravedad:'bien'}),account({cliente_id:'unknown'})])[0];assert.equal(t.estado,'gris');assert.equal(t.valor,0);assert(t.contexto.includes('1 de 2'));});
for(const value of [undefined,null,'0',NaN,-1,Infinity])check(()=>{const t=tileBy(eq([account({gasto:{ayer:value}})]),'Señales de cuentas paradas');assert(t);assert.equal(t.valor,null);assert.equal(t.estado,'gris');});
check(()=>{const t=tileBy(eq([account({gasto:{ayer:5}})]),'Señales de cuentas paradas');assert.equal(t.valor,0);assert.equal(t.estado,'gris');});
check(()=>{const t=tileBy(eq([account({gasto:{ayer:0}})]),'Señales de cuentas paradas');assert.equal(t.valor,1);assert.equal(t.estado,'rojo');assert(t.contexto.includes('por contrastar'));});
check(()=>{const t=tileBy(eq([account({cuenta_meta:{ultimo_dia_con_gasto:'2026-02-30'}})]),'Señales de cuentas paradas');assert.equal(t.valor,null);});
check(()=>{const t=tileBy(eq([account({cuenta_meta:{ultimo_dia_con_gasto:'2026-10-04'}})]),'Señales de cuentas paradas');assert.equal(t.valor,null);});
check(()=>{const t=tileBy(eq([account({gasto:{ayer:0}}),account({cliente_id:'unknown'})]),'Señales de cuentas paradas');assert.equal(t.valor,1);assert(t.unidad.includes('1 de 2'));assert.equal(t.medible,'medias');});
function ads(value){tiles=[];tables=[];const out=h('main',{});env.tAnuncios(out,ctx,d,account({anuncios:{cansadas:value,vigilar:value,problemas_total:value,ganadoras:0,total_7d:0,sin_autor:0,anuncios:[]}}));return tiles.filter(t=>['Cansadas','Con una señal','Rechazados o con problemas'].includes(t.etiqueta));}
for(const value of [undefined,null,'0',NaN,-1,Infinity,{},false])check(()=>{const ts=ads(value);assert.equal(ts.length,3);for(const t of ts){assert.equal(t.valor,null);assert.equal(t.estado,'gris');assert.equal(t.medible,'medias');}});
check(()=>{for(const t of ads(0)){assert.equal(t.valor,0);assert.equal(t.estado,'gris');assert(t.contexto.includes('no exhaustiva'));}});
check(()=>{const ts=ads(2);assert.deepEqual(ts.map(t=>t.estado),['rojo','ambar','rojo']);for(const t of ts){assert.equal(t.valor,2);assert.equal(t.medible,'medias');}});
check(()=>{const c=account({anuncios:{cansadas:1,vigilar:0,problemas_total:null,anuncios:[],cobertura:{completa:false}}});tiles=[];env.tAnuncios(h('main',{}),ctx,d,c);assert.equal(tiles[0].estado,'rojo');assert.equal(tiles[1].estado,'gris');assert.equal(tiles[3].valor,null);});
if(process.argv.includes('--antes')){assert(fallosAntes>=3);console.log('Baseline: '+fallosAntes+' escenarios reproducen los defectos; no es un FIX PASS.');process.exit(1);}
console.log(checks+' grupos648 PASS · funciones reales pEquipo/tAnuncios, missing/zero/positivo/parcial sin cumplimiento inventado.');
