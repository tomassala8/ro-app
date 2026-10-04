// Conducta285B: unidad acreditada antes de CPL/alertas; sólo fixtures.
const fs=require('fs'),assert=require('node:assert/strict'),vm=require('node:vm');
(async()=>{
 const M=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(__dirname+'/modulos/_paid_mediciones.js','utf8')).toString('base64'));
 const hoy='2026-10-03',d={datos_hasta:'2026-10-02',ventanas:{'7d':['2026-09-26','2026-10-02']},parametros:{techo_cpl:35}};
 const descriptor={version:'220.1',fuente:'meta_insights',nivel:'account',periodo_valido:true,desde:'2026-09-26',hasta:'2026-10-02',fecha_lectura:hoy,cohorte:'resultados_meta_sin_union_crm_ni_cualificacion_ro',tipo_lead:'lead',campos_observados:['gasto','leads']};
 const c={dinero:true,meta_activa:true,gasto:{'7d':1000},leads:{'7d':10},cpl_resumen:{ref:100,ref_base:'7d',fiable:true,medicion:descriptor},objetivo:{cargado:true,cpl_objetivo:40,cuando:'2026-10-01',vigente:true,fuente_generado:hoy,periodo:'2026-10',confirmado:true,estado:'confirmado'}};
 assert.equal(M.medirCplPaid(c,d,hoy).estado,'rojo');
 for(const patch of [{tienda_online:true},{tipo_negocio:'tienda_online'},{cliente_id:'kiosko-box'},{dinero:false},{cuenta_meta:{errores:['fixture']}},{gasto:{'7d':null}},{leads:{'7d':0}},{leads:{'7d':10.5}},{cpl_resumen:{...c.cpl_resumen,ref:90}},{cpl_resumen:{...c.cpl_resumen,medicion:null}}]){
  const x={...c,...patch},m=M.medirCplPaid(x,d,hoy);assert.equal(m.real,null);assert.equal(m.evaluable,false);assert.equal(m.estado,'gris');assert(!M.normalizarPaid(x,d,hoy).motivos.some(x=>/CPL observado supera/.test(x.texto)));
 }
 for(const patch of [{tipo_lead:'purchase'},{tipo_lead:'resultados'},{nivel:'campaign'},{cohorte:'otra'},{desde:'2026-09-25'},{campos_observados:['leads']},{fecha_lectura:'2026-10-04'},{fecha_lectura:'2026-09-30'},{periodo_valido:false}])assert.equal(M.medirCplPaid({...c,cpl_resumen:{...c.cpl_resumen,medicion:{...descriptor,...patch}}},d,hoy).real,null);
 assert.equal(M.medirCplPaid({...c,objetivo:{...c.objetivo,confirmado:false}},d,hoy).estado,'gris');
 const serie=Array.from({length:7},(_,i)=>{const day=new Date(Date.parse('2026-09-26')+i*864e5).toISOString().slice(0,10);return {d:day,gasto_meta:100,leads_meta:2,medicion:{...descriptor,desde:day,hasta:day}};});
 assert.equal(M.cplMovilPaid285(c,serie,hoy).at(-1).y,50);assert(M.cplMovilPaid285(c,serie.slice(1),hoy).every(p=>p.y===null));
 for(const edit of [s=>s[3].leads_meta=null,s=>delete s[3].medicion,s=>s[3].medicion.tipo_lead='purchase',s=>s[3].d=s[2].d,s=>s[3].gasto_meta=null]){const s=JSON.parse(JSON.stringify(serie));edit(s);assert.equal(M.cplMovilPaid285(c,s,hoy).at(-1).y,null);}
 assert(M.cplMovilPaid285({...c,tienda_online:true},serie,hoy).every(p=>p.y===null));
 const src=fs.readFileSync(__dirname+'/modulos/captacion.js','utf8');
 const env={esTienda:()=>false};vm.createContext(env);const start=src.indexOf('function cifras('),end=src.indexOf('\nfunction ',start+10);vm.runInContext(src.slice(start,end)+'\n;globalThis.calc=cifras;',env);
 const a={...c,ghl:{conectado:true},despacho:{leads_meta_7d:10,leads_ghl_7d:100,pct_llegan_crm:1}};const totals=env.calc([a],d);assert.equal(totals.sumGhl,100);assert.equal(totals.sumMeta,10);assert.equal(totals.pctCrm,null);assert.equal(totals.comparacionRecuentos,true);assert.equal(a.despacho.pct_llegan_crm,1);
 const tablas=[],opciones=[];const ui={filtroPendiente:()=>({fuga:true}),medirEmbudoCRM:()=>({parados:null,cohorte:null,sinEstado:null,asistencia:null,agendadas:null}),hoyMadrid:()=>hoy,h:()=>({replaceChildren(){}}),chipsFiltro:o=>{opciones.push(o);return {valor:()=> 'fuga'};},tablaDensa:o=>{tablas.push(o);return o;},panel:()=>({}),avisoParcial:()=>({})};vm.createContext(ui);
 const ps=src.indexOf('function pDespacho('),pe=src.indexOf('\nfunction ',ps+10);vm.runInContext(src.slice(ps,pe)+'\n;globalThis.despacho=pDespacho;',ui);ui.despacho({append(){}},{hoy},d,[a]);assert.equal(tablas[0].filas.length,1);assert.equal(tablas[0].filas[0].fuga,false);assert.equal(tablas[0].filas[0].llegan,null);assert(!opciones[0].opciones.some(o=>o.valor==='fuga'));assert.equal(opciones[0].valor,'');
 assert(!src.includes('pct_llegan_crm < 90'));assert(!src.includes('conversiones del píxel (compras'));assert(!src.includes("valor: 'fuga'"));assert(!src.includes("irAPestana(zona, 'despacho', { fuga: true })"));
 console.log('285B PASS: CPL tipado positivo; comercio/errores/ausencia/ventanas/eventos/referencia no evaluables; móvil siete observaciones exactas; recuentos independientes sin clamping ni fuga.');
})().catch(e=>{console.error(e);process.exit(1);});
