const fs=require('fs');const base=fs.readFileSync(__dirname+'/pruebas_urgencias_406.cjs','utf8').split('let n=0;')[0];
const extra=String.raw`
(async()=>{
let groups=0;
const fixture=mixed=>{const d=dto();d.filas.push({...row,tarea_id:'t2',estado_leido_utc:mixed?'2026-10-03T14:00:00Z':row.estado_leido_utc});d.abiertas_en_copia=2;d.observaciones=2;d.lectura_hasta_utc=d.filas[1].estado_leido_utc;return d;};
const mount=async mixed=>{const c=ctx(),root=new N('main');let reads=0;c.api=async()=>{reads++;return fixture(mixed);};await box.renderUrgencias406(root,c);all(root,x=>x.tag==='button')[0].events.click();return {c,root,reads,detail:all(root,x=>x.attrs['aria-label']==='Urgencias del cliente')[0]};};
const same=await mount(false),table=all(same.detail,x=>x.tag==='table')[0];assert.equal(table.attrs.class,'densa');assert.equal(table.attrs['aria-label'],'Urgencias observadas de Cliente fixture');assert.deepEqual(all(table,x=>x.tag==='th').map(x=>x.textContent),['Tarea','Estado observado','Abrir']);assert.equal(all(table,x=>x.tag==='tr').length,3);assert.equal(all(table,x=>x.tag==='td').length,6);assert.equal(all(same.detail,x=>x.tag==='p'&&x.textContent.startsWith('Estado leído')).length,1);assert(same.detail.textContent.includes('Madrid'));groups++;
const mixed=await mount(true),mt=all(mixed.detail,x=>x.tag==='table')[0];assert.deepEqual(all(mt,x=>x.tag==='th').map(x=>x.textContent),['Tarea','Estado observado','Lectura','Abrir']);assert.equal(all(mt,x=>x.tag==='td').length,8);assert.deepEqual(all(mt,x=>x.tag==='td'&&x.attrs.title).map(x=>x.attrs.title),['2026-10-03T13:00:00Z','2026-10-03T14:00:00Z']);assert.equal(all(mixed.detail,x=>x.tag==='p'&&x.textContent.startsWith('Estado leído')).length,0);groups++;
assert.equal(same.reads,1);assert.equal(mixed.reads,1);assert.deepEqual(all(table,x=>x.tag==='a').map(x=>x.attrs.href),['https://app.clickup.com/t/t1','https://app.clickup.com/t/t2']);assert(same.root.textContent.includes('Fuegos actuales: por confirmar'));groups++;
const link=all(table,x=>x.tag==='a')[0];same.c.ver=()=>({ok:false});let prevented=false;link.events.click({preventDefault(){prevented=true;}});assert(prevented);assert.equal(same.root.textContent,'');groups++;
console.log(groups+' grupos502 PASS: lectura común una vez, distintas por fila, cifras/links conservados y revocación.');
})().catch(e=>{console.error(e);process.exitCode=1;});`;
new Function('require','__dirname',base+extra)(require,__dirname);
