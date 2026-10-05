const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');const DIR=__dirname;
function localizarApp(){if(process.env.RO_APP_681){const p=path.resolve(process.env.RO_APP_681);assert(fs.existsSync(path.join(p,'servir.py')),'APP explícita válida');return p;}let p=DIR;while(true){if(fs.existsSync(path.join(p,'servir.py')))return p;const q=path.join(p,'30_APP_PROTOTIPO');if(fs.existsSync(path.join(q,'servir.py')))return q;const up=path.dirname(p);if(up===p)return null;p=up;}}
const APP=localizarApp(),INTEGRADO=APP&&fs.existsSync(path.join(APP,'modulos/_planning_transiciones_681.js')),SOURCE=INTEGRADO?path.join(APP,'modulos'):path.dirname(DIR);
function fragmentosActuales(){const source=fs.readFileSync(path.join(SOURCE,INTEGRADO?'_operaciones_equipo_262.js':'_operaciones_equipo_262_candidato.js'),'utf8');const a=source.indexOf('const modelos491='),b=source.indexOf('let filtro491=',a),c=source.indexOf('const filas491=',b),d=source.indexOf('function pintar491',c);assert(a>=0&&b>a&&c>b&&d>c,'declaraciones reales presentes');const out=source.slice(a,b)+source.slice(c,d);assert(out.includes('celdaPlanning681')&&out.includes('metricaPlanning681'),'montaje real681');return out;}
const clone=x=>JSON.parse(JSON.stringify(x));
function h(tag,attrs={},...children){assert(!Object.keys(attrs).some(k=>/^on[a-z]/.test(k)));return {tag,attrs,children:children.flat(Infinity).filter(x=>x!==null&&x!==undefined),replaceChildren(...x){this.children=x;},removeAttribute(k){delete this.attrs[k];}};}
const context=vm.createContext({Date,Intl,JSON,Number,Array,Map,Set,Object,h});vm.runInContext(fs.readFileSync(path.join(SOURCE,'_planning_transiciones_681.js'),'utf8').replace(/\bexport\s+/g,''),context);
const call=(name,...args)=>vm.runInContext(name,context)(...args),good=JSON.parse(fs.readFileSync(path.join(DIR,'fixture_DTO_681.json'),'utf8'));let live=true;
let groups=0;function test(name,fn){fn();groups++;}
const props=()=>({h,hoy:'2026-10-04',vigente:()=>live});
test('fila real antes/despues y observacion por creador',()=>{
 for(const file of ['fixture_filas_baseline_681.js','fixture_filas_candidato_681.js']){
  const PR=clone(good),people=PR.personas;
  Object.assign(context,{PR,creadores491:people,source:{filas:[]},by:new Map(people.map(p=>[p.persona_id,p])),nombre:p=>p.persona_id,ctx:{hoy:'2026-10-04'},comparacion:new Map(),adicional:false,creadasSemana287:()=>null,missing:s=>h('span',{title:s},'—'),valor:n=>n??h('span',{},'—'),fmt:n=>String(n),actual491:()=>live});
  vm.runInContext('{'+(file.includes('baseline')?fs.readFileSync(path.join(DIR,file),'utf8'):fragmentosActuales())+'globalThis.rows681=filas491;globalThis.models681=modelos491;}',context);
  const rows=context.rows681;assert.equal(rows.length,2);assert.equal(rows[0].length,7);
  if(file.includes('baseline')){assert.equal(rows[0][2].children[0],'—');assert.equal(context.models681[0].observado,false);}
  else{assert.equal(rows[0][2].children[0],'≥1');assert.equal(rows[1][2].children[0],'—');assert.equal(context.models681[0].observado,true);assert(rows[0][2].attrs.title.includes('fin exclusivo'));assert(rows[0][2].attrs['aria-label'].includes('mínimo observado'));}
 }
});
test('None no0 y fuente/periodo invalido',()=>{
 for(const modify of [m=>m.version='395.1',m=>m.cobertura='completa',m=>m.corte='2026-10-09T12:00:00Z',m=>m.desde='2026-09-21T22:00:00Z',m=>m.metricas.al_planning=0,m=>m.metricas.al_planning=true,m=>m.metricas.al_planning=1e100,m=>m.tareas_observadas=0]){
  const D=clone(good);modify(D.personas[0]._planning_transiciones_681);assert.equal(call('metricaPlanning681',D.personas[0],D,'al_planning',props()),null);
 }
 assert.equal(call('celdaPlanning681',good.personas[1],good,'al_planning',props()).children[0],'—');
});
test('scopeexacto/idsduplicados/revocado',()=>{
 const D=clone(good);D.proyectos.push(clone(D.proyectos[0]));assert.equal(call('metricaPlanning681',D.personas[0],D,'al_planning',props()),null);
 const E=clone(good);E.personas.push(clone(E.personas[0]));assert.equal(call('metricaPlanning681',E.personas[0],E,'al_planning',props()),null);
 live=false;assert.equal(call('metricaPlanning681',good.personas[0],good,'al_planning',props()),null);live=true;
 const node=call('celdaPlanning681',good.personas[0],good,'al_planning',props());live=false;node.attrs.on.focus();assert.equal(node.children.length,0);assert(!node.attrs.title);assert(!node.attrs['aria-label']);live=true;
});
test('fuentevisiblefuera/corteoriginalysinverde',()=>{const s=call('fuentePlanning681',good.personas,good,props());assert(s.includes('2026-10-03T12:00:00Z'));assert(s.includes('mínimos parciales'));const node=call('celdaPlanning681',good.personas[0],good,'al_planning',props());assert(!/verde|rojo|cumplido/.test(node.attrs.class||''));});
test('offset/imposible/nohistorial noindice',()=>{for(const stamp of ['2026-02-31T10:00:00Z','2026-10-03T10:00:00+02:99','2026-10-03 10:00:00']){const D=clone(good);D.personas[0]._planning_transiciones_681.corte=stamp;assert.equal(call('metricaPlanning681',D.personas[0],D,'al_planning',props()),null);}const D=clone(good);delete D.personas[0]._planning_transiciones_681;assert.equal(call('celdaPlanning681',D.personas[0],D,'al_planning',props()).children[0],'—');});
console.log(groups+' grupos681 UI reales PASS');
