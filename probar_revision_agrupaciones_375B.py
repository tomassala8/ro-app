"""Revisión independiente, sólo fixtures; sin generar candidato ni publicar datos."""
import unittest,copy,math
import probar_agrupaciones_artifact_375 as fixtures375
from fuentes_horas.agrupaciones_artifact_375 import construir
class Revision375B(unittest.TestCase):
 def setUp(self):
  base=fixtures375.Agrupaciones();base.setUp();self.tareas=base.tareas;self.entradas=base.entradas;self.kw=base.kw
 def calc(self,entries=None,tasks=None,**kw):return construir(self.entradas if entries is None else entries,self.tareas if tasks is None else tasks,**{**self.kw,**kw})
 def test_daily_window_does_not_keep_old_entries_for_recent_task(self):
  self.entradas.append({**self.entradas[0],'id':'old','inicio':'2026-08-01T00:00:00Z','horas':900})
  self.assertEqual(self.calc()['filas'][0]['total_h'],15)
 def test_sample_unit_same_task_different_users(self):
  entries=[{**self.entradas[0],'id':f'x{i}','usuario_id':f'u{i}','horas':i+1} for i in range(5)]
  r=self.calc(entries,usuario_ids={f'u{i}' for i in range(5)})['filas'][0]
  self.assertEqual((r['casos'],r['mediana_h'],r['max_h'],r['total_h']),(5,3,5,15))
 def test_invalid_global_collision_precedes_scope_filter(self):
  e={**self.entradas[0],'usuario_id':'foreign','horas':{'invalid':2}}
  self.assertEqual(self.calc(self.entradas+[e])['filas'],[])
 def test_positive_tiny_duration_stays_positive(self):
  for e in self.entradas:e['horas']=.0005
  r=self.calc()['filas'][0];self.assertGreater(r['mediana_h'],0);self.assertAlmostEqual(r['total_h'],.0025)
 def test_missing_invalid_client_and_internal_explicit(self):
  for value in [[],{},False,'foreign']:
   tasks=copy.deepcopy(self.tareas);tasks[0]['cliente_id']=value;self.assertEqual(self.calc(tasks=tasks)['filas'],[])
 def test_overflow_no_infinity(self):
  for e in self.entradas:e['horas']=1e308
  self.assertEqual(self.calc()['filas'],[])
 def test_no_duration_close_or_accepted_deliverable_claim(self):
  r=self.calc();self.assertFalse(r['duracion_cerrada_confirmada']);self.assertFalse(r['tipo_historico_confirmado']);self.assertIsNone(r['tiempo_normativo']);self.assertEqual(r['cobertura'],'parcial')
 def test_sensitive_group_is_excluded_not_exported(self):
  for title in ['password secretoFixtureSoloPrueba revisión mensual','correo fixture@example.test revisión mensual']:
   tasks=copy.deepcopy(self.tareas)
   for t in tasks:t['nombre']=title
   self.assertEqual(self.calc(tasks=tasks)['filas'],[])
 def test_amount_removed_from_safe_group(self):
  tasks=copy.deepcopy(self.tareas)
  for t in tasks:t['nombre']='presupuesto 1500 € revisión mensual'
  result=self.calc(tasks=tasks)
  self.assertNotIn('1500',str(result));self.assertNotIn('€',str(result))
 def test_entry_after_read_but_before_cut_is_not_observed(self):
  for e in self.entradas:e['inicio']='2026-10-03T07:30:00Z'
  self.assertEqual(self.calc()['filas'],[])
if __name__=='__main__':unittest.main()
