"""376B auditoría independiente. Sólo fixtures y depósitos temporales."""
import copy,datetime as dt,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import agrupaciones_tarea_api_376 as M
from fuentes_horas.deposito_agrupaciones_376 import construir
from probar_agrupaciones_tarea_376 import fixture,evidence,server,NOW
class Independiente(unittest.TestCase):
 def project(self,d,ev=None,personas=None,clientes=None):
  return M.proyectar(d,['b'] if personas is None else personas,['c1'] if clientes is None else clientes,evidence() if ev is None else ev,NOW)
 def test_collision_global_foreign_and_invalid(self):
  f=fixture();hs={'meta':{'generado':f['leido']},'entradas':copy.deepcopy(f['entradas'])};ts={'tareas':f['tareas']}
  for change in ({'usuario_id':'999'},{'task_id':'foreign'},{'usuario_id':True},{'horas':'9'}):
   rows=copy.deepcopy(hs);rows['entradas'].append({**rows['entradas'][0],**change})
   d=construir(rows,ts,{'f1':('c1','Fixture')},{'1':'b'},[],NOW)
   self.assertNotIn('e0',[e['id'] for e in d['entradas']]);self.assertEqual(d['diagnostico']['entrada_colision_o_invalida'],1)
 def test_uid_int_string_alias_is_canonical_replay(self):
  f=fixture();rows=copy.deepcopy(f['entradas']);rows.append({**rows[0],'usuario_id':1})
  d=construir({'meta':{'generado':f['leido']},'entradas':rows},{'tareas':f['tareas']},{'f1':('c1','Fixture')},{'1':'b'},[],NOW)
  self.assertEqual(len(d['entradas']),6);self.assertEqual(d['diagnostico']['replays_eliminados'],1)
  rows[-1]['usuario_id']='01';d=construir({'meta':{'generado':f['leido']},'entradas':rows},{'tareas':f['tareas']},{'f1':('c1','Fixture')},{'1':'b'},[],NOW);self.assertEqual(len(d['entradas']),5)
 def test_minimum_after_person_and_client_scope_no_ids(self):
  d=fixture();d['identidades']['2']='a'
  for e in d['entradas'][4:]:e['usuario_id']='2'
  self.assertEqual(self.project(d)['filas'],[])
  self.assertEqual(self.project(fixture(),clientes=[])['filas'],[])
  r=self.project(fixture())['filas'][0];self.assertEqual(set(r),{'grupo','casos','mediana_h','max_h','total_h','registros_mas10h'})
 def test_uid_folder_changed_prior_to_read(self):
  for k,v in [('identidades',{'1':'a','2':'a'}),('carpetas',{'f1':('other','other')})]:
   ev=evidence();ev[k]=v;self.assertEqual(self.project(fixture(),ev=ev)['filas'],[])
 def test_protected_groups_and_unknown_fields(self):
  for title in ['password=fixture-secret','correo fixture@example.invalid','https://fixture.invalid/?token=fixture-secret']:
   d=fixture();d['tareas'][0]['nombre']=title
   with self.assertRaises(ValueError):self.project(d)
  d=fixture();d['tareas'][0]['descripcion']='not for output'
  with self.assertRaises(ValueError):self.project(d)
 def test_scope_revoked_during_final_evidence_read(self):
  for change in [lambda S:S.E.crudo['personas'][0].update(estado='baja'),lambda S:setattr(S.ACT,'es_activo_id',lambda cid:False),lambda S:setattr(S,'ve_alguno',lambda p,m:None)]:
   S=server();n=[0]
   def ev(_):
    n[0]+=1
    if n[0]==2:change(S)
    return evidence()
   with patch.object(M,'cargar',return_value=(fixture(),{})),patch.object(M,'evidencia_actual',side_effect=ev):
    with self.assertRaises(M.ErrorAgrupaciones) as caught:M.listar(S,'a','a',path='/synthetic',ahora=NOW)
   self.assertEqual(caught.exception.codigo,403)
 def test_final_uid_or_folder_change(self):
  for key,new in [('identidades',{'1':'a'}),('carpetas',{'f1':('other','other')})]:
   second=evidence();second[key]=new;second['firma']='changed'
   with patch.object(M,'cargar',return_value=(fixture(),{})),patch.object(M,'evidencia_actual',side_effect=[evidence(),second]):
    with self.assertRaises(M.ErrorAgrupaciones) as caught:M.listar(server(),'a','a',path='/synthetic',ahora=NOW)
   self.assertEqual(caught.exception.codigo,403)
 def test_pins_regular_private_and_ancestor_symlink(self):
  d=fixture();raw=json.dumps(d).encode();sha=hashlib.sha256(raw).hexdigest();manifest={'version':'376.1','output_sha256':sha,'sin_promover':True,'proveedores_consultados':0,'dedup_global_antes_scope':True};mraw=json.dumps(manifest).encode()
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();dep=root/'dep';dep.mkdir(mode=0o700)
   for name,b in [('candidato.json',raw),('manifest.json',mraw)]:p=dep/name;p.write_bytes(b);p.chmod(0o600)
   with patch.object(M,'SHA',sha),patch.object(M,'MANIFEST_SHA',hashlib.sha256(mraw).hexdigest()):
    self.assertEqual(M.cargar(dep/'candidato.json')[0]['version'],'376.1')
    alias=root/'alias';alias.symlink_to(dep,target_is_directory=True)
    with self.assertRaises(OSError):M.cargar(alias/'candidato.json')
    (dep/'candidato.json').write_bytes(raw+b' ')
    with self.assertRaises(ValueError):M.cargar(dep/'candidato.json')
 def test_rotation_between_identity_reads_is_controlled(self):
  S=server();original=M.ambito_personas
  def rotate(*args):
   result=original(*args);S.E.crudo['personas']=S.E.crudo['personas'][1:];return result
  with patch.object(M,'ambito_personas',side_effect=rotate):
   with self.assertRaises(M.ErrorAgrupaciones) as caught:M._ambito(S,'a','a')
  self.assertEqual(caught.exception.codigo,403)
 def test_source_fifo_rejected_without_blocking_open(self):
  with tempfile.TemporaryDirectory() as tmp:
   fifo=Path(tmp)/'fifo';os.mkfifo(fifo,0o600);original=os.open
   def guarded(path,flags,*args,**kwargs):
    if Path(path)==fifo and not flags&os.O_NONBLOCK:raise AssertionError('open bloqueante antes de fstat')
    return original(path,flags,*args,**kwargs)
   for reader in (M._leer_fuente,M._hash_fuente):
    with patch.object(M.os,'open',side_effect=guarded):
     with self.assertRaises((ValueError,OSError)):reader(fifo)
 def test_source_leaf_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'actual').write_text('{}');(p/'link').symlink_to(p/'actual')
   with self.assertRaises(OSError):M._leer_fuente(p/'link')
if __name__=='__main__':unittest.main()
