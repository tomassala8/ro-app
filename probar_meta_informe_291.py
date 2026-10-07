import unittest,copy
import meta_informe_291 as M
import informe_word_api as W
class Test(unittest.TestCase):
 def setUp(self):
  self.p={'desde':'2026-09-01','hasta':'2026-09-30'};self.f={'cuenta':{'id':'act_1'},'moneda':'EUR','hora':'2026-10-02 12:00'};self.a={'leads':12,'gasto':24,'medicion':{'version':'220.1','fuente':'meta_insights','nivel':'account','periodo_valido':True,'desde':'2026-09-01','hasta':'2026-09-30','fecha_lectura':'2026-10-02 12:00','cohorte':'resultados_meta_sin_union_crm_ni_cualificacion_ro','campos_observados':['leads','gasto'],'tipo_lead':'lead','cuenta_id':'1','moneda':'EUR'}}
 def calc(self,a=None,f=None):return M.medir(a or self.a,f or self.f,self.p,'2026-10-03')
 def test_legacy(self):r=self.calc({'leads':201,'cpl':2,'gasto':402});self.assertEqual(r['resultados'],201);self.assertIsNone(r['leads']);self.assertIsNone(r['cpl'])
 def test_zero(self):self.assertIsNone(self.calc({'leads':0})['resultados'])
 def test_typed(self):r=self.calc();self.assertEqual((r['resultados'],r['leads'],r['cpl']),(12,12,2))
 def test_stale_semantic(self):
  for k,v in [('tipo_lead','purchase'),('cuenta_id','other'),('hasta','2026-09-29'),('nivel','campaign'),('fecha_lectura','2026-10-04 12:00'),('fecha_lectura','2026-10-02 25:00')]:
   a=copy.deepcopy(self.a);a['medicion'][k]=v;self.assertIsNone(self.calc(a)['leads'])
 def test_currency(self):a=copy.deepcopy(self.a);a['medicion']['moneda']='USD';self.assertIsNone(self.calc(a)['cpl'])
 def test_store(self):self.assertIsNone(M.medir(self.a,self.f,self.p,'2026-10-03',{'tienda_online':True})['leads'])
 def test_word(self):
  r=W.adaptar({'cliente_id':'c','meta':{'actual':{'leads':201,'gasto':999}},'fuentes':{'meta':self.f}},'c',self.p,{}, {'meta'},'2026-10-03');s=str(r);self.assertIn('201',s);self.assertIn('Resultados Meta',s);self.assertNotIn('Leads registrados',s);self.assertNotIn('999',s)
 def test_word_zero(self):r=W.adaptar({'cliente_id':'c','meta':{'actual':{'leads':0}},'fuentes':{'meta':self.f}},'c',self.p,{}, {'meta'},'2026-10-03');self.assertEqual(r['tablas'],[])
if __name__=='__main__':unittest.main()
