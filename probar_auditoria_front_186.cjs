// Reproducciones de UI actual; sólo fixtures y módulos puros, sin DOM/red/estado real.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 const load=async n=>import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(__dirname+'/modulos/'+n,'utf8')).toString('base64'));
 const paid=await load('_paid_mediciones.js'),crm=await load('_crm_mediciones.js');
 const d={datos_hasta:'2026-10-02',ventanas:{'7d':['2026-09-26','2026-10-02']}};
 const descriptor={version:'220.1',fuente:'meta_insights',nivel:'account',periodo_valido:true,desde:'2026-09-26',hasta:'2026-10-02',fecha_lectura:'2026-10-03',cohorte:'resultados_meta_sin_union_crm_ni_cualificacion_ro',tipo_lead:'lead',campos_observados:['gasto','leads']};
 const c={dinero:true,cpl_resumen:{ref:100,ref_base:'7d',fiable:true},objetivo:{cargado:true,cpl_objetivo:40,cuando:'2026-10-01',vigente:true,fuente_generado:'2026-10-03',periodo:'2026-10',confirmado:false,estado:'propuesta'}};
 const m=paid.medirCplPaid(c,d,'2026-10-03');assert.equal(m.evaluable,false);assert.equal(m.estado,'gris');
 const g={embudo:{contactos_90d:10,funnel:{nuevo:10},cohorte_30d:10,estancados_72h:3}};
 for(const fuente of [{hora:'2026-10-03',estado:'error',errores:['fixture']},{hora:'2020-01-01',estado:'bien'}]){
  const r=crm.medirEmbudoCRM(g,fuente,'2026-10-03');assert.equal(r.fechaValida,false);assert.equal(r.parados,null);
 }
 const src=fs.readFileSync(__dirname+'/modulos/captacion.js','utf8');
 const b=src.match(/^const crmDe = .*$/m);assert(b);assert(!src.includes('JEFA_CRM'));
 const env={};vm.createContext(env);vm.runInContext(b[0]+'\nglobalThis.destino=crmDe({equipo:{}});',env);
 assert.equal(env.destino,null);
 const confirmado={...c,gasto:{'7d':1000},leads:{'7d':10},cpl_resumen:{...c.cpl_resumen,medicion:descriptor},objetivo:{...c.objetivo,confirmado:true,estado:'confirmado'}};assert.equal(paid.medirCplPaid(confirmado,d,'2026-10-03').estado,'rojo');
 const legado={...c,objetivo:{...c.objetivo}};delete legado.objetivo.confirmado;delete legado.objetivo.estado;assert.equal(paid.medirCplPaid(legado,d,'2026-10-03').evaluable,false);
 for(const extra of [{datos_hasta:null},{datos_hasta:'2020-01-01'},{estado:undefined},{estado:'error'}])assert.equal(crm.medirEmbudoCRM(g,{hora:'2026-10-03',estado:'bien',...extra},'2026-10-03').fechaValida,false);
 const actual=crm.medirEmbudoCRM(g,{hora:'2026-10-03',estado:'bien'},'2026-10-03');assert.equal(actual.parados,3);assert.equal(actual.conversiones,null);assert.equal(actual.ventas,null);
 assert.equal(crm.medirEmbudoCRM(g,{hora:'2026-10-03 08:12',estado:'bien'},'2026-10-03').parados,3);
 for(const hora of ['2026-10-03 24:00','2026-10-03 08:99','2026-10-03 08:12basura'])assert.equal(crm.medirEmbudoCRM(g,{hora,estado:'bien'},'2026-10-03').fechaValida,false);
 assert.equal(paid.medirCplPaid({...confirmado,objetivo:{...confirmado.objetivo,fuente_generado:'2026-10-03 08:12'}},d,'2026-10-03').evaluable,true);
 const vieja=crm.normalizarFilaCRM({estado:'rojo',velocidad:{juzgables_72h:5,cuatro_en_72h:1,pct_4en72:20,mediana_min:12},motivos:[{nivel:'rojo',texto:'Motivo antiguo'}]},{hora:'2020-01-01',estado:'bien'},'2026-10-03');assert.equal(vieja.estado,'gris');assert.equal(vieja.velocidad.pct_4en72,null);assert.equal(vieja.velocidad.mediana_min,null);assert.match(vieja.motivos[0].texto,/Señal anterior/);
 const menus=[];const ui={h:(tag,attrs,...children)=>({tag,attrs,children}),icono:()=>'',menuMas:o=>{menus.push(o);return o;}};vm.createContext(ui);const sinImports=src.replace(/import[\s\S]*?from ['\"][^'\"]+['\"];\n/g,'').replace('export default {','const modulo = {');vm.runInContext(sinImports+';globalThis.caso=botonesCaso;',ui);ui.caso({}, {cliente_id:'fixture',nombre:'Fixture',equipo:{}}, {}, {clase_id:'crm'});assert(!menus[0].items.some(x=>/Tarea al CRM/.test(x.texto)));
 console.log('186 PASS: objetivo propuesto/legacy gris, confirmado positivo; CRM error/antigua/null desconocido; responsable ausente sin fallback nominal.');
})().catch(e=>{console.error(e);process.exitCode=1;});
