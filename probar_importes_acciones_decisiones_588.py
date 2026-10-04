"""Rutas GET reales AST/P actual con dinero exclusivamente sintético y SQLite temporal."""
import ast,copy,json,re,sqlite3,tempfile,types,unittest
from pathlib import Path
import permisos as P
A=Path(__file__).parent
TEXTO='Cuota 1470 €. Gasto Meta 300 €. Cobrado 600 €. Beneficio empresa 900 €. Revisar tarea 7 mañana.'

def cargar(nombre,ns):
 f=copy.deepcopy(next(n for n in ast.parse((A/'servir.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name==nombre))
 exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),'servir588','exec'),ns)

class Importes588(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.db=Path(self.t.name)/'fixture.sqlite';self.hook=None
  self.real={'id':'p','puestos':['account'],'estado':'activo','activo':True}
  self.vista=self.real;self.cid={'id':'c','activo':True,'estado':'activo','servicios':{'publicidad':'sí'}}
  self.e=types.SimpleNamespace(nucleo_bloqueado=False,modulos=P.cargar_modulos(),crudo={'personas':[self.real], 'clientes':[self.cid],
   'asignaciones':[{'cliente_id':'c','persona_id':'p','silla':'account','principal':True,'confianza':'confirmada'},
                   {'cliente_id':'c','persona_id':'p','silla':'trafficker','principal':True,'confianza':'confirmada'}]})
  self.e.persona=lambda pid:next((x for x in self.e.crudo['personas'] if x['id']==pid),None)
  self.act=types.SimpleNamespace(estado=lambda:{'c':True},es_activo_id=lambda cid:cid=='c')
  with self.con() as c:
   c.execute('CREATE TABLE acciones(id INTEGER PRIMARY KEY,quien TEXT,cliente_id TEXT,modulo TEXT,tipo TEXT,texto TEXT,vista_previa TEXT,estado TEXT,creada TEXT)')
   c.execute('INSERT INTO acciones VALUES(1,?,?,?,?,?,?,?,?)',('p','c','mi-dia','nota',TEXTO,json.dumps({'nota':TEXTO,'nested':{'motivo':TEXTO}}),'simulada','2026-10-04'))
   c.execute('CREATE TABLE decisiones(id INTEGER,clave TEXT,tipo TEXT,quien TEXT,titulo TEXT,problema TEXT,recomendacion TEXT,cliente_id TEXT,creada TEXT,respuesta TEXT,respondida TEXT,respondida_por TEXT,datos TEXT,anula_a INTEGER)')
   c.execute('INSERT INTO decisiones VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?,?)',('d','para_tomas','p',TEXTO,TEXTO,TEXTO,'c','2026-10-04',json.dumps({'motivo':TEXTO}),None,None,json.dumps({'extra':{'nota':TEXTO}}),None))
  def ve(p,mods):
   ns=[P.nivel_modulo(p,self.e.modulos.get(m,{})) for m in mods];ns=[n for n in ns if n]
   return max(ns,key={'resumen':1,'suyo':2,'todo':3}.get) if ns else None
  self.ns={'E':self.e,'P':P,'ACT':self.act,'json':json,'conectar':self.con,'ve_alguno':ve,'ahora':lambda:'2026-10-04',
   'puede_contestar':lambda *a:True}
  from probar_recorte_modulo_589 import cargar as cargar_recortes589
  self.ns.update(cargar_recortes589());self.ns['E']=self.e
  cargar('decisiones_para',self.ns)
  if any(isinstance(n,ast.FunctionDef) and n.name=='recorte_importes_lectura588' for n in ast.parse((A/'servir.py').read_text()).body):cargar('recorte_importes_lectura588',self.ns)
  tree=ast.parse((A/'servir.py').read_text())
  for path in ['/api/acciones','/api/decisiones']:
   b=copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)==f"ruta == '{path}'" and ('SELECT * FROM acciones' in ast.unparse(n) if path.endswith('acciones') else 'decisiones_para' in ast.unparse(n))))
   f=ast.parse('def get(self,ruta,real,persona,q,cp):\n pass').body[0];f.body=[b]
   exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),path,'exec'),self.ns)
   setattr(self,'get_'+path.split('/')[-1],self.ns['get'])
  self.h=types.SimpleNamespace(responder=lambda c,d:(c,d))
 def tearDown(self):self.t.cleanup()
 def con(self):
  c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row
  if self.hook:fn,self.hook=self.hook,None;fn()
  return c
 def request(self,path):
  with P.mirando_como(self.real,self.e.crudo):
   return getattr(self,'get_'+path)(self.h,'/api/'+path,self.real,self.vista,{'modulo':['mi-dia']},P.contexto(self.vista,self.e.crudo))
 def esperar(self,permitidas):
  for path in ['acciones','decisiones']:
   code,d=self.request(path);self.assertEqual(code,200)
   s=json.dumps(d,ensure_ascii=False)
   for n in ['1470','300','600','900']:
    self.assertEqual(n in s,n in permitidas,(path,n,s))
   self.assertIn('Revisar tarea 7 mañana',s)
 def test_account_no_importes_en_texto_json_y_decisiones(self):self.esperar(set())
 def test_administracion_conserva_cuota_cobros_no_inversion_empresa(self):
  self.real['puestos']=['administracion'];self.esperar({'1470','600'})
 def test_trafficker_su_gasto_no_cuota(self):
  self.real['puestos']=['trafficker'];self.esperar({'300'})
 def test_operaciones_no_beneficio_ni_cobros(self):
  self.real['puestos']=['operaciones'];self.esperar({'1470','300'})
 def test_direccion_finanzas_conservan_todos(self):
  for rol in ['direccion','finanzas_direccion']:
   self.real['puestos']=[rol];self.esperar({'1470','300','600','900'})
 def test_vercomo_direccion_no_eleva_account(self):
  self.real['puestos']=['direccion'];self.vista={'id':'v','puestos':['account'],'estado':'activo','activo':True}
  self.e.crudo['personas'].append(self.vista)
  self.e.crudo['asignaciones'].append({'cliente_id':'c','persona_id':'v','silla':'account'})
  with self.con() as c:c.execute("UPDATE decisiones SET quien='v'")
  self.esperar(set())
 def test_nota_vp_nojson_no_cambia_estado_recibo(self):
  with self.con() as c:c.execute('UPDATE acciones SET vista_previa=?',(TEXTO,))
  code,d=self.request('acciones');self.assertEqual(code,200)
  r=d['acciones'][0];self.assertEqual(r['estado'],'simulada');self.assertEqual(r['id'],1)
  self.assertNotIn('1470',r['vista_previa'])
 def test_revocacion_final_no_publica(self):
  self.hook=lambda:self.real.update(puestos=['setters'])
  self.assertEqual(self.request('decisiones')[0],403)
 def test_vp_sin_dinero_conserva_serializacion_y_numeros_operativos(self):
  vp=' { "fecha": "2026-10-04", "horas": 7, "nota": "Revisar ma\\u00f1ana" } '
  with self.con() as c:c.execute('UPDATE acciones SET vista_previa=?,texto=?',(vp,'Revisar tarea 7: 24 horas'))
  code,d=self.request('acciones');self.assertEqual(code,200)
  self.assertEqual(d['acciones'][0]['vista_previa'],vp)
  self.assertEqual(d['acciones'][0]['texto'],'Revisar tarea 7: 24 horas')
 def test_global_trafficker_no_inventa_permiso_inversion_sin_cliente(self):
  self.real['puestos']=['trafficker']
  with self.con() as c:
   c.execute('UPDATE acciones SET cliente_id=NULL');c.execute('UPDATE decisiones SET cliente_id=NULL')
  self.esperar(set())

if __name__=='__main__':unittest.main()
