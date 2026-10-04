const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 const text=fs.readFileSync(__dirname+'/modulos/_pasos_resumen_433.js','utf8');
 const{badgesPasos433}=await import('data:text/javascript;base64,'+Buffer.from(text).toString('base64'));
 let n=0;const pass=()=>n++;
 const empty=badgesPasos433(null);assert.equal(empty.length,7);assert(empty.every(x=>x.valor==='—'&&x.estado==='gris'));pass();
 const rows=Array.from({length:11},()=>({valor:'—',estado:'gris',detalle:'Sin fuente'}));
 for(const i of [0,3,9,10])rows[i]={valor:String(i),estado:'ambar',detalle:'Copia fixture'};rows[6]={valor:'6 señales',estado:'rojo',detalle:'Altas de la copia'};
 const b=badgesPasos433(rows);assert.deepEqual(b.map(x=>x.valor),['9','0','3','—','—','6','10']);assert.equal(b[1].estado,'ambar');assert.match(b[1].detalle,/clientes.*histórico/);assert.match(b[2].detalle,/revisiones.*parcial/);assert.match(b[0].detalle,/señales de registros/);pass();
 rows[2]={valor:'99/99',estado:'rojo',detalle:'Rojos sin plan'};rows[7]={valor:'100',estado:'verde',detalle:'Semáforos'};assert.equal(badgesPasos433(rows)[3].valor,'—');assert.equal(badgesPasos433(rows)[4].valor,'—');pass();
 rows[0].estado='verde';assert.equal(badgesPasos433(rows)[1].estado,'gris');pass();
 for(const v of ['—','-1','NaN','Infinity','0/10','1.5','999999999999999999999']){rows[3].valor=v;assert.equal(badgesPasos433(rows)[2].valor,'—');}pass();
 rows[9]={valor:'0',estado:'gris',detalle:'Cero señales observadas en copia'};assert.equal(badgesPasos433(rows)[0].valor,'0');rows[9].detalle='';assert.equal(badgesPasos433(rows)[0].valor,'—');pass();
 // Renderer274 real con loader de sus dependencias reales, sin sustituir el modelo ni relajar regresiones.
 let harness=fs.readFileSync(__dirname+'/pruebas_resumen_274.cjs','utf8');
 harness=harness.replace("console.log(num+' grupos PASS;",`check('433 siete badges y texto de unidad/alcance accesible',()=>{const pasos=walk(cont).filter(x=>String(x.attrs.class||'').startsWith('paso-badge433'));assert.equal(pasos.length,7);assert.ok(pasos.every(x=>x.textContent==='—'));const enlaces=walk(cont).filter(x=>x.tag==='a'&&x.attrs['aria-label']);assert.equal(enlaces.length,7);assert.ok(enlaces.every(x=>x.attrs.title===x.attrs['aria-label']));assert.deepEqual(enlaces.map(x=>x.children[0]),['1. Equipo','2. Clientes >48h','3. Producción','4. Fuegos · copia','5. Contacto/reu.','6. Nuevos','7. Cierre']);M.PASOS274.forEach((p,i)=>assert.ok(enlaces[i].attrs['aria-label'].startsWith((i+1)+'. '+p[1]+' · ')));assert.match(enlaces[3].attrs.title,/no acreditan Fuegos/);assert.match(enlaces[4].attrs.title,/semáforo no los sustituye/);});\nconst positivo433=h('main',{});positivo433.connected=true;await M.renderResumen274(positivo433,ctx(),{fuentes:{bandeja:B}});check('433 renderer contador clientes observado con copia y cobertura',()=>{const p=walk(positivo433).filter(x=>String(x.attrs.class||'').startsWith('paso-badge433'));assert.equal(p[1].textContent,'1');assert.equal(p[1].attrs.class,'paso-badge433 gris');assert.match(p[1].parent.attrs.title,/1\\/1 clientes medidos/);});\nconsole.log(num+' grupos PASS;`);
 const run=require('node:child_process').spawnSync(process.execPath,['-e',harness],{cwd:__dirname,encoding:'utf8'});
 process.stdout.write(run.stdout||'');process.stderr.write(run.stderr||'');assert.equal(run.status,0,'Renderer274 con dependencias reales');
 console.log(n+' grupos puros433 PASS; render274/regresión aprobados, sin POST; GET402 nuevo validado en530.');
})().catch(e=>{console.error(e);process.exitCode=1});
