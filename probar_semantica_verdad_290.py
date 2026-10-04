import copy,importlib.util,json,pathlib,sys,tempfile,types,unittest,contextlib,io
from datetime import date,timedelta
from fuentes_paneles.meta_mediciones_220 import fila
from fuentes_verdad.semantica_paid_290 import evaluar_publicidad
APP=pathlib.Path(__file__).resolve().parent
H='2026-10-03';W={'7d':['2026-09-26','2026-10-02']}
def typed(leads=0):
 rows=[]
 for i in range(7):
  d=(date(2026,9,26)+timedelta(days=i)).isoformat();v=fila({'date_start':d,'date_stop':d,'spend':'20','actions':[{'action_type':'lead','value':str(leads)}]},'2026-10-03T08:00:00Z','account')
  rows.append({'d':d,'gasto_meta':v['gasto'],'leads_meta':v['leads'],'medicion':v['medicion']})
 return {'cliente_id':'fixture','cuenta_meta':{'moneda':'EUR'},'serie':rows,'severidad':'critico','cuello':['integracion','ads'],'gasto':{'7d':140},'leads':{'7d':None}}
class FixedDate(date):
 @classmethod
 def today(cls):return cls(2026,10,3)
def run_main(cap,crm=None,client=None,alarms=None):
 spec=importlib.util.spec_from_file_location('verdad290_fixture',APP/'fuentes_verdad/generar_verdad.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 old=sys.modules.get('clientes_activos');stub=types.ModuleType('clientes_activos');stub.es_baja_id=lambda cid:False;stub.estado=lambda:{'activos':[{'id':'fixture','tipo':'recurrente'}]};sys.modules['clientes_activos']=stub
 try:
  with tempfile.TemporaryDirectory(prefix='verdad290_') as td:
   root=pathlib.Path(td);data=root/'data';data.mkdir();m.AQUI=root;m.DATA=data;m.SALIDA=data/'verdad';m.date=FixedDate
   files={'clientes.json':[{'id':'fixture','nombre':'Cliente sintético',**(client or {})}], 'personas.json':[{'id':'fixture_account','estado':'activo','activo':True,'puestos':['account']}],'asignaciones.json':[{'cliente_id':'fixture','persona_id':'fixture_account','silla':'account'}],'alarmas.json':alarms or [],'captacion/captacion.json':{'clientes':[cap],'ventanas':W},'crm/crm.json':{'subcuentas':[{'cliente_id':'fixture',**(crm or {})}]}}
   for name,d in files.items():p=data/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d))
   with contextlib.redirect_stdout(io.StringIO()):m.main()
   return json.loads((m.SALIDA/'clientes.json').read_text())
 finally:
  if old is None:sys.modules.pop('clientes_activos',None)
  else:sys.modules['clientes_activos']=old
class Test(unittest.TestCase):
 def test_normalizer_real_positive_zero_signal(self):
  r=evaluar_publicidad({},typed(),W,H);self.assertEqual(r['estado'],'medido');self.assertTrue(r['publicidad_sin_eventos_lead']);self.assertEqual(r['eventos_lead'],0)
 def test_positive_events_no_zero_signal(self):self.assertFalse(evaluar_publicidad({},typed(2),W,H)['publicidad_sin_eventos_lead'])
 def test_unknown_not_zero(self):
  for val in [None,False,'0',float('nan'),-1,10**1000]:
   k=typed();k['serie'][0]['leads_meta']=val;self.assertEqual(evaluar_publicidad({},k,W,H)['estado'],'sin_dato')
 def test_missing_duplicate_wrongwindow(self):
  for edit in [lambda k:k['serie'].pop(),lambda k:k['serie'].__setitem__(0,k['serie'][1]),lambda k:k['serie'][0]['medicion'].__setitem__('desde','2026-09-25')]:
   k=typed();edit(k);self.assertFalse(evaluar_publicidad({},k,W,H)['publicidad_sin_eventos_lead'])
  self.assertEqual(evaluar_publicidad({},typed(),{'7d':['2026-09-25','2026-10-01']},H)['estado'],'sin_dato')
 def test_commerce_errors_future_fields(self):
  self.assertFalse(evaluar_publicidad({'tienda_online':True},typed(),W,H)['publicidad_sin_eventos_lead'])
  for field,val in [('fecha_lectura','2026-10-04'),('fuente','cache_legacy'),('nivel','campaign'),('campos_observados',['leads']),('campos_observados',[{}]),('tipo_lead','purchase')]:
   k=typed();k['serie'][0]['medicion'][field]=val;self.assertEqual(evaluar_publicidad({},k,W,H)['estado'],'sin_dato')
  for edit in [lambda k:k['serie'][0].__setitem__('error',True),lambda k:k['cuenta_meta'].__setitem__('moneda','USD')]:
   k=typed();edit(k);self.assertFalse(evaluar_publicidad({},k,W,H)['publicidad_sin_eventos_lead'])
 def test_main_legacy_no_critical_or_health_bonus(self):
  for val in [None,0,False]:
   out=run_main({'cliente_id':'fixture','gasto':{'7d':180},'leads':{'7d':val},'severidad':'critico','cuello':['ads']},{'leads_meta_7d':20,'leads_ghl_7d':0});r=out['clientes'][0];self.assertIsNone(r['fuga_integracion']);self.assertFalse(any('gastados' in x or 'Captación con problemas'in x for x in r['motivos']));self.assertIsNone(r['salud']);self.assertIsNone(r['leads_ghl_7d']);self.assertEqual(r['gravedad'],'sin_dato');self.assertEqual(out['resumen']['sin_dato'],1)
 def test_main_measured_signal_no_sales_health(self):
  out=run_main(typed());r=out['clientes'][0];self.assertEqual(r['gravedad'],'critico');self.assertTrue(any('eventos lead Meta acreditados' in x for x in r['motivos']));self.assertIsNone(r['salud']);self.assertNotIn('gasto',r['meta_medicion_290']);self.assertEqual(r['leads_meta_7d'],0)
 def test_main_commerce_no_ads_critical(self):self.assertNotEqual(run_main(typed(),client={'tipo_negocio':'tienda_online'})['clientes'][0]['gravedad'],'critico')
 def test_main_preserves_other_positive_signal(self):
  out=run_main({'cliente_id':'fixture','severidad':'critico','cuello':['ads']},client={'semaforo':'crítico'},alarms=[{'cliente_id':'fixture','tipo':'Sin responder','texto':'lleva 12 días laborables'}]);r=out['clientes'][0];self.assertEqual(r['gravedad'],'critico');self.assertTrue(any('12 días' in x for x in r['motivos']));self.assertTrue(any('account' in x for x in r['motivos']))
 def test_main_counters_not_cohort_even_large_gap(self):
  r=run_main({'cliente_id':'fixture'},{'leads_meta_7d':120,'leads_ghl_7d':3})['clientes'][0];self.assertEqual(r['leads_meta_7d'],120);self.assertEqual(r['leads_ghl_7d'],3);self.assertIsNone(r['fuga_integracion']);self.assertEqual(r['integracion_medicion']['estado'],'sin_dato')
if __name__=='__main__':unittest.main()
