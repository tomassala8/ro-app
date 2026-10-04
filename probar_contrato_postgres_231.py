"""Contrato del adaptador existente, sin driver/conexión PostgreSQL ni servidor."""
import unittest,types,sqlite3
from unittest.mock import patch
from despliegue import base as B
import intenciones_acciones as I
import transiciones_mi_trabajo as T

class Cursor:
 def __init__(self,con):self.con=con;self.description=None
 def execute(self,*a):self.con.sql.append(a)
 def fetchone(self):return None
class Driver:
 def __init__(self):self.sql=[];self.commits=0;self.rollbacks=0;self.closes=0
 def cursor(self):return Cursor(self)
 def commit(self):self.commits+=1
 def rollback(self):self.rollbacks+=1
 def close(self):self.closes+=1

class Contrato(unittest.TestCase):
 def setUp(self):self.driver=Driver();self.con=B.ConexionPG.__new__(B.ConexionPG);self.con._con=self.driver
 def test_ledger_rejects_pg_before_sql_or_callback(self):
  with self.assertRaises(I.PersistenciaNoDisponible):I.iniciar(self.con)
  self.assertEqual(self.driver.sql,[]);self.assertFalse(hasattr(self.con,'in_transaction'))
 def test_capability_does_not_promise_atomic_pg(self):
  with patch.dict('os.environ',{'DATABASE_URL':'postgresql://synthetic.invalid/fixture','RO_PILOTO_LECTURA':'no'}):
   out=T.capacidad(self.con,{'id':'p'},{'id':'p'})
  self.assertFalse(out['activo']);self.assertEqual(out['motivo'],'base_no_validada')
 def test_begin_immediate_is_not_pg_translation(self):
  self.assertEqual(B.traducir('BEGIN IMMEDIATE')[0],'BEGIN IMMEDIATE')
 def test_current_executescript_commits_so_not_atomic_helper(self):
  self.con.executescript('CREATE TABLE IF NOT EXISTS fixture (id INTEGER);')
  self.assertEqual(self.driver.commits,1)
 def test_sinc_and_new_tables_do_not_have_automatic_returning(self):
  for table in ('sinc_cambios','sinc_pasos','kpi_evidencias'):
   self.assertNotIn(' RETURNING ',B.traducir('INSERT INTO '+table+'(quien) VALUES (?)')[0])
 def test_callback_and_intention_rollback_proven_sqlite_only(self):
  con=sqlite3.connect(':memory:');self.addCleanup(con.close);con.execute('CREATE TABLE acciones(id INTEGER PRIMARY KEY, texto TEXT)');I.iniciar(con)
  def fail(c):c.execute("INSERT INTO acciones VALUES (1,'fixture')");raise I.RechazoAccion(409,'Conflicto fixture')
  with self.assertRaises(I.RechazoAccion):I.guardar(con,'actor',{'intencion_id':'cb361d6f-34c3-48d2-888a-6361da330e48'},fail)
  con.rollback();self.assertEqual(con.execute('SELECT count(*) FROM acciones').fetchone()[0],0)
 def test_adapter_context_manager_rolls_back_exception(self):
  with self.assertRaises(ValueError):
   with self.con:raise ValueError('fixture')
  self.assertEqual(self.driver.rollbacks,1);self.assertEqual(self.driver.commits,0);self.assertEqual(self.driver.closes,1)

if __name__=='__main__':unittest.main()
