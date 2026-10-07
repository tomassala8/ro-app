import json,os,stat,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import agenda_zoom_api as Z

NOW=datetime(2026,10,3,12,tzinfo=timezone.utc)
HOST='https://us02web.zoom.us/s/123456789?zak=fixture'
JOIN='https://us02web.zoom.us/j/123456789?pwd=fixture'
E={'id':'evento-1','persona_id':'dueno','origenes':[]}

def fila(**extra):
 return {'persona_id':'dueno','leido':(NOW-timedelta(minutes=10)).isoformat(),'valido_hasta':(NOW+timedelta(hours=8)).isoformat(),'start_url':HOST,'join_url':JOIN,**extra}

class Zoom(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name).resolve();self.p=self.root/'enlaces.json'
  self.p.write_text(json.dumps({'salas':{'evento-1':fila()}}));self.p.chmod(0o600)
 def deposito(self):
  with patch.dict(os.environ,{'RO_ZOOM_ENLACES':str(self.p)}):return Z.deposito()
 def test_propietario_real_vista_y_deposito_coinciden(self):
  salas={'evento-1':fila()}
  self.assertEqual(Z.elegir(E,salas,'dueno','dueno',NOW),HOST)
  for real,vista in (('ajeno','ajeno'),('dueno','ajeno'),('ajeno','dueno'),('',''),(None,None)):
   self.assertIsNone(Z.elegir(E,salas,real,vista,NOW))
  self.assertIsNone(Z.elegir(E,{'evento-1':fila(persona_id='ajeno')},'dueno','dueno',NOW))
 def test_host_caduca_una_hora_aunque_declaren_ocho(self):
  leido=NOW-timedelta(hours=1)
  self.assertEqual(Z.elegir(E,{'evento-1':fila(leido=leido.isoformat())},'dueno','dueno',NOW),JOIN)
  self.assertEqual(Z.elegir(E,{'evento-1':fila(leido=(leido+timedelta(microseconds=1)).isoformat())},'dueno','dueno',NOW),HOST)
 def test_join_caduca_24horas_y_no_futuro_naive(self):
  for leido in (NOW-timedelta(hours=24),NOW+timedelta(microseconds=1),NOW.replace(tzinfo=None)):
   self.assertIsNone(Z.elegir(E,{'evento-1':fila(leido=leido.isoformat())},'dueno','dueno',NOW))
  self.assertEqual(Z.elegir(E,{'evento-1':fila(leido=(NOW-timedelta(hours=24)+timedelta(microseconds=1)).isoformat())},'dueno','dueno',NOW),JOIN)
  self.assertIsNone(Z.elegir(E,{'evento-1':fila()},'dueno','dueno',NOW.replace(tzinfo=None)))
 def test_expiracion_host_declarada_anterior_y_url_invalida(self):
  self.assertEqual(Z.elegir(E,{'evento-1':fila(valido_hasta=NOW.isoformat())},'dueno','dueno',NOW),JOIN)
  self.assertEqual(Z.elegir(E,{'evento-1':fila(start_url='https://evil.example/s/1')},'dueno','dueno',NOW),JOIN)
  self.assertIsNone(Z.elegir(E,{'evento-1':fila(start_url=None,join_url=None)},'dueno','dueno',NOW))
 def test_origenes_conflictivos_no_abren_sala_ambigua(self):
  e={**E,'origenes':[{'id':'otro'}]};salas={'evento-1':fila(),'otro':fila(start_url=HOST.replace('123456789','987654321'))}
  self.assertIsNone(Z.elegir(e,salas,'dueno','dueno',NOW))
  salas['otro']=fila();self.assertEqual(Z.elegir(e,salas,'dueno','dueno',NOW),HOST)
  self.assertIsNone(Z.elegir({**E,'id':{}},{},'dueno','dueno',NOW))
 def test_url_segura_no_crlf_credentials_puertos_host_falso(self):
  self.assertTrue(Z.enlace_valido(HOST));self.assertTrue(Z.enlace_valido(JOIN))
  for u in ('http://zoom.us/j/1','https://zoom.us.evil.example/j/1','https://evilzoom.us/j/1','https://fixture1@example.invalid/j/1','https://zoom.us:444/j/1','https://zoom.us/login','https://zoom.us/j/1\r\nX:fixture','https://zoom.us/j/1\t','https://zoom.us/j/1 fixture','https://zoom.us/j/a/b'):
   self.assertFalse(Z.enlace_valido(u),u)
 def test_deposito_mode600_y_json_duplicado(self):
  self.assertIn('evento-1',self.deposito())
  for mode in (0o644,0o640,0o400,0o660):
   self.p.chmod(mode);self.assertEqual(self.deposito(),{})
  self.p.chmod(0o600);self.p.write_text('{"salas":{},"salas":{"evento-1":{}}}')
  with self.assertRaises(ValueError):self.deposito()
 def test_symlink_hardlink_y_parent_symlink_no_se_leen(self):
  b=self.p.read_bytes();self.p.unlink();real=self.root/'real.json';real.write_bytes(b);real.chmod(0o600);self.p.symlink_to(real)
  self.assertEqual(self.deposito(),{});self.p.unlink();os.link(real,self.p);self.assertEqual(self.deposito(),{})
  self.p.unlink();parent=self.root/'link';parent.symlink_to(self.root,target_is_directory=True)
  with patch.dict(os.environ,{'RO_ZOOM_ENLACES':str(parent/'real.json')}):self.assertEqual(Z.deposito(),{})
 def test_owner_ajeno_tamano_y_fifo_rechazados(self):
  original=os.fstat
  def otro(fd):
   s=original(fd);return SimpleNamespace(st_mode=s.st_mode,st_nlink=s.st_nlink,st_size=s.st_size,st_uid=os.geteuid()+1)
  with patch.object(Z.os,'fstat',side_effect=otro):self.assertEqual(self.deposito(),{})
  self.p.write_bytes(b' '*2_000_001);self.assertEqual(self.deposito(),{})
  self.p.unlink();os.mkfifo(self.p,0o600);self.assertEqual(self.deposito(),{})
 def test_disponibilidad_no_expone_host_en_json_ni_vecomo(self):
  doc={'eventos':[{**E,'start_url':HOST,'atajos':[{'url':HOST}]}],'host_url':HOST}
  with patch.object(Z,'deposito',return_value={'evento-1':fila()}):
   salida=Z.disponibilidad(doc,{'id':'dueno'},{'id':'ajeno'})
  self.assertFalse(salida['eventos'][0]['zoom_privado_disponible'])
  self.assertNotIn('zak=fixture',json.dumps(salida));self.assertNotIn('start_url',json.dumps(salida))
  self.assertIn('start_url',doc['eventos'][0])
 def handler(self,nuclear=False):
  class H:
   def __init__(self):self.headers=[];self.code=None;self.json=None
   def responder(self,code,obj):self.code=code;self.json=obj;return code,obj
   def _api_get(self,*args):return 'original'
   def send_response(self,code):self.code=code
   def send_header(self,k,v):self.headers.append((k,v))
   def end_headers(self):pass
  S=SimpleNamespace(E=SimpleNamespace(nucleo_bloqueado=nuclear,crudo={}),P=SimpleNamespace(contexto=Mock(return_value={})),ve_alguno=Mock(return_value=True),modulo_recortado=Mock(return_value={'eventos':[E]}))
  Z.enganchar(H,S);return H(),S
 def test_endpoint_302_solo_dueño_sin_json_ni_seguir(self):
  h,s=self.handler()
  with patch.object(Z,'deposito',return_value={'evento-1':fila()}),patch.object(Z,'elegir',wraps=lambda e,d,r,v:Z_ORIGINAL(e,d,r,v,NOW)):
   h._api_get('/api/agenda/zoom',{'evento_id':['evento-1']},{'id':'dueno'},{'id':'dueno'})
  self.assertEqual(h.code,302);self.assertIsNone(h.json)
  self.assertIn(('Location',HOST),h.headers);self.assertIn(('Referrer-Policy','no-referrer'),h.headers)
  self.assertIn(('Cache-Control','no-store'),h.headers)
 def test_guardia_nuclear_y_ajeno_sin_leer_deposito(self):
  for nuclear,real,vista,code in ((True,'dueno','dueno',503),(False,'dueno','ajeno',403)):
   h,s=self.handler(nuclear)
   with patch.object(Z,'deposito') as d:
    self.assertEqual(h._api_get('/api/agenda/zoom',{'evento_id':['evento-1']},{'id':real},{'id':vista})[0],code)
    d.assert_not_called();s.modulo_recortado.assert_not_called()
 def test_endpoint_filtros_y_fallos_genericos(self):
  h,s=self.handler()
  for q in ({'evento_id':['evento-1','otro']},{'evento_id':['../a']},{'evento_id':['evento-1'],'otro':['x']}):
   self.assertEqual(h._api_get('/api/agenda/zoom',q,{'id':'dueno'},{'id':'dueno'})[0],400)
  with patch.object(Z,'deposito',side_effect=FileNotFoundError('privado')):
   self.assertEqual(h._api_get('/api/agenda/zoom',{'evento_id':['evento-1']},{'id':'dueno'},{'id':'dueno'})[0],404)
   self.assertNotIn('privado',json.dumps(h.json))
  self.assertEqual(h._api_get('/otra',{}, {},{}),'original')

Z_ORIGINAL=Z.elegir
if __name__=='__main__':unittest.main()
