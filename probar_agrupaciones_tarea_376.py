import copy,datetime as dt,json,os,socket,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import agrupaciones_tarea_api_376 as M
from fuentes_horas.deposito_agrupaciones_376 import construir,uid
from probar_historial_diario_api_362 import server as base_server
NOW=dt.datetime(2026,10,4,tzinfo=dt.timezone.utc)
DEP=Path(__file__).resolve().parent.parent/'RECUPERACION_CODEX_2026-10-03/staging_agrupaciones_376_v2'
def fixture():
 return {'version':'376.1','sin_promover':True,'sin_agregado_global':True,'dedup_global_antes_scope':True,'cobertura':'parcial','clasificacion':'orientativa_por_titulo','fuentes_sha256':{'tareas':'a'*64},'leido':'2026-10-03T07:00:00Z','corte':'2026-10-03T07:00:00Z','identidades':{'1':'b','2':'a'},'tareas':[{'id':f't{i}','lista_id':'l1','carpeta_id':'f1','cliente_id':'c1','nombre':'optimizar seo'} for i in range(6)],'entradas':[{'id':f'e{i}','usuario_id':'1','task_id':f't{i}','inicio':'2026-09-10T10:00:00Z','horas':i} for i in range(6)]}
def evidence():return {'identidades':{'1':'b','2':'a'},'carpetas':{'f1':('c1','Fixture')},'tareas_sha256':'a'*64,'firma':'actual'}
def server():
 S=base_server();S.E.crudo.update(clientes=[{'id':'c1','nombre':'Fixture','activo_confirmado':True}],asignaciones=[]);old=S.P.ver
 S.P.ver=lambda p,b,cp: {'ok':True} if b['tipo']=='cliente_detalle' else old(p,b,cp)
 S.ACT=SimpleNamespace(es_activo_id=lambda c:c=='c1');return S
class Pruebas(unittest.TestCase):
 def project(self,d=None,ps=None,cs=None,ev=None):return M.proyectar(d or fixture(),['b'] if ps is None else ps,['c1'] if cs is None else cs,ev or evidence(),NOW)
 def test_five_metrics_scope(self):
  r=self.project()['filas'][0];self.assertEqual((r['casos'],r['mediana_h'],r['max_h'],r['total_h']),(6,2.5,5,15));self.assertNotIn('cliente_id',json.dumps(r));self.assertEqual(self.project(ps=['a'])['filas'],[]);self.assertEqual(self.project(cs=[])['filas'],[])
 def test_folder_identity_source(self):
  e=evidence();e['carpetas']['f1']=('other','Other');self.assertEqual(self.project(ev=e)['filas'],[])
  e=evidence();e['identidades']['1']='a';self.assertEqual(self.project(ev=e)['filas'],[])
  e=evidence();e['tareas_sha256']='b'*64
  with self.assertRaises(ValueError):self.project(ev=e)
 def test_multi_uid_no_case_merge(self):
  d=fixture();d['identidades']['3']='b';e=evidence();e['identidades']['3']='b';d['entradas'].append({**d['entradas'][0],'id':'new','usuario_id':'3','horas':9})
  r=self.project(d,ev=e)['filas'][0];self.assertEqual((r['casos'],r['max_h'],r['total_h']),(7,9,24))
 def test_sum_case_max(self):
  d=fixture();d['entradas'].append({**d['entradas'][-1],'id':'extra','horas':8});self.assertEqual(self.project(d)['filas'][0]['max_h'],13)
 def test_unknown_zero_minimum(self):
  d=fixture();d['entradas']=d['entradas'][:4];self.assertEqual(self.project(d)['filas'],[])
  d=fixture()
  for e in d['entradas']:e['horas']=0
  self.assertEqual(self.project(d)['filas'][0]['total_h'],0)
 def test_malformed(self):
  for change in (lambda d:d['tareas'].append(copy.deepcopy(d['tareas'][0])),lambda d:d['entradas'].append(copy.deepcopy(d['entradas'][0])),lambda d:d['entradas'][0].update(usuario_id=True),lambda d:d['entradas'][0].update(horas=float('inf')),lambda d:d['tareas'][0].update(nombre='password=fixture'),lambda d:d.update(corte='2026-10-05T00:00:00Z'),lambda d:d['tareas'][0].update(lista_id=[])):
   d=fixture();change(d)
   with self.assertRaises((ValueError,TypeError)):self.project(d)
 def test_overflow(self):
  d=fixture()
  for e in d['entradas']:e['horas']=1e308
  self.assertEqual(self.project(d)['filas'],[])
 def test_levels_and_viewas(self):
  S=server();self.assertEqual(M._ambito(S,'a','b')[0],['b']);S.ve_alguno=lambda p,m:True
  with self.assertRaises(M.ErrorAgrupaciones):M._ambito(S,'a','a')
  S=server();S.P.ver=lambda *a:{'ok':False}
  with self.assertRaises(M.ErrorAgrupaciones):M._ambito(S,'a','b')
 def test_real_permissions(self):
  import permisos as P
  S=server();S.P=P
  with patch.dict(os.environ,{'RO_RELOJ':'2026-10-04T00:00'}):
   self.assertEqual(M._ambito(S,'a','a')[0],['a','b']);self.assertEqual(M._ambito(S,'b','b')[0],['b'])
   with P.mirando_como(S.E.crudo['personas'][0],S.E.crudo):self.assertEqual(M._ambito(S,'a','b')[0],['b'])
 def test_act_duplicate(self):
  S=server();self.assertEqual(M._ambito(S,'a','a')[1],['c1']);S.E.crudo['clientes'].append(copy.deepcopy(S.E.crudo['clientes'][0]));self.assertEqual(M._ambito(S,'a','a')[1],[])
  S=server();S.ACT.es_activo_id=lambda c:False;self.assertEqual(M._ambito(S,'a','a')[1],[])
 def test_missing_config_unknown(self):
  with patch.dict(os.environ,{},clear=True):d=M.listar(server(),'a','a',ahora=NOW)
  self.assertEqual((d['estado'],d['filas'],d['ventana']),('sin_dato',[],None))
 def test_revoke_while_read(self):
  for change in (lambda S:S.E.crudo['personas'][0].update(estado='baja'),lambda S:S.E.crudo['asignaciones'].append({'fixture':'change'}),lambda S:setattr(S.ACT,'es_activo_id',lambda c:False),lambda S:setattr(S,'ve_alguno',lambda *a:None)):
   S=server()
   def load(p):change(S);return fixture(),{}
   with patch.object(M,'cargar',load),patch.object(M,'evidencia_actual',lambda S:evidence()):
    with self.assertRaises(M.ErrorAgrupaciones) as c:M.listar(S,'a','a',path='/fixture',ahora=NOW)
   self.assertEqual(c.exception.codigo,403)
 def test_evidence_change(self):
  with patch.object(M,'cargar',lambda p:(fixture(),{})),patch.object(M,'evidencia_actual',side_effect=[evidence(),{**evidence(),'firma':'changed'}]):
   with self.assertRaises(M.ErrorAgrupaciones) as c:M.listar(server(),'a','a',path='/fixture',ahora=NOW)
  self.assertEqual(c.exception.codigo,403)
 def test_revocation_during_final_evidence(self):
  for change in (lambda S:S.E.crudo['personas'][0].update(estado='baja'),lambda S:setattr(S.ACT,'es_activo_id',lambda c:False),lambda S:setattr(S,'ve_alguno',lambda *a:None)):
   S=server();calls=[0]
   def ev(_):
    calls[0]+=1
    if calls[0]==2:change(S)
    return evidence()
   with patch.object(M,'cargar',lambda p:(fixture(),{})),patch.object(M,'evidencia_actual',ev):
    with self.assertRaises(M.ErrorAgrupaciones) as c:M.listar(S,'a','a',path='/fixture',ahora=NOW)
   self.assertEqual(c.exception.codigo,403)
 def test_pins_changed_during_final_evidence(self):
  calls=[0]
  def ev(_):
   calls[0]+=1
   if calls[0]==2:M.MANIFEST_SHA='f'*64
   return evidence()
  with patch.object(M,'MANIFEST_SHA',M.MANIFEST_SHA),patch.object(M,'cargar',lambda p:(fixture(),{})),patch.object(M,'evidencia_actual',ev):
   with self.assertRaises(M.ErrorAgrupaciones) as c:M.listar(server(),'a','a',path='/fixture',ahora=NOW)
  self.assertEqual(c.exception.codigo,403)
 def test_private_pin(self):
  with patch.object(socket,'socket',side_effect=AssertionError('No red')):d,m=M.cargar(DEP/'candidato.json')
  self.assertEqual(m['output_sha256'],M.SHA);text=json.dumps(d);self.assertTrue('@' not in text);self.assertTrue(all('descripcion' not in row for row in d['tareas']+d['entradas']))
 def test_fs_tamper(self):
  for mode in ('file','dir','link','content'):
   with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'private';p.mkdir(mode=0o700)
    for n in ('candidato.json','manifest.json'):(p/n).write_bytes((DEP/n).read_bytes());(p/n).chmod(0o600)
    if mode=='file':(p/'candidato.json').chmod(0o644)
    if mode=='dir':p.chmod(0o755)
    if mode=='link':(p/'candidato.json').unlink();(p/'candidato.json').symlink_to(DEP/'candidato.json')
    if mode=='content':(p/'candidato.json').write_text('{}')
    with self.assertRaises((ValueError,OSError)):M.cargar(p/'candidato.json')
 def test_producer_global_collision_privacy(self):
  hs={'meta':{'generado':'2026-10-03T07:00:00Z'},'entradas':fixture()['entradas']};ts={'tareas':[{'id':t['id'],'lista_id':'l1','carpeta_id':'f1','nombre':'Optimizar SEO Fixture septiembre'} for t in fixture()['tareas']]}
  kw=({'f1':('c1','Fixture')},{'1':'b'},['Fixture'],NOW)
  d=construir(hs,ts,*kw);self.assertEqual(len(d['entradas']),6);self.assertEqual(d['tareas'][0]['nombre'],'optimizar seo')
  hs['entradas'].append({**hs['entradas'][0],'usuario_id':'999','task_id':'foreign'});d=construir(hs,ts,*kw);self.assertEqual(len(d['entradas']),5);self.assertEqual(d['diagnostico']['entrada_colision_o_invalida'],1)
  ts['tareas'][0]['nombre']='password=fixture-secret';self.assertEqual(len(construir(hs,ts,*kw)['tareas']),5)
 def test_uid_future(self):
  self.assertEqual(uid(123),'123')
  for v in (True,[],{},0,-1,'01','other'):self.assertIsNone(uid(v))
  hs={'meta':{'generado':'2026-10-03T07:00:00Z'},'entradas':[{**fixture()['entradas'][0],'inicio':'2026-10-03T08:00:00Z'}]};self.assertEqual(construir(hs,{'tareas':[]},{},{},[],NOW)['entradas'],[])
 def test_hook(self):
  class H:
   def _api_get(self,*a):return 'other'
   def responder(self,c,d):return c,d
  M.enganchar(H,server());h=H();self.assertEqual(h._api_get('/other',{}, {},{}),'other');self.assertEqual(h._api_get(M.RUTA,{'x':['1']},{'id':'a'},{'id':'a'})[0],400)
if __name__=='__main__':unittest.main()
