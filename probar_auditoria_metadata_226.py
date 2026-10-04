"""Auditoría independiente sólo fixtures: no modifica implementación/datos reales."""
import copy,json,types,unittest
from unittest.mock import patch
from datetime import datetime,timezone
import tareas_metadata_219 as API
import probar_tareas_metadata_219 as fixtures
from identidades_clickup_204 import preparar_autorizacion
from fuentes_verdad import clientes_activos as ACT

class Auditoria(unittest.TestCase):
 setUp=fixtures.Metadatos219.setUp
 get=fixtures.Metadatos219.get
 def test_detecta_modulo_revocado_durante_lectura_fuente(self):
  source=self.M._fuente_autorizacion_tareas
  def after_read():self.module=False;return source()
  self.M._fuente_autorizacion_tareas=after_read
  code,d=self.get()
  # Regresión: primero se reprodujo200; con guardia226 debe denegar.
  self.assertEqual(code,404);self.assertFalse(self.module)
 def test_detecta_act_revocado_durante_lectura_fuente(self):
  source=self.M._fuente_autorizacion_tareas
  def after_read():self.active=False;return source()
  self.M._fuente_autorizacion_tareas=after_read
  self.assertEqual(self.get()[0],404);self.assertFalse(self.active)
 def test_revocation_during_projection_final_gate_denies(self):
  original=API.proyectar
  def project(raw,ahora):
   result=original(raw,ahora);self.module=False;return result
  with patch.object(API,'proyectar',side_effect=project):self.assertEqual(self.get()[0],404)
 def test_rotation_while_projecting_never_publishes_previous_raw(self):
  original=API.proyectar
  def project(raw,ahora):
   result=original(raw,ahora);self.raws=[copy.deepcopy(raw)];return result
  with patch.object(API,'proyectar',side_effect=project):self.assertEqual(self.get()[0],404)
 def test_canonical_person_replacement_no_authority_cache_grant(self):
  def source():
   ps=copy.deepcopy(self.personas);ps[0]['estado']='baja';self.E.crudo['personas']=ps
   return preparar_autorizacion(ps,[{'id':'u-owner','email':'owner@example.invalid'}],self.raws,self.folder)
  self.M._fuente_autorizacion_tareas=source
  self.assertEqual(self.get()[0],404)
 def test_current_client_gate_after_source_can_already_deny(self):
  source=self.M._fuente_autorizacion_tareas
  def source_changed():self.allowed=False;return source()
  self.M._fuente_autorizacion_tareas=source_changed;self.assertEqual(self.get()[0],404)
 def test_corrupted_rows_never_echo_values(self):
  value='https://private.example/contract?secret=Fixture9_Sensible'
  for key in ('lista_id','estado','carpeta_id'):
   prior=self.raw[key];self.raw[key]=value;code,d=self.get();self.assertEqual(code,404);self.assertNotIn(value,json.dumps(d));self.raw[key]=prior
 def test_no_scope_from_watchers_or_manual_actor_roles(self):
  self.raw['watchers']=[{'id':'u-foreign'}]
  self.assertEqual(self.get(self.foreign)[0],404)
  self.assertEqual(self.get(dict(self.foreign,puestos=['direccion']),self.owner)[0],404)
 def test_actual_policy_service_scope_and_double_identity(self):
  import permisos as P
  clientes=[{'id':'client-fixture','nombre':'Fixture','servicios':{'seo':'sí'}}]
  self.E.crudo.update(clientes=clientes,asignaciones=[{'persona_id':'owner','cliente_id':'client-fixture','silla':'seo'}])
  self.M.P=P
  mods=P.cargar_modulos();self.M.S.ve_alguno=lambda p,ms:any(P.nivel_modulo(p,mods.get(m,{})) for m in ms)
  with P.mirando_como(self.ops,self.E.crudo):self.assertEqual(self.get(self.ops,self.owner)[0],200)
  clientes[0]['servicios']['seo']='no'
  with P.mirando_como(self.ops,self.E.crudo):self.assertEqual(self.get(self.ops,self.owner)[0],404)
  with P.mirando_como(self.owner,self.E.crudo):self.assertEqual(self.get(self.owner,self.ops)[0],404)
 def test_denied_scope_does_not_read_private_source(self):
  with patch.object(self.M,'_fuente_autorizacion_tareas',wraps=self.M._fuente_autorizacion_tareas) as reader:
   self.allowed=False;self.assertEqual(self.get()[0],404);self.assertEqual(reader.call_count,0)
   self.allowed=True;self.active=False;self.assertEqual(self.get()[0],404);self.assertEqual(reader.call_count,0)
 def test_no_mutation_metadata_projection_full_raw(self):
  before=copy.deepcopy(self.raw)
  self.get();self.get(self.ops,self.owner)
  self.assertEqual(self.raw,before)

if __name__=='__main__':unittest.main()
