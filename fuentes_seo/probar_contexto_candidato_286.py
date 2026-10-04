import unittest,json
from fuentes_seo.contexto_candidato_286 import proyectar
from fuentes_seo.motores_contexto import contexto_desde_cache
class Test(unittest.TestCase):
 def go(self,c=None,e=None,**kw):
  args=dict(cliente_id='fixture',proyecto=10,motores_permitidos=[1],configuraciones=c if c is not None else [{'site_engine_id':1,'search_engine_id':251,'region_name':'City, Region, Country','lang_code':'es','merge_map':2}],catalogo=e if e is not None else [{'id':'251','name':'Google Spain','regionid':'999'}],leido='2026-10-03T07:00:00Z',ahora='2026-10-03T08:00:00Z');args.update(kw);return proyectar(**args)
 def test_exact_join_compatible(self):
  r=self.go();d={'catalogo':r['catalogo'],'clientes':{'fixture':r['registro']}};v=contexto_desde_cache('fixture',10,[{'site_engine_id':1}],d)[0];self.assertEqual(v['configuracion_actual']['region'],'City, Region, Country');self.assertIsNone(v['dispositivo']);self.assertIsNone(v['region']);self.assertTrue(v['configuracion_actual']['maps_separado'])
 def test_secret_whitelist(self):
  c={'site_engine_id':1,'search_engine_id':251,'phone':'PRIVATE','business_name':'PRIVATE','guest_link':'PRIVATE','merge_map':2};self.assertNotIn('PRIVATE',json.dumps(self.go(c=[c])))
 def test_duplicate_config_rejects(self):
  x={'site_engine_id':1,'search_engine_id':251};self.assertEqual(self.go(c=[x,x])['registro']['configuraciones'],[])
 def test_duplicate_catalog_rejects(self):
  self.assertEqual(self.go(e=[{'id':251},{'id':'251'}])['registro']['configuraciones'],[])
 def test_foreign_engine_rejects(self):
  self.assertFalse(self.go(c=[{'site_engine_id':2,'search_engine_id':251}])['registro']['cobertura']['completa'])
 def test_unknown_catalog_rejects(self):
  self.assertEqual(self.go(e=[])['registro']['configuraciones'],[])
 def test_future_naive_bad_date(self):
  for t in ['2026-10-04T00:00:00Z','2026-10-03','invalid']:
   with self.assertRaises(ValueError):self.go(leido=t)
 def test_boolean_id_rejects(self):
  with self.assertRaises(ValueError):self.go(proyecto=True)
 def test_maps_string_and_unknown(self):
  for raw,wanted in [('2',True),(0,False),(3,None),(True,None),(None,None)]:
   r=self.go(c=[{'site_engine_id':1,'search_engine_id':251,'merge_map':raw}]);self.assertIs(r['registro']['configuraciones'][0]['maps_separado'],wanted)
 def test_mobile_explicit_only(self):
  r=self.go(e=[{'id':251,'name':'Google Mobile Spain'}]);self.assertEqual(r['registro']['configuraciones'][0]['dispositivo'],'mobile');self.assertIsNone(self.go()['registro']['configuraciones'][0]['dispositivo'])
 def test_no_goal_or_historical_claim(self):
  r=self.go()['registro'];self.assertFalse(r['contexto_historico_confirmado']);self.assertFalse(r['objetivo_ciudad_confirmado'])
 def test_project_mismatch(self):
  r=self.go();d={'catalogo':r['catalogo'],'clientes':{'fixture':r['registro']}};v=contexto_desde_cache('fixture',11,[{'site_engine_id':1}],d)[0];self.assertIsNone(v['region'])
 def test_text_no_secret_urls(self):
  r=self.go(c=[{'site_engine_id':1,'search_engine_id':251,'region_name':'https://example.test?token=PRIVATE'}]);self.assertIsNone(r['registro']['configuraciones'][0]['region_name'])
if __name__=='__main__':unittest.main()
