import copy,hashlib,json,os,tempfile,types,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
import permisos as P
import urgencias_observadas_api_402 as B
from fuentes_produccion.urgencias_observadas_398 import construir
class APIUrgencias402(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name).resolve()/'deposito';self.folder.mkdir(mode=0o700);self.path=self.folder/'candidato.json';self.now=datetime(2026,10,4,1,tzinfo=timezone.utc)
  self.raw={'personas':[{'id':pid,'estado':'activo','puestos':[rol]} for pid,rol in [('ops','operaciones'),('a','account'),('b','account'),('paid','trafficker'),('admin','administracion')]],'clientes':[{'id':cid,'activo':True,'servicios':{'publicidad':'sí'}} for cid in ('c1','c2')],'asignaciones':[{'cliente_id':'c1','persona_id':'a','silla':'account','principal':True},{'cliente_id':'c2','persona_id':'b','silla':'account','principal':True},{'cliente_id':'c1','persona_id':'paid','silla':'trafficker','principal':True}]}
  self.modulos=P.cargar_modulos();self.act={'c1','c2'}
  def modulo(p,mods):
   ns=[P.nivel_modulo(p,self.modulos.get(m,{})) for m in mods];ns=[n for n in ns if n];return max(ns,key=lambda x:('resumen','suyo','todo').index(x)) if ns else None
  self.S=types.SimpleNamespace(E=types.SimpleNamespace(crudo=self.raw,nucleo_bloqueado=False),P=types.SimpleNamespace(ver=P.ver,contexto=P.contexto,PUESTO=P.PUESTO,REGLAS=P.REGLAS),ACT=types.SimpleNamespace(es_activo_id=lambda cid:cid in self.act),ve_alguno=modulo)
  t={'id':'t1','lista_id':'l1','carpeta_id':'f1','prioridad':'urgent','estado':'en curso','tipo_estado':'custom','estado_fuente':'clickup','estado_leido_utc':'2026-10-03T10:00:00Z'}
  tareas={'tareas':[t,{**t,'id':'t2','estado':'hecho','tipo_estado':'closed'},{**t,'id':'t3','carpeta_id':'f2'}]};cat={'listas':{'l1':{'ok':True,'estados':[{'status':'en curso','type':'custom'},{'status':'hecho','type':'closed'}]}}}
  self.doc=construir(tareas,cat,{'f1':('c1',None),'f2':('c2',None)},{'c1','c2'},self.now);self.sources={}
  for k,d in {'tareas':tareas,'catalogo_estados':cat,'ACT':{'activos':['c1','c2']},'cliente_documento:0':{'id':'c1'}}.items():
   path=self.folder/(k.replace(':','_')+'.source');path.write_text(json.dumps(d));path.chmod(0o600);self.sources[k]=path
  self.hashes={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in self.sources.items()};self.save();self.env=patch.dict(os.environ,{B.ENV:''});self.env.start();self.addCleanup(self.env.stop)
 def save(self):
  data=json.dumps(self.doc,allow_nan=False).encode();self.path.write_bytes(data);self.path.chmod(0o600);self.sha=hashlib.sha256(data).hexdigest();m={'version':'398.1','promovido':False,'lectura_no_concede_permiso':True,'candidato_sha256':self.sha,'fuentes_sha256':self.hashes};raw=json.dumps(m).encode();p=self.folder/'manifest.json';p.write_bytes(raw);p.chmod(0o600);self.msha=hashlib.sha256(raw).hexdigest()
 def call(self,r='ops',v=None,**kw):
  with patch.object(B,'SHA',self.sha),patch.object(B,'MANIFEST_SHA',self.msha):return B.listar(self.S,r,v or r,path=self.path,ahora=self.now,fuentes=self.sources,**kw)
 def denied(self,code=403,**kw):
  with self.assertRaises(B.ErrorUrgencias) as e:self.call(**kw)
  self.assertEqual(e.exception.codigo,code)
 def test_default_open_scoped_without_current_claim(self):
  d=self.call();self.assertEqual(len(d['filas']),2);self.assertEqual(d['finales_en_copia'],1);self.assertEqual(d['abiertas_en_copia'],2);self.assertIsNone(d['urgencias_actuales']);self.assertFalse(d['verificacion_conjunta']);self.assertTrue(all(not r['final_flujo_en_copia'] for r in d['filas']));self.assertEqual(d['lectura_hasta_utc'],'2026-10-03T10:00:00Z')
 def test_closed_separate_not_reopened(self):
  d=self.call(grupo='finales');self.assertEqual([r['tarea_id'] for r in d['filas']],['t2']);self.assertFalse(d['filas'][0]['aceptacion_verificada']);self.assertIsNone(d['filas'][0]['es_fuego_actual'])
 def test_account_own_and_paid_cartera_real_policy(self):
  for actor in ('a','paid'):
   d=self.call(r=actor,grupo='todas');self.assertEqual(d['cliente_ids'],['c1']);self.assertEqual(len(d['filas']),2);self.assertEqual(d['abiertas_en_copia'],1)
 def test_viewas_intersection_and_reverse_denied(self):
  self.assertEqual(self.call(v='a')['cliente_ids'],['c1']);self.denied(r='a',v='ops')
 def test_roles_unique_active_canonical(self):
  for roles in [['account','account'],['account',12],[],['paid']]:
   self.raw['personas'][1]['puestos']=roles;self.denied(r='a')
  self.raw['personas'][1]['puestos']=['account'];self.raw['personas'].append(copy.deepcopy(self.raw['personas'][1]));self.denied(r='a')
 def test_inactive_real_or_view(self):
  self.raw['personas'][0]['estado']='baja';self.denied();self.raw['personas'][0]['estado']='activo';self.raw['personas'][1]['activo']=False;self.denied(v='a')
 def test_no_enrojo_wildcard_grant(self):
  self.S.ve_alguno=lambda p,ms:'todo' if ms==['en-rojo'] else None;self.denied();self.denied(r='admin')
 def test_module_real_level_not_bool(self):
  for level in (True,False,None,'bad'):
   self.S.ve_alguno=lambda *a,n=level:n;self.denied()
 def test_client_filter_current_scope(self):
  d=self.call(cliente_id='c1');self.assertEqual(d['cliente_ids'],['c1']);self.assertEqual(d['observaciones'],1);self.denied(r='a',cliente_id='c2');self.denied(code=400,cliente_id={});self.denied(code=400,grupo='closed')
 def test_duplicate_or_inactive_clients_not_emitted(self):
  self.raw['clientes'].append(copy.deepcopy(self.raw['clientes'][0]));self.assertEqual(self.call()['cliente_ids'],['c2']);self.act.clear();d=self.call();self.assertEqual(d['filas'],[]);self.assertIsNone(d['observaciones']);self.assertIsNone(d['urgencias_actuales'])
 def test_corrupt_permission_catalog_controlled(self):
  self.raw['asignaciones'][0].pop('cliente_id');self.denied(code=503,r='a')
 def test_no_env_no_read_no_zero(self):
  with patch.object(B,'cargar',side_effect=AssertionError('IO')):d=B.listar(self.S,'ops','ops',ahora=self.now)
  self.assertEqual(d['estado'],'sin_dato');self.assertIsNone(d['abiertas_en_copia']);self.assertIsNone(d['sha256_candidato'])
 def test_source_and_catalog_hash_change_rejects(self):
  for key in ('tareas','catalogo_estados','ACT','cliente_documento:0'):
   p=self.sources[key];old=p.read_bytes();p.write_bytes(b'{}');self.denied(code=503);p.write_bytes(old)
 def test_candidate_and_manifest_pin_corrupt(self):
  self.path.write_text('{}');self.denied(code=503);self.save();(self.folder/'manifest.json').write_text('{}');self.denied(code=503)
 def test_private_permissions_symlink_fifo(self):
  self.path.chmod(0o644);self.denied(code=503);self.path.chmod(0o600);self.folder.chmod(0o755);self.denied(code=503);self.folder.chmod(0o700)
  p=self.sources['tareas'];p.unlink();os.mkfifo(p);self.denied(code=503)
 def test_malformed_typed_rows_not_exported(self):
  original=copy.deepcopy(self.doc)
  for mut in [lambda r:r.update(tarea_id=[]),lambda r:r.update(prioridad='high'),lambda r:r.update(final_flujo_en_copia=True),lambda r:r.update(es_fuego_actual=True),lambda r:r.update(verificacion_conjunta=True),lambda r:r.update(cliente_id={}),lambda r:r.update(money=999),lambda r:r.update(estado_leido_utc='2026-10-04T02:00:00Z')]:
   self.doc=copy.deepcopy(original);mut(self.doc['filas'][0]);self.save();self.denied(code=503)
 def test_duplicates_partition_closed_inconsistent(self):
  self.doc['filas'].append(copy.deepcopy(self.doc['filas'][0]));self.save();self.denied(code=503)
 def test_catalog_exact_not_global_label(self):
  self.doc['filas'][0]['lista_id']='foreign';self.save();self.denied(code=503)
 def test_revoke_during_final_io_denied(self):
  original=B.verificar_fuentes;calls=0
  def read(m,p):
   nonlocal calls
   calls+=1;d=original(m,p)
   if calls==2:self.act.remove('c1')
   return d
  with patch.object(B,'verificar_fuentes',read):self.denied()
 def test_revocation_after_last_file_read_denied(self):
  original=B.cargar;calls=0
  def read(path):
   nonlocal calls
   calls+=1;d=original(path)
   if calls==2:self.raw['personas'][0]['estado']='baja'
   return d
  with patch.object(B,'cargar',read):self.denied()
 def test_duplicate_client_after_last_read_denied(self):
  original=B.cargar;calls=0
  def read(path):
   nonlocal calls
   calls+=1;d=original(path)
   if calls==2:self.raw['clientes'].append(copy.deepcopy(self.raw['clientes'][0]))
   return d
  with patch.object(B,'cargar',read):self.denied()
 def test_roles_or_module_rotate_after_read_denied(self):
  original=B.cargar
  def read(path):
   d=original(path);self.raw['personas'][0]['puestos'].append('seo');return d
  with patch.object(B,'cargar',read):self.denied()
 def test_identity_rotation_during_scope_is_controlled(self):
  original=self.S.P.contexto
  def cp(p,raw):
   d=original(p,raw);self.S.E.crudo=copy.deepcopy(raw);return d
  self.S.P.contexto=cp;self.denied()
 def test_json_duplicate_float_overflow_reject_pinned_fixture(self):
  for raw in [b'{"version":"398.1","version":"398.1"}',b'{"x":1e999}']:
   self.path.write_bytes(raw);self.sha=hashlib.sha256(raw).hexdigest();m=json.loads((self.folder/'manifest.json').read_text());m['candidato_sha256']=self.sha;mr=json.dumps(m).encode();(self.folder/'manifest.json').write_bytes(mr);self.msha=hashlib.sha256(mr).hexdigest();self.denied(code=503)
 def test_snapshot_dates_not_now_or_work_execution(self):
  d=self.call();self.assertEqual(d['generado'],'2026-10-04T01:00:00Z');self.assertEqual(d['corte_preparacion_utc'],'2026-10-04T01:00:00Z');self.assertEqual(d['filas'][0]['estado_leido_utc'],'2026-10-03T10:00:00Z');self.assertIsNone(d['cumplimiento'])
 def test_hooks_queries_exact_and_no_write(self):
  class H:
   def _api_get(self,*args):return 418,{}
   def responder(self,c,d):return c,d
  B.enganchar(H,self.S);h=H();self.assertEqual(h._api_get('/else',{}, {},{})[0],418)
  for q in [{'yo':['ops']},{'cliente_id':['c1','c2']},{'grupo':['bad']},{'priority':['urgent']}]:self.assertEqual(h._api_get(B.RUTA,q,{'id':'ops'},{'id':'ops'})[0],400)
  self.assertEqual(h._api_get(B.RUTA,{}, {'id':'ops'},{'id':'ops'})[1]['estado'],'sin_dato')
if __name__=='__main__':unittest.main()
