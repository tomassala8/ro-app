"""Pruebas sin red/llavero: productor vía callbacks y wrappers AST reales."""
import ast,json,unittest
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
from fuentes_informe import meta_productor_298 as M
from meta_informe_291 import medir
P={'id':'x','desde':'2026-10-01','hasta':'2026-10-02','anterior':['2026-09-29','2026-09-30']}
PAY={'date_start':P['desde'],'date_stop':P['hasta'],'spend':'20','impressions':'0','actions':[{'action_type':'lead','value':'2'}]}
def proveedor(path,**q):
 if not path.endswith('/insights'):return {'currency':'EUR'}
 if q.get('time_increment'):return {'data':[{**PAY,'date_stop':P['desde']}]}
 if q.get('level')=='adset':return {'data':[{**PAY,'adset_id':'88','adset_name':'A'}]}
 return {'data':[PAY]}
class Tests298(unittest.TestCase):
 def test_fuente_cuenta_moneda_periodo_coste(self):
  out=M.leer(proveedor,'act_123',[P],'2026-10-03 10:00');r=M.periodo(out,P)
  z=medir(r['actual'],{'cuenta':{'id':'act_123'},'moneda':out['moneda']},P,'2026-10-03')
  self.assertTrue(z['typed']);self.assertEqual(z['cpl'],10);self.assertEqual(z['leads'],2)
 def test_payload_no_cambia_cuenta(self):
  def call(path,**q):
   r=proveedor(path,**q)
   return {'data':[{**x,'account_id':'999','currency':'USD'}for x in r['data']]}if 'data'in r else r
  out=M.leer(call,'act_123',[P],'2026-10-03 10:00');self.assertEqual(out['totales']['2026-10-01|2026-10-02']['medicion']['cuenta_id'],'123');self.assertEqual(out['moneda'],'EUR')
 def test_ausente_no_cero(self):
  def call(path,**q):return {'currency':'EUR'}if not path.endswith('/insights')else {'data':[{'date_start':P['desde'],'date_stop':P['hasta']}]}
  r=M.leer(call,'123',[P],'2026-10-03 10:00')['totales']['2026-10-01|2026-10-02'];self.assertIsNone(r['gasto']);self.assertIsNone(r['leads'])
 def test_cero_observado_preservado(self):
  def call(path,**q):return {'currency':'EUR'}if not path.endswith('/insights')else {'data':[{**PAY,'spend':'0','actions':[{'action_type':'lead','value':'0'}]}]}
  r=M.leer(call,'123',[P],'2026-10-03 10:00')['totales']['2026-10-01|2026-10-02'];self.assertEqual(r['gasto'],0);self.assertEqual(r['leads'],0)
 def test_duplicate_discordante_no_ultimo(self):
  def call(path,**q):return {'currency':'EUR'}if not path.endswith('/insights')else {'data':[PAY,{**PAY,'spend':'21'},PAY]}
  r=M.leer(call,'123',[P],'2026-10-03 10:00');self.assertIsNone(r['totales']['2026-10-01|2026-10-02']['gasto']);self.assertIn('periodo_meta_duplicado_discordante',r['errores'])
 def test_replay_no_doble_conteo(self):
  def call(path,**q):return {'currency':'EUR'}if not path.endswith('/insights')else {'data':[PAY,PAY]}
  r=M.leer(call,'123',[P],'2026-10-03 10:00');self.assertEqual(r['totales']['2026-10-01|2026-10-02']['leads'],2)
 def test_fuera_rango(self):
  def call(path,**q):return {'currency':'EUR'}if not path.endswith('/insights')else {'data':[{**PAY,'date_start':'2099-01-01','date_stop':'2099-01-02'}]}
  r=M.leer(call,'123',[P],'2026-10-03 10:00');self.assertEqual(r['totales'],{});self.assertTrue(r['errores'])
 def test_moneda_ausente_no_cpl(self):
  def call(path,**q):return {}if not path.endswith('/insights')else proveedor(path,**q)
  r=M.leer(call,'123',[P],'2026-10-03 10:00');self.assertIsNone(r['moneda']);self.assertIn('moneda_meta_sin_confirmar',r['errores'])
 def test_cuenta_invalida_no_lectura(self):
  def no(*a,**k):raise AssertionError('no debe consultar')
  self.assertIn('_error',M.leer(no,'fixture',[P],'2026-10-03'))
 def test_fecha_invalida(self):self.assertIn('_error',M.leer(proveedor,'123',[P],'fecha'))
 def test_paginacion_no_sigue_url_next(self):
  calls=[]
  def call(path,**q):
   calls.append((path,q));return {'data':[{}],'paging':{'next':'https://malicioso.invalid/token','cursors':{'after':'cursor1'}}}if len(calls)==1 else {'data':[{}]}
  rows,err=M.paginas(call,'/act_123/insights',level='account');self.assertIsNone(err);self.assertEqual(len(rows),2);self.assertEqual(calls[1][0],'/act_123/insights');self.assertEqual(calls[1][1]['after'],'cursor1')
 def test_cursor_repetido_finaliza(self):
  n=[]
  def call(*a,**q):n.append(1);return {'data':[],'paging':{'next':'x','cursors':{'after':'a'}}}
  self.assertIsNotNone(M.paginas(call,'/x')[1]);self.assertEqual(len(n),2)
 def test_cursor_ausente_no_finge_completo(self):self.assertIsNotNone(M.paginas(lambda *a,**q:{'data':[],'paging':{'next':'x'}},'/x')[1])
 def test_paginacion_acotada(self):
  n=[]
  def call(*a,**q):n.append(1);return {'data':[],'paging':{'next':'x','cursors':{'after':str(len(n))}}}
  self.assertIsNotNone(M.paginas(call,'/x')[1]);self.assertEqual(len(n),60)
 def test_payload_invalido(self):
  for r in ({'data':[None]},{'data':{}},{'_error':'token-secreto'},None):self.assertIsNotNone(M.paginas(lambda *a,**q:r,'/x')[1])
 def test_legacy_no_ceros_cpl_ni_mutacion(self):
  raw={'totales':{'2026-10-01|2026-10-02':{'gasto':10,'leads':0,'cpl':3}},'serie':{},'conjuntos':{}};old=deepcopy(raw);r=M.periodo(raw,P)
  self.assertEqual(raw,old);self.assertNotIn('cpl',r['actual']);self.assertIsNone(r['actual']['leads']);self.assertEqual(r['serie'][0][1:],[None,None]);self.assertEqual(r['actual']['medicion']['fuente'],'cache_legacy')
 def test_estado_no_confunde_missing_con_cero(self):
  self.assertEqual(M.estado_fuente({'actual':{'gasto':None}}),'dato');self.assertEqual(M.estado_fuente({'actual':{'gasto':0}}),'dato')
  r=M.periodo(M.leer(proveedor,'123',[P],'2026-10-03 10:00'),P)
  self.assertEqual(M.estado_fuente(r),'bien')
  r['actual']['gasto']=0;self.assertEqual(M.estado_fuente(r),'a_cero')
  r['errores']=['lectura incompleta'];self.assertEqual(M.estado_fuente(r),'dato')
 def test_medicion_diaria_falsa_no_revive_legacy_cero(self):
  raw={'totales':{},'serie':{'2026-10-01':[0,0]},'serie_mediciones':{'2026-10-01':{}},'conjuntos':{}}
  self.assertEqual(M.periodo(raw,P)['serie'][0][1:],[None,None])
 def test_fuente_exportada_y_consumidor291(self):
  cache=M.leer(proveedor,'act_123',[P],'2026-10-03 10:00');r=M.periodo(cache,P)
  f=M.fuente(r,cache,'2026-10-03 10:00',{'id':'act_123'},None)
  self.assertNotIn('errores',f);self.assertEqual(medir(r['actual'],f,P,'2026-10-03')['cpl'],10)
  r['errores']=['token privado potencial'];f=M.fuente(r,cache,None,{'id':'act_123'},None)
  self.assertNotIn('token privado',json.dumps(f));self.assertFalse(medir(r['actual'],f,P,'2026-10-03')['typed'])
 def test_wrappers_productor_real_ast(self):
  tree=ast.parse((Path(__file__).parent/'fuentes_informe/generar_informe.py').read_text());ns={'META298':M,'meta_get':lambda tk,path,**q:proveedor(path,**q),'PERIODOS':[P],'AHORA':'2026-10-03 10:00','C':SimpleNamespace(sanear=lambda x:x)}
  exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in {'meta_cliente','meta_periodo'}],type_ignores=[]),'AST298','exec'),ns)
  r=ns['meta_periodo'](ns['meta_cliente']('fixture','act_123'),P);self.assertEqual(r['actual']['medicion']['cuenta_id'],'123')
if __name__=='__main__':unittest.main()
