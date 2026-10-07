import os,sqlite3,tempfile,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import evidencias_kpi_api as A
from evidencias_kpi import ArchivoEvidencias,ErrorEvidencia

class Api(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name).resolve()/'privado'/'registros.sqlite3'
  self.env=patch.dict(os.environ,{'RO_EVIDENCIAS_KPI':str(self.path)},clear=True);self.env.start()
  people=[{'id':i,'estado':'activo','puestos':[r]} for i,r in [('own','account'),('ops','operaciones'),('other','account'),('seo','seo')]]
  self.S=SimpleNamespace(E=SimpleNamespace(nucleo_bloqueado=False,crudo={'personas':people,'clientes':[{'id':'uno'},{'id':'dos'}]}),ACT=SimpleNamespace(es_activo_id=lambda cid:cid=='uno'))
  self.can=True;self.respond=True
  self.S.P=SimpleNamespace(contexto=lambda p,c:{},ver=lambda p,d,cp:{'ok':self.can and p['id']!='other' and (d['tipo']!='responder_cliente' or self.respond)})
  self.S.ve_alguno=lambda p,mods:mods==['mi-trabajo']
  class H:
   def responder(self,n,obj):return n,obj
   def _api_get(self,*a):return 418,{'paso':'get'}
   def api_post(self,*a):return 418,{'paso':'post'}
  A.enganchar(H,self.S);self.h=H();self.own={'id':'own'};self.ops={'id':'ops'}
  self.body={'accion':'registrar','clave':str(uuid.uuid4()),'cliente_id':'uno','tipo':'contacto','canal':'email','fecha':'2026-09-30T10:00:00Z','motivo':'seguimiento'}
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def post(self,b=None,real=None,vista=None):return self.h.api_post(A.RUTA,real or self.own,vista or real or self.own,b or self.body)
 def get(self,q=None,real=None,vista=None):return self.h._api_get(A.RUTA,q or {'cliente_id':['uno']},real or self.own,vista or real or self.own)
 def test_hook_no_crea_y_passthrough(self):
  self.assertFalse(self.path.exists());self.assertEqual(self.h.api_post('/otra',self.own,self.own,{} )[0],418);self.assertFalse(self.path.exists())
 def test_registrar_replay_get_y_revocar(self):
  n,r=self.post();self.assertEqual(n,200);self.assertEqual(r['resultado'],'aceptado');self.assertEqual(self.post()[1]['resultado'],'duplicado')
  row=self.get()[1]['registros'][0];self.assertFalse(row['verificacion_externa']);self.assertIsNone(row['cumplimiento'])
  b={'accion':'revocar','cliente_id':'uno','clave':str(uuid.uuid4()),'registro_id':row['id'],'motivo':'correccion'}
  self.assertEqual(self.post(b,real=self.ops)[0],403);self.assertEqual(self.post(b)[1]['registro']['estado'],'revocado')
  self.assertEqual(self.post(b)[1]['resultado'],'duplicado');self.assertEqual(self.post()[1]['registro']['estado'],'revocado')
 def test_view_y_cliente_ajeno(self):
  self.assertEqual(self.post(vista=self.ops)[0],403);self.assertEqual(self.get(real=self.ops,vista={'id':'other'})[0],403);self.assertEqual(self.post({**self.body,'cliente_id':'dos'})[0],403);self.assertFalse(self.path.exists())
 def test_roles_canonicos_no_browser(self):
  self.assertEqual(self.post(real={'id':'seo','puestos':['direccion']})[0],403)
  self.S.E.crudo['personas'][0]['estado']='baja';self.assertEqual(self.get()[0],403);self.assertFalse(self.path.exists())
 def test_canonicos_duplicados_y_faltantes(self):
  for campo in ('personas','clientes'):
   original=list(self.S.E.crudo[campo]);self.S.E.crudo[campo].append(original[0].copy());self.assertEqual(self.post()[0],403);self.S.E.crudo[campo]=original
  self.assertEqual(self.get(real={'id':'ausente'})[0],403);self.assertFalse(self.path.exists())
 def test_filtros_payload_y_responder(self):
  self.assertEqual(self.get({'cliente_id':['uno','dos']})[0],400);self.assertEqual(self.get({'cliente_id':['uno'],'ids':['dos']})[0],400)
  self.assertEqual(self.post({**self.body,'source_kind':'externo'})[0],400);self.respond=False;self.assertEqual(self.post()[0],403);self.assertEqual(self.get()[0],200)
 def test_permission_revocado_dentro_transaccion(self):
  orig=ArchivoEvidencias._conectar
  from contextlib import contextmanager
  @contextmanager
  def conectar(a):
   with orig(a) as con:
    # Constructor hace executescript antes: revocar justo en conexión de mutación.
    if con.execute("SELECT count(*) FROM sqlite_master WHERE name='registros'").fetchone()[0]:self.can=False
    yield con
  with patch.object(ArchivoEvidencias,'_conectar',conectar):self.assertEqual(self.post()[0],403)
  with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM registros').fetchone()[0],0)
 def test_scope_cambia_antes_replay(self):
  self.post();self.can=False;self.assertEqual(self.post()[0],403);self.assertEqual(self.get()[0],403)
 def test_permiso_cambia_durante_lectura_y_filtros_identidad(self):
  self.post();original=ArchivoEvidencias.listar
  def lectura(a,*args,**kwargs):
   doc=original(a,*args,**kwargs);self.can=False;return doc
  with patch.object(ArchivoEvidencias,'listar',lectura):
   n,d=self.get();self.assertEqual(n,403);self.assertNotIn('registros',d)
  self.assertEqual(self.get({'cliente_id':['uno'],'yo':['ops']})[0],400)
 def test_error_sql_no_falso_recibo(self):
  self.get()
  with sqlite3.connect(self.path) as c:c.execute("CREATE TRIGGER fallo BEFORE INSERT ON eventos BEGIN SELECT RAISE(ABORT,'fixture'); END")
  n,r=self.post();self.assertEqual(n,503);self.assertNotIn('registro',r)
  with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM registros').fetchone()[0],0)
 def test_external_mode_sin_deposito_explicit(self):
  with patch.dict(os.environ,{'PGDATABASE_URL':'postgresql://fixture'},clear=True):self.assertEqual(self.post()[0],503)
  self.assertFalse(self.path.exists())
 def test_privacidad_archivo(self):
  self.post();self.assertEqual(self.path.stat().st_mode&0o777,0o600);self.assertEqual(self.path.parent.stat().st_mode&0o777,0o700)
  self.path.chmod(0o644);self.assertEqual(self.get()[0],503)
 def test_resumen_semana_scoped_revocado_y_no_actividad(self):
  r=self.post()[1]['registro'];self.post({**self.body,'clave':str(uuid.uuid4()),'tipo':'reunion','canal':'video'})
  self.post({'accion':'revocar','cliente_id':'uno','clave':str(uuid.uuid4()),'registro_id':r['id'],'motivo':'correccion'})
  n,d=self.h._api_get(A.RUTA+'/resumen',{'semana_inicio':['2026-09-28']},self.own,self.own)
  self.assertEqual(n,200);self.assertEqual(len(d['clientes']),1);self.assertEqual(d['clientes'][0]['contactos_declarados'],0);self.assertEqual(d['clientes'][0]['reuniones_declaradas'],1);self.assertIsNone(d['cumplimiento']);self.assertEqual(d['cobertura'],'parcial')
  self.assertEqual(self.h._api_get(A.RUTA+'/resumen',{'semana_inicio':['2026-09-29']},self.own,self.own)[0],400)
  self.assertEqual(self.h._api_get(A.RUTA+'/resumen',{'semana_inicio':['2026-09-28'],'cliente_id':['uno']},self.own,self.own)[0],400)
  self.assertEqual(self.h._api_get(A.RUTA+'/resumen',{'semana_inicio':['2026-09-28']},self.ops,{'id':'seo'})[0],403)
if __name__=='__main__':unittest.main()
