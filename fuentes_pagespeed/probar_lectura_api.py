import copy,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from .lectura_api import enganchar,leer_cache,proyectar,_leer
from .cliente import Cliente,guardar_cache
from .probar_pagespeed import RAW
import io

class Lectura(unittest.TestCase):
 def test_ausente_pendiente_no_cero(self):
  with tempfile.TemporaryDirectory() as t:
   d=leer_cache(Path(t).resolve()/'ausente','c','https://ejemplo.com/')
   self.assertEqual(d['estrategias']['mobile']['estado'],'pendiente');self.assertIsNone(d['estrategias']['mobile']['medicion'])
 def test_429_sin_metricas(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve()/'solo';guardar_cache(p,{'cliente_id':'c','estrategia':'mobile','intento':'2026-10-03T12:00:00Z','ok':False,'error':'cuota_o_limite','http':429})
   r=leer_cache(p,'c','https://ejemplo.com/')['estrategias']['mobile'];self.assertEqual(r['estado'],'lectura_fallida');self.assertEqual(r['http'],429);self.assertIsNone(r['medicion'])
 def test_proyeccion_privada_fecha_igual_y_ultima_buena(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve()/'solo';c=Cliente({'c':'https://ejemplo.com/'},abrir=lambda req,timeout:io.BytesIO(json.dumps(RAW).encode()));r=c.medir('c');guardar_cache(p,r)
   guardar_cache(p,{**r,'ok':False,'intento':'2026-10-04T12:00:00Z','error':'red_o_timeout'})
   doc=_leer(p,'c','mobile');doc['secreto']='SECRET';doc['medicion']['contacto']='CONTACT';doc['medicion']['laboratorio']['version']='SECRET'
   d=proyectar(doc,'c','mobile','https://ejemplo.com/');self.assertEqual(d['medicion']['fecha_medicion'],'2026-10-03T12:00:00+00:00');self.assertTrue(d['medicion_anterior']);self.assertNotIn('SECRET',json.dumps(d));self.assertNotIn('CONTACT',json.dumps(d))
 def test_identidad_web_alterada_no_exporta(self):
  doc={'cliente_id':'c','estrategia':'mobile','medicion':{'url_solicitada':'https://otro.com/','estrategia':'mobile'}}
  self.assertRaises(ValueError,proyectar,doc,'c','mobile','https://ejemplo.com/');self.assertRaises(ValueError,proyectar,doc,'otro','mobile','https://ejemplo.com/')
 def test_archivos_symlink_hardlink_tamano(self):
  for modo in ('symlink','hardlink','tamano'):
   with tempfile.TemporaryDirectory() as t:
    p=Path(t).resolve()/'solo';guardar_cache(p,{'cliente_id':'c','estrategia':'mobile','intento':'2026-10-03T12:00:00Z','ok':False,'error':'cuota_o_limite','http':429});f=next(p.glob('*.json'))
    if modo=='symlink':f.unlink();f.symlink_to(Path(t)/'otro')
    if modo=='hardlink':os.link(f,Path(t)/'otro')
    if modo=='tamano':f.write_bytes(b'x'* (128*1024+1))
    self.assertEqual(leer_cache(p,'c','https://ejemplo.com/')['estrategias']['mobile']['estado'],'cache_no_utilizable')
 def stub(self):
  class M:
   def _api_get(self,*args):return ('original',args[0])
   def responder(self,status,out):return status,out
  def contexto(p,datos):return {'cartera_ids':p.get('cartera',set())}
  def ver(p,d,cp):return {'ok':d['cliente_id'] in cp['cartera_ids']}
  S=NS(AQUI=Path('/path/no/se/lee'),E=NS(nucleo_bloqueado=False,crudo={'clientes':[{'id':'c','web':'https://ejemplo.com/'}]}),ACT=NS(es_activo_id=lambda cid:cid=='c'),P=NS(contexto=contexto,ver=ver),ve_alguno=lambda p,ms:p.get('seo',False))
  enganchar(M,S);return M(),S
 def persona(self,id='real',cartera=None,seo=True):return {'id':id,'cartera':{'c'} if cartera is None else cartera,'seo':seo}
 def test_ambos_autorizados_lectura_sin_red(self):
  m,s=self.stub()
  with patch('fuentes_pagespeed.lectura_api.leer_cache',return_value={'ok':'cache'}) as l:
   r=m._api_get('/api/pagespeed/cache',{'cliente_id':['c']},self.persona(),self.persona('vista'));self.assertEqual(r,(200,{'ok':'cache'}));self.assertEqual(l.call_count,1)
 def test_real_vista_y_puesto_ningun_fichero(self):
  for real,vista in [(self.persona(cartera=set()),self.persona('vista')),(self.persona(),self.persona('vista',set())),(self.persona(seo=False),self.persona('vista')),(self.persona(),self.persona('vista',seo=False))]:
   m,s=self.stub()
   with patch('fuentes_pagespeed.lectura_api.leer_cache') as l:
    self.assertEqual(m._api_get('/api/pagespeed/cache',{'cliente_id':['c']},real,vista)[0],403);l.assert_not_called()
 def test_inactivo_desconocido_path_query_doble(self):
  m,s=self.stub()
  for q,status in [({'cliente_id':['inactivo']},404),({'cliente_id':['../c']},404),({'cliente_id':['c','c']},400),({'cliente_id':['c'],'url':['https://otro.com']},400)]:
   with patch('fuentes_pagespeed.lectura_api.leer_cache') as l:
    self.assertEqual(m._api_get('/api/pagespeed/cache',q,self.persona(),self.persona())[0],status);l.assert_not_called()
  s.E.nucleo_bloqueado=True;self.assertEqual(m._api_get('/api/pagespeed/cache',{'cliente_id':['c']},self.persona(),self.persona())[0],503)
 def test_otra_ruta_no_intercepta(self):
  m,s=self.stub();self.assertEqual(m._api_get('/api/otra',{},self.persona(),self.persona()),('original','/api/otra'))
if __name__=='__main__':unittest.main()
