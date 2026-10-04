import copy,importlib.util,json,os,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from fuentes_produccion.planning_observado_355 import construir,VERSION
APP=Path(__file__).resolve().parents[1];R=APP.parent/'RECUPERACION_CODEX_2026-10-03'
spec=importlib.util.spec_from_file_location('candidate355',R/'preparar_planning_observado_355.py');W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)
class Planning(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,3,18,tzinfo=timezone.utc)
  self.t={'id':'t1','lista_id':'l1','carpeta_id':'f1','estado':'planning mensual','tipo_estado':'custom','estado_fuente':'clickup','estado_leido_utc':'2026-10-03T17:00:00Z','asignados':[{'id':12,'nombre':'CONTACTO_PRIVADO'}],'inicio':'1791158400000','vence':'1791244800000','estimacion_ms':7200000,'nombre':'PRECIO_TELEFONO','url':'https://host/?secret=x'}
  self.raw={'tareas':[self.t]};self.cat={'listas':{'l1':{'ok':True,'estados':[{'status':'planning mensual','type':'custom'},{'status':'backlog','type':'open'}]}}};self.folders={'f1':('c1','NO_EXPORTAR')};self.ids={'12':'p1'}
 def build(self):return construir(self.raw,self.cat,self.folders,{'c1'},self.ids,{'p1'},self.now)
 def test_contract_typed_minimized_immutable(self):
  before=copy.deepcopy(self.raw);d=self.build();r=d['filas'][0];self.assertEqual(r['asignados_persona_ids'],['p1']);self.assertEqual(r['estimacion']['unidad'],'milisegundos');self.assertEqual(r['estimacion']['valor'],7200000);self.assertIsNone(r['rompe_semanal']);self.assertIsNone(r['actor_historico']);self.assertFalse(d['promovido']);self.assertNotIn('PRIVADO',json.dumps(d));self.assertNotIn('NO_EXPORTAR',json.dumps(d));self.assertNotIn('secret',json.dumps(d));self.assertEqual(before,self.raw)
 def test_same_label_terminal_not_inventory(self):
  self.cat['listas']['l1']['estados'][0]['type']='closed';self.t['tipo_estado']='closed';self.assertEqual(self.build()['filas'],[])
 def test_catalog_contradiction_missing_duplicate_status(self):
  for cat in [{}, {'listas':{'l1':{'ok':False}}}, {'listas':{'l1':{'ok':True,'estados':[{'status':'planning mensual','type':'open'}]}}}]:
   self.cat=cat;self.assertEqual(self.build()['filas'],[])
 def test_no_global_name_guess(self):
  self.t['estado']='planning mensual urgente';self.assertEqual(self.build()['filas'],[])
 def test_no_read_cache_timestamp_fallback(self):
  self.raw['meta']={'generado':'2026-10-03 17:00'}
  for v in [None,'2026-10-03 17:00','2026-10-04T17:00:00Z','2026-02-30T17:00:00Z']:
   self.t['estado_leido_utc']=v;self.assertEqual(self.build()['filas'],[])
 def test_provider_source_required(self):self.t['estado_fuente']='cache';self.assertEqual(self.build()['filas'],[])
 def test_duplicate_malformed_task_ids_list_cid(self):
  self.raw['tareas'].append(copy.deepcopy(self.t));self.assertEqual(self.build()['filas'],[])
  self.raw['tareas']=[self.t]
  for k,v in [('id',{}),('id',True),('lista_id',12),('lista_id',[])]:
   old=self.t[k];self.t[k]=v;self.assertEqual(self.build()['filas'],[]);self.t[k]=old
  self.folders['f1']=([],None);self.assertEqual(self.build()['filas'],[])
 def test_unknown_foreign_unconfirmed_assignees_not_authority(self):
  self.ids={};d=self.build()['filas'][0];self.assertEqual(d['asignados_persona_ids'],[]);self.assertEqual(d['asignacion_estado'],'parcial');self.assertEqual(d['asignados_sin_identidad_confirmada'],1)
 def test_malformed_assignees_deny_row(self):
  for assigned in [[{'id':12},{'id':'12'}],[{'id':[]}],[{'id':True}]]:
   self.t['asignados']=assigned;self.assertEqual(self.build()['filas'],[])
 def test_dates_future_scheduling_allowed_bad_notzero(self):
  r=self.build()['filas'][0];self.assertEqual(r['vence_estado'],'observada')
  for v in [0,True,{},-1,'n/a']:
   self.t['vence']=v;r=self.build()['filas'][0];self.assertIsNone(r['vence_utc']);self.assertEqual(r['vence_estado'],'invalida')
 def test_estimation_unknown_notzero_nonfinite(self):
  for v in [0,-1,True,float('nan'),float('inf'),None,'22']:
   self.t['estimacion_ms']=v;self.assertIsNone(self.build()['filas'][0]['estimacion']['valor'])
 def test_act_scope_and_no_empty_success(self):
  d=construir(self.raw,self.cat,self.folders,set(),self.ids,{'p1'},self.now);self.assertEqual(d['filas'],[]);self.assertIsNone(d['cumplimiento']);self.assertTrue(d['cero_no_acredita_ausencia'])
 def test_atomic_private_replay_and_conflict(self):
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp)/'candidate';d=self.build();m={'fuentes_sha256':{'fixture':'a'*64}};first=W.publicar_candidato(dest,d,m);again=W.publicar_candidato(dest,d,m)
   self.assertFalse(first['replay']);self.assertTrue(again['replay']);self.assertEqual(first['candidato_sha256'],again['candidato_sha256']);self.assertEqual(dest.stat().st_mode&0o777,0o700)
   for p in dest.iterdir():self.assertEqual(p.stat().st_mode&0o777,0o600)
   with self.assertRaises(ValueError):W.publicar_candidato(dest,{**d,'cumplimiento':True},m)
 def test_crash_before_publish_no_half_candidate(self):
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp)/'candidate'
   with patch.object(W.os,'rename',side_effect=OSError('fixture')):
    with self.assertRaises(OSError):W.publicar_candidato(dest,self.build(),{})
   self.assertFalse(dest.exists());self.assertEqual(list(Path(tmp).iterdir()),[])
 def test_reader_no_symlink_hardlink_nonfinite(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'raw';p.write_text('{"x":NaN}')
   with self.assertRaises(ValueError):W.leer(p)
   p.write_text('{}');q=Path(tmp)/'link';q.symlink_to(p)
   with self.assertRaises(OSError):W.leer(q)
   q.unlink();os.link(p,q)
   with self.assertRaises(ValueError):W.leer(p)
if __name__=='__main__':unittest.main()
