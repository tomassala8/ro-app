const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'modulos/chat_equipo.js'),'utf8');
class N {
 constructor(tag,attrs={},...cs){this.tag=tag;this.attrs=attrs;this.style=attrs.style||{};this.dataset={};this.children=[];this.events={};this.isConnected=true;this.value=attrs.value||'';this.append(...cs);}
 append(...xs){for(const x of xs.flat(Infinity))if(x!==null&&x!==undefined)this.children.push(x);}
 replaceChildren(...xs){this.children=[];this.append(...xs);}
 querySelector(sel){if(sel==='[role="log"]')return nodes(this,n=>n.attrs?.role==='log')[0]||null;if(sel==='button[data-canal]')return nodes(this,n=>n.tag==='button'&&n.attrs?.['data-canal'])[0]||null;return null;}
 querySelectorAll(){return [];}getAttribute(k){return this.attrs[k];}setAttribute(k,v){this.attrs[k]=v;}addEventListener(k,f){this.events[k]=f;}focus(){}remove(){}scrollIntoView(){}
}
function nodes(n,p){let a=[];if(n&&typeof n==='object'){if(p(n))a.push(n);for(const x of n.children||[])a.push(...nodes(x,p));}return a;}
const h=(...x)=>new N(...x),txt=n=>typeof n==='string'?n:n?.children?.map(txt).join(' ')||'';
let mobile=false,notice=[],views=[];const apiCalls=[];
const c={console,Date,Map,Set,Promise,URL,document:{getElementById:()=>null,head:h('head')},location:{reload(){}},history:{replaceState(){}},localStorage:{getItem:()=>null,setItem(){}},
 MutationObserver:class{observe(){}},matchMedia:()=>({matches:mobile,addEventListener(){},removeEventListener(){}}),setTimeout:()=>0,clearTimeout(){},window:{dispatchEvent(){},open(){throw Error('no external open');}},CustomEvent:class{},
 h,fmt:{num:String},icono:x=>h('ico',{},x),chipEstado:(a,b)=>h('chip',{},b),chipsFiltro:o=>{views.push(o);return h('filtro',{class:'chips-f'});},
 vacio:o=>h('vacio',{},o.titulo),vacioLinea:s=>h('vacio',{},s),avisoParcial:s=>h('aviso',{},s),frescura:()=>h('fuente'),iniciales:s=>s.slice(0,2),avisoFlotante:s=>notice.push(s),selectorPersona:()=>h('selector'),abrirPedirAyuda(){throw Error('no external/action modal');}};
vm.createContext(c);vm.runInContext(source.replace(/import\s+[\s\S]*?from\s+['"][^'"]+['"];\s*/g,'').replace('export default {','const modulo = {'),c);
const chan={id:'general',tipo:'general',titulo:'General',puede_escribir:true,no_leidos:1};
const data={canal:chan,mensajes:[{id:1,tipo:'mensaje',quien:'yo',hora:'2026-10-03T10:00:00Z',texto:'Mensaje visible'}],miembros:['yo'],hay_mas:false};
const state=()=>({ctx:{persona:{id:'yo',nombre:'Persona'},datos:{personas:[]},nombre:x=>x,soloLectura:true,titulo(){},vigente:()=>true,api:async(...a)=>{apiCalls.push(a);return data;}},pid:'yo',raiz:h('raiz'),D:{_meta:{},canales:[],menciones:[]},A:{canales:[chan],preferencias:{},campana:{no_leidos:1,menciones:0,directos:0}},sel:{tipo:'app',id:'general'},vista:'todos',buscar:'',abiertos:new Set(),app:new Map([['general',data]]),cu:new Map(),adjuntos:[],filtroAviso:'abiertos',movilEnCanal:true});
(async()=>{
 const S=state();c.pintar(S);assert.equal(S.raiz.children[0].tag,'nav');assert.equal(S.raiz.children[1].attrs.class,'chat-caja');assert(txt(S.raiz).includes('Mensaje visible'));assert(!txt(S.raiz).includes('Tus canales'));assert(!txt(S.raiz).includes('Avisos para ti'));
 assert.equal(nodes(S.raiz,n=>n.attrs?.role==='log').length,1);assert.equal(views.filter(v=>v.etiqueta==='Vista').length,0);assert(nodes(S.raiz,n=>n.tag==='details').every(n=>!n.attrs.open));assert(nodes(S.raiz,n=>n.tag==='textarea')[0].attrs.disabled);
 mobile=true;c.pintar(S);assert.equal(nodes(S.raiz,n=>n.tag==='aside').length,0);assert(txt(S.raiz).includes('Mensaje visible'));assert(nodes(S.raiz,n=>n.attrs?.['aria-label']==='Volver a la lista de canales').length);
 const before=apiCalls.length;await assert.rejects(c.apiChat(S,'canales/mensaje',{metodo:'POST'}));assert.equal(apiCalls.length,before,'read-only never attempts POST');
 let active=false;S.ctx.vigente=()=>active;await assert.rejects(c.apiChat(S,'canales'));assert.equal(apiCalls.length,before,'stale route never calls API');
 const deferred=()=>{let resolve,reject;return {promise:new Promise((a,b)=>{resolve=a;reject=b;}),resolve,reject};};
 const d=deferred();active=true;S.ctx.api=()=>d.promise;const stale=c.apiChat(S,'canales');active=false;d.resolve({canales:['foreign']});await assert.rejects(stale);
 // Render's concurrent initial reads must not paint after navigation.
 const e=deferred(),cont=h('main');const ctx={...S.ctx,servidor:true,soloLectura:true,params:[],datosModulo(){throw Error('must not read other ClickUp in view-as');},api:()=>e.promise,vigente:()=>active};active=true;c.cont=cont;c.ctx=ctx;const r=vm.runInContext('modulo.render(cont,ctx)',c);active=false;e.resolve({canales:[chan]});await r;assert.equal(cont.children.length,0);
 // Actual initial render reads app only in view-as and keeps the compact navigation.
 active=true;ctx.api=async()=>({canales:[chan],campana:{},preferencias:{}});await vm.runInContext('modulo.render(cont,ctx)',c);assert(txt(cont).includes('En «ver como»'));assert.equal(nodes(cont,n=>n.tag==='nav').length,1);
 // Out-of-order search results cannot replace newer query data (also ABA same query).
 const B=state(),first=deferred(),second=deferred();let calls=0;B.ctx.api=()=>++calls===1?first.promise:second.promise;const p1=c.buscar(B,'viejo'),p2=c.buscar(B,'nuevo');second.resolve({resultados:[],clickup:[],marca:'nuevo'});await p2;first.resolve({resultados:[],clickup:[],marca:'viejo'});await p1;assert.equal(B.res.marca,'nuevo');
 // Failure keeps the actual message composer text; no success notification.
 const E=state();E.ctx.soloLectura=false;E.ctx.api=async()=>{const err=Error('Rechazado');err.status=400;throw err;};const composer=c.cajaEscribir(E,chan);const ta=nodes(composer,n=>n.tag==='textarea')[0];ta.value='Texto a corregir';const send=nodes(composer,n=>n.tag==='button'&&txt(n).includes('Enviar'))[0];await send.attrs.on.click();assert.equal(ta.value,'Texto a corregir');assert(!notice.some(n=>n==='Enviado. Queda en la app, con rastro.'));
 // Sending finishes in another channel: never clears that channel's attachments or falsely reports success.
 const F=state();F.ctx.soloLectura=false;const post=deferred();F.ctx.api=()=>post.promise;F.adjuntos=[{id:'old',tipo:'cliente'}];const write=c.escribir(F,chan,'Texto',null);F.sel={tipo:'app',id:'otro'};F.adjuntos=[{id:'new',tipo:'tarea'}];post.resolve({ok:true});assert.equal(await write,false);assert.equal(F.adjuntos[0].id,'new');
 console.log('Chat 114: render compacto, móvil, lectura, fallos y concurrencia OK');
})().catch(e=>{console.error(e);process.exitCode=1;});
