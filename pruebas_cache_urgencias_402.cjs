const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ro-cache402-'));try{
 fs.writeFileSync(path.join(dir,'package.json'),'{"type":"module"}');
 for(const f of ['datos.js','permisos.js','reglas_permisos.json'])fs.copyFileSync(path.join(__dirname,f),path.join(dir,f));
 const m=await import(require('node:url').pathToFileURL(path.join(dir,'datos.js')));
 for(const r of ['produccion/urgencias-observadas','produccion/urgencias-observadas?grupo=finales','produccion/urgencias-observadas?cliente_id=c1'])assert.equal(m.conMemoria(r),false);
 assert.equal(m.conMemoria('modulo/produccion/produccion'),true);
 console.log('4 contratos cache402 PASS (módulo y dependencias reales)');
}finally{fs.rmSync(dir,{recursive:true,force:true});}})().catch(e=>{console.error(e.message);process.exitCode=1;});
