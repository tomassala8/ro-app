import copy,datetime as dt,hashlib,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from zoneinfo import ZoneInfo
import evidencia_produccion_287 as M
from fuentes_produccion.comparacion_semanal_296 import construir
CUT=dt.datetime(2026,10,3,15,8,tzinfo=ZoneInfo('Europe/Madrid'))
def fixture():
 def t(i,c,days):return {'id':str(i),'carpeta_id':c,'lista_id':'list','estado':'cerrada','tipo_estado':'closed','creador':3,'creada':str(int((CUT-dt.timedelta(days=days)).timestamp()*1000)),'cerrada':str(int(CUT.timestamp()*1000))}
 tasks=[t(1,'fa',1),t(2,'fa',8),t(3,'fb',1),t(4,'fb',1)]
 return construir({'meta':{'generado':'2026-10-03 15:08'},'tareas':tasks},{'listas':{'list':{'ok':True,'estados':[{'status':'cerrada','type':'closed'}]}}},{'fa':('a',None),'fb':('b',None)},{'a','b'},{'3':'p'},{'p'},CUT,CUT+dt.timedelta(hours=1))
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name).resolve()/'c.json';self.c=fixture();self.write();self.env=patch.dict(os.environ,{M.ENV296:str(self.path),M.ENV:''});self.env.start();self.sha=patch.object(M,'SHA296',hashlib.sha256(self.path.read_bytes()).hexdigest());self.sha.start()
  self.dto={'proyectos':[{'cliente_id':'a','cliente':'Autorizado'}],'personas':[{'persona_id':'p'}]};self.catalog={'personas':[{'id':'ops','estado':'activo','puestos':['operaciones']},{'id':'p','estado':'activo'}],'clientes':[{'id':'a'},{'id':'b'}]};self.activos={'a','b'};self.denied=set();self.S=NS(E=NS(crudo=self.catalog,nucleo_bloqueado=False),ACT=NS(es_activo_id=lambda cid:cid in self.activos),ve_alguno=lambda p,m:p.get('puestos')==['operaciones'],P=NS(hoy_iso=lambda:'2026-10-03',contexto=lambda p,d:{},ver=lambda p,q,c:{'ok':(p['id'],q['tipo'],q.get('cliente_id',q.get('persona_id')))not in self.denied}));self.actor={'id':'ops'}
 def write(self):self.path.write_text(json.dumps(self.c));self.path.chmod(0o600)
 def tearDown(self):self.sha.stop();self.env.stop();self.tmp.cleanup()
 def runit(self):return M.enriquecer287(self.dto,self.S,self.actor,self.actor)
 def test_scoped_project_and_creator_no_foreign_sum(self):
  o=self.runit();self.assertEqual(len(o['proyectos']),1);self.assertEqual(o['proyectos'][0][M.KEY296]['creadas']['actual']['valor'],1);p=o['personas'][0][M.KEY296];self.assertEqual(p['creadas']['actual']['valor'],1);self.assertEqual(p['creadas']['anterior']['valor'],1);self.assertEqual(p['cliente_ids_scope'],['a']);self.assertNotIn('finales',p);self.assertNotIn(M.KEY296,self.dto['proyectos'][0])
 def test_client_permission(self):
  self.denied.add(('ops','cliente_detalle','a'));o=self.runit();self.assertNotIn(M.KEY296,o['proyectos'][0]);self.assertIsNone(o['personas'][0][M.KEY296]['creadas']['actual']['valor'])
 def test_person_permission(self):
  self.denied.add(('ops','horas_persona','p'));self.assertNotIn(M.KEY296,self.runit()['personas'][0])
 def test_inactive_client(self):self.activos.remove('a');self.assertNotIn(M.KEY296,self.runit()['proyectos'][0])
 def test_inactive_duplicate_actor(self):
  for change in [lambda:self.catalog['personas'][0].update(estado='baja'),lambda:self.catalog['personas'].append(copy.deepcopy(self.catalog['personas'][0]))]:
   old=copy.deepcopy(self.catalog);change()
   with patch.object(M,'leer_candidato296',side_effect=AssertionError('No leer')):self.assertEqual(self.runit(),self.dto)
   self.catalog.clear();self.catalog.update(old)
 def test_duplicate_client_dto(self):self.dto['proyectos'].append(copy.deepcopy(self.dto['proyectos'][0]));self.assertTrue(all(M.KEY296 not in r for r in self.runit()['proyectos']))
 def test_inactive_person(self):self.catalog['personas'][1]['estado']='baja';self.assertNotIn(M.KEY296,self.runit()['personas'][0])
 def test_viewas_intersection(self):
  self.catalog['personas'].append({'id':'vista','estado':'activo','puestos':['operaciones']});self.denied.add(('vista','cliente_detalle','a'));o=M.enriquecer287(self.dto,self.S,self.actor,{'id':'vista'});self.assertNotIn(M.KEY296,o['proyectos'][0]);self.assertIsNone(o['personas'][0][M.KEY296]['creadas']['actual']['valor'])
 def test_viewas_denied_no_read(self):
  self.catalog['personas'].append({'id':'vista','estado':'activo','puestos':['operaciones']});self.denied.add(('ops','ver_como',None))
  with patch.object(M,'leer_candidato296',side_effect=AssertionError('No leer')):self.assertEqual(M.enriquecer287(self.dto,self.S,self.actor,{'id':'vista'}),self.dto)
 def test_revoked_during_read(self):
  reader=M.leer_candidato296
  for revoke in [lambda:self.activos.remove('a'),lambda:self.denied.add(('ops','horas_persona','p')),lambda:self.catalog['personas'][0].update(puestos=[]),lambda:self.catalog['personas'][1].update(estado='baja'),lambda:setattr(self.S.E,'crudo',copy.deepcopy(self.catalog))]:
   original=copy.deepcopy(self.catalog)
   def r(path):o=reader(path);revoke();return o
   with patch.object(M,'leer_candidato296',side_effect=r):self.assertEqual(self.runit(),self.dto)
   self.catalog.clear();self.catalog.update(original);self.S.E.crudo=self.catalog;self.activos={'a','b'};self.denied.clear()
 def test_hash_modes_links(self):
  self.path.chmod(0o644);self.assertEqual(self.runit(),self.dto);self.path.chmod(0o600)
  link=self.path.with_name('link.json');link.symlink_to(self.path)
  with patch.dict(os.environ,{M.ENV296:str(link)}):self.assertEqual(self.runit(),self.dto)
  os.link(self.path,self.path.with_name('hard.json'));self.assertEqual(self.runit(),self.dto)
 def test_hash_tamper(self):self.path.write_text('{}');self.assertEqual(self.runit(),self.dto)
 def test_forged_descriptor_stripped_disabled(self):
  self.dto['proyectos'][0][M.KEY296]={'forged':100}
  with patch.dict(os.environ,{M.ENV296:''}):self.assertNotIn(M.KEY296,self.runit()['proyectos'][0])
 def test_invalid_window_and_missing_or_boolean_count(self):
  for change in [lambda c:c['ventanas']['anterior'].update(hasta_inclusiva=True),lambda c:c['proyectos'][0]['creadas']['actual'].update(valor=True),lambda c:c['proyectos'][0]['finales']['actual'].update(campo='creator'),lambda c:c['proyectos'][0].update(actor_cierre='p')]:
   c=fixture();change(c)
   with self.assertRaises(ValueError):M.aplicar296(self.dto,c,{'a'},{'p'},M.SHA296,M.SHA296)
 def test_creator_exceeds_project_rejected(self):
  c=fixture();c['creadores'][0]['creadas']['actual'].update(valor=999,observaciones=999)
  with self.assertRaises(ValueError):M.aplicar296(self.dto,c,{'a'},{'p'},M.SHA296,M.SHA296)
 def test_future_source_date(self):
  self.S.P.hoy_iso=lambda:'2026-10-02';self.assertEqual(self.runit(),self.dto)
if __name__=='__main__':unittest.main()
