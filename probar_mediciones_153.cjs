const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 const load=async n=>import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(__dirname+'/modulos/'+n)).toString('base64'));
 const paid=await load('_paid_mediciones.js'),crm=await load('_crm_mediciones.js'),cita299=await load('_coste_cita_299.js');
 const d={datos_hasta:'2026-10-02',ventanas:{'7d':['2026-09-26','2026-10-02']}};
 const descriptor={version:'220.1',fuente:'meta_insights',nivel:'account',periodo_valido:true,desde:'2026-09-26',hasta:'2026-10-02',fecha_lectura:'2026-10-03',cohorte:'resultados_meta_sin_union_crm_ni_cualificacion_ro',tipo_lead:'lead',campos_observados:['gasto','leads']};
 const c={dinero:true,severidad:'critico',cpl_resumen:{ref:86,ref_base:'7d',fiable:true},objetivo:{cargado:true,cpl_objetivo:35,cuando:'2026-10-01'},motivos:[{nivel:'critico',clase_id:'paid',texto:'2.5 veces el techo anterior'}]};
 let m=paid.medirCplPaid(c,d,'2026-10-03');assert.equal(m.real,null);assert.equal(m.referenciaAnterior,86);assert.equal(m.objetivo,35);assert.equal(m.estado,'gris');assert.equal(m.evaluable,false);
 let n=paid.normalizarPaid(c,d,'2026-10-03');assert.equal(n.severidad,'dato');assert.equal(n.motivos[0].nivel,'dato');assert.match(n.motivos[0].texto,/Señal anterior/);assert.equal(c.severidad,'critico');assert.equal(c.motivos[0].nivel,'critico');
 const vigente={...c,gasto:{'7d':860},leads:{'7d':10},cpl_resumen:{...c.cpl_resumen,medicion:descriptor},objetivo:{...c.objetivo,confirmado:true,vigente:true,fuente_generado:'2026-10-03T08:00:00Z'}};
 assert.equal(paid.medirCplPaid(vigente,d,'2026-10-03').estado,'rojo');
 assert.equal(paid.medirCplPaid({...vigente,gasto:{'7d':200},cpl_resumen:{...vigente.cpl_resumen,ref:20}},d,'2026-10-03').estado,'verde');
 for(const extra of [{vigente:false},{fuente_generado:'2026-09-01'},{vigente_hasta:'2026-10-02'},{vigente_desde:'2026-10-04'},{periodo:'2026-09'},{cuando:'2026-10-01basura'}])assert.equal(paid.medirCplPaid({...vigente,objetivo:{...vigente.objetivo,...extra}},d,'2026-10-03').evaluable,false);
 for(const data of [{...d,datos_hasta:'2026-09-30'},{...d,ventanas:{}},{...d,ventanas:{'7d':['2026-09-27','2026-10-03']}}])assert.equal(paid.medirCplPaid(vigente,data,'2026-10-03').evaluable,false);
 assert.equal(paid.medirCplPaid({...vigente,cpl_resumen:{...c.cpl_resumen,fiable:false}},d,'2026-10-03').estado,'gris');
 assert.equal(paid.medirCplPaid({...vigente,dinero:false},d,'2026-10-03').real,null);
 assert.equal(paid.medirCplPaid({...vigente,cuenta_meta:{errores:['fixture']}},d,'2026-10-03').real,null);
 const fuente={hora:'2026-10-03T08:00:00Z',estado:'bien'},row={estado:'verde',citas_30d:{agendadas:8,celebradas:3,no_presentadas:1,asistencia_pct:99},citas_14d:{sin_estado:null},velocidad:{juzgables:3,en_1h:1},leads_30d:8};
 n=crm.normalizarFilaCRM(row,fuente,'2026-10-03');assert.equal(n.estado,'gris');assert.equal(n.citas_30d.asistencia_pct,75);assert.equal(n.citas_14d.sin_estado,null);assert.equal(n.sin_tocar_24h,null);assert.equal(row.citas_30d.asistencia_pct,99);
 assert.equal(crm.normalizarFilaCRM({...row,error:'fixture'},fuente,'2026-10-03').citas_30d.celebradas,null);
 assert.equal(crm.normalizarFilaCRM(row,{hora:'2026-10-04'},'2026-10-03').leads_30d,null);
 const strip=s=>s.replace(/import[\s\S]*?from ['"][^'"]+['"];\n/g,'').replace('export default {','const modulo = {');
 const env={conteoCRM:crm.conteoCRM};vm.createContext(env);vm.runInContext(strip(fs.readFileSync(__dirname+'/modulos/crm.js','utf8'))+';globalThis.sum=sumar;',env);
 let sum=env.sum([{citas_30d:{celebradas:3,no_presentadas:null}},{citas_30d:{celebradas:null,no_presentadas:1}}]);assert.equal(sum.asistencia,null);assert.equal(sum.sinTocar,null);assert.equal(sum.pctVerde,null);
 sum=env.sum([n]);assert.equal(sum.asistencia,75);assert.equal(sum.sinEstado14,null);
 // Quincenal real: no fuente->Sin dato y bitácora fuera de la ventana queda fuera de texto/copiar.
 const rendered=[];const h=(tag,attrs,...children)=>({tag,attrs,children});
 const e={...cita299,h,panel:(x,...children)=>({x,children}),vacio:x=>x,medirEmbudoCRM:crm.medirEmbudoCRM,fmt:{num:v=>v===null?'Sin dato':String(v),eur:v=>String(v),pct:v=>String(v)},hoyMadrid:()=> '2026-10-03',botonConfirmar:x=>x,icono:()=>'',copiar:()=>{}};
 vm.createContext(e);vm.runInContext(strip(fs.readFileSync(__dirname+'/modulos/captacion.js','utf8'))+';globalThis.q=tQuincenal;',e);
 const bitacora=new Map([['fixture',[{creada:'2026-09-27',_local:true,texto:'DENTRO'},{creada:'2026-10-04',_local:true,texto:'FUERA'}]]]);
 e.q({append:x=>rendered.push(x)},{hoy:'2026-10-03',soloLectura:true},{fuentes:[],bitacora},{cliente_id:'fixture',nombre:'Fixture',quincenal:{periodo:['2026-09-20','2026-10-02']},ghl:{conectado:true,citas:{}}});
 const text=JSON.stringify(rendered);assert(text.includes('Sin dato'));assert(!text.includes('Todas con estado'));assert(!text.includes('FUERA'));assert(text.includes('DENTRO'));assert(text.includes('no son una misma cohorte'));
 // Overview real: null no se imprime como0 ni colorea asistencia con umbral anterior.
 const tablas=[];
 e.h=(tag,attrs,...children)=>({tag,attrs,children,replaceChildren(...x){this.children=x;}});
 e.avisoParcial=x=>x;e.chipsFiltro=()=>({valor:()=>''});e.tablaDensa=x=>{tablas.push(x);return x;};e.logoCliente=()=>'';e.chipEstado=(color,texto)=>({color,texto});e.medirCplPaid=paid.medirCplPaid;
 vm.runInContext('globalThis.despacho=pDespacho;globalThis.cpl=celdaCpl;',e);
 e.despacho({append:()=>{}},{hoy:'2026-10-03'},{fuentes:[{id:'ghl',...fuente}]},[{nombre:'Fixture',despacho:{},ghl:{conectado:true,embudo:{},citas:{}}}]);
 const tabla=tablas[0],fila=tabla.filas[0];assert.equal(fila.sinEstado,null);assert.equal(fila.asis,null);
 //425 usa raya compacta para unknown; los asserts null de la medición permanecen.
 assert.equal(tabla.columnas.find(x=>x.clave==='sinEstado').celda(fila),'—');
 const celda=e.cpl(c,35,d);assert(JSON.stringify(celda).includes('gris'));assert(!JSON.stringify(celda).includes('verde'));
 console.log('153 PASS: CPL vigente/legacy/ventanas/errores, normalización CRM, agregado pareado real, quincenal real y pureza.');
})().catch(e=>{console.error(e);process.exitCode=1;});
