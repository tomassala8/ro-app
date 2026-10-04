const fs=require('node:fs'),assert=require('node:assert/strict'),vm=require('node:vm');
class N{constructor(t,a={},xs=[]){this.tag=t;this.attrs=a;this.events=a.on||{};this.children=[];this.append(...xs)}get isConnected(){return this.connected===true||!!this.parent?.isConnected}append(...xs){for(const x of xs.flat(Infinity)){if(x==null)continue;if(x instanceof N)x.parent=this;this.children.push(x)}}replaceChildren(...xs){this.children=[];this.append(...xs)}addEventListener(k,f){this.events[k]=f}get textContent(){return this.children.map(x=>x instanceof N?x.textContent:String(x)).join(' ')}}
const h=(t,a,...xs)=>new N(t,a,xs),all=x=>x instanceof N?[x,...x.children.flatMap(all)]:[];
let n=0;const check=f=>{f();n++};
(async()=>{const M=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(__dirname+'/modulos/_objetivos_seo_374.js','utf8')).toString('base64'));
const make=()=>{const p={id:'seo',estado:'activo',puestos:['seo']};return {servidor:true,real:structuredClone(p),persona:structuredClone(p),datos:{personas:[structuredClone(p)]},hoy:'2026-10-03',clientes:[{id:'c',nombre:'Fixture',activo_confirmado:true,detalle:true}],clientesVisibles:[{id:'c',nombre:'Fixture',activo_confirmado:true,detalle:true}],veModulo:()=>true,ver:()=>({ok:true}),vigente:()=>true}};
const row={consulta:'asesoria ciudad',servicio:'asesoria',ciudad:'Ciudad',canal:'organico',posicion:1,fecha:'2026-10-02',dispositivo:null,ubicacion_medicion:null,medicion_id:'engine-1',objetivo_local_acreditado:false};
const dto=()=>({fecha:'2026-10-03',clientes:[{cliente_id:'c',habilitado:true,objetivos:[{...row}]}]});
const carga=(c,d=dto())=>({estado:'leido',firma:M.ambitoObjetivos374(c)?.firma,datos:d});
const mount=(c,d)=>{const parent=h('main',{});parent.connected=true;const r=M.renderObjetivos374(h,c,d);parent.append(r);return r};
let c=make(),d=carga(c),r=mount(c,d);
check(()=>{assert(r.textContent.includes('Fixture'));assert(r.textContent.includes('Ciudad'));assert(r.textContent.includes('asesoria'));assert(r.textContent.includes('#1 aspiracional'));assert(r.textContent.includes('Sin dato'));assert(r.textContent.includes('2026-10-02'));assert(!r.textContent.includes('cumplido'));assert.equal(all(r).filter(x=>x.tag==='th').length,7)});
check(()=>{const t=M.modeloObjetivos374(c,d)[0];assert.equal(t.organico.valor,1);assert.equal(t.maps.valor,null);assert.equal(t.ciudad_id,null);assert(!t.organico.acreditada)});
check(()=>{const src=dto();src.clientes[0].objetivos.push({...row,posicion:2});assert.equal(M.modeloObjetivos374(c,carga(c,src))[0].organico.valor,null)});
check(()=>{const src=dto();src.clientes[0].objetivos=[{...row,consulta_medida:'asesoria ciudad',posicion:6},{...row,consulta_medida:'Asesoría Ciudad',posicion:28}];const rs=M.modeloObjetivos374(c,carga(c,src));assert.equal(rs.length,2);assert.deepEqual(rs.map(x=>x.organico.valor),[6,28]);assert.equal(rs[1].consulta,'Asesoría Ciudad');assert.equal(rs[1].consulta_objetivo,'asesoria ciudad')});
check(()=>{const src=dto();src.clientes[0].objetivos=[{...row,fuente:'A',posicion:6},{...row,fuente:'B',posicion:28}];assert.deepEqual(M.modeloObjetivos374(c,carga(c,src)).map(x=>x.organico.valor),[6,28])});
check(()=>{const src=dto();src.clientes.push({...src.clientes[0]});assert.equal(M.modeloObjetivos374(c,carga(c,src)).length,0)});
check(()=>{const src=dto();src.clientes[0].cliente_id='foreign';assert.equal(M.modeloObjetivos374(c,carga(c,src)).length,0)});
check(()=>{const src=dto();src.clientes[0].objetivos[0].fecha='2026-99-99';assert.equal(M.modeloObjetivos374(c,carga(c,src))[0].organico.valor,null)});
check(()=>{const src=dto();src.fecha='2026-10-04';assert.equal(M.modeloObjetivos374(c,carga(c,src)).length,0)});
const historical={cliente_id:'c',habilitado:false,objetivos:[],objetivos_historicos:[{tipo:'Ciudad documentada',valor:'Ciudad histórica',fecha_documento:'2026-07-22',activar_consultas:false,benchmark_confirmado:false,razones:['Documento previo; confirmar vigencia']},{tipo:'Servicio del brief',valor:'laboral',fecha_documento:'2026-07-22',activar_consultas:false,benchmark_confirmado:false,razones:[]}]};
check(()=>{const src={fecha:'2026-10-03',clientes:[historical]},rr=mount(c,carga(c,src));assert(rr.textContent.includes('Ciudad histórica'));assert(rr.textContent.includes('laboral'));assert(rr.textContent.includes('histórico'));assert(rr.textContent.includes('Consultas actuales pendientes'));assert(!M.modeloObjetivos374(c,carga(c,src))[0].organico.valor)});
check(()=>{const src={fecha:'2026-10-03',clientes:[{...historical,objetivos_historicos:[{...historical.objetivos_historicos[0],valor:'token secret'}]}]};assert(!mount(c,carga(c,src)).textContent.includes('token secret'))});
for(const alter of [c=>c.datos.personas[0].estado='baja',c=>c.datos.personas.push({...c.datos.personas[0]}),c=>c.persona.puestos=['account'],c=>c.veModulo=m=>m!=='prioridades-cliente',c=>c.ver=()=>({ok:false}),c=>c.clientesVisibles[0].activo_confirmado=false,c=>c.clientesVisibles.push({...c.clientesVisibles[0]})]){const z=make(),before=carga(z);alter(z);check(()=>assert.equal(M.modeloObjetivos374(z,before).length,0))}
let done,calls=0;c=make();c.api=()=>{calls++;return new Promise(resolve=>done=resolve)};const pending=M.cargarObjetivos374(c);c.ver=()=>({ok:false});done(dto());let out=await pending;check(()=>{assert.equal(out.estado,'revocado');assert.equal(out.datos,null)});
c=make();c.real.estado='baja';c.api=()=>calls++;await M.cargarObjetivos374(c);check(()=>assert.equal(calls,1));
c=make();c.api=async route=>{assert.equal(route,'cerebro/seo');return dto()};out=await M.cargarObjetivos374(c);check(()=>assert.equal(out.estado,'leido'));
c=make();d=carga(c);r=mount(c,d);const details=all(r).find(x=>x.tag==='details'),a=all(r).find(x=>x.tag==='a');c.ver=()=>({ok:false});let prevented=false;a.events.click({preventDefault:()=>prevented=true});check(()=>{assert(prevented);assert(!r.textContent.includes('Fixture'))});
c=make();r=mount(c,carga(c));c.datos.personas[0].activo=false;all(r).find(x=>x.tag==='details').events.toggle();check(()=>assert(!r.textContent.includes('Fixture')));
// Consulta autorizada ver como: ambos actores canónicos; el DTO nunca amplía clientes.
c=make();const real={id:'dir',estado:'activo',puestos:['direccion']};c.real=real;c.datos.personas.push(structuredClone(real));c.api=async()=>dto();out=await M.cargarObjetivos374(c);check(()=>{assert.equal(out.estado,'leido');assert.equal(M.modeloObjetivos374(c,out).length,1)});
let finish;c=make();c.api=()=>new Promise(resolve=>finish=resolve);const identityAwait=M.cargarObjetivos374(c);c.real=real;c.datos.personas.push(structuredClone(real));finish(dto());out=await identityAwait;check(()=>{assert.equal(out.estado,'revocado');assert.equal(out.datos,null)});
// El módulo real engancha la celda objetivo y la matriz en cartera y detalle.
const src=fs.readFileSync(__dirname+'/modulos/seo.js','utf8');check(()=>{assert(src.includes('cargarObjetivos374(ctx)'));assert(src.includes('renderObjetivos374(h,ctx,d.objetivos374)'));assert(src.includes('renderObjetivos374(h,ctx,d.objetivos374,f.cliente_id)'));assert(src.includes('const objetivo=celdaObjetivo374(h,ctx,d.objetivos374,f.cliente_id)'))});
console.log(n+' grupos374 PASS: modelo/render real, fuente, histórico, scope/await/toggle/links.');})().catch(e=>{console.error(e);process.exitCode=1});

// Pintor SEO real con dependencia374 real y DTO autorizado no vacío.
const baseline374=fs.readFileSync(__dirname+'/probar_seo_oportunidades_332.cjs','utf8').split('c=ctx();Object.assign(c,{clientes:c.clientesVisibles')[0];
new Function('require','__dirname',baseline374+String.raw`
N.prototype.addEventListener=function(k,f){this.attrs.on ||= {};this.attrs.on[k]=f;};
c=ctx();Object.assign(c,{clientes:c.clientesVisibles,carteraIds:new Set(['c']),nombre:()=>null,soloLectura:true});
const rr={...f,cliente:'Fixture',seo_id:'seo',estado:'gris',alertas:[],_medicionSEO:{clics:{mes:true}},informe15:[],motivo:'Partial',n_alertas:{},seranking:null};
const loaded={estado:'leido',firma:s.ambitoObjetivos374?s.ambitoObjetivos374(c)?.firma:null,datos:{fecha:'2026-10-03',clientes:[{cliente_id:'c',habilitado:true,objetivos:[{consulta:'asesoria ciudad',servicio:'asesoria',ciudad:'Ciudad',canal:'organico',posicion:1,fecha:'2026-10-02'}]}]}};
// Obtiene scope desde helperreal en cierre propio, sin stub de permisos.
loaded.firma=vm.runInContext('(()=>{'+fs.readFileSync(__dirname+'/modulos/_objetivos_seo_374.js','utf8').replace(/export /g,'')+';return ambitoObjetivos374;})()',s)(c).firma;
const dd={seo:{_meta:meta},oportunidadesScope332:s.ambitoOportunidades332(c).firma,objetivos374:loaded},zone=h('root');s.pintarSeo(zone,c,dd,[rr],'seo');
assert(text(zone).includes('#1 · Ciudad'));assert(text(zone).includes('Objetivos locales · #1 aspiracional'));assert(text(zone).includes('asesoria ciudad'));assert(!text(zone).includes('objetivo cumplido'));
console.log('374 pintor SEO real + DTO objetivo confirmado PASS');
`)(require,__dirname);
