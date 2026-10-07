import os,sqlite3,tempfile,unittest,uuid,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from evidencias_kpi import ArchivoEvidencias,ErrorEvidencia,validar

class Evidencias(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name).resolve()/'eventos.sqlite';self.now=datetime(2026,10,8,12,tzinfo=timezone.utc)
  self.catalog={'uno':{'activo_confirmado':True},'ajeno':{'activo_confirmado':True},'baja':{'activo_confirmado':False}}
  self.people={pid:{'id':pid,'estado':'activo','activo':True} for pid in ('account','ops','otro')}
  self.can=lambda pid,cid:pid=='ops' or (pid=='account' and cid=='uno') or (pid=='otro' and cid=='ajeno')
  self.store=ArchivoEvidencias(self.path,self.catalog,self.people,self.can,ahora=lambda:self.now)
  self.body={'clave':str(uuid.uuid4()),'cliente_id':'uno','tipo':'contacto','canal':'email','fecha':'2026-10-04T23:30:00Z','motivo':'seguimiento'}
 def tearDown(self):self.tmp.cleanup()
 def codigo(self,n,fn,*args):
  with self.assertRaises(ErrorEvidencia) as e:fn(*args)
  self.assertEqual(e.exception.codigo,n)
 def register(self,body=None,real='account',vista='account'):return self.store.registrar(real,vista,body or self.body)
 def test_hecho_periodo_exacto_no_cumplimiento(self):
  r=self.register()['registro'];self.assertEqual(r['semana_inicio'],'2026-10-05');self.assertEqual(r['fecha_madrid'],'2026-10-05');self.assertEqual(r['mes'],'2026-10');self.assertEqual(r['source_kind'],'registro_equipo');self.assertFalse(r['verificacion_externa']);self.assertIsNone(r['cumplimiento'])
  self.assertEqual(self.store.listar('account','account','uno','2026-10-05')['registros'][0]['id'],r['id'])
  self.assertFalse(self.store.listar('account','account','uno')['cobertura']['contacto_exhaustivo'])
 def test_doble_identidad_act_y_cartera(self):
  self.codigo(403,self.register,self.body,'account','ops');self.codigo(403,self.store.listar,'ops','otro','uno');self.codigo(403,self.register,{**self.body,'cliente_id':'baja'});self.codigo(403,self.register,{**self.body,'cliente_id':'ajeno'})
  self.people['account']['estado']='baja';self.codigo(403,self.register)
 def test_payload_no_declara_identidad_ni_verificacion(self):
  for k,v in [('source_kind','proveedor'),('actor_id','ops'),('texto','Contacto personal'),('verificacion_externa',True),('salario',3)]:self.codigo(400,self.register,{**self.body,k:v})
 def test_idempotencia_y_conflicto_payload(self):
  r=self.register();d=self.register();self.assertEqual(r['resultado'],'aceptado');self.assertEqual(d['resultado'],'duplicado');self.assertEqual(r['registro']['id'],d['registro']['id'])
  self.codigo(409,self.register,{**self.body,'motivo':'revision'});self.codigo(409,self.register,self.body,'ops','ops');self.assertEqual(len(self.store.listar('account','account','uno')['registros']),1)
 def test_concurrencia_un_recibo_un_evento(self):
  with ThreadPoolExecutor(max_workers=8) as p:results=list(p.map(lambda _:self.register()['resultado'],range(8)))
  self.assertEqual(results.count('aceptado'),1);self.assertEqual(results.count('duplicado'),7)
  with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM eventos').fetchone()[0],1)
 def test_revocacion_replay_no_reactiva_y_audita(self):
  rid=self.register()['registro']['id'];clave=str(uuid.uuid4())
  self.codigo(403,self.store.revocar,'ops','ops','uno',rid,clave,'correccion')
  r=self.store.revocar('account','account','uno',rid,clave,'correccion');self.assertEqual(r['registro']['estado'],'revocado');self.assertEqual(self.store.revocar('account','account','uno',rid.upper(),clave.upper(),'correccion')['resultado'],'duplicado');self.assertEqual(self.register()['registro']['estado'],'revocado')
  self.codigo(409,self.store.revocar,'account','account','uno',rid,clave,'duplicado')
  with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM eventos').fetchone()[0],2)
 def test_fechas_y_periodos_no_inventados(self):
  for fecha in ('2026-10-09T10:00:00Z','2026-10-03 10:00','2026-02-30T10:00:00Z','hoy'):self.codigo(400,self.register,{**self.body,'fecha':fecha})
  self.codigo(400,self.register,{**self.body,'semana_inicio':'2026-09-28'});self.codigo(400,self.store.listar,'account','account','uno','2026-10-06')
 def test_urls_no_credenciales_ni_fuentes_arbitrarias(self):
  for u in ('http://app.clickup.com/t/a','https://evil.test/t/a','https://user:fixture1@example.invalid/t/a','https://app.clickup.com/t/a?token=secreto','https://app.clickup.com/../a','https://app.clickup.com/%2e%2e/a','https://app.clickup.com/token/a'):self.codigo(400,self.register,{**self.body,'enlace':u})
  self.assertEqual(self.register({**self.body,'enlace':'https://app.clickup.com/t/abc123'})['registro']['enlace'],'https://app.clickup.com/t/abc123')
 def test_fallo_audit_rollback_no_falso_aceptado(self):
  with sqlite3.connect(self.path) as c:c.execute("CREATE TRIGGER fallo BEFORE INSERT ON eventos BEGIN SELECT RAISE(ABORT,'fallo fixture'); END")
  with self.assertRaises(sqlite3.IntegrityError):self.register()
  with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM registros').fetchone()[0],0)
 def test_permisos_archivo_symlink_y_hardlink(self):
  self.assertEqual(self.path.stat().st_mode&0o777,0o600)
  link=self.path.parent/'link.sqlite';link.symlink_to(self.path);self.codigo(503,ArchivoEvidencias,link,self.catalog,self.people,self.can)
  hard=self.path.parent/'hard.sqlite';os.link(self.path,hard);self.codigo(503,ArchivoEvidencias,hard,self.catalog,self.people,self.can);hard.unlink()
  self.path.chmod(0o644);self.codigo(503,ArchivoEvidencias,self.path,self.catalog,self.people,self.can)
 def test_autorizacion_respuesta_ambigua_no_abre_scope(self):
  self.store.puede_ver=lambda *_:{'ok':False};self.codigo(403,self.register)
 def test_reunion_manual_no_equivale_cadencia(self):
  r=self.register({**self.body,'tipo':'reunion','canal':'video'})['registro'];self.assertEqual(r['estado'],'declarado');self.assertIsNone(r['cumplimiento']);self.assertNotIn('garantia',r);self.codigo(400,self.register,{**self.body,'tipo':'reunion','canal':'email'})
if __name__=='__main__':unittest.main()
