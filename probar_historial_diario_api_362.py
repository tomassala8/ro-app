import copy,datetime as dt,hashlib,json,os,socket,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import historial_diario_api_362 as M
NOW=dt.datetime(2026,10,3,19,tzinfo=dt.timezone.utc)
DEP=Path(__file__).parent.parent/'RECUPERACION_CODEX_2026-10-03/staging_historial_diario_359_v2'
def fixture():
 cut=dt.date(2026,10,3);days=[{'fecha':(cut-dt.timedelta(days=90-i)).isoformat(),'horas':None,'entradas':None,'estado':'sin_dato'} for i in range(90)]
 days[0]={'fecha':days[0]['fecha'],'horas':0,'entradas':1,'estado':'observado'}
 serie={'version':'359.1','fuente':'ClickUp entradas','fecha_fuente_utc':'2026-10-03T00:56:00+00:00','cobertura':'parcial','zona':'Europe/Madrid','zona_confirmada':True,'desde':'2026-07-05','hasta':'2026-10-02','corte_fecha':'2026-10-03','criterio_corte':'anterior_fecha_referencia','atribucion':'inicio','duracion_cerrada_confirmada':False,'sin_registros_no_equivale_a_cero':True,'dias':days}
 return {'version':'359.1','hoy':'2026-10-03','personas':[{'persona_id':p,'historial_diario_359':copy.deepcopy(serie)} for p in ('a','b')],'cobertura':'parcial','unidad':'duracion_personal_observada_atribuida_al_inicio','clientes_en_salida':False,'sin_promover':True}
def server():
 ps=[{'id':p,'estado':'activo','activo':True,'puestos':['operaciones'] if p=='a' else ['seo']} for p in ('a','b')]
 E=SimpleNamespace(crudo={'personas':ps},nucleo_bloqueado=False,modulos={'horas':{'operaciones':'todo','seo':'suyo'}})
 P=SimpleNamespace(REGLAS={'horas_persona':'fixture'},hoy_iso=lambda:'2026-10-03',contexto=lambda p,c:{'propio':p['id']})
 P.ver=lambda p,b,cp:{'ok':b['tipo']=='ver_como' or p['id']=='a' or b.get('persona_id')==p['id']}
 S=SimpleNamespace(E=E,P=P,ve_alguno=lambda p,ms:'todo' if p['id']=='a' else 'suyo')
 return S
class Pruebas(unittest.TestCase):
 def test_projection_scope_unknown_and_zero(self):
  d=M.proyectar(fixture(),['b'],NOW,'2026-10-03');self.assertEqual([r['persona_id'] for r in d],['b']);self.assertEqual(d[0]['historial_diario']['dias'][0]['horas'],0);self.assertIsNone(d[0]['historial_diario']['dias'][1]['horas'])
 def test_extra_private_fields_not_exported(self):
  f=fixture();f['secreto']='fixture';f['personas'][0]['nombre']='privado';f['personas'][0]['historial_diario_359']['salario']=999
  d=M.proyectar(f,['a'],NOW,'2026-10-03');s=json.dumps(d);self.assertNotIn('privado',s);self.assertNotIn('salario',s);self.assertNotIn('secreto',s)
 def test_invalid_series(self):
  mutations=[lambda f:f['personas'].append(copy.deepcopy(f['personas'][0])),lambda f:f['personas'][0]['historial_diario_359']['dias'].pop(),lambda f:f['personas'][0]['historial_diario_359']['dias'][1].update(horas=0),lambda f:f['personas'][0]['historial_diario_359'].update(fecha_fuente_utc='2026-10-04T00:00:00Z'),lambda f:f['personas'][0]['historial_diario_359'].update(fecha_fuente_utc='2026-10-03T00:00:00'),lambda f:f['personas'][0]['historial_diario_359']['dias'][0].update(horas=float('nan')),lambda f:f['personas'][0]['historial_diario_359']['dias'][0].update(entradas=True),lambda f:f.update(hoy='2026-10-04'),lambda f:f['personas'][0]['historial_diario_359']['dias'][2].update(fecha='2026-07-05')]
  for fn in mutations:
   with self.subTest(fn=fn):
    f=fixture();fn(f)
    with self.assertRaises(ValueError):M.proyectar(f,['a'],NOW,'2026-10-03')
 def test_module_string_not_bool(self):
  S=server();self.assertEqual(M._ambito(S,'a','b')[0],['b']);S.ve_alguno=lambda p,m:True
  with self.assertRaises(M.ErrorHistorial):M._ambito(S,'a','a')
 def test_denied_or_duplicate_actors(self):
  for change in (lambda S:S.E.crudo['personas'].append(copy.deepcopy(S.E.crudo['personas'][0])),lambda S:S.E.crudo['personas'][0].update(activo=False),lambda S:S.E.crudo['personas'][0].update(estado='baja')):
   S=server();change(S)
   with self.assertRaises(M.ErrorHistorial):M._ambito(S,'a','a')
 def test_intersection_and_vercomo(self):
  S=server();self.assertEqual(M._ambito(S,'a','b')[0],['b']);S.P.ver=lambda p,b,cp:{'ok':False}
  with self.assertRaises(M.ErrorHistorial):M._ambito(S,'a','b')
 def test_real_rules_self_ops_chief(self):
  import permisos as P
  S=server();S.P=P;S.E.crudo.update(asignaciones=[],clientes=[])
  S.E.crudo['personas'][1]['jefe']='a'
  with patch.dict(os.environ,{'RO_RELOJ':'2026-10-03T20:00'}):
   self.assertEqual(M._ambito(S,'b','b')[0],['b'])
   self.assertEqual(M._ambito(S,'a','a')[0],['a','b'])
   with P.mirando_como(S.E.crudo['personas'][0],S.E.crudo):self.assertEqual(M._ambito(S,'a','b')[0],['b'])
   S.E.crudo['personas'][0]['puestos']=['seo'];S.E.crudo['personas'][1]['jefe']='a'
   self.assertEqual(M._ambito(S,'a','a')[0],['a','b'])
 def test_missing_config_unknown(self):
  with patch.dict(os.environ,{},clear=True):d=M.listar(server(),'a','a',ahora=NOW)
  self.assertEqual(d['estado'],'sin_dato');self.assertEqual(d['personas'],[]);self.assertIsNone(d['cumplimiento'])
 def test_revocation_during_read(self):
  for mutate in (lambda S:S.E.crudo['personas'][1].update(estado='baja'),lambda S:setattr(S,'ve_alguno',lambda p,m:None),lambda S:setattr(S.P,'ver',lambda p,b,cp:{'ok':False}),lambda S:S.P.REGLAS.update(nueva='revocacion')):
   S=server()
   def loader(p):mutate(S);return fixture(),{'persona_filas':2,'desde':'2026-07-05','hasta':'2026-10-02'}
   with patch.object(M,'cargar',loader):
    with self.assertRaises(M.ErrorHistorial) as c:M.listar(S,'a','a',path='/fixture/candidato.json',ahora=NOW)
   self.assertEqual(c.exception.codigo,403)
 def test_sourceconfig_changes(self):
  def loader(p):os.environ[M.ENV]='/other/candidato.json';return fixture(),{'persona_filas':2,'desde':'2026-07-05','hasta':'2026-10-02'}
  with patch.dict(os.environ,{M.ENV:'/fixture/candidato.json'}),patch.object(M,'cargar',loader):
   with self.assertRaises(M.ErrorHistorial):M.listar(server(),'a','a',ahora=NOW)
 def test_actual_deposit_no_network(self):
  with patch.object(socket,'socket',side_effect=AssertionError('No red')):
   doc,manifest=M.cargar(DEP/'candidato.json');rows=M.proyectar(doc,[r['persona_id'] for r in doc['personas']],NOW,'2026-10-03')
  self.assertEqual(len(rows),27);self.assertEqual(len(rows[0]['historial_diario']['dias']),90);self.assertEqual(manifest['output_sha256'],M.SHA)
 def _deposit(self,p):
  os.chmod(p,0o700)
  for name in ('candidato.json','manifest.json'):
   target=p/name;target.write_bytes((DEP/name).read_bytes());os.chmod(target,0o600)
 def test_deposit_tamper_mode_links(self):
  for kind in ('content','file_mode','directory_mode','symlink','ancestor_link','hardlink'):
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as t:
    p=Path(t)/'private';p.mkdir();self._deposit(p);f=p/'candidato.json';path=f
    if kind=='content':f.write_bytes(b'{}')
    if kind=='file_mode':os.chmod(f,0o644)
    if kind=='directory_mode':os.chmod(p,0o755)
    if kind=='hardlink':os.link(f,Path(t)/'hard')
    if kind=='symlink':f.rename(p/'old');f.symlink_to(p/'old')
    if kind=='ancestor_link':(Path(t)/'alias').symlink_to(p,target_is_directory=True);path=Path(t)/'alias/candidato.json'
    with self.assertRaises((OSError,ValueError)):M.cargar(path)
 def test_import_no_io(self):
  code=compile(Path(M.__file__).read_text(),'<lector362>','exec')
  with patch('builtins.open',side_effect=AssertionError('IO import')),patch('os.open',side_effect=AssertionError('IO import')),patch.object(socket,'socket',side_effect=AssertionError('Red')):
   exec(code,{'__name__':'lector_fixture'})
 def test_sourcehash_changes_fail_closed(self):
  def loader(p):
   M.SHA='0'*64
   return fixture(),{'persona_filas':2,'desde':'2026-07-05','hasta':'2026-10-02'}
  with patch.object(M,'SHA',M.SHA),patch.object(M,'cargar',loader):
   with self.assertRaises(M.ErrorHistorial):M.listar(server(),'a','a',path='/fixture/candidato.json',ahora=NOW)
 def test_full_handler_no_parameters_no_post(self):
  class H:
   def _api_get(self,*a):return 'legacy'
   def responder(self,code,b):return code,b
  M.enganchar(H,server());h=H()
  self.assertEqual(h._api_get('/another',{},None,None),'legacy');self.assertEqual(h._api_get(M.RUTA,{'persona_id':['b']},{'id':'a'},{'id':'a'})[0],400)
  with patch.dict(os.environ,{},clear=True):self.assertEqual(h._api_get(M.RUTA,{}, {'id':'a'},{'id':'a'})[0],200)
if __name__=='__main__':unittest.main()
