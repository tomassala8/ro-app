const fs=require('fs'), vm=require('vm'), assert=require('assert');
const src=fs.readFileSync('modulos/ficha_equipo.js','utf8');
const bloque=(nombre)=>src.slice(src.indexOf('export function '+nombre),src.indexOf('\n/**',src.indexOf('export function '+nombre)+1)).replace('export function','function');
function h(tag,attrs={},...children){return {tag,attrs,children:children.flat(Infinity).filter(x=>x!=null)};}
const context={h,icono:x=>x,menuMas:x=>({menu:x}),fuente:(d,k)=>d?.fuentes?.[k],SILLA:{trafficker:{texto:'Publicidad'},crm:{texto:'CRM'},web:{texto:'Web'},seo:{texto:'SEO'},redes:{texto:'Redes'},account:{texto:'Account'}}};
vm.createContext(context);vm.runInContext(bloque('equipoAvisable')+'\n'+bloque('botonAvisar')+'\nthis.eq=equipoAvisable;this.bt=botonAvisar;',context);
function fixture(){const a={id:'acc',nombre:'Account fixture',estado:'activo',activo:true,puestos:['account']}, t={id:'traf',nombre:'Persona fixture',estado:'activo',activo:true,puestos:['trafficker']}; const c={id:'cliente-fixture',nombre:'Cliente fixture',activo_confirmado:true,detalle:true,equipo:{account:[{persona_id:'acc',principal:true}],trafficker:[{persona_id:'traf',principal:true}]}}; const ctx={real:a,persona:a,datos:{personas:[a,t]},clientes:[c],clientesVisibles:[c],vigente:()=>true,ver:()=>({ok:true}),nombre:id=>ctx.datos.personas.find(p=>p.id===id)?.nombre||id};const F={c,verdad:{equipo:{account:[{persona_id:'acc'}]}},doc:{fuentes:{asignaciones:{datos:{sillas:{account:'acc'}}}}}};return {ctx,F,c,t,a};}
let n=0;function test(name,f){f();n++;console.log('PASS',name)}
test('baseline reproduce silla ajena ausente en verdad/asignaciones',()=>{const {F}=fixture(); const old=Object.keys(context.SILLA).flatMap(s=>(F.verdad.equipo[s]||[]).length?F.verdad.equipo[s]:(F.doc.fuentes.asignaciones.datos.sillas[s]?[{persona_id:F.doc.fuentes.asignaciones.datos.sillas[s]}]:[])).filter(x=>x.persona_id!=='acc');assert.equal(old.length,0)});
test('respaldo autorizado recupera trafficker sin correos/contactos',()=>{const {ctx,F}=fixture();const r=context.eq(ctx,F);assert.equal(r.length,1);assert.equal(r[0].pid,'traf');assert.deepEqual(Object.keys(r[0]).sort(),['completo','nombre','pid','principal','silla']);});
test('prioridad verdad no mezcla personas adicionales de silla',()=>{const {ctx,F}=fixture();F.verdad.equipo.trafficker=[{persona_id:'acc'}];assert.equal(context.eq(ctx,F).length,0)});
test('sin equipo permitido no infiere desde directorio',()=>{const {ctx,F,c}=fixture();delete c.equipo;assert.equal(context.eq(ctx,F).length,0)});
for(const [name,mut] of Object.entries({detalle:q=>q.ctx.ver=()=>({ok:false}),ACT:q=>q.c.activo_confirmado=false,clienteDuplicado:q=>q.ctx.clientes.push({...q.c}),visibleAusente:q=>q.ctx.clientesVisibles=[],vigencia:q=>q.ctx.vigente=()=>false,receptorBaja:q=>q.t.estado='baja',receptorInactivo:q=>q.t.activo=false,receptorDuplicado:q=>q.ctx.datos.personas.push({...q.t}),receptorAusente:q=>q.ctx.datos.personas.pop(),actorBaja:q=>q.a.estado='baja',actorDuplicado:q=>q.ctx.datos.personas.push({...q.a}),vistaRoles:q=>q.ctx.persona={...q.a,puestos:['direccion']}})) test('deny '+name,()=>{const q=fixture();mut(q);assert.equal(context.eq(q.ctx,q.F).length,0)});
test('dedup por silla',()=>{const {ctx,F,c}=fixture();c.equipo.trafficker.push({...c.equipo.trafficker[0]});assert.equal(context.eq(ctx,F).length,1)});
test('botón abre compositor sólo si continúa autorizado',()=>{const {ctx,F}=fixture();let called=0;const btn=context.bt(ctx,F,()=>called++);btn.children[0].attrs.on.click();assert.equal(called,1);ctx.ver=()=>({ok:false});btn.children[0].attrs.on.click();assert.equal(called,1)});
test('revocación de receptor tras construir bloquea callback',()=>{const {ctx,F,t}=fixture();let called=0;const btn=context.bt(ctx,F,()=>called++);t.estado='baja';btn.children[0].attrs.on.click();assert.equal(called,0)});
test('ver como conserva ambos actores, no concede detalle',()=>{const {ctx,F}=fixture();const view={id:'ops',estado:'activo',activo:true,puestos:['operaciones'],nombre:'Vista fixture'};ctx.persona=view;ctx.datos.personas.push(view);assert.equal(context.eq(ctx,F).length,1);ctx.ver=()=>({ok:false});assert.equal(context.eq(ctx,F).length,0)});
test('fallback antiguo autorizado sigue utilizable',()=>{const {ctx,F,c}=fixture();delete c.equipo;F.doc.fuentes.asignaciones.datos.sillas.trafficker='traf';assert.equal(context.eq(ctx,F).length,1)});
test('contrato fuente real publica equipo sólo en DETALLE y directorio sin correo',()=>{const p=fs.readFileSync('permisos.py','utf8');assert.match(p,/DETALLE = \[[\s\S]*?"equipo"/);assert.match(p,/if out\["detalle"\]:[\s\S]*?for k in DETALLE:/);const pub=p.match(/PERSONA_PUBLICA = \[([^\]]+)\]/)[1];assert(!pub.includes('correo'));assert(!pub.includes('telefono'));});
test('recortar real: equipo detalle visible mientras asignaciones son sólo propias',()=>{
 const py=String.raw`import ast,json
from pathlib import Path
arbol=ast.parse(Path('permisos.py').read_text())
ns={'contexto':lambda p,d:{'cartera_ids':{'cliente-fixture'},'cartera_por_silla':{'account':{'cliente-fixture'}}},'ver':lambda p,d,cp:{'ok':d['tipo']=='cliente_detalle'},'solo_su_cartera':lambda p:True,'ambito':lambda p:'suyo','importes_a_quitar':lambda *a:(),'sin_importes':lambda x,q:x}
nodos=[x for x in arbol.body if isinstance(x,ast.FunctionDef) and x.name in {'recortar','directorio','meta_de_cartera'} or isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'COMUNES','DETALLE','PERSONA_PUBLICA'} for t in x.targets)]
exec(compile(ast.Module(body=nodos,type_ignores=[]),'permisos.py','exec'),ns)
a={'id':'acc','nombre':'Account fixture','puestos':['account'],'estado':'activo','activo':True}
t={'id':'traf','nombre':'Persona fixture','puestos':['trafficker'],'estado':'activo','activo':True,'correo':'PRIVATE-SYNTHETIC'}
c={'id':'cliente-fixture','nombre':'Cliente fixture','activo_confirmado':True,'responsable_id':'acc','equipo':{'trafficker':[{'persona_id':'traf','principal':True}]}}
d={'personas':[a,t],'clientes':[c],'logos':{},'alarmas':[],'asignaciones':[{'cliente_id':c['id'],'persona_id':'acc'},{'cliente_id':c['id'],'persona_id':'traf'}],'meta':{}}
r=ns['recortar'](a,d)
assert len(r['asignaciones'])==1
assert r['clientes'][0]['equipo']['trafficker'][0]['persona_id']=='traf'
assert 'correo' not in r['personas'][1]
ns['ver']=lambda *a:{'ok':False}
assert 'equipo' not in ns['recortar'](a,d)['clientes'][0]
print('ok')`;
 const run=require('child_process').spawnSync('python3',['-c',py],{encoding:'utf8'});assert.equal(run.status,0,run.stderr);assert.equal(run.stdout.trim(),'ok');
});
console.log(n+' grupos PASS602; ningún envío/API/DB');
