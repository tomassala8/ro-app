"""ACT + recorte real con fixtures; sin servidor, DB, proveedor ni mutaciones de fuentes."""
import copy
import json
import re
from pathlib import Path
import unittest
from unittest.mock import patch
import permisos as P
from fuentes_verdad import clientes_activos as ACT
from pruebas_permisos_servicio import recortador_puro
INACTIVOS=('campalans','pgb-auditores','quique-gomez-barreda','jenasa','medalba')


class Activos(unittest.TestCase):
 def setUp(self):
  self.estado={'_ids':{'medalba'},'_activos':{'propio','ajeno'},'_no_operativos':set(INACTIVOS),
   '_rx':re.compile(r'(?:^| )medalba(?: |$)'),'_compactos':['medalba'],'_exactos':{'medalba'},'_nombres_no_operativos':set(INACTIVOS)}
  p=patch.object(ACT,'estado',return_value=self.estado);p.start();self.addCleanup(p.stop)
 def doc(self):
  return {'comun':[{'id':cid,'nombre':'Etiqueta fixture','gravedad':'critico','motivo':'Motivo fixture'} for cid in ('propio','ajeno')+INACTIVOS],
   'clientes':[{'cliente_id':cid,'nombre':'Etiqueta fixture'} for cid in ('propio','ajeno')+INACTIVOS],
   'personas':[{'id':'persona_fixture','nombre':'Persona fixture'}],'config':{'umbral':70}}
 def test_cuatro_inactivos_y_medalba_no_operan_en_comun(self):
  d=ACT.quitar_bajas(self.doc(),'verdad/clientes');self.assertEqual([r['id'] for r in d['comun']],['propio','ajeno']);self.assertEqual([r['cliente_id'] for r in d['clientes']],['propio','ajeno'])
 def test_sin_id_desconocido_o_id_tipo_invalido_no_alias(self):
  d=self.doc();d['comun']=[{'id':'desconocido','nombre':'Propio'},{'nombre':'Propio'},{'id':None,'nombre':'Propio'},{'id':123,'nombre':'Propio'}]
  self.assertEqual(ACT.quitar_bajas(d,'verdad/clientes')['comun'],[])
 def test_alias_nombre_no_concede_identidad(self):
  d=self.doc();d['comun']=[{'id':'campalans','nombre':'Cliente confirmado activo'}]
  self.assertEqual(ACT.quitar_bajas(d,'verdad/clientes')['comun'],[])
 def test_inmutable_y_conserva_config_personas(self):
  d=self.doc();antes=copy.deepcopy(d);out=ACT.quitar_bajas(d,'verdad/clientes')
  self.assertEqual(d,antes);self.assertEqual(out['personas'],d['personas']);self.assertEqual(out['config'],d['config'])
 def test_tareas_personas_ids_genericos_no_se_recortan_como_clientes(self):
  d={'comun':[{'id':'tarea_fixture','nombre':'Tarea global'}],'personas':[{'id':'persona_fixture','nombre':'Persona fixture'}]}
  self.assertEqual(ACT.quitar_bajas(d,'otro/modulo'),d)
 def test_historico_autorizado_no_borrado(self):
  d=self.doc()
  for rel in ('informe/fixture','informes/fixture','finanzas/fixture'):
   self.assertIs(ACT.quitar_bajas(d,rel),d)
 def test_act_revocado_en_siguiente_llamada(self):
  d=self.doc();self.assertEqual(len(ACT.quitar_bajas(d,'verdad/clientes')['comun']),2)
  self.estado['_activos'].remove('propio');self.assertEqual([r['id'] for r in ACT.quitar_bajas(d,'verdad/clientes')['comun']],['ajeno'])
 def scoped(self, real, vista):
  clientes=[{'id':'propio','nombre':'Propio','servicios':{'seo':'sí'}},{'id':'ajeno','nombre':'Ajeno','servicios':{'seo':'no'}}]
  raw={'clientes':clientes,'personas':[real,vista] if real['id']!=vista['id'] else [real], 'asignaciones':[{'cliente_id':'propio','persona_id':'cuentas','silla':'account'}]}
  d=self.doc()
  for r in d['comun']:r['nombre']=next((c['nombre'] for c in clientes if c['id']==r['id']),r['id'])
  f=recortador_puro(raw)
  with P.mirando_como(real,raw):
   return ACT.quitar_bajas(f(vista,P.contexto(vista,raw),d),'verdad/clientes')
 def test_crm_cliente_sin_id_null_desconocido_no_es_operativo(self):
  d={'subcuentas':[{'tipo':'cliente'},{'tipo':'sin_cliente','cliente_id':None},{'tipo':'cliente','cliente_id':'desconocido'},{'tipo':'cliente','cliente_id':'medalba'},{'cliente_id':None},{'tipo':'cliente','cliente_id':'propio'}]}
  self.assertEqual(ACT.quitar_bajas(d,'crm/crm')['subcuentas'],[d['subcuentas'][-1]])
 def test_crm_diagnostico_tecnico_preservado_sin_reclasificar(self):
  d={'subcuentas':[{'tipo':'prueba','sub_id':'fixture_prueba'},{'tipo':'interna','sub_id':'fixture_interna'},{'tipo':'sin_cliente','sub_id':'fixture_desconocida'}]}
  out=ACT.quitar_bajas(d,'crm/crm');self.assertEqual(out['subcuentas'],d['subcuentas'][:2]);self.assertTrue(all('cliente_id' not in r for r in out['subcuentas']))
 def test_crm_doble_scope_preserva_activos_autorizados(self):
  real={'id':'tomas_fixture','puestos':['direccion']};vista={'id':'cuentas','puestos':['account']}
  raw={'clientes':[{'id':'propio','nombre':'Propio'},{'id':'ajeno','nombre':'Ajeno'}],'personas':[real,vista], 'asignaciones':[{'persona_id':'cuentas','cliente_id':'propio','silla':'account'}]}
  d={'subcuentas':[{'tipo':'cliente','cliente_id':'propio'},{'tipo':'cliente','cliente_id':'ajeno'},{'tipo':'sin_cliente','nombre':'Propio'},{'tipo':'cliente','cliente_id':'jenasa'}]}
  with P.mirando_como(real,raw):
   out=ACT.quitar_bajas(recortador_puro(raw)(vista,P.contexto(vista,raw),d),'crm/crm')
  self.assertEqual(out['subcuentas'],[d['subcuentas'][0]])
 def test_direccion_scope_amplio_solo_activos(self):
  p={'id':'tomas_fixture','puestos':['direccion']};self.assertEqual([r['id'] for r in self.scoped(p,p)['comun']],['propio','ajeno'])
 def test_account_y_vercomo_account_conservan_solo_su_cartera(self):
  p={'id':'cuentas','puestos':['account']};t={'id':'tomas_fixture','puestos':['direccion']}
  self.assertEqual([r['id'] for r in self.scoped(p,p)['comun']],['propio']);self.assertEqual([r['id'] for r in self.scoped(t,p)['comun']],['propio'])
 def test_disciplina_servicio_explicito_sin_clientes_inactivos(self):
  p={'id':'seo_fixture','puestos':['jefa_seo']};t={'id':'tomas_fixture','puestos':['direccion']}
  self.assertEqual([r['id'] for r in self.scoped(t,p)['comun']],['propio'])


class FuenteLocal(unittest.TestCase):
 def test_lista_comun_actual_respeta_catalogo_ACT_sin_mostrar_contenido(self):
  d=json.loads((Path(__file__).parent/'data/verdad/clientes.json').read_text())
  out=ACT.quitar_bajas(d,'verdad/clientes')
  self.assertTrue(all(ACT.es_activo_id(r['id']) is True for r in out['comun']))
  self.assertTrue(all(r['id'] not in INACTIVOS for r in out['comun']))

 def test_crm_actual_sin_operativas_anonimas_y_diagnostico_explicito(self):
  d=json.loads((Path(__file__).parent/'data/crm/crm.json').read_text());out=ACT.quitar_bajas(d,'crm/crm')
  self.assertTrue(all(r.get('tipo') in ('prueba','interna') or ACT.es_activo_id(r.get('cliente_id')) is True for r in out['subcuentas']))

if __name__=='__main__':unittest.main()
