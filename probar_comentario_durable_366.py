"""366: ledger194 real, únicamente SQLite efímero. Sin servidor/proveedor."""
import concurrent.futures,json,sqlite3,tempfile,unittest
from pathlib import Path
from intenciones_acciones import iniciar,guardar,ConflictoIntencion
UUID='11111111-1111-4111-8111-111111111111'
BODY={'modulo':'mi-trabajo','herramienta':'clickup','tipo':'comentario','objeto':'task-fixture','cliente_id':'client-fixture','texto':'Nota operativa fixture','vista_previa':{},'intencion_id':UUID}
class Comentarios(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'ledger.sqlite'
  with self.con() as c:c.execute('CREATE TABLE acciones(id INTEGER PRIMARY KEY, cuerpo TEXT)')
 def con(self):return sqlite3.connect(self.path,timeout=5)
 def put(self,body=None,fail=False):
  with self.con() as c:
   iniciar(c)
   def insert(con):
    aid=con.execute('INSERT INTO acciones(cuerpo) VALUES(?)',(json.dumps(body or BODY),)).lastrowid
    if fail:raise RuntimeError('fixture interruption')
    return aid
   return guardar(c,'actor-fixture',body or BODY,insert)
 def test_commit_response_lost_retry_after_restart_same_action(self):
  aid,rep=self.put();self.assertFalse(rep)
  # La respuesta se pierde después del commit; una nueva conexión conserva el vínculo.
  self.assertEqual(self.put(),(aid,True))
  with self.con() as c:self.assertEqual(c.execute('SELECT count(*) FROM acciones').fetchone()[0],1)
 def test_same_uuid_changed_text_task_scope_denied(self):
  self.put()
  for field,value in [('texto','Otro comentario'),('objeto','otro-task'),('cliente_id','otro-client')]:
   with self.assertRaises(ConflictoIntencion):self.put({**BODY,field:value})
  with self.con() as c:self.assertEqual(c.execute('SELECT count(*) FROM acciones').fetchone()[0],1)
 def test_concurrent_same_intent_single_row(self):
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:self.put(),range(8)))
  self.assertEqual(sum(not r for _,r in results),1);self.assertEqual(len({a for a,_ in results}),1)
 def test_failure_rolls_back_before_receipt(self):
  with self.assertRaises(RuntimeError):self.put(fail=True)
  with self.con() as c:self.assertEqual(c.execute('SELECT count(*) FROM acciones').fetchone()[0],0)
  self.assertEqual(self.put(),(1,False))
if __name__=='__main__':unittest.main()
