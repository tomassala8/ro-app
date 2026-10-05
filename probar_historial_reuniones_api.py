import copy,hashlib,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import permisos as P
import historial_reuniones_api as H

ROW={'id':'fathom_'+'a'*24,'cliente_id':'c','fecha':'2026-09-20','fecha_fuente':'recording_start_time','fecha_discrepancia':False,'fechas_evidencia':{'cache':'2026-09-20'},'enlace_cliente':'catalogo_confirmado','transcripcion_disponible':True,'titulo':'SECRET_PRIVATE_TITLE','host':'PRIVATE_HOST','texto':'PRIVATE_TRANSCRIPT','url':'https://fathom.video/calls/999','account_historico':{'persona_id':'account_actual'}}
CAT={'Carpeta':{'cliente_id':'c','confirmado':True,'fuente':'documento literal','hash_fuente':'b'*64}}
VALID={'red':False,'transcripciones_copiadas':False,'contratos_completos_copiados':False}

def guardar(p,d):
 p.write_text(json.dumps(d));p.chmod(0o600)

def origen(p,rows=None,cat=None):
 p.mkdir(mode=0o700)
 for n,d in [('catalogo_confirmado.json',cat or CAT),('reuniones_candidatas.json',{'reuniones':rows if rows is not None else [copy.deepcopy(ROW)]}),('validacion.json',VALID)]:guardar(p/n,d)
 guardar(p/'manifest_entregables.json',[{'archivo':str(p/n),'sha256':hashlib.sha256((p/n).read_bytes()).hexdigest()} for n in ('catalogo_confirmado.json','reuniones_candidatas.json','validacion.json')])

class Historial(unittest.TestCase):
 def test_preparacion_y_allowlist(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve();origen(p/'entrada');r=H.preparar_fuente(p/'entrada',p/'salida','2026-10-03');self.assertEqual(r['registros'],1)
   doc=H.cargar_fuente(p/'salida','c');s=json.dumps(doc);self.assertEqual(doc['total'],1);self.assertIn('Sin evidencia',s)
   for no in ('SECRET','PRIVATE','fathom_','999','account_actual',str(p),'titulo','host','texto','resumen'):self.assertNotIn(no,s)
   self.assertFalse(doc['registros'][0]['celebrada_confirmada']);self.assertEqual((p/'salida').stat().st_mode&0o777,0o700)
 def test_hash_mal_y_catalogo_unknown(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve();origen(p/'entrada');guardar(p/'entrada/reuniones_candidatas.json',{'reuniones':[]});self.assertRaises(ValueError,H.preparar_fuente,p/'entrada',p/'salida','2026-10-03');self.assertFalse((p/'salida').exists())
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve();origen(p/'entrada',cat={'Carpeta':{**CAT['Carpeta'],'confirmado':False}});H.preparar_fuente(p/'entrada',p/'salida','2026-10-03');self.assertEqual(H.cargar_fuente(p/'salida','c')['total'],0)
 def test_replay_y_conflicto(self):
  for r2,ok in [(ROW,True),({**ROW,'fecha':'2026-09-21'},False)]:
   with tempfile.TemporaryDirectory() as t:
    p=Path(t).resolve();origen(p/'entrada',rows=[ROW,r2])
    if ok:self.assertEqual(H.preparar_fuente(p/'entrada',p/'salida','2026-10-03')['registros'],1)
    else:self.assertRaises(ValueError,H.preparar_fuente,p/'entrada',p/'salida','2026-10-03')
 def test_fecha_ambigua_y_futura_no_ingresa(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve();r={**ROW,'fecha_discrepancia':True,'fechas_evidencia':{'cache':'2026-09-20','documentos':['2026-09-21']}};origen(p/'entrada',rows=[r,{**ROW,'id':'fathom_'+'c'*24,'fecha':'2026-10-04'}]);H.preparar_fuente(p/'entrada',p/'salida','2026-10-03');d=H.cargar_fuente(p/'salida','c');self.assertEqual(d['total'],1);self.assertTrue(d['registros'][0]['fecha_ambigua'])
 def test_deposito_alterado_manifest_duplicado(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve();origen(p/'entrada');H.preparar_fuente(p/'entrada',p/'salida','2026-10-03');guardar(p/'salida/reuniones.json',{});self.assertRaises(ValueError,H.cargar_fuente,p/'salida','c')
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve();origen(p/'entrada');m=json.loads((p/'entrada/manifest_entregables.json').read_text());guardar(p/'entrada/manifest_entregables.json',m+[m[0]]);self.assertRaises(ValueError,H.preparar_fuente,p/'entrada',p/'salida','2026-10-03')
 def test_descriptor0600_y_default_compatible(self):
  from fuentes_historial_reuniones.normalizador import leer_privado
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve();f=p/'metadatos';f.write_text('{}');f.chmod(0o644)
   self.assertEqual(leer_privado(f,p),b'{}');self.assertRaises(ValueError,leer_privado,f,p,modo_privado=True)
   f.chmod(0o600);self.assertEqual(leer_privado(f,p,modo_privado=True),b'{}')
 def test_permisos_symlink_hardlink_tamano(self):
  for modo in ('chmod','symlink','hardlink','size'):
   with tempfile.TemporaryDirectory() as t:
    p=Path(t).resolve();origen(p/'entrada');f=p/'entrada/catalogo_confirmado.json'
    if modo=='chmod':f.chmod(0o644)
    if modo=='symlink':f.unlink();f.symlink_to(p/'fuera')
    if modo=='hardlink':os.link(f,p/'copia')
    if modo=='size':f.write_bytes(b'x'*(H.MAX_BYTES+1))
    self.assertRaises((ValueError,OSError),H.preparar_fuente,p/'entrada',p/'salida','2026-10-03')
 def stub(self):
  class M:
   def _api_get(self,*args):return ('anterior',args[0])
   def responder(self,status,data):return status,data
  personas=[{'id':'dir','puestos':['direccion']},{'id':'ops','puestos':['operaciones']},{'id':'account','puestos':['account']},{'id':'otroaccount','puestos':['account']},{'id':'seo','puestos':['seo']}]
  S=NS(E=NS(nucleo_bloqueado=False,crudo={'clientes':[{'id':'c','servicios':{}}],'personas':personas,'asignaciones':[{'persona_id':'account','cliente_id':'c','silla':'account'}]}),P=P,ACT=NS(es_activo_id=lambda cid:cid=='c'))
  H.enganchar(M,S);return M(),S,{p['id']:p for p in personas}
 def test_permisos_reales_rol_cartera_y_vista(self):
  m,s,ps=self.stub()
  for a,b in [('dir','dir'),('ops','account'),('account','account')]:
   with patch.dict(os.environ,{'RO_HISTORIAL_REUNIONES':'/fuente'}),patch.object(H,'cargar_fuente',return_value={'ok':True}) as f:
    self.assertEqual(m._api_get('/api/historial/reuniones',{'cliente_id':['c']},ps[a],ps[b])[0],200);f.assert_called_once()
  for a,b in [('seo','dir'),('dir','seo'),('otroaccount','account'),('dir','otroaccount')]:
   with patch.object(H,'cargar_fuente') as f:
    self.assertEqual(m._api_get('/api/historial/reuniones',{'cliente_id':['c']},ps[a],ps[b])[0],403);f.assert_not_called()
 def test_expiracion_asignacion_rechaza(self):
  m,s,ps=self.stub();s.E.crudo['asignaciones'][0]['hasta']='2020-01-01'
  self.assertEqual(m._api_get('/api/historial/reuniones',{'cliente_id':['c']},ps['account'],ps['account'])[0],403)
 def test_sin_fuente_unknown_y_invalida(self):
  m,s,ps=self.stub()
  with patch.dict(os.environ,{},clear=True):
   r=m._api_get('/api/historial/reuniones',{'cliente_id':['c']},ps['dir'],ps['dir']);self.assertEqual(r[1]['estado_fuente'],'sin_configurar');self.assertIsNone(r[1]['total'])
  with patch.dict(os.environ,{'RO_HISTORIAL_REUNIONES':'/no-existe'}):self.assertEqual(m._api_get('/api/historial/reuniones',{'cliente_id':['c']},ps['dir'],ps['dir'])[0],503)
 def test_query_path_act_bloqueo(self):
  m,s,ps=self.stub()
  for q,status in [({'cliente_id':['c','c']},400),({'cliente_id':['../c']},404),({'cliente_id':['c'],'path':['fuera']},400),({'cliente_id':['baja']},404)]:
   with patch.object(H,'cargar_fuente') as f:self.assertEqual(m._api_get('/api/historial/reuniones',q,ps['dir'],ps['dir'])[0],status);f.assert_not_called()
  s.E.nucleo_bloqueado=True;self.assertEqual(m._api_get('/api/historial/reuniones',{'cliente_id':['c']},ps['dir'],ps['dir'])[0],503)
  self.assertEqual(m._api_get('/api/otra',{},ps['dir'],ps['dir']),('anterior','/api/otra'))
if __name__=='__main__':unittest.main()
