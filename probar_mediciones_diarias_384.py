import copy, unittest
from fuentes_paneles.meta_envelope_373 import proyectar
from fuentes_captacion.mediciones_diarias_384 import resumir
class Diario(unittest.TestCase):
 def setUp(self):
  self.ctx={'cuenta':'act_123','moneda':'EUR','zona_horaria':'America/Los_Angeles','medicion_meta':{'version':'220.1','origen':'api_meta','observacion_campos':'presencia_validada'}}
  cat=[{'cliente_id':'ok','cuenta_id':'123','moneda':'EUR','zona':'America/Los_Angeles','confirmada':True}]
  env={'request':{'cuenta_id':'123','level':'campaign','time_increment':1,'desde':'2026-10-01','hasta':'2026-10-02'},'account':{'id':'123','currency':'EUR','timezone_name':'America/Los_Angeles'},'leido_utc':'2026-10-04T00:00:00+00:00','paginas_completas':True,'response':{'data':[{'campaign_id':str(c),'account_id':'123','date_start':d,'date_stop':d,'spend':'3','impressions':'10','clicks':'2','actions':[{'action_type':'lead','value':'2'}]} for c in (1,2) for d in ('2026-10-01','2026-10-02')]}}
  self.doc=proyectar(env,cat)
 def run_d(self,doc=None,ctx=None,cid='ok'):
  return resumir(self.doc if doc is None else doc,self.ctx if ctx is None else ctx,cid,'2026-10-04T00:00:01+00:00')
 def test_observado(self):
  r=self.run_d();self.assertEqual(r['leads_observados'],8);self.assertEqual(r['gasto_observado'],12);self.assertEqual(r['nivel'],'campaign_diario');self.assertIsNone(r['leads_calificados']);self.assertIsNone(r['ventas']);self.assertNotIn('cuenta_id',r)
 def test_ausencia_no_cero(self):
  d=copy.deepcopy(self.doc);d['filas_diarias']=[r for r in d['filas_diarias'] if r['dia']=='2026-10-01'];r=self.run_d(d);self.assertIsNone(r['leads_observados']);self.assertIsNone(r['gasto_observado']);self.assertEqual(r['dias'][1]['filas_recibidas'],0)
 def test_campo_ausente(self):
  d=copy.deepcopy(self.doc);r=d['filas_diarias'][0];r['leads']=None;r['medicion']['campos_observados'].remove('leads');r['medicion']['tipo_lead']=None;o=self.run_d(d);self.assertIsNone(o['leads_observados']);self.assertEqual(o['gasto_observado'],12)
 def test_tipo_mixto(self):
  d=copy.deepcopy(self.doc);d['filas_diarias'][0]['medicion']['tipo_lead']='onsite_web_lead';self.assertIsNone(self.run_d(d)['leads_observados'])
 def test_identidad(self):
  self.assertIsNone(self.run_d(cid='otro'));c=copy.deepcopy(self.ctx);c['zona_horaria']='Europe/Madrid';self.assertIsNone(self.run_d(ctx=c))
 def test_whitelist(self):
  d=copy.deepcopy(self.doc);d['secret']='PRIVATE';d['filas_diarias'][0]['start_url']='PRIVATE';self.assertNotIn('PRIVATE',str(self.run_d(d)))
 def test_cero_explicito(self):
  d=copy.deepcopy(self.doc)
  for r in d['filas_diarias']:r['leads']=0;r['gasto']=0
  r=self.run_d(d);self.assertEqual(r['leads_observados'],0);self.assertEqual(r['gasto_observado'],0)
 def test_paginacion_incompleta(self):
  d=copy.deepcopy(self.doc);d['cobertura']['paginas_completas']=False;self.assertFalse(self.run_d(d)['paginas_completas']);self.assertEqual(self.run_d(d)['cobertura'],'filas_recibidas_no_censo')
if __name__=='__main__':unittest.main()
