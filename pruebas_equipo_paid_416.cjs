const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class N{constructor(tag,attrs={},kids=[]){this.tag=tag;this.attrs=attrs;this.style=attrs.style||{};this.children=[];this.append(...kids)}append(...xs){this.children.push(...xs.flat(Infinity).filter(x=>x!=null))}setAttribute(k,v){this.attrs[k]=v}get textContent(){return this.children.map(x=>x instanceof N?x.textContent:String(x)).join(' ')}desc(){return this.children.filter(x=>x instanceof N).flatMap(x=>[x,...x.desc()])}}
const h=(t,a,...xs)=>new N(t,a,xs),s=fs.readFileSync(__dirname+'/modulos/captacion.js','utf8');
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
const rows=Array.from({length:7},(_,i)=>({cliente_id:'c'+i,nombre:'Cliente '+i,equipo:{trafficker:i<6?'persona-a':'persona-b'},meta_activa:true,gravedad:i<6?'critico':'atencion',dinero:i<6,gasto:{'7d':10,mes_anterior:20,ayer:3},cpl_resumen:{ref:i<6?12:null},objetivo:{cargado:i===0},leads:{'7d':2},anuncios:{cansadas:i===0?1:0,problemas_total:i===1?1:0},nicho:'Sector fixture'}));
const d={parametros:{rojos_trafficker:[2,4],techo_cpl:15},carteras_publicidad:{'persona-a':{cartera:6,apoyo:1,con_meta:6,meta_encendida:6}},datos_hasta:'2026-10-03'},ctx={navegar:r=>navigated.push(r)};
const out=h('main',{});env.pEquipo(out,ctx,d,rows);
assert.equal(tables[0].columnas.length,8);assert.deepEqual(Array.from(tables[0].filas,x=>[x.id,x.rojos,x.atencion,x.gasto7,x.gastoMes,x.techoTxt,x.cansadas,x.rechazados,x.objetivos]),[['persona-a',6,0,60,120,'6 de 6',1,1,'1 de 6'],['persona-b',0,1,null,null,'—',0,0,'0 de 1']]);
const primary=out.children[0];assert.equal(primary.attrs['data-paid-equipo'],'416');assert(primary.desc().some(n=>n.tag==='table'));assert(!primary.desc().some(n=>Object.hasOwn(n.attrs,'data-tiles')));
const folds=out.desc().filter(n=>n.tag==='details');assert.equal(folds.length,3);assert(folds.every(n=>!n.attrs.open));assert(folds.every(n=>n.children[0].style.minHeight==='44px'));assert(folds[0].textContent.includes('Cifras'));assert(folds[1].textContent.includes('Comparativa'));assert(folds[2].textContent.includes('Auditoría'));
assert.equal(tiles.length,4);assert.equal(tiles[0].estado,'rojo');assert.equal(tiles[0].valor,1);assert.equal(tiles[1].valor,'120€');assert.equal(tiles[1].comparacion.texto,'60€ en los últimos 7 días');assert.equal(audits,1);
const reserved=tables[0].columnas.find(x=>x.clave==='gasto7').celda(tables[0].filas[1]);assert.equal(reserved.textContent,'—');assert(!reserved.textContent.includes('€'));assert(out.textContent.includes('no objetivo'));assert(out.textContent.includes('min-width:940px'));assert(out.textContent.includes('font-size:13px'));assert(out.textContent.includes('5px 6px'));
tables[0].alPulsar(tables[0].filas[0]);assert.deepEqual(navigated,['captacion/~trafficker/persona-a']);assert.deepEqual(JSON.parse(storage[0][1]),{trafficker:'persona-a'});
const fresh=JSON.stringify(rows);tables=[];tiles=[];const none=h('main',{});env.pEquipo(none,ctx,d,[]);assert.equal(tables[0].filas.length,0);assert.equal(JSON.stringify(rows),fresh);
console.log('8 grupos416 PASS · pEquipo+cifras reales: orden/8cols/cartera/cifras/colores/reservado/acciones conservados y secundarios cerrados.');
