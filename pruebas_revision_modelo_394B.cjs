// Modelo real, fixtures sin datos privados; no frontend del owner en curso.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const b={};vm.createContext(b);vm.runInContext(fs.readFileSync(__dirname+'/modulos/control_cartera.js','utf8').replace(/export /g,''),b);
const base={clientes:[{id:'ok',activo_confirmado:true}],persona_id:'a',esOps:true,carteraIds:[],asignaciones:[],personas:[],hoy:'2026-10-05',permisosPautaIds:['ok']};
const horas={hoy:'2026-09-30',fuentes:{horas:{hora:'2026-10-02 05:00'}},proyectos:[{cliente_id:'ok',horas_mes:7,horas_medicion:{estado:'medido',fuente:'horas',periodo:'2026-09',fecha:'2026-10-02 05:00'}}]};
const pauta={generado:'2026-10-02 05:00',mes_cuota:'2026-10',clientes:[{cliente_id:'ok',cuota_horas:{pautadas:20},cuota:987654}]};
const rows=b.prepararControlCartera({...base,fuentes:{produccion:horas,dinero_cliente:pauta}});assert.equal(rows[0].horas.medicion.periodo,'2026-09');assert.equal(rows[0].pauta_horas.periodo,'2026-10');assert.equal(rows[0].pauta_horas.presupuesto_confirmado,false);assert.equal(rows[0].pauta_horas.origen,'referencia_economica');assert(!JSON.stringify(rows).includes('987654'));assert(!('ratio' in rows[0].horas));
for(const invalid of ['2026-02-30','2026-10-01 24:00','2026-10-01T12:00:00+14:01','2026-10-01T12:00:00+15:00','2026-10-01T12:00:00+01:99','2026-10-01 secret=fixture']){const flujo={hoy:base.hoy,fuentes:{flujo:{hora:invalid}},proyectos:[{cliente_id:'ok',rev_account:3,rev_account_48:2,revisiones_account:{estado:'medido',fuente:'flujo',fecha:invalid}}]};
const r=b.prepararControlCartera({...base,fuentes:{produccion:flujo}})[0];assert.equal(r.revisiones.medicion,undefined,'Sello de calendario imposible no acredita revisión vigente');
}
const anterior='2026-09-20 05:00';const futuroMes={hoy:'2026-10-01',fuentes:{horas:{hora:anterior}},proyectos:[{cliente_id:'ok',horas_mes:7,horas_medicion:{estado:'medido',fuente:'horas',periodo:'2026-10',fecha:anterior}}]};
const incompatible=b.prepararControlCartera({...base,fuentes:{produccion:futuroMes}})[0];assert.equal(incompatible.horas.medicion,undefined,'Una lectura de septiembre no acredita observaciones de octubre aunque el descriptor declare octubre');
console.log('394B modelo PASS · meses/pauta/noimporte/calendario.');
