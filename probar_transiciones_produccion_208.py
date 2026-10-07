"""Fixtures aislados: permisos reales AST, CAS208 y corePOST194; sin servidor/proveedores."""
import ast,copy,json,sqlite3,tempfile,types,unittest,os
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import transiciones_produccion_208 as X
import transiciones_mi_trabajo as T
from identidades_clickup_204 import preparar_autorizacion
HERE=Path(__file__).resolve().parent
class Pruebas(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'db.sqlite3'
  self.account={'id':'reviewer','correo':'account@example.invalid','estado':'activo','puestos':['account']}
  self.author={'id':'author','correo':'author@example.invalid','estado':'activo','puestos':['seo'],'jefe':'seo-boss'}
  self.seo={'id':'seo-boss','correo':'seo@example.invalid','estado':'activo','puestos':['jefa_seo']}
  self.ads={'id':'ads-boss','estado':'activo','puestos':['jefa_publicidad']};self.ops={'id':'ops','estado':'activo','puestos':['operaciones']}
  self.crudo={'personas':[self.account,self.author,self.seo,self.ads,self.ops],'clientes':[{'id':'client-fixture'}]};self.permission=True;self.act=True
  self.row={'id':'task-fixture','cli':'client-fixture','persona_id':'author','lista_id':'list-fixture','estado':'revisión project manager','tipo_estado':'custom'}
  names=['diario','revisión técnica','revisión project manager','enviar  cliente','corrección']
  self.D={'generado':'fixture','tareas':[self.row],'estados_lista':{'list-fixture':names},'estados_detalle':{'list-fixture':[{'estado':s,'tipo':'custom'} for s in names]}}
  self.raw={'id':'task-fixture','lista_id':'list-fixture','estado':self.row['estado'],'carpeta_id':'folder-fixture','asignados':[{'id':'u-author'}]}
  self.users=[{'id':'u-author','email':'author@example.invalid'}]
  self.rules=json.loads((HERE/'reglas_permisos.json').read_text())
  self.p=types.SimpleNamespace(REGLAS=self.rules,contexto=lambda p,c:{'cartera_por_silla':{'account':{'client-fixture'} if p['id']=='reviewer' and 'account' in p.get('puestos',[]) else set()}},ver=lambda*a:{'ok':self.permission},enlace_seguro=lambda*a:True)
  tree=ast.parse((HERE/'servir.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='puede_revisar_pieza')
  E=types.SimpleNamespace(crudo=self.crudo,nucleo_bloqueado=False,persona=lambda pid:next((p for p in self.crudo['personas'] if p['id']==pid),None),modulos={'produccion':{}})
  ns={'P':self.p,'E':E};exec(compile(ast.Module(body=[fn],type_ignores=[]),'real_revisor','exec'),ns)
  self.s=types.SimpleNamespace(E=E,P=self.p,ACT=types.SimpleNamespace(es_activo_id=lambda cid:self.act),ve_alguno=lambda*a:True,
   tarea_de_produccion=lambda tid:{'id':tid,'cli':self.row['cli'],'estado':self.row['estado'],'autores':{'author'}},
   pieza_en_revision=lambda tid:{'cli':self.row['cli'],'estado':self.row['estado'],'autores':{'author'}} if self.row['estado'].startswith('revisión') else None,puede_revisar_pieza=ns['puede_revisar_pieza'],conectar=self.connect)
  def source():return {'D':self.D,'filas':{'task-fixture':[self.row]},'identidad':preparar_autorizacion(self.crudo['personas'],self.users,[self.raw],{'folder-fixture':['client-fixture']})}
  self.source=source
  def translate(a):
   vp=json.loads(a['vista_previa']);tipo=a['tipo'];rp=self.p.REGLAS['revision_piezas']
   dest=rp['por_estado'][self.row['estado']]['a'] if tipo=='pieza_aprobar' else rp['pedir_cambios_a'] if tipo=='pieza_pedir_cambios' else vp['a']
   return 'clickup',{'ref':a['objeto'],'resuelto':True},{'campo':'estado','valor':dest},{'estado':self.row['estado']},{}
  self.translate=translate
  for p in [patch.object(X,'S',self.s),patch.object(X,'fuentes',source),patch.dict('sys.modules',{'sincronia':types.SimpleNamespace(traducir=translate)}),patch.dict(os.environ,{},clear=False)]:p.start();self.addCleanup(p.stop)
  os.environ.pop('RO_PILOTO_LECTURA',None);os.environ.pop('DATABASE_URL',None)
  with self.connect() as c:c.executescript((HERE/'schema_v2.sql').read_text())
 @contextmanager
 def connect(self):
  c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row
  try:yield c;c.commit()
  except: c.rollback();raise
  finally:c.close()
 def body(self,actor=None,tipo='pieza_aprobar'):
  actor=actor or self.account
  with self.connect() as c:token=X.obtener(c,actor,actor)['transiciones_revision']['task-fixture']
  return {'modulo':'produccion','herramienta':'clickup','tipo':tipo,'objeto':'task-fixture','intencion_id':'f61a94b8-2091-453e-9299-43b5b1758192','vista_previa':{'transicion_produccion':True,'lista_id':token['lista_id'],'expected_estado':token['expected_estado'],'revision':token['revision'],'a':token['acciones'][tipo]['destino'],**({'comentario':'Corrige el titular'} if tipo=='pieza_pedir_cambios' else {})}}
 def cas(self,b,p=None):
  with self.connect() as c:c.execute('BEGIN IMMEDIATE');return X.validar_en_transaccion(c,p or self.account,b)
 def test_account_own_token_206(self):
  with self.connect() as c:d=X.obtener(c,self.account,self.account)
  self.assertEqual(d['capacidad_revision']['version'],'206.1');self.assertEqual(set(d['transiciones_revision']['task-fixture']['acciones']),{'pieza_aprobar','pieza_pedir_cambios'})
 def test_token_typed_exact_without_private_fields(self):
  with self.connect() as c:token=X.obtener(c,self.account,self.account)['transiciones_revision']['task-fixture']
  self.assertEqual(token['tipo_estado'],'custom');self.assertEqual(token['lista_id'],self.row['lista_id']);self.assertEqual(token['expected_estado'],self.row['estado'])
  self.assertEqual(set(token),{'modulo','tarea_id','cliente_id','tipo_estado','lista_id','expected_estado','revision','bloqueada','acciones'})
 def test_cas_actual(self):self.assertIsNone(self.cas(self.body()))
 def test_no_self_review_ops(self):
  self.author['puestos']=['operaciones'];_,err=X.validar_previo(self.author,self.author,self.body());self.assertEqual(err[0],403)
 def test_wrong_area_denied(self):
  self.row['estado']=self.raw['estado']='revisión técnica'
  with self.connect() as c:self.assertEqual(X.obtener(c,self.ads,self.ads)['transiciones_revision'],{});self.assertIn('task-fixture',X.obtener(c,self.seo,self.seo)['transiciones_revision'])
 def test_unknown_assignee_blocks_even_ops(self):
  self.raw['asignados'].append({'id':'missing'})
  with self.connect() as c:self.assertEqual(X.obtener(c,self.ops,self.ops)['transiciones_revision'],{})
 def test_author_inactive_blocks_documented(self):
  self.author['estado']='baja'
  with self.connect() as c:self.assertEqual(X.obtener(c,self.ops,self.ops)['transiciones_revision'],{})
 def test_raw_duplicate_blocks(self):
  self.raw['asignados'].append({'id':'u-author'})
  with self.connect() as c:self.assertEqual(X.obtener(c,self.account,self.account)['transiciones_revision'],{})
 def test_account_other_portfolio(self):
  b=self.body();self.p.contexto=lambda*a:{'cartera_por_silla':{'account':set()}};self.assertEqual(self.cas(b)[0],403)
 def test_scope_revoked(self):
  b=self.body();self.permission=False;self.assertEqual(self.cas(b)[0],403)
 def test_act_revoked(self):
  b=self.body();self.act=False;self.assertEqual(self.cas(b)[0],403)
 def test_view_no_tokens(self):
  with self.connect() as c:self.assertFalse(X.obtener(c,self.ops,self.account)['capacidad_revision']['activo'])
 def test_view_post_denied(self):self.assertEqual(X.validar_previo(self.account,self.ops,self.body())[1][0],403)
 def test_actor_payload_no_rolegrant(self):
  b=self.body();self.account['puestos']=[];self.assertEqual(self.cas(b,dict(self.account,puestos=['operaciones']))[0],403)
 def test_actor_duplicate_denied(self):
  b=self.body();self.crudo['personas'].append(dict(self.account));self.assertEqual(self.cas(b)[0],403)
 def test_wrong_client_body_denied(self):
  b=self.body();b['cliente_id']='foreign';self.assertEqual(X.validar_previo(self.account,self.account,b)[1][0],403)
 def test_invalid_target_no_fallback(self):
  b=self.body();b['vista_previa']['a']='corrección';self.assertEqual(self.cas(b)[0],400)
 def test_revision_stale_only_cas_not_pre(self):
  b=self.body();b['vista_previa']['revision']='b'*64;self.assertIsNone(X.validar_previo(self.account,self.account,b)[1]);self.assertEqual(self.cas(b)[0],409)
 def test_queue_saved_changes_revision(self):
  b=self.body()
  with self.connect() as c:c.execute("INSERT INTO acciones(quien,herramienta,tipo,objeto,modulo,vista_previa,estado) VALUES(?,?,?,?,?,?,?)",('reviewer','clickup','pieza_aprobar','task-fixture','produccion',json.dumps(b['vista_previa']),'simulada'))
  self.assertEqual(self.cas(b)[0],409)
 def test_comment_limit(self):
  b=self.body(tipo='pieza_pedir_cambios');self.assertIsNone(self.cas(b));b['vista_previa']['comentario']='x';self.assertEqual(self.cas(b)[0],400)
 def test_mover_to_review_owner_not_other(self):
  self.row['estado']=self.raw['estado']='diario';b=self.body(self.author,'mover_estado');self.assertEqual(b['vista_previa']['a'],'revisión project manager');self.assertIsNone(self.cas(b,self.author));self.assertEqual(self.cas(b,self.account)[0],403)
 def test_mover_cannot_skip_review(self):self.assertEqual(X.validar_previo(self.account,self.account,{**self.body(),'tipo':'mover_estado'})[1][0],403)
 def test_missing_catalog_denied(self):
  b=self.body();self.D['estados_lista']['list-fixture'].remove('enviar  cliente');self.assertEqual(self.cas(b)[0],409)
 def test_revocation_during_projection(self):
  b=self.body();original=T.proyectar
  def f(*a,**k):r=original(*a,**k);self.permission=False;return r
  with patch.object(T,'proyectar',f):self.assertEqual(self.cas(b)[0],403)
 def test_get_revoke_before_dto(self):
  original=T.proyectar
  def f(*a,**k):r=original(*a,**k);self.act=False;return r
  with patch.object(T,'proyectar',f),self.connect() as c:self.assertEqual(X.obtener(c,self.account,self.account)['transiciones_revision'],{})
 def test_pilot_readonly(self):
  b=self.body();os.environ['RO_PILOTO_LECTURA']='si'
  with self.connect() as c:self.assertEqual(X.obtener(c,self.account,self.account)['transiciones_revision'],{})
  self.assertEqual(self.cas(b)[0],403)
 def test_backend_translation_disagreement(self):
  b=self.body()
  def bad(a):z=list(self.translate(a));z[2]={'campo':'estado','valor':'inventado'};return z
  with patch.dict('sys.modules',{'sincronia':types.SimpleNamespace(traducir=bad)}):self.assertEqual(self.cas(b)[0],409)
 def test_author_changed_same_area_invalidates_hash(self):
  b=self.body();self.crudo['personas'].append({'id':'other-author','correo':'other@example.invalid','estado':'activo','puestos':['seo']});self.users.append({'id':'u-other','email':'other@example.invalid'});self.raw['asignados']=[{'id':'u-other'}]
  self.assertIsNone(X.validar_previo(self.account,self.account,b)[1]);self.assertEqual(self.cas(b)[0],409)
 def test_rules_changed_same_target_invalidates_hash(self):
  b=self.body();self.p.REGLAS=copy.deepcopy(self.rules);self.p.REGLAS['revision_piezas']['areas_tecnica']['jefa_seo'].append('otro-rol')
  self.assertEqual(self.cas(b)[0],409)
 def test_no_transaction(self):
  b=self.body()
  with self.connect() as c:self.assertEqual(X.validar_en_transaccion(c,self.account,b)[0],409)
 def test_get_strict_query_noidentity(self):
  class H:
   def _api_get(self,*a):return None
   def validar_accion(self,*a):return None,None
   def responder(self,status,data):return status,data
  X.enganchar(H,self.s);self.assertEqual(H()._api_get(X.RUTA,{'yo':['other']},self.account,self.account)[0],400)
 def test_core_post_actual_atomic_replay(self):
  tree=ast.parse((HERE/'servir.py').read_text());validator=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='validar_accion')
  branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and '/api/acciones' in ast.unparse(n.test) and 'INSERT INTO acciones' in ast.unparse(n))
  fun=ast.parse('def api_post(self,ruta,real,persona,b):\n pass').body[0];fun.body=[branch]
  ns={'P':self.p,'E':self.s.E,'ACT':self.s.ACT,'ve_alguno':self.s.ve_alguno,'_enlaces_malos':lambda*a:False,'pieza_en_revision':self.s.pieza_en_revision,'puede_revisar_pieza':self.s.puede_revisar_pieza,'tarea_de_produccion':self.s.tarea_de_produccion,'registrar_agrupado':lambda*a:None,'registrar':lambda*a:None,'json':json,'conectar':self.connect}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[validator,fun],type_ignores=[])),'core_real208','exec'),ns)
  class H:
   def responder(self,code,body):return code,body
   def _api_get(self,*a):return None
  H.validar_accion=ns['validar_accion'];H.api_post=ns['api_post'];X.enganchar(H,self.s);h=H();b=self.body()
  a=h.api_post('/api/acciones',self.account,self.account,copy.deepcopy(b));self.assertEqual(a[0],200)
  replay=h.api_post('/api/acciones',self.account,self.account,copy.deepcopy(b));self.assertEqual(replay[0],200);self.assertTrue(replay[1]['intencion_guardada']['repetida'])
  other=copy.deepcopy(b);other['intencion_id']='33333333-3333-4333-8333-333333333333';self.assertEqual(h.api_post('/api/acciones',self.account,self.account,other)[0],409)
  with self.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM acciones').fetchone()[0],1)
if __name__=='__main__':unittest.main()
