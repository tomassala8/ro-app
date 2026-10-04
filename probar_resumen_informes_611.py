"""611: API y política reales; únicamente SQLite y catálogos sintéticos temporales."""
import copy,json,os,sqlite3,tempfile,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import permisos as P
import evidencias_kpi_api as A

class Informes611(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name).resolve()/'privado'/'fixture.sqlite3'
  self.env=patch.dict(os.environ,{'RO_EVIDENCIAS_KPI':str(self.path)},clear=True);self.env.start()
  self.own={'id':'own','estado':'activo','activo':True,'puestos':['account']};self.ops={'id':'ops','estado':'activo','activo':True,'puestos':['operaciones']}
  self.other={'id':'other','estado':'activo','activo':True,'puestos':['account']}
  self.activos={'uno','dos'}
  self.S=SimpleNamespace(P=P,E=SimpleNamespace(nucleo_bloqueado=False,modulos=P.cargar_modulos(),crudo={'personas':[self.own,self.ops,self.other],'clientes':[{'id':i,'activo':True,'estado':'activo'} for i in ['uno','dos']], 'asignaciones':[{'cliente_id':i,'persona_id':p,'silla':'account','principal':True,'confianza':'confirmada'} for i,p in [('uno','own'),('dos','other')]]}),ACT=SimpleNamespace(estado=lambda:{'activos':set(self.activos)},es_activo_id=lambda cid:cid in self.activos))
  self.S.ve_alguno=self.ve
  class H:
   def responder(self,n,d):return n,d
   def _api_get(self,*a):return 404,{}
   def api_post(self,*a):return 404,{}
  A.enganchar(H,self.S);self.h=H();self.reglas=copy.deepcopy(P.REGLAS)
  self.body={'accion':'registrar','clave':str(uuid.uuid4()),'cliente_id':'uno','tipo':'informe_enviado','canal':'email','fecha':'2026-09-30T10:00:00Z','motivo':'revision','periodo_informe':'2026-08','enlace':'https://app.clickup.com/t/fixture'}
 def ve(self,p,ms):
  return any(P.nivel_modulo(p,self.S.E.modulos.get(m,{})) for m in ms)
 def tearDown(self):
  P.REGLAS.clear();P.REGLAS.update(self.reglas);self.env.stop();self.tmp.cleanup()
 def post(self,**kwargs):return self.h.api_post(A.RUTA,self.own,self.own,{**self.body,**kwargs})
 def get(self,q=None,real=None,vista=None):
  r=real or self.own;return self.h._api_get(A.RUTA+'/informes',q if q is not None else {'periodo_informe':['2026-08']},r,vista or r)
 def crear(self):
  code,d=self.post();self.assertEqual(code,200,d);return d['registro']
 def test_periodo_informe_no_mes_envio_y_salida_minima(self):
  self.crear();n,d=self.get();self.assertEqual(n,200,d);self.assertEqual(d['clientes'][0]['informes_declarados'],1)
  self.assertEqual(self.get({'periodo_informe':['2026-09']})[1]['clientes'][0]['informes_declarados'],0)
  self.assertEqual(set(d),{'version','periodo_informe','source_kind','clientes','cobertura','verificacion_externa','cumplimiento','nota'})
  self.assertEqual(set(d['clientes'][0]),{'cliente_id','informes_declarados','source_kind','verificacion_externa','cumplimiento'})
  self.assertFalse(d['verificacion_externa']);self.assertIsNone(d['cumplimiento']);self.assertEqual(d['cobertura'],'parcial')
 def test_replay_revocado_contactos_reuniones_no_cuentan(self):
  r=self.crear();self.post();self.post(clave=str(uuid.uuid4()),tipo='contacto',periodo_informe=None)
  self.assertEqual(self.get()[1]['clientes'][0]['informes_declarados'],1)
  b={'accion':'revocar','clave':str(uuid.uuid4()),'cliente_id':'uno','registro_id':r['id'],'motivo':'correccion'}
  self.assertEqual(self.h.api_post(A.RUTA,self.own,self.own,b)[0],200)
  self.assertEqual(self.get()[1]['clientes'][0]['informes_declarados'],0)
 def test_query_estricta(self):
  for q in ({},{'periodo_informe':['2026-08','2026-09']},{'periodo_informe':'2026-08'},{'periodo_informe':['2026-08'],'cliente_id':['dos']},{'periodo_informe':['2026-8']},{'periodo_informe':['9999-01']},{'periodo_informe':[True]}):
   self.assertEqual(self.get(q)[0],400)
  self.assertFalse(self.path.exists());self.assertEqual(self.h.api_post(A.RUTA+'/informes',self.own,self.own,{})[0],404)
 def test_ausente_no_crea_ni_cero(self):
  self.assertEqual(self.get()[0],503);self.assertFalse(self.path.exists());self.assertFalse(self.path.parent.exists())
 def test_scope_real_interseccion_vista(self):
  self.crear();self.assertEqual([r['cliente_id'] for r in self.get(real=self.ops,vista=self.own)[1]['clientes']],['uno'])
  self.assertEqual(self.get(real=self.own,vista=self.other)[1]['clientes'],[])
 def test_identidad_duplicada_inactiva_y_roles_no_body(self):
  with patch.object(A,'_leer_informes611',side_effect=AssertionError('IO prohibido')):
   self.S.E.crudo['personas'].append(copy.deepcopy(self.own));self.assertEqual(self.get()[0],403);self.S.E.crudo['personas'].pop()
   self.own['estado']='baja';self.assertEqual(self.get()[0],403);self.own['estado']='activo'
   self.own['puestos']=['seo'];self.assertEqual(self.get(real={'id':'own','puestos':['operaciones']})[0],403)
 def test_clientes_ACT_duplicados_y_unknown_omitidos(self):
  self.crear();self.activos.remove('uno');self.assertEqual(self.get()[1]['clientes'],[]);self.activos.add('uno')
  self.S.E.crudo['clientes'].append({'id':'uno','activo':True});self.assertEqual(self.get()[1]['clientes'],[])
 def test_corrupcion_schema_y_payload_no_cero(self):
  self.crear()
  with sqlite3.connect(self.path) as c:c.execute("UPDATE registros SET payload='{}'")
  self.assertEqual(self.get()[0],503)
  with sqlite3.connect(self.path) as c:c.execute('DROP TABLE registros')
  self.assertEqual(self.get()[0],503)
 def test_revocacion_durante_IO_y_ultima_validacion(self):
  self.crear();original=A._leer_informes611
  for mutate in (lambda:self.activos.discard('uno'),lambda:self.own.update(estado='baja'),lambda:self.S.E.crudo['asignaciones'].clear(),lambda:P.REGLAS.update(_fixture611=True)):
   crudo=copy.deepcopy(self.S.E.crudo);acts=set(self.activos)
   def leer(p):
    rows=original(p);mutate();return rows
   with patch.object(A,'_leer_informes611',leer):self.assertEqual(self.get()[0],403)
   self.S.E.crudo=crudo;self.own=crudo['personas'][0];self.activos=acts;P.REGLAS.clear();P.REGLAS.update(copy.deepcopy(self.reglas))
 def test_archivo_permisos_symlink_y_solo_lectura(self):
  self.crear();before=self.path.read_bytes();self.assertEqual(self.get()[0],200);self.assertEqual(self.path.read_bytes(),before)
  self.path.chmod(0o644);self.assertEqual(self.get()[0],503);self.path.chmod(0o600)
  link=self.path.parent/'link.sqlite';link.symlink_to(self.path)
  with patch.dict(os.environ,{'RO_EVIDENCIAS_KPI':str(link)}):self.assertEqual(self.get()[0],503)
 def test_json_ambiguo_y_no_finito(self):
  self.crear()
  with sqlite3.connect(self.path) as c:raw=c.execute('SELECT payload FROM registros').fetchone()[0]
  for bad in (raw[:-1]+',"cliente_id":"uno"}',raw[:-1]+',"campo":NaN}'):
   with sqlite3.connect(self.path) as c:c.execute('UPDATE registros SET payload=?',(bad,))
   self.assertEqual(self.get()[0],503)
 def test_revocacion_durante_validacion_DTO(self):
  self.crear();orig=A.validar_registro
  def validar(*args):
   d=orig(*args);self.own['puestos']=['seo'];return d
  with patch.object(A,'validar_registro',validar):self.assertEqual(self.get()[0],403)
 def test_revocacion_en_ultima_puerta_y_modulo(self):
  self.crear();orig=P.ver;count=[0]
  def ver(*args,**kwargs):
   d=orig(*args,**kwargs);count[0]+=1
   if count[0]==5:self.S.E.crudo['clientes'][0]['activo']=False
   return d
  with patch.object(P,'ver',ver):self.assertEqual(self.get()[0],403)
  self.S.E.crudo['clientes'][0]['activo']=True
  origleer=A._leer_informes611
  def leer(p):
   rows=origleer(p);self.S.E.modulos['mi-trabajo']={};return rows
  with patch.object(A,'_leer_informes611',leer):self.assertEqual(self.get()[0],403)
 def test_duplicados_registro_no_inflan_y_source_corrupto_no_publica(self):
  self.crear();orig=A._leer_informes611
  with patch.object(A,'_leer_informes611',side_effect=lambda p:orig(p)*2):self.assertEqual(self.get()[0],503)
  with sqlite3.connect(self.path) as c:
   raw=json.loads(c.execute('SELECT payload FROM registros').fetchone()[0]);raw['verificacion_externa']=True
   c.execute('UPDATE registros SET payload=?',(json.dumps(raw),))
  self.assertEqual(self.get()[0],503)
 def test_semanal_contactos_y_reuniones_intactos(self):
  self.crear();b={k:v for k,v in self.body.items() if k!='periodo_informe'}
  b.update(clave=str(uuid.uuid4()),tipo='contacto');self.assertEqual(self.h.api_post(A.RUTA,self.own,self.own,b)[0],200)
  n,d=self.h._api_get(A.RUTA+'/resumen',{'semana_inicio':['2026-09-28']},self.own,self.own)
  self.assertEqual(n,200);self.assertEqual(d['clientes'][0]['contactos_declarados'],1);self.assertEqual(d['clientes'][0]['reuniones_declaradas'],0)
if __name__=='__main__':unittest.main()
