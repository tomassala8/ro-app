import ast, copy, json, re, tempfile, traceback, types, unittest
from pathlib import Path
from unittest.mock import Mock, patch
import panel_direccion_privado_249 as G
import permisos as P

A=Path(__file__).parent
class Pruebas(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.tomas={'id':'tomas','estado':'activo','puestos':['direccion']}
  self.otro={'id':'nueva_direccion','estado':'activo','puestos':['direccion']}
  self.e=types.SimpleNamespace(crudo={'personas':[self.tomas,self.otro], 'clientes':[], 'asignaciones':[]},bloqueados=set(),nucleo_bloqueado=False,modulos=P.cargar_modulos())
  self.tree=ast.parse((A/'servir.py').read_text())
  self.read=Mock(side_effect=AssertionError('No leer datos'));self.cache=types.SimpleNamespace(leer=Mock(side_effect=AssertionError('No consultar cache')))
  reglas=json.loads((A/'reglas_permisos.json').read_text())
  reglas_patch=patch.object(P,'REGLAS',copy.deepcopy(reglas));reglas_patch.start();self.addCleanup(reglas_patch.stop)
  self.ns={'DATA':Path(self.tmp.name),'NUCLEO':['personas','clientes'],'P':P,'E':self.e,'ACT':types.SimpleNamespace(estado=lambda:{}),'re':re,'traceback':traceback,'_estado_fichero':lambda p:None,'PANEL_PRIVADO_249':G,'registrar_agrupado':Mock(),'leer_json_bueno':self.read,'CACHE_RESP':self.cache}
  # 581: dependencias reales de la puerta actual; sin bootstrap ni datos de negocio.
  nombres=('entrada_datos_modulo','puerta_modulo','modulo_recortado','ve_alguno',
           'ambito_datos_581','cliente_url_581','cliente_datos_581','documento_raiz_581','modulo_vigente_581')
  funs=[n for n in self.tree.body if isinstance(n,ast.FunctionDef) and n.name in nombres]
  exec(compile(ast.Module(body=funs,type_ignores=[]),'servir-fixture','exec'),self.ns)
 def test_tomas_canonico_todas_entradas(self):
  rels=[r for r in self.ns['P'].REGLAS['datos_de_modulo'] if r.startswith('panel_direccion/')]
  self.assertEqual(len(rels),8)
  for rel in rels:self.assertEqual(self.ns['puerta_modulo'](self.tomas,self.tomas,rel)['nivel'],'todo')
 def test_direccion_nueva_no_es_tomas(self):
  for real,vista in [(self.otro,self.otro),(self.otro,self.tomas),(self.tomas,self.otro)]:
   with self.subTest(real=real['id'],vista=vista['id']):self.assertEqual(self.ns['puerta_modulo'](real,vista,'panel_direccion/indice')['error'][0],403)
 def test_regresion_puesto_generico_sin_guardia_nominal(self):
  # Caracteriza la implementación anterior conservando su puerta real y reglas.
  fn=next(n for n in self.tree.body if isinstance(n,ast.FunctionDef) and n.name=='puerta_modulo')
  fn=__import__('copy').deepcopy(fn)
  guardias=[n for n in fn.body if isinstance(n,ast.If) and 'PANEL_PRIVADO_249' in ast.unparse(n.test)]
  self.assertEqual(len(guardias),1)
  fn.body=[n for n in fn.body if n not in guardias];ns=dict(self.ns)
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'puerta-anterior-fixture','exec'),ns)
  self.assertEqual(ns['puerta_modulo'](self.otro,self.otro,'panel_direccion/indice')['nivel'],'todo')
 def test_canonico_revocado_sesion_igual(self):
  for cambio in [{'estado':'baja'},{'activo':False},{'puestos':['operaciones']},{'estado':None}]:
   with self.subTest(cambio=cambio):
    self.e.crudo['personas']=[{**self.tomas,**cambio}]
    self.assertEqual(self.ns['puerta_modulo'](self.tomas,self.tomas,'panel_direccion/empresa')['error'][0],403)
 def test_canonico_ausente_ambiguo_y_tipo_invalido(self):
  for ps in [[],[self.tomas,self.tomas],{},None]:
   self.e.crudo['personas']=ps
   self.assertFalse(G.permitido(self.tomas,self.tomas,ps))
   self.assertEqual(self.ns['puerta_modulo'](self.tomas,self.tomas,'panel_direccion/original')['error'][0],403)
 def test_otro_modulo_no_nominal_nuevo(self):
  self.ns['P'].REGLAS['datos_de_modulo']['fixture/modulo']={'puestos':['direccion']}
  self.assertEqual(self.ns['puerta_modulo'](self.otro,self.otro,'fixture/modulo')['nivel'],'todo')
 def test_busqueda_no_lee_canonico_ajeno(self):
  self.assertIsNone(self.ns['modulo_recortado'](self.otro,self.otro,{},'panel_direccion/indice'))
  self.read.assert_not_called();self.cache.leer.assert_not_called()
 def api_fixture(self):
  orig=next(n for n in ast.walk(self.tree) if isinstance(n,ast.FunctionDef) and n.name=='_api_get')
  index=next(i for i,n in enumerate(orig.body) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and any(isinstance(x,ast.Constant) and x.value==r'/api/modulo/([\w\-/]+)' for x in n.value.args))
  args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=n) for n in ['self','ruta','real','persona','cp']],kwonlyargs=[],kw_defaults=[],defaults=[])
  fn=ast.FunctionDef(name='api_fixture',args=args,body=orig.body[index:index+2],decorator_list=[])
  self.ns['re']=__import__('re');self.ns['solo_lectura']=False
  exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'api-fixture','exec'),self.ns)
  outer=self
  class H:
   def responder(self,code,body):return code
   def api_get(self,ruta,q):return outer.ns['api_fixture'](self,ruta,outer.otro,outer.otro,{})
  return H()
 def test_api_get_deniega_antes_cache_y_lector(self):
  h=self.api_fixture()
  for rel in ['indice','empresa','original','captacion_oct']:
   self.assertEqual(self.ns['api_fixture'](h,'/api/modulo/panel_direccion/'+rel,self.otro,self.otro,{}),403)
  self.read.assert_not_called();self.cache.leer.assert_not_called()
 def test_legacy_data_pasa_por_misma_puerta(self):
  h=self.api_fixture();fn=next(n for n in ast.walk(self.tree) if isinstance(n,ast.FunctionDef) and n.name=='estatico')
  self.ns['ESTATICOS_PERMITIDOS']=__import__('re').compile(r'^app\.js$')
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'static-fixture','exec'),self.ns)
  self.assertEqual(self.ns['estatico'](h,'/data/panel_direccion/indice.json'),403)
  self.read.assert_not_called();self.cache.leer.assert_not_called()
 def test_nominal_role_forged_input_no_revive(self):
  self.e.crudo['personas']=[{'id':'tomas','estado':'activo','puestos':['account']}]
  self.assertFalse(G.permitido(self.tomas,self.tomas,self.e.crudo['personas']))
 def test_fuente_sin_mutacion(self):
  ps=[dict(self.tomas),dict(self.otro)];antes=json.dumps(ps,sort_keys=True)
  G.permitido(self.tomas,self.tomas,ps);self.assertEqual(json.dumps(ps,sort_keys=True),antes)
if __name__=='__main__':unittest.main()
