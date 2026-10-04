import copy,hashlib,importlib.util,json,os,unittest
from pathlib import Path
from unittest.mock import patch
import titulos_urgencias_485 as T
import urgencias_observadas_api_402 as B
from probar_urgencias_observadas_api_402 import APIUrgencias402
class Titulos485(unittest.TestCase):
 def setUp(self):
  self.fx=APIUrgencias402();self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.side=self.fx.folder.parent/'titulos';self.side.mkdir(mode=0o700);self.path=self.side/'candidato.json'
  raw=json.loads(self.fx.sources['tareas'].read_text())
  for t in raw['tareas']:t['nombre']='Revisar formulario'
  self.rows=raw;self.documents=[{'id':cid,'fuentes':{'tareas':{'datos':{'carpeta_id':fid}}}} for cid,fid in [('c1','f1'),('c2','f2')]]
  self.d=T.construir(raw,self.fx.doc,self.documents,self.fx.sha,self.fx.msha,self.fx.hashes['tareas']);self.save()
  self.env=patch.dict(os.environ,{T.ENV:str(self.path)});self.env.start();self.addCleanup(self.env.stop)
 def save(self):
  b=json.dumps(self.d,allow_nan=False).encode();self.path.write_bytes(b);self.path.chmod(0o600);self.sha=hashlib.sha256(b).hexdigest()
  m={k:self.d[k] for k in ('source_sha256','source_manifest_sha256','raw_sha256')};m.update(version='485.1',lectura_no_concede_permiso=True,candidato_sha256=self.sha)
  mb=json.dumps(m).encode();(self.side/'manifest.json').write_bytes(mb);(self.side/'manifest.json').chmod(0o600);self.msha=hashlib.sha256(mb).hexdigest()
 def call(self,**kw):
  with patch.object(T,'SHA',self.sha),patch.object(T,'MANIFEST_SHA',self.msha):return self.fx.call(**kw)
 def deny(self,code=503,**kw):
  with self.assertRaises(B.ErrorUrgencias) as e:self.call(**kw)
  self.assertEqual(e.exception.codigo,code)
 def degraded(self):
  d=self.call();self.assertEqual(d['observaciones'],2);self.assertEqual(d['abiertas_en_copia'],2);self.assertEqual(d['titulos_estado'],'sin_validacion');self.assertTrue(all(r['titulo'] is None and r['titulo_fuente'] is None and r['titulo_leido_utc'] is None for r in d['filas']))
 def test_scoped_title_and_timestamp_no_private_extras(self):
  d=self.call(r='a');self.assertEqual(len(d['filas']),1);r=d['filas'][0];self.assertEqual(r['titulo'],'Revisar formulario');self.assertEqual(r['titulo_leido_utc'],r['estado_leido_utc']);self.assertEqual(r['cliente_id'],'c1');self.assertIsNone(d['urgencias_actuales']);self.assertNotIn('nombre',r);self.assertNotIn('descripcion',r)
 def test_absent_sidecar_preserves_inventory(self):
  with patch.dict(os.environ,{T.ENV:''}):d=self.call()
  self.assertEqual(d['observaciones'],2);self.assertTrue(all(r['titulo'] is None for r in d['filas']))
 def test_unknown_title_without_fabrication(self):
  self.d['filas'][0].update(titulo=None,titulo_estado='no_disponible');self.save();r=self.call()['filas'][0];self.assertIsNone(r['titulo']);self.assertIsNone(r['titulo_fuente']);self.assertIsNone(r['titulo_leido_utc'])
 def test_pins_and_source_links_fail_closed(self):
  with patch.object(T,'SHA',None):
   d=self.fx.call();self.assertEqual(d['observaciones'],2);self.assertTrue(all(r['titulo'] is None for r in d['filas']))
  original=copy.deepcopy(self.d)
  for k in ('source_sha256','source_manifest_sha256','raw_sha256'):
   self.d=copy.deepcopy(original);self.d[k]='f'*64;self.save();self.degraded()
 def test_exact_join_and_duplicate_denied(self):
  old=copy.deepcopy(self.d)
  for k,v in [('tarea_id','foreign'),('lista_id','foreign'),('cliente_id','c2'),('estado','otro'),('estado_leido_utc','2026-10-03T11:00:00Z')]:
   self.d=copy.deepcopy(old);self.d['filas'][0][k]=v;self.save();self.degraded()
  self.d=old;self.d['filas'].append(copy.deepcopy(old['filas'][0]));self.save();self.degraded()
 def test_sanitizer_contact_money_secret_html_and_urls(self):
  for unsafe in ['x@example.invalid','+34912345678','Presupuesto: 1200 EUR','password: fixture-only','https://example.invalid/path?token=fake','<script>bad()</script>']:
   s=T.titulo_seguro('Revisar '+unsafe);self.assertNotIn(unsafe,s or '')
  self.assertIsNone(T.titulo_seguro('password: fixture-only'));self.assertIsNone(T.titulo_seguro('https://example.invalid/'))
  self.assertEqual(T.titulo_seguro(' <b>Revisar</b>\n formulario '),'Revisar formulario')
 def test_no_authority_before_io(self):
  with patch.object(T,'overlay',side_effect=AssertionError('no read')):self.deny(403,r='admin')
 def test_revoke_during_final_title_io_denied(self):
  original=B._privado402;calls=0
  def leer(p,*args):
   nonlocal calls
   d=original(p,*args)
   if Path(p)==self.path:
    calls+=1
    if calls==2:self.fx.act.remove('c1')
   return d
  with patch.object(B,'_privado402',leer):self.deny(403)
 def test_pin_rotation_during_last_io_denied(self):
  original=B._privado402;calls=0
  def leer(p,*args):
   nonlocal calls
   d=original(p,*args)
   if Path(p)==self.path:
    calls+=1
    if calls==2:T.SHA='f'*64
   return d
  with patch.object(B,'_privado402',leer):self.degraded()
 def test_primary_source_rotates_during_final_title_read_denies_all(self):
  original=B._privado402;calls=0
  def leer(p,*args):
   nonlocal calls
   d=original(p,*args)
   if Path(p)==self.path:
    calls+=1
    if calls==2:self.fx.sources['tareas'].write_bytes(b'{}')
   return d
  with patch.object(B,'_privado402',leer):self.deny(503)
 def test_private_mode_symlink_fifo_rejected(self):
  self.path.chmod(0o644);self.degraded();self.path.chmod(0o600);self.path.unlink();os.mkfifo(self.path);self.degraded()
 def test_builder_refuses_ambiguous_folder_and_task(self):
  with self.assertRaises(ValueError):T.construir(self.rows,self.fx.doc,[*self.documents,self.documents[0]],self.fx.sha,self.fx.msha,'a'*64)
  raw=copy.deepcopy(self.rows);raw['tareas'].append(copy.deepcopy(raw['tareas'][0]))
  with self.assertRaises(ValueError):T.construir(raw,self.fx.doc,self.documents,self.fx.sha,self.fx.msha,'a'*64)
 def test_atomic_replay_and_changed_candidate_rejected(self):
  path=B.APP.parent/'RECUPERACION_CODEX_2026-10-03/preparar_titulos_urgencias_485.py';spec=importlib.util.spec_from_file_location('prep485',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  dest=self.fx.folder.parent/'fresh';manifest={'source_sha256':self.fx.sha,'source_manifest_sha256':self.fx.msha,'raw_sha256':self.fx.hashes['tareas']}
  self.assertFalse(m.publicar(dest,self.d,manifest)['replay']);self.assertTrue(m.publicar(dest,self.d,manifest)['replay']);bad=copy.deepcopy(self.d);bad['filas'][0]['titulo']='Otro título'
  with self.assertRaises(ValueError):m.publicar(dest,bad,manifest)
if __name__=='__main__':unittest.main()
