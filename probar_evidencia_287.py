import copy,hashlib,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import evidencia_produccion_287 as M

class Pruebas(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name).resolve();self.path=self.dir/'c.json'
  self.c={'version':'275.1','corte':'2026-10-03T13:08:00Z','ayer':'2026-10-02','lunes':'2026-09-28','zona':'Europe/Madrid','cobertura':'parcial','proyectos':[{'cliente_id':c,'cierres_ayer':3,'cierres_ayer_observaciones':3,'creadas_semana':4,'creadas_semana_observaciones':4,'cobertura':'parcial','actor_cierre':None} for c in ['a','b']],'creadores':[{'cliente_id':c,'persona_id':'p','creadas_semana':n,'cobertura':'parcial'} for c,n in [('a',2),('b',99)]]}
  self.dto={'proyectos':[{'cliente_id':'a','cliente':'Fixture autorizada'}],'personas':[{'persona_id':'p'}]}
  self.catalogo={'clientes':[{'id':'a'},{'id':'b'}],'personas':[{'id':'ops','estado':'activo'},{'id':'p','estado':'activo'}]}
  self.denied=set();self.active={'a','b'}
  self.S=NS(E=NS(crudo=self.catalogo,nucleo_bloqueado=False),ACT=NS(es_activo_id=lambda cid:cid in self.active),P=NS(hoy_iso=lambda:'2026-10-03',contexto=lambda p,d:{},ver=lambda p,q,cp:{'ok':(q['tipo'],q.get('cliente_id',q.get('persona_id'))) not in self.denied}),ve_alguno=lambda p,mods:True)
  self.actor={'id':'ops'};self.write();self.env=patch.dict(os.environ,{M.ENV:str(self.path)});self.env.start();self.sha=patch.object(M,'SHA275',hashlib.sha256(self.path.read_bytes()).hexdigest());self.sha.start()
 def write(self):self.path.write_text(json.dumps(self.c));self.path.chmod(0o600)
 def tearDown(self):self.sha.stop();self.env.stop();self.tmp.cleanup()
 def runit(self):return M.enriquecer287(self.dto,self.S,self.actor,self.actor)
 def test_scope_no_sum_other_client(self):
  d=self.runit();self.assertEqual(d['personas'][0]['_evidencia_equipo_275']['creadas_semana'],2);self.assertEqual(len(d['proyectos']),1);self.assertEqual([p['cliente_id'] for p in d['proyectos']],['a']);self.assertEqual(d['proyectos'][0]['_evidencia_produccion_275']['actor_cierre'],None);self.assertNotIn('_evidencia_equipo_275',self.dto['personas'][0])
 def test_client_permission_denied(self):
  self.denied.add(('cliente_detalle','a'));d=self.runit();self.assertNotIn('_evidencia_produccion_275',d['proyectos'][0]);self.assertEqual(d['personas'][0]['_evidencia_equipo_275']['creadas_semana'],None)
 def test_person_denied(self):
  self.denied.add(('horas_persona','p'));self.assertNotIn('_evidencia_equipo_275',self.runit()['personas'][0])
 def test_inactive_client(self):
  self.active.remove('a');self.assertNotIn('_evidencia_produccion_275',self.runit()['proyectos'][0])
 def test_duplicate_actor_no_file(self):
  self.catalogo['personas'].append(copy.deepcopy(self.catalogo['personas'][0]));
  with patch.object(M,'leer_candidato287',side_effect=AssertionError('No debe leer')):self.assertEqual(self.runit(),self.dto)
 def test_duplicate_client(self):
  self.catalogo['clientes'].append({'id':'a'});self.assertNotIn('_evidencia_produccion_275',self.runit()['proyectos'][0])
 def test_hash_change(self):
  self.path.write_text('{}');self.assertEqual(self.runit(),self.dto)
 def test_file_modes(self):
  self.path.chmod(0o644);self.assertEqual(self.runit(),self.dto)
 def test_link(self):
  link=self.dir/'link.json';link.symlink_to(self.path)
  with patch.dict(os.environ,{M.ENV:str(link)}):self.assertEqual(self.runit(),self.dto)
 def test_hardlink(self):
  os.link(self.path,self.dir/'hard.json');self.assertEqual(self.runit(),self.dto)
 def test_future(self):
  self.c['corte']='2099-10-03T13:08:00Z';self.write()
  with patch.object(M,'SHA275',hashlib.sha256(self.path.read_bytes()).hexdigest()):self.assertEqual(self.runit(),self.dto)
 def test_revoked_during_read(self):
  read=M.leer_candidato287
  def wrapped(path):
   d=read(path);self.active.remove('a');return d
  with patch.object(M,'leer_candidato287',side_effect=wrapped):self.assertEqual(self.runit(),self.dto)
 def test_strip_injected_fields_disabled(self):
  self.dto['personas'][0]['_evidencia_equipo_275']={'forged':99}
  with patch.dict(os.environ,{M.ENV:''}):self.assertNotIn('_evidencia_equipo_275',self.runit()['personas'][0])
 def test_viewas_checks_both(self):
  self.catalogo['personas'].append({'id':'vista','estado':'activo'});self.S.P.ver=lambda p,q,cp:{'ok':not(p['id']=='vista' and q['tipo']=='cliente_detalle')}
  d=M.enriquecer287(self.dto,self.S,self.actor,{'id':'vista'});self.assertNotIn('_evidencia_produccion_275',d['proyectos'][0]);self.assertEqual(d['personas'][0]['_evidencia_equipo_275']['creadas_semana'],None)

if __name__=='__main__':unittest.main()
