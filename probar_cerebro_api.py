"""El endpoint conserva la puerta de cada fuente; no existe exportación de crudos."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import cerebro_api as A

class Handler:
 def _api_get(self,*args):return 'original'
 def responder(self,c,b):return c,b

class Prueba(unittest.TestCase):
 def setUp(self):
  self.leidas=[]
  self.S=SimpleNamespace(E=SimpleNamespace(nucleo_bloqueado=False,crudo={}),P=SimpleNamespace(contexto=lambda p,c:{},hoy_iso=lambda:"2026-10-03"),entrada_datos_modulo=lambda rel:{'modulos':[rel.split('/')[0]]},ve_alguno=lambda p,mods:bool(set(mods)&set(p['permiso'])),modulo_recortado=lambda real,p,cp,rel:self.leidas.append((real['id'],p['id'],rel)) or {'autorizado':p['id']})
  class H(Handler):pass
  A.enganchar(H,self.S);self.h=H()
  self.r={'id':'real','permiso':['prioridades-cliente','captacion','crm']}
  self.v={'id':'vista','permiso':['prioridades-cliente','crm']}
 def test_interseccion_antes_motor(self):
  with patch('cerebro_operativo.generar',return_value={'recomendaciones':[]}) as f:
   code,_=self.h._api_get('/api/cerebro/operativo',{},self.r,self.v)
   self.assertEqual(code,200);self.assertIsNone(f.call_args.args[0]);self.assertEqual(f.call_args.args[1],{'autorizado':'vista'});self.assertIsNone(f.call_args.args[2]);self.assertEqual(self.leidas,[('real','vista','crm/crm')])
 def test_no_ve_modulo_no_lee(self):
  self.v['permiso']=['crm'];self.assertEqual(self.h._api_get('/api/cerebro/operativo',{},self.r,self.v)[0],403);self.assertFalse(self.leidas)
 def test_bloqueado_no_lee(self):
  self.S.E.nucleo_bloqueado=True;self.assertEqual(self.h._api_get('/api/cerebro/operativo',{},self.r,self.v)[0],503);self.assertFalse(self.leidas)
 def test_filtro_extra_no_expande(self):
  self.assertEqual(self.h._api_get('/api/cerebro/operativo',{'cliente':['ajeno']},self.r,self.v)[0],400);self.assertFalse(self.leidas)
 def test_area_desconocida(self):
  self.assertEqual(self.h._api_get('/api/cerebro/operativo',{'area':['finanzas']},self.r,self.v)[0],400)
 def test_area_filtra_solo_salida(self):
  with patch('cerebro_operativo.generar',return_value={'recomendaciones':[{'area':'paid'},{'area':'crm'}]}):
   code,b=self.h._api_get('/api/cerebro/operativo',{'area':['crm']},self.r,self.v);self.assertEqual(b['recomendaciones'],[{'area':'crm'}])
 def test_otra_ruta(self):
  self.assertEqual(self.h._api_get('/api/otra',{},self.r,self.v),'original');self.assertFalse(self.leidas)

if __name__=='__main__':unittest.main()
