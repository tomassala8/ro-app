const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const path=require('path');
const c={Intl,Set,Map,Number,TypeError};vm.createContext(c);
vm.runInContext(fs.readFileSync(path.join(__dirname,'modulos/_control_artifact_250.js'),'utf8').replace(/export /g,''),c);
class N{
 constructor(tag,attrs={},...kids){this.tag=tag;this.attrs=attrs;this.children=[];this.events={};this.style={};this.isConnected=true;this.append(...kids);}
 append(...xs){for(const x of xs.flat(Infinity).filter(x=>x!=null)){this.children.push(x);if(x instanceof N)x.parent=this;}}
 remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);this.isConnected=false;}
 focus(){this.focused=true;}
 setAttribute(k,v){this.attrs[k]=String(v);}
 set className(v){this.attrs.class=v;}
 addEventListener(k,fn){this.events[k]=fn;}
}
// Constructor real de componentes: rechaza attrs.onclick; el primer falso h lo aceptaba.
c.Node=N;c.document={createElement:tag=>new N(tag),createTextNode:x=>String(x)};
const composants=fs.readFileSync(path.join(__dirname,'componentes.js'),'utf8');
const sourceH=composants.slice(composants.indexOf('export function h('),composants.indexOf("const svgNS ="));
vm.runInContext(sourceH.replace('export ',''),c);
const h=c.h,all=(n,p)=>[...(n instanceof N && p(n)?[n]:[]),...(n instanceof N?n.children.flatMap(x=>all(x,p)):[])];
const text=n=>n instanceof N?n.children.map(text).join(' '):String(n);
let total=0;const test=(name,fn)=>{fn();total++;};
const f=()=>[{id:'a',nombre:'Account A',clientes:4,celdas:{imputa:{valor:110.699999999,sub:'7 días observados',estado:'gris'},revisa:{valor:2,estado:'ambar',sub:'1/4 proyectos',detalle:'Copia parcial'}}},{id:'b',nombre:'Account B',clientes:0,celdas:{contacto:{valor:0,estado:'gris',sub:'declarados'}}}];
let r;
test('Diez columnas exactas y dos filas',()=>{r=c.pintarMapaControl250({h,filas:f()});assert.equal(all(r,x=>x.tag==='th').length,10);assert.equal(all(r,x=>x.tag==='tbody')[0].children.length,2);assert(all(r,x=>x.tag==='th').every(x=>x.attrs.scope==='col'));});
test('Referencia layout scoped y tactil',()=>{const css=text(all(r,x=>x.tag==='style')[0]);assert(css.includes('.ro-control-artifact250 .ctl250'));assert(css.includes('border-spacing:4px'));assert(css.includes('min-height:44px'));assert(css.includes('background:#fcebeb'));assert(!css.includes('font.googleapis'));});
test('Horas formateadas sin objetivo ficticio',()=>{const cells=all(r,x=>x.attrs.class?.startsWith('c250'));assert(text(cells[0]).includes('110,7'));assert(!text(cells[0]).includes('110.699'));assert(!text(cells[0]).includes('40'));});
test('Ausencia es guion gris Sin dato',()=>{const cells=all(r,x=>x.attrs.class?.startsWith('c250'));assert.equal(cells[2].attrs.class,'c250 gris');assert.equal(text(cells[2]),'—');assert(cells[2].attrs['aria-label'].includes('Sin dato'));assert(!text(cells[2]).includes('0'));});
test('Cero observado permanece gris',()=>{const cells=all(r,x=>x.attrs.class?.startsWith('c250'));assert.equal(cells[14].attrs.class,'c250 gris');assert(text(cells[14]).includes('0'));assert(!text(cells[14]).includes('declarados'));assert(cells[14].attrs['aria-label'].includes('declarados'));});
test('No verde automático ni desconocido contaminado',()=>{assert.equal(c.celdaControl250({valor:0,estado:'verde'}).estado,'gris');assert.equal(c.celdaControl250({valor:9,estado:'desconocido'}).valor,'—');for(const valor of [null,undefined,NaN,Infinity,-1,false])assert.equal(c.celdaControl250({valor}).valor,'—');});
test('Cifra backlog color sólo explicito',()=>{assert.equal(c.celdaControl250({valor:12}).estado,'gris');assert.equal(c.celdaControl250({valor:2,estado:'ambar'}).estado,'ambar');assert.equal(c.celdaControl250({valor:null,estado:'rojo'}).estado,'gris');});
test('No fusionar identidad ambigua',()=>{const a=f();a.push({...a[0]});const t=c.pintarMapaControl250({h,filas:a});assert.equal(all(t,x=>x.tag==='tbody')[0].children.length,1);assert(!text(all(t,x=>x.tag==='tbody')[0]).includes('Account A'));});
test('Teclado utiliza boton nativo, nombre accesible completo',()=>{const b=all(r,x=>x.attrs.class?.startsWith('c250'))[1];assert.equal(b.tag,'button');assert.equal(b.attrs.type,'button');assert(b.attrs['aria-label'].includes('Account A · Revisa · 2'));assert.equal(all(r,x=>x.attrs.class==='ctl250')[0].attrs.tabindex,'0');});
test('Seleccion y detalle caller sólo vigente y conectado',()=>{let vivo=true,selected=[],details=[];const t=c.pintarMapaControl250({h,filas:f(),vigente:()=>vivo,alSeleccionar:id=>selected.push(id),alDetalle:(row,k)=>details.push([row.id,k])});const bs=all(t,x=>x.tag==='button');bs[0].events.click();bs[2].events.click();assert.deepEqual(selected,['a']);assert.deepEqual(details,[['a','revisa']]);vivo=false;bs[0].events.click();bs[2].events.click();assert.equal(selected.length,1);assert.equal(details.length,1);vivo=true;t.isConnected=false;bs[0].events.click();assert.equal(selected.length,1);});
test('Detalle fallback abre foco y cierra devolviendo foco',()=>{const t=c.pintarMapaControl250({h,filas:f()});const boton=all(t,x=>x.attrs.class==='c250 ambar')[0];boton.events.click();const region=all(t,x=>x.attrs.class==='detalle250')[0];assert(region.focused);assert(text(region).includes('Copia parcial'));all(region,x=>x.tag==='button')[0].events.click();assert.equal(all(t,x=>x.attrs.class==='detalle250').length,0);assert(boton.focused);});
test('Datos como texto, sin HTML dinamico',()=>{const t=c.pintarMapaControl250({h,filas:[{id:'x',nombre:'<img onerror=alert(1)>',clientes:1,celdas:{}}]});assert(text(t).includes('<img onerror=alert(1)>'));assert.equal(all(t,x=>x.tag==='img').length,0);assert(!fs.readFileSync(path.join(__dirname,'modulos/_control_artifact_250.js'),'utf8').includes('innerHTML'));});
test('Sin filas ni columnas falsas y sin peticiones',()=>{const t=c.pintarMapaControl250({h,filas:[]});assert(text(t).includes('No hay accounts'));assert.equal(all(t,x=>x.tag==='table').length,0);const s=fs.readFileSync(path.join(__dirname,'modulos/_control_artifact_250.js'),'utf8');assert(!/\bfetch\s*\(|\.api\s*\(|\.accion\s*\(/.test(s));});
test('Override etiqueta no elimina columnas de referencia',()=>{const t=c.pintarMapaControl250({h,filas:f(),columnas:[{key:'imputa',titulo:'Horas observadas',sub:'28-sep–4-oct'},{key:'extranjera',titulo:'No incluir'}]});const th=all(t,x=>x.tag==='th');assert.equal(th.length,10);assert(text(th[1]).includes('Horas observadas'));assert(!text(t).includes('No incluir'));});
test('Montaje identidad obsoleta no pinta filas',()=>{const t=c.pintarMapaControl250({h,filas:f(),vigente:()=>false});assert.equal(all(t,x=>x.tag==='tbody').length,0);});
test('h real rechaza onclick y registra on click',()=>{const a=h('button',{onclick:()=>{throw Error('No debe ejecutarse');}});assert.equal(a.events.click,undefined);const b=h('button',{on:{click:()=>true}});assert.equal(b.events.click(),true);});
test('Verde exige cumplimiento explícito y valor conocido',()=>{assert.equal(c.celdaControl250({valor:0,estado:'verde'}).estado,'gris');assert.equal(c.celdaControl250({valor:0,estado:'verde',cumplimiento_confirmado:true}).estado,'verde');assert.equal(c.celdaControl250({valor:null,estado:'verde',cumplimiento_confirmado:true}).estado,'gris');});
console.log(`${total} grupos de pruebas250 PASS`);
