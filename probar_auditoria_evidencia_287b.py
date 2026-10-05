"""Revisión independiente287: fixtures privadas temporales; sin servidor/DB/proveedor."""
import copy,os,json,hashlib,unittest,ast
from types import SimpleNamespace as NS
from unittest.mock import patch
from pathlib import Path
import evidencia_produccion_287 as M
import probar_evidencia_287 as fixtures

class Auditoria(unittest.TestCase):
 setUp=fixtures.Pruebas.setUp
 tearDown=fixtures.Pruebas.tearDown
 write=fixtures.Pruebas.write
 runit=fixtures.Pruebas.runit
 def permiso_por_rol(self):
  self.catalogo['personas'][0]['puestos']=['operaciones']
  self.S.ve_alguno=lambda p,mods:'operaciones' in p.get('puestos',[])
  self.S.P.ver=lambda p,q,cp:{'ok':('operaciones' in p.get('puestos',[])) if p['id']=='ops' else True}
 def durante(self,mutation,real=None,vista=None):
  leer=M.leer_candidato287
  def lectura(path):
   resultado=leer(path);mutation();return resultado
  with patch.object(M,'leer_candidato287',side_effect=lectura):return M.enriquecer287(self.dto,self.S,real or self.actor,vista or self.actor)
 def test_modulo_revocado_in_place_durante_lectura(self):
  self.permiso_por_rol()
  d=self.durante(lambda:self.catalogo['personas'][0].update(puestos=[]))
  self.assertEqual(d,self.dto)
 def test_persona_reemplazada_activa_sin_grants_durante_lectura(self):
  self.permiso_por_rol()
  d=self.durante(lambda:self.catalogo['personas'].__setitem__(0,{'id':'ops','estado':'activo','puestos':[]}))
  self.assertEqual(d,self.dto)
 def test_vercomo_revocado_durante_lectura(self):
  self.catalogo['personas'].append({'id':'vista','estado':'activo'})
  permiso={'vista':True};self.S.P.ver=lambda p,q,cp:{'ok':permiso['vista'] if q['tipo']=='ver_como' else True}
  self.assertIn('_evidencia_equipo_275',M.enriquecer287(self.dto,self.S,self.actor,{'id':'vista'})['personas'][0])
  d=self.durante(lambda:permiso.update(vista=False),vista={'id':'vista'})
  self.assertEqual(d,self.dto)
 def test_cliente_revocado_solo_vista_durante_lectura(self):
  self.catalogo['personas'].append({'id':'vista','estado':'activo'})
  permiso={'a':True};self.S.P.ver=lambda p,q,cp:{'ok':False if p['id']=='vista' and q.get('cliente_id')=='a' and not permiso['a'] else True}
  d=self.durante(lambda:permiso.update(a=False),vista={'id':'vista'})
  self.assertEqual(d,self.dto)
 def test_horas_revocadas_reemplazo_persona_durante_lectura(self):
  self.permiso_por_rol();self.S.ve_alguno=lambda p,mods:True
  d=self.durante(lambda:self.catalogo['personas'].__setitem__(0,{'id':'ops','estado':'activo','puestos':[]}))
  self.assertEqual(d,self.dto)
 def test_duplicado_actor_durante_lectura(self):
  d=self.durante(lambda:self.catalogo['personas'].append(copy.deepcopy(self.catalogo['personas'][0])))
  self.assertEqual(d,self.dto)
 def test_cliente_duplicado_durante_lectura(self):
  d=self.durante(lambda:self.catalogo['clientes'].append({'id':'a'}))
  self.assertEqual(d,self.dto)
 def test_link_en_directorio_privado_rechazado(self):
  sub=self.dir/'real';sub.mkdir();target=sub/'c.json';target.write_bytes(self.path.read_bytes());target.chmod(0o600)
  link=self.dir/'indirecto';link.symlink_to(sub,target_is_directory=True)
  with patch.dict(os.environ,{M.ENV:str(link/'c.json')}):self.assertEqual(self.runit(),self.dto)
 def test_sin_modulo_no_lee_privado(self):
  self.S.ve_alguno=lambda p,m:False
  with patch.object(M,'leer_candidato287',side_effect=AssertionError('lectura privada prohibida')):self.assertEqual(self.runit(),self.dto)
 def test_cache_get_produccion_excluido_con_candidato(self):
  tree=ast.parse(Path(M.__file__).with_name('servir.py').read_text())
  nodes=[n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='guardable' for t in n.targets)]
  self.assertEqual(len(nodes),1);expression=compile(ast.Expression(nodes[0].value),'<cache_actual>','eval')
  ns={'marca':('fixture',),'rel':'produccion/produccion','conf':{},'solo_lectura':False,'os':os}
  self.assertFalse(eval(expression,ns))
  with patch.dict(os.environ,{M.ENV:''}):self.assertTrue(eval(expression,ns))
 def test_hook_indice_actual_usa_dto_scoped(self):
  tree=ast.parse(Path(M.__file__).with_name('servir.py').read_text())
  function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='modulo_recortado')
  self.S.E.bloqueados=[]
  self.S.ACT.quitar_bajas=lambda d,rel:d
  ns={'puerta_modulo':lambda *a,**k:{'fichero':self.path,'conf':{},'nivel':'todo'},'E':self.S.E,'leer_json_bueno':lambda p:(copy.deepcopy(self.dto),None),'ACT':self.S.ACT,'recortar_modulo':lambda *a:copy.deepcopy(self.dto),'EVIDENCIA_PRODUCCION_287':M,'sys':NS(modules={'audit':self.S}),'__name__':'audit'}
  exec(compile(ast.Module(body=[function],type_ignores=[]),'<hook_actual>','exec'),ns)
  out=ns['modulo_recortado'](self.actor,self.actor,{},'produccion/produccion')
  self.assertEqual(out['personas'][0]['_evidencia_equipo_275']['creadas_semana'],2)
  self.assertEqual([p['cliente_id'] for p in out['proyectos']],['a'])
  # Último dato bueno no recibe un sello nuevo.
  ns['leer_json_bueno']=lambda p:(copy.deepcopy(self.dto),'antiguo')
  self.assertEqual(ns['modulo_recortado'](self.actor,self.actor,{},'produccion/produccion'),self.dto)
 def test_ambiguedad_proyectos_no_suma_por_creador(self):
  self.dto['proyectos'].append(copy.deepcopy(self.dto['proyectos'][0]))
  d=self.runit();self.assertTrue(all('_evidencia_produccion_275' not in p for p in d['proyectos']));self.assertIsNone(d['personas'][0]['_evidencia_equipo_275']['creadas_semana'])

if __name__=='__main__':unittest.main()
