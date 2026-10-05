import copy, unittest
from cerebro_operativo import generar
from paid_mediciones_331 import ventana
from probar_cerebro_operativo import documentos,acreditar_paid331,reglas,HOY
class Paid331(unittest.TestCase):
 def fixture(self):
  a,c,o=documentos();a['ventanas']['7d_prev']=['2026-09-19','2026-09-25'];a['clientes'][0].update(leads={'7d':5,'7d_prev':10},gasto={'7d':200,'7d_prev':200});acreditar_paid331(a);return a,c,o
 def test_legacy_current_snapshot_has_no_cpl_or_no_leads_diagnosis(self):
  a,c,o=self.fixture();a['clientes'][0].pop('serie');rs=reglas(generar(a,c,o,HOY));self.assertIn('paid_validar_medicion',rs);self.assertFalse({'paid_sin_leads','paid_cpl_tendencia','paid_cpl_objetivo'}&rs)
 def test_confirmed_zero_and_not_zero_without_lead_event(self):
  a,c,o=self.fixture();k=a['clientes'][0];k['leads']['7d']=0;acreditar_paid331(a);self.assertIn('paid_sin_leads',reglas(generar(a,c,o,HOY)))
  k['serie'][7]['medicion']['tipo_lead']='purchase';self.assertNotIn('paid_sin_leads',reglas(generar(a,c,o,HOY)))
 def test_ecommerce_never_called_leads(self):
  a,c,o=self.fixture();a['clientes'][0]['tipo_negocio']='tienda_online';self.assertNotIn('paid_cpl_tendencia',reglas(generar(a,c,o,HOY)));self.assertIn('paid_validar_medicion',reglas(generar(a,c,o,HOY)))
 def test_errors_exact_real_field_no_content_leak(self):
  for field in ['error','errores']:
   a,c,o=self.fixture();a['clientes'][0]['cuenta_meta'][field]='SECRETO-FIXTURE';r=generar(a,c,o,HOY);self.assertFalse(any(x['area']=='paid' for x in r['recomendaciones']));self.assertNotIn('SECRETO-FIXTURE',str(r))
 def test_periods_ids_currency_missing_duplicate_stale(self):
  for change in [lambda k:k['serie'].append(copy.deepcopy(k['serie'][7])),lambda k:k['serie'].pop(),lambda k:k['serie'][7]['medicion'].update(desde='2026-09-25'),lambda k:k['serie'][7]['medicion'].update(cuenta_id='456'),lambda k:k['serie'][7]['medicion'].update(fecha_lectura='2026-09-01 01:00'),lambda k:k['serie'][7]['medicion'].update(fecha_lectura='2026-10-04 01:00')]:
   a,c,o=self.fixture();change(a['clientes'][0]);self.assertNotIn('paid_cpl_tendencia',reglas(generar(a,c,o,HOY)))
  a,c,o=self.fixture();a['clientes'][0]['cuenta_meta']['moneda']='USD';self.assertIsNone(ventana(a['clientes'][0],a['ventanas']['7d'],HOY)['gasto'])
 def test_fractional_events_or_missing_spend_not_inferred(self):
  a,c,o=self.fixture();a['clientes'][0]['serie'][7]['leads_meta']=4.5;self.assertNotIn('paid_cpl_tendencia',reglas(generar(a,c,o,HOY)))
  a,c,o=self.fixture();a['clientes'][0]['serie'][7].pop('gasto_meta');self.assertNotIn('paid_cpl_tendencia',reglas(generar(a,c,o,HOY)))
 def test_goal_confirmed_exact_month_from_observed_cost_not_legacy_ref(self):
  a,c,o=self.fixture();a['generado']='2026-10-10';a['datos_hasta']='2026-10-09';a['ventanas']={'7d':['2026-10-03','2026-10-09']};acreditar_paid331(a)
  for d in a['clientes'][0]['serie']:d['medicion']['fecha_lectura']='2026-10-10 01:00'
  a['clientes'][0]['cpl_resumen']={'ref':1,'fiable':False};o={'generado':'2026-10-10','clientes':[{'cliente_id':'fixture','objetivo':{'cpl_objetivo':10,'confirmado':True,'periodo':'2026-10'}}]}
  self.assertIn('paid_cpl_objetivo',reglas(generar(a,None,o,'2026-10-10')))
  o['clientes'][0]['objetivo']['confirmado']=False;self.assertNotIn('paid_cpl_objetivo',reglas(generar(a,None,o,'2026-10-10')))
 def test_scope_only_inputs_and_no_mutation_crm_preserved(self):
  a,c,o=self.fixture();c['subcuentas'][0]['velocidad']={'en_1h':1,'juzgables':2};before=copy.deepcopy((a,c,o));r=generar(a,c,o,HOY);self.assertIn('crm_primera_hora',reglas(r));self.assertEqual((a,c,o),before);self.assertEqual({x['cliente_id'] for x in r['recomendaciones']},{'fixture'});self.assertEqual(generar(None,None,None,HOY)['recomendaciones'],[])
if __name__=='__main__':unittest.main()
