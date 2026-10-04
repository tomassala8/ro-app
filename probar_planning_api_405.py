import copy,json,hashlib,os,unittest
from datetime import datetime,timezone
from unittest.mock import patch
import planning_observado_api_405 as M
import planning_observado_api_356 as B
from probar_planning_observado_api_356 import PlanningAPI
class Planning405(unittest.TestCase):
 def setUp(self):
  self.f=PlanningAPI('test_roundtrip355_scope_whitelist');self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.path=self.f.path;self.S=self.f.S;self.now=self.f.now
  self.doc=copy.deepcopy(self.f.doc);self.doc.update(version='395.1',estados_incluidos=sorted(M.ESTADOS),corte_preparacion_utc='2026-10-03T17:30:00Z',entradas_sha256={},codigo_sha256={})
  row=self.doc['filas'][0];self.doc['filas']=[{**copy.deepcopy(row),'tarea_id':'task'+str(i),'estado':state,'cliente_id':'c1' if i%2 else 'c2'} for i,state in enumerate(sorted(M.ESTADOS))]
  self.catalogo={'listas':{'l1':{'ok':True,'estados':[{'status':state,'type':'custom'} for state in M.ESTADOS]}}}
  self.save()
  self.env=patch.dict(os.environ,{M.ENV:''});self.env.start();self.addCleanup(self.env.stop)
 def save(self):
  raw=json.dumps(self.doc).encode();self.sha=hashlib.sha256(raw).hexdigest();self.path.write_bytes(raw);self.path.chmod(0o600)
  manifest={'version':'395.1','promovido':False,'lectura_no_concede_permiso':True,'candidato_sha256':self.sha,'fuentes_sha256':{},'codigo_sha256':{}}
  raw=json.dumps(manifest).encode();self.msha=hashlib.sha256(raw).hexdigest();p=self.path.parent/'manifest.json';p.write_bytes(raw);p.chmod(0o600)
 def call(self,r='ops',v=None):
  with patch.object(M,'SHA',self.sha),patch.object(M,'MANIFEST_SHA',self.msha),patch.object(M,'verificar_fuentes',return_value=self.catalogo):return M.listar(self.S,r,v or r,self.path,self.now)
 def test_five_exact_states_and_whitelist(self):
  d=self.call();self.assertEqual(d['version'],'405.1');self.assertEqual(d['observaciones'],5);self.assertEqual({r['estado'] for r in d['filas']},M.ESTADOS);self.assertNotIn('NO_EXPORTAR',json.dumps(d));self.assertNotIn('entradas_sha256',d);self.assertIsNone(d['disciplina']);self.assertIsNone(d['cumplimiento'])
 def test_actual_source_not_refreshed_clock(self):
  d=self.call();self.assertEqual(d['generado'],'2026-10-03T18:00:00Z');self.assertEqual(d['lectura_hasta_utc'],'2026-10-03T17:00:00Z');self.assertEqual(d['corte_preparacion_utc'],'2026-10-03T17:30:00Z')
 def test_account_own_real_view_scope(self):
  for r,v in [('a',None),('ops','a')]:self.assertEqual({x['cliente_id'] for x in self.call(r,v)['filas']},{'c1'})
 def test_invalid_catalog_list_type_final_exact_state(self):
  for fn in [lambda r:r.update(estado='Hoy'),lambda r:r.update(lista_id='otra'),lambda r:r.update(tipo_estado='closed'),lambda r:r.update(estado='planning mensual ',tipo_estado='custom')]:
   original=copy.deepcopy(self.doc);fn(self.doc['filas'][0]);self.save()
   with self.assertRaises(B.ErrorPlanning):self.call()
   self.doc=original;self.save()
 def test_global_duplicate_across_states(self):
  self.doc['filas'][1]['tarea_id']=self.doc['filas'][0]['tarea_id'];self.save()
  with self.assertRaises(B.ErrorPlanning):self.call()
 def test_invalid_unit_fraction_extreme_reading(self):
  for field,val in [('estimacion',{'valor':True,'unidad':'milisegundos','estado':'observada'}),('estado_leido_utc','2026-10-03T18:00:01Z'),('estado_leido_utc','2026-10-03T17:00:00+02:99'),('actor_historico','ops')]:
   original=copy.deepcopy(self.doc);self.doc['filas'][0][field]=val;self.save()
   with self.assertRaises(B.ErrorPlanning):self.call()
   self.doc=original;self.save()
 def test_revocation_during_load_and_role_module(self):
  original=M.cargar
  def revoked(path):
   d=original(path);self.S.ACT.es_activo_id=lambda cid:False;return d
  with patch.object(M,'cargar',revoked):
   with self.assertRaises(B.ErrorPlanning) as e:self.call()
  self.assertEqual(e.exception.codigo,403)
 def test_inactive_duplicate_actor_denied(self):
  for kind in ('inactive','duplicate','module'):
   backup=copy.deepcopy(self.S.E.crudo)
   if kind=='inactive':self.S.E.crudo['personas'][0]['estado']='baja'
   elif kind=='duplicate':self.S.E.crudo['personas'].append(copy.deepcopy(self.S.E.crudo['personas'][0]))
   else:self.S.ve_alguno=lambda *args:True
   with self.assertRaises(B.ErrorPlanning):self.call()
   self.S.E.crudo=backup;self.S.ve_alguno=lambda *args:'todo'
 def test_source_rotation_post_read_rejected(self):
  with patch.object(M,'SHA',self.sha),patch.object(M,'MANIFEST_SHA',self.msha),patch.object(M,'verificar_fuentes',side_effect=[self.catalogo,ValueError('cambió')]):
   with self.assertRaises(B.ErrorPlanning) as e:M.listar(self.S,'ops','ops',self.path,self.now)
  self.assertEqual(e.exception.codigo,503)
 def test_symlink_mode_hardlink_hash_denied(self):
  self.path.chmod(0o644)
  with self.assertRaises(B.ErrorPlanning):self.call()
  self.path.chmod(0o600);other=self.path.parent/'hard';os.link(self.path,other)
  with self.assertRaises(B.ErrorPlanning):self.call()
  other.unlink();self.path.write_text('{}')
  with self.assertRaises(B.ErrorPlanning):self.call()
 def test_empty_unknown_not_zero(self):
  self.doc['filas']=[];self.save();d=self.call();self.assertIsNone(d['observaciones']);self.assertEqual(d['filas'],[])
 def test_env_rotation_during_read_denied(self):
  original=M.cargar
  def rotate(path):
   d=original(path);os.environ[M.ENV]='otro';return d
  with patch.dict(os.environ,{M.ENV:str(self.path)}),patch.object(M,'cargar',rotate),patch.object(M,'SHA',self.sha),patch.object(M,'MANIFEST_SHA',self.msha),patch.object(M,'verificar_fuentes',return_value=self.catalogo):
   with self.assertRaises(B.ErrorPlanning) as e:M.listar(self.S,'ops','ops',ahora=self.now)
  self.assertEqual(e.exception.codigo,403)
 def test_strict_json_duplicates_nan_overflow(self):
  for raw in [b'{"version":"395.1","version":"395.1"}',b'{"x":NaN}',b'{"x":1e999}']:
   self.path.write_bytes(raw)
   with self.assertRaises(ValueError):M._leer(self.path,hashlib.sha256(raw).hexdigest(),1000,True)
 def test_hook_off_delegates_legacy_and_query_denied(self):
  class H:
   def _api_get(s,*args):return 'legacy'
   def responder(s,status,d):return status,d
  M.enganchar(H,self.S);self.assertEqual(H()._api_get(B.RUTA,{}, {}, {}),'legacy')
  with patch.dict(os.environ,{M.ENV:'fixture'}):self.assertEqual(H()._api_get(B.RUTA,{'yo':['ops']},{'id':'ops'},{'id':'ops'})[0],400)
if __name__=='__main__':unittest.main()
