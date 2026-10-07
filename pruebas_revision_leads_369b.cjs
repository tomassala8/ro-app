const fsB=require('node:fs');
const originalB=fsB.readFileSync(__dirname+'/pruebas_revision_leads_369.cjs','utf8');
const prefixB=originalB.slice(0,originalB.indexOf('let f=fixture();'));
new Function('require','__dirname',prefixB+String.raw`
let f=fixture(),calls=[],finish;
f.c.accion=b=>{calls.push(b);return new Promise((res,rej)=>finish=()=>rej(Error('respuesta perdida después de commit')))};
let u=mount(f),p=u.b.events.click();await u.w.children.filter(x=>x.tag==='button')[1].events.click();check(()=>assert.equal(calls.length,1));finish();await p;
f.c.real.puestos.push('seo');f.c.persona.puestos.push('seo');f.c.datos.personas[0].puestos.push('seo');u=mount(f);f.c.accion=async b=>{calls.push(b);return ack(b)};await u.b.events.click();check(()=>{assert.equal(calls.length,2);assert.equal(calls[0],calls[1]);assert.equal(calls[0].intencion_id,calls[1].intencion_id);assert(M.leadsPendientes369(f.d.leads_sin_tocar,f.d.subcuentas).length===1);assert.match(u.badge.textContent,/pendiente en GHL/)});
for(const alter of [f=>f.x.cliente_id='otro',f=>f.x.sub_id='otra-sub',f=>f.c.datos.personas.push({...f.c.real}),f=>f.c.clientesVisibles=[],f=>f.c.veModulo=()=>false]){
 f=fixture();f.c.accion=b=>new Promise(res=>finish=()=>res(ack(b)));u=mount(f);p=u.b.events.click();alter(f);finish();await p;check(()=>{assert.equal(f.d.revisados.size,0);assert.match(u.w.textContent,/permisos actuales/)});
}
f=fixture();f.d.revisados.set('lead '+f.x.ref,{id:172,tipo:'revisado_lead',objeto:'lead '+f.x.ref,cliente_id:f.x.cliente_id});check(()=>{assert.equal(M.leadsPendientes369(f.d.leads_sin_tocar,f.d.subcuentas).length,1);const estado=M.revisionLead369(f.x,f.d.revisados);assert(estado.registrada);assert.equal(estado.contacto_verificado,false);assert.equal(estado.resuelto_en_ghl,false)});
f=fixture();u=mount(f);f.c.datos.personas[0].activo=false;u.w.events.toggle();check(()=>{assert.match(u.w.textContent,/permisos actuales/);assert(!u.w.children.some(x=>x.tag==='button'))});
console.log(n+' grupos independientes369B PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
`)(require,__dirname);
