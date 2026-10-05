import json,types,unittest,copy
from contextlib import contextmanager
import probar_revision_confirmar_570 as D
from ajustes_validacion_579 import asignacion

class Ajustes579(unittest.TestCase):
 def setUp(self):
  self.f=D.Confirmar570();self.f.setUp()
  self.f.target.update(puestos=['account'],correo='fixture@rankingonline.com')
  self.f.e.crudo.update(clientes=[{'id':'c1','estado':'activo','activo':True}],asignaciones=[])
  self.act={'c1':True};self.f.ajustes.__globals__['ACT']=types.SimpleNamespace(es_activo_id=lambda cid:self.act.get(cid) is True)
 def tearDown(self):self.f.tearDown()
 def post(self,b):return self.f.ajustes(self.f.h,'/api/ajustes/asignacion',self.f.actor,b)
 def b(self,**kw):
  d={'operacion':'crear','cliente_id':'c1','persona_id':self.f.target['id'],'silla':'account','desde':'2026-10-04','principal':True,'suplencia':False};d.update(kw);return d
 def historial(self):
  with self.f.con() as c:return [dict(r) for r in c.execute('SELECT * FROM historial')]
 def test_crear_positivo_mismo_sillas_altas(self):
  fn=D.extraer('altas_personas.py','sillas_de_puestos',{'P':D.P})
  self.assertIn('account',fn(self.f.target['puestos']))
  self.assertEqual(self.post(self.b())[0],200)
  r=self.historial()[0];d=json.loads(r['datos']);self.assertEqual(r['operacion'],'crear');self.assertIs(d['principal'],True);self.assertIs(d['suplencia'],False)
 def test_persona_baja_dudosa_o_silla_ajena_no_crea(self):
  for estado in ('baja','dudoso','por_incorporar'):
   self.f.target['estado']=estado;self.assertEqual(self.post(self.b())[0],400)
  self.f.target['estado']='activo';self.f.target['activo']=False;self.assertEqual(self.post(self.b())[0],400)
  self.f.target['activo']=True;self.assertEqual(self.post(self.b(silla='trafficker'))[0],400)
  self.assertFalse(self.historial())
 def test_identidades_unicas_cliente_act(self):
  self.act['c1']=False;self.assertEqual(self.post(self.b())[0],400);self.act['c1']=True
  for col in ('personas','clientes'):
   filas=self.f.e.crudo[col];filas.append(copy.deepcopy(filas[-1]));self.assertEqual(self.post(self.b())[0],400);filas.pop()
  self.assertEqual(self.post(self.b(cliente_id='unknown'))[0],400);self.assertFalse(self.historial())
 def test_fechas_invalidas_orden_booleanos_no_coercion(self):
  for key in ('desde','hasta'):
   for v in ('2026-02-30','20261004','2026-10-04T00:00:00','',True,123):
    self.assertEqual(self.post(self.b(**{key:v}))[0],400)
  self.assertEqual(self.post(self.b(hasta='2026-10-03'))[0],400)
  for key in ('principal','suplencia'):
   for v in ('false','true',0,1,None,[],{}):self.assertEqual(self.post(self.b(**{key:v}))[0],400)
  self.assertFalse(self.historial())
 def test_suplencia_fin_titular_y_no_limite_inventado(self):
  self.assertEqual(self.post(self.b(suplencia=True))[0],400)
  self.assertEqual(self.post(self.b(suplencia=True,hasta='2026-11-01'))[0],400)
  self.assertEqual(self.post(self.b(suplencia=True,principal=False,hasta='2028-10-04'))[0],200)
  self.assertEqual(self.post(self.b(suplencia=True,principal=False,hasta='2026-11-01',titular_id=self.f.target['id']))[0],400)
  self.assertEqual(self.post(self.b(titular_id='unknown'))[0],400)
 def test_confirmar_cerrar_ui_defaults(self):
  b={'cliente_id':'c1','persona_id':self.f.target['id'],'silla':'account'}
  self.assertEqual(self.post(dict(b,operacion='confirmar'))[0],200)
  self.assertEqual(self.post(dict(b,operacion='cerrar'))[0],200)
  h=self.historial();self.assertEqual(h[-1]['operacion'],'cerrar');self.assertEqual(json.loads(h[-1]['datos'])['hasta'],'2026-10-04')
 def test_revocacion_antes_historial(self):
  original=self.f.con
  @contextmanager
  def con():
   self.act['c1']=False
   with original() as c:yield c
  self.f.ajustes.__globals__['conectar']=con
  self.assertEqual(self.post(self.b())[0],403);self.assertFalse(self.historial())
 def test_baja_a_de_rechazo_tras_mando(self):
  self.assertEqual(self.f.normal({'estado':'baja'},self.f.target['id'])[0],400)
  self.f.target['estado']='baja';self.f.target['activo']=False
  self.assertEqual(self.f.normal({'estado':'activo'},self.f.target['id'])[0],400)
  self.assertEqual(self.f.normal({'estado':'baja'},self.f.target['id'])[0],200)
  self.f.target.update(estado='activo',activo=True,puestos=['direccion'])
  self.assertEqual(self.f.normal({'estado':'baja'},self.f.target['id'])[0],403)
 def test_estados_guardar_ordinario_compatible(self):
  for estado in ('activo','dudoso','por_incorporar'):
   self.assertEqual(self.f.normal({'estado':estado,'alias':'Sintética','campo_legacy_ignorado':123},self.f.target['id'])[0],200)
  self.assertEqual(len(self.historial()),3)
 def test_correo_igual_normalizado_compatible_distinto_sin_access(self):
  self.assertEqual(self.f.normal({'correo':' FIXTURE@rankingonline.com '},self.f.target['id'])[0],200)
  self.assertEqual(self.f.normal({'correo':'otro@rankingonline.com'},self.f.target['id'])[0],400)
  self.assertEqual(self.f.normal({'correo':None},self.f.target['id'])[0],400)
  self.assertEqual(json.loads(self.historial()[0]['datos'])['correo'],'fixture@rankingonline.com')
  self.assertEqual(len(self.historial()),1)
 def test_correo_duplicado_sigue409_mando403(self):
  self.f.actor['correo']='otro@rankingonline.com'
  self.assertEqual(self.f.normal({'correo':'otro@rankingonline.com'},self.f.target['id'])[0],409)
  self.f.target['puestos']=['direccion'];self.assertEqual(self.f.normal({'correo':'otro@rankingonline.com'},self.f.target['id'])[0],403)
if __name__=='__main__':unittest.main()
