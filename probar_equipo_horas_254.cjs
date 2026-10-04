const fs=require('fs');
const base=fs.readFileSync(__dirname+'/probar_montaje_horas_182.cjs','utf8').split('const D=')[0];
new Function('require','__dirname',base+`
let casos=0,tables=[];
El.prototype.addEventListener=function(k,fn){(this.listeners ||= {})[k]=fn;};
sandbox.tablaDensa=o=>{tables.push(o);return h('table',{},o.filas.map(r=>h('row',{},o.columnas.map(col=>col.celda?col.celda(r):r[col.clave]))));};
const dias=['2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-02'];
const serie={version:'238.1',fuente:'ClickUp entradas',fecha_fuente:'2026-10-03 02:56',cobertura:'parcial',zona:'Europe/Madrid',zona_confirmada:true,desde:dias[0],hasta:dias[4],dias:dias.map((fecha,i)=>({fecha,horas:i===3?0:i===4?2:null,entradas:i>=3?1:null,estado:i>=3?'observado':'sin_dato'}))};
const p={persona_id:'a',nombre:'Fixture A',equipo:'Account',ayer:2,semana:2,meses:[{mes:'2026-09',imputadas:17,esperadas:128,pct:99},{mes:'2026-10',imputadas:2}],diario_238:serie};
const doc={hoy:'2026-10-03',generado:'2026-10-03 02:56',personas:[p,{...p,persona_id:'secret',nombre:'No autorizado'}]};
const r5=sandbox.rangoEquipo254('cinco',doc.hoy,'2026-09');
let r=sandbox.filaEquipo254(p,doc,r5);assert.equal(r.horas,2);assert.equal(r.total5,2);assert.equal(r.dias_observados,2);assert.equal(r.capacidad,null);assert.equal(r.porcentaje,null);casos++;
r=sandbox.filaEquipo254(p,doc,{tipo:'libre',desde:'2026-10-01',hasta:'2026-10-01'});assert.equal(r.horas,0);assert.equal(r.dias_observados,1);casos++;
for(const rango of [{tipo:'libre',desde:'2026-09-29',hasta:'2026-09-29'},{tipo:'libre',desde:'2026-09-27',hasta:'2026-10-02'},{tipo:'libre',desde:'2026-10-02',hasta:'2026-09-28'},{tipo:'libre',desde:'2026-02-31',hasta:'2026-10-02'}])assert.equal(sandbox.filaEquipo254(p,doc,rango).horas,null);casos++;
assert.equal(sandbox.rangoEquipo254('semana','2026-10-03','2026-09').desde,'2026-09-28');assert.equal(sandbox.rangoEquipo254('mes','2026-10-03','2026-09').hasta,'2026-09-30');assert.equal(sandbox.rangoEquipo254('mes','2026-10-03','2026-10').hasta,'2026-10-02');assert.equal(sandbox.rangoEquipo254('mes','2026-10-03','2026-11'),null);casos++;
assert.equal(sandbox.filaEquipo254(p,doc,sandbox.rangoEquipo254('mes',doc.hoy,'2026-09')).horas,17);assert.equal(sandbox.filaEquipo254({...p,meses:[{mes:'2026-09',imputadas:0}]},doc,sandbox.rangoEquipo254('mes',doc.hoy,'2026-09')).horas,null);assert.equal(sandbox.filaEquipo254({...p,meses:[p.meses[0],p.meses[0]]},doc,sandbox.rangoEquipo254('mes',doc.hoy,'2026-09')).horas,null);assert.equal(sandbox.filaEquipo254({...p,diario_238:null},{...doc,generado:'2026-09-01bad'},sandbox.rangoEquipo254('mes',doc.hoy,'2026-09')).horas,null);casos++;
assert.equal(sandbox.filaEquipo254(p,{...doc,hoy:'2026-10-01'},sandbox.rangoEquipo254('mes','2026-10-01','2026-10')).horas,null);assert.equal(sandbox.filaEquipo254(p,{...doc,hoy:'2026-09-28'},sandbox.rangoEquipo254('semana','2026-09-28','2026-09')).horas,null);casos++;
function text(n){return typeof n==='string'?n:typeof n==='number'?String(n):(n?.children||[]).map(text).join(' ')}
function find(n,p){return typeof n==='object'&&n?[...(p(n)?[n]:[]),...(n.children||[]).flatMap(x=>find(x,p))]:[]}
let live=true,mod=true,opened=[];const ctx={real:{id:'a'},persona:{id:'a'},vigente:()=>live,veModulo:()=>mod};
let out=sandbox.panoramaHoras(ctx,[p],'2026-09',doc,{alAbrir:id=>opened.push(id)});
assert.equal(tables[0].filas.length,1);assert.equal(tables[0].porPagina,1);assert.equal(tables[0].columnas.length,10);assert.equal(tables[0].columnas[0].minAncho,'190px');assert(text(out).includes('min-width:1100px'));assert(text(out).includes('width:200px'));assert(!text(out).includes('color:var(--good'));assert(!text(out).includes('No autorizado'));assert(!text(out).includes('99 %'));assert.equal(tables[0].filas[0].porcentaje,null);casos++;
const mes=find(out,n=>n.tag==='button'&&text(n)==='Mes elegido')[0];mes.attrs.on.click();assert.equal(tables.at(-1).filas[0].horas,17);assert(text(out).includes('2026-09-01 a 2026-09-30'));casos++;
const inputs=find(out,n=>n.tag==='input');inputs[0].value='2026-10-01';inputs[1].value='2026-10-01';inputs[0].listeners.change();assert.equal(tables.at(-1).filas[0].horas,0);inputs[0].value='2026-09-27';inputs[1].value='2026-10-02';inputs[0].listeners.change();assert.equal(tables.at(-1).filas[0].horas,null);casos++;
const box=find(out,n=>n.tag==='div'&&n.children.some(c=>c?.tag==='table'))[0];const antesDetached=tables.length;box.isConnected=false;mes.attrs.on.click();inputs[0].listeners.change();assert.equal(tables.length,antesDetached);box.isConnected=true;casos++;
const before=tables.length;ctx.persona.id='other';mes.attrs.on.click();assert.equal(tables.length,before);ctx.persona.id='a';mod=false;mes.attrs.on.click();assert.equal(tables.length,before);mod=true;live=false;mes.attrs.on.click();assert.equal(tables.length,before);tables[0].alPulsar(tables[0].filas[0]);assert.equal(opened.length,0);casos++;
live=true;tables=[];const many=Array.from({length:24},(_,i)=>({...p,persona_id:'p'+i}));out=sandbox.panoramaHoras(ctx,many,'2026-09',{...doc,personas:many});assert.equal(tables[0].filas.length,24);assert.equal(tables[0].porPagina,24);casos++;
tables=[];sandbox.panoramaHoras(ctx,[p],'2026-09',{...doc,personas:[p,p]});assert.equal(tables[0].filas.length,0);casos++;
console.log(casos+' grupos254 PASS: matriz actual completa/autorizada, rangos, fuente/mes, cero observado, unknown y callbacks revocados.');
`)(require,__dirname);
