const fs=require('fs'),assert=require('assert/strict'),vm=require('vm');
const src=fs.readFileSync(__dirname+'/modulos/informe.js','utf8'),sem=fs.readFileSync(__dirname+'/modulos/_meta_informe_291.js','utf8').replace(/export /g,'');
const render=src.slice(src.indexOf('  meta(S) {'),src.indexOf('  // ------------------------------------------------------------- 8 · Correo')).replace('  meta(S) {','function pintarMeta291(S) {').replace(/},\s*$/,'}');
const b={Date,Number,Set,Math,document:{},h:(tag,a,...c)=>({tag,a,c}),tile:x=>x,tiles:x=>x,fNum:v=>v==null?'—':String(v),fEur:v=>v==null?'—':String(v),vacioLinea:t=>({texto:t}),lineas:x=>x,tablaGrande:x=>({titulo:x.titulo,columns:x.columnas.map(c=>c.titulo),rows:x.filas.map(r=>x.columnas.map(c=>c.celda(r)))}),bloque:(s,id,t,c)=>({id,t,c}),bloqueInterno:()=>null,sinFuente:()=>null,nm:String,fresco:()=>null,interno:x=>x,avisoParcial:x=>x,PILA:()=>({}),SUB:{},icono:()=>null};vm.createContext(b);vm.runInContext(sem+'\n'+render,b);let n=0;function test(f){f();n++}
const p={desde:'2026-09-01',hasta:'2026-09-30'},f={cuenta:{id:'act_1'},moneda:'EUR'},md={version:'220.1',fuente:'meta_insights',nivel:'account',periodo_valido:true,desde:p.desde,hasta:p.hasta,fecha_lectura:'2026-10-02 12:00',cohorte:'resultados_meta_sin_union_crm_ni_cualificacion_ro',campos_observados:['leads','gasto'],tipo_lead:'lead',cuenta_id:'1',moneda:'EUR'};
const a={leads:12,gasto:24,medicion:md},call=(x=a,fu=f,c={})=>b.metaInforme291(x,fu,p,'2026-10-03',c);
test(()=>{const r=call({leads:201,cpl:2,gasto:402});assert.equal(r.resultados,201);assert.equal(r.leads,null);assert.equal(r.cpl,null)});
test(()=>assert.equal(call({leads:0}).resultados,null));
test(()=>assert.equal(call().cpl,2));
for(const [k,v] of [['cuenta_id','other'],['nivel','ad'],['hasta','2026-09-29'],['tipo_lead','purchase'],['fecha_lectura','2026-10-04 12:00'],['fecha_lectura','2026-10-02 25:00']])test(()=>assert.equal(call({...a,medicion:{...md,[k]:v}}).leads,null));
test(()=>assert.equal(call({...a,medicion:{...md,moneda:'USD'}}).cpl,null));
test(()=>assert.equal(call(a,f,{tienda_online:true}).leads,null));
test(()=>assert.equal(call({...a,leads:1.5}).resultados,null));
test(()=>assert.equal(call({...a,leads:0}).leads,0));
test(()=>{const S={f:{meta:{actual:{leads:201,cpl:2,gasto:402},serie:[],conjuntos:[{leads:5,gasto:10,cpl:2}]},fuentes:{meta:f}},P:p,ctx:{hoy:'2026-10-03'},c:{},veInversion:true};const out=JSON.stringify(b.pintarMeta291(S));assert.match(out,/201/);assert.match(out,/Resultados Meta/);assert.match(out,/Sin dato acreditado/);assert.doesNotMatch(out,/Sin actividad|Sin campañas con actividad|"etiqueta":"Leads"|"valor":"2"/)});
test(()=>{const S={f:{meta:{actual:{leads:0,gasto:0,impresiones:0},serie:[],conjuntos:[]},fuentes:{meta:f}},P:p,ctx:{hoy:'2026-10-03'},c:{},veInversion:true};const out=JSON.stringify(b.pintarMeta291(S));assert.doesNotMatch(out,/Sin actividad|0 impresiones|0 leads|0 €|Sin campañas con actividad/);assert.match(out,/"valor":null/)});
const revisar=fs.readFileSync(__dirname+'/modulos/informe_revisar.js','utf8');const cifras=revisar.slice(revisar.indexOf('function cifras('),revisar.indexOf('\n}',revisar.indexOf('function cifras('))+2);Object.assign(b,{fmt:{num:String,eur:String},variacion:()=>0});vm.runInContext(cifras,b);
test(()=>{const out=JSON.stringify(b.cifras({hoy:'2026-10-03',ver:()=>({ok:true})},{id:'c'},{meta:{actual:{leads:201,cpl:2}},fuentes:{meta:f}},p));assert.match(out,/201/);assert.match(out,/Resultados Meta/);assert.doesNotMatch(out,/"valor":"2"|201 leads/)});
console.log(n+' pruebas291 JS PASS (helper, bloque Meta real y revisar real)');
