"""L11 correctiva: funciones actuales AST, política real y fuentes sintéticas."""
import ast,copy,json,re,tempfile,types,unittest
from pathlib import Path
import permisos as P
APP=Path(__file__).parent
TREE=ast.parse((APP/'servir.py').read_text())
def cargar(nombre, ns):
    n = copy.deepcopy(next((n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == nombre)))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[n], type_ignores=[])), nombre, 'exec'), ns)
    return ns[nombre]
class Fixture603(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        for (rel, doc) in [('bandeja/bandeja.json', {'correos': [{'id': 'ticket_real', 'numero': '7', 'cliente_id': 'c_otro'}], 'triaje': []}), ('whatsapp/whatsapp.json', {'clientes': []}), ('crm/crm.json', {})]:
            p = self.data / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(doc))
        self.a = {'id': 'ops_fixture', 'estado': 'activo', 'activo': True, 'puestos': ['operaciones']}
        self.e = types.SimpleNamespace(nucleo_bloqueado=False,modulos=P.cargar_modulos(), crudo={'personas': [self.a], 'clientes': [{'id': 'c_ok'}, {'id': 'c_otro'}], 'asignaciones': []})
        self.ns = {'P': P, 'E': self.e, 'ACT': types.SimpleNamespace(estado=lambda: {'activos': {'c_ok'}},es_activo_id=lambda cid: cid == 'c_ok'), 'json': json, 're': re, 'DATA': self.data, 'RX_DIRECCION_CRUDA': re.compile('@|^\\+?[\\d\\s().-]{7,}$'), 'registrar_agrupado': lambda *a, **k: None}
        self.ns['ve_alguno'] = lambda p, mods: next((P.nivel_modulo(p, self.e.modulos.get(m, {})) for m in mods), None)
        for name in ['cliente_de_ticket', 'cliente_de_objeto', 'lleva_cliente', '_enlaces_malos', 'validar_accion']:
            cargar(name, self.ns)

    def tearDown(self):
        self.tmp.cleanup()

    def accion(self, **kw):
        b = {'modulo': 'bandeja', 'herramienta': 'app', 'tipo': 'nota', 'objeto': 'ticket_desconocido', 'texto': 'Fixture', **kw}
        return (self.ns['validar_accion'](None, self.a, self.a, b), b)
base=types.SimpleNamespace(P=P,cargar=cargar,L11=Fixture603)
class Tipadas603(unittest.TestCase):
 def setUp(self):
  base.L11.setUp(self)
  base.cargar('referencia_accion603',self.ns)
  base.cargar('autoridad_decision607',self.ns)
 def tearDown(self):base.L11.tearDown(self)
 accion=base.L11.accion
 def rechaza(self,**kw):
  (_,error),_=self.accion(**kw);self.assertIsNotNone(error);self.assertIn(error[0],(400,403))
 def test_app_ticket_ajeno_no_cliente_body(self):self.rechaza(objeto='ticket_real',cliente_id='c_ok')
 def test_app_ticket_sin_cid_deriva_y_aplica_ACT(self):self.rechaza(objeto='ticket_real')
 def test_desk_desconocido_nota_y_correo(self):
  for tipo in ('nota','correo','cerrar'):self.rechaza(herramienta='desk',tipo=tipo,cliente_id='c_ok')
 def test_responder_desconocido_todas_herramientas(self):
  for herr in ('desk','whatsapp','ghl'):self.rechaza(herramienta=herr,tipo='responder',cliente_id='c_ok')
 def test_desk_conocido_inactivo_no_cliente_body(self):self.rechaza(herramienta='desk',objeto='ticket_real',cliente_id='c_ok')
 def test_ghl_no_destinatario_desconocido(self):self.rechaza(herramienta='ghl',tipo='marcar_cita',cliente_id='c_ok')
 def test_decision_nueva_invalida_o_valida_no_entra_por_acciones(self):
  for vp in ({'tipo':'invalido'},{'tipo':'para_tomas','titulo':'Fixture','problema':'Fixture','recomendacion':'Fixture'},'Fixture'):
   (_,error),_=self.accion(tipo='decision_nueva',vista_previa=vp);self.assertEqual(error[0],400)
 def test_tickets_duplicados_no_primera_coincidencia(self):
  p=self.data/'bandeja/bandeja.json';p.write_text(json.dumps({'correos':[{'id':'duplicado','cliente_id':'c_ok'},{'id':'duplicado','cliente_id':'c_otro'}],'triaje':[]}))
  for herr in ('app','desk'):self.rechaza(herramienta=herr,objeto='duplicado',cliente_id='c_ok')
 def test_ticket_valido_cid_null_y_explicito(self):
  p=self.data/'bandeja/bandeja.json';p.write_text(json.dumps({'correos':[{'id':'t_ok','numero':'8','cliente_id':'c_ok'}],'triaje':[]}))
  for herr in ('app','desk'):
   for cid in (None,'c_ok'):
    (derivado,error),b=self.accion(herramienta=herr,objeto='8',cliente_id=cid)
    self.assertEqual(derivado,'c_ok');self.assertIsNone(error);self.assertEqual(b['cliente_id'],'c_ok')
 def test_cliente_exacto_y_globals_app_preservados(self):
  for kw,cid in [({'objeto':'c_ok'},'c_ok'),({'objeto':'global_fixture'},None),({'herramienta':'desk','tipo':'pedir_accesos','objeto':'c_ok'},'c_ok')]:
   (res,error),_=self.accion(**kw);self.assertEqual(res,cid);self.assertIsNone(error)
 def test_cliente_exactoforeign_y_duplicado(self):
  self.rechaza(objeto='c_otro',cliente_id='c_ok')
  self.e.crudo['clientes'].append({'id':'c_ok'});self.rechaza(objeto='c_ok')
 def test_factura_ajena_inexistente_duplicada_y_valida(self):
  self.a['puestos']=['direccion']  # puesto real permitido por acciones_solo_puestos
  p=self.data/'finanzas/impagos.json';p.parent.mkdir();
  for filas,esperado in [([{'doc':'F_fixture','cliente_id':'c_otro'}],False),([],False),([{'doc':'F_fixture','cliente_id':'c_ok'}]*2,False),([{'doc':'F_fixture','cliente_id':'c_ok'}],True)]:
   p.write_text(json.dumps({'filas':filas}))
   (cid,error),_=self.accion(modulo='finanzas',herramienta='desk',tipo='recordatorio_impago',objeto='F_fixture',cliente_id='c_ok')
   if esperado:self.assertEqual(cid,'c_ok');self.assertIsNone(error)
   else:self.assertIsNotNone(error);self.assertEqual(error[0],403)
 def test_factura_sin_cliente_no_puede_heredar_body_null(self):
  self.a['puestos']=['direccion']
  p=self.data/'finanzas/impagos.json';p.parent.mkdir();p.write_text(json.dumps({'filas':[{'doc':'F_fixture','cliente_id':None}]}))
  self.rechaza(modulo='finanzas',herramienta='desk',tipo='recordatorio_impago',objeto='F_fixture',cliente_id=None)
 def test_whatsapp_y_ghl_refs_validas(self):
  (self.data/'whatsapp/whatsapp.json').write_text(json.dumps({'clientes':[{'cliente_id':'c_ok'}]}))
  (self.data/'crm/crm.json').write_text(json.dumps({'citas_sin_estado':[{'ref':'ref_fixture','cliente_id':'c_ok'}]}))
  for herr,obj,tipo in [('whatsapp','c_ok','nota'),('ghl','Subcuenta · cita ref_fixture','marcar_cita')]:
   (cid,error),_=self.accion(herramienta=herr,objeto=obj,tipo=tipo);self.assertEqual(cid,'c_ok');self.assertIsNone(error)
 def test_proveedor_fuente_corrupta_no_fallback(self):
  (self.data/'bandeja/bandeja.json').write_text('{')
  self.rechaza(herramienta='desk',objeto='c_ok',tipo='pedir_accesos',cliente_id='c_ok')
 def test_viewas_y_permiso_modulo_no_ampliados(self):
  b={'modulo':'bandeja','herramienta':'app','tipo':'nota','objeto':'global_fixture'}
  _,err=self.ns['validar_accion'](None,self.a,{**self.a,'id':'otra'},b);self.assertEqual(err[0],403)
  a={**self.a,'puestos':['setters']};_,err=self.ns['validar_accion'](None,a,a,b);self.assertEqual(err[0],403)
 def test_cartera_denegada_no_hereda_cid_resuelto(self):
  self.a['puestos']=['account']
  p=self.data/'bandeja/bandeja.json';p.write_text(json.dumps({'correos':[{'id':'t_ok','cliente_id':'c_ok'}],'triaje':[]}))
  self.rechaza(herramienta='desk',objeto='t_ok')
 def test_ghl_whatsapp_duplicados_y_payload_malformado(self):
  for herr,rel,doc,obj in [('whatsapp','whatsapp/whatsapp.json',{'clientes':[{'cliente_id':'c_ok'},{'cliente_id':'c_ok'}]},'c_ok'),('ghl','crm/crm.json',{'citas_sin_estado':[{'ref':'x','cliente_id':'c_ok'},{'ref':'x','cliente_id':'c_otro'}]},'x')]:
   (self.data/rel).write_text(json.dumps(doc));self.rechaza(herramienta=herr,objeto=obj,cliente_id='c_ok')
  self.rechaza(herramienta='desk',objeto={'ticket':'8'},cliente_id='c_ok')
 def test_post_decisiones_formulario_positivo_y_campos_obligatorios(self):
  class Conexion:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def execute(self,*a):return types.SimpleNamespace(lastrowid=1)
  self.ns.update(conectar=Conexion,registrar=lambda *a,**k:None,TIPOS_DECISION=('para_tomas','para_coti','escalada'))
  fn=base.cargar('post_decision',self.ns);h=types.SimpleNamespace(responder=lambda c,d:(c,d));cp=base.P.contexto(self.a,self.e.crudo)
  b={'tipo':'para_tomas','titulo':'Fixture','problema':'Fixture','recomendacion':'Fixture','cliente_id':'c_ok'}
  self.assertEqual(fn(h,self.a,cp,b)[0],200)
  for campo in ('titulo','problema','recomendacion'):self.assertEqual(fn(h,self.a,cp,{**b,campo:''})[0],400)
# Compatibilidad de harness536: mismas aserciones, dependencia real nueva;
# no se modifica su archivo ni se abre DATA de aplicación.
import probar_guardia_propuesta_crm_536 as regresion536
class Regresion536Con603(regresion536.Guardia536):
 def setUp(self):
  super().setUp()
  import tempfile,re
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  ns=self.validar.__globals__;ns.update(DATA=Path(tmp.name),json=json,re=re)
  if 'referencia_accion603' not in ns:base.cargar('referencia_accion603',ns)
if __name__=='__main__':unittest.main()
