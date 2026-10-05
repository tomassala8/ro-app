import ast, copy, importlib.util, json, re, unittest
from pathlib import Path
from fuentes_captacion.cpm_referencia_417 import proyectar, KEY
APP=Path(__file__).resolve().parent
class CPM(unittest.TestCase):
 def setUp(self):
  self.c={'cuenta':'act_123','moneda':'EUR','leido':'2026-10-03 04:48','errores':[],'periodos':{'2026-09-26|2026-10-02':{'cuenta':{'gasto':20.,'impresiones':1000,'clics':99}}}}
 def p(self,c=None,**kw):return proyectar(c or self.c,kw.pop('cliente_id','cid'),kw.pop('cuenta_id','123'),kw.pop('ventana',['2026-09-26','2026-10-02']),kw.pop('moneda','EUR'),**{'activo':True,'cuenta_unica':True,**kw})
 def test_reference_whitelist(self):
  self.c['token']='secret_fixture';self.c['periodos']['2026-09-26|2026-10-02']['ad']={'x':{'gasto':999}}
  x=self.p();self.assertEqual(x['coste_por_mil'],20);self.assertFalse(x['medicion_actual']);self.assertIsNone(x['zona']);self.assertNotIn('secret',json.dumps(x));self.assertNotIn('clics',x)
 def test_identity_currency_scope(self):
  for kw in [{'cuenta_id':'456'},{'moneda':'USD'},{'activo':False},{'cuenta_unica':False},{'error_fuente':True},{'cliente_id':'../bad'}]:self.assertIsNone(self.p(**kw))
 def test_windows(self):
  for w in [['2026-09-25','2026-10-02'],['2026-09-27','2026-10-03'],['2026-02-30','2026-03-08']]:self.assertIsNone(self.p(ventana=w))
 def test_invalid_unknown_and_explicitzero(self):
  for field in ['gasto','impresiones']:
   for v in [None,'1',True,-1,float('inf')]:
    c=copy.deepcopy(self.c);c['periodos']['2026-09-26|2026-10-02']['cuenta'][field]=v;self.assertIsNone(self.p(c))
  c=copy.deepcopy(self.c);c['periodos']['2026-09-26|2026-10-02']['cuenta']['gasto']=0;self.assertEqual(self.p(c)['coste_por_mil'],0)
  c['periodos']['2026-09-26|2026-10-02']['cuenta']['impresiones']=0;self.assertIsNone(self.p(c))
 def test_error_and_date(self):
  for patch in [{'errores':['legacyerror']},{'_error':'denied'},{'leido':'private_fixture'},{'leido':'2026-10-02 22:00'},{'periodos':{}},{'leido':'2099-10-03 04:48'}]:self.assertIsNone(self.p({**self.c,**patch}))
 def test_offset_no_normalizado(self):
  for offset in ['+02:99','-02:60','+15:00','-14:01','+24:00']:
   self.assertIsNone(self.p({**self.c,'leido':'2026-10-03T04:48:00'+offset}))
  for offset in ['+14:00','-14:00','+02:59','Z','']:
   x=self.p({**self.c,'leido':'2026-10-03T04:48:00'+offset});self.assertIsNotNone(x);self.assertIsNone(x['zona'])
 def test_real_backend_recorte(self):
  t=ast.parse((APP/'servir.py').read_text());ns={'re':re}
  nodes=[n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in ('CLAVES_INVERSION','SERIES_CON_GASTO') for x in n.targets) or isinstance(n,ast.FunctionDef) and n.name in ('recortar_doc','_quita') or isinstance(n,ast.ClassDef) and n.name=='ClaveValor']
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual servir AST>','exec'),ns)
  result=ns['recortar_doc']({'clientes':[{'cliente_id':'cid',KEY:self.p(),'metric':4}]},[ns['CLAVES_INVERSION']]);self.assertNotIn(KEY,result['clientes'][0]);self.assertEqual(result['clientes'][0]['metric'],4)
 def test_generator_hook_ast_only(self):
  tree=ast.parse((APP/'fuentes_captacion/generar_captacion.py').read_text());calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='cpm_referencia417'];self.assertEqual(len(calls),1)
  self.assertIn('ventanas',ast.unparse(calls[0]));self.assertIn('es_activo_id',ast.unparse(calls[0]));self.assertIn('cuenta_unica',ast.unparse(calls[0]));self.assertIn(KEY,(APP/'fuentes_captacion/generar_captacion.py').read_text())
 def test_enrichment_preserves_snapshot_otherfields(self):
  p=APP.parent/'RECUPERACION_CODEX_2026-10-03/preparar_cpm_referencia_417.py';sp=importlib.util.spec_from_file_location('pre417',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
  dto={'generado':'old','ventanas':{'7d':['2026-09-26','2026-10-02']},'clientes':[{'cliente_id':'cid','id_captacion':'source','unchanged':[1,2]}]};before=copy.deepcopy(dto)
  x=m.enriquecer(dto,{'clientes':[{'id':'source','meta':{'cuenta_id':'123','moneda':'EUR'}}]},[{'id':'cid'}],{'cid':{'id':'cid','ids':{'captacion':'source'}}},{'cid':self.c},{'cid'});self.assertEqual(x['generado'],'old');self.assertEqual(x['clientes'][0]['unchanged'],[1,2]);self.assertEqual(dto,before);self.assertEqual(x['clientes'][0][KEY]['coste_por_mil'],20)
  x=m.enriquecer(dto,{'clientes':[{'id':'source'},{'id':'source'}]},[{'id':'cid'}],{'cid':{'id':'cid','ids':{'captacion':'source'}}},{'cid':self.c},{'cid'});self.assertNotIn(KEY,x['clientes'][0])
if __name__=='__main__':unittest.main()
