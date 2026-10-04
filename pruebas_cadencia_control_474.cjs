const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const c={};vm.createContext(c);vm.runInContext(fs.readFileSync(__dirname+'/modulos/control_cartera.js','utf8').replace(/export /g,''),c);
const hoy='2026-10-04',personas=[{id:'paid',estado:'activo',activo:true,puestos:['trafficker']}],row={cliente_id:'cliente-a',regla_id:'seguimiento_quincenal_especialista',cadencia_dias:15,responsable_role:'trafficker',incumplimiento:null,responsable_id:'paid',responsables_ids:['paid'],estado:'en_cadencia',ultima_confirmada:'2026-09-25',proxima_revision:'2026-10-10',fuentes_operativas:[{tipo:'reunion_celebrada',fuente:'zoom',fecha:'2026-09-25'}]},doc={hoy,sugerencias:[row],cobertura_reuniones:{completa:false}};
const render=(d=doc,ps=personas)=>c.prepararControlCartera({clientes:[{id:'cliente-a',activo_confirmado:true}],esOps:true,hoy,personas:ps,fuentes:{metodo:d}})[0].reuniones;
assert.equal(render().estado,'verde');let groups=1;
for(const change of [{ultima_confirmada:'2026-02-30'},{proxima_revision:'2026-12-31'},{fuentes_operativas:[]},{incumplimiento:false},{responsables_ids:['paid','otro']},{responsable_id:'no-existe'},{cadencia_dias:'15'}]){assert.notEqual(render({...doc,sugerencias:[{...row,...change}]}).estado,'verde');groups++;}
assert.notEqual(render(doc,[...personas,...personas]).estado,'verde');groups++;
assert.notEqual(render(doc,[{...personas[0],estado:'baja'}]).estado,'verde');groups++;
assert.notEqual(render(doc,[{...personas[0],puestos:['account']}]).estado,'verde');groups++;
for(const roles of [['trafficker','trafficker'],['trafficker',12]]){assert.notEqual(render(doc,[{...personas[0],puestos:roles}]).estado,'verde');groups++;}
for(const id of [null,'']){assert.notEqual(render({...doc,sugerencias:[{...row,responsable_id:id,responsables_ids:[id]}]},[{...personas[0],id}]).estado,'verde');groups++;}
assert.notEqual(render({...doc,hoy:'2026-10-03'}).estado,'verde');groups++;
assert.notEqual(render({...doc,sugerencias:[row,row]}).estado,'verde');groups++;
const late={...row,estado:'revisar_cadencia',ultima_confirmada:'2026-09-01',proxima_revision:'2026-09-16',fuentes_operativas:[{tipo:'reunion_celebrada',fuente:'zoom',fecha:'2026-09-01'}]};
assert.equal(render({...doc,sugerencias:[late]}).estado,'gris');groups++;
assert.equal(render({...doc,sugerencias:[late],cobertura_reuniones:{completa:true,desde:'2026-09-01',hasta:hoy}}).estado,'ambar');groups++;
assert.equal(render({...doc,sugerencias:[late],cobertura_reuniones:{completa:'true',desde:'2026-09-01',hasta:hoy}}).estado,'gris');groups++;
console.log(groups+' grupos474 PASS: renderer control, cadencia15d, evidencia, responsable, cobertura y desconocidos.');
