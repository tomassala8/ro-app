const fs=require('node:fs');const assert=require('node:assert/strict');
(async()=>{
 const src=fs.readFileSync('modulos/_herramientas_perfil.js','utf8').replace("import { h } from '../componentes.js';", "const h=(tag,attrs={},...children)=>({tag,attrs,children:children.flat(Infinity).filter(x=>x!=null)});");
 const {herramientasPerfil,panelHerramientas}=await import('data:text/javascript;base64,'+Buffer.from(src).toString('base64'));
 const ctx={real:{id:'carla'},persona:{id:'carla',estado:'activo',puestos:['account']},veModulo:id=>id==='salud-crm'};
 const ids=c=>herramientasPerfil(c).map(x=>x.id);
 assert.deepEqual(ids(ctx),['chatgpt','claude','ghl','googleads','analytics','searchconsole','drive']);
 assert.deepEqual(ids({...ctx,persona:{id:'paid',puestos:['trafficker']},veModulo:id=>id==='captacion'}),['chatgpt','claude','higgsfield','meta','googleads','analytics','drive']);
 assert.deepEqual(ids({...ctx,persona:{id:'junior',puestos:['setters']},veModulo:()=>false}),['chatgpt','claude','drive']);
 assert.deepEqual(ids({...ctx,persona:{...ctx.persona,estado:'baja'}}),[]);
 assert.deepEqual(ids({...ctx,persona:null}),[]);
 assert.equal(panelHerramientas(ctx,()=>false),null);
 let current=true;const node=panelHerramientas(ctx,()=>current);
 const walk=n=>typeof n==='object'&&n?[n,...(n.children||[]).flatMap(walk)]:[];
 const links=walk(node).filter(n=>n.tag==='a');assert.equal(links.length,7);
 for(const n of links){assert.equal(new URL(n.attrs.href).protocol,'https:');assert.equal(new URL(n.attrs.href).search,'');assert.equal(n.attrs.rel,'noopener noreferrer');assert.equal(n.attrs.referrerpolicy,'no-referrer');}
 let denied=0;links[2].attrs.on.click({preventDefault:()=>denied++});assert.equal(denied,0);
 ctx.veModulo=()=>false;links[2].attrs.on.click({preventDefault:()=>denied++});assert.equal(denied,1);
 current=false;links[0].attrs.on.click({preventDefault:()=>denied++});assert.equal(denied,2);
 current=true;ctx.real.id='otra';links[0].attrs.on.click({preventDefault:()=>denied++});assert.equal(denied,3);
 assert(!links.some(n=>/claves|wordpress|token|password/i.test(n.attrs.href)));
 ctx.real.id='carla';ctx.veModulo=id=>id==='ficha';
 const acceso=walk(panelHerramientas(ctx,()=>current)).find(n=>n.tag==='a'&&n.attrs.href==='#/ficha');assert(acceso);
 acceso.attrs.on.click({preventDefault:()=>denied++});assert.equal(denied,3);
 ctx.veModulo=()=>false;acceso.attrs.on.click({preventDefault:()=>denied++});assert.equal(denied,4);
 ctx.veModulo=()=>true;ctx.persona.id='otra';acceso.attrs.on.click({preventDefault:()=>denied++});assert.equal(denied,5);
 console.log('232: 13 grupos PASS (perfil, permisos, vigencia, identidad y enlaces sin secretos).');
})().catch(e=>{console.error(e);process.exitCode=1});
