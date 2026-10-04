const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(__dirname+'/modulos/seo.js','utf8'),helper=fs.readFileSync(__dirname+'/modulos/_seo_mediciones.js','utf8').replace(/export /g,'');
const h=(tag,attrs,...kids)=>({tag,attrs,kids,append(...xs){this.kids.push(...xs);}});const tables=[];
const b={Date,Number,URL,h,delta:(bien,texto)=>({bien,texto}),num:String,numD:String,TOQUE:{},icono:()=>null,fmt:{plural:n=>String(n)},S:{1:1,2:2},PUNTO:{},pctTxt:String,variacion:()=>0,
 panel:(o,...kids)=>({...o,kids}),vacioLinea:t=>({text:t}),tablaDensa:o=>{tables.push(o);return o;},grafico:o=>o,fDiaRO:String};vm.createContext(b);vm.runInContext(helper+'\nglobalThis.posicionSEO=posicionSEO;',b);
Object.assign(b,vm.runInContext('(()=>{'+fs.readFileSync(__dirname+'/modulos/_objetivos_seo_374.js','utf8').replace(/export /g,'')+';return {cargarObjetivos374,celdaObjetivo374,renderObjetivos374};})()',b));
vm.runInContext(source.slice(source.indexOf('function posCh(n)'),source.indexOf('\nconst nom =')),b);
let n=0;
for(const v of [undefined,null,0,-1,false,'1',NaN,Infinity,0.5]){assert.equal(b.posicionSEO(v),null);assert.equal(b.posCh(v).kids[0],'Sin dato');assert.equal(b.cambioPosicionSEO(3,v),null);assert.equal(b.deltaPos(3,v).kids[0],'Sin comparación');n++;}
assert.equal(b.posicionSEO(1),1);assert.equal(b.posCh(1).kids[0],'1');assert.match(b.posCh(1).attrs.class,/gris/);assert.equal(b.cambioPosicionSEO(10,3),7);assert.equal(b.deltaPos(10,3).texto,'▲ 7');assert.equal(b.cambioPosicionSEO(3,10),-7);n++;
assert.equal(b.filasSeoAutorizadas([{cliente_id:'a'},{cliente_id:'b'},{cliente_id:'c'},{cliente_id:'d'}],[{id:'a',activo_confirmado:true},{id:'b',activo_confirmado:false},{id:'c'}]).length,1);assert.equal(b.filasSeoAutorizadas([{cliente_id:'a'}],[]).length,0);n++;
let motors=b.contextoMotoresSEO({seranking:{motores_contexto:[{region:'Ciudad confirmada',dispositivo:'desktop',dispositivo_estado:'confirmado',fecha_contexto:'2026-10-03 01:42',principal:true},{dispositivo:'desktop',dispositivo_estado:'sin_dato'}]}});assert.equal(motors[0].dispositivo,'desktop');assert.equal(motors[1].dispositivo,null);assert.equal(motors[1].region,null);assert.equal(b.contextoMotoresSEO({}).length,0);n++;
const f={gsc_estado:'bien',gsc:{serie:[],busquedas:[],paginas:[['https://example.test/a',5,20,7,15],['https://example.test/b',0,8,15,0],['javascript:alert(1)',null,3,0,4]]},clics:{ventanas:{mes:['2026-09-01','2026-09-28'],mes_ant:['2026-08-04','2026-08-31']}}},meta={gsc:{leido:'2026-10-03 01:00'}};
let p=b.paginasSEO(f,meta,'2026-10-03');assert.equal(p.filas[0].perdidos,10);assert.match(p.filas[0].accion,/consultas/);assert.equal(p.filas[1].clics,0);assert.match(p.filas[1].accion,/sin clics/);assert.equal(p.filas[2].enlace,null);assert.equal(p.filas[2].clics,null);assert.equal(p.filas[2].posicion,null);n++;
p=b.paginasSEO({...f,clics:null},meta,'2026-10-03');assert.equal(p.filas[0].anterior,null);assert.equal(p.filas[0].perdidos,null);assert.match(p.filas[0].accion,/Confirmar ventana/);n++;
for(const date of ['2026-02-30','2026-10-04','2026-10-03 25:12',null]){assert.equal(b.paginasSEO(f,{gsc:{leido:date}},'2026-10-03').filas.length,0);n++;}
assert.equal(b.paginasSEO({...f,gsc:{...f.gsc,error:'fixture'}},meta,'2026-10-03').filas.length,0);assert.equal(b.paginasSEO({...f,gsc_estado:'sin_conectar'},meta,'2026-10-03').filas.length,0);n++;
// Ejecuta el renderizador anidado real de páginas; no copia una implementación de prueba.
const clics=source.slice(source.indexOf('  const pintarClics = z => {'),source.indexOf('  const pintarWeb = z => {')).replace('  const pintarClics = z => {','function pintarClics(z) {').replace(/};\s*$/,'}');
Object.assign(b,{f,d:{seo:{_meta:meta}},ctx:{hoy:'2026-10-03'}});vm.runInContext(clics,b);const nodes=[];b.pintarClics({append:x=>nodes.push(x)});const page=tables.find(t=>t.columnas.some(c=>c.clave==='accion'));assert.ok(page);assert.equal(page.filas[0].cl,5);assert.equal(page.filas[1].cl,0);const cell=page.columnas.find(c=>c.clave==='u').celda(page.filas.find(x=>!x.enlace));assert.equal(cell.tag,'span');assert.match(JSON.stringify(nodes),/muestra parcial/);assert.doesNotMatch(JSON.stringify(nodes),/Sin búsquedas con clics/);n++;
// Renderizador real posiciones: Maps independiente; movimientos con ausencia no inventan subida/caída.
const posiciones=source.slice(source.indexOf('  const pintarPosiciones = z => {'),source.indexOf('  const pintarClics = z => {')).replace('  const pintarPosiciones = z => {','function pintarPosiciones(z) {').replace(/};\s*$/,'}');
b.f={cliente_id:'a',seranking:{ultima:'2026-10-03'},informe15:[{k:'consulta sintética',hoy:null,mapa:2,sem:3,mes:null,vol:0}],alertas:[],movimientos:{suben:[{k:'ausente',antes:null,hoy:2}],bajan:[{k:'ausente',antes:3,hoy:null}]}};b.d={seo:{_meta:{}}};b.dos=(...kids)=>kids;vm.runInContext(posiciones,b);const posNodes=[];b.pintarPosiciones({append:(...x)=>posNodes.push(...x)});const tablaPos=tables.find(t=>t.columnas.some(c=>c.clave==='mapa'));assert.ok(tablaPos);assert.equal(tablaPos.columnas.find(c=>c.clave==='mapa').celda(tablaPos.filas[0]).kids[0],'2');assert.equal(tablaPos.columnas.find(c=>c.clave==='d').celda(tablaPos.filas[0]).kids[0],'Sin comparación');assert.match(JSON.stringify(posNodes),/Dispositivo y localidad sin metadatos/);assert.match(JSON.stringify(posNodes),/0 filas comparables/);assert.doesNotMatch(JSON.stringify(posNodes),/>100/);n++;
// Detalle completo real con reparto nuevo nullable; constructores UI simulados, ninguna acción ejecutada.
const detalleSource=source.slice(source.indexOf('function pintarDetalle('),source.indexOf('/** Barrido v1:'));
const tarjetas=[];
const fixture={cliente_id:'a',cliente:'Fixture',estado:'gris',motivo:'Lectura parcial',alertas:[],informe15:[],movimientos:null,seranking:null,top10_15:null,reparto:{top3:{hoy:5,mes:null},top5:{hoy:5,mes:null},top10:{hoy:5,mes:null},fuera:{hoy:null,mes:null}}};
const detailBox={...b,conteoSEO:v=>vm.runInContext('conteoSEO',b)(v),nom:()=>null,TXT_EST:{gris:'Sin dato'},ctx:{},
 selectorCliente:()=>h('selector'),chipEstado:()=>h('chip'),logoCliente:()=>h('logo'),iniciales:()=>'',lineaDatoSR:()=>null,
 tile:o=>{tarjetas.push(o);return {...o,classList:{contains:()=>true},querySelector:()=>({textContent:o.valor===null?'—':String(o.valor)})};},
 rejillaTarjetas:x=>({tarjetas:x}),botonConfirmar:()=>h('button'),botonDeshacer:()=>h('button'),
 ventanas:x=>({ventanas:x}),pestanas:o=>{const z={append:(...x)=>detailNodes.push(...x)};o.pintar('pos',z);return h('pestanas');}};
const detailNodes=[];vm.createContext(detailBox);vm.runInContext(detalleSource,detailBox);
detailBox.pintarDetalle({append:(...x)=>detailNodes.push(...x)},{titulo:()=>{},clientes:[{id:'a',activo_confirmado:true}],persona:{id:'fixture'},soloLectura:true},{seo:{clientes:[fixture],_meta:{gsc:{}}},webs:{webs:[]}},'a');
const topTile=tarjetas.find(t=>t.etiqueta==='Palabras en el top 5');assert.equal(topTile.valor,'5');assert.equal(topTile.comparacion,null);assert.match(topTile.contexto,/Top 10 sin dato/);assert.doesNotMatch(topTile.contexto,/0 de 15/);assert.match(JSON.stringify(detailNodes),/hace 30 días: Sin dato/);n++;
//332: constructor real de detalle usa segundo parámetro como pestaña existente.
let activa332;detailBox.pestanas=o=>{activa332=o.activa;return h('pestanas');};
for(const [param,expected] of [['clics','clics'],['unknown','pos']]){detailBox.pintarDetalle({append:()=>{}},{titulo:()=>{},clientes:[{id:'a',activo_confirmado:true}],persona:{id:'fixture'},params:['a',param],soloLectura:true},{seo:{clientes:[fixture],_meta:{gsc:{}}},webs:{webs:[]}},'a');assert.equal(activa332,expected);n++;}
// Agregación real portada: ausencia total no se convierte en cero; comparación misma muestra.
const aggregate=source.slice(source.indexOf('  const cohorteClics='),source.indexOf('  const websRojo ='))+'\n({sumSem,sumAnt,top5h,top5m})';
const calcular=base=>{const box={...b,base,metaS:meta,ctx:{hoy:'2026-10-03'}};vm.createContext(box);vm.runInContext(helper,box);return vm.runInContext(aggregate,box);};
let a=calcular([]);assert.equal(a.sumSem,null);assert.equal(a.top5h,null);n++;
a=calcular([{...f,alertas:[],clics:{...f.clics,semana:0,semana_ant:0},reparto:{top5:{hoy:0,mes:0}}}]);assert.equal(a.sumSem,null);assert.equal(a.sumAnt,null);assert.equal(a.top5h,0);n++;
a=calcular([{...f,alertas:[],clics:{...f.clics,semana:4}},{alertas:[],clics:{semana_ant:20}}]);assert.equal(a.sumSem,null);assert.equal(a.sumAnt,null);assert.equal(a.top5m,null);n++;
a=calcular([{...f,cliente_id:'a',alertas:[],clics:{semana:0,semana_ant:0,hasta:'2026-09-30',ventanas:{semana:['2026-09-24','2026-09-30'],semana_ant:['2026-09-17','2026-09-23']}}}]);assert.equal(a.sumSem,0);assert.equal(a.sumAnt,0);n++;
// Loader real: intersections antes de generar la tabla; no autoriza la fuente de webs globales.
vm.runInContext(source.slice(source.indexOf('async function cargar(ctx)'),source.indexOf('// =================================================================== portada')),b);
b.nom=()=>null;b.cargarTablero=async()=>null;b.revisadas=async()=>new Map();
(async()=>{const r=await b.cargar({clientesVisibles:[{id:'a',activo_confirmado:true}],datosModulo:async k=>k==='seo/seo'?{clientes:[{cliente_id:'a'},{cliente_id:'b'}]}:k==='seo/webs'?{webs:[]}:{_meta:{estado:'sin_conectar'},webs:[]}});assert.equal(r.seo.clientes.length,1);assert.equal(r.seo.clientes[0].cliente_id,'a');n++;console.log(n+' grupos SEO162 pasan: helper, celdas, páginas y loader reales; sin red ni datos reales.');})().catch(e=>{console.error(e);process.exitCode=1});
