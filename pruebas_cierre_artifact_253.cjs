const fs=require('fs'),vm=require('vm'),assert=require('assert');const b={};vm.createContext(b);const s=fs.readFileSync(__dirname+'/modulos/_cierre_artifact_253.js','utf8');vm.runInContext(s.replace(/export /g,''),b);
const cli=[{id:'a',activo_confirmado:true},{id:'b',activo_confirmado:true},{id:'inactivo',activo_confirmado:false}];const d={mes_horas:'2026-09',mes_cuota:'2026-10',clientes:[{cliente_id:'a',nombre:'A',coste_horas:{sep:10},cuota_horas:{pautadas:20}},{cliente_id:'b',nombre:'B',coste_horas:{sep:0}},{cliente_id:'inactivo',coste_horas:{sep:30}},{cliente_id:'ajeno',coste_horas:{sep:40}}]};
let r=b.prepararCierre253(d,cli);assert.equal(r.length,2);assert.equal(r[0].reales,10);assert.equal(r[0].pautadas,null);assert.equal(r[0].pct,null);assert.equal(r[1].reales,null);
r=b.prepararCierre253({...d,mes_cuota:'2026-09'},cli);assert.equal(r[0].pct,50);
assert.equal(b.prepararCierre253({...d,clientes:[d.clientes[0],d.clientes[0]]},cli).length,0);
assert.equal(b.prepararCierre253(d,[cli[0],cli[0]]).length,0);
for(const v of [-1,NaN,Infinity,'10',null])assert.equal(b.prepararCierre253({...d,clientes:[{...d.clientes[0],coste_horas:{sep:v}}]},cli)[0].reales,null);
assert.equal(b.prepararCierre253({...d,mes_horas:'2026-08'},cli)[0].reales,null);
assert(s.includes('Reuniones del mes'));assert(s.includes('Llamadas ≥30 s'));assert(!s.includes('fetch('));
const hist={version:'267.1',periodo:'2026-09',cobertura:'parcial',verificacion_externa:false,cumplimiento:null,no_evalua_garantia:true,sha256_candidato:'4afc61a142faadf9631141c3a33109712cfd9ecfdf832a99e469731e970f5bc2',fuente_llamadas:'zadarma_cache_historica',fuente_reuniones:'verificacion_manual_anterior_ID_exacto',llamadas30:2,reuniones_verificadas_historicas:1};
const conHist=h=>b.prepararCierre253({...d,clientes:[{...d.clientes[0],historico_267:h}]},cli)[0];
assert.equal(conHist(hist).llamadas,2);assert.equal(conHist(hist).reuniones,1);
for(const cambio of [{periodo:'2026-10'},{cumplimiento:true},{verificacion_externa:true},{sha256_candidato:'wrong'},{cobertura:'completa'}]){const r=conHist({...hist,...cambio});assert.equal(r.llamadas,null);assert.equal(r.reuniones,null);}
for(const v of [0,-1,'2',true,NaN,1.5])assert.equal(conHist({...hist,llamadas30:v}).llamadas,null);
console.log('253 PASS: meses incompatibles no se comparan, cero legacy desconocido, negativos y cadenas rechazados, clientes activos autorizados únicos, siete columnas referencia.');
