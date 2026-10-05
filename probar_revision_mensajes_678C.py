import importlib.util,unittest,hashlib
from pathlib import Path
APP=Path(__file__).parent
import probar_mensajes_crm_676 as T
f=APP/'fuentes_crm/generar_crm.py'
class Revision678C(unittest.TestCase):
 def setUp(self):self.ns=T.cargar(f)
 def test_message_id_container_crashes_before_normalizer(self):
  for v in ({'id':'synthetic'},['synthetic']):
   with self.subTest(kind=type(v).__name__):
    x=self.ns['leer_subcuenta'](T.Fake([T.msg(id=v)]),'sidFixture')['leads'][0];self.assertIsNone(x['respondio']);self.assertIsNone(x['mail_env'])
 def test_contact_id_container_crashes_before_normalizer(self):
  class Bad(T.Fake):
   def req(self,loc,method,ruta,*args,**kw):
    if ruta=='/contacts/search' and not(args and args[0].get('pageLimit')==1):return {'contacts':[{'id':['synthetic'],'dateAdded':T.START,'attributionSource':{'medium':'form'}}]}
    return super().req(loc,method,ruta,*args,**kw)
  x=self.ns['leer_subcuenta'](Bad([]),'sidFixture')['leads'][0];self.assertIsNone(x['respondio']);self.assertIsNone(x.get('mail_env'))
 def test_inbound_status_unknown_and_failure_remains_positive(self):
  for status in (None,'unknown','failed','undelivered','bounced'):
   with self.subTest(status=status):
    x=self.ns['leer_subcuenta'](T.Fake([T.msg(status=status)]),'sidFixture')['leads'][0]
    self.assertIsNone(x['respondio']);self.assertIsNone(x['mensajes_medicion']['entradas_observadas'])
 def test_null_creation_preserves_unknown(self):
  x=self.ns['leer_subcuenta'](T.Fake([T.msg()],creado=None),'sidFixture')['leads'][0]
  self.assertIsNone(x['respondio']);self.assertIsNone(x['intentos']);self.assertIsNone(x['mail_env'])
 def test_valid_independent_minima_no_cross_channel(self):
  x=self.ns['normalizar_mensajes676'](T.paquetes(T.msg(id='ok',direction='outbound',status='sent'),T.msg(id='bad',dateAdded=None)),T.START,T.CUT,'contactFixture',True)
  self.assertFalse(x['fiable']);self.assertIsNone(x['conteos']['mail_env']);self.assertEqual(x['minimos']['mail_env'],1);self.assertIsNone(x['minimos']['wa_env']);self.assertIsNone(x['minimos']['sms_env'])
 def test_invalid_context_matching_bindings_has_no_positive_minimum(self):
  for context in (123,True,None,[],{}):
   p=[{'mensaje':T.msg(contactId=context),'contacto_conversacion':context}]
   x=self.ns['normalizar_mensajes676'](p,T.START,T.CUT,context,True)
   self.assertIsNone(x['respondio']);self.assertTrue(all(v is None for v in x['minimos'].values()))
 def test_public_slots_original_clock_and_closed_cohort(self):
  import ast
  node=next(n for n in self.ns['tree'].body if isinstance(n,ast.FunctionDef) and n.name=='sin_tocar_publico676')
  exec(compile(ast.Module(body=[node],type_ignores=[]),'actual sin_tocar676','exec'),self.ns)
  x=self.ns['leer_subcuenta'](T.Fake([T.msg()]),'sidFixture')['leads'][0]
  run=self.ns['sin_tocar_publico676'];a=T.START-86400000;b=T.CUT-12*3600000
  good=run([x],'fixture','sidFixture','2026-10-04 12:00',a,b,T.CUT)
  self.assertEqual(good['hasta_ms'],T.CUT);self.assertEqual(good['cohorte_hasta_ms'],b);self.assertFalse(good['completa'])
  self.assertIsNone(run([x],'fixture','sidFixture','2026-10-04 12:01',a,b,T.CUT))
  self.assertIsNone(run([x],'fixture','sidFixture','2026-10-04 12:00',a,b,T.CUT+1))
  self.assertIsNone(run([x,x],'fixture','sidFixture','2026-10-04 12:00',a,b,T.CUT))
  self.assertIsNone(run([x],'fixture','sidFixture','2026-10-04 12:00',T.START+1,b,T.CUT))
 def test_malformed_conversation_never_builds_route(self):
  for ident in ('../other','a/b','https://example.invalid','',123,[],{}):
   class Bad(T.Fake):
    def req(self,loc,method,ruta,*args,**kw):
     if ruta=='/conversations/search':return {'conversations':[{'id':ident,'contactId':'contactFixture'}]}
     if ruta.startswith('/conversations/') and ruta.endswith('/messages'):
      raise AssertionError('Malformed conversation must not reach transport')
     return super().req(loc,method,ruta,*args,**kw)
   x=self.ns['leer_subcuenta'](Bad([]),'sidFixture')['leads'][0]
   self.assertIsNone(x['respondio']);self.assertIsNone(x['mail_env'])
 def test_malformed_supplied_conversation_in_pure_packet_is_unknown(self):
  for ident in ('../other','a/b',123,[],{}):
   ps=[{'mensaje':T.msg(),'contacto_conversacion':'contactFixture','conversacion_id':ident}]
   x=self.ns['normalizar_mensajes676'](ps,T.START,T.CUT,'contactFixture',True)
   self.assertIsNone(x['respondio']);self.assertIsNone(x['medicion']['entradas_observadas'])
 def test_opaque_numeric_conversation_and_binding_preserved(self):
  class Good(T.Fake):
   def req(self,loc,method,ruta,*args,**kw):
    if ruta=='/conversations/search':return {'conversations':[{'id':'123456','contactId':'contactFixture'}]}
    if ruta=='/conversations/123456/messages':return {'messages':{'messages':[T.msg()]}}
    return super().req(loc,method,ruta,*args,**kw)
  x=self.ns['leer_subcuenta'](Good([]),'sidFixture')['leads'][0]
  self.assertIs(x['respondio'],True)
if __name__=='__main__':unittest.main()
