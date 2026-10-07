import unittest
from seo_candidatos import proyectar
class Prueba(unittest.TestCase):
 def setUp(self):
  self.c={'cliente_id':'mio','tipo':'ciudad_objetivo','valor':'Madrid','fecha_estado_historico':'2026-07-22','estado':'pendiente_contraste','activar_consultas':False,'benchmark_confirmado':False,'fuentes':[{'archivo':'/privado/contrato.pdf','cuota':1470}],'razones_pendiente':['Contrastar vigencia.']}
 def test_scope_y_minimizacion(self):
  d=proyectar({'candidatos':[self.c,{**self.c,'cliente_id':'otro'}]},'mio','2026-10-03')
  self.assertEqual(len(d),1);self.assertNotIn('contrato',str(d));self.assertNotIn('1470',str(d));self.assertNotIn('otro',str(d))
 def test_nunca_confirma_ni_activa(self):
  for extra in ({'activar_consultas':True},{'benchmark_confirmado':True},{'estado':'confirmado'}):self.assertEqual(proyectar({'candidatos':[{**self.c,**extra}]},'mio','2026-10-03'),[])
  r=proyectar({'candidatos':[self.c]},'mio','2026-10-03')[0];self.assertIs(r['activar_consultas'],False);self.assertIs(r['benchmark_confirmado'],False)
 def test_tipo_fecha_texto_no_confiables(self):
  for extra in ({'tipo':'contrato'},{'tipo':[]},{'fecha_estado_historico':'ayer'},{'fecha_estado_historico':'2027-01-01'},{'valor':'persona@example.test'},{'valor':'token: secreto'},{'valor':'https://otro.es'}):self.assertEqual(proyectar({'candidatos':[{**self.c,**extra}]},'mio','2026-10-03'),[])
 def test_entrada_incompleta(self):
  for d in (None,{}, {'candidatos':[None,{},[]]}):self.assertEqual(proyectar(d,'mio','2026-10-03'),[])
if __name__=='__main__':unittest.main()
