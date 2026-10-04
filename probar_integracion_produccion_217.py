"""217: cadena 208→core194→traducción/recibo209→proyección191→JS206. Sin red."""
import ast,copy,json,subprocess,types,unittest
from pathlib import Path
from unittest.mock import patch
import probar_transiciones_produccion_208 as B
import transiciones_produccion_208 as X
import transiciones_mi_trabajo as T
import intenciones_acciones as IA
from probar_transporte_sincronia_193 import cargar
HERE=Path(__file__).resolve().parent
NODE=Path('/Users/tomassala/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
class Cadena217(B.Pruebas):
 def setUp(self):
  super().setUp()
  self.sinc=cargar();self.ns=self.sinc.ejecutar.__globals__;self.queue_failure=False
  tree=ast.parse((HERE/'sincronia.py').read_text())
  nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'destino_produccion_recibo','recibo_transicion_tablero','enganchar'}]
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'sincronia209:AST217','exec'),self.ns)
  self.ns.update(conectar=self.connect,tarea=lambda _:dict(self.row,nombre='Fixture'),
   _reglas_piezas=lambda:self.p.REGLAS['revision_piezas'],_mi_trabajo=lambda:self.D,
   estados_de_tarea=lambda _:self.D['estados_lista']['list-fixture'],_persona=lambda pid:next((p for p in self.crudo['personas'] if p['id']==pid),{}),
   preparar=lambda c:c.executescript(self.sinc.TABLAS_SQL),_guardia=lambda*a:None,_tras_accion=self.queue,
   traceback=types.SimpleNamespace(print_exc=lambda:None))
  actual_module=types.SimpleNamespace(traducir=self.ns['traducir'])
  pat=patch.dict('sys.modules',{'sincronia':actual_module});pat.start();self.addCleanup(pat.stop)
  self.tree=ast.parse((HERE/'servir.py').read_text())
  validator=next(n for n in ast.walk(self.tree) if isinstance(n,ast.FunctionDef) and n.name=='validar_accion')
  branch=next(n for n in ast.walk(self.tree) if isinstance(n,ast.If) and '/api/acciones' in ast.unparse(n.test) and 'INSERT INTO acciones' in ast.unparse(n))
  fun=ast.parse('def api_post(self,ruta,real,persona,b):\n pass').body[0];fun.body=[branch]
  ns={'P':self.p,'E':self.s.E,'ACT':self.s.ACT,'ve_alguno':self.s.ve_alguno,'_enlaces_malos':lambda*a:False,
   'pieza_en_revision':self.s.pieza_en_revision,'puede_revisar_pieza':self.s.puede_revisar_pieza,
   'tarea_de_produccion':self.s.tarea_de_produccion,'registrar_agrupado':lambda*a:None,'registrar':lambda*a:None,'json':json,'conectar':self.connect}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[validator,fun],type_ignores=[])),'core194:AST217','exec'),ns)
  class H:
   def responder(self,code,body,*a,**k):return code,body
   def _api_get(self,*a):return None
  H.validar_accion=ns['validar_accion'];H.api_post=ns['api_post'];X.enganchar(H,self.s)
  self.ns['enganchar'](H,self.s);self.h=H()
  with self.connect() as con:IA.preparar(con)
 def queue(self,aid):
  if self.queue_failure:raise RuntimeError('Fallo de cola después de registro local')
  with self.connect() as con:
   act=dict(con.execute('SELECT * FROM acciones WHERE id=?',(aid,)).fetchone())
   canal,obj,cam,base,_=self.ns['traducir'](act)
   cid,_=self.sinc.crear_cambio(con,clave='accion:'+str(aid),accion_id=aid,quien=act['quien'],canal=canal,tipo=act['tipo'],objeto=obj,
    cliente_id=act['cliente_id'],cambio=cam,base=base,modo='simulado',modulo=act['modulo'])
  return {'id':cid,'estado':'simulado'}
 def post(self,b,actor=None):
  actor=actor or self.account
  return self.h.api_post('/api/acciones',actor,actor,copy.deepcopy(b))
 def counts(self):
  with self.connect() as c:return tuple(c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['acciones','intenciones_acciones','sinc_cambios'])
 def jsrecibo(self,r,b,actor=None):
  actor=actor or self.account
  js="""const fs=require('fs'),vm=require('vm');const c={URL};vm.createContext(c);for(const f of ['_tarea_ia.js','_detalle_tarea_197.js','_transicion_produccion_206.js'])vm.runInContext(fs.readFileSync('modulos/'+f,'utf8').replace(/^import[^;]+;\\s*/gm,'').replace(/export function /g,'function ').replace(/export const /g,'const '),c);const d=JSON.parse(fs.readFileSync(0,'utf8'));c.r=d.r;c.i=d.i;process.stdout.write(JSON.stringify(vm.runInContext('validarReciboRevision206(r,i)',c)));"""
  d={'r':r,'i':{'identidad':json.dumps([actor['id'],actor['id']],separators=(',',':')),'payload':b}}
  out=subprocess.run([str(NODE),'-e',js],cwd=HERE,input=json.dumps(d),text=True,capture_output=True,check=True)
  return json.loads(out.stdout)
 def project(self):
  with self.connect() as c:return T.proyectar(self.D,'task-fixture',c)
 def test_cadena_real_recibo_consumible_y_replay_sin_doble_cola(self):
  b=self.body();code,r=self.post(b);self.assertEqual(code,200);self.assertTrue(r['recibo_durable'])
  js=self.jsrecibo(r,b);self.assertTrue(js['valido']);self.assertFalse(js['confirmacion_remota']);self.assertIsNone(js['aceptacion_entregable'])
  again=self.post(b)[1];self.assertEqual(again['recibo'],r['recibo']);self.assertEqual(self.counts(),(1,1,1))
  self.assertEqual(self.project()['expected_estado'],'enviar  cliente')
 def test_cola_falla_replay_recupera_desde_sqlite_misma_accion(self):
  b=self.body();self.queue_failure=True;r=self.post(b)[1];self.assertFalse(r['recibo_durable']);self.assertEqual(r['cola_estado'],'pendiente_recuperacion')
  self.assertFalse(self.jsrecibo(r,b)['valido']);self.assertEqual(self.counts(),(1,1,0));self.assertTrue(self.project()['bloqueada'])
  self.queue_failure=False;r=self.post(b)[1];self.assertTrue(self.jsrecibo(r,b)['valido']);self.assertEqual(self.counts(),(1,1,1))
 def test_dos_intenciones_revision_vieja_no_segunda_accion(self):
  b=self.body();self.post(b);other=copy.deepcopy(b);other['intencion_id']='33333333-3333-4333-8333-333333333333'
  self.assertEqual(self.post(other)[0],409);self.assertEqual(self.counts(),(1,1,1))
 def test_autoria_cambia_entre_lectura_y_escritura_no_inserta(self):
  b=self.body();self.crudo['personas'].append({'id':'other','correo':'other@example.invalid','estado':'activo','puestos':['seo']});self.users.append({'id':'u-other','email':'other@example.invalid'});self.raw['asignados']=[{'id':'u-other'}]
  self.assertEqual(self.post(b)[0],409);self.assertEqual(self.counts(),(0,0,0))
 def test_rol_revocado_entre_lectura_y_escritura_no_inserta(self):
  b=self.body();self.account['puestos']=[];self.assertEqual(self.post(b)[0],403);self.assertEqual(self.counts(),(0,0,0))
 def test_cliente_inactivo_entre_lectura_y_escritura_no_inserta(self):
  b=self.body();self.act=False;self.assertEqual(self.post(b)[0],403);self.assertEqual(self.counts(),(0,0,0))
 def test_mover_estado_tipo_genuino_y_proyeccion_del_destino(self):
  self.row['estado']=self.raw['estado']='diario';b=self.body(self.author,'mover_estado');r=self.post(b,self.author)[1]
  self.assertTrue(self.jsrecibo(r,b,self.author)['valido']);self.assertEqual(r['recibo']['tipo'],'mover_estado');self.assertEqual(self.project()['expected_estado'],'revisión project manager')
 def test_manual_simulado_no_remoto_ni_aceptacion(self):
  b=self.body();self.post(b)
  with self.connect() as c:self.sinc.paso(c,1,'confirmado','hecho_a_mano')
  r=self.post(b)[1];j=self.jsrecibo(r,b)
  self.assertTrue(j['valido']);self.assertFalse(j['confirmacion_remota']);self.assertIsNone(j['aceptacion_entregable']);self.assertTrue(self.project()['bloqueada'])
 def test_autor_inactivo_tras_token_no_inserta(self):
  b=self.body();self.author['estado']='baja';self.assertIn(self.post(b)[0],(403,409));self.assertEqual(self.counts(),(0,0,0))
 def test_replay_revocado_no_evade_autorizacion_actual(self):
  b=self.body();self.post(b);self.permission=False;self.assertEqual(self.post(b)[0],403);self.assertEqual(self.counts(),(1,1,1))
 def test_recibo_alterado_en_camino_rechazado_por_consumidor_real(self):
  b=self.body();r=self.post(b)[1];r['recibo']['tipo']='cambiar_estado';self.assertFalse(self.jsrecibo(r,b)['valido'])
 def test_regla_intercalada_despues_insert_antes_cola_no_falsa_confirmacion(self):
  b=self.body();original=self.ns['_tras_accion']
  def altered(aid):self.p.REGLAS=copy.deepcopy(self.rules);self.p.REGLAS['revision_piezas']['por_estado'][self.row['estado']]['a']='corrección';return original(aid)
  self.ns['_tras_accion']=altered;r=self.post(b)[1]
  self.assertFalse(r['recibo_durable']);self.assertTrue(r['requiere_revision']);self.assertFalse(self.jsrecibo(r,b)['valido']);self.assertEqual(self.counts(),(1,1,1));self.assertTrue(self.project()['bloqueada'])
# No repetir unitarias de 208: sólo la cadena nueva.
for name in B.Pruebas.__dict__:
 if name.startswith('test_') and name not in Cadena217.__dict__:setattr(Cadena217,name,None)
if __name__=='__main__':unittest.main()
