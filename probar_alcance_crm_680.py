"""Recorte real de descriptores CRM; sólo catálogo y mensajes ficticios."""
import copy
import re
import unittest
from unittest.mock import patch
import permisos as P
from fuentes_verdad import clientes_activos as ACT
from pruebas_permisos_servicio import recortador_puro

class Alcance680(unittest.TestCase):
 def setUp(self):
  self.estado={'_ids':{'inactivo_fixture'},'_activos':{'propio','ajeno'},'_no_operativos':{'inactivo_fixture'},'_rx':re.compile(r'\binactivo_fixture\b'),'_compactos':['inactivofixture'],'_exactos':{'inactivo_fixture'},'_nombres_no_operativos':{'inactivo_fixture'}}
  p=patch.object(ACT,'estado',return_value=self.estado);p.start();self.addCleanup(p.stop)
 def doc(self):
  def lead(cid):
   return {'cliente_id':cid,'sub_id':'sub_'+cid,'ref':'ref_'+cid,'respondio':True,'creado_iso676':'2026-10-01T10:00:00+00:00','respuesta_medicion676':{'version':'676.1','fuente':'ghl_conversacion','estado':'observado_parcial','completa':False,'cliente_id':cid,'sub_id':'sub_'+cid,'ref':'ref_'+cid,'entradas_observadas':1,'desde_ms':1790848800000,'hasta_ms':1791108000000,'ultima_entrada_ms':1790848860000,'respuesta_humana_confirmada':None,'resultado_comercial_confirmado':None}}
  return {'generado':'2026-10-04 12:00','leads':[lead(cid) for cid in ('propio','ajeno','inactivo_fixture','desconocido_fixture')], 'subcuentas':[], 'fuentes':{'ghl':{'estado':'bien','hora':'2026-10-04 12:00'}}}
 def recortar(self,real,vista,doc):
  raw={'clientes':[{'id':c,'nombre':'Cliente ficticio'} for c in ('propio','ajeno','inactivo_fixture')], 'personas':[real,vista], 'asignaciones':[{'persona_id':'cuentas','cliente_id':'propio','silla':'account'}]}
  with P.mirando_como(real,raw):return ACT.quitar_bajas(recortador_puro(raw)(vista,P.contexto(vista,raw),doc),'crm/crm')
 def test_account_solo_descriptor_propio(self):
  p={'id':'cuentas','puestos':['account']};d=self.doc();before=copy.deepcopy(d);out=self.recortar(p,p,d)
  self.assertEqual([x['cliente_id'] for x in out['leads']],['propio']);self.assertEqual(out['leads'][0]['respuesta_medicion676'],d['leads'][0]['respuesta_medicion676']);self.assertEqual(d,before)
 def test_ver_como_account_no_amplia(self):
  real={'id':'direccion_fixture','puestos':['direccion']};vista={'id':'cuentas','puestos':['account']}
  self.assertEqual([x['cliente_id'] for x in self.recortar(real,vista,self.doc())['leads']],['propio'])
 def test_real_account_vista_direccion_no_amplia(self):
  real={'id':'cuentas','puestos':['account']};vista={'id':'direccion_fixture','puestos':['direccion']}
  self.assertEqual([x['cliente_id'] for x in self.recortar(real,vista,self.doc())['leads']],['propio'])
 def test_direccion_activos_y_fecha_original(self):
  p={'id':'direccion_fixture','puestos':['direccion']};d=self.doc();out=self.recortar(p,p,d)
  self.assertEqual([x['cliente_id'] for x in out['leads']],['propio','ajeno']);self.assertEqual(out['fuentes'],d['fuentes']);self.assertEqual(out['generado'],d['generado'])
 def test_revocacion_activa_siguiente_lectura(self):
  p={'id':'direccion_fixture','puestos':['direccion']};d=self.doc();self.estado['_activos'].remove('propio')
  self.assertEqual([x['cliente_id'] for x in self.recortar(p,p,d)['leads']],['ajeno'])
if __name__=='__main__':unittest.main()
