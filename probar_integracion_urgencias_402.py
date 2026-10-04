"""Integración aislada sin servidor, proveedor ni DB."""
import ast,io,json,os,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import urgencias_observadas_api_402 as B
import piloto_lectura as PIL
from probar_urgencias_observadas_api_402 import APIUrgencias402
class Integracion402(unittest.TestCase):
 def setUp(self):
  self.f=APIUrgencias402();self.f.setUp();self.addCleanup(self.f.doCleanups)
  class H:
   def _api_get(self,*args):return ('original',args[0])
   def api_post(self,*args):raise AssertionError('No escribir')
   def responder(self,status,body):return status,body
  B.enganchar(H,self.f.S);PIL.enganchar(H);self.h=H()
  for p in [patch.object(B,'SHA',self.f.sha),patch.object(B,'MANIFEST_SHA',self.f.msha),patch.object(B,'_fuentes',lambda:self.f.sources),patch.dict(os.environ,{B.ENV:str(self.f.path),'RO_PILOTO_LECTURA':'1'})]:p.start();self.addCleanup(p.stop)
 def get(self,q=None,r='ops',v=None):return self.h._api_get(B.RUTA,q or {},{'id':r},{'id':v or r})
 def test_pilot_exact_get_real_scope(self):
  status,d=self.get();self.assertEqual(status,200);self.assertEqual(d['abiertas_en_copia'],2);self.assertIsNone(d['urgencias_actuales'])
  status,d=self.get({'grupo':['finales']},r='a');self.assertEqual(status,200);self.assertEqual([x['tarea_id'] for x in d['filas']],['t2'])
  self.assertEqual(self.get({'cliente_id':['c2']},r='a')[0],403);self.assertEqual(self.get(r='a',v='ops')[0],403)
 def test_no_post_neighbor_or_extra_query(self):
  self.assertEqual(self.h.api_post(B.RUTA,{}, {}, {})[0],403);self.assertEqual(self.h._api_get(B.RUTA+'/extra',{}, {}, {})[0],403)
  for q in ({'yo':['ops']},{'grupo':['abiertas','finales']},{'grupo':['otro']},{'cliente_id':['../c1']}):self.assertEqual(self.get(q)[0],400)
 def test_revocation_through_hooks(self):
  self.f.act.clear();status,d=self.get();self.assertEqual(status,200);self.assertEqual(d['cliente_ids'],[]);self.assertEqual(d['filas'],[]);self.assertIsNone(d['abiertas_en_copia'])
  self.f.raw['personas'][0]['estado']='baja';self.assertEqual(self.get()[0],403)
 def test_hook_order_and_launcher_without_execution(self):
  root=Path(__file__).parent;tree=ast.parse((root/'servir.py').read_text());names=[]
  for n in tree.body:
   if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='enganchar' and isinstance(n.value.func.value,ast.Name):names.append(n.value.func.value.id)
  self.assertLess(names.index('URGENCIAS_OBSERVADAS_402'),names.index('PILOTO_LECTURA'))
  launcher=root.parent/'RECUPERACION_CODEX_2026-10-03'/'arrancar_revision_local.py';ns={'__file__':str(launcher)};nodes=[]
  for n in ast.parse(launcher.read_text()).body:
   if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr in ('chdir','execvpe'):continue
   nodes.append(n)
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'launcher_without_execute','exec'),ns)
  self.assertEqual(ns['env'][B.ENV],str(launcher.parent/'staging_urgencias_398'/'candidato.json'));self.assertEqual(ns['env']['RO_CLICKUP_REAL'],'no');self.assertEqual(ns['env']['RO_ENVIOS_REALES'],'no')
 def test_real_responder_no_store(self):
  tree=ast.parse((Path(__file__).parent/'servir.py').read_text());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Manejador');fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='responder');ns={'json':json};exec(compile(ast.Module(body=[fn],type_ignores=[]),'responder_actual','exec'),ns)
  headers=[];h=SimpleNamespace(codificacion=lambda:None,send_response=lambda c:None,send_header=lambda k,v:headers.append((k,v)),end_headers=lambda:None,wfile=io.BytesIO())
  ns['responder'](h,200,{'urgencias_actuales':None});self.assertIn(('Cache-Control','no-store'),headers)
if __name__=='__main__':unittest.main()
