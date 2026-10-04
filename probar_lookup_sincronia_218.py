"""Lookup real con JSON temporales, sin DB/proveedor/servidor."""
import unittest,json,copy,os,threading
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import sincronia as X

class Lookup(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  for c in ('produccion','mi_trabajo'):(self.root/c).mkdir()
  p=patch.object(X,'DATA',self.root);p.start();self.addCleanup(p.stop)
  for name,value in [('_DOCUMENTOS_TAREA',{}),('_INDICE_TAREA',{'documentos':None,'por_id':{}}),('_MT',{'mtime':None,'doc':{},'por_id':{}})]:
   p=patch.object(X,name,value);p.start();self.addCleanup(p.stop)
  self.prod={'generado':'P-source','cola':[{'id':'shared','tarea':'First','estado':'cola','cli':None,'persona_id':'a'},{'id':'shared','tarea':'Other','estado':'other','cli':'wrong','persona_id':'b'}], 'revisiones':[{'id':'shared','tarea':'Review','estado':'review','cliente_id':'client'}, {'id':'shared','estado':'','cliente_id':'different'}, {'id':'only-review','estado':'review','cliente_id':'c'}]}
  self.mi={'generado':'MI-source','tareas':[{'id':'shared','tarea':'Ignored','estado':'MI','cli':'wrong','persona_id':'other','vence':'first','lista_id':'first'},{'id':'shared','vence':'last','lista_id':'last','persona_id':'last'}, {'id':'mi','tarea':'MI-first','estado':'active','cli':'c','persona_id':'p'},{'id':'mi','tarea':'MI-second','estado':'other','cli':'wrong','persona_id':'q','vence':None,'lista_id':'l'}], 'estados_lista':{'last':['review']}}
  self.write('produccion',self.prod);self.write('mi_trabajo',self.mi)
 def write(self,slot,doc):
  p=self.root/slot/(slot+'.json');t=p.with_suffix('.tmp');t.write_text(json.dumps(doc));os.replace(t,p)
 def old(self,ref):
  ref=str(ref or '');d=self.prod;out=None
  for r in d.get('cola') or []:
   if isinstance(r,dict) and str(r.get('id'))==ref:
    out=out or {'id':ref,'nombre':r.get('tarea'),'estado':r.get('estado'),'cli':r.get('cli'),'autores':set()};out['autores'].add(r.get('persona_id'))
  for r in d.get('revisiones') or []:
   if isinstance(r,dict) and str(r.get('id'))==ref:
    out=out or {'id':ref,'nombre':r.get('tarea'),'estado':r.get('estado'),'cli':r.get('cliente_id'),'autores':set()};out['estado']=r.get('estado') or out['estado'];out['cli']=out['cli'] or r.get('cliente_id')
  if not out:
   for r in self.mi.get('tareas') or []:
    if isinstance(r,dict) and str(r.get('id'))==ref:
     out=out or {'id':ref,'nombre':r.get('tarea'),'estado':r.get('estado'),'cli':r.get('cli'),'autores':set()};out['autores'].add(r.get('persona_id'))
   if out:out['visto']=self.mi.get('generado')
  else:out['visto']=d.get('generado')
  mt=next((r for r in reversed(self.mi.get('tareas') or []) if isinstance(r,dict) and str(r.get('id'))==ref),None)
  if out and mt:out['vence']=mt.get('vence');out['lista_id']=mt.get('lista_id')
  return out
 def test_priority_contradictions_authors_lastMI_and_reference_shapes_identical(self):
  self.prod['cola'] += [{'id':None,'tarea':'N','persona_id':None},{'id':0,'tarea':'Zero','persona_id':'p'},'ignored']
  self.write('produccion',self.prod)
  for ref in ('shared','only-review','mi','unknown','None','0',0,None):self.assertEqual(X.tarea(ref),self.old(ref))
  self.assertEqual(X.tarea('shared')['autores'],{'a','b'});self.assertEqual(X.tarea('shared')['estado'],'review');self.assertEqual(X.tarea('shared')['lista_id'],'last')
 def test_caller_cannot_mutate_cached_authors_or_metadata(self):
  t=X.tarea('shared');t['autores'].add('intruder');t['cli']='foreign'
  self.assertEqual(X.tarea('shared'),self.old('shared'))
 def test_new_file_same_mtime_different_state_and_catalog_refresh(self):
  old=(self.root/'mi_trabajo/mi_trabajo.json').stat()
  X.tarea('mi');self.mi['tareas'][2]['estado']='NEW';self.mi['estados_lista']={'last':['NEW']};self.write('mi_trabajo',self.mi)
  os.utime(self.root/'mi_trabajo/mi_trabajo.json',ns=(old.st_atime_ns,old.st_mtime_ns))
  self.assertEqual(X.tarea('mi')['estado'],'NEW');self.assertEqual(X.estados_de_tarea('shared'),['NEW'])
 def test_same_inode_same_mtime_same_size_refresh_via_ctime(self):
  p=self.root/'produccion/produccion.json';X.tarea('shared');st=p.stat();text=p.read_text();p.write_text(text.replace('review','REVNEW'));os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns))
  self.assertEqual(X.tarea('shared')['estado'],'REVNEW')
 def test_removed_invalid_unreadable_no_old_doc_fallback(self):
  X.tarea('only-review');p=self.root/'produccion/produccion.json';p.unlink();self.assertIsNone(X.tarea('only-review'))
  p.write_text('{malformed');self.assertIsNone(X.tarea('only-review'))
  self.write('produccion',self.prod)
  with patch.object(X,'leer_json',return_value={}):
   self.write('produccion',dict(self.prod,generado='new'));self.assertIsNone(X.tarea('only-review'))
 def test_mid_read_race_retries_and_never_publishes_obsolete_read(self):
  original=X.leer_json;reads=[]
  def reader(p,default=None):
   d=original(p,default)
   if Path(p).parent.name=='produccion' and not reads:
    reads.append(1);self.prod['revisiones'][0]['estado']='after-race';self.write('produccion',self.prod)
   return d
  with patch.object(X,'leer_json',side_effect=reader):self.assertEqual(X.tarea('shared')['estado'],'after-race')
 def test_persistent_race_bounded_returns_empty_not_old(self):
  calls=[]
  def unstable(p,default=None):
   calls.append(1);self.write('produccion',dict(self.prod,generado=str(len(calls))));return self.prod
  with patch.object(X,'leer_json',side_effect=unstable):
   self.assertEqual(X._produccion(),{});self.assertEqual(len(calls),2)
 def test_12k_batch_parse_twice_build_once_no_per_ref_scans(self):
  self.prod={'cola':[],'revisiones':[]};self.mi={'generado':'source','tareas':[{'id':str(i),'persona_id':'p','estado':'open','lista_id':'l'} for i in range(12000)]}
  self.write('produccion',self.prod);self.write('mi_trabajo',self.mi)
  with patch.object(X,'leer_json',wraps=X.leer_json) as read:
   for i in range(12000):self.assertEqual(X.tarea(str(i))['id'],str(i))
   self.assertEqual(read.call_count,2)
  self.assertEqual(len(X._DOCUMENTOS_TAREA),2);self.assertEqual(len(X._INDICE_TAREA['por_id']),12000)
 def test_concurrent_readers_do_not_merge_sources_authors_or_rebuild(self):
  with patch.object(X,'leer_json',wraps=X.leer_json) as read:
   with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda i:X.tarea('shared'),range(100)))
   self.assertTrue(all(t==self.old('shared') for t in results));self.assertEqual(read.call_count,2)
 def test_authority_is_evaluated_again_with_unchanged_document(self):
  chief={'id':'chief','puestos':[]};current={'jefe':'chief'}
  with patch.object(X,'S',None),patch.object(X,'_persona',side_effect=lambda pid:current):
   self.assertIsNotNone(X.tarea_tocable(chief,'shared')[0])
   current.clear();self.assertIsNone(X.tarea_tocable(chief,'shared')[0])
   self.assertEqual(X.tarea('shared')['autores'],{'a','b'})
 def test_changed_namespace_never_reuses_old_version(self):
  X.tarea('shared')
  with TemporaryDirectory() as d,patch.object(X,'DATA',Path(d)):self.assertIsNone(X.tarea('shared'))
  self.assertEqual(X.tarea('shared'),self.old('shared'))

if __name__=='__main__':unittest.main()
