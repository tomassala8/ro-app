const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const base=fs.readFileSync(path.join(__dirname,'pruebas_operaciones_accounts_263.cjs'),'utf8');
const {dir,walk,text,tables}=new Function('require','__dirname',base.slice(0,base.indexOf('(async()=>{try{'))+';return {dir,walk,text,tables};')(require,__dirname);
let groups=0;const test=(name,fn)=>{fn();groups++;};
(async()=>{try{
 const {h}=await import('file://'+path.join(dir,'componentes.mjs')),{renderAccounts263}=await import('file://'+path.join(dir,'_operaciones_accounts_263.mjs'));
 const copy=x=>JSON.parse(JSON.stringify(x));
 const actor={id:'ops',estado:'activo',puestos:['operaciones']},cs=Array.from({length:8},(_,i)=>({id:'c'+i,nombre:'Cliente '+i,activo_confirmado:true,detalle:true,equipo:{account:[{persona_id:'account',principal:true,confianza:'confirmada'}]}}));
 const doc={generado:'2026-10-03T12:00:00Z',alertas:Array.from({length:162},(_,i)=>({id:'alerta-'+i,cliente_id:'c'+i%8,tipo:['acc_critico','alta_fuera_plazo','acc_correos','web_caida'][i%4],titulo:'Señal '+i,motivo:'Evidencia '+i,gravedad:'alta',ir:'#/en-rojo'}))};
 let gets=[];
 function ctx(extra={}){return {real:copy(actor),persona:copy(actor),servidor:true,hoy:'2026-10-04',vigente:()=>true,veModulo:()=>true,ver:()=>({ok:true}),nombre:id=>id,clientes:copy(cs),clientesVisibles:copy(cs),datos:{personas:[copy(actor),{id:'account',estado:'activo',puestos:['account']}],asignaciones:cs.map(c=>({cliente_id:c.id,silla:'account',principal:true,persona_id:'account'}))},carteraPorSilla:{account:cs.map(c=>c.id)},verdad:id=>({cliente_id:id,gravedad:'atencion'}),api:async()=>null,datosModulo:async r=>{gets.push(r);return r.startsWith('alertas/')?doc:null;},...extra};}
 const c=ctx(),main=h('main',{});main.connected=true;await renderAccounts263(main,c,'hoy');
 const first=walk(main).find(n=>n.attrs['data-hoy-principal']==='414'),rest=walk(main).find(n=>n.attrs['data-hoy-coleccion']==='414'),body=first.parent;
 test('Top6 antes de matriz y colección completa',()=>{assert.equal(body.children[0],first);assert(body.children.indexOf(rest)>body.children.indexOf(first));assert.equal(walk(first).filter(n=>n.tag==='article').length,6);assert.equal(new Set(walk(first).filter(n=>n.tag==='article').map(n=>n.attrs['data-cliente-top'])).size,6);});
 test('matriz existente visible, sin plegar ni perder columnas',()=>{assert.equal(tables(body.children[1])[0]?.tag,'table');assert.equal(walk(tables(body.children[1])[0]).filter(n=>n.tag==='th').length,9);assert.equal(body.children[1].tag==='details',false);});
 test('162 registros siguen disponibles en detalle cerrado',()=>{assert.equal(rest.tag,'details');assert(!rest.attrs.open);assert.match(text(rest),/162 registros autorizados/);assert.equal(walk(rest).filter(n=>n.attrs['data-alarmas-completas']==='342').length,1);assert.equal(rest.children[0].attrs.style.minHeight,'44px');assert(tables(rest).some(t=>walk(t).filter(n=>n.tag==='th').length===4));});
 test('una lectura existente de alertas y ninguna escritura',()=>{assert.equal(gets.filter(r=>r==='alertas/alertas').length,1);assert.equal(doc.alertas.length,162);});
 test('abrir detalle después de revocación limpia el contenido',()=>{c.clientes[0].activo_confirmado=false;rest.events.toggle({});assert.equal(walk(body).filter(n=>n.tag==='article').length,0);assert.doesNotMatch(text(body),/Evidencia 0/);});
 const account=ctx();account.real=account.persona={id:'account',estado:'activo',puestos:['account']};account.carteraPorSilla.account=['c1'];const own=h('main',{});own.connected=true;await renderAccounts263(own,account,'hoy');
 test('Accounts conserva sólo clientes de cartera en Top6',()=>{const nodes=walk(own).filter(n=>n.tag==='article');assert.equal(nodes.length,1);assert.equal(nodes[0].attrs['data-cliente-top'],'c1');assert(!nodes.some(n=>n.attrs['data-cliente-top']==='c0'));});
 const absent=h('main',{});absent.connected=true;await renderAccounts263(absent,ctx({datosModulo:async()=>null}),'hoy');
 test('sin fuente no inventa seis tarjetas ni éxito',()=>{assert.equal(walk(absent).filter(n=>n.tag==='article').length,0);assert.match(text(absent),/Prioridades pendientes/);});
 let resolve,alive=true;const pending=new Promise(r=>resolve=r),stale=h('main',{});stale.connected=true;const request=renderAccounts263(stale,ctx({vigente:()=>alive,datosModulo:r=>r.startsWith('alertas/')?pending:Promise.resolve(null)}),'hoy');
 await new Promise(r=>setTimeout(r,0));alive=false;resolve(doc);await request;
 test('respuesta tardía tras navegación no publica Top6',()=>assert.equal(walk(stale).filter(n=>n.tag==='article').length,0));
 console.log(groups+' grupos414 PASS · renderer Hoy263+Top388 reales, orden, colección cerrada, matriz preservada, cartera y revocación.');
}finally{fs.rmSync(dir,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1;});
