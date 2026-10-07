import copy,json,unittest
import probar_revision_confirmar_570 as D

class Confirmar572(unittest.TestCase):
 def setUp(self):
  self.f=D.Confirmar570();self.f.setUp()
  self.f.e.crudo.update(clientes=[],asignaciones=[])
  self.f.target.update(puestos=['account'])
  self.f.dudas[0]['persona_id']=self.f.target['id']
 def tearDown(self):self.f.tearDown()
 def payload(self,cambios=None,**kw):
  r={'tipo':'persona','duda':'d-fixture','persona_id':self.f.target['id'],'cambios':cambios if cambios is not None else {'estado':'activo'}};r.update(kw);return r
 def post(self,r):return self.f.ajustes(self.f.h,'/api/ajustes/confirmar',self.f.actor,{'respuesta':r})
 def count(self):
  with self.f.con() as c:return c.execute('SELECT count(*) FROM decisiones').fetchone()[0]
 def test_campos_privilegiados_rechazados_sin_persistir(self):
  for cambios in ({'puestos':['direccion']},{'correo':'synthetic@example.invalid'},{'jefe':'ops-fixture'},{'id':'tomas'},{'activo':False},{'estado':'baja'},{'estado':True},{'estado':None},{'estado':'activo','puestos':['direccion']},{}):
   self.assertEqual(self.post(self.payload(cambios))[0],400)
  self.assertEqual(self.count(),0);self.assertEqual(self.f.actor['puestos'],['operaciones'])
 def test_valido_activo_dudoso_preserva_identidad(self):
  before=copy.deepcopy(self.f.target)
  for estado in ('dudoso','activo'):
   self.assertEqual(self.post(self.payload({'estado':estado}))[0],200)
   self.assertEqual(self.f.target['estado'],estado);self.assertEqual(self.f.target['activo'],estado=='activo')
   self.assertEqual(self.f.target['puestos'],before['puestos'])
 def test_nota_persona_sin_modificaciones(self):
  old=copy.deepcopy(self.f.target)
  self.assertEqual(self.post({'tipo':'nota','duda':'d-fixture','nota':'Nota sintética'})[0],200)
  self.assertEqual(self.f.target,old)
  self.assertEqual(self.post({'tipo':'nota','duda':'d-fixture','nota':'Nota','cambios':{'puestos':['direccion']}})[0],400)
 def test_duda_persona_ausente_ajena_duplicada(self):
  for r in (self.payload(duda='missing'),self.payload(persona_id=self.f.actor['id']),self.payload(persona_id='missing')):
   self.assertEqual(self.post(r)[0],400)
  self.f.dudas.append(dict(self.f.dudas[0]));self.assertEqual(self.post(self.payload())[0],400);self.f.dudas.pop()
  self.f.personas.append(dict(self.f.target));self.assertEqual(self.post(self.payload())[0],400)
  self.assertEqual(self.count(),0)
 def test_formas_lista_completa_y_tipo_escondido(self):
  for r in ([],[self.payload(),None],['x'],[self.payload(),self.payload(duda='otra')],self.payload(tipo='servicio'),{},'string'):
   self.assertEqual(self.post(r)[0],400)
  self.assertEqual(self.count(),0)
 def test_revocacion_actor_catalogo_antes_insert(self):
  original=self.f.con
  from contextlib import contextmanager
  @contextmanager
  def revocar():
   self.f.actor['puestos']=['account']
   with original() as c:yield c
  # ajustes AST globals son el diccionario de la función.
  self.f.ajustes.__globals__['conectar']=revocar
  self.assertEqual(self.post(self.payload())[0],403);self.assertEqual(self.count(),0)
 def test_revocacion_duda_en_ultimo_select_no_anula_ni_guarda(self):
  original=self.f.con
  from contextlib import contextmanager
  @contextmanager
  def conexion():
   with original() as c:
    class Proxy:
     def execute(s,sql,args=()):
      cursor=c.execute(sql,args)
      if sql.startswith('SELECT id FROM decisiones'):
       self.f.dudas.clear()
      return cursor
    yield Proxy()
  self.f.ajustes.__globals__['conectar']=conexion
  self.assertEqual(self.post(self.payload())[0],403);self.assertEqual(self.count(),0)
 def test_replay_whitelist_todos_origenes_con_y_sin_catalogo(self):
  for contexto in (None,self.f.dudas):
   original=copy.deepcopy(self.f.target)
   r=self.payload({'puestos':['direccion'],'correo':'synthetic@example.invalid','estado':'baja'})
   a=self.f.aplicar([r],self.f.personas,[],{},{},'2026-10-04',dudas=contexto)
   self.assertTrue(a[0].get('error'));self.assertEqual(self.f.target,original)
   a=self.f.aplicar([None,self.payload(persona_id='ausente')],self.f.personas,[],{},{},'2026-10-04',dudas=contexto)
   self.assertTrue(all(x.get('error') for x in a))
  self.assertTrue(self.f.aplicar([self.payload(duda='otra')],self.f.personas,[],{},{},'2026-10-04',dudas=self.f.dudas)[0].get('error'))
 def test_estado_replay_antiguo_y_corrupto_omite_no_marca_respondida(self):
  with self.f.con() as c:
   c.execute('ALTER TABLE historial ADD COLUMN n INTEGER')
   for valor in (json.dumps(self.payload({'puestos':['direccion'],'estado':'activo'})), '{', 'true'):
    c.execute("INSERT INTO decisiones(tipo,respuesta) VALUES('para_confirmar',?)",(valor,))
  ns={'P':D.P,'json':json,'conectar':self.f.con,'aplicar_respuestas':self.f.aplicar,'hoy':lambda:'2026-10-04'}
  fn=D.extraer('servir.py','aplicar_ajustes',ns)
  from types import SimpleNamespace
  raw={'personas':self.f.personas,'clientes':[],'asignaciones':[],'para_confirmar':self.f.dudas}
  old=copy.deepcopy(self.f.target)
  from contextlib import redirect_stdout
  from io import StringIO
  aviso=StringIO()
  with redirect_stdout(aviso):fn(SimpleNamespace(id_app={}),raw)
  self.assertEqual(self.f.target,old);self.assertFalse(self.f.dudas[0].get('respondida',False))
  self.assertIn('omitida',aviso.getvalue());self.assertNotIn(self.f.target['id'],aviso.getvalue())
 def test_baja_no_resucitar(self):
  self.f.target['estado']='baja';self.f.target['activo']=False
  self.assertEqual(self.post(self.payload())[0],400)
  a=self.f.aplicar([self.payload()],self.f.personas,[],{},{},'2026-10-04',dudas=self.f.dudas)
  self.assertTrue(a[0].get('error'));self.assertEqual(self.f.target['estado'],'baja')
 def test_estado_mando_mismo_limite_que_ajustes_persona(self):
  self.f.target['puestos']=['direccion']
  self.assertEqual(self.post(self.payload({'estado':'dudoso'}))[0],403)
  self.assertEqual(self.count(),0)
  self.assertEqual(self.post({'tipo':'nota','duda':'d-fixture','nota':'Nota sintética'})[0],200)
 def test_otros_tipos_validos_no_se_modifican(self):
  self.f.dudas[:]=[{'id':'s1','tipo':'servicio'}]
  r={'tipo':'servicio','duda':'s1','cliente_id':'c1','servicio':'seo','valor':'si'}
  self.assertEqual(self.post(r)[0],200)
 def test_ajustes_normales_control_no_ampliado(self):
  self.assertEqual(self.f.normal({'puestos':['direccion']})[0],403)
  self.assertEqual(self.f.normal({'imputa_horas':False},self.f.target['id'])[0],200)

if __name__=='__main__':unittest.main()
