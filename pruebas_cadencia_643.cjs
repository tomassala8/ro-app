const fs641=require('fs'),path641=require('path');
const APP=__dirname;
const source=fs641.readFileSync(__dirname+'/pruebas_seguimiento_metodo_453.cjs','utf8');
const prefix=source.slice(0,source.indexOf('let checks=0;'));
const req=require;
new Function('require','__dirname',prefix+String.raw`
(async()=>{
let n=0;const check=(f)=>{f();n++};
for(const roles of [[],['account'],['publicidad'],['trafficker','trafficker'],['trafficker',12],['trafficker',''],['trafficker',' '],['trafficker',' seo'],['trafficker','séo'],['trafficker',{}]]){
 const c=ctx();c.datos.personas[1].puestos=roles;const r=rows(c,doc())[0];check(()=>{assert.equal(r.estado,'sin_dato');assert.equal(r.responsable_id,null);assert.equal(b.estadoCadencia(r),'gris')});
}
for(const change of [c=>delete c.clientes,c=>c.clientes=[],c=>c.clientes[0].activo=false,c=>c.clientes[0].estado='baja',c=>c.clientes[0].detalle=false,c=>c.clientes.push(copy(c.clientes[0])),c=>c.clientesVisibles[0].activo=false,c=>c.clientesVisibles[0].estado='baja',c=>c.clientesVisibles.push(copy(c.clientesVisibles[0]))]){
 const c=ctx();change(c);check(()=>assert.equal(b.ambitoCadencia307(c).ids.length,0));
}
for(const change of [c=>c.datos.personas[1].puestos=['account'],c=>c.datos.personas[1].estado='baja',c=>c.datos.personas.push(copy(c.datos.personas[1])),c=>c.datos.asignaciones=[{persona_id:'other',cliente_id:'c',silla:'trafficker'}],c=>c.clientes[0].activo=false,c=>c.ver=()=>({ok:false})]){
 const c=ctx(),a=b.ambitoCadencia307(c),r=render(c);mount(r);open(r);assert.equal(pick(r,'th').length,7);change(c);check(()=>{assert.notEqual(b.ambitoCadencia307(c).firma,a.firma);open(r);assert.equal(r.children.length,0)});
}
for(const change of [c=>c.datos.personas[1].estado='baja',c=>c.datos.personas[1].puestos=['account'],c=>c.datos.personas.push(copy(c.datos.personas[1]))]){
 const c=ctx();c.datosModulo=async()=>({asistencias:[],clientes:[{cliente_id:'c',estado:'sin_reunion'}]});c.api=async p=>{if(p==='metodo/sugerencias'){change(c);return doc()}return {acciones:[]}};const main=new N('main');attach(main);await b.modulo453.render(main,c);check(()=>{assert(!all(main).some(x=>x.attrs.class?.includes('chip verde')));assert(!text(main).includes('10-oct'))});
}
const good=ctx(),r=render(good);mount(r);open(r);check(()=>{assert.equal(pick(r,'th').length,7);assert(text(r).includes('Trafficker fixture'));assert.equal(text(pick(r,'tbody')[0].children[0].children[4]),'2');assert(text(r).includes('históricos'));assert(!text(r).includes('cumplimiento'));assert(pick(r,'td')[3].attrs.title.includes('no es una cita agendada'))});
console.log(n+' grupos643 PASS: fuentes APP actuales, roles/ACT/firma/await/callback y siete columnas.');
})().catch(e=>{console.error(e);process.exitCode=1});
`)(req,__dirname);
