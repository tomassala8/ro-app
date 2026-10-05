import copy,datetime as dt,json,tempfile,unittest,os,hashlib
from pathlib import Path
from unittest.mock import patch
from fuentes_produccion.ejemplos_creador_438 import construir
import ejemplos_creador_api_438 as A
from probar_agrupaciones_tarea_376 import server
NOW=dt.datetime(2026,10,4,tzinfo=dt.timezone.utc)
CAT={'listas':{'l1':{'ok':True,'estados':[{'status':'planning mensual','type':'custom'}]}}}
def task():return {'id':'t1','lista_id':'l1','carpeta_id':'f1','estado':'planning mensual','tipo_estado':'custom','estado_fuente':'clickup','estado_leido_utc':'2026-10-03T13:00:00Z','creada':'1790938800000','creador':2,'asignados':[{'id':1}],'nombre':'Ejemplo operativo'}
def build(tasks=None,ident=None,active=None):return construir({'tareas':tasks or [task()]},CAT,{'f1':('c1','privado')},{'c1'},ident or {'1':'b','2':'a'},active or {'a','b'},NOW)
class Tests(unittest.TestCase):
 def test_creator_not_assignee(self):
  raw=[task()];before=copy.deepcopy(raw);d=build(raw);self.assertEqual(d['filas'][0]['persona_id'],'a');self.assertEqual(raw,before);self.assertNotIn('asignados',json.dumps(d));self.assertTrue(d['creacion_no_es_planificacion']);self.assertIsNone(d['cumplimiento'])
 def test_identity_unknown_bool_dup_no_grants(self):
  for uid in [None,True,'unknown']:
   t=task();t['creador']=uid;self.assertEqual(build([t])['filas'],[])
  t=task();self.assertEqual(build([t,{**t,'carpeta_id':'foreign'}])['filas'],[]);self.assertEqual(build(active={'b'})['filas'],[])
 def test_date_bounds_and_read_stamp(self):
  for ms in [None,True,'0','x','99999999999999999999999','1791208800000']:
   t=task();t['creada']=ms;self.assertEqual(build([t])['filas'],[])
  t=task();t['estado_leido_utc']='2026-10-03T13:00:00+14:01';self.assertEqual(build([t])['filas'],[])
 def test_title_redaction(self):
  for label in ['password=fixture_test_secret','clave: fixture_test_secret','Bearer eyJhbGciOiJIUzI1NiJ9.abcdefghi.xyzabc','https://usuario:clave@example.org/?token=foo','Cuota: 1470 €']:
   t=task();t['nombre']=label;s=json.dumps(build([t]));self.assertNotIn('fixture_test_secret',s);self.assertNotIn('1470',s);self.assertNotIn('https://',s)
 def test_angles_normalized_without_weakening_secret_redaction(self):
  t=task();t['nombre']='Comparar indicador < umbral';r=build([t])['filas'][0];self.assertEqual(r['titulo_saneado'],'Comparar indicador ‹ umbral');self.assertNotIn('<',r['titulo_saneado']);self.assertEqual(len(A.proyectar(build([t]),['a'],['c1'],NOW,CAT,{'2':'a'})),1)
 def test_scope_filters_both_dimensions(self):
  d=build();self.assertEqual(len(A.proyectar(d,['a'],['c1'],NOW,CAT,{'2':'a'})),1);self.assertEqual(A.proyectar(d,['b'],['c1'],NOW,CAT,{'2':'a'}),[]);self.assertEqual(A.proyectar(d,['a'],[],NOW,CAT,{'2':'a'}),[])
 def test_global_duplicate_before_scope_and_metadata(self):
  for fn in [lambda d:d['filas'].append({**d['filas'][0],'cliente_id':'foreign'}),lambda d:d['filas'][0].update(rawUID=2),lambda d:d['filas'][0].update(titulo_saneado='password=fixture_test_secret'),lambda d:d['filas'][0].update(creada_utc='2026-02-30T00:00:00Z'),lambda d:d.update(corte_preparacion_utc='2027-01-01T00:00:00Z')]:
   d=build();fn(d)
   with self.assertRaises(ValueError):A.proyectar(d,['a'],['c1'],NOW,CAT,{'2':'a'})
 def test_creator_remap_never_reattributed(self):
  d=build();self.assertEqual(A.proyectar(d,['a','b'],['c1'],NOW,CAT,{'2':'b'}),[]);self.assertEqual(A.proyectar(d,['a'],['c1'],NOW,CAT,{}),[])
  row=A.proyectar(d,['a'],['c1'],NOW,CAT,{'2':'a'})[0];self.assertNotIn('creador_usuario_id',row);self.assertEqual(row['persona_id'],'a')
 def test_current_scope_real_view_grants(self):
  S=server();self.assertEqual(A.G._ambito(S,'a','b')[0],['b']);S.ACT.es_activo_id=lambda c:False;self.assertEqual(A.G._ambito(S,'a','b')[1],[])
  S=server();S.E.crudo['personas'].append(copy.deepcopy(S.E.crudo['personas'][0]))
  with self.assertRaises(A.G.ErrorAgrupaciones):A.G._ambito(S,'a','b')
 def test_malformed_roles_never_grant_new_scope(self):
  S=server();S.E.crudo['personas'][0]['puestos']=['operaciones','operaciones']
  with self.assertRaises(A.G.ErrorAgrupaciones):A._ambito(S,'a','a')
  S=server();S.E.crudo['personas'][1]['puestos']=[];self.assertNotIn('b',A._ambito(S,'a','a')[0])
 def test_revocation_during_last_read(self):
  for mutate in [lambda S:S.E.crudo['personas'][0].update(estado='baja'),lambda S:setattr(S,'ve_alguno',lambda *a:False),lambda S:setattr(S.ACT,'es_activo_id',lambda c:False),lambda S:setattr(S.P,'ver',lambda *a:{'ok':False})]:
   S=server()
   with patch.object(A,'cargar',return_value=(build(),{'base395':{'fuentes_sha256':{'miembros':'a'*64}},'codigo438_sha256':{p.name:'a'*64 for p in A.CODES}},CAT)),patch.object(A.D,'verificar_fuentes',side_effect=lambda m:mutate(S)),patch.object(A,'SHA','a'*64),patch.object(A.D,'_leer',return_value={'miembros':[]}):
    with self.assertRaises(A.G.ErrorAgrupaciones):A.listar(S,'a','b',path='/fixture/candidato.json',ahora=NOW)
 def test_pins_disabled_and_private_symlink_no_content(self):
  with patch.object(A,'SHA',None),patch.object(A,'MANIFEST_SHA',None):
   with self.assertRaises(ValueError):A.cargar('/fixture/candidato.json')
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'private';p.mkdir(mode=0o700);f=p/'x';f.write_text('{"safe":true}');f.chmod(0o600);link=p/'candidato.json';link.symlink_to(f)
   with self.assertRaises(OSError):A.D._leer(link,hashlib.sha256(f.read_bytes()).hexdigest(),1000,True)
 def test_hook_query_and_error_generic(self):
  class H:
   def _api_get(self,*a):return 'original'
   def responder(self,c,b):return c,b
  A.enganchar(H,server());h=H();self.assertEqual(h._api_get('/other',{}, {},{}),'original');self.assertEqual(h._api_get(A.RUTA,{'yo':['a']},{'id':'a'},{'id':'a'})[0],400)
  with patch.dict(os.environ,{},clear=True):self.assertEqual(h._api_get(A.RUTA,{}, {'id':'a'},{'id':'a'})[0],503)
if __name__=='__main__':unittest.main()
