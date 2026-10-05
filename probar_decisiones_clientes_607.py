"""Decisiones nuevas: autoridad real vigente, SQLite exclusivamente temporal."""
import ast,copy,json,re,sqlite3,tempfile,types,unittest
from pathlib import Path
import permisos as P
APP=Path(__file__).parent
TREE=ast.parse((APP/'servir.py').read_text())
def cargar(nombre,ns):
 f=copy.deepcopy(next(n for n in ast.walk(TREE) if isinstance(n,ast.FunctionDef) and n.name==nombre))
 exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),nombre,'exec'),ns)
 return ns[nombre]
class Decisiones607(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'fixture.sqlite';self.hook=None;self.trazas=[]
  self.actor={'id':'account_fixture','estado':'activo','activo':True,'puestos':['account']}
  self.c1={'id':'c1','estado':'activo','activo':True};self.c2={'id':'c2','estado':'activo','activo':True}
  self.e=types.SimpleNamespace(nucleo_bloqueado=False,modulos=P.cargar_modulos(),crudo={'personas':[self.actor],'clientes':[self.c1,self.c2],'asignaciones':[{'cliente_id':'c1','persona_id':self.actor['id'],'silla':'account','principal':True,'confianza':'confirmada'}]})
  self.activos={'c1','c2'};self.act=types.SimpleNamespace(estado=lambda:{'activos':set(self.activos)},es_activo_id=lambda cid:cid in self.activos)
  self.ns={'P':P,'E':self.e,'ACT':self.act,'json':json,'re':re,'conectar':self.con,'TIPOS_DECISION':('para_tomas','para_coti','escalada'),'registrar':lambda *a,**k:self.trazas.append((a,k))}
  for name in ('autoridad_decision607','post_decision','puede_contestar'):cargar(name,self.ns)
  self.h=types.SimpleNamespace(responder=lambda code,dto:(code,dto))
  with self.con() as c:c.execute('CREATE TABLE decisiones(id INTEGER PRIMARY KEY,quien TEXT,tipo TEXT,clave TEXT,titulo TEXT,problema TEXT,recomendacion TEXT,cliente_id TEXT,datos TEXT,respuesta TEXT,respondida TEXT,respondida_por TEXT)')
  self.b={'titulo':'Decisión fixture','problema':'Problema fixture','recomendacion':'Recomendación fixture','cliente_id':'c1'}
  self.reglas=copy.deepcopy(P.REGLAS)
 def tearDown(self):
  P.REGLAS.clear();P.REGLAS.update(self.reglas);self.tmp.cleanup()
 def con(self):
  c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row
  if self.hook:
   f,self.hook=self.hook,None;f()
  return c
 def call(self,b=None,cp=None,actor=None):
  return self.ns['post_decision'](self.h,actor or self.actor,cp if cp is not None else P.contexto(self.actor,self.e.crudo),copy.deepcopy(self.b if b is None else b))
 def filas(self):
  with self.con() as c:return [dict(x) for x in c.execute('SELECT * FROM decisiones')]
 def neg(self,code=403,b=None,cp=None,actor=None):
  self.assertEqual(self.call(b,cp,actor)[0],code);self.assertEqual(self.filas(),[]);self.assertEqual(self.trazas,[])
 def test_cliente_actual_valido_y_global_sin_cliente(self):
  self.assertEqual(self.call()[0],200)
  self.assertEqual(self.call({k:v for k,v in self.b.items() if k!='cliente_id'})[0],200)
  self.assertEqual([r['cliente_id'] for r in self.filas()],['c1',None])
 def test_ACT_baja_deniega_aunque_ops_detalle(self):
  self.actor['puestos']=['operaciones'];self.activos.remove('c1');self.neg()
 def test_cliente_estado_baja_y_activo_false(self):
  for field,value in [('estado','baja'),('activo',False)]:
   self.c1[field]=value;self.neg();self.c1.update(estado='activo',activo=True)
 def test_cliente_desconocido_y_duplicado(self):
  self.neg(b={**self.b,'cliente_id':'unknown'})
  self.e.crudo['clientes'].append(copy.deepcopy(self.c1));self.neg()
 def test_actor_inactivo_desconocido_duplicado(self):
  for cambio in ('baja','false','missing','duplicado'):
   with self.subTest(cambio=cambio):
    self.e.crudo['personas']=[copy.deepcopy(self.actor)]
    if cambio=='baja':self.e.crudo['personas'][0]['estado']='baja'
    if cambio=='false':self.e.crudo['personas'][0]['activo']=False
    if cambio=='missing':self.e.crudo['personas']=[]
    if cambio=='duplicado':self.e.crudo['personas']*=2
    self.neg()
 def test_roles_actuales_distintos_snapshot_deniegan(self):
  self.e.crudo['personas']=[{**self.actor,'puestos':['setters']}];self.neg()
 def test_cp_antiguo_no_restaura_cartera(self):
  cp=P.contexto(self.actor,self.e.crudo);self.e.crudo['asignaciones']=[];self.neg(cp=cp)
 def test_extra_clientes_ajenos_no_canal_alternativo(self):
  for b in ({**self.b,'clientes':['c1','c2']},{**self.b,'cliente_id':None,'clientes':['c2']}):self.neg(b=b)
 def test_extra_clientes_validos_guardan_IDS_no_nombres(self):
  self.actor['puestos']=['operaciones'];self.assertEqual(self.call({**self.b,'clientes':['c1','c2']})[0],200)
  self.assertEqual(json.loads(self.filas()[0]['datos'])['clientes'],['c1','c2'])
 def test_extra_tipos_duplicados_y_CID_malformados_400(self):
  for value in ({'cliente_id':'c1'},'c1',[1],['c1','c1'],[None],[True]):self.neg(400,b={**self.b,'clientes':value})
  for cid in ('',[],{},True,1):self.neg(400,b={**self.b,'cliente_id':cid})
 def test_body_no_objeto_400_no500(self):
  for value in ([],True,'fixture',1):self.neg(400,b=value)
 def test_campos_texto_malformados_400_no500(self):
  for field in ('titulo','problema','recomendacion'):
   for value in ([],{},True,0,None,''):self.neg(400,b={**self.b,field:value})
 def test_revocacion_antes_INSERT_cartera_ACT_y_catalogos(self):
  for cambiar in (lambda:self.e.crudo['asignaciones'].clear(),lambda:self.activos.discard('c1'),lambda:self.e.crudo['clientes'].append(copy.deepcopy(self.c1))):
   antes=copy.deepcopy(self.e.crudo);act=set(self.activos);self.hook=cambiar;self.neg();self.e.crudo=antes;self.activos=act
 def test_revocacion_antes_INSERT_actor_y_politica(self):
  for cambiar in (lambda:self.e.crudo['personas'][0].update(estado='baja'),lambda:P.REGLAS.update(_fixture607='cambio')):
   antes=copy.deepcopy(self.e.crudo);self.hook=cambiar;self.neg();self.e.crudo=antes;P.REGLAS.clear();P.REGLAS.update(copy.deepcopy(self.reglas))
 def test_revocacion_durante_ultima_puerta_cliente(self):
  original=P.ver;llamadas=[]
  def ver(*a,**k):
   r=original(*a,**k);llamadas.append(1)
   if len(llamadas)==3:self.c1['activo']=False
   return r
  P.ver=ver
  try:self.neg()
  finally:P.ver=original
 def test_nucleo_bloqueado_antes_IO(self):
  self.e.nucleo_bloqueado=True;self.hook=lambda:(_ for _ in ()).throw(AssertionError('IO indebido'))
  self.assertEqual(self.call()[0],403);self.assertIsNotNone(self.hook);self.hook=None
 def test_api_post_vercomo_deniega_antes_persistencia(self):
  fn=cargar('api_post',self.ns);self.hook=lambda:(_ for _ in ()).throw(AssertionError('IO indebido'))
  code,_=fn(self.h,'/api/decisiones',self.actor,{**self.actor,'id':'vista_fixture'},self.b)
  self.assertEqual(code,403);self.assertIsNotNone(self.hook);self.hook=None
 def test_respuesta_historica_cliente_baja_permanece_autorizada(self):
  self.actor['puestos']=['direccion'];self.c1['estado']='baja';self.activos.clear()
  with self.con() as c:c.execute('INSERT INTO decisiones(id,quien,tipo,cliente_id) VALUES(1,?,?,?)',(self.actor['id'],'para_tomas','c1'))
  self.assertEqual(self.call({'operacion':'responder','id':'db-1','decision':'Aprobar la recomendación'})[0],200)
  self.assertIsNotNone(self.filas()[0]['respondida'])
 def test_respuesta_historica_no_destinatario_sigue_denegada(self):
  with self.con() as c:c.execute('INSERT INTO decisiones(id,quien,tipo,cliente_id) VALUES(1,?,?,?)',(self.actor['id'],'para_tomas','c1'))
  self.assertEqual(self.call({'operacion':'responder','id':'db-1','decision':'Aprobar la recomendación'})[0],403)
  self.assertIsNone(self.filas()[0]['respondida'])
if __name__=='__main__':unittest.main()
