"""Caracterización L08 local: AST actual, montaje wrappers y SQLite sintético."""
import ast,copy,contextlib,json,re,sqlite3,tempfile,threading,types,unittest
from datetime import datetime
from pathlib import Path
import permisos as P
A=Path(__file__).parent

def fn(file,name,ns,nested=False):
 tree=ast.parse((A/file).read_text());nodes=ast.walk(tree) if nested else tree.body
 f=copy.deepcopy(next(n for n in nodes if isinstance(n,ast.FunctionDef) and n.name==name))
 exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),file+'582','exec'),ns);return ns[name]

class Lecturas582(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.path=Path(self.t.name)/'fixture.sqlite';self.eventos=[]
  self.real={'id':'real-fixture','alias':'Real sintético','estado':'activo','activo':True,'puestos':['direccion']}
  self.vista={'id':'vista-fixture','alias':'Vista sintética','estado':'activo','activo':True,'puestos':['operaciones']}
  self.e=types.SimpleNamespace(nucleo_bloqueado=False,crudo={'personas':[self.real,self.vista],'clientes':[],'asignaciones':[],'para_confirmar':[]})
  with self.con() as c:
   c.execute('CREATE TABLE decisiones(id INTEGER,tipo TEXT)');c.execute('CREATE TABLE historial(n INTEGER)')
  self.ns={'re':re,'P':P,'E':self.e,'json':json,'conectar':self.con,'ahora':lambda:'2026-10-04',
   'decisiones_para':lambda p,cp:[],'datetime':datetime,'_LECTURAS_VISTAS':{},
   'registrar':lambda *a,**kw:self.eventos.append((a,kw))}
  self.apuntar=fn('servir.py','apuntar_lectura_ver_como',self.ns)
  self.ns['apuntar_lectura_ver_como']=self.apuntar
  base=fn('servir.py','_api_get',self.ns,nested=True)
  api=fn('servir.py','api_get',self.ns,nested=True)
  self.H=type('Handler582',(),{'api_get':api,'_api_get':base,'quien':lambda h,q:(self.real,self.vista,None),
   'responder':lambda h,code,d:(code,d)})
  self.h=self.H()
 def tearDown(self):self.t.cleanup()
 @contextlib.contextmanager
 def con(self):
  c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row
  try:
   with c:yield c
  finally:c.close()
 def test_decisiones_ajustes200_viewas_sin_lectura_registrada(self):
  self.assertEqual(self.h.api_get('/api/decisiones',{})[0],200)
  c,d=self.h.api_get('/api/ajustes',{});self.assertEqual(c,200);self.assertFalse(d['puedeEditar'])
  self.assertEqual(self.eventos,[],'Caracterización de ausencia actual, no prueba del arreglo')
 def test_wrapper_ia_actual_preserva_contexto_pero_no_log_central(self):
  ns={'S':types.SimpleNamespace(E=self.e),'G':types.SimpleNamespace(get=lambda *a:(200,{})),
      'get':lambda h,r,q,real,vista:h.responder(200,{'sin_clave':True}), 'get_orig':self.H._api_get}
  wrapper=fn('ia.py','_api_get',ns,nested=True)
  self.H._api_get=wrapper
  self.assertEqual(self.h.api_get('/api/ia/estado',{})[0],200);self.assertEqual(self.eventos,[])
 def test_modulo_central_registra_y_agrupa_mismo_minuto(self):
  self.H._api_get=lambda *a:(200,{})
  for _ in range(4):self.assertEqual(self.h.api_get('/api/modulo/ejemplo/fixture',{})[0],200)
  self.assertEqual(len(self.eventos),1);self.assertEqual(self.eventos[0][1]['como'],self.vista['id'])
 def test_helper_acepta_query_sensible_y_marca_antes_de_persistir(self):
  ruta='/api/canales/buscar?TEXTO_SINTETICO_PRIVADO'
  self.apuntar(self.real,self.vista,ruta)
  self.assertIn('TEXTO_SINTETICO_PRIVADO',self.eventos[0][0][3])
  self.eventos.clear();self.ns['registrar']=lambda *a,**kw:(_ for _ in ()).throw(sqlite3.OperationalError('fixture'))
  with self.assertRaises(sqlite3.OperationalError):self.apuntar(self.real,self.vista,'/api/fixture/fallo')
  self.ns['registrar']=lambda *a,**kw:self.eventos.append((a,kw))
  self.apuntar(self.real,self.vista,'/api/fixture/fallo');self.assertEqual(self.eventos,[],'Marca en memoria sin fila durable')
 def test_sincronia_get_escribe_aun_sin_filas_visibles(self):
  tree=ast.parse((A/'sincronia.py').read_text());schema=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TABLAS_SQL' for t in n.targets)))
  with self.con() as c:
   c.execute('CREATE TABLE acciones(id INTEGER, herramienta TEXT,quien TEXT,tipo TEXT,cliente_id TEXT,modulo TEXT,creada TEXT)')
   c.execute("INSERT INTO acciones VALUES(1,'clickup','otro','estado',NULL,'mi-trabajo','2026-10-04')")
  ns={'sqlite3':sqlite3,'TABLAS_SQL':schema,'conectar':self.con,'_CANDADO':threading.Lock()}
  ns['preparar']=fn('sincronia.py','preparar',ns)
  ns.update(traducir=lambda a:('clickup',{'ref':'task-fixture'}, {'estado':'diario'},None,None),
    clave_accion=lambda n:'fixture:'+str(n),leer_hora=lambda h:h)
  def crear(con,**kw):
   cur=con.execute('INSERT INTO sinc_cambios(clave,accion_id,quien,canal,tipo,objeto,objeto_ref,cambio,modo) VALUES(?,?,?,?,?,?,?,?,?)',
    (kw['clave'],kw['accion_id'],kw['quien'],kw['canal'],kw['tipo'],json.dumps(kw['objeto']),kw['objeto']['ref'],json.dumps(kw['cambio']),'simulado'))
   return cur.lastrowid,True
  ns['crear_cambio']=crear;ns['sincronizar']=fn('sincronia.py','sincronizar',ns)
  ns.update(_visible=lambda *a:False,resumen_estado=lambda *a:{})
  get=fn('sincronia.py','_get',ns)
  code,d=get(self.h,'/api/sincronia/objeto',{'ref':['task-fixture']},self.real,self.vista)
  self.assertEqual(code,200);self.assertEqual(d['cambios'],[])
  with self.con() as c:self.assertEqual(c.execute('SELECT count(*) FROM sinc_cambios').fetchone()[0],1)
  # preparar y sincronizar son reales; crear_cambio/translator son dobles de almacenamiento,
  # sin identidad ClickUp/proveedor. Demuestra escritura previa al filtro, no auth bypass.

if __name__=='__main__':unittest.main()
