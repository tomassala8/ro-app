import unittest,copy
from fuentes_seo.seo_prioridades import evaluar_seo,consultas_objetivo
C={'cliente_id':'fixture','servicio_seo_confirmado':True,'fuente_servicio':'fixture','servicios_reales':['asesoria'],'ciudades_verificadas':[{'ciudad':'Ciudad','fuente':'brief fixture'}]}
R={'consulta':'asesoria ciudad','ciudad':'Ciudad','canal':'organico','posicion':1,'fecha':'2026-10-02','fuente':'fixture'}
class SEO374(unittest.TestCase):
 def result(self,c=C,r=R):return evaluar_seo(c,{'rankings':[r]},'2026-10-03')
 def test_position_one_without_context_not_local_goal(self):
  r=self.result();o=r['objetivos'][0]
  self.assertEqual(o['posicion'],1);self.assertFalse(o['objetivo_local_acreditado']);self.assertEqual(o['estado'],'posicion_1_observada_contexto_pendiente');self.assertEqual(r['prioridades'][0]['tipo'],'confirmar_contexto');self.assertFalse(r['garantia'])
 def test_labels_alone_cannot_confirm_engine(self):
  r=self.result(r={**R,'dispositivo':'desktop','ubicacion_medicion':'Ciudad'})
  self.assertFalse(r['objetivos'][0]['objetivo_local_acreditado'])
 def test_context_requires_canonical_city_channel_and_temporal_attestation(self):
  c={**C,'ciudades_verificadas':[{'ciudad':'Ciudad','ciudad_id':'city-fixture','fuente':'brief'}]}
  valid={**R,'ciudad_id':'city-fixture','dispositivo':'desktop','ubicacion_medicion':'Ciudad','canal_confirmado':True,'contexto_posicion_confirmado':True}
  self.assertTrue(self.result(c,valid)['objetivos'][0]['objetivo_local_acreditado'])
  for k,v in [('ciudad_id','other'),('canal_confirmado',False),('contexto_posicion_confirmado',False),('ubicacion_medicion','other'),('dispositivo',None)]:self.assertFalse(self.result(c,{**valid,k:v})['objetivos'][0]['objetivo_local_acreditado'])
 def test_absence_and_false_position_never_zero(self):
  for v in [None,0,False,'1',float('inf')]:self.assertIsNone(self.result(r={**R,'posicion':v})['objetivos'][0]['posicion'])
 def test_no_city_no_services_invented(self):
  self.assertFalse(self.result({**C,'ciudades_verificadas':[]})['habilitado']);self.assertFalse(self.result({**C,'servicios_reales':[]})['habilitado'])
 def test_service_is_from_explicit_taxonomy_not_label(self):
  qs=consultas_objetivo(C);self.assertEqual(qs[0]['servicio'],'asesoria');self.assertEqual(len(qs),1)
 def test_inputs_immutable_and_future_not_current(self):
  c=copy.deepcopy(C);r=copy.deepcopy(R);self.result(c,r);self.assertEqual(c,C);self.assertEqual(r,R);self.assertIsNone(self.result(r={**R,'fecha':'2026-10-04'})['objetivos'][0]['posicion'])
if __name__=='__main__':unittest.main()
