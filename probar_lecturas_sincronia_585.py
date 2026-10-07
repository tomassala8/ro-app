"""L08: funciones reales AST, wrappers actuales y bases exclusivamente temporales."""
import ast, contextlib, json, sqlite3, threading, unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import probar_lecturas_ver_como_582 as caracterizacion582
fn=caracterizacion582.fn
A=caracterizacion582.A

class Lecturas585(unittest.TestCase):
 setUp=caracterizacion582.Lecturas582.setUp
 tearDown=caracterizacion582.Lecturas582.tearDown
 con=caracterizacion582.Lecturas582.con
 def preparar_traza(self):
  self.ns['_CANDADO_LECTURAS_VISTAS']=threading.Lock()
  fn('servir.py','ruta_lectura_ver_como585',self.ns)
  self.e.modulos=caracterizacion582.P.cargar_modulos()
  self.ns['ACT']=type('ACT',(),{'estado':staticmethod(lambda:{}),'es_activo_id':staticmethod(lambda cid:False)})
  from probar_recorte_modulo_589 import cargar as cargar_recortes589
  self.ns.update(cargar_recortes589())
  fn('servir.py','recorte_importes_lectura588',self.ns)
 def test_base_decisiones_ajustes_y_wrapper_ia_antes_dispatch(self):
  self.preparar_traza()
  for ruta in ['/api/decisiones','/api/ajustes']:
   self.assertEqual(self.h.api_get(ruta,{})[0],200)
  self.assertEqual(len(self.eventos),2)
  ns={'S':type('S',(),{'E':self.e}), 'get_orig':self.H._api_get,
      'get':lambda h,r,q,real,vista:h.responder(200,{'seguro':True})}
  self.H._api_get=fn('ia.py','_api_get',ns,nested=True)
  self.assertEqual(self.h.api_get('/api/ia/estado',{})[0],200)
  self.assertEqual(len(self.eventos),3)
  for args,kw in self.eventos:
   self.assertEqual(args[0],self.real['id']);self.assertEqual(kw['como'],self.vista['id'])
   self.assertNotIn('alias',json.dumps((args,kw)))
 def test_todas_familias_y_desconocida_sin_query_ni_ids(self):
  self.preparar_traza();self.H._api_get=lambda *a:(200,{})
  rutas=['/api/operaciones/registros','/api/cliente/CLIENTE_PRIVADO','/api/modulo/PRIVADO/a',
         '/api/canales/buscar?token=SECRETO','/api/sincronia/objeto','/api/ia/consejo','/api/ajustes','/api/PRIVADO']
  for ruta in rutas:self.assertEqual(self.h.api_get(ruta,{'q':['SECRETO']})[0],200)
  texto=json.dumps(self.eventos)
  self.assertNotIn('PRIVADO',texto);self.assertNotIn('SECRETO',texto);self.assertNotIn('Real sintético',texto)
  self.assertEqual(len(self.eventos),len(rutas))
 def test_fallo_registro_reintenta_no_dispatch_no_exito(self):
  self.preparar_traza();despachos=[];self.H._api_get=lambda *a:despachos.append(1) or (200,{})
  self.ns['registrar']=lambda *a,**kw:(_ for _ in ()).throw(sqlite3.OperationalError('PRIVADO'))
  code,d=self.h.api_get('/api/decisiones',{});self.assertEqual(code,503)
  self.assertNotIn('PRIVADO',json.dumps(d));self.assertEqual(despachos,[]);self.assertEqual(self.ns['_LECTURAS_VISTAS'],{})
  self.ns['registrar']=lambda *a,**kw:self.eventos.append((a,kw))
  self.assertEqual(self.h.api_get('/api/decisiones',{})[0],200);self.assertEqual(len(despachos),1)
 def test_dedup_concurrente_solo_una_fila_y_otra_identidad(self):
  self.preparar_traza()
  with ThreadPoolExecutor(max_workers=8) as pool:
   list(pool.map(lambda _:self.apuntar(self.real,self.vista,'/api/cliente/uno'),range(30)))
  self.assertEqual(len(self.eventos),1)
  self.apuntar(self.real,{**self.vista,'id':'otra'},'/api/cliente/dos');self.assertEqual(len(self.eventos),2)
 def test_denegacion_identidad_y_self_no_traza(self):
  self.preparar_traza();self.H._api_get=lambda *a:(200,{})
  self.H.quien=lambda h,q:(None,None,(403,'No permitido'))
  self.assertEqual(self.h.api_get('/api/ia/estado',{})[0],403);self.assertEqual(self.eventos,[])
  self.H.quien=lambda h,q:(self.real,self.real,None)
  self.assertEqual(self.h.api_get('/api/ia/estado',{})[0],200);self.assertEqual(self.eventos,[])

class Sincronia585(unittest.TestCase):
 def setUp(self):
  import tempfile
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'s.sqlite';self.sql=[]
  self.ns={'sqlite3':sqlite3,'conectar':self.con,'timedelta':timedelta,
   'ahora_utc':lambda:datetime(2026,10,4,tzinfo=timezone.utc),'conf':lambda:{'horas_sin_reflejar':4},
   'json':json,'iso_z':lambda x:x,'txt_hora':lambda x:x.isoformat(),
   '_visible':lambda r,v,c:r['id']=='r' and v['id']=='v' and c['quien']=='v',
   've_todos':lambda p:False,'interruptor':lambda:{'reales':False,'canales':{},'chat_puente':False,'texto':'OFF'},
   'ESTADOS':['simulado'],'CANALES':['clickup'],'texto_informe':lambda x:'fixture',
   'preparar':lambda *a:(_ for _ in ()).throw(AssertionError('GET DDL')),
   'sincronizar':lambda *a:(_ for _ in ()).throw(AssertionError('GET reconcilia'))}
  self.get=fn('sincronia.py','_get',self.ns);fn('sincronia.py','sin_reflejar',self.ns)
  self.ns['a_json']=lambda c,row,*a:{'id':row['id'],'estado':'simulado','canal':'clickup'}
  self.ns['resumen_estado']=lambda c,i:{'id':i}
  self.h=type('H',(),{'responder':lambda h,c,d:(c,d)})();self.real={'id':'r'};self.vista={'id':'v'}
 def tearDown(self):self.tmp.cleanup()
 @contextlib.contextmanager
 def con(self):
  c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row
  c.set_trace_callback(self.sql.append)
  deny={sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_INDEX,sqlite3.SQLITE_CREATE_TRIGGER,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_TRANSACTION}
  c.set_authorizer(lambda op,*a:sqlite3.SQLITE_DENY if op in deny else sqlite3.SQLITE_OK)
  try:yield c
  finally:c.close()
 def esquema(self):
  tree=ast.parse((A/'sincronia.py').read_text());schema=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TABLAS_SQL' for t in n.targets)))
  c=sqlite3.connect(self.path);c.executescript(schema)
  c.execute("CREATE TABLE acciones(id INTEGER)");c.execute("INSERT INTO acciones VALUES(1)");c.commit();c.close()
 def test_sin_schema503_sin_crear_y_error_generico(self):
  c,d=self.get(self.h,'/api/sincronia',{},self.real,self.vista);self.assertEqual(c,503)
  self.assertNotIn('sqlite',json.dumps(d))
  with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT name FROM sqlite_master').fetchall(),[])
 def test_tres_rutas_selectonly_y_accion_pendiente_no_reconcilia(self):
  self.esquema()
  for ruta,q,status in [('/api/sincronia',{},200),('/api/sincronia/cambio',{'id':['999']},404),('/api/sincronia/objeto',{'ref':['fixture']},200)]:
   self.assertEqual(self.get(self.h,ruta,q,self.real,self.vista)[0],status)
  self.assertTrue(self.sql);self.assertTrue(all(s.lstrip().upper().startswith('SELECT') for s in self.sql))
  with sqlite3.connect(self.path) as c:
   self.assertEqual(c.execute('SELECT count(*) FROM sinc_cambios').fetchone()[0],0)
   self.assertEqual(c.execute('SELECT count(*) FROM acciones').fetchone()[0],1)
 def test_visibilidad_doble_scope_y_id_malformado(self):
  self.esquema()
  with sqlite3.connect(self.path) as c:
   c.execute("INSERT INTO sinc_cambios(clave,quien,canal,tipo,objeto,objeto_ref,cambio,modo) VALUES('k','v','clickup','estado','{}','t','{}','simulado')")
  self.assertEqual(self.get(self.h,'/api/sincronia/cambio',{'id':['1']},self.real,self.vista)[0],200)
  for r,v in [({'id':'otro'},self.vista),(self.real,{'id':'otro'})]:
   self.assertEqual(self.get(self.h,'/api/sincronia/cambio',{'id':['1']},r,v)[0],403)
  self.assertEqual(self.get(self.h,'/api/sincronia/cambio',{'id':['no']},self.real,self.vista)[0],400)
 def test_visibilidad_real_minimo_de_ambos_no_solo_vista(self):
  self.esquema()
  self.ns['conf']=lambda:{'ven_todos_puestos':['operaciones'],'horas_sin_reflejar':4}
  fn('sincronia.py','ve_todos',self.ns);fn('sincronia.py','_visible',self.ns)
  with sqlite3.connect(self.path) as c:
   c.execute("INSERT INTO sinc_cambios(clave,quien,canal,tipo,objeto,objeto_ref,cambio,modo) VALUES('k','v','clickup','estado','{}','t','{}','simulado')")
  vista={'id':'v','puestos':['account']};real={'id':'r','puestos':['operaciones']}
  self.assertEqual(self.get(self.h,'/api/sincronia/cambio',{'id':['1']},real,vista)[0],200)
  for r,v in [({'id':'r','puestos':['account']},vista),(real,{'id':'otro','puestos':['account']})]:
   self.assertEqual(self.get(self.h,'/api/sincronia/cambio',{'id':['1']},r,v)[0],403)
 def test_informe_con_cambio_real_y_pasos_selectonly(self):
  self.esquema();fn('sincronia.py','estado_actual',self.ns)
  self.ns.update(FINALES={'confirmado','descartado'},leer_hora=lambda v:datetime.fromisoformat(v).replace(tzinfo=timezone.utc))
  with sqlite3.connect(self.path) as c:
   c.execute("INSERT INTO sinc_cambios(clave,creado,quien,canal,tipo,objeto,objeto_ref,cambio,modo) VALUES('k','2026-10-01','v','clickup','estado','{\"ref\":\"t\"}','t','{}','simulado')")
   c.execute("INSERT INTO sinc_pasos(cambio_id,estado,evento) VALUES(1,'simulado','creado')")
  code,d=self.get(self.h,'/api/sincronia',{},self.real,self.vista)
  self.assertEqual(code,200);self.assertEqual(d['informe']['total'],1)
  self.assertTrue(all(s.lstrip().upper().startswith('SELECT') for s in self.sql))

if __name__=='__main__':unittest.main()
