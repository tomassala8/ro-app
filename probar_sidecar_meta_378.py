import unittest,copy,json
from fuentes_paneles.meta_envelope_373 import proyectar
from fuentes_paneles.meta_mediciones_220 import proyectar_cache,descriptor
class Sidecar378(unittest.TestCase):
 def setUp(self):
  c=[{'cliente_id':'fixture','cuenta_id':'123','moneda':'EUR','zona':'Europe/Madrid','confirmada':True}]
  e={'request':{'cuenta_id':'123','level':'campaign','time_increment':1,'desde':'2026-10-01','hasta':'2026-10-02'},'account':{'id':'123','currency':'EUR','timezone_name':'Europe/Madrid'},'leido_utc':'2026-10-03T00:56:00+00:00','paginas_completas':True,'response':{'data':[{'campaign_id':'456','date_start':'2026-10-02','date_stop':'2026-10-02','spend':'1.2','actions':[{'action_type':'lead','value':'0'}]}]}}
  self.d=proyectar(e,c);self.cache={'cuenta':'act_123','moneda':'EUR','zona_horaria':'Europe/Madrid','leido':'2026-10-03 02:55','medicion_meta':descriptor('2026-10-03 02:55'),'mediciones_diarias_373':self.d}
 def dto(self,cache=None,cid='fixture',clock='2026-10-03T03:00:00+00:00'):return proyectar_cache(self.cache if cache is None else cache,cliente_id=cid,observado_hasta=clock)['mediciones_diarias_373']
 def test_valid_preserves_explicit_zero_not_qualified(self):
  r=self.dto()['filas_diarias'][0];self.assertEqual(r['leads'],0);self.assertEqual(r['medicion']['tipo_lead'],'lead');self.assertIn('no_cualificados',r['medicion']['unidad_contador']);self.assertEqual(r['gasto'],1.2)
 def test_no_external_client_no_projection(self):self.assertIsNone(proyectar_cache(self.cache)['mediciones_diarias_373'])
 def test_outer_context_mismatch_closed(self):
  for k,v in [('cuenta','act_999'),('moneda','USD'),('zona_horaria','America/New_York')]:
   c=copy.deepcopy(self.cache);c[k]=v;self.assertIsNone(self.dto(c))
  self.assertIsNone(self.dto(cid='foreign'))
 def test_legacy_not_promoted(self):
  c=copy.deepcopy(self.cache);del c['medicion_meta'];self.assertIsNone(self.dto(c))
 def test_missing_fields_not_fill_zero(self):
  r=self.dto()['filas_diarias'][0];self.assertIsNone(r['clics']);self.assertNotIn('clics',r['medicion']['campos_observados'])
 def test_unknown_secret_keys_dropped_all_levels(self):
  c=copy.deepcopy(self.cache);s=c['mediciones_diarias_373'];s['secret']='fixture-secret';s['request']['access_token']='fixture-secret';s['filas_diarias'][0]['url']='https://x?token=fixture-secret';s['filas_diarias'][0]['medicion']['secret']='fixture-secret'
  out=self.dto(c);self.assertIsNotNone(out);self.assertNotIn('fixture-secret',json.dumps(out));self.assertNotIn('url',json.dumps(out))
 def test_duplicate_campaign_day_rejected(self):
  self.d['filas_diarias'].append(copy.deepcopy(self.d['filas_diarias'][0]));self.assertIsNone(self.dto())
 def test_invalid_snapshot_and_future_clocks(self):
  for clock in ['2026-10-03T00:55:00+00:00','2026-10-03T03:00:00', 'mal']:
   self.assertIsNone(self.dto(clock=clock))
 def test_bad_row_dates_and_channels(self):
  for k,v in [('desde','2026-02-30'),('nivel','ad'),('fuente','legacy'),('unidad_contador','leads_cualificados')]:
   c=copy.deepcopy(self.cache);c['mediciones_diarias_373']['filas_diarias'][0]['medicion'][k]=v;self.assertIsNone(self.dto(c))
 def test_currency_and_zone_metadata_mismatch(self):
  for k,v in [('moneda','USD'),('zona','America/New_York'),('cuenta_id','999')]:
   c=copy.deepcopy(self.cache);c['mediciones_diarias_373']['filas_diarias'][0]['medicion'][k]=v;self.assertIsNone(self.dto(c))
 def test_fields_types_presence_and_event_compatible(self):
  for v in [False,1.5,'0',float('inf'),-1]:
   c=copy.deepcopy(self.cache);c['mediciones_diarias_373']['filas_diarias'][0]['leads']=v;self.assertIsNone(self.dto(c))
  self.d['filas_diarias'][0]['medicion']['tipo_lead']='purchase';self.assertIsNone(self.dto())
 def test_conflict_all_unknown_preserved(self):
  r=self.d['filas_diarias'][0]
  for k in ['gasto','impresiones','alcance','frecuencia','clics','clics_enlace','leads']:r[k]=None
  r['medicion'].update(conflicto=True,tipo_lead=None,campos_observados=[])
  out=self.dto()['filas_diarias'][0];self.assertTrue(out['medicion']['conflicto']);self.assertIsNone(out['leads'])
 def test_error_strings_not_exported(self):
  self.d['errores']=['https://x?token=fixture-secret'];self.assertIsNone(self.dto())
 def test_no_mutation_and_naive_outer_stamp_preserved(self):
  before=copy.deepcopy(self.cache);d=self.dto();self.assertIsNotNone(d);self.assertEqual(before,self.cache);self.assertEqual(d['leido_utc'],'2026-10-03T00:56:00+00:00')
 def test_empty_sidecar_no_census_zero(self):
  self.d['filas_diarias']=[];out=self.dto();self.assertEqual(out['filas_diarias'],[]);self.assertFalse(out['cobertura']['completa_leads'])
if __name__=='__main__':unittest.main()
