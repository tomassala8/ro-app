"""621: API467, motor620 y permisos reales; depósitos/pins estrictamente sintéticos."""
import copy,json,os,unittest
from datetime import datetime,timezone
from unittest.mock import patch
import cerebro_api as API
import reservas_cerebro_api_621 as B
import crm_embudo_api_467 as E
import cerebro_reservas_620 as H
import probar_crm_embudo_api_467 as F

class Clock(datetime):
 @classmethod
 def now(cls,tz=None):return cls(2026,10,4,12,tzinfo=timezone.utc)

class Puente621(unittest.TestCase):
 def setUp(self):
  self.f=F.Embudo467();self.f.setUp();self.S=self.f.S
  self.clock=patch.object(B,'datetime',Clock);self.clock.start()
  self.day=patch.object(self.S.P,'hoy_iso',return_value='2026-10-04');self.day.start()
  self.crm={'generado':'2026-10-04T04:01:00+02:00','subcuentas':[{'cliente_id':'c1','sub_id':'sid_fixture','tipo':'cliente'}]}
  self.S.entrada_datos_modulo=lambda rel:{'modulos':['salud-crm']}
  self.S.modulo_recortado=lambda *args:copy.deepcopy(self.crm)
  self.r={'cliente_id':'c1','regla_id':'crm_citas_sin_estado','area':'crm','evidencias':[{'fuente':'crm','texto':'fixture'}],'criterio_entrega':'Contrastar el resultado.'}
  self.result={'recomendaciones':[self.r,{'cliente_id':'c1','regla_id':'crm_otra','evidencias':[]}],'clientes':[{'cliente_id':'c1'}]}
  self.ops=self.S.E.crudo['personas'][0];self.account=self.S.E.crudo['personas'][1]
 def tearDown(self):self.day.stop();self.clock.stop();self.f.tearDown()
 def call(self,real=None,vista=None):return B.enriquecer_api621(self.S,self.result,self.crm,real or self.ops,vista or real or self.ops)
 def añadido(self,d):return [e for e in d['recomendaciones'][0]['evidencias'] if e['fuente']==H.FUENTE]
 def test_positivo_lector_real_apendice_sin_mutar_ni_ampliar(self):
  antes=copy.deepcopy(self.result);d=self.call();self.assertEqual(len(self.añadido(d)),1);self.assertEqual(self.result,antes)
  self.assertEqual(d['recomendaciones'][1],antes['recomendaciones'][1]);self.assertEqual(d['clientes'],antes['clientes']);self.assertEqual(len(d['recomendaciones']),2)
  for s in ('private-lead','private-event','sid_fixture','subcuenta_huella','"tasa":','"denominador":'):self.assertNotIn(s,json.dumps(d))
 def test_off_no_lector_no_enriquecimiento(self):
  with patch.dict(os.environ,{E.ENV:''}),patch.object(E,'listar',side_effect=AssertionError('IO')):
   self.assertIs(self.call(),self.result)
 def test_otras_reglas_y_CID_duplicado_o_sid_ambiguo_no_IO(self):
  for change in ('regla','cliente','sid','tipo'):
   before=copy.deepcopy(self.crm);r=copy.deepcopy(self.result)
   if change=='regla':self.r['regla_id']='otra'
   if change=='cliente':self.crm['subcuentas'].append(copy.deepcopy(self.crm['subcuentas'][0]))
   if change=='sid':self.crm['subcuentas'].append({'cliente_id':'c2','sub_id':'sid_fixture','tipo':'cliente'})
   if change=='tipo':self.crm['subcuentas'][0]['tipo']='interna'
   with patch.object(E,'listar',side_effect=AssertionError('IO')):self.assertIs(self.call(),self.result)
   self.crm=before;self.result=r;self.r=r['recomendaciones'][0]
 def test_corrupto_y_viejo_conservan_propuesta_original(self):
  self.f.path.write_bytes(b'{}');self.assertEqual(self.call(),self.result)
  self.f.doc.update(hora_fuente='2026-09-20T04:01:00+02:00');self.f.persist();self.assertEqual(E.listar(self.S,'ops','ops','c1')['estado'],'copia_observada');self.assertEqual(self.call(),self.result)
 def test_real_vista_scope_valido_y_ajeno_no_IO(self):
  self.assertEqual(len(self.añadido(self.call(vista=self.account))),1)
  foreign=self.S.E.crudo['personas'][2]
  with patch.object(E,'listar',side_effect=AssertionError('IO')):
   d=self.call(vista=foreign);self.assertEqual(d['recomendaciones'],[]);self.assertEqual(d['clientes'],[])
 def test_revocacion_durante_ultimo_IO_no_publica_destino(self):
  original=E.cargar
  for mode in ('ACT','rol','module','duplicado'):
   raw=copy.deepcopy(self.S.E.crudo);mods=copy.deepcopy(self.S.E.modulos);self.f.active={'c1','c2'};calls=[0]
   def cargar(p):
    v=original(p);calls[0]+=1
    if calls[0]==2:
     if mode=='ACT':self.f.active.discard('c1')
     if mode=='rol':self.S.E.crudo['personas'][0]['puestos']=['seo']
     if mode=='module':self.S.E.modulos['salud-crm']={}
     if mode=='duplicado':self.S.E.crudo['personas'].append(copy.deepcopy(self.S.E.crudo['personas'][0]))
    return v
   with patch.object(E,'cargar',cargar),self.assertRaises(B.ErrorPuente621) as e:self.call()
   self.assertEqual(e.exception.codigo,403);self.S.E.crudo=raw;self.S.E.modulos=mods;self.ops=raw['personas'][0];self.account=raw['personas'][1]
 def test_revocacion_tras_motor_puro_y_prioridades(self):
  original=H.enriquecer_reservas620
  def enrich(*a,**kw):
   out=original(*a,**kw);self.S.E.modulos['prioridades-cliente']={};return out
  with patch.object(H,'enriquecer_reservas620',enrich),self.assertRaises(B.ErrorPuente621):self.call()
 def test_misma_fuente_y_config_pin_al_final(self):
  self.S.modulo_recortado=lambda *args:{**self.crm,'generado':'2026-10-03'};self.assertEqual(self.call(),self.result)
  self.S.modulo_recortado=lambda *args:copy.deepcopy(self.crm)
  original=H.enriquecer_reservas620
  def enrich(*a,**kw):
   out=original(*a,**kw);os.environ[E.ENV]='';return out
  with patch.object(H,'enriquecer_reservas620',enrich):self.assertEqual(self.call(),self.result)
 def test_error_opcional_y_env_rotado_no_lee_privados_extra(self):
  with patch.object(E,'listar',side_effect=E.ErrorEmbudo(503,'fixture')):
   self.assertEqual(self.call(),self.result)
  orig=E.listar
  def read(*a):
   d=orig(*a);os.environ[E.ENV]='';return d
  with patch.object(E,'listar',read):self.assertEqual(self.call(),self.result)
 def test_pins_rotados_y_fuente_revocada_durante_reread(self):
  original=H.enriquecer_reservas620;sha=E.SHA
  def enrich(*a,**kw):
   d=original(*a,**kw);E.SHA='b'*64;return d
  try:
   with patch.object(H,'enriquecer_reservas620',enrich):self.assertEqual(self.call(),self.result)
  finally:E.SHA=sha
  def read(*a):
   self.f.active.discard('c1');return copy.deepcopy(self.crm)
  self.S.modulo_recortado=read
  with self.assertRaises(B.ErrorPuente621):self.call()
 def test_motor_real_regla_id_y_ruta_API_sin_stub_motor(self):
  self.crm['subcuentas'][0]['citas_30d']={'sin_estado':1,'sin_estado_max_h':5,'agendadas':2}
  self.crm['ventanas']={'citas':['2026-09-04','2026-10-03']}
  class Handler:
   def responder(self,n,d):return n,d
   def _api_get(self,*a):return 404,{}
  API.enganchar(Handler,self.S)
  with patch.object(API,'leer_fuentes',return_value=[None,self.crm,None]):
   n,d=Handler()._api_get('/api/cerebro/operativo',{'area':['crm']},self.ops,self.ops)
  self.assertEqual(n,200,d)
  recos=[r for r in d['recomendaciones'] if r['regla_id']=='crm_citas_sin_estado']
  self.assertEqual(len(recos),1);self.assertEqual(sum(e['fuente']==H.FUENTE for e in recos[0]['evidencias']),1)
  self.assertIsNone(recos[0]['responsable_id']);self.assertNotIn('tasa',recos[0])
 def test_hook_real_y_rechazo_no_exponer_error_privado(self):
  class Handler:
   def responder(self,n,d):return n,d
   def _api_get(self,*a):return 404,{}
  API.enganchar(Handler,self.S)
  with patch.object(API,'leer_fuentes',return_value=[None,self.crm,None]),patch('cerebro_operativo.generar',return_value=self.result):
   n,d=Handler()._api_get('/api/cerebro/operativo',{'area':['crm']},self.ops,self.ops);self.assertEqual(n,200);self.assertEqual(len(self.añadido(d)),1)
   orig=E.listar
   def leer(*a):
    d=orig(*a);self.f.active.discard('c1');return d
   with patch.object(E,'listar',leer):
    n,d=Handler()._api_get('/api/cerebro/operativo',{'area':['crm']},self.ops,self.ops)
   self.assertEqual(n,403);self.assertEqual(set(d),{'error'});self.assertNotIn('private',d['error'])
if __name__=='__main__':unittest.main()
