// Independiente: imports ESM reales en directorio temporal; sin servidor ni proveedor.
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ro390b-'));fs.chmodSync(dir,0o700);
for(const n of ['_historial_diario_364','_bandas_horas_381','_imputa_personal_390'])fs.writeFileSync(path.join(dir,n+'.mjs'),fs.readFileSync(path.join(__dirname,'modulos',n+'.js'),'utf8').replace(/from '\.\/([^']+)\.js'/g,"from './$1.mjs'"));
const clone=x=>JSON.parse(JSON.stringify(x));
function doc(values={},zona='Europe/Madrid',fuente='2026-10-05T00:30:00Z'){
 const cut='2026-10-05',dias=Array.from({length:90},(_,i)=>{const f=new Date(Date.parse(cut+'T00:00:00Z')-(90-i)*864e5).toISOString().slice(0,10),ok=Object.hasOwn(values,f);return {fecha:f,horas:ok?values[f]:null,entradas:ok?1:null,estado:ok?'observado':'sin_dato'};});
 return {version:'362.1',estado:'copia_observada',generado:'2026-10-05T01:00:00Z',fuente:'ClickUp entradas',fuente_version:'359.1',sha256_candidato:'21abf5db866bfd0ed9805b61bf686a625f613d37d21ce80095ef998f209f6280',cobertura:'parcial',unidad:'h',cumplimiento:null,capacidad_contractual:null,personas:[{persona_id:'acc',historial_diario:{version:'359.1',fuente:'ClickUp entradas',cobertura:'parcial',unidad:'h',zona,zona_confirmada:true,desde:dias[0].fecha,hasta:dias.at(-1).fecha,corte_fecha:cut,fecha_fuente_utc:fuente,atribucion:'inicio',duracion_cerrada_confirmada:false,sin_registros_no_equivale_a_cero:true,dias}}]};
}
function contexto(d=doc()){
 const a={id:'ops',estado:'activo',puestos:['operaciones']},b={id:'acc',estado:'activo',puestos:['account']};
 return {servidor:true,hoy:'2026-10-05',real:clone(a),persona:clone(a),datos:{personas:[clone(a),clone(b)]},veModulo:m=>m==='horas',vigente:()=>true,ver:q=>({ok:q.tipo==='horas_persona'}),api:async()=>d};
}
let n=0;const fallos=[];const test=async(name,f)=>{try{await f();n++;}catch(e){fallos.push(name);}};
(async()=>{try{
 const M=await import('file://'+path.join(dir,'_imputa_personal_390.mjs'));
 await test('unknown vs explicit zero',async()=>{for(const [v,w] of [[{},null],[{'2026-10-03':0},0]]){const c=contexto(doc(v)),m=await M.cargarImputa390(c,['acc']);assert.equal(M.celdaImputa390(c,m,'acc').total,w);}});
 await test('local midnight read day excluded across zones',async()=>{for(const [zone,want] of [['Europe/Madrid',11],['America/Argentina/Buenos_Aires',1],['Pacific/Kiritimati',11]]){const c=contexto(doc({'2026-10-03':1,'2026-10-04':10},zone)),m=await M.cargarImputa390(c,['acc']);assert.equal(M.celdaImputa390(c,m,'acc').total,want);}});
 await test('stale copy never fills absent dates with zero',async()=>{const d=doc({'2026-09-30':3,'2026-10-01':80,'2026-10-04':90},'Europe/Madrid','2026-10-01T12:00:00Z'),c=contexto(d),m=await M.cargarImputa390(c,['acc']);const x=M.celdaImputa390(c,m,'acc');assert.equal(x.total,3);assert.equal(x.observadas,1);assert(x.detalle.includes('1/7'));});
 await test('sum overflow unknown',async()=>{const c=contexto(doc({'2026-10-01':Number.MAX_VALUE,'2026-10-02':Number.MAX_VALUE})),m=await M.cargarImputa390(c,['acc']);assert.equal(M.celdaImputa390(c,m,'acc').total,null);});
 await test('canonical target roles must be typed unique beforeGET',async()=>{for(const roles of [['account','account'],['account',12],['account','']]){const c=contexto();c.datos.personas[1].puestos=roles;let calls=0;c.api=async()=>{calls++;return doc()};assert.equal(await M.cargarImputa390(c,['acc']),null);assert.equal(calls,0);}});
 await test('actor duplicate roles and stale snapshot deny',async()=>{for(const cambio of [c=>{for(const p of [c.real,c.persona,c.datos.personas[0]])p.puestos=['operaciones','operaciones']},c=>c.real.puestos=['direccion'],c=>c.datos.personas.push(clone(c.real))]){const c=contexto();cambio(c);let calls=0;c.api=async()=>{calls++;return doc()};assert.equal(await M.cargarImputa390(c,['acc']),null);assert.equal(calls,0);}});
 await test('grant or target membership changed duringawait',async()=>{for(const cambio of [c=>c.ver=()=>({ok:false}),c=>c.datos.personas[1].puestos=['seo'],c=>c.datos.personas[1].estado='baja',c=>c.persona.id='acc',c=>c.hoy='2026-10-06']){const c=contexto(doc({'2026-10-03':8}));c.api=async()=>{cambio(c);return doc({'2026-10-03':8})};assert.equal(await M.cargarImputa390(c,['acc']),null);}});
 await test('callback revoked no lingering total',async()=>{const c=contexto(doc({'2026-10-03':8})),m=await M.cargarImputa390(c,['acc']);c.datos.personas.splice(1);assert(!M.imputaVigente390(c,m));assert.equal(M.celdaImputa390(c,m,'acc').total,null);});
 await test('bad source sequence and timestamps reject',async()=>{for(const change of [d=>d.personas[0].historial_diario.dias[89].fecha='2026-02-30',d=>d.personas[0].historial_diario.fecha_fuente_utc='2026-10-05T24:00:00Z',d=>d.personas[0].historial_diario.zona='Fake/Zone',d=>d.personas.push(clone(d.personas[0]))]){const d=doc({'2026-10-03':8});change(d);assert.equal(await M.cargarImputa390(contexto(d),['acc']),null);}});
 console.log(n+' grupos independientes390B PASS · roles/fechas/zonas/null/overflow/lectura364.');if(fallos.length)throw Error('Fallos: '+fallos.join('; '));
}finally{fs.rmSync(dir,{recursive:true,force:true});}})().catch(e=>{console.error(e.message);process.exitCode=1});
