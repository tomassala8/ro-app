import ast, copy, json, os, tempfile, threading, types, unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import escaner_secretos as ESC

SRC=Path(__file__).parent/'servir.py'
class Secretos567(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.root=Path(self.t.name); self.data=self.root/'data'; self.data.mkdir()
  self.f=self.data/'modulo'/'doc.json'; self.f.parent.mkdir()
  self.e=types.SimpleNamespace(bloqueados={},nucleo_bloqueado=False)
  names={'_estado_fichero','DatoRoto','DatoSecreto','_lectura_secreta_actual','leer_json_bueno'}
  tree=ast.parse(SRC.read_text()); nodes=[copy.deepcopy(n) for n in tree.body if getattr(n,'name',None) in names]
  self.ns=dict(AQUI=self.root,ESC=ESC,E=self.e,NUCLEO=['personas'],json=json,datetime=datetime,
   _ULTIMO_BUENO={},_CANDADO_BUENO=threading.Lock(),CANDADO=threading.RLock())
  exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'lector_actual567','exec'),self.ns)
  self.p1=patch.object(ESC,'AQUI',self.root);self.p2=patch.object(ESC,'DATA',self.data);self.p1.start();self.p2.start()
 def tearDown(self):self.p2.stop();self.p1.stop();self.t.cleanup()
 def write(self,d):self.f.write_text(json.dumps(d))
 def read(self):return self.ns['leer_json_bueno'](self.f)
 def test_limpio_secreto_limpio_sin_fallback(self):
  self.write({'texto':'seguro'}); self.assertEqual(self.read()[0],{'texto':'seguro'})
  self.write({'password':'SyntheticSecret123'})
  with self.assertRaises(self.ns['DatoSecreto']):self.read()
  self.assertIn('data/modulo/doc.json',self.e.bloqueados)
  self.assertEqual(next(iter(self.ns['_ULTIMO_BUENO'].values()))[1],{'texto':'seguro'})
  self.write({'texto':'limpio'}); self.assertEqual(self.read()[0],{'texto':'limpio'});self.assertFalse(self.e.bloqueados)
 def test_mismo_mtime_tamano_no_bypass(self):
  good=json.dumps({'texto':'z'*24}); bad=json.dumps({'password':'Synthet1cSecret!'})
  good=good+' '*(max(len(good),len(bad))-len(good));bad=bad+' '*(len(good)-len(bad))
  self.f.write_text(good);self.read();st=self.f.stat();self.f.write_text(bad);os.utime(self.f,ns=(st.st_atime_ns,st.st_mtime_ns))
  self.assertEqual(self.f.stat().st_size,st.st_size)
  with self.assertRaises(self.ns['DatoSecreto']):self.read()
 def test_permitidos_ruta_real_y_retiro(self):
  value='bearer SyntheticToken123456789012345'
  pol=self.root/'escaner_permitidos.json';pol.write_text(json.dumps({'data/modulo/doc.json':[value]}))
  self.write({'texto':value});self.assertEqual(self.read()[0]['texto'],value)
  pol.write_text('{}')
  with self.assertRaises(self.ns['DatoSecreto']):self.read()
 def test_politica_corrupta_no_fallback(self):
  self.write({'texto':'bien'});self.read();(self.root/'escaner_permitidos.json').write_text('{')
  with self.assertRaises(self.ns['DatoSecreto']):self.read()
 def test_rotura_sin_secreto_conserva_ultimo_valido(self):
  self.write({'texto':'bien'});self.read();self.f.write_text('{')
  d,av=self.read();self.assertEqual(d,{'texto':'bien'});self.assertIsNotNone(av)
  self.f.write_text('{"texto":"bearer SyntheticToken123456789012345"')
  with self.assertRaises(self.ns['DatoSecreto']):self.read()
 def test_correos_ro_excepcion_original(self):
  self.f=self.data/'personas.json';self.write([{'correo':'fixture1@rankingonline.com'}]);self.assertIsNone(self.read()[1])
  self.write([{'texto':'fixture1@rankingonline.com'}])
  with self.assertRaises(self.ns['DatoSecreto']):self.read()
 def test_version_estable_no_repite_scanner_y_cambio_si(self):
  self.write({'texto':'bien'})
  with patch.object(ESC,'escanear_fichero',wraps=ESC.escanear_fichero) as scan:
   self.read();self.read();self.assertEqual(scan.call_count,1)
   self.write({'texto':'otro'});self.read();self.assertEqual(scan.call_count,2)
 def test_rotacion_durante_lectura_no_publica_version_inestable(self):
  self.write({'texto':'bien'})
  original=Path.read_text
  def leer(path,*a,**kw):
   texto=original(path,*a,**kw)
   if path==self.f:
    path.write_text(texto+' ')
   return texto
  with patch.object(Path,'read_text',leer):
   with self.assertRaises(self.ns['DatoSecreto']):self.read()
  self.assertFalse(self.ns['_ULTIMO_BUENO'])
 def test_get_cache_primero_escanea_y_bloqueo_no_cortocircuita(self):
  # El endpoint conserva ahora las puertas canónicas 581. Se cargan las
  # dependencias reales sobre cartera/ACT ficticios, sin neutralizar la puerta.
  import probar_puertas_cliente_581 as G
  fixture=G.Puertas581();fixture.setUp()
  try:
   ns=fixture.f.ns
   fixture.f.data=fixture.f.data.resolve()
   ns["DATA"]=fixture.f.data
   root=fixture.f.data.parent
   tree=ast.parse(SRC.read_text())
   names={'_estado_fichero','DatoRoto','DatoSecreto','_lectura_secreta_actual','leer_json_bueno'}
   nodes=[copy.deepcopy(n) for n in tree.body if getattr(n,'name',None) in names]
   ns.update(AQUI=root,ESC=ESC,datetime=datetime,_ULTIMO_BUENO={},
             _CANDADO_BUENO=threading.Lock(),CANDADO=threading.RLock())
   ns['E'].bloqueados={}
   exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'lector_actual567','exec'),ns)
   class Cache:
    def __init__(self):self.d={}
    def leer(self,k):return self.d.get(k)
    def guardar(self,k,v):self.d[k]=v
   ns.update(CACHE_RESP=Cache(),etag_de=lambda *a:'sintetico',
             responder_de_memoria=lambda h,d:h.responder(200,json.loads(d['cuerpo'])))
   rel='paneles/ga4/cid-own'
   get=lambda:fixture.f.get('/api/modulo/'+rel)
   with patch.object(ESC,'AQUI',root),patch.object(ESC,'DATA',fixture.f.data):
    fixture.f.write(rel,{'texto':'bien'})
    self.assertEqual(get()[0],200);self.assertEqual(get()[0],200)
    self.assertTrue(ns['CACHE_RESP'].d, 'la segunda lectura debe comprobar una caché real')
    fixture.f.write(rel,{'password':'SyntheticSecret123'})
    self.assertEqual(get()[0],503)
    fixture.f.write(rel,{'texto':'limpio'})
    self.assertEqual(get(),(200,{'texto':'limpio'}));self.assertFalse(ns['E'].bloqueados)
  finally:fixture.tearDown()
if __name__=='__main__':unittest.main()
