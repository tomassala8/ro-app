import copy,json,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import permisos as P
import historico_llamadas_350 as H

def person(pid,role):return {'id':pid,'estado':'activo','puestos':[role]}
class Historico(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'fixture.json'
  self.raw={'personas':[person('ops','operaciones'),person('a','account'),person('b','account')],'clientes':[{'id':'c1','activo':True},{'id':'c2','activo':True}],'asignaciones':[{'cliente_id':'c1','persona_id':'a','silla':'account','principal':True,'confianza':'confirmada','desde':'2026-01-01'},{'cliente_id':'c2','persona_id':'b','silla':'account','principal':True,'confianza':'confirmada'}]}
  self.S=types.SimpleNamespace(E=types.SimpleNamespace(crudo=self.raw,nucleo_bloqueado=False),P=types.SimpleNamespace(ver=P.ver,contexto=P.contexto,hoy_iso=lambda:'2026-10-03'),ACT=types.SimpleNamespace(es_activo_id=lambda cid:True),ve_alguno=lambda p,mods:True)
  self.hist={'version':'267.1','periodo':'2026-09','cobertura':'parcial','verificacion_externa':False,'cumplimiento':None,'no_evalua_garantia':True,'sha256_candidato':H.HASH_CANDIDATO,'fuente_llamadas':'zadarma_cache_historica','llamadas30':3}
  self.doc={'clientes':[{'cliente_id':'c1','historico_267':self.hist,'cuota_secreta':999,'telefono':'NO_EXPORTAR'},{'cliente_id':'c2','historico_267':{**self.hist,'llamadas30':0}}]};self.write()
 def write(self):self.path.write_text(json.dumps(self.doc))
 def run_(self,r='ops',v=None,period='2026-09'):return H.listar(self.S,r,v or r,period,self.path)
 def test_scoped_whitelist_real_permisos(self):
  d=self.run_();self.assertEqual(len(d['filas']),2);self.assertEqual(d['filas'][0]['llamadas_30s'],3);self.assertIsNone(d['filas'][1]['llamadas_30s']);self.assertNotIn('999',json.dumps(d));self.assertNotIn('NO_EXPORTAR',json.dumps(d));self.assertIsNone(d['filas'][0]['actor_id']);self.assertIsNone(d['filas'][0]['direccion'])
 def test_account_own_confirmed(self):self.assertEqual([r['cliente_id'] for r in self.run_('a')['filas']],['c1'])
 def test_viewas_intersection(self):self.assertEqual([r['cliente_id'] for r in self.run_('ops','a')['filas']],['c1'])
 def test_no_actor_alias_or_foreigngrant(self):
  with self.assertRaises(H.ErrorHistorico):self.run_('a','b')
  self.raw['asignaciones'][0]['confianza']='alta';d=self.run_('a');self.assertEqual([r['cliente_id'] for r in d['filas']],['c1']);self.assertIsNone(d['filas'][0]['actor_id'])
 def test_read_cartera_without_confirmed_receiver_not_foreign(self):
  self.raw['asignaciones'][0]['principal']=False
  self.raw['asignaciones'][0]['confianza']='alta'
  d=self.run_('a');self.assertEqual([r['cliente_id'] for r in d['filas']],['c1'])
  self.raw['asignaciones'][0]['hasta']='2026-01-02'
  self.assertEqual(self.run_('a')['filas'],[])
 def test_detail_grant_deny_blocks_own_read(self):
  original=self.S.P.ver
  self.S.P.ver=lambda p,d,cp: {'ok':False} if d.get('tipo')=='cliente_detalle' else original(p,d,cp)
  self.assertEqual(self.run_('a')['filas'],[])
 def test_oct_unknown_never_sept(self):
  d=self.run_(period='2026-10');self.assertEqual(d['estado'],'sin_dato');self.assertTrue(all(r['llamadas_30s'] is None for r in d['filas']))
 def test_missing_source_notzero(self):self.path.unlink();self.assertEqual(self.run_()['estado'],'sin_dato')
 def test_corrupt_fields_dates_hash_count(self):
  for changes in [{'sha256_candidato':'a'*64},{'periodo':'2026-10'},{'llamadas30':True},{'llamadas30':-1},{'verificacion_externa':True},{'cumplimiento':True}]:
   self.doc['clientes'][0]['historico_267']={**self.hist,**changes};self.write()
   with self.assertRaises(H.ErrorHistorico) as e:self.run_()
   self.assertEqual(e.exception.codigo,503)
 def test_source_duplicate_or_symlink_denied(self):
  self.doc['clientes'].append(copy.deepcopy(self.doc['clientes'][0]));self.write()
  with self.assertRaises(H.ErrorHistorico):self.run_()
  self.path.unlink();target=Path(self.tmp.name)/'other';target.write_text('{}');self.path.symlink_to(target)
  with self.assertRaises(H.ErrorHistorico):self.run_()
 def test_act_duplicate_client_never_scope(self):
  self.S.ACT.es_activo_id=lambda cid:cid!='c1';self.assertEqual([r['cliente_id'] for r in self.run_()['filas']],['c2'])
  self.raw['clientes'].append({'id':'c2'});self.assertEqual(self.run_()['filas'],[])
 def test_identity_role_module_revoked(self):
  for field,value in [('estado','baja'),('puestos',['seo'])]:
   old=self.raw['personas'][0][field];self.raw['personas'][0][field]=value
   with self.assertRaises(H.ErrorHistorico):self.run_()
   self.raw['personas'][0][field]=old
  self.S.ve_alguno=lambda *args:False
  with self.assertRaises(H.ErrorHistorico):self.run_()
 def test_revoke_during_read(self):
  read=H.leer_agregado
  def revoke(path):
   result=read(path);self.raw['personas'][0]['estado']='baja';return result
  with patch.object(H,'leer_agregado',revoke):
   with self.assertRaises(H.ErrorHistorico):self.run_()
 def test_hook_exact_query_noio_import(self):
  class Handler:
   def _api_get(self,*a):return 418,{}
   def responder(self,c,d):return c,d
  H.enganchar(Handler,self.S);h=Handler()
  with patch.object(H,'leer_agregado',side_effect=AssertionError('no read')):
   for q in [{},{'periodo':['2026-09','2026-10']},{'periodo':['2026-09'],'yo':['ops']}]:self.assertEqual(h._api_get(H.RUTA,q,{'id':'ops'},{'id':'ops'})[0],400)
   self.assertEqual(h._api_get('/other',{},None,None)[0],418)
   self.assertEqual(h._api_get(H.RUTA,{'periodo':['2026-10']},{'id':'ops'},{'id':'ops'})[0],200)
if __name__=='__main__':unittest.main()
