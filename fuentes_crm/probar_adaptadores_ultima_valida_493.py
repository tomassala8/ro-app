import copy,unittest
from fuentes_crm.adaptadores_ultima_valida_493 import adaptar
from fuentes_crm.ultima_valida_490 import actualizar,clave,VERSION
NOW='2026-10-04T12:00:00+02:00'
WINDOW={'tipo':'medicion_pasada','desde':'2026-09-01T00:00:00+02:00','hasta':'2026-10-03T23:59:59+02:00'}
RAW={
 'contactos':{'contacts':[{'id':'contact-fixture','dateAdded':'2026-10-02T12:00:00+02:00','email':'private@example.invalid','phone':'private','firstName':'private'}]},
 'contactos_total':{'total':8,'contacts':[]},
 'calendarios':{'calendars':[{'id':'calendar-fixture','isActive':True,'name':'private'}]},
 'citas':{'events':[{'id':'appointment-fixture','contactId':'contact-fixture','calendarId':'dimension-fixture','dateAdded':'2026-10-02T12:00:00+02:00','startTime':'2026-10-20T12:00:00+02:00','appointmentStatus':'confirmed','title':'private'}]},
 'oportunidades':{'opportunities':[{'id':'opportunity-fixture','contactId':'contact-fixture','createdAt':'2026-10-02T12:00:00+02:00','status':'open','monetaryValue':999}]},
 'conversaciones':{'conversations':[{'id':'conversation-fixture','contactId':'dimension-fixture','lastMessageBody':'private'}]},
 'mensajes':{'messages':{'messages':[{'id':'message-fixture','conversationId':'dimension-fixture','dateAdded':'2026-10-02T12:00:00+02:00','direction':'outbound','messageType':'TYPE_WHATSAPP','source':'workflow','status':'failed','body':'private'}]}}
}
def read(resource,response=None,**kwargs):
 args={'subcuenta_id':'sub-fixture','dimension_id':'dimension-fixture' if resource in ('citas','conversaciones','mensajes') else None,'intentado_en':NOW,'observado_en':NOW,'ventana':WINDOW if resource in ('contactos','citas','oportunidades','mensajes') else None,'clasificaciones':{'contact-fixture':True}}
 if resource=='citas':args['ventana']={'tipo':'inventario_programado','desde':WINDOW['desde'],'hasta':'2026-11-01T00:00:00+02:00'}
 args.update(kwargs);return adaptar(resource,[copy.deepcopy(RAW[resource]) if response is None else response],**args)
class Adaptadores493(unittest.TestCase):
 def test_current_shapes_all_seven_resources(self):
  es=[read(r) for r in RAW];out=actualizar({'version':VERSION,'recursos':{}},es,NOW)
  self.assertEqual(len(out['recursos']),7);self.assertTrue(all(x['ultima_valida'] is not None for x in out['recursos'].values()))
  self.assertTrue(all(not x['ultima_valida']['cobertura']['completa'] for x in out['recursos'].values()))
 def test_private_fields_never_output_or_mutate(self):
  import json
  before=copy.deepcopy(RAW)
  for r in RAW:
   text=json.dumps(read(r));self.assertNotIn('private',text);self.assertNotIn('monetaryValue',text);self.assertNotIn('firstName',text)
  self.assertEqual(RAW,before)
 def test_empty_without_explicit_complete_is_not_zero(self):
  e=read('mensajes',{'messages':{'messages':[]}});out=actualizar({'version':VERSION,'recursos':{}},[e],NOW)
  self.assertIsNone(out['recursos'][clave(e)]['ultima_valida']);self.assertEqual(out['recursos'][clave(e)]['ultimo_intento']['resultado'],'no_promovido')
 def test_verified_empty_and_total_zero_can_be_observed(self):
  for r,response in [('mensajes',{'messages':{'messages':[]}}),('contactos_total',{'total':0})]:
   e=read(r,response,fin_paginacion=True);out=actualizar({'version':VERSION,'recursos':{}},[e],NOW)
   self.assertIsNotNone(out['recursos'][clave(e)]['ultima_valida'])
 def test_error_status_and_message_failure_propagate(self):
  for code,expected in [(401,'sin_acceso'),(403,'sin_acceso'),(404,'no_encontrado'),(429,'limite'),(502,'http_5xx'),('red','red'),('timeout','timeout')]:
   e=read('mensajes',{'_error':code,'_msg':'private'});self.assertEqual(e['codigo_error'],expected);self.assertIsNone(e['datos']);self.assertIsNone(e['observado_en'])
  e=read('mensajes',RAW['mensajes'],estados_http=[503]);self.assertEqual(e['codigo_error'],'http_5xx')
 def test_failure_has_no_fabricated_observation_timestamp(self):
  e=read('mensajes',{'_error':'timeout'},observado_en=None);self.assertEqual(e['codigo_error'],'timeout');self.assertIsNone(e['observado_en'])
  e=read('mensajes',observado_en=None);self.assertEqual(e['codigo_error'],'esquema_invalido');self.assertIsNone(e['datos'])
 def test_known_http_deny_wins_over_error_body(self):
  for status in (401,403,404):
   for body in ('red',500):
    e=read('mensajes',{'_error':body,'_msg':'private'},estados_http=[status],observado_en=None)
    self.assertEqual(e['resultado'],'denegado');self.assertEqual(e['codigo_error'],'no_encontrado' if status==404 else 'sin_acceso')
 def test_partial_page_then_error_preserves_lkg(self):
  good=read('contactos');old=actualizar({'version':VERSION,'recursos':{}},[good],NOW)
  bad=adaptar('contactos',[RAW['contactos'],{'_error':'timeout'}],subcuenta_id='sub-fixture',intentado_en='2026-10-04T12:01:00+02:00',observado_en='2026-10-04T12:01:00+02:00',ventana=WINDOW,clasificaciones={'contact-fixture':True})
  out=actualizar(old,[bad],'2026-10-04T12:01:00+02:00');self.assertEqual(out['recursos'][clave(good)]['ultima_valida'],old['recursos'][clave(good)]['ultima_valida']);self.assertEqual(bad['codigo_error'],'timeout')
 def test_no_exhaustivity_from_short_page_or_recorte(self):
  e=read('contactos');self.assertFalse(e['cobertura']['completa'])
  e=read('contactos',fin_paginacion=True,lectura_limitada=True);self.assertFalse(e['cobertura']['completa'])
 def test_known_caps_remain_partial(self):
  pages=[{'opportunities':[dict(RAW['oportunidades']['opportunities'][0],id='op-'+str(i))]} for i in range(3)]
  e=adaptar('oportunidades',pages,subcuenta_id='sub-fixture',intentado_en=NOW,observado_en=NOW,ventana=WINDOW,fin_paginacion=True);self.assertFalse(e['cobertura']['completa'])
  rows=[dict(RAW['conversaciones']['conversations'][0],id='cv-'+str(i)) for i in range(5)]
  self.assertFalse(read('conversaciones',{'conversations':rows},fin_paginacion=True)['cobertura']['completa'])
  rows=[dict(RAW['mensajes']['messages']['messages'][0],id='msg-'+str(i)) for i in range(100)]
  self.assertFalse(read('mensajes',{'messages':{'messages':rows}},fin_paginacion=True)['cobertura']['completa'])
 def test_bound_dimensions_and_location_ids(self):
  for r,key,value in [('mensajes','conversationId','foreign'),('citas','calendarId','foreign'),('conversaciones','contactId','foreign')]:
   raw=copy.deepcopy(RAW[r]);rows=raw['messages']['messages'] if r=='mensajes' else raw['events'] if r=='citas' else raw['conversations'];rows[0][key]=value;self.assertEqual(read(r,raw)['codigo_error'],'esquema_invalido')
  raw={**RAW['calendarios'],'locationId':'foreign'};self.assertEqual(read('calendarios',raw)['codigo_error'],'esquema_invalido')
 def test_missing_fields_duplicates_and_boolean_epoch(self):
  cases=[('mensajes',{}),('mensajes',{'messages':[]}),('contactos_total',{'total':True}),('calendarios',{'calendars':[{'id':'cal'}]}),('citas',{'events':[dict(RAW['citas']['events'][0],startTime=True)]}),('oportunidades',{'opportunities':[dict(RAW['oportunidades']['opportunities'][0],status='unknown')]})]
  for r,response in cases:self.assertEqual(read(r,response)['codigo_error'],'esquema_invalido')
  raw={'contacts':[RAW['contactos']['contacts'][0]]*2};self.assertEqual(read('contactos',raw)['codigo_error'],'esquema_invalido')
 def test_unknown_message_source_not_human_or_sent(self):
  raw=copy.deepcopy(RAW['mensajes']);raw['messages']['messages'][0].update(source=None,status=None)
  e=read('mensajes',raw);self.assertEqual(e['datos'][0]['origen'],'desconocido');self.assertEqual(e['datos'][0]['estado'],'desconocido')
  raw['messages']['messages'][0]['source']='app';e=read('mensajes',raw,origenes={'app':'humano'});self.assertEqual(e['datos'][0]['origen'],'humano')
 def test_contact_classification_required_not_qualification(self):
  e=read('contactos',clasificaciones={});self.assertEqual(e['codigo_error'],'esquema_invalido')
  e=read('contactos',clasificaciones={'contact-fixture':False});self.assertFalse(e['datos'][0]['es_lead']);self.assertNotIn('cualificado',e['datos'][0])
 def test_impossible_date_unknown_state_deleted_event_not_promoted(self):
  for patch in [{'dateAdded':'2026-10-04T12:00:00+02:99'},{'appointmentStatus':'custom-new'},{'deleted':True},{'appointmentStatus':'confirmed','appoinmentStatus':'cancelled'}]:
   raw=copy.deepcopy(RAW['citas']);raw['events'][0].update(patch);self.assertEqual(read('citas',raw)['codigo_error'],'esquema_invalido')
 def test_future_query_window_cannot_be_closed_measurement(self):
  with self.assertRaises(ValueError):read('citas',ventana={'tipo':'medicion_pasada','desde':WINDOW['desde'],'hasta':'2026-11-01T00:00:00+02:00'})
  e=read('citas',ventana={'tipo':'inventario_programado','desde':WINDOW['desde'],'hasta':'2026-11-01T00:00:00+02:00'});self.assertEqual(e['ventana']['tipo'],'inventario_programado');self.assertEqual(e['observado_en'],'2026-10-04T10:00:00+00:00')
  with self.assertRaises(ValueError):read('contactos',ventana={'tipo':'inventario_programado','desde':WINDOW['desde'],'hasta':'2026-11-01T00:00:00+02:00'})
  # Inicio futuro válido sigue siendo una observaciónprogramada, no asistencia.
  e=read('citas');self.assertEqual(e['datos'][0]['estado'],'confirmed');self.assertGreater(e['datos'][0]['inicio'],e['datos'][0]['creada'])
if __name__=='__main__':unittest.main()
