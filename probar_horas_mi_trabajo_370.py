import ast, unittest, math
from pathlib import Path
from datetime import date,timedelta
class Horas370(unittest.TestCase):
 def setUp(self):
  funcs=[x for x in ast.parse(Path(__file__).with_name('mi_trabajo.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name in {'raras_de','laborables_atras','numero_horas_370','suma_horas_370'}]
  self.ns={'math':math,'date':date,'timedelta':timedelta,'persona':lambda _: {},'hoy_de':lambda _:date(2026,10,3),'es_dia':lambda x:date.fromisoformat(x) if x else None}
  exec(compile(ast.Module(body=funcs,type_ignores=[]),'real370','exec'),self.ns)
 def run_fixture(self,dias,D=None):
  return self.ns['raras_de']('p',dias,None,D or {'jornada':[{'persona_id':'p'}]}, {},lambda _:False)
 def test_absence_is_unknown(self):
  rs=self.run_fixture({});self.assertEqual(len(rs),5)
  self.assertTrue(all(r['regla']=='sin_registros_copia' and r['horas'] is None and not r['calendario_confirmado'] for r in rs))
 def test_explicit_zero_not_missing(self):
  rs=self.run_fixture({'2026-10-02':{'cu':0,'app':0}})
  self.assertEqual(len(rs),4);self.assertNotIn('2026-10-02',[r['dia'] for r in rs])
 def test_positive_preserved_and_long_review(self):
  rs=self.run_fixture({'2026-10-02':{'cu':11,'app':0}})
  self.assertEqual([r['horas'] for r in rs if r['regla']=='mas_10'],[11])
 def test_weekend_observed_not_schedule_breach(self):
  rs=self.run_fixture({'2026-09-27':{'cu':2,'app':0}})
  self.assertEqual([r['horas'] for r in rs if r['regla']=='fin_semana'],[2])
 def test_no_reference_no_invented_missing_dates(self):
  self.assertEqual(self.run_fixture({}, {'jornada':[]}),[])
 def test_invalid_values_and_overflow_never_crash_or_emit_infinity(self):
  for v in [None,'2',True,float('nan'),float('inf')]:
   self.assertEqual(self.run_fixture({'2026-10-02':{'cu':v,'app':0}}, {'jornada':[]}),[])
  self.assertEqual(self.run_fixture({'2026-10-02':{'cu':1e308,'app':1e308}}, {'jornada':[]}),[])
 def test_estimation_invalid_sum_is_omitted(self):
  D={'jornada':[], 'raras_estimacion':[{'persona_id':'p','tarea_id':'t','horas_t':1e308,'est_h':1}]}
  self.assertEqual(self.ns['raras_de']('p',{},None,D,{'t':1e308},lambda _:False),[])
 def test_real_dto_component_presence_and_ro_mark(self):
  tree=ast.parse(Path(__file__).with_name('mi_trabajo.py').read_text());g=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='get_estado')
  start=next(i for i,n in enumerate(g.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='marcas' for t in n.targets))
  end=next(i for i,n in enumerate(g.body[start:],start) if isinstance(n,ast.FunctionDef) and n.name=='ve_cli')
  chunk=compile(ast.Module(body=g.body[start:end],type_ignores=[]),'dto_real370','exec')
  cambio={'campo':'horas','estado':'simulado','marca':'ro:fixture','quien':'p','tarea':'t','dia':'2026-10-02','minutos':60}
  def project(rows,changes):
   v={**self.ns,'D':{'horas_dia':rows},'ids':{'p'},'cambios_personales':changes,'tareas_autorizadas':{'t'}};exec(chunk,v);return v
  v=project([], [cambio]);x=v['dias']['p']['2026-10-02'];self.assertIsNone(x['cu']);self.assertFalse(x['cu_observado']);self.assertEqual(x['app'],1);self.assertTrue(x['app_observado'])
  v=project([{'persona_id':'p','dias':{'2026-10-02':0},'marcas':[]}],[]);x=v['dias']['p']['2026-10-02'];self.assertEqual(x['cu'],0);self.assertTrue(x['cu_observado']);self.assertIsNone(x['app']);self.assertFalse(x['app_observado'])
  v=project([{'persona_id':'p','dias':{'2026-10-02':1},'marcas':['ro:fixture']}],[cambio]);self.assertIsNone(v['dias']['p']['2026-10-02']['app']);self.assertTrue(v['horas_app'][0]['en_clickup'])
  v=project([], [{**cambio,'minutos':True}]);self.assertEqual(v['dias']['p'],{})
if __name__=='__main__'  :unittest.main()
