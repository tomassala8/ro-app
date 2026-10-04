import unittest
import permisos as P
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import cerebro_seo_api as A
class H:
 def _api_get(self,*a):return 'anterior'
 def responder(self,c,b):return c,b
class Prueba(unittest.TestCase):
 def setUp(self):
  self.p={'id':'ops','estado':'activo','puestos':['operaciones']}
  self.S=SimpleNamespace(AQUI=Path('/app'),P=P,ACT=SimpleNamespace(es_activo_id=lambda cid:cid=='mio',estado=lambda:{'activos':{'mio'}}),E=SimpleNamespace(nucleo_bloqueado=False,modulos=P.cargar_modulos(),crudo={'personas':[self.p], 'asignaciones':[], 'clientes':[{'id':'mio','web':'https://cliente.es','servicios':{'seo':'sí'}}]}),ve_alguno=lambda p,mods:any(P.nivel_modulo(p,self.S.E.modulos.get(m,{})) for m in mods),modulo_recortado=lambda *a:{'clientes':[{'cliente_id':'mio','seo_id':'empleado'}]})
  class Handler(H):pass
  A.enganchar(Handler,self.S);self.h=Handler()
 def test_fuentes_recortadas_y_servicio_confirmado(self):
  fuente={'clientes':[{'cliente_id':'mio','servicios':{'seo':'sí'},'leida':'2026-10-03','cuota':1470},{'cliente_id':'ajeno','servicios':{'seo':'sí'}},{'cliente_id':'sinservicio','servicios':{}}]}
  with patch.object(A,'leer',side_effect=[fuente,{'clientes':[]},{}]),patch.object(A,'cargar_local',return_value={'habilitado':False}) as motor:
   c,d=self.h._api_get('/api/cerebro/seo',{},self.p,self.p)
   self.assertEqual(c,200);self.assertEqual([r['cliente_id'] for r in d['recomendaciones']],['mio']);self.assertEqual(motor.call_count,1)
   self.assertNotIn('cuota',str(d));self.assertNotIn('ajeno',str(d));self.assertEqual(motor.call_args.args[1]['ciudades_verificadas'],[])
 def test_historico_scoped_no_confirma_contexto(self):
  fuente={'clientes':[{'cliente_id':'mio','servicios':{'seo':'sí'},'leida':'2026-10-03'}]}
  c={'cliente_id':'mio','tipo':'ciudad_objetivo','valor':'Madrid','fecha_estado_historico':'2026-07-22','estado':'pendiente_contraste','activar_consultas':False,'benchmark_confirmado':False}
  candidatos={'candidatos':[c,{**c,'cliente_id':'otro','valor':'OtraCiudad'}]}
  with patch.object(A,'leer',side_effect=[fuente,{'clientes':[]},candidatos]),patch.object(A,'cargar_local',return_value={'habilitado':False}) as motor:
   d=A.generar(self.S,self.p,self.p)
   self.assertEqual(motor.call_args.args[1]['ciudades_verificadas'],[])
   self.assertIn('Histórico pendiente de contraste',str(d['recomendaciones']))
   self.assertIn('2026-07-22',str(d));self.assertNotIn('OtraCiudad',str(d))
   self.assertIs(d['clientes'][0]['objetivos_historicos'][0]['activar_consultas'],False)
 def test_no_ver_seo_no_lee(self):
  with patch.object(A,'generar') as g:
   self.assertEqual(self.h._api_get('/api/cerebro/seo',{},self.p,{'modulos':['prioridades-cliente']})[0],403);g.assert_not_called()
 def test_actor_y_vista(self):
  with patch.object(A,'generar') as g:
   self.assertEqual(self.h._api_get('/api/cerebro/seo',{}, {'modulos':['seo-web']},self.p)[0],403);g.assert_not_called()
 def test_extra_no_expande(self):
  self.assertEqual(self.h._api_get('/api/cerebro/seo',{'cliente':['ajeno']},self.p,self.p)[0],400)
 def test_bloqueo(self):
  self.S.E.nucleo_bloqueado=True;self.assertEqual(self.h._api_get('/api/cerebro/seo',{},self.p,self.p)[0],503)
 def test_puerta_cliente_antes_de_motor(self):
  fuente={'clientes':[{'cliente_id':'mio','servicios':{'seo':'sí'}}]}
  orig=P.ver
  def ver(p,d,cp):return {'ok':False} if d.get('tipo')=='cliente_detalle' else orig(p,d,cp)
  with patch.object(P,'ver',ver),patch.object(A,'leer',side_effect=[fuente,{'clientes':[]},{}]),patch.object(A,'cargar_local') as motor:
   self.assertEqual(A.generar(self.S,self.p,self.p)['clientes'],[])
   motor.assert_not_called()
 def test_cliente_fuera_nucleo_actual_no_lee(self):
  self.S.E.crudo['clientes']=[]
  fuente={'clientes':[{'cliente_id':'mio','servicios':{'seo':'sí'}}]}
  with patch.object(A,'leer',side_effect=[fuente,{'clientes':[]},{}]),patch.object(A,'cargar_local') as motor:
   self.assertEqual(A.generar(self.S,self.p,self.p)['clientes'],[])
   motor.assert_not_called()
 def test_url_privada_no_sale(self):
  url=A.url_publica('https://persona:fixture1@example.invalid/pagina?email=persona@example.org#secreto','https://cliente.es')
  self.assertEqual(url,'https://www.cliente.es/pagina')
 def test_otras_propiedades_y_esquemas_denegados(self):
  for url in ('https://cliente.es.evil.org/p','https://evilcliente.es/p','https://otro.cliente.es/p','javascript:alert(1)','https://cliente.es:8765/p','https://evil.org/?url=https://cliente.es'):
   self.assertIsNone(A.url_publica(url,'https://cliente.es'))
  self.assertIsNone(A.url_publica('https://cliente.es/p',None))
 def test_saneado_conserva_medicion_y_elimina_pagina_ajena(self):
  d={'habilitado':True,'objetivos':[{'posicion':3,'url_o_ficha':'https://cliente.es/?token=secreto'}], 'prioridades':[{'tipo':'revisar_pagina','url':'https://cliente.es/a?q=privado'}, {'tipo':'revisar_pagina','url':'https://evil.org/a'}, {'tipo':'revisar_posicion','evidencia':{'url_o_ficha':'https://evil.org/ficha','posicion':4}}]}
  resultado=A.sanear_urls(d,'https://www.cliente.es')
  self.assertEqual(resultado['objetivos'][0],{'posicion':3,'url_o_ficha':'https://cliente.es/'})
  self.assertEqual(len(resultado['prioridades']),2)
  self.assertEqual(resultado['prioridades'][0]['url'],'https://cliente.es/a')
  self.assertIsNone(resultado['prioridades'][1]['evidencia']['url_o_ficha'])
  self.assertEqual(resultado['prioridades'][1]['evidencia']['posicion'],4)
 def test_otra(self):self.assertEqual(self.h._api_get('/api/otra',{},self.p,self.p),'anterior')
if __name__=='__main__':unittest.main()
