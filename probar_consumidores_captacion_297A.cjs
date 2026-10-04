// Auditoría de consumidores reales; no modifica pantallas, no red ni DOM de negocio.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert/strict');
const base=__dirname,s=fs.readFileSync(path.join(base,'modulos/captacion.js'),'utf8');
const grabar=s.match(/const GRAV = \{[\s\S]*?\n\};/)[0];
const grav=vm.runInNewContext(grabar+'; GRAV');
assert.equal(grav.dato.e,'gris');assert.match(grav.dato.t,/pendiente/);
assert.equal(grav.dato.o,3);
const fx=s.match(/function completarDinero\(c, f\) \{[\s\S]*?\n\}/)[0];
(async()=>{
 const cita=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(path.join(base,'modulos/_coste_cita_299.js'))).toString('base64'));
 const completar=vm.runInNewContext(fx+'; completarDinero',{normalizarCita299:cita.normalizarCita299,referenciaCita299:cita.referenciaCita299});
const c={coste_por_cita:{alarma_100:false,medicion:'referencia_legacy_sin_cohorte_enlazada'},quincenal:{coste_por_cita_14d:null}};
completar(c,{fuentes:{captacion_ghl:{datos:{coste_por_cita:{coste_por_cita_14d:150}}}}});
// La fuente299 de raíz conserva sólo referencia incluso al completar dinero desde ficha.
assert.equal(c.coste_por_cita.alarma_100,false);
assert.equal(c.quincenal.coste_por_cita_14d,null);
assert.equal(c.quincenal.coste_por_cita_referencia_14d,150);
 const m=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(path.join(base,'modulos/_crm_mediciones.js'))).toString('base64'));
 const r=m.medirEmbudoCRM({citas:{'14d':{sin_estado:null,agendadas:null}}},{hora:'2026-10-03 08:00',estado:'bien'},'2026-10-03');
 assert.equal(r.sinEstado,null);assert.equal(r.agendadas,null);assert.equal(r.asistencia,null);
 assert.equal(r.ventas,null);assert.equal(r.conversiones,null);
 console.log('3 casos reales: GRAV dato gris PASS; completarDinero299 no revive alarma PASS; CRM null sin ratios PASS. No certifica render global.');
})().catch(e=>{console.error(e);process.exitCode=1;});
