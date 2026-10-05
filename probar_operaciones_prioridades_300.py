import copy,os,sqlite3,tempfile,types,unittest
from pathlib import Path
from contextlib import nullcontext
from uuid import uuid4
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import operaciones_prioridades_300 as M
class Prioridades(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'db'
  self.raw={'personas':[{'id':'ops','estado':'activo','puestos':['operaciones']},{'id':'otro','estado':'activo','puestos':['direccion']}],'clientes':[{'id':'c'}]}
  self.rows=[{'id':'exacta','cliente_id':'c','titulo':'Comprobar respuesta','detalle':'Acción concreta'}];self.active=True
  self.S=types.SimpleNamespace(E=types.SimpleNamespace(crudo=self.raw,nucleo_bloqueado=False),P=types.SimpleNamespace(hoy_iso=lambda:'2026-10-03',contexto=lambda p,c:{},mirando_como=lambda *a:nullcontext(),ver=lambda *a:{'ok':True}),ACT=types.SimpleNamespace(es_activo_id=lambda c:self.active),ve_alguno=lambda *a:True,modulo_recortado=lambda *a:{'alertas':copy.deepcopy(self.rows)},DB=self.path)
  self.env=patch.dict(os.environ,{'RO_PILOTO_LECTURA':'no'});self.env.start();self.addCleanup(self.env.stop)
 def con(self):
  c=sqlite3.connect(self.path,timeout=10);c.row_factory=sqlite3.Row;return c
 def b(self,**kw):return {'prioridad_id':'exacta','fuente_revision':M.referencias(self.S,'ops','ops')['exacta']['fuente_revision'],'dia':'2026-10-03','revision':0,'estado':'empujado','nota':'Contacto declarado','intencion_id':str(uuid4()),**kw}
 def save(self,b,r='ops',v='ops'):
  with self.con() as c:return M.guardar(self.S,c,r,v,b)
 def read(self,actor='ops'):
  with self.con() as c:return M.leer(self.S,c,actor,actor)
 def test_durable_restart_declaracion_no_ejecucion(self):
  b=self.b();x=self.save(b);self.assertTrue(x['recibo_durable']);self.assertFalse(x['recibo']['ejecucion_verificada']);self.assertFalse(x['recibo']['envio_realizado']);self.assertEqual(self.read()['prioridades'][0]['actual'],x['recibo'])
 def test_replay_cas_uuid(self):
  b=self.b();a=self.save(b);self.assertEqual(self.save(b)['recibo'],a['recibo'])
  for q in (self.b(),{**b,'nota':'Distinta'}):
   with self.assertRaises(M.ErrorPrioridad) as e:self.save(q)
   self.assertEqual(e.exception.codigo,409)
  with self.con() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM operaciones_prioridades_300').fetchone()[0],1)
 def test_concurrent_claim(self):
  bs=[self.b(),self.b()]
  def f(b):
   try:return self.save(b)['resultado']
   except M.ErrorPrioridad as e:return e.codigo
  with ThreadPoolExecutor(2) as ex:r=list(ex.map(f,bs))
  self.assertEqual(sorted(map(str,r)),['409','guardado'])
 def test_owner_isolated(self):
  self.save(self.b());self.assertIsNone(self.read('otro')['prioridades'][0]['actual'])
 def test_scope_revoked_and_duplicate_identity(self):
  b=self.b();self.active=False
  with self.assertRaises(M.ErrorPrioridad):self.save(b)
  self.assertEqual(M.leer(self.S,None,'ops','ops')['prioridades'],[])
  self.active=True;self.raw['personas'].append(copy.deepcopy(self.raw['personas'][0]))
  with self.assertRaises(M.ErrorPrioridad):self.save(b)
 def test_pilot_viewas_roles(self):
  b=self.b()
  with self.assertRaises(M.ErrorPrioridad):self.save(b,'ops','otro')
  with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'si'}):
   with self.assertRaises(M.ErrorPrioridad):self.save(b)
   self.assertFalse(M.leer(self.S,None,'ops','ops')['puede_registrar'])
  self.raw['personas'][0]['puestos']=['account']
  with self.assertRaises(M.ErrorPrioridad):self.save(b)
 def test_source_changes_and_duplicate_ids(self):
  b=self.b();self.rows[0]['detalle']='Acción diferente'
  with self.assertRaises(M.ErrorPrioridad) as e:self.save(b)
  self.assertEqual(e.exception.codigo,409)
  self.rows.append(copy.deepcopy(self.rows[0]));self.assertEqual(M.referencias(self.S,'ops','ops'),{})
 def test_revocation_before_commit_rolls_back(self):
  b=self.b();original=M.resolver;n=[0]
  def wrapped(*a,**k):
   n[0]+=1
   if n[0]==3:self.active=False
   return original(*a,**k)
  with patch.object(M,'resolver',wrapped):
   with self.assertRaises(M.ErrorPrioridad):self.save(b)
  with self.con() as c:self.assertFalse(M.tabla_existe(c))
 def test_note_required_period_current_and_extra_reject(self):
  for b in (self.b(estado='resuelto',nota=''),self.b(dia='2026-10-04'),{**self.b(),'cliente_id':'forged'}):
   with self.assertRaises(M.ErrorPrioridad):self.save(b)
 def test_replay_yesterday_no_current_progress(self):
  b=self.b();self.save(b);self.S.P.hoy_iso=lambda:'2026-10-04';self.assertEqual(self.save(b)['resultado'],'duplicado');self.assertIsNone(self.read()['prioridades'][0]['actual'])
 def test_no_foreign_transaction_commit_append_only(self):
  self.save(self.b());c=self.con()
  try:
   with self.assertRaises(sqlite3.IntegrityError):c.execute('DELETE FROM operaciones_prioridades_300')
   c.rollback();c.execute('CREATE TABLE other(x)');c.execute('INSERT INTO other VALUES(1)')
   with self.assertRaises(M.ErrorPrioridad):M.guardar(self.S,c,'ops','ops',self.b(revision=1))
   self.assertTrue(c.in_transaction);c.rollback();self.assertEqual(c.execute('SELECT COUNT(*) FROM other').fetchone()[0],0)
  finally:c.close()
 def test_read_no_creation(self):
  d=M.leer(self.S,None,'ops','ops');self.assertFalse(self.path.exists());self.assertEqual(d['prioridades'][0]['revision'],0)
 def test_real_policy_ops_vs_account(self):
  import permisos as P
  self.S.P=types.SimpleNamespace(contexto=P.contexto,ver=P.ver,mirando_como=P.mirando_como,hoy_iso=lambda:'2026-10-03')
  self.raw['clientes'][0]['activo_confirmado']=True
  self.raw['asignaciones']=[]
  self.assertTrue(self.save(self.b())['recibo_durable'])
  self.raw['personas'][0]['puestos']=['account']
  with self.assertRaises(M.ErrorPrioridad):M.leer(self.S,None,'ops','ops')
 def test_hook_read_no_database_created_and_query_rejected(self):
  class H:
   def _api_get(self,*a):return 'fallback'
   def api_post(self,*a):return 'fallback'
   def responder(self,code,doc):return code,doc
  M.enganchar(H,self.S);h=H();p={'id':'ops'}
  code,d=h._api_get(M.RUTA,{},p,p);self.assertEqual(code,200);self.assertFalse(self.path.exists())
  self.assertEqual(h._api_get(M.RUTA,{'yo':['otro']},p,p)[0],400)
  self.assertEqual(h._api_get('/other',{},p,p),'fallback')
if __name__=='__main__':unittest.main()
