// Datos ficticios; ejecuta el helper y los renderizadores reales, sin red ni almacenamiento.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const src=fs.readFileSync(__dirname+'/modulos/informe.js','utf8');
const helper=src.slice(src.indexOf('export function medicionesEmbudoInforme'),src.indexOf('// =================================================================== paridad')).replace(/export /g,'');
const render=src.slice(src.indexOf('  embudo(S) {'),src.indexOf('  // ------------------------------------------------------------- 2 · GA4')).replace('  embudo(S) {','function renderEmbudo(S) {').replace(/},\s*$/,'}');
const b={console,Date,Number,Math,variacion:()=>0,num4:String,fNum:v=>v===null?'Sin dato':String(v),fEur:String,
 h:(tag,attrs,...kids)=>({tag,attrs,kids}),PILA:()=>({}),SUB:{},vacioLinea:t=>({texto:t}),barraProgreso:o=>o,
 tiles:x=>x,tile:x=>x,barras:x=>x,bloque:(s,k,t,x)=>({titulo:t,contenido:x}),fresco:()=>null,atajo:()=>null,URL:{embudo:()=>null,meta:()=>null}};
vm.createContext(b);const sem=fs.readFileSync(__dirname+'/modulos/_meta_informe_291.js','utf8').replace(/export /g,'');vm.runInContext(sem+'\n'+helper+'\n'+render,b);
const medir=b.medicionesEmbudoInforme,clone=x=>JSON.parse(JSON.stringify(x));let n=0;
const base={ctx:{hoy:'2026-10-03'},P:{id:'2026-09',texto:'Septiembre 2026'},c:{servicios:{crm_ghl:'sí'}},veInversion:true,crm:'uso',f:{fuentes:{meta:{estado:'bien',hora:'2026-10-02 17:12'},google_ads:{estado:'bien',hora:'2026-10-02 13:57'},ghl:{estado:'bien',hora:'2026-10-03 01:42'}},meta:{actual:{leads:201,gasto:402}},google_ads:{conversiones:2,coste:100},ga4:{actual:{usuarios:9,conversiones:21}},embudo:{leads_ghl:3,citas:{agendadas:0,celebradas:0,sin_estado:0},funnel_90d:{nuevo:0,cerrado:5},estancados_72h:0,ganadas_total:5}}};
let m=medir(base);assert.equal(m.leadsMeta,null);assert.equal(m.resultadosMeta,201);assert.equal(m.conversionesGoogle,2);assert.equal(m.contactosCRM,3);assert.equal(m.cplMeta,null);assert.equal(m.cpaGoogle,50);assert.equal(m.ventas,null);assert.equal(m.conversionCohorte,null);n++;
assert.equal(m.agendadas,0);assert.equal(m.sinEstado,0);assert.equal(m.parados,0);assert.equal(m.fechaMeta,'2026-10-02');n++;
let x=clone(base);delete x.f.embudo.citas;delete x.f.embudo.estancados_72h;m=medir(x);assert.equal(m.agendadas,null);assert.equal(m.parados,null);n++;
for(const crm of ['sin_uso','sin_crm']){x=clone(base);x.crm=crm;m=medir(x);assert.equal(m.agendadas,null);assert.equal(m.contactosCRM,null);assert.equal(m.parados,null);assert.equal(m.etapas.length,0);assert.doesNotMatch(m.avisoCRM,/No usa el CRM|no agenda/);const out=JSON.stringify(b.renderEmbudo(x));assert.doesNotMatch(out,/Donde más se pierde|100 %|0 %/);assert.equal(b.borrador(x).perdidas,'');n++;}
x=clone(base);x.c.servicios.crm_ghl='no';assert.equal(medir(x).contactosCRM,null);n++;
for(const t of [undefined,'2026-02-30','2026-10-04 01:00','2026-10-02 25:12','2026-10-02 basura']){x=clone(base);x.f.fuentes.meta.hora=t;assert.equal(medir(x).resultadosMeta,null);n++;}
for(const estado of ['error','sin_conectar','no_aplica',undefined]){x=clone(base);x.f.fuentes.ghl.estado=estado;assert.equal(medir(x).agendadas,null);n++;}
x=clone(base);x.f.meta.errores=['fixture'];x.f.google_ads.error='fixture';x.f.embudo.error='fixture';m=medir(x);assert.equal(m.leadsMeta,null);assert.equal(m.conversionesGoogle,null);assert.equal(m.agendadas,null);n++;
x=clone(base);x.veInversion=false;m=medir(x);assert.equal(m.cplMeta,null);assert.equal(m.cpaGoogle,null);assert.equal(m.leadsMeta,null);assert.equal(m.resultadosMeta,201);n++;
for(const v of [-1,NaN,Infinity,'0',false,0.5]){x=clone(base);x.f.embudo.citas.agendadas=v;assert.equal(medir(x).agendadas,null);n++;}
x=clone(base);x.f.google_ads.conversiones=2.5;assert.equal(medir(x).conversionesGoogle,2.5);n++;
x=clone(base);x.f.embudo.funnel_90d['nombre privado']=8;assert.equal(medir(x).etapas.length,2);n++;
const output=JSON.stringify(b.renderEmbudo(base));assert.match(output,/201/);assert.match(output,/Conversiones de Google Ads/);assert.doesNotMatch(output,/203|224|Donde más se pierde|100 %|0 %/);assert.match(output,/no son una cohorte/);assert.match(output,/no se suman/);n++;
x=clone(base);x.crm='sin_uso';const out=JSON.stringify(b.renderEmbudo(x));assert.doesNotMatch(out,/Stock de oportunidades por etapa|oportunidades sin avance de etapa observado/);assert.match(out,/Pocos contactos observados/);n++;
const draft=b.borrador(base);assert.match(draft.mes,/21 conversiones/);assert.match(draft.mes,/sin unión con leads publicitarios ni ventas acreditadas/);assert.match(draft.perdidas,/No acredita ausencia de contacto/);assert.doesNotMatch(draft.mes,/203|224/);n++;
console.log(n+' grupos de embudo/informe158 pasan, con helper y renderizadores reales');
