const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/modulos/_cierre_artifact_253.js','utf8');
const b={};vm.createContext(b);vm.runInContext(source.replace(/export /g,''),b);
let n=0;function test(name,fn){fn();n++;console.log('PASS '+name)}
const value=v=>{b.v=v;return vm.runInContext('fMin553(v)',b)};
const parse=s=>Number(s.replaceAll('.','').replace(',','.'));
test('mínimos decimales nunca aumentados',()=>{for(const v of [1.06,1.16,1.96,130.06,130.16,0.11,0.19,999.96]){const s=value(v);assert(parse(s)<=v,`${v}: ${s}`)}assert.equal(value(1.06),'1');assert.equal(value(130.06),'130')});
test('positivos pequeños no se convierten en cero',()=>{for(const v of [Number.MIN_VALUE,1e-8,0.0001,0.06]){const s=value(v);assert.notEqual(s,'0');assert.equal(parse(s),v)}});
test('extremos y límites conservan finitud',()=>{for(const v of [0,1,1e20,1e308,Number.MAX_VALUE]){const p=parse(value(v));assert(Number.isFinite(p));assert(p<=v)}for(const v of [null,NaN,Infinity,-1,'1'])assert.equal(value(v),'—')});
test('sin soporte Intl floor utiliza representación exacta',()=>{const z={Intl:{NumberFormat:function(){return{resolvedOptions:()=>({}),format:()=>{throw Error('No redondear sin floor')}}}}};vm.createContext(z);vm.runInContext(source.replace(/export /g,''),z);for(const v of [1.06,0.06,Number.MAX_VALUE]){z.v=v;const s=vm.runInContext('fMin553(v)',z);assert.equal(parse(s),v)}});
function h(tag,attrs,...kids){return{tag,attrs,kids:kids.flat(Infinity),append(...xs){this.kids.push(...xs.flat(Infinity))}}}
const walk=x=>!x||typeof x!=='object'?[]:[x,...(x.kids||[]).flatMap(walk)];
const text=x=>typeof x==='string'?x:(x?.kids||[]).map(text).join(' ');
function render(v,p=100){return b.pintarCierre253({h,d:{mes_horas:'2026-09',mes_cuota:'2026-09',clientes:[{cliente_id:'a',nombre:'A',account_id:'ops',coste_horas:{sep:v},cuota_horas:{pautadas:p}}]},clientes:[{id:'a',activo_confirmado:true}],verdad:()=>null})}
test('render mínimo subtotal tooltip y porcentaje fila',()=>{const r=render(1.06),summary=walk(r).find(x=>x.attrs?.['data-cierre-resumen']);assert(text(summary).includes('≥1 h observadas'));assert(!text(summary).includes('≥1,1'));const ratios=walk(r).filter(x=>x.attrs?.class?.startsWith('ratio361'));assert.equal(ratios.length,2);assert(text(ratios[0]).includes('≥1 % ref.'));assert.equal(text(ratios[1]),'≥1 %');assert(ratios[1].attrs.title.includes('copia parcial'));assert(ratios.some(x=>x.attrs.title.includes('≥1 h observadas')));assert.equal(walk(r).filter(x=>x.tag==='th').length,7)});
test('no cambian métricas ni umbral de exceso',()=>{const d={mes_horas:'2026-09',mes_cuota:'2026-09',clientes:[{cliente_id:'a',coste_horas:{sep:130.06},cuota_horas:{pautadas:100}}]};const r=b.prepararCierre253(d,[{id:'a',activo_confirmado:true}])[0];assert.equal(r.reales,130.06);assert.equal(r.pct,130.06);assert.equal(b.resumenCierre361([r]).ratio,130.06);assert.equal(walk(render(130.06)).filter(x=>x.attrs?.class==='ratio361 rojo').length,2);assert.equal(walk(render(130)).filter(x=>x.attrs?.class==='ratio361 rojo').length,0)});
console.log(n+' grupos mínimos553 PASS');
