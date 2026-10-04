const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let src=fs.readFileSync(__dirname+'/modulos/mi_trabajo.js','utf8');
const original=src;
src=src.replace(/import[\s\S]*?from ['"][^'"]+['"];\n/g,'').replace('export default {','const modulo = {').replace(/export function /g,'function ');
let aperturas=0;
const env={vacioLinea:(texto)=>({texto}),bloqueTareaIA:()=>{aperturas++;return {cta:true};}};
vm.createContext(env);vm.runInContext(src+';globalThis.probar={consultaLocalTrabajo,avisoLecturaTrabajo,contextoTareaTrabajo};',env);
const ctx=(extra={})=>({servidor:true,soloLectura:false,real:{id:'real'},persona:{id:'real'},...extra});
const f=env.probar;
let c=ctx({pilotoLectura:true,soloLectura:true});
assert.equal(f.consultaLocalTrabajo(c),true);assert.match(f.avisoLecturaTrabajo(c),/Piloto de consulta/);
assert.match(f.contextoTareaTrabajo({ctx:c},{}).texto,/lectura actual de ClickUp/);assert.equal(aperturas,0);
// Compatibilidad con carcasa anterior sin flag: consulta real readonly conserva límite local.
c=ctx({soloLectura:true});assert.equal(f.consultaLocalTrabajo(c),true);
assert.match(f.avisoLecturaTrabajo(c),/Consulta de solo lectura/);assert.doesNotMatch(f.avisoLecturaTrabajo(c),/ver como/);
f.contextoTareaTrabajo({ctx:c},{});assert.equal(aperturas,0);
// Ver como ordinario no se etiqueta piloto ni elimina la lectura autorizada previa.
c=ctx({soloLectura:true,persona:{id:'vista'}});assert.equal(f.consultaLocalTrabajo(c),false);
assert.match(f.avisoLecturaTrabajo(c),/ver como/);assert.equal(f.contextoTareaTrabajo({ctx:c},{}).cta,true);
// El piloto también limita lectura con identidad vista distinta.
c=ctx({pilotoLectura:true,soloLectura:true,persona:{id:'vista'}});
assert.equal(f.consultaLocalTrabajo(c),true);assert.match(f.avisoLecturaTrabajo(c),/Piloto de consulta/);
f.contextoTareaTrabajo({ctx:c},{});assert.equal(aperturas,1);
// Sesión normal y copia offline mantienen el componente previo (que explica falta de servidor).
assert.equal(f.contextoTareaTrabajo({ctx:ctx()},{}).cta,true);
assert.equal(f.contextoTareaTrabajo({ctx:ctx({servidor:false})},{}).cta,true);
assert.equal(aperturas,3);
assert.match(original,/contextoTareaTrabajo\(E, t\),/);assert.match(original,/avisoLecturaTrabajo\(E.ctx\)/);
console.log('PASS 147: CTA piloto sin aperturas, fallback carcasa, ver como/normal/offline y wiring actual.');
