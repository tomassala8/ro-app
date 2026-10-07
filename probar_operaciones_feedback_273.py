import copy
import os
import sqlite3
import tempfile
import types
import unittest
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import permisos as P
import operaciones_feedback_273 as F

def persona(pid,rol):return {'id':pid,'estado':'activo','puestos':[rol]}
def body(**kw):return {'cliente_id':'c','semana':'2026-09-28','estado':'pedida','nota':'Solicitud declarada','revision':0,'intencion_id':str(uuid4()),**kw}

class Feedback(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'local.db'
  self.raw={'personas':[persona('a','account'),persona('b','account'),persona('ops','operaciones'),persona('tomas','direccion')], 'clientes':[{'id':'c','estado':'activo','activo_confirmado':True},{'id':'otro','estado':'activo','activo_confirmado':True}], 'asignaciones':[{'persona_id':'a','cliente_id':'c','silla':'account','principal':True,'confianza':'confirmada'},{'persona_id':'b','cliente_id':'otro','silla':'account','principal':True,'confianza':'confirmada'}]}
  self.S=types.SimpleNamespace(E=types.SimpleNamespace(crudo=self.raw,nucleo_bloqueado=False),P=types.SimpleNamespace(ver=P.ver,contexto=P.contexto,hoy_iso=lambda:'2026-10-03'),ACT=types.SimpleNamespace(es_activo_id=lambda cid: any(c['id']==cid and c.get('activo_confirmado') is True for c in self.S.E.crudo['clientes'])),ve_alguno=lambda p,mods:True,DB=self.path,conectar=self.con)
  self.env=patch.dict(os.environ,{'RO_PILOTO_LECTURA':'no','DATABASE_URL':'','PGDATABASE_URL':''});self.env.start();self.addCleanup(self.env.stop)
 def con(self):
  c=sqlite3.connect(self.path,timeout=10);c.row_factory=sqlite3.Row;return c
 def guardar(self,b,r='a',v=None):
  con=self.con()
  try:return F.guardar(self.S,con,r,v or r,b)
  finally:con.close()
 def leer(self,r='a',v=None):
  con=self.con()
  try:return F.leer(self.S,con,r,v or r,'c')
  finally:con.close()
 def test_pedido_no_conseguido_y_reinicio(self):
  b=body();p=self.guardar(b);self.assertEqual(p['recibo']['estado'],'pedida');self.assertFalse(p['recibo']['envio_realizado'])
  r=self.guardar(body(estado='conseguida',revision=1,nota='El cliente dijo que son pertinentes'))
  self.assertFalse(r['recibo']['respuesta_verificada']);d=self.leer();self.assertEqual(d['actual']['estado'],'conseguida');self.assertEqual(d['revision'],2);self.assertEqual(len(d['historial']),2)
 def test_idempotencia_cas_y_uuid_actor_payload(self):
  b=body();a=self.guardar(b);z=self.guardar(b);self.assertEqual(a['recibo'],z['recibo']);self.assertEqual(z['resultado'],'duplicado')
  for otro,r in [({**b,'nota':'Cambio'},'a'),(b,'ops'),(body(),'a')]:
   with self.assertRaises(F.ErrorFeedback) as e:self.guardar(otro,r)
   self.assertEqual(e.exception.codigo,409)
  with self.con() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM operaciones_feedback_273').fetchone()[0],1)
 def test_two_connections_same_revision_one_commit(self):
  bs=[body(estado='pedida'),body(estado='conseguida')]
  def call(b):
   try:return self.guardar(b)['resultado']
   except F.ErrorFeedback as e:return e.codigo
  with ThreadPoolExecutor(2)as ex:results=list(ex.map(call,bs))
  self.assertEqual(sorted(map(str,results)),['409','guardado']);self.assertEqual(self.leer()['revision'],1)
 def test_replay_pasada_semana_y_nueva_denegada(self):
  b=body();uno=self.guardar(b);self.S.P.hoy_iso=lambda:'2026-10-12'
  self.assertEqual(self.guardar(b)['recibo'],uno['recibo']);self.assertIsNone(self.leer()['actual'])
  with self.assertRaises(F.ErrorFeedback)as e:self.guardar(body())
  self.assertEqual(e.exception.codigo,400)
 def test_append_only_no_commit_ajeno(self):
  self.guardar(body());c=self.con()
  try:
   for sql in ['DELETE FROM operaciones_feedback_273','UPDATE operaciones_feedback_273 SET estado="conseguida"']:
    with self.assertRaises(sqlite3.IntegrityError):c.execute(sql)
    c.rollback()
   c.execute('CREATE TABLE ajena(x)');c.execute('INSERT INTO ajena VALUES(1)')
   with self.assertRaises(F.ErrorFeedback):F.guardar(self.S,c,'a','a',body(revision=1))
   self.assertTrue(c.in_transaction);c.rollback();self.assertEqual(c.execute('SELECT COUNT(*) FROM ajena').fetchone()[0],0)
  finally:c.close()
 def test_scope_cartera_modulo_vercomo_piloto_act(self):
  with self.assertRaises(F.ErrorFeedback):self.guardar(body(),'b')
  with self.assertRaises(F.ErrorFeedback):self.guardar(body(),'ops','a')
  with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'si'}):
   with self.assertRaises(F.ErrorFeedback):self.guardar(body())
  self.guardar(body(),'ops');self.assertEqual(self.leer('ops','a')['actual']['autor'],'ops')
  self.S.E.crudo['clientes'][0]['activo_confirmado']=False
  with self.assertRaises(F.ErrorFeedback):self.leer('ops')
 def test_identidad_duplicada_inactiva_y_contrato_revocado(self):
  for ps in [[persona('a','account'),persona('a','account')],[{**persona('a','account'),'activo':False}],[{**persona('a','account'),'estado':'baja'}]]:
   self.S.E.crudo={**self.raw,'personas':ps}
   with self.assertRaises(F.ErrorFeedback):self.guardar(body())
  self.S.E.crudo=self.raw;self.S.ve_alguno=lambda*a:False
  with self.assertRaises(F.ErrorFeedback):self.guardar(body())
 def test_revocacion_antes_commit_rollback(self):
  count=0
  def gate(p,mods):
   nonlocal count
   count+=1
   return count<5
  self.S.ve_alguno=gate
  with self.assertRaises(F.ErrorFeedback):self.guardar(body())
  with self.con()as c:self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='operaciones_feedback_273'").fetchone())
 def test_payload_typo_semana_autor_invalidos(self):
  for kw in [{'estado':'recibida_api'},{'semana':'2026-10-03'},{'semana':'2026-10-05'},{'semana':'2026-02-30'},{'revision':True},{'autor':'ops'},{'registrado_en':'2026-10-03'},{'intencion_id':'x'},{'nota':'x'*301}]:
   with self.assertRaises(F.ErrorFeedback):self.guardar(body(**kw))
 def test_nota_saneada_recibo_no_secreto_precio_contacto(self):
  d=self.guardar(body(nota='Email fixture@example.test; cuota 200 euros; password=contraseñafalsa123'))
  nota=d['recibo']['nota'];self.assertNotIn('fixture@example.test',nota);self.assertNotIn('200',nota);self.assertNotIn('contraseñafalsa123',nota)
 def test_coherencia_storage(self):
  self.guardar(body());c=self.con()
  try:
   c.execute('DROP TRIGGER feedback273_sin_update');c.execute("UPDATE operaciones_feedback_273 SET estado='conseguida'");c.commit()
  finally:c.close()
  with self.assertRaises(F.ErrorFeedback)as e:self.leer()
  self.assertEqual(e.exception.codigo,503)
 def test_hook_get_lazy_readonly_y_post_recibo(self):
  class H:
   def _api_get(self,*a):return 'original_get'
   def api_post(self,*a):return 'original_post'
   def responder(self,code,d):return code,d
  F.enganchar(H,self.S);h=H();p=self.raw['personas'][0]
  self.assertEqual(h._api_get('/otra',{},p,p),'original_get');self.assertFalse(self.path.exists())
  code,d=h._api_get(F.RUTA,{'cliente_id':['c']},p,p);self.assertEqual(code,200);self.assertEqual(d['revision'],0);self.assertFalse(self.path.exists())
  self.assertEqual(h._api_get(F.RUTA,{'cliente_id':['c'],'yo':['ops']},p,p)[0],400)
  code,d=h.api_post(F.RUTA,p,p,body());self.assertEqual(code,200)
  with self.con()as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM operaciones_feedback_273').fetchone()[0],1)
  code,d=h._api_get(F.RUTA,{'cliente_id':['c']},p,p);self.assertEqual(code,200);self.assertEqual(d['revision'],1)
 def test_post_storage_failure_not_success(self):
  class H:
   def _api_get(self,*a):pass
   def api_post(self,*a):pass
   def responder(self,code,d):return code,d
  def fallo():raise sqlite3.OperationalError('fixture')
  self.S.conectar=fallo;F.enganchar(H,self.S);p=self.raw['personas'][0]
  self.assertEqual(H().api_post(F.RUTA,p,p,body())[0],503)
 def test_clientes_duplicados_e_inexistentes_no_historia(self):
  self.guardar(body());self.S.E.crudo['clientes'].append(copy.deepcopy(self.raw['clientes'][0]))
  with self.assertRaises(F.ErrorFeedback)as e:self.leer()
  self.assertEqual(e.exception.codigo,404)
if __name__=='__main__':unittest.main()
