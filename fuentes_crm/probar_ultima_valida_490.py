import copy,json,os,tempfile,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fuentes_crm.ultima_valida_490 import actualizar,clave,guardar_atomico,validar_estado,VERSION,DEFINICIONES
NOW='2026-10-04T12:00:00+02:00';OLD='2026-10-03T12:00:00+02:00'
def empty():return {'version':VERSION,'recursos':{}}
def intent(resource='contactos',sid='sub-fixture',when=OLD):
 if resource=='oportunidades_abiertas':
  e=intent('oportunidades',sid,when);e.update(recurso=resource,definicion=DEFINICIONES[resource],ventana=None);return e
 dim='dimension-fixture' if resource in ('citas','conversaciones','mensajes') else None
 data={'contactos':[{'id':'contact-fixture','creado':1791021600000,'es_lead':True}],'contactos_total':{'total':1},'calendarios':[{'id':'calendar-fixture','activo':True}],'citas':[{'id':'appointment-fixture','contacto':'contact-fixture','creada':1791021600000,'inicio':1791108000000,'estado':'confirmed'}],'oportunidades':[{'id':'opportunity-fixture','contacto':'contact-fixture','creada':1791021600000,'estado':'open'}],'conversaciones':[{'id':'conversation-fixture','contacto':'contact-fixture'}],'mensajes':[{'id':'message-fixture','creado':1791021600000,'direccion':'outbound','tipo':'whatsapp','origen':'humano','estado':'enviado'}]}[resource]
 result={'version':VERSION,'subcuenta_id':sid,'recurso':resource,'dimension_id':dim,'definicion':DEFINICIONES[resource],'resultado':'ok','intentado_en':when,'observado_en':when,'ventana':{'tipo':'medicion_pasada','desde':'2026-09-01T00:00:00+02:00','hasta':'2026-10-02T23:59:59+02:00'} if resource in ('contactos','citas','mensajes','oportunidades') else None,'cobertura':{'completa':False,'paginas_leidas':1,'fin_paginacion':False,'vacio_confirmado':False},'datos':copy.deepcopy(data),'codigo_error':None}
 if resource=='citas':result['ventana']={'tipo':'inventario_programado','desde':'2026-09-01T00:00:00Z','hasta':'2026-11-01T00:00:00Z'}
 return result
def fail(e,code='timeout'):
 return dict(e,resultado='error',intentado_en=NOW,observado_en=None,cobertura=None,datos=None,codigo_error=code)
class LKG490(unittest.TestCase):
 def test_error_preserves_original_date_and_data(self):
  e=intent();s=actualizar(empty(),[e],NOW);before=copy.deepcopy(s);out=actualizar(s,[fail(e)],NOW);r=out['recursos'][clave(e)];self.assertEqual(r['ultima_valida'],s['recursos'][clave(e)]['ultima_valida']);self.assertEqual(r['ultimo_intento']['resultado'],'error');self.assertEqual(s,before)
 def test_first_failure_is_missing_not_empty(self):
  e=fail(intent());r=actualizar(empty(),[e],NOW)['recursos'][clave(e)];self.assertIsNone(r['ultima_valida']);self.assertEqual(r['ultimo_intento']['codigo_error'],'timeout')
 def test_mixed_accounts_resources_update_independently(self):
  a,b,c=intent(),intent('citas'),intent(sid='other-fixture');old=actualizar(empty(),[a,b,c],NOW);newa=dict(a,intentado_en=NOW,observado_en=NOW,datos=[]);newa['cobertura']={'completa':True,'paginas_leidas':1,'fin_paginacion':True,'vacio_confirmado':True};out=actualizar(old,[newa,fail(b)],NOW);self.assertEqual(out['recursos'][clave(a)]['ultima_valida']['datos'],[]);self.assertEqual(out['recursos'][clave(b)]['ultima_valida'],old['recursos'][clave(b)]['ultima_valida']);self.assertEqual(out['recursos'][clave(c)],old['recursos'][clave(c)])
 def test_empty_partial_never_replaces_positive(self):
  e=intent();old=actualizar(empty(),[e],NOW);bad=dict(e,intentado_en=NOW,observado_en=NOW,datos=[]);out=actualizar(old,[bad],NOW);self.assertEqual(out['recursos'][clave(e)]['ultima_valida']['datos'],e['datos']);self.assertEqual(out['recursos'][clave(e)]['ultimo_intento']['resultado'],'no_promovido')
 def test_explicit_complete_empty_and_zero_are_legitimate(self):
  for r in ('contactos','contactos_total'):
   e=intent(r);e['datos']=[] if r=='contactos' else {'total':0};e['cobertura'].update(completa=True,fin_paginacion=True,vacio_confirmado=True);self.assertEqual(actualizar(empty(),[e],NOW)['recursos'][clave(e)]['ultima_valida']['datos'],e['datos'])
 def test_malformed_success_records_failure_preserving_lkg(self):
  e=intent();old=actualizar(empty(),[e],NOW)
  for data in [None,{},[{'id':'fake','creado':float('nan'),'es_lead':True}],[{**e['datos'][0],'correo':'private-fixture@example.invalid'}],[e['datos'][0],e['datos'][0]]]:
   bad=dict(e,intentado_en=NOW,observado_en=NOW,datos=data);out=actualizar(old,[bad],NOW);self.assertEqual(out['recursos'][clave(e)]['ultima_valida'],old['recursos'][clave(e)]['ultima_valida']);self.assertEqual(out['recursos'][clave(e)]['ultimo_intento']['codigo_error'],'esquema_invalido')
 def test_permission_denied_no_fallback(self):
  e=intent();old=actualizar(empty(),[e],NOW);out=actualizar(old,[fail(e,'sin_acceso')],NOW);self.assertIsNone(out['recursos'][clave(e)]['ultima_valida']);self.assertEqual(out['recursos'][clave(e)]['acceso'],'denegado')
 def test_dates_units_and_definitions_strict(self):
  for patch in [{'recurso':{}},{'subcuenta_id':[]},{'definicion':'other'},{'intentado_en':'2026-10-04T12:00:00+02:99'},{'intentado_en':'2026-10-05T12:00:00Z'},{'dimension_id':'fake'}]:
   e=intent();e.update(patch)
   with self.assertRaises(ValueError):actualizar(empty(),[e],NOW)
  e=intent();e['datos'][0]['creado']=True;self.assertIsNone(actualizar(empty(),[e],NOW)['recursos'][clave(e)]['ultima_valida'])
 def test_malformed_result_and_error_are_controlled(self):
  for patch in ({'resultado':{}},{'resultado':[]},{'codigo_error':{}},{'codigo_error':[]}):
   e=fail(intent());e.update(patch)
   with self.assertRaises(ValueError):actualizar(empty(),[e],NOW)
  for field in ('resultado','codigo_error'):
   e=intent();s=actualizar(empty(),[e],NOW);s['recursos'][clave(e)]['ultimo_intento'][field]={}
   with self.assertRaises(ValueError):validar_estado(s)
 def test_replay_conflict_older_read_not_rejuvenated(self):
  e=intent();s=actualizar(empty(),[e],NOW);self.assertEqual(actualizar(s,[e],NOW),s)
  bad=copy.deepcopy(e);bad['datos'][0]['es_lead']=False
  with self.assertRaises(ValueError):actualizar(s,[bad],NOW)
  bad=dict(e,intentado_en=NOW,observado_en='2026-10-02T12:00:00+02:00')
  with self.assertRaises(ValueError):actualizar(s,[bad],NOW)
 def test_stored_empty_without_coverage_rejected(self):
  e=intent();s=actualizar(empty(),[e],NOW);s['recursos'][clave(e)]['ultima_valida']['datos']=[]
  with self.assertRaises(ValueError):validar_estado(s)
 def test_scheduled_inventory_only_explicit_appointments(self):
  for resource in ('citas','contactos','mensajes','oportunidades'):
   e=intent(resource);e['ventana']={'tipo':'inventario_programado','desde':'2026-09-01T00:00:00Z','hasta':'2026-11-01T00:00:00Z'}
   if resource=='citas':
    r=actualizar(empty(),[e],NOW)['recursos'][clave(e)];self.assertEqual(r['ultima_valida']['ventana']['tipo'],'inventario_programado');self.assertEqual(r['ultima_valida']['observado_en'],'2026-10-03T10:00:00+00:00')
   else:
    with self.assertRaises(ValueError):actualizar(empty(),[e],NOW)
  e=intent('citas');e['ventana']['tipo']='medicion_pasada';e['ventana']['hasta']='2026-11-01T00:00:00Z'
  with self.assertRaises(ValueError):actualizar(empty(),[e],NOW)
  e['ventana']['tipo']='inventario_programado';e['observado_en']='2026-11-02T00:00:00Z'
  with self.assertRaises(ValueError):actualizar(empty(),[e],NOW)
 def test_future_row_dates_and_calendar_start_contract(self):
  for resource,key in [('contactos','creado'),('citas','creada'),('oportunidades','creada'),('mensajes','creado')]:
   e=intent(resource);e['datos'][0][key]=1791300000000
   r=actualizar(empty(),[e],NOW)['recursos'][clave(e)];self.assertIsNone(r['ultima_valida']);self.assertEqual(r['ultimo_intento']['codigo_error'],'esquema_invalido')
  e=intent('citas');e['ventana']={'tipo':'medicion_pasada','desde':'2026-09-01T00:00:00Z','hasta':'2026-10-02T00:00:00Z'}
  self.assertIsNone(actualizar(empty(),[e],NOW)['recursos'][clave(e)]['ultima_valida'])
 def test_ancestor_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d).resolve();private=root/'private';private.mkdir(mode=0o700);link=root/'link';link.symlink_to(private,target_is_directory=True)
   with self.assertRaises(ValueError):guardar_atomico(link/'state.json',actualizar(empty(),[intent()],NOW))
 def test_previous_state_future_even_without_new_attempt(self):
  s=actualizar(empty(),[intent()],NOW)
  with self.assertRaises(ValueError):actualizar(s,[],'2026-10-02T12:00:00Z')
 def test_legacy_version_never_auto_migrated(self):
  old=empty();old['version']='490.1'
  with self.assertRaises(ValueError):actualizar(old,[intent()],NOW)
  e=intent();e['ventana'].pop('tipo')
  with self.assertRaises(ValueError):actualizar(empty(),[e],NOW)
 def test_all_resources_normalized_contracts(self):
  es=[intent(r) for r in DEFINICIONES];s=actualizar(empty(),es,NOW);self.assertEqual(len(s['recursos']),8);self.assertTrue(all(r['ultima_valida'] is not None for r in s['recursos'].values()))
 def test_private_atomic_writer_cas_replay_and_concurrency(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d).resolve()/'state.json';os.chmod(p.parent,0o700);s=actualizar(empty(),[intent()],NOW);h=guardar_atomico(p,s);self.assertEqual(guardar_atomico(p,s,h),h);self.assertEqual(p.stat().st_mode&0o777,0o600)
   one=actualizar(s,[fail(intent())],NOW);other=actualizar(s,[dict(intent(),intentado_en=NOW,observado_en=NOW)],NOW)
   def save(v):
    try:return guardar_atomico(p,v,h)
    except ValueError:return None
   with ThreadPoolExecutor(2) as ex:results=list(ex.map(save,[one,other]))
   self.assertEqual(sum(x is not None for x in results),1);self.assertIn(json.loads(p.read_text()),[one,other])
 def test_symlink_fifo_nonprivate_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d).resolve()/'state.json';os.chmod(p.parent,0o700);s=actualizar(empty(),[intent()],NOW);p.symlink_to(p.parent/'other')
   with self.assertRaises((OSError,ValueError)):guardar_atomico(p,s)
   p.unlink();os.mkfifo(p)
   with self.assertRaises(ValueError):guardar_atomico(p,s)
   p.unlink();os.chmod(p.parent,0o755)
   with self.assertRaises(ValueError):guardar_atomico(p,s)
if __name__=='__main__':unittest.main()
