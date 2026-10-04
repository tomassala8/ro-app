"""219: metadatos sólo locales con fuente204/ACT/política por ambas identidades."""
import ast,copy,json,types,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
import tareas_metadata_219 as X
from identidades_clickup_204 import preparar_autorizacion
AHORA=datetime(2026,10,3,12,tzinfo=timezone.utc)
class Metadatos219(unittest.TestCase):
 def setUp(self):
  self.owner={'id':'owner','estado':'activo','correo':'owner@example.invalid','puestos':['seo']}
  self.ops={'id':'ops','estado':'activo','puestos':['operaciones']};self.foreign={'id':'foreign','estado':'activo','correo':'foreign@example.invalid','puestos':['seo']}
  self.personas=[self.owner,self.ops,self.foreign];self.row={'id':'task-fixture','cli':'client-fixture','lista_id':'list-fixture','persona_id':'owner','estado':'diario'}
  self.raw={'id':'task-fixture','lista_id':'list-fixture','carpeta_id':'folder-fixture','estado':'diario','asignados':[{'id':'u-owner'}],
   'estado_fuente':'clickup','estado_leido_utc':'2026-10-03T10:00:00Z','checklists':[{'id':'check-fixture','items':[{'id':'item-a','resolved':True},{'id':'item-b','resolved':False}],'items_cobertura':{'estado':'observado','leidos':2,'observados':2}}],
   'watchers':[],'metadata_cobertura':{'checklists':{'estado':'observado','leidos':1,'observados':1},'watchers':{'estado':'observado','leidos':0,'observados':0},'attachments':{'estado':'ausente'}}}
  self.raws=[self.raw];self.folder={'folder-fixture':['client-fixture']};self.allowed=True;self.module=True;self.active=True
  self.E=types.SimpleNamespace(nucleo_bloqueado=False,crudo={'personas':self.personas,'clientes':[{'id':'client-fixture'}]})
  self.M=types.SimpleNamespace(S=types.SimpleNamespace(E=self.E,ve_alguno=lambda*a:self.module),MODULO='mi-trabajo',
   P=types.SimpleNamespace(contexto=lambda*a:{},ver=lambda*a:{'ok':self.allowed}),doc=lambda:{'tareas':[self.row]},
   _fuente_autorizacion_tareas=lambda:preparar_autorizacion(self.personas,[{'id':'u-owner','email':'owner@example.invalid'}],self.raws,self.folder))
  from fuentes_verdad import clientes_activos as ACT
  p=patch.object(ACT,'es_activo_id',lambda cid:self.active);p.start();self.addCleanup(p.stop)
  self.h=types.SimpleNamespace(responder=lambda code,data:(code,data))
 def get(self,real=None,vista=None,q=None):return X.get_metadatos(self.h,q if q is not None else {'tarea':['task-fixture']},real or self.owner,vista or real or self.owner,self.M,ahora=AHORA)
 def test_dto_observado_sin_textos_links_ni_grants(self):
  self.raw.update(description='private',custom_fields=[{'id':'field','name':'Entregable Final','value':'https://host/?token=secret'}]);self.raw['checklists'][0]['name']='password secret'
  code,d=self.get();self.assertEqual(code,200);self.assertEqual(d['checklists']['total_confirmado'],2);self.assertEqual(d['checklists']['resueltos_observados'],1)
  self.assertIsNone(d['entregable']['url']);self.assertEqual(d['adjuntos']['cantidad'],None);self.assertEqual(d['seguidores']['cantidad'],0)
  text=json.dumps(d);self.assertNotIn('secret',text);self.assertNotIn('Entregable Final',text);self.assertNotIn('https',text)
 def test_ausencia_no_cero(self):
  self.raw.pop('checklists');d=self.get()[1]['checklists'];self.assertEqual(d['estado'],'sin_dato');self.assertIsNone(d['items_observados']);self.assertIsNone(d['total_confirmado'])
 def test_cero_observado_no_exito_entrega(self):
  self.raw['checklists']=[];self.raw['metadata_cobertura']['checklists'].update(leidos=0,observados=0);d=self.get()[1]['checklists'];self.assertEqual(d['total_confirmado'],0);self.assertIsNone(d['todos_resueltos'])
 def test_todos_resueltos_no_aceptacion(self):
  self.raw['checklists'][0]['items'][1]['resolved']=True;d=self.get()[1];self.assertTrue(d['checklists']['todos_resueltos']);self.assertEqual(d['entregable']['estado'],'sin_dato');self.assertNotIn('aceptado',json.dumps(d))
 def test_parcial_no_total_confirmado(self):
  self.raw['metadata_cobertura']['checklists']['estado']='parcial';d=self.get()[1]['checklists'];self.assertEqual(d['items_observados'],2);self.assertIsNone(d['total_confirmado'])
 def test_duplicate_items_no_first_wins(self):
  self.raw['checklists'][0]['items'].append({'id':'item-a','resolved':False});d=self.get()[1]['checklists'];self.assertEqual(d['items_observados'],1);self.assertIsNone(d['total_confirmado'])
 def test_cap1000_explicitamente_parcial(self):
  c=self.raw['checklists'][0];c['items']=[{'id':'item-'+str(i),'resolved':False} for i in range(1001)];c['items_cobertura'].update(leidos=1001,observados=1001);d=self.get()[1]['checklists'];self.assertEqual(d['items_observados'],1000);self.assertIsNone(d['total_confirmado'])
 def test_bool_counts_no_acredita_cero(self):
  self.raw['watchers']=[];self.raw['metadata_cobertura']['watchers'].update(leidos=False,observados=False);self.assertIsNone(self.get()[1]['seguidores']['cantidad'])
 def test_lectura_tarea_no_fecha_generado(self):
  self.raw['estado_leido_utc']='2027-10-03T10:00:00Z';self.assertIsNone(self.get()[1]['estado_leido_utc']);self.raw['estado_leido_utc']='2026-10-03';self.assertIsNone(self.get()[1]['estado_leido_utc'])
 def test_view_intersection_ambos_confirmados(self):
  self.assertEqual(self.get(self.ops,self.owner)[0],200);self.assertEqual(self.get(self.ops,self.foreign)[0],404);self.assertEqual(self.get(self.foreign,self.owner)[0],404)
 def test_watchers_no_autorizan(self):
  self.raw['watchers']=[{'id':'foreign'}];self.assertEqual(self.get(self.foreign)[0],404)
 def test_role_body_forged_no_grant(self):self.assertEqual(self.get(dict(self.foreign,puestos=['operaciones']))[0],404)
 def test_act_cartera_modulo_denegados(self):
  for key in ['active','allowed','module']:
   setattr(self,key,False);self.assertEqual(self.get()[0],404);setattr(self,key,True)
 def test_canonico_baja_o_duplicado_no_lectura(self):
  self.owner['estado']='baja';self.assertEqual(self.get()[0],404);self.owner['estado']='activo';self.personas.append(dict(self.owner));self.assertEqual(self.get()[0],404)
 def test_task_folder_list_state_coherence(self):
  for key in ['lista_id','estado','carpeta_id']:
   old=self.raw[key];self.raw[key]='other';self.assertEqual(self.get()[0],404);self.raw[key]=old
  self.raws.append(copy.deepcopy(self.raw));self.assertEqual(self.get()[0],404)
 def test_query_strict_and_scope_unknown(self):
  for q in [{},{'tarea':['task-fixture'],'yo':['ops']},{'tarea':['task-fixture','other']},{'tarea':'task-fixture'},{'tarea':['../secret']}]:self.assertEqual(self.get(q=q)[0],400)
  self.assertEqual(self.get(q={'tarea':['unknown-task']})[0],404)
 def test_hook_get_real_no_proveedor_ni_arranque(self):
  tree=ast.parse(Path(__file__).with_name('mi_trabajo.py').read_text());hook=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='enganchar')
  node=next(n for n in hook.body if isinstance(n,ast.FunctionDef) and n.name=='_api_get')
  ns={'__name__':'fixture_metadata_219','get_orig':lambda*a:(418,{})}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'GET219:AST','exec'),ns)
  with patch.dict('sys.modules',{'fixture_metadata_219':self.M}):
   code,d=ns['_api_get'](self.h,X.RUTA,{'tarea':['task-fixture']},self.owner,self.owner)
   self.assertEqual(code,200);self.assertEqual(d['checklists']['total_confirmado'],2)
   self.assertEqual(ns['_api_get'](self.h,'/otra',{},self.owner,self.owner)[0],418)
 def test_fuente_bloqueada(self):self.E.nucleo_bloqueado=True;self.assertEqual(self.get()[0],503)
if __name__=='__main__':unittest.main()
