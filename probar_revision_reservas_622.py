"""622 independiente: motor/hook/lector reales con fuentes estrictamente sintéticas."""
import copy,json,os,sys,unittest
from unittest.mock import patch
import cerebro_api as API
import cerebro_reservas_620 as H
import crm_embudo_api_467 as E
import embudo_eventos as Motor
import probar_puente_cerebro_reservas_621 as Fixture621

class Revision622(unittest.TestCase):
 def setUp(self):
  self.f=Fixture621.Puente621();self.f.setUp()
  self.f.crm['subcuentas'][0]['citas_30d']={'sin_estado':2,'sin_estado_max_h':5,'agendadas':3}
  self.f.crm['ventanas']={'citas':['2026-10-01','2026-10-03']}
  eventos=[]
  for i in range(3):
   lid='private-lead-'+str(i)
   eventos.append(dict(cliente_id='c1',source='ghl',lead_id=lid,event_id='private-received-'+str(i),etapa='recibido',fecha='2026-10-01T01:00:00Z'))
   if i<2:eventos.append(dict(cliente_id='c1',source='ghl',lead_id=lid,event_id='private-booking-'+str(i),etapa='cita',fecha='2026-10-02T01:00:00Z'))
  # Reserva de un recibido anterior: cuenta en eventos, no en la cohorte actual.
  eventos.extend([dict(cliente_id='c1',source='ghl',lead_id='private-old',event_id='private-old-received',etapa='recibido',fecha='2026-09-01T01:00:00Z'),dict(cliente_id='c1',source='ghl',lead_id='private-old',event_id='private-old-booking',etapa='cita',fecha='2026-10-02T01:00:00Z')])
  self.f.f.doc['clientes'][0]['medicion']=Motor.calcular(eventos,self.f.f.start,self.f.f.end,self.f.f.cut);self.f.f.persist()
 def tearDown(self):self.f.tearDown()
 def hook(self):
  class Handler:
   def responder(self,n,d):return n,d
   def _api_get(self,*a):return 404,{}
  API.enganchar(Handler,self.f.S)
  with patch.object(API,'leer_fuentes',return_value=[None,self.f.crm,None]):
   return Handler()._api_get('/api/cerebro/operativo',{'area':['crm']},self.f.ops,self.f.ops)
 def reco(self):
  n,d=self.hook();self.assertEqual(n,200,d)
  return next(r for r in d['recomendaciones'] if r['regla_id']=='crm_citas_sin_estado')
 def test_motor_hook_lector_real_cohorte_no_suma(self):
  r=self.reco();e=next(e for e in r['evidencias'] if e['fuente']==H.FUENTE)
  self.assertIn('3 recibidos observados; 2 reservas',e['texto']);self.assertNotIn('3 reservas',e['texto'])
  self.assertIn('canceladas',e['texto']);self.assertIn('fecha futura',e['texto']);self.assertIn('no acreditan asistencia, ventas',e['texto'])
  self.assertIn(H.CRITERIO,r['criterio_entrega'])
  for x in ('private-lead','private-booking','sid_fixture','subcuenta_huella','"tasa":'):self.assertNotIn(x,json.dumps(r))
 def test_off_real_hook_sin_lector(self):
  with patch.dict(os.environ,{E.ENV:''}),patch.object(E,'listar',side_effect=AssertionError('IO')):
   r=self.reco();self.assertFalse(any(e['fuente']==H.FUENTE for e in r['evidencias']))
 def test_fuente_error_no_falso_cero(self):
  self.f.f.doc['clientes'][0]['diagnosticos']={'fuente_reporta_errores':1};self.f.f.persist()
  self.assertFalse(any(e['fuente']==H.FUENTE for e in self.reco()['evidencias']))
 def test_revocacion_ultima_lectura_hook_no_publica(self):
  original=E.cargar;calls=[0]
  def leer(*a):
   d=original(*a);calls[0]+=1
   if calls[0]==2:self.f.f.active.clear()
   return d
  with patch.object(E,'cargar',leer):n,d=self.hook()
  self.assertEqual(n,403);self.assertEqual(set(d),{'error'})
 def test_scope_ajeno_no_enriquece(self):
  self.f.ops=self.f.S.E.crudo['personas'][2]
  with patch.object(E,'listar',side_effect=AssertionError('IO')):
   n,d=self.hook()
  self.assertEqual(n,200);self.assertEqual(d['recomendaciones'],[])
 def test_fecha_futura_no_actual(self):
  self.f.f.doc['hora_fuente']='2026-10-05T04:01:00+02:00';self.f.f.persist()
  self.assertFalse(any(e['fuente']==H.FUENTE for e in self.reco()['evidencias']))

if __name__=='__main__':
 if '--dto' in sys.argv:
  t=Revision622();t.setUp()
  try:
   n,d=t.hook()
   if n!=200:raise AssertionError(n)
   print(json.dumps(d))
  finally:t.tearDown()
 else:unittest.main()
