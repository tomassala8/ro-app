"""Fuente privada temporal y guardias reales204; sin fuentes/DB/proveedores reales."""
import json,os,unittest,copy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from documento_privado_222 import DocumentoPrivado
import mi_trabajo as M
import probar_identidades_clickup_204 as fixtures

class Fuente(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'tareas.json';self.cache=DocumentoPrivado()
 def write(self,d):
  t=self.path.with_suffix('.tmp');t.write_text(json.dumps(d));os.replace(t,self.path)
 def test_one_parse_per_version_and_no_deepcopy_12k_rows(self):
  self.write({'tareas':[{'id':str(i),'checklists':[],'descripcion':'Fixture '*100} for i in range(12000)]})
  with patch.object(self.cache,'cargar',wraps=self.cache.cargar) as read:
   d=self.cache.leer(self.path)
   for _ in range(100):self.assertIs(self.cache.leer(self.path),d)
   self.assertEqual(read.call_count,1)
  self.assertEqual(len(d['tareas']),12000)
 def test_same_mtime_atomic_replace_refresh_full_metadata(self):
  self.write({'tareas':[{'id':'x','estado':'one','checklists':[{'id':'old'}]}]});d=self.cache.leer(self.path);st=self.path.stat()
  self.write({'tareas':[{'id':'x','estado':'two','checklists':[{'id':'new'}]}]});os.utime(self.path,ns=(st.st_atime_ns,st.st_mtime_ns))
  e=self.cache.leer(self.path);self.assertIsNot(e,d);self.assertEqual(e['tareas'][0]['checklists'][0]['id'],'new')
 def test_same_inode_same_size_mtime_refresh_ctime(self):
  self.write({'tareas':[{'id':'x','estado':'one'}]});self.cache.leer(self.path);st=self.path.stat();text=self.path.read_text();self.path.write_text(text.replace('one','two'));os.utime(self.path,ns=(st.st_atime_ns,st.st_mtime_ns))
  self.assertEqual(self.cache.leer(self.path)['tareas'][0]['estado'],'two')
 def test_invalid_missing_and_unreadable_never_old_fallback(self):
  self.write({'tareas':[{'id':'old'}]});self.cache.leer(self.path);self.path.write_text('{bad');self.assertEqual(self.cache.leer(self.path),{})
  self.path.unlink();self.assertEqual(self.cache.leer(self.path),{})
  self.write({'tareas':[{'id':'new'}]})
  with patch.object(Path,'read_text',side_effect=OSError):self.assertEqual(self.cache.leer(self.path),{})
 def test_transient_read_failure_can_recover_same_version(self):
  self.write({'tareas':[{'id':'available'}]})
  with patch.object(Path,'read_text',side_effect=OSError):self.assertEqual(self.cache.leer(self.path),{})
  self.assertEqual(self.cache.leer(self.path)['tareas'][0]['id'],'available')
 def test_change_during_read_retries_before_publish(self):
  self.write({'tareas':[{'id':'old'}]});calls=[];original=self.cache.cargar
  def race(p):
   d=original(p)
   if not calls:calls.append(1);self.write({'tareas':[{'id':'new'}]})
   return d
  with patch.object(self.cache,'cargar',side_effect=race):self.assertEqual(self.cache.leer(self.path)['tareas'][0]['id'],'new')
 def test_persistent_race_bounded_and_recovery(self):
  self.write({'tareas':[{'id':'old'}]});n=[]
  def race(p):n.append(1);self.write({'tareas':[{'id':str(len(n))}]});return {'tareas':[{'id':'obsolete'}]}
  with patch.object(self.cache,'cargar',side_effect=race):self.assertEqual(self.cache.leer(self.path),{});self.assertEqual(len(n),2)
  self.assertEqual(self.cache.leer(self.path)['tareas'][0]['id'],'2')
 def test_concurrent_initial_requests_share_document_once(self):
  self.write({'tareas':[{'id':'x','checklists':[]}]})
  with patch.object(self.cache,'cargar',wraps=self.cache.cargar) as read:
   with ThreadPoolExecutor(max_workers=8) as pool:docs=list(pool.map(lambda _:self.cache.leer(self.path),range(100)))
   self.assertEqual(read.call_count,1);self.assertTrue(all(d is docs[0] for d in docs))
 def test_namespace_change_no_data_from_previous_path(self):
  self.write({'tareas':[{'id':'old'}]});self.cache.leer(self.path);other=self.path.with_name('other.json');other.write_text('{"tareas": []}')
  self.assertEqual(self.cache.leer(other),{'tareas':[]});self.assertEqual(self.cache.leer(self.path)['tareas'][0]['id'],'old')

class Autoridad(unittest.TestCase):
 setUp=fixtures.Guardia204.setUp
 write=fixtures.Guardia204.write
 def setUp(self):
  fixtures.Guardia204.setUp(self)
  p=patch.object(M,'_RAW_TAREAS_222',DocumentoPrivado());p.start();self.addCleanup(p.stop)
 def test_personas_roles_client_permission_revoked_without_source_version_change(self):
  with patch.object(M._RAW_TAREAS_222,'cargar',wraps=M._RAW_TAREAS_222.cargar) as load:
   self.assertEqual(M.tarea_para_accion(self.p,'task-fixture'),self.row)
   self.p['correo']='otra@example.invalid'
   with self.assertRaises(PermissionError):M.tarea_para_accion(self.p,'task-fixture')
   self.p['correo']='owner@example.invalid';self.permission=False
   with self.assertRaises(PermissionError):M.tarea_para_accion(self.ops,'task-fixture')
   self.permission=True;self.p['estado']='baja'
   with self.assertRaises(PermissionError):M.tarea_para_accion(self.p,'task-fixture')
   self.assertEqual(load.call_count,1)
 def test_members_folder_config_and_assignment_still_read_current(self):
  self.assertEqual(M.tarea_para_accion(self.p,'task-fixture'),self.row)
  self.users[0]['email']='otra@example.invalid';self.write(self.root/'panel/_crudo/clickup/miembros.json',{'miembros':self.users})
  with self.assertRaises(PermissionError):M.tarea_para_accion(self.p,'task-fixture')
  self.users[0]['email']='owner@example.invalid';self.write(self.root/'panel/_crudo/clickup/miembros.json',{'miembros':self.users})
  self.write(self.root/'data/clientes/client-fixture.json',{'id':'client-fixture','fuentes':{'tareas':{'datos':{'carpeta_id':'OTHER'}}}})
  with self.assertRaises(ValueError):M.tarea_para_accion(self.ops,'task-fixture')
 def test_fresh_indices_per_request_preserve_shared_readonly_document(self):
  a=M._fuente_autorizacion_tareas();b=M._fuente_autorizacion_tareas();self.assertIsNot(a,b);self.assertIsNot(a['identidades'],b['identidades']);self.assertIsNot(a['personas'],b['personas'])
  self.assertIs(a['tareas']['task-fixture'][0],b['tareas']['task-fixture'][0])
  original=copy.deepcopy(a['tareas']['task-fixture'][0]);a['identidades'].clear()
  self.assertEqual(M._fuente_autorizacion_tareas()['identidades'],{'cu-owner':'owner'});self.assertEqual(b['tareas']['task-fixture'][0],original)

if __name__=='__main__':unittest.main()
