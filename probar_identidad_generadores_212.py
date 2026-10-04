"""Generadores reales con datos sintéticos inyectados; cero proveedores/caches reales."""
import unittest,json,io,copy,sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from contextlib import redirect_stdout
from identidad_generadores_212 import identidades,carpetas_confirmadas,clientes_directos
A=Path(__file__).parent;sys.path.insert(0,str(A/'fuentes_produccion'))
from fuentes_produccion import generar_produccion as GP
from fuentes_mi_trabajo import generar_mi_trabajo as GM

def cli(cid,folder):return {'id':cid,'nombre':'Nombre igual no autoriza','fuentes':{'tareas':{'datos':{'carpeta_id':folder}}}}

class Canonico(unittest.TestCase):
 def test_only_exact_no_names_and_historical_active_not_a_permission(self):
  ps=[{'id':'p','nombre':'Nombre Coincidente','correo':'p@example.test','estado':'baja'}]
  us=[{'id':1,'email':'p@example.test','nombre':'Otro'},{'id':2,'email':'otra@example.test','nombre':'Nombre Coincidente'}]
  self.assertEqual(identidades(ps,us)['por_usuario'],{'1':'p'})
 def test_duplicate_person_id_not_collapsed_before_resolution(self):
  p={'id':'p','correo':'p@example.test'};self.assertEqual(identidades([p,p],[{'id':1,'email':'p@example.test'}])['por_usuario'],{})
 def test_shared_email_ambiguous_never_choose(self):
  self.assertEqual(identidades([{'id':'p','correo':'x@example.test'},{'id':'q','correo':'x@example.test'}],[{'id':1,'email':'x@example.test'}])['por_usuario'],{})
 def test_conflicting_provider_sameid_never_destinatary(self):
  r=identidades([{'id':'p','correo':'p@example.test'}],[{'id':1,'email':'p@example.test'},{'id':1,'email':'otra@example.test'}]);self.assertEqual(r['por_usuario'],{});self.assertEqual(r['usuario_unico_por_persona'],{})
 def test_multiple_exact_users_read_but_no_automatic_destinatary(self):
  r=identidades([{'id':'p','correo':'p@example.test'}],[{'id':1,'email':'p@example.test'},{'id':2,'email':'p@example.test'}]);self.assertEqual(r['por_usuario'],{'1':'p','2':'p'});self.assertEqual(r['usuario_unico_por_persona'],{})
 def test_folder_duplicate_or_unknown_no_name_match(self):
  folders,names=carpetas_confirmadas([cli('a','f'),cli('b','f'),cli('c',None)]);self.assertEqual(folders,{});self.assertEqual(len(names),3)
 def test_client_identity_duplicate_no_folder(self):
  self.assertEqual(carpetas_confirmadas([cli('a','f'),cli('a','g')]),({},{}))
 def test_safe_documents_missing_shape_and_boolean_folder(self):
  folders,_=carpetas_confirmadas([cli('a',False),{'id':'b','fuentes':None},cli('c',123)]);self.assertEqual(folders,{'123':('c','Nombre igual no autoriza')})
 def test_reader_temp_symlink_rejected(self):
  with TemporaryDirectory() as d:
   p=Path(d);(p/'clientes').mkdir();(p/'real.json').write_text('{}');(p/'clientes/a.json').symlink_to(p/'real.json')
   with self.assertRaises(ValueError):clientes_directos(p)

class Generadores(unittest.TestCase):
 def run_generators(self,people=None,plan_fixture=None):
  people=people or [{'id':'p','nombre':'Nombre Coincidente','correo':'p@example.test','estado':'activo','puestos':['account'],'alias':'P','imputa_horas':'sí','horas_mes':128}]
  users=[{'id':1,'nombre':'Otro','email':'p@example.test'},{'id':2,'nombre':'Nombre Coincidente','email':'sin-mapa@example.test'}]
  tasks=[{'id':tid,'nombre':'Tarea fixture','lista_id':'l','carpeta_id':folder,'carpeta':'Nombre igual no autoriza','espacio':'Fixture','estado':'en curso','tipo_estado':'custom','asignados':[{'id':uid}], 'historial':[], 'descripcion':'Brief fixture','estado_fuente':'clickup','estado_leido_utc':'2026-10-03T01:00:00Z'} for tid,uid,folder in [('known',1,'f'),('unresolved',2,'f'),('folder_unknown',1,'missing')]]
  raw={'meta':{'generado':'2026-10-03 02:00','cobertura':{'completa':False}},'tareas':tasks}
  hours={'meta':{'generado':'2026-10-02 02:00'},'entradas':[{'usuario_id':uid,'task_id':tid,'inicio':'2026-10-02T09:00:00+02:00','horas':hs,'carpeta_id':'f'} for uid,tid,hs in [(1,'known',2),(2,'unresolved',9)]]}
  catalog={'listas':{'l':{'ok':True,'estados':[{'status':'en curso','type':'custom'}]}},'cobertura':{'completa':True}}
  output={}
  def leer(path,defecto=None):
   key=str(path)
   if key.endswith('produccion/produccion.json'):return output['produccion.json']
   if key.endswith('/tareas.json'):return raw
   if key.endswith('/horas.json'):return hours
   if key.endswith('/estados_listas.json'):return catalog
   if key.endswith('/asignaciones.json'):return []
   if key.endswith('/planificacion.json'):return plan_fixture if plan_fixture is not None else {'Nombre Coincidente':{'n':3,'por_dia':{}}}
   if key.endswith('/tareas_flujo.json'):return {'Nombre igual no autoriza':{'carpeta_id':'missing'}}
   return defecto
  with TemporaryDirectory() as d:
   data=Path(d);(data/'clientes').mkdir();(data/'clientes/a.json').write_text(json.dumps(cli('a','f')))
   for mod in (GP,GM):
    with patch.object(mod,'DATA',data),patch.object(mod,'personas',return_value=people),patch.object(mod,'miembros_clickup',return_value=users),patch.object(mod,'leer',side_effect=leer),patch.object(mod,'escribir',side_effect=lambda path,datos,compacto=False:output.update({Path(path).name:copy.deepcopy(datos)})),redirect_stdout(io.StringIO()):mod.main()
  return output
 def test_both_generators_task_hours_and_private_inventory_exact(self):
  out=self.run_generators();pr=out['produccion.json'];mi=out['mi_trabajo.json'];board=out['tablero_tareas.json']
  self.assertEqual({t['id'] for t in pr['cola']},{'known','folder_unknown'});self.assertEqual({t['id'] for t in mi['tareas']},{'known','folder_unknown'})
  self.assertEqual(next(t for t in mi['tareas'] if t['id']=='folder_unknown')['cli'],None)
  self.assertEqual(next(p for p in pr['personas'] if p['persona_id']=='p')['horas_mes'],2)
  self.assertEqual(sum(mi['horas_dia'][0]['dias'].values()),2)
  self.assertEqual({t['id'] for t in board['tareas']},{'known','unresolved','folder_unknown'})
  unresolved=next(t for t in board['tareas'] if t['id']=='unresolved');self.assertEqual(unresolved['asignados'],[]);self.assertEqual(unresolved['_usuarios_asignados'],['2']);self.assertEqual(unresolved['asignados_sin_identidad'],1)
  self.assertEqual(pr['proyectos'],[]);self.assertEqual(pr['no_planificado'],[]);self.assertIsNone(pr['no_planificado_cobertura']['total_semana']);self.assertEqual(pr['no_planificado_cobertura']['filas_sin_identidad'],1)
  self.assertEqual(board['usuarios_personas'],{'p':'1'});self.assertEqual(mi['fuentes']['horas']['hora'],'2026-10-02 02:00')
 def test_noplan_explicit_identity_preserved_and_missing_source_unknown(self):
  source={'_meta':{'generado':'2026-10-02'},'Etiqueta no determina identidad':{'persona_id':'p','semana':{'rompen':3,'creadas':4,'ejemplos':[]},'semana_ant':{'rompen':1}}}
  out=self.run_generators(plan_fixture=source)['produccion.json'];self.assertEqual(out['no_planificado'][0]['persona_id'],'p');self.assertEqual(out['no_planificado_cobertura']['total_semana'],3)
  empty=self.run_generators(plan_fixture={})['produccion.json'];self.assertIsNone(empty['no_planificado_cobertura']['total_semana'])
 def test_duplicate_person_source_no_generated_attribution(self):
  p={'id':'p','nombre':'Nombre Coincidente','correo':'p@example.test','estado':'activo','puestos':[]};out=self.run_generators([p,p])
  self.assertEqual(out['produccion.json']['cola'],[]);self.assertEqual(out['mi_trabajo.json']['tareas'],[]);self.assertEqual(out['tablero_tareas.json']['usuarios_personas'],{})

if __name__=='__main__':unittest.main()
