//626: helper/modelo/render374 reales. Catálogo actual independiente de la copia visible.
const fs626=require('fs');
const original626=fs626.readFileSync(__dirname+'/pruebas_objetivos_seo_374.cjs','utf8');
const prefix626=original626.slice(0,original626.indexOf('let c=make(),d=carga(c),r=mount(c,d);'));
new Function('require','__dirname',prefix626+String.raw`
for(const change of [c=>delete c.clientes,c=>c.clientes=[],c=>c.clientes.push({...c.clientes[0]}),c=>c.clientes[0].activo_confirmado=false,c=>c.clientes[0].activo=false,c=>c.clientes[0].estado='baja',c=>c.clientes[0].detalle=false,c=>c.clientesVisibles[0].activo=false,c=>c.clientesVisibles[0].estado='baja']){
 const c=make(),loaded=carga(c);change(c);check(()=>assert.equal(M.modeloObjetivos374(c,loaded).length,0));
}
for(const change of [c=>c.clientes[0].activo=false,c=>c.clientes[0].estado='baja',c=>c.clientes.push({...c.clientes[0]})]){
 const c=make();let finish;c.api=()=>new Promise(r=>finish=r);const reading=M.cargarObjetivos374(c);change(c);finish(dto());const out=await reading;
 check(()=>{assert.equal(out.estado,'revocado');assert.equal(out.datos,null);assert.equal(M.modeloObjetivos374(c,out).length,0)});
}
for(const method of ['toggle','click']){
 const c=make(),root=mount(c,carga(c));assert(root.textContent.includes('Fixture'));c.clientes[0].activo_confirmado=false;
 let prevented=false;if(method==='toggle')all(root).find(x=>x.tag==='details').events.toggle();else all(root).find(x=>x.tag==='a').events.click({preventDefault:()=>prevented=true});
 check(()=>{assert(!root.textContent.includes('Fixture'));assert(!all(root).some(x=>x.tag==='table'));if(method==='click')assert(prevented)});
}
const c=make(),src=dto();src.clientes[0].objetivos.push({...row,canal:'maps',posicion:4});const data=carga(c,src),model=M.modeloObjetivos374(c,data),root=mount(c,data);
check(()=>{assert.equal(model[0].organico.valor,1);assert.equal(model[0].maps.valor,4);assert.equal(model[0].organico.acreditada,false);assert.equal(model[0].maps.acreditada,false);assert(!root.textContent.includes('cumplido'));assert.equal(all(root).filter(x=>x.tag==='th').length,7)});
c.clientes[0].detalle=false;check(()=>assert.equal(M.modeloObjetivos374(c,data).length,0));
const historical={fecha:'2026-10-03',clientes:[{cliente_id:'c',habilitado:false,objetivos_historicos:[{tipo:'Ciudad documentada',valor:'Ciudad histórica',fecha_documento:'2026-07-22',activar_consultas:false,benchmark_confirmado:false,razones:[]}]}]};
const hc=make();hc.soloLectura=true;const hr=mount(hc,carga(hc,historical));check(()=>{assert(hr.textContent.includes('histórico'));assert(hr.textContent.includes('no activa ciudades'));assert(!all(hr).some(x=>x.tag==='button'));assert.equal(M.modeloObjetivos374(hc,carga(hc,historical))[0].organico.valor,null)});
hc.clientes=[];all(hr).find(x=>x.tag==='details').events.toggle();check(()=>assert(!hr.textContent.includes('Ciudad histórica')));
console.log(n+' grupos626 PASS: catálogo actual, await/callbacks, canales y referencias históricas.');
})().catch(e=>{console.error(e);process.exitCode=1});
`)(require,__dirname);
