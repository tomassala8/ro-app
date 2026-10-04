// Serialización real _tarea_ia +337; fixtures canónicas sintéticas, sin API/HTML externo.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const b={Date,Intl,URL};vm.createContext(b);const load=file=>fs.readFileSync(__dirname+'/modulos/'+file+'.js','utf8').replace(/^import[^;]+;\s*/gm,'').replace(/export /g,'');vm.runInContext(load('_tarea_ia'),b);vm.runInContext(load('_prioridades_contexto_337'),b);
const TODAY='2026-10-05';
const fixture=(area='accounts')=>({cliente_id:'cliente-fixture',regla_id:'seguimiento_quincenal_especialista'+(area==='accounts'?'_account':''),area,titulo:'Verificar seguimiento',motivo:'Referencia metodológica',accion:'Preparar revisión',criterio_entrega:'Contrastar evidencia',responsable_id:'owner-private',responsable_role:'trafficker',ejecutor_operativo:'trafficker',comprobador_role:area==='accounts'?'account':'trafficker',metodo_308:{cliente_id:'cliente-fixture',regla_id:'seguimiento_quincenal_especialista',cadencia_dias:15,responsable_role:'trafficker',responsable_id:'owner-private',responsable_confirmado:true,estado:'preparar_seguimiento',ultima_confirmada:'2026-09-28',proxima_revision:'2026-10-13',reunion_agendada:null,incumplimiento:null,hoy:TODAY,cobertura_completa:false,fuente_regla:'decision_humana_metodo_vigente',fuente_celebracion:'zoom',contacto_semanal_account:'separado',reunion_mensual_account:'separada'},evidencias:[{fuente:'metodo_confirmado_local',fecha:TODAY,periodo:null,cobertura:'regla_confirmada_no_historial_exhaustivo',vigencia:'actual',texto:'Regla 15 días: no prueba de celebración.'}]});
const send=(r=fixture(),today=TODAY)=>b.encargoPrioridades337(r,'Cliente ficticio',{paid:'Paid',accounts:'Accounts'},today);
let n=0;const test=f=>{f();n++;};
for(const area of ['accounts','paid'])test(()=>{const out=send(fixture(area));for(const t of ['Última celebración registrada: 2026-09-28','Fuente: zoom','Próxima REVISIÓN calculada: 2026-10-13','no cita agendada','Ejecutor operativo: Trafficker',`Comprobador: ${area==='accounts'?'Account':'Trafficker'}`,'no demuestra cumplimiento'])assert(out.includes(t),t);assert(!out.includes('owner-private'));assert(!out.includes('cliente-fixture'));assert(out.includes('Acceso: Desconocido'));});
for(const clock of ['',null,'2026-02-30','2026-10-04','2026-10-06','2026-10-05T10:00:00Z'])test(()=>assert(!send(fixture(),clock).includes('Método de seguimiento autorizado:')));
for(const mutate of [r=>r.regla_id='other',r=>r.area='crm',r=>r.metodo_308.regla_id='other',r=>r.metodo_308.cliente_id='foreign',r=>r.metodo_308.cadencia_dias='15',r=>r.metodo_308.cadencia_dias=30,r=>r.metodo_308.responsable_confirmado=false,r=>r.responsable_id='foreign',r=>r.metodo_308.responsable_id=['owner-private'],r=>r.metodo_308.responsable_role='account',r=>r.ejecutor_operativo='account',r=>r.comprobador_role='direccion',r=>r.metodo_308.fuente_regla='arbitrary',r=>r.metodo_308.reunion_agendada=true,r=>r.metodo_308.incumplimiento=true,r=>r.metodo_308.cobertura_completa='false',r=>r.metodo_308.ultima_confirmada='2026-02-30',r=>r.metodo_308.ultima_confirmada='2026-10-06',r=>r.metodo_308.proxima_revision='2026-10-14',r=>r.metodo_308.fuente_celebracion='PRIVATE@CONTACT.invalid',r=>r.metodo_308.estado='revisar_cadencia',r=>r.metodo_308.contacto_semanal_account='sustituido',r=>r.evidencias=[],r=>r.evidencias[0].vigencia='referencia',r=>r.evidencias[0].fecha='2026-10-04',r=>r.evidencias.push({...r.evidencias[0]})])test(()=>{const r=fixture();mutate(r);const out=send(r);assert(!out.includes('Método de seguimiento autorizado:'));assert(out.includes('Criterio de entrega y comprobación'));});
test(()=>{const r=fixture();Object.assign(r.metodo_308,{ultima_confirmada:null,proxima_revision:null,fuente_celebracion:null,estado:'confirmar_programacion'});const out=send(r);assert(out.includes('Última celebración registrada: pendiente de evidencia'));assert(out.includes('Próxima REVISIÓN calculada: pendiente de evidencia'));assert(!out.includes('Fuente: null'));});
test(()=>{const r=fixture();Object.assign(r.metodo_308,{ultima_confirmada:null,proxima_revision:null,fuente_celebracion:null,estado:'confirmar_programacion',cobertura_completa:true});assert(!send(r).includes('Método de seguimiento autorizado:'));});
test(()=>{const r=fixture();Object.assign(r.metodo_308,{ultima_confirmada:'2026-09-01',proxima_revision:'2026-09-16',estado:'confirmar_recencia'});assert(send(r).includes('Próxima REVISIÓN calculada: 2026-09-16'));r.metodo_308.estado='revisar_cadencia';assert(!send(r).includes('Método de seguimiento autorizado:'));});
test(()=>{const r=fixture(),before=JSON.stringify(r);send(r);assert.equal(JSON.stringify(r),before);});
test(()=>{const r=fixture();delete r.metodo_308;assert.equal(send(r),b.encargoPrioridades337(r,'Cliente ficticio',{paid:'Paid',accounts:'Accounts'}));});
test(()=>{const r=fixture();r.motivo='correo person@example.invalid contraseña=x';const out=send(r);assert(!out.includes('person@example.invalid'));assert(!out.includes('contraseña=x'));assert(out.includes('[dato protegido omitido]'));});
const {execFileSync}=require('child_process');
const reales=JSON.parse(execFileSync('python3',['-c',String.raw`
import json
from cerebro_operativo import generar
hoy='2026-10-05'
personas=[{'id':'paid','estado':'activo','puestos':['trafficker']}]
asignaciones=[{'persona_id':'paid','cliente_id':'fixture','silla':'trafficker','desde':'2026-09-01','principal':True,'confianza':'confirmada'}]
fila={'cliente_id':'fixture','regla_id':'seguimiento_quincenal_especialista','cadencia_dias':15,'responsable_role':'trafficker','responsables_ids':['paid'],'responsable_id':'paid','incumplimiento':None,'ultima_confirmada':'2026-09-28','proxima_revision':'2026-10-13','fuentes_operativas':[{'tipo':'reunion_celebrada','fecha':'2026-09-28','fuente':'zoom'}]}
doc={'hoy':hoy,'sugerencias':[fila],'cobertura_reuniones':{'completa':False},'_ids_308':['fixture'],'_personas_308':personas,'_asignaciones_308':asignaciones}
print(json.dumps(generar(hoy=hoy,metodo=doc)['recomendaciones']))
`],{cwd:__dirname,encoding:'utf8'}));
test(()=>{assert.equal(reales.length,2);for(const r of reales){const out=send(r);assert(out.includes('Última celebración registrada: 2026-09-28'));assert(out.includes('Próxima REVISIÓN calculada: 2026-10-13'));assert(out.includes('no cita agendada'));assert(out.includes(`Comprobador: ${r.area==='accounts'?'Account':'Trafficker'}`));assert(!out.includes('Responsable: paid'));assert(!out.includes('Cliente: fixture'));}});
const source337=fs.readFileSync(__dirname+'/probar_prioridades_contexto_337.cjs','utf8');
const H=new Function('require','__dirname',source337.slice(0,source337.indexOf('let total=0;'))+';return {cargar,main,contexto,boton,click};')(require,__dirname);
(async()=>{
 for(const r of reales){
  const ui=H.cargar(),m=H.main(),c=H.contexto(async route=>route==='cerebro/operativo'?{recomendaciones:[r],cobertura:{clientes:[]}}:{sugerencias:[]});
  c.hoy=TODAY;c.clientesVisibles=[{id:'fixture',nombre:'Cliente ficticio',activo_confirmado:true,detalle:true}];c.clientes=c.clientesVisibles.map(x=>({...x,activo:true,estado:"activo"}));
  await ui.modulo.render(m,c);await H.click(H.boton(m,'Revisar'));
  const ta=m.descendants().find(x=>x.tag==='textarea'&&x.attrs['aria-label']?.startsWith('Encargo'));
  assert(ta);assert(ta.value.includes('Última celebración registrada: 2026-09-28'));assert(ta.value.includes('Próxima REVISIÓN calculada: 2026-10-13'));assert(ta.value.includes('Cliente: Cliente ficticio'));
  await H.click(H.boton(m,'copiar-ia'));assert.equal(ui.copies[0],ta.value);n++;
 }
 console.log(n+' grupos663 PASS: fechas/papeles canónicos, reloj actual obligatorio, productor/textarea/copy reales.');
})().catch(e=>{console.error(e);process.exitCode=1});
