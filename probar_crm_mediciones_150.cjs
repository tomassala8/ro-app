const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 const m=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(__dirname+'/modulos/_crm_mediciones.js')).toString('base64'));
 const fuente={hora:'2026-10-03T08:00:00Z',estado:'bien',fuente:'CRM fixture'};
 const medir=(ghl,fuente_=fuente)=>m.medirEmbudoCRM(ghl,fuente_,'2026-10-03');
 let r=medir({conectado:true,embudo:{},citas:{}});assert.equal(r.total,null);assert.equal(r.parados,null);assert.equal(r.agendadas,null);assert.equal(r.sinEstado,null);assert.equal(r.asistencia,null);
 const e={contactos_90d:0,funnel:{nuevo:0,seguimiento:0,cita:0,presupuesto:0,cerrado:0,descartado:0},cohorte_30d:0,estancados_72h:0};
 r=medir({embudo:e,citas:{'14d':{agendadas:0,celebradas:0,no_presentadas:0,sin_estado:0}}});assert.equal(r.total,0);assert.equal(r.parados,0);assert.equal(r.agendadas,0);assert.equal(r.sinEstado,0);assert.equal(r.asistencia,null);assert.equal(r.cobertura,'registros_observados_no_exhaustivos');
 for(const hora of (null,'2026-10-03basura','2026-02-30','2026-10-03T25:00:00Z','2026-10-04')){r=medir({embudo:e},{hora});assert.equal(r.total,null);assert.equal(r.fechaValida,false);}
 for(const n of (null,false,-1,1.5,NaN,Infinity,'0')){r=medir({embudo:{...e,contactos_90d:n}});assert.equal(r.total,null);}
 r=medir({embudo:{...e,contactos_90d:1,funnel:{nuevo:2}}});assert.equal(r.total,null);assert.equal(r.incoherente,true);assert(r.etapas.every(x=>x.n===null));
 r=medir({embudo:{contactos_90d:3,funnel:{nuevo:2}}});assert.equal(r.etapas.find(x=>x.id==='nuevo').n,2);assert.equal(r.etapas.find(x=>x.id==='cita').n,null);
 r=medir({embudo:{cohorte_30d:2,estancados_72h:3}});assert.equal(r.parados,null);
 r=medir({embudo:{...e,error:'fixture'},citas:{'14d':{agendadas:2},errores:['fixture']}});assert.equal(r.total,null);assert.equal(r.agendadas,null);
 r=medir({citas:{'14d':{agendadas:10,celebradas:3,no_presentadas:1,sin_estado:6,con_fecha_en_ventana:10,canceladas:0}}});assert.equal(r.asistencia,75);assert.equal(r.marcadas,4);assert.equal(r.sinEstado,6);
 r=medir({citas:{'14d':{agendadas:10,celebradas:3,no_presentadas:1,sin_estado:6,con_fecha_en_ventana:2}}});assert.equal(r.asistencia,null);assert.equal(r.sinEstado,null);
 r=medir({embudo:{...e,conv_lead_cita:90,conv_cita_pres:80,conv_pres_cierre:70}});assert.equal(r.conversiones,null);assert.equal(r.ventas,null);
 // Un sello reciente no convierte los textos heredados en garantías ni confirma uso/estancamiento.
 const fila={leads_30d:4,sin_tocar_24h:2,mot1:{texto:'incumple contrato'},motivos:[{clave:'velocidad',nivel:'rojo',texto:'garantía: 70 %'},{clave:'sin_uso',texto:'el cliente no usa GoHighLevel'},{clave:'estancados',texto:'sin cambiar de etapa'},{clave:'desconocida',texto:'todas cumplen'}]};
 const nf=m.normalizarFilaCRM(fila,fuente,'2026-10-03');assert.equal(nf.leads_30d,4);assert.equal(nf.sin_tocar_24h,2);assert.strictEqual(nf.mot1,nf.motivos[0]);assert.equal(nf.estado,'gris');assert(nf.motivos.every(x=>x.nivel==='dato'&&x.origen==='referencia_legacy'));assert(nf.mot1.texto.includes('no evalúa la garantía'));assert(!JSON.stringify(nf.motivos).includes('70 %'));assert(nf.motivos[1].texto.includes('por confirmar'));assert(nf.motivos[2].texto.includes('updatedAt'));assert(!nf.motivos[3].texto.includes('todas cumplen'));
 const anterior=m.normalizarFilaCRM(fila,{...fuente,hora:'2026-09-01'},'2026-10-03');assert.equal(anterior.leads_30d,null);assert(anterior.motivos.every(x=>x.nivel==='dato'&&x.texto.startsWith('Señal anterior:')));assert.deepEqual(m.normalizarFilaCRM({motivos:'texto arbitrario'},fuente,'2026-10-03').motivos,[]);
 // El renderer real consume el helper, no un stub que fabrica sus estados.
 let src=fs.readFileSync(__dirname+'/modulos/captacion.js','utf8');src=src.replace(/import[\s\S]*?from ['"][^'"]+['"];\n/g,'').replace('export default {','const modulo = {');
 const configs=[];
 const env={medirEmbudoCRM:m.medirEmbudoCRM,h:(tag,attrs,...children)=>({tag,attrs,children}),panel:(x,...children)=>({x,children}),vacio:x=>x,
 tile:x=>{configs.push(x);return x;},tiles:x=>x,embudoBarras:(x)=>({barras:x}),hoyMadrid:()=> '2026-10-03',fmt:{num:v=>String(v),pct:v=>String(v)+'%'},Date};
 vm.createContext(env);vm.runInContext(src+';globalThis.renderEmbudo=tEmbudo;',env);
 const salida=[],el={append:x=>salida.push(x)};
 env.renderEmbudo(el,{hoy:'2026-10-03'},{fuentes:[{id:'ghl',...fuente}]},{ghl:{conectado:true,embudo:{},citas:{}}});
 assert.equal(configs.length,3);assert(configs.every(x=>x.estado==='gris'));assert(configs.every(x=>x.valor===null));
 assert(JSON.stringify(salida).includes('Embudo sin medición confirmada'));assert(!JSON.stringify(salida).includes('Todas con estado'));
 configs.length=0;salida.length=0;
 env.renderEmbudo(el,{hoy:'2026-10-03'},{fuentes:[{id:'ghl',...fuente}]},{ghl:{conectado:true,embudo:e,citas:{'14d':{agendadas:0,celebradas:0,no_presentadas:0,sin_estado:0}}}});
 assert(configs.every(x=>x.estado==='gris'));assert(JSON.stringify(salida).includes('Cero contactos observados'));assert(!JSON.stringify(salida).includes('Lead → cita'));
 assert.equal(configs[0].valor,'0 de 0');assert.equal(configs[1].valor,'0');assert.equal(configs[2].valor,null);
 console.log('150 PASS: helper y 2 renders reales; desconocido/0/fechas/errores/coherencia/asistencia/stock sin conversión ni verde.');
})().catch(e=>{console.error(e);process.exitCode=1;});
