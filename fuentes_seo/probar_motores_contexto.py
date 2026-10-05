import unittest,json
from fuentes_seo.motores_contexto import motores_contexto,contexto_desde_cache
class Test(unittest.TestCase):
 def test_sin_contactos(self):
  r=motores_contexto([{'site_engine_id':1,'search_engine_id':251,'region_name':'Barcelona, Catalonia, Spain','merge_map':2,'phone':'private','business_name':'private'}],[{'id':'251','name':'Google Spain','type':'google'}])[0]
  self.assertEqual(r['region'],'Barcelona, Catalonia, Spain');self.assertIsNone(r['dispositivo']);self.assertTrue(r['maps_separado']);self.assertNotIn('private',json.dumps(r))
 def test_no_fuzzy_ni_primero(self):
  r=motores_contexto([{'site_engine_id':2,'search_engine_id':999}],[{'id':251,'name':'Google Mobile Spain'}]);self.assertEqual(r,[])
 def test_mobile_explicito_dedup(self):
  r=motores_contexto([{'site_engine_id':2,'search_engine_id':252},{'site_engine_id':2,'search_engine_id':252},None],[{'id':252,'name':'Google Mobile Spain'}]);self.assertEqual(r,[])
 def test_proyecto_no_intercambiable(self):
  doc={'catalogo':[{'id':251,'name':'Google Spain'}],'clientes':{'c':{'proyecto':10,'leido':'2026-10-03','configuraciones':[{'site_engine_id':1,'search_engine_id':251,'region_name':'Barcelona'}]}}}
  r=contexto_desde_cache('c',11,[{'site_engine_id':1,'principal':True}],doc)[0];self.assertIsNone(r['region']);self.assertEqual(r['estado_contexto'],'sin_dato')
 def test_identidad_motor_fecha_y_unknown(self):
  doc={'catalogo':[{'id':251,'name':'Google Spain'}],'clientes':{'c':{'proyecto':10,'leido':'2026-10-03','configuraciones':[{'site_engine_id':1,'search_engine_id':251,'region_name':'Barcelona','merge_map':2}]}}}
  rs=contexto_desde_cache('c',10,[{'site_engine_id':1,'principal':True},{'site_engine_id':2}],doc)
  self.assertEqual(rs[0]['fecha_contexto'],'2026-10-03');self.assertTrue(rs[0]['configuracion_actual']['maps_separado']);self.assertIsNone(rs[0]['dispositivo']);self.assertIsNone(rs[0]['region']);self.assertIsNone(rs[1]['region']);self.assertIsNone(rs[1]['fecha_contexto'])
 def test_cache_malformada_no_tumba(self):
  for doc in [None,[],{'clientes':[]},{'clientes':{'c':None}}]:
   self.assertEqual(contexto_desde_cache('c',10,[{'site_engine_id':1}],doc)[0]['estado_contexto'],'sin_dato')
if __name__=='__main__':unittest.main()
