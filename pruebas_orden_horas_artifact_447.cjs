const fs=require('node:fs'),assert=require('node:assert/strict');
const prefix=fs.readFileSync(__dirname+'/pruebas_operaciones_equipo_262.cjs','utf8').split('(async()=>{')[0];
const E=new Function('require','__dirname',prefix+'\nreturn {c,N,all,text,H,PR,docs,make};')(require,__dirname);
const {c,N,all,text,H,PR,docs,make}=E,copy=x=>JSON.parse(JSON.stringify(x));
let n=0;async function check(label,f){await f();n++;}
const r={desde:'2026-09-28',hasta:'2026-10-03'},row=(id,valor,tipo='observado_diario',rango=r)=>({persona:{persona_id:id},medicion:{valor,tipo},rango});
const ids=xs=>Array.from(xs,x=>x.persona.persona_id),order=xs=>c.ordenarHorasArtifact447(xs,r);
const fixture=()=>{const known=(id,h)=>{const p=copy(H.personas[0]);p.persona_id=id;p.nombre=id;p.meses=[];p.diario_238.dias[0].horas=h;return p;};return {...H,personas:[{persona_id:'unknown',nombre:'unknown'},known('high',14),known('zero',0),known('low',2),known('equal',2)]};};
function ctx(doc){const x=make();x.datosModulo=async p=>p==='horas/horas'?doc:docs[p];return x;}
const rows=n=>all(all(n,x=>x.tag==='table')[0],x=>x.tag==='tbody')[0].children;
const names=n=>rows(n).map(x=>text(x.children[0]));
(async()=>{
 await check('ascending exact observed values incl explicit zero',()=>assert.deepEqual(ids(order([row('high',14),row('zero',0),row('low',2)])),['zero','low','high']));
 await check('ties stable and source unmutated',()=>{const a=[row('b',2),row('a',2)];assert.deepEqual(ids(order(a)),['b','a']);assert.deepEqual(ids(a),['b','a']);assert.equal(order(a)[0],a[0]);});
 await check('unknown and monthly refs last not zero',()=>assert.deepEqual(ids(order([row('null',null),row('legacy',.1,'referencia_mensual'),row('good',8),row('absent',undefined)])),['good','null','legacy','absent']));
 await check('other range never compared',()=>assert.deepEqual(ids(order([row('outside',0,'observado_diario',{desde:'2026-09-01',hasta:'2026-09-30'}),row('same',2)])),['same','outside']));
 await check('invalid numeric type infinity and negative unknown',()=>{const bad=[NaN,Infinity,-1,true,'0',null,undefined];assert.deepEqual(ids(order([...bad.map((v,i)=>row('bad'+i,v)),row('good',1)])),['good',...bad.map((_,i)=>'bad'+i)]);});
 await check('malformed range never sorts as known',()=>{const a=[row('high',14),row('zero',0)];for(const r of [null,{desde:'2026-02-30',hasta:'2026-10-03'},{desde:'2026-10-04',hasta:'2026-10-03'}])assert.deepEqual(ids(c.ordenarHorasArtifact447(a,r)),['high','zero']);});
 await check('typed90d same policy, no extrapolation or normalization',()=>assert.deepEqual(ids(order([row('a',8,'observado_historial_90d'),row('b',2,'observado_historial_90d')])),['b','a']));
 await check('empty and absent collection',()=>{assert.deepEqual(Array.from(order([])),[]);assert.deepEqual(Array.from(order(null)),[]);});
 await check('real262 renderer original 6 and4 cols ordered',async()=>{const main=new N('main');await c.renderEquipo262(main,ctx(fixture()),'horas');assert.deepEqual(names(main),['zero','low','equal','high','unknown']);const tables=all(main,x=>x.tag==='table');assert.deepEqual(tables.map(t=>all(t,x=>x.tag==='th').length),[6,4]);assert(text(main).includes('menor → mayor observado'));assert.equal(text(rows(main)[0].children[1]),'0');assert.equal(text(rows(main).at(-1).children[1]),'—');});
 await check('range callback recomputes keys, absence not zero',async()=>{const main=new N('main');await c.renderEquipo262(main,ctx(fixture()),'horas');all(main,x=>x.tag==='button'&&text(x)==='Este mes')[0].events.click();assert.deepEqual(names(main),['unknown','high','zero','low','equal']);assert(rows(main).every(x=>text(x.children[1])==='—'));});
 await check('legacy monthly stays reference last after daily typed',async()=>{const d=fixture();d.personas[0].meses=[{mes:'2026-09',imputadas:.1}];const main=new N('main');await c.renderEquipo262(main,ctx(d),'horas');all(main,x=>x.tag==='button'&&text(x)==='Mes pasado')[0].events.click();assert.deepEqual(names(main),['zero','low','equal','high','unknown']);assert(text(rows(main).at(-1).children[1]).includes('0,1'));});
 await check('revoked module cannot repaint through ordering',async()=>{const x=ctx(fixture()),main=new N('main');let allowed=true;x.veModulo=()=>allowed;await c.renderEquipo262(main,x,'horas');const before=text(main);allowed=false;all(main,q=>q.tag==='button'&&text(q)==='Mes pasado')[0].events.click();assert.equal(text(main),before);});
 await check('late identity cannot paint sorted private rows',async()=>{const x=ctx(fixture()),main=new N('main');x.datosModulo=async p=>{x.persona={id:'other'};return p==='horas/horas'?fixture():docs[p];};assert.equal(await c.renderEquipo262(main,x,'horas'),false);assert(!text(main).includes('high'));});
 await check('real362typed series sorts monthly, never reuses positive legacy',async()=>{
  const src=fs.readFileSync(__dirname+'/pruebas_historial_diario_364.cjs','utf8'),fn=src.slice(src.indexOf('function dto364()'),src.indexOf('function ctx364()')),d=new Function(fn+';return dto364();')();
  const hdoc={...H,personas:['high','unknown','low','zero'].map(id=>({persona_id:id,nombre:id,meses:[{mes:'2026-09',imputadas:999}]}))},base=d.personas[0].historial_diario;
  d.personas=hdoc.personas.map(p=>{const serie=copy(base);serie.dias.forEach(x=>Object.assign(x,{horas:null,entradas:null,estado:'sin_dato'}));if(p.persona_id!=='unknown')Object.assign(serie.dias.find(x=>x.fecha==='2026-09-01'),{horas:{high:14,low:2,zero:0}[p.persona_id],entradas:1,estado:'observado'});return {persona_id:p.persona_id,historial_diario:serie};});
  const x=ctx(hdoc),actor={id:'real',estado:'activo',activo:true,puestos:['operaciones']};Object.assign(x,{servidor:true,real:actor,persona:{...actor},datos:{personas:[actor,...hdoc.personas.map(p=>({id:p.persona_id,estado:'activo',activo:true,puestos:['seo']}))]},api:async()=>d});
  const main=new N('main');await c.renderEquipo262(main,x,'horas');all(main,y=>y.tag==='button'&&text(y)==='Mes pasado')[0].events.click();assert.deepEqual(names(main),['zero','low','high','unknown']);assert(!text(all(main,y=>y.tag==='table')[0]).includes('999'));assert.equal(text(rows(main)[0].children[1]),'≥0');assert.equal(text(rows(main).at(-1).children[1]),'—');
  x.datos.personas[1].activo=false;all(main,y=>y.tag==='button'&&text(y)==='Este mes')[0].events.click();assert(!text(main).includes('high'));assert(!text(main).includes('low'));
 });
 await check('inventory covers34real original functions with exactsource hash',()=>{const crypto=require('node:crypto'),source=fs.readFileSync('/Users/tomassala/Downloads/PANEL_OPERACIONES_2026-10-01/plantilla.html'),doc=fs.readFileSync(__dirname+'/../447_PARIDAD_FUNCIONAL_Y_ORDEN_HORAS_CODEX.md','utf8'),functions=[...source.toString().matchAll(/function (v\w+|abrirFicha)\(/g)].map(x=>x[1]);assert.equal(functions.length,34);assert.equal(crypto.createHash('sha256').update(source).digest('hex'),'468e796d0dab7e8b366ba37c97d0a1e1c7b93b9e82e79ea967ccd6aefa2e01a5');for(const fn of functions)assert(doc.includes('|'+fn+'|'),fn);assert(source.toString().includes('sort((x,y)=>x.p-y.p)'));});
 console.log(n+' grupos447 PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
