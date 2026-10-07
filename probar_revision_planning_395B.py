"""Auditoría independiente395B: fixtures propios, sin fuentes privadas ni promoción."""
import copy,importlib.util,json,os,sys,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
APP=Path(__file__).resolve().parent
sys.path.insert(0,str(APP))
from fuentes_produccion.planning_observado_395 import construir,instante
R=APP.parent/'RECUPERACION_CODEX_2026-10-03'
spec=importlib.util.spec_from_file_location('writer_ind395B',R/'preparar_planning_observado_395.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)
class Independiente395B(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,4,12,tzinfo=timezone.utc)
  self.task={'id':'task_1','lista_id':'list_1','carpeta_id':'folder_1','estado':'diario','tipo_estado':'unstarted','estado_fuente':'clickup','estado_leido_utc':'2026-10-03T12:00:00Z','asignados':[{'id':101}],'inicio':None,'vence':None,'estimacion_ms':None}
  self.raw={'tareas':[self.task]}
  self.cat={'listas':{'list_1':{'ok':True,'estados':[{'status':'diario','type':'unstarted'},{'status':'en curso','type':'custom'}]}}}
  self.folders={'folder_1':('client_1','NOMBRE_PRIVADO')};self.ident={'101':'person_1'}
 def build(self):return construir(self.raw,self.cat,self.folders,{'client_1'},self.ident,{'person_1'},self.now)
 def test_invalid_offsets_never_accredited(self):
  for stamp in ['2026-10-03T12:00:00+02:99','2026-10-03T12:00:00+15:00','2026-10-03T12:00:00+14:01','2026-10-03T12:00:00-15:00']:
   with self.subTest(stamp=stamp):
    self.task['estado_leido_utc']=stamp;self.assertIsNone(instante(stamp));self.assertEqual(self.build()['filas'],[])
 def test_calendar_future_bad_source_never_accredited(self):
  for stamp in ['2026-02-30T12:00:00Z','2026-10-03T24:00:00Z','2026-10-05T12:00:00Z',None,'2026-10-03 12:00']:
   self.task['estado_leido_utc']=stamp;self.assertEqual(self.build()['filas'],[])
  self.task['estado_leido_utc']='2026-10-03T12:00:00Z';self.task['estado_fuente']='cache';self.assertEqual(self.build()['filas'],[])
 def test_fractional_order_and_timezone_not_rejuvenated(self):
  second=copy.deepcopy(self.task);second.update(id='task_2',estado_leido_utc='2026-10-03T14:00:00.500000+02:00');self.raw['tareas'].append(second)
  d=self.build();self.assertEqual(d['lecturas_estado']['desde'],'2026-10-03T12:00:00Z');self.assertEqual(d['lecturas_estado']['hasta'],'2026-10-03T12:00:00.500000Z');self.assertEqual(d['corte_preparacion_utc'],'2026-10-04T12:00:00Z')
 def test_duplicate_global_task_outside_selected_state_denies(self):
  duplicate=copy.deepcopy(self.task);duplicate['estado']='archivado';self.raw['tareas'].append(duplicate);self.assertEqual(self.build()['filas'],[])
 def test_typed_state_per_exact_list_no_cross_list(self):
  for key,value in [('lista_id','foreign_list'),('tipo_estado','custom'),('estado','Diario')]:
   old=self.task[key];self.task[key]=value;self.assertEqual(self.build()['filas'],[]);self.task[key]=old
  self.cat['listas']['list_1']['estados'][0]['type']='closed';self.task['tipo_estado']='closed';self.assertEqual(self.build()['filas'],[])
 def test_act_and_folder_exact_no_alias(self):
  self.assertEqual(construir(self.raw,self.cat,self.folders,set(),self.ident,{'person_1'},self.now)['filas'],[])
  self.task['cliente_id']='client_1';self.task['carpeta_id']='unknown';self.assertEqual(self.build()['filas'],[])
 def test_unknown_inactive_identity_preserves_unassigned_not_guess(self):
  for identities,active in [({}, {'person_1'}),({'101':'person_1'},set())]:
   row=construir(self.raw,self.cat,self.folders,{'client_1'},identities,active,self.now)['filas'][0]
   self.assertEqual(row['asignados_persona_ids'],[]);self.assertEqual(row['asignacion_estado'],'parcial');self.assertEqual(row['asignados_sin_identidad_confirmada'],1)
 def test_uid_normalization_global_duplicate_and_boolean_deny(self):
  for assigned in [[{'id':101},{'id':'101'}],[{'id':True}]]:
   self.task['asignados']=assigned;self.assertEqual(self.build()['filas'],[])
 def test_whitelisted_output_no_titles_urls_contact_finance(self):
  self.task.update(nombre='PRIVATE_TITLE',url='https://private.invalid',descripcion='PRIVATE_DESCRIPTION',importe=12345,asignados=[{'id':101,'email':'private@example.invalid','nombre':'PRIVATE_PERSON'}])
  before=copy.deepcopy(self.raw);d=self.build();serial=json.dumps(d)
  for token in ['PRIVATE_','private.invalid','private@example','12345','NOMBRE_PRIVADO','importe','descripcion']:
   self.assertNotIn(token,serial)
  self.assertEqual(before,self.raw);self.assertIsNone(d['cumplimiento']);self.assertFalse(d['clasificacion_historia']);self.assertTrue(d['cero_no_acredita_ausencia'])
 def test_json_duplicates_and_nonfinite_fail_closed(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'fixture'
   for body in ['{"tareas":[],"tareas":[{"id":"task_1"}]}','{"nested":{"id":"one","id":"two"}}','{"value":NaN}','{"value":1e999}']:
    p.write_text(body)
    with self.subTest(body=body):
     with self.assertRaises(ValueError):W.leer(p)
 def test_private_atomic_replay_and_conflicting_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp)/'deposit';d=self.build();first=W.publicar_candidato(dest,d,{});again=W.publicar_candidato(dest,d,{})
   self.assertFalse(first['replay']);self.assertTrue(again['replay']);self.assertEqual(dest.stat().st_mode&0o777,0o700)
   self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in dest.iterdir()))
   with self.assertRaises(ValueError):W.publicar_candidato(dest,{**d,'version':'foreign'},{})
 def test_no_symlink_hardlink_fifo_sources(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'regular';p.write_text('{}');q=Path(tmp)/'link';q.symlink_to(p)
   with self.assertRaises(OSError):W.leer(q)
   q.unlink();os.link(p,q)
   with self.assertRaises(ValueError):W.leer(p)
   f=Path(tmp)/'fifo';os.mkfifo(f)
   with self.assertRaises(ValueError):W.leer(f)
if __name__=='__main__':unittest.main()
