const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'modulos/ficha.js'),'utf8');
class N{constructor(tag,attrs={},...children){this.tag=tag;this.attrs=attrs;this.children=children.flat(Infinity).filter(x=>x!=null);this.isConnected=true;}append(...xs){this.children.push(...xs);}replaceChildren(...xs){this.children=xs.flat(Infinity).filter(x=>x!=null);}}
const text=n=>typeof n==='string'?n:n?.children?.map(text).join(' ')||'';
const nodes=n=>n&&typeof n==='object'?[n,...n.children.flatMap(nodes)]:[];
const h=(...args)=>new N(...args),c={h,Set,encodeURIComponent,panel:(o,...xs)=>h('panel',{},o.titulo,o.sub,...xs)};
vm.createContext(c);vm.runInContext(src.slice(src.indexOf('async function pintarHistorialReuniones(')),c);
(async()=>{
 const F={c:{id:'c'}},z=h('root'),ctx={persona:{puestos:['account']},real:{puestos:['direccion']},vigente:()=>true,api:async()=>({cliente_id:'c',estado_fuente:'disponible',importado_el:'2026-10-03',registros:[{fecha:'2026-09-20',fuente:'Archivo local',transcripcion_registrada:true,fecha_ambigua:true,fechas_documentadas:['2026-09-20','2026-09-21']}]})};
 await c.pintarHistorialReuniones(z,ctx,F);assert(text(z).includes('2026-09-20'));assert(text(z).includes('Fecha por contrastar'));assert(text(z).includes('texto reservado'));assert(!nodes(z).some(n=>n.tag==='a'));assert.equal(nodes(z).filter(n=>n.tag==='details')[0].attrs.open,undefined);
 let resolve,active=true;const old=h('root');ctx.api=()=>new Promise(r=>resolve=r);ctx.vigente=()=>active;const p=c.pintarHistorialReuniones(old,ctx,F);active=false;resolve({cliente_id:'c',estado_fuente:'disponible',registros:[{fecha:'SECRET OLD'}]});await p;assert(!text(old).includes('SECRET OLD'));
 active=true;ctx.vigente=()=>true;ctx.api=async()=>{throw Error('provider-secret')};const err=h('root');await c.pintarHistorialReuniones(err,ctx,F);assert(text(err).includes('No se puede concluir ausencia'));assert(!text(err).includes('provider-secret'));
 ctx.api=async()=>({cliente_id:'c',estado_fuente:'disponible',importado_el:'2026-10-03',registros:[]});const empty=h('root');await c.pintarHistorialReuniones(empty,ctx,F);assert(text(empty).includes('no demuestra ausencia'));
 ctx.api=async()=>({cliente_id:'otro',estado_fuente:'disponible',registros:[{fecha:'FOREIGN'}]});const wrong=h('root');await c.pintarHistorialReuniones(wrong,ctx,F);assert(!text(wrong).includes('FOREIGN'));
 let calls=0;ctx.persona={puestos:['seo']};ctx.api=async()=>{calls++;throw Error('should not')};const denied=h('root');await c.pintarHistorialReuniones(denied,ctx,F);assert.equal(calls,0);assert.equal(denied.children.length,0);
 console.log('129 ficha: render real compacto, fecha ambigua, sin enlaces, error/unknown, scopes y respuestas tardías OK');
})();
