const fs=require('node:fs');const base=fs.readFileSync(__dirname+'/pruebas_tablero_mi_trabajo_181.cjs','utf8').split('const a=')[0];
new Function('require','__dirname',base+String.raw`
(async()=>{
const a={id:'task-a',lista_id:'list-1',cli:'cliente-1',cliente:'Proyecto',persona_id:'yo',tarea:'Visible',estado:'diario',tipo_estado:'custom',grupoV:'hoy',capa:{cambios:[]}};
const uuid='f61a94b8-2091-453e-9299-43b5b1758192';c.crypto={randomUUID:()=>uuid};let sends=[];
const E=()=>({D:{tareas:[a],fuentes:{}},V:{yo:'yo',personas:[{id:'yo'}],cambios:[],estados_detalle:{'list-1':[{estado:'diario',tipo:'custom'},{estado:'completado',tipo:'custom'},{estado:'rechazado',tipo:'done'},{estado:'complete',tipo:'closed'}]},capacidad_transicion:{version:'191.1',activo:true},transiciones:{'task-a':{lista_id:'list-1',expected_estado:'diario',revision:'a'.repeat(64),bloqueada:false}}},local:[],ctx:{hoy:'2026-10-03',persona:{id:'yo',puestos:[]},real:{id:'yo'},servidor:true,clientes:[{id:'cliente-1'}],nombre:x=>x,accion:async p=>{sends.push(JSON.stringify(p));throw Error('timeout');}},vigente:()=>true});
let e=E(),tree;const paint=()=>tree=c.cambioEstadoDetalle200(e,a,paint);
const open=()=>c.botonFinalizar203(e,a,paint).attrs.on.click();
const menu=()=>buscar(tree,n=>n.tag==='menu')[0]?.attrs.config;
const save=()=>buscar(tree,n=>n.tag==='button'&&n.attrs['aria-label']?.startsWith('Guardar cambio'))[0];
const row=c.fila(e,a,'mias',paint);const final=buscar(row,n=>n.attrs['data-finalizar-203']===a.id)[0];assert(final);assert(text(final)==='Finalizar…');assert(!text(row).includes('Hecha'));final.attrs.on.click();assert.equal(sends.length,0);assert.equal(e.abierta,'yo:task-a');assert.equal(menu().valor,'');assert.deepEqual(Array.from(menu().opciones,x=>x.valor),['rechazado','complete']);assert(save().attrs.disabled);casos++;
menu().alCambiar('complete');await save().attrs.on.click();assert.equal(sends.length,1);const p=JSON.parse(sends[0]);assert.equal(p.tipo,'cambiar_estado');assert.equal(p.vista_previa.a,'complete');assert.equal(p.vista_previa.expected_estado,'diario');assert.equal(p.vista_previa.transicion_tablero,true);assert.equal(p.intencion_id,uuid);assert.equal(e.local.length,0);assert.equal(e.D.tareas[0].estado,'diario');casos++;
const first=sends[0];open();assert.equal(e.movimientos192.get(a.id).intento.payload.intencion_id,uuid);await save().attrs.on.click();assert.equal(sends[1],first);casos++;
e=E();e.V.estados_detalle['list-1']=e.V.estados_detalle['list-1'].filter(x=>x.estado!=='rechazado');open();assert.equal(menu().valor,'complete');assert(!save().attrs.disabled);assert.equal(sends.length,2,'Abrir único destino no envía');casos++;
e=E();e.V.estados_detalle['list-1']=e.V.estados_detalle['list-1'].filter(x=>!['done','closed'].includes(x.tipo));assert(c.botonFinalizar203(e,a,paint).attrs.disabled);assert(c.botonFinalizar203(e,a,paint).attrs.title.includes('No hay un destino final'));casos++;
for(const mutate of [e=>e.ctx.soloLectura=true,e=>e.ctx.pilotoLectura=true,e=>e.ctx.real.id='otra',e=>delete e.V.transiciones,e=>e.V.transiciones[a.id].bloqueada=true]){e=E();mutate(e);assert(c.botonFinalizar203(e,a,paint).attrs.disabled);const total=sends.length;open();assert.equal(sends.length,total);assert.equal(e.abierta,undefined);casos++;}
e=E();open();menu().alCambiar('completado');const total=sends.length;await save().attrs.on.click();assert.equal(sends.length,total,'Destino no final inyectado nunca pasa');casos++;
e=E();open();const all=buscar(tree,n=>n.tag==='button'&&text(n)==='Ver todos los estados de esta lista')[0];all.attrs.on.click();assert(menu().opciones.some(x=>x.valor==='completado'));assert.equal(menu().valor,'');assert(save().attrs.disabled);casos++;
for(const tipo of ['marcar_hecha','cambiar_estado']){e=E();await assert.rejects(c.actuar(e,a,tipo,{a:'complete'},'Hecha'),/intención durable/);assert.equal(e.local.length,0);casos++;}
assert(!source.includes("alHacer: () => actuar(E, t, 'marcar_hecha'"));assert(!source.includes("? 'completado' :"));casos++;
console.log(casos+' pruebas UI203 PASS: fila real, finales exactos/ambigüedad, apertura sin POST, scope, CAS, retry y bloqueo legacy.');
})().catch(e=>{console.error(e);process.exitCode=1;});
`)(require,__dirname);
