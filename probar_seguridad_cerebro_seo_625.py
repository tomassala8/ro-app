"""625: puertas/motor actuales, catálogos y archivos exclusivamente sintéticos."""
import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import cerebro_seo_api as A
import probar_cerebro_seo_api as F

class Seguridad625(unittest.TestCase):
 def setUp(self):
  self.f=F.Prueba();self.f.setUp();self.S=self.f.S;self.p=self.f.p;self.tmp=tempfile.TemporaryDirectory();self.S.AQUI=Path(self.tmp.name).resolve()
  self.docs=[{'clientes':[{'cliente_id':'mio','servicios':{'seo':'sí'}}]},{'clientes':[]},{}]
 def tearDown(self):self.tmp.cleanup()
 def call(self):return self.f.h._api_get('/api/cerebro/seo',{},self.p,self.p)
 def good(self):
  with patch.object(A,'leer',side_effect=copy.deepcopy(self.docs)),patch.object(A,'cargar_local',return_value={'habilitado':False}):return self.call()
 def test_identidad_actual_inactiva_duplicada_roles_y_modulos_antes_IO(self):
  for change in ('baja','duplicate','roles','modulo'):
   raw=copy.deepcopy(self.S.E.crudo);mods=copy.deepcopy(self.S.E.modulos)
   if change=='baja':self.p['estado']='baja'
   if change=='duplicate':self.S.E.crudo['personas'].append(copy.deepcopy(self.p))
   if change=='roles':self.p['puestos']=['operaciones','operaciones']
   if change=='modulo':self.S.E.modulos['seo-web']={}
   with patch.object(A,'leer',side_effect=AssertionError('IO prohibido')):self.assertEqual(self.call()[0],403)
   self.S.E.crudo=raw;self.S.E.modulos=mods;self.p=raw['personas'][0]
 def test_roles_malformados_y_identidad_sin_ID_no500_ni_IO(self):
  for roles in ([{}],['desconocido'],[],None):
   self.p['puestos']=roles
   with patch.object(A,'leer',side_effect=AssertionError('IO prohibido')):self.assertEqual(self.call()[0],403)
  with patch.object(A,'leer',side_effect=AssertionError('IO prohibido')):
   self.assertEqual(self.f.h._api_get('/api/cerebro/seo',{}, {},{})[0],403)
 def test_clientes_ACT_inactivos_duplicados_y_detalle_sin_IO(self):
  for change in ('activo','duplicado','ACT'):
   raw=copy.deepcopy(self.S.E.crudo);act=self.S.ACT.es_activo_id
   if change=='activo':raw['clientes'][0]['activo']=False
   if change=='duplicado':raw['clientes'].append(copy.deepcopy(raw['clientes'][0]))
   if change=='ACT':self.S.ACT.es_activo_id=lambda cid:False
   self.S.E.crudo=raw
   with patch.object(A,'leer',side_effect=AssertionError('IO prohibido')):self.assertEqual(self.call()[1]['clientes'],[])
   self.S.E.crudo['clientes']=[{'id':'mio','servicios':{'seo':'sí'}}];self.S.ACT.es_activo_id=act
 def test_viewas_grant_y_snapshot_no_otorga_permisos(self):
  other={'id':'other','estado':'activo','puestos':['account']};self.S.E.crudo['personas'].append(other)
  with patch.object(A,'leer',side_effect=AssertionError('IO prohibido')):
   self.assertEqual(self.f.h._api_get('/api/cerebro/seo',{},other,self.p)[0],403)
 def test_duplicados_SEO_servicios_contexto_no_ganador(self):
  for kind in ('seo','services','context'):
   docs=copy.deepcopy(self.docs);seo={'clientes':[{'cliente_id':'mio'}]}
   if kind=='seo':seo['clientes']*=2
   if kind=='services':docs[0]['clientes']*=2
   if kind=='context':docs[1]['clientes']=[{'cliente_id':'mio'},{'cliente_id':'mio'}]
   with patch.object(self.S,'modulo_recortado',return_value=seo),patch.object(A,'leer',side_effect=docs),patch.object(A,'cargar_local') as motor:
    n,d=self.call();self.assertEqual(n,200);self.assertEqual(d['clientes'],[]);motor.assert_not_called()
 def test_revocacion_tras_fuentes_y_motor(self):
  for moment in ('fuentes','motor'):
   self.p['estado']='activo';calls=[0]
   def read(path):
    doc=copy.deepcopy(self.docs[calls[0]]);calls[0]+=1
    if moment=='fuentes' and calls[0]==3:self.p['estado']='baja'
    return doc
   def motor(*args):
    if moment=='motor':self.p['estado']='baja'
    return {'habilitado':False}
   with patch.object(A,'leer',read),patch.object(A,'cargar_local',motor):self.assertEqual(self.call()[0],403)
 def test_retira_ACT_durante_motor(self):
  def motor(*args):self.S.ACT.es_activo_id=lambda cid:False;return {'habilitado':False}
  with patch.object(A,'leer',side_effect=self.docs),patch.object(A,'cargar_local',motor):self.assertEqual(self.call()[0],403)
 def test_archivo_malformado_ambiguo_no_finito_y_shape(self):
  p=self.S.AQUI/'fuentes_verdad/servicios_confirmados.json';p.parent.mkdir()
  for raw in ('{','{"clientes":[],"clientes":[]}','{"clientes":[],"n":NaN}','{"clientes":[],"n":1e999}','{"clientes":{}}'):
   p.write_text(raw);self.assertEqual(self.call()[0],503)
 def test_fuente_rotada_y_parent_symlink(self):
  target=self.S.AQUI/'fuentes_verdad';external=self.S.AQUI/'externo';external.mkdir();target.symlink_to(external,target_is_directory=True)
  with patch.object(A,'leer',side_effect=AssertionError('IO prohibido')):self.assertEqual(self.call()[0],503)
  target.unlink();target.mkdir();p=target/'servicios_confirmados.json';p.write_text('{}')
  def motor(*args):p.write_text('{"cambio":true}');return {'habilitado':False}
  with patch.object(A,'leer',side_effect=self.docs),patch.object(A,'cargar_local',motor):self.assertEqual(self.call()[0],503)
 def test_ultimo_control_despues_marcas_revalida_ACT(self):
  original=A._marcas625;calls=[0]
  def marcas(app):
   x=original(app);calls[0]+=1
   if calls[0]==2:self.S.ACT.es_activo_id=lambda cid:False
   return x
  with patch.object(A,'_marcas625',marcas),patch.object(A,'leer',side_effect=self.docs),patch.object(A,'cargar_local',return_value={'habilitado':False}):self.assertEqual(self.call()[0],403)
 def test_FIFO_y_archivo_enorme_no_lector(self):
  p=self.S.AQUI/'fuentes_verdad/servicios_confirmados.json';p.parent.mkdir();os.mkfifo(p)
  with patch.object(A,'leer',side_effect=AssertionError('FIFO prohibido')):self.assertEqual(self.call()[0],503)
  p.unlink()
  with p.open('wb') as f:f.truncate(10*1024*1024+1)
  with patch.object(A,'leer',side_effect=AssertionError('Enorme prohibido')):self.assertEqual(self.call()[0],503)
 def test_loader624_actual_sin_cache_conserva_desconocido(self):
  with patch.object(A,'leer',side_effect=self.docs):
   n,d=self.call();self.assertEqual(n,200);self.assertFalse(d['clientes'][0]['habilitado']);self.assertIsNone(d['recomendaciones'][0]['responsable_id'])
 def test_owner_cache_sin_asignacion_no_confirma(self):
  n,d=self.good();self.assertEqual(n,200);self.assertIsNone(d['recomendaciones'][0]['responsable_id'])
 def test_owner_actual_confirmado_y_conflicto_vigente(self):
  owner={'id':'empleado','estado':'activo','puestos':['seo']};self.S.E.crudo['personas'].append(owner)
  a={'cliente_id':'mio','persona_id':'empleado','silla':'seo','principal':True,'confianza':'confirmada','desde':'2026-01-01'};self.S.E.crudo['asignaciones']=[a]
  self.assertEqual(self.good()[1]['recomendaciones'][0]['responsable_id'],'empleado')
  self.S.E.crudo['asignaciones'].append({**a,'confianza':'pendiente'});self.assertIsNone(self.good()[1]['recomendaciones'][0]['responsable_id'])
 def test_owner_roles_objeto_no_tumba_mediciones(self):
  self.S.E.crudo['personas'].append({'id':'empleado','estado':'activo','puestos':[{}]})
  self.S.E.crudo['asignaciones']=[{'cliente_id':'mio','persona_id':'empleado','silla':'seo','principal':True,'confianza':'confirmada'}]
  n,d=self.good();self.assertEqual(n,200);self.assertEqual(len(d['clientes']),1);self.assertIsNone(d['recomendaciones'][0]['responsable_id'])
 def test_malformed_motor_y_fuentes_no500(self):
  with patch.object(A,'leer',side_effect=[{'clientes':'bad'},{},{}]):self.assertEqual(self.call()[0],503)
  with patch.object(A,'leer',side_effect=self.docs),patch.object(A,'cargar_local',return_value=[]):self.assertEqual(self.call()[0],503)
if __name__=='__main__':unittest.main()
