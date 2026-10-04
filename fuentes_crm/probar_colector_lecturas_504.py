import copy,json,os,tempfile,unittest
from datetime import datetime,timedelta
from pathlib import Path
from fuentes_crm.colector_lecturas_504 import registrar,cerrar_recurso,VERSION
from fuentes_crm.adaptadores_ultima_valida_493 import adaptar
from fuentes_crm.pipeline_ultima_valida_496 import procesar,leer_proyeccion
from fuentes_crm.probar_adaptadores_ultima_valida_493 import RAW
NOW='2026-10-04T12:00:00+02:00';START='2026-10-04T11:59:00+02:00';LATER='2026-10-04T12:01:00+02:00'
GTE='2026-09-03T00:00:00+02:00'
def query(resource='contactos',page=1,emit=START):
 sid='sub-fixture';dim='dimension-fixture' if resource in ('citas','conversaciones','mensajes') else None
 p={'contactos':{'locationId':sid,'pageLimit':100,'page':page,'filters':[{'field':'dateAdded','operator':'range','value':{'gte':GTE}}],'sort':[{'field':'dateAdded','direction':'desc'}]},'contactos_total':{'locationId':sid,'pageLimit':1},'calendarios':{'locationId':sid},'citas':{'locationId':sid,'calendarId':dim,'startTime':int((datetime.fromisoformat(START)-timedelta(days=90)).timestamp()*1000),'endTime':int((datetime.fromisoformat(START)+timedelta(days=30)).timestamp()*1000)},'conversaciones':{'locationId':sid,'contactId':dim,'limit':5},'mensajes':{'limit':100},'oportunidades_abiertas':{'location_id':sid,'status':'open','limit':100,'page':page}}[resource]
 path={'contactos':'/contacts/search','contactos_total':'/contacts/search','calendarios':'/calendars/','citas':'/calendars/events','conversaciones':'/conversations/search','mensajes':f'/conversations/{dim}/messages','oportunidades_abiertas':'/opportunities/search'}[resource]
 return {'version':VERSION,'recurso':resource,'subcuenta_id':sid,'dimension_id':dim,'metodo':'POST' if resource in ('contactos','contactos_total') else 'GET','ruta':path,'parametros':p,'pagina':page,'limite':1 if resource=='contactos_total' else 100 if resource in ('contactos','mensajes','oportunidades_abiertas') else 5 if resource=='conversaciones' else None,'emitida_en':emit,'ventana_contexto':{'tipo':'medicion_pasada','desde':GTE,'hasta':START} if resource=='mensajes' else None}
def transport(resource='contactos',payload=None,status=200,kind='json',end=NOW,obs=NOW):
 raw=RAW['oportunidades'] if resource=='oportunidades_abiertas' else RAW[resource]
 return {'estado_http':status,'resultado':kind,'payload':copy.deepcopy(raw) if payload is None and kind=='json' else payload,'terminado_en':end,'observado_en':obs}
def capture(resource='contactos',q=None,t=None):return registrar(query(resource) if q is None else q,transport(resource) if t is None else t,(t or {}).get('terminado_en',NOW))
def close(captures,**kw):return cerrar_recurso(captures,clasificaciones={'contact-fixture':True},**kw)
def adapted(args):return adaptar(args['recurso'],args['respuestas'],**{k:v for k,v in args.items() if k not in ('recurso','respuestas')})
class Colector504(unittest.TestCase):
 def test_seven_current_query_shapes_and_stock_explicit(self):
  for r in ('contactos','contactos_total','calendarios','citas','conversaciones','mensajes','oportunidades_abiertas'):
   args=close([capture(r)]);e=adapted(args);self.assertEqual(e['resultado'],'ok')
  self.assertIsNone(close([capture('oportunidades_abiertas')])['ventana'])
 def test_raw_originals_are_immutable_and_only_temporary(self):
  q,t=query(),transport();before=copy.deepcopy((q,t));c=registrar(q,t,NOW);args=close([c]);self.assertEqual((q,t),before)
  self.assertNotIn('private',json.dumps(adapted(args)));c['transporte']['respuesta']['contacts'][0]['firstName']='changed';self.assertEqual((q,t),before)
 def test_contact_window_exact_gte_not_thirty_closed_days(self):
  c=capture();args=close([c]);self.assertEqual(args['ventana']['desde'],GTE);self.assertEqual(args['ventana']['hasta'],'2026-10-04T10:00:00+00:00');self.assertEqual(c['consulta']['parametros']['filters'][0]['value']['gte'],GTE)
 def test_two_pages_original_times_and_partial_no_len_inference(self):
  one=capture();q=query(page=2,emit=NOW);raw=copy.deepcopy(RAW['contactos']);raw['contacts'][0]['id']='second';two=registrar(q,transport(payload=raw,end=LATER,obs=LATER),LATER)
  args=cerrar_recurso([one,two],clasificaciones={'contact-fixture':True,'second':True});self.assertEqual(args['intentado_en'],'2026-10-04T10:01:00+00:00');self.assertFalse(adapted(args)['cobertura']['completa'])
 def test_three_pages_remain_capped_partial(self):
  cs=[];classes={}
  for i in range(1,4):
   emit=datetime.fromisoformat(START)+timedelta(minutes=i);end=emit+timedelta(seconds=10);raw=copy.deepcopy(RAW['contactos']);raw['contacts'][0]['id']='contact-'+str(i);classes['contact-'+str(i)]=True
   cs.append(registrar(query(page=i,emit=emit.isoformat()),transport(payload=raw,end=end.isoformat(),obs=end.isoformat()),end.isoformat()))
  e=adapted(cerrar_recurso(cs,fin_explicito=True,clasificaciones=classes));self.assertFalse(e['cobertura']['completa'])
 def test_explicit_recorte_150_and_conversation_two(self):
  self.assertFalse(adapted(close([capture()],fin_explicito=True,recortado=True))['cobertura']['completa'])
  self.assertFalse(adapted(close([capture('conversaciones')],fin_explicito=True,recortado=True))['cobertura']['completa'])
 def test_message_100_and_context_always_partial(self):
  args=close([capture('mensajes')],fin_explicito=True);self.assertTrue(args['lectura_limitada']);self.assertFalse(adapted(args)['cobertura']['completa'])
  raw=copy.deepcopy(RAW['mensajes']);row=raw['messages']['messages'][0];raw['messages']['messages']=[dict(row,id='message-'+str(i)) for i in range(100)]
  self.assertFalse(adapted(close([capture('mensajes',t=transport('mensajes',payload=raw))],fin_explicito=True))['cobertura']['completa'])
 def test_outside_message_context_no_silent_filter_or_zero(self):
  for date in ('2026-08-01T00:00:00Z','2026-10-04T12:00:00+02:00'):
   raw=copy.deepcopy(RAW['mensajes']);raw['messages']['messages'][0]['dateAdded']=date
   e=adapted(close([capture('mensajes',t=transport('mensajes',payload=raw))]));self.assertEqual(e['codigo_error'],'esquema_invalido');self.assertIsNone(e['datos'])
 def test_known_denial_and_retry_429_status_survive(self):
  for status in (401,403,404):
   c=capture('mensajes',t=transport('mensajes',payload={'_error':'red','_msg':'private'},status=status));e=adapted(close([c]));self.assertEqual(e['resultado'],'denegado');self.assertNotIn('private',json.dumps(c))
  t=transport('mensajes',status=429,kind='red',obs=None);e=adapted(close([capture('mensajes',t=t)]));self.assertEqual(e['codigo_error'],'limite')
 def test_free_error_message_is_not_captured(self):
  for code in ('Bearer credential-fixture',{'token':'credential-fixture'}):
   c=capture(t=transport(payload={'_error':code,'_msg':'credential-fixture'}));self.assertNotIn('credential-fixture',json.dumps(c));self.assertEqual(adapted(close([c]))['codigo_error'],'esquema_invalido')
 def test_parse_200_error_no_fabricated_read_or_zero(self):
  for kind in ('json_invalido','red','timeout'):
   t=transport(kind=kind,status=200 if kind=='json_invalido' else None,obs=None);e=adapted(close([capture(t=t)]));self.assertIsNone(e['datos']);self.assertIsNone(e['observado_en'])
 def test_page_error_preserved_and_next_page_forbidden(self):
  one=capture();q=query(page=2,emit=NOW);two=registrar(q,transport(kind='timeout',status=None,end=LATER,obs=None),LATER)
  e=adapted(close([one,two]));self.assertEqual(e['codigo_error'],'timeout')
  q=query(page=3,emit=LATER);three=registrar(q,transport(end=LATER,obs=LATER),LATER)
  with self.assertRaises(ValueError):close([one,two,three])
 def test_pagination_order_identity_calendar_and_sid_strict(self):
  c=capture()
  for patch in [{'pagina':True},{'metodo':'DELETE'},{'ruta':'https://foreign.invalid'},{'subcuenta_id':'foreign'},{'limite':99}]:
   q=query();q.update(patch)
   with self.assertRaises(ValueError):registrar(q,transport(),NOW)
  q=query(page=2);two=registrar(q,transport(),NOW)
  with self.assertRaises(ValueError):close([two,c])
  q=query(page=2,emit=NOW);q['parametros']['filters'][0]['value']['gte']='2026-09-04T00:00:00+02:00';two=registrar(q,transport(end=LATER,obs=LATER),LATER)
  with self.assertRaises(ValueError):close([c,two])
 def test_dates_original_and_offsets_order_checked(self):
  for field,value in [('observado_en','2026-10-05T00:00:00Z'),('observado_en','2026-10-04T12:00:00+02:99'),('terminado_en','2026-10-04T11:58:00+02:00')]:
   t=transport();t[field]=value
   with self.assertRaises(ValueError):registrar(query(),t,NOW)
  c=capture();self.assertEqual(c['transporte']['observado_en'],'2026-10-04T10:00:00+00:00')
 def test_first_page_future_entity_not_justified_by_last_page_cut(self):
  raw=copy.deepcopy(RAW['contactos']);raw['contacts'][0]['dateAdded']='2026-10-04T12:00:30+02:00';one=capture(t=transport(payload=raw));two=registrar(query(page=2,emit=NOW),transport(end=LATER,obs=LATER),LATER)
  e=adapted(close([one,two]));self.assertEqual(e['codigo_error'],'esquema_invalido');self.assertIsNone(e['datos'])
 def test_query_epoch_milliseconds_preserved_exact(self):
  from fuentes_crm.colector_lecturas_504 import _iso_ms
  for value in (0,1791108000001,253402300799999):
   d=datetime.fromisoformat(_iso_ms(value));epoch=datetime.fromisoformat('1970-01-01T00:00:00+00:00');delta=d-epoch;self.assertEqual(delta.days*86400000+delta.seconds*1000+delta.microseconds//1000,value)
 def test_scheduled_calendar_window_exact_90_30_not_attendance(self):
  c=capture('citas');args=close([c]);self.assertEqual(args['ventana']['tipo'],'inventario_programado');self.assertEqual(int(datetime.fromisoformat(args['ventana']['hasta']).timestamp()*1000),c['consulta']['parametros']['endTime']);self.assertEqual(adapted(args)['datos'][0]['estado'],'confirmed')
 def test_reject_legacy_opportunity_window_or_response_authority(self):
  q=query('oportunidades_abiertas');q['recurso']='oportunidades'
  with self.assertRaises(ValueError):registrar(q,transport('oportunidades_abiertas'),NOW)
  q=query();q['autorizar']=True
  with self.assertRaises(ValueError):registrar(q,transport(),NOW)
 def test_transport_to_pipeline_restart_and_failure(self):
  auth=lambda:{'actor_real':'ops-fixture','actor_vista':'ops-fixture','firma_sha256':'a'*64,'clientes':[{'cliente_id':'client-fixture','subcuenta_id':'sub-fixture'}]}
  with tempfile.TemporaryDirectory() as d:
   p=Path(d).resolve()/'state.json';os.chmod(p.parent,0o700);args=close([capture()]);first=procesar(p,[args],auth,NOW)
   later=registrar(query(emit=NOW),transport(kind='timeout',status=None,end=LATER,obs=None),LATER);second=procesar(p,[close([later])],auth,LATER,first['sha_estado']);self.assertEqual(leer_proyeccion(p,auth,LATER),second['proyeccion']);text=json.dumps(second['proyeccion']);self.assertIn('ultima_valida_anterior',text);self.assertNotIn('private',text);self.assertNotIn('contact-fixture',text)
 def test_unknown_empty_vs_verified_calendars_empty(self):
  c=capture('calendarios',t=transport('calendarios',payload={'calendars':[]}));one=adapted(close([c]));self.assertFalse(one['cobertura']['vacio_confirmado']);two=adapted(close([c],fin_explicito=True));self.assertTrue(two['cobertura']['vacio_confirmado'])
if __name__=='__main__':unittest.main()
