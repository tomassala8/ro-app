const fs=require('fs'),path=require('path');
const base=fs.readFileSync(path.join(__dirname,'pruebas_agenda_111.cjs'),'utf8').split('const evento=')[0];
const tests=`
const old={fuente:'calendar',tipo:'prospecto',id:'fixture',titulo:'COMIDA',persona_id:'tomas',inicio:'2026-10-03 15:00'};
const got=c.normalizarTipoAgenda(old);assert.equal(got.tipo,'evento');assert.equal(old.tipo,'prospecto');assert.equal(got.id,old.id);assert.equal(got.inicio,old.inicio);
for(const patch of [{fuente:'crm'},{fuente:'ghl'},{fuente:'bookings'},{tipo:'cliente'},{tipo:'interna'},{tipo_confirmado:true}]){
 const e={...old,...patch};assert.equal(c.normalizarTipoAgenda(e),e);
}
const opaque={...old,titulo:'X. Y.'};assert.equal(c.normalizarTipoAgenda(opaque).tipo,'evento');
console.log('174 PASS: Calendar sin clasificación confirmada no es lead; no muta ni borra eventos.');
`;
eval(base+tests);
