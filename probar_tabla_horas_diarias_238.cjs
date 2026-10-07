const fs=require('fs');
const base=fs.readFileSync(__dirname+'/probar_montaje_horas_182.cjs','utf8').split('const D=')[0];
new Function('require','__dirname',base+`
let n=0,tables=[];sandbox.tablaDensa=o=>{tables.push(o);return h('table',{},o.filas.map(r=>h('row',{},o.columnas.map(col=>col.celda?col.celda(r):r[col.clave]))));};
const days=['2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-02'];
const series={version:'238.1',fuente:'ClickUp entradas',fecha_fuente:'2026-10-03 02:56',cobertura:'parcial',zona:'Europe/Madrid',zona_confirmada:true,desde:days[0],hasta:days[4],dias:days.map((fecha,i)=>({fecha,horas:i===3?0:i===4?2:null,entradas:i>=3?1:null,estado:i>=3?'observado':'sin_dato'}))};
const persona={persona_id:'a',nombre:'Synthetic A',ayer:2,semana:2,meses:[{mes:'2026-10',imputadas:2,esperadas:8}],diario_238:series};
const doc={hoy:'2026-10-03',ayer:'2026-10-02',fuentes:{horas:{hora:'2026-10-03 02:56'}},personas:[persona,{persona_id:'b',nombre:'Unauthorized',diario_238:series}]};
const text=node=>typeof node==='string'?node:typeof node==='number'?String(node):(node?.children||[]).map(text).join(' ');
let live=true,opened=[];const ctx={vigente:()=>live};
let out=sandbox.panoramaHoras(ctx,[persona],'2026-10',doc,{alAbrir:id=>opened.push(id)});
assert.equal(tables.length,3);assert.equal(tables[0].columnas.length,10);assert.equal(tables[0].filas.length,1);assert(!text(out).includes('Unauthorized'));assert(text(out).includes('0 h'));assert(text(out).includes('—'));assert.equal(tables[1].columnas.find(c=>c.clave==='mes').titulo,'Mes 2026-10');n++;
tables[0].alPulsar(tables[0].filas[0]);assert.equal(opened[0],'a');live=false;tables[0].alPulsar(tables[0].filas[0]);assert.equal(opened.length,1);n++;
for(const change of [s=>s.version='legacy',s=>s.dias[0].horas=0,s=>s.dias[4].entradas=0,s=>s.dias[4].horas=NaN,s=>s.dias[4].fecha='2026-10-04',s=>s.zona='bad',s=>s.fecha_fuente='2026-10-04',s=>s.cobertura='completa']){
 const x=JSON.parse(JSON.stringify(persona));change(x.diario_238);assert.equal(sandbox.serieHorasDiaria238(x,'2026-10-03'),null);n++;
}
live=true;tables=[];const old={...persona};delete old.diario_238;
out=sandbox.panoramaHoras(ctx,[old],'2026-10',{...doc,personas:[old]});assert.equal(tables.length,3);assert(text(out).includes('El equipo, día a día'));n++;
assert.equal(sandbox.matrizHorasDiaria238([persona,persona],'2026-10-03'),null);n++;
console.log('238 UI '+n+' casos PASS: render panorama real, cinco fechas typed, cero observado/unknown, alcance, filtros legacy intactos y guardias.');
`)(require,__dirname);
