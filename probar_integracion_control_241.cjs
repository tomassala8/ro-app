const fs=require('node:fs');
const prefijo=fs.readFileSync(__dirname+'/pruebas_control_macro_138.cjs','utf8').split('const macros=root.desc()')[0];
new Function('require','__dirname',prefijo+String.raw`
ctx.servidor=true;ctx.real={id:'account',estado:'activo'};ctx.persona={id:'account',estado:'activo'};
ctx.ver=q=>({ok:q.cliente_id==='uno'});
const dinero={generado:'2026-10-03 06:31',mes_cuota:'2026-10',mes_horas:'2026-09',cuota_tarifa_hora:31.47,clientes:[{cliente_id:'uno',cuota:9999,cuota_horas:{pautadas:20},coste_horas:{sep:5},facturas_holded_url:'https://private.invalid/'},{cliente_id:'ajeno',cuota_horas:{pautadas:44}}]};
const reus={_meta:{generado:'2026-10-03 06:30'},clientes:[{cliente_id:'uno',mes:'2026-09',ultima:'2026-09-28',detalle:[{asunto:'texto privado'}]}]};
const source={opcional:n=>n==='dinero_cliente/dinero_cliente'?dinero:n==='reuniones/reuniones'?reus:D.opcional(n)};
const visible=n=>typeof n==='string'?n:typeof n==='number'?String(n):n?.tag==='details'?n.k.filter(x=>x?.tag==='summary').map(visible).join(' '):(n?.k||[]).map(visible).join(' ');
let cases=0,node=b.panelControlCartera(ctx,source,'account',()=>true),txt=visible(node);
assert(txt.includes('2,5 / 20'));assert(!txt.includes('Registro histórico:'));assert(node.textContent.includes('2026-09-28'));assert(node.textContent.includes('No confirma celebración'));assert(!txt.includes('44 h'));assert(!node.textContent.includes('9999'));assert(!node.textContent.includes('31.47'));assert(!node.textContent.includes('private.invalid'));assert(!node.textContent.includes('texto privado'));assert(!txt.includes('Cumplido'));assert.equal(node.desc().filter(n=>n.tag==='table').length,1);cases++;
assert(node.textContent.includes('no acredita presupuesto aprobado'));assert(node.textContent.includes('No confirma celebración'));cases++;
ctx.real={id:'tomas',estado:'activo'};node=b.panelControlCartera(ctx,source,'account',()=>true);assert(!visible(node).includes(' / 20'));assert(!visible(node).includes('Registro histórico:'));assert(node.textContent.includes('2026-09-28'));cases++;
ctx.real={id:'account',estado:'activo'};ctx.ver=q=>({ok:q.tipo!=='horas_pautadas'});node=b.panelControlCartera(ctx,source,'account',()=>true);assert(!visible(node).includes(' / 20'));cases++;
ctx.ver=q=>({ok:q.cliente_id==='uno'});node=b.panelControlCartera(ctx,source,'account',()=>true);ctx.ver=()=>({ok:false});node.desc().find(n=>n.tag==='select'&&n.attrs['aria-label']==='Filtrar por servicio confirmado').listeners.change();assert(!visible(node).includes(' / 20'));assert(!node.textContent.includes('Pauta de referencia:'));cases++;
ctx.ver=q=>({ok:q.cliente_id==='uno'});ctx.servidor=false;node=b.panelControlCartera(ctx,source,'account',()=>true);assert(!visible(node).includes(' / 20'));cases++;
ctx.servidor=true;ctx.real.activo=false;node=b.panelControlCartera(ctx,source,'account',()=>true);assert(!visible(node).includes(' / 20'));cases++;
console.log(cases+' grupos241 UIreal PASS: permiso, identidad/viewas, revocación, período y privacidad.');
`)(require,__dirname);
(async()=>{
const path241=require('node:path'),os241=require('node:os'),dir241=fs.mkdtempSync(path241.join(os241.tmpdir(),'ro241-esm-'));fs.chmodSync(dir241,0o700);
try{
for(const n of ['_control_cartera_ruta_239','_imputa_personal_390','_historial_diario_364','_bandas_horas_381'])fs.writeFileSync(path241.join(dir241,n+'.mjs'),fs.readFileSync(__dirname+'/modulos/'+n+'.js','utf8').replace(/from '\.\/([^']+)\.js'/g,"from './$1.mjs'"));
const {renderControl239}=await import('file://'+path241.join(dir241,'_control_cartera_ruta_239.mjs'));
const make=()=>{const req=[],c={servidor:true,real:{id:'actor',estado:'activo',puestos:['account']},persona:{id:'actor',estado:'activo',puestos:['account']},params:[],clientesVisibles:[{id:'uno',activo_confirmado:true}],veModulo:()=>true,ver:()=>({ok:true}),titulo:()=>{},datosModulo:async n=>{req.push(n);return{}},api:async n=>({})};return{c,req}};
const cont={replaceChildren:()=>{}};const h=(...a)=>a;const panel=()=>({});let cases=0;
let t=make();await renderControl239(cont,t.c,()=>true,panel,h,()=>({}));if(!t.req.includes('dinero_cliente/dinero_cliente'))throw Error('Fuente autorizada no leída');cases++;
t=make();t.c.real.id='real';await renderControl239(cont,t.c,()=>true,panel,h,()=>({}));if(t.req.includes('dinero_cliente/dinero_cliente'))throw Error('viewas amplía');cases++;
t=make();t.c.ver=()=>({ok:false});await renderControl239(cont,t.c,()=>true,panel,h,()=>({}));if(t.req.includes('dinero_cliente/dinero_cliente'))throw Error('denegada leída');cases++;
t=make();let seen=null;t.c.datosModulo=async n=>{t.req.push(n);if(n==='dinero_cliente/dinero_cliente')t.c.ver=()=>({ok:false});return{}};await renderControl239(cont,t.c,()=>true,(_ctx,D)=>{seen=D.opcional('dinero_cliente/dinero_cliente')},h,()=>({}));if(seen!==null)throw Error('Publica fuente tras revocación');cases++;
console.log(cases+' grupos241 carga239 PASS: fuente opcional sólo permitida y descarte tras revocación.');
}finally{fs.rmSync(dir241,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1});
