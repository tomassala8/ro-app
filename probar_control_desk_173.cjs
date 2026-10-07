// Fuente y helper reales, reloj explícito congelado; sin red ni datos reales.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');const box={};vm.createContext(box);vm.runInContext(fs.readFileSync(__dirname+'/modulos/control_cartera.js','utf8').replace(/export /g,''),box);
const base={clientes:[{id:'fixture',nombre:'Fixture',activo_confirmado:true},{id:'ajeno',activo_confirmado:true}],persona_id:'account',esOps:false,carteraIds:['fixture'],asignaciones:[],personas:[],hoy:'2026-10-03'};
const counts={cliente_id:'fixture',sin_contestar:1,entre_24_48:0,mas_48:1};
const source={generado:'2026-10-03 09:00',fuentes:{desk:{hora:'2026-10-02 17:12',estado:'bien'}},clientes:[counts]};
const row=d=>box.prepararControlCartera({...base,fuentes:{bandeja:d}})[0];let n=0;
let r=row(source);assert.equal(r.tickets.estado,'rojo');assert.equal(r.tickets.medicion.mas_48,1);assert.equal(r.tickets.fecha,'2026-10-02 17:12');n++;
for(const v of [undefined,null,'2026-02-30 01:00','2026-10-04 01:00','2026-10-03 25:00','2026-10-03 24:00','2026-10-03 invalid']){
 for(const key of ['generado','lectura']){const d=structuredClone(source);if(key==='generado')d.generado=v;else d.fuentes.desk.hora=v;r=row(d);assert.equal(r.tickets.valor,'Sin dato');assert.equal(r.tickets.estado,'gris');assert.equal(r.tickets.medicion,undefined);assert.equal(box.resumirAccountsControl([r])[0].tickets48.valor,null);n++;}
}
for(const estado of [undefined,'error','sin_conectar','no_aplica']){r=row({...source,fuentes:{desk:{...source.fuentes.desk,estado}}});assert.equal(r.tickets.valor,'Sin dato');n++;}
r=row({...source,generado:'2026-10-02 08:00'});assert.equal(r.tickets.valor,'Sin dato');n++;
r=row({...source,fuentes:{desk:{...source.fuentes.desk,error:'fixture'}}});assert.equal(r.tickets.valor,'Sin dato');n++;
r=row({...source,fuentes:{desk:{...source.fuentes.desk,errores:['fixture']}}});assert.equal(r.tickets.valor,'Sin dato');n++;
for(const error of [undefined,'fixture']){r=row({...source,fuentes:{desk:{...source.fuentes.desk,estado:'dato_viejo',error}}});assert.equal(r.tickets.estado,'gris');assert.match(r.tickets.valor,/Última copia/);assert.equal(r.tickets.medicion,undefined);assert.equal(box.resumirAccountsControl([r])[0].tickets48.valor,null);n++;}
r=row({...source,clientes:[{...counts,sin_contestar:0,mas_48:0,entre_24_48:0}]});assert.equal(r.tickets.medicion.total,0);assert.equal(r.tickets.estado,'gris');assert.equal(box.resumirAccountsControl([r])[0].tickets48.valor,0);n++;
for(const values of [{sin_contestar:0,mas_48:1},{sin_contestar:1.5},{sin_contestar:'1'},{sin_contestar:-1},{sin_contestar:Number.MAX_SAFE_INTEGER+1}]){r=row({...source,clientes:[{...counts,...values}]});assert.equal(r.tickets.valor,'Sin dato');n++;}
r=row({...source,clientes:[counts,counts]});assert.equal(r.tickets.valor,'Sin dato');n++;
const rows=box.prepararControlCartera({...base,fuentes:{bandeja:{...source,clientes:[counts,{...counts,cliente_id:'ajeno',sin_contestar:999,mas_48:999}]}}});assert.equal(rows.length,1);assert.equal(box.resumirAccountsControl(rows)[0].tickets48.valor,1);n++;
// Reproducción de las otras dos carencias: calendario/disponibilidad y subproyectos, sin modificar producto.
const horasSource=fs.readFileSync(__dirname+'/modulos/horas.js','utf8');vm.runInContext(horasSource.slice(horasSource.indexOf('export function resumenHorasPersona'),horasSource.indexOf('export function panoramaHoras')).replace('export ',''),box);
const hp=box.resumenHorasPersona({persona_id:'fixture',ayer:0,semana:4,meses:[{mes:'2026-10',imputadas:4,esperadas:128}]},'2026-10',{ayer:'2026-10-02',fuentes:{horas:{hora:'2026-10-03 09:00'}}});assert.equal(hp.dia,0);assert.equal(hp.referencia_mes,128);assert.equal(hp.disponibilidad,null);n++;
const proyectos={hoy:'2026-10-03',fuentes:{horas:{hora:'2026-10-03 09:00'}},proyectos:[{cliente_id:'fixture',proyecto_id:'p1',horas_mes:2},{cliente_id:'fixture',proyecto_id:'p2',horas_mes:3}]};const rr=box.prepararControlCartera({...base,fuentes:{produccion:proyectos}});assert.equal(rr.length,1);assert.equal(rr[0].alcance_proyecto,'cliente_agrupado');assert.equal(rr[0].horas.valor,'Sin dato');assert.equal(rr[0].presupuesto.valor,'Sin presupuesto confirmado');n++;
console.log(n+' grupos173 PASS: fuente Desk/fecha/estado, última copia, cero medido, agregados, alcance y límites de capacidad/subproyecto reales.');
