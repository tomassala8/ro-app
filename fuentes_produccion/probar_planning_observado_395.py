import copy,importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fuentes_produccion.planning_observado_355 import construir as anterior
from fuentes_produccion.planning_observado_395 import construir,ESTADOS
from fuentes_produccion.probar_planning_observado_355 import Planning as CasosBase
APP=Path(__file__).resolve().parents[1];R=APP.parent/'RECUPERACION_CODEX_2026-10-03'
spec=importlib.util.spec_from_file_location('writer395',R/'preparar_planning_observado_395.py');W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)
class Planning395(CasosBase):
 def build(self):return construir(self.raw,self.cat,self.folders,{'c1'},self.ids,{'p1'},self.now)
 def full(self):
  self.raw['tareas']=[];self.cat['listas']['l1']['estados']=[]
  for n,e in enumerate(sorted(ESTADOS)):
   self.raw['tareas'].append({**copy.deepcopy(self.t),'id':'t'+str(n),'estado':e,'tipo_estado':'custom'});self.cat['listas']['l1']['estados'].append({'status':e,'type':'custom'})
 def test_all_exact_states_no_hoy_guess(self):
  self.full();d=self.build();self.assertEqual(len(d['filas']),5);self.assertEqual(set(r['estado'] for r in d['filas']),ESTADOS)
  self.raw['tareas'].append({**self.t,'id':'extra','estado':'hoy'});self.assertEqual(len(self.build()['filas']),5)
 def test_legacy_subset_preserved_exactly(self):
  self.full();old=anterior(self.raw,self.cat,self.folders,{'c1'},self.ids,{'p1'},self.now);new=self.build()
  self.assertEqual([r for r in new['filas'] if r['estado'] in {'backlog','planning mensual'}],old['filas']);self.assertEqual(new['version'],'395.1')
 def test_same_label_other_list_no_catalog_inference(self):
  self.full();self.raw['tareas'][0]['lista_id']='otra';self.assertEqual(len(self.build()['filas']),4)
 def test_reading_span_not_preparation_rejuvenation(self):
  self.full();self.raw['tareas'][0]['estado_leido_utc']='2026-10-01T10:00:00+02:00';d=self.build()
  self.assertEqual(d['lecturas_estado']['desde'],'2026-10-01T08:00:00Z');self.assertEqual(d['lecturas_estado']['hasta'],'2026-10-03T17:00:00Z');self.assertEqual(d['corte_preparacion_utc'],'2026-10-03T18:00:00Z')
 def test_fractional_read_times_ordered_as_instants(self):
  self.full();self.raw['tareas'][0]['estado_leido_utc']='2026-10-03T17:00:00.001Z';d=self.build();self.assertEqual(d['lecturas_estado']['desde'],'2026-10-03T17:00:00Z');self.assertEqual(d['lecturas_estado']['hasta'],'2026-10-03T17:00:00.001000Z')
 def test_malformed_offset_rejected(self):
  for stamp in ['2026-10-03T17:00:00+02:99','2026-10-03T17:00:00+15:00','2026-10-03T17:00:00+14:01']:
   self.t['estado_leido_utc']=stamp;self.assertEqual(self.build()['filas'],[])
 def test_json_duplicate_keys_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'raw';p.write_text('{"estado":"diario","estado":"backlog"}')
   with self.assertRaises(ValueError):W.leer(p)
 def test_json_overflow_float_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'raw';p.write_text('{"estimacion_ms":1e999}')
   with self.assertRaises(ValueError):W.leer(p)
 def test_duplicates_across_states_denied_globally(self):
  self.full();self.raw['tareas'][1]['id']=self.raw['tareas'][0]['id'];self.assertEqual(len(self.build()['filas']),3)
 def test_empty_scope_not_work_absence(self):
  self.full();d=construir(self.raw,self.cat,self.folders,set(),self.ids,{'p1'},self.now);self.assertEqual(d['filas'],[]);self.assertIsNone(d['lecturas_estado']['desde']);self.assertIsNone(d['cumplimiento']);self.assertTrue(d['cero_no_acredita_ausencia'])
 def test_extreme_numeric_inputs_fail_closed(self):
  self.t['estimacion_ms']=10**1000;self.assertIsNone(self.build()['filas'][0]['estimacion']['valor']);self.t['id']=10**1000;self.assertEqual(self.build()['filas'],[])
 def test_private395_replay_schema_and_modes(self):
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp)/'candidate';d=self.build();a=W.publicar_candidato(dest,d,{});b=W.publicar_candidato(dest,d,{})
   self.assertTrue(b['replay']);self.assertEqual(a['candidato_sha256'],b['candidato_sha256']);self.assertEqual(json.loads((dest/'manifest.json').read_text())['version'],'395.1');os.chmod(dest/'candidato.json',0o640)
   with self.assertRaises(ValueError):W.publicar_candidato(dest,d,{})
 def test_fifo_nonblock_and_regular_required(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'fifo';os.mkfifo(p);real=W.os.open
   def audited(path,flags,*a):
    if Path(path)==p:self.assertTrue(flags&os.O_NONBLOCK)
    return real(path,flags,*a)
   with patch.object(W.os,'open',side_effect=audited):
    with self.assertRaises(ValueError):W.leer(p)
 def test_new_writer_atomic_no_half_candidate(self):
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp)/'candidate'
   with patch.object(W.os,'rename',side_effect=OSError('fixture')):
    with self.assertRaises(OSError):W.publicar_candidato(dest,self.build(),{})
   self.assertFalse(dest.exists());self.assertEqual(list(Path(tmp).iterdir()),[])
del CasosBase
if __name__=='__main__':unittest.main()
