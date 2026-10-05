import copy,datetime as d,unittest
from zoneinfo import ZoneInfo
from fuentes_produccion.comparacion_semanal_296 import construir
MAD=ZoneInfo('Europe/Madrid');CUT=d.datetime(2026,10,3,15,8,tzinfo=MAD);NOW=CUT+d.timedelta(hours=1)
def ms(v):return str(int(v.timestamp()*1000))
def task(tid='task1',cr=None,cl=None,**kw):return {'id':tid,'carpeta_id':'folder','lista_id':'list','estado':'completado','tipo_estado':'closed','creador':3,'creada':ms(cr or CUT-d.timedelta(days=1)),'cerrada':ms(cl)if cl else None,**kw}
CAT={'listas':{'list':{'ok':True,'estados':[{'status':'completado','type':'closed'}]}}}
def run(ts,**kw):return construir({'meta':{'generado':'2026-10-03 15:08'},'tareas':ts},kw.get('cat',CAT),kw.get('folders',{'folder':('cliente',None)}),kw.get('activos',{'cliente'}),kw.get('ids',{'3':'persona'}),kw.get('ps',{'persona'}),kw.get('cut',CUT),kw.get('now',NOW))
class Tests(unittest.TestCase):
 def test_original_column_never_creation_substitute(self):
  o=run([task()]);self.assertIn('no_sustituir',o['columna_original_semana_pasada']);a=o['creadores'][0];self.assertIsNone(a['rompen_semanal']);self.assertIsNone(a['al_planning']);self.assertIsNone(a['fuegos_directos'])
 def test_boundaries_and_previous_week(self):
  monday=d.datetime(2026,9,28,tzinfo=MAD);prev=monday-d.timedelta(days=7)
  o=run([task('a',monday),task('b',prev),task('c',monday-d.timedelta(microseconds=1000)),task('d',prev-d.timedelta(seconds=1)),task('e',CUT),task('f',CUT+d.timedelta(seconds=1))]);r=o['creadores'][0]['creadas'];self.assertEqual(r['actual']['valor'],2);self.assertEqual(r['anterior']['valor'],2);self.assertFalse(o['ventanas']['anterior']['hasta_inclusiva']);self.assertTrue(o['ventanas']['actual']['hasta_inclusiva'])
 def test_final_only_project_not_assignee_or_creator_actor(self):
  t=task(cl=CUT,asignados=[{'id':'someone'}],actor_cierre='forged');o=run([t]);self.assertEqual(o['proyectos'][0]['finales']['actual']['valor'],1);self.assertIsNone(o['proyectos'][0]['actor_cierre']);self.assertIsNone(o['proyectos'][0]['aceptacion_entrega']);self.assertNotIn('finales',o['creadores'][0])
 def test_terminal_by_catalog_not_label(self):
  cat=copy.deepcopy(CAT);cat['listas']['list']['estados'][0]['type']='custom';t=task(cl=CUT,tipo_estado='custom');self.assertIsNone(run([t],cat=cat)['proyectos'][0]['finales']['actual']['valor']);self.assertIsNone(run([task(cl=CUT)],cat=cat)['proyectos'][0]['finales']['actual']['valor'])
 def test_unknown_not_zero(self):
  r=run([task(cr=CUT-d.timedelta(days=20))])['proyectos'][0]['creadas']['actual'];self.assertIsNone(r['valor']);self.assertEqual(r['observaciones'],0);self.assertTrue(r['cero_no_acredita_ausencia'])
 def test_ids_and_scopes_failclosed(self):
  self.assertEqual(run([task(),task()])['proyectos'],[]);self.assertEqual(run([task()],activos=set())['proyectos'],[]);self.assertEqual(run([task()],folders={'folder':['cliente','other']})['proyectos'],[])
  for args in [{'ids':{}},{'ps':set()}]:self.assertEqual(run([task()],**args)['creadores'],[])
 def test_invalid_future_dates_and_history_not_initial(self):
  for val in [None,False,'not-ms',-1,10**1000]:self.assertEqual(run([task(creada=val)])['creadores'],[])
  t=task(cl=CUT-d.timedelta(days=2),historial=[{'estado':'planning semanal','desde':'1','orden':0}]);o=run([t]);self.assertIsNone(o['proyectos'][0]['finales']['actual']['valor']);self.assertIsNone(o['creadores'][0]['rompen_semanal'])
 def test_future_naive_cut_denies(self):
  for cut in [CUT.replace(tzinfo=None),NOW+d.timedelta(seconds=1)]:
   with self.assertRaises(ValueError):run([],cut=cut)
 def test_dst_previous_window_utc_correct(self):
  cut=d.datetime(2026,10,26,10,tzinfo=MAD);o=run([],cut=cut,now=cut+d.timedelta(hours=1));w=o['ventanas']['anterior'];a=d.datetime.fromisoformat(w['desde_utc'].replace('Z','+00:00'));b=d.datetime.fromisoformat(w['hasta_utc'].replace('Z','+00:00'));self.assertEqual((b-a).total_seconds()/3600,169)
 def test_does_not_mutate_inputs(self):
  ts=[task()];before=copy.deepcopy(ts);run(ts);self.assertEqual(ts,before)
if __name__=='__main__':unittest.main()
