import copy,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from fuentes_crm import pipeline_ultima_valida_496 as P
from fuentes_crm import ultima_valida_490 as W
from fuentes_crm.probar_adaptadores_ultima_valida_493 import RAW,WINDOW
NOW='2026-10-04T12:00:00+02:00';LATER='2026-10-04T12:01:00+02:00'
def scope():return {'actor_real':'ops-fixture','actor_vista':'account-fixture','firma_sha256':'a'*64,'clientes':[{'cliente_id':'client-a','subcuenta_id':'sub-a'},{'cliente_id':'client-b','subcuenta_id':'sub-b'}]}
def lectura(recurso='contactos',sid='sub-a',when=NOW,response=None,**kw):
 d={'recurso':recurso,'respuestas':[copy.deepcopy(RAW[recurso]) if response is None else response],'subcuenta_id':sid,'dimension_id':'dimension-fixture' if recurso in ('citas','conversaciones','mensajes') else None,'intentado_en':when,'observado_en':when,'ventana':copy.deepcopy(WINDOW) if recurso in ('contactos','citas','oportunidades','mensajes') else None,'clasificaciones':{'contact-fixture':True}}
 if recurso=='citas':d['ventana']={'tipo':'inventario_programado','desde':WINDOW['desde'],'hasta':'2026-11-01T00:00:00+02:00'}
 d.update(kw);return d
def resource(dto,cid='client-a',r='contactos'):
 return next(x for c in dto['clientes'] if c['cliente_id']==cid for x in c['recursos'] if x['recurso']==r)
class Pipeline496(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name).resolve()/'estado.json';os.chmod(self.path.parent,0o700);self.auth=scope();self.callback=lambda:copy.deepcopy(self.auth)
 def tearDown(self):self.tmp.cleanup()
 def process(self,reads,now=NOW,sha=None):return P.procesar(self.path,reads,self.callback,now,sha)
 def test_two_accounts_failure_preserves_other_and_restart(self):
  first=self.process([lectura(),lectura(sid='sub-b')]);old=P.leer_proyeccion(self.path,self.callback,NOW)
  failed=lectura(when=LATER,response={'_error':'timeout','_msg':'private'},observado_en=None)
  second=self.process([failed],LATER,first['sha_estado']);dto=P.leer_proyeccion(self.path,self.callback,LATER)
  self.assertEqual(dto,second['proyeccion']);a=resource(dto);self.assertEqual(a['conteo_observado'],1);self.assertEqual(a['estado_lectura'],'ultima_valida_anterior');self.assertEqual(a['observaciones'][0]['observado_en'],resource(old)['observaciones'][0]['observado_en']);self.assertEqual(resource(dto,'client-b'),resource(old,'client-b'))
 def test_first_failure_and_missing_file_are_unknown(self):
  dto=P.leer_proyeccion(self.path,self.callback,NOW);self.assertIsNone(resource(dto)['conteo_observado']);self.assertFalse(self.path.exists())
  first=self.process([lectura(response={'_error':'red'},observado_en=None)]);self.assertIsNone(resource(first['proyeccion'])['conteo_observado'])
 def test_explicit_empty_legitimate_partial_not_fake_zero(self):
  first=self.process([lectura(response={'contacts':[]})]);self.assertIsNone(resource(first['proyeccion'])['conteo_observado'])
  empty=lectura(when=LATER,response={'contacts':[]},fin_paginacion=True);second=self.process([empty],LATER,first['sha_estado']);self.assertEqual(resource(second['proyeccion'])['conteo_observado'],0);self.assertEqual(resource(second['proyeccion'])['estado_lectura'],'leida');self.assertFalse(second['proyeccion']['completa'])
 def test_partial_messages_error_not_response_or_attempt_zero(self):
  first=self.process([lectura('mensajes')]);self.assertEqual(resource(first['proyeccion'],r='mensajes')['estado_lectura'],'parcial')
  failed=lectura('mensajes',when=LATER,response={'_error':500},observado_en=None);second=self.process([failed],LATER,first['sha_estado']);row=resource(second['proyeccion'],r='mensajes');self.assertEqual(row['conteo_observado'],1);self.assertEqual(row['observaciones'][0]['ultimo_intento']['codigo_error'],'http_5xx');self.assertNotIn('respondio',row)
 def test_scope_duplicates_and_foreign_read_before_io(self):
  for malformed in [dict(scope(),clientes=scope()['clientes']+[scope()['clientes'][0]]),dict(scope(),clientes=[scope()['clientes'][0],{'cliente_id':'other','subcuenta_id':'sub-a'}]),dict(scope(),actor_real=[]),dict(scope(),clientes=[])]:
   with patch.object(P,'_cargar',side_effect=AssertionError('IO')):
    with self.assertRaises(PermissionError):P.leer_proyeccion(self.path,lambda:malformed,NOW)
  with patch.object(P,'_cargar',side_effect=AssertionError('IO')):
   with self.assertRaises(PermissionError):self.process([lectura(sid='foreign')])
 def test_denied_resource_clears_private_fallback(self):
  first=self.process([lectura()]);second=self.process([lectura(when=LATER,response={'_error':403},observado_en=None)],LATER,first['sha_estado']);r=resource(second['proyeccion']);self.assertEqual(r['estado_lectura'],'sin_acceso');self.assertIsNone(r['conteo_observado']);self.assertNotIn('contact-fixture',self.path.read_text())
 def test_revoke_after_read_denies_projection(self):
  self.process([lectura()]);original=P._cargar
  def rotate(path):
   result=original(path);self.auth['firma_sha256']='b'*64;return result
  with patch.object(P,'_cargar',side_effect=rotate):
   with self.assertRaises(PermissionError):P.leer_proyeccion(self.path,self.callback,NOW)
 def test_revoke_after_writer_read_before_commit_no_change(self):
  first=self.process([lectura()]);old=self.path.read_bytes();original=W._leer
  def rotate(path):
   result=original(path);self.auth['clientes'][0]['subcuenta_id']='rotated';return result
  with patch.object(W,'_leer',side_effect=rotate):
   with self.assertRaises(PermissionError):self.process([lectura(when=LATER)],LATER,first['sha_estado'])
  self.assertEqual(self.path.read_bytes(),old)
 def test_revoke_after_temp_write_before_replace_no_new_target(self):
  original=W.os.fsync;calls=[]
  def rotate(fd):
   calls.append(fd);original(fd)
   if len(calls)==1:self.auth['firma_sha256']='b'*64
  with patch.object(W.os,'fsync',side_effect=rotate):
   with self.assertRaises(PermissionError):self.process([lectura()])
  self.assertFalse(self.path.exists());self.assertEqual(list(self.path.parent.glob('.lkg490-*')),[])
 def test_revoke_after_commit_blocks_return_without_destructive_rollback(self):
  original=W.os.replace
  def rotate(a,b):original(a,b);self.auth['firma_sha256']='b'*64
  with patch.object(W.os,'replace',side_effect=rotate):
   with self.assertRaises(PermissionError):self.process([lectura()])
  self.assertTrue(self.path.exists());W.validar_estado(json.loads(self.path.read_text()))
  # La nueva autoridad se valida de nuevo; datos no conceden ningún grant.
  with self.assertRaises(PermissionError):P.leer_proyeccion(self.path,lambda:None,NOW)
 def test_restart_recovers_cas_version_without_private_payload(self):
  first=self.process([lectura()]);version=P.leer_version(self.path,self.callback,NOW);self.assertEqual(version['sha_estado'],first['sha_estado']);self.assertNotIn('contact-fixture',json.dumps(version))
  second=self.process([lectura(when=LATER)],LATER,version['sha_estado']);self.assertNotEqual(second['sha_estado'],version['sha_estado'])
 def test_cas_and_replay_are_durable(self):
  first=self.process([lectura()]);again=self.process([lectura()],sha=first['sha_estado']);self.assertEqual(first['sha_estado'],again['sha_estado'])
  with self.assertRaises(ValueError):self.process([lectura(when=LATER)],LATER,sha='f'*64)
  self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),first['sha_estado'])
 def test_concurrent_pipeline_one_cas_winner(self):
  first=self.process([lectura()]);sha=first['sha_estado']
  def run(read):
   try:return self.process([read],LATER,sha)
   except ValueError:return None
  with ThreadPoolExecutor(2) as executor:
   results=list(executor.map(run,[lectura(when=LATER),lectura(when=LATER,response={'_error':'timeout'},observado_en=None)]))
  self.assertEqual(sum(r is not None for r in results),1);self.assertIn(P.leer_proyeccion(self.path,self.callback,LATER),[r['proyeccion'] for r in results if r is not None])
 def test_projection_no_private_ids_text_or_fake_rates(self):
  first=self.process([lectura(r) for r in RAW]);text=json.dumps(first['proyeccion'])
  for forbidden in ('sub-a','sub-b','dimension-fixture','contact-fixture','conversation-fixture','message-fixture','private','email','monetaryValue','es_lead','conversion','asistencia','"venta"'):
   self.assertNotIn(forbidden,text)
  self.assertEqual(resource(first['proyeccion'],r='contactos_total')['conteo_observado'],8)
 def test_dimensions_not_summed_or_mixed_cuts(self):
  a=lectura('mensajes');b=lectura('mensajes',dimension_id='other-conversation',response={'messages':{'messages':[dict(RAW['mensajes']['messages']['messages'][0],conversationId='other-conversation',id='other-message')]}})
  dto=self.process([a,b])['proyeccion'];r=resource(dto,r='mensajes');self.assertIsNone(r['conteo_observado']);self.assertEqual(len(r['observaciones']),2);self.assertEqual(r['estado_lectura'],'dimensiones_separadas')
 def test_current_scope_filters_previous_foreign_without_leak(self):
  self.process([lectura(),lectura(sid='sub-b')]);self.auth['clientes']=[scope()['clientes'][0]];self.auth['firma_sha256']='b'*64
  dto=P.leer_proyeccion(self.path,self.callback,NOW);self.assertEqual([c['cliente_id'] for c in dto['clientes']],['client-a'])
 def test_json_malformed_private_file_never_becomes_unknown_empty(self):
  for raw in [b'{"version":"490.2","version":"490.2","recursos":{}}',b'{"version":"490.2","recursos":{},"bad":NaN}',b'{"version":"490.2","recursos":{},"bad":1e999}',b'{}',b'not json']:
   self.path.write_bytes(raw);self.path.chmod(0o600)
   with self.assertRaises(ValueError):P.leer_proyeccion(self.path,self.callback,NOW)
 def test_private_permissions_symlink_fifo_rejected(self):
  self.path.symlink_to(self.path.parent/'other')
  with self.assertRaises(ValueError):P.leer_proyeccion(self.path,self.callback,NOW)
  self.path.unlink();os.mkfifo(self.path)
  with self.assertRaises(ValueError):P.leer_proyeccion(self.path,self.callback,NOW)
 def test_projection_output_independent_of_state(self):
  self.process([lectura()]);state,_=P._cargar(self.path);before=copy.deepcopy(state);dto=P.proyectar(state,P._ambito(self.callback),NOW);resource(dto)['observaciones'][0]['ventana']['tipo']='tampered';self.assertEqual(state,before)
if __name__=='__main__':unittest.main()
