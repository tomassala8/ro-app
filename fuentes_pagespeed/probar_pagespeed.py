import io,json,tempfile,unittest,urllib.error,os
from pathlib import Path
from fuentes_pagespeed.cliente import Cliente,normalizar,guardar_cache,url_publica,MAX_BYTES

RAW={'analysisUTCTimestamp':'2026-10-03T12:00:00Z','lighthouseResult':{'requestedUrl':'https://ejemplo.com/','finalUrl':'https://ejemplo.com/', 'lighthouseVersion':'13.0', 'categories':{'performance':{'score':.7}},'audits':{'largest-contentful-paint':{'numericValue':2200},'cumulative-layout-shift':{'numericValue':.03},'screenshot':{'data':'privado'}},'fullPageScreenshot':{'secret':'never'}}}
class TestPS(unittest.TestCase):
 def cliente(self,raw=RAW):return Cliente({'cliente':'https://ejemplo.com/'},abrir=lambda req,timeout:io.BytesIO(json.dumps(raw).encode()))
 def test_normaliza_sin_artefactos(self):
  r=self.cliente().medir('cliente');self.assertTrue(r['ok']);d=r['medicion'];self.assertEqual(d['laboratorio']['performance'],70);self.assertIsNone(d['laboratorio']['metricas']['fcp_ms']);self.assertEqual(d['campo_url']['estado'],'sin_dato');self.assertNotIn('screenshot',json.dumps(d));self.assertNotIn('never',json.dumps(d))
 def test_scope_no_request(self):
  c=self.cliente();self.assertRaises(PermissionError,c.medir,'otra');self.assertRaises(ValueError,c.medir,'cliente','tablet')
 def test_error_sin_filtrar_secretos(self):
  def fail(req,timeout):raise urllib.error.HTTPError(req.full_url,429,'SECRET_KEY',{},None)
  d=Cliente({'cliente':'https://ejemplo.com/'},clave='SECRET_KEY',abrir=fail).medir('cliente');self.assertEqual(d['error'],'cuota_o_limite');self.assertNotIn('SECRET',json.dumps(d))
 def test_url_privada_credenciales(self):
  for u in ['https://localhost/','https://127.0.0.1/','https://10.0.0.1/','https://foo.local/','http://ejemplo.com','https://a:b@ejemplo.com','https://ejemplo.com/?email=x','https://ejemplo.com/#a']:
   with self.subTest(u=u):self.assertRaises(ValueError,url_publica,u)
 def test_error_runtime_fecha_score(self):
  for change in ({'runtimeError':{'message':'x'}},{'categories':{}},{'categories':{'performance':{'score':True}}}):
   raw={**RAW,'lighthouseResult':{**RAW['lighthouseResult'],**change}};self.assertFalse(self.cliente(raw).medir('cliente')['ok'])
  raw={**RAW,'analysisUTCTimestamp':'not_a_date'};self.assertFalse(self.cliente(raw).medir('cliente')['ok'])
 def test_cache_fallo_preserva_medicion_privacidad(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'solo';ok=self.cliente().medir('cliente');guardar_cache(p,ok)
   bad={**ok,'ok':False,'medicion':None,'error':'red_o_timeout','intento':'2026-10-04T12:00:00+00:00'}
   out=guardar_cache(p,bad);self.assertEqual(out['medicion']['fecha_medicion'],'2026-10-03T12:00:00+00:00');self.assertFalse(out['ultimo_intento_ok']);self.assertEqual(p.stat().st_mode&0o777,0o700);self.assertEqual(next(p.glob('*.json')).stat().st_mode&0o777,0o600)
 def test_cache_cambio_url_no_resucita_otra(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'solo';ok=self.cliente().medir('cliente');guardar_cache(p,ok)
   out=guardar_cache(p,{**ok,'ok':False,'url_solicitada':'https://otra.com/','error':'red_o_timeout'})
   self.assertIsNone(out['medicion'])
 def test_estrategia_respuesta_distinta(self):
  raw={**RAW,'lighthouseResult':{**RAW['lighthouseResult'],'configSettings':{'formFactor':'desktop'}}}
  self.assertFalse(self.cliente(raw).medir('cliente','mobile')['ok'])
 def test_cache_rechaza_symlink_y_hardlink(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'solo';ok=self.cliente().medir('cliente');guardar_cache(p,ok);f=next(p.glob('*.json'))
   os.link(f,Path(t)/'link');self.assertRaises(ValueError,guardar_cache,p,ok)
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'solo';ok=self.cliente().medir('cliente');guardar_cache(p,ok);f=next(p.glob('*.json'));f.unlink();f.symlink_to(Path(t)/'otra');self.assertRaises(ValueError,guardar_cache,p,ok)
 def test_bounded_read(self):
  c=Cliente({'cliente':'https://ejemplo.com/'},abrir=lambda req,timeout:io.BytesIO(b' '* (MAX_BYTES+1)));self.assertFalse(c.medir('cliente')['ok'])
 def test_redirect_no_reasigna(self):
  raw={**RAW,'lighthouseResult':{**RAW['lighthouseResult'],'finalUrl':'https://otro.com/'}};d=self.cliente(raw).medir('cliente');self.assertEqual(d['cliente_id'],'cliente');self.assertTrue(d['medicion']['redireccion_otro_dominio'])
 def test_crux_url_origen_separados(self):
  raw={**RAW,'originLoadingExperience':{'metrics':{'LARGEST_CONTENTFUL_PAINT_MS':{'percentile':3100}}}};d=self.cliente(raw).medir('cliente')['medicion'];self.assertEqual(d['campo_url']['estado'],'sin_dato');self.assertEqual(d['campo_origen']['metricas']['lcp_ms'],3100)
if __name__=='__main__':unittest.main()
