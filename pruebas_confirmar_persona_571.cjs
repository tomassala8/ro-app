// Renderer real extraído; transporte fixture, ninguna escritura al runtime.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'modulos/ajustes.js'),'utf8');
const fn=source.slice(source.indexOf('function tarjetaDuda('),source.indexOf('// ---------------------------------------------------------------- Ver como'));
const posts=[];
function h(tag,props,...children){return {tag,props:props||{},value:props?.value||'',children:children.flat(Infinity).filter(x=>x!=null)};}
const env={h,campo:(label,node)=>h('label',{},label,node),chipEstado:()=>h('span',{}),fmt:{fecha:x=>x},
 botonConfirmar:op=>({tag:'button',props:op,children:[]}),post:async(ctx,url,body)=>{posts.push({ctx,url,body});return {ok:true};},SILLAS_NOMBRE:{}};
vm.createContext(env);vm.runInContext(fn+';this.render=tarjetaDuda;',env);
function nodes(n){return typeof n==='object'&&n?[n,...(n.children||[]).flatMap(nodes)]:[];}
function render(edit){return env.render({id:'d-fixture',tipo:'persona',persona_id:'p-fixture',objeto:'Fixture',choque:'Contraste'}, {},edit,{'p-fixture':'Persona fixture'}, {},[],{personas:[]},null);}
(async()=>{
 const tree=render(true),all=nodes(tree),select=all.find(n=>n.tag==='select');
 assert.equal(select.props.disabled,false);
 assert.deepEqual(nodes(select).filter(n=>n.tag==='option').map(n=>n.props.value),['','activo','dudoso']);
 const button=all.find(n=>n.tag==='button');
 for(const estado of ['activo','dudoso']){
  select.value=estado;await button.props.alConfirmar();
  const actual=JSON.parse(JSON.stringify(posts.at(-1)));
  assert.equal(actual.url,'ajustes/confirmar');
  assert.deepEqual(actual.body,{respuesta:{duda:'d-fixture',tipo:'persona',persona_id:'p-fixture',cambios:{estado}}});
 }
 select.value='';await assert.rejects(button.props.alConfirmar(),/elige una opción/);
 const readonly=nodes(render(false));
 assert.equal(readonly.find(n=>n.tag==='select').props.disabled,true);
 assert.equal(readonly.some(n=>n.tag==='button'),false);
 assert.equal(posts.length,2);
 // Otras rutas y controles permanecen presentes, sin extraer ni ejecutar sus envíos.
 assert.match(source,/id: 'altas', texto: 'Altas y bajas'/);
 console.log('571: 3 grupos PASS (opciones/payload y nota vacía/solo lectura).');
})().catch(e=>{console.error(e);process.exitCode=1;});
