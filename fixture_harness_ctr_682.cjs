const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const prefix=fs.readFileSync('pruebas_revision_captacion_415.cjs','utf8').split('\nconst c={')[0],outer={require,console,process,__dirname:process.cwd()};vm.createContext(outer);vm.runInContext(prefix+';globalThis.ENV=e;globalThis.NODE=N;globalThis.H=h;',outer);const e=outer.ENV,N=outer.NODE,h=outer.H;
const src=fs.readFileSync(process.env.CAPTACION_682||'modulos/captacion.js','utf8'),components=fs.readFileSync('componentes.js','utf8');
vm.runInContext(components.slice(components.indexOf('export function tablaApilable('),components.indexOf('// --------------------------------------------------- contacto:')).replace('export ',''),e);
Object.assign(e,vm.runInContext('(()=>{'+fs.readFileSync('modulos/_crm_mediciones.js','utf8').replaceAll('export ','')+';return {medirEmbudoCRM,medirCitasCRM};})()',e));
vm.runInContext(src.slice(src.indexOf('const distingue ='),src.indexOf('\n',src.indexOf('const distingue ='))),e);
e.panel=(o,...kids)=>h('section',{},o.titulo,o.sub,...kids);e.vacio=o=>h('p',{},o.titulo);e.pct=x=>x==null?'—':x+' %';e.num=x=>x==null?'—':String(x);e.chipsFiltro=o=>{let value=o.valor||'';return Object.assign(h('div',{},o.opciones.map(x=>h('button',{on:{click:()=>{value=x.valor;o.alCambiar();}}},x.texto))),{valor:()=>value});};
vm.runInContext(src.slice(src.indexOf('function pCreatividades('),src.indexOf('// ------------------------------------------------------------------ pestaña · Google Ads')),e);

vm.runInContext(fs.readFileSync('modulos/_ctr_paid_682.js','utf8').replaceAll('export ',''),e);
vm.runInContext(src.slice(src.indexOf('function tAnuncios('),src.indexOf('function tMetas(')),e);
module.exports={e,N,h,src};
