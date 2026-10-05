import ast,copy,json,types,unittest
from contextlib import contextmanager,redirect_stdout
from io import StringIO
import probar_revision_trabajador_574 as D

class Worker575(unittest.TestCase):
 def setUp(self):
  self.f=D.Trabajador574();self.f.setUp();self.backoffs=[]
  self.f.ns['time'].sleep=lambda n:self.backoffs.append(n)
  tree=ast.parse((D.APP/'servir.py').read_text())
  for name in ('_validar_pasos_recarga575','_fallo_recarga575'):
   fn=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name))
   exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'helper_actual575','exec'),self.f.ns)
  self.log=StringIO()
 def tearDown(self):self.f.tearDown()
 def correr(self):
  with redirect_stdout(self.log):r=self.f.correr()
  self.assertEqual(r,['parada_controlada'])
 def datos(self):
  with self.f.con() as c:return [dict(r) for r in c.execute('SELECT * FROM recargas ORDER BY id')]
 def estados(self,primero='con_fallos'):
  self.assertEqual(self.f.estados(),[(1,primero),(2,'ok')])
 def fallo_primera(self,key):
  previo=self.f.ns[key];calls=[]
  def ejecutar(*a,**kw):
   calls.append(True)
   if len(calls)==1:raise RuntimeError('PRIVADO_NO_PUBLICAR')
   return previo(*a,**kw)
  self.f.ns[key]=ejecutar
 def test_control_y_no_baseexception_shutdown(self):
  self.correr();self.estados('ok');self.assertEqual(len(self.f.procesos),2);self.assertFalse(self.backoffs)
 def test_parada_baseexception_en_ejecucion_no_se_convierte_en_fallo(self):
  def parar(*a,**kw):raise D.PararFixture()
  self.f.ns['subprocess'].run=parar
  self.correr();self.assertEqual(self.f.estados(),[(1,'en_curso'),(2,'pendiente')])
  self.assertFalse(self.backoffs);self.assertFalse(self.log.getvalue())
 def test_cfg_corrupta_primera_continua_siguiente(self):
  calls=[];cfg=self.f.cfg
  def read():calls.append(True);return '{' if len(calls)==1 else cfg
  self.f.ns['RECARGA_CFG'].read_text=read
  self.correr();self.estados();self.assertEqual(len(self.f.procesos),1)
  self.assertEqual(json.loads(self.datos()[0]['pasos'])[-1]['salida'],['fase: configuracion','clase: JSONDecodeError'])
 def test_noop_explicito_carga_avisos_y_siguiente_job(self):
  with self.f.con() as c:c.execute("UPDATE recargas SET modo='noop' WHERE id=1")
  self.f.cfg=json.dumps({'noop':[],'ligera':[{'id':'p','cmd':['NO_EJECUTAR']}]})
  self.correr();self.estados('ok');self.assertEqual(len(self.f.procesos),1)
  self.assertEqual(len(self.f.cargas),2);self.assertEqual(len(self.f.avisos),2)
  self.assertEqual(json.loads(self.datos()[0]['pasos'] or '[]'),[])
  self.assertEqual(self.f.ns['_validar_pasos_recarga575']({'noop':[]},'noop'),[])
  for invalido in ({}, {'noop':None}, {'noop':{}}, {'noop':True}):
   with self.assertRaises(ValueError):self.f.ns['_validar_pasos_recarga575'](invalido,'noop')
 def test_missing_step_valida_antes_de_ejecutar(self):
  calls=[];cfg=self.f.cfg
  def read():calls.append(True);return json.dumps({'ligera':[{'cmd':['NO']} ]}) if len(calls)==1 else cfg
  self.f.ns['RECARGA_CFG'].read_text=read;self.correr();self.estados();self.assertEqual(len(self.f.procesos),1)
 def test_modo_ausente_no_ok_por_lista_vacia(self):
  with self.f.con() as c:c.execute("UPDATE recargas SET modo='desconocido' WHERE id=1")
  self.correr();self.estados();self.assertEqual(len(self.f.procesos),1)
 def test_registro_y_error_secundario_no_matan_hilo(self):
  calls=[]
  def registro(*a):
   calls.append(a)
   if a[3]=='1':raise RuntimeError('PRIVADO_NO_PUBLICAR')
  self.f.ns['registrar']=registro;self.correr();self.estados();self.assertEqual(len(self.f.procesos),2)
  self.assertNotIn('PRIVADO_NO_PUBLICAR',self.log.getvalue()+str(self.datos()))
  self.assertEqual(json.loads(self.datos()[0]['pasos'])[0]['ok'],True)
 def test_avisos_y_carga_continuan_sin_re_ejecutar(self):
  self.fallo_primera('calcular_avisos');self.correr();self.estados();self.assertEqual(len(self.f.procesos),2)
 def test_carga_fallida_no_se_marca_ok(self):
  calls=[]
  def cargar():
   calls.append(True)
   if len(calls)==1:raise OSError('PRIVADO_NO_PUBLICAR')
  self.f.ns['E'].cargar=cargar;self.correr();self.estados();self.assertEqual(len(self.f.procesos),2)
 def interceptar_sql(self,pred,numero=1,terminal=False):
  original=self.f.con;fallos=[]
  @contextmanager
  def con():
   with original() as c:
    class Proxy:
     def execute(s,sql,args=()):
      if pred(sql,args) and len(fallos)<numero:
       fallos.append(sql);raise D.sqlite3.OperationalError('PRIVADO_NO_PUBLICAR')
      return c.execute(sql,args)
    yield Proxy()
  self.f.ns['conectar']=con
  return fallos
 def test_consulta_inicial_recupera_pendientes(self):
  self.f.fallo_conexion=True;self.correr();self.estados('ok');self.assertEqual(len(self.f.procesos),2)
  self.assertEqual(self.backoffs,[1])
 def test_claim_fallido_no_ejecuta_antes_de_autoridad(self):
  self.interceptar_sql(lambda sql,args:"SET estado='en_curso'" in sql)
  self.correr();self.estados('ok');self.assertEqual(len(self.f.procesos),2)
 def test_progreso_fallido_preserva_paso_no_retry(self):
  self.interceptar_sql(lambda sql,args:sql.startswith('UPDATE recargas SET pasos='))
  self.correr();self.estados();self.assertEqual(len(self.f.procesos),2)
  pasos=json.loads(self.datos()[0]['pasos']);self.assertTrue(pasos[0]['ok']);self.assertEqual(pasos[-1]['salida'][0],'fase: progreso')
 def test_finalizacion_y_terminalizacion_secundaria_recuperadas(self):
  failed=[];original=self.f.con
  @contextmanager
  def con():
   with original() as c:
    class Proxy:
     def execute(s,sql,args=()):
      if sql.startswith('UPDATE recargas SET estado=?') and not failed:
       failed.append('original');raise D.sqlite3.OperationalError('PRIVADO_NO_PUBLICAR')
      if "SET estado='con_fallos'" in sql and failed==['original']:
       failed.append('secundario');raise D.sqlite3.OperationalError('PRIVADO_NO_PUBLICAR')
      return c.execute(sql,args)
    yield Proxy()
  self.f.ns['conectar']=con;self.correr();self.estados();self.assertEqual(len(self.f.procesos),2)
  self.assertEqual(failed,['original','secundario']);self.assertNotIn('PRIVADO_NO_PUBLICAR',self.log.getvalue()+str(self.datos()))
 def test_senal_durante_clear_no_pierde_trabajo_persistido(self):
  def clear():
   self.f.cola.limpiezas+=1
   with self.f.con() as c:c.execute("INSERT INTO recargas(id,quien,modo,estado) VALUES(3,'fixture','ligera','pendiente')")
  self.f.cola.clear=clear;self.correr()
  self.assertEqual(self.f.estados(),[(1,'ok'),(2,'ok'),(3,'ok')]);self.assertEqual(len(self.f.procesos),3)
 def test_timeouts_limites_malformed_no_ejecucion(self):
  check=self.f.ns['_validar_pasos_recarga575']
  for value in (None,True,0,-1,float('nan'),float('inf'),'300'):
   with self.assertRaises(ValueError):check({'m':[{'id':'p','cmd':['NO'],'timeout':value}]},'m')
  self.assertEqual(check({'m':[{'id':'p','cmd':['NO'],'timeout':10800}]},'m')[0]['timeout'],10800)
 def test_error_subprocess_generico_sin_privados(self):
  calls=[]
  def run(*a,**kw):
   calls.append(True)
   if len(calls)==1:raise OSError('PRIVADO_NO_PUBLICAR')
   return types.SimpleNamespace(returncode=0,stdout='',stderr='')
  self.f.ns['subprocess'].run=run;self.correr();self.estados();self.assertEqual(len(calls),2)
  self.assertNotIn('PRIVADO_NO_PUBLICAR',self.log.getvalue()+str(self.datos()))
if __name__=='__main__':unittest.main()
