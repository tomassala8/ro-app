"""Función meta_leer REAL vía AST; transporte stub sin importar productor/bootstrap."""
import ast,copy,json,unittest,urllib.parse
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
from types import SimpleNamespace
from fuentes_paneles import meta_mediciones_220 as M
class Clock(datetime):
 @classmethod
 def now(cls,tz=None):return datetime(2026,10,3,0,56,tzinfo=timezone.utc)
class Conexion373(unittest.TestCase):
 def setUp(self):
  self.info={'account_id':'123','account_status':1,'currency':'EUR','timezone_name':'Europe/Madrid'}
  self.rows=[{'account_id':'123','campaign_id':'456','date_start':'2026-10-02','date_stop':'2026-10-02','spend':'1.2','actions':[{'action_type':'lead','value':'0'}]}]
  self.calls=[];self.error=None
 def run_reader(self):
  funcs=[n for n in ast.parse(Path(__file__).with_name('fuentes_paneles').joinpath('generar_paneles.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='meta_leer']
  def paginar(token,path,**q):
   self.calls.append((path,copy.deepcopy(q)))
   return (copy.deepcopy(self.rows),self.error) if q.get('time_increment')==1 else ([],None)
  ns={'META220':M,'get_json':lambda url:copy.deepcopy(self.info),'meta_paginar':paginar,'datetime':Clock,'date':date,'timedelta':timedelta,'urllib':urllib,'json':json,'AHORA':'2026-10-03 02:56','HOY':date(2026,10,3),'DESDE_SERIE':'2026-10-01','PERIODOS':[],'C':SimpleNamespace(sanear=lambda x:x)}
  exec(compile(ast.Module(body=funcs,type_ignores=[]),'meta_leer_AST_real','exec'),ns)
  return ns['meta_leer']('fixture-token-private',{'id':'fixture','meta':'act_123','meta_nombre':'Fixture'})
 def test_future_read_preserves_daily_descriptor_and_legacy_vector(self):
  d=self.run_reader();r=d['mediciones_diarias_373']['filas_diarias'][0]
  self.assertEqual(r['medicion']['tipo_lead'],'lead');self.assertEqual(r['medicion']['moneda'],'EUR');self.assertEqual(r['medicion']['zona'],'Europe/Madrid');self.assertEqual(r['leads'],0)
  self.assertEqual(d['gasto_serie']['456']['2026-10-02'],[1.2,None,None,None,0]);self.assertNotIn('fixture-token-private',json.dumps(d))
 def test_missing_actions_remains_unknown_purchase_not_lead(self):
  for action in [None,[{'action_type':'purchase','value':'8'}]]:
   self.rows[0]['actions']=action;d=self.run_reader();self.assertIsNone(d['mediciones_diarias_373']['filas_diarias'][0]['leads']);self.assertIsNone(d['gasto_serie']['456']['2026-10-02'][4])
 def test_conflicting_campaign_day_is_unknown_both_views(self):
  self.rows.append({**self.rows[0],'spend':'9'});d=self.run_reader();r=d['mediciones_diarias_373']['filas_diarias'][0];self.assertTrue(r['medicion']['conflicto']);self.assertIsNone(r['gasto']);self.assertEqual(d['gasto_serie']['456']['2026-10-02'],[None]*5)
 def test_partial_pagination_no_secret_error_export(self):
  self.error='url https://graph.example?access_token=fixture-token-private';d=self.run_reader();self.assertFalse(d['mediciones_diarias_373']['cobertura']['paginas_completas']);self.assertNotIn('access_token',json.dumps(d));self.assertNotIn('fixture-token-private',json.dumps(d))
 def test_zone_account_date_not_fake_madrid(self):
  self.info['timezone_name']='America/Los_Angeles';d=self.run_reader();self.assertEqual(d['mediciones_diarias_373']['request']['hasta'],'2026-10-02');self.assertEqual(d['mediciones_diarias_373']['zona'],'America/Los_Angeles');self.assertEqual(json.loads(next(q['time_range'] for _,q in self.calls if q.get('time_increment')==1))['until'],'2026-10-02')
 def test_invalid_missing_timezone_does_not_invent_typed_context(self):
  for zone in [None,'not/a-zone']:
   self.info['timezone_name']=zone;self.assertIsNone(self.run_reader()['mediciones_diarias_373'])
 def test_account_response_discordant_no_typed(self):
  self.info['account_id']='999';d=self.run_reader();self.assertIsNone(d['mediciones_diarias_373']);self.assertIn('mediciones_diarias_373: contexto_o_periodo_no_acreditado',d['errores'])
 def test_error_account_no_urls(self):
  self.info={'_error':403,'_msg':'url?token=fixture-token-private'};d=self.run_reader();self.assertNotIn('fixture-token-private',json.dumps(d));self.assertEqual(d['_error'],'lectura_cuenta_meta_fallida')
 def test_sensitive_context_strings_not_public_fields(self):
  self.info['currency']='https://x?token=fixture-token-private';self.info['timezone_name']='https://x?token=fixture-token-private';d=self.run_reader();self.assertIsNone(d['mediciones_diarias_373']);self.assertIsNone(d['moneda']);self.assertIsNone(d['zona_horaria']);self.assertNotIn('fixture-token-private',json.dumps(d))
if __name__=='__main__':unittest.main()
