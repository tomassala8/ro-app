const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync('modulos/ficha.js','utf8');
const helper=fs.readFileSync('modulos/_contexto_ficha_233.js','utf8').replace(/export /g,'');
class N{constructor(tag,...xs){this.tag=tag;this.children=xs.flat().filter(x=>x!=null);this.isConnected=true;}append(...xs){this.children.push(...xs.flat());}replaceChildren(...xs){this.children=xs.flat();}querySelector(){return null;}}
const h=(tag,attrs,...xs)=>new N(tag,...xs),text=n=>typeof n==='string'?n:(n?.children||[]).map(text).join(' ');
const defer=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
let privado='private-dir',fetches=0;const frames=[];
const box={h,URLSearchParams,console,setTimeout,location:{hash:'#/ficha/c/resumen'},history:{replaceState(){}},
 document:{addEventListener(){},removeEventListener(){}},window:{},
 fetch:async()=>{fetches++;return{ok:true,json:async()=>({valor:privado})};},
 vigilarCortes(){},estilosIA(){},ses:{leer:()=>null,poner(){}},CLAVE_ULTIMO:'k',
 ORDEN:{account:['resumen']},PESTANAS:{resumen:{texto:'Resumen'}},perfil:()=> 'account',
 serviciosActivos:()=>[],pestanaConSentido:()=>true,pestanaFicha:()=> 'resumen',selectorCliente:()=>h('selector'),detalleSelector(){},
 TITULO_CORTO:()=>true,esqueleto:()=>h('loading'),vacio:o=>h('empty',{},o.titulo),icono:()=>'',
 cargarObjetivos:async()=>new Map(),medicionDe:()=>[],contadores:()=>({}),bloqueMedicion:()=>null,
 cabecera:(ctx,F)=>{frames.push(F);return h('header',{},F.doc.marca,F.portal?.marca,F.contactos.valor);},
 PINTAR:{resumen:()=>{}},pestanas:o=>{const z=h('tab');o.pintar('resumen',z);return z;},plegarConsejo(){},motivoSinCartera:()=>'',
};
vm.createContext(box);vm.runInContext(helper,box);
vm.runInContext(src.slice(src.indexOf('async function cargarCliente'),src.indexOf('// =================================================================== render')),box);
const render=src.slice(src.indexOf('  async render(cont, ctx) {'),src.indexOf('// =================================================================== cabecera')).replace(/^  async render/,'async function render').replace(/,\n};\s*$/,'');
vm.runInContext(render,box);
function context(identity='dir'){
 const c={id:'c',nombre:'Synthetic',detalle:true};
 return {real:{id:identity,puestos:['account']},persona:{id:identity,puestos:['account']},params:['c','resumen'],
 servidor:true,clientes:[c],clientesVisibles:[c],datos:{alarmas:[]},ver:()=>({ok:true}),veModulo:()=>true,vigente:()=>true,
 verDato:async()=>{fetches++;return{valor:privado};},api:async()=>({fuentes:{marca:identity}}),datosModulo:async()=>({filas:[{cliente_id:'c',marca:identity}]}),titulo(){},navegar(){},accion:async()=>({ok:true})};
}
(async()=>{
 let count=0;
 const a=context(),root=h('root'),sa=box.contextoFicha233(a,root,'c');
 a.api=async()=>{count++;return{fuentes:{marca:'direction-money'}}};
 assert.equal((await box.cargarCliente(sa,'c')).marca,'direction-money');
 const b=context('account'),sb=box.contextoFicha233(b,h('root'),'c');
 b.api=async()=>{count++;return{fuentes:{marca:'account-safe'}}};
 assert.equal((await box.cargarCliente(sb,'c')).marca,'account-safe');assert.equal(count,2);
 assert.equal((await box.cargarModulo(sa,'ficha/portal')).filas[0].marca,'dir');
 assert.equal((await box.cargarModulo(sb,'ficha/portal')).filas[0].marca,'account');
 assert.equal((await box.cargarPrivado(sa,'contactos','c')).valor,'private-dir');
 privado='private-account';assert.equal((await box.cargarPrivado(sb,'contactos','c')).valor,'private-account');assert.equal(fetches,2);
 // Actual orchestration: same client, independent snapshots, no shared money/resource/private data.
 privado='dir-only';await box.render(h('main'),context());
 privado='account-only';await box.render(h('main'),context('account'));
 assert.equal(frames.at(-2).doc.marca,'dir');assert.equal(frames.at(-1).doc.marca,'account');
 assert.equal(frames.at(-1).portal.marca,'account');assert.equal(frames.at(-1).contactos.valor,'account-only');
 // Response from previous render must never reach the real header renderer.
 let alive=true;const late=defer(),old=context();old.vigente=()=>alive;old.api=()=>late.promise;
 const node=h('main'),before=frames.length,p=box.render(node,old);alive=false;late.resolve({fuentes:{marca:'OLD-PRIVATE'}});await p;
 assert.equal(frames.length,before);assert(!text(node).includes('OLD-PRIVATE'));assert.equal(node.children[0].children.length,0);
 for(const revoke of [c=>c.real.id='other',c=>c.persona.puestos.push('seo'),c=>c.clientesVisibles=[],c=>c.ver=()=>({ok:false}),c=>c.veModulo=()=>false]){
  const ctx=context(),r=h('root',{},'already-private'),s=box.contextoFicha233(ctx,r,'c');revoke(ctx);assert.equal(s.vigente(),false);assert.equal(r.children.length,0);await assert.rejects(s.api('cliente/c'));
 }
 const pending=defer(),ctx=context(),r=h('root',{},'private');ctx.api=()=>pending.promise;const guarded=box.contextoFicha233(ctx,r,'c');
 const request=guarded.api('cliente/c');ctx.soloLectura=true;pending.resolve({secret:'synthetic'});await assert.rejects(request);assert.equal(r.children.length,0);
 // Private POST is fully stubbed: permission loss while its JSON is pending discards the value.
 const privateLate=defer(),privateCtx=context(),privateRoot=h('root'),privateGuard=box.contextoFicha233(privateCtx,privateRoot,'c');
 privateCtx.verDato=()=>privateLate.promise;
 const privateRequest=box.cargarPrivado(privateGuard,'contactos','c');await Promise.resolve();
 privateCtx.ver=()=>({ok:false});privateLate.resolve({valor:'LATE-CONTACT'});await assert.rejects(privateRequest);assert.equal(privateRoot.children.length,0);
 const detached=context(),detachedRoot=h('root'),detachedGuard=box.contextoFicha233(detached,detachedRoot,'c');detachedRoot.isConnected=false;assert.equal(detachedGuard.vigente(),false);
 const denied=context('seo');denied.ver=()=>({ok:false});let reads=fetches;assert((await box.cargarPrivado(denied,'chat','c')).negado);assert.equal(fetches,reads);
 assert(!src.includes('CACHE'));console.log('233 PASS: loaders reales, render real, identidad/cartera/roles/módulo/permisos revocados, respuesta tardía y privados sin caché.');
})().catch(e=>{console.error(e);process.exitCode=1});
