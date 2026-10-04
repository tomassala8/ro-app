import copy,hashlib,json,os,tempfile,types,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
import planning_observado_api_356 as B
import permisos as P
from fuentes_produccion.planning_observado_355 import construir
class PlanningAPI(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name).resolve()/'private';self.folder.mkdir(mode=0o700);self.path=self.folder/'candidato.json';self.now=datetime(2026,10,3,18,tzinfo=timezone.utc)
  self.raw={'personas':[{'id':i,'estado':'activo','puestos':[role]} for i,role in [('ops','operaciones'),('a','account'),('b','account')]],'clientes':[{'id':'c1','activo':True},{'id':'c2','activo':True}],'asignaciones':[{'cliente_id':'c1','persona_id':'a','silla':'account','principal':True,'confianza':'confirmada'},{'cliente_id':'c2','persona_id':'b','silla':'account','principal':True,'confianza':'confirmada'}]}
  self.S=types.SimpleNamespace(E=types.SimpleNamespace(crudo=self.raw,nucleo_bloqueado=False),P=types.SimpleNamespace(ver=P.ver,contexto=P.contexto,hoy_iso=lambda:'2026-10-03'),ACT=types.SimpleNamespace(es_activo_id=lambda _:True),ve_alguno=lambda *args:'todo')
  t={'id':'t1','carpeta_id':'f1','lista_id':'l1','estado':'planning mensual','tipo_estado':'custom','estado_fuente':'clickup','estado_leido_utc':'2026-10-03T17:00:00Z','asignados':[{'id':12}], 'vence':'1791244800000','estimacion_ms':22}
  self.doc=construir({'tareas':[t,{**t,'id':'t2','carpeta_id':'f2'}]},{'listas':{'l1':{'ok':True,'estados':[{'status':'planning mensual','type':'custom'}]}}},{'f1':('c1',None),'f2':('c2',None)},{'c1','c2'},{'12':'a'},{'a'},self.now)
  self.doc['PII_extra']='NO_EXPORTAR';self.manifest={'version':'355.1','promovido':False,'lectura_no_concede_permiso':True};self.save()
  self.env=patch.dict(os.environ,{B.ENV:''});self.env.start();self.addCleanup(self.env.stop)
 def save(self):
  data=json.dumps(self.doc,allow_nan=False).encode();self.path.write_bytes(data);os.chmod(self.path,0o600);self.sha=hashlib.sha256(data).hexdigest();m={**self.manifest,'candidato_sha256':self.sha};raw=json.dumps(m).encode();p=self.folder/'manifest.json';p.write_bytes(raw);os.chmod(p,0o600);self.msha=hashlib.sha256(raw).hexdigest()
 def call(self,r='ops',v=None):
  with patch.object(B,'SHA',self.sha),patch.object(B,'MANIFEST_SHA',self.msha):return B.listar(self.S,r,v or r,self.path,self.now)
 def test_roundtrip355_scope_whitelist(self):
  d=self.call();self.assertEqual(d['observaciones'],2);self.assertEqual(d['fuente_version'],'355.1');self.assertIsNone(d['disciplina']);self.assertIsNone(d['cumplimiento']);self.assertNotIn('NO_EXPORTAR',json.dumps(d));self.assertNotIn('entradas_sha256',d);self.assertEqual(d['filas'][0]['vence_estado'],'observada')
 def test_account_confirmed_own_only(self):
  d=self.call('a');self.assertEqual(d['cliente_ids'],['c1']);self.assertEqual([r['cliente_id'] for r in d['filas']],['c1'])
 def test_view_as_intersection(self):self.assertEqual(len(self.call('ops','a')['filas']),1)
 def test_read_grant_not_historical_responsibility(self):
  self.raw['asignaciones'][0]['confianza']='alta';d=self.call('a');self.assertEqual([r['cliente_id'] for r in d['filas']],['c1']);self.assertIsNone(d['filas'][0]['actor_historico']);self.assertIsNone(d['disciplina'])
 def test_unknown_no_env_no_read_no_zero(self):
  with patch.object(B,'cargar',side_effect=AssertionError('read')):d=B.listar(self.S,'ops','ops',ahora=self.now)
  self.assertEqual(d['estado'],'sin_dato');self.assertIsNone(d['observaciones']);self.assertIsNone(d['sha256_candidato'])
 def test_module_identity_duplicate_denied(self):
  self.S.ve_alguno=lambda p,mods:None if mods==['produccion'] else 'todo'
  with self.assertRaises(B.ErrorPlanning):self.call()
  self.S.ve_alguno=lambda *a:'todo';self.raw['personas'].append(copy.deepcopy(self.raw['personas'][0]))
  with self.assertRaises(B.ErrorPlanning):self.call()
 def test_actual_module_levels_and_invalid_denied(self):
  for nivel in ('todo','suyo','resumen'):
   self.S.ve_alguno=lambda *args,n=nivel:n
   self.assertEqual(self.call()['observaciones'],2)
  for nivel in (None,False,True,'desconocido'):
   self.S.ve_alguno=lambda p,mods,n=nivel:n if mods==['produccion'] else 'todo'
   with self.assertRaises(B.ErrorPlanning) as e:self.call()
   self.assertEqual(e.exception.codigo,403)
 def test_module_level_change_during_read_denies(self):
  original=B.cargar
  def load(path):
   doc=original(path)
   self.S.ve_alguno=lambda p,mods:'suyo' if mods==['produccion'] else 'todo'
   return doc
  with patch.object(B,'cargar',load):
   with self.assertRaises(B.ErrorPlanning) as e:self.call()
   self.assertEqual(e.exception.codigo,403)
 def test_act_duplicate_client_excluded(self):
  self.S.ACT.es_activo_id=lambda cid:cid!='c1';self.assertEqual([r['cliente_id'] for r in self.call()['filas']],['c2'])
  self.raw['clientes'].append({'id':'c2'});self.assertEqual(self.call()['filas'],[])
 def test_assigned_person_now_inactive_no_claim(self):
  self.raw['personas'][1]['estado']='baja';r=self.call()['filas'][0];self.assertEqual(r['asignados_persona_ids'],[]);self.assertEqual(r['asignacion_estado'],'parcial')
 def test_temporal_future_read_deny_but_future_due_allowed(self):
  self.doc['filas'][0]['estado_leido_utc']='2026-10-04T17:00:00Z';self.save()
  with self.assertRaises(B.ErrorPlanning) as e:self.call()
  self.assertEqual(e.exception.codigo,503)
 def test_hash_or_manifest_tamper(self):
  self.path.write_text('{}')
  with self.assertRaises(B.ErrorPlanning):self.call()
  self.save();(self.folder/'manifest.json').write_text('{}')
  with self.assertRaises(B.ErrorPlanning):self.call()
 def test_symlink_permissions_and_root_relative_rejected(self):
  self.path.chmod(0o644)
  with self.assertRaises(B.ErrorPlanning):self.call()
  self.path.chmod(0o600);self.folder.chmod(0o755)
  with self.assertRaises(B.ErrorPlanning):self.call()
 def test_invalid_type_semantics_duplicate_unit_future_dates(self):
  base=copy.deepcopy(self.doc)
  for fn in [lambda r:r.update(tipo_estado='closed'),lambda r:r.update(estado_fuente='cache'),lambda r:r.update(asignados_persona_ids=[{}]),lambda r:r['estimacion'].update(unidad='horas'),lambda r:r.update(actor_historico='a')]:
   self.doc=copy.deepcopy(base);fn(self.doc['filas'][0]);self.save()
   with self.assertRaises(B.ErrorPlanning):self.call()
 def test_scope_revoke_during_load(self):
  original=B.cargar
  def load(path):d=original(path);self.S.ACT.es_activo_id=lambda _:False;return d
  with patch.object(B,'cargar',load):
   with self.assertRaises(B.ErrorPlanning) as e:self.call()
  self.assertEqual(e.exception.codigo,403)
 def test_generation_is_read_not_observed_source(self):
  d=self.call();self.assertEqual(d['generado'],'2026-10-03T18:00:00Z');self.assertEqual(d['lectura_hasta_utc'],'2026-10-03T17:00:00Z')
 def test_current_source_times_fraction_order(self):
  self.doc['filas'][1]['estado_leido_utc']='2026-10-03T17:00:00.100000Z';self.save();d=self.call();self.assertEqual(d['lectura_hasta_utc'],'2026-10-03T17:00:00.100000Z')
 def test_query_exact_hook_without_writes(self):
  class H:
   def _api_get(self,*a):return 418,{}
   def responder(self,c,d):return c,d
  B.enganchar(H,self.S);h=H()
  with patch.object(B,'cargar',side_effect=AssertionError('read')):
   self.assertEqual(h._api_get(B.RUTA,{'yo':['ops']},{'id':'ops'},{'id':'ops'})[0],400)
   code,d=h._api_get(B.RUTA,{}, {'id':'ops'},{'id':'ops'});self.assertEqual(code,200);self.assertEqual(d['estado'],'sin_dato')
if __name__=='__main__':unittest.main()
