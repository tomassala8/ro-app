import unittest,tempfile,sqlite3,contextlib,copy,uuid
from types import SimpleNamespace as NS
import operaciones_pedidos_account as M
class P:
 @staticmethod
 def hoy_iso():return '2026-10-03'
 @staticmethod
 def contexto(p,d):return {'cartera_por_silla':{'account':{'c'} if p['id']=='a' else set()}}
 @staticmethod
 def ver(p,q,cp):return {'ok':q.get('cliente_id','c')=='c' and (p['id']=='o' or p['id']=='a')}
 @staticmethod
 def mirando_como(*args):return contextlib.nullcontext()
class Test(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=self.tmp.name+'/r.sqlite';self.con=sqlite3.connect(self.db);self.con.row_factory=sqlite3.Row
  self.raw={'personas':[{'id':'o','puestos':['operaciones'],'estado':'activo'},{'id':'a','puestos':['account'],'estado':'activo'},{'id':'s','puestos':['seo'],'estado':'activo'}],'clientes':[{'id':'c'}],'asignaciones':[{'cliente_id':'c','persona_id':'a','silla':'account','principal':True,'confianza':'confirmada','desde':'2026-01-01','hasta':None}]};self.B={'generado':'2026-10-03','fuentes':{},'correos':[{'id':'t','cliente_id':'c'}],'llamadas':[{'id':'l','cliente_id':'c'}]};self.S=NS(E=NS(nucleo_bloqueado=False,crudo=self.raw),P=P,ACT=NS(es_activo_id=lambda c:c=='c'),ve_alguno=lambda p,ms:True,modulo_recortado=lambda *args:self.B);self.old=M.piloto_lectura.activo;M.piloto_lectura.activo=lambda:False
 def tearDown(self):M.piloto_lectura.activo=self.old;self.con.close();self.tmp.cleanup()
 def body(self,estado='pedido',revision=0):
  o,t=M.capacidad(self.S,'o','o','c','responder_correo','t');return {'cliente_id':'c','tipo':'responder_correo','referencia_id':'t','estado':estado,'revision':revision,'revision_fuente':t,'intencion_id':str(uuid.uuid4())}
 def put(self,b):return M.guardar(self.S,self.con,'o','o',b)
 def test_store_replay(self):
  b=self.body();r=self.put(b);self.assertEqual(r['recibo']['receptor'],'a');self.assertFalse(r['recibo']['llamada_realizada']);self.assertEqual(self.put(b)['resultado'],'duplicado');self.assertEqual(self.con.execute('SELECT COUNT(*) FROM '+M.TABLA).fetchone()[0],1)
 def test_payload_collision(self):
  b=self.body();self.put(b);b['estado']='anulado'
  with self.assertRaises(M.ErrorPedido) as e:self.put(b)
  self.assertEqual(e.exception.codigo,409)
 def test_revision_stale(self):
  b=self.body();self.put(b)
  with self.assertRaises(M.ErrorPedido):self.put(self.body())
 def test_source_changed(self):
  b=self.body();self.B['generado']='2026-10-04'
  with self.assertRaises(M.ErrorPedido) as e:self.put(b)
  self.assertEqual(e.exception.codigo,409);self.assertFalse(self.con.in_transaction)
 def test_revoke_during_cas(self):
  b=self.body();calls=0;old=self.S.modulo_recortado
  def read(*a):
   nonlocal calls;calls+=1
   if calls==2:self.S.ACT.es_activo_id=lambda c:False
   return old(*a)
  self.S.modulo_recortado=read
  with self.assertRaises(M.ErrorPedido):self.put(b)
  self.assertIsNone(self.con.execute("SELECT 1 FROM sqlite_master WHERE name=?",(M.TABLA,)).fetchone())
 def test_ambiguous_account(self):
  self.raw['asignaciones'].append(copy.deepcopy(self.raw['asignaciones'][0]))
  with self.assertRaises(M.ErrorPedido):self.body()
 def test_high_confidence_not_confirmed(self):
  self.raw['asignaciones'][0]['confianza']='alta'
  with self.assertRaises(M.ErrorPedido):self.body()
 def test_inactive_recipient(self):
  self.raw['personas'][1]['estado']='baja'
  with self.assertRaises(M.ErrorPedido):self.body()
 def test_duplicate_reference(self):
  self.B['correos'].append(copy.deepcopy(self.B['correos'][0]))
  with self.assertRaises(M.ErrorPedido):self.body()
 def test_auto_reference(self):
  self.B['correos'][0]['auto']=True
  with self.assertRaises(M.ErrorPedido):self.body()
 def test_scope_roles_view_pilot(self):
  b=self.body()
  for rid,vid in [('s','s'),('o','a')]:
   with self.assertRaises(M.ErrorPedido):M.guardar(self.S,self.con,rid,vid,b)
  M.piloto_lectura.activo=lambda:True
  with self.assertRaises(M.ErrorPedido):self.put(b)
 def test_queue_declared(self):
  self.put(self.body());r=M.leer(self.S,self.con,'a','a');self.assertEqual(len(r['pedidos']),1);self.assertEqual(r['pedidos'][0]['estado'],'pedido');self.assertFalse(r['pedidos'][0]['envio_realizado']);self.assertNotIn('asunto',str(r))
 def test_resolve_not_call(self):
  self.put(self.body());b=self.body('resuelto_declarado',1);r=self.put(b);self.assertFalse(r['recibo']['llamada_realizada']);self.assertEqual(M.leer(self.S,self.con,'a','a')['pedidos'][0]['estado'],'resuelto_declarado')
 def test_get_empty_no_creation(self):r=M.leer(self.S,None,'o','o','c');self.assertEqual(r['pedidos'],[]);self.assertEqual(len(r['capacidades']),2);self.assertFalse(self.con.in_transaction)
 def test_revoke_during_get(self):
  self.put(self.body());old=M.dto
  def revoke(r):self.S.ACT.es_activo_id=lambda c:False;return old(r)
  M.dto=revoke
  try:
   with self.assertRaises(M.ErrorPedido):M.leer(self.S,self.con,'a','a')
  finally:M.dto=old
 def test_http_hook_query_read_write(self):
  class H:
   def _api_get(self,*a):return 'delegado'
   def api_post(self,*a):return 'delegado'
   def responder(self,code,body):return code,body
  self.S.DB=self.db;self.S.conectar=lambda:sqlite3.connect(self.db)
  M.enganchar(H,self.S);h=H();real={'id':'o'}
  code,d=h._api_get(M.RUTA,{'cliente_id':['c']},real,real);self.assertEqual(code,200);self.assertEqual(d['pedidos'],[])
  self.assertIsNone(self.con.execute("SELECT 1 FROM sqlite_master WHERE name=?",(M.TABLA,)).fetchone())
  self.assertEqual(h._api_get(M.RUTA,{'yo':['a']},real,real)[0],400)
  b=self.body();self.assertEqual(h.api_post(M.RUTA,real,real,b)[0],200);self.assertEqual(h._api_get(M.RUTA,{}, {'id':'a'},{'id':'a'})[1]['pedidos'][0]['receptor'],'a')
  self.assertEqual(h._api_get('/otra',{},real,real),'delegado')
 def test_uuid_malformed_fields(self):
  b=self.body();b['intencion_id']='no'
  with self.assertRaises(M.ErrorPedido) as e:self.put(b)
  self.assertEqual(e.exception.codigo,400)
  b=self.body();b['receptor']='s'
  with self.assertRaises(M.ErrorPedido):self.put(b)
 def test_recipient_revoke_during_commit(self):
  b=self.body();old=self.S.modulo_recortado;calls=0
  def read(*args):
   nonlocal calls;calls+=1
   if calls==2:self.raw['personas'][1]['estado']='baja'
   return old(*args)
  self.S.modulo_recortado=read
  with self.assertRaises(M.ErrorPedido):self.put(b)
  self.assertIsNone(self.con.execute("SELECT 1 FROM sqlite_master WHERE name=?",(M.TABLA,)).fetchone())
 def test_two_connections_same_revision(self):
  import concurrent.futures
  b1,b2=self.body(),self.body()
  def put(b):
   with sqlite3.connect(self.db,timeout=3) as con:
    con.row_factory=sqlite3.Row
    try:return M.guardar(self.S,con,'o','o',b)['resultado']
    except M.ErrorPedido as e:return e.codigo
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:results=list(ex.map(put,[b1,b2]))
  self.assertCountEqual(results,['guardado',409]);self.assertEqual(self.con.execute('SELECT COUNT(*) FROM '+M.TABLA).fetchone()[0],1)
 def test_queue_filters_before_limit(self):
  self.put(self.body())
  # Filas sintéticas coherentes de otro receptor: no deben agotar el límite de cola propia.
  for i in range(505):
   b={'intencion_id':str(uuid.uuid4()),'cliente_id':'c','tipo':'responder_correo','referencia_id':'other'+str(i),'revision':0,'revision_fuente':'a'*64,'estado':'pedido'}
   self.con.execute('INSERT INTO '+M.TABLA+' VALUES (?,?,?,?,?,?,?,?,?,?,?)',(b['intencion_id'],'c',b['tipo'],b['referencia_id'],1,'o','otro','pedido','2026-10-03T19:00:00Z',b['revision_fuente'],M.fingerprint(b,'o')))
  self.con.commit();r=M.leer(self.S,self.con,'a','a');self.assertEqual(len(r['pedidos']),1);self.assertEqual(r['pedidos'][0]['receptor'],'a');self.assertFalse(r['truncado'])
 def test_recipient_context_denied(self):
  old=self.S.ve_alguno;self.S.ve_alguno=lambda p,ms:p['id']!='a'
  with self.assertRaises(M.ErrorPedido):self.body()
  self.S.ve_alguno=old
if __name__=='__main__':unittest.main()
