const fs=require('fs');const base=fs.readFileSync(__dirname+'/pruebas_urgencias_406.cjs','utf8').split('let n=0;')[0];
const extra=String.raw`
const withTitle=()=>{const d=dto();Object.assign(d.filas[0],{titulo:'Revisar formulario',titulo_estado:'observado_saneado',titulo_fuente:'clickup_cache_local',titulo_leido_utc:row.estado_leido_utc});return d;};
(async()=>{
let groups=0;
const c=ctx(),root=new N('main');c.api=async()=>withTitle();await box.renderUrgencias406(root,c);all(root,x=>x.tag==='button')[0].events.click();assert(root.textContent.includes('Revisar formulario'));assert(root.textContent.includes('t1'));assert.equal(all(root,x=>x.tag==='a')[0].attrs.href,'https://app.clickup.com/t/t1');groups++;
for(const patch of [{titulo:13},{titulo:'<script>x</script>'},{titulo:'x@example.invalid'},{titulo_fuente:'other'},{titulo_leido_utc:'2026-10-03T14:00:00Z'},{titulo_estado:'actual'},{titulo:'x'.repeat(241)}]){const x=ctx(),d=withTitle();Object.assign(d.filas[0],patch);assert.equal(box.proyectarUrgencias406(x,d,box.ambitoUrgencias406(x)),null);}groups++;
const old=ctx(),v=new N('main');await box.renderUrgencias406(v,old);all(v,x=>x.tag==='button')[0].events.click();assert(v.textContent.includes('Título no disponible'));assert(v.textContent.includes('t1'));groups++;
const blank=ctx(),bv=new N('main');blank.api=async()=>{const d=dto();Object.assign(d.filas[0],{titulo:null,titulo_estado:'no_disponible',titulo_fuente:null,titulo_leido_utc:null});return d;};await box.renderUrgencias406(bv,blank);all(bv,x=>x.tag==='button')[0].events.click();assert(bv.textContent.includes('Título no disponible'));groups++;
const denied=ctx(),d=withTitle();d.filas[0].cliente_id='foreign';assert.equal(box.proyectarUrgencias406(denied,d,box.ambitoUrgencias406(denied)),null);groups++;
const wait=ctx(),wv=new N('main');let resolve;wait.api=()=>new Promise(r=>resolve=r);const p=box.renderUrgencias406(wv,wait);wait.clientes[0].activo_confirmado=false;resolve(withTitle());await p;assert.equal(wv.textContent,'');groups++;
c.ver=()=>({ok:false});all(root,x=>x.tag==='button')[0].events.click();assert.equal(root.textContent,'');groups++;
console.log(groups+' grupos485 DOM PASS: título/ID/enlace seguros, antiguo y ausencia, DTO inválido y revocación.');
})().catch(e=>{console.error(e);process.exitCode=1;});`;
new Function('require','__dirname',base+extra)(require,__dirname);
