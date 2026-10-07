"""Auditoría aislada: reglas reales, AST de sesión y datos sintéticos. Sin servidor/DB/red."""
import ast,types,unittest,os
from pathlib import Path
from unittest.mock import patch
import permisos as P
import contratos_privados as C
import panel_direccion_privado_249 as D
import piloto_lectura as L
A=Path(__file__).parent

def p(id,rol,**extra):return {'id':id,'puestos':[rol],'estado':'activo',**extra}
def raw(ps):return {'personas':ps,'clientes':[{'id':'own','servicios':{'publicidad':'sí','seo':'sí','crm_ghl':'sí'}},{'id':'foreign','servicios':{'publicidad':'sí','seo':'sí','crm_ghl':'sí'}}], 'asignaciones':[{'persona_id':'account','cliente_id':'own','silla':'account'},{'persona_id':'paid','cliente_id':'own','silla':'trafficker'}]}
class Matrix(unittest.TestCase):
 def test_account_y_paid_sin_importes_ajenos(self):
  account,paid=p('account','account'),p('paid','trafficker');r=raw([account,paid])
  for person in [account,paid]:
   cp=P.contexto(person,r)
   self.assertTrue(P.ver(person,{'tipo':'cliente_detalle','cliente_id':'own'},cp)['ok'])
   self.assertFalse(P.ver(person,{'tipo':'cliente_detalle','cliente_id':'foreign'},cp)['ok'])
   self.assertFalse(P.ver(person,{'tipo':'cuota','cliente_id':'own'},cp)['ok'])
  self.assertFalse(P.ver(account,{'tipo':'inversion','cliente_id':'own'},P.contexto(account,r))['ok'])
  self.assertTrue(P.ver(paid,{'tipo':'inversion','cliente_id':'own'},P.contexto(paid,r))['ok'])
  self.assertFalse(P.ver(paid,{'tipo':'inversion','cliente_id':'foreign'},P.contexto(paid,r))['ok'])
 def test_interseccion_vista_no_eleva_cuota_sueldo(self):
  tomas,ops,account=p('tomas','direccion'),p('ops','operaciones'),p('account','account');r=raw([tomas,ops,account])
  with P.mirando_como(ops,r):self.assertFalse(P.ver(tomas,{'tipo':'sueldos','persona_id':'account'},P.contexto(tomas,r))['ok'])
  with P.mirando_como(account,r):self.assertFalse(P.ver(tomas,{'tipo':'cuota','cliente_id':'own'},P.contexto(tomas,r))['ok'])
 def test_sueldos_nominales_no_nuevos_puestos(self):
  for tipo in ['sueldo','sueldos']:
   for who in [p('newdir','direccion'),p('newhr','rrhh'),p('ops','operaciones'),p('admin','administracion')]:self.assertFalse(P.ver(who,{'tipo':tipo,'persona_id':'other'},{})['ok'])
   self.assertTrue(P.ver(p('tomas','direccion'),{'tipo':tipo,'persona_id':'other'},{})['ok'])
   self.assertTrue(P.ver(p('cecilia','rrhh'),{'tipo':tipo,'persona_id':'other'},{})['ok'])
 def test_contratos_salida_no_por_puesto(self):
  body={'nota':'Incidencia genérica','contrato':{'url':'https://sign.zoho.com/request/fixture'},'documentos':[{'tipo':'contrato_firmado','nombre':'Fixture contrato','url':'https://drive.google.com/file/d/CONTRACTFIXTURE123/view'},{'tipo':'sop','nombre':'Instrucción genérica'}]}
  for real,vista in [(p('ops','operaciones'),p('ops','operaciones')),(p('admin','administracion'),p('admin','administracion')),(p('tomas','direccion'),p('account','account')),(p('account','account'),p('tomas','direccion'))]:
   self.assertFalse(C.permitido(real,vista));clean=C.sanear(body,frozenset({'CONTRACTFIXTURE123'}));self.assertNotIn('contrato',clean);self.assertEqual(len(clean['documentos']),1);self.assertEqual(clean['nota'],'Incidencia genérica')
 def test_panel_nominal_actual_revocado(self):
  tomas=p('tomas','direccion')
  self.assertTrue(D.permitido(tomas,tomas,[tomas]))
  for role in P.PUESTO:
   other=p('other',role);self.assertFalse(D.permitido(other,other,[tomas,other]))
  self.assertFalse(D.permitido(tomas,tomas,[{**tomas,'activo':False}]))
 def test_piloto_post_denegado_sin_handler(self):
  calls=[]
  class H:
   def responder(self,c,b):return c
   def api_post(self,*args):calls.append(args);return 200
   def _api_get(self,*args):calls.append(args);return 200
  L.enganchar(H)
  with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'si'}):
   h=H();self.assertEqual(h.api_post('/api/acciones',p('tomas','direccion'),p('tomas','direccion'),{}),403);self.assertEqual(h._api_get('/api/sincronia/enviar',{},None,None),403)
  self.assertEqual(calls,[])
 def test_vista_baja_y_activo_false_denegados_en_sesion(self):
  # Regresión del hallazgo reproducido antes del cambio259: denegación temprana.
  tree=ast.parse((A/'servir.py').read_text());fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_quien')
  real=p('tomas','direccion');vista=p('departed','operaciones',estado='baja')
  personas=[real,vista];E=types.SimpleNamespace(crudo=raw(personas),persona=lambda id:next((x for x in personas if x['id']==id),None))
  ns={'P':P,'E':E,'ACCESO':types.SimpleNamespace(activo=lambda:False)};exec(compile(ast.Module(body=[fn],type_ignores=[]),'session-fixture','exec'),ns)
  h=types.SimpleNamespace(client_address=('127.0.0.1',12000),headers={'X-RO-Yo':'tomas','X-RO-Como':'departed'},galletas=lambda:{})
  a,b,error=ns['_quien'](h,{});self.assertEqual(error[0],403);self.assertIsNone(b)
  h.headers={'X-RO-Yo':'tomas'};real['activo']=False;self.assertEqual(ns['_quien'](h,{})[2][0],403)

class SesionActual(unittest.TestCase):
 def setUp(self):
  tree=ast.parse((A/'servir.py').read_text());fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_quien')
  self.real=p('tomas','direccion');self.vista=p('account','account');self.rows=[self.real,self.vista]
  self.e=types.SimpleNamespace(crudo=raw(self.rows),por_correo=lambda correo:self.real)
  self.access=types.SimpleNamespace(activo=lambda:False,correo_validado=lambda headers:('login@fixture.invalid',None))
  self.ns={'P':P,'E':self.e,'ACCESO':self.access};exec(compile(ast.Module(body=[fn],type_ignores=[]),'session-current-fixture','exec'),self.ns)
 def call(self,headers=None,q=None,cookies=None):
  h=types.SimpleNamespace(client_address=('127.0.0.1',12000),headers=headers or {},galletas=lambda:cookies or {})
  return self.ns['_quien'](h,q or {})
 def test_header_query_y_cookie_canonicos(self):
  # 590: el correo raw no identifica en local; sólo acompaña una identidad local válida.
  for headers,q,cookie in [({'X-RO-Yo':'tomas'},{},{}),({}, {'yo':['tomas']},{}),({}, {},{'ro_yo':'tomas'}),({'X-RO-Yo':'tomas','Cf-Access-Authenticated-User-Email':'fixture@fixture.invalid'}, {},{})]:
   real,vista,error=self.call(headers,q,cookie);self.assertIsNone(error);self.assertIs(real,self.real);self.assertIs(vista,self.real)
 def test_sin_identidad_no_tomas_y_id_desconocido(self):
  self.assertEqual(self.call()[2][0],401)
  for who in ['missing','Tomás','',None]:self.assertIsNotNone(self.call({'X-RO-Yo':who})[2])
 def test_produccion_ignora_yo_cookie_y_usa_sello(self):
  self.access.activo=lambda:True
  real,vista,error=self.call({'X-RO-Yo':'account'},{'yo':['account']},{'ro_yo':'account'});self.assertIsNone(error);self.assertIs(real,self.real)
  self.access.correo_validado=lambda headers:(None,'Sello inválido')
  self.assertEqual(self.call({'X-RO-Yo':'tomas'})[2][0],403)
 def test_correo_resuelto_snapshot_viejo_no_conserva_roles(self):
  self.access.activo=lambda:True # correo del validador servidor, no cabecera local sin sello
  self.e.por_correo=lambda correo:{**self.real,'puestos':['direccion','rrhh']}
  self.e.crudo['personas']=[{**self.real,'puestos':['account']},self.vista]
  real,vista,error=self.call({'Cf-Access-Authenticated-User-Email':'fixture@fixture.invalid'});self.assertIsNone(error);self.assertEqual(real['puestos'],['account'])
 def test_ambigua_real_y_vista_no_primero(self):
  self.e.crudo['personas']=[self.real,self.real,self.vista];self.assertEqual(self.call({'X-RO-Yo':'tomas'})[2][0],403)
  self.e.crudo['personas']=[self.real,self.vista,self.vista];self.assertEqual(self.call({'X-RO-Yo':'tomas','X-RO-Como':'account'})[2][0],403)
 def test_revocada_vista_antes_contexto_y_datos(self):
  for change in [{'estado':'baja'},{'estado':None},{'estado':'pendiente'},{'activo':False}]:
   self.e.crudo['personas']=[self.real,{**self.vista,**change}]
   with patch.object(P,'contexto',side_effect=AssertionError('No construir scope')):
    self.assertEqual(self.call({'X-RO-Yo':'tomas','X-RO-Como':'account'})[2][0],403)
 def test_real_actual_baja_inactiva_no_correo_snapshot(self):
  self.access.activo=lambda:True
  for change in [{'estado':'baja'},{'estado':None},{'activo':False}]:
   self.e.crudo['personas']=[{**self.real,**change},self.vista]
   self.assertEqual(self.call({'Cf-Access-Authenticated-User-Email':'fixture@fixture.invalid'})[2][0],403)
 def test_viewas_roles_actuales_no_eleva(self):
  real,vista,error=self.call({'X-RO-Yo':'tomas','X-RO-Como':'account'});self.assertIsNone(error);self.assertIs(vista,self.vista)
  self.e.crudo['personas']=[{**self.real,'puestos':['account']},self.vista]
  self.assertEqual(self.call({'X-RO-Yo':'tomas','X-RO-Como':'account'})[2][0],403)

if __name__=='__main__':unittest.main()
