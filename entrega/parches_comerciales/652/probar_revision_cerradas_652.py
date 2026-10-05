import importlib.util,unittest,json,hashlib
from pathlib import Path
R=Path(__file__).parent;APP=R
def load(name):
    spec=importlib.util.spec_from_file_location(name,R/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
OLD=load('oportunidades_cerradas_original');NEW=load('oportunidades_cerradas')
class Fake:
    def __init__(self,pages):self.pages=pages;self.calls=[]
    def req(self,loc,method,path,**q):
        self.calls.append((loc,method,path,q));pages=self.pages.get(q['status'],[{'opportunities':[],'meta':{'total':0}}]);i=sum(x[3]['status']==q['status'] for x in self.calls)-1
        return pages[min(i,len(pages)-1)]
def row(**kw):return {'id':'fixture','status':'won',**kw}
class Revision652(unittest.TestCase):
    def read(self,pages,old=False,**kw):return (OLD if old else NEW).collect(Fake(pages),'loc',hoy='2026-10-03',max_pages=3,**kw)
    def test_nan_before_complete_after_unknown(self):
        p={'won':[{'opportunities':[],'meta':{'total':float('nan')}}]};self.assertTrue(self.read(p,True)['cobertura']['completa']);d=self.read(p);self.assertFalse(d['cobertura']['completa']);self.assertIn('total_invalido',d['cobertura']['estados']['won']['incidencias'])
    def test_total_invalid_typed(self):
        for total in (True,-1,float('inf'),1.5,'0',None,2**53):
            d=self.read({'won':[{'opportunities':[],'meta':{'total':total}}]});self.assertFalse(d['cobertura']['completa']);self.assertIn('total_invalido',d['cobertura']['estados']['won']['incidencias']);self.assertNotIn('NaN',json.dumps(d,allow_nan=False))
    def test_empty_meta_array_before_complete_after_invalid(self):
        p={'won':[{'opportunities':[],'meta':[]}]};self.assertTrue(self.read(p,True)['cobertura']['completa']);self.assertFalse(self.read(p)['cobertura']['completa'])
    def test_metadata_falsy_invalid(self):
        for meta in (False,0,''):
            d=self.read({'won':[{'opportunities':[],'meta':meta}]});self.assertIn('metadatos_invalidos',d['cobertura']['estados']['won']['incidencias'])
    def test_location_collision_global_all_variants_removed(self):
        p={'won':[{'opportunities':[row(locationId='loc'),row(locationId='other')],'meta':{'total':2}}]};self.assertEqual(self.read(p,True)['conteos_observados']['won'],1);d=self.read(p,incluir_privado=True);self.assertEqual(d['conteos_observados']['won'],0);self.assertEqual(d['privado']['oportunidades'],[])
    def test_reverse_collision_also_removed(self):
        p={'won':[{'opportunities':[row(locationId='other'),row(locationId='loc')],'meta':{'total':2}}]};self.assertEqual(self.read(p)['conteos_observados']['won'],0)
    def test_wrong_status_collision_removed(self):
        d=self.read({'won':[{'opportunities':[row(),row(status='open')],'meta':{'total':2}}]});self.assertEqual(d['conteos_observados']['won'],0)
    def test_known_zero_retained_only_with_completed_source(self):
        d=self.read({});self.assertTrue(d['cobertura']['completa']);self.assertEqual(d['conteos_observados']['won'],0);self.assertIsNone(d['ratio_leads_ventas']);self.assertIsNone(d['cierres_del_periodo'])
    def test_omitted_metadata_backward_compatible(self):
        d=self.read({'won':[{'opportunities':[row()]},{'opportunities':[]}]});self.assertTrue(d['cobertura']['completa']);self.assertEqual(d['conteos_observados']['won'],1)
    def test_same_scope_none_explicit_location_replay(self):
        d=self.read({'won':[{'opportunities':[row(),row(locationId='loc')],'meta':{'total':1}}]});self.assertTrue(d['cobertura']['completa']);self.assertEqual(d['conteos_observados']['won'],1)
    def test_observed_rows_remain_partial_if_total_invalid(self):
        d=self.read({'won':[{'opportunities':[row(name='secret@example.test',monetaryValue=500)],'meta':{'total':float('inf')}}]});self.assertFalse(d['cobertura']['completa']);self.assertEqual(d['conteos_observados']['won'],1);self.assertNotIn('secret',json.dumps(d));self.assertNotIn('500',json.dumps(d))
    def test_stock_never_closure_sales(self):
        d=self.read({'won':[{'opportunities':[row(updatedAt='2026-10-02T09:00:00Z')],'meta':{'total':1}}]},incluir_privado=True);self.assertIsNone(d['privado']['oportunidades'][0]['fecha_cierre']);self.assertIsNone(d['ratio_leads_ventas']);self.assertIn('Stock observado',d['limite'])
if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Revision652)
    source=(APP/'pruebas_oportunidades_cerradas.py').read_text().replace('from fuentes_crm.oportunidades_cerradas import collect','collect = COLLECT_652')
    ns={'COLLECT_652':NEW.collect,'__name__':'regresion_existente_652'};exec(compile(source,'suite_original_sin_editar','exec'),ns)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ns['Pruebas']))
    result=unittest.TextTestRunner(verbosity=1).run(suite);raise SystemExit(not result.wasSuccessful())
