"""681 integrado + permisos/ACT/ve_alguno reales, sólo catálogo ficticio."""
import ast,copy,os,re,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
APP=Path(os.environ.get('RO_APP_689',str(HERE if (HERE/'servir.py').is_file() else HERE.parent/'30_APP_PROTOTIPO'))).resolve()
sys.path.insert(0,str(APP))
import permisos as P
from fuentes_verdad import clientes_activos as ACT
from controlador_planning_681 import conectar_produccion681,enriquecer681
from planning_transiciones_681 import KEY
import probar_planning_681 as F
indice=(APP/'modulos/indice.js').read_text()
block=indice[indice.index("{ id: 'produccion',"):];line=block[block.index('puestos_que_lo_ven: {')+len('puestos_que_lo_ven: '):].split('\n',1)[0].rstrip().rstrip(',')
MOD=ast.literal_eval(re.sub(r'(?<![\w\"\'])\b([a-z_]+):',r"'\1':",line.replace('null','None')))
tree=ast.parse((APP/'servir.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='ve_alguno')
class Server:
 def __init__(self,real='opsFixture',view=None):
  self.P=P;self.ACT=ACT
  self.E=types.SimpleNamespace(nucleo_bloqueado=False,modulos={'produccion':MOD},crudo={'personas':[{'id':'opsFixture','estado':'activo','puestos':['operaciones']},{'id':'accountFixture','estado':'activo','puestos':['account']},{'id':'otherAccount','estado':'activo','puestos':['account']},{'id':'workerFixture','estado':'activo','puestos':['produccion']},{'id':'hrFixture','estado':'activo','puestos':['rrhh']}],'clientes':[{'id':'ownFixture','estado':'activo','activo_confirmado':True},{'id':'otherFixture','estado':'activo','activo_confirmado':True}],'asignaciones':[{'persona_id':'accountFixture','cliente_id':'ownFixture','silla':'account','desde':'2026-01-01','principal':True}]})
  self.real=copy.deepcopy(next(p for p in self.E.crudo['personas'] if p['id']==real));self.view=copy.deepcopy(next(p for p in self.E.crudo['personas'] if p['id']==(view or real)))
  ns={'P':P,'E':self.E};exec(compile(ast.Module(body=[node],type_ignores=[]),'realVeAlguno689','exec'),ns);self.ve_alguno=ns['ve_alguno']
def dto(cid='ownFixture',pid='accountFixture'):return {'proyectos':[{'cliente_id':cid,'no_planificadas':99}],'personas':[{'persona_id':pid,'creadas':7}]}
def payload(cid='ownFixture',pid='accountFixture'):
 p=F.payload();p['registro']['tareas'][0].update(cliente_id=cid,creador_id=pid);p['registro']['eventos'][0].update(cliente_id=cid,actor_id=pid);return p
class Scope689(unittest.TestCase):
 def setUp(self):
  self.active={'ownFixture','otherFixture'}
  state={'_activos':self.active,'_ids':set(),'_no_operativos':set(),'_rx':re.compile(r'(?!)'),'_compactos':[],'_exactos':set(),'_nombres_no_operativos':set()}
  pt=patch.object(ACT,'estado',return_value=state);pt.start();self.addCleanup(pt.stop)
  pt=patch.dict(os.environ,{'RO_RELOJ':'2026-10-04T12:00'},clear=False);pt.start();self.addCleanup(pt.stop)
 def run_call(self,s,d=None,reader=None,enabled=True):
  d=d or dto();calls=[]
  def read():calls.append(1);return (reader or (lambda:payload(d['proyectos'][0]['cliente_id'],d['personas'][0]['persona_id'])))()
  with P.mirando_como(s.real,s.E.crudo):value=conectar_produccion681(d,s,s.real,s.view,read,F.NOW,enabled)
  return value,calls
 def test_ops_ambos_clientes_horas_ajenas(self):
  for cid in self.active:
   value,calls=self.run_call(Server(),dto(cid,'workerFixture'));self.assertEqual(calls,[1]);self.assertEqual(value['personas'][0][KEY]['metricas']['al_planning'],1)
 def test_account_propio_no_ajeno(self):
  value,calls=self.run_call(Server('accountFixture'));self.assertEqual(calls,[1]);self.assertEqual(value['personas'][0][KEY]['metricas']['al_planning'],1)
  for d in (dto('otherFixture'),dto('ownFixture','workerFixture')):
   value,calls=self.run_call(Server('accountFixture'),d);self.assertIsNone(value);self.assertEqual(calls,[])
 def test_ops_ver_account_interseccion(self):
  value,calls=self.run_call(Server('opsFixture','accountFixture'));self.assertEqual(calls,[1]);self.assertEqual(value['personas'][0][KEY]['metricas']['al_planning'],1)
  value,calls=self.run_call(Server('opsFixture','accountFixture'),dto('otherFixture'));self.assertIsNone(value);self.assertEqual(calls,[])
 def test_account_ver_ops_sin_grant_no_io(self):
  value,calls=self.run_call(Server('accountFixture','opsFixture'));self.assertIsNone(value);self.assertEqual(calls,[])
 def test_otros_accounts_sin_cartera_no_io(self):
  value,calls=self.run_call(Server('otherAccount'));self.assertIsNone(value);self.assertEqual(calls,[])
 def test_resumen_no_historial_con_puerta_real(self):
  s=Server('hrFixture');self.assertEqual(s.ve_alguno(s.real,['produccion']),'resumen')
  value,calls=self.run_call(s);self.assertIsNone(value);self.assertEqual(calls,[])
  import lector_planning_681 as L
  with patch.dict(os.environ,{'RO_PLANNING_TRANSICIONES_681':'/synthetic','RO_SHA_PLANNING_TRANSICIONES_681':'a'*64}),patch.object(L,'leer_planning681',side_effect=AssertionError('IO no autorizado')):
   self.assertEqual(enriquecer681(dto(),s,s.real,s.view),dto())
 def test_revoca_cartera_entre_lecturas(self):
  s=Server('accountFixture')
  def read():s.E.crudo['asignaciones'].clear();return payload()
  value,calls=self.run_call(s,reader=read);self.assertIsNone(value);self.assertEqual(calls,[1])
 def test_revoca_ACT_entre_lecturas(self):
  s=Server()
  def read():self.active.remove('ownFixture');return payload()
  value,calls=self.run_call(s,reader=read);self.assertIsNone(value);self.assertEqual(calls,[1])
 def test_revoca_horas_jefatura_entre_lecturas(self):
  s=Server('accountFixture');worker=next(p for p in s.E.crudo['personas'] if p['id']=='workerFixture');worker['jefe']='accountFixture'
  def read():worker.pop('jefe');return payload(pid='workerFixture')
  value,calls=self.run_call(s,dto(pid='workerFixture'),read);self.assertIsNone(value);self.assertEqual(calls,[1])
 def test_duplicados_actor_y_cliente_antes_io(self):
  for key in ('personas','clientes'):
   s=Server();s.E.crudo[key].append(copy.deepcopy(s.E.crudo[key][0]));value,calls=self.run_call(s);self.assertIsNone(value);self.assertEqual(calls,[])
 def test_baja_actor_no_io(self):
  s=Server();s.E.crudo['personas'][0]['estado']='baja';value,calls=self.run_call(s);self.assertIsNone(value);self.assertEqual(calls,[])
 def test_revoca_regla_horas_durante_lectura(self):
  s=Server();rules=copy.deepcopy(P.REGLAS)
  def read():rules['tipos']['horas_persona']={'si':[],'no':'Denied fixture'};return payload()
  with patch.object(P,'REGLAS',rules):
   value,calls=self.run_call(s,reader=read);self.assertIsNone(value);self.assertEqual(calls,[1])
 def test_revoca_modulo_real_durante_lectura(self):
  s=Server()
  def read():s.E.modulos['produccion']={'operaciones':None};return payload()
  value,calls=self.run_call(s,reader=read);self.assertIsNone(value);self.assertEqual(calls,[1])
 def test_optin_off_no_io_con_permiso_real(self):
  value,calls=self.run_call(Server('accountFixture'),enabled=False);self.assertEqual(value,dto());self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
