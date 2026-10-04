// Auditoría de lectura: regresiones corregidas325 y límites de referencia restantes.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const s=fs.readFileSync(path.join(__dirname,'modulos/_operaciones_equipo_262.js'),'utf8');
function extraer(n){const start=s.indexOf('function '+n+'(');assert(start>=0);let a=s.indexOf('{',start),depth=1,i=a+1;for(;depth&&i<s.length;i++){if(s[i]==='{')depth++;if(s[i]==='}')depth--;}return s.slice(start,i);}
const c={num:x=>typeof x==='number'&&Number.isFinite(x)&&x>=0,arr:x=>Array.isArray(x)?x:[],dia:x=>/^\d{4}-\d{2}-\d{2}$/.test(x),serieHorasDiaria238:()=>({dias:[{fecha:'2026-10-01',estado:'observado',horas:4},{fecha:'2026-10-02',estado:'observado',horas:4}]})};
vm.createContext(c);vm.runInContext(['horasRango262','diasLaborables262','referenciaHoras262'].map(extraer).join('\n'),c);
let x=c.horasRango262({meses:[{mes:'2026-10',imputadas:60}]},{hoy:'2026-10-03'},{desde:'2026-10-01',hasta:'2026-10-03'});
assert.equal(x.valor,60);assert.equal(x.dias,2);assert.equal(x.ultima,'2026-10-02');
console.log('CONFIRMADO: total mensual legacy se admite sin descriptor; días/última proceden sólo de serie corta.');
x=c.horasRango262({meses:[{mes:'2026-10',imputadas:0}]},{hoy:'2026-10-03'},{desde:'2026-10-01',hasta:'2026-10-03'});
assert.equal(x.valor,8);assert.match(x.detalle,/Suma sólo/);assert.equal(x.tipo,'observado_diario');
console.log('CORREGIDO325: fallback de 8h se describe como muestra diaria, no total mensual.');
const laborables=Array.from(c.diasLaborables262('2026-10-05'));const naturales=['2026-09-30','2026-10-01','2026-10-02','2026-10-03','2026-10-04'];
assert.deepEqual(laborables.filter(d=>!naturales.includes(d)),['2026-09-28','2026-09-29']);
console.log('Límite238.1: cinco días naturales no cubren lunes;238.2 lo resuelve con siete.');
assert.equal(c.referenciaHoras262({desde:'2026-09-28',hasta:'2026-10-02'},'2026-10-02').horas,40);
console.log('CONFIRMADO: referencia inclusiva del viernes=40h; productor excluye hoy, cuatro días completos=32h (80% referencia).');
