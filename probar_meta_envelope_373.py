import unittest,copy,json
from fuentes_paneles.meta_envelope_373 import proyectar
class Meta373(unittest.TestCase):
 def setUp(self):
  self.c=[{'cliente_id':'fixture','cuenta_id':'123','moneda':'EUR','zona':'Europe/Madrid','confirmada':True}]
  self.e={'request':{'cuenta_id':'123','level':'campaign','time_increment':1,'desde':'2026-10-01','hasta':'2026-10-02'},'account':{'id':'123','currency':'EUR','timezone_name':'Europe/Madrid'},'leido_utc':'2026-10-03T00:56:00+00:00','paginas_completas':True,'response':{'data':[{'campaign_id':'456','date_start':'2026-10-02','date_stop':'2026-10-02','spend':'1.2','actions':[{'action_type':'lead','value':'0'}]}]}}
 def test_explicit_zero_event_and_currency(self):
  d=proyectar(self.e,self.c);r=d['filas_diarias'][0];self.assertEqual(r['leads'],0);self.assertEqual(r['medicion']['tipo_lead'],'lead');self.assertEqual(r['medicion']['moneda'],'EUR');self.assertEqual(len(d['filas_diarias']),1)
 def test_empty_not_zero(self):
  self.e['response']['data']=[];self.assertEqual(proyectar(self.e,self.c)['filas_diarias'],[])
 def test_purchase_not_lead(self):
  self.e['response']['data'][0]['actions']=[{'action_type':'purchase','value':'12'}];self.assertIsNone(proyectar(self.e,self.c)['filas_diarias'][0]['leads'])
 def test_overlapping_variants_not_sum(self):
  self.e['response']['data'][0]['actions']=[{'action_type':'lead','value':'3'},{'action_type':'onsite_conversion.lead_grouped','value':'4'}];self.assertEqual(proyectar(self.e,self.c)['filas_diarias'][0]['leads'],3)
 def test_replay_not_double_sum(self):
  self.e['response']['data']*=2;self.assertEqual(len(proyectar(self.e,self.c)['filas_diarias']),1)
 def test_conflict_unknown(self):
  r=copy.deepcopy(self.e['response']['data'][0]);r['spend']='2';self.e['response']['data'].append(r);r=proyectar(self.e,self.c)['filas_diarias'][0];self.assertIsNone(r['gasto']);self.assertTrue(r['medicion']['conflicto'])
 def test_scope_duplicates_denied(self):
  for c in [self.c*2,[{**self.c[0],'confirmada':False}],[{**self.c[0],'cuenta_id':'999'}]]:
   with self.assertRaises(ValueError):proyectar(self.e,c)
 def test_account_currency_zone_discordance(self):
  for field,value in [('id','999'),('currency','USD'),('timezone_name','America/New_York')]:
   e=copy.deepcopy(self.e);e['account'][field]=value
   with self.assertRaises(ValueError):proyectar(e,self.c)
 def test_not_distribute_aggregate(self):
  self.e['response']['data'][0]['date_start']='2026-10-01';self.assertEqual(proyectar(self.e,self.c)['filas_diarias'],[])
 def test_future_period_and_naive_stamp(self):
  for e in [{**self.e,'leido_utc':'2026-10-03T01:00:00'}, {**self.e,'request':{**self.e['request'],'hasta':'2099-01-01'}}]:
   with self.assertRaises(ValueError):proyectar(e,self.c)
 def test_bad_counts_not_zero_and_secret_keys_not_exported(self):
  self.e['response']['data'][0].update(actions=[{'action_type':'lead','value':'1.5'}],access_token='fixture-secret',url='https://x?token=fixture-secret');d=proyectar(self.e,self.c);self.assertIsNone(d['filas_diarias'][0]['leads']);self.assertNotIn('fixture-secret',json.dumps(d))
 def test_partial_pages_not_complete(self):
  self.e['paginas_completas']=False;d=proyectar(self.e,self.c);self.assertFalse(d['cobertura']['paginas_completas']);self.assertFalse(d['cobertura']['completa_leads'])
if __name__=='__main__':unittest.main()
