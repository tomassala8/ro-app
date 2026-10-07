const fs=require('fs'),vm=require('vm'),assert=require('assert');
class El {constructor(tag,attrs,...children){this.tag=tag;this.attrs=attrs||{};this.children=children.flat().filter(x=>x!=null);this.isConnected=true;this.events={};this.open=false;}append(...x){this.children.push(...x);}replaceChildren(...x){this.children=x;}addEventListener(k,f){this.events[k]=f;}}
const h=(...x)=>new El(...x),text=n=>n&&typeof n==='object'?(n.children||[]).map(text).join(' '):String(n??''),all=n=>n&&typeof n==='object'?[n,...(n.children||[]).flatMap(all)]:[];
const s={h,Date,Intl,Map,Set,JSON,Number,String,Array,Object,Promise,console,panel:(o,n)=>h('section',{},h('h2',{},o.titulo),o.sub,n),tablaDensa:()=>h('table',{}),panelRituales269:async()=>{},chipEstado:()=>h('i',{})};
vm.createContext(s);// Dependencia real392 aislada: evita colisiones de declaraciones con265, sin mocks.
const declarativo392=fs.readFileSync(__dirname+'/modulos/_rastro_declarativo_392.js','utf8').replace(/^import[^;]+;\s*/gm,'').replace(/export /g,'');
vm.runInContext('(function(){'+declarativo392+';globalThis.renderRastroDeclarativo392=renderRastroDeclarativo392;})();',s);
vm.runInContext(fs.readFileSync(__dirname+'/modulos/_operaciones_dia_direccion_265.js','utf8').replace(/^import .*;\n/gm,'').replace(/export /g,''),s);
const p={id:'mili',estado:'activo',activo:true,puestos:['operaciones'],nombre:'Persona autorizada'};
function ctx(){return {real:{...p},persona:{...p},datos:{personas:[{...p}]},clientes:[{id:'ok',activo_confirmado:true,detalle:true},{id:'baja',activo_confirmado:false,detalle:true}],clientesVisibles:[{id:'ok',nombre:'Cliente permitido',activo_confirmado:true,detalle:true}],ver:x=>({ok:x.cliente_id==='ok'}),veModulo:()=>true,vigente:()=>true,servidor:true,datosModulo:async()=>({}),api:async()=>({})};}
const row=(x={})=>({creada:'2026-10-02 23:10:00',quien:'mili',accion:'leer',coleccion:'tareas',datos:'{"cliente_id":"ok"}',...x});
const now=Date.parse('2026-10-04T12:00:00Z');let cases=0;
(async()=>{
 let c=ctx(),d=s.porDia379(c,[row()],now);assert.equal(d[0].dia,'2026-10-03');assert.equal(d[0].filas[0].cuando,'03/10/2026, 01:10 · Madrid');assert.equal(d[0].filas[0].quien,'Persona autorizada');cases++;
 for(const id of ['ajeno','baja','missing',23,''])assert.equal(s.porDia379(c,[row({datos:JSON.stringify({cliente_id:id})})],now).length,0);
 assert.equal(s.porDia379(c,[row({cliente_id:'other'})],now).length,0);cases++;
 c.clientes.push({id:'ok',activo_confirmado:false});assert.equal(s.porDia379(c,[row()],now).length,0);c=ctx();c.clientesVisibles.push({...c.clientesVisibles[0]});assert.equal(s.porDia379(c,[row()],now).length,0);cases++;
 c=ctx();c.clientes[0].activo_confirmado=false;assert.equal(s.porDia379(c,[row()],now).length,0);cases++;
 c=ctx();for(const stamp of ['2026-02-30','2026-10-02evil','2026-10-02T24:00:00Z','2026-10-10 00:00:00','???']) {d=s.porDia379(c,[row({creada:stamp})],now);assert.equal(d[0].dia,'Fecha sin confirmar');assert.equal(d[0].n,1);assert.equal(d[0].filas.length,0);}cases++;
 d=s.porDia379(c,[row({quien:{id:'mili'}}),row({quien:'untrusted'})],now);assert(d[0].filas.every(x=>x.quien==='Autor sin confirmar'));c.datos.personas.push({...p});assert.equal(s.porDia379(c,[row()],now)[0].filas[0].quien,'Autor sin confirmar');cases++;
 c=ctx();assert.equal(s.porDia379(c,[row({datos:'bad'}),row({datos:'[]'})],now).length,0);d=s.porDia379(c,[row({estado:'hecho',nota:'PRIVATE',datos:'{"cliente_id":"ok","secret":"PRIVATE"}',accion:'password:secret'})],now);assert(!JSON.stringify(d).includes('PRIVATE'));assert.equal(d[0].filas[0].que,'Sin dato confirmado');cases++;
 const render=async(change)=>{const c=ctx(),calls=[];c.api=async path=>{calls.push(path);return path==='rastro'?{registro:[row()]}:{};};const root=h('main',{});await s.renderDiaDireccion265(root,c,'rastro');assert.deepEqual(calls,['decisiones','rastro']);const detail=all(root).find(n=>n.tag==='details');assert(detail);assert(!text(root).includes('Persona autorizada'));assert(!detail.open);detail.open=true;detail.events.toggle();assert(text(root).includes('Persona autorizada'));assert(text(root).includes('Cuándo'));assert(!text(root).includes('PRIVATE'));if(change){change(c,root);detail.events.toggle();assert(!text(root).includes('Persona autorizada'));}return{c,root,detail};};
 const visible=await render();assert(text(visible.root).includes('Cliente permitido'));cases++;
 for(const change of [c=>c.real.id='other',c=>c.datos.personas[0].estado='baja',c=>c.datos.personas[0].puestos=[],c=>c.veModulo=()=>false,c=>c.clientes[0].activo_confirmado=false,c=>c.clientesVisibles[0].activo_confirmado=false,c=>c.ver=()=>({ok:false}),c=>c.datos.personas.push({...p})])await render(change);cases++;
 c=ctx();c.veModulo=id=>id!=='decisiones';let reads=0;c.api=c.datosModulo=async()=>{reads++;return{};};const root=h('main',{});await s.renderDiaDireccion265(root,c,'rastro');assert.equal(reads,0);cases++;
 c=ctx();c.api=async path=>{if(path==='rastro'){c.datos.personas[0].puestos=[];return{registro:[row()]};}return{};};const stale=h('main',{});await s.renderDiaDireccion265(stale,c,'rastro');assert(!text(stale).includes('Persona autorizada'));assert(!all(stale).some(x=>x.tag==='details'));cases++;
 c=ctx();delete c.real.id;delete c.persona.id;delete c.datos.personas[0].id;reads=0;c.api=c.datosModulo=async()=>{reads++;return{};};await s.renderDiaDireccion265(h('main',{}),c,'rastro');assert.equal(reads,0);cases++;
 c=ctx();c.real.puestos=['direccion'];reads=0;c.api=c.datosModulo=async()=>{reads++;return{};};await s.renderDiaDireccion265(h('main',{}),c,'rastro');assert.equal(reads,0);cases++;
 console.log(`${cases} grupos379 PASS: scope exacto, fechas Madrid, unknown, datos no publicados, detalles plegados y revocación.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
