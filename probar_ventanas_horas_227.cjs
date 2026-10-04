const fs=require('node:fs'),assert=require('node:assert/strict');
const base=fs.readFileSync(__dirname+'/probar_montaje_horas_182.cjs','utf8').split('const D=')[0];
new Function('require','__dirname',base+`
let casos=0;let tablas=[];let heading;
sandbox.tablaDensa=o=>{tablas.push(o);return h('table')};sandbox.panel=(o,...xs)=>{heading=o;return h('panel',{},...xs)};
const d={hoy:'2026-10-03',ayer:'2026-10-02',generado:'2026-10-03 02:56',personas:[{persona_id:'a',nombre:'Fixture',ayer_fecha:'2026-10-01',ayer:0,semana:2,meses:[{mes:'2026-09',imputadas:7}]}]};
sandbox.panoramaHoras({vigente:()=>true},[{persona_id:'a'}],'2026-09',d);
assert.equal(tablas[1].filas[0].dia,0);assert.equal(tablas[1].filas[0].dia_fecha,'2026-10-01');assert.equal(tablas[1].filas[0].mes,7);assert.equal(tablas[1].filas[0].disponibilidad,null);casos++;
assert.equal(tablas[1].columnas.find(c=>c.clave==='dia').titulo,'Último día de la copia');assert.equal(tablas[1].columnas.find(c=>c.clave==='semana').titulo,'Semana de la copia');assert.equal(tablas[1].columnas.find(c=>c.clave==='mes').titulo,'Mes 2026-09');assert(heading.sub.includes('personas autorizadas'));assert(sandbox.ventanasHoras227(d,'2026-09').detalle.includes('no cambia las otras dos ventanas'));casos++;
const day=tablas[1].columnas.find(c=>c.clave==='dia').celda(tablas[1].filas[0]);assert(day.children.some(x=>x?.children?.includes('2026-10-01')));casos++;
let row=sandbox.resumenHorasPersona({...d.personas[0],ayer_fecha:'2026-02-31'},'2026-09',d);assert.equal(row.dia_fecha,null);assert.equal(row.dia,0);casos++;
row=sandbox.resumenHorasPersona({...d.personas[0],ayer:null,semana:null},'2026-09',d);assert.equal(row.dia,null);assert.equal(row.semana,null);casos++;
row=sandbox.resumenHorasPersona({...d.personas[0],meses:[{mes:'2026-09',imputadas:2},{mes:'2026-09',imputadas:3}]},'2026-09',d);assert.equal(row.mes,null);casos++;
assert.equal(sandbox.fechaControl227('2026-02-30'),null);assert.equal(sandbox.ventanasHoras227({hoy:'no-fecha',ayer:'no-fecha'},'2026-13').mes_titulo,'Mes sin confirmar');assert.equal(sandbox.ventanasHoras227({},'2026-09').corte,null);casos++;
// Cambiar mes no mueve las medidas día/semana, ni suma una ventana no relacionada.
row=sandbox.resumenHorasPersona(d.personas[0],'2026-10',d);assert.equal(row.mes,null);assert.equal(row.dia,0);assert.equal(row.semana,2);casos++;
// Render real con un único mes: antes mes por defecto undefined, ahora conserva copia disponible.
(async()=>{const only={...d,meses:['2026-09'],personas:[d.personas[0],{...d.personas[0],persona_id:'b'}],raras:[]};const root=h('main');const ctx={persona:{id:'a',puestos:['operaciones']},real:{id:'a'},datos:{personas:[]},soloLectura:false,servidor:false,params:[],ver:()=>({ok:true}),vigente:()=>true,titulo(){},indicador:()=>null,datosModulo:async()=>only};tablas=[];await sandbox.modulo.render(root,ctx);assert.equal(tablas[1].columnas.find(c=>c.clave==='mes').titulo,'Mes 2026-09');assert(tablas[1].filas.every(r=>r.mes===7));casos++;console.log(casos+' pruebas227 Horas real PASS: fechas individuales/corte global/mes distinto, unknown, no suma ventanas y único mes.');})().catch(e=>{console.error(e);process.exitCode=1});
`)(require,__dirname);
