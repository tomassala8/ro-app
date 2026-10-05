const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const src = fs.readFileSync(path.join(__dirname,'modulos/captacion.js'),'utf8');
const start = src.indexOf("    t.push(tile({ icono: 'plug', etiqueta: 'Meta y CRM · 7 días'");
assert(start >= 0);
const end = src.indexOf('\n  }\n  const pr',start);
assert(end>start);
const body=src.slice(start,end);
function card(c){const t=[];vm.runInNewContext(body,{c,t,tile:x=>x,num:x=>x===null||x===undefined?'sin dato':String(x),fuenteDe:()=>({fecha:'2026-10-03 01:42'}),d:{}});return t[0];}
const cases=[{meta:6,crm:13},{meta:13,crm:0},{meta:13,crm:null}];
for(const f of cases){const c=card({ghl:{conectado:true},despacho:{leads_meta_7d:f.meta,leads_ghl_7d:f.crm,pct_llegan_crm:100}});assert.equal(c.estado,'gris');assert.equal(c.valor,f.crm===null?'sin dato':String(f.crm));assert(c.comparacion.texto.includes(String(f.meta)));assert(!c.comparacion.texto.includes('%'));assert(!c.contexto.includes('Llegan todos'));assert(c.contexto.includes('Sin unión por lead/origen'));}
assert.equal(card({ghl:{conectado:false},despacho:{leads_meta_7d:3,leads_ghl_7d:null}}).valor,null);
// Independent source counts cannot certify a conversion ratio; generator now keeps it unknown.
const gen=fs.readFileSync(path.join(__dirname,'fuentes_captacion/generar_captacion.py'),'utf8');assert(!gen.includes("round(min(100, ghl_7 / leads_meta_7 * 100))"));assert(gen.includes("'pct_llegan_crm': None"));
console.log('4 fixtures reales de presentación: exceso CRM no atribuido, cero distinto de desconocido, desconectado sin cifra; sin conversión falsa.');

const fn=src.slice(src.indexOf('function contrastarMotivo('),src.indexOf('const textoMot ='));
const context={};vm.runInNewContext(fn,context);
assert(!context.contrastarMotivo('Ningún lead ha llegado a cita: el despacho no trabaja los leads').includes('no trabaja'));
assert(context.contrastarMotivo('Subcuenta de GoHighLevel sin usar: los 105 leads de Meta de 7 días no van a GoHighLevel').includes('no está reconciliado por lead'));
assert(context.contrastarMotivo('techo de 35 €').includes('umbral anterior'));
assert.equal(context.contrastarMotivo('7 días sin leads (103 € invertidos)'), '7 días sin leads (103 € invertidos)');
console.log('4 casos adicionales: motivos heredados sin acusación ni objetivos inventados; evidencia preservada.');
