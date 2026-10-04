"""596: ledger/API reales sobre depósito nuevo temporal, sin transporte HTTP."""
import json,sqlite3,unittest,uuid
import probar_evidencias_kpi_api_151 as F

class Informes596(unittest.TestCase):
 def setUp(self):
  self.f=F.Api();self.f.setUp()
  self.body={**self.f.body,'tipo':'informe_enviado','periodo_informe':'2026-08','enlace':'https://app.clickup.com/t/fixture-report','motivo':'revision'}
 def tearDown(self):self.f.tearDown()
 def post(self,**c):return self.f.post({**self.body,**c})
 def test_roundtrip_periodo_no_equivale_mes_envio(self):
  code,d=self.post();self.assertEqual(code,200);r=d['registro']
  self.assertEqual(r['periodo_informe'],'2026-08');self.assertEqual(r['mes'],'2026-09')
  self.assertEqual(r['estado'],'declarado');self.assertIsNone(r['cumplimiento']);self.assertFalse(r['verificacion_externa'])
  self.assertEqual(r['registrado_por'],'own');self.assertNotIn('account_id',r)
  self.assertEqual(self.f.get()[1]['registros'][0],r)
 def test_replay_y_cambio_periodo_conflictivo(self):
  rid=self.post()[1]['registro']['id'];self.assertEqual(self.post()[1]['resultado'],'duplicado')
  self.assertEqual(self.post(periodo_informe='2026-07')[0],409)
  with sqlite3.connect(self.f.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM eventos').fetchone()[0],1)
  self.assertEqual(self.f.get()[1]['registros'][0]['id'],rid)
 def test_periodo_estricto_no_futuro(self):
  for value in (None,'','2026-00','2026-13','2026-8','2026-10',202608,True,'2026-08 extra'):
   with self.subTest(value=value):self.assertEqual(self.post(periodo_informe=value)[0],400)
  self.assertFalse(self.f.path.exists())
 def test_referencia_obligatoria_y_segura(self):
  for value in (None,'','http://app.clickup.com/t/x','https://evil.invalid/t/x','https://app.clickup.com/t/x?token=fixture'):
   with self.subTest(value=value):self.assertEqual(self.post(enlace=value)[0],400)
  self.assertFalse(self.f.path.exists())
 def test_canales_y_fecha(self):
  for value in ('telefono','video','presencial'):
   self.assertEqual(self.post(canal=value)[0],400)
  self.assertEqual(self.post(fecha='2999-01-01T12:00:00Z')[0],400)
  self.assertEqual(self.post(canal='whatsapp')[0],200)
 def test_no_campos_de_autor_verificacion_cumplimiento(self):
  for k,v in [('autor_envio','ops'),('account_id','ops'),('verificacion_externa',True),('cumplimiento',True),('source_kind','proveedor')]:
   self.assertEqual(self.post(**{k:v})[0],400)
  self.assertFalse(self.f.path.exists())
 def test_scope_cliente_y_ver_como(self):
  self.assertEqual(self.f.post(self.body,vista=self.f.ops)[0],403)
  self.assertEqual(self.post(cliente_id='dos')[0],403)
  self.assertEqual(self.f.post(self.body,real={'id':'seo','puestos':['direccion']})[0],403)
  self.assertFalse(self.f.path.exists())
 def test_revocacion_no_reactiva(self):
  r=self.post()[1]['registro'];payload={'accion':'revocar','cliente_id':'uno','registro_id':r['id'],'clave':str(uuid.uuid4()),'motivo':'correccion'}
  self.assertEqual(self.f.post(payload)[1]['registro']['estado'],'revocado')
  self.assertEqual(self.post()[1]['registro']['estado'],'revocado')
 def test_no_cuenta_como_contacto_o_reunion(self):
  self.post();code,d=self.f.h._api_get(F.A.RUTA+'/resumen',{'semana_inicio':['2026-09-28']},self.f.own,self.f.own)
  self.assertEqual(code,200);self.assertEqual(d['clientes'][0]['contactos_declarados'],0);self.assertEqual(d['clientes'][0]['reuniones_declaradas'],0);self.assertIsNone(d['cumplimiento'])
 def test_dto_corrupto_no_publicado(self):
  self.post()
  with sqlite3.connect(self.f.path) as c:
   row=c.execute('SELECT id,payload FROM registros').fetchone();payload=json.loads(row[1]);payload['periodo_informe']='2026-13'
   c.execute('UPDATE registros SET payload=? WHERE id=?',(json.dumps(payload),row[0]))
  code,d=self.f.get();self.assertEqual(code,503);self.assertNotIn('registros',d)
 def test_contacto_no_admite_periodo_informe(self):
  self.assertEqual(self.post(tipo='contacto')[0],400)
  self.assertEqual(self.f.post()[0],200)
 def test_fallo_audit_no_recibo_exitoso(self):
  self.f.get()
  with sqlite3.connect(self.f.path) as c:c.execute("CREATE TRIGGER fallo596 BEFORE INSERT ON eventos BEGIN SELECT RAISE(ABORT,'fixture audit'); END")
  code,d=self.post();self.assertEqual(code,503);self.assertNotIn('registro',d)
  with sqlite3.connect(self.f.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM registros').fetchone()[0],0)
if __name__=='__main__':unittest.main()
