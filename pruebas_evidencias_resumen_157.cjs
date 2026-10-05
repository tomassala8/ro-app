const fs=require('fs'),vm=require('vm'),assert=require('assert'),cp=require('child_process'),path=require('path');
const box={};vm.createContext(box);vm.runInContext(fs.readFileSync(path.join(__dirname,'modulos/_evidencias_resumen.js'),'utf8').replace(/export /g,''),box);
const identidad={real_id:'own',vista_id:'own',generacion:1};
const r={cliente_id:'uno',contactos_declarados:0,reuniones_declaradas:2,source_kind:'registro_equipo',verificacion_externa:false,cumplimiento:null};
const response={semana_inicio:'2026-09-28',cobertura:'parcial',verificacion_externa:false,cumplimiento:null,clientes:[r]};
const base={respuesta:response,semana_inicio:'2026-09-28',cliente_ids:['uno'],identidad,identidad_actual:{...identidad},vigente:true};
const preparar=x=>box.prepararResumenEvidencias({...base,...x});let casos=0;
function unknown(x){const d=preparar(x);assert.equal(d.estado,'sin_dato');for(const f of d.filas){assert.equal(f.contactos_declarados,null);assert.equal(f.color,'gris');assert.equal(f.cumplimiento,null);}casos++;}
let d=preparar();assert.equal(d.filas[0].contacto_texto,'0 contactos declarados');assert.equal(d.filas[0].reunion_texto,'2 reuniones declaradas');assert.equal(d.filas[0].actividad,'desconocida');assert.equal(d.filas[0].color,'gris');casos++;
unknown({respuesta:null});unknown({vigente:false});unknown({identidad_actual:{...identidad,generacion:2}});unknown({identidad_actual:{...identidad,vista_id:'otro'}});unknown({identidad_actual:{...identidad,real_id:'ops'}});
for(const semana of ['2026-09-29','2026-02-30','2026-09-21'])unknown({semana_inicio:semana});
for(const extra of [{cobertura:'completa'},{cumplimiento:true},{verificacion_externa:true}])unknown({respuesta:{...response,...extra}});
for(const extra of [{cliente_id:'ajeno'},{estado:'revocado'},{source_kind:'proveedor'},{verificacion_externa:true},{cumplimiento:false},{contactos_declarados:-1},{contactos_declarados:0.5},{contactos_declarados:null},{contactos_declarados:Number.MAX_SAFE_INTEGER+1},{registrado_por:'persona_privada'}])unknown({respuesta:{...response,clientes:[{...r,...extra}]}});
unknown({respuesta:{...response,clientes:[r,r]}});unknown({cliente_ids:['uno','uno']});
d=preparar({cliente_ids:['uno','dos']});assert.equal(d.estado,'parcial');assert.equal(d.filas[1].contactos_declarados,null);assert.equal(d.filas[1].contacto_texto,'Sin dato');casos++;
unknown({cliente_ids:[]}); // cartera retirada: respuesta antigua no puede reaparecer.
// Integración de contrato real151 sobre SQLite tempfile: uno revocado y uno activo.
const fixture=cp.execFileSync('python3',['-B','-c',`import json
from probar_evidencias_kpi_api_151 import Api
import evidencias_kpi_api as A
import uuid
t=Api();t.setUp()
try:
 r=t.post()[1]['registro']
 t.post({'accion':'revocar','cliente_id':'uno','clave':str(uuid.uuid4()),'registro_id':r['id'],'motivo':'correccion'})
 t.post({**t.body,'clave':str(uuid.uuid4()),'tipo':'reunion','canal':'video'})
 n,d=t.h._api_get(A.RUTA+'/resumen',{'semana_inicio':['2026-09-28']},t.own,t.own)
 assert n==200
 print(json.dumps(d))
finally:t.tearDown()`],{cwd:__dirname,encoding:'utf8'});
d=preparar({respuesta:JSON.parse(fixture)});assert.equal(d.filas[0].contactos_declarados,0);assert.equal(d.filas[0].reuniones_declaradas,1);assert.equal(d.filas[0].reunion_texto,'1 reunión declarada');assert.equal(d.filas[0].cumplimiento,null);casos++;
assert.equal(JSON.stringify(response),JSON.stringify(base.respuesta));
console.log(`${casos} casos pasan; fixture real151 temporal, sin datos reales ni proveedores.`);
