// Render del módulo actual con datos sintéticos: ningún proveedor ni fichero de horas real.
const fs=require('fs');
const base=fs.readFileSync(__dirname+'/probar_montaje_horas_182.cjs','utf8').split('const D=')[0];
new Function('require','__dirname',base+`
function buscar(n,p){let out=[];if(n&&typeof n==='object'){if(p(n))out.push(n);for(const x of n.children||[])out.push(...buscar(x,p));}return out;}
const texto=n=>typeof n==='string'?n:typeof n==='number'?String(n):n?.children?.map(texto).join(' ')||'';
Object.defineProperty(El.prototype,'textContent',{get(){return texto(this)},set(v){this.replaceChildren(v)}});
const capturas={tiles:[],barras:[],tablas:[]};let casos=0;
Object.assign(sandbox,{estadoTexto:(e,t)=>h('span',{estado:e},t),fmt:{num:String,pct:x=>String(x)+' %'},tile:o=>{capturas.tiles.push(o);return h('tile',{config:o},o.etiqueta,o.valor,o.unidad,o.contexto,o.medibleDetalle)},tiles:x=>h('tiles',{},x),
 chipEstado:(estado,t)=>h('chip',{estado},t),barras:o=>{capturas.barras.push(o);return h('chart',{},o.titulo)},barraMini:()=>h('barra'),dosColumnas:(...xs)=>h('dos',{},xs),selectorPersona:()=>h('selector'),tablaDensa:o=>{capturas.tablas.push(o);return h('table',{},o.columnas.map(col=>col.titulo),o.filas.map(r=>h('tr',{},o.columnas.map(col=>typeof col.celda==='function'?col.celda(r):r[col.clave]))))}});
const mes=(extra={})=>({mes:'2026-09',nombre_mes:'septiembre',imputadas:5,esperadas:128,pct:4,dias_sin_imputar:3,fechas_sin_imputar:['2026-09-01'],dias_lab:22,tipos:[],tareas:1,desvio:false,...extra});
async function pintar(extra={}){
 capturas.tiles=[];capturas.barras=[];
 const D={ayer:'2026-10-02',hoy:'2026-10-03',meses:['2026-09','2026-10'],raras:[],fuentes:{horas:{hora:'2026-10-03 02:56'}},personas:[{persona_id:'persona_fixture',nombre:'Persona fixture',equipo:'Accounts',grupo:'Accounts',ayer:0,semana:12,dias_lab_semana:5,meses:[mes(extra),mes({mes:'2026-10',nombre_mes:'octubre',imputadas:0,esperadas:16,pct:0})]}]};
 const cont=h('main'),ctx={persona:{id:'persona_fixture',puestos:['account']},real:{id:'persona_fixture'},datos:{personas:[]},soloLectura:true,servidor:false,hoy:D.hoy,params:[],ver:()=>({ok:false}),vigente:()=>true,titulo(){},datosModulo:async()=>D};
 await sandbox.modulo.render(cont,ctx);return cont;
}
(async()=>{
 let root=await pintar();let get=s=>capturas.tiles.find(t=>t.etiqueta.startsWith(s));
 assert.equal(get('Imputadas').valor,'5');assert.equal(get('Imputadas').estado,'gris');assert.equal(get('Imputadas').comparacion,null);assert(!get('Imputadas').unidad.includes('128'));assert(!texto(root).includes('objetivo 90'));casos++;
 assert.equal(get('Esta semana').valor,'12');assert.equal(get('Esta semana').estado,'gris');assert(!get('Esta semana').unidad.includes('40'));assert(get('Esta semana').contexto.includes('por confirmar'));casos++;
 assert.equal(get('Ayer').valor,'0');assert.equal(get('Ayer').estado,'gris');assert.notEqual(get('Ayer').valor,'Sin registro');casos++;
 assert.equal(get('Fechas candidatas').valor,3);assert.equal(get('Fechas candidatas').estado,'gris');assert(texto(root).includes('Fechas a contrastar'));assert(!texto(root).includes('Días sin imputar'));casos++;
 assert(texto(root).includes('No hay desglose por tipo de tarea disponible'));assert(!texto(root).includes('no hay registros de tiempo en ClickUp'));casos++;
 const chart=capturas.barras[0];assert.equal(chart.puntos[0].valor,5);assert.equal(chart.puntos[0].ref,128);assert(chart.puntos.every(p=>p.estado==='gris'));assert(texto(root).includes('ausencias no registradas como cero'));assert(texto(root).includes('no es jornada ni capacidad confirmada'));casos++;
 assert.equal(get('Imputadas').frescura.fecha,'2026-10-03 02:56');casos++;
 root=await pintar({dias_sin_imputar:0,fechas_sin_imputar:[]});assert.equal(get('Fechas candidatas').valor,0);assert.equal(get('Fechas candidatas').estado,'gris');casos++;
 for(const missing of [null,undefined,-1,Infinity,'0',false]){root=await pintar({imputadas:missing,esperadas:missing,pct:null});assert.equal(get('Imputadas').valor,null);assert.equal(capturas.barras[0].puntos[0].valor,null);assert.equal(capturas.barras[0].puntos[0].ref,null);casos++;}
 root=await pintar({imputadas:0,pct:0});assert.equal(get('Imputadas').valor,'0');assert.equal(get('Imputadas').estado,'gris');casos++;
 root=await pintar({antes_de_imputar:true});assert.equal(get('Imputadas').valor,null);assert.equal(capturas.barras[0].puntos[0].valor,null);casos++;
 root=await pintar({horas_por_tarea:10,mediana_propia:3,desvio:true,desvio_pct:233});const hitos=get('Hitos de tareas');assert.equal(hitos.estado,'gris');assert.equal(hitos.comparacion.delta,undefined);assert(hitos.comparacion.texto.includes('233'));assert(texto(root).includes('Diferencia histórica observada'));assert(texto(root).includes('h por hito'));assert(!texto(root).includes('tarea resuelta'));assert(!texto(root).includes('tareas resueltas'));assert(!texto(root).includes('Productividad frente a sí misma'));casos++;
 const compFuente=fs.readFileSync(__dirname+'/componentes.js','utf8');const tileBody=compFuente.slice(compFuente.indexOf('export function tile(o)'),compFuente.indexOf('/** tiles([...])'));const tileEnv={...sandbox,Node:El,limpiaTexto:x=>x,infoCompacta:()=>null};vm.createContext(tileEnv);vm.runInContext(tileBody.replace('export function','function'),tileEnv);const tileReal=tileEnv.tile(hitos);assert(!buscar(tileReal,n=>['Va a peor','Va a mejor'].includes(n.attrs?.title)).length);assert(texto(tileReal).includes('Diferencia observada: +233 %'));casos++;
 const barFuente=fs.readFileSync(__dirname+'/modulos/produccion_comun.js','utf8');const barBody=barFuente.slice(barFuente.indexOf('export function barras(o)'),barFuente.indexOf('/** cuentagotas'));let grafActual;const barsEnv={...sandbox,grafico:o=>{grafActual=o;return h('grafico')}};vm.createContext(barsEnv);vm.runInContext(barBody.replace('export function','function'),barsEnv);barsEnv.barras(capturas.barras[0]);assert.equal(grafActual.series[0].nombre,'Referencia estimada anterior');assert.equal(grafActual.barras.nombre,'Horas registradas en la copia');assert(!JSON.stringify(grafActual).includes('Esperadas'));casos++;
 for(const tabla of capturas.tablas.filter(t=>t.columnas.some(c=>c.clave==='desvio_pct'))){const col=tabla.columnas.find(c=>c.clave==='desvio_pct');const celda=col.celda({desvio_pct:233,desvio:true});assert.equal(celda.children[0],'+233 %');assert.equal(celda.attrs.estado,'gris');assert.equal(col.titulo,'Diferencia observada');}casos++;
 // Pestaña Equipo real: navegar desde Persona, sin ejecutar un cálculo replicado.
 async function equipo(override={},antes=false){
  capturas.tiles=[];capturas.barras=[];
  const D={hoy:'2026-10-03',ayer:'2026-10-02',meses:['2026-09','2026-10'],raras:[],fuentes:{horas:{hora:'2026-10-03 02:56'}},personas:['a','b'].map((id,i)=>({persona_id:id,nombre:'Fixture '+id,equipo:'Accounts',grupo:'Accounts',ayer:0,semana:0,dias_lab_semana:5,meses:[mes(i?{imputadas:7,esperadas:128,...override,antes_de_imputar:antes}:{}),mes({mes:'2026-10',nombre_mes:'octubre',imputadas:0,esperadas:16,pct:0})]}))};
  const cont=h('main'),ctx={persona:{id:'a',puestos:['operaciones']},real:{id:'a'},datos:{personas:[]},servidor:false,soloLectura:true,hoy:D.hoy,params:['a'],ver:()=>({ok:true}),vigente:()=>true,titulo(){},datosModulo:async()=>D};
  await sandbox.modulo.render(cont,ctx);const tabs=buscar(cont,n=>n.tag==='tabs')[0];capturas.barras=[];tabs.elegir('equipo');return cont;
 }
 root=await equipo();assert.equal(capturas.barras.length,1);let eq=capturas.barras[0];assert.equal(eq.puntos[0].valor,12);assert.equal(eq.puntos[0].ref,256);assert(eq.puntos.every(p=>p.estado==='gris'));assert(!eq.titulo.includes('porcentaje'));assert(eq.formato(12).includes('h'));assert(texto(root).includes('No confirman jornada'));assert(!texto(root).includes('100 % de lo esperado'));casos++;
 for(const missing of [null,undefined,-1,Infinity,'0',false]){await equipo({imputadas:missing,esperadas:missing});eq=capturas.barras[0];assert.equal(eq.puntos[0].valor,null);assert.equal(eq.puntos[0].ref,null);assert.equal(eq.puntos[0].estado,'gris');casos++;}
 await equipo({imputadas:0,esperadas:0});eq=capturas.barras[0];assert.equal(eq.puntos[0].valor,5);assert.equal(eq.puntos[0].ref,128);assert.equal(eq.puntos[1].valor,0);assert.equal(eq.puntos[1].estado,'gris');casos++;
 await equipo({},true);eq=capturas.barras[0];assert.equal(eq.puntos[0].valor,5);assert.equal(eq.puntos[0].ref,128);casos++;
 // 161: revisar la salida del componente real de declaraciones, sin inferir cumplimiento.
 const hechos={h,Date,Intl,console};vm.createContext(hechos);vm.runInContext(fs.readFileSync(__dirname+'/modulos/evidencias_kpi.js','utf8').replace(/import[^;]+;\\s*/g,'').replace(/export function /g,'function '),hechos);
 const ctx={servidor:true,pilotoLectura:false,soloLectura:true,real:{id:'ops',puestos:['operaciones']},persona:{id:'ops',puestos:['operaciones']},clientes:[{id:'cli_fixture'}],ver:()=>({ok:true}),vigente:()=>true,nombre:()=> 'Actor fixture',api:async()=>({cliente_id:'cli_fixture',registros:[{id:'r_fixture',tipo:'contacto',fecha_madrid:'2026-10-02 10:00',canal:'telefono',motivo:'seguimiento',registrado_por:'actor',estado:'declarado',source_kind:'registro_equipo',verificacion_externa:false,cumplimiento:null}]})};
 const r=hechos.crearRegistroHechos(ctx,'cli_fixture');await r.cargar();assert(texto(r.nodo).includes('Declarado, sin comprobación externa'));assert(texto(r.nodo).includes('no certifican por sí solos el cumplimiento'));assert(!buscar(r.nodo,n=>n.attrs?.estado==='verde').length);casos++;
 ctx.api=async()=>({cliente_id:'cli_fixture',registros:[]});await r.cargar();assert(texto(r.nodo).includes('Esto no significa que no haya habido contactos o reuniones'));casos++;
 console.log(casos+' casos188 PASS: detalle real neutral, referencias históricas, unknown vs cero y declaraciones161 no cumplimiento.');
})().catch(e=>{console.error(e);process.exitCode=1});
`)(require,__dirname);
