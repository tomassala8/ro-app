import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import decisiones_durables_382 as M
UUID='00000000-0000-4000-8000-000000000001';UUID2='00000000-0000-4000-8000-000000000002'
DDL="""CREATE TABLE decisiones (id INTEGER PRIMARY KEY,quien TEXT,tipo TEXT,clave TEXT,titulo TEXT,problema TEXT,recomendacion TEXT,cliente_id TEXT,datos TEXT,creada TEXT DEFAULT (datetime('now')),respuesta TEXT,respondida TEXT,respondida_por TEXT,anula_a INTEGER);"""
def fake():
 ps=[{'id':'tomas','estado':'activo','activo':True,'puestos':['direccion']},{'id':'autor','estado':'activo','puestos':['seo']},{'id':'coti','estado':'activo','puestos':['proyectos']}]
 s=NS(E=NS(nucleo_bloqueado=False,crudo={'personas':ps,'clientes':[{'id':'ok','activo':True}]}),ACT=NS(es_activo_id=lambda _:True),P=NS(contexto=lambda p,d:{},ver=lambda p,x,c:{'ok':True}),ve_alguno=lambda *a:'suyo',puede_contestar=lambda p,t:'direccion' in p['puestos'] or (t=='para_coti' and 'proyectos' in p['puestos']))
 return s
class Pruebas382(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.con=sqlite3.connect(Path(self.temp.name)/'test.sqlite3');self.con.row_factory=sqlite3.Row;self.con.executescript(DDL);self.S=fake();self.piloto=patch.object(M.piloto_lectura,'activo',return_value=False);self.piloto.start()
 def tearDown(self):self.piloto.stop();self.con.close();self.temp.cleanup()
 def nueva(self,key=UUID,cid='ok'):
  return {'operacion':'nueva','intencion_id':key,'tipo':'para_tomas','cliente_id':cid,'titulo':'Decidir revisión','problema':'Falta una decisión operativa','recomendacion':'Revisar el alcance mañana'}
 def save(self,b,r='tomas',v=None):return M.guardar(self.S,self.con,r,v or r,b)
 def answer(self,key=UUID2):
  r=self.save(self.nueva())['recibo'];return {'operacion':'responder','intencion_id':key,'id':r['id'],'revision':r['revision'],'decision':'Aprobar la recomendación','motivo':None,'delegada_en':None}
 def count(self):return self.con.execute('SELECT count(*) FROM decisiones').fetchone()[0]
 def test_nueva_replay_durable(self):
  a=self.save(self.nueva());b=self.save(self.nueva());self.assertEqual(self.count(),1);self.assertEqual(a['recibo'],b['recibo']);self.assertEqual(b['resultado'],'duplicado');self.assertFalse(a['recibo']['envio_realizado'])
 def test_collision_no_overwrite(self):
  self.save(self.nueva());b=self.nueva();b['titulo']='Otro texto'
  with self.assertRaises(M.ErrorDecision) as x:self.save(b)
  self.assertEqual(x.exception.codigo,409);self.assertEqual(self.count(),1)
 def test_respuesta_replay_y_revision(self):
  b=self.answer();a=self.save(b);dup=self.save(b);self.assertEqual(a['recibo'],dup['recibo']);self.assertEqual(dup['resultado'],'duplicado');self.assertNotEqual(a['recibo']['revision'],b['revision'])
 def test_otraintencion_trasrespuesta409(self):
  b=self.answer();self.save(b);b={**b,'intencion_id':'00000000-0000-4000-8000-000000000003'}
  with self.assertRaises(M.ErrorDecision) as x:self.save(b)
  self.assertEqual(x.exception.codigo,409)
 def test_CAS_cambio_legacy(self):
  b=self.answer();self.con.execute("UPDATE decisiones SET recomendacion='Cambio legado' WHERE id=1");self.con.commit()
  with self.assertRaises(M.ErrorDecision) as x:self.save(b)
  self.assertEqual(x.exception.codigo,409);self.assertIsNone(self.con.execute('SELECT respondida FROM decisiones').fetchone()[0])
 def test_destinatario_policy_sin_ampliar(self):
  b=self.answer()
  for actor in ('autor','coti'):
   with self.assertRaises(M.ErrorDecision):self.save(b,actor)
 def test_grant_ACT_view_piloto(self):
  for mode in ('ACT','grant','view','piloto'):
   with self.subTest(mode=mode):
    self.S=fake()
    with patch.object(M.piloto_lectura,'activo',return_value=mode=='piloto'):
     if mode=='ACT':self.S.ACT.es_activo_id=lambda _:False
     if mode=='grant':self.S.P.ver=lambda *a:{'ok':False}
     with self.assertRaises(M.ErrorDecision):self.save(self.nueva(),v='autor' if mode=='view' else None)
 def test_persona_duplicate_inactivo(self):
  for mode in ('duplicate','baja','activo_false'):
   self.S=fake()
   if mode=='duplicate':self.S.E.crudo['personas'].append(copy.deepcopy(self.S.E.crudo['personas'][0]))
   elif mode=='baja':self.S.E.crudo['personas'][0]['estado']='baja'
   else:self.S.E.crudo['personas'][0]['activo']=False
   with self.assertRaises(M.ErrorDecision):self.save(self.nueva())
 def test_revoca_antescommit_rollback(self):
  original=M.autorizar_fila
  def revoke(*args,**kw):self.S.ACT.es_activo_id=lambda _:False;return original(*args,**kw)
  with patch.object(M,'autorizar_fila',side_effect=revoke):
   with self.assertRaises(M.ErrorDecision):self.save(self.nueva())
  self.assertEqual(self.count(),0)
 def test_delegado_canonico_y_cambia(self):
  b=self.answer();b.update(decision='Delegar',motivo='Necesita revisión técnica',delegada_en='coti');self.S.E.crudo['personas'][2]['estado']='baja'
  with self.assertRaises(M.ErrorDecision):self.save(b)
  self.assertIsNone(self.con.execute('SELECT respondida FROM decisiones').fetchone()[0])
 def test_datos_extra_secretos_no_persistir(self):
  for field,value in [('titulo','password: fixture-secreto'),('problema','correo fixture@example.com'),('recomendacion','Presupuesto 500 €')]:
   b=self.nueva();b[field]=value
   with self.assertRaises(M.ErrorDecision):self.save(b)
  b=self.nueva();b['prueba']='https://secret.test'
  with self.assertRaises(M.ErrorDecision):self.save(b)
  self.assertEqual(self.count(),0)
 def test_GET_saneado_sin_payload_y_scope(self):
  self.save(self.nueva(),r='autor');out=M.listar(self.S,self.con,'autor','autor');self.assertEqual(len(out['decisiones']),1);self.assertFalse(out['decisiones'][0]['puede_responder']);self.assertNotIn('datos',out['decisiones'][0]);self.assertIsNone(out['decisiones'][0]['respuesta']);self.assertFalse(out['envio_realizado'])
 def test_lectura_revalidada_cliente(self):
  self.save(self.nueva());old=M.dto
  def mutate(*a):x=old(*a);self.S.ACT.es_activo_id=lambda _:False;return x
  with patch.object(M,'dto',side_effect=mutate):
   with self.assertRaises(M.ErrorDecision):M.listar(self.S,self.con,'tomas','tomas')
 def test_interno_explicito(self):
  r=self.save(self.nueva(cid=None));self.assertTrue(r['recibo']['guardado_local'])
 def test_historial_respuesta_real_minimo(self):
  b=self.answer();b.update(decision='Delegar',motivo='Revisar planificación',delegada_en='coti');self.save(b)
  d=M.listar(self.S,self.con,'tomas','tomas')['decisiones'][0]
  self.assertEqual(d['respondida_por'],'tomas');self.assertEqual(d['respuesta'],{'decision':'Delegar','motivo':'Revisar planificación','delegada_en':'coti'});self.assertFalse(d['puede_responder'])
 def test_respuesta_legacy_malformada_unknown(self):
  self.save(self.nueva())
  for value in ['[]','"texto privado"','not-json',json.dumps({'decision':'Inventada','motivo':'texto privado'}),json.dumps({'decision':'Rechazar','motivo':{'secret':'fixture'}})]:
   self.con.execute("UPDATE decisiones SET respondida=datetime('now'),respuesta=? WHERE id=1",(value,));self.con.commit()
   d=M.listar(self.S,self.con,'tomas','tomas')['decisiones'][0];self.assertIsNone(d['respuesta']);self.assertNotIn('texto privado',str(d))
 def test_respuesta_legacy_whitelist_saneado_y_autores_unknown(self):
  self.save(self.nueva());raw={'decision':'Delegar','motivo':'Correo fixture@example.com y password: fixture-secreto','delegada_en':'coti','nota':'privado-noleer','datos':{'secret':'privado-noleer'}}
  self.con.execute("UPDATE decisiones SET respondida=datetime('now'),respuesta=?,respondida_por='no-canonico' WHERE id=1",(json.dumps(raw),));self.con.commit();self.S.E.crudo['personas'][2]['estado']='baja'
  d=M.listar(self.S,self.con,'tomas','tomas')['decisiones'][0]
  self.assertIsNone(d['respuesta']['delegada_en']);self.assertIsNone(d['respondida_por']);self.assertNotIn('fixture@example.com',str(d));self.assertNotIn('fixture-secreto',str(d));self.assertNotIn('privado-noleer',str(d));self.assertEqual(d['respuesta']['decision'],'Delegar')
 def test_estado_legacy_vacio_no_recibo_falso(self):
  b=self.answer();self.con.execute("UPDATE decisiones SET respondida='' WHERE id=1");self.con.commit()
  b['revision']=M.revision(M.leer(self.con,'db-1'))
  with self.assertRaises(M.ErrorDecision) as e:self.save(b)
  self.assertEqual(e.exception.codigo,409);self.assertEqual(self.con.execute('SELECT count(*) FROM decisiones_intenciones_382').fetchone()[0],1)
 def test_replay_otra_conexion_mismo_ledger(self):
  self.save(self.nueva());path=Path(self.temp.name)/'test.sqlite3'
  with sqlite3.connect(path) as otra:
   otra.row_factory=sqlite3.Row;r=M.guardar(self.S,otra,'tomas','tomas',self.nueva())
  self.assertEqual(r['resultado'],'duplicado');self.assertEqual(self.count(),1)
 def test_delegado_cambia_antescommit_rollback(self):
  b=self.answer();b.update(decision='Delegar',motivo='Necesita revisión técnica',delegada_en='coti');original=M.autorizar_fila;calls=[]
  def change(*args,**kw):
   calls.append(True)
   if len(calls)==2:self.S.E.crudo['personas'][2]['puestos'].append('seo')
   return original(*args,**kw)
  with patch.object(M,'autorizar_fila',side_effect=change):
   with self.assertRaises(M.ErrorDecision) as e:self.save(b)
  self.assertEqual(e.exception.codigo,409);self.assertIsNone(self.con.execute('SELECT respondida FROM decisiones').fetchone()[0])
 def test_handler_POST_GET_y_receipt(self):
  path=Path(self.temp.name)/'test.sqlite3';self.S.conectar=lambda:sqlite3.connect(path)
  class H:
   _api_get=lambda *a:'old';api_post=lambda *a:'old'
   responder=lambda self,status,d:(status,d)
  M.enganchar(H,self.S);p=self.S.E.crudo['personas'][0];h=H()
  status,first=h.api_post(M.RUTA,p,p,self.nueva());self.assertEqual(status,200)
  status,replay=h.api_post(M.RUTA,p,p,self.nueva());self.assertEqual(status,200);self.assertEqual(replay['resultado'],'duplicado');self.assertEqual(first['recibo'],replay['recibo'])
  status,view=h._api_get(M.RUTA,{},p,p);self.assertEqual(status,200);self.assertEqual(len(view['decisiones']),1);self.assertTrue(view['decisiones'][0]['puede_responder'])
 def test_handler_modoexterno_no_SQL(self):
  self.S.conectar=lambda:(_ for _ in ()).throw(AssertionError('no debe conectar'))
  class H:
   _api_get=lambda *a:'old';api_post=lambda *a:'old'
   responder=lambda self,status,d:(status,d)
  M.enganchar(H,self.S);p=self.S.E.crudo['personas'][0]
  with patch.dict('os.environ',{'PGDATABASE_URL':'fixture-no-token'}):self.assertEqual(H()._api_get(M.RUTA,{},p,p)[0],503)
 def test_hook_q400_no_sql(self):
  class H:
   _api_get=lambda *a:'old';api_post=lambda *a:'old'
   responder=lambda self,status,d:(status,d)
  M.enganchar(H,self.S);p=self.S.E.crudo['personas'][0];self.assertEqual(H()._api_get(M.RUTA,{'yo':['autor']},p,p)[0],400)
if __name__=='__main__':unittest.main()
