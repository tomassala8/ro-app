const fs=require('fs'),vm=require('vm'),assert=require('assert');
class El{constructor(tag,attrs,...children){this.tag=tag;this.attrs=attrs||{};this.children=children.flat().filter(x=>x!=null);this.isConnected=true;this.events={};}addEventListener(k,v){this.events[k]=v;}removeAttribute(k){delete this.attrs[k];}append(...x){this.children.push(...x);}replaceChildren(...x){this.children=x;}}
const h=(t,a,...c)=>new El(t,a,...c),tables=[];
const s={console,Date,Map,Set,JSON,Number,Array,String,Object,Promise,h,hoyMadrid:()=> '2026-10-03',
panel:(o,n)=>h('section',{},h('h2',{},o.titulo),o.sub,n),chipEstado:(c,t)=>h('span',{},t),
tablaDensa:o=>{tables.push(o);return h('table',{},o.filas.length?o.filas.map(r=>h('tr',{},o.columnas.map(c=>c.celda?c.celda(r):r[c.clave]))):o.vacio?.titulo);}};
vm.createContext(s);
const code=fs.readFileSync(__dirname+'/modulos/_operaciones_dia_direccion_265.js','utf8').replace(/^import .*;\n/gm,'').replace(/export /g,'');
vm.runInContext('globalThis.panelRituales269=(()=>{'+fs.readFileSync(__dirname+'/modulos/_operaciones_registros_269.js','utf8').replace(/^import .*;\n/gm,'').replace(/export /g,'')+'\nreturn panelRituales269;})();',s);
Object.assign(s,vm.runInContext('(()=>{'+fs.readFileSync(__dirname+'/modulos/_operaciones_registros_272.js','utf8').replace(/^import .*;\n/gm,'').replace(/export /g,'')+'\nreturn {panelEncargos272,panelFotosControl272};})();',s));
function cargaReal(nombre,exports){const src=fs.readFileSync(__dirname+'/modulos/'+nombre+'.js','utf8').replace(/^import .*;\n/gm,'').replace(/export /g,'');Object.assign(s,vm.runInContext('(()=>{'+src+'\nreturn {'+exports.join(',')+'};})();',s));}
cargaReal('_rastro_declarativo_392',['renderRastroDeclarativo392']);
cargaReal('_decision_durable_382',['ambitoDecision382','prepararDecision382','guardarDecision382']);
cargaReal('_operaciones_decisiones_387',['renderDecisiones387']);
cargaReal('_informe_semanal_operaciones',['panelInformeSemanalOperaciones']);
cargaReal('_horas_diarias_238',['serieHorasDiaria238']);
cargaReal('control_cartera',['prepararControlCartera','resumirAccountsControl']);
cargaReal('_control_artifact_250',['pintarMapaControl250','COLUMNAS_CONTROL_250']);
cargaReal('_historial_diario_364',['ambitoHistorial364','modeloHistorial364','historialVigente364','cargarHistorial364']);
cargaReal('_bandas_horas_381',['bandaHoras381']);
cargaReal('_imputa_personal_390',['ambitoImputa390','modeloImputa390','cargarImputa390','celdaImputa390','imputaVigente390']);
cargaReal('_control_cartera_ruta_239',['puestoControl239']);
cargaReal('_kpis_compactos_396',['celdaKpiCompacta396','LEYENDA_KPIS_396']);
cargaReal('_operaciones_accounts_263',['prepararAccounts263']);
cargaReal('_operaciones_feedback_273',['renderFeedback273']);
cargaReal('_meta_semantica_285',['semanticaMeta285']);
cargaReal('_operaciones_bandeja_270',['prepararBandeja270']);
cargaReal('_operaciones_prioridades_300',['renderPrioridades300']);
cargaReal('_operaciones_resumen_274',['renderResumen274']);
cargaReal('_planes_pendientes_327',['leerPlanes327','clasificarPlan327']);
cargaReal('_tendencias_operaciones_329',['tendenciasFotos329']);
cargaReal('_miniserie_operaciones_439',['modeloMiniserie439','pintarMiniserie439']);
cargaReal('_numeros_semanales_449',['pintarNumerosSemanales449']);
vm.runInContext(code+'\nglobalThis.R=REFERENCIAS_265;',s);
const text=n=>typeof n==='object'&&n ? (n.children||[]).map(text).join(' ') : String(n??'');
const p={id:'tomas',estado:'activo',puestos:['direccion']};
function ctx(){return {real:{...p},persona:{...p},datos:{personas:[{...p}]},clientesVisibles:[{id:'ok',activo_confirmado:true,detalle:true},{id:'denied',activo_confirmado:true,detalle:true}],clientes:[{id:'ok'},{id:'denied'}],
veModulo:()=>true,ver:d=>({ok:d.cliente_id==='ok'}),vigente:()=>true,servidor:true,nombre:id=>id,
datosModulo:async()=>({}),api:async ruta=>ruta==='operaciones/registros'?{version:'269.1',propietario:'tomas',registros:[],periodos:{manana:'2026-10-03',cierre:'2026-10-03',lunes:'2026-09-28',viernes:'2026-10-02',mes:'2026-10'},puede_registrar:false}:{}};}
let casos=0;
(async()=>{
const nombres=ctx();nombres.clientesVisibles[0].nombre='Proyecto autorizado';nombres.nombre=()=>{throw Error('No usar el catálogo de personas para clientes');};
assert.equal(s.nombreCliente265(nombres,'ok'),'Proyecto autorizado');
assert.equal(s.nombreCliente265(nombres,'denied'),'Cliente por confirmar');
nombres.clientesVisibles.push({...nombres.clientesVisibles[0]});assert.equal(s.nombreCliente265(nombres,'ok'),'Cliente por confirmar');casos++;
const artifact=fs.readFileSync('/Users/tomassala/Downloads/PANEL_OPERACIONES_2026-10-01/plantilla.html','utf8');
for(const labels of [s.R.indicadores,s.R.numeros,s.R.tendencias,s.R.rituales])for(const label of labels)assert(artifact.includes(label),label);casos++;
for(const clave of ['dia','tomas','rastro']){const c=ctx(),root=h('main',{});await s.renderDiaDireccion265(root,c,clave);const t=text(root);
 for(const label of clave==='dia'?[...s.R.indicadores,...s.R.numeros,...s.R.rituales,'Encargos de Tomás']:clave==='tomas'?['Decisiones para Tomás',...s.R.tendencias,'Rojos sin plan o sin visto de Coti','Informe de la semana para Tomás','Fotos de los miércoles y viernes','Bajas con su motivo']:['Acciones registradas','Por día','Por cliente','Rituales'])assert(t.includes(label),label);
 const sinDatoAccesible=n=>n&&typeof n==='object'&&(/Sin dato confirmado/.test(n.attrs?.title||'')||(n.children||[]).flat(Infinity).some(sinDatoAccesible));
 assert(t.includes('Sin dato')||t.includes('Sin registros')||sinDatoAccesible(root));}casos++;
const c=ctx();const m=s.modelo265(c,{alertas:{alertas:[{id:'a',cliente_id:'ok'},{id:'b',cliente_id:'denied'},{id:'c',cliente_id:'absent'}]},
verdad:{clientes:[{cliente_id:'ok',gravedad:'critico'},{cliente_id:'denied',gravedad:'critico'}]},
rastro:{registro:[{cliente_id:'ok',creada:'2026-10-02',accion:'x'},{cliente_id:'denied',creada:'2026-10-02',accion:'y'}]},
decisiones:{decisiones:[{id:'b',cliente_id:'denied'},{id:'a',cliente_id:'ok',tipo:'para_coti',creada:'2026-10-01 00:00:00'}]}});
assert.equal(m.prioridades.length,1);assert.equal(m.rojos.length,1);assert.equal(m.registro.length,1);assert.equal(m.decisiones.length,1);assert.equal(m.decisiones[0].reloj,24);assert.equal(m.decisiones[0].estado265,'Fuera de plazo');assert(m.tendencias.every(x=>x.actual===null));casos++;
c.clientesVisibles.push({id:'ok',activo_confirmado:true,detalle:true});assert.equal(s.modelo265(c,{alertas:{alertas:[{cliente_id:'ok'}]}}).prioridades.length,0);casos++;
for(const change of [c=>c.persona.id='other',c=>c.real.estado='baja',c=>c.datos.personas.push({...p}),c=>c.veModulo=()=>false]){
const c=ctx();change(c);let calls=0;c.datosModulo=async()=>{calls++;return {};};const root=h('main',{});await s.renderDiaDireccion265(root,c,'tomas');assert.equal(calls,0);}casos++;
let release;const delayed=new Promise(r=>release=r),c2=ctx(),root=h('main',{});c2.datosModulo=()=>delayed;
const reading=s.renderDiaDireccion265(root,c2,'dia');c2.persona.id='other';release({});await reading;assert(!text(root).includes('Tus indicadores'));casos++;
const c3=ctx(),root3=h('main',{});c3.datosModulo=async path=>{if(path.startsWith('produccion'))throw Error('PRIVATE_SECRET');return {};};
await s.renderDiaDireccion265(root3,c3,'dia');assert(text(root3).includes('Tus indicadores'));assert(text(root3).includes('Fuentes no disponibles: produccion'));assert(!text(root3).includes('PRIVATE_SECRET'));casos++;
let n=0;const c4=ctx();c4.veModulo=()=>false;c4.api=async()=>{n++;return {registro:[{accion:'secret'}]};};await s.renderDiaDireccion265(h('main',{}),c4,'rastro');assert.equal(n,0);casos++;
const ops=ctx();ops.real={id:'mili',estado:'activo',puestos:['operaciones']};ops.persona={...ops.real};ops.datos.personas=[{...ops.real}];assert(s.puerta265(ops,'tomas'));const opsRoot=h('main',{});await s.renderDiaDireccion265(opsRoot,ops,'tomas');assert(text(opsRoot).includes('Decisiones para Tomás'));casos++;
const mm=s.modelo265(ctx(),{direccion:{cierre_mes:{bajas:[{cliente:'historico',cuota:123,fecha_baja:'2026-09-01',motivo:'fixture'}]}}});assert(!('cuota' in mm.bajas[0]));assert.equal(mm.prioridades.length,0);casos++;
const dedup=ctx(),lecturas=new Map();dedup.datosModulo=async path=>{lecturas.set(path,(lecturas.get(path)||0)+1);return {};};await s.renderDiaDireccion265(h('main',{}),dedup,'dia');for(const path of ['produccion/produccion','alertas/p_tomas','horas/horas','bandeja/por_cliente','bandeja/bandeja','nuevos/nuevos','informes/informes'])assert.equal(lecturas.get(path),1,path);casos++;

for(const estado of ['sin_plan','visto','sin_revision','incompatible']){
 const cp=ctx(),rp=h('main',{});cp.datos.personas.push({id:'constanza',estado:'activo',puestos:['proyectos']});cp.clientesVisibles[0].nombre='Proyecto plan327';
 cp.datosModulo=async ruta=>ruta==='verdad/clientes'?{clientes:[{cliente_id:'ok',gravedad:'critico',motivo:'Motivo único327'}]}:{};
 const dto={cliente_id:'ok',version:0,plan:null,revision:null,historial:[],capacidades:{},origen:'local'};
 if(estado!=='sin_plan'){dto.version=2;dto.plan={version:1,que:'Texto privado del plan no resumido327',responsable_id:'account',plazo:'2026-10-12'};if(estado!=='sin_revision')dto.revision={version:2,plan_version:estado==='incompatible'?99:1,actor_id:'constanza',estado:'visto'};}
 let planes=0;cp.api=async(ruta,op)=>{assert(!op?.metodo||op.metodo==='GET');if(ruta==='en-rojo/planes?cliente_id=ok'){planes++;return dto;}return {};};
 await s.renderDiaDireccion265(rp,cp,'tomas');assert.equal(planes,1);assert(!text(rp).includes('Texto privado del plan'));
 if(estado==='visto'){assert(!text(rp).includes('Motivo único327'));assert(text(rp).includes('1 con plan vigente visto por Coti'));}
 else{assert(text(rp).includes('Motivo único327'));assert(text(rp).includes(estado==='sin_plan'?'Sin plan local registrado':estado==='sin_revision'?'pendiente de revisión':'Plan / revisión no comprobados'));}
 casos++;
}

for(const mode of ['legacy','typed','wrongscope','wrongactor']){
 const c=ctx(),root=h('main',{}),scope='a'.repeat(64);let calls=0;
 const now=new Date(),past=new Date(now.getTime()-3600000),past2=new Date(now.getTime()-7200000);
 const metricas=(value,cut)=>s.R.tendencias.map((etiqueta,i)=>({id:['pend48','rojas','imputacion','revision48','nota_accounts','semaforo_sin','rastro'][i],etiqueta,valor:i===1?value:null,fecha_fuente:i===1?cut:null,estado:i===1?'observado_copia':'desconocido'}));
 const f=(objeto,value,cut)=>({tipo:'foto',objeto,scope_hash:scope,registrado_por:'tomas',registrado_en:now.toISOString(),cumplimiento:null,exhaustiva:false,metricas:metricas(value,cut),mediciones_329:mode==='typed'?[{version:'329.1',id:'rojas',valor:value,validado_servidor:true,origen:'medicion_copia',scope_hash:scope,cohorte_hash:'b'.repeat(64),definicion_hash:'c'.repeat(64),unidad:'alarmas',completa:false,corte:cut,leido:now.toISOString(),periodo:{tipo:'stock'}}]:[]});
 const doc={version:'272.1',propietario:mode==='wrongactor'?'foreign':'tomas',scope_foto_actual:mode==='wrongscope'?'d'.repeat(64):scope,registros:[f('old',11,past2.toISOString()),f('new',9,past.toISOString())],puede_registrar:false};
 c.api=async ruta=>{if(ruta==='operaciones/control'){calls++;return doc;}return {};};
 await s.renderDiaDireccion265(root,c,'tomas');const tt=text(root);assert.equal(calls,1);for(const et of s.R.tendencias)assert(tt.includes(et));
 const tabla= [...tables].reverse().find(t=>t.columnas.some(x=>x.clave==='comparacion'));
 assert.equal(tabla.filas.length,7);
 const cell=tabla.columnas.find(x=>x.clave==='actual').celda(tabla.filas[1]);
 assert.equal(text(cell),mode==='typed'?'9':'—');if(mode!=='typed')assert.equal(cell.attrs['aria-label'],'Sin medición comparable confirmada');
 assert.equal(tabla.filas[1].actual,mode==='typed'?9:null);assert.equal(tabla.filas[1].anterior,mode==='typed'?11:null);
 if(mode==='legacy')assert(tt.includes('Referencia de copia: 11'));
 if(mode==='wrongscope'||mode==='wrongactor')assert(!tt.includes('Referencia de copia: 11'));
 casos++;
}
const staleC=ctx(),staleRoot=h('main',{});let releaseControl;const waitControl=new Promise(r=>releaseControl=r);staleC.api=async ruta=>ruta==='operaciones/control'?waitControl:{};const waiting=s.renderDiaDireccion265(staleRoot,staleC,'tomas');staleC.datos.personas[0].estado='inactivo';releaseControl({version:'272.1',propietario:'tomas',scope_foto_actual:'a'.repeat(64),registros:[]});await waiting;assert(!text(staleRoot).includes('¿Mejora o empeora?'));casos++;

const revoked=ctx(),revokedRoot=h('main',{});let permit=true,doneScope;revoked.ver=()=>({ok:permit});const gate=new Promise(r=>doneScope=r);revoked.api=async path=>path==='operaciones/control'?gate:{};const rendering=s.renderDiaDireccion265(revokedRoot,revoked,'tomas');permit=false;doneScope({version:'272.1',propietario:'tomas',scope_foto_actual:'a'.repeat(64),registros:[]});await rendering;assert(text(revokedRoot).includes('— sin medición o comparación acreditada.'));assert(text(revokedRoot).includes('No se pudieron leer las fotos de control.'));casos++;
console.log(casos+' grupos265 PASS: secciones originales, scopes, unknown, revocación, errores parciales e histórico sin importes.');
})().catch(e=>{console.error(e);process.exit(1);});
