import copy,datetime as dt,json,unittest
from fuentes_horas.historial_diario_359 import construir_historial
class Historial(unittest.TestCase):
 def setUp(self):
  self.ps=[{'id':'p','correo':'p@example.test','estado':'activo','zona':'Europe/Madrid','zona_a_confirmar':False}]
  self.us=[{'id':1,'email':'p@example.test'}]
  self.cache={'meta':{'generado':'2026-10-03T00:56:00Z'},'entradas':[]}
 def entry(self,eid='e',h=1,date='2026-09-01T09:00:00Z',uid=1):return {'id':eid,'usuario_id':uid,'inicio':date,'horas':h,'task_id':'t','tarea':'NO_PRINT','descripcion':'NO_PRINT'}
 def go(self,c=None,ps=None,us=None):return construir_historial(c or self.cache,self.ps if ps is None else ps,self.us if us is None else us,'2026-10-03')
 def day(self,out,date,pid='p'):return next(x for x in out['series'][pid]['dias'] if x['fecha']==date)
 def test_90_days_and_unknown(self):
  out=self.go();s=out['series']['p'];self.assertEqual(len(s['dias']),90);self.assertEqual(s['desde'],'2026-07-05');self.assertEqual(s['hasta'],'2026-10-02');self.assertTrue(all(x['horas'] is None for x in s['dias']))
 def test_observed_zero_and_positive(self):
  self.cache['entradas']=[self.entry('z',0),self.entry('v',3)];d=self.day(self.go(),'2026-09-01');self.assertEqual(d['horas'],3);self.assertEqual(d['entradas'],2)
 def test_zero_explicit(self):self.cache['entradas']=[self.entry(h=0)];self.assertEqual(self.day(self.go(),'2026-09-01')['horas'],0)
 def test_tiny_positive_not_zero(self):
  self.cache['entradas']=[self.entry(h=0.00000001)];self.assertGreater(self.day(self.go(),'2026-09-01')['horas'],0)
 def test_replay_dedup(self):
  e=self.entry();self.cache['entradas']=[e,copy.deepcopy(e)];o=self.go();self.assertEqual(self.day(o,'2026-09-01')['horas'],1);self.assertEqual(o['diagnostico']['replays'],1)
 def test_malformed_task_id_cannot_certify_replay(self):
  for bad in [{'x':'y'},[],True,'']:
   a=self.entry();a['task_id']=bad;b=self.entry();b['task_id']=str(bad)
   self.cache['entradas']=[a,b];o=self.go();self.assertIsNone(self.day(o,'2026-09-01')['horas']);self.assertEqual(o['diagnostico']['replays'],0)
 def test_internal_without_task_id_and_typed_replay(self):
  for task in [None,'t',123]:
   a=self.entry();a['task_id']=task;self.cache['entradas']=[a,copy.deepcopy(a)];o=self.go();self.assertEqual(self.day(o,'2026-09-01')['horas'],1);self.assertEqual(o['diagnostico']['replays'],1)
 def test_conflict_suppresses_day(self):
  self.cache['entradas']=[self.entry(),self.entry(h=2),self.entry('ok',4)];o=self.go();self.assertIsNone(self.day(o,'2026-09-01')['horas']);self.assertEqual(o['diagnostico']['ids_invalidos_o_conflictivos'],1)
 def test_conflict_foreign_uid_not_ignored(self):
  self.cache['entradas']=[self.entry(),self.entry(uid=99)];self.assertIsNone(self.day(self.go(),'2026-09-01')['horas'])
 def test_invalid_replay_not_choose_valid(self):
  self.cache['entradas']=[self.entry(),self.entry(h='1')];self.assertIsNone(self.day(self.go(),'2026-09-01')['horas'])
 def test_exact_alias_email_not_names(self):
  self.ps[0]['correo']='other@example.test';self.ps[0]['nombre']='Provider';self.us[0]['username']='Provider';self.cache['entradas']=[self.entry()];self.assertIsNone(self.day(self.go(),'2026-09-01')['horas'])
 def test_duplicate_and_inactive_persons(self):
  for ps in [self.ps+self.ps,[{**self.ps[0],'activo':False}],[{**self.ps[0],'estado':'baja'}],[{**self.ps[0],'zona_a_confirmar':True}]]:self.assertEqual(self.go(ps=ps)['series'],{})
 def test_person_id_requires_canonical_string(self):
  self.assertEqual(self.go(ps=[{**self.ps[0],'id':1}])['series'],{})
 def test_shared_email_and_provider_conflict(self):
  self.cache['entradas']=[self.entry()]
  out=self.go(ps=self.ps+[{**self.ps[0],'id':'q'}]);self.assertTrue(all(d['horas'] is None for d in out['series']['p']['dias']))
  out=self.go(us=self.us+[{'id':1,'email':'other@example.test'}]);self.assertIsNone(self.day(out,'2026-09-01')['horas'])
 def test_timezone_confirmed_not_default(self):
  for p in [{**self.ps[0],'zona':None},{**self.ps[0],'zona':'Unknown/City'}]:self.assertEqual(self.go(ps=[p])['series'],{})
 def test_person_timezone_date(self):
  self.ps[0]['zona']='America/Argentina/Buenos_Aires';self.cache['entradas']=[self.entry(date='2026-09-02T01:00:00Z')];self.assertEqual(self.day(self.go(),'2026-09-01')['horas'],1)
 def test_future_today_and_outside(self):
  self.cache['entradas']=[self.entry('future',date='2026-10-04T00:00:00Z'),self.entry('today',date='2026-10-03T00:00:00Z'),self.entry('old',date='2026-07-04T00:00:00Z')];o=self.go();self.assertTrue(all(d['horas'] is None for d in o['series']['p']['dias']));self.assertGreaterEqual(o['diagnostico']['invalidas'],1)
 def test_invalid_and_large_valid_duration(self):
  for h in [True,-1,float('nan'),float('inf'),'2']:
   self.cache['entradas']=[self.entry(h=h)];self.assertIsNone(self.day(self.go(),'2026-09-01')['horas'])
  self.cache['entradas']=[self.entry(h=12)];self.assertEqual(self.day(self.go(),'2026-09-01')['horas'],12)
 def test_overflow_not_zero(self):
  self.cache['entradas']=[self.entry('a',1e308),self.entry('b',1e308)];self.assertIsNone(self.day(self.go(),'2026-09-01')['horas'])
 def test_source_naive_requires_zone(self):
  self.cache['meta']['generado']='2026-10-03 02:56'
  with self.assertRaises(ValueError):self.go()
  o=construir_historial(self.cache,self.ps,self.us,'2026-10-03',zona_sello='Europe/Madrid');self.assertEqual(o['series']['p']['fecha_fuente_utc'],'2026-10-03T00:56:00+00:00')
 def test_invalid_source_and_aware_entries(self):
  for s in ['2026-10-04T00:00Z','notdate','2026-02-30T00:00Z']:
   self.cache['meta']['generado']=s
   with self.assertRaises(ValueError):self.go()
  self.cache['meta']['generado']='2026-10-03T00:56Z';self.cache['entradas']=[self.entry(date='2026-09-01T09:00')];self.assertIsNone(self.day(self.go(),'2026-09-01')['horas'])
 def test_privacy_no_mutation(self):
  self.cache['entradas']=[self.entry()];before=copy.deepcopy(self.cache);out=self.go();self.assertEqual(self.cache,before);self.assertNotIn('NO_PRINT',json.dumps(out));self.assertNotIn('example.test',json.dumps(out));self.assertNotIn('task_id',json.dumps(out))
if __name__=='__main__':unittest.main()
